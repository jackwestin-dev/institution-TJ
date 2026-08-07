"""
Paths and credential lookup for the Canvas Accuracy views.

Credentials resolve in this order:
  1. st.secrets  — how Streamlit Community Cloud supplies them
  2. environment / .env — how local runs supply them
  3. "" — the views then prompt for the value in the sidebar

Reading st.secrets raises when no secrets.toml exists, which is the normal
local case, so every lookup is guarded.
"""
import os
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional on the server
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent

# Full Student Analysis exports — gitignored, present only on a local checkout
# that has run sync_reports.py.
CACHE_DIR = REPO_ROOT / "reports_cache"

# MCAT score exports — gitignored, student names in the clear.
EXAM_DATA_DIR = REPO_ROOT / "exam_data"

# Name-free aggregates built by build_canvas_metrics.py. Committed, so the
# deployed app has data even with no cache on disk.
DATA_DIR = REPO_ROOT / "data"


def secret(name: str, default: str = "") -> str:
    """Look up a credential in st.secrets, then the environment."""
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()


def has_local_cache() -> bool:
    """True when the full report cache is on disk (local dev, not the server)."""
    return CACHE_DIR.exists() and any(CACHE_DIR.glob("*.csv"))


def cache_note() -> str:
    """One-line explanation of where the numbers on screen came from."""
    if has_local_cache():
        n = len(list(CACHE_DIR.glob("*.csv")))
        return f"Reading {n} cached report(s) from `reports_cache/`."
    return (
        "No local report cache — this is the deployed app, so per-student views "
        "are unavailable. Run `python sync_reports.py` on a local checkout to "
        "populate `reports_cache/`."
    )
