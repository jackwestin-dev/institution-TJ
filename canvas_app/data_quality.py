"""
Screening rules applied when the published data bundle is built.

Canvas reports a non-attempt and a genuinely wrong answer identically: both come
back as a score of 0. Left alone, those zeros are read as poor performance, and
they distort two things at once — they drag the cohort average down, and they
widen the spread so the assignment looks harder than it was.

Two rules, applied at build time so the committed data never carries them. Both
target assignments that were never graded at all — not students who scored badly.

  1. A **homework** where every submitted score is 0 was never graded. Course
     345 has two — a study-skills homework and a coaching-session homework,
     both marked for completion in Canvas. They are dropped whole, since a
     homework nobody was scored on says nothing about anything.

  2. Any **other** assignment where every score is 0 keeps its submissions but
     loses its scores. Six fall here: four participation tasks and two survey
     forms. Dropping them outright would delete a genuine record of who turned
     up, so only the fictitious 0% accuracy goes. This is also what stopped
     surveys reporting an average score of 5%.

Both rules report what they removed rather than applying silently, because what
was taken out changes how the remaining numbers should be read.

Deliberately NOT a rule: dropping individual zero rows from a homework that has
several. That was tried and removed. It rested on reading two zeros among ninety
students as "blank submissions", which a normal low tail also produces, and it
cost more than it bought — 12 real scores deleted, one assignment's average
moved 5.7 points, and the local report cache left disagreeing with the published
bundle because only one of them had been screened. A student who scored zero is
exactly the student this dashboard exists to surface, so an unscored zero stays
visible unless the whole assignment proves ungraded.
"""

# Limited to homework: participation tasks are marked for taking part, so a zero
# there means something different in kind and rule 2 handles them instead.
GRADED_TYPES = ("Homework",)


def screen(item_type: str, pct_by_key: dict) -> "tuple[bool, set, bool, str]":
    """
    Decide what to keep for one assignment.

    Returns (keep_assignment, keys_to_drop, blank_scores, reason):
      keep_assignment  False drops the assignment and all its rows
      keys_to_drop     students whose individual rows should be omitted; always
                       empty now that per-student screening has been removed,
                       kept so callers need no change if it ever returns
      blank_scores     keep the submissions, discard the scores
      reason           why, for the build log
    """
    scored = {key: value for key, value in pct_by_key.items() if value is not None}
    if not scored:
        return True, set(), False, ""

    if all(value == 0 for value in scored.values()):
        why = f"every one of {len(scored)} scores is 0 — never graded"
        if item_type in GRADED_TYPES:
            return False, set(), False, why
        return True, set(), True, why + "; submissions kept, scores cleared"

    return True, set(), False, ""
