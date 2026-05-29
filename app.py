# app.py — VHSCRM v4 — Top navbar layout
import streamlit as st
import sys, os, hashlib, base64

def format_money(val):
    if not val: return "0"
    return f"{int(val):,}".replace(",", ".")


from utils.database import init_db, get_connection
from utils.styles import GLOBAL_CSS, FONT_CSS, card, badge, section_header, stat_row, COLORS
from datetime import timezone, datetime, date, timedelta
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Load logo
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")
with open(_LOGO_PATH, "rb") as _f:
    _LOGO_B64 = base64.b64encode(_f.read()).decode()
_LOGO_URI = f"data:image/png;base64,{_LOGO_B64}"

from PIL import Image
st.set_page_config(
    page_title="VHSCRM", page_icon=Image.open(_LOGO_PATH),
    layout="wide", initial_sidebar_state="collapsed"
)
init_db()

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(FONT_CSS, unsafe_allow_html=True)
# Global CSS override for primary buttons
st.markdown("""
<style>
/* Override default primary button color to ensure it is always the dark VHS gradient */
div[data-testid="baseButton-primary"] > button, div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important;
    color: white !important;
    border: none !important;
}
div[data-testid="baseButton-primary"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg, #1e293b 0%, #294d3f 60%, #22c55e 100%) !important;
    box-shadow: 0 8px 24px rgba(22,163,74,0.3) !important;
    color: white !important;
    transform: translateY(-1px) !important;
}
</style>
""", unsafe_allow_html=True)

# PWA Install to Home Screen Injection
components.html(f"""
<script>
const head = window.parent.document.head;

let appleIcon = head.querySelector('link[rel="apple-touch-icon"]');
if (!appleIcon) {{
    appleIcon = window.parent.document.createElement('link');
    appleIcon.rel = 'apple-touch-icon';
    head.appendChild(appleIcon);
}}
appleIcon.href = '{_LOGO_URI}';

let manifest = head.querySelector('link[rel="manifest"]');
const manifestData = {{
    "short_name": "VHSCRM",
    "name": "VHS CRM",
    "icons": [
        {{ "src": "{_LOGO_URI}", "type": "image/png", "sizes": "192x192" }},
        {{ "src": "{_LOGO_URI}", "type": "image/png", "sizes": "512x512" }}
    ],
    "start_url": ".",
    "display": "standalone",
    "theme_color": "#0f172a",
    "background_color": "#0f172a"
}};
const manifestBlob = new Blob([JSON.stringify(manifestData)], {{type: 'application/json'}});
const manifestUrl = URL.createObjectURL(manifestBlob);

if (manifest) {{
    manifest.href = manifestUrl;
}} else {{
    manifest = window.parent.document.createElement('link');
    manifest.rel = 'manifest';
    manifest.href = manifestUrl;
    head.appendChild(manifest);
}}

let themeMeta = head.querySelector('meta[name="theme-color"]');
if (themeMeta) {{ themeMeta.content = '#0f172a'; }}
else {{
    themeMeta = window.parent.document.createElement('meta');
    themeMeta.name = 'theme-color';
    themeMeta.content = '#0f172a';
    head.appendChild(themeMeta);
}}

['mobile-web-app-capable', 'apple-mobile-web-app-capable'].forEach(name => {{
    let meta = head.querySelector(`meta[name="${{name}}"]`);
    if (!meta) {{
        meta = window.parent.document.createElement('meta');
        meta.name = name;
        meta.content = 'yes';
        head.appendChild(meta);
    }}
}});

let appleTitle = head.querySelector('meta[name="apple-mobile-web-app-title"]');
if (!appleTitle) {{
    appleTitle = window.parent.document.createElement('meta');
    appleTitle.name = 'apple-mobile-web-app-title';
    appleTitle.content = 'VHSCRM';
    head.appendChild(appleTitle);
}}
</script>
""", height=0, width=0)

# ============================================================
# PIN AUTHENTICATION LAYER
# ============================================================
def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def _ensure_pin_table():
    """Tạo bảng app_settings và PIN mặc định (1234) nếu chưa có."""
    conn = get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    conn.commit()
    existing = conn.execute("SELECT value FROM app_settings WHERE key='pin_hash'").fetchone()
    if not existing:
        conn.execute("INSERT INTO app_settings (key, value) VALUES ('pin_hash', ?)", (_hash_pin("1234"),))
        conn.commit()
    conn.close()

def _verify_pin(pin: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key='pin_hash'").fetchone()
    conn.close()
    if not row:
        return pin == "1234"
    return row["value"] == _hash_pin(pin)

import time
def _check_lockout():
    conn = get_connection()
    lock = conn.execute("SELECT value FROM app_settings WHERE key='locked_until'").fetchone()
    conn.close()
    if lock:
        try:
            lock_time = float(lock['value'])
            if time.time() < lock_time:
                return lock_time
            else:
                _reset_lockout()
        except: pass
    return 0

def _record_failed_attempt():
    conn = get_connection()
    attempts = conn.execute("SELECT value FROM app_settings WHERE key='failed_attempts'").fetchone()
    count = int(attempts['value']) if attempts else 0
    count += 1
    conn.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES ('failed_attempts', ?)", (str(count),))
    if count >= 5:
        lock_time = time.time() + 300 # 5 minutes lockout
        conn.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES ('locked_until', ?)", (str(lock_time),))
    conn.commit()
    conn.close()

def _reset_lockout():
    conn = get_connection()
    conn.execute("DELETE FROM app_settings WHERE key='failed_attempts'")
    conn.execute("DELETE FROM app_settings WHERE key='locked_until'")
    conn.commit()
    conn.close()

def _change_pin(new_pin: str):
    conn = get_connection()
    conn.execute("UPDATE app_settings SET value=? WHERE key='pin_hash'", (_hash_pin(new_pin),))
    conn.commit()
    conn.close()

_ensure_pin_table()

# ---------- PIN GATE ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "pin_error" not in st.session_state:
    st.session_state.pin_error = False
if "pin_input" not in st.session_state:
    st.session_state.pin_input = ""

if not st.session_state.authenticated:
    # Style the entire page as the PIN screen
    st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
.stApp {
    background: linear-gradient(145deg, #0a0f1e 0%, #101b33 40%, #0d2b1a 100%) !important;
}
.block-container {
    max-width: 400px !important;
    padding-top: 8vh !important;
    margin: 0 auto !important;
}
/* Style the PIN input specifically */
[data-testid="stTextInput"] > div > div > input {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 16px !important;
    text-align: center !important;
    letter-spacing: 2px !important;
}
[data-testid="stTextInput"] > div > div > input:focus {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)

    error_html = ""
    if st.session_state.pin_error:
        error_html = '<div style="background:rgba(220,38,38,0.12);border:1px solid rgba(220,38,38,0.3);border-radius:10px;padding:8px 14px;margin-bottom:16px;font-size:13px;color:#fca5a5;font-weight:600;text-align:center;animation:pinShake 0.4s ease-in-out;">🔒 Mã PIN không chính xác!</div>'

    st.markdown(f"""
<style>
@keyframes pinSlideIn {{
    from {{ opacity: 0; transform: translateY(30px) scale(0.97); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes pinPulse {{
    0%, 100% {{ box-shadow: 0 0 30px rgba(22,163,74,0.3); }}
    50% {{ box-shadow: 0 0 50px rgba(22,163,74,0.5); }}
}}
@keyframes pinShake {{
    0%, 100% {{ transform: translateX(0); }}
    20%, 60% {{ transform: translateX(-8px); }}
    40%, 80% {{ transform: translateX(8px); }}
}}
div[data-testid="InputInstructions"] {{ display: none !important; }}
</style>
<div style="animation:pinSlideIn 0.5s cubic-bezier(0.16,1,0.3,1);text-align:center;padding:20px 0 24px;">
    <img src="{_LOGO_URI}" style="width:90px;height:90px;margin:0 auto 20px;display:block;filter:drop-shadow(0 0 20px rgba(22,163,74,0.4));animation:pinPulse 2s infinite;" />
    <div class="vhs-logo-font" style="font-size:26px;font-weight:800;color:#f8fafc;margin-bottom:6px;letter-spacing:-0.3px;">VHSCRM</div>
    <div style="font-size:13px;color:#64748b;margin-bottom:24px;">Nhập mã PIN để truy cập hệ thống</div>
    {error_html}
""", unsafe_allow_html=True)

    st.markdown("""
    <style>
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        pin_val = st.text_input(
            "Nhập mã PIN",
            type="password",
            max_chars=6,
            key="pin_field",
            placeholder="",
            label_visibility="collapsed"
        )
        
        import streamlit.components.v1 as components
        components.html("""
        <script>
        const setNumeric = () => {
            const inputs = window.parent.document.querySelectorAll('input[type="password"]');
            inputs.forEach(input => {
                if (input.getAttribute('inputmode') !== 'numeric') {
                    input.setAttribute('inputmode', 'numeric');
                    input.setAttribute('pattern', '[0-9]*');
                }
            });
        };
        setNumeric();
        setTimeout(setNumeric, 100);
        setTimeout(setNumeric, 500);
        setTimeout(setNumeric, 1000);
        setTimeout(setNumeric, 2000);
        </script>
        """, height=0, width=0)

        submitted = st.form_submit_button("🔓 XÁC NHẬN", type="primary", use_container_width=True)

    lock_time = _check_lockout()
    if lock_time > 0:
        st.error(f"Quá nhiều lần thử! Vui lòng thử lại sau {int(lock_time - time.time())} giây.")
        st.stop()
        
    if submitted:
        is_valid = False
        role = ""
        if pin_val == "1710":
            is_valid = True
            role = "ktv"
        elif _verify_pin(pin_val):
            is_valid = True
            role = "admin"
            
        if is_valid:
            _reset_lockout()
            st.markdown(f"""
            <style>
            .loader-overlay {{
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background: #0f172a;
                z-index: 999999;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                animation: pinSlideIn 0.3s ease;
            }}
            </style>
            <div class="loader-overlay">
                <img src="{_LOGO_URI}" style="width:80px;height:80px;animation:pinPulse 1s infinite;margin-bottom:20px;border-radius:20px;filter:drop-shadow(0 0 20px rgba(22,163,74,0.4));" />
                <div style="color:#22c55e;font-weight:700;font-size:17px;letter-spacing:0.5px;">Đang tải dữ liệu...</div>
            </div>
            """, unsafe_allow_html=True)
            import time
            time.sleep(0.8)
            st.session_state.authenticated = True
            st.session_state.auth_role = role
            st.session_state.pin_error = False
            st.session_state.pin_input = ""
            st.rerun()
        else:
            _record_failed_attempt()
            st.session_state.pin_error = True
            st.rerun()

    st.markdown("""
<div style="text-align:center;margin-top:32px;font-size:11px;color:#475569;">
    <i class=\"ph-shield-check\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Bảo mật bởi VHSCRM
</div>
""", unsafe_allow_html=True)

    st.stop()  # Block everything below until authenticated

# ============================================================
# AUTHENTICATED — MAIN APP
# ============================================================

if st.session_state.get("auth_role") == "ktv":
    import importlib
    from pages import p7_mobile_ktv
    importlib.reload(p7_mobile_ktv)
    p7_mobile_ktv.render()
    st.stop()

# Tự động sinh lịch mỗi lần load app (tháng trước + tháng này + tháng tới)
if "auto_scheduled_month" not in st.session_state or st.session_state.auto_scheduled_month != date.today().strftime("%Y-%m"):
    from utils.scheduling import auto_generate_all_future_schedules
    auto_generate_all_future_schedules(months=2)
    st.session_state.auto_scheduled_month = date.today().strftime("%Y-%m")

# Tự động backup Google Drive cuối tháng
if "auto_backup_checked" not in st.session_state:
    st.session_state.auto_backup_checked = True
    try:
        conn = get_connection()
        last_backup = conn.execute("SELECT value_data FROM settings WHERE key_name='last_drive_backup_month'").fetchone()
        last_backup_month = last_backup['value_data'] if last_backup else ""
        
        current_date = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
        current_month_str = current_date.strftime("%Y-%m")
        
        import calendar
        is_last_day = current_date.day == calendar.monthrange(current_date.year, current_date.month)[1]
        
        should_backup = False
        if is_last_day and last_backup_month != current_month_str:
            should_backup = True
        elif last_backup_month and current_month_str > last_backup_month:
            should_backup = True
            
        if not last_backup_month and not is_last_day:
            conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='last_drive_backup_month'), 'last_drive_backup_month', ?)", (current_month_str,))
            conn.commit()
            
        if should_backup:
            import sqlite3, os, tempfile
            tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            fd, path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            if os.path.exists(path): os.remove(path)
            
            local_conn = sqlite3.connect(path)
            for t in tables:
                tname = t['name']
                sql = t['sql']
                if sql: local_conn.execute(sql)
                rows = conn.execute(f"SELECT * FROM {tname}").fetchall()
                if rows:
                    cols = rows[0].keys() if hasattr(rows[0], 'keys') else rows[0]._mapping.keys()
                    placeholders = ','.join(['?' for _ in cols])
                    col_names = ','.join(cols)
                    insert_sql = f"INSERT INTO {tname} ({col_names}) VALUES ({placeholders})"
                    for row in rows:
                        local_conn.execute(insert_sql, tuple(row[c] for c in cols))
            local_conn.commit(); local_conn.close()
            
            with open(path, "rb") as f:
                db_bytes = f.read()
            os.remove(path)
            
            from utils.google_sync import get_cached_credentials, upload_to_google_drive
            settings = dict(conn.execute("SELECT key_name, value_data FROM settings").fetchall())
            client_id = settings.get("google_client_id")
            client_secret = settings.get("google_client_secret")
            cache_str = settings.get("google_token_cache")
            if client_id and client_secret and cache_str:
                creds, _ = get_cached_credentials(client_id, client_secret, cache_str)
                if creds and creds.valid:
                    filename = f"vhscrm_backup_{current_month_str}_{current_date.day}.db" if is_last_day else f"vhscrm_backup_missed_{last_backup_month}.db"
                    ok, _ = upload_to_google_drive(creds, db_bytes, filename)
                    if ok:
                        conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='last_drive_backup_month'), 'last_drive_backup_month', ?)", (current_month_str,))
                        conn.commit()
                        # Only show toast if it was a background task during a session
        conn.close()
    except Exception as e:
        print("Auto Backup error:", e)




# ============================================================
# TOP NAVBAR
# ============================================================
@st.cache_data(ttl=15)
def _get_navbar_stats(today_str):
    conn = get_connection()
    ca = conn.execute(
        "SELECT COUNT(*) FROM schedules WHERE ngay_du_kien=? AND trang_thai='scheduled'",
        (today_str,)
    ).fetchone()[0]
    no = conn.execute(
        "SELECT COALESCE(SUM(can_thu-da_thu),0) FROM debts WHERE can_thu>da_thu"
    ).fetchone()[0]
    conn.close()
    return ca, no

now  = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
today_str   = now.date().strftime("%Y-%m-%d")
ca_hom_nay, tong_no = _get_navbar_stats(today_str)

# Brand + status HTML
st.markdown(f"""
<div class="vhs-nav">
  <div class="vhs-nav-brand">
    <img src="{_LOGO_URI}" style="width:38px;height:38px;border-radius:8px;" />
    <div>
      <div class="vhs-nav-brand-text">VHSCRM</div>
      <div class="vhs-nav-brand-sub">Pest Control v4</div>
    </div>
  </div>
  <!-- nav items rendered by st.radio below -->
  <div style="flex:1;display:flex;align-items:center;" id="vhs-nav-items"></div>
  <div class="vhs-status">
    <div class="vhs-status-pill"><i class=\"ph-wrench\" style=\"font-size:15px;color:#475569;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>{ca_hom_nay}</b> ca hôm nay</div>
    <div class="vhs-status-pill"><i class=\"ph-warning\" style=\"font-size:15px;color:#d97706;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Nợ <b>{format_money(tong_no)}</b></div>
    <div class="vhs-status-pill"><i class=\"ph-clock\" style=\"font-size:15px;color:#d97706;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>{now.strftime('%H:%M')}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

NAV_ITEMS = [
    "🏠 Tổng Quan",
    "👥 Khách Hàng",
    "📄 Hợp Đồng",
    "📅 Lịch Thi Công",
    "📓 Work Log",
    "💰 Công Nợ",
    "🖨️ Xuất PDF",
    "⚙️ Cài đặt"
]

# Đặt radio ngay dưới navbar (CSS inline lo Desktop, CSS media query lo Mobile)
st.markdown('<div style="background:#0f172a;padding:0 24px 0 180px;margin-top:-74px;margin-bottom:20px;" class="nav-marker">', unsafe_allow_html=True)
page = st.radio("nav", NAV_ITEMS, horizontal=True, label_visibility="collapsed", key="topnav")
st.markdown("</div>", unsafe_allow_html=True)

# JS: Thêm class vào đúng container của radio để CSS dễ style (không dùng appendChild để tránh lỗi React)
# Và tag mục Logbook để đẩy lên đầu trên Mobile
components.html("""
<script>
(function() {
    const parentDoc = window.parent.document;
    
    function updateNav() {
        const navMark = parentDoc.querySelector('.nav-marker');
        if (navMark) {
            const mdContainer = navMark.closest('.element-container');
            if (mdContainer) {
                const radioContainer = mdContainer.nextElementSibling;
                if (radioContainer) {
                    radioContainer.classList.add('vhs-nav-st-radio');
                    
                    // Tìm Logbook và gắn class để CSS xếp nó lên đầu tiên
                    const labels = radioContainer.querySelectorAll('label');
                    labels.forEach(label => {
                        if (label.innerText && label.innerText.includes('Work Log')) {
                            // Đi ngược lên DOM để tìm phần tử con trực tiếp của radiogroup
                            let current = label;
                            while (current && current.parentElement) {
                                if (current.parentElement.getAttribute('role') === 'radiogroup') {
                                    current.classList.add('mobile-logbook-item');
                                    break;
                                }
                                current = current.parentElement;
                            }
                        }
                    });
                }
            }
        }
    }
    
    // Chạy định kỳ để đảm bảo không bị mất class khi React render lại
    setInterval(updateNav, 500);
    updateNav();
})();
</script>
""", height=0, width=0)

if "last_main_tab" not in st.session_state:
    st.session_state.last_main_tab = page
if "current_subpage" not in st.session_state:
    st.session_state.current_subpage = None

if page != st.session_state.last_main_tab:
    st.session_state.current_subpage = None
    st.session_state.last_main_tab = page


# ============================================================
# DASHBOARD
# ============================================================
if page == "🏠 Tổng Quan":
    conn = get_connection()
    today = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
    today_str = today.strftime("%Y-%m-%d")

    total_kh    = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_hd    = conn.execute("SELECT COUNT(*) FROM contracts WHERE trang_thai='active'").fetchone()[0]
    doanh_thu   = conn.execute("SELECT COALESCE(SUM(gia_tri_thang),0) FROM contracts WHERE trang_thai='active'").fetchone()[0]
    ca_hom_nay  = conn.execute("SELECT COUNT(*) FROM schedules WHERE ngay_du_kien=? AND trang_thai='scheduled'",(today_str,)).fetchone()[0]
    sap_het_han = conn.execute(
        "SELECT COUNT(*) FROM contracts WHERE ngay_het_han BETWEEN ? AND ?",
        (today_str,(today+timedelta(days=30)).strftime("%Y-%m-%d"))
    ).fetchone()[0]
    tong_no     = conn.execute("SELECT COALESCE(SUM(can_thu-da_thu),0) FROM debts WHERE can_thu>da_thu").fetchone()[0]
    ca_done     = conn.execute("SELECT COUNT(*) FROM schedules WHERE trang_thai='completed'").fetchone()[0]
    da_thu_thang = conn.execute(
        "SELECT COALESCE(SUM(da_thu),0) FROM debts WHERE ky_thanh_toan=?",
        (today.strftime("%Y-%m"),)
    ).fetchone()[0]

    # Banner
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a2f 60%,#166534 100%);
                border-radius:18px;padding:24px 28px;margin-bottom:22px;
                box-shadow:0 4px 24px rgba(0,0,0,.15);">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-size:22px;font-weight:800;color:white;text-transform:uppercase;">Tổng quan hệ thống VHS</div>
          <div style="font-size:13px;color:#86efac;margin-top:3px;">{now.strftime('%A, %d/%m/%Y — %H:%M')}</div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:white;">{ca_hom_nay}</div>
            <div style="font-size:11px;color:#bbf7d0;">Ca hôm nay</div>
          </div>
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:#fbbf24;">{sap_het_han}</div>
            <div style="font-size:11px;color:#bbf7d0;">HĐ sắp hết hạn</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("👥 Khách Hàng",    total_kh)
    with c2: st.metric("📄 HĐ Active",      total_hd)
    with c3: st.metric("💵 Doanh Thu/Tháng",f"{format_money(doanh_thu)} đ")
    with c4: st.metric("✓ Ca Hoàn Thành",  ca_done)
    with c5: st.metric("⚠️ Công Nợ",        f"{format_money(tong_no)} đ")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Charts
    col_l, col_r = st.columns([3,2])
    with col_l:
        monthly = conn.execute("""
            SELECT ky_thanh_toan, SUM(can_thu) ct, SUM(da_thu) dt
            FROM debts GROUP BY ky_thanh_toan ORDER BY ky_thanh_toan DESC LIMIT 6
        """).fetchall()
        monthly = list(reversed(monthly))
        if monthly:
            fig = go.Figure()
            fig.add_scatter(x=[r["ky_thanh_toan"] for r in monthly],
                            y=[r["ct"] for r in monthly],
                            name="Cần Thu", line=dict(color="#e2e8f0",width=3),
                            fill="tozeroy", fillcolor="rgba(226,232,240,.3)")
            fig.add_scatter(x=[r["ky_thanh_toan"] for r in monthly],
                            y=[r["dt"] for r in monthly],
                            name="Đã Thu", line=dict(color="#16a34a",width=3),
                            fill="tozeroy", fillcolor="rgba(22,163,74,.15)",
                            mode="lines+markers", marker=dict(size=6,color="#16a34a"))
            fig.update_layout(height=240, paper_bgcolor="white", plot_bgcolor="white",
                title=dict(text="Doanh Thu 6 Tháng (triệu đ)",font=dict(size=13,color="#0f172a")),
                margin=dict(l=10,r=10,t=36,b=30), font=dict(family="Inter"),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True,gridcolor="#f1f5f9"),
                legend=dict(orientation="h",y=-0.25))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_r:
        seg = conn.execute("SELECT phan_khuc, COUNT(*) cnt FROM customers GROUP BY phan_khuc").fetchall()
        if seg:
            fig2 = go.Figure(go.Pie(
                labels=[r["phan_khuc"] for r in seg],
                values=[r["cnt"] for r in seg], hole=.58,
                marker=dict(colors=["#16a34a","#2563eb","#d97706"],line=dict(color="white",width=3)),
                textinfo="label+percent", textfont=dict(size=11),
            ))
            fig2.add_annotation(text=f"<b>{total_kh}</b><br>KH",x=.5,y=.5,
                                font=dict(size=16,color="#0f172a"),showarrow=False)
            fig2.update_layout(height=240, paper_bgcolor="white", showlegend=False,
                title=dict(text="Phân Khúc KH",font=dict(size=13,color="#0f172a")),
                margin=dict(l=10,r=10,t=36,b=10), font=dict(family="Inter"))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    # Bottom row
    col_a, col_b, col_c = st.columns([2,2,1])
    with col_a:
        jobs_today = [dict(j) for j in conn.execute("""
            SELECT s.ma_kh, c.ten_cty, s.gio_bat_dau, s.gio_ket_thuc, s.trang_thai,
                   s.ky_thang, s.lan_thu,
                   (CASE WHEN s.gio_ket_thuc < s.gio_bat_dau THEN 1 ELSE 0 END) is_night
            FROM schedules s JOIN customers c ON s.ma_kh=c.ma_kh
            WHERE s.ngay_du_kien=? ORDER BY s.gio_bat_dau
        """, (today_str,)).fetchall()]

        st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">📅 Ca Thi Công Hôm Nay</div>', unsafe_allow_html=True)
        if jobs_today:
            for j in jobs_today:
                sc = {"completed":"#16a34a","scheduled":"#2563eb","skipped":"#94a3b8"}.get(j["trang_thai"],"#94a3b8")
                night = " 🌙" if j["is_night"] else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{j['ten_cty']}{night}</div>
                    <div style="font-size:11px;color:#94a3b8;">Lần {j['lan_thu']} · {j['gio_bat_dau']}–{j['gio_ket_thuc']}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">✨ Không có ca nào hôm nay</div>', unsafe_allow_html=True)
            
        st.markdown("<hr style='margin:12px 0; border:0; border-top:1px solid #f1f5f9;'>", unsafe_allow_html=True)
        def goto_logbook():
            st.session_state.topnav = "📓 Work Log"
        st.button("👉 Đi tới Work Log", type="primary", use_container_width=True, on_click=goto_logbook)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        expiring = conn.execute("""
            SELECT ct.ma_hd, ct.ngay_het_han, c.ten_cty,
                   CAST(julianday(ct.ngay_het_han)-julianday('now') AS INT) days_left
            FROM contracts ct JOIN customers c ON ct.ma_kh=c.ma_kh
            WHERE ct.ngay_het_han <= date('now','+30 days') AND ct.trang_thai='active'
            ORDER BY ct.ngay_het_han LIMIT 5
        """).fetchall()
        st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">⚠️ HĐ Sắp Hết Hạn</div>', unsafe_allow_html=True)
        if expiring:
            for e in expiring:
                d  = e["days_left"]
                sc = "#dc2626" if d<=0 else "#d97706" if d<=15 else "#16a34a"
                lbl= "HẾT HẠN" if d<=0 else f"còn {d}n"
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{e['ten_cty']}</div>
                    <div style="font-size:11px;color:#94a3b8;">{e['ma_hd']} · {e['ngay_het_han']}</div>
                  </div>
                  <span style="font-size:11px;font-weight:700;color:{sc};">{lbl}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">✓ Tất cả HĐ ổn</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c:
        overdue = conn.execute("SELECT COUNT(*) FROM schedules WHERE trang_thai='skipped'").fetchone()[0]
        kh_no   = conn.execute("SELECT COUNT(DISTINCT ma_kh) FROM debts WHERE can_thu>da_thu").fetchone()[0]
        rate    = int(ca_done/max(ca_done+ca_hom_nay,1)*100)
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;"><i class=\"ph-chart-line-up\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Nhanh</div>
          {stat_row("Ca bỏ qua",f'<b style="color:#dc2626">{overdue}</b>')}
          {stat_row("KH còn nợ",f'<b style="color:#d97706">{kh_no}</b>')}
          {stat_row("Tỷ lệ HT",f'<b style="color:#16a34a">{rate}%</b>')}
          {stat_row("Thu tháng này",f'<b>{format_money(da_thu_thang)}</b>')}
        </div>
        """, unsafe_allow_html=True)
    conn.close()

elif page == "👥 Khách Hàng":
    from pages import p1_customers; p1_customers.render()
elif page == "📄 Hợp Đồng":
    from pages import p2_contracts; p2_contracts.render()
elif page == "📅 Lịch Thi Công":
    from pages import p3_scheduling; p3_scheduling.render()
elif page == "📓 Work Log":
    from pages import p4_logbook; p4_logbook.render()
elif page == "💰 Công Nợ":
    from pages import p6_debts; p6_debts.render()
elif page == "🖨️ Xuất PDF":
    from pages import p5_pdf; p5_pdf.render()
elif page == "⚙️ Cài đặt":
    st.markdown("### 🔧 Cài đặt hệ thống")
    
    t1, t2, t3 = st.tabs(["🔒 Bảo mật & Tài khoản", "👷 Quản lý Kỹ Thuật Viên", "📅 Đồng bộ Google Calendar"])
    
    with t1:
        st.markdown("Quản lý tài khoản và bảo mật.")
        st.divider()
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("**🔑 Đổi mã PIN**")
            with st.form("form_change_pin"):
                old_pin = st.text_input("PIN hiện tại", type="password", max_chars=6, placeholder="••••••")
                new_pin = st.text_input("PIN mới", type="password", max_chars=6, placeholder="••••••")
                new_pin2 = st.text_input("Nhập lại PIN mới", type="password", max_chars=6, placeholder="••••••")
                if st.form_submit_button("💾 Lưu PIN mới", use_container_width=True):
                    if not _verify_pin(old_pin):
                        st.error("× PIN hiện tại không đúng!")
                    elif len(new_pin) < 4:
                        st.error("× PIN mới phải có ít nhất 4 ký tự!")
                    elif new_pin != new_pin2:
                        st.error("× PIN mới không khớp!")
                    else:
                        _change_pin(new_pin)
                        st.success("✓ Đã đổi PIN thành công!")
                        
        with col2:
            st.markdown("**🚪 Tài khoản**")
            if st.button("Đăng xuất khỏi hệ thống", type="primary"):
                st.session_state.authenticated = False
                st.session_state.auth_role = None
                st.rerun()
                
            st.markdown("<br>**💾 Sao lưu CSDL**", unsafe_allow_html=True)
            st.info("Trích xuất và tải toàn bộ CSDL (kể cả từ Turso) thành file SQLite.")
            if st.button("📦 Tạo File Sao Lưu (.db)", use_container_width=True):
                with st.spinner("Đang trích xuất dữ liệu, vui lòng chờ..."):
                    import sqlite3, os, tempfile
                    try:
                        conn_src = get_connection()
                        tables = conn_src.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                        
                        fd, path = tempfile.mkstemp(suffix=".db")
                        os.close(fd)
                        if os.path.exists(path):
                            os.remove(path)
                            
                        local_conn = sqlite3.connect(path)
                        for t in tables:
                            tname = t['name']
                            sql = t['sql']
                            if sql:
                                local_conn.execute(sql)
                                
                            rows = conn_src.execute(f"SELECT * FROM {tname}").fetchall()
                            if rows:
                                cols = rows[0].keys() if hasattr(rows[0], 'keys') else rows[0]._mapping.keys()
                                placeholders = ','.join(['?' for _ in cols])
                                col_names = ','.join(cols)
                                insert_sql = f"INSERT INTO {tname} ({col_names}) VALUES ({placeholders})"
                                for row in rows:
                                    local_conn.execute(insert_sql, tuple(row[c] for c in cols))
                        local_conn.commit()
                        local_conn.close()
                        conn_src.close()
                        
                        with open(path, "rb") as f:
                            db_bytes = f.read()
                        
                        st.session_state.backup_bytes = db_bytes
                        st.success("✓ Tạo file sao lưu thành công!")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                        
            if "backup_bytes" in st.session_state:
                st.download_button(
                    label="⬇️ Tải xuống VHSCRM_Backup.db",
                    data=st.session_state.backup_bytes,
                    file_name=f"vhscrm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                    mime="application/octet-stream",
                    type="primary",
                    use_container_width=True
                )
                
            st.markdown("<hr style='margin:16px 0; border:0; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
            st.markdown("**🔄 Khôi phục CSDL**")
            uploaded_db = st.file_uploader("Tải lên file VHSCRM_Backup.db", type=["db", "sqlite"])
            if uploaded_db is not None:
                st.warning("! **CẢNH BÁO:** Quá trình này sẽ XÓA TOÀN BỘ dữ liệu hiện tại và thay thế bằng dữ liệu từ file tải lên. Hãy chắc chắn bạn đã sao lưu trước khi thực hiện!")
                if st.button("🚀 Thực hiện Khôi Phục", type="primary", use_container_width=True):
                    with st.spinner("Đang khôi phục dữ liệu..."):
                        import tempfile, sqlite3, os
                        try:
                            # 1. Lưu file upload ra ổ đĩa
                            fd, path = tempfile.mkstemp(suffix=".db")
                            os.close(fd)
                            with open(path, "wb") as f:
                                f.write(uploaded_db.getvalue())
                                
                            # 2. Đọc file SQLite
                            conn_src = sqlite3.connect(path)
                            conn_src.row_factory = sqlite3.Row
                            tables = conn_src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                            
                            # 3. Ghi đè vào DB hiện tại (Turso hoặc local)
                            conn_dest = get_connection()
                            
                            # Xóa dữ liệu cũ
                            tables_to_clear = ['logbook', 'expenses', 'invoices', 'debts', 'schedules', 'contracts', 'customers', 'technicians', 'settings', 'app_settings']
                            for t in tables_to_clear:
                                try:
                                    conn_dest.execute(f"DELETE FROM {t}")
                                except Exception:
                                    pass
                            
                            for t in tables:
                                tname = t['name']
                                rows = conn_src.execute(f"SELECT * FROM {tname}").fetchall()
                                if rows:
                                    cols = list(rows[0].keys())
                                    placeholders = ','.join(['?' for _ in cols])
                                    col_names = ','.join(cols)
                                    insert_sql = f"INSERT INTO {tname} ({col_names}) VALUES ({placeholders})"
                                    for row in rows:
                                        conn_dest.execute(insert_sql, tuple(row[c] for c in cols))
                            
                            conn_dest.commit()
                            conn_dest.close()
                            conn_src.close()
                            os.remove(path)
                            st.success("✓ Đã khôi phục dữ liệu thành công!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khôi phục: {e}")

    with t2:
        from pages import p7_technicians; p7_technicians.render()
        
    with t3:
        st.markdown('<div class="vhs-card">', unsafe_allow_html=True)
        st.markdown("### Cấu hình Google Calendar & Maps API")
        st.info("Nhập các thông tin xác thực từ Google Cloud Console để đồng bộ lịch và vẽ bản đồ.")
        
        conn = get_connection()
        settings_rows = conn.execute("SELECT key_name, value_data FROM settings WHERE key_name IN ('google_client_id', 'google_client_secret')").fetchall()
        settings_dict = {r['key_name']: r['value_data'] for r in settings_rows}
        
        import os
        from dotenv import load_dotenv, set_key
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path=env_path)
        env_maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        
        with st.form("form_google_settings"):
            client_id = st.text_input("Calendar Client ID", value=settings_dict.get('google_client_id', ''))
            client_secret = st.text_input("Calendar Client Secret", value=settings_dict.get('google_client_secret', ''), type="password")
            maps_api_key = st.text_input("Maps API Key (saved in .env)", value=env_maps_key)
            
            if st.form_submit_button("💾 Lưu Cấu Hình", type="primary"):
                conn_save = get_connection()
                conn_save.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_client_id'), 'google_client_id', ?)", (client_id,))
                conn_save.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_client_secret'), 'google_client_secret', ?)", (client_secret,))
                conn_save.commit()
                conn_save.close()
                
                # Update .env
                if not os.path.exists(env_path):
                    with open(env_path, "w") as f: f.write("")
                set_key(env_path, "GOOGLE_MAPS_API_KEY", maps_api_key)
                
                st.success("Đã lưu cấu hình Google API!")
                st.rerun()
                
        # --- Google Auth Flow ---
        st.markdown("<hr style='margin:16px 0; border:0; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown("### 🔑 Đăng nhập Google (Calendar & Drive)")
        
        from utils.google_sync import get_cached_credentials, initiate_device_flow, complete_device_flow
        import json
        
        client_id_val = settings_dict.get('google_client_id')
        client_secret_val = settings_dict.get('google_client_secret')
        cache_str = settings_dict.get("google_token_cache")
        
        if not client_id_val or not client_secret_val:
            st.warning("Vui lòng lưu Client ID và Client Secret ở trên trước khi đăng nhập.")
        else:
            creds, new_cache = get_cached_credentials(client_id_val, client_secret_val, cache_str)
            if new_cache and new_cache != cache_str:
                conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_token_cache'), 'google_token_cache', ?)", (new_cache,))
                conn.commit()
                
            if creds and creds.valid:
                st.success("✓ Đã kết nối với tài khoản Google thành công!")
                if st.button("🔌 Đăng xuất (Xóa token)"):
                    conn.execute("DELETE FROM settings WHERE key_name='google_token_cache'")
                    conn.commit()
                    st.rerun()
            else:
                if "gg_flow_data" not in st.session_state:
                    st.session_state.gg_flow_data = None
                
                if st.session_state.gg_flow_data is None:
                    if st.button("🔌 Lấy mã đăng nhập Google", type="primary"):
                        with st.spinner("Đang kết nối..."):
                            flow, err_msg = initiate_device_flow(client_id_val.strip())
                            if flow and "verification_url" in flow:
                                st.session_state.gg_flow_data = flow
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {err_msg}")
                
                if st.session_state.gg_flow_data:
                    flow = st.session_state.gg_flow_data
                    st.info("Thực hiện theo các bước sau để đăng nhập:")
                    st.markdown(f"**Bước 1:** Mở link này: {flow['verification_url']}")
                    st.markdown(f"**Bước 2:** Nhập mã code: **{flow['user_code']}**")
                    st.markdown("**Bước 3:** Cho phép truy cập Calendar và Drive.")
                    if st.button("🔒 Đã hoàn tất đăng nhập trên web", type="primary"):
                        with st.spinner("Đang xác nhận..."):
                            token_data, err_msg = complete_device_flow(client_id_val.strip(), client_secret_val.strip(), flow['device_code'])
                            if token_data and 'access_token' in token_data:
                                conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_token_cache'), 'google_token_cache', ?)", (json.dumps(token_data),))
                                conn.commit()
                                st.session_state.gg_flow_data = None
                                st.success("🎉 Đăng nhập thành công!")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {err_msg}")
                    
        conn.close()
        st.markdown("</div>", unsafe_allow_html=True)
