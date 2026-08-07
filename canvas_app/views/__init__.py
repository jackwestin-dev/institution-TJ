"""
Canvas Accuracy views. Each module exposes render() and has no import-time
Streamlit side effects, so main.py can import all three up front and call only
the one the Canvas radio selected.
"""
from . import attendance, exam_growth, quiz_reports

# Radio label → render function. main.py builds its radio from these keys, so
# adding a view here is enough to surface it.
VIEWS = {
    "Quiz Reports":    quiz_reports.render,
    "Exam Growth":     exam_growth.render,
    "Nova Attendance": attendance.render,
}

__all__ = ["VIEWS", "attendance", "exam_growth", "quiz_reports"]
