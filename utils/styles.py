# utils/styles.py — VHS CRM v4 — Top nav layout

from utils.font_sqr721e_b64 import FONT_SQR721E_B64

FONT_CSS = f"""
<style>
@font-face {{
    font-family: 'Square721 Ex BT';
    src: url(data:font/truetype;charset=utf-8;base64,{FONT_SQR721E_B64}) format('truetype');
    font-weight: normal;
    font-style: normal;
}}
.vhs-nav-brand-text, .vhs-logo-font {{
    font-family: 'Square721 Ex BT', sans-serif !important;
}}
</style>
"""

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

/* ── VHS STANDARDIZED UI ── */
.vhs-card, div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white !important; border: 1px solid #e2e8f0 !important; border-radius: 14px !important; padding: 24px !important; box-shadow: 0 1px 4px rgba(0,0,0,.04) !important;
}
.vhs-list-item {
    background: white !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; padding: 16px !important; margin-bottom: 16px !important; display: block !important;
}
.vhs-sub-card {
    background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important; padding: 12px !important; margin-top: 10px !important;
}
.vhs-text-title { font-size: 16px !important; font-weight: 700 !important; color: #0f172a !important; }
.vhs-text-subtitle { font-size: 13px !important; color: #64748b !important; }
.vhs-text-caption { font-size: 11px !important; color: #94a3b8 !important; }

/* ── TOP NAVBAR ── */
.vhs-nav {
    position: sticky; top: 0; z-index: 999;
    background: #ffffff;
    padding: 0 24px;
    display: flex; align-items: center; gap: 0;
    height: 54px;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
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
    font-size: 15px; font-weight: 800; color: #0f172a;
    letter-spacing: -.02em;
}
.vhs-nav-brand-sub {
    font-size: 9px; color: #475569; font-weight: 600;
    letter-spacing: .08em; text-transform: uppercase;
}

/* ── NAV ITEMS (radio buttons restyled) ── */
div[data-testid="stRadio"] { margin: 0 !important; width: 100% !important; }
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important; flex-direction: row !important;
    flex-wrap: nowrap !important; gap: 8px !important;
    justify-content: space-between !important;
    width: 100% !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label {
    flex: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    background: transparent !important;
    color: #64748b !important;
    border: none !important; border-radius: 8px !important;
    padding: 8px 10px !important;
    font-size: 13px !important; font-weight: 500 !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    transition: all .15s !important;
}
.element-container:has(.nav-marker) + .element-container div[data-testid="stRadio"] [role="radiogroup"] > label p {
    text-transform: uppercase !important;
    font-weight: 600 !important;
}
/* Hide the radio button circle itself */
div[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {
    display: none !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] input:checked + div,
div[data-testid="stRadio"] input:checked ~ div { color: white !important; }
/* Active nav item */
div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important;
    color: white !important;
}

/* ── STATUS BAR (right side of nav) ── */
.vhs-status {
    margin-left: auto;
    display: flex; align-items: center; gap: 16px;
}
.vhs-status-pill {
    background: #f1f5f9;
    border-radius: 20px; padding: 4px 12px;
    font-size: 11px; color: #64748b;
    display: flex; align-items: center; gap: 5px;
    white-space: nowrap;
}
.vhs-status-pill b { color: #0f172a; }

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
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important;
    color: white !important;
    border: none !important; border-radius: 14px !important;
    font-weight: 600 !important; font-size: 14px !important;
    padding: 10px 18px !important; transition: all .2s ease !important;
    letter-spacing: 0.5px !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg, #1e293b 0%, #294d3f 60%, #22c55e 100%) !important;
    box-shadow: 0 6px 18px rgba(22,163,74,.3) !important;
    transform: translateY(-1px) !important;
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
    font-weight: 600 !important; color: #64748b !important;
    padding: 7px 16px !important; background: transparent !important;
    text-transform: uppercase !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important; color: white !important;
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
    width: 100% !important; 
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
    .block-container { padding: 60px .5rem 20px !important; }
    
    .vhs-nav-st-radio,
    .element-container:has(.nav-marker) + .element-container {
        position: fixed !important;
        top: 0 !important; left: 0 !important; right: 0 !important;
        bottom: auto !important;
        background: white !important;
        border-bottom: 1px solid #e2e8f0 !important;
        z-index: 999999 !important;
        padding: 6px 6px 10px 6px !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08) !important;
        pointer-events: auto; /* Ensure mobile is clickable */
    }
    
    /* Scoped mobile styling for the nav radio only */
    .vhs-nav-st-radio .stRadio,
    .element-container:has(.nav-marker) + .element-container .stRadio { 
        width: 100% !important; margin: 0 !important; 
    }
    .vhs-nav-st-radio .stRadio [role="radiogroup"],
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] {
        display: flex !important;
        width: 100% !important;
        gap: 0px !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        padding: 2px 2px !important;
        scroll-snap-type: x mandatory;
    }
    /* Ẩn thanh cuộn */
    .vhs-nav-st-radio .stRadio [role="radiogroup"]::-webkit-scrollbar,
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"]::-webkit-scrollbar { display: none; }
    .vhs-nav-st-radio .stRadio [role="radiogroup"],
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] { -ms-overflow-style: none; scrollbar-width: none; }

    .vhs-nav-st-radio .stRadio [role="radiogroup"] > div,
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] > div {
        flex: 0 0 auto !important;
        display: flex !important;
        scroll-snap-align: start;
        margin: 0 4px 0 0 !important;
        padding: 0 !important;
    }
    
    /* Đưa Logbook lên đầu tiên trên Mobile */
    .mobile-logbook-item {
        order: -1 !important;
    }
    .vhs-nav-st-radio .stRadio [role="radiogroup"] > div > label,
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] > div > label {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 4px !important;
        background: #f1f5f9 !important;
        color: #334155 !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        border: none !important;
        white-space: nowrap !important;
        min-width: 0 !important;
        margin-right: 2px !important; 
        margin: 0 !important;
    }
    .vhs-nav-st-radio .stRadio [role="radiogroup"] > div > label:hover,
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] > div > label:hover {
        background: #e2e8f0 !important;
    }
    .vhs-nav-st-radio .stRadio [role="radiogroup"] label:has(input:checked),
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(22,163,74,0.3) !important;
    }
    .vhs-nav-st-radio .stRadio [role="radiogroup"] p,
    .element-container:has(.nav-marker) + .element-container .stRadio [role="radiogroup"] p {
        font-size: 15px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        white-space: nowrap !important;
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
    return f'<div style="margin-bottom:18px;"><div style="font-size:20px;font-weight:800;color:#0f172a;text-transform:uppercase;">{icon} {title}</div>{sub}</div>'

def stat_row(label, value, color="#0f172a"):
    return f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f1f5f9;"><span style="font-size:13px;color:#64748b;">{label}</span><span style="font-size:14px;font-weight:600;color:{color};">{value}</span></div>'
