import streamlit as st

COLORS = {
    "dark": "#243447",
    "muted": "#607086",
    "silver": "#E9EEF2",
    "silver2": "#F5F7FA",
    "white": "#FFFFFF",
    "aqua": "#6FD3C0",
    "turquoise": "#35B6D6",
    "lilac": "#B8A7E8",
    "purple": "#6E4CCF",
    "purple_dark": "#4B2CA0",
    "warning": "#F59E0B",
    "danger": "#E85D75",
    "ok": "#2FBF9B",
}


def aplicar_tema():
    st.markdown(
        """
<style>
    :root {
        --dark: #243447;
        --muted: #607086;
        --silver: #E9EEF2;
        --silver2: #F5F7FA;
        --white: #FFFFFF;
        --aqua: #6FD3C0;
        --turquoise: #35B6D6;
        --lilac: #B8A7E8;
        --purple: #6E4CCF;
        --purpleDark: #4B2CA0;
        --warning: #F59E0B;
        --danger: #E85D75;
        --ok: #2FBF9B;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(111,211,192,0.10), transparent 30%),
            radial-gradient(circle at top right, rgba(184,167,232,0.10), transparent 32%),
            linear-gradient(180deg, #FFFFFF 0%, #F4F8FA 100%);
        color: var(--dark);
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F0F5F8 100%);
        border-right: 1px solid rgba(138,151,166,0.24);
    }

    .hero {
        background:
            linear-gradient(135deg, rgba(36,52,71,0.98) 0%, rgba(53,182,214,0.94) 54%, rgba(110,76,207,0.92) 100%);
        color: white !important;
        border-radius: 28px;
        padding: 28px 32px;
        margin-bottom: 18px;
        box-shadow: 0 18px 52px rgba(36,52,71,0.22);
        position: relative;
        overflow: hidden;
    }

    .hero h1, .hero p, .hero div, .hero span {
        color: white !important;
    }

    .hero h1 {
        margin: 0;
        font-size: 38px;
        font-weight: 850;
        letter-spacing: -0.04em;
    }

    .hero p {
        margin: 8px 0 0 0;
        font-size: 15px;
        color: rgba(255,255,255,0.84) !important;
        max-width: 900px;
    }

    .kpi-card {
        background: rgba(255,255,255,0.96);
        border: 1px solid rgba(233,238,242,0.95);
        border-radius: 24px;
        padding: 18px 20px;
        min-height: 128px;
        box-shadow: 0 14px 35px rgba(36,52,71,0.08);
        color: var(--dark) !important;
    }

    .kpi-card div, .kpi-card span, .kpi-card p {
        color: var(--dark) !important;
    }

    .kpi-label {
        color: var(--muted) !important;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 8px;
    }

    .kpi-value {
        color: var(--dark) !important;
        font-size: 31px;
        font-weight: 850;
        line-height: 1.05;
        letter-spacing: -0.03em;
    }

    .kpi-sub {
        color: var(--muted) !important;
        font-size: 13px;
        margin-top: 8px;
    }

    .panel {
        background: rgba(255,255,255,0.96);
        border: 1px solid rgba(233,238,242,0.95);
        border-radius: 26px;
        padding: 22px;
        box-shadow: 0 14px 40px rgba(36,52,71,0.07);
        margin-bottom: 18px;
        color: var(--dark) !important;
    }

    .panel div, .panel span, .panel p, .panel label {
        color: var(--dark) !important;
    }

    .panel-title {
        color: var(--dark) !important;
        font-size: 20px;
        font-weight: 850;
        letter-spacing: -0.02em;
        margin-bottom: 14px;
    }

    .panel-subtitle {
        color: var(--muted) !important;
        font-size: 13px;
        margin-top: -8px;
        margin-bottom: 14px;
    }

    .pill {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 800;
        margin: 2px 4px 2px 0;
        white-space: nowrap;
    }

    .pill-aqua { background: rgba(111,211,192,0.22); color: #116B5B !important; }
    .pill-turq { background: rgba(53,182,214,0.20); color: #075D72 !important; }
    .pill-lilac { background: rgba(184,167,232,0.28); color: #4B2CA0 !important; }
    .pill-purple { background: rgba(110,76,207,0.18); color: #4B2CA0 !important; }
    .pill-danger { background: rgba(232,93,117,0.17); color: #9F1239 !important; }
    .pill-warn { background: rgba(245,158,11,0.18); color: #8A4F00 !important; }

    .mini-row {
        border: 1px solid rgba(233,238,242,0.95);
        border-radius: 18px;
        padding: 12px 14px;
        margin-bottom: 10px;
        background: #FFFFFF;
        color: var(--dark) !important;
    }

    .mini-row div, .mini-row span, .mini-row p {
        color: var(--dark) !important;
    }

    .mini-title {
        color: var(--dark) !important;
        font-weight: 820;
        font-size: 15px;
    }

    .mini-sub {
        color: var(--muted) !important;
        font-size: 13px;
        margin-top: 2px;
    }

    .alert-box {
        border-radius: 20px;
        padding: 14px 16px;
        margin-bottom: 10px;
        border: 1px solid rgba(233,238,242,0.9);
        background: white;
        color: var(--dark) !important;
    }

    .alert-box div, .alert-box span, .alert-box p, .alert-box b {
        color: var(--dark) !important;
    }

    .alert-danger { border-left: 7px solid var(--danger); }
    .alert-warn { border-left: 7px solid var(--warning); }
    .alert-ok { border-left: 7px solid var(--aqua); }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        flex-wrap: wrap;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding: 10px 17px;
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(233,238,242,0.95);
    }

    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {
        color: var(--dark) !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(111,211,192,0.32), rgba(184,167,232,0.30));
    }

    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {
        color: var(--purpleDark) !important;
        font-weight: 800;
    }

    .stButton > button {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, var(--purpleDark), var(--purple));
        border: 0;
        border-radius: 12px;
        font-weight: 800;
    }

    .stButton > button:hover {
        filter: brightness(1.06);
        border: 0;
    }

    input, textarea, select {
        color: var(--dark) !important;
    }

    label, p, span, div {
        color: var(--dark);
    }

    .muted {
        color: var(--muted) !important;
        font-size: 13px;
    }

    .big-number {
        font-size: 42px;
        color: var(--dark) !important;
        font-weight: 900;
        line-height: 1;
        letter-spacing: -0.05em;
    }
</style>
        """,
        unsafe_allow_html=True,
    )
