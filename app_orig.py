# app.py G«ˆ VHS CRM v4 G«ˆ Top navbar layout
import streamlit as st
import sys, os


from utils.database import init_db, seed_demo_data, get_connection
from utils.styles import GLOBAL_CSS, card, badge, section_header, stat_row, COLORS
from datetime import timezone, datetime, date, timedelta
import plotly.graph_objects as go
import streamlit.components.v1 as components

st.set_page_config(
    page_title="VHS CRM", page_icon="=É…¢",
    layout="wide", initial_sidebar_state="collapsed"
)
init_db()
seed_demo_data()

# Tﬂ+¶ -Êﬂ+÷ng sinh lﬂ+Ôch cho 2 th+Ìng tﬂ+¢i cho c+Ìc kh+Ìch -Êﬂ+Ônh kﬂ+¶
if "auto_scheduled" not in st.session_state:
    from utils.scheduling import auto_generate_all_future_schedules
    auto_generate_all_future_schedules(months=2)
    st.session_state.auto_scheduled = True

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def inject_countdown_banner(conn):
    try:
        now_vn = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
        today_str = now_vn.strftime('%Y-%m-%d')
        tomorrow_str = (now_vn + timedelta(days=1)).strftime('%Y-%m-%d')
        
        jobs = conn.execute('''
            SELECT s.ngay_du_kien, s.gio_bat_dau, c.ten_cty
            FROM schedules s JOIN customers c ON s.ma_kh = c.ma_kh
            WHERE s.trang_thai = 'scheduled' 
              AND s.ngay_du_kien IN (?, ?)
        ''', (today_str, tomorrow_str)).fetchall()
        
        upcoming = []
        for j in jobs:
            try:
                job_dt_str = f"{j['ngay_du_kien']} {j['gio_bat_dau']}"
                job_dt = datetime.strptime(job_dt_str, '%Y-%m-%d %H:%M')
                job_dt = job_dt.replace(tzinfo=timezone(timedelta(hours=7)))
                delta = (job_dt - now_vn).total_seconds()
                
                # Trong v+¶ng 6 tiﬂ¶+ng (21600 gi+Ûy)
                if 0 < delta <= 21600:
                    upcoming.append({
                        "ten_cty": j['ten_cty'],
                        "gio_bat_dau": j['gio_bat_dau'],
                        "timestamp": job_dt.timestamp() * 1000 # JS uses milliseconds
                    })
            except Exception:
                pass
                
        if upcoming:
            upcoming.sort(key=lambda x: x["timestamp"])
            best = upcoming[0]
            
            js_code = f"""
            <script>
            (function() {{
                const targetTime = {best['timestamp']};
                const cty = "{best['ten_cty']}";
                const gio = "{best['gio_bat_dau']}";
                
                const parentDoc = window.parent.document;
                let banner = parentDoc.getElementById("vhs-countdown-banner");
                
                if (!banner) {{
                    banner = parentDoc.createElement("div");
                    banner.id = "vhs-countdown-banner";
                    banner.style.position = "fixed";
                    banner.style.top = "15px";
                    banner.style.left = "50%";
                    banner.style.transform = "translateX(-50%)";
                    banner.style.zIndex = "999999";
                    banner.style.backgroundColor = "#fff";
                    banner.style.border = "1px solid #e2e8f0";
                    banner.style.borderLeft = "5px solid #f59e0b";
                    banner.style.borderRadius = "12px";
                    banner.style.padding = "10px 16px";
                    banner.style.boxShadow = "0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)";
                    banner.style.width = "90%";
                    banner.style.maxWidth = "350px";
                    banner.style.fontFamily = "Inter, sans-serif";
                    banner.style.display = "flex";
                    banner.style.flexDirection = "column";
                    banner.style.alignItems = "center";
                    banner.style.cursor = "pointer";
                    
                    banner.onclick = function() {{ banner.style.display = "none"; }};
                    parentDoc.body.appendChild(banner);
                }}
                
                const updateTimer = () => {{
                    const now = new Date().getTime();
                    const distance = targetTime - now;
                    
                    if (distance < 0) {{
                        banner.innerHTML = `<div style="font-size:12px;color:#475569;font-weight:600;margin-bottom:2px;">=É‹ø -…+˙ -Êﬂ¶+n giﬂ+• thi c+¶ng:</div>
                                            <div style="font-size:14px;color:#0f172a;font-weight:800;">${{cty}} (${{gio}})</div>`;
                        return;
                    }}
                    
                    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    
                    let timeStr = "";
                    if (hours > 0) timeStr += hours + "h ";
                    timeStr += minutes + "m " + seconds + "s";
                    
                    banner.innerHTML = `
                        <div style="font-size:11px;color:#64748b;font-weight:600;margin-bottom:2px;text-transform:uppercase;letter-spacing:0.5px;">Sﬂ¶ªp tﬂ+¢i ca thi c+¶ng (nhﬂ¶—n -Êﬂ+‚ ﬂ¶¨n)</div>
                        <div style="font-size:14px;color:#0f172a;font-weight:800;margin-bottom:2px;text-align:center;">${{cty}}</div>
                        <div style="font-size:24px;color:#f59e0b;font-weight:900;letter-spacing:1px;font-variant-numeric:tabular-nums;">${{timeStr}}</div>
                    `;
                }};
                
                updateTimer();
                setInterval(updateTimer, 1000);
            }})();
            </script>
            """
            components.html(js_code, height=0, width=0)
    except Exception as e:
        pass

conn_main = get_connection()
inject_countdown_banner(conn_main)
conn_main.close()

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
    <div class="vhs-nav-brand-icon">=É…¢</div>
    <div>
      <div class="vhs-nav-brand-text">VHS CRM</div>
      <div class="vhs-nav-brand-sub">Pest Control v4</div>
    </div>
  </div>
  <!-- nav items rendered by st.radio below -->
  <div style="flex:1;display:flex;align-items:center;" id="vhs-nav-items"></div>
  <div class="vhs-status">
    <div class="vhs-status-pill">=Éˆ∫ <b>{ca_hom_nay}</b> ca h+¶m nay</div>
    <div class="vhs-status-pill">G‹·n+≈ Nﬂ+˙ <b>{tong_no/1e6:.1f}M</b></div>
    <div class="vhs-status-pill">=ÉÚ… <b>{now.strftime('%H:%M')}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

# Radio nav G«ˆ nﬂ¶¶m trong mﬂ+÷t container -Êﬂ¶+c biﬂ+Át -Ê¶¶ﬂ+˙c CSS h+¶a th+·nh horizontal nav
NAV_ITEMS = [
    "=É≈· Tﬂ+Úng",
    "=ÉÊ— Kh+Ìch",
    "=ÉÙ‰ H-…",
    "=ÉÙ‡ Lﬂ+Ôch",
    "=ÉÙ¶ Logbook",
    "G‹÷n+≈ Menu"
]

# -…ﬂ¶+t radio ngay d¶¶ﬂ+¢i navbar (CSS sﬂ¶+ position n+¶ b+¨n trong navbar tr+¨n Desktop, v+· ﬂ+É bottom tr+¨n Mobile)
st.markdown('<div class="vhs-nav-radio-container">', unsafe_allow_html=True)
page = st.radio("nav", NAV_ITEMS, horizontal=True, label_visibility="collapsed", key="topnav")
st.markdown("</div>", unsafe_allow_html=True)

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
if page == "=É≈· Tﬂ+Úng":
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
          <div style="font-size:22px;font-weight:800;color:white;">Tﬂ+Úng quan hﬂ+Á thﬂ+Êng VHS</div>
          <div style="font-size:13px;color:#86efac;margin-top:3px;">{now.strftime('%A, %d/%m/%Y G«ˆ %H:%M')}</div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:white;">{ca_hom_nay}</div>
            <div style="font-size:11px;color:#bbf7d0;">Ca h+¶m nay</div>
          </div>
          <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:10px 18px;text-align:center;">
            <div style="font-size:22px;font-weight:800;color:#fbbf24;">{sap_het_han}</div>
            <div style="font-size:11px;color:#bbf7d0;">H-… sﬂ¶ªp hﬂ¶+t hﬂ¶Ìn</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("=ÉÊ— Kh+Ìch H+·ng",    total_kh)
    with c2: st.metric("=ÉÙ‰ H-… Active",      total_hd)
    with c3: st.metric("=É∆¶ Doanh Thu/Th+Ìng",f"{doanh_thu/1e6:.1f}M -Ê")
    with c4: st.metric("G£‡ Ca Ho+·n Th+·nh",  ca_done)
    with c5: st.metric("G‹·n+≈ C+¶ng Nﬂ+˙",        f"{tong_no/1e6:.1f}M -Ê")

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
                            name="Cﬂ¶∫n Thu", line=dict(color="#e2e8f0",width=3),
                            fill="tozeroy", fillcolor="rgba(226,232,240,.3)")
            fig.add_scatter(x=[r["ky_thanh_toan"] for r in monthly],
                            y=[r["dt"]/1e6 for r in monthly],
                            name="-…+˙ Thu", line=dict(color="#16a34a",width=3),
                            fill="tozeroy", fillcolor="rgba(22,163,74,.15)",
                            mode="lines+markers", marker=dict(size=6,color="#16a34a"))
            fig.update_layout(height=240, paper_bgcolor="white", plot_bgcolor="white",
                title=dict(text="Doanh Thu 6 Th+Ìng (triﬂ+Áu -Ê)",font=dict(size=13,color="#0f172a")),
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
                title=dict(text="Ph+Ûn Kh+¶c KH",font=dict(size=13,color="#0f172a")),
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
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">=ÉÙ‡ Ca Thi C+¶ng H+¶m Nay</div>', unsafe_allow_html=True)
        if jobs_today:
            for j in jobs_today:
                sc = {"completed":"#16a34a","scheduled":"#2563eb","skipped":"#94a3b8"}.get(j["trang_thai"],"#94a3b8")
                night = " =ÉÓ÷" if j["is_night"] else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{j['ten_cty']}{night}</div>
                    <div style="font-size:11px;color:#94a3b8;">Lﬂ¶∫n {j['lan_thu']} -+ {j['gio_bat_dau']}G«Ù{j['gio_ket_thuc']}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">G£ø Kh+¶ng c+¶ ca n+·o h+¶m nay</div>', unsafe_allow_html=True)
            
        st.markdown("<hr style='margin:12px 0; border:0; border-top:1px solid #f1f5f9;'>", unsafe_allow_html=True)
        if st.button("GPÌn+≈ -…i tﬂ+¢i Sﬂ+Ú Nhﬂ¶°t K++ (Logbook)", use_container_width=True):
            st.session_state.topnav = "=ÉÙ¶ Logbook"
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
        st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">G‹·n+≈ H-… Sﬂ¶ªp Hﬂ¶+t Hﬂ¶Ìn</div>', unsafe_allow_html=True)
        if expiring:
            for e in expiring:
                d  = e["days_left"]
                sc = "#dc2626" if d<=0 else "#d97706" if d<=15 else "#16a34a"
                lbl= "Hﬂ¶+T Hﬂ¶·N" if d<=0 else f"c+¶n {d}n"
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc;">
                  <div style="width:8px;height:8px;border-radius:50%;background:{sc};flex-shrink:0;"></div>
                  <div style="flex:1;">
                    <div style="font-size:13px;font-weight:600;color:#0f172a;">{e['ten_cty']}</div>
                    <div style="font-size:11px;color:#94a3b8;">{e['ma_hd']} -+ {e['ngay_het_han']}</div>
                  </div>
                  <span style="font-size:11px;font-weight:700;color:{sc};">{lbl}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:24px;color:#94a3b8;font-size:13px;">G£‡ Tﬂ¶—t cﬂ¶˙ H-… ﬂ+Ún</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c:
        overdue = conn.execute("SELECT COUNT(*) FROM schedules WHERE trang_thai='skipped'").fetchone()[0]
        kh_no   = conn.execute("SELECT COUNT(DISTINCT ma_kh) FROM debts WHERE can_thu>da_thu").fetchone()[0]
        rate    = int(ca_done/max(ca_done+ca_hom_nay,1)*100)
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,.04);">
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;">=ÉÙÍ Nhanh</div>
          {stat_row("Ca bﬂ+≈ qua",f'<b style="color:#dc2626">{overdue}</b>')}
          {stat_row("KH c+¶n nﬂ+˙",f'<b style="color:#d97706">{kh_no}</b>')}
          {stat_row("Tﬂ++ lﬂ+Á HT",f'<b style="color:#16a34a">{rate}%</b>')}
          {stat_row("Thu th+Ìng n+·y",f'<b>{da_thu_thang/1e6:.1f}M</b>')}
        </div>
        """, unsafe_allow_html=True)
    conn.close()

elif page == "=É≈· Tﬂ+Úng":
    pass # Already handled above as Dashboard
elif page == "=ÉÊ— Kh+Ìch":
    from pages import p1_customers; p1_customers.render()
elif page == "=ÉÙ‰ H-…":
    from pages import p2_contracts; p2_contracts.render()
elif page == "=ÉÙ‡ Lﬂ+Ôch":
    from pages import p3_scheduling; p3_scheduling.render()
elif page == "=ÉÙ¶ Logbook":
    from pages import p4_logbook; p4_logbook.render()
elif page == "G‹÷n+≈ Menu":
    if not st.session_state.current_subpage:
        st.markdown('<div style="padding:10px;font-size:20px;font-weight:800;color:#0f172a;margin-bottom:15px;">G‹÷n+≈ Menu ﬂ+øng Dﬂ+—ng</div>', unsafe_allow_html=True)
        
        m1, m2 = st.columns(2)
        with m1:
            if st.button("=É∆¶ C+¶ng Nﬂ+˙", use_container_width=True):
                st.session_state.current_subpage = "C+¶ng Nﬂ+˙"
                st.rerun()
            if st.button("=É˚øn+≈ Xuﬂ¶—t PDF", use_container_width=True):
                st.session_state.current_subpage = "Xuﬂ¶—t PDF"
                st.rerun()
        with m2:
            if st.button("=ÉÊ+ Kﬂ+¶ Thuﬂ¶°t Vi+¨n", use_container_width=True):
                st.session_state.current_subpage = "Kﬂ+¶ Thuﬂ¶°t Vi+¨n"
                st.rerun()
            if st.button("=ÉÙ¶ App KTV (Mobile)", use_container_width=True):
                st.session_state.current_subpage = "App KTV"
                st.rerun()
    else:
        st.markdown(f'<div style="margin-bottom:15px;">', unsafe_allow_html=True)
        if st.button("Gº‡n+≈ Quay lﬂ¶Ìi Menu", type="secondary"):
            st.session_state.current_subpage = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        sp = st.session_state.current_subpage
        if sp == "C+¶ng Nﬂ+˙": from pages import p6_debts; p6_debts.render()
        elif sp == "Xuﬂ¶—t PDF": from pages import p5_pdf; p5_pdf.render()
        elif sp == "Kﬂ+¶ Thuﬂ¶°t Vi+¨n": from pages import p7_technicians; p7_technicians.render()
        elif sp == "App KTV": from pages import p7_mobile_ktv; p7_mobile_ktv.render()
