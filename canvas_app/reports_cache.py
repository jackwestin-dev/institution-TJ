"""
Local disk cache for Canvas New Quizzes Student Analysis CSVs.

Layout (repo root, gitignored — these exports carry student names):
  reports_cache/
    index.json          <- metadata for every cached quiz
    {course_id}_{assignment_id}.csv

Populated by sync_reports.py on a local checkout. The deployed app has no
cache directory and every reader here degrades to empty rather than raising.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from . import question_filter
from .config import CACHE_DIR

INDEX_FILE = CACHE_DIR / "index.json"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_index() -> dict:
    """Return the full index dict. Keys are "{course_id}_{assignment_id}"."""
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_index(index: dict) -> None:
    _ensure_dir()
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def _key(course_id: int, assignment_id: int) -> str:
    return f"{course_id}_{assignment_id}"


def _csv_path(course_id: int, assignment_id: int) -> Path:
    return CACHE_DIR / f"{course_id}_{assignment_id}.csv"


def is_cached(course_id: int, assignment_id: int) -> bool:
    key = _key(course_id, assignment_id)
    return key in load_index() and _csv_path(course_id, assignment_id).exists()


def get_cached_csv(course_id: int, assignment_id: int) -> "bytes | None":
    """The cached export, with any excluded questions removed.

    Every reader goes through here, so an activity where the class never reached
    some questions is corrected once rather than in each caller. The file on disk
    stays exactly as Canvas exported it — see canvas_app.question_filter.
    """
    path = _csv_path(course_id, assignment_id)
    if not path.exists():
        return None
    return question_filter.apply(course_id, assignment_id, path.read_bytes())


def save_csv(
    course_id: int,
    assignment_id: int,
    csv_bytes: bytes,
    *,
    title: str = "",
    points_possible: "float | None" = None,
    due_at: str = "",
    n_students: int = 0,
) -> None:
    """Write CSV bytes to disk and update the index."""
    _ensure_dir()
    _csv_path(course_id, assignment_id).write_bytes(csv_bytes)
    index = load_index()
    index[_key(course_id, assignment_id)] = {
        "title": title,
        "points_possible": points_possible,
        "due_at": due_at,
        "n_students": n_students,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    save_index(index)


def cached_for_course(course_id: int) -> list:
    """
    Return list of dicts for every cached quiz in this course.
    Each dict: {assignment_id, title, points_possible, due_at, n_students, cached_at}
    """
    index = load_index()
    prefix = f"{course_id}_"
    result = []
    for key, meta in index.items():
        if key.startswith(prefix):
            try:
                assignment_id = int(key[len(prefix):])
            except ValueError:
                continue
            if _csv_path(course_id, assignment_id).exists():
                result.append({"assignment_id": assignment_id, **meta})
    return result


def missing_from_cache(course_id: int, quiz_list: list) -> list:
    """
    Given the full quiz list for a course, return those not yet cached.
    quiz_list items must have "id" field.
    """
    return [q for q in quiz_list if not is_cached(course_id, q["id"])]
