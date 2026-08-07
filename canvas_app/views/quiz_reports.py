import io


import streamlit as st
import pandas as pd
import plotly.express as px
from ..canvas_api import CanvasAPI
from .. import jw_theme as jw
from .. import reports_cache as _rc
from ..config import secret as _secret


# page_config and global CSS are set once in the app.py router

# ─── Cached API helpers ──────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _courses(url: str, token: str) -> list:
    return CanvasAPI(url, token).get_courses()

@st.cache_data(ttl=300, show_spinner=False)
def _quizzes(url: str, token: str, course_id: int) -> list:
    return CanvasAPI(url, token).get_quizzes(course_id)

@st.cache_data(ttl=300, show_spinner=False)
def _submissions(url: str, token: str, course_id: int, quiz_id: int, quiz_type: str = "classic") -> tuple:
    return CanvasAPI(url, token).get_quiz_submissions(course_id, quiz_id, quiz_type)

@st.cache_data(ttl=300, show_spinner=False)
def _students(url: str, token: str, course_id: int) -> dict:
    return CanvasAPI(url, token).get_students(course_id)

@st.cache_data(ttl=300, show_spinner=False)
def _statistics(url: str, token: str, course_id: int, quiz_id: int):
    return CanvasAPI(url, token).get_quiz_statistics(course_id, quiz_id)

@st.cache_data(ttl=300, show_spinner=False)
def _modules(url: str, token: str, course_id: int) -> list:
    return CanvasAPI(url, token).get_modules(course_id)


# ─── Quiz type classifier ────────────────────────────────────────────────────

import re as _re

def _classify_quiz_type(title: str) -> str:
    t = title.lower()
    if _re.search(r'pre[-\s]?quiz|pre[-\s]?test|pretest|pre[-\s]?class', t):
        return "Pre-Quiz"
    if _re.search(r'\bsurvey\b', t):
        return "Survey"
    if _re.search(r'\bhomework\b|\bhw\b', t):
        return "Homework"
    if _re.search(r'\bparticipation\b', t):
        return "Participation"
    if _re.search(r'\bexam\b|\bmidterm\b|\bfinal\b', t):
        return "Exam"
    if _re.search(r'\bquiz\b', t):
        return "Quiz"
    return "Assignment"

_TYPE_ORDER = ["Pre-Quiz", "Survey", "Quiz", "Participation", "Homework", "Exam", "Assignment"]
_TYPE_COLOR = {
    "Pre-Quiz":      jw.VIOLET_300,
    "Survey":        jw.AMBER_500,
    "Quiz":          jw.VIOLET_600,
    "Participation": jw.TEAL_500,
    "Homework":      jw.SUCCESS,
    "Exam":          jw.DANGER,
    "Assignment":    jw.GRAY_400,
}

# ─── CSV parsing helper ───────────────────────────────────────────────────────

# Lives in score_parsing.py so the Exam Growth page can share it without
# importing this page (which would re-run this script).
from ..score_parsing import parse_score_csv as _parse_score_csv


def _extract_essay_responses(uploaded_file) -> "pd.DataFrame | None":
    """
    Extract essay question responses from a Canvas New Quizzes Student Analysis CSV.
    Returns a DataFrame with columns [Student, <question1_text>, <question2_text>, ...]
    or None if no essay questions are found.

    The CSV has a wide format: one row per student, with groups of columns
    (ItemID, ItemType, <question text>, EarnedPoints, Status) for each question.
    We look for groups where ItemType == "essay".
    """
    import io, re
    import html as html_lib
    try:
        if hasattr(uploaded_file, "read"):
            raw = uploaded_file.read()
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
        else:
            raw = uploaded_file

        df = pd.read_csv(io.BytesIO(raw) if isinstance(raw, bytes) else io.StringIO(raw))
        df.columns = [str(c).strip() for c in df.columns]

        # Find the Name column
        name_col = next(
            (c for c in df.columns if c.lower().replace(" ", "") in ("name", "student", "studentname")),
            df.columns[0],
        )

        # Identify ItemType columns (they repeat as "ItemType", "ItemType.1", "ItemType.2", ...)
        item_type_cols = [c for c in df.columns if re.match(r"^ItemType(\.\d+)?$", c)]

        essay_questions = {}  # {question_col: display_label}
        for itcol in item_type_cols:
            # The question text column is immediately after ItemType in the CSV
            idx = df.columns.tolist().index(itcol)
            if idx + 1 >= len(df.columns):
                continue
            question_col = df.columns[idx + 1]
            # Check if any student has "essay" in this ItemType column
            types = df[itcol].dropna().str.lower().unique()
            if any("essay" in t or "short" in t or "text_entry" in t for t in types):
                # Truncate long question text for the label
                label = re.sub(r"<[^>]+>", "", question_col)  # strip HTML tags
                label = html_lib.unescape(label).strip()
                label = label[:80] + "…" if len(label) > 80 else label
                essay_questions[question_col] = label

        if not essay_questions:
            return None

        result = df[[name_col] + list(essay_questions.keys())].copy()
        result.columns = ["Student"] + list(essay_questions.values())
        # Strip HTML tags from student responses
        for col in result.columns[1:]:
            result[col] = result[col].fillna("").astype(str).apply(
                lambda v: html_lib.unescape(re.sub(r"<[^>]+>", "", v)).strip()
            )
        return result.reset_index(drop=True)
    except Exception:
        return None


# ─── Essay tab renderer (defined before use) ─────────────────────────────────

def _render_essay_tab(
    backend: str,
    doc_url: str,
    quiz_id: int,
    quiz_name: str,
    anthropic_key: str = "",
    gemini_key: str = "",
) -> None:
    """
    backend: "keyword" | "gemini" | "anthropic"
    """
    from ..essay_checker import (
        fetch_google_doc,
        parse_answer_guide_keyword,
        concept_check_keyword,
    )

    st.subheader("📝 Essay Review")

    # Backend-specific imports and validation
    if backend == "anthropic":
        if not anthropic_key:
            st.info("Enter your **Anthropic API Key** in the sidebar to enable Claude concept checking.")
            return
        import anthropic as _anthropic
        from ..essay_checker import parse_answer_guide, concept_check
        _client = _anthropic.Anthropic(api_key=anthropic_key)
    elif backend == "gemini":
        if not gemini_key:
            st.info(
                "Enter your **Google Gemini API Key** in the sidebar.\n\n"
                "Get a free key at [aistudio.google.com](https://aistudio.google.com) "
                "— no credit card required, just a Google account."
            )
            return
        try:
            from google import genai  # noqa: F401
        except ImportError:
            st.error(
                "The `google-genai` package is not installed. "
                "Run: `pip install google-genai` then restart the app."
            )
            return
        from ..essay_checker import parse_answer_guide_gemini, concept_check_gemini

    # ── Step 1: Answer Guide ──────────────────────────────────────────────────
    st.markdown("#### Step 1 — Answer Guide")

    answer_guide: dict = {}
    if not doc_url:
        st.info("Paste a public Google Doc URL in the sidebar (Answer Guide field) to load the essay guide.")
    else:
        # Cache key includes backend so switching backends re-parses
        guide_key = f"guide_{backend}_{doc_url}"
        if guide_key not in st.session_state:
            with st.spinner("Fetching Google Doc..."):
                try:
                    doc_text = fetch_google_doc(doc_url)
                except PermissionError as e:
                    st.error(str(e))
                    st.session_state[guide_key] = {}
                    doc_text = ""
                except Exception as e:
                    st.error(f"Could not fetch document: {e}")
                    st.session_state[guide_key] = {}
                    doc_text = ""

            if doc_text:
                try:
                    if backend == "anthropic":
                        with st.spinner("Parsing answer guide with Claude..."):
                            st.session_state[guide_key] = parse_answer_guide(doc_text, _client)
                    elif backend == "gemini":
                        with st.spinner("Parsing answer guide with Gemini..."):
                            st.session_state[guide_key] = parse_answer_guide_gemini(doc_text, gemini_key)
                    else:
                        # Keyword mode: instant, no API
                        st.session_state[guide_key] = parse_answer_guide_keyword(doc_text)
                        # Values are lists of concepts; join for display compatibility
                        parsed = st.session_state[guide_key]
                        st.session_state[guide_key] = {
                            k: "; ".join(v) if isinstance(v, list) else v
                            for k, v in parsed.items()
                        }
                        # Also store raw lists for keyword matching
                        st.session_state[guide_key + "_lists"] = parsed
                except Exception as e:
                    st.error(f"Could not parse answer guide: {e}")
                    st.session_state[guide_key] = {}

        answer_guide = st.session_state.get(guide_key, {})

        if answer_guide:
            st.success(f"Answer guide loaded — {len(answer_guide)} question(s) found.")
            with st.expander("View parsed answer guide"):
                for qlabel, gtext in answer_guide.items():
                    st.markdown(f"**{qlabel}:** {gtext}")
        else:
            st.warning("No questions could be parsed from the document.")

        if st.button("🔄 Reload answer guide", key=f"reload_guide_{quiz_id}"):
            for k in list(st.session_state.keys()):
                if k.startswith("guide_"):
                    del st.session_state[k]
            st.rerun()

    # ── Step 2: Student Responses ─────────────────────────────────────────────
    st.markdown("#### Step 2 — Student Essay Responses")

    resp_df = None
    resp_source = "auto"
    fetched_csv_key = f"fetched_csv_{quiz_id}"
    if fetched_csv_key in st.session_state:
        auto_resp = _extract_essay_responses(st.session_state[fetched_csv_key])
        if auto_resp is not None and len(auto_resp.columns) > 1:
            st.success(
                f"Found {len(auto_resp.columns) - 1} essay question(s) in the auto-fetched report."
            )
            with st.expander("Preview auto-loaded responses"):
                st.dataframe(auto_resp.head(5), use_container_width=True, hide_index=True)
            resp_df = auto_resp

    if resp_df is None:
        st.markdown(
            "No essay questions found in the auto-fetched report, or the report hasn't been "
            "fetched yet. Upload a CSV with one row per student and one column per essay question:"
        )
        n_q = max(len(answer_guide), 2)
        q_labels = list(answer_guide.keys()) if answer_guide else [f"Q{i+1}" for i in range(n_q)]
        template_df = pd.DataFrame(
            [["Jane Smith"] + ["Student answer here..."] * len(q_labels)],
            columns=["Student"] + q_labels,
        )
        st.download_button(
            "Download response template",
            template_df.to_csv(index=False).encode(),
            file_name="essay_responses_template.csv",
            mime="text/csv",
            key=f"tmpl_{quiz_id}",
        )
        responses_file = st.file_uploader(
            "Upload student essay responses (CSV)",
            type=["csv"],
            key=f"essay_csv_{quiz_id}",
        )
        if responses_file is None:
            return

        resp_source = "upload"
        try:
            resp_df = pd.read_csv(responses_file)
            resp_df.columns = [c.strip() for c in resp_df.columns]
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

    name_col = next(
        (c for c in resp_df.columns if c.lower() in ("student", "name", "student name")),
        resp_df.columns[0] if len(resp_df.columns) else None,
    )
    if name_col is None:
        st.error("CSV must have a 'Student' column.")
        return

    q_cols = [c for c in resp_df.columns if c != name_col]
    if not q_cols:
        st.error("CSV must have at least one question column beyond the Student column.")
        return

    st.success(f"Loaded {len(resp_df)} student responses, {len(q_cols)} question column(s).")

    # ── Step 3: Concept Checking ──────────────────────────────────────────────
    backend_label = {"keyword": "Keyword Matching (no API key)", "gemini": "Google Gemini", "anthropic": "Anthropic Claude"}
    backend_color = {"keyword": jw.TEAL_500, "gemini": jw.AMBER_500, "anthropic": jw.VIOLET_600}
    st.markdown(
        f"#### Step 3 — Concept Checking"
        f"<span style='margin-left:10px; padding:3px 10px; border-radius:12px; "
        f"background:{backend_color.get(backend, jw.GRAY_400)}22; "
        f"color:{backend_color.get(backend, jw.GRAY_400)}; font-size:0.85em; font-weight:600'>"
        f"▶ {backend_label.get(backend, backend)}</span>",
        unsafe_allow_html=True,
    )

    if not answer_guide:
        st.warning("Load an answer guide (Step 1) before running concept checks.")
        return

    _resp_name = getattr(responses_file, "name", resp_source) if resp_source == "upload" else "auto"
    run_key = f"essay_results_{quiz_id}_{backend}_{_resp_name}_{len(resp_df)}"

    # Show guide-to-question mapping so user can verify before running
    guide_keys = list(answer_guide.keys())

    def _find_guide_match(q_col: str, q_idx: int) -> "str | None":
        if q_col in answer_guide:
            return q_col
        q_up = q_col.upper()
        for ak in answer_guide:
            if q_up.startswith(ak.upper()) or ak.upper().startswith(q_up):
                return ak
        if q_idx < len(guide_keys):
            return guide_keys[q_idx]
        return None

    col_to_guide = {q_col: _find_guide_match(q_col, i) for i, q_col in enumerate(q_cols)}

    n_matched = sum(1 for gm in col_to_guide.values() if gm)
    n_skipped = sum(1 for gm in col_to_guide.values() if not gm)
    with st.expander(
        f"Question → Guide mapping — {n_matched} matched, {n_skipped} skipped (no guide entry)",
        expanded=True,
    ):
        for q_col, gm in col_to_guide.items():
            match_type = "exact" if q_col in answer_guide else (
                "prefix" if gm and any(
                    q_col.upper().startswith(ak.upper()) or ak.upper().startswith(q_col.upper())
                    for ak in answer_guide
                ) else ("positional" if gm else "—")
            )
            if gm:
                guide_text = answer_guide[gm]
                st.markdown(f"✅ **{q_col[:70]}** → **{gm}** `{match_type}`")
                st.caption(f"Concepts: {guide_text[:150]}{'…' if len(guide_text) > 150 else ''}")
            else:
                st.markdown(f"⏭️ ~~{q_col[:70]}~~ — _no guide entry, excluded from analysis_")

    col_run, col_clear = st.columns([1, 1])
    run_clicked = col_run.button("Run concept checks", type="primary", key=f"run_{quiz_id}")
    clear_clicked = col_clear.button("Clear & re-run", key=f"clear_{quiz_id}")

    if clear_clicked and run_key in st.session_state:
        del st.session_state[run_key]
        st.rerun()

    if run_clicked and run_key not in st.session_state:
        results = []
        total_calls = len(resp_df) * len(q_cols)
        progress = st.progress(0, text="Running concept checks...")
        call_count = 0

        # For keyword mode, retrieve raw concept lists if available
        guide_lists = st.session_state.get(f"guide_{backend}_{doc_url}_lists", {})

        for _, row in resp_df.iterrows():
            student_name = str(row[name_col])
            for q_col in q_cols:
                guide_match = col_to_guide[q_col]
                student_resp = str(row.get(q_col, ""))

                if guide_match is None:
                    continue  # no guide entry for this question — skip it
                else:
                    try:
                        if backend == "keyword":
                            concepts = guide_lists.get(
                                guide_match,
                                [c.strip() for c in answer_guide[guide_match].split(";") if c.strip()],
                            )
                            chk = concept_check_keyword(guide_match, concepts, student_resp)
                        elif backend == "gemini":
                            chk = concept_check_gemini(
                                guide_match, answer_guide[guide_match], student_resp, gemini_key
                            )
                        else:
                            chk = concept_check(
                                guide_match, answer_guide[guide_match], student_resp, _client
                            )

                        results.append({
                            "Student":    student_name,
                            "Question":   q_col,
                            "Response":   student_resp[:200],
                            "Coverage %": chk.get("coverage_pct"),
                            "Covered":    "; ".join(chk.get("covered", [])),
                            "Missing":    "; ".join(chk.get("missing", [])),
                            "Feedback":   chk.get("feedback", ""),
                        })
                    except Exception as e:
                        results.append({
                            "Student":    student_name,
                            "Question":   q_col,
                            "Response":   student_resp[:200],
                            "Coverage %": None,
                            "Covered":    "",
                            "Missing":    "",
                            "Feedback":   f"Error: {e}",
                        })

                call_count += 1
                progress.progress(call_count / total_calls, text=f"{student_name} — {q_col}")

        progress.empty()
        st.session_state[run_key] = results

    if run_key in st.session_state:
        results = st.session_state[run_key]
        results_df = pd.DataFrame(results)

        numeric = results_df[results_df["Coverage %"].notna()].copy()
        if not numeric.empty:
            avg_by_q = numeric.groupby("Question")["Coverage %"].mean().reset_index()
            fig = px.bar(
                avg_by_q, x="Question", y="Coverage %",
                color="Coverage %",
                color_continuous_scale=[[0, jw.DANGER], [0.5, jw.AMBER_500], [1, jw.SUCCESS]],
                range_color=[0, 100],
                title="Average Concept Coverage by Question",
                text="Coverage %",
            )
            fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            fig.update_layout(**jw.plotly_layout())
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(results_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download results",
            results_df.to_csv(index=False).encode(),
            file_name=f"{quiz_name}_essay_results.csv",
            mime="text/csv",
            key=f"dl_results_{quiz_id}",
        )


# ─── Trends tab renderer ─────────────────────────────────────────────────────

def _render_trends_tab(
    canvas_url: str,
    token: str,
    course_id: int,
    quizzes: list,
    pass_threshold: float,
    excluded_ids: "set | None" = None,
) -> None:
    st.subheader("Trends Over Time")

    excluded_ids = excluded_ids or set()
    # Build a lookup from assignment_id → quiz metadata (title, due_at)
    quiz_meta = {q["id"]: q for q in quizzes if q.get("_type") == "new" and q["id"] not in excluded_ids}

    # Load all cached quiz CSVs for this course (excluding filtered quizzes)
    cached = [c for c in _rc.cached_for_course(course_id) if c["assignment_id"] not in excluded_ids]

    if not cached:
        st.info(
            "No reports are cached yet. Use the **Report Cache** section above to sync reports, "
            "then come back here to see trends."
        )
        return

    total_students = len(_students(canvas_url, token, course_id))

    trend_rows = []
    for entry in cached:
        aid = entry["assignment_id"]
        csv_bytes = _rc.get_cached_csv(course_id, aid)
        if not csv_bytes:
            continue

        score_df, pts = _parse_score_csv(io.BytesIO(csv_bytes))
        if score_df is None or pts is None or pts == 0:
            continue

        qmeta = quiz_meta.get(aid, {})
        title = qmeta.get("title") or entry.get("title") or str(aid)
        due_raw = entry.get("due_at") or qmeta.get("due_at") or qmeta.get("created_at") or ""

        n_submitted = len(score_df)
        avg_pct = round(score_df["score"].mean() / pts * 100, 1)
        participation_pct = round(n_submitted / total_students * 100, 1) if total_students else None
        pass_pct = round((score_df["score"] / pts >= pass_threshold / 100).mean() * 100, 1)

        trend_rows.append({
            "Quiz":             title[:45],
            "Date":             pd.to_datetime(due_raw, utc=True, errors="coerce") if due_raw else pd.NaT,
            "Participation %":  participation_pct,
            "Avg Score %":      avg_pct,
            "Pass Rate %":      pass_pct,
            "Students":         n_submitted,
        })

    if not trend_rows:
        st.warning("Cached reports found but could not extract score data from them.")
        return

    trend_df = pd.DataFrame(trend_rows)

    # Quizzes without a date: fall back to alphabetical position
    has_date = trend_df["Date"].notna()
    trend_df = trend_df.sort_values(
        ["Date", "Quiz"], na_position="last"
    ).reset_index(drop=True)

    if not has_date.any():
        st.caption("No due dates found — quizzes sorted alphabetically.")

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Quizzes with data", len(trend_df))
    m2.metric("Avg participation", f"{trend_df['Participation %'].mean():.1f}%")
    m3.metric("Avg score",         f"{trend_df['Avg Score %'].mean():.1f}%")
    m4.metric("Avg pass rate",     f"{trend_df['Pass Rate %'].mean():.1f}%")

    st.divider()

    # Chart 1: Participation over time
    part_df = trend_df.dropna(subset=["Participation %"])
    x_col = "Date" if has_date.any() else "Quiz"

    fig1 = px.line(
        part_df, x=x_col, y="Participation %",
        hover_name="Quiz",
        title="Participation Rate Over Time",
        markers=True,
        color_discrete_sequence=[jw.VIOLET_600],
        labels={"Date": "Quiz Due Date"},
    )
    fig1.add_hline(y=80, line_dash="dot", line_color=jw.GRAY_200,
                   annotation_text="80%", annotation_font_color=jw.GRAY_400)
    fig1.update_layout(**jw.plotly_layout(yaxis_range=[0, 105]))
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Accuracy and pass rate over time
    acc_df = trend_df.dropna(subset=["Avg Score %"])

    fig2 = px.line(
        acc_df, x=x_col, y=["Avg Score %", "Pass Rate %"],
        hover_name="Quiz",
        title="Score & Pass Rate Over Time",
        markers=True,
        color_discrete_map={
            "Avg Score %":  jw.SUCCESS,
            "Pass Rate %":  jw.VIOLET_600,
        },
        labels={"value": "%", "variable": "Metric", "Date": "Quiz Due Date"},
    )
    fig2.add_hline(
        y=pass_threshold, line_dash="dash", line_color=jw.DANGER,
        annotation_text=f"Pass threshold ({pass_threshold}%)",
        annotation_font_color=jw.DANGER,
    )
    fig2.update_layout(**jw.plotly_layout(yaxis_range=[0, 105]))
    st.plotly_chart(fig2, use_container_width=True)

    # Data table
    display_df = trend_df[["Quiz", "Date", "Students", "Participation %", "Avg Score %", "Pass Rate %"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d").where(display_df["Date"].notna(), "—")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download trends CSV",
        display_df.to_csv(index=False).encode(),
        file_name=f"course_{course_id}_trends.csv",
        mime="text/csv",
    )


def _render_module_tab(
    canvas_url: str,
    token: str,
    course_id: int,
    quizzes: list,
    excluded_ids: "set | None" = None,
) -> None:
    st.subheader("Module Comparison")
    excluded_ids = excluded_ids or set()

    with st.spinner("Loading modules from Canvas…"):
        try:
            modules = _modules(canvas_url, token, course_id)
        except Exception as exc:
            st.error(f"Could not load modules: {exc}")
            return

    if not modules:
        st.info("No modules found for this course.")
        return

    cached_ids = {c["assignment_id"] for c in _rc.cached_for_course(course_id)}
    quiz_id_to_meta = {q["id"]: q for q in quizzes if q.get("_type") == "new"}

    # Build module list restricted to cached, non-excluded assignments
    module_data = []
    for mod in modules:
        items = []
        for item in mod["assignments"]:
            aid = item["assignment_id"]
            if aid in excluded_ids or aid not in cached_ids:
                continue
            title = item.get("title") or quiz_id_to_meta.get(aid, {}).get("title", str(aid))
            qt = _classify_quiz_type(title)
            items.append({"assignment_id": aid, "title": title, "quiz_type": qt})
        if items:
            module_data.append({"id": mod["id"], "name": mod["name"], "items": items})

    if not module_data:
        st.info(
            "No cached reports found for any module assignments. "
            "Use the **Report Cache** section above to sync reports first."
        )
        return

    module_names = [m["name"] for m in module_data]
    selected_names = st.multiselect(
        "Select modules to compare",
        options=module_names,
        default=module_names[: min(3, len(module_names))],
    )
    if not selected_names:
        st.info("Select at least one module above.")
        return

    selected_modules = [m for m in module_data if m["name"] in selected_names]

    # Load score data for every assignment across selected modules
    all_items = [
        {**item, "module": mod["name"]}
        for mod in selected_modules
        for item in mod["items"]
    ]

    # student_matrix[student_name][assignment_id] = pct (0–100)
    student_matrix: dict = {}
    item_pts: dict = {}  # assignment_id → points_possible

    for item in all_items:
        aid = item["assignment_id"]
        if aid in item_pts:
            continue  # already loaded (shared across modules)
        csv_bytes = _rc.get_cached_csv(course_id, aid)
        if not csv_bytes:
            continue
        score_df, pts = _parse_score_csv(io.BytesIO(csv_bytes))
        if score_df is None or pts is None or pts == 0:
            continue
        item_pts[aid] = pts
        for _, row in score_df.iterrows():
            name = str(row["student"]).strip()
            if not name or name.lower() == "nan":
                continue
            pct = round(row["score"] / pts * 100, 1)
            student_matrix.setdefault(name, {})[aid] = pct

    if not student_matrix:
        st.warning("Could not extract score data from cached reports for the selected modules.")
        return

    # ── Chart 1: Average score by quiz type per module ────────────────────────
    st.markdown("### Avg Score by Quiz Type")

    bar_rows = []
    for mod in selected_modules:
        for item in mod["items"]:
            aid = item["assignment_id"]
            if aid not in item_pts:
                continue
            scores = [v[aid] for v in student_matrix.values() if aid in v]
            if not scores:
                continue
            bar_rows.append({
                "Module":      mod["name"],
                "Quiz Type":   item["quiz_type"],
                "Avg Score %": round(sum(scores) / len(scores), 1),
                "Title":       item["title"][:50],
                "N Students":  len(scores),
            })

    if bar_rows:
        bar_df = pd.DataFrame(bar_rows)
        bar_df["Quiz Type"] = pd.Categorical(
            bar_df["Quiz Type"], categories=_TYPE_ORDER, ordered=True
        )
        bar_df = bar_df.sort_values(["Module", "Quiz Type"])

        fig_bar = px.bar(
            bar_df,
            x="Quiz Type",
            y="Avg Score %",
            color="Quiz Type",
            barmode="group",
            facet_col="Module" if len(selected_names) > 1 else None,
            facet_col_wrap=2,
            color_discrete_map=_TYPE_COLOR,
            hover_data=["Title", "N Students"],
            title="Average Score % by Quiz Type per Module",
        )
        fig_bar.update_layout(**jw.plotly_layout(yaxis_range=[0, 105]))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ── Chart 2: Pre-Quiz vs Homework scatter per module ─────────────────────
    st.markdown("### Pre-Quiz → Homework Comparison")
    scatter_any = False
    for mod in selected_modules:
        pq_aids = [i["assignment_id"] for i in mod["items"]
                   if i["quiz_type"] == "Pre-Quiz" and i["assignment_id"] in item_pts]
        hw_aids = [i["assignment_id"] for i in mod["items"]
                   if i["quiz_type"] == "Homework" and i["assignment_id"] in item_pts]
        if not pq_aids or not hw_aids:
            continue
        scatter_any = True

        scat_rows = []
        for name, scores in student_matrix.items():
            pre_vals = [scores[a] for a in pq_aids if a in scores]
            hw_vals  = [scores[a] for a in hw_aids  if a in scores]
            if not pre_vals or not hw_vals:
                continue
            scat_rows.append({
                "Student":    name,
                "Pre-Quiz %": round(sum(pre_vals) / len(pre_vals), 1),
                "Homework %": round(sum(hw_vals)  / len(hw_vals),  1),
            })

        if scat_rows:
            scat_df = pd.DataFrame(scat_rows)
            fig_scat = px.scatter(
                scat_df,
                x="Pre-Quiz %",
                y="Homework %",
                hover_name="Student",
                title=f"Pre-Quiz → Homework: {mod['name']}",
                color_discrete_sequence=[jw.VIOLET_600],
            )
            fig_scat.add_shape(
                type="line", x0=0, y0=0, x1=100, y1=100,
                line={"dash": "dot", "color": jw.GRAY_400},
            )
            fig_scat.update_layout(**jw.plotly_layout(xaxis_range=[0, 105], yaxis_range=[0, 105]))
            st.plotly_chart(fig_scat, use_container_width=True)

    if not scatter_any:
        st.caption(
            "No selected modules have both Pre-Quiz and Homework reports cached. "
            "Sync more reports to enable this chart."
        )

    st.divider()

    # ── Individual student view ───────────────────────────────────────────────
    st.markdown("### Individual Student View")

    all_student_names = sorted(student_matrix.keys())
    selected_student = st.selectbox("Select student", options=all_student_names)

    if selected_student:
        stu_rows = []
        for mod in selected_modules:
            for item in mod["items"]:
                aid = item["assignment_id"]
                if aid not in item_pts:
                    continue
                pct = student_matrix.get(selected_student, {}).get(aid)
                stu_rows.append({
                    "Module":    mod["name"],
                    "Quiz Type": item["quiz_type"],
                    "Title":     item["title"][:50],
                    "Score %":   pct,
                    "Status":    f"{pct:.0f}%" if pct is not None else "Not submitted",
                })

        if stu_rows:
            stu_df = pd.DataFrame(stu_rows)
            stu_df["Quiz Type"] = pd.Categorical(
                stu_df["Quiz Type"], categories=_TYPE_ORDER, ordered=True
            )
            stu_df = stu_df.sort_values(["Module", "Quiz Type"]).reset_index(drop=True)

            scored = stu_df[stu_df["Score %"].notna()]
            if not scored.empty:
                fig_stu = px.bar(
                    scored,
                    x="Title",
                    y="Score %",
                    color="Quiz Type",
                    facet_col="Module" if len(selected_names) > 1 else None,
                    facet_col_wrap=2,
                    color_discrete_map=_TYPE_COLOR,
                    title=f"Scores for {selected_student}",
                )
                fig_stu.update_layout(**jw.plotly_layout(yaxis_range=[0, 105]))
                st.plotly_chart(fig_stu, use_container_width=True)

            st.dataframe(
                stu_df[["Module", "Quiz Type", "Title", "Status"]],
                use_container_width=True,
                hide_index=True,
            )


def render() -> None:
    # ─── Sidebar ─────────────────────────────────────────────────────────────────

    with st.sidebar:
        st.title("⚙️ Settings")
        canvas_url = st.text_input(
            "Canvas URL",
            value=_secret("CANVAS_URL"),
            placeholder="https://your-school.instructure.com",
        )
        token = st.text_input(
            "API Token",
            value=_secret("CANVAS_TOKEN"),
            type="password",
            help="Account → Settings → New Access Token",
        )
        pass_threshold = st.slider("Pass threshold (%)", 50, 95, 70, 5)

        st.divider()
        st.markdown("**📝 Essay Review**")

        essay_backend = st.radio(
            "Concept-check method",
            options=["keyword", "gemini", "anthropic"],
            format_func=lambda x: {
                "keyword":   "Keyword matching (no API key)",
                "gemini":    "Google Gemini (free API key)",
                "anthropic": "Anthropic Claude",
            }[x],
            index=0,
            help=(
                "**Keyword**: no AI, instant, checks if key terms appear in responses.\n"
                "**Gemini**: free AI (get key at aistudio.google.com with a Google account).\n"
                "**Anthropic**: most capable, requires console.anthropic.com account."
            ),
        )

        gemini_key = ""
        anthropic_key = ""

        if essay_backend == "gemini":
            gemini_key = st.text_input(
                "Gemini API Key",
                value=_secret("GEMINI_API_KEY"),
                type="password",
                help="Free key from aistudio.google.com — no credit card needed.",
            )
        elif essay_backend == "anthropic":
            anthropic_key = st.text_input(
                "Anthropic API Key",
                value=_secret("ANTHROPIC_API_KEY"),
                type="password",
                help="From console.anthropic.com.",
            )

        essay_doc_url = st.text_input(
            "Answer Guide (Google Doc URL)",
            placeholder="https://docs.google.com/document/d/...",
            help="Public Google Doc with expected key concepts per question.",
        )

        st.caption("Data refreshes every 5 minutes.")

    if not canvas_url or not token:
        st.markdown(jw.brand_header(), unsafe_allow_html=True)
        st.info("Enter your Canvas URL and API token in the sidebar to get started.")
        st.stop()

    # ─── Brand header ─────────────────────────────────────────────────────────────

    st.markdown(jw.brand_header(), unsafe_allow_html=True)

    # ─── Course selector ─────────────────────────────────────────────────────────

    with st.spinner("Loading courses…"):
        try:
            courses = _courses(canvas_url, token)
        except Exception as e:
            st.error(f"Could not connect to Canvas: {e}")
            st.stop()

    if not courses:
        st.warning("No teacher-enrolled courses found. Verify your token has Teacher access.")
        st.stop()

    course_map = {c["name"]: c["id"] for c in sorted(courses, key=lambda x: x.get("name", ""))}
    selected_course = st.selectbox("Course", list(course_map.keys()))
    course_id = course_map[selected_course]

    # ─── Quiz selector ────────────────────────────────────────────────────────────

    with st.spinner("Loading quizzes…"):
        try:
            quizzes = _quizzes(canvas_url, token, course_id)
        except Exception as e:
            st.error(f"Could not load quizzes: {e}")
            st.stop()

    if not quizzes:
        st.warning("No quizzes found in this course.")
        st.stop()

    quiz_map = {q["title"]: q for q in sorted(quizzes, key=lambda x: x.get("title", ""))}

    # Attach quiz type to each entry
    for _title, _q in quiz_map.items():
        _q.setdefault("_quiz_type", _classify_quiz_type(_title))

    # Quiz type filter
    _all_types_present = [t for t in _TYPE_ORDER if any(q["_quiz_type"] == t for q in quiz_map.values())]
    _type_filter_key = f"type_filter_{course_id}"
    _selected_types = st.multiselect(
        "Quiz types to show",
        options=_all_types_present,
        default=st.session_state.get(_type_filter_key, _all_types_present),
        key=f"type_filter_sel_{course_id}",
        help="Filter the quiz selector below by assignment type.",
    )
    st.session_state[_type_filter_key] = _selected_types

    _filtered_quiz_names = [
        title for title, q in quiz_map.items()
        if q["_quiz_type"] in _selected_types
    ]
    if not _filtered_quiz_names:
        st.warning("No quizzes match the selected types. Enable at least one type above.")
        st.stop()

    selected_quiz_name = st.selectbox("QUIZ", _filtered_quiz_names)
    quiz = quiz_map[selected_quiz_name]
    quiz_id   = quiz["id"]
    quiz_type = quiz.get("_type", "classic")
    raw_pts   = quiz.get("points_possible") or 0.0
    is_zero_point = (raw_pts == 0)

    st.divider()

    # ─── Quiz exclusion ───────────────────────────────────────────────────────────

    _excl_key = f"excluded_{course_id}"
    with st.expander("🚫 Exclude quizzes from analysis", expanded=False):
        st.caption("Excluded quizzes are hidden from the Trends tab and skipped during Report Cache sync.")
        all_quiz_names = sorted(quiz_map.keys())
        excluded_quiz_names = st.multiselect(
            "Select quizzes to exclude",
            options=all_quiz_names,
            default=st.session_state.get(_excl_key, []),
            key=f"excl_select_{course_id}",
        )
        st.session_state[_excl_key] = excluded_quiz_names

    excluded_ids = {quiz_map[n]["id"] for n in excluded_quiz_names if n in quiz_map}

    # ─── Report cache sync section ────────────────────────────────────────────────

    from datetime import datetime, timezone as _tz
    _now = datetime.now(_tz.utc)

    def _is_past_or_undated(q: dict) -> bool:
        due = q.get("due_at") or ""
        if not due:
            return True  # no due date → available now, include
        parsed = pd.to_datetime(due, utc=True, errors="coerce")
        return pd.isna(parsed) or parsed <= _now

    _lti_quizzes = [q for q in quizzes if q.get("_type") == "new" and q["id"] not in excluded_ids]
    _cached_ids   = {c["assignment_id"] for c in _rc.cached_for_course(course_id)}
    _missing      = [q for q in _lti_quizzes if q["id"] not in _cached_ids and _is_past_or_undated(q)]
    _n_cached     = len(_cached_ids)
    _n_total      = len(_lti_quizzes)

    with st.expander(
        f"📦 Report Cache — {_n_cached}/{_n_total} synced",
        expanded=(_n_cached == 0 and _n_total > 0),
    ):
        st.markdown(
            f"**{_n_cached}** of **{_n_total}** quiz reports are saved locally. "
            f"Cached reports load instantly and power the Trends tab."
        )
        if _missing:
            st.markdown(f"**{len(_missing)}** report(s) not yet downloaded.")
        else:
            st.success("All reports are up to date.")

        from ..report_fetcher import is_playwright_available as _pw_avail, fetch_quiz_report_csv as _fetch_csv
        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

        if _missing:
            if not _pw_avail():
                st.info(
                    "**Syncing runs locally, not here.** Report download drives a headless "
                    "Chromium through Playwright, which Streamlit Community Cloud can't "
                    "install — and its filesystem is wiped on restart, so a synced cache "
                    "wouldn't survive anyway.\n\n"
                    "On a local checkout:\n"
                    "```\npip install playwright\nplaywright install chromium\npython sync_reports.py\n```\n"
                    "Then rebuild the committed aggregate and push:\n"
                    "```\npython build_canvas_metrics.py\ngit add data/ && git commit -m 'Refresh Canvas metrics' && git push\n```",
                    icon="ℹ️",
                )
            else:
                _workers = st.slider("Parallel downloads", min_value=1, max_value=5, value=3,
                                     help="How many reports to download simultaneously. Higher = faster but heavier on your machine.",
                                     key="sync_workers")
                sync_clicked = st.button(
                    f"⬇️ Sync {len(_missing)} missing report(s)",
                    type="primary",
                    key="sync_all_btn",
                )
                if sync_clicked:
                    sync_bar  = st.progress(0, text="Starting parallel sync...")
                    sync_status = st.empty()
                    sync_errors = []
                    done_count  = [0]  # mutable for closure

                    def _fetch_one(q):
                        qname = q.get("title", str(q["id"]))
                        csv_bytes = _fetch_csv(
                            canvas_url=canvas_url,
                            api_token=token,
                            course_id=course_id,
                            assignment_id=q["id"],
                        )
                        _rc.save_csv(
                            course_id, q["id"], csv_bytes,
                            title=qname,
                            points_possible=q.get("points_possible"),
                            due_at=q.get("due_at", ""),
                        )
                        return qname, len(csv_bytes)

                    with ThreadPoolExecutor(max_workers=_workers) as _pool:
                        _futures = {_pool.submit(_fetch_one, q): q for q in _missing}
                        for _fut in _as_completed(_futures):
                            q = _futures[_fut]
                            done_count[0] += 1
                            pct = done_count[0] / len(_missing)
                            try:
                                qname, nbytes = _fut.result()
                                sync_bar.progress(pct, text=f"{done_count[0]}/{len(_missing)} — {qname} ({nbytes//1024} KB)")
                            except Exception as e:
                                qname = q.get("title", str(q["id"]))
                                sync_errors.append(f"{qname}: {e}")
                                sync_bar.progress(pct, text=f"{done_count[0]}/{len(_missing)} done")

                    sync_status.empty()
                    if sync_errors:
                        st.warning(f"Completed with {len(sync_errors)} error(s):\n" + "\n".join(sync_errors[:5]))
                    else:
                        st.success(f"Synced {len(_missing)} report(s) successfully.")
                    st.rerun()

        # ── Compiled CSV download ──────────────────────────────────────────────────
        if _cached_ids:
            st.divider()
            st.markdown("**Download compiled report**")
            all_cached = _rc.cached_for_course(course_id)
            quiz_meta_map = {q["id"]: q for q in quizzes}

            if st.button("Build compiled CSV", key="build_compiled"):
                compiled_rows = []
                for entry in all_cached:
                    aid = entry["assignment_id"]
                    if aid in excluded_ids:
                        continue
                    csv_bytes = _rc.get_cached_csv(course_id, aid)
                    if not csv_bytes:
                        continue
                    score_df, pts = _parse_score_csv(io.BytesIO(csv_bytes))
                    if score_df is None:
                        continue
                    qmeta = quiz_meta_map.get(aid, {})
                    title = qmeta.get("title") or entry.get("title") or str(aid)
                    due = entry.get("due_at") or qmeta.get("due_at") or ""
                    due_str = pd.to_datetime(due, utc=True, errors="coerce")
                    due_str = due_str.strftime("%Y-%m-%d") if pd.notna(due_str) else ""
                    score_df = score_df.copy()
                    score_df["Quiz"]           = title
                    score_df["Due Date"]       = due_str
                    score_df["Points Possible"] = pts or ""
                    score_df["Score %"]        = (score_df["score"] / pts * 100).round(1) if pts else ""
                    score_df = score_df.rename(columns={"student": "Student", "score": "Score"})
                    score_df = score_df[["Student", "Quiz", "Due Date", "Score", "Points Possible", "Score %"]]
                    compiled_rows.append(score_df)

                if compiled_rows:
                    compiled_df = pd.concat(compiled_rows, ignore_index=True).sort_values(["Due Date", "Student"])
                    st.session_state["compiled_csv"] = compiled_df.to_csv(index=False).encode()
                    st.success(f"Built {len(compiled_df)} rows across {len(compiled_rows)} quiz(zes).")
                else:
                    st.warning("No score data found in cached reports.")

            if "compiled_csv" in st.session_state:
                st.download_button(
                    "⬇️ Download compiled CSV",
                    st.session_state["compiled_csv"],
                    file_name=f"course_{course_id}_all_scores.csv",
                    mime="text/csv",
                    key="dl_compiled",
                )

    # ─── Load submissions ─────────────────────────────────────────────────────────

    with st.spinner("Loading submissions…"):
        try:
            raw_subs, sub_users = _submissions(canvas_url, token, course_id, quiz_id, quiz_type)
        except Exception as e:
            st.error(f"Could not load submissions: {e}")
            st.stop()

    completed = [s for s in raw_subs if s.get("workflow_state") == "complete"]

    # ─── Zero-point quiz: explanation + CSV import ────────────────────────────────

    imported_df: "pd.DataFrame | None" = None
    imported_pts: "float | None" = None

    if is_zero_point and quiz_type == "new":
        # Auto-load from local cache if available
        if _rc.is_cached(course_id, quiz_id) and f"fetched_csv_{quiz_id}" not in st.session_state:
            _cached_bytes = _rc.get_cached_csv(course_id, quiz_id)
            if _cached_bytes:
                st.session_state[f"fetched_csv_{quiz_id}"] = _cached_bytes

        if f"fetched_csv_{quiz_id}" not in st.session_state:
            st.warning(
                "**Scores show as 0** — this quiz is set to **0 points** in the Canvas gradebook. "
                "The actual performance lives inside the New Quizzes tool.\n\n"
                "**To see actual scores:** fetch or upload the Student Analysis CSV below.",
                icon="ℹ️",
            )

        with st.expander(
            "📥 Get Actual Scores from New Quizzes",
            expanded=f"fetched_csv_{quiz_id}" not in st.session_state,
        ):
            from ..report_fetcher import is_playwright_available, fetch_quiz_report_csv

            # ── Auto-fetch via browser automation ──────────────────────────────────
            pw_ready = is_playwright_available()
            st.markdown("**Option 1 — Fetch automatically** (browser automation)")
            if not pw_ready:
                st.info(
                    "Auto-fetch needs Playwright, which isn't available here. On a local "
                    "checkout run `pip install playwright && playwright install chromium`. "
                    "On the deployed app, use **Option 2** below and upload the CSV by hand.",
                    icon="ℹ️",
                )
            else:
                fetch_col, clear_col = st.columns([2, 1])
                fetch_clicked = fetch_col.button(
                    "🤖 Fetch report from Canvas",
                    key=f"fetch_{quiz_id}",
                    type="primary",
                )
                if clear_col.button("🗑️ Clear fetched", key=f"clear_fetch_{quiz_id}"):
                    st.session_state.pop(f"fetched_csv_{quiz_id}", None)
                    st.rerun()

                if fetch_clicked:
                    # Check cache before launching browser
                    if _rc.is_cached(course_id, quiz_id):
                        _cached_bytes = _rc.get_cached_csv(course_id, quiz_id)
                        if _cached_bytes:
                            st.session_state[f"fetched_csv_{quiz_id}"] = _cached_bytes
                            st.info("Loaded from local cache (already downloaded).")
                            st.rerun()

                    status_box = st.empty()
                    msgs = []
                    def _log(m):
                        msgs.append(m)
                        status_box.info("\n\n".join(msgs))

                    try:
                        with st.spinner("Launching browser…"):
                            csv_bytes = fetch_quiz_report_csv(
                                canvas_url=canvas_url,
                                api_token=token,
                                course_id=course_id,
                                assignment_id=quiz_id,
                                status_callback=_log,
                            )
                        st.session_state[f"fetched_csv_{quiz_id}"] = csv_bytes
                        _rc.save_csv(
                            course_id, quiz_id, csv_bytes,
                            title=selected_quiz_name,
                            points_possible=raw_pts,
                            due_at=quiz.get("due_at", ""),
                        )
                        status_box.success("Report downloaded and saved to local cache.")
                        st.rerun()
                    except Exception as e:
                        status_box.error(f"Auto-fetch failed: {e}")

                if f"fetched_csv_{quiz_id}" in st.session_state:
                    csv_bytes = st.session_state[f"fetched_csv_{quiz_id}"]
                    fetched_df, fetched_pts = _parse_score_csv(io.BytesIO(csv_bytes))
                    if fetched_df is not None:
                        imported_df, imported_pts = fetched_df, fetched_pts
                        st.success(f"Using fetched report — {len(fetched_df)} students.")
                        st.download_button(
                            "⬇️ Save fetched CSV",
                            csv_bytes,
                            file_name=f"{selected_quiz_name}_report.csv",
                            mime="text/csv",
                            key=f"save_fetched_{quiz_id}",
                        )

            # ── Manual upload fallback ──────────────────────────────────────────────
            st.markdown("**Option 2 — Upload manually** (Canvas → open quiz → Reports → Student Analysis → Download)")
            uploaded = st.file_uploader("Upload CSV", type=["csv"], key=f"score_csv_{quiz_id}")
            if uploaded:
                imported_df, imported_pts = _parse_score_csv(uploaded)
                if imported_df is None:
                    st.error(
                        "Could not parse this CSV. Make sure it has a **Student** (or Name) column "
                        "and a **Score** (or Final Score) column."
                    )
                else:
                    st.success(f"Loaded {len(imported_df)} student scores.")

    # ─── Decide data source and build main DataFrame ──────────────────────────────

    PASS_COLOR = jw.SUCCESS
    FAIL_COLOR = jw.DANGER

    if imported_df is not None:
        points_possible = imported_pts or imported_df["score"].max() or 1
        df = imported_df.copy()
        df["pct"]    = (df["score"] / points_possible * 100).round(1)
        df["passed"] = df["pct"] >= pass_threshold
        data_source  = "csv"

    elif not is_zero_point:
        if not completed:
            st.warning("No completed submissions for this quiz yet.")
            st.stop()
        points_possible = raw_pts
        df = pd.DataFrame([
            {
                "student": sub_users.get(s["user_id"], str(s["user_id"])),
                "score":   (s.get("kept_score") if s.get("kept_score") is not None
                            else s.get("score") or 0),
                "attempt": s.get("attempt", 1),
            }
            for s in completed
        ])
        df["pct"]    = (df["score"] / points_possible * 100).round(1)
        df["passed"] = df["pct"] >= pass_threshold
        data_source  = "canvas"

    else:
        data_source = "completion"

    # ─── Completion mode ──────────────────────────────────────────────────────────

    if data_source == "completion":
        with st.spinner("Loading enrolled students…"):
            all_students = _students(canvas_url, token, course_id)

        submitted_ids = {s["user_id"] for s in completed}

        comp_rows = [
            {"student": name, "completed": uid in submitted_ids}
            for uid, name in all_students.items()
        ]
        comp_df = pd.DataFrame(comp_rows)
        total = len(comp_df)
        done  = int(comp_df["completed"].sum())

        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
            ["📋 Summary", "👤 Completion", "❓ Question Analysis", "📈 Cross-Quiz", "📝 Essay Review", "📉 Trends", "🗂️ Module Comparison"]
        )

        with tab1:
            st.subheader(f"Completion Summary — {selected_quiz_name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Enrolled Students", total)
            c2.metric("Completed",         done)
            c3.metric("Completion Rate",   f"{done / total * 100:.1f}%" if total else "—")

            fig = px.pie(
                names=["Completed", "Not Completed"],
                values=[done, total - done],
                color=["Completed", "Not Completed"],
                color_discrete_map={"Completed": jw.SUCCESS, "Not Completed": jw.DANGER},
                title="Quiz Completion",
            )
            fig.update_layout(**jw.plotly_layout())
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Student Completion Status")
            display = (
                comp_df[["student", "completed"]]
                .rename(columns={"student": "Student", "completed": "Completed"})
                .sort_values("Completed", ascending=False)
                .reset_index(drop=True)
            )
            display["Status"] = display["Completed"].map(
                {True: "✅ Completed", False: "❌ Not Completed"}
            )
            st.dataframe(display[["Student", "Status"]], use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download CSV",
                display[["Student", "Status"]].to_csv(index=False).encode(),
                file_name=f"{selected_quiz_name}_completion.csv",
                mime="text/csv",
            )

        with tab3:
            st.info(
                "Question-level analysis is not available for 0-point quizzes. "
                "Upload actual scores via the CSV import above to enable this view."
            )

        with tab4:
            st.info("Cross-quiz comparison requires non-zero point assignments or imported CSV scores.")

        with tab5:
            _render_essay_tab(
                backend=essay_backend,
                doc_url=essay_doc_url,
                quiz_id=quiz_id,
                quiz_name=selected_quiz_name,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
            )

        with tab6:
            _render_trends_tab(canvas_url, token, course_id, quizzes, pass_threshold, excluded_ids)

        with tab7:
            _render_module_tab(canvas_url, token, course_id, quizzes, excluded_ids)

        st.stop()

    # ─── Score-based views (Canvas API or CSV import) ─────────────────────────────

    if not len(df):
        st.warning("No score data available for this quiz.")
        st.stop()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["📋 Summary", "👤 Student Scores", "❓ Question Analysis", "📈 Cross-Quiz", "📝 Essay Review", "📉 Trends", "🗂️ Module Comparison"]
    )

    # ── Tab 1: Summary ────────────────────────────────────────────────────────────

    with tab1:
        st.subheader(f"Summary — {selected_quiz_name}")
        if data_source == "csv":
            st.caption(f"Scores imported from CSV · Points possible: {points_possible:.1f}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Students",     len(df))
        c2.metric("Avg Score",    f"{df['pct'].mean():.1f}%")
        c3.metric("Median Score", f"{df['pct'].median():.1f}%")
        c4.metric("Pass Rate",    f"{df['passed'].mean() * 100:.1f}%",
                  help=f"≥ {pass_threshold}% threshold")

        col_l, col_r = st.columns(2)
        col_l.metric("Highest", f"{df['score'].max():.1f} / {points_possible:.1f}")
        col_r.metric("Lowest",  f"{df['score'].min():.1f} / {points_possible:.1f}")

        fig = px.histogram(
            df, x="pct", nbins=20,
            labels={"pct": "Score (%)"},
            title="Score Distribution",
            color_discrete_sequence=[jw.VIOLET_600],
        )
        fig.add_vline(
            x=pass_threshold, line_dash="dash", line_color=jw.DANGER,
            annotation_text=f"Pass threshold ({pass_threshold}%)",
            annotation_position="top right",
            annotation_font_color=jw.DANGER,
        )
        fig.update_layout(**jw.plotly_layout())
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: Student Scores ─────────────────────────────────────────────────────

    with tab2:
        st.subheader("Student Scores")

        display = (
            df[["student", "score", "pct", "passed"]]
            .rename(columns={"student": "Student", "score": "Score",
                             "pct": "% Score", "passed": "Passed"})
            .sort_values("% Score", ascending=False)
            .reset_index(drop=True)
        )

        fig = px.bar(
            display, x="Student", y="% Score",
            color="Passed",
            color_discrete_map={True: PASS_COLOR, False: FAIL_COLOR},
            title="Score by Student",
            labels={"% Score": "Score (%)"},
        )
        fig.add_hline(
            y=pass_threshold, line_dash="dash", line_color=jw.GRAY_400,
            annotation_text=f"{pass_threshold}% threshold",
            annotation_font_color=jw.GRAY_400,
        )
        fig.update_layout(**jw.plotly_layout(xaxis_tickangle=-40))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download CSV",
            display.to_csv(index=False).encode(),
            file_name=f"{selected_quiz_name}_scores.csv",
            mime="text/csv",
        )

    # ── Tab 3: Question Analysis ──────────────────────────────────────────────────

    with tab3:
        st.subheader("Question Analysis")

        if data_source == "csv":
            st.info(
                "Question-level analysis is only available when using the Canvas API as the data source. "
                "For imported scores, check the New Quizzes Reports inside Canvas for per-question stats."
            )
        else:
            with st.spinner("Loading question statistics…"):
                try:
                    stats = _statistics(canvas_url, token, course_id, quiz_id)
                except Exception as e:
                    stats = None
                    st.warning(f"Could not load statistics: {e}")

            if stats is None:
                st.info("Question-level statistics are not available for this quiz.")
            else:
                q_data = stats.get("quiz_statistics", [{}])[0].get("question_statistics", [])

                if not q_data:
                    st.info("No question data returned.")
                else:
                    q_rows = []
                    for i, q in enumerate(q_data):
                        total   = q.get("responses", 0) or 1
                        correct = q.get("correct_count", 0)
                        q_rows.append({
                            "Q#":             i + 1,
                            "Question":       (q.get("question_text", "")[:80] +
                                               ("…" if len(q.get("question_text", "")) > 80 else "")),
                            "Type":           q.get("question_type", "").replace("_question", "")
                                                .replace("_", " ").title(),
                            "% Correct":      round(correct / total * 100, 1),
                            "Correct":        correct,
                            "Responses":      total,
                            "Discrimination": round(q.get("point_biserial") or 0, 3),
                        })

                    q_df = pd.DataFrame(q_rows)

                    fig = px.bar(
                        q_df, x="Q#", y="% Correct",
                        color="% Correct",
                        color_continuous_scale=[
                            [0.0, jw.DANGER],
                            [0.5, jw.AMBER_500],
                            [1.0, jw.SUCCESS],
                        ],
                        range_color=[0, 100],
                        title="Question Difficulty (% Answered Correctly)",
                        text="% Correct",
                    )
                    fig.update_traces(texttemplate="%{text}%", textposition="outside")
                    fig.add_hline(y=50, line_dash="dot", line_color=jw.GRAY_200,
                                  annotation_text="50%", annotation_font_color=jw.GRAY_400)
                    fig.update_layout(**jw.plotly_layout())
                    st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(q_df, use_container_width=True, hide_index=True)

                    # Student × Question heatmap
                    all_uids = set(df["student"].map(
                        {v: k for k, v in sub_users.items()}
                    ).dropna().astype(int))

                    heatmap_cols = {}
                    for i, q in enumerate(q_data):
                        correct_uids, answering_uids = set(), set()
                        for ans in q.get("answers", []):
                            uids = {int(u) for u in ans.get("user_ids", [])}
                            answering_uids |= uids
                            if ans.get("correct"):
                                correct_uids |= uids
                        if not answering_uids:
                            continue
                        heatmap_cols[f"Q{i+1}"] = {
                            uid: (1 if uid in correct_uids else 0) for uid in all_uids
                        }

                    if heatmap_cols:
                        hm = pd.DataFrame(heatmap_cols).fillna(0)
                        hm.index = hm.index.map(lambda uid: sub_users.get(uid, str(uid)))
                        hm = hm.sort_index()

                        fig_hm = px.imshow(
                            hm,
                            color_continuous_scale=[[0, jw.DANGER], [1, jw.SUCCESS]],
                            zmin=0, zmax=1,
                            labels={"color": "Correct"},
                            title="Student × Question Correctness",
                            aspect="auto",
                        )
                        fig_hm.update_coloraxes(showscale=False)
                        fig_hm.update_layout(**jw.plotly_layout(
                            xaxis_title="Question",
                            yaxis_title="Student",
                            margin=dict(t=48, r=8, b=8, l=8),
                        ))
                        st.plotly_chart(fig_hm, use_container_width=True)

    # ── Tab 4: Cross-Quiz Comparison ──────────────────────────────────────────────

    with tab4:
        st.subheader("Cross-Quiz Comparison")
        compare = st.multiselect(
            "Quizzes to compare",
            options=list(quiz_map.keys()),
            default=[selected_quiz_name],
        )

        if not compare:
            st.info("Select at least one quiz above.")
        else:
            rows = []
            bar = st.progress(0, text="Fetching quiz data…")

            for i, qname in enumerate(compare):
                qobj  = quiz_map[qname]
                qid   = qobj["id"]
                qpts  = qobj.get("points_possible") or 0
                qtype = qobj.get("_type", "classic")
                try:
                    subs, _ = _submissions(canvas_url, token, course_id, qid, qtype)
                    done = [s for s in subs if s.get("workflow_state") == "complete"]
                    if done:
                        if qpts > 0:
                            pcts = [
                                (s.get("kept_score") if s.get("kept_score") is not None
                                 else s.get("score") or 0) / qpts * 100
                                for s in done
                            ]
                            passed = sum(1 for p in pcts if p >= pass_threshold)
                            rows.append({
                                "Quiz":        qname,
                                "Students":    len(pcts),
                                "Avg %":       round(sum(pcts) / len(pcts), 1),
                                "Median %":    round(sorted(pcts)[len(pcts) // 2], 1),
                                "Pass Rate %": round(passed / len(pcts) * 100, 1),
                                "Max %":       round(max(pcts), 1),
                                "Min %":       round(min(pcts), 1),
                            })
                        else:
                            rows.append({
                                "Quiz":        qname,
                                "Students":    len(done),
                                "Avg %":       "0-pt quiz",
                                "Median %":    "—",
                                "Pass Rate %": "—",
                                "Max %":       "—",
                                "Min %":       "—",
                            })
                except Exception:
                    pass
                bar.progress((i + 1) / len(compare), text=f"Loaded: {qname}")

            bar.empty()

            if rows:
                cmp = pd.DataFrame(rows)
                scored = cmp[cmp["Avg %"] != "0-pt quiz"].copy()
                if not scored.empty:
                    scored["Avg %"] = scored["Avg %"].astype(float)
                    scored["Pass Rate %"] = scored["Pass Rate %"].astype(float)
                    fig = px.bar(
                        scored, x="Quiz", y="Avg %",
                        color="Pass Rate %",
                        color_continuous_scale=[[0, jw.DANGER], [0.5, jw.AMBER_500], [1, jw.SUCCESS]],
                        range_color=[0, 100],
                        title="Average Score by Quiz",
                        text="Avg %",
                    )
                    fig.update_traces(texttemplate="%{text}%", textposition="outside")
                    fig.add_hline(
                        y=pass_threshold, line_dash="dash", line_color=jw.DANGER,
                        annotation_text=f"{pass_threshold}% threshold",
                        annotation_font_color=jw.DANGER,
                    )
                    fig.update_layout(**jw.plotly_layout(xaxis_tickangle=-30))
                    st.plotly_chart(fig, use_container_width=True)

                st.dataframe(cmp, use_container_width=True, hide_index=True)
            else:
                st.warning("No completed submissions found for the selected quizzes.")

    # ── Tab 5: Essay Review ───────────────────────────────────────────────────────

    with tab5:
        _render_essay_tab(
            backend=essay_backend,
            doc_url=essay_doc_url,
            quiz_id=quiz_id,
            quiz_name=selected_quiz_name,
            anthropic_key=anthropic_key,
            gemini_key=gemini_key,
        )

    # ── Tab 6: Trends ─────────────────────────────────────────────────────────────

    with tab6:
        _render_trends_tab(canvas_url, token, course_id, quizzes, pass_threshold)

    # ── Tab 7: Module Comparison ──────────────────────────────────────────────────

    with tab7:
        _render_module_tab(canvas_url, token, course_id, quizzes, excluded_ids)
