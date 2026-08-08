"""
Read the committed, de-identified data bundle in data/.

This is the deployed app's only data source. It exists so the dashboard opens
with real numbers and no credentials — no Canvas token, no Nova cookies, nothing
to type — because it gets presented to school administration.

The bundle is built by build_data_bundle.py from the local report cache, and
carries opaque student IDs (S001, S002…) rather than names. Everything the
pages need is derivable from four small tables:

    students.csv           student_id, cohort
    assignments.csv        course_id, assignment_id, title, item_type, topic, due_at
    assignment_scores.csv  student_id, course_id, assignment_id, score_pct
    exam_scores.csv        student_id, exam, total, C/P, CARS, B/B, P/S

A row in assignment_scores means the student submitted, so participation is
countable even where score_pct is blank (ungraded surveys and completion items).

canvas_app.exam_scores prefers the full local cache when it exists and falls
back here otherwise, so the same code paths serve both a local checkout with
real names and the anonymous deployed app.
"""
import pandas as pd

from .config import DATA_DIR

STUDENTS = DATA_DIR / "students.csv"
ASSIGNMENTS = DATA_DIR / "assignments.csv"
SCORES = DATA_DIR / "assignment_scores.csv"
EXAMS = DATA_DIR / "exam_scores.csv"

SECTIONS = ["C/P", "CARS", "B/B", "P/S"]


def available() -> bool:
    """True when enough of the bundle is present to drive the assignment views."""
    return ASSIGNMENTS.exists() and SCORES.exists()


def has_exams() -> bool:
    return EXAMS.exists()


def _read(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def items(course_id: int) -> pd.DataFrame:
    """Same shape as exam_scores.cached_items: assignment_id, title, item_type, due_at."""
    df = _read(ASSIGNMENTS)
    if df.empty:
        return pd.DataFrame(columns=["assignment_id", "title", "item_type", "due_at"])
    df = df[df["course_id"] == course_id].copy()
    df["due_at"] = df["due_at"].fillna("")
    cols = ["assignment_id", "title", "item_type", "due_at"]
    return df[cols].sort_values(["due_at", "title"]).reset_index(drop=True)


def _course_scores(course_id: int) -> pd.DataFrame:
    df = _read(SCORES)
    if df.empty:
        return df
    return df[df["course_id"] == course_id]


def submitters(course_id: int, assignment_id: int) -> "list[str]":
    """Student IDs with a submission for this assignment."""
    df = _course_scores(course_id)
    if df.empty:
        return []
    hit = df[df["assignment_id"] == assignment_id]
    return hit["student_id"].dropna().astype(str).tolist()


def pct_by_key(course_id: int, assignment_id: int) -> "dict[str, float]":
    """{student_id: score %} for one assignment, blanks dropped."""
    df = _course_scores(course_id)
    if df.empty:
        return {}
    hit = df[(df["assignment_id"] == assignment_id) & df["score_pct"].notna()]
    return {str(r.student_id): float(r.score_pct) for r in hit.itertuples()}


def exam_frames() -> "tuple[pd.DataFrame, pd.DataFrame]":
    """
    (exam1, exam2) shaped like exam_scores.extract_scores output, so
    build_growth_table consumes them unchanged.
    """
    empty = pd.DataFrame(columns=["key", "student", "total", *SECTIONS, "source_row"])
    df = _read(EXAMS)
    if df.empty:
        return empty.copy(), empty.copy()

    out = []
    for label in ("exam1", "exam2"):
        subset = df[df["exam"] == label].copy()
        if subset.empty:
            out.append(empty.copy())
            continue
        frame = pd.DataFrame({
            "key":        subset["student_id"].astype(str),
            "student":    subset["student_id"].astype(str),
            "total":      pd.to_numeric(subset["total"], errors="coerce"),
            **{s: pd.to_numeric(subset[s], errors="coerce") if s in subset else None
               for s in SECTIONS},
            "source_row": range(len(subset)),
        })
        out.append(frame.reset_index(drop=True))
    return out[0], out[1]


def cohorts() -> "dict[str, str]":
    df = _read(STUDENTS)
    if df.empty:
        return {}
    return {str(r.student_id): str(r.cohort) for r in df.itertuples()}


def summary() -> dict:
    """Counts for the 'where these numbers come from' note on each page."""
    assignments, scores, exams = _read(ASSIGNMENTS), _read(SCORES), _read(EXAMS)
    return {
        "assignments": len(assignments),
        "submissions": len(scores),
        "students":    scores["student_id"].nunique() if len(scores) else 0,
        "exam_rows":   len(exams),
        "courses":     sorted(assignments["course_id"].unique().tolist()) if len(assignments) else [],
    }
