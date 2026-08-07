"""
Course Performance — what students did in the Canvas course, from published data.

Built for presentation: it opens with no credentials, no uploads and nothing to
type, reading the de-identified bundle in data/ that build_data_bundle.py
produces. Every section states what it is showing and what it was computed from,
because the audience is not the person who built it.

Reads through canvas_app.exam_scores, so a local checkout with the full report
cache renders the same page with real names.
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from .. import bundle
from .. import exam_scores as ex
from .. import jw_theme as jw

COHORTS = {345: "EY26", 351: "EY25"}

# Ordered most- to least-instructional, which is also how they read in a table.
TYPE_ORDER = ["Pre-Class Quiz", "Homework", "Participation Task", "Survey", "Other"]
TYPE_COLOR = {
    "Pre-Class Quiz":     jw.VIOLET_300,
    "Homework":           jw.VIOLET_600,
    "Participation Task": jw.TEAL_500,
    "Survey":             jw.AMBER_500,
    "Other":              jw.GRAY_400,
}

TYPE_MEANING = {
    "Pre-Class Quiz":     "Taken **before** the session, to check what students already knew.",
    "Homework":           "Taken **after** the session, graded on correctness. The most informative score.",
    "Participation Task": "Completed **during** the session. Marked for taking part, not for accuracy.",
    "Survey":             "Forms and score-reporting. Ungraded, so no accuracy figure.",
    "Other":              "Anything that doesn't fit the categories above.",
}


def _course_table(course_id: int) -> pd.DataFrame:
    """One row per assignment: type, submissions, average score."""
    items = ex.course_items(course_id)
    if items.empty:
        return items
    rows = []
    for _, item in items.iterrows():
        aid = item["assignment_id"]
        submitters = ex.course_submitters(course_id, aid)
        pcts = ex._pct_by_key(course_id, aid)
        values = list(pcts.values())
        rows.append({
            "Assignment":  item["title"],
            "Type":        item["item_type"],
            "Submissions": len(submitters),
            "Average %":   round(sum(values) / len(values), 1) if values else None,
            "due_at":      item.get("due_at") or "",
            "assignment_id": aid,
        })
    return pd.DataFrame(rows).sort_values(["due_at", "Assignment"]).reset_index(drop=True)


def render() -> None:
    with st.sidebar:
        st.title("📚 Course Performance")
        st.caption("What students did in the Canvas course.")
        with st.expander("Advanced settings", expanded=False):
            course_id = int(st.selectbox(
                "Course",
                options=list(COHORTS),
                format_func=lambda c: f"{COHORTS[c]} — Canvas course {c}",
                help="EY26 is the current cohort; EY25 is the prior year.",
            ))

    st.markdown(jw.brand_header(f"Course Performance — {COHORTS.get(course_id, course_id)}"),
                unsafe_allow_html=True)

    table = _course_table(course_id)
    if table.empty:
        st.warning(
            f"No published course data for Canvas course {course_id}. "
            "Run `build_data_bundle.py` on a local checkout and commit `data/`."
        )
        return

    graded = table[table["Average %"].notna()]
    n_students = 0
    for aid in table["assignment_id"]:
        n_students = max(n_students, len(ex.course_submitters(course_id, aid)))

    # ── What this page is ─────────────────────────────────────────────────────
    st.markdown(
        f"""
This page summarises every graded activity in the **{COHORTS.get(course_id, course_id)}**
Canvas course. Each row of data behind it is one student's submission to one
assignment. Students are shown as anonymous identifiers.

**How to read the two headline numbers:**

- **Participation** — the share of enrolled students who submitted an activity.
  It says how many took part, not how well they did.
- **Accuracy** — the average score of the students who *did* submit, as a
  percentage of the available points. It says how well the work was done, and it
  ignores anyone who didn't hand in.

A high participation rate with low accuracy means students showed up but
struggled; the reverse means a strong few and a long tail of non-submitters.
"""
    )

    k = st.columns(4)
    k[0].metric("Activities", len(table),
                help="Distinct Canvas assignments with at least one submission.")
    k[1].metric("Graded activities", len(graded),
                help="Activities that carry a score. Surveys and completion forms don't.")
    k[2].metric("Students seen", n_students,
                help="Largest number of students submitting any single activity.")
    k[3].metric("Average accuracy", f"{graded['Average %'].mean():.0f}%",
                help="Mean of each graded activity's average score.")

    st.divider()

    # ── Activity types ────────────────────────────────────────────────────────
    st.markdown("### The course runs four kinds of activity")
    st.caption(
        "Each session follows the same shape, and the type of an activity "
        "determines what its score can tell you."
    )

    present = [t for t in TYPE_ORDER if t in set(table["Type"])]
    for t in present:
        subset = table[table["Type"] == t]
        scored = subset[subset["Average %"].notna()]
        avg = f"{scored['Average %'].mean():.0f}%" if len(scored) else "not scored"
        st.markdown(
            f"<div style='border-left:3px solid {TYPE_COLOR.get(t, jw.GRAY_400)};"
            f"padding:2px 0 2px 12px;margin-bottom:10px'>"
            f"<b>{t}</b> — {len(subset)} activities · average <b>{avg}</b><br>"
            f"<span style='color:{jw.GRAY_500};font-size:0.92em'>{TYPE_MEANING.get(t,'')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.info(
        "**Participation tasks are not a measure of ability.** They are marked for "
        "taking part, so nearly every student scores close to 100%. Their scores "
        "correlate almost not at all with MCAT performance (about +0.09), while "
        "pre-class quiz and homework scores correlate around +0.5. Read participation "
        "task figures as attendance, and homework figures as learning.",
        icon="💡",
    )

    st.divider()

    # ── Accuracy by type ──────────────────────────────────────────────────────
    st.markdown("### Average score by activity type")
    st.caption(
        "Each bar is the average of every graded activity of that type. Only the "
        "students who submitted are counted."
    )
    by_type = (graded.groupby("Type")["Average %"].mean().reindex(present).dropna()
               .reset_index())
    if len(by_type):
        fig = go.Figure(go.Bar(
            x=by_type["Type"], y=by_type["Average %"],
            marker_color=[TYPE_COLOR.get(t, jw.GRAY_400) for t in by_type["Type"]],
            text=[f"{v:.0f}%" for v in by_type["Average %"]], textposition="outside",
            hovertemplate="%{x}<br>average %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(**jw.plotly_layout(height=340, yaxis_range=[0, 108],
                                             yaxis_title="Average score %", xaxis_title=None))
        st.plotly_chart(fig, use_container_width=True)

    # ── Over time ─────────────────────────────────────────────────────────────
    dated = table[table["due_at"].astype(str).str.len() > 0].copy()
    dated["Date"] = pd.to_datetime(dated["due_at"], utc=True, errors="coerce")
    dated = dated.dropna(subset=["Date", "Average %"])
    if len(dated) > 2:
        st.divider()
        st.markdown("### Scores over the course")
        st.caption(
            "One point per graded activity, in due-date order. A downward drift usually "
            "means later material was harder, not that students got worse — the topics "
            "change from week to week."
        )
        fig_t = px.scatter(
            dated, x="Date", y="Average %", color="Type",
            hover_name="Assignment", color_discrete_map=TYPE_COLOR,
            category_orders={"Type": present},
        )
        fig_t.update_traces(marker=dict(size=10, line=dict(color=jw.WHITE, width=1)))
        fig_t.update_layout(**jw.plotly_layout(
            height=400, yaxis_range=[0, 105], yaxis_title="Average score %",
            xaxis_title="Due date",
            legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
            margin=dict(t=30, r=20, b=80, l=60),
        ))
        st.plotly_chart(fig_t, use_container_width=True)

    # ── Pre-class vs homework ─────────────────────────────────────────────────
    _, topics = ex.learning_tables(course_id, post_type="Homework")
    if not topics.empty:
        st.divider()
        st.markdown("### Before and after teaching, by topic")
        st.caption(
            "For each topic, the cohort's average on the pre-class quiz (taken before "
            "the session) against the homework on the same topic (taken after). The two "
            "assessments are not equally hard, so the gap between them is not a clean "
            "measure of learning — it is shown here to describe the topics, not to rank them."
        )
        view = topics.head(20)
        fig_p = go.Figure()
        for _, row in view.iterrows():
            fig_p.add_trace(go.Scatter(
                x=[row["Pre %"], row["Post %"]], y=[row["Topic"], row["Topic"]],
                mode="lines", line=dict(color=jw.GRAY_200, width=2),
                showlegend=False, hoverinfo="skip"))
        for name, color, col in (("Pre-class quiz", jw.VIOLET_300, "Pre %"),
                                 ("Homework", jw.VIOLET_600, "Post %")):
            fig_p.add_trace(go.Scatter(
                x=view[col], y=view["Topic"], mode="markers", name=name,
                marker=dict(size=10, color=color, line=dict(color=jw.WHITE, width=2)),
                customdata=view["Students"],
                hovertemplate="%{y}<br>" + name + ": %{x:.1f}%<br>%{customdata} students<extra></extra>"))
        fig_p.update_layout(**jw.plotly_layout(
            height=max(360, len(view) * 26 + 150), xaxis_title="Cohort average %",
            xaxis_range=[0, 105], yaxis_title=None,
            yaxis=dict(categoryorder="array", categoryarray=view["Topic"].tolist()[::-1],
                       tickfont=dict(size=10)),
            legend=dict(orientation="h", yanchor="bottom", y=1.005, x=0),
            margin=dict(t=100, r=24, b=48, l=8)))
        st.plotly_chart(fig_p, use_container_width=True)

    # ── Full table ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Every activity")
    st.caption(
        "Submissions is how many students handed the activity in. Average % is the "
        "mean score among those students. A blank average means the activity carries "
        "no score — a survey or a completion form."
    )
    pick = st.multiselect("Show types", options=present, default=present)
    shown = table[table["Type"].isin(pick)] if pick else table
    st.dataframe(
        shown[["Assignment", "Type", "Submissions", "Average %"]],
        use_container_width=True, hide_index=True,
    )
    st.download_button(
        "⬇️ Download this table (CSV)",
        shown[["Assignment", "Type", "Submissions", "Average %"]].to_csv(index=False).encode(),
        file_name=f"course_{course_id}_activities.csv",
        mime="text/csv",
    )

    st.caption(
        f"Source: {'published data in data/' if ex.using_bundle(course_id) else 'local Canvas report cache'}"
        f" · Canvas course {course_id} · {len(table)} activities."
    )
