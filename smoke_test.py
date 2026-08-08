#!/usr/bin/env python
"""
Headless check that every view loads, under both conditions the app runs in.

The interesting case is the second one. Locally you have reports_cache/,
exam_data/ and a .env, so everything is populated and bugs in the empty-state
paths stay hidden. On Streamlit Community Cloud none of those exist — that is
where a merge like this breaks, and where a page that assumes its data is
present raises instead of prompting.

    python smoke_test.py

Exits non-zero if any view raises.
"""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent
PRESENTATION_VIEWS = ["Exam Growth", "Course Performance", "Attendance"]
ADMIN_VIEWS = ["Canvas Explorer (live)"]
SCHOLAR_VIEWS = [
    "EY25 Scholar March-May Engagement, Interventions, and Predictions",
    "Individual Student Data - EY25",
    "Summer EY25 and EY26",
]

# Everything the deployed app does NOT have.
LOCAL_ONLY = ["reports_cache", "exam_data", ".env"]


@contextmanager
def hidden(names):
    """Temporarily move paths aside so the app sees a bare server checkout."""
    moved = []
    try:
        for name in names:
            src = ROOT / name
            if src.exists():
                dst = ROOT / f"_smoketest_hidden_{name}"
                src.rename(dst)
                moved.append((src, dst))
        yield
    finally:
        for src, dst in moved:
            dst.rename(src)


def _radio(at, label):
    return next(r for r in at.radio if r.label == label)


def check(label: str, section: str, view: str, staff: bool = False) -> bool:
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=300).run()
    _radio(at, "Section").set_value(section).run()
    if staff:
        at.checkbox[0].set_value(True).run()
    _radio(at, "View").set_value(view).run()

    problems = [str(e.value) for e in at.exception]
    print(f"[{'FAIL' if problems else 'ok'}] {label}: {view}")
    for p in problems:
        print(f"       {p[:300]}")
    return not problems


def main() -> int:
    ok = True

    print("--- local checkout (cache, exam data and .env present) ---")
    for view in SCHOLAR_VIEWS:
        ok &= check("local", "Scholar Dashboard", view)
    for view in PRESENTATION_VIEWS:
        ok &= check("local", "JAMP EY26", view)
    for view in ADMIN_VIEWS:
        ok &= check("local", "JAMP EY26", view, staff=True)

    print("\n--- deployed server (no cache, no exam data, no .env) ---")
    with hidden(LOCAL_ONLY):
        for view in SCHOLAR_VIEWS:
            ok &= check("server", "Scholar Dashboard", view)
        for view in PRESENTATION_VIEWS:
            ok &= check("server", "JAMP EY26", view)
        for view in ADMIN_VIEWS:
            ok &= check("server", "JAMP EY26", view, staff=True)

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
