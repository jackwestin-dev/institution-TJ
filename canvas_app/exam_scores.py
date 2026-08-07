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

from . import bundle as _bundle
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


MANUAL_FILE = "manual_scores.csv"


def manual_scores(exam_label: str) -> pd.DataFrame:
    """
    Scores typed in by hand, for students the export can't carry.

    Some students answer the score survey by uploading a screenshot of their
    score report instead of entering numbers. The CSV export then holds a PNG
    filename where the score should be, and nothing in it can be parsed. Reading
    those images is a human job; this is where the result goes.

    exam_data/manual_scores.csv, columns:
        student,exam,total,C/P,CARS,B/B,P/S
        Example Student,exam2,505,126,125,127,127

    Only `student`, `exam` and either `total` or all four sections are needed.
    The file is gitignored — it carries names.
    """
    from .config import EXAM_DATA_DIR

    path = EXAM_DATA_DIR / MANUAL_FILE
    empty = pd.DataFrame(columns=["key", "student", "total", *SECTIONS, "source_row"])
    if not path.exists():
        return empty
    try:
        raw = pd.read_csv(path)
    except Exception:
        return empty

    raw.columns = [str(c).strip() for c in raw.columns]
    name_col = next((c for c in raw.columns if c.lower() in ("student", "name")), None)
    exam_col = next((c for c in raw.columns if c.lower() == "exam"), None)
    if name_col is None or exam_col is None:
        return empty

    rows = []
    for idx, row in raw.iterrows():
        if str(row[exam_col]).strip().lower() != exam_label.lower():
            continue
        key = normalize_name(row[name_col])
        if not key:
            continue
        sections = {s: parse_section(row.get(s)) for s in SECTIONS}
        section_sum = (sum(sections[s] for s in SECTIONS)
                       if all(sections[s] is not None for s in SECTIONS) else None)
        total = parse_total(row.get("total")) or section_sum
        if total is None:
            continue
        rows.append({
            "key": key, "student": display_name(row[name_col]), "total": float(total),
            **sections, "source_row": f"manual:{idx}",
        })
    return pd.DataFrame(rows, columns=["key", "student", "total", *SECTIONS, "source_row"])


def with_manual(frame: pd.DataFrame, exam_label: str) -> pd.DataFrame:
    """Fold hand-entered scores into an extracted exam frame, manual winning."""
    manual = manual_scores(exam_label)
    if manual.empty:
        return frame
    keep = frame[~frame["key"].isin(set(manual["key"]))]
    return pd.concat([manual, keep], ignore_index=True)


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


# ── Data source: full local cache, or the committed de-identified bundle ──────
#
# A local checkout has reports_cache/ and shows real names. The deployed app has
# only data/, where students are S001, S002… Everything below reads through
# these three functions so neither the analysis nor the pages need to know which
# one they are looking at — the only visible difference is what a student is
# called.

def using_bundle(course_id: int) -> bool:
    """True when this course's numbers come from the committed bundle."""
    if _rc.cached_for_course(course_id):
        return False
    return _bundle.available()


def course_items(course_id: int) -> pd.DataFrame:
    return _bundle.items(course_id) if using_bundle(course_id) else cached_items(course_id)


def course_submitters(course_id: int, assignment_id: int) -> "list[str]":
    """Identifiers of everyone who submitted — names locally, IDs on the server."""
    if using_bundle(course_id):
        return _bundle.submitters(course_id, assignment_id)
    raw = _rc.get_cached_csv(course_id, assignment_id)
    return submitted_students(io.BytesIO(raw)) if raw else []


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
    items = course_items(course_id)
    items = items[items["item_type"].isin(item_types)]
    items = items[~items["assignment_id"].isin(exclude_ids)]

    submissions: "dict[str, dict]" = {}
    n_items = 0

    for _, item in items.iterrows():
        names = course_submitters(course_id, item["assignment_id"])
        if not names:
            continue
        n_items += 1

        pct_by_key = _pct_by_key(course_id, item["assignment_id"])

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


# ── Within-course learning: pre-class vs post-class on the same topic ────────
#
# Every session ships a Pre-Class Quiz taken before instruction and a
# Participation Task taken during/after it, both on the same topic. The
# difference between a student's two scores is the closest thing this course has
# to a measured learning gain, and it is what the Learning tab correlates
# against MCAT growth.
#
# Homework deliberately has no part in the pairing: almost every homework item
# is titled just "Homework", so there is no topic to match on. It is still
# reported as a plain average alongside the other item types.

# Stripped from a title to leave the bare topic. Longest variants first, so
# "Pre-Class Prep Work" is not half-consumed by the "Pre-Class" in a later
# pattern.
_TOPIC_MARKERS = [
    r"pre[-\s]?class\s+prep\s+work",
    r"pre[-\s]?class\s+check",
    r"pre[-\s]?class\s+quiz",
    r"participation\s+tasks?",
    r"pre[-\s]?quiz",
    r"homework",
    # Canvas suffixes a re-run with " -2"; the topic is the same.
    r"\s-\s*\d+\s*$",
]


def topic_of(title: str) -> str:
    """
    Reduce an assignment title to a topic key comparable across item types.

        "Chemical Equilibrium and Kinetics - Pre-Class Quiz"    ->
        "Chemical Equilibrium and Kinetics Participation Task"  ->
            both "chemical equilibrium and kinetics"

    Punctuation is dropped rather than normalised because the two titles for one
    topic rarely agree on it — "Electrostatics- Pre-Class Quiz" against
    "Electrostatics Participation Task", "Waves (Light + Sound)" against
    "Waves (Light + Sound)".
    """
    text = clean_cell(title).lower()
    for marker in _TOPIC_MARKERS:
        text = re.sub(marker, " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _pct_by_key(course_id: int, assignment_id: int) -> "dict[str, float]":
    """{student identifier: score %} for one assignment, best attempt kept."""
    if using_bundle(course_id):
        return _bundle.pct_by_key(course_id, assignment_id)
    raw = _rc.get_cached_csv(course_id, assignment_id)
    if not raw:
        return {}
    score_df, pts = parse_score_csv(io.BytesIO(raw))
    if score_df is None or not pts:
        return {}
    out: "dict[str, float]" = {}
    for _, row in score_df.iterrows():
        key = normalize_name(row["student"])
        if not key:
            continue
        pct = round(row["score"] / pts * 100, 1)
        # A retake shows up as a second row; keep the better one.
        if pct > out.get(key, -1):
            out[key] = pct
    return out


POST_TYPES = ["Homework", "Participation Task"]

# A z-score needs a cohort behind it. Below this many students on a topic the
# standard deviation is too unstable to divide by, so that topic contributes to
# the raw gain but not to the standing change.
MIN_TOPIC_STUDENTS = 8


def _mean_sd(values: "list[float]") -> "tuple[float, float]":
    """Population mean and standard deviation. sd is 0.0 for a constant list."""
    n = len(values)
    if not n:
        return 0.0, 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return mean, var ** 0.5


def paired_topics(
    course_id: int,
    *,
    post_type: str = "Homework",
    exclude_ids: "set | None" = None,
) -> pd.DataFrame:
    """
    Topics that have BOTH a cached pre-class quiz and a cached `post_type` item.

    Columns: topic, pre_id, post_id, pre_title, post_title. A topic with two
    pre-class items (an occasional re-run) keeps the earliest by due date, so
    the "before instruction" reading is the one used.

    post_type="Homework" is the meaningful pairing: homework is graded on
    correctness and spreads students out. Participation tasks are marked for
    completion, so nearly everyone scores ~100% and a "gain" against them mostly
    measures where the student started rather than what they learned.
    """
    exclude_ids = exclude_ids or set()
    items = course_items(course_id)
    items = items[~items["assignment_id"].isin(exclude_ids)]

    def first_by_topic(item_type: str) -> dict:
        subset = items[items["item_type"] == item_type].sort_values("due_at")
        picked: dict = {}
        for _, row in subset.iterrows():
            key = topic_of(row["title"])
            if key and key not in picked:
                picked[key] = row
        return picked

    pre = first_by_topic("Pre-Class Quiz")
    post = first_by_topic(post_type)

    rows = []
    for key in sorted(set(pre) & set(post)):
        rows.append({
            "topic":      key,
            "pre_id":     int(pre[key]["assignment_id"]),
            "post_id":    int(post[key]["assignment_id"]),
            "pre_title":  pre[key]["title"],
            "post_title": post[key]["title"],
        })
    return pd.DataFrame(rows, columns=["topic", "pre_id", "post_id", "pre_title", "post_title"])


def learning_tables(
    course_id: int,
    *,
    post_type: str = "Homework",
    exclude_ids: "set | None" = None,
) -> "tuple[pd.DataFrame, pd.DataFrame]":
    """
    Per-student and per-topic learning gain for a course.

    Returns (students, topics).

    students: key, Student, Topics Paired, Pre-Class Avg %, Post-Class Avg %,
              Learning Gain
        Averages cover only the topics where that student sat BOTH halves, so
        the gain is never the difference of two different topic sets.

    topics:   Topic, Students, Pre %, Post %, Gain, pre_title, post_title
        Cohort means per topic, over the students who sat both halves of it.
    """
    pairs = paired_topics(course_id, post_type=post_type, exclude_ids=exclude_ids)
    if pairs.empty:
        return (
            pd.DataFrame(columns=["key", "Student", "Topics Paired",
                                  "Pre-Class Avg %", "Post-Class Avg %", "Learning Gain"]),
            pd.DataFrame(columns=["Topic", "Students", "Pre %", "Post %", "Gain",
                                  "pre_title", "post_title"]),
        )

    display: "dict[str, str]" = {}
    per_student: "dict[str, dict]" = {}
    topic_rows = []
    dropped: "list[str]" = []

    for _, pair in pairs.iterrows():
        pre_pct = _pct_by_key(course_id, pair["pre_id"])
        post_pct = _pct_by_key(course_id, pair["post_id"])
        both = set(pre_pct) & set(post_pct)
        if not both:
            continue

        # An item every student scores identically on was never really graded —
        # course 345 has homework rows where Canvas reports 0 correct, 0
        # incorrect and 0 no-response for the whole cohort. Pairing against one
        # produces a fictitious -93 point "gain", so drop the topic and say so.
        if len({pre_pct[k] for k in both}) == 1 or len({post_pct[k] for k in both}) == 1:
            dropped.append(pair["post_title"])
            continue

        pre_mean, pre_sd = _mean_sd([pre_pct[k] for k in both])
        post_mean, post_sd = _mean_sd([post_pct[k] for k in both])

        for key in both:
            rec = per_student.setdefault(key, {"pre": [], "post": [], "z": []})
            rec["pre"].append(pre_pct[key])
            rec["post"].append(post_pct[key])
            # Standing change: where the student sat in the cohort on the
            # homework, minus where they sat on the pre-class quiz. Both sides
            # are z-scored within their own assignment, so a homework that was
            # simply harder shifts every student's post score by the same amount
            # and cancels. What is left is movement relative to peers on the
            # same material. Needs a real cohort to standardise against.
            if len(both) >= MIN_TOPIC_STUDENTS and pre_sd and post_sd:
                rec["z"].append(
                    (post_pct[key] - post_mean) / post_sd
                    - (pre_pct[key] - pre_mean) / pre_sd
                )

        topic_rows.append({
            "Topic":      pair["post_title"][:60],
            "Students":   len(both),
            "Pre %":      round(pre_mean, 1),
            "Post %":     round(post_mean, 1),
            "Gain":       round(post_mean - pre_mean, 1),
            "Difficulty": round(post_mean - pre_mean, 1),
            "pre_title":  pair["pre_title"],
            "post_title": pair["post_title"],
        })

    # Recover a readable label for each key. Locally that means the student's
    # name from a cached export; on the bundle the identifier is already the
    # label, so there is nothing to look up.
    if not using_bundle(course_id):
        for _, pair in pairs.iterrows():
            for aid in (pair["pre_id"], pair["post_id"]):
                raw = _rc.get_cached_csv(course_id, aid)
                if not raw:
                    continue
                for name in submitted_students(io.BytesIO(raw)):
                    key = normalize_name(name)
                    if key and key not in display:
                        display[key] = display_name(name)

    student_rows = []
    for key, rec in per_student.items():
        pre_avg = sum(rec["pre"]) / len(rec["pre"])
        post_avg = sum(rec["post"]) / len(rec["post"])
        student_rows.append({
            "key":               key,
            "Student":           display.get(key, key.title()),
            "Topics Paired":     len(rec["pre"]),
            "Pre-Class Avg %":   round(pre_avg, 1),
            "Post-Class Avg %":  round(post_avg, 1),
            "Learning Gain":     round(post_avg - pre_avg, 1),
            "Topics Standardised": len(rec["z"]),
            "Standing Change":   round(sum(rec["z"]) / len(rec["z"]), 3) if rec["z"] else None,
        })

    students = pd.DataFrame(student_rows, columns=[
        "key", "Student", "Topics Paired", "Pre-Class Avg %", "Post-Class Avg %",
        "Learning Gain", "Topics Standardised", "Standing Change",
    ])
    if len(students):
        students = students.sort_values("Learning Gain", ascending=False).reset_index(drop=True)

    topics = pd.DataFrame(topic_rows, columns=[
        "Topic", "Students", "Pre %", "Post %", "Gain", "pre_title", "post_title",
    ])
    if len(topics):
        topics = topics.sort_values("Gain", ascending=False).reset_index(drop=True)

    # Carried on the frame so the page can report what was excluded instead of
    # silently showing a smaller topic count than the cache suggests.
    topics.attrs["dropped_ungraded"] = dropped

    return students, topics


def type_averages(course_id: int, *, exclude_ids: "set | None" = None) -> pd.DataFrame:
    """
    Per-student mean score % within each item type.

    Columns: key, then "<type> Avg %" for every type that had cached, scoreable
    reports. Lets the Learning tab line up "how well they scored on homework"
    against "how much they gained", which the paired view alone can't show.
    """
    exclude_ids = exclude_ids or set()
    items = course_items(course_id)
    items = items[~items["assignment_id"].isin(exclude_ids)]

    collected: "dict[str, dict[str, list]]" = {}
    for _, item in items.iterrows():
        item_type = item["item_type"]
        for key, pct in _pct_by_key(course_id, item["assignment_id"]).items():
            collected.setdefault(key, {}).setdefault(item_type, []).append(pct)

    seen_types = sorted({t for rec in collected.values() for t in rec})
    rows = []
    for key, rec in collected.items():
        row = {"key": key}
        for item_type in seen_types:
            values = rec.get(item_type)
            row[f"{item_type} Avg %"] = round(sum(values) / len(values), 1) if values else None
        rows.append(row)

    return pd.DataFrame(rows, columns=["key"] + [f"{t} Avg %" for t in seen_types])


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


def partial_correlation(x: pd.Series, y: pd.Series, control: pd.Series) -> dict:
    """
    Correlation between x and y after linearly removing `control` from both.

    Needed because Exam 1 drives this cohort hard: students who scored low on
    Exam 1 have the most room to improve (regression to the mean) AND tend to
    score low on pre-class quizzes, which inflates their measured learning gain.
    A raw gain-vs-growth correlation therefore mostly restates the Exam 1 effect.
    Residualising both sides on Exam 1 leaves whatever the gain adds by itself.

    Returns {n, pearson}; pearson is None with fewer than four complete triples
    or a degenerate series.
    """
    import numpy as np

    trio = pd.DataFrame({"x": x, "y": y, "c": control}).dropna()
    out = {"n": len(trio), "pearson": None}
    if len(trio) < 4:
        return out

    xv, yv, cv = (trio[col].to_numpy(float) for col in ("x", "y", "c"))
    if cv.std() == 0 or xv.std() == 0 or yv.std() == 0:
        return out

    def residual(v):
        slope, intercept = np.polyfit(cv, v, 1)
        return v - (slope * cv + intercept)

    rx, ry = residual(xv), residual(yv)
    if rx.std() == 0 or ry.std() == 0:
        return out
    out["pearson"] = float(np.corrcoef(rx, ry)[0, 1])
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
