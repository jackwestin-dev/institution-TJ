"""
Canvas Accuracy views.

Two groups, because they have different audiences:

  PRESENTATION — open with no credentials and nothing to type, reading the
  committed de-identified bundle in data/. These are what gets shown to school
  administration.

  ADMIN — talk to Canvas and Nova live and need a token or session cookies.
  Hidden behind the sidebar's "Staff tools" toggle so they never appear in a
  presentation, and surfaced only on request.

Each module exposes render() and has no import-time Streamlit side effects.
"""
from . import attendance, course_performance, exam_growth, quiz_reports

PRESENTATION_VIEWS = {
    "Exam Growth":        exam_growth.render,
    "Course Performance": course_performance.render,
    "Attendance":         attendance.render,
}

ADMIN_VIEWS = {
    "Canvas Explorer (live)": quiz_reports.render,
}

# Back-compat for anything still importing the old flat mapping.
VIEWS = {**PRESENTATION_VIEWS, **ADMIN_VIEWS}

__all__ = [
    "PRESENTATION_VIEWS", "ADMIN_VIEWS", "VIEWS",
    "attendance", "course_performance", "exam_growth", "quiz_reports",
]
