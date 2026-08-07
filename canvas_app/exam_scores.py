"""
MCAT exam-score ingestion and growth analysis for the JAMP EY26 cohort.

The exam data lives in Canvas New Quizzes "survey" forms that students fill in
themselves, so every score field is free text: "125", "<p>125</p>",
"39/59 (125)", "121 estimated score". Nothing here trusts a column to be
numeric — every value goes through `parse_total` / `parse_section`, which pull
the first plausible number out of the cell and reject anything outside the
valid MCAT range.

Two shapes of source file are supported and auto-detected:

  * a **total** column — e.g. "Total MCAT Score" or "What was your overall
    score based on the score converter?"
  * four **section scaled** columns — C/P, CARS, B/B, P/S — which are summed

Layout is otherwise irrelevant: any CSV with one row per student works,
including the raw Canvas Student Analysis exports (where question text becomes
the column header) and hand-cleaned sheets.
"""
import html as _html
import io
import re

import pandas as pd

from . import reports_cache as _rc
from .score_parsing import parse_score_csv, submitted_students

# ── MCAT scales ──────────────────────────────────────────────────────────────

TOTAL_MIN, TOTAL_MAX = 472, 528
SECTION_MIN, SECTION_MAX = 118, 132

# Band thresholds, high → low. Order matters: `band_of` returns the first match.
BANDS = [
    ("On Track (502+)",      502, TOTAL_MAX),
    ("Borderline (496–501)", 496, 501),
    ("Needs Support (≤495)", TOTAL_MIN, 495),
]
BAND_NAMES = [b[0] for b in BANDS]

SECTIONS = ["C/P", "CARS", "B/B", "P/S"]


def band_of(total: "float | None") -> "str | None":
    if total is None or pd.isna(total):
        return None
    for name, lo, hi in BANDS:
        if lo <= total <= hi:
            return name
    return None


# ── Cell cleaning / number extraction ────────────────────────────────────────

def clean_cell(value) -> str:
    """Strip HTML tags and entities from a student-entered cell."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = _html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _numbers(text: str) -> "list[float]":
    """All standalone numbers in the text, ignoring those inside x/y fractions."""
    # Drop "25/59" style fractions first — those are raw question counts, not
    # scaled scores, and their numerator can fall inside a valid range.
    text = re.sub(r"\d+\s*(?:/|\s+of\s+|\s+out\s+of\s+)\s*\d+", " ", text)
    return [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)]


def parse_total(value) -> "float | None":
    """Pull a valid MCAT total (472–528) out of a free-text cell."""
    for n in _numbers(clean_cell(value)):
        if TOTAL_MIN <= n <= TOTAL_MAX:
            return n
    return None


def parse_section(value) -> "float | None":
    """Pull a valid MCAT section scaled score (118–132) out of a free-text cell."""
    for n in _numbers(clean_cell(value)):
        if SECTION_MIN <= n <= SECTION_MAX:
            return n
    return None


# ── Name matching ────────────────────────────────────────────────────────────

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def normalize_name(name) -> str:
    """
    Canonical key for joining a student across files.

    Handles "Last, First" ordering, punctuation, casing, extra whitespace and
    name suffixes. Returns "" for anything unusable.
    """
    text = clean_cell(name)
    if not text or text.lower() == "nan":
        return ""
    if "," in text:
        last, _, first = text.partition(",")
        text = f"{first.strip()} {last.strip()}"
    text = re.sub(r"[^\w\s'-]", " ", text.lower())
    parts = [p for p in text.split() if p and p.strip(".") not in _SUFFIXES]
    return " ".join(parts)


def display_name(name) -> str:
    return clean_cell(name)


# ── Column auto-detection ────────────────────────────────────────────────────

def _norm_col(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", clean_cell(col).lower())


_NAME_PATTERNS = ("name", "student", "studentname", "namefirstandlast", "fullname")

_TOTAL_PATTERNS = (
    "totalmcatscore", "totalscore", "mcattotal", "total",
    "overallscore", "overallscorebasedonthescoreconverter",
)

# Columns Canvas appends to every New Quizzes export. In a 0-point survey they
# are all zero, so they must never be mistaken for a student-reported score —
# "OverallScore" in particular would otherwise beat the real question column
# ("What was your overall score based on the score converter?"). Only reserved
# when the file is a raw export; a hand-cleaned sheet may legitimately call its
# total column "Overall Score".
_CANVAS_META_COLS = {
    "overallscore", "pointspossible", "numberofcorrect", "numberofincorrect",
    "noresponse", "earnedpoints", "elapsedtime", "attempt", "submitted",
    "id", "sisid", "sectionids", "sectionnames", "sectionsisids", "status",
}


def is_raw_canvas_export(columns) -> bool:
    """True when the table still has the per-question ItemID/ItemType columns."""
    return any(_norm_col(c).startswith(("itemtype", "itemid")) for c in columns)


def _reserved_columns(columns) -> set:
    if not is_raw_canvas_export(columns):
        return set()
    return {
        c for c in columns
        if _norm_col(c).rstrip("0123456789") in _CANVAS_META_COLS
        or _norm_col(c) in _CANVAS_META_COLS
    }

# (section label, ordered list of regexes tried against the normalised header)
_SECTION_PATTERNS = {
    "C/P":  [r"^cpscaledscore$", r"chemphysscaledscore", r"^cp.*scaled", r"chemphys.*scaled"],
    "CARS": [r"^carsscaledscore$", r"cars.*scaled", r"^cars$"],
    "B/B":  [r"^bbscaledscore$", r"biobiochemscaledscore", r"^bb.*scaled", r"biobiochem.*scaled"],
    "P/S":  [r"^psscaledscore$", r"psychsocscaledscore", r"^ps.*scaled", r"psychsoc.*scaled"],
}


def detect_name_column(columns) -> "str | None":
    normed = {c: _norm_col(c) for c in columns}
    for pattern in _NAME_PATTERNS:
        for col, n in normed.items():
            if n == pattern:
                return col
    for col, n in normed.items():
        if "name" in n or "student" in n:
            return col
    return None


def detect_total_column(columns) -> "str | None":
    reserved = _reserved_columns(columns)
    normed = {c: _norm_col(c) for c in columns if c not in reserved}
    for pattern in _TOTAL_PATTERNS:
        for col, n in normed.items():
            if n == pattern:
                return col
    # Substring fallback, most specific first
    for needle in ("totalmcatscore", "totalscore", "overallscore", "scoreconverter"):
        for col, n in normed.items():
            if needle in n:
                return col
    return None


def detect_section_columns(columns) -> "dict[str, str]":
    normed = {c: _norm_col(c) for c in columns}
    found: "dict[str, str]" = {}
    for section, patterns in _SECTION_PATTERNS.items():
        for pattern in patterns:
            match = next((c for c, n in normed.items()
                          if re.search(pattern, n) and c not in found.values()), None)
            if match:
                found[section] = match
                break
    return found


def describe_source(df: pd.DataFrame) -> dict:
    """Auto-detected mapping for a freshly loaded table."""
    cols = list(df.columns)
    sections = detect_section_columns(cols)
    return {
        "name_col":     detect_name_column(cols),
        "total_col":    detect_total_column(cols),
        "section_cols": sections,
        "mode":         "total" if detect_total_column(cols) else
                        ("sections" if len(sections) == 4 else "none"),
    }


# ── Extraction ───────────────────────────────────────────────────────────────

def extract_scores(
    df: pd.DataFrame,
    name_col: str,
    total_col: "str | None" = None,
    section_cols: "dict[str, str] | None" = None,
    *,
    prefer: str = "total",
) -> pd.DataFrame:
    """
    Reduce a source table to one row per student.

    Returns columns: key, student, total, C/P, CARS, B/B, P/S, source_row.
    `total` is None when the row holds nothing usable — callers decide whether
    to report or drop those.

    prefer="total"    use the total column, fall back to summing sections
    prefer="sections" sum the sections, fall back to the total column
    """
    section_cols = section_cols or {}
    rows = []

    for idx, row in df.iterrows():
        key = normalize_name(row.get(name_col))
        if not key:
            continue

        sections = {s: parse_section(row.get(col)) for s, col in section_cols.items()}
        section_sum = (
            sum(sections[s] for s in SECTIONS)
            if all(sections.get(s) is not None for s in SECTIONS)
            else None
        )
        from_total = parse_total(row.get(total_col)) if total_col else None

        if prefer == "sections":
            total = section_sum if section_sum is not None else from_total
        else:
            total = from_total if from_total is not None else section_sum

        rows.append({
            "key":        key,
            "student":    display_name(row.get(name_col)),
            "total":      total,
            **{s: sections.get(s) for s in SECTIONS},
            "source_row": idx,
        })

    out = pd.DataFrame(rows, columns=["key", "student", "total", *SECTIONS, "source_row"])
    # A student who submitted twice appears twice; keep their best valid total.
    out = out.sort_values("total", ascending=False, na_position="last")
    return out.drop_duplicates(subset="key", keep="first").reset_index(drop=True)


def merge_sources(frames: "list[pd.DataFrame]") -> pd.DataFrame:
    """
    Combine several extracted frames for the same exam, earlier frames winning.

    Used when a cohort reported one exam through more than one form.
    """
    frames = [f for f in frames if f is not None and len(f)]
    if not frames:
        return pd.DataFrame(columns=["key", "student", "total", *SECTIONS, "source_row"])
    combined = pd.concat(frames, ignore_index=True)
    combined["_valid"] = combined["total"].notna()
    combined["_order"] = range(len(combined))
    combined = combined.sort_values(["_valid", "_order"], ascending=[False, True])
    combined = combined.drop_duplicates(subset="key", keep="first")
    return combined.drop(columns=["_valid", "_order"]).reset_index(drop=True)


def build_growth_table(exam1: pd.DataFrame, exam2: pd.DataFrame) -> pd.DataFrame:
    """
    Join the two exams on the normalised name key.

    Returns one row per student seen in either exam, with per-exam totals,
    section scores, bands, and the change between them. Students missing one
    exam are kept with NaN so the page can report coverage honestly.
    """
    e1 = exam1.set_index("key")
    e2 = exam2.set_index("key")
    keys = list(dict.fromkeys(list(e1.index) + list(e2.index)))

    rows = []
    for key in keys:
        r1 = e1.loc[key] if key in e1.index else None
        r2 = e2.loc[key] if key in e2.index else None
        t1 = r1["total"] if r1 is not None else None
        t2 = r2["total"] if r2 is not None else None
        t1 = None if t1 is None or pd.isna(t1) else float(t1)
        t2 = None if t2 is None or pd.isna(t2) else float(t2)

        row = {
            "key":       key,
            "Student":   (r2["student"] if r2 is not None and str(r2["student"]).strip()
                          else (r1["student"] if r1 is not None else key.title())),
            "Exam 1":    t1,
            "Exam 2":    t2,
            "Change":    (t2 - t1) if (t1 is not None and t2 is not None) else None,
            "Band 1":    band_of(t1),
            "Band 2":    band_of(t2),
        }
        for section in SECTIONS:
            v1 = r1[section] if r1 is not None else None
            v2 = r2[section] if r2 is not None else None
            row[f"{section} 1"] = None if v1 is None or pd.isna(v1) else float(v1)
            row[f"{section} 2"] = None if v2 is None or pd.isna(v2) else float(v2)
            row[f"{section} Δ"] = (
                row[f"{section} 2"] - row[f"{section} 1"]
                if row[f"{section} 1"] is not None and row[f"{section} 2"] is not None
                else None
            )
        rows.append(row)

    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values("Change", ascending=False, na_position="last").reset_index(drop=True)
    return out


def band_movement(row) -> str:
    """Human-readable band transition for one student."""
    b1, b2 = row.get("Band 1"), row.get("Band 2")
    # NaN is truthy, so test it explicitly — a missing band must not index into
    # BAND_NAMES.
    if b1 not in BAND_NAMES or b2 not in BAND_NAMES:
        return "—"
    if b1 == b2:
        return "Stayed"
    return "Moved up" if BAND_NAMES.index(b2) < BAND_NAMES.index(b1) else "Moved down"


# ── Participation, from the local Canvas report cache ────────────────────────

PARTICIPATION_TYPES = ["Participation Task", "Pre-Class Quiz", "Homework", "Survey", "Other"]


def classify_item(title: str) -> str:
    """Bucket a Canvas assignment title into a participation item type."""
    text = (title or "").lower()
    if "participation" in text:
        return "Participation Task"
    if re.search(r"pre[-\s]?class\s+(quiz|prep|check)|pre[-\s]?quiz|prep work", text):
        return "Pre-Class Quiz"
    if re.search(r"\bhomework\b|\bhw\b", text):
        return "Homework"
    if re.search(r"\bsurvey\b|submission form|score submission|date reporting", text):
        return "Survey"
    return "Other"


def cached_items(course_id: int) -> pd.DataFrame:
    """Every cached report for the course, with its participation item type."""
    rows = []
    for entry in _rc.cached_for_course(course_id):
        title = entry.get("title") or str(entry["assignment_id"])
        rows.append({
            "assignment_id": entry["assignment_id"],
            "title":         title,
            "item_type":     classify_item(title),
            "due_at":        entry.get("due_at") or "",
        })
    out = pd.DataFrame(rows, columns=["assignment_id", "title", "item_type", "due_at"])
    return out.sort_values(["due_at", "title"]).reset_index(drop=True)


def participation_table(
    course_id: int,
    item_types: "list[str]",
    *,
    exclude_ids: "set | None" = None,
) -> "tuple[pd.DataFrame, int]":
    """
    Per-student participation across the cached reports for a course.

    Returns (table, n_items). Table columns:
      key, Student, Items Completed, Items Available, Participation %, Avg Task Score %

    "Completed" means the student appears in that assignment's Student Analysis
    export, i.e. they submitted an attempt. "Avg Task Score %" averages the
    score percentages of the items they did submit, and is NaN for items whose
    points can't be resolved (0-point tasks with no question-count columns).
    """
    exclude_ids = exclude_ids or set()
    items = cached_items(course_id)
    items = items[items["item_type"].isin(item_types)]
    items = items[~items["assignment_id"].isin(exclude_ids)]

    submissions: "dict[str, dict]" = {}
    n_items = 0

    for _, item in items.iterrows():
        csv_bytes = _rc.get_cached_csv(course_id, item["assignment_id"])
        if not csv_bytes:
            continue
        names = submitted_students(io.BytesIO(csv_bytes))
        if not names:
            continue
        n_items += 1

        score_df, pts = parse_score_csv(io.BytesIO(csv_bytes))
        pct_by_key: "dict[str, float]" = {}
        if score_df is not None and pts:
            for _, srow in score_df.iterrows():
                k = normalize_name(srow["student"])
                if k:
                    pct_by_key[k] = round(srow["score"] / pts * 100, 1)

        for name in names:
            key = normalize_name(name)
            if not key:
                continue
            rec = submissions.setdefault(key, {"student": display_name(name), "n": 0, "pcts": []})
            rec["n"] += 1
            if key in pct_by_key:
                rec["pcts"].append(pct_by_key[key])

    rows = []
    for key, rec in submissions.items():
        rows.append({
            "key":               key,
            "Student":           rec["student"],
            "Items Completed":   rec["n"],
            "Items Available":   n_items,
            "Participation %":   round(rec["n"] / n_items * 100, 1) if n_items else None,
            "Avg Task Score %":  round(sum(rec["pcts"]) / len(rec["pcts"]), 1) if rec["pcts"] else None,
        })

    table = pd.DataFrame(rows, columns=[
        "key", "Student", "Items Completed", "Items Available",
        "Participation %", "Avg Task Score %",
    ])
    if len(table):
        table = table.sort_values("Participation %", ascending=False).reset_index(drop=True)
    return table, n_items


# ── Correlation helpers (numpy only — no scipy dependency) ───────────────────

def correlation(x: pd.Series, y: pd.Series) -> dict:
    """
    Pearson and Spearman correlation plus a least-squares fit.

    Returns {n, pearson, spearman, slope, intercept}; coefficients are None
    when there are fewer than three complete pairs or a series is constant.
    """
    import numpy as np

    pair = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(pair)
    out = {"n": n, "pearson": None, "spearman": None, "slope": None, "intercept": None}
    if n < 3:
        return out

    xv, yv = pair["x"].to_numpy(float), pair["y"].to_numpy(float)
    if xv.std() == 0 or yv.std() == 0:
        return out

    out["pearson"] = float(np.corrcoef(xv, yv)[0, 1])
    rx = pair["x"].rank().to_numpy(float)
    ry = pair["y"].rank().to_numpy(float)
    if rx.std() and ry.std():
        out["spearman"] = float(np.corrcoef(rx, ry)[0, 1])
    slope, intercept = np.polyfit(xv, yv, 1)
    out["slope"], out["intercept"] = float(slope), float(intercept)
    return out


def strength_label(r: "float | None") -> str:
    """Plain-language reading of a correlation coefficient."""
    if r is None:
        return "not enough data"
    a = abs(r)
    direction = "positive" if r > 0 else "negative"
    if a < 0.1:
        return "essentially no relationship"
    if a < 0.3:
        return f"weak {direction}"
    if a < 0.5:
        return f"moderate {direction}"
    if a < 0.7:
        return f"strong {direction}"
    return f"very strong {direction}"
