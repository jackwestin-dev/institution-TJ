"""Jack Westin Design System — Streamlit theme helpers."""

# ── Color tokens ─────────────────────────────────────────────────────────────

VIOLET_50  = "#F5F6FD"
VIOLET_100 = "#ECEBFE"
VIOLET_300 = "#BFBEFA"
VIOLET_600 = "#5D5DF2"   # core brand
VIOLET_700 = "#4A45C9"
VIOLET_900 = "#201E3A"   # ink / text-strong

TEAL_500   = "#38B2AC"
AMBER_500  = "#E0922A"

GRAY_50    = "#F7F8FC"
GRAY_100   = "#EFF2F7"
GRAY_200   = "#E4E6F2"
GRAY_400   = "#9A9AB2"
GRAY_500   = "#6E6EA8"
GRAY_600   = "#5A5A72"
WHITE      = "#FFFFFF"

SUCCESS    = "#2FA36B"
DANGER     = "#E0556B"
WARNING    = "#E0922A"

# Ordered palette for multi-series charts
COLOR_SEQ  = [VIOLET_600, TEAL_500, AMBER_500, SUCCESS, DANGER,
              "#9B99F7", "#7FD6CE", "#ECC077"]

# ── Brand header HTML ─────────────────────────────────────────────────────────

JW_LOGO_SVG = (
    '<svg width="40" height="40" viewBox="0 0 96 96" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" aria-label="Jack Westin">'
    f'<rect width="96" height="96" rx="24" fill="{VIOLET_600}"/>'
    '<text x="50%" y="52%" dy="0.04em" text-anchor="middle" '
    'dominant-baseline="middle" font-family="Outfit, system-ui, sans-serif" '
    'font-weight="800" font-size="46" letter-spacing="-1" fill="#FFFFFF">JW</text>'
    '</svg>'
)


def brand_header(subtitle: str = "Canvas Quiz Reports") -> str:
    return f"""
<div style="display:flex;align-items:center;gap:14px;padding:0 0 8px 0;">
  {JW_LOGO_SVG}
  <div>
    <div style="font-family:'Outfit',system-ui,sans-serif;font-weight:800;
                font-size:1.55rem;color:{VIOLET_900};letter-spacing:-0.02em;
                line-height:1.1;">{subtitle}</div>
    <div style="font-family:'Figtree',system-ui,sans-serif;font-size:0.82rem;
                color:{GRAY_500};margin-top:2px;">Jack Westin · JAMP</div>
  </div>
</div>
"""


# ── Global CSS ────────────────────────────────────────────────────────────────

CSS = f"""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Figtree:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=Space+Mono:wght@400;700&display=swap');

/* ── Base typography ── */
html, body, [class*="css"], [data-testid="stMarkdownContainer"] {{
    font-family: 'Figtree', system-ui, sans-serif !important;
    color: {GRAY_600};
}}

h1, h2, h3, h4, h5 {{
    font-family: 'Outfit', system-ui, sans-serif !important;
    color: {VIOLET_900} !important;
    letter-spacing: -0.02em;
}}

/* ── App background ── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"] > div:first-child {{
    background: {GRAY_100};
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {VIOLET_50} !important;
    border-right: 1px solid {GRAY_200} !important;
}}
[data-testid="stSidebar"] h1 {{
    font-family: 'Outfit', system-ui, sans-serif !important;
    color: {VIOLET_600} !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSlider label {{
    font-family: 'Figtree', system-ui, sans-serif !important;
    color: {VIOLET_900} !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}}
[data-testid="stSidebar"] [data-testid="stCaption"] {{
    color: {GRAY_400} !important;
    font-size: 0.78rem !important;
}}

/* ── Metric cards ── */
[data-testid="stMetricContainer"] {{
    background: {WHITE};
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    padding: 1.1rem 1.4rem 1rem !important;
    box-shadow: 0 2px 6px rgba(32,30,58,0.07);
}}
[data-testid="stMetricLabel"] > div {{
    font-family: 'Figtree', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: {GRAY_500} !important;
}}
[data-testid="stMetricValue"] > div {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
    letter-spacing: -0.03em;
    color: {VIOLET_600} !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 2px solid {GRAY_200};
    gap: 4px;
}}
[data-testid="stTabs"] button[role="tab"] {{
    font-family: 'Figtree', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: {GRAY_500} !important;
    border-radius: 8px 8px 0 0;
    padding: 8px 16px !important;
    border: none !important;
    background: transparent !important;
    transition: color 150ms, background 150ms;
}}
[data-testid="stTabs"] button[role="tab"]:hover {{
    color: {VIOLET_700} !important;
    background: {VIOLET_100} !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {VIOLET_600} !important;
    border-bottom: 2px solid {VIOLET_600} !important;
    background: transparent !important;
}}

/* ── Buttons ── */
.stButton > button[kind="primary"],
.stButton > button {{
    font-family: 'Figtree', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    letter-spacing: 0.01em;
    transition: all 200ms cubic-bezier(0.22,1,0.36,1) !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 10px 24px rgba(93,93,242,0.28) !important;
}}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {{
    background: transparent !important;
    color: {VIOLET_600} !important;
    border: 1.5px solid {VIOLET_300} !important;
    border-radius: 8px !important;
    font-family: 'Figtree', sans-serif !important;
    font-weight: 600 !important;
}}
[data-testid="stDownloadButton"] > button:hover {{
    background: {VIOLET_50} !important;
    border-color: {VIOLET_600} !important;
}}

/* ── Selectbox / inputs ──
   A near-white control on a near-white page reads as a caption, not something
   you can click. These give the closed state a visible edge, a tinted fill and
   a chevron big enough to notice. */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    border-color: {GRAY_200} !important;
    border-radius: 8px !important;
    background: {WHITE};
    font-family: 'Figtree', sans-serif !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    border: 1.5px solid {VIOLET_300} !important;
    background: {VIOLET_50} !important;
    cursor: pointer !important;
    transition: border-color 120ms ease, box-shadow 120ms ease;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {{
    border-color: {VIOLET_600} !important;
    box-shadow: 0 0 0 3px rgba(93,93,242,0.14) !important;
}}
/* Streamlit's default #31333F is a mid grey that goes washed out against the
   tinted control. The chosen value and the menu options are the two things a
   reader actually has to read, so both get full-strength text. */
[data-testid="stSelectbox"] div[data-baseweb="select"] div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] div,
[data-testid="stSelectbox"] div[data-baseweb="select"] input,
[data-testid="stMultiSelect"] div[data-baseweb="select"] input {{
    color: {VIOLET_900} !important;
    font-weight: 600 !important;
    -webkit-text-fill-color: {VIOLET_900} !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] [class*="placeholder"],
[data-testid="stMultiSelect"] div[data-baseweb="select"] [class*="placeholder"] {{
    color: {GRAY_500} !important;
    -webkit-text-fill-color: {GRAY_500} !important;
    font-weight: 500 !important;
}}
/* The open menu is a portal outside the widget, so it needs its own rules. */
div[data-baseweb="popover"] li,
ul[data-baseweb="menu"] li,
li[role="option"] {{
    color: {VIOLET_900} !important;
    font-family: 'Figtree', sans-serif !important;
    font-weight: 500 !important;
}}
li[role="option"]:hover,
ul[data-baseweb="menu"] li:hover {{
    background: {VIOLET_50} !important;
    color: {VIOLET_900} !important;
}}
li[role="option"][aria-selected="true"] {{
    background: {VIOLET_50} !important;
    font-weight: 700 !important;
}}

/* The chevron ships at 16px in the page's text colour — easy to miss.
   Must come after the blanket colour rule above so it keeps its own. */
[data-testid="stSelectbox"] div[data-baseweb="select"] svg,
[data-testid="stMultiSelect"] div[data-baseweb="select"] svg {{
    width: 24px !important;
    height: 24px !important;
    color: {VIOLET_600} !important;
    fill: {VIOLET_600} !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div:last-child,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div > div:last-child {{
    border-left: 1px solid {VIOLET_300};
    padding-left: 2px;
}}
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {{
    font-family: 'Figtree', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {VIOLET_900} !important;
}}

/* ── Text inputs (URL / token) ── */
[data-testid="stTextInput"] input {{
    border-color: {GRAY_200} !important;
    border-radius: 8px !important;
    font-family: 'Figtree', sans-serif !important;
    background: {WHITE} !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {VIOLET_600} !important;
    box-shadow: 0 0 0 3px rgba(93,93,242,0.18) !important;
}}

/* ── Divider ── */
hr {{
    border-color: {GRAY_200} !important;
    margin: 1.25rem 0 !important;
}}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div {{
    background: {VIOLET_600} !important;
    border-radius: 999px !important;
}}
[data-testid="stProgressBar"] > div {{
    background: {GRAY_200} !important;
    border-radius: 999px !important;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 6px rgba(32,30,58,0.06);
}}

/* ── Alert / info boxes ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    font-family: 'Figtree', sans-serif !important;
}}

/* ── Spinner text ── */
[data-testid="stSpinner"] p {{
    font-family: 'Figtree', sans-serif !important;
    color: {GRAY_500} !important;
}}

/* ── Subheader ── */
[data-testid="stMarkdownContainer"] h3 {{
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: {VIOLET_900} !important;
    border-bottom: 1px solid {GRAY_200};
    padding-bottom: 8px;
    margin-bottom: 16px;
}}
</style>
"""


# ── Plotly chart defaults ─────────────────────────────────────────────────────

def _deep_merge(base: dict, extra: dict) -> dict:
    """
    Merge `extra` into `base`, recursing into nested dicts.

    A plain dict.update() would let a caller passing xaxis=dict(categoryorder=…)
    wipe out the entire styled xaxis — gridcolor, tick font and all — leaving an
    unstyled axis. Only the keys actually supplied should win.
    """
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def plotly_layout(**overrides) -> dict:
    """
    Layout dict to pass to fig.update_layout().

    Callers override any key; nested dicts merge rather than replace, and
    `title="…"` is accepted as shorthand for the title text so the styling
    survives.
    """
    # Plotly.js prints the string "undefined" above a chart when the title
    # object carries styling but no text, which is exactly what this base
    # provides. An explicit empty string keeps untitled charts blank.
    title_override = overrides.pop("title", None)
    if isinstance(title_override, str):
        title_override = {"text": title_override}

    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=WHITE,
        font=dict(
            family="Figtree, system-ui, sans-serif",
            color=GRAY_600,
            size=13,
        ),
        title=dict(
            text="",
            font=dict(
                family="Outfit, system-ui, sans-serif",
                color=VIOLET_900,
                size=16,
                weight=700,
            ),
            x=0,
            xanchor="left",
            pad=dict(b=12),
        ),
        xaxis=dict(
            gridcolor=GRAY_200,
            linecolor=GRAY_200,
            tickfont=dict(family="Space Mono, monospace", size=11, color=GRAY_400),
            title_font=dict(family="Figtree, sans-serif", color=GRAY_500, size=12),
        ),
        yaxis=dict(
            gridcolor=GRAY_200,
            linecolor=GRAY_200,
            tickfont=dict(family="Space Mono, monospace", size=11, color=GRAY_400),
            title_font=dict(family="Figtree, sans-serif", color=GRAY_500, size=12),
        ),
        colorway=COLOR_SEQ,
        hoverlabel=dict(
            bgcolor=WHITE,
            bordercolor=GRAY_200,
            font=dict(family="Figtree, sans-serif", color=VIOLET_900, size=13),
        ),
        margin=dict(t=48, r=16, b=16, l=16),
        legend=dict(
            font=dict(family="Figtree, sans-serif", size=12, color=GRAY_600),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    if title_override is not None:
        overrides["title"] = title_override
    return _deep_merge(base, overrides)
