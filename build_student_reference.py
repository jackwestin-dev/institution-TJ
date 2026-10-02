#!/usr/bin/env python
"""
Build the local staff reference sheet: dashboard IDs -> student names.

The dashboard shows students as opaque identifiers, on purpose — the JAMP EY26
section reads the de-identified bundle in data/ and prints IDs like S042, while
the Scholar Dashboard section reads the Nova exports and prints numeric roster
IDs like 37. Neither is nameable from the committed files. That is the point of
the de-identification, and this script does not change it.

But staff reading the dashboard internally need to know who a row is about.
This writes that lookup once, from the two local sources that already hold it:

    data/.student_map.csv   S042 -> "Example Student"   (gitignored, built by
                                                         build_data_bundle.py)
    roster.csv              37   -> "Example S."        (first name + initial)

Where a roster entry resolves to exactly one full name in the map, the two IDs
are merged onto one row, so a student who appears in both sections of the
dashboard has a single line. Ambiguous or unmatched entries stay separate and
say so in `notes` rather than guessing.

Output: student_reference.csv — gitignored, same as the map it derives from.
Regenerate it after any build_data_bundle.py run that adds students.

Usage:
    python build_student_reference.py
    python build_student_reference.py --out somewhere_else.csv
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
MAP_FILE = ROOT / "data" / ".student_map.csv"
STUDENTS = ROOT / "data" / "students.csv"
ROSTER = ROOT / "roster.csv"
DEFAULT_OUT = ROOT / "student_reference.csv"

COLUMNS = [
    "name",
    "bundle_id",
    "roster_id",
    "cohort",
    "shown_in",
    "name_source",
    "notes",
]

# Where each ID namespace is visible to someone reading the dashboard. Kept
# ASCII so the sheet opens cleanly in Excel on any machine.
BUNDLE_SECTION = "JAMP EY26 > Exam Growth"
ROSTER_SECTION = "Scholar Dashboard > Individual Student Data"


def _parts(name: str) -> "list[str]":
    return [p for p in re.split(r"\s+", str(name).strip()) if p]


def _roster_key(display_name: str) -> "tuple[str, str] | None":
    """('example', 's') from "Example S." — first name plus last initial."""
    parts = _parts(display_name)
    if len(parts) < 2:
        return None
    return parts[0].lower(), parts[1][0].lower()


def _full_name_key(full_name: str) -> "tuple[str, str] | None":
    """Same key shape from a full name, so the two sides can be compared."""
    parts = _parts(full_name)
    if len(parts) < 2:
        return None
    return parts[0].lower(), parts[-1][0].lower()


def load_sources() -> "tuple[pd.DataFrame, pd.DataFrame]":
    if not MAP_FILE.exists():
        sys.exit(
            f"{MAP_FILE.relative_to(ROOT)} not found.\n"
            "It is written by build_data_bundle.py from the local reports_cache/ "
            "and exam_data/ folders. Run that first."
        )
    name_map = pd.read_csv(MAP_FILE, dtype=str).fillna("")

    if STUDENTS.exists():
        cohorts = pd.read_csv(STUDENTS, dtype=str).fillna("")
        name_map = name_map.merge(cohorts, on="student_id", how="left")
    if "cohort" not in name_map.columns:
        name_map["cohort"] = ""
    name_map["cohort"] = name_map["cohort"].fillna("")

    roster = (
        pd.read_csv(ROSTER, dtype=str).fillna("")
        if ROSTER.exists()
        else pd.DataFrame(columns=["student_id", "display_name"])
    )
    return name_map, roster


def build(name_map: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    # Index the full names by (first, last initial). A key with more than one
    # full name behind it cannot be resolved from "Example S." alone.
    by_key: "dict[tuple[str, str], list[dict]]" = {}
    for row in name_map.to_dict("records"):
        key = _full_name_key(row.get("display_name", ""))
        if key:
            by_key.setdefault(key, []).append(row)

    matched_bundle_ids: "dict[str, dict]" = {}   # bundle_id -> roster info
    roster_only: "list[dict]" = []

    for row in roster.to_dict("records"):
        rid = str(row.get("student_id", "")).strip()
        shown = str(row.get("display_name", "")).strip()
        if not rid:
            continue
        key = _roster_key(shown)
        hits = by_key.get(key, []) if key else []

        if len(hits) == 1 and hits[0]["student_id"] not in matched_bundle_ids:
            matched_bundle_ids[hits[0]["student_id"]] = {"roster_id": rid, "shown": shown}
        else:
            if not hits:
                note = ("no matching name in the bundle map — EY25-only scholar, "
                        "or spelled differently in Canvas")
            elif len(hits) > 1:
                note = f"ambiguous: {len(hits)} students match '{shown}'"
            else:
                # Its one candidate was already claimed by an earlier roster row.
                note = (f"'{shown}' also matches {hits[0]['student_id']}, already "
                        f"linked to another roster ID — check by hand")
            roster_only.append({
                "name": shown,
                "bundle_id": "",
                "roster_id": rid,
                "cohort": "",
                "shown_in": ROSTER_SECTION,
                "name_source": "roster.csv (first name + last initial only)",
                "notes": note,
            })

    rows: "list[dict]" = []
    for row in name_map.to_dict("records"):
        bid = row["student_id"]
        link = matched_bundle_ids.get(bid)
        rows.append({
            "name": row.get("display_name", ""),
            "bundle_id": bid,
            "roster_id": link["roster_id"] if link else "",
            "cohort": row.get("cohort", ""),
            "shown_in": (
                f"{BUNDLE_SECTION}; {ROSTER_SECTION}" if link else BUNDLE_SECTION
            ),
            "name_source": "data/.student_map.csv (Canvas / exam exports)",
            "notes": (
                f"roster.csv shows this student as '{link['shown']}'" if link else ""
            ),
        })

    out = pd.DataFrame(rows + roster_only, columns=COLUMNS)
    return out.sort_values(["name", "bundle_id"], key=lambda c: c.str.lower()).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output CSV path")
    args = ap.parse_args()

    name_map, roster = load_sources()
    sheet = build(name_map, roster)

    out_path = Path(args.out)
    # utf-8-sig: names carry accents, and Excel needs the BOM to read them.
    sheet.to_csv(out_path, index=False, encoding="utf-8-sig")

    linked = int((sheet["bundle_id"].ne("") & sheet["roster_id"].ne("")).sum())
    bundle_only = int((sheet["bundle_id"].ne("") & sheet["roster_id"].eq("")).sum())
    roster_only = int(sheet["bundle_id"].eq("").sum())

    print(f"Wrote {out_path}  —  {len(sheet)} rows")
    print(f"  {linked:4d} students with both IDs (full name)")
    print(f"  {bundle_only:4d} bundle IDs only (full name)")
    print(f"  {roster_only:4d} roster IDs only (first name + initial)")
    print("\nLocal file — gitignored, do not commit or share outside staff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
