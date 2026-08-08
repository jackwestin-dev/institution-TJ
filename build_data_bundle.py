#!/usr/bin/env python
"""
Build the committed, de-identified data bundle the deployed dashboard runs on.

The dashboard must open with no Canvas token, no Nova cookies and no typing —
it gets presented to school administration. That means the numbers have to be
in the repo. But this repo is public, so no student may be nameable in it.

This script is the boundary between those two facts. It reads the local,
gitignored sources (reports_cache/, exam_data/) and writes data/, replacing
every name with an opaque, stable ID:

    reports_cache/345_868.csv   "Example Student", 78.0%
    exam_data/exam2_*.csv       "Student, Example", 503
                    |
                    v
    data/assignment_scores.csv  S042, 345_868, 78.0
    data/exam_scores.csv        S042, exam2, 503

IDs are assigned once and reused forever, so a student keeps the same ID across
rebuilds and charts stay comparable between deploys. The ID -> name map is
written to data/.student_map.csv, which .gitignore excludes — a local checkout
can still show real names because it has the full cache anyway.

Nothing here is reversible from the committed files alone: without the map,
S042 is just S042.

Usage:
    python sync_reports.py          # refresh reports_cache/ (local only)
    python build_data_bundle.py     # rebuild data/ from it
    git add data/ && git commit -m "Refresh dashboard data" && git push
"""
import argparse
import csv
import io
import sys
from pathlib import Path

import pandas as pd

from canvas_app import data_quality as dq
from canvas_app import exam_scores as ex
from canvas_app import reports_cache as rc
from canvas_app.config import DATA_DIR, EXAM_DATA_DIR, has_local_cache
from canvas_app.score_parsing import parse_score_csv, submitted_students

COURSE_COHORT = {345: "EY26", 351: "EY25"}
MAP_FILE = DATA_DIR / ".student_map.csv"      # gitignored
STUDENTS = DATA_DIR / "students.csv"
ASSIGNMENTS = DATA_DIR / "assignments.csv"
SCORES = DATA_DIR / "assignment_scores.csv"
EXAMS = DATA_DIR / "exam_scores.csv"


# ── Stable pseudonyms ────────────────────────────────────────────────────────

def load_map() -> "dict[str, str]":
    """{normalised name: student_id} from the previous build, if any."""
    if not MAP_FILE.exists():
        return {}
    out = {}
    with MAP_FILE.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["name_key"]] = row["student_id"]
    return out


def save_map(mapping: "dict[str, str]", display: "dict[str, str]") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(mapping.items(), key=lambda kv: int(kv[1][1:]))
    with MAP_FILE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["student_id", "name_key", "display_name"])
        for key, sid in rows:
            writer.writerow([sid, key, display.get(key, "")])


def assign_ids(name_keys: "set[str]", existing: "dict[str, str]") -> "dict[str, str]":
    """Keep every ID already handed out; number new students after the highest."""
    mapping = dict(existing)
    used = {int(sid[1:]) for sid in mapping.values() if sid[1:].isdigit()}
    nxt = max(used) + 1 if used else 1
    for key in sorted(name_keys):           # sorted => deterministic first build
        if key not in mapping:
            mapping[key] = f"S{nxt:03d}"
            nxt += 1
    return mapping


# ── Collection ───────────────────────────────────────────────────────────────

def collect_assignments_and_scores() -> "tuple[list, list, dict, dict, list, list]":
    """
    Walk the cache once.

    Returns assignment rows, score rows, names, cohorts, and the two screening
    logs — assignments dropped whole, and assignments that lost individual rows.
    """
    assignment_rows, score_rows = [], []
    display: "dict[str, str]" = {}
    cohort: "dict[str, str]" = {}
    dropped_assignments: "list[str]" = []
    dropped_rows: "list[str]" = []

    for course_id, cohort_name in COURSE_COHORT.items():
        for item in rc.cached_for_course(course_id):
            aid = item["assignment_id"]
            raw = rc.get_cached_csv(course_id, aid)
            if not raw:
                continue

            title = (item.get("title") or str(aid)).strip()
            names = submitted_students(io.BytesIO(raw))
            if not names:
                continue

            score_df, pts = parse_score_csv(io.BytesIO(raw))
            pct_by_key: "dict[str, float]" = {}
            if score_df is not None and pts:
                for _, row in score_df.iterrows():
                    key = ex.normalize_name(row["student"])
                    if not key:
                        continue
                    pct = round(row["score"] / pts * 100, 1)
                    if pct > pct_by_key.get(key, -1):   # retake: keep the better
                        pct_by_key[key] = pct

            item_type = ex.classify_item(title)

            # Canvas can't distinguish "answered nothing" from "answered wrong" —
            # both export as 0. See canvas_app.data_quality for what that costs
            # and which zeros are removed here.
            keep, drop_keys, blank_scores, reason = dq.screen(item_type, pct_by_key)
            if not keep:
                dropped_assignments.append(f"{course_id}_{aid} {title[:44]} — {reason}")
                continue
            if blank_scores:
                # Ungraded but genuinely submitted — a participation task or
                # survey Canvas never scored. Keeping the rows preserves the
                # record of who took part; clearing the scores stops a fictitious
                # 0% being averaged in as performance.
                pct_by_key = {}
                dropped_rows.append(f"{course_id}_{aid} {title[:44]} — {reason}")
            elif drop_keys:
                dropped_rows.append(f"{course_id}_{aid} {title[:44]} — {reason}")

            kept_names = [n for n in names if ex.normalize_name(n) not in drop_keys]

            assignment_rows.append({
                "course_id":     course_id,
                "assignment_id": aid,
                "title":         title,
                "item_type":     item_type,
                "topic":         ex.topic_of(title),
                "due_at":        item.get("due_at") or "",
                "n_submitted":   len(kept_names),
            })

            for name in kept_names:
                key = ex.normalize_name(name)
                if not key:
                    continue
                display.setdefault(key, ex.display_name(name))
                cohort.setdefault(key, cohort_name)
                score_rows.append({
                    "_key":          key,
                    "course_id":     course_id,
                    "assignment_id": aid,
                    "score_pct":     pct_by_key.get(key),
                })

    return assignment_rows, score_rows, display, cohort, dropped_assignments, dropped_rows


def collect_exams() -> "tuple[list, dict]":
    """Extract both MCAT exams from exam_data/, newest-looking file per exam."""
    rows, display = [], {}
    if not EXAM_DATA_DIR.exists():
        return rows, display

    files = sorted(p for p in EXAM_DATA_DIR.iterdir()
                   if p.suffix.lower() in (".csv", ".xlsx", ".xls"))
    for label, needle in (("exam1", "exam1"), ("exam2", "exam2")):
        match = next((p for p in files if needle in p.name.lower()), None)
        if match is None:
            print(f"  ! no file matching {needle!r} in {EXAM_DATA_DIR.name}/")
            continue
        df = (pd.read_excel(match) if match.suffix.lower() in (".xlsx", ".xls")
              else pd.read_csv(match))
        mapping = ex.describe_source(df)
        if not mapping["name_col"]:
            print(f"  ! {match.name}: no name column detected, skipped")
            continue
        extracted = ex.extract_scores(
            df, mapping["name_col"], mapping["total_col"], mapping["section_cols"])
        # Screenshot-only responses, typed in by hand — see exam_scores.manual_scores.
        before = int(extracted["total"].notna().sum())
        extracted = ex.with_manual(extracted, label)
        added = int(extracted["total"].notna().sum()) - before
        if added:
            print(f"    +{added} hand-entered score(s) from {ex.MANUAL_FILE}")
        kept = 0
        for _, row in extracted.iterrows():
            if row["key"] and pd.notna(row["total"]):
                display.setdefault(row["key"], row["student"])
                rows.append({
                    "_key":  row["key"],
                    "exam":  label,
                    "total": float(row["total"]),
                    **{s: (float(row[s]) if pd.notna(row[s]) else None) for s in ex.SECTIONS},
                })
                kept += 1
        print(f"  {match.name} -> {kept} usable score(s) as {label}")
    return rows, display


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Build the de-identified data bundle.")
    ap.add_argument("--dry-run", action="store_true", help="Report, write nothing.")
    args = ap.parse_args()

    if not has_local_cache():
        print("ERROR: reports_cache/ is empty. Run `python sync_reports.py` first.",
              file=sys.stderr)
        return 2

    print("Reading report cache…")
    (assignment_rows, score_rows, display, cohort,
     dropped_assignments, dropped_rows) = collect_assignments_and_scores()
    print(f"  {len(assignment_rows)} assignments, {len(score_rows)} submission rows")

    if dropped_assignments:
        print(f"  dropped {len(dropped_assignments)} ungraded assignment(s):")
        for line in dropped_assignments:
            print(f"    {line}")
    if dropped_rows:
        print(f"  screened zero rows on {len(dropped_rows)} homework(s):")
        for line in dropped_rows:
            print(f"    {line}")

    print("Reading exam data…")
    exam_rows, exam_display = collect_exams()
    display = {**exam_display, **display}     # cache spelling wins; it is canonical

    all_keys = {r["_key"] for r in score_rows} | {r["_key"] for r in exam_rows}
    mapping = assign_ids(all_keys, load_map())
    reused = len(load_map())
    print(f"  {len(all_keys)} distinct students ({reused} keeping an existing ID, "
          f"{len(all_keys) - reused} newly assigned)")

    if args.dry_run:
        print("(dry run — nothing written)")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        sorted(({"student_id": mapping[k], "cohort": cohort.get(k, "")} for k in all_keys),
               key=lambda r: r["student_id"])
    ).to_csv(STUDENTS, index=False)

    pd.DataFrame(assignment_rows).sort_values(
        ["course_id", "due_at", "title"]
    ).to_csv(ASSIGNMENTS, index=False)

    scores = pd.DataFrame(score_rows)
    scores["student_id"] = scores["_key"].map(mapping)
    scores.drop(columns=["_key"]).sort_values(
        ["course_id", "assignment_id", "student_id"]
    ).to_csv(SCORES, index=False)

    if exam_rows:
        exams = pd.DataFrame(exam_rows)
        exams["student_id"] = exams["_key"].map(mapping)
        exams.drop(columns=["_key"]).sort_values(
            ["exam", "student_id"]
        ).to_csv(EXAMS, index=False)

    save_map(mapping, display)

    # ── Refuse to ship anything nameable ──────────────────────────────────────
    leaked = []
    names = {n.lower() for n in display.values() if len(n) > 3}
    for path in (STUDENTS, ASSIGNMENTS, SCORES, EXAMS):
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8").lower()
        hits = [n for n in names if n in body]
        if hits:
            leaked.append((path.name, hits[:3]))
    if leaked:
        print("\nABORT: a student name reached a committed file:", file=sys.stderr)
        for name, hits in leaked:
            print(f"  {name}: {hits}", file=sys.stderr)
        return 1

    print(f"\nWrote to {DATA_DIR.name}/ (no names — verified):")
    for path in (STUDENTS, ASSIGNMENTS, SCORES, EXAMS):
        if path.exists():
            print(f"  {path.name:24s} {len(path.read_text(encoding='utf-8').splitlines()) - 1:6d} rows")
    print(f"  {MAP_FILE.name:24s} {len(mapping):6d} rows  (gitignored, local only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
