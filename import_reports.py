#!/usr/bin/env python
"""
Import hand-downloaded Student Analysis CSVs into the report cache, and refresh
cached titles from Canvas.

Why this exists: Canvas exports every homework with the same filename, and for a
long stretch of course 345 every homework assignment was literally titled
"Homework". Topic pairing (pre-class quiz vs homework on the same subject) is
impossible against titles like that, so the assignments were renamed in Canvas
and re-exported. This script folds those exports back in.

Matching is by content first, filename second:

  1. ItemID fingerprint against the files already cached. Canvas item IDs are
     unique per question, so an exact set match identifies the assignment
     regardless of what either file is called. This is what disambiguates the
     two distinct "CARS - Practice Homework" assignments.
  2. Normalised filename against the live Canvas assignment list, for exports of
     assignments that were never cached at all.

Titles always come from Canvas, never from the filename — the filename is only
ever used to find the right assignment.

Usage:
    python import_reports.py --course 345 --source "path/to/Renamed Homeworks"
    python import_reports.py --course 345 --retitle-only
    python import_reports.py --course 345 --source ... --dry-run
"""
import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from canvas_app import reports_cache as rc
from canvas_app.canvas_api import CanvasAPI

load_dotenv()

# Canvas tacks these onto every export; strip before matching a filename.
_FILENAME_NOISE = re.compile(
    r"\s*(student analysis report|quiz and item analysis report)\s*(\(\d+\))?\s*$",
    re.IGNORECASE,
)


def normalise(text: str) -> str:
    """Comparison key that survives the export's punctuation mangling.

    Canvas filenames replace "/" and ":" with "_", so "Acid/Base Chemistry"
    arrives as "Acid_Base Chemistry" and "Enzymes: Features" as
    "Enzymes_ Features". Dropping non-alphanumerics sidesteps all of it.
    """
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text).lower())).strip()


def title_from_filename(path: Path) -> str:
    return _FILENAME_NOISE.sub("", path.stem).strip()


def item_fingerprint(path_or_bytes) -> frozenset:
    """Set of Canvas ItemIDs in a Student Analysis export."""
    try:
        df = pd.read_csv(path_or_bytes, nrows=5, low_memory=False)
    except Exception:
        return frozenset()
    ids = set()
    for col in df.columns:
        if re.match(r"^ItemID(\.\d+)?$", str(col)):
            ids |= {str(v) for v in df[col].dropna().unique()}
    return frozenset(ids)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--course", type=int, required=True)
    ap.add_argument("--source", help="Folder of Student Analysis CSVs to import.")
    ap.add_argument("--retitle-only", action="store_true",
                    help="Only refresh cached titles from Canvas; import nothing.")
    ap.add_argument("--dry-run", action="store_true", help="Report, change nothing.")
    args = ap.parse_args()

    if not args.source and not args.retitle_only:
        ap.error("give --source, or --retitle-only")

    canvas_url = os.getenv("CANVAS_URL", "").strip()
    token = os.getenv("CANVAS_TOKEN", "").strip()
    if not canvas_url or not token:
        print("ERROR: CANVAS_URL and CANVAS_TOKEN must be set in .env.", file=sys.stderr)
        return 2

    print(f"Fetching assignment list for course {args.course}…")
    quizzes = [q for q in CanvasAPI(canvas_url, token).get_quizzes(args.course)
               if q.get("_type") == "new"]
    by_id = {q["id"]: q for q in quizzes}
    print(f"  {len(quizzes)} New Quizzes")

    # ── Refresh titles on everything already cached ────────────────────────────
    index = rc.load_index()
    retitled = 0
    for entry in rc.cached_for_course(args.course):
        aid = entry["assignment_id"]
        live = by_id.get(aid)
        if not live:
            continue
        old, new = entry.get("title") or "", live["title"]
        if old != new:
            print(f"  retitle {aid}: {old[:34]!r} -> {new[:52]!r}")
            retitled += 1
            if not args.dry_run:
                index[f"{args.course}_{aid}"]["title"] = new
    if retitled and not args.dry_run:
        rc.save_index(index)
    print(f"Retitled {retitled} cached report(s).")

    if args.retitle_only:
        return 0

    # ── Import the source folder ───────────────────────────────────────────────
    source = Path(args.source)
    if not source.is_dir():
        print(f"ERROR: {source} is not a directory.", file=sys.stderr)
        return 2
    files = sorted(source.glob("*.csv"))
    print(f"\n{len(files)} CSV(s) in {source.name}")

    cached_fp = {
        entry["assignment_id"]: item_fingerprint(rc.CACHE_DIR / f"{args.course}_{entry['assignment_id']}.csv")
        for entry in rc.cached_for_course(args.course)
    }
    title_index: "dict[str, list]" = {}
    for q in quizzes:
        title_index.setdefault(normalise(q["title"]), []).append(q)

    imported = replaced = skipped = 0
    unresolved = []

    for path in files:
        fp = item_fingerprint(path)

        # 1. content match against the cache
        aid = next((a for a, cfp in cached_fp.items() if cfp and fp and cfp == fp), None)
        how = "content"

        # 2. filename match against Canvas
        if aid is None:
            candidates = title_index.get(normalise(title_from_filename(path)), [])
            unclaimed = [q for q in candidates if q["id"] not in cached_fp]
            if len(unclaimed) == 1:
                aid, how = unclaimed[0]["id"], "filename"
            elif len(candidates) == 1:
                aid, how = candidates[0]["id"], "filename"
            else:
                unresolved.append((path.name, f"{len(candidates)} title match(es)"))
                continue

        live = by_id.get(aid)
        if live is None:
            unresolved.append((path.name, f"assignment {aid} not in Canvas"))
            continue

        existed = rc.is_cached(args.course, aid)
        action = "replace" if existed else "IMPORT "
        print(f"  {action} {args.course}_{aid}  ({how:8s})  {live['title'][:54]}")
        if not args.dry_run:
            rc.save_csv(
                args.course, aid, path.read_bytes(),
                title=live["title"],
                points_possible=live.get("points_possible"),
                due_at=live.get("due_at", ""),
            )
            cached_fp[aid] = fp
        replaced += existed
        imported += not existed

    print(f"\n=== {imported} imported, {replaced} replaced, {skipped} skipped ===")
    if unresolved:
        print(f"{len(unresolved)} could not be matched:")
        for name, why in unresolved:
            print(f"  {name[:66]} — {why}")
    if args.dry_run:
        print("(dry run — nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
