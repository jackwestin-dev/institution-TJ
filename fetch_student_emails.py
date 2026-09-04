#!/usr/bin/env python
"""Pull the course roster's email addresses into a local, gitignored CSV.

The outreach list is worked by emailing students, so it needs an address next to
each name. Canvas has them on the enrolment endpoint (`include[]=email`), but
nothing else in this repo stores them: `data/students.csv` and `roster.csv` are
deliberately de-identified, and the committed data bundle carries opaque IDs.

Output is `data/.student_emails.csv` — a dotfile alongside `.student_map.csv`,
gitignored for the same reason: an email address identifies a student as surely
as their name, and git history cannot be un-published.

Re-run this whenever enrolment changes; build_outreach_report.py reads the file
if it is present and leaves the Email column blank if it is not.

Usage:
    python fetch_student_emails.py            # course 345 (EY26)
    python fetch_student_emails.py --course 351

Credentials come from .env (CANVAS_URL, CANVAS_TOKEN) or the environment.
"""
import argparse
import csv
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", ".student_emails.csv")


def fetch(canvas_url: str, token: str, course_id: int) -> list:
    """[{name, sortable_name, email, canvas_user_id, sis_user_id}] for students."""
    url = f"{canvas_url.rstrip('/')}/api/v1/courses/{course_id}/users"
    params = {
        "enrollment_type[]": ["student"],
        "include[]": ["email"],
        "per_page": 100,
    }
    headers = {"Authorization": f"Bearer {token}"}
    rows = []
    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        params = None  # the Link header carries the query on later pages
        for u in resp.json():
            if not isinstance(u, dict) or "id" not in u:
                continue
            # login_id is the fallback: on this instance it is the same address,
            # and it is populated even when the email attribute is suppressed.
            email = (u.get("email") or u.get("login_id") or "").strip()
            rows.append({
                "canvas_user_id": u["id"],
                "name": (u.get("name") or "").strip(),
                "sortable_name": (u.get("sortable_name") or "").strip(),
                "email": email,
                "sis_user_id": (u.get("sis_user_id") or "").strip(),
            })
        url = None
        for part in (resp.headers.get("Link") or "").split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip("<> ")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--course", type=int, default=345)
    args = ap.parse_args()

    canvas_url = os.getenv("CANVAS_URL", "").strip()
    token = os.getenv("CANVAS_TOKEN", "").strip()
    if not canvas_url or not token:
        print("ERROR: CANVAS_URL and CANVAS_TOKEN must be set in .env or the environment.",
              file=sys.stderr)
        return 1

    rows = fetch(canvas_url, token, args.course)
    if not rows:
        print(f"No students returned for course {args.course}.", file=sys.stderr)
        return 1

    rows.sort(key=lambda r: r["sortable_name"] or r["name"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    missing = [r["name"] for r in rows if not r["email"]]
    print(f"wrote {OUT}")
    print(f"{len(rows)} students, {len(rows) - len(missing)} with an address")
    if missing:
        print(f"  no address for {len(missing)}: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
