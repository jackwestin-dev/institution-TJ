import requests
from typing import Optional


class CanvasAPI:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self._s = requests.Session()
        self._s.headers.update({"Authorization": f"Bearer {token}"})

    def _next_page(self, resp: requests.Response) -> Optional[str]:
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None

    def _get_list(self, path: str, params: dict = None) -> list:
        url = f"{self.base_url}/api/v1/{path}"
        out = []
        while url:
            r = self._s.get(url, params=params, timeout=30)
            r.raise_for_status()
            out.extend(r.json())
            url = self._next_page(r)
            params = None
        return out

    def get_courses(self) -> list:
        return self._get_list(
            "courses",
            {"enrollment_type": "teacher", "state[]": ["available", "completed"], "per_page": 100},
        )

    def get_quizzes(self, course_id: int) -> list:
        # Classic Quizzes
        classic = self._get_list(f"courses/{course_id}/quizzes", {"per_page": 100})
        for q in classic:
            q.setdefault("_type", "classic")

        # New Quizzes (Canvas Quiz LTI) — identified by quiz-lti in external_tool_tag_attributes.url
        try:
            assignments = self._get_list(
                f"courses/{course_id}/assignments",
                {"per_page": 100},
            )
            new_quizzes = []
            for a in assignments:
                tag = a.get("external_tool_tag_attributes") or {}
                tool_url = (tag.get("url") or "")
                if "quiz-lti" in tool_url:
                    new_quizzes.append({
                        "id":              a["id"],
                        "title":           a["name"],
                        "points_possible": a.get("points_possible"),
                        "_type":           "new",
                        "due_at":          a.get("due_at") or a.get("created_at") or "",
                        "created_at":      a.get("created_at") or "",
                    })
        except Exception:
            new_quizzes = []

        return classic + new_quizzes

    def get_quiz_submissions(self, course_id: int, quiz_id: int, quiz_type: str = "classic") -> tuple:
        """Returns (submissions_list, users_dict {id: name})."""
        if quiz_type == "new":
            return self._get_assignment_submissions(course_id, quiz_id)

        url = f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"
        params = {"include[]": ["user"], "per_page": 100}
        submissions, users = [], {}
        while url:
            r = self._s.get(url, params=params, timeout=30)
            r.raise_for_status()
            body = r.json()
            submissions.extend(body.get("quiz_submissions", []))
            for u in body.get("users", []):
                users[u["id"]] = u.get("name", str(u["id"]))
            url = self._next_page(r)
            params = None
        return submissions, users

    def _get_assignment_submissions(self, course_id: int, assignment_id: int) -> tuple:
        """Fetch New Quiz (LTI) submissions via the assignments submissions endpoint."""
        raw = self._get_list(
            f"courses/{course_id}/assignments/{assignment_id}/submissions",
            {"include[]": ["user"], "per_page": 100},
        )
        submissions, users = [], {}
        # States that mean the student actually submitted something
        submitted_states = {"graded", "pending_review", "submitted"}
        for s in raw:
            state = s.get("workflow_state") or ""
            uid = s.get("user_id")
            user = s.get("user") or {}
            if uid and user.get("name"):
                users[uid] = user["name"]
            if state not in submitted_states:
                continue
            submissions.append({
                "user_id":        uid,
                "score":          s.get("score"),
                "kept_score":     s.get("score"),
                "attempt":        s.get("attempt", 1),
                # normalise so app.py filter of workflow_state=="complete" works
                "workflow_state": "complete",
            })
        return submissions, users

    def get_students(self, course_id: int) -> dict:
        """Return {user_id: name} for all students enrolled in the course."""
        users = self._get_list(
            f"courses/{course_id}/users",
            {"enrollment_type[]": ["student"], "per_page": 100},
        )
        return {
            u["id"]: u.get("name", str(u["id"]))
            for u in users
            if isinstance(u, dict) and "id" in u
        }

    def get_modules(self, course_id: int) -> list:
        """
        Return course modules with their assignment items, sorted by position.
        Each entry: {id, name, position, assignments: [{assignment_id, title}]}
        """
        modules = self._get_list(
            f"courses/{course_id}/modules",
            {"per_page": 100, "include[]": ["items"]},
        )
        result = []
        for mod in modules:
            if not isinstance(mod, dict):
                continue
            items = mod.get("items") or []
            if not items:
                try:
                    items = self._get_list(
                        f"courses/{course_id}/modules/{mod['id']}/items",
                        {"per_page": 100},
                    )
                except Exception:
                    items = []
            assignment_items = [
                {"assignment_id": item["content_id"], "title": item.get("title", "")}
                for item in items
                if isinstance(item, dict)
                and item.get("type") in ("Assignment", "Quiz")
                and item.get("content_id")
            ]
            result.append({
                "id":          mod["id"],
                "name":        mod.get("name", f"Module {mod['id']}"),
                "position":    mod.get("position", 0),
                "assignments": assignment_items,
            })
        return sorted(result, key=lambda m: m["position"])

    def get_quiz_statistics(self, course_id: int, quiz_id: int) -> Optional[dict]:
        r = self._s.get(
            f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}/statistics",
            timeout=30,
        )
        if r.status_code == 403:
            return None
        r.raise_for_status()
        return r.json()
