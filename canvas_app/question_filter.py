"""Questions excluded from a cached report, and the arithmetic to remove them.

Sometimes a class does not reach every question on an activity. The Canvas
export still counts the unreached questions against every student, so the
activity reads far worse than it was. CARS: Assumption & Analogy (345_1230) is
the case this was built for: the session ran out of time before the soccer
passage, 64 of the 90 submissions have its two questions as "No Answer", and the
cohort average reads 61.6% instead of the 91.9% the students actually earned on
the three questions they were taught.

The exclusion is declarative and applied on *read*, in reports_cache.get_cached_csv,
rather than by editing the cached CSV. Two reasons:

  * reports_cache/ is a faithful copy of what Canvas exported. Rewriting a file
    there makes the cache disagree with Canvas with nothing on disk to say why.
  * sync_reports.py re-downloads reports. An edited file would be silently
    overwritten and the bad number would come back with no warning.

Recomputing the tallies needs to know which answer was correct, and on a 0-point
New Quiz the export cannot say: every EarnedPoints is 0 and Status only reads
"Graded" or "No Answer". The correct answers below come from that quiz's *Quiz
and Item Analysis* report, whose AnswerFrequencies JSON flags the right option.
Only the dropped questions need an entry, because the tallies are adjusted by
subtraction:

    new_correct   = NumberOfCorrect   - (dropped questions answered correctly)
    new_incorrect = NumberOfIncorrect - (dropped questions answered wrongly)
    new_noresponse = NoResponse       - (dropped questions left blank)

which needs no knowledge of how the retained questions were answered.
"""
import html
import io
import re

import pandas as pd

# (course_id, assignment_id) -> {ItemID: correct answer text}
#
# Verified: recomputing all five questions from these answers reproduced Canvas's
# own NumberOfCorrect on all 90 rows of 345_1230 before the two were dropped.
EXCLUDED_QUESTIONS = {
    (345, 1230): {
        # CARS: Assumption & Analogy Participation Task, 2026-08-13.
        # Q4 and Q5 belong to the soccer/World Cup passage, which the session
        # never got to. 64 of 90 students left both blank.
        1632: "More women play soccer than men.",
        1637: "a fair game is fair in as many ways as possible.",
    },
    (345, 1246): {
        # ETC, ATP Production & Bioenergetics Participation Task, 2026-08-31.
        # Canvas "Participation Task 7", which is the SIXTH question block in
        # the export — this activity's export order does not match Canvas's item
        # numbering, so the ItemID is the only safe handle. 17 of 92 blank
        # against 0-3 on the questions the class did reach.
        1734: "Oxaloacetate is siphoned into gluconeogenesis, so acetyl-CoA "
              "condenses into ketone bodies instead of entering the TCA cycle",
    },
    (345, 1254): {
        # Thermodynamics, Gases & Phase Changes Participation Task, 2026-09-03.
        # Canvas Tasks 5 and 6; the session stopped after Task 4. 49 and 51 of
        # 86 blank, against 1-4 on Tasks 1-4.
        1764: "W = 0, so ΔU = Q",
        1765: "4.4 kJ",
    },
}


def _strip_html(value) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", str(value))).strip()


def has_exclusions(course_id: int, assignment_id: int) -> bool:
    return (int(course_id), int(assignment_id)) in EXCLUDED_QUESTIONS


def excluded_count(course_id: int, assignment_id: int) -> int:
    return len(EXCLUDED_QUESTIONS.get((int(course_id), int(assignment_id)), ()))


def _question_blocks(columns) -> list:
    """[(ItemID, ItemType, question text, EarnedPoints, Status)] column names."""
    cols = list(columns)
    return [tuple(cols[i:i + 5]) for i, c in enumerate(cols)
            if c == "ItemID" or str(c).startswith("ItemID.")]


def apply(course_id: int, assignment_id: int, csv_bytes: bytes) -> bytes:
    """Drop the excluded questions and restate the tallies. No-op when none."""
    answers = EXCLUDED_QUESTIONS.get((int(course_id), int(assignment_id)))
    if not answers or not csv_bytes:
        return csv_bytes

    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), low_memory=False)
    except Exception:
        return csv_bytes

    blocks = _question_blocks(df.columns)
    drop, drop_cols = [], []
    for block in blocks:
        ids = df[block[0]].dropna()
        if ids.empty:
            continue
        item_id = int(ids.iloc[0])
        if item_id in answers:
            drop.append((item_id, block))
            drop_cols.extend(block)

    # A report that does not carry the expected questions is left untouched
    # rather than half-adjusted — better a known-stale number than a wrong one.
    if len(drop) != len(answers):
        return csv_bytes

    correct = incorrect = noresp = None
    for item_id, block in drop:
        responses = df[block[2]]
        blank = responses.isna() | (responses.astype(str).str.strip() == "")
        right = (~blank) & (responses.map(_strip_html) == answers[item_id])
        wrong = (~blank) & (~right)
        correct = right.astype(int) if correct is None else correct + right.astype(int)
        incorrect = wrong.astype(int) if incorrect is None else incorrect + wrong.astype(int)
        noresp = blank.astype(int) if noresp is None else noresp + blank.astype(int)

    out = df.drop(columns=[c for c in drop_cols if c in df.columns])

    for column, adjustment in (("NumberOfCorrect", correct),
                               ("NumberOfIncorrect", incorrect),
                               ("NoResponse", noresp)):
        if column in out.columns:
            out[column] = (pd.to_numeric(out[column], errors="coerce").fillna(0)
                           - adjustment).clip(lower=0).astype(int)

    # Scored quizzes only: take back the points the dropped questions carried.
    # Left alone on 0-point activities, where both columns are already 0.
    if "OverallScore" in out.columns:
        earned = None
        for _, block in drop:
            got = pd.to_numeric(df[block[3]], errors="coerce").fillna(0)
            earned = got if earned is None else earned + got
        out["OverallScore"] = (pd.to_numeric(out["OverallScore"], errors="coerce").fillna(0)
                               - earned).clip(lower=0)
    if "PointsPossible" in out.columns:
        possible = pd.to_numeric(out["PointsPossible"], errors="coerce").fillna(0)
        # Only safe to reduce when the quiz was one point per question.
        if len(blocks) and (possible == len(blocks)).all():
            out["PointsPossible"] = len(blocks) - len(drop)

    buffer = io.StringIO()
    out.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
