# -*- coding: utf-8 -*-
import io
import os
import shutil
import pandas as pd
import streamlit as st
from datetime import datetime, date
import hmac
import altair as alt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau, ttest_ind
import warnings
warnings.filterwarnings('ignore')

# Configure Streamlit page
st.set_page_config(
    page_title="Institution TJ Scholar Dashboard",
    page_icon="▧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
.main {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    background-color: #ffffff !important;
    color: #1e293b !important;
}

.stMetric {
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    margin-bottom: 0.5rem !important;
    min-height: auto !important;
    max-height: none !important;
    display: block !important;
    width: 100% !important;
}

.stMetric > div {
    color: #1e293b !important;
    background: transparent !important;
    width: 100% !important;
    overflow: visible !important;
    height: auto !important;
}

.stMetric [data-testid="metric-container"] {
    background: transparent !important;
    border: none !important;
    padding: 0.5rem 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    min-height: auto !important;
    max-height: none !important;
    width: 100% !important;
    display: block !important;
    text-align: left !important;
    overflow: visible !important;
}

.stMetric [data-testid="metric-container"] > div {
    color: #1e293b !important;
    overflow: visible !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    height: auto !important;
    line-height: 1.4 !important;
    width: 100% !important;
    text-align: left !important;
    display: block !important;
}

.stMetric [data-testid="metric-container"] label {
    color: #1e293b !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    overflow: visible !important;
    line-height: 1.4 !important;
    text-align: left !important;
    display: inline !important;
    width: auto !important;
    margin: 0 !important;
}

.stMetric [data-testid="metric-container"] [data-testid="metric-value"] {
    color: #1e293b !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    overflow: visible !important;
    text-align: left !important;
    display: inline !important;
    width: auto !important;
    margin: 0 0.5rem 0 0 !important;
}

.stMetric [data-testid="metric-container"] [data-testid="metric-delta"] {
    color: #64748b !important;
    font-size: 0.9rem !important;
    font-weight: 400 !important;
    overflow: visible !important;
    text-align: left !important;
    display: inline !important;
    width: auto !important;
    margin: 0 0 0 0.5rem !important;
}

.stSuccess {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.5rem 0 !important;
    color: #10b981 !important;
    border-left: 3px solid #10b981 !important;
    padding-left: 1rem !important;
}

.stInfo {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.5rem 0 !important;
    color: #3b82f6 !important;
    border-left: 3px solid #3b82f6 !important;
    padding-left: 1rem !important;
}

.stWarning {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.5rem 0 !important;
    color: #f59e0b !important;
    border-left: 3px solid #f59e0b !important;
    padding-left: 1rem !important;
}

.stError {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.5rem 0 !important;
    color: #ef4444 !important;
    border-left: 3px solid #ef4444 !important;
    padding-left: 1rem !important;
}

.tier-flex {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    width: 100%;
    gap: 1rem;
}
.tier-column {
    width: 32%;
    padding: 0.5rem;
    border-radius: 0;
    border: none;
    background: transparent;
}
.tier1-text {
    color: #4CAF50;
    font-weight: bold;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}
.tier2-text {
    color: #FF9800;
    font-weight: bold;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}
.tier3-text {
    color: #EF5350;
    font-weight: bold;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}
.tier-criteria {
    margin: 6px 0;
    font-size: 0.9rem;
    line-height: 1.4;
}

.tier-button-block { margin-bottom: 1rem; }
.tier-button-label { font-weight: bold; color: #1e293b; font-size: 1rem; margin-bottom: 0.35rem; }
.tier-button {
    display: inline-block; padding: 0.6rem 1.5rem; border-radius: 12px; font-weight: bold;
    color: white !important; font-size: 1.1rem; text-align: center; min-width: 80px;
}

h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #1e293b !important;
}
h1 { font-size: 2.25rem !important; margin-bottom: 1rem !important; }
h2 { font-size: 1.875rem !important; margin-bottom: 1rem !important; color: #334155 !important; }
h3 { font-size: 1.5rem !important; margin-bottom: 0.75rem !important; color: #475569 !important; }
</style>
""", unsafe_allow_html=True)

# ── Design system ──────────────────────────────────────────────────────────────
BRAND_COLORS = {
    'primary': '#00B4A6',
    'secondary': '#7C3AED',
    'success': '#10b981',
    'info': '#3b82f6',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'gradient': ['#00B4A6', '#7C3AED', '#3b82f6', '#10b981', '#f59e0b'],
    'chart_palette': ['#00B4A6', '#7C3AED', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
}

TIER_COLORS = {'Tier 1': '#4CAF50', 'Tier 2': '#FF9800', 'Tier 3': '#EF5350'}
OUTCOME_COLORS = {
    'Passing': '#4CAF50',
    'Borderline': '#FF9800',
    'Below 495': '#EF5350',
    'No score reported': '#9E9E9E'
}

# ── Helper functions ───────────────────────────────────────────────────────────

@st.cache_data
def load_jfd_data():
    """Load and prepare the JFD combined data."""
    jfd_df = None
    possible_files = [
        'student-data/jfd-combined.csv',
        './student-data/jfd-combined.csv'
    ]
    for file_path in possible_files:
        try:
            if os.path.exists(file_path):
                jfd_df = pd.read_csv(file_path)
                break
        except Exception:
            continue

    if jfd_df is not None:
        jfd_df['highest_exam_score'] = pd.to_numeric(jfd_df['highest_exam_score'], errors='coerce')
        jfd_df['exam_count'] = pd.to_numeric(jfd_df['exam_count'], errors='coerce').fillna(0).astype(int)
        tier_cols = ['survey_tier', 'large_group_tier', 'small_group_tier', 'class_participation_tier']
        for col in tier_cols:
            if col in jfd_df.columns:
                jfd_df[col] = jfd_df[col].fillna('N/A')

    return jfd_df


def apply_light_mode_styling(fig):
    """Apply consistent light mode styling to Plotly charts."""
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Inter, sans-serif", color='#1e293b', size=12),
        title_font=dict(size=18, color='#1e293b', family="Inter, sans-serif"),
        xaxis=dict(
            gridcolor='#f1f5f9',
            zerolinecolor='#e2e8f0',
            tickfont=dict(color='#1e293b', size=11),
            title_font=dict(color='#1e293b', size=12)
        ),
        yaxis=dict(
            gridcolor='#f1f5f9',
            zerolinecolor='#e2e8f0',
            tickfont=dict(color='#1e293b', size=11),
            title_font=dict(color='#1e293b', size=12)
        ),
        legend=dict(
            bgcolor='white',
            bordercolor='#e2e8f0',
            borderwidth=1,
            font=dict(color='#1e293b', size=11)
        )
    )
    try:
        fig.update_layout(
            coloraxis_colorbar=dict(
                tickfont=dict(color='#1e293b', size=10),
                title_font=dict(color='#1e293b', size=11)
            )
        )
    except Exception:
        pass
    try:
        fig.update_traces(marker_line_color='#1e293b')
    except Exception:
        pass
    return fig


def get_name(student_id, roster_df):
    """Resolve student ID to name — falls back to 'Student N' if roster not loaded."""
    if roster_df is None or roster_df.empty:
        return f"Student {student_id}"
    match = roster_df[roster_df['Student id'] == int(student_id)]
    if match.empty:
        return f"Student {student_id}"
    return match.iloc[0]['Name Surname']


def tier_badge(tier_str):
    color = TIER_COLORS.get(tier_str, '#9E9E9E')
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:10px;font-weight:bold;font-size:0.85rem;">{tier_str}</span>'
    )


def outcome_badge(outcome_str):
    color = OUTCOME_COLORS.get(outcome_str, '#9E9E9E')
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:10px;font-weight:bold;font-size:0.85rem;">{outcome_str}</span>'
    )


def assign_tier(value, thresholds):
    """
    Assign Tier 1/2/3 string based on value and thresholds dict.
    thresholds = {'tier1_min': 0.70, 'tier2_min': 0.40}
    """
    if pd.isna(value):
        return 'Tier 3'
    if value >= thresholds['tier1_min']:
        return 'Tier 1'
    if value >= thresholds['tier2_min']:
        return 'Tier 2'
    return 'Tier 3'


def tier_num(tier_str):
    return {'Tier 1': 1, 'Tier 2': 2, 'Tier 3': 3}.get(tier_str, 3)


# ── Page title ─────────────────────────────────────────────────────────────────
st.title('Institution TJ - Scholar Dashboard')

# ── Password protection ────────────────────────────────────────────────────────
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        try:
            if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
                st.session_state["password_correct"] = True
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
        except Exception:
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]

    if st.session_state.get("password_correct", False):
        return True

    try:
        _ = st.secrets["password"]
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            st.error("😕 Password incorrect")
        return False
    except Exception:
        return True


if not check_password():
    st.stop()

# ── Sidebar navigation ─────────────────────────────────────────────────────────
st.sidebar.title("Navigation")
view_mode = st.sidebar.radio(
    "View",
    [
        "EY25 Scholars - March - April Outcomes, Scores, Tiers, and Intervention",
        "Individual Student Data - EY25",
    ],
    label_visibility="visible",
)

# Student roster reference (collapsed expander) — hidden on programming/partner pages
if view_mode not in ("EY 26 Programming", "EY25 Summer Retester Cohort"):
    roster_path = None
    for path in ['roster.csv', './roster.csv']:
        if os.path.exists(path):
            roster_path = path
            break
    if roster_path:
        roster_df_ref = pd.read_csv(roster_path)
        with st.expander("Student roster (reference)", expanded=False):
            st.dataframe(
                roster_df_ref.rename(columns={'student_id': 'Student ID', 'name': 'Name'}),
                use_container_width=True,
                hide_index=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: Individual Student Data - EY25
# ══════════════════════════════════════════════════════════════════════════════
if view_mode == "Individual Student Data - EY25":
    data_paths = [
        '',
        'TJEY25/',
        './TJEY25/',
        'student-data/',
        './student-data/',
        'student_data/',
        './student_data/',
    ]

    individual_data_available = False
    test_data_available = False
    base_path_used = None

    for base_path in data_paths:
        try:
            engagement_path = f'{base_path}institution-1-engagement-data.csv'
            if not os.path.exists(engagement_path):
                continue
            df_engagement_attendance = pd.read_csv(engagement_path, parse_dates=['start_date', 'end_date'])
            individual_data_available = True
            base_path_used = base_path
            test_path = f'{base_path}institution-1-test-data.csv'
            if os.path.exists(test_path):
                df_test_scores = pd.read_csv(test_path, parse_dates=['test_date'])
                df_test_scores['test_date'] = pd.to_datetime(df_test_scores['test_date']).dt.date
                test_data_available = True
            else:
                df_test_scores = None
            break
        except Exception:
            continue

    if individual_data_available and not test_data_available:
        for base_path in data_paths:
            test_path = f'{base_path}institution-1-test-data.csv'
            try:
                if os.path.exists(test_path):
                    df_test_scores = pd.read_csv(test_path, parse_dates=['test_date'])
                    df_test_scores['test_date'] = pd.to_datetime(df_test_scores['test_date']).dt.date
                    test_data_available = True
                    break
            except Exception:
                continue

    if not individual_data_available:
        st.error("**Individual Student Dashboard Data Not Found**")
        st.info("The Individual Student Dashboard requires `institution-1-engagement-data.csv`.")
        try:
            current_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            if current_files:
                st.markdown("**CSV files in root directory:**")
                for f in current_files:
                    st.write(f"- {f}")
        except Exception:
            pass

    if individual_data_available:
        student_id = st.selectbox("Choose a student:", list(df_engagement_attendance['student_id'].unique()))

        st.markdown("**Surveys & resources:**")
        st.markdown("- [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)")
        st.write(' ')

        tier_df = None
        for path in ['tier.csv', './tier.csv']:
            try:
                if os.path.exists(path):
                    tier_df = pd.read_csv(path)
                    break
            except Exception:
                continue

        st.markdown("**Tier definitions**")
        st.markdown("""
        <div class="tier-flex">
            <div class="tier-column">
                <div class="tier1-text">Tier 1 Students</div>
                <div class="tier-criteria" style="color: #4CAF50;">Tier 1: &gt;5 exams reported</div>
                <div class="tier-criteria" style="color: #4CAF50;">Attendance in Large Group Sessions (&gt;70%)</div>
                <div class="tier-criteria" style="color: #4CAF50;">Attendance in Small Group Sessions (&gt;70%)</div>
            </div>
            <div class="tier-column">
                <div class="tier2-text">Tier 2 Students</div>
                <div class="tier-criteria" style="color: #FF9800;">Tier 2: 3-4 exams reported</div>
                <div class="tier-criteria" style="color: #FF9800;">Attendance in Large Group Sessions (50-69%)</div>
                <div class="tier-criteria" style="color: #FF9800;">Attendance in Small Group Sessions (50-69%)</div>
            </div>
            <div class="tier-column">
                <div class="tier3-text">Tier 3 Students</div>
                <div class="tier-criteria" style="color: #EF5350;">Tier 3: &lt;2 exams reported</div>
                <div class="tier-criteria" style="color: #EF5350;">Attendance in Large Group Sessions (&lt;49%)</div>
                <div class="tier-criteria" style="color: #EF5350;">Attendance in Small Group Sessions (&lt;49%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.write(' ')

        jfd_df = load_jfd_data()
        tier_cols = ['survey_tier', 'large_group_tier', 'small_group_tier', 'class_participation_tier']
        if jfd_df is not None and 'student_id' in jfd_df.columns:
            jfd_student = jfd_df[jfd_df['student_id'] == student_id]
            if not jfd_student.empty:
                display_tier_cols = [c for c in tier_cols if c in jfd_student.columns]
                if display_tier_cols:
                    tier_table = jfd_student[['student_id'] + display_tier_cols].head(1)
                    tier_table.columns = ['Student ID'] + [c.replace('_', ' ').title() for c in display_tier_cols]
                    st.markdown("**Tiers (text)**")
                    st.dataframe(tier_table, use_container_width=True, hide_index=True)
                    st.write(' ')

        df_engagement_attendance_student_filtered = df_engagement_attendance[
            df_engagement_attendance['student_id'] == student_id
        ].copy()
        df_engagement_attendance_student_filtered['date_range'] = df_engagement_attendance_student_filtered.apply(
            lambda row: f"{row['start_date'].strftime('%m/%d/%y')} - {row['end_date'].strftime('%m/%d/%y')}", axis=1
        )

        for col in ['num_attended_large_session', 'num_scheduled_large_session',
                    'num_attended_small_session', 'num_scheduled_small_session']:
            if col in df_engagement_attendance_student_filtered.columns:
                df_engagement_attendance_student_filtered[col] = pd.to_numeric(
                    df_engagement_attendance_student_filtered[col], errors='coerce'
                ).fillna(0)

        denom_lg = df_engagement_attendance_student_filtered['num_scheduled_large_session'].replace(0, np.nan)
        denom_sm = df_engagement_attendance_student_filtered['num_scheduled_small_session'].replace(0, np.nan)
        df_engagement_attendance_student_filtered['large_session'] = (
            df_engagement_attendance_student_filtered['num_attended_large_session'] / denom_lg
        )
        df_engagement_attendance_student_filtered['small_session'] = (
            df_engagement_attendance_student_filtered['num_attended_small_session'] / denom_sm
        )

        if test_data_available:
            df_test_scores_student_filtered = df_test_scores[df_test_scores['student_id'] == student_id]
        else:
            df_test_scores_student_filtered = None

        st.write(' ')
        st.write(' ')

        # Tier showcase buttons
        def tier_button_color(tier_str):
            if not tier_str or tier_str == "—" or "No " in str(tier_str):
                return "#9E9E9E"
            if "Tier 1" in str(tier_str):
                return "#4CAF50"
            if "Tier 2" in str(tier_str):
                return "#FF9800"
            return "#EF5350"

        if tier_df is not None and not tier_df.empty:
            student_tier = tier_df[tier_df['student_id'] == student_id]
            jun_dec = student_tier[student_tier['date_window'] == 'Jun-Dec 2025'] if not student_tier.empty else pd.DataFrame()
            jan_cur = student_tier[student_tier['date_window'] == 'Jan 2026-Current'] if not student_tier.empty else pd.DataFrame()

            def get_tier_val(df_window, col):
                if df_window.empty or col not in df_window.columns:
                    return "—"
                val = df_window.iloc[0][col]
                return val if pd.notna(val) else "—"

            lg_jd = get_tier_val(jun_dec, 'large_group_tier')
            sm_jd = get_tier_val(jun_dec, 'small_group_tier')
            lg_jc = get_tier_val(jan_cur, 'large_group_tier')
            sm_jc = get_tier_val(jan_cur, 'small_group_tier')

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Jun–Dec 2025**")
                st.markdown(f"""
                <div class="tier-button-block">
                  <div class="tier-button-label">Large Group Attendance</div>
                  <div class="tier-button" style="background:{tier_button_color(lg_jd)}">{lg_jd}</div>
                </div>
                <div class="tier-button-block">
                  <div class="tier-button-label">Small Group Attendance</div>
                  <div class="tier-button" style="background:{tier_button_color(sm_jd)}">{sm_jd}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown("**Jan 2026–Current**")
                st.markdown(f"""
                <div class="tier-button-block">
                  <div class="tier-button-label">Large Group Attendance</div>
                  <div class="tier-button" style="background:{tier_button_color(lg_jc)}">{lg_jc}</div>
                </div>
                <div class="tier-button-block">
                  <div class="tier-button-label">Small Group Attendance</div>
                  <div class="tier-button" style="background:{tier_button_color(sm_jc)}">{sm_jc}</div>
                </div>
                """, unsafe_allow_html=True)
            st.write(' ')

        # Practice Exam Scores
        if test_data_available and df_test_scores_student_filtered is not None and not df_test_scores_student_filtered.empty:
            st.subheader('8 Exams are Required for the JW MCAT Course, 4 Are Due by December 31, 2025')
            st.write('Students were asked to update us with practice exam schedules and scores throughout the program.')
            st.write(' ')
            exam_display = df_test_scores_student_filtered[['test_name', 'test_date', 'actual_exam_score']].copy()
            st.dataframe(exam_display, use_container_width=True)
            st.write(' ')

            point_exam_scores = alt.Chart(df_test_scores_student_filtered).mark_point().transform_fold(
                fold=['actual_exam_score'],
                as_=['variable', 'value']
            ).encode(
                x=alt.X('yearmonthdate(test_date):O', axis=alt.Axis(labelAngle=-45, title='Test Date')),
                y=alt.Y('value:Q', axis=alt.Axis(title='Practice Exam Score'), scale=alt.Scale(domain=[470, 528])),
                tooltip=[
                    alt.Tooltip('test_date:T', title='Test Date'),
                    alt.Tooltip('value:Q', title='Exam Score')
                ],
                color=alt.Color('variable:N', legend=alt.Legend(
                    title='Exam Scores', orient='bottom',
                    labelExpr="'Practice Exam Score'"
                ))
            )
            st.altair_chart(point_exam_scores, use_container_width=True)
            st.write(' ')
        elif test_data_available:
            st.info('No practice exam records for this student.')
            st.write(' ')

        # Attendance
        st.header('Attendance')
        _att_max = df_engagement_attendance_student_filtered['end_date'].max() if not df_engagement_attendance_student_filtered.empty else None
        _att_through = _att_max.strftime('%B %d, %Y') if _att_max is not None and hasattr(_att_max, 'strftime') else '—'
        st.caption(f'Updated through {_att_through}.')
        st.write(
            'Below demonstrates the weekly percentage of attendance by students within our "All Student" and "Small Group" classes.\n\n'
            'For example, if there are two large classes and a student attends one of them, they would receive a 50% attendance rate for that week. '
            'A data point with 0% indicates no attendance during that week, while the absence of a data point reflects that no classes were held that week.'
        )
        st.write(' ')

        line_attendance = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
            fold=['large_session', 'small_session'],
            as_=['variable', 'value']
        ).encode(
            x=alt.X('week:O', axis=alt.Axis(labelAngle=0, title='Week')),
            y=alt.Y('value:Q', axis=alt.Axis(title='Weekly Attendance Rate', format='%'), scale=alt.Scale(domain=[0, 1])),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Weekly Attendance Rate', format='0.0%')
            ],
            color=alt.Color('variable:N', legend=alt.Legend(
                title='Session Type', orient='bottom',
                labelExpr="datum.value == 'large_session' ? 'Classes with All Students' : 'Small Group Sessions'"
            ))
        )
        st.altair_chart(line_attendance, use_container_width=True)
        st.write(' ')

        df_through_week_29 = df_engagement_attendance_student_filtered[
            df_engagement_attendance_student_filtered['week'] <= 29
        ]
        _w29_max = df_through_week_29['end_date'].max() if not df_through_week_29.empty else None
        _w29_through = _w29_max.strftime('%B %d, %Y') if _w29_max is not None and hasattr(_w29_max, 'strftime') else '—'

        # Completed Question Sets
        st.header('Completed Question Sets')
        st.caption(f'Updated through {_w29_through}.')
        st.write('This graph displays the number of question sets completed within our question bank per week.')
        st.write(' ')

        line_question_sets = alt.Chart(df_through_week_29).mark_line(point=True).encode(
            x=alt.X('week:O', axis=alt.Axis(labelAngle=0, title='Week')),
            y=alt.Y('total_completed_passages_discrete_sets', axis=alt.Axis(title='Completed Number of Question Sets')),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('total_completed_passages_discrete_sets', title='Completed Count')
            ]
        )
        st.altair_chart(line_question_sets, use_container_width=True)
        st.write(' ')

        # Accuracy
        st.header('Accuracy')
        st.subheader('Average Accuracy (%) on Question Sets Per Week')
        st.caption(f'Updated through {_w29_through}.')
        st.write(
            'During Session Practice: "In-Class Questions" refer to accuracy for question sets given during class.\n\n'
            'Self-Learning Practice: "CARS Questions" and "Science Questions" refer to weekly performance on independent practice sets.'
        )
        st.write(' ')

        line_engagement_accuracy = alt.Chart(df_through_week_29).mark_line(point=True).transform_fold(
            fold=['sciences_accuracy', 'cars_accuracy', 'class_accuracy'],
            as_=['variable', 'value']
        ).encode(
            x=alt.X('week:O', axis=alt.Axis(labelAngle=0, title='Week')),
            y=alt.Y('value:Q', axis=alt.Axis(title='Average Accuracy (%)', format='%')),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Accuracy Rate', format='0.1%')
            ],
            color=alt.Color('variable:N', legend=alt.Legend(
                title='Subject', orient='bottom',
                labelExpr="datum.value == 'cars_accuracy' ? 'CARS Questions' : datum.value == 'class_accuracy' ? 'In-Class Questions' : 'Science Questions'"
            ))
        )
        st.altair_chart(line_engagement_accuracy, use_container_width=True)
        st.write(' ')

        # Completed Lessons
        st.header('Completed Lessons')
        st.subheader('Self-Learning with Jack Westin Course or Question Bank')
        st.caption(f'Updated through {_w29_through}.')
        st.write('This graph displays the number of video lessons or assignments within the Self-Paced JW Complete MCAT Course completed per week.')
        st.write(' ')

        line_engagement = alt.Chart(df_through_week_29).mark_line(point=True).transform_fold(
            ['completed_lessons'], as_=['variable', 'value']
        ).encode(
            x=alt.X('week:O', axis=alt.Axis(labelAngle=0, title='Week')),
            y=alt.Y('value:Q', axis=alt.Axis(title='Completed Count')),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Completed Number of Lessons')
            ],
            color=alt.Color('variable:N', legend=alt.Legend(
                title='Type', orient='bottom',
                labelExpr="'Completed Course Lessons'"
            ))
        )
        st.altair_chart(line_engagement, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: EY25 Summer Retester Cohort
# ══════════════════════════════════════════════════════════════════════════════
elif view_mode == "EY25 Summer Retester Cohort":
    st.title("EY25 Summer Retester Cohort")
    st.write(" ")

    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0; font-size: 1rem; line-height: 1.45;">
    <p style="margin: 0 0 0.4rem 0;"><strong>Class days and times are flexible.</strong> For instance:</p>
    <ul style="margin: 0.25rem 0 0.4rem 1.25rem; padding-left: 0.5rem;">
    <li>A Monday–Wednesday class in the morning can be switched to a Tuesday–Thursday class in the evening.</li>
    <li>A three-day-per-week program that has four classes can be changed to a four-day-per-week program that has four classes.<br>
    <span style="display: block; margin-left: 1.5rem; margin-top: 0.25rem;"><strong>The number of classes per week stays the same.</strong></span></li>
    </ul>
    <p style="margin: 0.4rem 0 0.25rem 0;">Practice exam timing is also flexible: we can move mandatory practice exam due dates around. These are our recommendations, but they're flexible.</p>
    <p style="margin: 0.5rem 0 0.25rem 0;"><strong>Goal:</strong> Finalize scheduling by end of March for EY25 so we can ensure proper instructor headcount.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    st.markdown("""
    - Designed for scholars sitting for summer AAMC exams.
    - Aligns with official AAMC test dates and historical second-attempt trends.
    - Includes built-in benchmarking and structured exam pacing.
    - 85% of students in the EY24 cohort had taken their exam by the end of July. Attendance tended to drop prior to exam dates. Students value the breathing room between class and their next exam.
    """)
    st.write(" ")

    st.info("**Second Attempt recommended requirements** — Students must complete **3 full-length exams** between their first and second attempts.")
    st.write(" ")
    st.markdown("**Summer Program Student recommended requirements**")
    st.markdown("- 1 full-length exam completed before the start of the summer program.")
    st.markdown("- 2 additional full-length exams completed during the summer.")
    st.markdown("- *Exception:* Students testing June 12 or June 13 may have adjusted requirements due to limited timeline.")
    st.write(" ")

    opt1_tab, opt2_tab = st.tabs(["Option 1", "Option 2"])
    with opt1_tab:
        st.markdown("**Structure**")
        st.markdown("- Three Large Group classes weekly (2 hours each).")
        st.markdown("- No class on double AAMC exam weeks.")
        st.markdown("- Two Small Group sessions weekly (1 hour each).")
        st.markdown("- Program dates: June 1 – July 27.")
    with opt2_tab:
        st.markdown("**Structure**")
        st.markdown("- 1 Large Group class weekly (2 hours).")
        st.markdown("- First week of June and July include 2 Large Group classes.")
        st.markdown("- 1 Small Group session weekly.")
        st.markdown("- Program dates: June 1 – July 27.")

    st.write(" ")
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #64748b; background-color: #f8fafc; border-radius: 0 6px 6px 0;">
    <strong>Comparison</strong> — Option 1 prioritizes structured exam benchmarking and formal study breaks. Option 2 prioritizes consistent weekly cadence with lighter pacing.
    </div>
    """, unsafe_allow_html=True)

    EY25_SUMMER_ASSETS = "ey25_summer_assets"
    EY25_SUMMER_PDF = os.path.join(EY25_SUMMER_ASSETS, "retaker_cohort_side_by_side.pdf")
    _cursor_retaker = os.path.expanduser(
        "~/Library/Application Support/Cursor/User/workspaceStorage/bd0c71989d537611b6a480339d820d09/pdfs/2845df9b-0ed3-4dca-90f4-21c9b04b9f17/retaker cohort side by side.pdf"
    )
    if not os.path.exists(EY25_SUMMER_PDF) and os.path.exists(_cursor_retaker):
        os.makedirs(EY25_SUMMER_ASSETS, exist_ok=True)
        try:
            shutil.copy2(_cursor_retaker, EY25_SUMMER_PDF)
        except Exception:
            pass
    if os.path.exists(EY25_SUMMER_PDF):
        st.write(" ")
        st.subheader("Retaker cohort calendar")
        try:
            import fitz
            doc = fitz.open(EY25_SUMMER_PDF)
            for i in range(len(doc)):
                page = doc.load_page(i)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                st.image(io.BytesIO(img_bytes), use_container_width=True)
            doc.close()
        except Exception:
            st.caption("PDF available in app assets; enable PyMuPDF to view.")
    st.write(" ")

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: Current Status EY25
# ══════════════════════════════════════════════════════════════════════════════
elif view_mode == "Current Status EY25":
    st.header("Current Status EY25")
    st.write(" ")

    tier_df = None
    for path in ['tier.csv', './tier.csv']:
        try:
            if os.path.exists(path):
                tier_df = pd.read_csv(path)
                break
        except Exception:
            continue

    test_df = None
    for path in ['institution-1-test-data.csv', './institution-1-test-data.csv', 'student-data/institution-1-test-data.csv']:
        try:
            if os.path.exists(path):
                test_df = pd.read_csv(path, parse_dates=['test_date'])
                break
        except Exception:
            continue

    engagement_df = None
    for path in ['institution-1-engagement-data.csv', './institution-1-engagement-data.csv', 'student-data/institution-1-engagement-data.csv']:
        try:
            if os.path.exists(path):
                engagement_df = pd.read_csv(path, parse_dates=['start_date', 'end_date'])
                break
        except Exception:
            continue

    has_tier = tier_df is not None and not tier_df.empty
    has_test = test_df is not None and not test_df.empty
    has_engagement = engagement_df is not None and not engagement_df.empty

    st.write(" ")

    # First Final Exam Score outcome
    st.subheader("First Final Exam Score outcome")
    st.markdown("""
    **First Final Exam Score** = score from the row where **test_name** is *First Attempt* only.

    **Definitions:**
    - **Passed:** First Final Exam Score **≥ 502**
    - **Borderline:** First Final Exam Score **495–501**
    - **Below 495:** First Final Exam Score **< 495**
    """)
    st.write(" ")

    if has_test and not test_df.empty:
        test_df['actual_exam_score'] = pd.to_numeric(test_df['actual_exam_score'], errors='coerce')
        first_attempt_designated = test_df[
            (test_df['test_name'] == 'First Attempt') &
            test_df['actual_exam_score'].notna() &
            (test_df['actual_exam_score'] > 0)
        ]
        if first_attempt_designated.empty:
            first_attempt = pd.DataFrame(columns=['student_id', 'first_attempt_date', 'first_attempt_score'])
        else:
            first_attempt = first_attempt_designated.groupby('student_id').first().reset_index()[
                ['student_id', 'test_date', 'actual_exam_score']
            ]
            first_attempt = first_attempt.rename(columns={
                'actual_exam_score': 'first_attempt_score',
                'test_date': 'first_attempt_date'
            })

        first_attempt['first_attempt_score_clean'] = pd.to_numeric(
            first_attempt['first_attempt_score'], errors='coerce'
        )
        first_attempt = first_attempt[
            first_attempt['first_attempt_score_clean'].notna() &
            (first_attempt['first_attempt_score_clean'] >= 472) &
            (first_attempt['first_attempt_score_clean'] <= 528)
        ]

        def outcome_label(score):
            if score >= 502:
                return 'Passed'
            elif score >= 495:
                return 'Borderline'
            else:
                return 'Below 495'

        first_attempt['first_attempt_outcome'] = first_attempt['first_attempt_score_clean'].apply(outcome_label)

        # Exam tier from practice exam count
        practice_scores = test_df[
            (test_df['test_name'] != 'First Attempt') &
            (test_df['test_name'] != 'Second Exam Attempt') &
            (test_df['test_name'] != 'Anticipated Test Date') &
            (test_df['test_name'] != 'Anticipated Exam Date') &
            pd.to_numeric(test_df['actual_exam_score'], errors='coerce').between(472, 528)
        ]
        exam_counts = practice_scores.groupby('student_id').size().reset_index(name='exam_count')
        first_attempt = first_attempt.merge(exam_counts, on='student_id', how='left')
        first_attempt['exam_count'] = first_attempt['exam_count'].fillna(0).astype(int)

        def exam_tier_label(n):
            if n > 5:
                return 'Tier 1'
            elif n >= 3:
                return 'Tier 2'
            else:
                return 'Tier 3'

        first_attempt['exam_tier'] = first_attempt['exam_count'].apply(exam_tier_label)

        # Attendance tiers from tier.csv
        if has_tier:
            tier_recent = tier_df[tier_df['date_window'] == 'Jan 2026-Current']
            tier_jd = tier_df[tier_df['date_window'] == 'Jun-Dec 2025']
            lg_recent = tier_recent[['student_id', 'large_group_tier', 'small_group_tier']].rename(
                columns={'large_group_tier': 'large_group_tier', 'small_group_tier': 'small_group_tier'}
            )
            lg_jd = tier_jd[['student_id', 'large_group_tier', 'small_group_tier']].rename(
                columns={'large_group_tier': 'large_group_tier_JunDec', 'small_group_tier': 'small_group_tier_JunDec'}
            )
            first_attempt = first_attempt.merge(lg_recent, on='student_id', how='left')
            first_attempt = first_attempt.merge(lg_jd, on='student_id', how='left')
            for col in ['large_group_tier', 'small_group_tier', 'large_group_tier_JunDec', 'small_group_tier_JunDec']:
                if col in first_attempt.columns:
                    first_attempt[col] = first_attempt[col].fillna('No data')
        else:
            first_attempt['large_group_tier'] = '—'
            first_attempt['small_group_tier'] = '—'
            first_attempt['large_group_tier_JunDec'] = '—'
            first_attempt['small_group_tier_JunDec'] = '—'

        first_attempt['attendance_tier_1_or_2'] = (
            first_attempt['large_group_tier'].isin(['Tier 1', 'Tier 2']) &
            first_attempt['small_group_tier'].isin(['Tier 1', 'Tier 2'])
        )
        first_attempt['exam_tier_1_or_2'] = first_attempt['exam_tier'].isin(['Tier 1', 'Tier 2'])
        passed = first_attempt['first_attempt_outcome'] == 'Passed'
        tier12_att_or_exam = first_attempt['attendance_tier_1_or_2'] | first_attempt['exam_tier_1_or_2']
        n_passed = int(passed.sum())
        n_passed_tier12 = int((passed & tier12_att_or_exam).sum())
        outcome_counts = first_attempt['first_attempt_outcome'].value_counts()

        o1, o2, o3 = st.columns(3)
        for col, out in zip([o1, o2, o3], ["Passed", "Borderline", "Below 495"]):
            with col:
                st.metric(out, int(outcome_counts.get(out, 0)))
        st.write(" ")

        outcome_order_top = ["Passed", "Borderline", "Below 495"]
        outcome_for_chart_top = [o for o in outcome_order_top if o in outcome_counts.index]
        counts_list_top = [int(outcome_counts.get(o, 0)) for o in outcome_for_chart_top]
        if outcome_for_chart_top and sum(counts_list_top) > 0:
            df_outcome_top = pd.DataFrame({"Outcome": outcome_for_chart_top, "Count": counts_list_top})
            color_map_top = {"Passed": "#10b981", "Borderline": "#f59e0b", "Below 495": "#ef4444"}
            fig_outcome_top = px.bar(df_outcome_top, x="Outcome", y="Count", color="Outcome",
                color_discrete_map=color_map_top, title="First Final Exam Score outcome (counts)")
            fig_outcome_top.update_layout(showlegend=False, xaxis_tickangle=-25)
            fig_outcome_top = apply_light_mode_styling(fig_outcome_top)
            st.plotly_chart(fig_outcome_top, use_container_width=True)
        st.write(" ")

        # Borderline students
        borderline = first_attempt[
            (first_attempt['first_attempt_score_clean'] >= 495) &
            (first_attempt['first_attempt_score_clean'] < 502)
        ]
        if not borderline.empty:
            borderline_ids = borderline['student_id'].tolist()
            test_valid = test_df[test_df['student_id'].isin(borderline_ids)].copy()
            test_valid['actual_exam_score'] = pd.to_numeric(test_valid['actual_exam_score'], errors='coerce')
            test_valid = test_valid[test_valid['actual_exam_score'].notna() & (test_valid['actual_exam_score'] > 0)]
            first_scores = borderline.set_index('student_id')['first_attempt_score']
            low_fa_high = []
            for sid in borderline_ids:
                rows = test_valid[test_valid['student_id'] == sid]
                if rows.empty:
                    continue
                scores = rows['actual_exam_score'].values
                low, high = float(scores.min()), float(scores.max())
                fa = float(first_scores.loc[sid]) if sid in first_scores.index else np.nan
                low_fa_high.append({'student_id': sid, 'Lowest': low, 'First Attempt': fa, 'Highest': high})
            df_borderline_scores = pd.DataFrame(low_fa_high)
            if not df_borderline_scores.empty:
                st.subheader("Borderline students: baseline to score increase")
                st.caption("Students whose **First Attempt** actual MCAT score is **495–501**.")
                plot_df = df_borderline_scores[['student_id', 'Lowest', 'First Attempt', 'Highest']].copy()
                plot_df = plot_df.rename(columns={'Lowest': 'Baseline', 'First Attempt': 'Actual'})
                plot_ids = plot_df['student_id'].tolist()
                plot_df['student_id'] = plot_df['student_id'].astype(str)
                plot_df = plot_df.melt(id_vars=['student_id'], value_vars=['Baseline', 'Actual', 'Highest'],
                                       var_name='Metric', value_name='Score')
                fig_borderline = px.bar(plot_df, x='student_id', y='Score', color='Metric', barmode='group',
                    title='Borderline students: baseline, actual (First Attempt), and highest score',
                    color_discrete_map={'Baseline': '#94a3b8', 'Actual': '#f59e0b', 'Highest': '#10b981'},
                    category_orders={'student_id': [str(i) for i in plot_ids]})
                y_min = max(472, int(plot_df['Score'].min()) - 10)
                y_max = min(528, int(plot_df['Score'].max()) + 10)
                fig_borderline.update_layout(
                    xaxis_title='Student ID',
                    xaxis={'type': 'category', 'categoryorder': 'array', 'categoryarray': [str(i) for i in plot_ids]},
                    yaxis={'title': 'Score', 'range': [y_min, y_max], 'dtick': 5},
                    bargap=0.2, bargroupgap=0.02,
                    legend={'orientation': 'h', 'yanchor': 'top', 'y': 0.99, 'xanchor': 'right', 'x': 0.99,
                            'bgcolor': 'rgba(255,255,255,0.8)'},
                    margin={'t': 100}
                )
                fig_borderline = apply_light_mode_styling(fig_borderline)
                st.plotly_chart(fig_borderline, use_container_width=True)
        st.write(" ")

        # Score improvement frequency
        test_valid_all = test_df[
            pd.to_numeric(test_df['actual_exam_score'], errors='coerce').between(472, 528)
        ].copy()
        test_valid_all['actual_exam_score'] = pd.to_numeric(test_valid_all['actual_exam_score'], errors='coerce')
        score_range = test_valid_all.groupby('student_id')['actual_exam_score'].agg(['min', 'max'])
        score_range['improvement'] = score_range['max'] - score_range['min']
        improved_df = score_range[score_range['improvement'] > 0].reset_index()
        improvements_1_30 = improved_df['improvement'][improved_df['improvement'].between(1, 30)]
        if not improvements_1_30.empty:
            st.subheader("Score improvement frequency")
            st.caption("Among students with 2+ valid scores: improvement = highest − lowest. X = points improved, Y = number of students.")
            freq = improvements_1_30.value_counts().sort_index()
            df_freq = freq.reset_index()
            df_freq.columns = ['Points improved', 'Number of students']
            fig_freq = px.bar(df_freq, x='Points improved', y='Number of students',
                title='Frequency of score improvement')
            fig_freq.update_layout(xaxis={'dtick': 1, 'range': [-0.5, 30.5]}, margin={'t': 80})
            fig_freq = apply_light_mode_styling(fig_freq)
            st.plotly_chart(fig_freq, use_container_width=True)
        st.write(" ")

        # Test date distribution
        attempt_df = test_df[test_df['test_name'].isin(['Anticipated Exam Date', 'Second Exam Attempt',
                                                         'Anticipated Test Date'])].copy()
        attempt_df['test_date'] = pd.to_datetime(attempt_df['test_date'], errors='coerce')
        attempt_df = attempt_df.dropna(subset=['test_date'])
        attempt_df['month_name'] = attempt_df['test_date'].dt.month_name()
        month_order = ['January', 'February', 'March', 'April', 'May']
        attempt_df = attempt_df[attempt_df['month_name'].isin(month_order)]

        if not attempt_df.empty:
            st.subheader("Test date distribution: Anticipated Exam Date and Second Exam Attempt")
            students_with_first_attempt = set(
                test_df.loc[test_df['test_name'] == 'First Attempt', 'student_id'].dropna().astype(int)
            )
            col1, col2 = st.columns(2)
            ant_df = attempt_df[attempt_df['test_name'].isin(['Anticipated Exam Date', 'Anticipated Test Date'])]
            sa_df = attempt_df[attempt_df['test_name'] == 'Second Exam Attempt']
            with col1:
                if not ant_df.empty:
                    stack_rows = []
                    for month in month_order:
                        month_students = ant_df[ant_df['month_name'] == month]
                        ids_in_month = month_students['student_id'].dropna().astype(int).unique()
                        reported = sum(1 for i in ids_in_month if i in students_with_first_attempt)
                        not_reported = len(ids_in_month) - reported
                        stack_rows.append({'Month': month, 'Segment': 'Reported exam score', 'Count': reported})
                        stack_rows.append({'Month': month, 'Segment': 'Not reported', 'Count': not_reported})
                    df_ant_stack = pd.DataFrame(stack_rows)
                    fig_ant = px.bar(df_ant_stack, x='Month', y='Count', color='Segment', barmode='stack',
                        title='Anticipated Exam Date — by month (Jan–May)',
                        color_discrete_map={'Reported exam score': '#10b981', 'Not reported': '#94a3b8'})
                    fig_ant.update_layout(xaxis_tickangle=-25, yaxis_title='Number of students', margin={'t': 80})
                    fig_ant = apply_light_mode_styling(fig_ant)
                    st.plotly_chart(fig_ant, use_container_width=True)
            with col2:
                if not sa_df.empty:
                    sa_counts = sa_df.groupby('month_name').size().reset_index(name='Count')
                    sa_counts = sa_counts[sa_counts['month_name'].isin(month_order)]
                    fig_sa = px.bar(sa_counts, x='month_name', y='Count',
                        title='Second Exam Attempt — by month',
                        color_discrete_sequence=[BRAND_COLORS['secondary']],
                        category_orders={'month_name': month_order})
                    fig_sa.update_layout(xaxis_title='Month', xaxis_tickangle=-25, margin={'t': 80})
                    fig_sa = apply_light_mode_styling(fig_sa)
                    st.plotly_chart(fig_sa, use_container_width=True)
        st.write(" ")

        # Interventions
        st.markdown("### Interventions")
        st.markdown("""
        Students are flagged for outreach based on the following intervention categories.

        **1. No reported practice exam scores** — Students who had not reported any practice exam scores.

        **2. No anticipated exam date** — Students who had not reported an anticipated exam date.

        **3. Low attendance in classes** — Students with low attendance.
        """)
        st.write(" ")

        interventions_path = None
        for path in ['Interventions_initial.csv', './Interventions_initial.csv']:
            if os.path.exists(path):
                interventions_path = path
                break

        if interventions_path:
            with open(interventions_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip() for line in f]
            group_ids = {
                'No reported practice scores': [],
                'No anticipated exam date': [],
                'Low attendance in classes': []
            }
            responded_ids = set()
            current = None
            for line in lines:
                if 'Students with No Reported Practice Exam Scores' in line:
                    current = 'No reported practice scores'
                    continue
                if 'Students with No Anticipated Exam Date' in line:
                    current = 'No anticipated exam date'
                    continue
                if 'Tier 3 Students' in line:
                    current = 'Low attendance in classes'
                    continue
                if current is None:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if not parts:
                    continue
                try:
                    sid = int(parts[0])
                    if sid > 0 and sid not in group_ids[current]:
                        group_ids[current].append(sid)
                    if current == 'Low attendance in classes':
                        responded = (len(parts) > 2 and parts[2].upper() == 'TRUE') or \
                                    (len(parts) > 3 and parts[3].upper() == 'TRUE')
                    else:
                        responded = len(parts) > 2 and parts[2].upper() == 'TRUE'
                    if responded:
                        responded_ids.add(sid)
                except (ValueError, IndexError):
                    continue

            all_intervention_ids = set()
            for ids in group_ids.values():
                all_intervention_ids.update(ids)

            n_total = len(all_intervention_ids)
            n_responded = len(responded_ids & all_intervention_ids)

            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.metric("Total intervened students", n_total)
            with ic2:
                st.metric("Responded to outreach", n_responded)
            with ic3:
                pct = f"{n_responded / n_total * 100:.0f}%" if n_total > 0 else "—"
                st.metric("Response rate", pct)
            st.write(" ")

            for group_name, ids in group_ids.items():
                if ids:
                    st.markdown(f"**{group_name}** — {len(ids)} students")
        else:
            st.info("Add **Interventions_initial.csv** to the project folder to see the interventions section.")

    else:
        st.info("Load test data (`institution-1-test-data.csv`) to see First Final Exam Score outcomes.")

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: EY 26 Programming
# ══════════════════════════════════════════════════════════════════════════════
elif view_mode == "EY 26 Programming":
    EY26_ASSETS_DIR = "ey26_assets"
    EY26_PDF_FILENAME = "calendars_side_by_side.pdf"
    EY26_PDF_PATH = os.path.join(EY26_ASSETS_DIR, EY26_PDF_FILENAME)
    _cursor_pdf_path = os.path.expanduser(
        "~/Library/Application Support/Cursor/User/workspaceStorage/bd0c71989d537611b6a480339d820d09/pdfs/bb5fac0d-c0dc-4881-a8cf-e9c1368e46d0/calendars side by side.pdf"
    )
    if not os.path.exists(EY26_PDF_PATH) and os.path.exists(_cursor_pdf_path):
        os.makedirs(EY26_ASSETS_DIR, exist_ok=True)
        try:
            shutil.copy2(_cursor_pdf_path, EY26_PDF_PATH)
        except Exception:
            pass

    st.title("EY26 Programming")
    st.write(" ")

    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0; font-size: 1rem; line-height: 1.45;">
    <p style="margin: 0 0 0.4rem 0;"><strong>Class days and times are flexible.</strong> For instance:</p>
    <ul style="margin: 0.25rem 0 0.4rem 1.25rem; padding-left: 0.5rem;">
    <li>A Monday–Wednesday class in the morning can be switched to a Tuesday–Thursday class in the evening.</li>
    <li>A three-day-per-week program that has four classes can be changed to a four-day-per-week program that has four classes.<br>
    <span style="display: block; margin-left: 1.5rem; margin-top: 0.25rem;"><strong>The number of classes per week stays the same.</strong></span></li>
    </ul>
    <p style="margin: 0.4rem 0 0.25rem 0;">Practice exam timing is also flexible.</p>
    <p style="margin: 0.5rem 0 0.25rem 0;"><strong>Goal:</strong> Finalize scheduling by end of March for EY26 so we can ensure proper instructor headcount.</p>
    <p style="margin: 0.4rem 0 0; font-weight: 600;">Brief update: Single instructor for all 100 students coming in June.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    st.subheader("Options")
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #3b82f6; background-color: #eff6ff; border-radius: 0 6px 6px 0;">
    All proposed options are informed by a retrospective analysis across two prior cohorts.
    The current cohort receives approximately <strong>240 hours</strong> of live instruction.
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    st.subheader("Summer 2026")
    summer_tabs = st.tabs(["Option I", "Option II", "Option III"])
    with summer_tabs[0]:
        st.markdown("**Cadence**")
        st.markdown("- June **with** small groups")
        st.markdown("- July Intensive")
        st.markdown("**What's included**")
        st.markdown("- Early small-group coaching; July intensive for increased content coverage.")
    with summer_tabs[1]:
        st.markdown("**Cadence**")
        st.markdown("- June **without** small groups")
        st.markdown("- July Intensive")
        st.markdown("**What's included**")
        st.markdown("- Standard timeline for small-group access; July intensive.")
    with summer_tabs[2]:
        st.markdown("**Cadence (not pictured)**")
        st.markdown("- Starting July, scholars begin the **Fall 2026** cadence.")
        st.markdown("- Large group: 2×/week, 2 hours each")
        st.markdown("- Small groups: every other week")

    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #2563eb; background-color: #eff6ff; border-radius: 0 6px 6px 0; color: #1e40af; font-size: 1rem;">
    Summer large group attendance is nearly double versus other seasons.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("**Why front-load chemistry and physics in summer**")
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0;">
    To support performance and align with engagement trends, we recommend front-loading foundational chemistry and physics in summer so fall can prioritize higher-yield topics and advanced applications.
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    st.subheader("Fall 2026")
    st.markdown("All options share the same fall cadence:")
    st.markdown("- **Large group:** 2×/week")
    st.markdown("- **Small groups:** every other week")
    st.write(" ")

    st.subheader("Spring 2026")
    st.markdown("If the proposed programs are adopted, **~190 of 240 hours** will be completed by end of December 2025.")
    st.write(" ")
    spring_tabs = st.tabs(["Option I (February end)", "Option II (March end)", "Option III (April end)"])
    _wk = """
    <div style="padding: 0.75rem 1rem; margin: 0.75rem 0; border-left: 3px solid #64748b; background-color: #f8fafc; border-radius: 0 6px 6px 0; font-size: 0.95rem;">
    <strong>Worth keeping in mind</strong><ul style="margin: 0.5rem 0 0 1rem; padding-left: 1rem;">
    """
    with spring_tabs[0]:
        st.markdown("**Intended end date:** February 2026")
        st.markdown("**Cadence:** Large group 2×/week; small groups once every 3 weeks through course end.")
        st.markdown("""| Component | Hours | Meeting details |\n|---|---|---|\n| Large group | 32 | 16 meetings at 2×/week |\n| Small group | 18 | 6 small groups × 3 meetings |""")
        st.markdown(_wk + "<li>Maintains higher-intensity pace after winter break.</li></ul></div>", unsafe_allow_html=True)
    with spring_tabs[1]:
        st.markdown("**Intended end date:** March 2026")
        st.markdown("**Cadence:** Large group 2×/week; small groups once monthly in Jan/Feb.")
        st.markdown("""| Component | Hours | Meeting details |\n|---|---|---|\n| Large group | 38 | 19 at 2×/week |\n| Small group | 12 | 6 small groups × 2 meetings |""")
        st.markdown(_wk + "<li>More flexible retest timeline.</li></ul></div>", unsafe_allow_html=True)
    with spring_tabs[2]:
        st.markdown("**Intended end date:** April 2026")
        st.markdown("**Cadence:** Small groups removed. Large groups 2×/week.")
        st.markdown("""| Component | Hours | Meeting details |\n|---|---|---|\n| Large group | 50 | 25 at 2×/week |\n| Small group | 0 | No meetings |""")
        st.markdown(_wk + "<li>Maximizes large group coverage for most Spring test dates.</li></ul></div>", unsafe_allow_html=True)
    st.write(" ")

    st.subheader("June: Option I vs Option II")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        st.markdown("**Option I** — Early invitations to small-group coaching.")
    with col_j2:
        st.markdown("**Option II** — Standard timeline for small-group coaching access.")
    st.write(" ")

    st.subheader("July: Option I vs Option II")
    col_jul1, col_jul2 = st.columns(2)
    with col_jul1:
        st.markdown("**Option I** — 4 meetings per week; increased content coverage.")
    with col_jul2:
        st.markdown("**Option II** — Fewer weekly meetings; lighter schedule.")
    st.write(" ")

    st.subheader("Calendars")
    if os.path.exists(EY26_PDF_PATH):
        try:
            import fitz
            doc = fitz.open(EY26_PDF_PATH)
            st.caption("Scroll to view all pages.")
            for i in range(len(doc)):
                page = doc.load_page(i)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                st.image(io.BytesIO(img_bytes), use_container_width=True)
            doc.close()
        except Exception as e:
            st.warning(f"Could not render PDF: {e}")
    else:
        st.info("Calendar PDF not found. Add **calendars_side_by_side.pdf** to the **ey26_assets** folder.")
    st.write(" ")

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: EY25 Scholars - March - April Outcomes, Scores, Tiers, and Intervention
# ══════════════════════════════════════════════════════════════════════════════
elif view_mode == "EY25 Scholars - March - April Outcomes, Scores, Tiers, and Intervention":
    st.header("EY25 Scholars - March - April Outcomes, Scores, Tiers, and Intervention")
    st.write(" ")

    st.markdown("""
    <div class="tier-flex">
        <div class="tier-column">
            <div class="tier1-text">Tier 1 Students</div>
            <div class="tier-criteria" style="color: #4CAF50;">Tier 1: &gt;5 exams reported</div>
            <div class="tier-criteria" style="color: #4CAF50;">Attendance in Large Group Sessions (&gt;70%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Attendance in Small Group Sessions (&gt;70%)</div>
        </div>
        <div class="tier-column">
            <div class="tier2-text">Tier 2 Students</div>
            <div class="tier-criteria" style="color: #FF9800;">Tier 2: 3-4 exams reported</div>
            <div class="tier-criteria" style="color: #FF9800;">Attendance in Large Group Sessions (50-69%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Attendance in Small Group Sessions (50-69%)</div>
        </div>
        <div class="tier-column">
            <div class="tier3-text">Tier 3 Students</div>
            <div class="tier-criteria" style="color: #EF5350;">Tier 3: &lt;2 exams reported</div>
            <div class="tier-criteria" style="color: #EF5350;">Attendance in Large Group Sessions (&lt;49%)</div>
            <div class="tier-criteria" style="color: #EF5350;">Attendance in Small Group Sessions (&lt;49%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    # ── Tier thresholds (documented here for transparency) ─────────────────────
    # Exam tier:        ≥5 = Tier 1 | 3-4 = Tier 2 | <3 = Tier 3
    # Attendance tier:  >70% = Tier 1 | 50-69% = Tier 2 | <50% = Tier 3
    # Participation tier: ≥60% = Tier 1 | 40-59% = Tier 2 | <40% = Tier 3
    # Overall tier:     worst of the three above

    # ── Load convata_data.csv ──────────────────────────────────────────────────
    convata_df = None
    for path in ['convata_data.csv', './convata_data.csv', 'student-data/convata_data.csv']:
        try:
            if os.path.exists(path):
                convata_df = pd.read_csv(path)
                break
        except Exception:
            continue

    if convata_df is None or convata_df.empty:
        st.info(
            "Data not found. Add **convata_data.csv** to the project folder to see the EY25 Scholars - March - April Outcomes, Scores, Tiers, and Intervention.\n\n"
            "Expected columns: Student ID, Name Surname, Email, Class Attendance, Class Participation, "
            "In-Class Accuracy, First Attempt, Next Attempt Date"
        )
        st.stop()

    # Clean and parse
    convata_df = convata_df.dropna(subset=['Student ID'])
    convata_df['Student ID'] = pd.to_numeric(convata_df['Student ID'], errors='coerce')
    convata_df = convata_df[convata_df['Student ID'].notna()].copy()
    convata_df['Student ID'] = convata_df['Student ID'].astype(int)

    for col in ['Class Attendance', 'Class Participation', 'In-Class Accuracy']:
        if col in convata_df.columns:
            convata_df[col] = convata_df[col].astype(str).str.replace('%', '').str.strip()
            convata_df[col] = pd.to_numeric(convata_df[col], errors='coerce').fillna(0) / 100

    convata_df['First Attempt'] = pd.to_numeric(convata_df.get('First Attempt', pd.Series(dtype=float)), errors='coerce')

    # ── Load roster (optional, private) ───────────────────────────────────────
    roster_df = None
    for path in ['roster.csv', './roster.csv']:
        try:
            if os.path.exists(path):
                roster_df = pd.read_csv(path)
                roster_df = roster_df.dropna(subset=['Student id'])
                roster_df['Student id'] = pd.to_numeric(roster_df['Student id'], errors='coerce')
                roster_df = roster_df[roster_df['Student id'].notna()].copy()
                roster_df['Student id'] = roster_df['Student id'].astype(int)
                break
        except Exception:
            continue

    # ── Load test data for exam counts ────────────────────────────────────────
    test_df_c = None
    for path in ['institution-1-test-data.csv', './institution-1-test-data.csv',
                 'student-data/institution-1-test-data.csv']:
        try:
            if os.path.exists(path):
                test_df_c = pd.read_csv(path)
                break
        except Exception:
            continue

    # ── Compute exam counts and highest practice score ─────────────────────────
    highest_practice_map = {}
    if test_df_c is not None and not test_df_c.empty:
        practice_mask = (
            ~test_df_c['test_name'].isin(['First Attempt', 'Second Exam Attempt',
                                          'Anticipated Test Date', 'Anticipated Exam Date']) &
            pd.to_numeric(test_df_c['actual_exam_score'], errors='coerce').between(472, 528)
        )
        practice_scores_c = test_df_c[practice_mask].copy()
        practice_scores_c['actual_exam_score'] = pd.to_numeric(practice_scores_c['actual_exam_score'], errors='coerce')
        highest_practice_map = practice_scores_c.groupby('student_id')['actual_exam_score'].max().apply(lambda x: str(int(x))).to_dict()

        exam_counts_c = (
            test_df_c[practice_mask]
            .groupby('student_id')
            .size()
            .reset_index(name='exam_count')
            .rename(columns={'student_id': 'Student ID'})
        )
        convata_df = convata_df.merge(exam_counts_c, on='Student ID', how='left')
        convata_df['exam_count'] = convata_df['exam_count'].fillna(0).astype(int)
    else:
        convata_df['exam_count'] = 0

    # ── Tier thresholds ────────────────────────────────────────────────────────
    def _att_tier(rate):
        if rate > 0.70: return 'Tier 1'
        if rate >= 0.50: return 'Tier 2'
        return 'Tier 3'

    def _par_tier(rate):
        if rate >= 0.60: return 'Tier 1'
        if rate >= 0.40: return 'Tier 2'
        return 'Tier 3'

    def _exam_tier(n):
        if n >= 5: return 'Tier 1'
        if n >= 3: return 'Tier 2'
        return 'Tier 3'

    # ── Compute tiers ──────────────────────────────────────────────────────────
    convata_df['Attendance Tier'] = convata_df['Class Attendance'].apply(_att_tier)
    convata_df['Participation Tier'] = convata_df['Class Participation'].apply(_par_tier)
    convata_df['Exam Tier'] = convata_df['exam_count'].apply(_exam_tier)
    convata_df['Overall Tier Num'] = convata_df.apply(
        lambda r: max(tier_num(r['Attendance Tier']), tier_num(r['Participation Tier']), tier_num(r['Exam Tier'])),
        axis=1
    )
    convata_df['Overall Tier'] = convata_df['Overall Tier Num'].map({1: 'Tier 1', 2: 'Tier 2', 3: 'Tier 3'})

    # ── Score outcome ──────────────────────────────────────────────────────────
    def score_outcome(score):
        if pd.isna(score): return 'No score reported'
        if score >= 502:   return 'Passing'
        if score >= 495:   return 'Borderline'
        return 'Below 495'

    convata_df['Score Outcome'] = convata_df['First Attempt'].apply(score_outcome)

    # ── Cohort-level aggregates ────────────────────────────────────────────────
    n_students    = len(convata_df)
    n_passing     = int((convata_df['First Attempt'] >= 502).sum())
    pct_passing   = n_passing / n_students if n_students > 0 else 0
    avg_attendance    = convata_df['Class Attendance'].mean()
    avg_participation = convata_df['Class Participation'].mean()

    # ── Load mcat_source_data.csv for first exam dates and took-no-score list ──
    mcat_src = None
    for path in ['mcat_source_data.csv', './mcat_source_data.csv', 'student-data/mcat_source_data.csv']:
        try:
            if os.path.exists(path):
                mcat_src = pd.read_csv(path)
                break
        except Exception:
            continue

    first_exam_date_map = {}
    took_no_score_list = []
    if mcat_src is not None and not mcat_src.empty:
        for _, mr in mcat_src.iterrows():
            sid = mr.get('student_id')
            d = str(mr.get('first_exam_date', '')).strip()
            if pd.notna(sid):
                first_exam_date_map[int(sid)] = d if d not in ('', 'nan', '—') else '—'
            if str(mr.get('category', '')).strip() == 'took_no_score':
                _sid_int = int(sid) if pd.notna(sid) else None
                took_no_score_list.append({
                    'Student ID':              _sid_int if _sid_int else '—',
                    '1st Exam Date':           d if d not in ('', 'nan') else '—',
                    'Highest Practice Score':  highest_practice_map.get(_sid_int, '—') if _sid_int else '—',
                    'College':                 mr.get('college', ''),
                })

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — Score Outcome Distribution
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("Score Outcomes")
    outcome_order = ['Passing', 'Borderline', 'Below 495', 'No score reported']
    outcome_counts_c = convata_df['Score Outcome'].value_counts()
    outcome_data = []
    for o in outcome_order:
        cnt = int(outcome_counts_c.get(o, 0))
        pct = cnt / n_students * 100 if n_students > 0 else 0
        outcome_data.append({'Outcome': o, 'Count': cnt, 'Pct': f"{pct:.1f}%"})
    df_outcome_c = pd.DataFrame(outcome_data)

    oc1, oc2, oc3, oc4 = st.columns(4)
    for col_w, row in zip([oc1, oc2, oc3, oc4], outcome_data):
        with col_w:
            st.metric(row['Outcome'], f"{row['Count']} ({row['Pct']})")
    st.write(" ")

    fig_outcome_c = px.bar(
        df_outcome_c, x='Outcome', y='Count', color='Outcome',
        color_discrete_map=OUTCOME_COLORS,
        title='First Attempt score outcome — full cohort',
        text='Count',
        category_orders={'Outcome': outcome_order}
    )
    fig_outcome_c.update_traces(textposition='outside')
    fig_outcome_c.update_layout(showlegend=False, margin={'t': 60})
    fig_outcome_c = apply_light_mode_styling(fig_outcome_c)
    st.plotly_chart(fig_outcome_c, use_container_width=True)
    st.write(" ")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — Took Test, Score Not Yet Reported
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("Took Test — Score Not Yet Reported")
    st.caption(
        f"{len(took_no_score_list)} students whose 1st exam date has passed "
        "but no score has been reported. These students need follow-up."
    )
    st.write(" ")
    if took_no_score_list:
        df_no_score = pd.DataFrame(took_no_score_list).sort_values('1st Exam Date')
        st.markdown(df_no_score.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.success("All students whose exam date has passed have reported a score.")
    st.write(" ")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — Detailed Student Table
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("Student Detail")
    st.write(" ")

    # Sort: Tier 3 first, then by score urgency within tier
    outcome_sort_map = {'No score reported': 0, 'Below 495': 1, 'Borderline': 2, 'Passing': 3}
    convata_df['_outcome_sort'] = convata_df['Score Outcome'].map(outcome_sort_map)
    detail_sorted = convata_df.sort_values(
        ['Overall Tier Num', '_outcome_sort', 'Class Attendance'],
        ascending=[False, True, True]
    )

    # Split into intervention (not passing) and passing
    intervention_df = detail_sorted[detail_sorted['Score Outcome'] != 'Passing']
    passing_df      = detail_sorted[detail_sorted['Score Outcome'] == 'Passing']

    # Split intervention into non-April and April exam dates
    def _is_april(sid):
        date_str = first_exam_date_map.get(int(sid), '—')
        return str(date_str).startswith('4')

    intervention_non_april = intervention_df[~intervention_df['Student ID'].apply(_is_april)]
    intervention_april     = intervention_df[intervention_df['Student ID'].apply(_is_april)]

    def _render_intervention_tables(df_subset):
        tier_rows = []
        for _, row in df_subset.iterrows():
            sid = int(row['Student ID'])
            score = row['First Attempt']
            score_display = str(int(score)) if pd.notna(score) else "—"
            next_date = str(row.get('Next Attempt Date', ''))
            next_date = next_date if next_date.strip() not in ('', 'nan') else "—"
            tier_rows.append({
                'Student ID':              sid,
                'Overall Tier':            tier_badge(row['Overall Tier']),
                'Exam Tier':               tier_badge(row['Exam Tier']),
                'Attendance Tier':         tier_badge(row['Attendance Tier']),
                'Participation Tier':      tier_badge(row['Participation Tier']),
                'Highest Practice Score':  highest_practice_map.get(sid, '—'),
                '1st Exam Date':           first_exam_date_map.get(sid, '—'),
                'First Attempt':           score_display,
                'Next Attempt Date':       next_date,
            })
        df_tier_table = pd.DataFrame(tier_rows)
        st.markdown(df_tier_table.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.write(" ")

        detail_rows = []
        for _, row in df_subset.iterrows():
            score = row['First Attempt']
            score_display = str(int(score)) if pd.notna(score) else "—"
            next_date = str(row.get('Next Attempt Date', ''))
            next_date = next_date if next_date.strip() not in ('', 'nan') else "—"
            detail_rows.append({
                'Student ID':        int(row['Student ID']),
                'Exams Reported':    int(row['exam_count']),
                'Attendance':        f"{row['Class Attendance']:.1%}",
                'Participation':     f"{row['Class Participation']:.1%}",
                'In-Class Accuracy': f"{row['In-Class Accuracy']:.1%}",
                'First Attempt':     score_display,
                'Score Outcome':     outcome_badge(row['Score Outcome']),
                'Next Attempt Date': next_date,
            })
        df_detail_table = pd.DataFrame(detail_rows)
        st.markdown(df_detail_table.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ── Students Needing Intervention ─────────────────────────────────────────
    st.markdown("#### Students Needing Intervention")
    st.caption("Missing score or First Attempt below 502 — sorted by urgency within tier. Tiers were tracked for attendance and participation from March 2nd onward. Exam tiers were tracked since the beginning of the program.")

    if intervention_non_april.empty:
        st.success("All non-April students with reported scores are passing (≥502).")
    else:
        _render_intervention_tables(intervention_non_april)

    st.write(" ")

    # ── April Test-Takers Needing Intervention ────────────────────────────────
    st.markdown("#### April Test-Takers Needing Intervention")
    st.caption("Students with a first exam date in April — missing score or First Attempt below 502.")

    if intervention_april.empty:
        st.success("No April test-takers require intervention.")
    else:
        _render_intervention_tables(intervention_april)

    st.write(" ")

    # ── Passing Students ───────────────────────────────────────────────────────
    with st.expander(f"Passing students ({len(passing_df)})", expanded=False):
        st.caption("Students with First Attempt ≥ 502.")
        if passing_df.empty:
            st.info("No students have reported a passing score yet.")
        else:
            passing_rows = []
            for _, row in passing_df.iterrows():
                score = row['First Attempt']
                score_display = str(int(score)) if pd.notna(score) else "—"
                next_date = str(row.get('Next Attempt Date', ''))
                next_date = next_date if next_date.strip() not in ('', 'nan') else "—"
                passing_rows.append({
                    'Student ID':        int(row['Student ID']),
                    '1st Exam Date':     first_exam_date_map.get(int(row['Student ID']), '—'),
                    'First Attempt':     score_display,
                    'Next Attempt Date': next_date,
                })
            df_passing = pd.DataFrame(passing_rows)
            st.markdown(df_passing.to_html(escape=False, index=False), unsafe_allow_html=True)
