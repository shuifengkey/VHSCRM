# app.py — VHS CRM v4 — Top navbar layout
import streamlit as st
import sys, os, hashlib, base64
sys.path.insert(0, os.path.dirname(__file__))

from utils.database import init_db, get_connection
from utils.styles import GLOBAL_CSS, card, badge, section_header, stat_row, COLORS
from datetime import timezone, datetime, date, timedelta
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Load logo
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")
with open(_LOGO_PATH, "rb") as _f:
    _LOGO_B64 = base64.b64encode(_f.read()).decode()
_LOGO_URI = f"data:image/png;base64,{_LOGO_B64}"

st.set_page_config(
    page_title="VHS CRM", page_icon=_LOGO_PATH,
    layout="wide", initial_sidebar_state="collapsed"
)
init_db()

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
/* Style the text input */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #f1f5f9 !important;
    border-radius: 14px !important;
    padding: 14px 18px !important;
    font-size: 20px !important;
    text-align: center !important;
    letter-spacing: 8px !important;
    font-weight: 700 !important;
}
.stTextInput > div > div > input::placeholder {
    color: #475569 !important;
    letter-spacing: 6px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #16a34a !important;
    box-shadow: 0 0 20px rgba(22,163,74,0.2) !important;
}
/* Style the button */
.stButton > button {
    background: linear-gradient(135deg, #16a34a, #15803d) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 14px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #22c55e, #16a34a) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(22,163,74,0.3) !important;
}
.stButton > button:active {
    transform: scale(0.98) !important;
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
</style>
<div style="animation:pinSlideIn 0.5s cubic-bezier(0.16,1,0.3,1);text-align:center;padding:20px 0 24px;">
    <img src="{_LOGO_URI}" style="width:90px;height:90px;margin:0 auto 20px;display:block;filter:drop-shadow(0 0 20px rgba(22,163,74,0.4));animation:pinPulse 2s infinite;" />
    <div style="font-size:26px;font-weight:800;color:#f8fafc;margin-bottom:6px;letter-spacing:-0.3px;">VHS CRM</div>
    <div style="font-size:13px;color:#64748b;margin-bottom:24px;">Nhập mã PIN để truy cập hệ thống</div>
    {error_html}
</div>
""", unsafe_allow_html=True)

    pin_val = st.text_input(
        "Nhập mã PIN",
        type="password",
        max_chars=6,
        key="pin_field",
        placeholder="••••••",
        label_visibility="collapsed"
    )
    if st.button("🔓 XÁC NHẬN", use_container_width=True, key="pin_submit"):
        if pin_val == "1710":
            st.session_state.authenticated = True
            st.session_state.auth_role = "ktv"
            st.session_state.pin_error = False
            st.session_state.pin_input = ""
            st.rerun()
        elif _verify_pin(pin_val):
            st.session_state.authenticated = True
            st.session_state.auth_role = "admin"
            st.session_state.pin_error = False
            st.session_state.pin_input = ""
            st.rerun()
        else:
            st.session_state.pin_error = True
            st.rerun()

    st.markdown("""
<div style="text-align:center;margin-top:32px;font-size:11px;color:#475569;">
    🛡️ Bảo mật bởi VHS CRM
</div>
""", unsafe_allow_html=True)

    st.stop()  # Block everything below until authenticated

# ============================================================
# AUTHENTICATED — MAIN APP
# ============================================================

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

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
      <div class="vhs-nav-brand-text">VHS CRM</div>
      <div class="vhs-nav-brand-sub">Pest Control v4</div>
    </div>
  </div>
  <!-- nav items rendered by st.radio below -->
  <div style="flex:1;display:flex;align-items:center;" id="vhs-nav-items"></div>
  <div class="vhs-status">
    <div class="vhs-status-pill">🔧 <b>{ca_hom_nay}</b> ca hôm nay</div>
    <div class="vhs-status-pill">⚠️ Nợ <b>{tong_no/1e6:.1f}M</b></div>
    <div class="vhs-status-pill">🕐 <b>{now.strftime('%H:%M')}</b></div>
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
          <div style="font-size:22px;font-weight:800;color:white;">Tổng quan hệ thống VHS</div>
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
    with c3: st.metric("💵 Doanh Thu/Tháng",f"{doanh_thu/1e6:.1f}M đ")
    with c4: st.metric("✅ Ca Hoàn Thành",  ca_done)
    with c5: st.metric("⚠️ Công Nợ",        f"{tong_no/1e6:.1f}M đ")

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
                            y=[r["ct"]/1e6 for r in monthly],
                            name="Cần Thu", line=dict(color="#e2e8f0",width=3),
                            fill="tozeroy", fillcolor="rgba(226,232,240,.3)")
            fig.add_scatter(x=[r["ky_thanh_toan"] for r in monthly],
                            y=[r["dt"]/1e6 for r in monthly],
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
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">✅ Tất cả HĐ ổn</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c:
        overdue = conn.execute("SELECT COUNT(*) FROM schedules WHERE trang_thai='skipped'").fetchone()[0]
        kh_no   = conn.execute("SELECT COUNT(DISTINCT ma_kh) FROM debts WHERE can_thu>da_thu").fetchone()[0]
        rate    = int(ca_done/max(ca_done+ca_hom_nay,1)*100)
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;">📈 Nhanh</div>
          {stat_row("Ca bỏ qua",f'<b style="color:#dc2626">{overdue}</b>')}
          {stat_row("KH còn nợ",f'<b style="color:#d97706">{kh_no}</b>')}
          {stat_row("Tỷ lệ HT",f'<b style="color:#16a34a">{rate}%</b>')}
          {stat_row("Thu tháng này",f'<b>{da_thu_thang/1e6:.1f}M</b>')}
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
                        st.error("❌ PIN hiện tại không đúng!")
                    elif len(new_pin) < 4:
                        st.error("❌ PIN mới phải có ít nhất 4 ký tự!")
                    elif new_pin != new_pin2:
                        st.error("❌ PIN mới không khớp!")
                    else:
                        _change_pin(new_pin)
                        st.success("✅ Đã đổi PIN thành công!")
                        
        with col2:
            st.markdown("**🚪 Tài khoản**")
            if st.button("Đăng xuất khỏi hệ thống", type="primary"):
                st.session_state.authenticated = False
                st.session_state.auth_role = None
                st.rerun()

    with t2:
        from pages import p7_technicians; p7_technicians.render()
        
    with t3:
        st.markdown('<div class="vhs-card">', unsafe_allow_html=True)
        st.markdown("### Cấu hình Google Calendar API")
        st.info("Nhập Client ID và Client Secret từ ứng dụng Google Cloud Console để đồng bộ lịch thi công sang Google Calendar.")
        
        conn = get_connection()
        settings_rows = conn.execute("SELECT key_name, value_data FROM settings WHERE key_name IN ('google_client_id', 'google_client_secret')").fetchall()
        settings_dict = {r['key_name']: r['value_data'] for r in settings_rows}
        
        with st.form("form_google_settings"):
            client_id = st.text_input("Client ID", value=settings_dict.get('google_client_id', ''))
            client_secret = st.text_input("Client Secret", value=settings_dict.get('google_client_secret', ''), type="password")
            
            if st.form_submit_button("💾 Lưu Cấu Hình", type="primary"):
                conn_save = get_connection()
                conn_save.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_client_id'), 'google_client_id', ?)", (client_id,))
                conn_save.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_client_secret'), 'google_client_secret', ?)", (client_secret,))
                conn_save.commit()
                conn_save.close()
                st.success("Đã lưu cấu hình Google Calendar!")
                st.rerun()
                
        conn.close()
        st.markdown("</div>", unsafe_allow_html=True)
