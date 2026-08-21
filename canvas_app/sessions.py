"""Teaching sessions inside a single Canvas course.

Course 345 did not stop and restart in Canvas — the Fall curriculum was added to
the same course shell on 2026-08-10, starting at assignment 1225. Averaging
across the join mixes two separate stretches of teaching, and plotting it as one
continuous line implies a trend between them that does not exist.

Sessions are matched on assignment due date, so both the local report cache and
the published bundle in data/ can use them — they each carry due_at. Anything
earlier than the first explicit start belongs to the first session.

To add a session, append to the list for that course.
"""
import pandas as pd

from . import jw_theme as jw

SESSIONS = {
    345: [
        {"name": "Summer 2026", "start": None, "color": jw.TEAL_500},
        {"name": "Fall 2026", "start": "2026-08-10", "color": jw.VIOLET_600},
    ],
    351: [
        {"name": "EY25 Pathway", "start": None, "color": jw.AMBER_500},
    ],
}

UNDATED = "Undated"

_DEFAULT = [{"name": "All", "start": None, "color": jw.VIOLET_600}]


def sessions_for(course_id: int) -> list:
    return SESSIONS.get(int(course_id), _DEFAULT)


def has_multiple(course_id: int) -> bool:
    return len(sessions_for(course_id)) > 1


def order(course_id: int) -> list:
    return [s["name"] for s in sessions_for(course_id)]


def colors(course_id: int) -> dict:
    out = {s["name"]: s["color"] for s in sessions_for(course_id)}
    out.setdefault(UNDATED, jw.GRAY_400)
    return out


def boundaries(course_id: int) -> list:
    """[(Timestamp, name)] for every session that has an explicit start."""
    return [(pd.Timestamp(s["start"], tz="UTC"), s["name"])
            for s in sessions_for(course_id) if s["start"]]


def label(course_id: int, due) -> str:
    """Session name for one assignment due date."""
    stamp = pd.to_datetime(due, utc=True, errors="coerce")
    if pd.isna(stamp):
        return UNDATED
    name = sessions_for(course_id)[0]["name"]
    for s in sessions_for(course_id):
        if s["start"] and stamp >= pd.Timestamp(s["start"], tz="UTC"):
            name = s["name"]
    return name


def label_all(course_id: int, dues) -> pd.Series:
    dues = pd.Series(dues)
    return dues.map(lambda d: label(course_id, d))


def present(course_id: int, dues) -> list:
    """Session names actually represented in these due dates, in course order."""
    seen = set(label_all(course_id, dues))
    found = [name for name in order(course_id) if name in seen]
    if UNDATED in seen:
        found.append(UNDATED)
    return found
