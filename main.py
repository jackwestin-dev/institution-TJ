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

# Custom CSS for styling (no external font import to avoid CSP/load errors)
st.markdown("""
<style>
/* Global styling */
.main {
 font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
 background-color: #ffffff !important;
 color: #1e293b !important;
 }
 
 /* Remove all metric boxes - display as clean text lists */
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
 
 /* Remove boxes from Success/Info/Warning messages */
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
 
 /* Tier definition styling */
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

 /* Tier showcase buttons (Exam / Large Group / Small Group) */
 .tier-button-block { margin-bottom: 1rem; }
 .tier-button-label { font-weight: bold; color: #1e293b; font-size: 1rem; margin-bottom: 0.35rem; }
 .tier-button {
     display: inline-block; padding: 0.6rem 1.5rem; border-radius: 12px; font-weight: bold;
     color: white !important; font-size: 1.1rem; text-align: center; min-width: 80px;
 }

 /* Section headers */
 h1, h2, h3 {
     font-family: 'Inter', sans-serif !important;
     font-weight: 600 !important;
     color: #1e293b !important;
 }

 h1 {
     font-size: 2.25rem !important;
     margin-bottom: 1rem !important;
 }

 h2 {
     font-size: 1.875rem !important;
     margin-bottom: 1rem !important;
     color: #334155 !important;
 }

 h3 {
     font-size: 1.5rem !important;
     margin-bottom: 0.75rem !important;
     color: #475569 !important;
 }
</style>
""", unsafe_allow_html=True)

# Design system colors
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

@st.cache_data
def load_jfd_data():
 """Load and prepare the JFD combined data."""
 import os
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
     except Exception as e:
         continue

 if jfd_df is not None:
     # Clean data
     jfd_df['highest_exam_score'] = pd.to_numeric(jfd_df['highest_exam_score'], errors='coerce')
     jfd_df['exam_count'] = pd.to_numeric(jfd_df['exam_count'], errors='coerce').fillna(0).astype(int)
     # Fill NaN in tier columns with a placeholder for easier filtering and display
     tier_cols = ['survey_tier', 'large_group_tier', 'small_group_tier', 'class_participation_tier']
     for col in tier_cols:
         if col in jfd_df.columns:
             jfd_df[col] = jfd_df[col].fillna('N/A')

 return jfd_df

def get_chart_colors():
 """Get consistent color palette for charts"""
 return BRAND_COLORS['chart_palette']

def apply_light_mode_styling(fig):
    """Apply consistent light mode styling to Plotly charts"""
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

    # Try to update coloraxis if it exists
    try:
        fig.update_layout(
            coloraxis_colorbar=dict(
                tickfont=dict(color='#1e293b', size=10),
                title_font=dict(color='#1e293b', size=11)
            )
        )
    except:
        pass

    # Update traces safely - only add properties that are valid for all trace types
    try:
        fig.update_traces(marker_line_color='#1e293b')
    except:
        pass

    return fig

st.title('Institution TJ - Scholar Dashboard')

# Password protection (optional - only if secrets are configured)
def check_password():
     """Returns `True` if the user had the correct password."""

     def password_entered():
         """Checks whether a password entered by the user is correct."""
         try:
             if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
                 st.session_state["password_correct"] = True
                 del st.session_state["password"] # Don't store the password.
             else:
                 st.session_state["password_correct"] = False
         except:
             # If secrets are not configured, skip password protection
             st.session_state["password_correct"] = True
             if "password" in st.session_state:
                 del st.session_state["password"]

     # Return True if the password is validated.
     if st.session_state.get("password_correct", False):
         return True

     # Check if secrets are configured
     try:
         test_secret = st.secrets["password"]
         # Show input for password if secrets are configured
         st.text_input(
             "Password", type="password", on_change=password_entered, key="password"
         )
         if "password_correct" in st.session_state:
             st.error("😕 Password incorrect")
         return False
     except:
         # No secrets configured, skip password protection
         return True

if not check_password():
    st.stop() # Do not continue if check_password is not True.

# Sidebar Navigation
st.sidebar.title("Navigation")
view_mode = st.sidebar.radio(
    "View",
    ["Current Status EY25", "Individual Student Data - EY25", "EY25 Summer Retester Cohort", "EY 26 Programming"],
    label_visibility="visible",
)

# Student roster reference (dropdown at top of page) — hidden on EY26/EY25 Summer programming pages
if view_mode not in ("EY 26 Programming", "EY25 Summer Retester Cohort"):
    roster_path = None
    for path in ['roster.csv', './roster.csv']:
        if os.path.exists(path):
            roster_path = path
            break
    if roster_path:
        roster_df = pd.read_csv(roster_path)
        with st.expander("Student roster (reference)", expanded=False):
            st.dataframe(roster_df.rename(columns={'student_id': 'Student ID', 'name': 'Name'}), use_container_width=True, hide_index=True)

if view_mode == "Individual Student Data - EY25":
    # Individual Student Dashboard
    ## Read data from CSV files (with error handling)
    import os

    # Try multiple possible paths (project root / TJEY25 first, then student-data/)
    data_paths = [
        '',  # Project root (e.g. TJEY25)
        './',
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
            # Optionally load test data (practice exam scores) if present at same path
            test_path = f'{base_path}institution-1-test-data.csv'
            if os.path.exists(test_path):
                df_test_scores = pd.read_csv(test_path, parse_dates=['test_date'])
                df_test_scores['test_date'] = pd.to_datetime(df_test_scores['test_date']).dt.date
                test_data_available = True
            else:
                df_test_scores = None
            break
        except Exception as e:
            continue

    # If engagement loaded but test data wasn't (e.g. engagement in student-data/, test in root), try loading exam data from other paths
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
        st.info("The Individual Student Dashboard requires:")
        st.markdown("""
        **Required (in this project folder or student-data/):**
        - `institution-1-engagement-data.csv`

        **Optional (for Practice Exam Scores section):**
        - `institution-1-test-data.csv`
 
        **Current directory contents:**
        """)

        # Show current directory contents for debugging
        current_files = []
        try:
            current_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            if current_files:
                st.markdown("**CSV files in root directory:**")
                for f in current_files:
                    st.write(f"- {f}")

            if os.path.exists('student-data'):
                student_files = [f for f in os.listdir('student-data') if f.endswith('.csv')]
                if student_files:
                    st.markdown("**CSV files in student-data/ directory:**")
                    for f in student_files:
                        st.write(f"- student-data/{f}")
            else:
                st.write("- student-data/ directory not found")
        except:
            st.write("- Unable to list directory contents")

    if individual_data_available:
        ## Create dashboard filters
        student_id = st.selectbox("Choose a student:", list(df_engagement_attendance['student_id'].unique()))

        st.markdown("**Surveys & resources:**")
        st.markdown("- [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)")
        st.write(' ')

        # Load tier.csv for attendance tier buttons (from build_tier_csv.py)
        tier_df = None
        for path in ['tier.csv', './tier.csv']:
            try:
                if os.path.exists(path):
                    tier_df = pd.read_csv(path)
                    break
            except Exception:
                continue

        # Tier definitions (side-by-side, color-coded)
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

        # Tier text table (from JFD data when available — text only, no analysis)
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

        ## Transform dataframes
        df_engagement_attendance_student_filtered = df_engagement_attendance[df_engagement_attendance['student_id'] == student_id]
        # Create date_range column for tooltips
        df_engagement_attendance_student_filtered['date_range'] = df_engagement_attendance_student_filtered.apply(
        lambda row: f"{row['start_date'].strftime('%m/%d/%y')} - {row['end_date'].strftime('%m/%d/%y')}", 
        axis=1
        )
        # Coerce numeric; avoid division by zero for attendance rates
        for col in ['num_attended_large_session', 'num_scheduled_large_session', 'num_attended_small_session', 'num_scheduled_small_session']:
            if col in df_engagement_attendance_student_filtered.columns:
                df_engagement_attendance_student_filtered[col] = pd.to_numeric(df_engagement_attendance_student_filtered[col], errors='coerce').fillna(0)
        # Weekly attendance rate (this week only): large = 2 classes → 0%, 50%, 100%; small = 0 or 1 session → 0% or 100%
        denom_lg = df_engagement_attendance_student_filtered['num_scheduled_large_session'].replace(0, np.nan)
        denom_sm = df_engagement_attendance_student_filtered['num_scheduled_small_session'].replace(0, np.nan)
        df_engagement_attendance_student_filtered['large_session'] = (
            df_engagement_attendance_student_filtered['num_attended_large_session'] / denom_lg
        )
        df_engagement_attendance_student_filtered['small_session'] = (
            df_engagement_attendance_student_filtered['num_attended_small_session'] / denom_sm
        )
        df_engagement_attendance_avg = df_engagement_attendance_student_filtered[['class_participation','homework_participation','cars_accuracy','sciences_accuracy','class_accuracy']].mean()

        class_participation = df_engagement_attendance_avg.loc['class_participation']
        homework_participation = df_engagement_attendance_avg.loc['homework_participation']
        overall_participation = (class_participation + homework_participation) / 2

        if test_data_available:
            df_test_scores_student_filtered = df_test_scores[df_test_scores['student_id'] == student_id]
        else:
            df_test_scores_student_filtered = None

        ## Create sections and render dashboard (engagement data only; tier and exam-section data removed)
        st.write(' ')
        st.write(' ')

        # Tier showcase buttons: 6 labels total — for each period (Jun-Dec 2025, Jan 2026-Current): Exam Tier, Large Group, Small Group
        def tier_button_color(tier_str):
            if not tier_str or tier_str == "—" or "No " in str(tier_str):
                return "#9E9E9E"
            if "Tier 1" in str(tier_str):
                return "#4CAF50"
            if "Tier 2" in str(tier_str):
                return "#FF9800"
            if "Tier 3" in str(tier_str):
                return "#EF5350"
            return "#9E9E9E"

        exam_count = len(df_test_scores_student_filtered) if (test_data_available and df_test_scores_student_filtered is not None and not df_test_scores_student_filtered.empty) else 0
        if not test_data_available or df_test_scores_student_filtered is None:
            exam_tier_str = "—"
        elif exam_count > 5:
            exam_tier_str = "Tier 1"
        elif 3 <= exam_count <= 4:
            exam_tier_str = "Tier 2"
        else:
            exam_tier_str = "Tier 3"  # <2 exams (0, 1, or 2)

        # Get tier row for each period from tier.csv
        row_jundec = None
        row_jan = None
        if tier_df is not None and 'student_id' in tier_df.columns:
            student_tiers = tier_df[tier_df['student_id'] == student_id]
            if not student_tiers.empty:
                jundec = student_tiers[student_tiers['date_window'] == 'Jun-Dec 2025']
                jan = student_tiers[student_tiers['date_window'] == 'Jan 2026-Current']
                row_jundec = jundec.iloc[0] if not jundec.empty else None
                row_jan = jan.iloc[0] if not jan.empty else None
        large_jundec = row_jundec['large_group_tier'] if row_jundec is not None and 'large_group_tier' in row_jundec.index else "—"
        small_jundec = row_jundec['small_group_tier'] if row_jundec is not None and 'small_group_tier' in row_jundec.index else "—"
        large_jan = row_jan['large_group_tier'] if row_jan is not None and 'large_group_tier' in row_jan.index else "—"
        small_jan = row_jan['small_group_tier'] if row_jan is not None and 'small_group_tier' in row_jan.index else "—"

        # Six blocks stacked: top row = Jun-Dec 2025, bottom row = Jan 2026-Current
        st.markdown("**Jun-Dec 2025**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Exam Tier</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(exam_tier_str)};">{exam_tier_str}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Large Group attendance</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(large_jundec)};">{large_jundec}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Small Group Attendance</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(small_jundec)};">{small_jundec}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.write(' ')
        st.markdown("**Jan 2026-Current**")
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Exam Tier</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(exam_tier_str)};">{exam_tier_str}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with c5:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Large Group attendance</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(large_jan)};">{large_jan}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with c6:
            st.markdown(
                f'<div class="tier-button-block">'
                f'<div class="tier-button-label">Small Group Attendance</div>'
                f'<div class="tier-button" style="background-color: {tier_button_color(small_jan)};">{small_jan}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.write(' ')

        # Practice Exam Scores section — only if institution-1-test-data.csv is present
        if test_data_available and df_test_scores_student_filtered is not None and not df_test_scores_student_filtered.empty:
            st.header('Practice Exam Scores')
            st.caption('Updated through February 24.')
            st.subheader('8 Exams are Required for the JW MCAT Course, 4 Are Due by December 31, 2025')
            st.write('Students were asked to update us with practice exam schedules and scores throughout the program.')
            st.write(' ')
            exam_display = df_test_scores_student_filtered[['test_name', 'test_date', 'actual_exam_score']].copy()
            if jfd_df is not None and 'student_id' in jfd_df.columns:
                jfd_student = jfd_df[jfd_df['student_id'] == student_id]
                if not jfd_student.empty:
                    for c in tier_cols:
                        if c in jfd_student.columns:
                            exam_display[c.replace('_', ' ').title()] = jfd_student[c].iloc[0]
            st.dataframe(exam_display, use_container_width=True)
            st.write(' ')
            point_exam_scores = alt.Chart(df_test_scores_student_filtered).mark_point().transform_fold(
                fold=['actual_exam_score'],
                as_=['variable','value']
            ).encode(
                x=alt.X(
                    'yearmonthdate(test_date):O',
                    axis=alt.Axis(labelAngle=-45, title='Test Date'),
                ),
                y=alt.Y(
                    'value:Q',
                    axis=alt.Axis(title='Practice Exam Score'),
                    scale=alt.Scale(domain=[470, 528])
                ),
                tooltip=[
                    alt.Tooltip('test_date:T', title='Test Date'),
                    alt.Tooltip('value:Q', title='Exam Score')
                ],
                color=alt.Color(
                    'variable:N',
                    legend=alt.Legend(title='Exam Scores', orient='bottom', labelExpr="'Practice Exam Score'")
                )
            )
            st.altair_chart(point_exam_scores, use_container_width=True)
            st.write(' ')
        elif test_data_available and (df_test_scores_student_filtered is None or df_test_scores_student_filtered.empty):
            st.info('No practice exam records for this student.')
            st.write(' ')

        # Attendance (right beneath exams)
        st.header('Attendance')
        _att_max = df_engagement_attendance_student_filtered['end_date'].max() if not df_engagement_attendance_student_filtered.empty and 'end_date' in df_engagement_attendance_student_filtered.columns else None
        _att_through = _att_max.strftime('%B %d, %Y') if _att_max is not None and hasattr(_att_max, 'strftime') else '—'
        st.caption(f'Updated through {_att_through}.')
        st.write(
            'Below demonstrates the weekly percentage of attendance by students within our "All Student" and "Small Group" classes.\n\n'
            'For example, if there are two large classes and a student attends one of them, they would receive a 50% attendance rate for that week. '
            'A data point with 0% indicates no attendance during that week, while the absence of a data point reflects that no classes were held that week.'
        )
        st.write(' ')
        st.write(' ')

        line_attendance = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
            fold=['large_session', 'small_session'],
            as_=['variable', 'value']
        ).encode(
            x=alt.X(
                'week:O',
                axis=alt.Axis(
                    labelAngle=0,
                    title='Week'
                )
            ),
            y=alt.Y(
                'value:Q',
                axis=alt.Axis(
                    title='Weekly Attendance Rate',
                    format='%'
                ),
                scale=alt.Scale(domain=[0, 1])
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Weekly Attendance Rate', format='0.0%')
            ],
            color=alt.Color(
                'variable:N',
                legend=alt.Legend(
                    title='Session Type',
                    orient='bottom',
                    labelExpr="datum.value == 'large_session' ? 'Classes with All Students' : 'Small Group Sessions'"
                )
            )
        )

        st.altair_chart(line_attendance, use_container_width=True)

        st.write(' ')
        st.write(' ')

        # Data through week 29 only for question sets, accuracy, and completed lessons (attendance and exams show all data)
        df_through_week_29 = df_engagement_attendance_student_filtered[df_engagement_attendance_student_filtered['week'] <= 29]
        _w29_max = df_through_week_29['end_date'].max() if not df_through_week_29.empty else None
        _w29_through = _w29_max.strftime('%B %d, %Y') if _w29_max is not None and hasattr(_w29_max, 'strftime') else '—'

        # Completed Question Sets (x-axis stops at week 29)
        st.header('Completed Question Sets')
        st.caption(f'Updated through {_w29_through}.')
        st.write('This graph displays the number of question sets completed within our question bank per week. Question sets usually range between 5 to 10 questions, and can be discrete or passage-based questions.')
        st.write(' ')
        st.write(' ')

        line_question_sets = alt.Chart(df_through_week_29).mark_line(point=True).encode(
            x=alt.X(
                'week:O',
                axis=alt.Axis(
                    labelAngle=0,
                    title='Week'
                )
            ),
            y=alt.Y(
                'total_completed_passages_discrete_sets',
                axis=alt.Axis(
                    title='Completed Number of Question Sets'
                )
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('total_completed_passages_discrete_sets', title='Completed Count')
            ],
        )

        st.altair_chart(line_question_sets, use_container_width=True)

        st.write(' ')
        st.write(' ')

        # Accuracy
        st.header('Accuracy')
        st.subheader('Average Accuracy (%) on Question Sets Per Week')
        st.caption(f'Updated through {_w29_through}.')
        st.write(
            'During Session Practice: "In-Class Questions" refer to a student\'s accuracy percentage for question sets specifically given during class. '
            'That being said, these percentages will not be present if a student did not attempt the class activity. Also, to note, a data point will not be present if there was no class during a certain week.\n\n'
            'Self-Learning Practice: "CARS Questions" and "Science Questions" refer to a student\'s weekly performance on independent practice sets that they complete independently. Data points will be present for all weeks the student completed a passage or question set.'
        )
        st.write(' ')
        st.write(' ')

        line_engagement_accuracy = alt.Chart(df_through_week_29).mark_line(point=True).transform_fold(
            fold=['sciences_accuracy', 'cars_accuracy', 'class_accuracy'],
            as_=['variable', 'value']
        ).encode(
            x=alt.X(
                'week:O',
                axis=alt.Axis(
                    labelAngle=0,
                    title='Week'
                )
            ),
            y=alt.Y(
                'value:Q',
                axis=alt.Axis(
                    title='Average Accuracy (%)',
                    format='%'
                )
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Accuracy Rate', format='0.1%')
            ],
            color=alt.Color(
                'variable:N',
                legend=alt.Legend(
                    title='Subject',
                    orient='bottom',
                    labelExpr="datum.value == 'cars_accuracy' ? 'CARS Questions' : datum.value == 'class_accuracy' ? 'In-Class Questions' : 'Science Questions'"
                )
            )
        )

        st.altair_chart(line_engagement_accuracy, use_container_width=True)

        st.write(' ')
        st.write(' ')

        # Completed Lessons (last)
        st.header('Completed Lessons')
        st.subheader('Self-Learning with Jack Westin Course or Question Bank')
        st.caption(f'Updated through {_w29_through}.')
        st.write('This graph displays the number of video lessons or assignments within the Self-Paced JW Complete MCAT Course completed by the student per week.')
        st.write(' ')
        st.write(' ')

        line_engagement = alt.Chart(df_through_week_29).mark_line(point=True).transform_fold(
            ['completed_lessons'],
            as_=['variable', 'value']
        ).encode(
            x=alt.X(
                'week:O',
                axis=alt.Axis(
                    labelAngle=0,
                    title='Week'
                )
            ),
            y=alt.Y(
                'value:Q',
                axis=alt.Axis(
                    title='Completed Count',
                )
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Completed Number of Lessons')
            ],
            color=alt.Color(
                'variable:N',
                legend=alt.Legend(
                    title='Type',
                    orient='bottom',
                    labelExpr="'Completed Course Lessons'"
                )
            )
        )

        st.altair_chart(line_engagement, use_container_width=True)

elif view_mode == "EY25 Summer Retester Cohort":
    # -------------------------------------------------------------------------
    # EY25 Summer Retester Cohort (JFD-facing; format similar to EY26 Programming)
    # Ahmed may adjust copy or exam dates below.
    # -------------------------------------------------------------------------
    st.title("EY25 Summer Retester Cohort")
    st.write(" ")

    # Green box on top: flexibility and goal (no brief update)
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0; font-size: 1rem; line-height: 1.45;">
    <p style="margin: 0 0 0.4rem 0;"><strong>Class days and times are flexible.</strong> For instance:</p>
    <ul style="margin: 0.25rem 0 0.4rem 1.25rem; padding-left: 0.5rem;">
    <li>A Monday–Wednesday class in the morning can be switched to a Tuesday–Thursday class in the evening.</li>
    <li>A three-day-per-week program that has four classes can be changed to a four-day-per-week program that has four classes.<br><span style="display: block; margin-left: 1.5rem; margin-top: 0.25rem;"><strong>The number of classes per week stays the same.</strong></span></li>
    </ul>
    <p style="margin: 0.4rem 0 0.25rem 0;">Practice exam timing is also flexible: we can move mandatory practice exam due dates around. These are our recommendations, but they're flexible.</p>
    <p style="margin: 0.5rem 0 0.25rem 0;"><strong>Goal:</strong> Finalize scheduling by end of March for EY25 so we can ensure proper instructor headcount.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    # Intro bullets (including EY24 cohort and attendance)
    st.markdown("""
    - Designed for scholars sitting for summer AAMC exams.
    - Aligns with official AAMC test dates and historical second-attempt trends.
    - Includes built-in benchmarking and structured exam pacing.
    - 85% of students in the EY24 cohort had taken their exam by the end of July. Attendance tended to drop prior to exam dates. That makes sense. Students value the breathing room between class and their next exam to have the week to focus on preparing for it.
    """)
    st.write(" ")

    # Recommended requirements (above tabs)
    st.info("**Second Attempt recommended requirements** — Students must complete **3 full-length exams** between their first and second attempts. This ensures adequate benchmarking and readiness.")
    st.write(" ")
    st.markdown("**Summer Program Student recommended requirements**")
    st.markdown("- 1 full-length exam completed before the start of the summer program.")
    st.markdown("- 2 additional full-length exams completed during the summer.")
    st.markdown("- *Exception:* Students testing June 12 or June 13 may have adjusted requirements due to limited timeline.")
    st.write(" ")

    # Tabs: Option 1 | Option 2 (Option not Model)
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
    # Comparison note at bottom
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #64748b; background-color: #f8fafc; border-radius: 0 6px 6px 0;">
    <strong>Comparison</strong> — Option 1 prioritizes structured exam benchmarking and formal study breaks. Option 2 prioritizes consistent weekly cadence with lighter pacing.
    </div>
    """, unsafe_allow_html=True)

    # Optional: retaker cohort PDF (add retaker_cohort_side_by_side.pdf to ey25_summer_assets/ to display)
    EY25_SUMMER_ASSETS = "ey25_summer_assets"
    EY25_SUMMER_PDF = os.path.join(EY25_SUMMER_ASSETS, "retaker_cohort_side_by_side.pdf")
    _cursor_retaker = os.path.expanduser("~/Library/Application Support/Cursor/User/workspaceStorage/bd0c71989d537611b6a480339d820d09/pdfs/2845df9b-0ed3-4dca-90f4-21c9b04b9f17/retaker cohort side by side.pdf")
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

elif view_mode == "EY 26 Programming":
    # -------------------------------------------------------------------------
    # EY26 Programming: embedded calendar PDF at top (scrollable), options below.
    # Place your PDF in ey26_assets/calendars_side_by_side.pdf (or it will be copied from Cursor upload path if present).
    # -------------------------------------------------------------------------
    EY26_ASSETS_DIR = "ey26_assets"
    EY26_PDF_FILENAME = "calendars_side_by_side.pdf"
    EY26_PDF_PATH = os.path.join(EY26_ASSETS_DIR, EY26_PDF_FILENAME)
    # If user uploaded PDF via Cursor, copy from workspace storage into project so app can load it
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

    # Top-of-page: flexibility and goal (bullets, reduced spacing)
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0; font-size: 1rem; line-height: 1.45;">
    <p style="margin: 0 0 0.4rem 0;"><strong>Class days and times are flexible.</strong> For instance:</p>
    <ul style="margin: 0.25rem 0 0.4rem 1.25rem; padding-left: 0.5rem;">
    <li>A Monday–Wednesday class in the morning can be switched to a Tuesday–Thursday class in the evening.</li>
    <li>A three-day-per-week program that has four classes can be changed to a four-day-per-week program that has four classes.<br><span style="display: block; margin-left: 1.5rem; margin-top: 0.25rem;"><strong>The number of classes per week stays the same.</strong></span></li>
    </ul>
    <p style="margin: 0.4rem 0 0.25rem 0;">Practice exam timing is also flexible: we can move mandatory practice exam due dates around. These are our recommendations, but they’re flexible.</p>
    <p style="margin: 0.5rem 0 0.25rem 0;"><strong>Goal:</strong> Finalize scheduling by end of March for EY26 so we can ensure proper instructor headcount.</p>
    <p style="margin: 0.4rem 0 0; font-weight: 600;">Brief update: Single instructor for all 100 students coming in June.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    # Options (text above the calendar view)
    st.subheader("Options")

    # B) Program framing (callout)
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #3b82f6; background-color: #eff6ff; border-radius: 0 6px 6px 0;">
    All proposed options are informed by a retrospective analysis across two prior cohorts. The current cohort receives approximately <strong>240 hours</strong> of live instruction. Based on observed engagement patterns and outcome data, this total can be intentionally adjusted upward or downward throughout the year to better align with scholar needs.
    </div>
    """, unsafe_allow_html=True)
    st.write(" ")

    # C) Summer 2026 (tabs)
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
        st.markdown("- Starting July, scholars begin the **Fall 2026** cadence:")
        st.markdown("- Large group: 2×/week, 2 hours each")
        st.markdown("- Small groups: every other week")
        st.markdown("**What's included**")
        st.markdown("- Fall-style schedule from July onward.")
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #2563eb; background-color: #eff6ff; border-radius: 0 6px 6px 0; color: #1e40af; font-size: 1rem;">
    Summer large group attendance is nearly double versus other seasons. Small groups are also more engaged during the summer and fall.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("**Why front-load chemistry and physics in summer**")
    st.markdown("""
    <div style="padding: 0.75rem 1rem; margin: 0.5rem 0; border-left: 4px solid #059669; background-color: #ecfdf5; border-radius: 0 6px 6px 0;">
    To support performance and align with engagement trends, we recommend front-loading foundational chemistry and physics in summer so fall can prioritize higher-yield topics, cross-disciplinary connections, and advanced applications.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("- Survey data and JW Exam 1 performance indicate students need stronger foundations in chemistry and physics.")
    st.markdown("- Many concepts are lower-yield but benefit from earlier, structured exposure.")
    st.markdown("- Summer engagement is higher; we capitalize on availability and build core understanding early.")
    st.markdown("- Fall can then shift to higher-yield topics, deeper connections, and heavier application and strategy practice.")
    st.write(" ")

    # D) Fall 2026
    st.subheader("Fall 2026")
    st.markdown("All options share the same fall cadence:")
    st.markdown("- **Large group:** 2×/week")
    st.markdown("- **Small groups:** every other week")
    st.markdown("Lecture topics may vary depending on the summer intensive structure.")
    st.write(" ")

    # E) Spring 2026 (tabs)
    st.subheader("Spring 2026")
    st.markdown("If the proposed programs are adopted, **~190 of 240 hours** will be completed by end of December 2025 to support January 2026 test dates. Spring options reflect how the remaining **50 hours** are allocated.")
    st.write(" ")
    spring_tabs = st.tabs(["Option I (February end)", "Option II (March end)", "Option III (April end)"])
    _wk = """
    <div style="padding: 0.75rem 1rem; margin: 0.75rem 0; border-left: 3px solid #64748b; background-color: #f8fafc; border-radius: 0 6px 6px 0; font-size: 0.95rem;">
    <strong>Worth keeping in mind</strong><ul style="margin: 0.5rem 0 0 1rem; padding-left: 1rem;">
    """
    with spring_tabs[0]:
        st.markdown("**Intended end date**  \nFebruary 2026 (prep for March testing)")
        st.markdown("**Cadence**  \nLarge group 2×/week; small groups once every 3 weeks through course end.")
        st.markdown("**Hours allotment**")
        st.markdown("""
        | Component    | Hours | Meeting details |
        |--------------|-------|-----------------|
        | Large group  | 32    | 16 meetings at 2×/week |
        | Small group  | 18    | 6 small groups × 3 meetings (1 every 3 weeks) |
        """)
        st.markdown(_wk + "<li>Maintains higher-intensity pace after winter break.</li><li>Jan–Feb targets weakness/strategy gaps revealed by January testing.</li><li>Small groups remain similar; messaging shifts for early March retesting.</li></ul></div>", unsafe_allow_html=True)
    with spring_tabs[1]:
        st.markdown("**Intended end date**  \nMarch 2026 (supports March + early April testers)")
        st.markdown("**Cadence**  \nLarge group 2×/week; small groups once monthly in Jan/Feb.")
        st.markdown("**Hours allotment**")
        st.markdown("""
        | Component    | Hours | Meeting details |
        |--------------|-------|-----------------|
        | Large group  | 38    | 19 at 2×/week (32-hour Jan/Feb identical to Option I) |
        | Small group  | 12    | 6 small groups × 2 meetings (1/month) |
        """)
        st.markdown(_wk + "<li>Similar to Option I but more flexible retest timeline.</li><li>Reduced small groups can be offset by increased coaching in large group.</li></ul></div>", unsafe_allow_html=True)
    with spring_tabs[2]:
        st.markdown("**Intended end date**  \nApril 2026")
        st.markdown("**Cadence**  \nSmall groups removed. Large groups start 1/11/26 (one week later); 2×/week thereafter.")
        st.markdown("**Hours allotment**")
        st.markdown("""
        | Component    | Hours | Meeting details |
        |--------------|-------|-----------------|
        | Large group  | 50    | 25 at 2×/week (Feb 16-hour allotment identical to Options I/II) |
        | Small group  | 0     | No meetings |
        """)
        st.markdown(_wk + "<li>Maximizes large group coverage for most Spring test dates.</li><li>Add more coaching content in large group to compensate for no small groups.</li></ul></div>", unsafe_allow_html=True)
    st.write(" ")

    # G) June comparison
    st.subheader("June: Option I vs Option II")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        st.markdown("**Option I**")
        st.markdown("- Early invitations to small-group coaching.")
        st.markdown("- Students build community, accountability, and peer engagement sooner.")
    with col_j2:
        st.markdown("**Option II**")
        st.markdown("- Standard timeline for small-group coaching access.")
    st.write(" ")

    # H) July comparison
    st.subheader("July: Option I vs Option II")
    col_jul1, col_jul2 = st.columns(2)
    with col_jul1:
        st.markdown("**Option I**")
        st.markdown("- 4 meetings per week; increased content coverage during summer.")
    with col_jul2:
        st.markdown("**Option II**")
        st.markdown("- Fewer weekly meetings; lighter schedule.")
    st.write(" ")

    # Calendar view (below all text)
    st.subheader("Calendars")
    if os.path.exists(EY26_PDF_PATH):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(EY26_PDF_PATH)
            st.caption("Scroll to view all pages.")
            for i in range(len(doc)):
                page = doc.load_page(i)
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for readability
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                st.image(io.BytesIO(img_bytes), use_container_width=True)
            doc.close()
        except Exception as e:
            st.warning(f"Could not render PDF: {e}. Add **calendars_side_by_side.pdf** to **ey26_assets** and ensure the `pymupdf` package is installed.")
        st.write(" ")
    else:
        st.info("Calendar PDF not found. Add **calendars_side_by_side.pdf** to the **ey26_assets** folder, or upload it via Cursor so it can be copied here.")
        st.write(" ")

elif view_mode == "Current Status EY25":
    st.header("Current Status EY25")
    st.write(" ")

    # Placeholder: load same data sources for future widgets
    import os
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

    # -------------------------------------------------------------------------
    # First Attempt outcome (from institution-1-test-data.csv)
    # >=502 Passed | 495 to <502 Borderline | <495 Below 495
    # -------------------------------------------------------------------------
    st.subheader("First Final Exam Score outcome")
    st.markdown("""
    **First Final Exam Score** = score from the row where **test_name** is *First Attempt* only (students without that row are not included).  
    **Definitions:**  
    - **Passed:** First Final Exam Score **≥ 502**  
    - **Borderline:** First Final Exam Score **495–501**  
    - **Below 495:** First Final Exam Score **< 495**
    """)
    st.write(" ")

    if has_test and not test_df.empty:
        test_df['actual_exam_score'] = pd.to_numeric(test_df['actual_exam_score'], errors='coerce')
        # First attempt = only the designated "First Attempt" row (so Passed count matches reconciliation, e.g. 22 with ≥502)
        first_attempt_designated = test_df[(test_df['test_name'] == 'First Attempt') & test_df['actual_exam_score'].notna() & (test_df['actual_exam_score'] > 0)]
        if first_attempt_designated.empty:
            first_attempt = pd.DataFrame(columns=['student_id', 'first_attempt_date', 'first_attempt_score'])
        else:
            first_attempt = first_attempt_designated.groupby('student_id').first().reset_index()[['student_id', 'test_date', 'actual_exam_score']]
            first_attempt = first_attempt.rename(columns={'actual_exam_score': 'first_attempt_score', 'test_date': 'first_attempt_date'})
        # Drop invalid scores (e.g. 0) for classification; keep row but outcome "No valid score" if needed
        first_attempt['first_attempt_score_clean'] = first_attempt['first_attempt_score'].replace(0, np.nan)
        def outcome(score):
            if pd.isna(score) or score == 0:
                return "No valid score"
            if score >= 502:
                return "Passed"
            if score >= 495:
                return "Borderline"
            return "Below 495"
        first_attempt['first_attempt_outcome'] = first_attempt['first_attempt_score_clean'].apply(outcome)

        # Exam tier by count (for data story)
        exam_counts = test_df.groupby('student_id').size().reset_index(name='exam_count')
        def exam_tier_label(n):
            if n > 5:
                return "Tier 1"
            if n >= 3:
                return "Tier 2"
            return "Tier 3"
        exam_counts['exam_tier'] = exam_counts['exam_count'].apply(exam_tier_label)
        first_attempt = first_attempt.merge(exam_counts, on='student_id', how='left')

        # Merge tier.csv: Jan 2026-Current and Jun-Dec 2025
        if has_tier and 'date_window' in tier_df.columns:
            jan = tier_df[tier_df['date_window'] == 'Jan 2026-Current'][['student_id', 'large_group_tier', 'small_group_tier']]
            first_attempt = first_attempt.merge(jan, on='student_id', how='left')
            first_attempt['large_group_tier'] = first_attempt['large_group_tier'].fillna("—")
            first_attempt['small_group_tier'] = first_attempt['small_group_tier'].fillna("—")
            jundec = tier_df[tier_df['date_window'] == 'Jun-Dec 2025'][['student_id', 'large_group_tier', 'small_group_tier']].rename(
                columns={'large_group_tier': 'large_group_tier_JunDec', 'small_group_tier': 'small_group_tier_JunDec'}
            )
            first_attempt = first_attempt.merge(jundec, on='student_id', how='left')
            first_attempt['large_group_tier_JunDec'] = first_attempt['large_group_tier_JunDec'].fillna("—")
            first_attempt['small_group_tier_JunDec'] = first_attempt['small_group_tier_JunDec'].fillna("—")
        else:
            first_attempt['large_group_tier'] = "—"
            first_attempt['small_group_tier'] = "—"
            first_attempt['large_group_tier_JunDec'] = "—"
            first_attempt['small_group_tier_JunDec'] = "—"

        # Tier 1 or 2 flags for data story
        first_attempt['attendance_tier_1_or_2'] = (
            first_attempt['large_group_tier'].isin(['Tier 1', 'Tier 2']) &
            first_attempt['small_group_tier'].isin(['Tier 1', 'Tier 2'])
        )
        first_attempt['exam_tier_1_or_2'] = first_attempt['exam_tier'].isin(['Tier 1', 'Tier 2'])
        passed = first_attempt['first_attempt_outcome'] == 'Passed'
        tier12_att = first_attempt['attendance_tier_1_or_2'] == True
        tier12_exam = first_attempt['exam_tier_1_or_2'] == True
        tier12_both = tier12_att & tier12_exam
        tier12_att_or_exam = tier12_att | tier12_exam
        n_passed = passed.sum()
        n_passed_tier12 = (passed & tier12_att_or_exam).sum()
        pct_passed_tier12 = (n_passed_tier12 / n_passed * 100) if n_passed > 0 else 0
        outcome_counts = first_attempt['first_attempt_outcome'].value_counts()

        # --- TOP: Counts by First Final Exam Score outcome (no No valid score)
        st.markdown("**Counts by First Final Exam Score outcome**")
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

        # --- Pie chart (Among students who passed: Tier 1/2 in attendance and/or exams)
        if n_passed > 0:
            df_pie = pd.DataFrame({
                "Segment": ["Tier 1 or 2 (attendance and/or exams)", "Not Tier 1/2"],
                "Count": [int(n_passed_tier12), int(n_passed - n_passed_tier12)]
            })
            fig_pie = px.pie(df_pie, values="Count", names="Segment", title="Among students who passed: Tier 1/2 in attendance and/or exams",
                color="Segment", color_discrete_map={"Tier 1 or 2 (attendance and/or exams)": "#10b981", "Not Tier 1/2": "#94a3b8"})
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie = apply_light_mode_styling(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)
        st.write(" ")

        # --- List of students (beneath pie) — only those who passed
        passed_only = first_attempt[passed]
        display_cols = ['student_id', 'first_attempt_score', 'first_attempt_outcome', 'exam_tier',
            'large_group_tier_JunDec', 'small_group_tier_JunDec', 'large_group_tier', 'small_group_tier']
        display_rename = {'first_attempt_score': 'First Final Exam Score', 'first_attempt_outcome': 'Outcome'}
        with st.expander("**First Final Exam Score + tiers (students who passed)**", expanded=False):
            st.dataframe(passed_only[display_cols].rename(columns=display_rename), use_container_width=True, hide_index=True)
        st.write(" ")

        # Build improvement data (needed for table and for 8+ point graph)
        jw1 = test_df[test_df['test_name'] == 'JW Exam 1'].sort_values('test_date').groupby('student_id').first().reset_index()
        jw1 = jw1[['student_id', 'actual_exam_score']].rename(columns={'actual_exam_score': 'baseline_score'})
        highest = test_df.groupby('student_id')['actual_exam_score'].max().reset_index().rename(columns={'actual_exam_score': 'highest_score'})
        improvement_df = first_attempt[['student_id', 'exam_tier', 'large_group_tier_JunDec', 'small_group_tier_JunDec', 'large_group_tier', 'small_group_tier']].merge(
            jw1, on='student_id', how='left'
        ).merge(highest, on='student_id', how='left')
        improvement_df['score_improvement'] = (
            improvement_df['highest_score'].fillna(0) - improvement_df['baseline_score'].fillna(0)
        ).fillna(0).astype(int)
        improvement_df = improvement_df.merge(passed_only[['student_id']], on='student_id', how='inner')

        # --- Tiers of students who had +8 point or more increase (graph beneath passed table)
        gain_8_plus = improvement_df[improvement_df['score_improvement'] >= 8]
        if not gain_8_plus.empty:
            st.header("Tiers of students who had +8 point or more increase")
            n_total = len(gain_8_plus)
            tier_cols_for_chart = ['exam_tier', 'large_group_tier_JunDec', 'small_group_tier_JunDec']
            tier_labels = ['Exam tier', 'Large group (Jun–Dec)', 'Small group (Jun–Dec)']
            counts_list = []
            for col, label in zip(tier_cols_for_chart, tier_labels):
                vc = gain_8_plus[col].value_counts().reindex(['Tier 1', 'Tier 2', 'Tier 3'], fill_value=0)
                n12 = int(vc.get('Tier 1', 0)) + int(vc.get('Tier 2', 0))
                n3 = int(vc.get('Tier 3', 0))
                pct12 = (n12 / n_total * 100) if n_total else 0
                pct3 = (n3 / n_total * 100) if n_total else 0
                counts_list.append({'Category': label, 'Segment': 'Tier 1 or 2', 'Count': n12, 'Pct': pct12})
                counts_list.append({'Category': label, 'Segment': 'Tier 3', 'Count': n3, 'Pct': pct3})
            df_tier8 = pd.DataFrame(counts_list)
            fig_8plus = px.bar(df_tier8, x='Category', y='Count', color='Segment', text='Pct',
                title=f'Tier breakdown: students with ≥8 point increase (n={n_total})',
                barmode='stack',
                color_discrete_map={'Tier 1 or 2': '#4CAF50', 'Tier 3': '#EF5350'})
            fig_8plus.update_traces(texttemplate='%{text:.0f}%', textposition='inside')
            fig_8plus = apply_light_mode_styling(fig_8plus)
            st.plotly_chart(fig_8plus, use_container_width=True)
        else:
            st.caption("No students who passed had a +8 point or more increase from baseline (JW Exam 1) to highest score.")
        st.write(" ")

        # --- Borderline students (First Attempt 495–501): baseline to score increase (institution-1-test-data)
        borderline = first_attempt[(first_attempt['first_attempt_score_clean'] >= 495) & (first_attempt['first_attempt_score_clean'] < 502)]
        if not borderline.empty:
            borderline_ids = borderline['student_id'].tolist()
            test_valid = test_df[test_df['student_id'].isin(borderline_ids)].copy()
            test_valid['actual_exam_score'] = pd.to_numeric(test_valid['actual_exam_score'], errors='coerce')
            test_valid = test_valid[test_valid['actual_exam_score'].notna() & (test_valid['actual_exam_score'] > 0)]
            first_scores = borderline.set_index('student_id')['first_attempt_score']

            # Per student: lowest, first attempt, highest (all from test data)
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
                st.caption("Students whose **First Attempt** actual MCAT score is **495–501**. Per student: **Baseline** (lowest reported score), **Actual** (First Attempt score), **Highest** (highest reported score).")
                # Grouped bar: Baseline (lowest), Actual (First Attempt), Highest per student; x = only these IDs (categorical, no number line)
                plot_df = df_borderline_scores[['student_id', 'Lowest', 'First Attempt', 'Highest']].copy()
                plot_df = plot_df.rename(columns={'Lowest': 'Baseline', 'First Attempt': 'Actual', 'Highest': 'Highest'})
                plot_ids = plot_df['student_id'].tolist()
                plot_df['student_id'] = plot_df['student_id'].astype(str)
                plot_df = plot_df.melt(id_vars=['student_id'], value_vars=['Baseline', 'Actual', 'Highest'], var_name='Metric', value_name='Score')
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
                    bargap=0.2,
                    bargroupgap=0.02,
                    legend={'orientation': 'h', 'yanchor': 'top', 'y': 0.99, 'xanchor': 'right', 'x': 0.99, 'bgcolor': 'rgba(255,255,255,0.8)'},
                    margin={'t': 100})
                fig_borderline = apply_light_mode_styling(fig_borderline)
                st.plotly_chart(fig_borderline, use_container_width=True)
        st.write(" ")

        # --- Score improvement frequency (all students, institution-1-test-data): lowest to highest, increases only, 1–30 pts
        # Use only valid MCAT 3-digit range (472–528) to avoid outliers (e.g. typos like 107)
        MCAT_MIN, MCAT_MAX = 472, 528
        test_valid_all = test_df[test_df['actual_exam_score'].notna() & (test_df['actual_exam_score'] >= MCAT_MIN) & (test_df['actual_exam_score'] <= MCAT_MAX)]
        low_high = test_valid_all.groupby('student_id')['actual_exam_score'].agg(['min', 'max']).reset_index()
        low_high['improvement'] = (low_high['max'] - low_high['min']).astype(int)
        improved_df = low_high[low_high['improvement'] > 0]
        improvements_positive = improved_df['improvement']
        # Only show improvement between 1 and 30 (exclude outliers)
        improvements_1_30 = improvements_positive[(improvements_positive >= 1) & (improvements_positive <= 30)]
        if not improvements_1_30.empty:
            st.subheader("Score improvement: frequency of growth")
            st.caption("Per student: **improvement** = highest − lowest reported three-digit score (valid range 472–528). X = points improved, Y = number of students.")
            freq = improvements_1_30.value_counts().sort_index()
            df_freq = freq.reset_index()
            df_freq.columns = ['Points improved', 'Number of students']
            fig_freq = px.bar(df_freq, x='Points improved', y='Number of students',
                title='Frequency of score improvement',
                labels={'Points improved': 'Points improved', 'Number of students': 'Number of students'})
            fig_freq.update_layout(xaxis={'dtick': 1, 'range': [-0.5, 30.5]}, yaxis_title='Number of students', margin={'t': 80})
            fig_freq = apply_light_mode_styling(fig_freq)
            st.plotly_chart(fig_freq, use_container_width=True)
            # Table beneath graph: 98 students positive improvement, avg exams reported among them
            n_improved = len(improved_df)
            exam_counts_per_student = test_valid_all.groupby('student_id').size()
            improved_ids = improved_df['student_id'].tolist()
            avg_exams = float(exam_counts_per_student.reindex(improved_ids).mean()) if improved_ids else 0
            summary_table = pd.DataFrame({
                'Metric': ['Students with positive improvement', 'Average exams reported (among those students)'],
                'Value': [n_improved, round(avg_exams, 1)]
            })
            st.dataframe(summary_table, use_container_width=True, hide_index=True, column_config={'Metric': st.column_config.TextColumn('Metric'), 'Value': st.column_config.NumberColumn('Value', format='%g')})

        # --- Test date distribution (bottom of page): Anticipated Exam Date + Second Exam Attempt (Jan–May)
        attempt_df = test_df[test_df['test_name'].isin(['Anticipated Exam Date', 'Second Exam Attempt'])].copy()
        attempt_df['test_date'] = pd.to_datetime(attempt_df['test_date'], errors='coerce')
        attempt_df = attempt_df.dropna(subset=['test_date'])
        attempt_df['month'] = attempt_df['test_date'].dt.month
        attempt_df['month_name'] = attempt_df['test_date'].dt.month_name()
        month_order = ['January', 'February', 'March', 'April', 'May']
        attempt_df = attempt_df[attempt_df['month_name'].isin(month_order)]

        if not attempt_df.empty:
            st.subheader("Test date distribution: Anticipated Exam Date and Second Exam Attempt")
            st.caption("Distribution by month (Jan–May). Left: Anticipated Exam Date split by **% reported exam score** (has First Attempt) vs **% not reported**. Right: Second Exam Attempt.")
            ant_df = attempt_df[attempt_df['test_name'] == 'Anticipated Exam Date']
            sa_df = attempt_df[attempt_df['test_name'] == 'Second Exam Attempt']
            students_with_first_attempt = set(test_df.loc[test_df['test_name'] == 'First Attempt', 'student_id'].dropna().astype(int))

            col1, col2 = st.columns(2)
            with col1:
                if not ant_df.empty:
                    stack_rows = []
                    for month in month_order:
                        month_students = ant_df[ant_df['month_name'] == month]
                        if month_students.empty:
                            stack_rows.append({'Month': month, 'Segment': 'Reported exam score', 'Count': 0})
                            stack_rows.append({'Month': month, 'Segment': 'Not reported', 'Count': 0})
                            continue
                        ids_in_month = month_students['student_id'].dropna().astype(int).unique()
                        reported = sum(1 for i in ids_in_month if i in students_with_first_attempt)
                        not_reported = len(ids_in_month) - reported
                        stack_rows.append({'Month': month, 'Segment': 'Reported exam score', 'Count': reported})
                        stack_rows.append({'Month': month, 'Segment': 'Not reported', 'Count': not_reported})
                    df_ant_stack = pd.DataFrame(stack_rows)
                    fig_ant = px.bar(df_ant_stack, x='Month', y='Count', color='Segment', barmode='stack',
                        title='Anticipated Exam Date — by month (Jan–May): reported vs not reported',
                        color_discrete_map={'Reported exam score': '#10b981', 'Not reported': '#94a3b8'})
                    fig_ant.update_layout(xaxis_tickangle=-25, yaxis_title='Number of students',
                        legend={'orientation': 'h', 'yanchor': 'top', 'y': 0.99, 'xanchor': 'right', 'x': 0.99, 'bgcolor': 'rgba(255,255,255,0.8)'}, margin={'t': 80})
                    fig_ant = apply_light_mode_styling(fig_ant)
                    st.plotly_chart(fig_ant, use_container_width=True)
                else:
                    st.write("No Anticipated Exam Date rows with test_date in Jan–May.")
            with col2:
                if not sa_df.empty:
                    sa_counts = sa_df['month_name'].value_counts().reindex(month_order, fill_value=0)
                    df_sa_bar = sa_counts.reset_index()
                    df_sa_bar.columns = ['Month', 'Number of students']
                    fig_sa = px.bar(df_sa_bar, x='Month', y='Number of students', title='Second Exam Attempt — by month (Jan–May)', color_discrete_sequence=['#8b5cf6'])
                    fig_sa.update_layout(xaxis_tickangle=-25, showlegend=False)
                    fig_sa = apply_light_mode_styling(fig_sa)
                    st.plotly_chart(fig_sa, use_container_width=True)
                else:
                    st.write("No Second Exam Attempt rows with test_date in Jan–May.")

            # Anticipated Exam Date — distribution by outcome by month (Jan–May); add "Total" bar so Passed shows 22
            first_attempt_scores = test_df[test_df['test_name'] == 'First Attempt'][['student_id', 'actual_exam_score']].copy()
            first_attempt_scores['actual_exam_score'] = pd.to_numeric(first_attempt_scores['actual_exam_score'], errors='coerce')
            first_attempt_scores = first_attempt_scores.dropna(subset=['actual_exam_score']).drop_duplicates(subset=['student_id'], keep='first')
            score_by_student = first_attempt_scores.set_index('student_id')['actual_exam_score'].to_dict()

            outcome_rows = []
            for month in month_order:
                month_students = ant_df[ant_df['month_name'] == month]
                if month_students.empty:
                    for seg in ['Passed (>502)', 'Borderline (495–501)', 'Failing (<495)', 'No reported score']:
                        outcome_rows.append({'Month': month, 'Outcome': seg, 'Count': 0})
                    continue
                ids_in_month = month_students['student_id'].dropna().astype(int).unique()
                passed = borderline = failing = no_score = 0
                for sid in ids_in_month:
                    score = score_by_student.get(sid)
                    if score is None or pd.isna(score):
                        no_score += 1
                    elif score > 502:
                        passed += 1
                    elif score >= 495:
                        borderline += 1
                    else:
                        failing += 1
                outcome_rows.append({'Month': month, 'Outcome': 'Passed (>502)', 'Count': passed})
                outcome_rows.append({'Month': month, 'Outcome': 'Borderline (495–501)', 'Count': borderline})
                outcome_rows.append({'Month': month, 'Outcome': 'Failing (<495)', 'Count': failing})
                outcome_rows.append({'Month': month, 'Outcome': 'No reported score', 'Count': no_score})

            # Add "Total" bar with full-dataset counts so 22 Passed is visible
            n_passed = int(outcome_counts.get('Passed', 0))
            n_borderline = int(outcome_counts.get('Borderline', 0))
            n_below = int(outcome_counts.get('Below 495', 0))
            n_no_valid = int(outcome_counts.get('No valid score', 0))
            all_ids = set(test_df['student_id'].dropna().astype(int))
            first_attempt_ids = set(first_attempt['student_id'].dropna().astype(int))
            n_no_reported = len(all_ids - first_attempt_ids) + n_no_valid
            outcome_rows.append({'Month': 'Total (full dataset)', 'Outcome': 'Passed (>502)', 'Count': n_passed})
            outcome_rows.append({'Month': 'Total (full dataset)', 'Outcome': 'Borderline (495–501)', 'Count': n_borderline})
            outcome_rows.append({'Month': 'Total (full dataset)', 'Outcome': 'Failing (<495)', 'Count': n_below})
            outcome_rows.append({'Month': 'Total (full dataset)', 'Outcome': 'No reported score', 'Count': n_no_reported})

            df_outcome = pd.DataFrame(outcome_rows)
            month_order_with_total = month_order + ['Total (full dataset)']
            fig_outcome = px.bar(df_outcome, x='Month', y='Count', color='Outcome', barmode='stack',
                title='Anticipated Exam Date — distribution by First Attempt outcome (Jan–May + Total)',
                color_discrete_map={'Passed (>502)': '#10b981', 'Borderline (495–501)': '#f59e0b', 'Failing (<495)': '#ef4444', 'No reported score': '#94a3b8'},
                category_orders={'Month': month_order_with_total})
            fig_outcome.update_layout(xaxis_tickangle=-25, yaxis_title='Number of students',
                legend={'orientation': 'h', 'yanchor': 'top', 'y': 0.99, 'xanchor': 'right', 'x': 0.99, 'bgcolor': 'rgba(255,255,255,0.8)'}, margin={'t': 80})
            fig_outcome = apply_light_mode_styling(fig_outcome)
            st.plotly_chart(fig_outcome, use_container_width=True)

        st.write(" ")

    else:
        st.info("Load test data to see First Final Exam Score outcomes and tier comparison.")

    # --- Interventions: header, categories, then score distribution and tier comparison
    st.markdown("### Interventions")
    st.markdown("""
    Students are flagged for outreach based on the following intervention categories.

    **1. No reported practice exam scores** — Students who had not reported any practice exam scores; outreach encourages score reporting so progress can be tracked.

    **2. No anticipated exam date** — Students who had not reported an anticipated exam date; outreach asks them to share when they plan to test.

    **3. Low attendance in classes** — Students with low attendance; outreach supports engagement and preparation.
    """)
    st.write(" ")

    if has_test and not test_df.empty:
        interventions_path = None
        for path in ['Interventions_initial.csv', './Interventions_initial.csv']:
            if os.path.exists(path):
                interventions_path = path
                break
        if interventions_path:
            with open(interventions_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip() for line in f]
            group_ids = {'No reported practice scores': [], 'No anticipated exam date': [], 'Low attendance in classes': []}
            responded_ids = set()  # students who responded to intervention in any section
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
                    # Response: section 1 & 2 use column 2; section 3 = Email (2) or Survey (3) TRUE
                    if current == 'Low attendance in classes':
                        responded = (len(parts) > 2 and parts[2].upper() == 'TRUE') or (len(parts) > 3 and parts[3].upper() == 'TRUE')
                    else:
                        responded = len(parts) > 2 and parts[2].upper() == 'TRUE'
                    if responded:
                        responded_ids.add(sid)
                except (ValueError, IndexError):
                    continue
            intervention_list = []
            for grp, ids in group_ids.items():
                for sid in ids:
                    intervention_list.append({'student_id': sid, 'intervention_group': grp})
            if intervention_list:
                # Keep students in every category they belong to (no dedup) so they can appear in multiple bar segments
                int_df = pd.DataFrame(intervention_list)
                test_df['actual_exam_score'] = pd.to_numeric(test_df['actual_exam_score'], errors='coerce')
                valid_scores = test_df[test_df['actual_exam_score'].notna() & (test_df['actual_exam_score'] >= 472) & (test_df['actual_exam_score'] <= 528)]
                most_recent = valid_scores.groupby('student_id')['actual_exam_score'].max().reset_index(name='most_recent_score')
                int_df = int_df.merge(most_recent, on='student_id', how='left')

                def score_bucket(s):
                    if pd.isna(s): return 'No score'
                    if s >= 502: return '502+ (Passed)'
                    if s >= 495: return '495–501 (Borderline)'
                    return '<495 (Failing)'
                int_df['score_bucket'] = int_df['most_recent_score'].apply(score_bucket)
                group_order = ['No reported practice scores', 'No anticipated exam date', 'Low attendance in classes']
                bucket_order = ['No score', '<495 (Failing)', '495–501 (Borderline)', '502+ (Passed)']

                g_dist = int_df.groupby(['intervention_group', 'score_bucket']).size().reset_index(name='Count')
                fig_dist = px.bar(g_dist, x='intervention_group', y='Count', color='score_bucket', barmode='stack',
                    title='Score distribution by intervention category (most recent score from test data)',
                    color_discrete_map={'No score': '#94a3b8', '<495 (Failing)': '#ef4444', '495–501 (Borderline)': '#f59e0b', '502+ (Passed)': '#10b981'},
                    category_orders={'intervention_group': group_order, 'score_bucket': bucket_order})
                fig_dist.update_layout(xaxis_tickangle=-20, yaxis_title='Number of students',
                    legend={'orientation': 'h', 'yanchor': 'top', 'y': -0.35, 'xanchor': 'center', 'x': 0.5, 'bgcolor': 'rgba(255,255,255,0.8)'},
                    margin={'t': 70, 'b': 140})
                fig_dist = apply_light_mode_styling(fig_dist)
                st.plotly_chart(fig_dist, use_container_width=True)
                st.write(" ")

                # Table: % of students not passing by intervention category (not passing = no score or most_recent < 502)
                int_df['not_passing'] = int_df['most_recent_score'].isna() | (int_df['most_recent_score'] < 502)
                tbl = int_df.groupby('intervention_group').agg(n=('student_id', 'count'), not_passing=('not_passing', 'sum')).reset_index()
                tbl['% not passing'] = (100 * tbl['not_passing'] / tbl['n']).round(1).astype(str) + '%'
                tbl = tbl[['intervention_group', 'n', '% not passing']].rename(columns={'intervention_group': 'Intervention category', 'n': 'N students'})
                tbl = tbl.set_index('Intervention category').reindex(group_order).reset_index()
                st.dataframe(tbl, use_container_width=True, hide_index=True)
                st.write(" ")

                # Bar chart: # intervened vs # responded
                intervened_ids = set(pd.DataFrame(intervention_list)['student_id'].unique())
                n_intervened = len(intervened_ids)
                n_responded = len(responded_ids)
                fig_resp = px.bar(x=['Students intervened', 'Students that responded'], y=[n_intervened, n_responded],
                    title='Students intervened vs students that responded',
                    labels={'x': '', 'y': 'Number of students'}, text=[n_intervened, n_responded])
                fig_resp.update_traces(textposition='outside')
                fig_resp = apply_light_mode_styling(fig_resp)
                st.plotly_chart(fig_resp, use_container_width=True)
                st.write(" ")

                # Dropdown table: list of intervened students with Responded, most recent score, practice exam count, Jun-Dec tiers
                resp_table = pd.DataFrame({'student_id': sorted(intervened_ids)})
                resp_table['Responded'] = resp_table['student_id'].isin(responded_ids).map({True: 'Yes', False: 'No'})
                resp_table = resp_table.merge(most_recent, on='student_id', how='left')
                resp_table['most_recent_score'] = resp_table['most_recent_score'].astype(object).fillna('—')
                # Practice exam count (from test data)
                exam_count = test_df.groupby('student_id').size().reset_index(name='practice_exam_count')
                resp_table = resp_table.merge(exam_count, on='student_id', how='left')
                resp_table['practice_exam_count'] = resp_table['practice_exam_count'].fillna(0).astype(int)
                # Jun-Dec 2025: large and small group attendance tier (first portion)
                jundec_col = 'June through December large and small group attendance tier'
                if has_tier and tier_df is not None and 'date_window' in tier_df.columns:
                    jundec = tier_df[tier_df['date_window'] == 'Jun-Dec 2025'][['student_id', 'large_group_tier', 'small_group_tier']].copy()
                    jundec[jundec_col] = 'Large: ' + jundec['large_group_tier'].astype(str) + ', Small: ' + jundec['small_group_tier'].astype(str)
                    jundec = jundec[['student_id', jundec_col]].drop_duplicates('student_id')
                    resp_table = resp_table.merge(jundec, on='student_id', how='left')
                    resp_table[jundec_col] = resp_table[jundec_col].fillna('—')
                else:
                    resp_table[jundec_col] = '—'
                resp_table = resp_table.rename(columns={'most_recent_score': 'Most recent score', 'practice_exam_count': 'Practice exams taken'})
                resp_table = resp_table[['student_id', 'Responded', 'Most recent score', 'Practice exams taken', jundec_col]]
                with st.expander('List of intervened students: responded, most recent score, practice exams, Jun–Dec attendance tier'):
                    st.dataframe(resp_table, use_container_width=True, hide_index=True)
    st.write(" ")

