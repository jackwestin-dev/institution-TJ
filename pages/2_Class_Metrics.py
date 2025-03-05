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
df_engagement_attendance.rename(
    columns={
        'total_completed_passages_discrete_sets': 'completed_question_sets'
    },
    inplace=True
)
df_engagement_attendance['attendance'] = df_engagement_attendance['num_attended_large_session'] / df_engagement_attendance['num_scheduled_large_session']

df_tier_data = pd.read_csv('./student-data/tierdata.csv')

# Add these lines here - right before creating the weekly aggregation
# Create a lookup for date ranges by week
week_dates = df_engagement_attendance.groupby('week')[['start_date', 'end_date']].first().reset_index()
# Convert to a dictionary for easy lookup
week_to_dates = {row['week']: (row['start_date'], row['end_date']) for _, row in week_dates.iterrows()}

## Performance Class Average - Data Prep
df_engagement_attendance_weekly = df_engagement_attendance.groupby(['week']).agg(
    {
        'start_date': 'first',  # Get the first start_date for each week
        'end_date': 'first',    # Get the first end_date for each week
        'cars_accuracy':'mean',
        'sciences_accuracy':'mean',
        'class_accuracy':'mean',
        'attendance':'mean',
        'completed_lessons':'mean',
        'completed_question_sets':'mean',
        'homework_participation':'mean',
        'class_participation':'mean'
    }
)
# Now add the date columns back to the aggregated dataframe
df_engagement_attendance_weekly = df_engagement_attendance_weekly.reset_index()
df_engagement_attendance_weekly['start_date'] = df_engagement_attendance_weekly['week'].map(lambda w: week_to_dates.get(w, (None, None))[0])
df_engagement_attendance_weekly['end_date'] = df_engagement_attendance_weekly['week'].map(lambda w: week_to_dates.get(w, (None, None))[1])
df_engagement_attendance_weekly = df_engagement_attendance_weekly.set_index('week')

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

## Tier - Data Prep
assessment_categories = ['Survey Tier', 'Large Group Tier', 'Small Group Tier', 'Class Participation Tier', 'Final Tier']
tier_values = ['Tier 1', 'Tier 2', 'Tier 3']
df_tier_percentages = pd.DataFrame(index=assessment_categories, columns=tier_values)
total_students = len(df_tier_data)

for category in assessment_categories:
    # Count occurrences of each tier in this category
    tier_counts = df_tier_data[category].value_counts()
    
    # Calculate percentages
    for tier in tier_values:
        if tier in tier_counts:
            percentage = (tier_counts[tier] / total_students)
            df_tier_percentages.loc[category, tier] = round(percentage, 2)
        else:
            df_tier_percentages.loc[category, tier] = 0.0

# Fill any NaN values with 0
df_tier_percentages = df_tier_percentages.fillna(0.0)

# Add a descriptive column name for the assessment categories
df_tier_percentages.index.name = 'Assessment Category'

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
    df_engagement_attendance_weekly[['cars_accuracy','sciences_accuracy']].sort_values(by='week',ascending=False).style.format(
    {
        'start_date': lambda x: x.strftime('%m/%d/%y'),
        'end_date': lambda x: x.strftime('%m/%d/%y'),
        'cars_accuracy' : '{:.1%}',
        'sciences_accuracy' : '{:.1%}',
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
st.write('Participation includes the % of students who completed the activities provided in class. This typically comes as a completed question set that instructors assign during the class. Here is an [participation activity example](https://www.loom.com/share/48b383838811401892a38e17761c4993?sid=a0215f6f-0d3f-4abb-b0c8-75e1836075e1) here.')
st.write(' ')
st.dataframe(
    df_engagement_attendance_weekly[['class_participation']].sort_values(by='week',ascending=False).style.format(
    {
        'class_participation' : '{:.1%}',
    }
),
use_container_width=True
)
st.write(' ')
st.write(' ')
st.header('Engagement')
st.write(' ')
st.write(' ')
st.dataframe(df_engagement_attendance_weekly[['completed_lessons','completed_question_sets']].sort_values(by='week',ascending=False).style.format(
    {
        'completed_lessons' : '{:,.1f}',
        'completed_question_sets' : '{:,.1f}',
    }
),
use_container_width=True
)
st.write(' ')
st.write(' ')
st.header('Class Tier Data')
st.write('Listed below is the class breakdown of the percentage of students that fall into different tiers for each assessment category.')
st.write(' ')
st.write(' ')
st.dataframe(
    df_tier_percentages.style.format(
    {
        'Tier 1' : '{:.1%}',
        'Tier 2' : '{:.1%}',
        'Tier 3' : '{:.1%}'
    }
), 
use_container_width=True
)
