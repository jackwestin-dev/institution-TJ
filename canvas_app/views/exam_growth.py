"""
Exam Growth — JAMP EY26 growth across the cohort's full-length practice exams.

Three questions this page answers:
  1. How much has each student grown since their baseline exam?
  2. Which score band is each student in (502+ / 496–501 / ≤495), and who moved?
  3. Does homework track with improvement?

The exams are listed in exam_scores.EXAMS. The headline comparison is the first
exam against the latest, because both are AAMC exams: the Jack Westin exam in
between is a different test maker's scale, so a drop from it to the AAMC exam is
partly a change of ruler rather than of the student. Any other pair can still be
picked.

Score files live in `exam_data/` at the repo root (drop the next exam's export
there) or can be uploaded ad hoc. That directory is gitignored — the exports
carry student names — so on the deployed app the only route in is the uploader
or the committed de-identified bundle. Participation comes from the local Canvas
report cache that sync_reports.py builds.
"""
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from .. import bundle
from .. import exam_scores as ex
from .. import jw_theme as jw
from ..config import EXAM_DATA_DIR as DATA_DIR

# Band → status color. Bands are always written out in text alongside the color,
# never encoded by color alone.
BAND_COLOR = {
    "On Track (502+)":      jw.SUCCESS,
    "Borderline (496–501)": jw.AMBER_500,
    "Needs Support (≤495)": jw.DANGER,
}
EXAM1_COLOR = jw.VIOLET_300
EXAM2_COLOR = jw.VIOLET_600

DEFAULT_PARTICIPATION_TYPES = ["Participation Task", "Pre-Class Quiz", "Homework"]

EXAMS_INDEX = {e["label"]: i for i, e in enumerate(ex.EXAMS)}

# Homework completion tiers for the Homework tab, as [lower, upper) bounds.
HOMEWORK_TIERS = [("Under 75%", 0, 75), ("75–89%", 75, 90), ("90% or more", 90, 101)]

NONE_OPTION = "— not loaded —"
UPLOAD_OPTION = "Upload a file…"


# ─── Loading ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(raw))


def _read_table(raw: bytes, filename: str) -> "pd.DataFrame | None":
    """Read an uploaded or on-disk table. CSV always; XLSX when openpyxl is installed."""
    if filename.lower().endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(raw))
        except ImportError:
            st.error(
                f"**{filename}** is an Excel file. Reading those needs one extra package — "
                "run `pip install openpyxl` and restart, or re-save the sheet as CSV."
            )
            return None
        except Exception as exc:
            st.error(f"Could not read **{filename}**: {exc}")
            return None
    try:
        return _read_csv_bytes(raw)
    except Exception as exc:
        st.error(f"Could not read **{filename}**: {exc}")
        return None


def _data_dir_files() -> "list[Path]":
    if not DATA_DIR.exists():
        return []
    return sorted(
        p for p in DATA_DIR.iterdir()
        if p.suffix.lower() in (".csv", ".xlsx", ".xls") and not p.name.startswith("~$")
    )


def _source_picker(label: str, key: str, prefix: str) -> "tuple[pd.DataFrame | None, str]":
    """
    Choose a score file for one exam: a file from exam_data/, an upload, or none.
    Defaults to the file whose name starts with `prefix`, or to none when there
    isn't one — so a missing exam is skipped rather than read from another
    exam's file. Returns (dataframe, human-readable source name).
    """
    files = _data_dir_files()
    options = [f.name for f in files] + [NONE_OPTION, UPLOAD_OPTION]
    default_index = next(
        (i for i, f in enumerate(files) if f.name.lower().startswith(prefix)),
        options.index(NONE_OPTION),
    )

    choice = st.selectbox(
        label,
        options=options,
        index=default_index,
        key=f"src_{key}",
        help="Files listed here come from `exam_data/`. Drop new exports in that folder.",
    )

    if choice == NONE_OPTION:
        return None, ""
    if choice == UPLOAD_OPTION:
        upload = st.file_uploader(
            f"{label} — upload CSV or XLSX", type=["csv", "xlsx", "xls"], key=f"up_{key}"
        )
        if upload is None:
            return None, ""
        return _read_table(upload.getvalue(), upload.name), upload.name

    path = DATA_DIR / choice
    return _read_table(path.read_bytes(), choice), choice


def _mapping_controls(df: pd.DataFrame, source_name: str, key: str) -> dict:
    """Auto-detected column mapping with manual override."""
    detected = ex.describe_source(df)
    columns = list(df.columns)
    none_label = "— none —"

    if detected["mode"] == "none":
        st.warning(
            f"Couldn't find a score column in **{source_name}**. "
            "Pick one below — either a single total column, or all four section "
            "scaled-score columns."
        )
    else:
        via = "total column" if detected["mode"] == "total" else "four section columns"
        st.caption(f"**{source_name}** — auto-detected via {via}. Adjust below if wrong.")

    with st.expander(f"Column mapping — {source_name}", expanded=detected["mode"] == "none"):
        name_col = st.selectbox(
            "Student name column",
            options=columns,
            index=columns.index(detected["name_col"]) if detected["name_col"] in columns else 0,
            key=f"name_{key}",
        )
        total_options = [none_label] + columns
        total_col = st.selectbox(
            "Total score column",
            options=total_options,
            index=(total_options.index(detected["total_col"])
                   if detected["total_col"] in columns else 0),
            key=f"total_{key}",
            help="A student-reported MCAT total (472–528). Free text is fine — "
                 "the first valid number in the cell is used.",
        )
        st.caption("Section scaled scores (118–132) — used when no total column, "
                   "and for the per-section breakdown.")
        section_cols = {}
        cols_ui = st.columns(4)
        for i, section in enumerate(ex.SECTIONS):
            detected_col = detected["section_cols"].get(section)
            picked = cols_ui[i].selectbox(
                section,
                options=total_options,
                index=total_options.index(detected_col) if detected_col in columns else 0,
                key=f"sec_{key}_{section}",
            )
            if picked != none_label:
                section_cols[section] = picked

    return {
        "name_col":     name_col,
        "total_col":    None if total_col == none_label else total_col,
        "section_cols": section_cols,
    }


def _unparsed_rows(df: pd.DataFrame, extracted: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Students whose score cell held nothing usable, with the raw text shown."""
    missing = extracted[extracted["total"].isna()]
    if missing.empty:
        return pd.DataFrame(columns=["Student", "What they entered"])
    cells = []
    for _, row in missing.iterrows():
        raw_idx = row["source_row"]
        pieces = []
        for col in filter(None, [mapping["total_col"], *mapping["section_cols"].values()]):
            try:
                text = ex.clean_cell(df.at[raw_idx, col])
            except Exception:
                text = ""
            if text:
                pieces.append(text)
        cells.append({
            "Student": row["student"],
            "What they entered": " · ".join(pieces)[:180] or "(blank)",
        })
    return pd.DataFrame(cells)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _pct(part: int, whole: int) -> str:
    return f"{part / whole * 100:.0f}%" if whole else "—"


# ─── Follow-up cohort ────────────────────────────────────────────────────────

def _render_followup(growth: pd.DataFrame, course_id: int, a: str, b: str) -> None:
    """
    Students the growth figures cannot speak for, and what that costs.

    Every band number on this page describes students who reported a score for
    both exams. Students who reported the first and then stopped are silently
    absent, and they are not a random sample: a student who stops reporting is
    more likely to be struggling than one who reports an improvement. Leaving
    them out of the count makes the cohort look better than the evidence
    supports, so they are counted here instead — as outreach, not as failure.
    """
    only_first = growth[growth["Exam 1"].notna() & growth["Exam 2"].isna()]
    paired = growth.dropna(subset=["Change"])
    if only_first.empty:
        return

    ns = "Needs Support (≤495)"
    ns_unknown = int((only_first["Band 1"] == ns).sum())
    ns_confirmed = int((paired["Band 2"] == ns).sum())

    # Students doing the coursework who never reported a usable score for either
    # exam. A form submitted with an unreadable score doesn't count as reported —
    # the published bundle has already dropped those rows, and this keeps the
    # local count the same as the deployed one.
    no_exam = 0
    reported = growth[growth["Exam 1"].notna() | growth["Exam 2"].notna()]
    try:
        part, _ = ex.participation_table(int(course_id), DEFAULT_PARTICIPATION_TYPES)
        if len(part):
            no_exam = len(set(part["key"]) - set(reported["key"]))
    except Exception:
        no_exam = 0

    st.divider()
    st.markdown("### Students needing outreach")
    st.markdown(
        f"""
The bands above describe the **{len(paired)} students who reported a score for both
{a} and {b}**. A further **{len(only_first)} reported {a} and have not reported
{b}**, so their current standing is unknown rather than good.

That matters for how the improvement is read. **{ns_unknown} of those {len(only_first)} were in
Needs Support on {a}.** They have not been shown to have improved; they have
simply stopped appearing in the data. Students who are struggling are less
likely to report a score than students who are pleased with one, so this group
should be treated as at-risk until contacted.
"""
    )

    cols = st.columns(3)
    cols[0].metric(
        "Confirmed still needing support", ns_confirmed,
        help=f"Scored 495 or below on {b}.",
    )
    cols[1].metric(
        f"Status unknown — no {b}", len(only_first),
        delta=f"{ns_unknown} were Needs Support on {a}",
        delta_color="off",
        help=f"Reported {a} and has not reported {b}.",
    )
    cols[2].metric(
        "No exam reported at all", no_exam,
        help="Active in the Canvas course but never reported a practice exam score "
             "for either of these two exams.",
    )

    st.warning(
        f"**Outreach list: {len(only_first) + no_exam} students.** "
        f"{len(only_first)} reported {a} but not {b} ({ns_unknown} of them below 496), "
        f"and {no_exam} taking part in the course have reported neither. "
        f"The first thing to establish is whether they sat the exam and did not "
        f"report it, or did not sit it — those need different responses.",
        icon="📣",
    )

    with st.expander(f"Where the {len(only_first)} unreported students stood on {a}"):
        rows = []
        for band in ex.BAND_NAMES:
            members = only_first[only_first["Band 1"] == band]
            if len(members):
                rows.append({
                    f"{a} band": band,
                    "Students": len(members),
                    f"Mean {a}": round(members["Exam 1"].mean(), 1),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        gap = only_first["Exam 1"].mean() - paired["Exam 1"].mean()
        st.caption(
            f"Their mean {a} score was {only_first['Exam 1'].mean():.1f}, against "
            f"{paired['Exam 1'].mean():.1f} for the students who reported both — so as a "
            f"group they started {'behind' if gap < 0 else 'level or ahead'}."
        )


# ─── Charts ──────────────────────────────────────────────────────────────────

def _dumbbell(paired: pd.DataFrame, title: str, a: str, b: str) -> go.Figure:
    """One row per student: start dot → end dot, connected, sorted by change."""
    data = paired.sort_values("Change").reset_index(drop=True)
    fig = go.Figure()

    # Connectors, drawn per direction so each gets one legend entry
    for label, color, mask in (
        ("Improved", jw.SUCCESS, data["Change"] > 0),
        ("No change", jw.GRAY_400, data["Change"] == 0),
        ("Declined", jw.DANGER, data["Change"] < 0),
    ):
        subset = data[mask]
        if subset.empty:
            continue
        xs, ys = [], []
        for _, row in subset.iterrows():
            xs += [row["Exam 1"], row["Exam 2"], None]
            ys += [row["Student"], row["Student"], None]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=label,
            line=dict(color=color, width=2),
            hoverinfo="skip",
        ))

    for name, color, col in (
        (a, EXAM1_COLOR, "Exam 1"),
        (b, EXAM2_COLOR, "Exam 2"),
    ):
        fig.add_trace(go.Scatter(
            x=data[col], y=data["Student"], mode="markers", name=name,
            marker=dict(size=9, color=color, line=dict(color=jw.WHITE, width=2)),
            customdata=data["Change"],
            hovertemplate="%{y}<br>" + name + ": %{x:.0f}<br>Change: %{customdata:+.0f}<extra></extra>",
        ))

    for _, lo, hi in ex.BANDS:
        fig.add_vline(x=lo - 0.5, line_dash="dot", line_color=jw.GRAY_200)

    fig.update_layout(**jw.plotly_layout(
        title=title,
        height=max(420, len(data) * 19 + 170),
        xaxis_title="MCAT total",
        yaxis_title=None,
        # Without an explicit category order Plotly orders rows by which trace
        # mentioned them first, which is not the sort the title promises.
        yaxis=dict(tickfont=dict(family="Figtree, sans-serif", size=10, color=jw.GRAY_500),
                   gridcolor=jw.GRAY_200, linecolor=jw.GRAY_200,
                   categoryorder="array", categoryarray=data["Student"].tolist()),
        legend=dict(orientation="h", yanchor="bottom", y=1.005, x=0),
        margin=dict(t=112, r=24, b=48, l=8),
    ))
    return fig


def _scatter_with_fit(
    data: pd.DataFrame, x: str, y: str, *, title: str, x_title: str, y_title: str,
    color_col: "str | None" = "Band 2", hline: "float | None" = None,
    y_fmt: str = "+.1f",
) -> go.Figure:
    """Scatter coloured by band, with a least-squares fit line."""
    fig = go.Figure()
    stats = ex.correlation(data[x], data[y])

    if color_col and color_col in data.columns:
        for band in ex.BAND_NAMES:
            subset = data[data[color_col] == band]
            if subset.empty:
                continue
            fig.add_trace(go.Scatter(
                x=subset[x], y=subset[y], mode="markers", name=band,
                marker=dict(size=10, color=BAND_COLOR[band],
                            line=dict(color=jw.WHITE, width=1.5)),
                text=subset["Student"],
                hovertemplate="%{text}<br>" + x_title + ": %{x:.1f}<br>"
                              + y_title + ": %{y:" + y_fmt + "}<extra>" + band + "</extra>",
            ))
        unbanded = data[~data[color_col].isin(ex.BAND_NAMES)]
        if not unbanded.empty:
            fig.add_trace(go.Scatter(
                x=unbanded[x], y=unbanded[y], mode="markers", name="No band",
                marker=dict(size=9, color=jw.GRAY_400, line=dict(color=jw.WHITE, width=1.5)),
                text=unbanded["Student"],
                hovertemplate="%{text}<extra>no band</extra>",
            ))
    else:
        fig.add_trace(go.Scatter(
            x=data[x], y=data[y], mode="markers", name=y_title,
            marker=dict(size=10, color=EXAM2_COLOR, line=dict(color=jw.WHITE, width=1.5)),
            text=data["Student"],
            hovertemplate="%{text}<br>%{x:.1f} → %{y:" + y_fmt + "}<extra></extra>",
        ))

    if stats["slope"] is not None:
        pair = data[[x, y]].dropna()
        xs = np.linspace(pair[x].min(), pair[x].max(), 50)
        fig.add_trace(go.Scatter(
            x=xs, y=stats["slope"] * xs + stats["intercept"],
            mode="lines", name="Best fit",
            line=dict(color=jw.VIOLET_900, width=2, dash="dash"),
            hoverinfo="skip",
        ))

    if hline is not None:
        fig.add_hline(y=hline, line_dash="dot", line_color=jw.GRAY_400)

    fig.update_layout(**jw.plotly_layout(
        title=title, xaxis_title=x_title, yaxis_title=y_title, height=460,
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0),
        margin=dict(t=56, r=24, b=96, l=72),
    ))
    return fig, stats


def _band_sankey(paired: pd.DataFrame, a: str, b: str) -> go.Figure:
    """Flows from each start band to each end band, same students on both sides."""
    bands = ex.BAND_NAMES
    n1 = {band: int((paired["Band 1"] == band).sum()) for band in bands}
    n2 = {band: int((paired["Band 2"] == band).sum()) for band in bands}
    labels = [f"{band} · {n1[band]}" for band in bands] + [f"{band} · {n2[band]}" for band in bands]
    colors = [BAND_COLOR[band] for band in bands] * 2

    src, dst, val, link_colors, hover = [], [], [], [], []
    for i, b1 in enumerate(bands):
        for j, b2 in enumerate(bands):
            n = int(((paired["Band 1"] == b1) & (paired["Band 2"] == b2)).sum())
            if not n:
                continue
            src.append(i)
            dst.append(len(bands) + j)
            val.append(n)
            # Flows coloured by where they end up, so "moved up into On Track"
            # reads green wherever it started.
            link_colors.append(_rgba(BAND_COLOR[b2], 0.35))
            move = "stayed" if i == j else ("moved up" if j < i else "moved down")
            hover.append(f"{n} student(s) {move}<br>{b1} → {b2}")

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        # Plotly haloes Sankey labels by default, which blurs them over the flows.
        textfont=dict(family="Figtree, sans-serif", size=13, color=jw.VIOLET_900,
                      shadow="none"),
        node=dict(
            label=labels, color=colors, pad=22, thickness=18,
            line=dict(color=jw.WHITE, width=2),
            x=[0.01] * 3 + [0.99] * 3,
            y=[0.1, 0.45, 0.85] * 2,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(source=src, target=dst, value=val, color=link_colors,
                  customdata=hover, hovertemplate="%{customdata}<extra></extra>"),
    ))
    fig.update_layout(**jw.plotly_layout(
        title=f"Band movement, {a} (left) → {b} (right) — {len(paired)} students",
        height=440, margin=dict(t=64, r=16, b=16, l=16),
    ))
    return fig


def render() -> None:
    # ─── Sidebar ─────────────────────────────────────────────────────────────────

    # Nothing here needs setting for the page to work — the defaults are the
    # EY26 cohort. Kept behind an expander so the sidebar is empty at a glance
    # when this is being presented.
    with st.sidebar:
        st.title("📈 Exam Growth")
        st.caption("MCAT growth across the full-length practice exams, JAMP EY26 cohort.")
        with st.expander("Advanced settings", expanded=False):
            course_id = st.number_input(
                "Course ID", value=345, min_value=1, step=1,
                help="345 = Jack Westin MCAT Preparation (EY26). Used for course "
                     "participation figures only; the exam scores are independent of it.",
            )
            participation_types = st.multiselect(
                "Course items that count toward participation",
                options=ex.PARTICIPATION_TYPES,
                default=DEFAULT_PARTICIPATION_TYPES,
                help="Participation = the share of these items a student submitted. "
                     "The Homework tab always uses homework alone.",
            )

    st.markdown(jw.brand_header("Exam Growth — JAMP EY26"), unsafe_allow_html=True)

    # ─── Sources ─────────────────────────────────────────────────────────────────
    #
    # Default path needs no input at all: the committed bundle already holds the
    # exams. The file pickers only appear when someone opens the loading section,
    # so this page can be projected in front of administration as-is.

    local_files = _data_dir_files()
    scores: "dict[str, pd.DataFrame]" = {}
    raw: "dict[str, pd.DataFrame]" = {}
    maps: "dict[str, dict]" = {}
    names: "dict[str, str]" = {}
    other_exam: "dict[str, pd.Series]" = {}

    if local_files:
        with st.expander("📂 Score sources", expanded=False):
            st.caption(
                "Reading MCAT exports from `exam_data/`. Adjust the file or column "
                "mapping here if a new export is shaped differently."
            )
            for col, exam in zip(st.columns(len(ex.EXAMS)), ex.EXAMS):
                label = exam["label"]
                with col:
                    st.markdown(f"##### {exam['short']}")
                    st.caption(f"{exam['name']} · {exam['taken']}")
                    df, source_name = _source_picker("File", label, label)
                    if df is None:
                        continue
                    df, dropped = ex.filter_exam_rows(df, exam.get("which_exam"))
                    if len(dropped):
                        st.caption(
                            f"Kept rows reporting {exam['name']}; set aside "
                            f"{int(dropped.sum())} reporting a different exam."
                        )
                    mapping = _mapping_controls(df, source_name, label)
                    raw[label], maps[label], names[label] = df, mapping, source_name
                    other_exam[label] = dropped

        for label, df in raw.items():
            mapping = maps[label]
            extracted = ex.extract_scores(
                df, mapping["name_col"], mapping["total_col"], mapping["section_cols"])
            # Students who answered the survey with a screenshot instead of
            # numbers are unreadable from the export; their scores are typed
            # into exam_data/manual_scores.csv and folded in here.
            scores[label] = ex.with_manual(extracted, label)

    elif bundle.has_exams():
        scores = bundle.exam_frames([e["label"] for e in ex.EXAMS])
        names = {e["label"]: f"published data ({e['short']})" for e in ex.EXAMS}

    else:
        st.info(
            "No exam scores are available. On a local checkout, drop the MCAT "
            "exports into `exam_data/`; on the server, run `build_data_bundle.py` "
            "and commit `data/`."
        )
        st.stop()

    available = [e for e in ex.EXAMS
                 if e["label"] in scores and scores[e["label"]]["total"].notna().any()]
    for exam in ex.EXAMS:
        if exam["label"] in raw and exam not in available:
            st.warning(
                f"No valid MCAT totals (472–528) could be read for **{exam['short']}**. "
                "Check its column mapping in **Score sources**."
            )
    if len(available) < 2:
        st.info("Growth needs scores for at least two exams — choose files in "
                "**Score sources** above.")
        st.stop()

    # ─── Which two exams to compare ──────────────────────────────────────────────
    #
    # Defaults to the first exam against the latest: growth over the whole course
    # so far, rather than whichever exam happened to come just before.

    pairs = [(s, e) for i, s in enumerate(available) for e in available[i + 1:]]
    default_pair = (available[0], available[-1])
    pair_index = st.radio(
        "Compare",
        options=range(len(pairs)),
        index=pairs.index(default_pair),
        format_func=lambda i: (f"{pairs[i][0]['short']} → {pairs[i][1]['short']}"
                               + ("  (overall growth)" if pairs[i] == default_pair else "")),
        horizontal=True,
        help="Overall growth compares the first exam with the latest. The other "
             "pairs show each step along the way.",
    )
    start, end = pairs[pair_index]
    A, B = start["short"], end["short"]

    growth = ex.build_growth_table(scores[start["label"]], scores[end["label"]])
    growth["Movement"] = growth.apply(ex.band_movement, axis=1)

    participation, n_items = ex.participation_table(int(course_id), participation_types)
    if len(participation):
        growth = growth.merge(
            participation.drop(columns=["Student", "Items Available"]), on="key", how="left"
        )
    else:
        for col in ("Items Completed", "Participation %", "Avg Task Score %"):
            growth[col] = np.nan

    # Homework alone, counted only up to the end exam, so work set after it
    # isn't credited to growth it can't have caused.
    # Never-graded homework is left out, as the published bundle leaves it out.
    homework, n_homework = ex.participation_table(
        int(course_id), ["Homework"], due_before=end["homework_cutoff"],
        exclude_ids=ex.never_graded(int(course_id), "Homework"))
    homework = homework.rename(columns={
        "Items Completed":  "Homework Done",
        "Participation %":  "Homework %",
        "Avg Task Score %": "Homework Accuracy %",
    })
    if len(homework):
        growth = growth.merge(
            homework[["key", "Homework Done", "Homework %", "Homework Accuracy %"]],
            on="key", how="left",
        )
    else:
        for col in ("Homework Done", "Homework %", "Homework Accuracy %"):
            growth[col] = np.nan

    # Within-course learning: pre-class quiz vs participation task on the same
    # topic. Merged so the downloadable growth table carries it.
    learning, topic_gains = ex.learning_tables(int(course_id))
    if len(learning):
        growth = growth.merge(learning.drop(columns=["Student"]), on="key", how="left")
    else:
        for col in ("Topics Paired", "Pre-Class Avg %", "Post-Class Avg %", "Learning Gain"):
            growth[col] = np.nan

    type_avgs = ex.type_averages(int(course_id))
    if len(type_avgs):
        growth = growth.merge(type_avgs, on="key", how="left")

    paired = growth.dropna(subset=["Change"]).copy()

    if paired.empty:
        st.error(
            f"No student appears in both {A} and {B} with a readable score, so growth "
            "can't be computed. Check that the name columns hold comparable names."
        )
        st.stop()

    # Every exam side by side, for the trajectory views.
    totals = pd.DataFrame({
        e["short"]: scores[e["label"]].dropna(subset=["total"]).set_index("key")["total"]
        for e in available
    })
    all_sat = totals.dropna()

    # Internal column names stay "Exam 1"/"Exam 2"; tables show the exam names.
    display_names = {"Exam 1": A, "Exam 2": B, "Band 1": f"{A} band", "Band 2": f"{B} band"}

    def shown(df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=display_names)

    tab_growth, tab_bands, tab_homework, tab_student, tab_data = st.tabs(
        ["📈 Growth", "🎯 Score Bands", "📚 Homework vs Growth", "👤 Student", "🧾 Data & Methods"]
    )

    # ── Tab: Growth ──────────────────────────────────────────────────────────────

    with tab_growth:
        st.subheader(f"Growth from {A} to {B}")
        st.markdown(
            f"""
Students in this cohort have sat {len(available)} full-length practice MCATs and
reported their scores through Canvas surveys. This tab compares
**{A}** ({start['name']}, {start['taken']}) with **{B}** ({end['name']}, {end['taken']}).

**What the numbers mean.** The MCAT is scored **472–528**, with 500 as the
midpoint. Each of the four sections is scored 118–132 and the four add up to the
total. A change of a few points is normal test-to-test variation; a change of
ten or more is a real shift.

**Who is counted.** Only the **{len(paired)} students who have a usable score for
both exams**. Someone who sat one and not the other can't show growth, so
including them would distort every figure on this tab. Coverage for everyone
else is in **Data & Methods**.
"""
        )

        m = st.columns(5)
        m[0].metric("Students with both", len(paired))
        m[1].metric(f"Mean {A}", f"{paired['Exam 1'].mean():.1f}")
        m[2].metric(f"Mean {B}", f"{paired['Exam 2'].mean():.1f}")
        m[3].metric("Mean change", f"{paired['Change'].mean():+.1f}",
                    delta=f"{paired['Change'].mean():+.1f} pts")
        m[4].metric("Improved", f"{(paired['Change'] > 0).mean() * 100:.0f}%",
                    help=f"{int((paired['Change'] > 0).sum())} of {len(paired)} students scored higher")

        up, flat, down = (int((paired["Change"] > 0).sum()),
                          int((paired["Change"] == 0).sum()),
                          int((paired["Change"] < 0).sum()))
        st.markdown(
            f"**{up}** improved · **{flat}** unchanged · **{down}** declined · "
            f"median change **{paired['Change'].median():+.0f}** · "
            f"range **{paired['Change'].min():+.0f}** to **{paired['Change'].max():+.0f}**"
        )

        # ── Every exam, for context ───────────────────────────────────────────
        if len(available) > 2 and len(all_sat) >= 3:
            st.divider()
            st.markdown("### Across every exam")
            means = all_sat.mean()
            fig_traj = go.Figure(go.Scatter(
                x=[f"{e['short']}<br><sub>{e['maker']} · {e['taken']}</sub>" for e in available],
                y=means.values,
                mode="lines+markers+text",
                line=dict(color=jw.VIOLET_600, width=2),
                marker=dict(size=10, color=jw.VIOLET_600, line=dict(color=jw.WHITE, width=2)),
                text=[f"{v:.1f}" for v in means.values],
                textposition="top center",
                textfont=dict(color=jw.VIOLET_900),
                hovertemplate="%{x}<br>Mean %{y:.1f}<extra></extra>",
            ))
            fig_traj.update_layout(**jw.plotly_layout(
                title=f"Mean total score at each exam — the {len(all_sat)} students who sat all {len(available)}",
                height=360, yaxis_title="Mean MCAT total", showlegend=False,
                yaxis=dict(range=[means.min() - 4, means.max() + 4]),
            ))
            st.plotly_chart(fig_traj, use_container_width=True)

            # The point of this section: say plainly why the latest exam can read
            # lower than the one before it without the cohort having gone
            # backwards.
            makers = [e["maker"] for e in available]
            if start["maker"] == end["maker"] and len(set(makers)) > 1:
                middle = [e for e in available
                          if e["maker"] != end["maker"] and EXAMS_INDEX[e["label"]] < EXAMS_INDEX[end["label"]]]
                if middle:
                    mid = middle[-1]
                    both = totals[[mid["short"], B]].dropna()
                    step = (both[B] - both[mid["short"]]).mean()
                    st.info(
                        f"**Why {A} → {B} is the headline.** {A} and {B} are both "
                        f"{end['maker']} exams, so comparing them is like for like. "
                        f"{mid['short']} is a {mid['maker']} exam, and different test "
                        f"makers' exams are not on an identical scale. The "
                        f"{len(both)} students who sat both {mid['short']} and {B} "
                        f"averaged **{step:+.1f}** points on {B} against {mid['short']}; "
                        f"read that as partly a change of ruler. Measured on the same "
                        f"maker's exams, the cohort moved **{paired['Change'].mean():+.1f}** "
                        f"points from {A} to {B}."
                        if pairs[pair_index] == default_pair else
                        f"{A} and {B} are both {end['maker']} exams; {mid['short']} "
                        f"in between is a {mid['maker']} exam, which isn't on an "
                        "identical scale.",
                        icon="📏",
                    )
            elif start["maker"] != end["maker"]:
                st.warning(
                    f"{A} is a {start['maker']} exam and {B} is a {end['maker']} exam. "
                    "Different test makers' exams are not on an identical scale, so part "
                    f"of this change reflects the switch of exam rather than the students. "
                    f"Pick **{available[0]['short']} → {available[-1]['short']}** for the "
                    "overall comparison.",
                    icon="📏",
                )

        st.divider()
        view_col, n_col = st.columns([2, 1])
        view = view_col.radio(
            "Students to chart",
            options=["All", "Biggest gains", "Biggest drops"],
            horizontal=True,
        )
        if view == "All":
            charted, chart_title = paired, f"{A} → {B}, all {len(paired)} students (sorted by change)"
        else:
            top_n = n_col.slider("How many", 5, max(5, len(paired)), min(20, len(paired)), 5)
            ascending = view == "Biggest drops"
            charted = paired.sort_values("Change", ascending=ascending).head(top_n)
            chart_title = f"{A} → {B} — {view.lower()} ({len(charted)} students)"

        st.plotly_chart(_dumbbell(charted, chart_title, A, B), use_container_width=True)

        st.divider()
        left, right = st.columns(2)

        with left:
            fig_hist = px.histogram(
                paired, x="Change", nbins=24,
                title="Distribution of score change",
                labels={"Change": "Change in MCAT total (points)"},
                color_discrete_sequence=[jw.VIOLET_600],
            )
            fig_hist.add_vline(x=0, line_dash="dash", line_color=jw.GRAY_400,
                               annotation_text="no change", annotation_font_color=jw.GRAY_500)
            fig_hist.update_layout(**jw.plotly_layout(height=380, yaxis_title="Students"))
            st.plotly_chart(fig_hist, use_container_width=True)

        with right:
            fig_pair, _ = _scatter_with_fit(
                paired, "Exam 1", "Exam 2",
                title=f"{A} vs {B} (dotted = no change)",
                x_title=f"{A} total", y_title=f"{B} total", y_fmt=".0f",
            )
            lo = float(min(paired["Exam 1"].min(), paired["Exam 2"].min())) - 3
            hi = float(max(paired["Exam 1"].max(), paired["Exam 2"].max())) + 3
            fig_pair.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi,
                               line=dict(color=jw.GRAY_400, width=2, dash="dot"))
            fig_pair.update_layout(height=380, xaxis_range=[lo, hi], yaxis_range=[lo, hi])
            st.plotly_chart(fig_pair, use_container_width=True)

        # Section detail — only meaningful where both exams carry scaled sections
        delta_cols = [f"{s} Δ" for s in ex.SECTIONS]
        have_deltas = [c for c in delta_cols if paired[c].notna().any()]
        exam2_cols = [f"{s} 2" for s in ex.SECTIONS if paired[f"{s} 2"].notna().any()]

        st.divider()
        if have_deltas:
            section_means = pd.DataFrame({
                "Section": [c.replace(" Δ", "") for c in have_deltas],
                "Mean change": [round(paired[c].mean(), 2) for c in have_deltas],
                "Students": [int(paired[c].notna().sum()) for c in have_deltas],
            })
            fig_sec = px.bar(
                section_means, x="Section", y="Mean change", text="Mean change",
                title=f"Mean section change, {A} → {B} (scaled points)",
                hover_data=["Students"],
                color_discrete_sequence=[jw.VIOLET_600],
            )
            fig_sec.update_traces(texttemplate="%{text:+.2f}", textposition="outside")
            fig_sec.add_hline(y=0, line_color=jw.GRAY_400)
            fig_sec.update_layout(**jw.plotly_layout(height=360))
            st.plotly_chart(fig_sec, use_container_width=True)
        elif exam2_cols:
            section_means = pd.DataFrame({
                "Section": [c.replace(" 2", "") for c in exam2_cols],
                "Mean scaled score": [round(paired[c].mean(), 2) for c in exam2_cols],
            })
            fig_sec = px.bar(
                section_means, x="Section", y="Mean scaled score", text="Mean scaled score",
                title=f"{B} mean section scaled score",
                color_discrete_sequence=[EXAM2_COLOR],
            )
            fig_sec.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_sec.update_layout(**jw.plotly_layout(height=360, yaxis_range=[117, 133]))
            st.plotly_chart(fig_sec, use_container_width=True)
            st.caption(
                f"Section *change* needs scaled section scores for both exams. The {A} "
                "form collected raw question counts rather than scaled sections, so only "
                f"{B} sections are shown."
            )

    # ── Tab: Score Bands ─────────────────────────────────────────────────────────

    with tab_bands:
        st.subheader("Score bands")
        st.markdown(
            f"""
Students are grouped into three bands by total score, so movement between them
shows how the cohort's readiness shifted rather than just its average.

| Band | Score | Meaning |
|---|---|---|
| **On Track** | 502 and above | At or above the median MCAT score |
| **Borderline** | 496 – 501 | Close, but below the median |
| **Needs Support** | 495 and below | Well below the median |

A student "moved up" if their band on {B} is higher than on {A}.
"""
        )

        n_e1 = int(growth["Exam 1"].notna().sum())
        n_e2 = int(growth["Exam 2"].notna().sum())

        cohort = st.radio(
            "Cohort",
            options=["paired", "all"],
            format_func=lambda v: (f"Students with both exams ({len(paired)}) — like-for-like"
                                   if v == "paired"
                                   else f"Everyone with a score ({n_e1} {A} / {n_e2} {B})"),
            horizontal=True,
            help=f"{A} and {B} were taken by different numbers of students, so "
                 "comparing all of each would mix real movement with who sat the exam. "
                 "The like-for-like view fixes the cohort to the students in both.",
        )
        band_source = paired if cohort == "paired" else growth

        band_df = pd.DataFrame([
            {
                "Band": band,
                A:      int((band_source["Band 1"] == band).sum()),
                B:      int((band_source["Band 2"] == band).sum()),
            }
            for band in ex.BAND_NAMES
        ])

        tiles = st.columns(3)
        for i, band in enumerate(ex.BAND_NAMES):
            n1 = int(band_df.loc[i, A])
            n2 = int(band_df.loc[i, B])
            tiles[i].metric(
                band, n2,
                delta=f"{n2 - n1:+d} vs {A}" if cohort == "paired" else None,
                # More students in Needs Support is the bad direction.
                delta_color="inverse" if band == "Needs Support (≤495)" else "normal",
                help=(f"{n1} were in this band on {A}" if cohort == "paired" else
                      "Different students sat each exam, so no change figure is shown "
                      "here — switch to the like-for-like cohort for that."),
            )

        # The improvement is stated right here, so the group it excludes has to be
        # stated here too rather than only further down the page.
        _only_first = int((growth["Exam 1"].notna() & growth["Exam 2"].isna()).sum())
        if cohort == "paired" and _only_first:
            _ns_unknown = int(
                (growth["Band 1"] == "Needs Support (≤495)")
                [growth["Exam 2"].isna()].sum()
            )
            st.info(
                f"These counts cover the {len(paired)} students who reported both exams. "
                f"A further **{_only_first} reported {A} and not {B}**, "
                f"**{_ns_unknown}** of them from Needs Support — their standing is unknown, "
                f"not improved. See **Students needing outreach** below.",
                icon="ℹ️",
            )

        long = band_df.melt(id_vars="Band", var_name="Exam", value_name="Students")
        fig_band = px.bar(
            long, x="Band", y="Students", color="Exam", barmode="group", text="Students",
            title=(f"Students per band, {A} vs {B} — same students in both"
                   if cohort == "paired" else
                   "Students per band — everyone with a score for that exam"),
            color_discrete_map={A: EXAM1_COLOR, B: EXAM2_COLOR},
            category_orders={"Band": ex.BAND_NAMES},
        )
        fig_band.update_traces(textposition="outside")
        fig_band.update_layout(**jw.plotly_layout(
            height=440, xaxis_title=None,
            legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
            margin=dict(t=56, r=24, b=80, l=48),
        ))
        st.plotly_chart(fig_band, use_container_width=True)
        if cohort == "paired":
            st.caption(
                f"Both columns describe the same {len(paired)} students, so the "
                "differences are real movement between bands."
            )
        else:
            st.caption(
                f"{A} covers {n_e1} students and {B} covers {n_e2}, and they are "
                f"not the same group — a drop in a band here can just mean those students "
                f"didn't sit {B}. Use the like-for-like cohort to read movement."
            )

        st.divider()
        st.markdown("### Band movement")

        moves = paired[paired["Movement"] != "—"]
        n_up = int((moves["Movement"] == "Moved up").sum())
        n_stay = int((moves["Movement"] == "Stayed").sum())
        n_down = int((moves["Movement"] == "Moved down").sum())
        mv = st.columns(3)
        mv[0].metric("Moved up", n_up, help=_pct(n_up, len(moves)) + " of students")
        mv[1].metric("Stayed", n_stay, help=_pct(n_stay, len(moves)) + " of students")
        mv[2].metric("Moved down", n_down, help=_pct(n_down, len(moves)) + " of students")

        # Movement out of the bottom band is the question the program is judged on,
        # so it gets its own sentence rather than being left to the chart.
        ns, bl, ot = ex.BAND_NAMES[2], ex.BAND_NAMES[1], ex.BAND_NAMES[0]
        from_ns = paired[paired["Band 1"] == ns]
        from_bl = paired[paired["Band 1"] == bl]
        if len(from_ns) or len(from_bl):
            lines = []
            if len(from_ns):
                left_ns = int((from_ns["Band 2"] != ns).sum())
                lines.append(
                    f"- Of the **{len(from_ns)}** who started below 496, **{left_ns}** "
                    f"({_pct(left_ns, len(from_ns))}) have moved out of Needs Support — "
                    f"{int((from_ns['Band 2'] == bl).sum())} to Borderline and "
                    f"{int((from_ns['Band 2'] == ot).sum())} straight to 502+."
                )
            if len(from_bl):
                bl_up = int((from_bl["Band 2"] == ot).sum())
                bl_down = int((from_bl["Band 2"] == ns).sum())
                lines.append(
                    f"- Of the **{len(from_bl)}** who started at 496–501, **{bl_up}** reached "
                    f"502+ and {bl_down} slipped below 496."
                )
            on_track = int((paired["Band 2"] == ot).sum())
            started_on_track = int((paired["Band 1"] == ot).sum())
            lines.append(
                f"- **{on_track}** of {len(paired)} ({_pct(on_track, len(paired))}) are at "
                f"502+ on {B}, against {started_on_track} ({_pct(started_on_track, len(paired))}) on {A}."
            )
            st.markdown("\n".join(lines))

        st.plotly_chart(_band_sankey(paired, A, B), use_container_width=True)
        st.caption(
            "Each band on the left splits into where those students landed on the right. "
            "Flows are coloured by the band they end in."
        )

        with st.expander("Same movement as a table"):
            matrix = pd.DataFrame(
                [[int(((paired["Band 1"] == b1) & (paired["Band 2"] == b2)).sum())
                  for b2 in ex.BAND_NAMES] for b1 in ex.BAND_NAMES],
                index=[f"{A}: {b}" for b in ex.BAND_NAMES],
                columns=[f"{B}: {b}" for b in ex.BAND_NAMES],
            )
            st.dataframe(matrix, use_container_width=True)

        # ── Band share at every exam ───────────────────────────────────────────
        if len(available) > 2 and len(all_sat) >= 3:
            st.divider()
            st.markdown("### Bands at every exam")
            share_rows = []
            for exam in available:
                col = all_sat[exam["short"]]
                for band in ex.BAND_NAMES:
                    n = int((col.map(ex.band_of) == band).sum())
                    share_rows.append({
                        "Exam": f"{exam['short']} ({exam['maker']})", "Band": band,
                        "Students": n, "Share": n / len(all_sat) * 100,
                    })
            share = pd.DataFrame(share_rows)
            fig_share = px.bar(
                share, x="Exam", y="Share", color="Band", text="Students",
                color_discrete_map=BAND_COLOR,
                category_orders={"Band": ex.BAND_NAMES[::-1]},
                custom_data=["Band", "Students"],
                title=f"Band mix at each exam — the {len(all_sat)} students who sat all {len(available)}",
            )
            fig_share.update_traces(
                texttemplate="%{text}", textposition="inside",
                insidetextfont=dict(color=jw.WHITE),
                marker_line=dict(color=jw.WHITE, width=2),
                hovertemplate="%{x}<br>%{customdata[0]}: %{customdata[1]} students "
                              "(%{y:.0f}%)<extra></extra>",
            )
            fig_share.update_layout(**jw.plotly_layout(
                height=420, xaxis_title=None, yaxis_title="Share of students (%)",
                yaxis=dict(range=[0, 100]), bargap=0.45,
                legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, traceorder="reversed"),
                margin=dict(t=56, r=24, b=80, l=56),
            ))
            st.plotly_chart(fig_share, use_container_width=True)
            st.caption(
                "Numbers in the bars are student counts. Same students at every exam, "
                "so the changes are movement, not a change in who reported."
            )

        st.divider()
        st.markdown(f"### Rosters by {B} band")

        roster_cols = ["Student", "Exam 1", "Exam 2", "Change", "Band 1", "Movement",
                       "Homework %"]
        for band in ex.BAND_NAMES:
            members = growth[growth["Band 2"] == band]
            if members.empty:
                continue
            with st.expander(f"{band} — {len(members)} student(s)"):
                st.dataframe(
                    shown(members[roster_cols].sort_values("Exam 2", ascending=False)),
                    use_container_width=True, hide_index=True,
                )

        unbanded = growth[growth["Band 2"].isna()]
        if not unbanded.empty:
            with st.expander(f"No {B} score — {len(unbanded)} student(s)"):
                st.dataframe(
                    shown(unbanded[["Student", "Exam 1", "Band 1", "Homework %"]]
                          .sort_values("Student")),
                    use_container_width=True, hide_index=True,
                )

        _render_followup(growth, course_id, A, B)

    # ── Tab: Homework vs Growth ──────────────────────────────────────────────────

    with tab_homework:
        st.subheader(f"Homework and growth, {A} → {B}")
        cutoff = pd.Timestamp(end["homework_cutoff"])
        st.markdown(
            f"""
**Homework completion** is the share of the **{n_homework} homework assignments due
before {B}** (before {cutoff:%b} {cutoff.day}) that a student submitted. Homework set after
{B} isn't counted, since it can't have contributed to that score.
**Homework accuracy** is the student's average score on the homework they did submit.
"""
        )

        hp = paired.dropna(subset=["Homework %"]).copy()
        if hp.empty or n_homework == 0:
            st.info("No homework data matched to these students.")
        else:
            c_raw = ex.correlation(hp["Homework %"], hp["Change"])
            c_adj = ex.partial_correlation(hp["Homework %"], hp["Change"], hp["Exam 1"])
            a_raw = ex.correlation(hp["Homework Accuracy %"], hp["Change"])
            a_adj = ex.partial_correlation(hp["Homework Accuracy %"], hp["Change"], hp["Exam 1"])
            a_end = ex.correlation(hp["Homework Accuracy %"], hp["Exam 2"])

            fmt_r = lambda r: f"{r:+.2f}" if r is not None else "—"
            k = st.columns(4)
            k[0].metric("Students", len(hp), help=f"Have both exams and homework records.")
            k[1].metric("Median completion", f"{hp['Homework %'].median():.0f}%",
                        help=f"of {n_homework} homework assignments")
            k[2].metric("Completion ↔ growth", fmt_r(c_raw["pearson"]),
                        help="Pearson r between homework completion and score change. "
                             "0 = no relationship, ±1 = perfect.")
            k[3].metric("Accuracy ↔ growth", fmt_r(a_raw["pearson"]),
                        help="Pearson r between homework accuracy and score change.")

            # ── By completion tier: the band-movement question ────────────────
            st.markdown("### Growth by how much homework was done")
            tier_rows = []
            for tier, lo, hi in HOMEWORK_TIERS:
                g = hp[(hp["Homework %"] >= lo) & (hp["Homework %"] < hi)]
                if g.empty:
                    continue
                n = len(g)
                tier_rows.append({
                    "Homework done":        tier,
                    "Students":             n,
                    f"Mean {A}":            round(g["Exam 1"].mean(), 1),
                    f"Mean {B}":            round(g["Exam 2"].mean(), 1),
                    "Mean change":          round(g["Change"].mean(), 1),
                    "Improved %":           round((g["Change"] > 0).mean() * 100),
                    "Moved up a band %":    round((g["Movement"] == "Moved up").mean() * 100),
                    "Moved down a band %":  round((g["Movement"] == "Moved down").mean() * 100),
                    f"502+ on {B} %":       round((g["Band 2"] == ex.BAND_NAMES[0]).mean() * 100),
                })
            tiers = pd.DataFrame(tier_rows)
            tiers["label"] = tiers["Homework done"] + "<br><sub>" + tiers["Students"].astype(str) + " students</sub>"

            t_left, t_right = st.columns(2)
            with t_left:
                fig_up = px.bar(
                    tiers, x="label", y="Moved up a band %", text="Moved up a band %",
                    title="Moved up at least one band",
                    color_discrete_sequence=[jw.SUCCESS],
                )
                fig_up.update_traces(texttemplate="%{text}%", textposition="outside",
                                     hovertemplate="%{x}<br>%{y}% moved up<extra></extra>")
                fig_up.update_layout(**jw.plotly_layout(
                    height=360, xaxis_title="Homework completed", yaxis_title="% of students",
                    yaxis=dict(range=[0, max(10, tiers["Moved up a band %"].max() * 1.3)]),
                ))
                st.plotly_chart(fig_up, use_container_width=True)
            with t_right:
                fig_chg = px.bar(
                    tiers, x="label", y="Mean change", text="Mean change",
                    title="Mean score change (points)",
                    color_discrete_sequence=[jw.VIOLET_600],
                )
                fig_chg.update_traces(texttemplate="%{text:+.1f}", textposition="outside",
                                      hovertemplate="%{x}<br>%{y:+.1f} points<extra></extra>")
                fig_chg.add_hline(y=0, line_color=jw.GRAY_400)
                fig_chg.update_layout(**jw.plotly_layout(
                    height=360, xaxis_title="Homework completed", yaxis_title="Points",
                ))
                st.plotly_chart(fig_chg, use_container_width=True)

            st.dataframe(tiers.drop(columns=["label"]), use_container_width=True, hide_index=True)

            # ── What it adds up to ────────────────────────────────────────────
            # Written from the numbers each time, so a refresh that changes the
            # finding changes the sentence too.
            top = tiers.iloc[-1]
            bottom = tiers.iloc[0]
            share_90 = (hp["Homework %"] >= 90).mean() * 100
            findings = []
            if len(tiers) > 1:
                findings.append(
                    f"- **Band movement.** {top['Moved up a band %']:.0f}% of students in the "
                    f"{top['Homework done']} group moved up a band, against "
                    f"{bottom['Moved up a band %']:.0f}% in the {bottom['Homework done'].lower()} group. "
                    f"The groups are small ({', '.join(str(n) for n in tiers['Students'])} "
                    "students), so a difference of one or two students moves these percentages "
                    "a lot."
                )
            findings.append(
                f"- **Completion and points gained:** r = {fmt_r(c_raw['pearson'])} "
                f"({ex.strength_label(c_raw['pearson'])}); {fmt_r(c_adj['pearson'])} once "
                f"each student's {A} score is accounted for. {share_90:.0f}% of students "
                "completed at least 90% of the homework, so completion has little room to "
                "separate one student from another."
            )
            findings.append(
                f"- **Accuracy and points gained:** r = {fmt_r(a_raw['pearson'])} "
                f"({ex.strength_label(a_raw['pearson'])}); {fmt_r(a_adj['pearson'])} after "
                f"accounting for {A}. Accuracy tracks the {B} score itself more closely "
                f"(r = {fmt_r(a_end['pearson'])}) — students who get homework right also "
                "tend to score higher."
            )
            st.markdown("### What this shows\n" + "\n".join(findings))
            st.caption(
                "Correlation is not cause: students who keep up with homework may differ in "
                "other ways too. \"Accounted for\" means the relationship left after removing "
                f"what the {A} score alone predicts, because students who start low have "
                "more room to rise regardless of homework."
            )

            # ── Student by student ────────────────────────────────────────────
            st.divider()
            s_left, s_right = st.columns(2)
            with s_left:
                fig_c, _ = _scatter_with_fit(
                    hp, "Homework %", "Change",
                    title="Homework completion vs score change",
                    x_title="Homework completed (%)", y_title="Change (points)", hline=0,
                )
                st.plotly_chart(fig_c, use_container_width=True)
            with s_right:
                fig_a, _ = _scatter_with_fit(
                    hp.dropna(subset=["Homework Accuracy %"]), "Homework Accuracy %", "Change",
                    title="Homework accuracy vs score change",
                    x_title="Homework accuracy (%)", y_title="Change (points)", hline=0,
                )
                st.plotly_chart(fig_a, use_container_width=True)
            st.caption(f"Each dot is a student, coloured by their {B} band. "
                       "Dashed line = best fit; dotted line = no change.")

    # ── Tab: Student ─────────────────────────────────────────────────────────────

    with tab_student:
        st.subheader("Individual student")

        who = st.selectbox("Student", options=growth["Student"].sort_values().tolist())
        row = growth[growth["Student"] == who].iloc[0]

        s = st.columns(4)
        s[0].metric(A, f"{row['Exam 1']:.0f}" if pd.notna(row["Exam 1"]) else "—")
        s[1].metric(B, f"{row['Exam 2']:.0f}" if pd.notna(row["Exam 2"]) else "—")
        s[2].metric("Change", f"{row['Change']:+.0f}" if pd.notna(row["Change"]) else "—",
                    delta=f"{row['Change']:+.0f}" if pd.notna(row["Change"]) else None)
        s[3].metric("Homework completed",
                    f"{row['Homework %']:.0f}%" if pd.notna(row.get("Homework %")) else "—",
                    help=f"{row.get('Homework Done'):.0f} of {n_homework} due before {B}"
                         if pd.notna(row.get("Homework Done")) else None)

        if row["key"] in totals.index and len(available) > 2:
            history = totals.loc[row["key"]]
            st.markdown(
                "**Every exam:** " + " → ".join(
                    f"{exam} **{history[exam]:.0f}**" if pd.notna(history[exam]) else f"{exam} —"
                    for exam in history.index
                )
            )

        band1 = row["Band 1"] if isinstance(row["Band 1"], str) else "no score"
        band2 = row["Band 2"] if isinstance(row["Band 2"], str) else "no score"
        chip = lambda label, color: (
            f"<span style='background:{color}1F;color:{color};padding:4px 12px;"
            f"border-radius:999px;font-weight:700;font-size:0.85rem'>{label}</span>"
        )
        st.markdown(
            "**Band:** "
            + chip(band1, BAND_COLOR.get(band1, jw.GRAY_400)) + " &nbsp;→&nbsp; "
            + chip(band2, BAND_COLOR.get(band2, jw.GRAY_400))
            + f" &nbsp;&nbsp;<span style='color:{jw.GRAY_500}'>({row['Movement']})</span>",
            unsafe_allow_html=True,
        )

        def _fmt(value, signed=False) -> str:
            if value is None or pd.isna(value):
                return "—"
            return f"{value:+.0f}" if signed else f"{value:.0f}"

        section_df = pd.DataFrame([
            {
                "Section": section,
                A:         _fmt(row.get(f"{section} 1")),
                B:         _fmt(row.get(f"{section} 2")),
                "Change":  _fmt(row.get(f"{section} Δ"), signed=True),
            }
            for section in ex.SECTIONS
        ])
        has_any = any(section_df.loc[:, [A, B]].to_numpy().ravel() != "—")
        if has_any:
            st.markdown("##### Sections (scaled)")
            st.dataframe(section_df, use_container_width=True, hide_index=True)
            if all(v == "—" for v in section_df["Change"]):
                st.caption(
                    "Section change is blank because only one of these two exams "
                    "collected scaled section scores."
                )
        else:
            st.caption("No scaled section scores available for this student.")

    # ── Tab: Data & Coverage ─────────────────────────────────────────────────────

    with tab_data:
        st.subheader("Coverage")

        cov = st.columns(len(available) + 1)
        for col, exam in zip(cov, available):
            frame = scores[exam["label"]]
            col.metric(f"{exam['short']} scores", int(frame["total"].notna().sum()),
                       help=f"{len(frame)} rows; {int(frame['total'].notna().sum())} with a readable total")
        cov[-1].metric(f"In both {A} and {B}", len(paired))

        lines = []
        for exam in available:
            frame = scores[exam["label"]]
            note = ""
            dropped = other_exam.get(exam["label"])
            if dropped is not None and len(dropped):
                note = (f" — {int(dropped.sum())} row(s) set aside for reporting a different exam: "
                        + ", ".join(f"{n} × {what}" for what, n in dropped.items()))
            lines.append(
                f"- **{exam['short']}** ({exam['name']}, {names.get(exam['label'], '')}) → "
                f"{int(frame['total'].notna().sum())} of {len(frame)} usable totals{note}"
            )
        if len(all_sat):
            lines.append(f"- **{len(all_sat)}** students have a score for all {len(available)} exams")
        lines.append(
            f"- Homework drawn from **{n_homework}** assignment(s) due before "
            f"{end['homework_cutoff']}; participation from **{n_items}** cached item(s) "
            f"for course {int(course_id)}"
        )
        st.markdown("\n".join(lines))

        st.divider()
        st.markdown("### Scores that couldn't be read")
        st.caption(
            "A total is accepted only inside 472–528, and section scores inside 118–132. "
            "Raw question counts like “25/59” are ignored on purpose. Fix these at the "
            "source form and re-export to bring the students below into the analysis."
        )
        if not raw:
            st.caption(
                "Unreadable rows are reported when reading raw exports. The published "
                "data has already had them filtered out at build time."
            )
        else:
            for exam in available:
                label = exam["label"]
                if label not in raw:
                    continue
                bad = _unparsed_rows(raw[label], scores[label], maps[label])
                if bad.empty:
                    st.success(f"**{exam['short']}** — every row parsed.")
                else:
                    st.markdown(f"**{exam['short']}** — {len(bad)} unusable row(s)")
                    st.dataframe(bad, use_container_width=True, hide_index=True)

        only1 = growth[growth["Exam 1"].notna() & growth["Exam 2"].isna()]
        only2 = growth[growth["Exam 2"].notna() & growth["Exam 1"].isna()]
        st.divider()
        st.markdown("### Students in one exam only")
        one_col1, one_col2 = st.columns(2)
        with one_col1:
            st.markdown(f"**{A} but not {B} — {len(only1)}**")
            st.dataframe(shown(only1[["Student", "Exam 1", "Band 1", "Homework %"]]),
                         use_container_width=True, hide_index=True)
        with one_col2:
            st.markdown(f"**{B} but not {A} — {len(only2)}**")
            st.dataframe(shown(only2[["Student", "Exam 2", "Band 2", "Homework %"]]),
                         use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### Downloads")
        export_cols = [c for c in growth.columns if c != "key"]
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Growth table (CSV)",
            shown(growth[export_cols]).to_csv(index=False).encode(),
            file_name=f"ey26_exam_growth_{start['label']}_{end['label']}.csv",
            mime="text/csv",
        )
        if len(participation):
            d2.download_button(
                "⬇️ Participation table (CSV)",
                participation.drop(columns=["key"]).to_csv(index=False).encode(),
                file_name=f"ey26_participation_course_{int(course_id)}.csv",
                mime="text/csv",
            )
