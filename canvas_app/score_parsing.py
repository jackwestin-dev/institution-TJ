"""
Canvas New Quizzes "Student Analysis" CSV parsing.

Shared by the Quiz Reports page and the Exam Growth page. Kept in its own
module so both can use it without importing a Streamlit page (which would
execute that page's script body).
"""
import pandas as pd


def _norm(columns) -> dict:
    """{column: comparison key} — lowercase, no spaces or underscores."""
    return {c: str(c).lower().replace(" ", "").replace("_", "") for c in columns}


def _pick(col_norm: dict, *names) -> "str | None":
    return next((c for c, n in col_norm.items() if n in names), None)


def latest_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """One row per student: the attempt Canvas keeps.

    A New Quiz that allows a retake exports one row per attempt, so a row count
    is not a submission count and a column mean is not a cohort mean. GI System,
    Plasma Membrane & Second Messengers (345_1278) is the case this was built
    for: the activity ran across two class sessions, 31 of its 89 students sat
    it twice, and the export's 120 rows read as 120 submissions against a roster
    of 122 — 98.4% participation on an activity 73.0% of the cohort did.

    Canvas keeps the last attempt, and keeping it here reproduces that quiz's own
    Quiz and Item Analysis report exactly: 449 correct of 534, 84.1%, where the
    raw 120 rows average 79.2%. Neither other candidate rule lands on Canvas's
    number (first attempt 410, highest-scoring 455), and the kept set matches the
    89 submissions the submissions API reports.

    Rows whose student cannot be identified are always kept — dropping a row for
    want of an ID would undercount a submission that did happen.
    """
    col_norm = _norm(df.columns)
    key = (_pick(col_norm, "id", "sisid")
           or _pick(col_norm, "student", "name", "studentname", "fullname"))
    if key is None or df[key].is_unique:
        return df

    ranked = df
    attempt = _pick(col_norm, "attempt")
    if attempt is not None:
        ranked = df.assign(
            _attempt=pd.to_numeric(df[attempt], errors="coerce").fillna(0)
        ).sort_values("_attempt", kind="stable")

    identified = ranked[ranked[key].notna()]
    kept = identified.groupby(key, sort=False).tail(1)
    return df.loc[df.index.isin(kept.index) | df[key].isna()]


def parse_score_csv(uploaded_file) -> "tuple[pd.DataFrame | None, float | None]":
    """
    Parse a Canvas New Quizzes Student Analysis CSV export.
    Returns (df with columns [student, score], points_possible) or (None, None).

    Canvas New Quizzes format:
      Name, ID, SectionIDs, SectionNames, Submitted, ElapsedTime, Attempt,
      [ItemID, ItemType, <question text>, EarnedPoints, Status] × N questions,
      NumberOfCorrect, NumberOfIncorrect, NoResponse, PointsPossible, OverallScore
    """
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]
        df = latest_attempts(df)

        # Normalised column names for matching (lowercase, no spaces/underscores)
        col_norm = {c: c.lower().replace(" ", "").replace("_", "") for c in df.columns}

        name_col = next(
            (c for c, n in col_norm.items() if n in ("student", "name", "studentname", "fullname")),
            None,
        )
        score_col = next(
            (c for c, n in col_norm.items() if n in (
                "score", "finalscore", "totalscore", "points", "grade",
                "overallscore",  # Canvas New Quizzes Student Analysis
            )),
            None,
        )
        # Prefer an EXACT normalised match for the canonical points column.
        # A loose "possible" substring match would wrongly grab a question column
        # whose text contains the word "possible" (e.g. "Name a possible topic…"),
        # which then parses to NaN and drops the whole quiz.
        pts_col = next(
            (c for c, n in col_norm.items() if n in (
                "pointspossible", "possiblepoints", "maxscore", "scoremax", "pointsmax",
            )),
            None,
        )
        if pts_col is None:
            pts_col = next(
                (c for c in df.columns if "possible" in c.lower()
                 or ("max" in c.lower() and "score" in c.lower())),
                None,
            )

        if name_col is None or score_col is None:
            return None, None

        result = df[[name_col, score_col]].copy()
        result.columns = ["student", "score"]
        result["score"] = pd.to_numeric(result["score"], errors="coerce").fillna(0)

        pts: "float | None" = None
        if pts_col:
            pts_series = pd.to_numeric(df[pts_col], errors="coerce").dropna()
            pts = float(pts_series.iloc[0]) if len(pts_series) else None
        elif "/" in score_col:
            try:
                pts = float(score_col.split("/")[-1].strip())
            except ValueError:
                pass

        # Fall back to the question-count basis when PointsPossible cannot be the
        # real denominator. Two ways that happens:
        #   * 0-point New Quizzes — PointsPossible and OverallScore both export
        #     as 0, but the real performance survives in the question-count
        #     columns.
        #   * PointsPossible set BELOW the question count. Assignment 1246 is a
        #     7-question activity configured as 1 point, so OverallScore is a
        #     0-1 ratio that Canvas rounds to 1.0 for anyone near-perfect: it
        #     reads as a completion rate (97.8%) rather than accuracy (87.3%).
        # PointsPossible ABOVE the question count is left alone — that is
        # ordinary per-question weighting.
        correct_col = next((c for c, n in col_norm.items() if n == "numberofcorrect"), None)
        incorrect_col = next((c for c, n in col_norm.items() if n == "numberofincorrect"), None)
        noresp_col = next((c for c, n in col_norm.items() if n == "noresponse"), None)
        derived_pts = 0.0
        correct = None
        if correct_col is not None:
            correct = pd.to_numeric(df[correct_col], errors="coerce").fillna(0)
            incorrect = (pd.to_numeric(df[incorrect_col], errors="coerce").fillna(0)
                         if incorrect_col else 0)
            noresp = (pd.to_numeric(df[noresp_col], errors="coerce").fillna(0)
                      if noresp_col else 0)
            total = (correct + incorrect + noresp)
            derived_pts = float(total.max()) if len(total) else 0.0

        if pts is None or pts == 0 or (derived_pts and pts < derived_pts):
            if correct is not None and derived_pts > 0:
                result["score"] = correct.values
                pts = derived_pts

        return result.dropna(subset=["student"]).reset_index(drop=True), pts
    except Exception:
        return None, None


def submitted_students(uploaded_file) -> "list[str]":
    """
    Return the list of student names that appear in a Student Analysis CSV.

    A student in the export submitted an attempt, so this is the completion
    roster for that assignment regardless of whether scores parse. One name per
    student, not one per attempt — see latest_attempts.
    """
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]
        df = latest_attempts(df)
        col_norm = {c: c.lower().replace(" ", "").replace("_", "") for c in df.columns}
        name_col = next(
            (c for c, n in col_norm.items() if n in ("student", "name", "studentname", "fullname")),
            None,
        )
        if name_col is None:
            return []
        names = df[name_col].dropna().astype(str).str.strip()
        return [n for n in names.tolist() if n and n.lower() != "nan"]
    except Exception:
        return []
