"""
Canvas New Quizzes "Student Analysis" CSV parsing.

Shared by the Quiz Reports page and the Exam Growth page. Kept in its own
module so both can use it without importing a Streamlit page (which would
execute that page's script body).
"""
import pandas as pd


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

        # Fallback for 0-point New Quizzes: PointsPossible and OverallScore are
        # both 0 in the gradebook export, but the real performance survives in the
        # question-count columns. Derive score = #correct and pts = #questions so
        # downstream score/pts*100 yields a meaningful percentage.
        if pts is None or pts == 0:
            correct_col = next((c for c, n in col_norm.items() if n == "numberofcorrect"), None)
            incorrect_col = next((c for c, n in col_norm.items() if n == "numberofincorrect"), None)
            noresp_col = next((c for c, n in col_norm.items() if n == "noresponse"), None)
            if correct_col is not None:
                correct = pd.to_numeric(df[correct_col], errors="coerce").fillna(0)
                incorrect = (pd.to_numeric(df[incorrect_col], errors="coerce").fillna(0)
                             if incorrect_col else 0)
                noresp = (pd.to_numeric(df[noresp_col], errors="coerce").fillna(0)
                          if noresp_col else 0)
                total = (correct + incorrect + noresp)
                derived_pts = float(total.max()) if len(total) else 0.0
                if derived_pts > 0:
                    result["score"] = correct.values
                    pts = derived_pts

        return result.dropna(subset=["student"]).reset_index(drop=True), pts
    except Exception:
        return None, None


def submitted_students(uploaded_file) -> "list[str]":
    """
    Return the list of student names that appear in a Student Analysis CSV.

    A row in the export means the student submitted an attempt, so this is the
    completion roster for that assignment regardless of whether scores parse.
    """
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]
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
