#!/usr/bin/env python3
"""
Read a CSV with columns: [N Anticipated Test Date] and [YYYY-MM-DD 0:00:00].
Strip " 0:00:00" from dates and append rows to institution-1-test-data.csv.
Usage: python add_anticipated_test_dates.py [input.csv]
Default input: anticipated_test_dates.csv
"""
import csv
import re
import sys

INPUT_CSV = "anticipated_test_dates.csv"
OUTPUT_CSV = "institution-1-test-data.csv"

def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else INPUT_CSV
    rows_to_append = []

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # First populated column: "N Anticipated Test Date" -> student_id = N
            first = (row[0] or "").strip()
            match = re.match(r"^(\d+)\s*Anticipated Test Date", first, re.IGNORECASE)
            if not match:
                continue
            student_id = match.group(1)
            # Find column with date (YYYY-MM-DD 0:00:00)
            date_str = None
            for cell in row:
                cell = (cell or "").strip()
                if re.match(r"\d{4}-\d{2}-\d{2}", cell):
                    date_str = cell.replace(" 0:00:00", "").strip()
                    break
            if not date_str:
                continue
            rows_to_append.append((student_id, "Anticipated Test Date", date_str, ""))

    if not rows_to_append:
        print("No rows parsed. Check CSV format: first column 'N Anticipated Test Date', another column 'YYYY-MM-DD 0:00:00'")
        return

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in rows_to_append:
            writer.writerow(r)

    print(f"Appended {len(rows_to_append)} rows to {OUTPUT_CSV} (dates cleaned: no 0:00:00).")

if __name__ == "__main__":
    main()
