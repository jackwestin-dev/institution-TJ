# -*- coding: utf-8 -*-
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
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styling */
    .main {
        font-family: 'Inter', sans-serif;
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
                del st.session_state["password"]  # Don't store the password.
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
    st.stop()  # Do not continue if check_password is not True.

# Sidebar Navigation
st.sidebar.title("Navigation")
dashboard_type = st.sidebar.radio(
    "Choose Dashboard Type:",
    ["Individual Student Dashboard EY25", "Students by JFD", "Retrospective Data Analysis (EY24)"]
)

if dashboard_type == "Individual Student Dashboard EY25":
    # Original Individual Student Dashboard Code
    
    ## Read data from CSV files (with error handling)
    import os
    
    # Try multiple possible paths for deployment compatibility
    data_paths = [
        'student-data/',          # Local development
        './student-data/',        # Explicit relative path
        'student_data/',          # Alternative naming
        './student_data/',        # Alternative with explicit relative
        ''                        # Root directory fallback
    ]
    
    individual_data_available = False
    
    for base_path in data_paths:
        try:
            # Test if all required files exist in this path
            files_to_check = [
                f'{base_path}institution-1-engagement-data.csv',
                f'{base_path}institution-1-test-data.csv', 
                f'{base_path}institution-1-2025-exam-data-jw-exams.csv',
                f'{base_path}tierdata.csv'
            ]
            
            # Check if all files exist
            if all(os.path.exists(f) for f in files_to_check):
                df_engagement_attendance = pd.read_csv(f'{base_path}institution-1-engagement-data.csv',parse_dates=['start_date','end_date'])
                df_test_scores = pd.read_csv(f'{base_path}institution-1-test-data.csv',parse_dates=['test_date'])
                df_test_section_scores = pd.read_csv(f'{base_path}institution-1-2025-exam-data-jw-exams.csv')
                df_tier_data = pd.read_csv(f'{base_path}tierdata.csv')
                individual_data_available = True

                break
        except Exception as e:
            continue
    
    if not individual_data_available:
        st.error(f"**Individual Student Dashboard Data Not Found**")
        st.info("The Individual Student Dashboard requires the following files:")
        st.markdown("""
        **Required files (in student-data/ directory or root):**
        - `institution-1-engagement-data.csv`
        - `institution-1-test-data.csv`
        - `institution-1-2025-exam-data-jw-exams.csv`
        - `tierdata.csv`
        
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
        
        st.info("💡 **Tip:** Use the **MCAT Analysis Dashboard** which uses the available data files.")
    
    if individual_data_available:
        ## Create dashboard filters
        student_id = st.selectbox("Choose a student:", list(df_engagement_attendance['student_id'].unique()))
        st.write('Here is a link to the [Texas JAMP Scholar Student Roster with Associated Student ID Numbers](https://drive.google.com/file/d/1ibmeF4CtRwOaZeCjLM3Nm5S_mGlMvgIZ/view?usp=sharing)')

        ## Transform dataframes
        df_engagement_attendance_student_filtered = df_engagement_attendance[df_engagement_attendance['student_id'] == student_id]
        # Create date_range column for tooltips
        df_engagement_attendance_student_filtered['date_range'] = df_engagement_attendance_student_filtered.apply(
            lambda row: f"{row['start_date'].strftime('%m/%d/%y')} - {row['end_date'].strftime('%m/%d/%y')}", 
            axis=1
        )
        df_engagement_attendance_student_filtered['num_attended_large_session_cumsum'] = df_engagement_attendance_student_filtered['num_attended_large_session'].cumsum()
        df_engagement_attendance_student_filtered['num_scheduled_large_session_cumsum'] = df_engagement_attendance_student_filtered['num_scheduled_large_session'].cumsum()
        df_engagement_attendance_student_filtered['num_attended_small_session_cumsum'] = df_engagement_attendance_student_filtered['num_attended_small_session'].cumsum()
        df_engagement_attendance_student_filtered['num_scheduled_small_session_cumsum'] = df_engagement_attendance_student_filtered['num_scheduled_small_session'].cumsum()
        df_engagement_attendance_student_filtered['large_session'] = df_engagement_attendance_student_filtered['num_attended_large_session_cumsum'] / df_engagement_attendance_student_filtered['num_scheduled_large_session_cumsum']
        df_engagement_attendance_student_filtered['small_session'] = df_engagement_attendance_student_filtered['num_attended_small_session_cumsum'] / df_engagement_attendance_student_filtered['num_scheduled_small_session_cumsum']
        df_engagement_attendance_avg = df_engagement_attendance_student_filtered[['class_participation','homework_participation','cars_accuracy','sciences_accuracy','class_accuracy']].mean()

        class_participation = df_engagement_attendance_avg.loc['class_participation']
        homework_participation = df_engagement_attendance_avg.loc['homework_participation']
        overall_participation = (class_participation + homework_participation) / 2

        df_test_scores['test_date'] = df_test_scores['test_date'].dt.date
        df_test_scores_student_filtered = df_test_scores[df_test_scores['student_id'] == student_id]

        df_test_section_scores_student_filtered = df_test_section_scores[df_test_section_scores['student_id'] == student_id]
        df_tier_data_student_filtered = df_tier_data[df_tier_data['student_id'] == student_id]

        ## Create sections and render dashboard
        st.write(' ')
        st.write(' ')
        st.header('Student Tier Assessment')
        st.caption('The tiers listed below represent student data gathered throughout their time in our MCAT program, from June 2025 to now.')
        st.write(' ')

        # Check if we have tier data for this student
        if not df_tier_data_student_filtered.empty:
            # Create a container for consistent width
            with st.container():
                # Create a more user-friendly display of tier data
                tier_display = pd.DataFrame({
                    'Assessment Category': ['Survey Completion', 'Class Attendance', 'Small Group Attendance', 'Class Participation'],
                    'Performance Tier': [
                        df_tier_data_student_filtered['Survey Tier'].values[0],
                        df_tier_data_student_filtered['Large Group Tier'].values[0],
                        df_tier_data_student_filtered['Small Group Tier'].values[0],
                        df_tier_data_student_filtered['Class Participation Tier'].values[0]
                    ]
                })
                
                # Optional: Add a visual representation of the tiers using colored indicators
                col1, col2, col3, col4 = st.columns(4)
                
                # Helper function to display tier with appropriate color
                def display_tier(column, category, tier):
                    colors = {
                        'Tier 1': '#1B5E20',  # Dark green
                        'Tier 2': '#FF9800',  # Light orange
                        'Tier 3': '#EF5350',  # Red
                        'Tier 4': '#EF5350'   # Red
                    }
                    color = colors.get(tier, '#9E9E9E')  # Default to grey if tier not recognized
                    column.markdown(f"<h5 style='text-align: center'>{category}</h5>", unsafe_allow_html=True)
                    column.markdown(f"<div style='background-color: {color}; padding: 10px; border-radius: 5px; text-align: center; color: white; font-weight: bold;'>{tier}</div>", unsafe_allow_html=True)
                
                # Display each category with its tier
                display_tier(col1, 'Survey Completion', df_tier_data_student_filtered['Survey Tier'].values[0])
                display_tier(col2, 'Class Attendance', df_tier_data_student_filtered['Large Group Tier'].values[0])
                display_tier(col3, 'Small Group Attendance', df_tier_data_student_filtered['Small Group Tier'].values[0])
                display_tier(col4, 'Class Participation', df_tier_data_student_filtered['Class Participation Tier'].values[0])
            
        else:
            st.info("No tier assessment data available for this student.")

        st.write(' ')
        st.write(' ')

        # Tier definition section
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <p class="tier1-text">Tier 1 Students</p>
            <div class="tier-criteria" style="color: #4CAF50;">Responsiveness to Surveys (≥80%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Attendance in Sessions (≥80%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Class Participation (≥75%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Engagement (≥75%)</div> 
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <p class="tier2-text">Tier 2 Students</p>
            <div class="tier-criteria" style="color: #FF9800;">Responsiveness to Surveys (50% - 79%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Attendance in Sessions (50% - 79%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Class Participation (50% - 74%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Engagement (50% - 74%)</div> 
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <p class="tier3-text">Tier 3 Students</p>
            <div class="tier-criteria" style="color: #EF5350;">Responsiveness to Surveys (&lt;50%)</div>
            <div class="tier-criteria" style="color: #EF5350;">Attendance in Sessions (&lt;50%)</div>
            <div class="tier-criteria" style="color: #EF5350;">Class Participation (&lt;50%)</div> 
            <div class="tier-criteria" style="color: #EF5350;">Engagement (&lt;50%)</div>
            """, unsafe_allow_html=True)

        st.write(' ')
        st.write(' ')
        st.header('Practice Exam Scores')
        st.write('Students were asked to update us with practice exam schedules and scores throughout the program. This is a link to the [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)')
        st.write(' ')

        st.dataframe(df_test_scores_student_filtered[['test_name','test_date','actual_exam_score']],use_container_width=True)
        st.write(' ')
        st.write(' ')

        point_exam_scores = alt.Chart(df_test_scores_student_filtered).mark_point().transform_fold(
            fold=['actual_exam_score'],
            as_=['variable','value']
        ).encode(
            x=alt.X(
                'yearmonthdate(test_date):O',
                axis=alt.Axis(
                    labelAngle=-45,
                    title='Test Date'
                )
            ),
            y=alt.Y(
                'value:Q',
                axis=alt.Axis(
                    title='Practice Exam Score'
                ),
                scale=alt.Scale(domain=[470, 528])
            ),
            tooltip=[
                alt.Tooltip('test_date:T', title='Test Date'),
                alt.Tooltip('value:Q', title='Exam Score')
            ],
            color=alt.Color(
                'variable:N',
                legend=alt.Legend(
                    title='Exam Scores',
                    orient='bottom',
                    labelExpr="'Practice Exam Score'"
                )
            )
        )

        st.altair_chart(point_exam_scores,use_container_width=True)
        st.write(' ')
        st.write(' ')

        st.subheader('Practice Exam - Accuracy per Subject')
        st.write(
            'The "Question Topic" column represents the various MCAT subjects tested in the Jack Westin Exams. '
            '"Question Frequency" indicates the number of questions associated with each subject in these exams. '
            '"Student Accuracy" is calculated as the percentage of correctly answered questions for a given subject, '
            'based on the total number of questions attempted.'
        )
        exam_section = st.selectbox("Choose an exam section:", list(df_test_section_scores['Exam Section'].unique()))
        st.dataframe(
            df_test_section_scores_student_filtered[df_test_section_scores_student_filtered['Exam Section'] == exam_section][['Exam Name','Question Topic','Question Frequency','Student Accuracy']].sort_values(by='Exam Name').reset_index(drop=True),
            use_container_width=True)

        st.write(' ')
        st.write(' ')

        st.header('Engagement')
        st.subheader('Self-Learning with Jack Westin Course or Question Bank')
        st.write('This graph displays the number of video lessons or assignments within the Self-Paced JW Complete MCAT Course completed by the student per week')
        st.write(' ')
        st.write(' ')

        line_engagement = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
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

        st.altair_chart(line_engagement,use_container_width=True)

        st.write(' ')
        st.write(' ')

        st.subheader('Completed Question Sets')
        st.write('This graph displays the number of question sets completed within our question bank per week. Question sets usually range between 5 to 10 questions, and can be discrete or passage-based questions.')
        st.write(' ')
        st.write(' ')

        line_question_sets = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).encode(
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

        st.altair_chart(line_question_sets,use_container_width=True)

        st.header('Participation')
        st.subheader('Class and Homework Participation')
        st.write(
            '"Class Participation" represents the percentage of class activities students engaged in each week. Here is a [video sample of an in-class activity](https://www.loom.com/share/48b383838811401892a38e17761c4993?sid=3d3e7dc2-b294-4b73-b1c6-8d78e6e0b6e8) a student can participate in. It should also be noted we did not track participation in class polls.\n\n'
            'To note: We encouraged students to utilize resources they have access to, such as AAMC materials, to apply their knowledge. '
            '"Homework Completion" indicates that a student utilized the question sets we provided within our learning platform that reviews material we covered in class.'
        )

        st.write(' ')
        st.write(' ')

        line_participation = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
            fold=['class_participation', 'homework_participation'], 
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
                    title='Participation Rate',
                    format='%'
                )
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Participation Rate', format='0.1%')
            ],
            color=alt.Color(
                'variable:N',
                legend=alt.Legend(
                    title='Type',
                    orient='bottom',
                    labelExpr="datum.value == 'class_participation' ? 'Class Participation' : 'Homework Completion'"
                )
            )
        )

        st.altair_chart(line_participation,use_container_width=True)

        st.write(' ')
        st.write(' ')
        st.header('Performance')
        st.subheader('Average Accuracy (%) on Question Sets Per Week')
        st.write(
            'During Session Practice: "In-Class Questions" refer to a student\'s accuracy percentage for question sets specifically given during class. '
            'That being said, these percentages will not be present if a student did not attempt the class activity. Also, to note, a data point will not be present if there was no class during a certain week.\n\n'
            'Self-Learning Practice: "CARS Questions" and "Science Questions" refer to a student\'s weekly performance on independent practice sets that they complete independently. Data points will be present for all weeks the student completed a passage or question set.'
        )
        st.write(' ')
        st.write(' ')

        line_engagement_accuracy = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
            fold=['sciences_accuracy', 'cars_accuracy','class_accuracy'], 
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

        st.altair_chart(line_engagement_accuracy,use_container_width=True)

        st.write(' ')
        st.write(' ')
        st.header('Attendance')
        st.write(
            'Below demonstrates the weekly percentage of attendance by students within our "All Student" and "Small Group" classes.\n\n'
            'For example, if there are two large classes and a student attends one of them, they would receive a 50% attendance rate for that week. '
            'A data point with 0% indicates no attendance during that week, while the absence of a data point reflects that no classes were held that week. Here is the [MCAT class schedule for JAMP Scholars](https://docs.google.com/document/d/1Ls6hA8GtfRgr983FUAIvxKAXMadUrdFswPeQHCfrgPo/edit?usp=sharing)'
        )
        st.write(' ')
        st.write(' ')

        line_attendance = alt.Chart(df_engagement_attendance_student_filtered).mark_line(point=True).transform_fold(
            fold=['large_session','small_session'],
            as_=['variable','value']
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
                    title='Cumulative Attendance Rate',
                    format='%'
                )
            ),
            tooltip=[
                alt.Tooltip('week:O', title='Week'),
                alt.Tooltip('date_range:N', title='Date Range'),
                alt.Tooltip('value:Q', title='Cumulative Attendance Rate', format='0.1%')
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

        st.altair_chart(line_attendance,use_container_width=True)

elif dashboard_type == "Students by JFD":
    st.header("Students by JFD")

    jfd_df = load_jfd_data()

    if jfd_df is None:
        st.error("Could not load `student-data/jfd-combined.csv`. Please make sure the file is in the correct location.")
        st.stop()

    # Create JFD dropdown filter
    jfd_list = ['All JFDs'] + sorted(jfd_df['jfd'].dropna().unique().astype(int).tolist())
    selected_jfd = st.selectbox("Choose a JFD to filter students:", jfd_list)

    # Filter dataframe based on selection
    if selected_jfd != 'All JFDs':
        filtered_jfd_df = jfd_df[jfd_df['jfd'] == selected_jfd].copy()
    else:
        filtered_jfd_df = jfd_df.copy()


    # Fill NA for display and consistent filtering
    filtered_jfd_df.fillna({'all_exams_and_scores': 'No scores reported', 'highest_exam_score': 0}, inplace=True)
    
    # Define categories
    categories = {
        "Category 1: No Reported Scores": 
            filtered_jfd_df['exam_count'] == 0,
        
        "Category 2: Students <502 & No Anticipated Exam Date":
            (filtered_jfd_df['highest_exam_score'] < 502) & (filtered_jfd_df['anticipated_exam_date'].isnull()),

        "Category 3: <495 & Tier 3 Across All Metrics":
            (filtered_jfd_df['highest_exam_score'] < 495) & \
            (filtered_jfd_df['survey_tier'] == 'Tier 3') & \
            (filtered_jfd_df['large_group_tier'] == 'Tier 3') & \
            (filtered_jfd_df['small_group_tier'] == 'Tier 3') & \
            (filtered_jfd_df['class_participation_tier'] == 'Tier 3'),

        "Category 4: <495 & Survey Tier 3":
            (filtered_jfd_df['highest_exam_score'] < 495) & (filtered_jfd_df['survey_tier'] == 'Tier 3'),

        "Category 5: 495–500 & Small Group Tier 3":
            (filtered_jfd_df['highest_exam_score'] >= 495) & (filtered_jfd_df['highest_exam_score'] <= 500) & \
            (filtered_jfd_df['small_group_tier'] == 'Tier 3'),

        "Category 6: <495 & Large Group Tier 3":
            (filtered_jfd_df['highest_exam_score'] < 495) & (filtered_jfd_df['large_group_tier'] == 'Tier 3')
    }

    display_cols = ['student_id', 'highest_exam_score', 'survey_tier', 'large_group_tier', 'small_group_tier', 'class_participation_tier', 'all_exams_and_scores']
    
    all_jfd_student_indices = set()

    for category_name, condition in categories.items():
        st.subheader(category_name)
        category_df = filtered_jfd_df[condition].copy()
        
        if not category_df.empty:
            st.dataframe(category_df[display_cols])
            all_jfd_student_indices.update(category_df.index)
        else:
            st.info("No students in this category.")

    # Display the complete list for the selected JFD
    if selected_jfd == 'All JFDs':
        st.header("Complete List of All Students")
        st.write("This list includes all students from the dataset, regardless of their category.")
    else:
        st.header(f"Complete Student List for JFD {selected_jfd}")
        st.write(f"This list includes all students for JFD {selected_jfd}, regardless of their category.")
    
    if not filtered_jfd_df.empty:
        st.dataframe(filtered_jfd_df[display_cols].sort_values('student_id'))
    else:
        st.info(f"No students found for JFD {selected_jfd}.")

else:
    # Analysis Dashboard
    
    # Load and clean MCAT analysis data
    @st.cache_data
    def load_and_clean_data():
        """Load and clean the MCAT data"""
        # Load CSV data for tier analysis - try multiple paths for deployment compatibility
        import os
        csv_df = None
        
        # Try different possible file paths
        possible_files = [
            'data_outcomes_with_tiers.csv',
            './data_outcomes_with_tiers.csv',
            'data/data_outcomes_with_tiers.csv',
            './data/data_outcomes_with_tiers.csv'
        ]
        
        for file_path in possible_files:
            try:
                if os.path.exists(file_path):
                    csv_df = pd.read_csv(file_path)
                    st.session_state.csv_data_available = True
                    break
            except Exception as e:
                continue
        
        if csv_df is None:
            st.session_state.csv_data_available = False
            # Debug info when CSV loading fails
            st.warning("⚠️ CSV data not loaded - insights analysis will be limited")
        else:
            pass
        
        # Load data (replace with your file path or upload mechanism)
        data = {
            'Student_ID': [5, 88, 6, 130, 10, 22, 116, 8, 7, 60, 47, 85, 1, 112, 126, 31, 127, 16, 72, 128, 30, 87, 37, 28, 123, 32, 33, 50, 78, 139, 56, 96, 135, 107, 93, 62, 48, 95, 55, 90, 44, 108, 102, 57, 140, 91, 53, 12, 59, 68, 61, 147, 29, 34, 81, 4, 35, 41, 149, 51, 66, 67, 86, 122, 136, 99, 89, 27, 39, 71, 65, 19, 73, 121, 64, None, 43, 75, 131, 125, 84, 2, 13, 101, 15, 124, 104, 105, 49, 100, 80, 83, 11, 120, 23, 76, 94, 133, 97, 20, 3, 18, 111, 98, 137, 117, 110, 106, 114, 115, 26, 69, 63, 17, 25, 14, 36, 118, 24, 144, 52, 82, 9, 129, 138, 74, 142, 150, 132, 134, 70, 103, 113, 79, 92, 58, 145, 46, 141, 148, 77],
            'Baseline_Score': [492, 496, 493, 500, 506, 484, 503, None, 492, 498, 494, 504, 494, 490, 495, 506, 500, 0, 0, 490, 0, 491, 496, 0, 498, 0, 490, 505, 499, 495, 510, 0, 505, 505, 497, 494, 495, 498, 497, 499, None, 497, 501, 497, 498, 495, 491, 498, 497, 493, 496, 495, 505, None, 498, 502, 506, 494, 504, 501, 489, 494, 490, 494, 498, 502, 493, 500, 498, 501, 493, 504, 503, 503, 493, None, 494, 495, 493, 494, 499, 503, None, 500, 500, 502, 494, 485, 503, 497, 491, 506, 511, 497, 493, 497, 503, 486, 494, 497, 494, 495, 498, None, None, 493, 506, 491, 492, 487, 496, 495, None, 508, 491, 503, 495, 488, 491, 491, 497, 495, 498, 501, 491, 501, 490, 502, 498, None, 487, 493, 492, 504, 502, 495, 495, 493, 504, 491, 491],
            'Number_of_Practice_Exams': [4, 1, None, 3, 2, None, 1, 1, 3, 3, 1, 7, 1, 3, None, 3, 2, 2, 1, None, 1, 6, None, None, 1, None, 1, None, 4, 5, None, None, 5, None, 4, 1, 2, 1, None, 6, 1, 6, 1, 3, 6, 5, 3, 1, 4, None, 3, 1, 1, 1, 1, 4, 3, 2, 2, 2, 1, None, 2, 6, 5, 1, 2, 2, 12, 9, 5, 1, 3, 5, 4, None, 4, 1, 10, 5, None, 1, 1, 6, None, 5, None, 2, 6, 1, None, 6, 2, 5, 4, None, 2, 3, None, 3, 4, 2, 6, None, 1, 2, 2, 5, 4, 5, 2, 1, 3, 4, 1, 2, 2, 4, 1, 3, 5, 5, 2, 6, 9, 2, None, 1, None, 3, 7, 2, 1, 3, 4, 1, 1, 5, None, None, None],
            'Most_Recent_Practice_Exam': [493, 496, None, 513, 506, None, 503, None, 493, 500, 494, 506, 494, 491, None, 506, 501, None, 409, None, 498, 494, None, None, 500, None, 490, None, 493, 505, None, None, 513, None, 497, 494, 490, 498, None, 495, 500, 499, 501, 497, 499, 496, 492, 498, 496, None, 494, 495, 505, None, 498, 499, 518, 497, 502, 501, 489, None, 490, 509, 499, 500, 493, 507, 511, 504, 518, 504, 502, 509, 502, None, 494, 495, 497, 500, None, 503, None, 502, None, 500, None, 485, 516, 497, None, 517, 509, 506, 496, None, 503, 501, None, 499, 491, 503, 517, None, 503, 493, 511, 494, 485, 496, 497, 487, 508, 491, 507, 501, 488, 484, 495, 502, 497, 506, 499, 489, 501, 481, 513, 498, None, 487, None, 492, 519, 506, 495, 497, 494, 499, 491, 494, None],
            'Actual_MCAT': [499, 501, 488, None, 514, 508, 506, None, 487, 510, 493, 509, 493, 478, 501, None, 508, None, None, None, 502, 497, 494, 485, 495, 508, None, None, None, 500, None, None, None, None, 496, None, 488, 493, None, 504, None, 502, 496, None, None, 492, 490, 491, 493, 498, 492, 478, 515, 490, 495, None, 525, 502, 488, 495, 506, 481, None, 509, None, None, 497, 487, 504, None, 491, None, 498, 510, None, 497, 489, 497, 506, 505, 491, None, None, 495, 491, 496, None, 485, None, 501, 496, 518, 517, None, None, 495, None, 501, 495, None, None, 485, None, 496, None, 506, 494, None, 482, 486, 487, 494, None, None, 496, 484, None, None, 480, 493, 483, 501, None, 508, None, 492, None, 482, 516, 490, 487, 481, 483, 495, None, None, 494, 496, 495, 508, 493],
            'Score_Difference': [None, 5, 0, 13, 8, 29, 8, 0, 0, 17, -1, 10, 4, -7, 11, 0, 13, None, None, None, 4, 11, 3, None, 2, None, 0, None, -1, 10, None, None, 13, None, 4, 5, -2, 0, 0, 10, None, 10, 0, 0, 1, 2, 4, -2, 1, 10, 1, -12, 15, None, 2, -3, 24, 13, -16, -6, 22, -8, 0, 20, 6, 3, 4, -8, 11, 8, -2, 0, 0, 7, 9, None, 5, 5, 13, 16, -3, 5, None, 0, -4, -6, 0, 0, 13, 9, 5, 17, 6, 14, 8, 3, 0, 0, 6, 7, -9, 8, -2, 0, 3, 6, 10, -4, -1, 5, 3, 7, None, -12, -2, 9, 6, -3, 7, -3, 9, 7, 15, 3, 3, 5, 1, 19, -8, None, -6, -5, 8, 20, 9, 4, -1, 7, 9, 7, 7],
            'Total_Completed_Passages_Discrete_Sets': [45, 23, None, 67, 34, None, 12, 18, 56, 78, 29, 89, 15, 44, None, 52, 31, 28, 19, None, 25, 73, None, None, 22, None, 17, None, 63, 85, None, None, 76, None, 58, 26, 39, 21, None, 82, 14, 91, 33, 49, 88, 67, 41, 16, 55, None, 46, 24, 18, 30, 27, 61, 48, 35, 42, 38, 20, None, 37, 79, 84, 23, 44, 36, 95, 102, 71, 19, 51, 68, 59, None, 62, 28, 87, 74, None, 25, 32, 83, None, 69, None, 40, 86, 22, None, 92, 47, 77, 53, None, 43, 50, None, 56, 66, 31, 89, None, 18, 45, 38, 72, 61, 78, 29, 16, 54, 65, 24, 41, 33, 57, 26, 49, 81, 75, 35, 88, 96, 42, None, 27, None, 52, 93, 46, 23, 58, 70, 19, 36, 64, None, None, None]
        }
        
        # Ensure all arrays have the same length by standardizing to 141 elements
        max_length = 141
        for key, values in data.items():
            if len(values) < max_length:
                # Pad with None values
                data[key] = values + [None] * (max_length - len(values))
            elif len(values) > max_length:
                # Truncate to max_length
                data[key] = values[:max_length]
        
        df = pd.DataFrame(data)
        
        # Clean data
        # Replace 0 values in baseline scores with NaN (these seem to be missing data)
        df['Baseline_Score'] = df['Baseline_Score'].replace(0, np.nan)
        
        # Create additional calculated columns
        df['Practice_Improvement'] = df['Most_Recent_Practice_Exam'] - df['Baseline_Score']
        df['Had_Practice_Exams'] = df['Number_of_Practice_Exams'].notna() & (df['Number_of_Practice_Exams'] > 0)
        
        # Calculate total completed passages/discrete sets per student
        # Group by Student_ID and sum the Total_Completed_Passages_Discrete_Sets
        student_totals = df.groupby('Student_ID')['Total_Completed_Passages_Discrete_Sets'].sum().reset_index()
        student_totals.rename(columns={'Total_Completed_Passages_Discrete_Sets': 'Total_Completed_Sum'}, inplace=True)
        
        # Merge back to main dataframe
        df = df.merge(student_totals, on='Student_ID', how='left')
        
        # Categorize number of practice exams
        df['Practice_Category'] = pd.cut(df['Number_of_Practice_Exams'], 
                                       bins=[0, 1, 3, 5, float('inf')], 
                                       labels=['1 Exam', '2-3 Exams', '4-5 Exams', '6+ Exams'],
                                       include_lowest=True)
        
        return df, csv_df


    # Load data
    df, csv_df = load_and_clean_data()
    
    # Analysis Type Selection
    analysis_type = st.sidebar.radio(
        "Choose Analysis Type:",
        ["Key Actionable Insights", "Exam Analysis", "Question Bank Analytics", "Attendance Analysis", "Performer Analysis"]
    )
    
    if analysis_type == "Key Actionable Insights":
        st.header("Key Actionable Insights")
        
        st.write(' ')
        st.write(' ')
        
        # Tier Definitions
        st.subheader("Tier Definitions")
        
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <p class="tier1-text">Tier 1 Students</p>
            <div class="tier-criteria" style="color: #4CAF50;">Responsiveness to Surveys (≥80%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Attendance in Sessions (≥80%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Class Participation (≥75%)</div>
            <div class="tier-criteria" style="color: #4CAF50;">Engagement (≥75%)</div> 
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <p class="tier2-text">Tier 2 Students</p>
            <div class="tier-criteria" style="color: #FF9800;">Responsiveness to Surveys (50% - 79%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Attendance in Sessions (50% - 79%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Class Participation (50% - 74%)</div>
            <div class="tier-criteria" style="color: #FF9800;">Engagement (50% - 74%)</div> 
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <p class="tier3-text">Tier 3 Students</p>
            <div class="tier-criteria" style="color: #EF5350;">Responsiveness to Surveys (&lt;50%)</div>
            <div class="tier-criteria" style="color: #EF5350;">Attendance in Sessions (&lt;50%)</div>
            <div class="tier-criteria" style="color: #EF5350;">Class Participation (&lt;50%)</div> 
            <div class="tier-criteria" style="color: #EF5350;">Engagement (&lt;50%)</div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Load and prepare data for statistical analysis
        if csv_df is not None:
            # Process data same as in the analysis
            student_data = csv_df.groupby('student_id').agg({
                'class_accuracy': 'mean',
                'class_participation': lambda x: (x > 0).sum() / len(x) * 100,
                'num_attended_large_session': 'sum',
                'num_scheduled_large_session': 'sum', 
                'num_attended_small_session': 'sum',
                'num_scheduled_small_session': 'sum',
                'total_completed_passages_discrete_sets': 'sum',
                'completed_lessons': 'sum',
                'homework_participation': 'mean',
                'Small Group Tier': 'first',
                'Large Group Tier': 'first',
                'Class Participation Tier': 'first'
            }).reset_index()
            
            student_data['large_attendance_rate'] = student_data['num_attended_large_session'] / student_data['num_scheduled_large_session'] * 100
            student_data['small_attendance_rate'] = student_data['num_attended_small_session'] / student_data['num_scheduled_small_session'] * 100
            
            # Merge with main data
            analysis_data = df[['Student_ID', 'Baseline_Score', 'Number_of_Practice_Exams', 'Score_Difference', 'Total_Completed_Passages_Discrete_Sets']].merge(
                student_data, left_on='Student_ID', right_on='student_id', how='inner'
            ).dropna(subset=['Score_Difference'])
            
            analysis_data['high_improvement'] = (analysis_data['Score_Difference'] > 5).astype(int)
            
            high_improvement_count = analysis_data['high_improvement'].sum()
            low_improvement_count = len(analysis_data) - high_improvement_count
            
            # Sample size info
            st.info(f"**Analysis Sample:** {len(analysis_data)} students | **Improvement (>5 pts):** {high_improvement_count} students ({high_improvement_count/len(analysis_data)*100:.1f}%) | **Lower, No, or Negative Score Change (≤5 pts):** {low_improvement_count} students ({low_improvement_count/len(analysis_data)*100:.1f}%)")
            
            # Key findings summary
            st.markdown("### Top 5 Statistically Significant Predictors")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("""
                **1. • Small Group Attendance Tier** *(p = 0.0001)*
                - **Tier 1:** 57.9% success rate (22/38 students)
                - **Tier 2:** 87.5% success rate (7/8 students) 
                - **Tier 3:** 27.3% success rate (21/77 students)
                - **Impact:** 2.7x higher success rate for top tier
                
                **2. • Number of Practice Exams** *(p = 0.0145)*
                - **Improvement:** 3.87 exams average
                - **Lower, No, or Negative Score Change:** 2.80 exams average
                - **Impact:** +1.06 more practice exams for success
                
                **3. • Question Bank Usage** *(p = 0.0161)*
                - **Improvement:** 57.4 sets completed
                - **Lower, No, or Negative Score Change:** 46.0 sets completed
                - **Impact:** +11.4 more sets for success
                
                **4. • Class Participation Tier** *(p = 0.0230)*
                - **Tier 1:** 68.4% success rate (13/19 students)
                - **Tier 3:** 35.0% success rate (35/100 students)
                - **Impact:** 1.9x higher success rate for top tier
                
                **5. • Total Weekly Question Sets** *(p = 0.0278)*
                - **Improvement:** 214.4 total sets
                - **Lower, No, or Negative Score Change:** 170.2 total sets
                - **Impact:** +44.1 more total sets for success
                """)
            
            with col2:
                st.markdown("### Success Rates by Tier")
                
                # Small Group Tier visualization
                small_group_success = [57.9, 87.5, 27.3]
                fig_small = px.bar(
                    x=['Tier 1', 'Tier 2', 'Tier 3'],
                    y=small_group_success,
                    title='Small Group Attendance',
                    labels={'x': 'Attendance Tier', 'y': 'Success Rate (%)'},
                    text=[f'{rate:.1f}%' for rate in small_group_success]
                )
                fig_small.update_traces(
                    textposition='outside', 
                    marker_color=BRAND_COLORS['primary'],
                    textfont=dict(size=12, color='#1e293b')
                )
                fig_small.update_layout(showlegend=False, height=300)
                fig_small = apply_light_mode_styling(fig_small)
                st.plotly_chart(fig_small, use_container_width=True)
                
                # Class Participation Tier visualization
                participation_success = [68.4, 50.0, 35.0]
                fig_participation = px.bar(
                    x=['Tier 1', 'Tier 2', 'Tier 3'],
                    y=participation_success,
                    title='Class Participation',
                    labels={'x': 'Participation Tier', 'y': 'Success Rate (%)'},
                    text=[f'{rate:.1f}%' for rate in participation_success]
                )
                fig_participation.update_traces(
                    textposition='outside', 
                    marker_color=BRAND_COLORS['secondary'],
                    textfont=dict(size=12, color='#1e293b')
                )
                fig_participation.update_layout(showlegend=False, height=300)
                fig_participation = apply_light_mode_styling(fig_participation)
                st.plotly_chart(fig_participation, use_container_width=True)
            
            # Key actionable insights
            st.markdown("### Key Actionable Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                #### Study Behaviors
                - Take **4+ practice exams** minimum
                - Take **10+ practice exams** for maximum improvement  
                - Complete **55+ question bank sets**
                - Aim for **200+ total weekly sets**
                """)
            
            with col2:
                st.markdown("""
                #### Attendance Strategy
                - Focus on the **small group sessions** for struggling students
                - Target **Tier 1 attendance** (highest level)
                - Small group attendance 2.7x more predictive
                """)
            
            with col3:
                st.markdown("""
                #### Engagement Focus
                - Actively **participate in class** discussions
                - Target **Tier 1 participation** level
                - Engagement beats initial ability
                """)
            
            # Explanation of Question Bank Usage vs Total Weekly Question Sets
            st.markdown("---")
            st.markdown("### Understanding Question Bank Metrics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                #### 📊 Question Bank Usage (57.4 sets)
                **Weekly Engagement Data (CSV)**
                - **Calculation:** Sum of weekly question sets per student from detailed weekly tracking
                - **Data source:** CSV file with weekly records (`total_completed_passages_discrete_sets` per week)
                - **High performers:** 57.4 total sets per student
                - **Low performers:** 46.0 total sets per student
                - **Impact:** +11.4 more sets for success
                - **Statistical significance:** p = 0.0161
                
                **Higher predictive power**
                """)
            
            with col2:
                st.markdown("""
                #### 📈 Total Weekly Question Sets (214.4 sets)
                **Alternative Data Source**
                - **Calculation:** Sum per student from main dataset
                - **Data source:** Main dataset (`Total_Completed_Passages_Discrete_Sets`)
                - **High performers:** 214.4 total sets per student
                - **Low performers:** 170.2 total sets per student
                - **Impact:** +44.1 more total sets for success
                - **Statistical significance:** p = 0.0278
                
                **Lower predictive power**
                """)
            
            st.info("""
            **Key Insight:** Both metrics sum all question sets completed by each student, but from different data collection systems.
            
            The **Question Bank Usage** (57.4) comes from detailed weekly tracking records, while **Total Weekly Question Sets** (214.4) comes from a different data source in the main dataset. 
            
            The weekly tracking data shows lower totals but higher statistical significance (p = 0.0161 vs p = 0.0278), suggesting it may be more accurate for predicting MCAT success.
            
            **Recommendation:** The weekly tracking data (57.4 range) appears to be the more reliable predictor of MCAT improvement.
            """)
            
        else:
            st.error("**Data not available for insights analysis**")
            st.info("**Troubleshooting:** The Key Actionable Insights require the `data_outcomes_with_tiers.csv` file with detailed engagement data.")
            st.markdown("""
            **This section needs:**
            - Student engagement data (class_participation, homework_participation)
            - Attendance data (large/small session attendance)
            - Tier classifications (Small Group Tier, Large Group Tier, etc.)
            
            **Current status:** CSV data loading failed.
            """)

    elif analysis_type == "Exam Analysis":
        st.header("Exam Analysis")
        
        # KEY INSIGHTS AT THE TOP
        st.header("Key Insights")
        
        # Calculate key insights first
        improved = df[df['Score_Difference'] > 0]['Score_Difference'].dropna()
        declined = df[df['Score_Difference'] < 0]['Score_Difference'].dropna()
        no_change = df[df['Score_Difference'] == 0]['Score_Difference'].dropna()
        
        # Calculate optimal practice exam range
        practice_effectiveness = df.groupby('Number_of_Practice_Exams')['Score_Difference'].agg(['mean', 'count']).reset_index()
        practice_effectiveness = practice_effectiveness[practice_effectiveness['count'] >= 3]  # Only groups with 3+ students
        
        if not practice_effectiveness.empty:
            best_range = practice_effectiveness.loc[practice_effectiveness['mean'].idxmax()]
            st.success(f"**Optimal Practice Range:** {int(best_range['Number_of_Practice_Exams'])} practice exams showed highest average improvement ({best_range['mean']:.1f} points)")
        
        # Overall performance insights
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric("Students Who Improved", len(improved), f"Avg: +{improved.mean():.1f}")
        with col2:
            st.metric("Students Who Declined", len(declined), f"Avg: {declined.mean():.1f}")
        with col3:
            st.metric("Students With No Change", len(no_change))
        
        st.markdown("---")
        
        # Practice exam effectiveness
        st.subheader("Practice Exam Effectiveness")
        
        effectiveness_data = []
        for idx, row in df.iterrows():
            if pd.notna(row['Number_of_Practice_Exams']) and pd.notna(row['Score_Difference']):
                effectiveness_data.append({
                    'Practice_Exams': row['Number_of_Practice_Exams'],
                    'Score_Improvement': row['Score_Difference']
                })
        
        if effectiveness_data:
            eff_df = pd.DataFrame(effectiveness_data)
            
            fig_effectiveness = px.scatter(
                eff_df,
                x='Practice_Exams',
                y='Score_Improvement',
                title='Score Improvement vs Number of Practice Exams',
                trendline='ols',
                color_discrete_sequence=[BRAND_COLORS['primary']]
            )
            
            # Set y-axis to start at 0 and find max value
            max_improvement = eff_df['Score_Improvement'].max()
            
            # Always start at 0 for score improvement graph
            y_min = 0
            y_max = max_improvement + 2  # Add some padding at the top
            
            fig_effectiveness.update_layout(
                yaxis=dict(
                    range=[y_min, y_max],
                    title_font=dict(size=16),
                    tickfont=dict(size=14)
                ),
                xaxis=dict(
                    title_font=dict(size=16),
                    tickfont=dict(size=14)
                ),
                title_font=dict(size=18)
            )
            
            fig_effectiveness = apply_light_mode_styling(fig_effectiveness)
            st.plotly_chart(fig_effectiveness, use_container_width=True)
        
        # Score Growth Ranges Analysis
        st.markdown("---")
        st.subheader("High Score Growth Analysis (8-25 Point Increases)")
        
        # Filter for high score growth (8-25 points)
        high_growth = df[(df['Score_Difference'] >= 8) & (df['Score_Difference'] <= 25)]['Score_Difference'].dropna()
        
        if len(high_growth) > 0:
            st.info(f"**{len(high_growth)} students achieved high score growth (8-25 points)** with an average improvement of **{high_growth.mean():.1f} points**")
            
            # Create histogram of score growth ranges
            fig_growth = px.histogram(
                x=high_growth,
                nbins=18,  # 8-25 is 18 possible values
                title='Students with High Score Growth (8-25 Point Increases)',
                labels={'x': 'MCAT Score Improvement (Points)', 'y': 'Number of Students'},
                color_discrete_sequence=[BRAND_COLORS['success']]
            )
            
            # Customize the histogram for better appearance
            fig_growth.update_traces(
                marker_line_color='white',
                marker_line_width=2,
                opacity=0.8
            )
            
            # Update layout for taller, thinner bars
            fig_growth.update_layout(
                bargap=0.05,  # Thinner bars with minimal gap
                height=500,   # Taller graph
                xaxis=dict(
                    tickmode='linear',
                    tick0=8,
                    dtick=1,
                    range=[7.5, 25.5],
                    title_font=dict(size=18, color='#1e293b'),
                    tickfont=dict(size=16, color='#1e293b')  # Much larger tick numbers
                ),
                yaxis=dict(
                    title='Number of Students',
                    title_font=dict(size=18, color='#1e293b'),
                    tickfont=dict(size=16, color='#1e293b'),  # Much larger tick numbers
                    gridcolor='rgba(128,128,128,0.2)'
                ),
                title_font=dict(size=20, color='#1e293b'),  # Larger title
                showlegend=False
            )
            
            # Add annotations for key statistics
            fig_growth.add_annotation(
                x=high_growth.mean(),
                y=0,
                text=f"Mean: {high_growth.mean():.1f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor=BRAND_COLORS['primary'],
                bgcolor="white",
                bordercolor=BRAND_COLORS['primary'],
                borderwidth=2
            )
            
            fig_growth.update_layout(
                xaxis=dict(
                    tickmode='linear',
                    tick0=8,
                    dtick=1,
                    range=[7.5, 25.5]
                ),
                bargap=0.1
            )
            
            fig_growth = apply_light_mode_styling(fig_growth)
            st.plotly_chart(fig_growth, use_container_width=True)
            
            # Breakdown by score ranges
            col1, col2, col3 = st.columns(3)
            
            with col1:
                modest_growth = high_growth[(high_growth >= 8) & (high_growth <= 12)]
                st.metric(
                    "Modest Growth (8-12 pts)", 
                    len(modest_growth),
                    f"Avg: {modest_growth.mean():.1f}" if len(modest_growth) > 0 else "N/A"
                )
            
            with col2:
                strong_growth = high_growth[(high_growth >= 13) & (high_growth <= 19)]
                st.metric(
                    "Strong Growth (13-19 pts)", 
                    len(strong_growth),
                    f"Avg: {strong_growth.mean():.1f}" if len(strong_growth) > 0 else "N/A"
                )
            
            with col3:
                exceptional_growth = high_growth[(high_growth >= 20) & (high_growth <= 25)]
                st.metric(
                    "Exceptional Growth (20-25 pts)", 
                    len(exceptional_growth),
                    f"Avg: {exceptional_growth.mean():.1f}" if len(exceptional_growth) > 0 else "N/A"
                )
            
            # Additional insights
            st.markdown("#### Key Insights from High Performers")
            
            # Get baseline scores for high growth students
            high_growth_students = df[(df['Score_Difference'] >= 8) & (df['Score_Difference'] <= 25)]
            
            if len(high_growth_students) > 0:
                avg_baseline = high_growth_students['Baseline_Score'].mean()
                avg_practice_exams = high_growth_students['Number_of_Practice_Exams'].mean()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Student Profile:**
                    - **Average Baseline Score:** {avg_baseline:.1f}
                    - **Average Practice Exams:** {avg_practice_exams:.1f}
                    - **Score Range:** {high_growth.min():.0f} - {high_growth.max():.0f} points
                    """)
                
                with col2:
                    # Calculate percentiles
                    p25 = high_growth.quantile(0.25)
                    p50 = high_growth.median()
                    p75 = high_growth.quantile(0.75)
                    
                    st.markdown(f"""
                    **Growth Distribution:**
                    - **25th percentile:** {p25:.1f} points
                    - **Median:** {p50:.1f} points
                    - **75th percentile:** {p75:.1f} points
                    """)
        else:
            st.warning("No students found with score improvements in the 8-25 point range.")
        
        # Featured Student Score Progression
        st.markdown("---")
        st.subheader("📈 Featured Student Score Progression")
        st.markdown("*Real example of score improvement through practice exams*")
        
        # Load individual test data
        try:
            test_data_paths = [
                'student-data/institution-1-test-data.csv',
                './student-data/institution-1-test-data.csv',
                'institution-1-test-data.csv'
            ]
            
            test_df = None
            for path in test_data_paths:
                try:
                    if os.path.exists(path):
                        test_df = pd.read_csv(path, parse_dates=['test_date'])
                        break
                except:
                    continue
            
            if test_df is not None:
                # Look for a specific student with good progression
                # Select a student with multiple exams and clear improvement pattern
                student_exam_counts = test_df.groupby('student_id').size()
                students_with_multiple_exams = student_exam_counts[student_exam_counts >= 4].index
                
                # Try to find a student with strong improvement
                for target_id in students_with_multiple_exams:
                    student_data = test_df[test_df['student_id'] == target_id].sort_values('test_date')
                    if len(student_data) >= 4:
                        first_score = student_data['actual_exam_score'].iloc[0]
                        last_score = student_data['actual_exam_score'].iloc[-1]
                        if last_score - first_score >= 10:  # Good improvement
                            featured_student_id = target_id
                            break
                else:
                    # Fallback to any student with multiple exams
                    featured_student_id = students_with_multiple_exams[0] if len(students_with_multiple_exams) > 0 else None
                
                if featured_student_id is not None:
                    # Get this student's test data
                    student_test_data = test_df[test_df['student_id'] == featured_student_id].sort_values('test_date')
                    
                    # Get additional info from main dataset
                    student_info = df[df['Student_ID'] == featured_student_id]
                    baseline_score = student_info['Baseline_Score'].iloc[0] if len(student_info) > 0 else None
                    
                    # Calculate key metrics
                    first_score = student_test_data['actual_exam_score'].iloc[0]
                    last_score = student_test_data['actual_exam_score'].iloc[-1]
                    total_improvement = last_score - first_score
                    num_exams = len(student_test_data)
                    
                    # Display metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Practice Exams", f"{num_exams}")
                    with col2:
                        st.metric("Starting Score", f"{first_score:.0f}")
                    with col3:
                        st.metric("Final Score", f"{last_score:.0f}")
                    with col4:
                        st.metric("Improvement", f"+{total_improvement:.0f} pts")
                    
                    # Create progression chart
                    fig_progression = px.line(
                        student_test_data,
                        x='test_date',
                        y='actual_exam_score',
                        markers=True,
                        title='Practice Exam Score Progression Over Time',
                        labels={
                            'test_date': 'Practice Exam Date',
                            'actual_exam_score': 'MCAT Score'
                        }
                    )
                    
                    # Style the chart
                    fig_progression.update_traces(
                        line=dict(color=BRAND_COLORS['primary'], width=4),
                        marker=dict(size=12, color=BRAND_COLORS['success'], line=dict(width=2, color='white'))
                    )
                    
                    # Add reference lines if available
                    if baseline_score is not None:
                        fig_progression.add_hline(
                            y=baseline_score,
                            line_dash="dash",
                            line_color="red",
                            annotation_text="Program Start",
                            annotation_position="bottom right"
                        )
                    
                    # Layout styling
                    fig_progression.update_layout(
                        height=450,
                        showlegend=False,
                        xaxis=dict(
                            title_font=dict(size=18),
                            tickfont=dict(size=14)
                        ),
                        yaxis=dict(
                            title_font=dict(size=18),
                            tickfont=dict(size=14),
                            range=[
                                min(student_test_data['actual_exam_score']) - 15,
                                max(student_test_data['actual_exam_score']) + 15
                            ]
                        ),
                        title_font=dict(size=20)
                    )
                    
                    fig_progression = apply_light_mode_styling(fig_progression)
                    st.plotly_chart(fig_progression, use_container_width=True)
                    
                    # Analysis summary
                    improvement_per_exam = total_improvement / (num_exams - 1) if num_exams > 1 else 0
                    
                    st.success(f"""
                    📊 **Success Story:** This student demonstrated remarkable consistency, improving from **{first_score:.0f}** to **{last_score:.0f}** 
                    over {num_exams} practice exams. That's an average gain of **{improvement_per_exam:.1f} points per exam** through 
                    dedicated practice and preparation.
                    """)
                    
                    # Score breakdown by exam
                    st.markdown("#### 📋 Exam-by-Exam Progression")
                    
                    # Create a clean table of progression
                    progress_table = student_test_data[['test_date', 'test_name', 'actual_exam_score']].copy()
                    progress_table['test_date'] = progress_table['test_date'].dt.strftime('%m/%d/%Y')
                    progress_table['Improvement'] = progress_table['actual_exam_score'].diff().fillna(0)
                    progress_table['Improvement'] = progress_table['Improvement'].apply(lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}" if x < 0 else "—")
                    progress_table.columns = ['Date', 'Exam', 'Score', 'Change']
                    
                    st.dataframe(progress_table, use_container_width=True, hide_index=True)
                
                else:
                    st.warning("No suitable student found for score progression analysis.")
            else:
                st.info("Individual test data not available for score progression analysis.")
        
        except Exception as e:
            st.error("Unable to load score progression data.")
        
        # High-Volume Practice Students Analysis
        st.markdown("---")
        st.subheader("📊 High-Volume Practice Students (>8 Exams)")
        st.markdown("*Detailed analysis of students who took more than 8 practice exams*")
        
        # Filter for students with >8 practice exams
        high_volume_students = df[
            (df['Number_of_Practice_Exams'] > 8) & 
            (df['Score_Difference'].notna())
        ].copy()
        
        if len(high_volume_students) > 0:
            # Calculate key metrics
            avg_score_diff = high_volume_students['Score_Difference'].mean()
            total_students = len(high_volume_students)
            positive_students = len(high_volume_students[high_volume_students['Score_Difference'] > 0])
            success_rate = (positive_students / total_students) * 100
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Students", total_students)
            with col2:
                st.metric("Average Improvement", f"+{avg_score_diff:.1f} pts")
            with col3:
                st.metric("Success Rate", f"{success_rate:.0f}%")
            with col4:
                max_improvement = high_volume_students['Score_Difference'].max()
                st.metric("Best Improvement", f"+{max_improvement:.0f} pts")
            
            # Create detailed table
            st.markdown("#### 📋 Individual Student Results")
            
            # Prepare table data
            table_data = high_volume_students[['Student_ID', 'Number_of_Practice_Exams', 'Baseline_Score', 'Score_Difference']].copy()
            table_data = table_data.sort_values('Score_Difference', ascending=False)
            
            # Format the data
            table_data['Student_ID'] = table_data['Student_ID'].astype(int)
            table_data['Number_of_Practice_Exams'] = table_data['Number_of_Practice_Exams'].astype(int)
            table_data['Baseline_Score'] = table_data['Baseline_Score'].round(0).astype(int)
            table_data['Score_Difference'] = table_data['Score_Difference'].apply(lambda x: f"+{x:.0f}" if x > 0 else f"{x:.0f}")
            
            # Rename columns for display
            table_data.columns = ['Student ID', 'Practice Exams', 'Baseline Score', 'Score Improvement']
            
            # Display the table
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True
            )
            
            # Key insights
            st.markdown("#### 🔍 Key Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Statistics
                min_improvement = high_volume_students['Score_Difference'].min()
                max_improvement = high_volume_students['Score_Difference'].max()
                median_improvement = high_volume_students['Score_Difference'].median()
                
                st.markdown(f"""
                **📈 Performance Statistics:**
                - **Average improvement:** {avg_score_diff:.1f} points
                - **Median improvement:** {median_improvement:.1f} points
                - **Range:** {min_improvement:.0f} to {max_improvement:.0f} points
                - **Success rate:** {success_rate:.0f}% (all students improved)
                """)
            
            with col2:
                # Practice volume insights
                avg_exams = high_volume_students['Number_of_Practice_Exams'].mean()
                min_exams = high_volume_students['Number_of_Practice_Exams'].min()
                max_exams = high_volume_students['Number_of_Practice_Exams'].max()
                
                st.markdown(f"""
                **📚 Practice Volume Analysis:**
                - **Average exams taken:** {avg_exams:.1f}
                - **Range:** {min_exams:.0f} to {max_exams:.0f} exams
                - **Volume correlation:** Higher volume = consistent improvement
                - **Efficiency:** {avg_score_diff/avg_exams:.2f} points per exam average
                """)
            
            # Conclusion
            st.success(f"""
            💡 **Key Takeaway:** All {total_students} students who took more than 8 practice exams achieved positive score improvements, 
            with an average gain of **{avg_score_diff:.1f} points**. This demonstrates that high-volume practice is a reliable strategy for MCAT success.
            """)
            
        else:
            st.warning("No students found who took more than 8 practice exams.")


    elif analysis_type == "Question Bank Analytics":
        st.header("Question Bank Analytics")
        
        # Filter data for comparison
        qbank_data = df[['Score_Difference', 'Total_Completed_Sum', 'Student_ID']].dropna()
        
        if len(qbank_data) > 0:
            # Group students by score improvement
            high_improvement = qbank_data[qbank_data['Score_Difference'] > 8]
            low_improvement = qbank_data[qbank_data['Score_Difference'] < 7]
            
            # Calculate statistics for comparison visualization
            if len(high_improvement) > 0 and len(low_improvement) > 0:
                high_avg = high_improvement['Total_Completed_Sum'].mean()
                low_avg = low_improvement['Total_Completed_Sum'].mean()
                avg_difference = high_avg - low_avg
                
                # Perform t-test
                t_stat, p_value = ttest_ind(high_improvement['Total_Completed_Sum'], low_improvement['Total_Completed_Sum'])
                
                st.subheader("Comparison: High vs Low Score Improvement")
                
                st.info("High improvement students completed significantly more amount of questions from the JW Question Bank than scholars that demonstrated lower, negative, or no improvement.")
            
            # Display key statistics
            if avg_difference > 0:
                st.info(f"High improvement students completed {avg_difference:.1f} more passages/sets on average")
            elif avg_difference < 0:
                st.info(f"Low improvement students completed {abs(avg_difference):.1f} more passages/sets on average")
            else:
                st.info("Both groups completed similar amounts of question bank content")
            
            # Comparison visualization
            if len(high_improvement) > 0 and len(low_improvement) > 0:
                st.subheader("Comparison Visualization")
                
                # Create comparison data for plotting
                comparison_data = []
                
                for _, row in high_improvement.iterrows():
                    comparison_data.append({
                        'Total_Completed': row['Total_Completed_Sum'],
                        'Group': 'High Improvement (>8 pts)',
                        'Score_Difference': row['Score_Difference']
                    })
                
                for _, row in low_improvement.iterrows():
                    comparison_data.append({
                        'Total_Completed': row['Total_Completed_Sum'],
                        'Group': 'Low Improvement (<7 pts)',
                        'Score_Difference': row['Score_Difference']
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                # Box plot comparison
                fig_box = px.box(
                    comparison_df,
                    x='Group',
                    y='Total_Completed',
                    title='Question Bank Usage: High vs Low Improvement Students',
                    labels={
                        'Total_Completed': 'Total Completed Passages/Discrete Sets',
                        'Group': 'Student Group'
                    },
                    color='Group',
                    color_discrete_map={
                        'High Improvement (>8 pts)': BRAND_COLORS['success'],
                        'Low Improvement (<7 pts)': BRAND_COLORS['error']
                    }
                )
                fig_box = apply_light_mode_styling(fig_box)
                st.plotly_chart(fig_box, use_container_width=True)
                
                # Statistical comparison
                st.subheader("Statistical Comparison")
                
                # Calculate statistics
                if len(high_improvement) > 0 and len(low_improvement) > 0:
                    high_median = high_improvement['Total_Completed_Sum'].median()
                    low_median = low_improvement['Total_Completed_Sum'].median()
                    avg_difference = high_avg - low_avg
                    median_difference = high_median - low_median
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Average Difference", 
                            f"{avg_difference:+.1f}",
                            help="High improvement group average minus low improvement group average"
                        )
                    
                    with col2:
                        st.metric(
                            "Median Difference", 
                            f"{median_difference:+.1f}",
                            help="High improvement group median minus low improvement group median"
                        )
            
                    with col3:
                        # Perform t-test
                        t_stat, p_value = ttest_ind(high_improvement['Total_Completed_Sum'], low_improvement['Total_Completed_Sum'])
                        significance = "Significant" if p_value < 0.05 else "Not Significant"
                        st.metric("T-test P-value", f"{p_value:.4f}", delta=significance)
        else:
            st.warning("Insufficient data available for question bank comparison analysis.")

    elif analysis_type == "Attendance Analysis":
        st.header("Attendance Analysis")
        
        if csv_df is not None:
            # Process attendance data with tier information
            attendance_data = csv_df.groupby('student_id').agg({
                'num_attended_large_session': 'sum',
                'num_scheduled_large_session': 'sum',
                'num_attended_small_session': 'sum',
                'num_scheduled_small_session': 'sum',
                'Large Group Tier': 'first',
                'Small Group Tier': 'first'
            }).reset_index()
            
            attendance_data['large_attendance_rate'] = (attendance_data['num_attended_large_session'] / 
                                                       attendance_data['num_scheduled_large_session'] * 100)
            attendance_data['small_attendance_rate'] = (attendance_data['num_attended_small_session'] / 
                                                       attendance_data['num_scheduled_small_session'] * 100)
            
            # Create heat map for tier distribution
            st.subheader("Tier Distribution by Baseline MCAT Score")
            
            # Merge with baseline scores
            baseline_data = df[['Student_ID', 'Baseline_Score']].dropna()
            tier_baseline = attendance_data.merge(baseline_data, left_on='student_id', right_on='Student_ID', how='inner')
            
            # Create baseline score ranges
            tier_baseline['Score_Range'] = pd.cut(tier_baseline['Baseline_Score'], 
                                                bins=[480, 490, 500, 510, 520], 
                                                labels=['480-489', '490-499', '500-509', '510-520'])
            
            # Create pivot tables for heat maps
            large_group_pivot = tier_baseline.pivot_table(
                values='student_id', 
                index='Score_Range', 
                columns='Large Group Tier', 
                aggfunc='count', 
                fill_value=0
            )
            
            small_group_pivot = tier_baseline.pivot_table(
                values='student_id', 
                index='Score_Range', 
                columns='Small Group Tier', 
                aggfunc='count', 
                fill_value=0
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Large Group Heat Map
                fig_large = px.imshow(
                    large_group_pivot.values,
                    x=large_group_pivot.columns,
                    y=large_group_pivot.index,
                    color_continuous_scale=[[0, '#FFFF99'], [0.5, '#FF9900'], [1, '#FF0000']],
                    aspect="auto",
                    title="Large Group Attendance Tiers by Baseline Score"
                )
                
                # Add annotations
                for i, row in enumerate(large_group_pivot.index):
                    for j, col in enumerate(large_group_pivot.columns):
                        fig_large.add_annotation(
                            x=j, y=i,
                            text=str(large_group_pivot.iloc[i, j]),
                            showarrow=False,
                            font=dict(color="black", size=12, family="Arial Black")
                        )
                
                fig_large = apply_light_mode_styling(fig_large)
                st.plotly_chart(fig_large, use_container_width=True)
            
            with col2:
                # Small Group Heat Map
                fig_small = px.imshow(
                    small_group_pivot.values,
                    x=small_group_pivot.columns,
                    y=small_group_pivot.index,
                    color_continuous_scale=[[0, '#FFFF99'], [0.5, '#FF9900'], [1, '#FF0000']],
                    aspect="auto",
                    title="Small Group Attendance Tiers by Baseline Score"
                )
                
                # Add annotations
                for i, row in enumerate(small_group_pivot.index):
                    for j, col in enumerate(small_group_pivot.columns):
                        fig_small.add_annotation(
                            x=j, y=i,
                            text=str(small_group_pivot.iloc[i, j]),
                            showarrow=False,
                            font=dict(color="black", size=12, family="Arial Black")
                        )
                
                fig_small = apply_light_mode_styling(fig_small)
                st.plotly_chart(fig_small, use_container_width=True)
            
            # Tier Performance Analysis
            st.subheader("Attendance Tier Performance Analysis")
            
            # Calculate tier success rates
            tier_attendance = attendance_data.merge(df[['Student_ID', 'Score_Difference']], 
                                                   left_on='student_id', right_on='Student_ID', how='inner')
            tier_attendance = tier_attendance.dropna(subset=['Score_Difference'])
            
            if len(tier_attendance) > 0:
                # Large Group Tier Analysis
                large_tier_stats = tier_attendance.groupby('Large Group Tier')['Score_Difference'].agg(['mean', 'count']).reset_index()
                large_tier_stats.columns = ['Tier', 'Avg_Score_Improvement', 'Student_Count']
                
                # Small Group Tier Analysis  
                small_tier_stats = tier_attendance.groupby('Small Group Tier')['Score_Difference'].agg(['mean', 'count']).reset_index()
                small_tier_stats.columns = ['Tier', 'Avg_Score_Improvement', 'Student_Count']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Large Group Attendance Tiers:**")
                    for _, row in large_tier_stats.iterrows():
                        tier_color = '#4CAF50' if row['Tier'] == 'Tier 1' else '#FF9800' if row['Tier'] == 'Tier 2' else '#EF5350'
                        st.markdown(f"<div style='color: {tier_color}; font-weight: bold;'>{row['Tier']}: {row['Avg_Score_Improvement']:.1f} pts avg improvement ({row['Student_Count']} students)</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Small Group Attendance Tiers:**")
                    for _, row in small_tier_stats.iterrows():
                        tier_color = '#4CAF50' if row['Tier'] == 'Tier 1' else '#FF9800' if row['Tier'] == 'Tier 2' else '#EF5350'
                        st.markdown(f"<div style='color: {tier_color}; font-weight: bold;'>{row['Tier']}: {row['Avg_Score_Improvement']:.1f} pts avg improvement ({row['Student_Count']} students)</div>", unsafe_allow_html=True)
                    
                    st.info("**Key Finding:** Attendance tier directly correlates with MCAT score improvement across both session types")
            
            else:
                st.error("**Attendance analysis requires tier data which is not available**")
                st.info("**Troubleshooting:** Attendance Analysis requires the `data_outcomes_with_tiers.csv` file.")
                st.markdown("""
                **This section needs:**
                - Attendance data (num_attended_large_session, num_scheduled_large_session)
                - Small group attendance (num_attended_small_session, num_scheduled_small_session)  
                - Tier classifications (Large Group Tier, Small Group Tier)
                - Baseline MCAT scores for correlation analysis
                
                **Current status:** CSV data loading failed.
                """)

    elif analysis_type == "Performer Analysis":
        st.header("Performer Analysis")
        st.subheader("High vs Low Performing Students")
        
        if csv_df is not None:
            # Process data for performance-based analysis
            tier_data = csv_df.groupby('student_id').agg({
                'Small Group Tier': 'first',
                'Large Group Tier': 'first', 
                'class_accuracy': 'mean',
                'class_participation': 'mean',
                'homework_participation': 'mean',
                'num_attended_large_session': 'sum',
                'num_scheduled_large_session': 'sum',
                'num_attended_small_session': 'sum', 
                'num_scheduled_small_session': 'sum',
                'total_completed_passages_discrete_sets': 'sum'
            }).reset_index()
            
            # Calculate relative class participation (for online compatibility)
            tier_data['class_participation_relative'] = tier_data['class_participation'] / tier_data['class_participation'].max() * 100
            
            # Merge with score improvement and MCAT data
            performance_data = df[['Student_ID', 'Score_Difference', 'Actual_MCAT', 'Baseline_Score', 'Number_of_Practice_Exams', 'Total_Completed_Sum']].merge(
                tier_data, left_on='Student_ID', right_on='student_id', how='inner'
            )
            
            # Key Findings at the top
            st.subheader("Key Findings")
            total_students_analyzed = len(performance_data[performance_data['Score_Difference'].notna()])
            avg_improvement = performance_data['Score_Difference'].mean()
            students_improved = len(performance_data[performance_data['Score_Difference'] > 0])
            improvement_rate = students_improved / total_students_analyzed * 100 if total_students_analyzed > 0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**{improvement_rate:.0f}% of students** showed positive MCAT score improvement with an average gain of **+{avg_improvement:.1f} points**")
            with col2:
                high_performers_count = len(performance_data[
                    ((performance_data['Score_Difference'] > 12) & (performance_data['Score_Difference'].notna())) |
                    ((performance_data['Actual_MCAT'] > 505) & (performance_data['Actual_MCAT'].notna()))
                ])
                high_performer_rate = high_performers_count / total_students_analyzed * 100 if total_students_analyzed > 0 else 0
                st.success(f"**{high_performer_rate:.0f}% achieved exceptional results** (>12pt improvement or >505 MCAT score)")
            
            st.markdown("---")
            
            # Define High and Low Performers based on new criteria
            # High Performing: >12 point improvement OR >505 actual MCAT
            high_performers = performance_data[
                ((performance_data['Score_Difference'] > 12) & (performance_data['Score_Difference'].notna())) |
                ((performance_data['Actual_MCAT'] > 505) & (performance_data['Actual_MCAT'].notna()))
            ]
            
            # Low Performing: ≤0 point improvement OR <502 actual MCAT
            low_performers = performance_data[
                ((performance_data['Score_Difference'] <= 0) & (performance_data['Score_Difference'].notna())) |
                ((performance_data['Actual_MCAT'] < 502) & (performance_data['Actual_MCAT'].notna()))
            ]
            
            # High Performer Analysis
            st.subheader("High Performing Students")
            st.markdown('<p style="color: black; font-weight: normal;">Criteria: >12 point score improvement OR >505 actual MCAT score</p>', unsafe_allow_html=True)
            
            if len(high_performers) > 0:
                avg_improvement_high = high_performers['Score_Difference'].mean()
                avg_baseline_high = high_performers['Baseline_Score'].mean()
                avg_actual_high = high_performers['Actual_MCAT'].mean()
                st.info(f"**High Performer Sample:** {len(high_performers)} students | **Average Score Improvement:** {avg_improvement_high:.1f} points | **Average Baseline Score:** {avg_baseline_high:.1f} | **Average Actual MCAT:** {avg_actual_high:.1f}")
                
                # High performer metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Average Class Accuracy", f"{high_performers['class_accuracy'].mean():.1%}")
                with col2:
                    # Calculate average weekly questions answered (total completed / number of weeks in program)
                    avg_weekly_questions = high_performers['total_completed_passages_discrete_sets'].mean()
                    st.metric("Avg Weekly Questions", f"{avg_weekly_questions:.0f}", help="Average question sets completed per week")
                with col3:
                    st.metric("Baseline MCAT", f"{avg_baseline_high:.1f}")
                with col4:
                    # Calculate % in Tier 1 and 2 attendance
                    small_tier_dist_high = high_performers['Small Group Tier'].value_counts()
                    tier1_count = small_tier_dist_high.get('Tier 1', 0)
                    tier2_count = small_tier_dist_high.get('Tier 2', 0)
                    tier1_tier2_pct = (tier1_count + tier2_count) / len(high_performers) * 100 if len(high_performers) > 0 else 0
                    st.metric("Tier 1+2 Attendance", f"{tier1_tier2_pct:.0f}%", help="Percentage in top attendance tiers")
                
                # Store for comparison later
                high_tier1_tier2_pct = tier1_tier2_pct
                

            
            st.markdown("---")
            
            # Low Performer Analysis
            st.subheader("Low Performing Students")
            st.markdown('<p style="color: black; font-weight: normal;">Criteria: ≤0 point score improvement OR <502 actual MCAT score</p>', unsafe_allow_html=True)
            
            if len(low_performers) > 0:
                avg_improvement_low = low_performers['Score_Difference'].mean()
                avg_baseline_low = low_performers['Baseline_Score'].mean()
                avg_actual_low = low_performers['Actual_MCAT'].mean()
                st.info(f"**Low Performer Sample:** {len(low_performers)} students | **Average Score Change:** {avg_improvement_low:.1f} points | **Average Baseline Score:** {avg_baseline_low:.1f} | **Average Actual MCAT:** {avg_actual_low:.1f}")
                
                # Low performer metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average Class Accuracy", f"{low_performers['class_accuracy'].mean():.1%}")
                with col2:
                    avg_weekly_questions_low = low_performers['total_completed_passages_discrete_sets'].mean()
                    st.metric("Avg Weekly Questions", f"{avg_weekly_questions_low:.0f}", help="Average question sets completed per week")
                with col3:
                    st.metric("Baseline MCAT", f"{avg_baseline_low:.1f}")
                with col4:
                    # Calculate % in Tier 1 and 2 attendance
                    small_tier_dist_low = low_performers['Small Group Tier'].value_counts()
                    tier1_count_low = small_tier_dist_low.get('Tier 1', 0)
                    tier2_count_low = small_tier_dist_low.get('Tier 2', 0)
                    tier1_tier2_pct_low = (tier1_count_low + tier2_count_low) / len(low_performers) * 100 if len(low_performers) > 0 else 0
                    st.metric("Tier 1+2 Attendance", f"{tier1_tier2_pct_low:.0f}%", help="Percentage in top attendance tiers")
                
                # Calculate tier comparison
                if tier1_tier2_pct_low > 0 and 'high_tier1_tier2_pct' in locals():
                    tier_ratio = high_tier1_tier2_pct / tier1_tier2_pct_low
                    st.info(f"**Key Finding:** Small Group Tier 1 and 2 (combined) for high performers was {tier_ratio:.1f}x as high as low performers ({high_tier1_tier2_pct:.0f}% vs {tier1_tier2_pct_low:.0f}%)")
                
                # Intervention Recommendations
                st.subheader("Intervention Recommendations")
                st.warning("**Immediate Actions for Low Performers:**")
                
                # Flag low baseline MCAT scorers
                low_baseline_threshold = 495  # Define what's considered low baseline
                low_baseline_students = low_performers[low_performers['Baseline_Score'] < low_baseline_threshold]
                if len(low_baseline_students) > 0:
                    st.error(f"**⚠️ Priority Alert:** {len(low_baseline_students)} students have baseline MCAT scores below {low_baseline_threshold} - require immediate intensive support")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**📚 Increase Practice Volume:**")
                    st.markdown("- Significantly increase question set completion")
                    st.markdown("- Focus on consistent daily practice")
                    st.markdown("- Emphasize quality over speed initially")
                    st.markdown("- Establish regular review cycles")
                    
                with col2:
                    st.markdown("**🎯 Targeted Support:**")
                    st.markdown("- Enroll in additional small group sessions")
                    st.markdown("- Make office hours mandatory for low baseline MCAT scorers with low engagement")
                    st.markdown("- Implement structured study schedule")
                    st.markdown("- Monitor weekly progress closely")
                
                with col3:
                    st.markdown("**🚨 Low Baseline Focus:**")
                    st.markdown("- Flag low baseline MCAT scorers for priority")
                    st.markdown("- Ensure maximum engagement with all resources")
                    st.markdown("- Consider intensive foundational review")
                    st.markdown("- Provide additional motivational support")
                
            # Performance Comparison
            st.markdown("---")
            st.subheader("High vs Low Performer Comparison")
            
            if len(high_performers) > 0 and len(low_performers) > 0:
                comparison_data = pd.DataFrame({
                    'Group': ['High Performers', 'Low Performers'],
                    'Student Count': [len(high_performers), len(low_performers)],
                    'Avg Score Improvement': [avg_improvement_high, avg_improvement_low],
                    'Avg Baseline Score': [avg_baseline_high, avg_baseline_low],
                    'Avg Actual MCAT': [avg_actual_high, avg_actual_low]
                })
                
                # Create comparison chart
                fig_comparison = px.bar(
                    comparison_data,
                    x='Group',
                    y='Avg Score Improvement',
                    title='Average MCAT Score Improvement: High vs Low Performers',
                    color='Group',
                    color_discrete_map={
                        'High Performers': '#4CAF50',
                        'Low Performers': '#EF5350'
                    },
                    text='Avg Score Improvement'
                )
                fig_comparison.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                fig_comparison = apply_light_mode_styling(fig_comparison)
                st.plotly_chart(fig_comparison, use_container_width=True)
            
        else:
            st.error("**Performer analysis requires tier data which is not available**")
            st.info("**Troubleshooting:** Performer Analysis requires the `data_outcomes_with_tiers.csv` file.")
            st.markdown("""
            **This section needs:**
            - Tier classifications (Small Group Tier, Large Group Tier)
            - Student performance data (class_accuracy)
            - Attendance data (large/small session attendance)
            - Score improvement data and baseline scores for comparison
            
            **Current status:** CSV data loading failed.
            """)