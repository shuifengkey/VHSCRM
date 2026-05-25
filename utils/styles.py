# utils/styles.py — VHS CRM v4 — Top nav layout

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, sans-serif !important;
}
.stApp { background: #f0f2f5 !important; color: #0f172a !important; }
.block-container { padding: 0 1.5rem 2rem !important; max-width: 1400px; }

/* ── HIDE sidebar & default chrome ── */
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── TOP NAVBAR ── */
.vhs-nav {
    position: sticky; top: 0; z-index: 999;
    background: #0f172a;
    padding: 0 24px;
    display: flex; align-items: center; gap: 0;
    height: 54px;
    box-shadow: 0 2px 12px rgba(0,0,0,.25);
    margin-bottom: 20px;
}
.vhs-nav-brand {
    display: flex; align-items: center; gap: 10px;
    padding-right: 24px;
    border-right: 1px solid #1e293b;
    margin-right: 8px;
    white-space: nowrap;
}
.vhs-nav-brand-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg,#16a34a,#0d9488);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
}
.vhs-nav-brand-text {
    font-size: 15px; font-weight: 800; color: #f1f5f9;
    letter-spacing: -.02em;
}
.vhs-nav-brand-sub {
    font-size: 9px; color: #475569; font-weight: 600;
    letter-spacing: .08em; text-transform: uppercase;
}

/* ── NAV ITEMS (radio buttons restyled) ── */
div[data-testid="stHorizontalBlock"] { gap: 0 !important; }
.stRadio { margin: 0 !important; }
.stRadio > label { display: none !important; }
.stRadio > div {
    display: flex !important; flex-direction: row !important;
    flex-wrap: nowrap !important; gap: 2px !important;
}
.stRadio > div > label {
    background: transparent !important;
    color: #94a3b8 !important;
    border: none !important; border-radius: 8px !important;
    padding: 6px 13px !important;
    font-size: 13px !important; font-weight: 500 !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    transition: all .15s !important;
}
/* Hide the radio button circle itself */
.stRadio > div > label > div:first-child {
    display: none !important;
}
.stRadio > div > label:hover {
    background: rgba(255,255,255,.07) !important;
    color: #e2e8f0 !important;
}
.stRadio > div > label[data-baseweb="radio"] input:checked + div,
.stRadio input:checked ~ div { color: white !important; }
/* Active nav item */
.stRadio > div [data-checked="true"],
.stRadio > div label:has(input:checked) {
    background: #16a34a !important;
    color: white !important;
}

/* ── STATUS BAR (right side of nav) ── */
.vhs-status {
    margin-left: auto;
    display: flex; align-items: center; gap: 16px;
}
.vhs-status-pill {
    background: rgba(255,255,255,.07);
    border-radius: 20px; padding: 4px 12px;
    font-size: 11px; color: #94a3b8;
    display: flex; align-items: center; gap: 5px;
    white-space: nowrap;
}
.vhs-status-pill b { color: #e2e8f0; }

/* ── METRICS ── */
[data-testid="metric-container"] {
    background: white !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.05) !important;
    transition: transform .15s, box-shadow .15s;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,.09) !important;
}
[data-testid="metric-container"] label {
    font-size: 11px !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: .06em !important;
    color: #64748b !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 26px !important; font-weight: 800 !important; color: #0f172a !important;
}

/* ── BUTTONS ── */
.stButton > button {
    background: #16a34a !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; font-size: 13px !important;
    padding: 9px 18px !important; transition: all .15s !important;
}
.stButton > button:hover {
    background: #15803d !important;
    box-shadow: 0 4px 14px rgba(22,163,74,.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important; color: #374151 !important;
    border: 1.5px solid #d1d5db !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #f9fafb !important; box-shadow: 0 2px 8px rgba(0,0,0,.08) !important;
}

/* ── INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important; font-size: 13px !important;
    background: white !important; color: #0f172a !important;
    transition: border-color .15s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #16a34a !important;
    box-shadow: 0 0 0 3px rgba(22,163,74,.12) !important;
}
.stTextInput label, .stSelectbox label, .stNumberInput label,
.stDateInput label, .stTextArea label, .stTimeInput label {
    font-size: 11px !important; font-weight: 700 !important;
    color: #374151 !important; text-transform: uppercase !important;
    letter-spacing: .05em !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: white !important; border-radius: 12px !important;
    padding: 4px !important; gap: 2px !important;
    border: 1px solid #e2e8f0 !important;
    width: fit-content !important; margin-bottom: 18px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important; font-size: 13px !important;
    font-weight: 500 !important; color: #64748b !important;
    padding: 7px 16px !important; background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: #16a34a !important; color: white !important;
}

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: white !important; border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important; font-weight: 600 !important;
    font-size: 13px !important; color: #0f172a !important;
}
.streamlit-expanderContent {
    background: #fafafa !important; border: 1px solid #e2e8f0 !important;
    border-top: none !important; border-radius: 0 0 12px 12px !important;
}

/* ── FORM SUBMIT ── */
[data-testid="stFormSubmitButton"] > button {
    background: #16a34a !important; color: white !important;
    border-radius: 10px !important; font-weight: 700 !important;
    width: 100%; padding: 12px !important; font-size: 14px !important;
}

/* ── ALERTS ── */
.stAlert { border-radius: 10px !important; border-left-width: 4px !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* ── MOBILE ── */
@media (max-width: 768px) {
    .vhs-nav { display: none !important; }
    .block-container { padding: 0 .5rem 80px !important; }
    
    .vhs-nav-radio-container {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: white;
        border-top: 1px solid #e2e8f0;
        z-index: 9999;
        padding: 6px 4px 16px 4px !important; /* Thu nhỏ padding 2 bên */
        box-shadow: 0 -4px 24px rgba(0,0,0,0.08);
    }
    .stRadio { width: 100% !important; margin: 0 !important; }
    .stRadio > div {
        justify-content: space-between !important;
        width: 100% !important;
        gap: 1px !important; /* Thu nhỏ tối đa khoảng cách */
        flex-wrap: nowrap !important;
        background: #f1f5f9 !important; /* Tạo viền giả giữa các nút */
        padding: 2px !important;
        border-radius: 14px !important;
    }
    .stRadio > div > label {
        flex: 1 1 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        background: transparent !important;
        color: #475569 !important;
        padding: 6px 0 !important;
        border-radius: 10px !important;
        border: none !important;
        height: auto !important;
        min-height: 48px !important;
        overflow: hidden !important;
    }
    .stRadio > div > label:hover {
        background: rgba(0,0,0,0.04) !important;
    }
    .stRadio > div [data-checked="true"],
    .stRadio > div label:has(input:checked) {
        background: #16a34a !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(22,163,74,0.3) !important;
    }
    /* Style the text inside the radio labels to be small */
    .stRadio > div > label p {
        font-size: 11px !important;
        font-weight: 800 !important;
        margin: 0 !important;
        text-align: center !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
    }

    /* ── TABS (Menu phụ) MOBILE ── */
    .stTabs [data-baseweb="tab-list"] {
        width: 100% !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        padding: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1 0 auto !important;
        text-align: center !important;
        padding: 8px 12px !important;
        font-size: 12px !important;
        white-space: nowrap !important;
    }
    /* Ẩn thanh cuộn của tab */
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
}
</style>
"""

COLORS = {
    "primary":"#16a34a","primary_dark":"#15803d","primary_light":"#dcfce7",
    "danger":"#dc2626","danger_light":"#fee2e2",
    "warning":"#d97706","warning_light":"#fef3c7",
    "info":"#2563eb","info_light":"#dbeafe",
    "text":"#0f172a","muted":"#64748b","border":"#e2e8f0",
    "card":"#ffffff","bg":"#f0f2f5",
}

def card(content, padding="18px", border_left=None, bg="white", extra=""):
    bl = f"border-left:4px solid {border_left};" if border_left else ""
    return f'<div style="background:{bg};border:1px solid #e2e8f0;border-radius:14px;padding:{padding};{bl}box-shadow:0 1px 4px rgba(0,0,0,.05);margin-bottom:10px;{extra}">{content}</div>'

def badge(text, color="green"):
    s = {"green":("dcfce7","166534"),"red":("fee2e2","991b1b"),
         "yellow":("fef9c3","854d0e"),"blue":("dbeafe","1e40af"),
         "gray":("f1f5f9","475569"),"purple":("ede9fe","5b21b6"),
         "orange":("ffedd5","9a3412")}
    bg, fg = s.get(color, s["gray"])
    return f'<span style="background:#{bg};color:#{fg};padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.04em;">{text}</span>'

def section_header(title, subtitle="", icon=""):
    sub = f'<div style="font-size:13px;color:#64748b;margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return f'<div style="margin-bottom:18px;"><div style="font-size:20px;font-weight:800;color:#0f172a;">{icon} {title}</div>{sub}</div>'

def stat_row(label, value, color="#0f172a"):
    return f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f1f5f9;"><span style="font-size:13px;color:#64748b;">{label}</span><span style="font-size:14px;font-weight:600;color:{color};">{value}</span></div>'
