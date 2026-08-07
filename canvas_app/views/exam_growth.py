"""
Exam Growth — JAMP EY26 first → second full-length comparison.

Three questions this page answers:
  1. How much did each student grow between the two exams?
  2. Which score band is each student in (502+ / 496–501 / ≤495), and who moved?
  3. Does course participation track with improvement?

Score files live in `exam_data/` at the repo root (drop the next exam's export
there) or can be uploaded ad hoc. That directory is gitignored — the exports
carry student names — so on the deployed app the only route in is the uploader.
Participation comes from the local Canvas report cache that sync_reports.py
builds.
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


def _source_picker(label: str, key: str, default_match: str) -> "tuple[pd.DataFrame | None, str]":
    """
    Choose a score file for one exam: a file from exam_data/, or an upload.
    Returns (dataframe, human-readable source name).
    """
    files = _data_dir_files()
    options = [f.name for f in files]
    default_index = next(
        (i for i, name in enumerate(options) if default_match in name.lower()), 0
    )

    choice = st.selectbox(
        label,
        options=options + ["Upload a file…"],
        index=default_index if options else len(options),
        key=f"src_{key}",
        help="Files listed here come from `exam_data/`. Drop new exports in that folder.",
    )

    if choice == "Upload a file…":
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


# ─── Course work vs exam growth ──────────────────────────────────────────────

def _render_course_work_section(paired, topic_gains, course_id) -> None:
    """
    Whether doing well in the course predicted improving on the MCAT.

    It didn't, and this section says so. It stays in the app because a null
    result that isn't written down gets re-investigated, and because the method
    matters: the obvious version of this analysis produces a convincing-looking
    positive number that is entirely an artefact.
    """
    st.markdown("### Did course work predict exam improvement?")

    if topic_gains.empty or "Standing Change" not in paired.columns:
        st.caption("Not enough paired course data for this course to answer that.")
        return

    view = paired.dropna(subset=["Standing Change", "Change"])
    if len(view) < 4:
        st.caption("Too few students have both course and exam data to answer that.")
        return

    raw = ex.correlation(view["Standing Change"], view["Change"])
    adj = ex.partial_correlation(view["Standing Change"], view["Change"], view["Exam 1"])

    st.info(
        f"**No. Course performance and MCAT improvement are unrelated in this cohort** "
        f"(r = {raw['pearson']:+.2f}; r = {adj['pearson']:+.2f} after accounting for where "
        f"students started, n = {len(view)}). Students who improved most in class were "
        f"not the students who improved most on the MCAT. The exam growth on the other "
        f"tabs is the real result — this is here to record that the link was tested.",
        icon="🔍",
    )

    with st.expander("How this was measured, and why the obvious version is wrong"):
        st.markdown(
            "**The idea.** Every session has a *pre-class quiz* taken before teaching and "
            "a *homework* on the same topic taken after. The difference between a "
            "student's two scores should approximate what they learned from that session."
            "\n\n"
            "**Why raw score difference fails.** Homework and quiz are not equally hard. "
            f"Across the {len(topic_gains)} paired topics the cohort's average moved by "
            f"{topic_gains['Gain'].min():+.0f} to {topic_gains['Gain'].max():+.0f} points "
            "depending on the topic — Emotion and Stress homework ran far harder than its "
            "quiz, Redox far easier. A raw difference therefore measures which topics a "
            "student happened to sit as much as what they learned. It is also mechanically "
            "tied to the starting score: anyone who scores low on the quiz has more room "
            "to gain."
            "\n\n"
            "**What is used instead.** Each student is scored against their own cohort on "
            "each assignment, then compared: *how far up the class did they move from quiz "
            "to homework on the same material?* A harder homework pushes everyone down "
            "equally and cancels out. This measure is largely free of the starting-score "
            "artefact (correlation with starting score falls from −0.47 to −0.15)."
            "\n\n"
            "**Result.** Even with a clean measure, it is unrelated to MCAT change. "
            "Course assessments do track *ability* — pre-class scores correlate with "
            "Exam 1 at about +0.5 — they just do not predict who *improves*."
        )

        st.markdown("**Topic difficulty — the confound this controls for**")
        st.caption(
            "Cohort average on the pre-class quiz vs the homework for the same topic. "
            "A large gap means the two assessments were not equally hard."
        )
        show = topic_gains[["Topic", "Students", "Pre %", "Post %", "Gain"]].rename(
            columns={"Pre %": "Pre-class avg %", "Post %": "Homework avg %",
                     "Gain": "Difficulty gap (pts)"})
        st.dataframe(show, use_container_width=True, hide_index=True)

        dropped = topic_gains.attrs.get("dropped_ungraded") or []
        if dropped:
            st.caption(
                "Excluded as ungraded (Canvas reports 0 correct, 0 incorrect and 0 "
                "no-response for every student, so there is nothing to compare): "
                + ", ".join(dropped)
            )

        st.markdown("**Every candidate measure against exam change**")
        st.caption(
            "The second column is what matters: it removes the effect of where a student "
            "started, since low starters improve more regardless. Nothing survives it."
        )
        rows = []
        for col, label in [
            ("Standing Change",          "Course learning (difficulty-adjusted)"),
            ("Learning Gain",            "Course learning (raw point difference)"),
            ("Pre-Class Avg %",          "Pre-class quiz score"),
            ("Post-Class Avg %",         "Homework score"),
            ("Participation %",          "Participation rate"),
            ("Avg Task Score %",         "Average score across all course items"),
        ]:
            if col not in paired.columns or paired[col].notna().sum() < 4:
                continue
            r1 = ex.correlation(paired[col], paired["Change"])
            r2 = ex.partial_correlation(paired[col], paired["Change"], paired["Exam 1"])
            rows.append({
                "Measure": label,
                "Students": r1["n"],
                "vs exam change": round(r1["pearson"], 2) if r1["pearson"] is not None else None,
                "…allowing for starting score": round(r2["pearson"], 2) if r2["pearson"] is not None else None,
                "Verdict": ex.strength_label(r2["pearson"]),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─── Charts ──────────────────────────────────────────────────────────────────

def _dumbbell(paired: pd.DataFrame, title: str) -> go.Figure:
    """One row per student: Exam 1 dot → Exam 2 dot, connected, sorted by change."""
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
        ("Exam 1", EXAM1_COLOR, "Exam 1"),
        ("Exam 2", EXAM2_COLOR, "Exam 2"),
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
                              + y_title + ": %{y:+.1f}<extra>" + band + "</extra>",
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
            hovertemplate="%{text}<br>%{x:.1f} → %{y:+.1f}<extra></extra>",
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


def render() -> None:
    # ─── Sidebar ─────────────────────────────────────────────────────────────────

    # Nothing here needs setting for the page to work — the defaults are the
    # EY26 cohort. Kept behind an expander so the sidebar is empty at a glance
    # when this is being presented.
    with st.sidebar:
        st.title("📈 Exam Growth")
        st.caption("MCAT full-length 1 → full-length 2, JAMP EY26 cohort.")
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
                help="Participation = the share of these items a student submitted.",
            )

    st.markdown(jw.brand_header("Exam Growth — JAMP EY26"), unsafe_allow_html=True)

    # ─── Sources ─────────────────────────────────────────────────────────────────
    #
    # Default path needs no input at all: the committed bundle already holds both
    # exams. The file pickers only appear when someone opens the loading section,
    # so this page can be projected in front of administration as-is.

    local_files = _data_dir_files()
    name1 = name2 = ""

    if local_files:
        with st.expander("📂 Score sources", expanded=False):
            st.caption(
                "Reading MCAT exports from `exam_data/`. Adjust the file or column "
                "mapping here if a new export is shaped differently."
            )
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Exam 1 (baseline)")
                df1, name1 = _source_picker("Exam 1 file", "e1", "exam1")
                map1 = _mapping_controls(df1, name1, "e1") if df1 is not None else None
            with col2:
                st.markdown("##### Exam 2")
                df2, name2 = _source_picker("Exam 2 file", "e2", "exam2")
                map2 = _mapping_controls(df2, name2, "e2") if df2 is not None else None

        if df1 is None or df2 is None or map1 is None or map2 is None:
            st.info("Choose a file for each exam in **Score sources** above.")
            st.stop()

        scores1 = ex.extract_scores(df1, map1["name_col"], map1["total_col"], map1["section_cols"])
        scores2 = ex.extract_scores(df2, map2["name_col"], map2["total_col"], map2["section_cols"])
        # Students who answered the survey with a screenshot instead of numbers
        # are unreadable from the export; their scores are typed into
        # exam_data/manual_scores.csv and folded in here.
        scores1 = ex.with_manual(scores1, "exam1")
        scores2 = ex.with_manual(scores2, "exam2")

        if scores1["total"].notna().sum() == 0 or scores2["total"].notna().sum() == 0:
            which = "Exam 1" if scores1["total"].notna().sum() == 0 else "Exam 2"
            st.error(
                f"No valid MCAT totals (472–528) could be read from the **{which}** file. "
                "Check the column mapping in **Score sources**."
            )
            st.stop()

    elif bundle.has_exams():
        scores1, scores2 = bundle.exam_frames()
        name1, name2 = "published data (Exam 1)", "published data (Exam 2)"
        df1 = df2 = None
        map1 = map2 = None
        if scores1.empty or scores2.empty:
            st.error("The published exam data is missing one of the two exams.")
            st.stop()

    else:
        st.info(
            "No exam scores are available. On a local checkout, drop the MCAT "
            "exports into `exam_data/`; on the server, run `build_data_bundle.py` "
            "and commit `data/`."
        )
        st.stop()

    growth = ex.build_growth_table(scores1, scores2)
    growth["Movement"] = growth.apply(ex.band_movement, axis=1)

    participation, n_items = ex.participation_table(int(course_id), participation_types)
    if len(participation):
        growth = growth.merge(
            participation.drop(columns=["Student", "Items Available"]), on="key", how="left"
        )
    else:
        for col in ("Items Completed", "Participation %", "Avg Task Score %"):
            growth[col] = np.nan

    # Within-course learning: pre-class quiz vs participation task on the same
    # topic. Merged here so every tab can use it, not just the Learning tab.
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
            "No student appears in both exam files with a readable score, so growth "
            "can't be computed. Check that the name columns hold comparable names."
        )
        st.stop()

    # The learning analysis is deliberately not a headline tab. Course learning
    # turned out to have no relationship with exam growth (r = -0.08 once the
    # Exam 1 baseline is controlled for), so promoting it would advertise a
    # finding that isn't there. It lives inside Data & Coverage, where the
    # method and the null result are both written down.
    tab_growth, tab_bands, tab_student, tab_data = st.tabs(
        ["📈 Growth", "🎯 Score Bands", "👤 Student", "🧾 Data & Methods"]
    )

    # ── Tab: Growth ──────────────────────────────────────────────────────────────

    with tab_growth:
        st.subheader("Growth from Exam 1 to Exam 2")
        st.markdown(
            f"""
Students in this cohort sat two full-length practice MCATs, and reported their
scores through a Canvas survey. This tab compares the two.

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
        m[1].metric("Mean Exam 1", f"{paired['Exam 1'].mean():.1f}")
        m[2].metric("Mean Exam 2", f"{paired['Exam 2'].mean():.1f}")
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

        view_col, n_col = st.columns([2, 1])
        view = view_col.radio(
            "Students to chart",
            options=["All", "Biggest gains", "Biggest drops"],
            horizontal=True,
        )
        if view == "All":
            charted, chart_title = paired, f"Exam 1 → Exam 2, all {len(paired)} students (sorted by change)"
        else:
            top_n = n_col.slider("How many", 5, max(5, len(paired)), min(20, len(paired)), 5)
            ascending = view == "Biggest drops"
            charted = paired.sort_values("Change", ascending=ascending).head(top_n)
            chart_title = f"Exam 1 → Exam 2 — {view.lower()} ({len(charted)} students)"

        st.plotly_chart(_dumbbell(charted, chart_title), use_container_width=True)

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
                title="Exam 1 vs Exam 2 (dashed = no change)",
                x_title="Exam 1 total", y_title="Exam 2 total",
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
                title="Mean section change (scaled points)",
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
                title="Exam 2 mean section scaled score",
                color_discrete_sequence=[EXAM2_COLOR],
            )
            fig_sec.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_sec.update_layout(**jw.plotly_layout(height=360, yaxis_range=[117, 133]))
            st.plotly_chart(fig_sec, use_container_width=True)
            st.caption(
                "Section *change* needs scaled section scores in both files. The Exam 1 "
                "form collected raw question counts rather than scaled sections, so only "
                "Exam 2 sections are shown."
            )

    # ── Tab: Score Bands ─────────────────────────────────────────────────────────

    with tab_bands:
        st.subheader("Score bands")
        st.markdown(
            """
Students are grouped into three bands by total score, so movement between them
shows how the cohort's readiness shifted rather than just its average.

| Band | Score | Meaning |
|---|---|---|
| **On Track** | 502 and above | At or above the median MCAT score |
| **Borderline** | 496 – 501 | Close, but below the median |
| **Needs Support** | 495 and below | Well below the median |

A student "moved up" if their band on Exam 2 is higher than on Exam 1.
"""
        )

        n_e1 = int(growth["Exam 1"].notna().sum())
        n_e2 = int(growth["Exam 2"].notna().sum())

        cohort = st.radio(
            "Cohort",
            options=["paired", "all"],
            format_func=lambda v: (f"Students with both exams ({len(paired)}) — like-for-like"
                                   if v == "paired"
                                   else f"Everyone with a score ({n_e1} Exam 1 / {n_e2} Exam 2)"),
            horizontal=True,
            help="Exam 1 and Exam 2 were taken by different numbers of students, so "
                 "comparing all of each would mix real movement with who sat the exam. "
                 "The like-for-like view fixes the cohort to the students in both.",
        )
        band_source = paired if cohort == "paired" else growth

        band_df = pd.DataFrame([
            {
                "Band":   band,
                "Exam 1": int((band_source["Band 1"] == band).sum()),
                "Exam 2": int((band_source["Band 2"] == band).sum()),
            }
            for band in ex.BAND_NAMES
        ])

        tiles = st.columns(3)
        for i, band in enumerate(ex.BAND_NAMES):
            n1 = int(band_df.loc[i, "Exam 1"])
            n2 = int(band_df.loc[i, "Exam 2"])
            tiles[i].metric(
                band, n2,
                delta=f"{n2 - n1:+d} vs Exam 1" if cohort == "paired" else None,
                help=(f"{n1} were in this band on Exam 1" if cohort == "paired" else
                      "Different students sat each exam, so no change figure is shown "
                      "here — switch to the like-for-like cohort for that."),
            )

        long = band_df.melt(id_vars="Band", var_name="Exam", value_name="Students")
        fig_band = px.bar(
            long, x="Band", y="Students", color="Exam", barmode="group", text="Students",
            title=("Students per band, Exam 1 vs Exam 2 — same students in both"
                   if cohort == "paired" else
                   "Students per band — everyone with a score for that exam"),
            color_discrete_map={"Exam 1": EXAM1_COLOR, "Exam 2": EXAM2_COLOR},
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
                f"Exam 1 covers {n_e1} students and Exam 2 covers {n_e2}, and they are "
                "not the same group — a drop in a band here can just mean those students "
                "didn't sit Exam 2. Use the like-for-like cohort to read movement."
            )

        st.divider()
        st.markdown("### Band movement")

        moves = paired[paired["Movement"] != "—"]
        mv = st.columns(3)
        mv[0].metric("Moved up", int((moves["Movement"] == "Moved up").sum()))
        mv[1].metric("Stayed", int((moves["Movement"] == "Stayed").sum()))
        mv[2].metric("Moved down", int((moves["Movement"] == "Moved down").sum()))

        matrix = pd.DataFrame(
            [[int(((paired["Band 1"] == b1) & (paired["Band 2"] == b2)).sum())
              for b2 in ex.BAND_NAMES] for b1 in ex.BAND_NAMES],
            index=ex.BAND_NAMES, columns=ex.BAND_NAMES,
        )
        fig_mx = px.imshow(
            matrix, text_auto=True, aspect="auto",
            color_continuous_scale=[[0, jw.VIOLET_50], [1, jw.VIOLET_600]],
            labels={"x": "Exam 2 band", "y": "Exam 1 band", "color": "Students"},
            title="Where students ended up (rows = Exam 1, columns = Exam 2)",
        )
        fig_mx.update_coloraxes(showscale=False)
        fig_mx.update_layout(**jw.plotly_layout(
            height=380, margin=dict(t=64, r=16, b=16, l=16),
            xaxis=dict(side="bottom"),
        ))
        st.plotly_chart(fig_mx, use_container_width=True)

        st.divider()
        st.markdown("### Rosters by Exam 2 band")

        roster_cols = ["Student", "Exam 1", "Exam 2", "Change", "Band 1", "Movement",
                       "Participation %"]
        for band in ex.BAND_NAMES:
            members = growth[growth["Band 2"] == band]
            if members.empty:
                continue
            with st.expander(f"{band} — {len(members)} student(s)"):
                st.dataframe(
                    members[roster_cols].sort_values("Exam 2", ascending=False),
                    use_container_width=True, hide_index=True,
                )

        unbanded = growth[growth["Band 2"].isna()]
        if not unbanded.empty:
            with st.expander(f"No Exam 2 score — {len(unbanded)} student(s)"):
                st.dataframe(
                    unbanded[["Student", "Exam 1", "Band 1", "Participation %"]]
                    .sort_values("Student"),
                    use_container_width=True, hide_index=True,
                )

    # ── Tab: Participation vs Growth ─────────────────────────────────────────────

    with tab_student:
        st.subheader("Individual student")

        who = st.selectbox("Student", options=growth["Student"].sort_values().tolist())
        row = growth[growth["Student"] == who].iloc[0]

        s = st.columns(4)
        s[0].metric("Exam 1", f"{row['Exam 1']:.0f}" if pd.notna(row["Exam 1"]) else "—")
        s[1].metric("Exam 2", f"{row['Exam 2']:.0f}" if pd.notna(row["Exam 2"]) else "—")
        s[2].metric("Change", f"{row['Change']:+.0f}" if pd.notna(row["Change"]) else "—",
                    delta=f"{row['Change']:+.0f}" if pd.notna(row["Change"]) else None)
        s[3].metric("Participation",
                    f"{row['Participation %']:.0f}%" if pd.notna(row.get("Participation %")) else "—",
                    help=f"{row.get('Items Completed')} of {n_items} items"
                         if pd.notna(row.get("Items Completed")) else None)

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
                "Exam 1":  _fmt(row.get(f"{section} 1")),
                "Exam 2":  _fmt(row.get(f"{section} 2")),
                "Change":  _fmt(row.get(f"{section} Δ"), signed=True),
            }
            for section in ex.SECTIONS
        ])
        has_any = any(section_df.loc[:, ["Exam 1", "Exam 2"]].to_numpy().ravel() != "—")
        if has_any:
            st.markdown("##### Sections (scaled)")
            st.dataframe(section_df, use_container_width=True, hide_index=True)
            if all(v == "—" for v in section_df["Change"]):
                st.caption(
                    "Section change is blank because the Exam 1 form collected raw "
                    "question counts rather than scaled section scores."
                )
        else:
            st.caption("No scaled section scores available for this student.")

    # ── Tab: Data & Coverage ─────────────────────────────────────────────────────

    with tab_data:
        st.subheader("Coverage")

        cov = st.columns(4)
        cov[0].metric("Exam 1 rows", len(scores1),
                      help=f"{int(scores1['total'].notna().sum())} with a readable total")
        cov[1].metric("Exam 2 rows", len(scores2),
                      help=f"{int(scores2['total'].notna().sum())} with a readable total")
        cov[2].metric("In both exams", len(paired))
        cov[3].metric("Matched to participation",
                      int(growth["Participation %"].notna().sum()))

        st.markdown(
            f"- **{name1}** → {int(scores1['total'].notna().sum())} of {len(scores1)} usable totals\n"
            f"- **{name2}** → {int(scores2['total'].notna().sum())} of {len(scores2)} usable totals\n"
            f"- **{len(growth)}** distinct students across both files; "
            f"**{len(paired)}** have a score in each and drive every growth number\n"
            f"- Participation drawn from **{n_items}** cached item(s) for course {int(course_id)}"
        )

        st.divider()
        st.markdown("### Scores that couldn't be read")
        st.caption(
            "A total is accepted only inside 472–528, and section scores inside 118–132. "
            "Raw question counts like “25/59” are ignored on purpose. Fix these at the "
            "source form and re-export to bring the students below into the analysis."
        )
        if map1 is None or map2 is None:
            st.caption(
                "Unreadable rows are reported when reading raw exports. The published "
                "data has already had them filtered out at build time."
            )
        else:
            for label, df_raw, extracted, mapping in (
                (name1, df1, scores1, map1),
                (name2, df2, scores2, map2),
            ):
                bad = _unparsed_rows(df_raw, extracted, mapping)
                if bad.empty:
                    st.success(f"**{label}** — every row parsed.")
                else:
                    st.markdown(f"**{label}** — {len(bad)} unusable row(s)")
                    st.dataframe(bad, use_container_width=True, hide_index=True)

        only1 = growth[growth["Exam 1"].notna() & growth["Exam 2"].isna()]
        only2 = growth[growth["Exam 2"].notna() & growth["Exam 1"].isna()]
        st.divider()
        st.markdown("### Students in one exam only")
        one_col1, one_col2 = st.columns(2)
        with one_col1:
            st.markdown(f"**Exam 1 but not Exam 2 — {len(only1)}**")
            st.dataframe(only1[["Student", "Exam 1", "Band 1", "Participation %"]],
                         use_container_width=True, hide_index=True)
        with one_col2:
            st.markdown(f"**Exam 2 but not Exam 1 — {len(only2)}**")
            st.dataframe(only2[["Student", "Exam 2", "Band 2", "Participation %"]],
                         use_container_width=True, hide_index=True)

        st.divider()
        _render_course_work_section(paired, topic_gains, course_id)

        st.divider()
        st.markdown("### Downloads")
        export_cols = [c for c in growth.columns if c != "key"]
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Growth table (CSV)",
            growth[export_cols].to_csv(index=False).encode(),
            file_name=f"ey26_exam_growth_course_{int(course_id)}.csv",
            mime="text/csv",
        )
        if len(participation):
            d2.download_button(
                "⬇️ Participation table (CSV)",
                participation.drop(columns=["key"]).to_csv(index=False).encode(),
                file_name=f"ey26_participation_course_{int(course_id)}.csv",
                mime="text/csv",
            )
