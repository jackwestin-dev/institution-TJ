import pandas as pd
import streamlit as st
from datetime import datetime, date
import hmac
import altair as alt

st.set_page_config(page_title='Institution TJ Student Dashboard',layout='wide')

st.title('Institution TJ - Student Dashboard')

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

## Read data from CSV files
df_engagement_attendance = pd.read_csv('./student-data/institution-1-engagement-data.csv',parse_dates=['start_date','end_date'])
df_engagement_attendance['attendance'] = df_engagement_attendance['num_attended_large_session'] / df_engagement_attendance['num_scheduled_large_session']

## Performance Class Average - Data Prep
df_engagement_attendance_weekly = df_engagement_attendance.groupby(['week']).agg(
    {
        'cars_accuracy':'mean',
        'sciences_accuracy':'mean',
        'class_accuracy':'mean',
        'attendance':'mean',
        'homework_participation':'mean',
        'class_participation':'mean'
    }
)

week_total = df_engagement_attendance_weekly.reset_index()['week'].max()
sciences_accuracy_latest_week = df_engagement_attendance_weekly.loc[week_total]['sciences_accuracy']
sciences_accuracy_first_week = df_engagement_attendance_weekly.loc[1]['sciences_accuracy']
sciences_accuracy_magnitude_change = sciences_accuracy_latest_week - sciences_accuracy_first_week


if sciences_accuracy_magnitude_change > 0:
    sciences_accuracy_directional_change = 'increased'
else:
    sciences_accuracy_directional_change = 'decreased'

cars_accuracy_latest_week = df_engagement_attendance_weekly.loc[week_total]['cars_accuracy']
cars_accuracy_first_week = df_engagement_attendance_weekly.loc[1]['cars_accuracy']
cars_accuracy_magnitude_change = cars_accuracy_latest_week - cars_accuracy_first_week

if cars_accuracy_magnitude_change > 0:
    cars_accuracy_directional_change = 'increased'
else:
    cars_accuracy_directional_change = 'decreased'
    
class_accuracy_weekly_min = df_engagement_attendance_weekly['class_accuracy'].min()
class_accuracy_weekly_max = df_engagement_attendance_weekly['class_accuracy'].max()

## Engagement - Attendance - Data Prep
attendance_weekly_min = df_engagement_attendance_weekly['attendance'].min()
attendance_weekly_max = df_engagement_attendance_weekly['attendance'].max()

## Engagement - Participation - Data Prep
class_participation_latest_week = df_engagement_attendance_weekly.loc[week_total]['class_participation']
class_participation_first_week = df_engagement_attendance_weekly.loc[1]['class_participation']
class_participation_magnitude_change = class_participation_latest_week - class_participation_first_week

if class_participation_magnitude_change > 0:
    class_participation_directional_change = 'increased'
else:
    class_participation_directional_change = 'decreased'
    
homework_participation_latest_week = df_engagement_attendance_weekly.loc[week_total]['homework_participation']
homewrok_participation_first_week = df_engagement_attendance_weekly.loc[1]['homework_participation']
homework_participation_magnitude_change = homework_participation_latest_week - homewrok_participation_first_week

if homework_participation_magnitude_change > 0:
    homework_participation_directional_change = 'increased'
else:
    homework_participation_directional_change = 'decreased'

## Tier Data Analysis
# Count students in each tier category
survey_tier_counts = df_tier_data['Survey Tier'].value_counts()
large_group_tier_counts = df_tier_data['Large Group Tier'].value_counts()
small_group_tier_counts = df_tier_data['Small Group Tier'].value_counts()
class_participation_tier_counts = df_tier_data['Class Participation Tier'].value_counts()
final_tier_counts = df_tier_data['Final Tier'].value_counts()

# Calculate percentages
total_students = len(df_tier_data)
tier_percentages = pd.DataFrame({
    'Tier 1': [
        survey_tier_counts.get('Tier 1', 0) / total_students * 100,
        large_group_tier_counts.get('Tier 1', 0) / total_students * 100,
        small_group_tier_counts.get('Tier 1', 0) / total_students * 100,
        class_participation_tier_counts.get('Tier 1', 0) / total_students * 100,
        final_tier_counts.get('Tier 1', 0) / total_students * 100
    ],
    'Tier 2': [
        survey_tier_counts.get('Tier 2', 0) / total_students * 100,
        large_group_tier_counts.get('Tier 2', 0) / total_students * 100,
        small_group_tier_counts.get('Tier 2', 0) / total_students * 100,
        class_participation_tier_counts.get('Tier 2', 0) / total_students * 100,
        final_tier_counts.get('Tier 2', 0) / total_students * 100
    ],
    'Tier 3': [
        survey_tier_counts.get('Tier 3', 0) / total_students * 100,
        large_group_tier_counts.get('Tier 3', 0) / total_students * 100,
        small_group_tier_counts.get('Tier 3', 0) / total_students * 100,
        class_participation_tier_counts.get('Tier 3', 0) / total_students * 100,
        final_tier_counts.get('Tier 3', 0) / total_students * 100
    ]
}, index=['Survey Tier', 'Large Group Tier', 'Small Group Tier', 'Class Participation Tier', 'Final Tier'])


## Create sections and render dashboard
st.write(' ')
st.write(' ')
st.header('Performance Class Average')
st.write(
    f'''
    Over the course of {week_total} weeks:
    * The scholar's accuracy rates on their science questions (passage or discrete questions) {sciences_accuracy_directional_change} by {sciences_accuracy_magnitude_change:.0%} from {sciences_accuracy_first_week:.0%} to {sciences_accuracy_latest_week:.0%}.
    * The scholar's accuracy rates on their CARS passages {cars_accuracy_directional_change} by {cars_accuracy_magnitude_change:.0%} from  {cars_accuracy_first_week:.0%} to {cars_accuracy_latest_week:.0%}.
    * Class accuracy averages on question sets completed in class fluctuated week to week, with a range of {class_accuracy_weekly_min:.0%} - {class_accuracy_weekly_max:.0%}.
    '''
)
st.write(' ')
st.write(' ')
st.dataframe(
    df_engagement_attendance_weekly[['cars_accuracy','sciences_accuracy','class_accuracy']].sort_values(by='week',ascending=False).style.format(
    {
        'cars_accuracy' : '{:.1%}',
        'sciences_accuracy' : '{:.1%}',
        'class_accuracy' : '{:.1%}'
    }
),
use_container_width=True
)

st.write(' ')
st.write(' ')
st.header('Student Tier Distribution')
st.write('Percentage of students in each performance tier:')
st.write(' ')

# Create a styled dataframe
styled_tier_percentages = tier_percentages.style.format("{:.1f}%").background_gradient(
    cmap='RdYlGn_r',  # Red for high numbers (tier 4), green for low numbers (tier 1)
    axis=1
)

st.dataframe(styled_tier_percentages, use_container_width=True)

# Add a visualization of overall tier distribution
st.subheader('Overall Tier Distribution')
tier_data_melted = pd.melt(
    tier_percentages.reset_index(), 
    id_vars='index', 
    var_name='Tier', 
    value_name='Percentage'
)

tier_chart = alt.Chart(tier_data_melted).mark_bar().encode(
    x=alt.X('index:N', title='Assessment Category'),
    y=alt.Y('Percentage:Q', title='Percentage of Students'),
    color=alt.Color('Tier:N', 
        scale=alt.Scale(
            domain=['Tier 1', 'Tier 2', 'Tier 3', 'Tier 4'],
            range=['#1B5E20', '#66BB6A', '#FFC107', '#EF5350']
        )
    ),
    tooltip=['index', 'Tier', alt.Tooltip('Percentage:Q', format='.1f')]
).properties(
    height=300
)

st.altair_chart(tier_chart, use_container_width=True)

st.write(' ')
st.write(' ')

## Create sections and render dashboard
st.write(' ')
st.write(' ')
st.header('Performance Class Average')
st.write(
    f'''
    Over the course of {week_total} weeks:
    * The scholar’s accuracy rates on their science questions (passage or discrete questions) {sciences_accuracy_directional_change} by {sciences_accuracy_magnitude_change:.0%} from {sciences_accuracy_first_week:.0%} to {sciences_accuracy_latest_week:.0%}.
    * The scholar’s accuracy rates on their CARS passages {cars_accuracy_directional_change} by {cars_accuracy_magnitude_change:.0%} from  {cars_accuracy_first_week:.0%} to {cars_accuracy_latest_week:.0%}.
    * Class accuracy averages on question sets completed in class fluctuated week to week, with a range of {class_accuracy_weekly_min:.0%} - {class_accuracy_weekly_max:.0%}.
    '''
)
st.write(' ')
st.write(' ')
st.dataframe(
    df_engagement_attendance_weekly[['cars_accuracy','sciences_accuracy','class_accuracy']].sort_values(by='week',ascending=False).style.format(
    {
        'cars_accuracy' : '{:.1%}',
        'sciences_accuracy' : '{:.1%}',
        'class_accuracy' : '{:.1%}'
    }
),
use_container_width=True
)

st.write(' ')
st.write(' ')
st.header('Average Participation Class Data')
st.write(' ')
st.write(' ')
st.subheader('Attendance')
st.write(
    f'''
    Through {week_total} weeks of the course, the range of attendance has been between {attendance_weekly_min:.0%} and {attendance_weekly_max:.0%}.
    '''
)
st.write(' ')
st.write(' ')
st.dataframe(
    df_engagement_attendance_weekly[['attendance']].sort_values(by='week',ascending=False).style.format(
    {
        'attendance' : '{:.1%}'
    }
),
use_container_width=True
)
st.write(' ')
st.write(' ')
st.subheader('Participation')
# st.write(
#     f'''
#     Over the course of {week_total} weeks:
#     * Class participation has {class_participation_directional_change} by {class_participation_magnitude_change:.0%}, from {class_participation_first_week:.0%} to {class_participation_latest_week:.0%}.
#     * Homework participation has {homework_participation_directional_change} by {homework_participation_magnitude_change:.0%}, from {homewrok_participation_first_week:.0%} to {homework_participation_latest_week:.0%}.
#     '''
# )
st.write(' ')
st.write(' ')
st.dataframe(
    df_engagement_attendance_weekly[['class_participation','homework_participation']].style.format(
    {
        'class_participation' : '{:.1%}',
        'homework_participation' : '{:.1%}'
    }
),
use_container_width=True
)
