

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import base64
import urllib.parse
import concurrent.futures
from datetime import datetime

from .. import jw_theme as jw

# page_config and global CSS are set once in the app.py router

BASE_URL = "https://jackwestin.com/nova-api"


# ── helpers ───────────────────────────────────────────────────────────────────

def get_headers(cookie_string, user_agent=""):
    cookie_string = cookie_string.strip().replace("\n", "").replace("\r", "")
    xsrf_token = ""
    for part in cookie_string.split(";"):
        part = part.strip()
        if part.startswith("XSRF-TOKEN="):
            xsrf_token = urllib.parse.unquote(part[len("XSRF-TOKEN="):])
            break
    headers = {
        "Cookie": cookie_string,
        "X-XSRF-TOKEN": xsrf_token,
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://jackwestin.com/nova/",
    }
    if user_agent:
        headers["User-Agent"] = user_agent.strip()
    return headers


def nova_to_dict(resource):
    """Flatten Nova's {id, fields:[{attribute, value, belongsToId}]} into a plain dict."""
    id_raw = resource.get("id", {})
    row = {"id": id_raw.get("value") if isinstance(id_raw, dict) else id_raw}
    for field in resource.get("fields", []):
        attr = field.get("attribute")
        if not attr or attr == "id":
            continue
        row[attr] = field.get("value")
        bid = field.get("belongsToId")
        if bid is not None:
            row[f"{attr}_id"] = bid
    return row


def safe_get(url, params, headers, label):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching {label}: {e}")
        st.stop()
    if r.status_code == 401:
        st.error("Session expired (401) — paste fresh cookies and click Load Data again.")
        st.stop()
    if r.status_code == 403:
        if "Cloudflare" in r.text or "cf-ray" in str(r.headers).lower():
            st.error(
                "Cloudflare is blocking the request (403). "
                "Make sure you copied the **User-Agent** from your browser and pasted it in the sidebar, "
                "and that your cookies include `cf_clearance`."
            )
        else:
            st.error(
                f"Access denied (403) fetching {label}. "
                "Your cookies may have expired — paste fresh ones from the browser. "
                "If fresh, your account may not have access to this class ID."
            )
        with st.expander("Response details"):
            st.code(r.text[:1000])
        st.stop()
    if not r.ok:
        st.error(f"HTTP {r.status_code} fetching {label}: {r.text[:300]}")
        st.stop()
    try:
        return r.json()
    except Exception:
        st.error(f"Non-JSON response for {label}: {r.text[:300]}")
        st.stop()


def session_sort_key(sess):
    """Extract a datetime from a session dict for sorting."""
    for key in ("date", "scheduled_at", "start_at", "starts_at", "started_at"):
        val = sess.get(key)
        if val and str(val).strip():
            try:
                return datetime.fromisoformat(str(val).replace(" ", "T"))
            except Exception:
                pass
    return datetime.min


def build_session_label(sess, idx):
    """Return a unique human-readable label for a session dict."""
    prefix = f"#{idx + 1}"
    for key in ("date", "scheduled_at", "start_at", "starts_at", "started_at", "name", "title"):
        val = sess.get(key)
        if val and str(val).strip():
            try:
                dt = datetime.fromisoformat(str(val).replace(" ", "T"))
                return f"{prefix} {dt.strftime('%b %d')}"
            except Exception:
                return f"{prefix} {str(val)[:20]}"
    return f"Session {idx + 1}"


def dedup_attendance(df):
    """Collapse multiple re-join records for the same student+session into one row."""
    group_cols = ["session_id", "user_id"] if "user_id" in df.columns else ["session_id", "user"]
    agg = {"user": "first", "session_label": "first", "session_num": "first"}
    if "started_at" in df.columns:
        agg["started_at"] = "min"
    if "ended_at" in df.columns:
        agg["ended_at"] = "max"
    if "duration_min" in df.columns:
        agg["duration_min"] = "sum"
    return df.groupby(group_cols, as_index=False).agg(agg)


# ── API calls ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_sessions(class_id, cookie_string, user_agent=""):
    headers = get_headers(cookie_string, user_agent)
    sessions = []
    page = 1
    while True:
        params = {
            "search": "",
            "filters": base64.b64encode(b"[]").decode(),
            "orderBy": "id,asc",
            "perPage": 200,
            "trashed": "",
            "page": page,
            "viaResource": "classes",
            "viaResourceId": class_id,
            "viaRelationship": "sessions",
            "relationshipType": "hasMany",
        }
        data = safe_get(f"{BASE_URL}/sessions", params, headers, "sessions")
        sessions.extend([nova_to_dict(r) for r in data.get("resources", [])])
        if data.get("next_page_url") is None:
            break
        page += 1
    return sorted(sessions, key=session_sort_key)


def _fetch_attendances_worker(session_id, headers):
    """Fetch all attendance pages for one session. Raises on error (no Streamlit calls)."""
    filters_b64 = base64.b64encode(
        json.dumps([{"class": "App\\Nova\\Filters\\AttendedOpenFilter", "value": ""}]).encode()
    ).decode()
    records = []
    page = 1
    while True:
        params = {
            "search": "",
            "filters": filters_b64,
            "orderBy": "",
            "perPage": 100,
            "trashed": "",
            "page": page,
            "viaResource": "sessions",
            "viaResourceId": session_id,
            "viaRelationship": "attendances",
            "relationshipType": "hasMany",
        }
        r = requests.get(f"{BASE_URL}/attendances", params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        records.extend([nova_to_dict(rec) for rec in data.get("resources", [])])
        if data.get("next_page_url") is None:
            break
        page += 1
    return records


def fetch_all_attendances(sessions, cookie_str, ua_str):
    """Fetch attendance for all sessions in parallel. Returns (all_rows, errors)."""
    headers = get_headers(cookie_str, ua_str)

    def fetch_one(args):
        i, sess = args
        sid = sess["id"]
        label = build_session_label(sess, i)
        records = _fetch_attendances_worker(sid, headers)
        for rec in records:
            rec["session_id"] = sid
            rec["session_label"] = label
            rec["session_num"] = i + 1
        return i, records

    n = len(sessions)
    all_results = [[] for _ in range(n)]
    errors = []
    progress = st.progress(0, text="Loading attendance records…")
    done = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_one, (i, sess)): i for i, sess in enumerate(sessions)}
        for future in concurrent.futures.as_completed(futures):
            try:
                i, records = future.result()
                all_results[i] = records
            except Exception as e:
                idx = futures[future]
                errors.append(f"Session {sessions[idx].get('id', idx)}: {e}")
            done += 1
            progress.progress(done / n, text=f"Loaded {done} / {n} sessions…")

    progress.empty()
    all_rows = [rec for records in all_results for rec in records]
    return all_rows, errors


def render() -> None:
    # ── sidebar ───────────────────────────────────────────────────────────────────

    with st.sidebar:
        st.title("⚙️ Settings")
        class_id = st.number_input("Class ID", value=722, min_value=1, step=1)
        cookie_string = st.text_area(
            "Browser Cookies",
            height=150,
            placeholder="Paste the full Cookie header value here…",
            help="F12 → Network → any nova-api request → Headers → Request Headers → Cookie",
        )
        user_agent = st.text_input(
            "User-Agent",
            placeholder="Paste your browser's User-Agent header value here…",
            help="F12 → Network → any request → Request Headers → User-Agent. Required when Cloudflare blocks requests.",
        )
        load_btn = st.button(
            "🔄 Load Data", type="primary", use_container_width=True,
            disabled=not bool(cookie_string)
        )
        st.caption("⚠️ Cookies expire with your browser session. Re-paste if you get a 401 error.")

    if not cookie_string:
        st.markdown(jw.brand_header("Nova Attendance Dashboard"), unsafe_allow_html=True)
        st.info("👈 Paste your browser cookies in the sidebar, then click **Load Data**.")
        st.stop()


    # ── load sessions ─────────────────────────────────────────────────────────────

    if load_btn or "sessions" not in st.session_state:
        fetch_sessions.clear()
        with st.spinner("Fetching sessions for class…"):
            sessions = fetch_sessions(int(class_id), cookie_string, user_agent)
        if not sessions:
            st.warning(f"No sessions returned for class {class_id}. Check the class ID.")
            st.stop()
        st.session_state["sessions"] = sessions
        st.session_state["cookie"] = cookie_string
        st.session_state["user_agent"] = user_agent
        st.session_state.pop("df_raw", None)
        st.session_state.pop("df", None)

    sessions = st.session_state["sessions"]
    cookie_str = st.session_state.get("cookie", cookie_string)
    ua_str = st.session_state.get("user_agent", user_agent)


    # ── load all attendance records (parallel) ────────────────────────────────────

    if "df_raw" not in st.session_state:
        all_rows, errors = fetch_all_attendances(sessions, cookie_str, ua_str)

        if errors:
            st.warning(f"Could not load {len(errors)} session(s): {'; '.join(errors[:3])}")

        if not all_rows:
            st.warning("No attendance records found across all sessions.")
            st.stop()

        df_raw = pd.DataFrame(all_rows)
        for col in ("started_at", "ended_at"):
            if col in df_raw.columns:
                df_raw[col] = pd.to_datetime(df_raw[col], errors="coerce")
        if "started_at" in df_raw.columns and "ended_at" in df_raw.columns:
            df_raw["duration_min"] = (
                (df_raw["ended_at"] - df_raw["started_at"]).dt.total_seconds() / 60
            ).round(1)

        st.session_state["df_raw"] = df_raw
        st.session_state["df"] = dedup_attendance(df_raw)

    df_raw = st.session_state["df_raw"]
    df_all = st.session_state["df"]


    # ── session filter (sidebar) ──────────────────────────────────────────────────

    all_labels = [build_session_label(s, i) for i, s in enumerate(sessions)]

    with st.sidebar:
        st.divider()
        selected_labels = st.multiselect(
            "Sessions to display",
            options=all_labels,
            default=all_labels,
        )

    if not selected_labels:
        st.warning("No sessions selected — pick at least one in the sidebar.")
        st.stop()

    df = df_all[df_all["session_label"].isin(selected_labels)]
    df_raw_view = df_raw[df_raw["session_label"].isin(selected_labels)]
    total_sessions = len(selected_labels)


    # ── page header ───────────────────────────────────────────────────────────────

    st.markdown(jw.brand_header("Nova Attendance Dashboard"), unsafe_allow_html=True)
    st.caption(f"Class {class_id} · {total_sessions} of {len(sessions)} sessions · {df['user'].nunique()} unique students")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", total_sessions)
    c2.metric("Unique Students", df["user"].nunique())
    c3.metric("Attendance Records", len(df))
    if "duration_min" in df.columns:
        c4.metric("Median Duration", f"{df['duration_min'].median():.0f} min")

    st.divider()


    # ── ordered session list for chart axes ───────────────────────────────────────

    sess_order = [lbl for lbl in all_labels if lbl in selected_labels]


    # ── chart 1: attendees per session ────────────────────────────────────────────

    st.subheader("Attendees per Session")

    sess_counts = df.groupby("session_label").size().reset_index(name="attendees")

    fig1 = px.bar(
        sess_counts,
        x="session_label",
        y="attendees",
        category_orders={"session_label": sess_order},
        labels={"session_label": "Session", "attendees": "Students Attended"},
        color="attendees",
        color_continuous_scale="Blues",
        height=380,
    )
    fig1.update_coloraxes(showscale=False)
    fig1.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig1, use_container_width=True)


    # ── chart 2: duration distribution per session ────────────────────────────────

    if "duration_min" in df.columns:
        st.subheader("Time Spent per Student per Session")
        fig2 = px.box(
            df,
            x="session_label",
            y="duration_min",
            category_orders={"session_label": sess_order},
            labels={"session_label": "Session", "duration_min": "Duration (min)"},
            points="all",
            height=380,
        )
        fig2.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)


    # ── chart 3: student × session heatmap ───────────────────────────────────────

    st.subheader("Student × Session Heatmap")

    pivot = df.pivot_table(
        index="user",
        columns="session_label",
        values="session_id",
        aggfunc="count",
        fill_value=0,
    )
    pivot = pivot.reindex(columns=[c for c in sess_order if c in pivot.columns], fill_value=0)
    pivot = pivot.clip(upper=1)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    fig3 = px.imshow(
        pivot,
        color_continuous_scale=["#f0f0f0", "#1a73e8"],
        zmin=0,
        zmax=1,
        aspect="auto",
        labels={"color": "Attended"},
        height=max(420, len(pivot) * 20),
    )
    fig3.update_coloraxes(showscale=False)
    fig3.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig3, use_container_width=True)


    # ── chart 4: per-student summary table ───────────────────────────────────────

    st.subheader("Per-Student Attendance Summary")

    agg_dict = {"session_label": "nunique"}
    if "duration_min" in df.columns:
        agg_dict["duration_min"] = "mean"

    summary = df.groupby("user").agg(agg_dict).reset_index()
    summary.columns = (
        ["Student", "Sessions Attended", "Avg Duration (min)"]
        if "duration_min" in df.columns
        else ["Student", "Sessions Attended"]
    )
    summary["Attendance %"] = (summary["Sessions Attended"] / total_sessions * 100).round(1)
    if "Avg Duration (min)" in summary.columns:
        summary["Avg Duration (min)"] = summary["Avg Duration (min)"].round(1)
    summary = summary.sort_values("Attendance %", ascending=False)

    st.dataframe(summary, use_container_width=True, hide_index=True)


    # ── raw data ──────────────────────────────────────────────────────────────────

    with st.expander("📋 Raw attendance records"):
        st.dataframe(df_raw_view, use_container_width=True)
