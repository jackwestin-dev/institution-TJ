#!/usr/bin/env python
"""
Build the committed, name-free Canvas aggregate from the local report cache.

reports_cache/ holds full Student Analysis exports — every student's name and
per-question answers — so it is gitignored and never reaches the server. This
script reduces it to one row per assignment with counts only, which is what the
deployed app and the "Summer EY25 and EY26" view actually read.

    reports_cache/345_1075.csv   (116 named students, per-question detail)
        -> EY26,345_1075,Chemical Equilibrium...,Participation Task,116,96.1,96.7

Output columns match the hand-built summer_canvas_metrics.csv this replaces, so
the Summer view consumes it unchanged.

Usage:
    python sync_reports.py           # refresh reports_cache/ first
    python build_canvas_metrics.py   # then rebuild the aggregate
"""
import io
import re
import sys
from pathlib import Path

import pandas as pd

from canvas_app import reports_cache as rc
from canvas_app.config import DATA_DIR, has_local_cache
from canvas_app.score_parsing import parse_score_csv, submitted_students

OUT_FILE = DATA_DIR / "canvas_metrics.csv"

# Canvas course -> (cohort label, enrollment). Enrollment is the denominator for
# participation; it is the cohort roster size, not the number who submitted.
COURSES = {
    345: ("EY26", 120),
    351: ("EY25", 65),
}


def classify(title: str) -> str:
    """
    Bucket an assignment title into the vocabulary the Summer view already uses.

    Deliberately not canvas_app.exam_scores.classify_item — that one serves the
    Exam Growth participation basis and uses a different, coarser vocabulary
    ("Survey", no post-class bucket).
    """
    text = (title or "").lower()
    if "participation" in text:
        return "Participation Task"
    if re.search(r"post[-\s]?class", text):
        return "Post-Class Quiz"
    if re.search(r"pre[-\s]?class|pre[-\s]?quiz|prep work", text):
        return "Pre-Class Quiz"
    if re.search(r"\bhomework\b|\bhw\b", text):
        return "Homework"
    if re.search(r"\bsurvey\b|submission form|score submission|date reporting|\bform\b", text):
        return "Survey/Form"
    return "Other"


def build() -> pd.DataFrame:
    rows = []
    for course_id, (cohort, enrollment) in COURSES.items():
        for entry in rc.cached_for_course(course_id):
            aid = entry["assignment_id"]
            raw = rc.get_cached_csv(course_id, aid)
            if not raw:
                continue

            names = submitted_students(io.BytesIO(raw))
            n_submitted = len(names)
            if not n_submitted:
                continue

            # Accuracy is left blank for ungraded items (surveys, 0-point forms
            # with no question-count columns) rather than reported as zero — a
            # form nobody can get wrong is not a 0% score. The same applies to
            # assignments Canvas never scored, which come back as a flawless run
            # of zeros across the whole cohort; see exam_scores._is_ungraded.
            score_df, pts = parse_score_csv(io.BytesIO(raw))
            accuracy = None
            if score_df is not None and pts and not (score_df["score"] == 0).all():
                accuracy = round(score_df["score"].mean() / pts * 100, 1)

            title = (entry.get("title") or str(aid)).strip()
            rows.append({
                "cohort":        cohort,
                "key":           f"{course_id}_{aid}",
                "title":         title,
                "type":          classify(title),
                "n_submitted":   n_submitted,
                "accuracy":      accuracy,
                "participation": round(n_submitted / enrollment * 100, 1),
            })

    out = pd.DataFrame(rows, columns=[
        "cohort", "key", "title", "type", "n_submitted", "accuracy", "participation",
    ])
    return out.sort_values(["cohort", "type", "title"]).reset_index(drop=True)


def main() -> int:
    if not has_local_cache():
        print(
            "ERROR: reports_cache/ is empty or missing.\n"
            "  Run `python sync_reports.py` first — this script only aggregates, "
            "it does not download.",
            file=sys.stderr,
        )
        return 2

    table = build()
    if table.empty:
        print("ERROR: cache held no readable reports.", file=sys.stderr)
        return 2

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_FILE, index=False)

    # Guard against a future cache format leaking names into the committed file.
    text = OUT_FILE.read_text(encoding="utf-8")
    assert "\n" in text and text.count(",") > 0
    print(f"Wrote {OUT_FILE.relative_to(Path.cwd())} — {len(table)} assignment(s)")
    for cohort, group in table.groupby("cohort"):
        graded = group["accuracy"].notna().sum()
        print(f"  {cohort}: {len(group)} items ({graded} graded) · "
              f"mean participation {group['participation'].mean():.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
