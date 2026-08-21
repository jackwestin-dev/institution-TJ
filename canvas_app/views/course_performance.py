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
from .. import sessions as sess

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

# Rendered inside a styled <div>, so these use HTML tags — markdown asterisks
# would come out literally.
TYPE_MEANING = {
    "Pre-Class Quiz":     "Taken <b>before</b> the session, to check what students already knew.",
    "Homework":           "Taken <b>after</b> the session, graded on correctness. The most informative score.",
    "Participation Task": "Completed <b>during</b> the session.",
    "Survey":             "Forms and score-reporting. Ungraded, so no accuracy figure.",
    "Other":              "Anything that doesn't fit the categories above.",
}

# The three that make up a teaching cycle, in the order students meet them.
CYCLE = ["Pre-Class Quiz", "Participation Task", "Homework"]


def _render_topic_detail(course_id: int, table: pd.DataFrame) -> None:
    """
    One topic at a time, across the three activities that make up its session.

    Reading a single topic end to end — what students knew going in, what they
    did in the room, how they scored on the follow-up — is far more legible than
    a cohort average across thirty unrelated subjects.
    """
    work = table[table["Type"].isin(CYCLE)].copy()
    if work.empty:
        return
    work["Topic"] = work["Assignment"].map(ex.topic_of)
    work = work[work["Topic"].astype(bool)]

    # Only topics that actually run more than one kind of activity are worth a
    # breakdown; a lone homework has nothing to compare against.
    counts = work.groupby("Topic")["Type"].nunique()
    topics = sorted(counts[counts >= 2].index)
    if not topics:
        return

    st.markdown("### One topic at a time")
    st.caption(
        "Each teaching topic runs up to three activities. Pick one to see how the "
        "cohort did at each stage of that session."
    )

    def _label(topic: str) -> str:
        rows = work[work["Topic"] == topic]
        longest = max(rows["Assignment"], key=len)
        for suffix in (" Homework", " Participation Task", " - Pre-Class Quiz"):
            longest = longest.replace(suffix, "")
        return longest.strip(" -") or topic.title()

    default = next((i for i, t in enumerate(topics) if "acid" in t), 0)
    topic = st.selectbox(
        "Topic", options=topics, index=default, format_func=_label,
        help="Only topics with more than one activity are listed.",
    )

    rows = work[work["Topic"] == topic]
    by_type = {r["Type"]: r for _, r in rows.iterrows()}

    cols = st.columns(len(CYCLE))
    for col, activity in zip(cols, CYCLE):
        row = by_type.get(activity)
        if row is None:
            col.metric(activity, "—", help="No activity of this type for this topic.")
            continue
        avg = row["Average %"]
        col.metric(
            activity,
            f"{avg:.0f}%" if pd.notna(avg) else "not scored",
            help=f"{int(row['Submissions'])} students submitted “{row['Assignment']}”.",
        )

    plot_rows = [
        {"Activity": a, "Average %": by_type[a]["Average %"],
         "Submissions": int(by_type[a]["Submissions"]),
         "Assignment": by_type[a]["Assignment"]}
        for a in CYCLE
        if a in by_type and pd.notna(by_type[a]["Average %"])
    ]
    if plot_rows:
        pdf = pd.DataFrame(plot_rows)
        fig = go.Figure(go.Bar(
            x=pdf["Activity"], y=pdf["Average %"],
            marker_color=[TYPE_COLOR.get(a, jw.GRAY_400) for a in pdf["Activity"]],
            text=[f"{v:.0f}%" for v in pdf["Average %"]], textposition="outside",
            customdata=pdf[["Submissions", "Assignment"]].values,
            hovertemplate="%{customdata[1]}<br>%{y:.1f}% average<br>"
                          "%{customdata[0]} students<extra></extra>",
        ))
        fig.update_layout(**jw.plotly_layout(
            title=_label(topic), height=360, yaxis_range=[0, 108],
            yaxis_title="Average score %", xaxis_title="",
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Pre-class and homework are graded on correctness and are comparable to "
        "each other. The participation task is marked for taking part, so its "
        "score sits higher and measures something different."
    )
    st.dataframe(
        rows[["Assignment", "Type", "Submissions", "Average %"]]
        .sort_values("Type", key=lambda s: s.map({t: i for i, t in enumerate(CYCLE)})),
        use_container_width=True, hide_index=True,
    )


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
        due = item.get("due_at") or ""
        rows.append({
            "Assignment":  item["title"],
            "Type":        item["item_type"],
            "Submissions": len(submitters),
            "Average %":   round(sum(values) / len(values), 1) if values else None,
            "due_at":      due,
            "Session":     sess.label(course_id, due),
            "assignment_id": aid,
        })
    table = pd.DataFrame(rows).sort_values(["due_at", "Assignment"]).reset_index(drop=True)
    # An activity whose deadline has not arrived is still collecting submissions,
    # so its participation is a partial count rather than a result.
    due_stamp = pd.to_datetime(table["due_at"], utc=True, errors="coerce")
    table["Still open"] = due_stamp.notna() & (due_stamp > pd.Timestamp.now(tz="UTC"))
    return table


def _scope_controls(course_id: int, table: pd.DataFrame) -> pd.DataFrame:
    """Session picker and the still-open exclusion. Returns the filtered table."""
    names = sess.present(course_id, table["due_at"])
    open_n = int(table["Still open"].sum())

    if len(names) > 1:
        st.markdown("### Which stretch of the course")
        st.caption(
            "This course shell runs more than one teaching session. They cover "
            "different material to different students, so the numbers below are "
            "kept separate rather than averaged across the join."
        )
        left, right = st.columns([3, 2])
        with left:
            choice = st.radio(
                "Session", ["All sessions"] + names, horizontal=True,
                label_visibility="collapsed",
            )
        with right:
            hide_open = st.checkbox(
                f"Exclude {open_n} activity(ies) not due yet", value=True,
                disabled=not open_n,
                help="Still-open activities have only some of their submissions "
                     "in, so they understate participation.",
            ) if open_n else True
        if choice != "All sessions":
            table = table[table["Session"] == choice]
    else:
        hide_open = st.checkbox(
            f"Exclude {open_n} activity(ies) not due yet", value=True,
            help="Still-open activities have only some of their submissions in.",
        ) if open_n else True

    if hide_open and open_n:
        excluded = ", ".join(table.loc[table["Still open"], "Assignment"])
        table = table[~table["Still open"]]
        if excluded:
            st.caption(f"Not due yet, left out: {excluded}")
    return table.reset_index(drop=True)


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

    st.divider()

    table = _scope_controls(course_id, table)
    if table.empty:
        st.info("Nothing to show for this selection.")
        return
    shown_sessions = sess.present(course_id, table["due_at"])
    graded = table[table["Average %"].notna()]
    n_students = 0
    for aid in table["assignment_id"]:
        n_students = max(n_students, len(ex.course_submitters(course_id, aid)))

    st.divider()

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

    st.divider()

    # ── One topic, all three activity types ───────────────────────────────────
    _render_topic_detail(course_id, table)

    st.divider()

    # ── Accuracy by type ──────────────────────────────────────────────────────
    st.markdown("### Average score by activity type")
    st.caption(
        "Each bar is the average of every graded activity of that type. Only the "
        "students who submitted are counted."
    )
    if len(shown_sessions) > 1:
        # Two sessions in view: put them side by side per type rather than
        # collapsing them into one bar that belongs to neither.
        st.caption(
            "Bars are grouped by session, so a type that got easier or harder "
            "between them is visible instead of averaged away."
        )
        session_colors = sess.colors(course_id)
        grouped = (graded.groupby(["Type", "Session"])["Average %"].mean()
                   .round(1).reset_index())
        fig = go.Figure()
        for name in shown_sessions:
            part = grouped[grouped["Session"] == name].set_index("Type").reindex(present)
            fig.add_trace(go.Bar(
                name=name, x=present, y=part["Average %"],
                marker_color=session_colors.get(name, jw.GRAY_400),
                text=[f"{v:.0f}%" if pd.notna(v) else "" for v in part["Average %"]],
                textposition="outside",
                hovertemplate="%{x} · " + name + "<br>average %{y:.1f}%<extra></extra>",
            ))
        fig.update_layout(**jw.plotly_layout(
            height=380, barmode="group", yaxis_range=[0, 108],
            yaxis_title="Average score %", xaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        ))
        st.plotly_chart(fig, use_container_width=True)
    else:
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
        # Mark where one session ends and the next begins, so the gap is not read
        # as a lull in a single continuous course.
        span = dated["Date"]
        for stamp, name in sess.boundaries(course_id):
            if name not in shown_sessions or not (span.min() <= stamp <= span.max()):
                continue
            fig_t.add_vline(
                x=stamp.timestamp() * 1000, line_dash="dot", line_width=2,
                line_color=sess.colors(course_id).get(name, jw.GRAY_400),
                annotation_text=f"{name} begins", annotation_position="top left",
                annotation_font_color=sess.colors(course_id).get(name, jw.GRAY_400),
            )
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
        view = topics.head(20).copy()
        # Every row here is a homework, so repeating the word on all of them
        # spends label width on nothing and pushes the real topic off the end.
        view["Label"] = (
            view["Topic"].str.replace(r"\s*Homework\s*$", "", regex=True)
                         .str.strip(" -–—,")
                         .str.slice(0, 44)
        )
        fig_p = go.Figure()
        for _, row in view.iterrows():
            fig_p.add_trace(go.Scatter(
                x=[row["Pre %"], row["Post %"]], y=[row["Label"], row["Label"]],
                mode="lines", line=dict(color=jw.GRAY_200, width=2),
                showlegend=False, hoverinfo="skip"))
        for name, color, col in (("Pre-class quiz", jw.VIOLET_300, "Pre %"),
                                 ("Homework", jw.VIOLET_600, "Post %")):
            fig_p.add_trace(go.Scatter(
                x=view[col], y=view["Label"], mode="markers", name=name,
                marker=dict(size=10, color=color, line=dict(color=jw.WHITE, width=2)),
                customdata=view["Students"],
                hovertemplate="%{y}<br>" + name + ": %{x:.1f}%<br>%{customdata} students<extra></extra>"))
        fig_p.update_layout(**jw.plotly_layout(
            height=max(360, len(view) * 26 + 150), xaxis_title="Cohort average %",
            xaxis_range=[0, 105], yaxis_title=None,
            yaxis=dict(categoryorder="array", categoryarray=view["Label"].tolist()[::-1],
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
    columns = ["Assignment", "Type", "Submissions", "Average %"]
    if len(shown_sessions) > 1:
        columns.insert(2, "Session")
    st.dataframe(shown[columns], use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download this table (CSV)",
        shown[columns].to_csv(index=False).encode(),
        file_name=f"course_{course_id}_activities.csv",
        mime="text/csv",
    )

    st.caption(
        f"Source: {'published data in data/' if ex.using_bundle(course_id) else 'local Canvas report cache'}"
        f" · Canvas course {course_id} · {len(table)} activities."
    )
