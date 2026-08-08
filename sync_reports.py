#!/usr/bin/env python
"""
Standalone report-cache sync agent.

Downloads every New Quiz (LTI) Student Analysis report for a course and writes
it into reports_cache/, exactly like the dashboard's "Report Cache" section —
but runs OUTSIDE Streamlit. The in-app sync drives Playwright's *sync* API from
ThreadPoolExecutor threads inside Streamlit's own event loop, which is what
keeps crashing it.

This is also the ONLY way to refresh data for the deployed app: Streamlit
Community Cloud cannot install Chromium and its filesystem is ephemeral. Run
this locally, then rebuild the committed aggregate and push:

    python sync_reports.py
    python build_canvas_metrics.py
    git add data/ && git commit -m "Refresh Canvas metrics" && git push

Parallelism model (why it doesn't crash like the dashboard):
  * Each download runs in its OWN process (ProcessPoolExecutor), so every
    headless Chromium is fully isolated — no shared event loop, no thread
    safety issues.
  * Workers ONLY fetch and return the raw CSV bytes. The single parent process
    does every cache write, so index.json can never be corrupted by concurrent
    writers.

Usage:
    python sync_reports.py                      # all courses, 4 parallel workers
    python sync_reports.py --workers 10         # up to 10 downloads at once
    python sync_reports.py --course 345         # only course 345
    python sync_reports.py --force              # re-download even if cached
    python sync_reports.py --list               # list courses + cache status only

Credentials come from .env (CANVAS_URL, CANVAS_TOKEN) or the environment.
"""
import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

from dotenv import load_dotenv

from canvas_app import reports_cache as rc
from canvas_app.canvas_api import CanvasAPI
from canvas_app.report_fetcher import is_playwright_available, fetch_quiz_report_csv

load_dotenv()


def _is_past_or_undated(q: dict) -> bool:
    """Include quizzes with no due date or a due date in the past."""
    due = q.get("due_at") or ""
    if not due:
        return True
    try:
        parsed = datetime.fromisoformat(due.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _fetch_worker(task: dict) -> dict:
    """
    Runs in a child process. Fetches ONE report and returns its bytes.
    Does NOT touch the cache — the parent process owns all writes.
    """
    try:
        csv_bytes = fetch_quiz_report_csv(
            canvas_url=task["canvas_url"],
            api_token=task["token"],
            course_id=task["course_id"],
            assignment_id=task["assignment_id"],
            status_callback=lambda m: None,
            generate_if_missing=task.get("generate_if_missing", False),
        )
        return {**task, "ok": True, "csv": csv_bytes}
    except Exception as e:  # return, don't raise — keeps the pool healthy
        return {**task, "ok": False, "error": str(e)}


def gather_targets(api: CanvasAPI, canvas_url: str, token: str, courses: list,
                   *, force: bool) -> list:
    """Build the flat list of reports to download across all courses."""
    targets = []
    for c in sorted(courses, key=lambda x: x.get("name", "")):
        cid, cname = c["id"], c.get("name", str(c["id"]))
        try:
            quizzes = api.get_quizzes(cid)
        except Exception as e:
            print(f"  ! {cname}: could not load quizzes: {e}")
            continue
        lti = [q for q in quizzes if q.get("_type") == "new"]
        n_skip = 0
        for q in lti:
            if not force and rc.is_cached(cid, q["id"]):
                n_skip += 1
                continue
            if not _is_past_or_undated(q):
                n_skip += 1
                continue
            targets.append({
                "canvas_url": canvas_url,
                "token": token,
                "course_id": cid,
                "course_name": cname,
                "assignment_id": q["id"],
                "title": q.get("title", str(q["id"])),
                "points_possible": q.get("points_possible"),
                "due_at": q.get("due_at", ""),
            })
        print(f"  {cname} (course {cid}): {len(lti)} New Quizzes | "
              f"{n_skip} skipped | {len([t for t in targets if t['course_id'] == cid])} queued")
    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Canvas New Quiz reports into the local cache.")
    ap.add_argument("--course", type=int, help="Only sync this course ID (default: all teacher courses).")
    ap.add_argument("--workers", type=int, default=4, help="Parallel downloads (default 4, max 10).")
    ap.add_argument("--force", action="store_true", help="Re-download even if already cached.")
    ap.add_argument("--generate", action="store_true",
                    help="Click 'Generate Report' and poll up to 2 min when a report "
                         "isn't ready. Default: export-only (assumes reports are "
                         "pre-generated in Canvas) — fails fast on ungenerated reports.")
    ap.add_argument("--list", action="store_true", help="List courses and cache status, download nothing.")
    args = ap.parse_args()

    workers = max(1, min(args.workers, 10))

    canvas_url = os.getenv("CANVAS_URL", "").strip()
    token = os.getenv("CANVAS_TOKEN", "").strip()
    if not canvas_url or not token:
        print("ERROR: CANVAS_URL and CANVAS_TOKEN must be set in .env or the environment.")
        return 2

    if not is_playwright_available():
        print("ERROR: Playwright is not installed.\n"
              "  pip install playwright && playwright install chromium")
        return 2

    api = CanvasAPI(canvas_url, token)

    if args.course:
        courses = [{"id": args.course, "name": f"Course {args.course}"}]
    else:
        try:
            courses = api.get_courses()
        except Exception as e:
            print(f"ERROR: could not load courses: {e}")
            return 2

    if args.list:
        for c in sorted(courses, key=lambda x: x.get("name", "")):
            cid = c["id"]
            print(f"  [{cid}] {c.get('name', '')} — {len(rc.cached_for_course(cid))} cached")
        return 0

    print("Gathering quizzes...")
    targets = gather_targets(api, canvas_url, token, courses, force=args.force)
    for t in targets:
        t["generate_if_missing"] = args.generate
    n = len(targets)
    if n == 0:
        print("\n=== Nothing to download — cache is up to date. ===")
        return 0

    mode = "generate+export" if args.generate else "export-only (fast-fail if not generated)"
    print(f"\nDownloading {n} report(s) with {workers} parallel worker(s) — mode: {mode}...\n")

    n_ok = n_fail = 0
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_worker, t): t for t in targets}
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            title = res["title"][:55]
            if res.get("ok"):
                # Parent-only cache write — no index.json race.
                rc.save_csv(
                    res["course_id"], res["assignment_id"], res["csv"],
                    title=res["title"],
                    points_possible=res["points_possible"],
                    due_at=res["due_at"],
                )
                n_ok += 1
                print(f"[{done}/{n}] OK    {title} ({len(res['csv']) // 1024} KB)", flush=True)
            else:
                n_fail += 1
                print(f"[{done}/{n}] FAIL  {title} — {res['error']}", flush=True)

    print(f"\n=== DONE: {n_ok} downloaded, {n_fail} failed (of {n}) ===")
    return 1 if n_fail else 0


if __name__ == "__main__":
    main_rc = main()
    sys.exit(main_rc)
