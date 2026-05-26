from zoneinfo import ZoneInfo
# app.py ΓÇö VHS CRM v4 ΓÇö Top navbar layout
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.database import init_db, seed_demo_data, get_connection
from utils.styles import GLOBAL_CSS, card, badge, section_header, stat_row, COLORS
from datetime import timezone, datetime, date, timedelta
import plotly.graph_objects as go

st.set_page_config(
    page_title="VHS CRM", page_icon="≡ƒÉ¢",
    layout="wide", initial_sidebar_state="collapsed"
)
init_db()
seed_demo_data()

# Tß╗▒ ─æß╗Öng sinh lß╗ïch cho 2 th├íng tß╗¢i cho c├íc kh├ích ─æß╗ïnh kß╗│
if "auto_scheduled" not in st.session_state:
    from utils.scheduling import auto_generate_all_future_schedules
    auto_generate_all_future_schedules(months=2)
    st.session_state.auto_scheduled = True

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ============================================================
# TOP NAVBAR
# ============================================================
now  = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
conn = get_connection()
today_str   = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().strftime("%Y-%m-%d")
ca_hom_nay  = conn.execute(
    "SELECT COUNT(*) FROM schedules WHERE ngay_du_kien=? AND trang_thai='scheduled'",
    (today_str,)
).fetchone()[0]
tong_no     = conn.execute(
    "SELECT COALESCE(SUM(can_thu-da_thu),0) FROM debts WHERE can_thu>da_thu"
).fetchone()[0]
conn.close()

# Brand + status HTML
st.markdown(f"""
<div class="vhs-nav">
  <div class="vhs-nav-brand">
    <div class="vhs-nav-brand-icon">≡ƒÉ¢</div>
    <div>
      <div class="vhs-nav-brand-text">VHS CRM</div>
      <div class="vhs-nav-brand-sub">Pest Control v4</div>
    </div>
  </div>
  <!-- nav items rendered by st.radio below -->
  <div style="flex:1;display:flex;align-items:center;" id="vhs-nav-items"></div>
  <div class="vhs-status">
    <div class="vhs-status-pill">≡ƒöº <b>{ca_hom_nay}</b> ca h├┤m nay</div>
    <div class="vhs-status-pill">ΓÜá∩╕Å Nß╗ú <b>{tong_no/1e6:.1f}M</b></div>
    <div class="vhs-status-pill">≡ƒòÉ <b>{now.strftime('%H:%M')}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

# Radio nav ΓÇö nß║▒m trong mß╗Öt container ─æß║╖c biß╗çt ─æ╞░ß╗úc CSS h├│a th├ánh horizontal nav
NAV_ITEMS = [
    "≡ƒÅá Dashboard",
    "≡ƒæÑ Kh├ích H├áng",
    "≡ƒôä Hß╗úp ─Éß╗ông",
    "≡ƒôà Lß╗ïch Thi C├┤ng",
    "≡ƒô▒ Logbook",
    "≡ƒû¿∩╕Å Xuß║Ñt PDF",
    "≡ƒÆ░ C├┤ng Nß╗ú",
    "≡ƒæ╖ Kß╗╣ Thuß║¡t Vi├¬n",
    "≡ƒô▓ App KTV (Mobile)",
]

# ─Éß║╖t radio ngay d╞░ß╗¢i navbar (CSS sß║╜ position n├│ b├¬n trong navbar)
st.markdown('<div style="background:#0f172a;padding:0 24px 0 180px;margin-top:-74px;margin-bottom:20px;">', unsafe_allow_html=True)
page = st.radio("nav", NAV_ITEMS, horizontal=True, label_visibility="collapsed",
                key="topnav")
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================
if page == "≡ƒÅá Dashboard":
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
          <div style="font-size:22px;font-weight:800;color:white;">Tß╗òng quan hß╗ç thß╗æng VHS</div>
          <div style="font-size:13px;color:#86efac;margin-top:3px;">{now.strftime('%A, %d/%m/%Y ΓÇö %H:%M')}</div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:white;">{ca_hom_nay}</div>
            <div style="font-size:11px;color:#bbf7d0;">Ca h├┤m nay</div>
          </div>
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:#fbbf24;">{sap_het_han}</div>
            <div style="font-size:11px;color:#bbf7d0;">H─É sß║»p hß║┐t hß║ín</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("≡ƒæÑ Kh├ích H├áng",    total_kh)
    with c2: st.metric("≡ƒôä H─É Active",      total_hd)
    with c3: st.metric("≡ƒÆ╡ Doanh Thu/Th├íng",f"{doanh_thu/1e6:.1f}M ─æ")
    with c4: st.metric("Γ£à Ca Ho├án Th├ánh",  ca_done)
    with c5: st.metric("ΓÜá∩╕Å C├┤ng Nß╗ú",        f"{tong_no/1e6:.1f}M ─æ")

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
                            name="Cß║ºn Thu", line=dict(color="#e2e8f0",width=3),
                            fill="tozeroy", fillcolor="rgba(226,232,240,.3)")
            fig.add_scatter(x=[r["ky_thanh_toan"] for r in monthly],
                            y=[r["dt"]/1e6 for r in monthly],
                            name="─É├ú Thu", line=dict(color="#16a34a",width=3),
                            fill="tozeroy", fillcolor="rgba(22,163,74,.15)",
                            mode="lines+markers", marker=dict(size=6,color="#16a34a"))
            fig.update_layout(height=240, paper_bgcolor="white", plot_bgcolor="white",
                title=dict(text="Doanh Thu 6 Th├íng (triß╗çu ─æ)",font=dict(size=13,color="#0f172a")),
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
                title=dict(text="Ph├ón Kh├║c KH",font=dict(size=13,color="#0f172a")),
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
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">≡ƒôà Ca Thi C├┤ng H├┤m Nay</div>', unsafe_allow_html=True)
        if jobs_today:
            for j in jobs_today:
                sc = {"completed":"#16a34a","scheduled":"#2563eb","skipped":"#94a3b8"}.get(j["trang_thai"],"#94a3b8")
                night = " ≡ƒîÖ" if j["is_night"] else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{j['ten_cty']}{night}</div>
                    <div style="font-size:11px;color:#94a3b8;">Lß║ºn {j['lan_thu']} ┬╖ {j['gio_bat_dau']}ΓÇô{j['gio_ket_thuc']}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">Γ£¿ Kh├┤ng c├│ ca n├áo h├┤m nay</div>', unsafe_allow_html=True)
            
        st.markdown("<hr style='margin:12px 0; border:0; border-top:1px solid #f1f5f9;'>", unsafe_allow_html=True)
        if st.button("Γ₧í∩╕Å ─Éi tß╗¢i Sß╗ò Nhß║¡t K├╜ (Logbook)", use_container_width=True):
            st.session_state.nav_radio = "≡ƒô▒ Logbook"
            st.rerun()
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
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">ΓÜá∩╕Å H─É Sß║»p Hß║┐t Hß║ín</div>', unsafe_allow_html=True)
        if expiring:
            for e in expiring:
                d  = e["days_left"]
                sc = "#dc2626" if d<=0 else "#d97706" if d<=15 else "#16a34a"
                lbl= "Hß║╛T Hß║áN" if d<=0 else f"c├▓n {d}n"
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{e['ten_cty']}</div>
                    <div style="font-size:11px;color:#94a3b8;">{e['ma_hd']} ┬╖ {e['ngay_het_han']}</div>
                  </div>
                  <span style="font-size:11px;font-weight:700;color:{sc};">{lbl}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">Γ£à Tß║Ñt cß║ú H─É ß╗òn</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c:
        overdue = conn.execute("SELECT COUNT(*) FROM schedules WHERE trang_thai='skipped'").fetchone()[0]
        kh_no   = conn.execute("SELECT COUNT(DISTINCT ma_kh) FROM debts WHERE can_thu>da_thu").fetchone()[0]
        rate    = int(ca_done/max(ca_done+ca_hom_nay,1)*100)
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;">≡ƒôê Nhanh</div>
          {stat_row("Ca bß╗Å qua",f'<b style="color:#dc2626">{overdue}</b>')}
          {stat_row("KH c├▓n nß╗ú",f'<b style="color:#d97706">{kh_no}</b>')}
          {stat_row("Tß╗╖ lß╗ç HT",f'<b style="color:#16a34a">{rate}%</b>')}
          {stat_row("Thu th├íng n├áy",f'<b>{da_thu_thang/1e6:.1f}M</b>')}
        </div>
        """, unsafe_allow_html=True)
    conn.close()

elif page == "≡ƒæÑ Kh├ích H├áng":
    from pages import p1_customers; p1_customers.render()
elif page == "≡ƒôä Hß╗úp ─Éß╗ông":
    from pages import p2_contracts; p2_contracts.render()
elif page == "≡ƒôà Lß╗ïch Thi C├┤ng":
    from pages import p3_scheduling; p3_scheduling.render()
elif page == "≡ƒô▒ Logbook":
    from pages import p4_logbook; p4_logbook.render()
elif page == "≡ƒû¿∩╕Å Xuß║Ñt PDF":
    from pages import p5_pdf; p5_pdf.render()
elif page == "≡ƒÆ░ C├┤ng Nß╗ú":
    from pages import p6_debts; p6_debts.render()
elif page == "≡ƒæ╖ Kß╗╣ Thuß║¡t Vi├¬n":
    from pages import p7_technicians; p7_technicians.render()
elif page == "≡ƒô▓ App KTV (Mobile)":
    from pages import p7_mobile_ktv; p7_mobile_ktv.render()
