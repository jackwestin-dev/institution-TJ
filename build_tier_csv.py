#!/usr/bin/env python3
"""
Build tier.csv from institution-1-engagement-data.csv:
Small Group and Large Group attendance tiers per student_id across two time windows.
Output: tier.csv (or path given by OUT_PATH).
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_CSV = "institution-1-engagement-data.csv"
# Prefer project directory; if /mnt/data exists (e.g. in a container), write there too
OUT_PATH = "tier.csv"
OUT_PATH_ALT = "/mnt/data/tier.csv"

WINDOW_A_START = "2025-06-01"
WINDOW_A_END = "2025-12-31"
WINDOW_A_LABEL = "Jun-Dec 2025"
WINDOW_B_START = "2026-01-01"
WINDOW_B_LABEL = "Jan 2026-Current"

# Column detection (aggregated format)
AGG_COLS = {
    "student_id": "student_id",
    "date_col": "start_date",  # used to assign window
    "num_attended_small_session": "num_attended_small_session",
    "num_scheduled_small_session": "num_scheduled_small_session",
    "num_attended_large_session": "num_attended_large_session",
    "num_scheduled_large_session": "num_scheduled_large_session",
}


def parse_date(s):
    """Parse US-style or ISO date."""
    if pd.isna(s) or s == "":
        return pd.NaT
    s = str(s).strip()
    try:
        return pd.to_datetime(s)
    except Exception:
        pass
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT


def assign_window(dt, window_b_start, max_date):
    if pd.isna(dt):
        return None
    if dt >= window_b_start and dt <= max_date:
        return WINDOW_B_LABEL
    if WINDOW_A_START <= str(dt)[:10] <= WINDOW_A_END:
        return WINDOW_A_LABEL
    return None


def tier_from_rate(rate, scheduled):
    if scheduled == 0 or pd.isna(scheduled):
        return "No Scheduled Sessions"
    if pd.isna(rate):
        return "No Scheduled Sessions"
    if rate > 0.70:  # Tier 1: >70%
        return "Tier 1"
    if rate >= 0.50 and rate <= 0.70:  # Tier 2: 50–70%
        return "Tier 2"
    return "Tier 3"


def main():
    # ---------------------------------------------------------------------------
    # 1) Load and detect format
    # ---------------------------------------------------------------------------
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    # Drop completely empty columns (e.g. Unnamed: 16)
    df = df.dropna(axis=1, how="all")

    # Detect: aggregated columns present?
    has_agg = all(
        c in df.columns
        for c in [
            AGG_COLS["student_id"],
            AGG_COLS["num_attended_small_session"],
            AGG_COLS["num_scheduled_small_session"],
            AGG_COLS["num_attended_large_session"],
            AGG_COLS["num_scheduled_large_session"],
        ]
    )
    date_col = AGG_COLS["date_col"] if AGG_COLS["date_col"] in df.columns else None

    if has_agg and date_col:
        print("Detected: aggregated format (num_attended_* / num_scheduled_* per row).")
        print(f"Using date column: {date_col}")
    else:
        # Would need log-level handling and session type/scheduled/attended flags
        raise ValueError(
            "Aggregated columns not found. Expected: student_id, num_attended_small_session, "
            "num_scheduled_small_session, num_attended_large_session, num_scheduled_large_session, "
            "and a date column (e.g. start_date) for window assignment."
        )

    sid = AGG_COLS["student_id"]
    df["_parsed_date"] = df[date_col].apply(parse_date)
    max_date = df["_parsed_date"].max()
    window_b_start_dt = pd.Timestamp(WINDOW_B_START)

    df["date_window"] = df["_parsed_date"].apply(
        lambda d: assign_window(d, window_b_start_dt, max_date)
    )
    df = df[df["date_window"].notna()].copy()

    # Coerce numeric
    for col in [
        "num_attended_small_session",
        "num_scheduled_small_session",
        "num_attended_large_session",
        "num_scheduled_large_session",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # ---------------------------------------------------------------------------
    # 2) Aggregate per student_id per date_window
    # ---------------------------------------------------------------------------
    grp = df.groupby([sid, "date_window"], as_index=False).agg(
        num_scheduled_small_session=("num_scheduled_small_session", "sum"),
        num_attended_small_session=("num_attended_small_session", "sum"),
        num_scheduled_large_session=("num_scheduled_large_session", "sum"),
        num_attended_large_session=("num_attended_large_session", "sum"),
    )

    # ---------------------------------------------------------------------------
    # 3) Rates and tiers
    # ---------------------------------------------------------------------------
    def rate(sched, att):
        if sched == 0:
            return np.nan
        return att / sched

    grp["small_group_attendance_rate"] = grp.apply(
        lambda r: rate(r["num_scheduled_small_session"], r["num_attended_small_session"]), axis=1
    )
    grp["large_group_attendance_rate"] = grp.apply(
        lambda r: rate(r["num_scheduled_large_session"], r["num_attended_large_session"]), axis=1
    )

    grp["small_group_tier"] = grp.apply(
        lambda r: tier_from_rate(
            r["small_group_attendance_rate"], r["num_scheduled_small_session"]
        ),
        axis=1,
    )
    grp["large_group_tier"] = grp.apply(
        lambda r: tier_from_rate(
            r["large_group_attendance_rate"], r["num_scheduled_large_session"]
        ),
        axis=1,
    )

    # Round rates to 3 decimals; leave blank when no scheduled
    grp["small_group_attendance_rate"] = grp["small_group_attendance_rate"].round(3)
    grp["large_group_attendance_rate"] = grp["large_group_attendance_rate"].round(3)
    grp.loc[grp["num_scheduled_small_session"] == 0, "small_group_attendance_rate"] = np.nan
    grp.loc[grp["num_scheduled_large_session"] == 0, "large_group_attendance_rate"] = np.nan

    # ---------------------------------------------------------------------------
    # 4) Final column order (exact sheet format, no extra tiers)
    # ---------------------------------------------------------------------------
    out = grp[
        [
            sid,
            "date_window",
            "num_scheduled_small_session",
            "num_attended_small_session",
            "small_group_attendance_rate",
            "small_group_tier",
            "num_scheduled_large_session",
            "num_attended_large_session",
            "large_group_attendance_rate",
            "large_group_tier",
        ]
    ].copy()
    out = out.sort_values([sid, "date_window"]).reset_index(drop=True)

    # Ensure date_window order: Jun-Dec 2025 then Jan 2026-Current
    out["date_window"] = pd.Categorical(
        out["date_window"], categories=[WINDOW_A_LABEL, WINDOW_B_LABEL], ordered=True
    )
    out = out.sort_values([sid, "date_window"]).reset_index(drop=True)
    out["date_window"] = out["date_window"].astype(str)

    # ---------------------------------------------------------------------------
    # 5) Save
    # ---------------------------------------------------------------------------
    out.to_csv(OUT_PATH, index=False)
    print(f"Saved: {os.path.abspath(OUT_PATH)}")
    if os.path.isdir(os.path.dirname(OUT_PATH_ALT)):
        out.to_csv(OUT_PATH_ALT, index=False)
        print(f"Also saved: {OUT_PATH_ALT}")

    # ---------------------------------------------------------------------------
    # 6) Summaries: tier counts per date_window
    # ---------------------------------------------------------------------------
    print("\n--- Small group tier counts by date_window ---")
    for w in [WINDOW_A_LABEL, WINDOW_B_LABEL]:
        sub = out[out["date_window"] == w]
        if sub.empty:
            print(f"  {w}: (no rows)")
            continue
        counts = sub["small_group_tier"].value_counts().sort_index()
        print(f"  {w}:")
        for tier, n in counts.items():
            print(f"    {tier}: {n}")

    print("\n--- Large group tier counts by date_window ---")
    for w in [WINDOW_A_LABEL, WINDOW_B_LABEL]:
        sub = out[out["date_window"] == w]
        if sub.empty:
            print(f"  {w}: (no rows)")
            continue
        counts = sub["large_group_tier"].value_counts().sort_index()
        print(f"  {w}:")
        for tier, n in counts.items():
            print(f"    {tier}: {n}")


if __name__ == "__main__":
    main()
