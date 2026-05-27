# pages/p3_scheduling.py — Lịch Thi Công v4
import streamlit as st, sys, os

from utils.database  import get_connection
from utils.scheduling import (auto_generate_schedules, calc_dates_for_month,
                               is_job_active_now, THU_NAMES)
from utils.styles    import section_header, badge, COLORS
from datetime import timezone, date, datetime, timedelta
import datetime as dt
import plotly.graph_objects as go
import calendar

ST_CLR = {"completed":"#16a34a","scheduled":"#2563eb","skipped":"#94a3b8"}
ST_LBL = {"completed":"Xong","scheduled":"Chờ TC","skipped":"Bỏ qua"}
TS_LABEL = {1:"1 Lần/tháng", 2:"2 Lần", 3:"3 Lần", 4:"4 Lần"}
THU_OPTS = {1:"Thứ 2",2:"Thứ 3",3:"Thứ 4",4:"Thứ 5",5:"Thứ 6",6:"Thứ 7",0:"Chủ Nhật"}

@st.dialog("🔄 Đồng bộ Google Calendar")
def google_sync_dialog(thang, nam):
    import json
    from utils.google_sync import get_cached_credentials, initiate_device_flow, complete_device_flow, push_event_to_google
    conn = get_connection()
    settings = dict(conn.execute("SELECT key_name, value_data FROM settings").fetchall())
    conn.close()
    
    client_id = settings.get("google_client_id")
    client_secret = settings.get("google_client_secret")
    cache_str = settings.get("google_token_cache")
    
    if not client_id or not client_secret:
        st.warning("⚠️ Chưa cấu hình Google Cloud App!")
        st.info("Vui lòng vào mục **Cài Đặt** để điền Client ID và Client Secret trước khi đồng bộ.")
        return
    
    # Thử load token đã lưu
    creds, new_cache = get_cached_credentials(client_id, client_secret, cache_str)
    if new_cache and new_cache != cache_str:
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_token_cache'), 'google_token_cache', ?)", (new_cache,))
        conn.commit(); conn.close()

    # Đã có token hợp lệ → hiện nút đồng bộ
    if creds and creds.valid:
        st.success("✅ Đã kết nối với Google Calendar!")
        st.markdown(f"Bạn đang chuẩn bị đồng bộ lịch thi công của **Tháng {thang}/{nam}** lên Google Calendar.")
        
        if st.button(f"🚀 Bắt đầu Đồng bộ Tháng {thang}", type="primary", use_container_width=True):
            with st.spinner("Đang đẩy dữ liệu sang Google Calendar..."):
                ky_str = f"{nam}-{thang:02d}"
                conn = get_connection()
                schedules = conn.execute('''
                    SELECT s.id
                    FROM schedules s
                    WHERE strftime('%Y-%m', s.ngay_du_kien) = ? AND s.trang_thai != 'skipped'
                ''', (ky_str,)).fetchall()
                
                success_count = 0
                from utils.google_sync import auto_sync_schedule_to_google
                for s in schedules:
                    ok, res = auto_sync_schedule_to_google(conn, s['id'], "upsert")
                    if ok: 
                        success_count += 1
                    else:
                        st.error(f"Lỗi khi đẩy lịch ID {s['id']}: {res}")
                conn.close()
                
                if success_count == len(schedules):
                    st.success(f"✅ Đã đồng bộ thành công {success_count}/{len(schedules)} sự kiện!")
                else:
                    st.warning(f"Đã đồng bộ {success_count}/{len(schedules)} sự kiện. (Có {len(schedules)-success_count} lỗi)")
                st.balloons()
        return

    # Chưa có token → bước đăng nhập
    # Bước 1: Lấy flow (không dùng session_state để tránh mất khi rerun)
    if "gg_flow_data" not in st.session_state:
        st.session_state.gg_flow_data = None

    st.markdown("### 🔑 Đăng nhập Google")

    if st.session_state.gg_flow_data is None:
        if st.button("🔌 Lấy mã đăng nhập Google", type="primary", use_container_width=True):
            with st.spinner("Đang kết nối với Google..."):
                flow, err_msg = initiate_device_flow(client_id.strip())
                if flow and "verification_url" in flow:
                    st.session_state.gg_flow_data = flow
                else:
                    st.error(f"❌ Không thể kết nối với Google. Lỗi: {err_msg}")
    
    if st.session_state.gg_flow_data:
        flow = st.session_state.gg_flow_data
        st.divider()
        st.markdown("**📋 Hướng dẫn đăng nhập:**")
        st.markdown(f"**Bước 1:** Mở link sau trên điện thoại hoặc máy tính:")
        st.code(flow['verification_url'], language=None)
        st.markdown(f"**Bước 2:** Nhập mã code:")
        st.code(flow['user_code'], language=None)
        st.markdown("**Bước 3:** Chọn tài khoản Google → Bấm Allow → Quay lại đây bấm nút bên dưới.")
        st.divider()
        
        if st.button("🔒 Tôi đã đăng nhập xong", type="primary", use_container_width=True):
            with st.spinner("Đang xác nhận..."):
                token_data, err_msg = complete_device_flow(client_id.strip(), client_secret.strip(), flow['device_code'])
                if token_data and 'access_token' in token_data:
                    new_cache = json.dumps(token_data)
                    conn = get_connection()
                    conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_token_cache'), 'google_token_cache', ?)", (new_cache,))
                    conn.commit(); conn.close()
                    st.session_state.gg_flow_data = None
                    st.success("🎉 Đăng nhập thành công! Vui lòng ĐÓNG và mở lại hộp thoại để đồng bộ.")
                    st.balloons()
                else:
                    st.error(f"❌ Chưa xác nhận được. Lỗi: {err_msg}")

def render():
    conn_t = get_connection()
    try:
        KTV_LIST = [r["ten"] for r in conn_t.execute("SELECT ten FROM technicians WHERE active=1 ORDER BY ten").fetchall()]
    except:
        KTV_LIST = []
    finally:
        conn_t.close()

    st.markdown("""
    <style>
    /* Add shift specific classes to override vhs-list-item without relying on inline !important which Streamlit strips */
    .vhs-list-item.shift-morning {
        background: #fffbeb !important;
        border-left: 5px solid #f59e0b !important;
        border-radius: 0 12px 12px 0 !important;
    }
    .vhs-list-item.shift-afternoon {
        background: #eff6ff !important;
        border-left: 5px solid #3b82f6 !important;
        border-radius: 0 12px 12px 0 !important;
    }
    .vhs-list-item.shift-night {
        background: #f5f3ff !important;
        border-left: 5px solid #8b5cf6 !important;
        border-radius: 0 12px 12px 0 !important;
    }
    .vhs-list-item.shift-overdue {
        background: #fef2f2 !important;
        border-left: 5px solid #dc2626 !important;
        border-radius: 0 12px 12px 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(section_header("Lịch Thi Công","Quản lý lịch — Điều chỉnh thủ công — Calendar view","📅"),
                unsafe_allow_html=True)

    tab_today, tab_month, tab_cal, tab_bulk = st.tabs([
        "🔥  Sắp Thi Công","📋  Theo Tháng / HĐ","📆  Calendar","⚙️  Hàng Loạt"
    ])

    # ═══════════════════════════════════
    # SẮP THI CÔNG (trong 24h tới) + Quá ca
    # ═══════════════════════════════════
    with tab_today:
        now      = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
        today    = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
        today_str = today.strftime("%Y-%m-%d")
        tom_str   = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        past3_str = (today - timedelta(days=3)).strftime("%Y-%m-%d")

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f172a,#166534);color:white;
                    padding:18px 22px;border-radius:14px;margin-bottom:18px;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
          <div>
            <div style="font-size:11px;color:#86efac;font-weight:700;letter-spacing:.08em;">KIỂM TRA LÚC</div>
            <div style="font-size:26px;font-weight:800;">{now.strftime('%H:%M:%S')}</div>
            <div style="font-size:13px;color:#86efac;">{today.strftime('%d/%m/%Y')}</div>
          </div>
          <div style="background:rgba(255,255,255,.1);border-radius:10px;padding:10px 14px;font-size:12px;color:#bbf7d0;text-align:center;">
            ⏰ Hiển thị ca trong 24h tới<br>+ ca chưa thi công (quá ca)
          </div>
        </div>
        """, unsafe_allow_html=True)

        conn = get_connection()
        raw = conn.execute("""
            SELECT s.*, c.ten_cty, c.dia_chi, c.sdt, ct.tan_suat, ct.kieu_lap, ct.lap_thu
            FROM schedules s
            JOIN customers c ON s.ma_kh=c.ma_kh
            JOIN contracts ct ON s.ma_hd=ct.ma_hd
            WHERE s.trang_thai!='completed' AND s.ngay_du_kien BETWEEN ? AND ?
            ORDER BY s.ngay_du_kien, s.gio_bat_dau
        """, (past3_str, tom_str)).fetchall()
        conn.close()

        # Phân loại: upcoming (trong 24h tới) vs overdue (quá ca chưa thi công)
        upcoming_jobs = []
        overdue_jobs = []
        for r in raw:
            j = dict(r)
            sch_date = date.fromisoformat(j["ngay_du_kien"])
            h_bd, m_bd = 8, 0
            try: h_bd, m_bd = map(int, (j["gio_bat_dau"] or "08:00").split(":"))
            except: pass
            start_dt = datetime(sch_date.year, sch_date.month, sch_date.day, h_bd, m_bd)
            diff_hours = (start_dt - now).total_seconds() / 3600

            if 0 <= diff_hours <= 24:
                upcoming_jobs.append(j)
            elif diff_hours < 0:
                overdue_jobs.append(j)
                
        def get_sort_key(job):
            d = job["ngay_du_kien"]
            h, m = 0, 0
            try: h, m = map(int, (job["gio_bat_dau"] or "00:00").split(":"))
            except: pass
            return (d, h, m)

        upcoming_jobs.sort(key=get_sort_key)
        overdue_jobs.sort(key=get_sort_key)

        if not upcoming_jobs and not overdue_jobs:
            st.markdown("""
            <div class="vhs-card" style="text-align:center;padding:56px;">
              <div style="font-size:52px;">✅</div>
              <div style="font-size:17px;font-weight:700;color:#0f172a;margin-top:10px;">Không có ca nào trong 24h tới!</div>
            </div>""", unsafe_allow_html=True)
        else:
            all_jobs = overdue_jobs + upcoming_jobs
            map_jobs = [j for j in all_jobs if j.get('dia_chi') and j['dia_chi'].strip()]
            col_list, col_map = st.columns([5, 4], gap='large')
            with col_list:
                # --- Overdue ---
                if overdue_jobs:
                    st.markdown(f'<div style="font-size:14px;font-weight:700;color:#dc2626;margin:12px 0 8px;">🚨 QUÁ CA — Chưa thi công ({len(overdue_jobs)} ca)</div>', unsafe_allow_html=True)
                    for j in overdue_jobs:
                        is_night = False
                        shift_class = "shift-overdue"
                        try: 
                            h_bd = int(j["gio_bat_dau"].split(":")[0])
                            is_night = int(j["gio_ket_thuc"].split(":")[0]) < h_bd
                        except: pass
    
                        st.markdown(f"""
    <div class="vhs-list-item {shift_class}">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>
    <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:4px;">
    {j['ten_cty']}
    <span style="background:#dc2626;color:white;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;margin-left:6px;">⚠️ QUÁ CA</span>
    {'<span style="background:#1e1b4b;color:#c4b5fd;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;margin-left:6px;">🌙 CA ĐÊM</span>' if is_night else ''}
    </div>
    <div style="font-size:12px;color:#64748b;line-height:2;">
    📋 <b>{j['ma_hd']}</b> · Kỳ <b>{j['ky_thang']}</b> · Lần <b>{j['lan_thu']}/{j['tan_suat']}</b><br>
    📅 <b>{j['ngay_du_kien']}</b> · ⏰ <b>{j['gio_bat_dau']} → {j['gio_ket_thuc']}</b>
    {'<br>📍 ' + j['dia_chi'] if j.get('dia_chi') else ''}
    {'<br>👷 KTV: ' + j['ky_thuat_vien'] if j.get('ky_thuat_vien') else '<br>👷 KTV: (Chưa gán)'}
    </div>
    </div>
    <div style="background:white;border-radius:8px;padding:8px 14px;text-align:center;border:1px solid #dc262630;">
    <div style="font-size:10px;color:#94a3b8;">TRẠNG THÁI</div>
    <div style="font-size:13px;font-weight:700;color:#dc2626;">⚠️ Quá ca</div>
    </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
    
                # --- Upcoming ---
                if upcoming_jobs:
                    st.markdown(f'<div style="font-size:14px;font-weight:700;color:#2563eb;margin:16px 0 8px;">🚀 Sắp thi công — trong 24h ({len(upcoming_jobs)} ca)</div>', unsafe_allow_html=True)
                    for j in upcoming_jobs:
                        is_night = False
                        shift_class = "shift-afternoon"
                        border = "#2563eb"
                        try: 
                            h_bd = int(j["gio_bat_dau"].split(":")[0])
                            is_night = int(j["gio_ket_thuc"].split(":")[0]) < h_bd
                            if h_bd < 12: 
                                shift_class = "shift-morning"
                                border = "#f59e0b"
                            elif h_bd < 18: 
                                shift_class = "shift-afternoon"
                                border = "#3b82f6"
                            else: 
                                shift_class = "shift-night"
                                border = "#8b5cf6"
                        except: pass
    
                        st.markdown(f"""
    <div class="vhs-list-item {shift_class}">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>
    <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:4px;">
    {j['ten_cty']}
    {'<span style="background:#1e1b4b;color:#c4b5fd;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;margin-left:6px;">🌙 CA ĐÊM</span>' if is_night else ''}
    </div>
    <div style="font-size:12px;color:#64748b;line-height:2;">
    📋 <b>{j['ma_hd']}</b> · Kỳ <b>{j['ky_thang']}</b> · Lần <b>{j['lan_thu']}/{j['tan_suat']}</b><br>
    📅 <b>{j['ngay_du_kien']}</b> · ⏰ <b>{j['gio_bat_dau']} → {j['gio_ket_thuc']}</b>
    {'<br>📍 ' + j['dia_chi'] if j.get('dia_chi') else ''}
    {'<br>👷 KTV: ' + j['ky_thuat_vien'] if j.get('ky_thuat_vien') else '<br>👷 KTV: (Chưa gán)'}
    </div>
    </div>
    <div style="background:white;border-radius:8px;padding:8px 14px;text-align:center;border:1px solid {border}30;">
    <div style="font-size:10px;color:#94a3b8;">TRẠNG THÁI</div>
    <div style="font-size:13px;font-weight:700;color:{border};">{ST_LBL.get(j['trang_thai'],'?')}</div>
    </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

            with col_map:
                st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin:12px 0 8px;">🗺️ Lộ Trình Di Chuyển Hôm Nay</div>', unsafe_allow_html=True)
                if not map_jobs:
                    st.info("Các ca thi công hôm nay không có thông tin địa chỉ để vẽ bản đồ.")
                else:
                    import urllib.parse
                    
                    conn_map = get_connection()
                    api_key_row = conn_map.execute("SELECT value_data FROM settings WHERE key_name='google_maps_api_key'").fetchone()
                    api_key = api_key_row['value_data'] if api_key_row else None
                    conn_map.close()
                    
                    origin = "164 Huy Cận, Phước Long"
                    dest = map_jobs[-1]['dia_chi']
                    
                    wp_list = [j['dia_chi'] for j in map_jobs[:-1]]
                    
                    if api_key and api_key.strip():
                        if wp_list:
                            waypoints = "|".join(urllib.parse.quote(wp) for wp in wp_list)
                            wp_param = f"&waypoints={waypoints}"
                        else:
                            wp_param = ""
                            
                        map_url = f"https://www.google.com/maps/embed/v1/directions?key={api_key}&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}{wp_param}"
                        dir_url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}{wp_param}"
                    else:
                        if wp_list:
                            waypoints = " to:".join(wp for wp in wp_list)
                            daddr = f"{waypoints} to:{dest}"
                            wp_param = "&waypoints=" + "|".join(urllib.parse.quote(wp) for wp in wp_list)
                        else:
                            daddr = dest
                            wp_param = ""
                        map_url = f"https://maps.google.com/maps?saddr={urllib.parse.quote(origin)}&daddr={urllib.parse.quote(daddr)}&output=embed"
                        dir_url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}{wp_param}"
                    
                    st.components.v1.iframe(map_url, height=500, scrolling=True)
                    st.markdown(f'<a href="{dir_url}" target="_blank" style="display:inline-block;margin-top:10px;background:#3b82f6;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">📍 Bắt đầu đi từ nhà (Google Maps)</a>', unsafe_allow_html=True)

    # ═══════════════════════════════════
    # THEO THÁNG / HĐ
    # ═══════════════════════════════════
    with tab_month:
        conn = get_connection()
        contracts = conn.execute("""
            SELECT ct.ma_hd, ct.ma_kh, c.ten_cty, ct.tan_suat,
                   ct.gio_bat_dau, ct.gio_ket_thuc, ct.kieu_lap, ct.lap_thu,
                   ct.ngay_thi_cong_dau, ct.loai_khach, c.dia_chi, ct.khu_vuc_xu_ly,
                   ct.loai_con_trung, ct.phuong_phap_xu_ly
            FROM contracts ct JOIN customers c ON ct.ma_kh=c.ma_kh
            WHERE ct.trang_thai='active' ORDER BY ct.ma_hd
        """).fetchall()
        conn.close()

        if not contracts:
            st.info("Chưa có hợp đồng active.")
        else:

            c1,c2 = st.columns([2,1])
            with c1:
                hd_opts = {
                    f"{r['ma_hd']} — {r['ten_cty']} ({TS_LABEL.get(r['tan_suat'],'?')})": dict(r)
                    for r in contracts
                }
                hd_sel = st.selectbox("Chọn Hợp Đồng",list(hd_opts.keys()),key="mth_hd")
                hd = hd_opts[hd_sel]
            with c2:
                today = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
                ky_choices = []
                for delta in range(-2,5):
                    d = today.replace(day=1) + timedelta(days=32*delta)
                    ky_choices.append(d.strftime("%Y-%m"))
                ky_sel = st.selectbox("Kỳ tháng",ky_choices,index=2,key="mth_ky")
    
            # Lấy lịch của kỳ đó
            conn = get_connection()
            rows = [dict(r) for r in conn.execute("""
                SELECT s.* FROM schedules s
                WHERE s.ma_hd=? AND s.ky_thang=? ORDER BY s.ngay_du_kien, s.gio_bat_dau
            """, (hd["ma_hd"],ky_sel)).fetchall()]
            conn.close()
    
            # Tự động sinh lịch nếu trống
            if not rows:
                n = auto_generate_schedules(hd["ma_hd"],ky_sel)
                if n > 0:
                    conn2 = get_connection()
                    rows = [dict(r) for r in conn2.execute("""
                        SELECT s.* FROM schedules s
                        WHERE s.ma_hd=? AND s.ky_thang=? ORDER BY s.ngay_du_kien, s.gio_bat_dau
                    """, (hd["ma_hd"],ky_sel)).fetchall()]
                    conn2.close()
    
            expected = hd["tan_suat"] if hd.get("loai_khach", "Định kỳ") == "Định kỳ" else len(rows)
            done_cnt = sum(1 for r in rows if r["trang_thai"]=="completed")
            pct = int(done_cnt/expected*100) if expected else 0
    
            # Header kỳ
            kieu_txt = "📅 Ngày cố định" if hd["kieu_lap"]=="ngay_co_dinh" else f"📆 {THU_OPTS.get(hd['lap_thu'],'?')} hàng tuần"
            st.markdown(f"""
            <div class="vhs-list-item">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                <div>
                  <div style="font-size:15px;font-weight:700;color:#0f172a;">Kỳ {ky_sel} — {hd['ten_cty']}</div>
                  <div style="font-size:12px;color:#64748b;margin-top:2px;">
                    {kieu_txt} · {TS_LABEL.get(expected,'?')} · ⏰ {hd['gio_bat_dau']}–{hd['gio_ket_thuc']}
                  </div>
                </div>
                <div style="text-align:center;">
                  <div style="font-size:26px;font-weight:800;color:{'#16a34a' if pct==100 else '#d97706' if pct>0 else '#94a3b8'};">{pct}%</div>
                  <div style="font-size:11px;color:#94a3b8;">{done_cnt}/{expected} ca</div>
                </div>
              </div>
              <div style="background:#f1f5f9;border-radius:99px;height:5px;margin-top:10px;">
                <div style="background:#16a34a;height:5px;border-radius:99px;width:{pct}%;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
    
            if not rows:
                st.info(f"Không có lịch thi công nào được lên cho kỳ {ky_sel}.")
            else:
                for r in rows:
                    tt  = r["trang_thai"]
                    sc  = ST_CLR.get(tt,"#94a3b8")
                    is_night = False
                    try: is_night = int(r["gio_ket_thuc"].split(":")[0]) < int(r["gio_bat_dau"].split(":")[0])
                    except: pass
                    manual_tag = ' <span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:6px;font-size:10px;font-weight:700;">✏️ Đã chỉnh</span>' if r["nguon"]=="manual" else ""
    
                    with st.expander(
                        f"Lần {r['lan_thu']}/{expected} — {r['ngay_du_kien']} "
                        f"{'🌙' if is_night else ''} · {r['gio_bat_dau']}–{r['gio_ket_thuc']} · {ST_LBL.get(tt,'?')}"
                    ):
                        col_info, col_edit = st.columns([3,2])
                        with col_info:
                            st.markdown(f"""
                            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
                              <div style="background:#f8fafc;border-radius:8px;padding:10px 14px;min-width:100px;">
                                <div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">Ngày</div>
                                <div style="font-size:14px;font-weight:700;color:#0f172a;">{r['ngay_du_kien']}</div>
                              </div>
                              <div style="background:#f8fafc;border-radius:8px;padding:10px 14px;min-width:100px;">
                                <div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">Giờ</div>
                                <div style="font-size:14px;font-weight:700;color:#0f172a;">{'🌙 ' if is_night else ''}{r['gio_bat_dau']}→{r['gio_ket_thuc']}</div>
                              </div>
                              <div style="background:{sc}15;border:1px solid {sc}30;border-radius:8px;padding:10px 14px;">
                                <div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">Trạng thái{manual_tag}</div>
                                <div style="font-size:13px;font-weight:700;color:{sc};">{ST_LBL.get(tt,'?')}</div>
                              </div>
                              <div style="background:#f8fafc;border-radius:8px;padding:10px 14px;">
                                <div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">KTV</div>
                                <div style="font-size:13px;font-weight:700;color:#0f172a;">{r.get('ky_thuat_vien') or '(Chưa gán)'}</div>
                              </div>
                            </div>
                            <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#0369a1;line-height:1.6;">
                              {'📍 <b>' + hd['dia_chi'] + '</b><br>' if hd.get('dia_chi') else ''}
                              {'🏠 Khu vực: <b>' + hd['khu_vuc_xu_ly'] + '</b><br>' if hd.get('khu_vuc_xu_ly') else ''}
                              {'🕷️ Dịch hại: <b>' + (r.get('loai_con_trung') or hd.get('loai_con_trung') or '') + '</b><br>' if (r.get('loai_con_trung') or hd.get('loai_con_trung')) else ''}
                              {'💊 Phương pháp: <b>' + hd['phuong_phap_xu_ly'] + '</b>' if hd.get('phuong_phap_xu_ly') else ''}
                            </div>
                            {f'<div style="font-size:12px;color:#64748b;">📝 {r["ghi_chu"]}</div>' if r.get("ghi_chu") else ""}
                            """, unsafe_allow_html=True)
    
                        with col_edit:
                            if tt != "completed":
                                st.markdown("**✏️ Điều Chỉnh**")
                                with st.form(f"edit_{r['id']}"):
                                    new_ngay = st.date_input(
                                        "Đổi ngày",
                                        value=date.fromisoformat(r["ngay_du_kien"]),
                                        key=f"dn_{r['id']}"
                                    )
                                    c_a,c_b = st.columns(2)
                                    with c_a:
                                        h_bd,m_bd = map(int,r["gio_bat_dau"].split(":"))
                                        new_gbd = st.time_input("Giờ bắt đầu",
                                            value=dt.time(h_bd,m_bd), key=f"gbd_{r['id']}")
                                    with c_b:
                                        h_kt,m_kt = map(int,r["gio_ket_thuc"].split(":"))
                                        new_gkt = st.time_input("Giờ kết thúc",
                                            value=dt.time(h_kt,m_kt), key=f"gkt_{r['id']}")
                                    new_gc = st.text_input("Ghi chú",
                                        value=r.get("ghi_chu","") or "", key=f"gc_{r['id']}")
                                    
                                    curr_ktv = r.get("ky_thuat_vien", "")
                                    ktv_idx = 0
                                    if curr_ktv in KTV_LIST:
                                        ktv_idx = KTV_LIST.index(curr_ktv) + 1
                                    new_ktv = st.selectbox("Kỹ thuật viên", [""] + KTV_LIST, index=ktv_idx, key=f"ktv_{r['id']}")
                                    
                                    new_pest = st.text_input("Dịch hại", value=r.get("loai_con_trung") or hd.get("loai_con_trung") or "", key=f"pest_{r['id']}")
                                    apply_future = st.checkbox("🔄 Áp dụng dịch hại này cho lần lặp tương ứng ở các tháng sau", value=False, key=f"apply_{r['id']}")
    
                                    cs,ck = st.columns(2)
                                    with cs: save_btn = st.form_submit_button("💾 Lưu",use_container_width=True)
                                    with ck: skip_btn = st.form_submit_button("🚫 Bỏ qua",use_container_width=True,type="secondary")
    
                                    if save_btn:
                                        try:
                                            conn = get_connection()
                                            
                                            # Check overlap
                                            if new_ktv:
                                                overlap = False
                                                ovs = conn.execute("SELECT s.gio_bat_dau, s.gio_ket_thuc, c.ten_cty FROM schedules s JOIN customers c ON s.ma_kh=c.ma_kh WHERE s.ngay_du_kien=? AND s.ky_thuat_vien=? AND s.id!=? AND s.trang_thai!='skipped' AND s.trang_thai!='completed'", (new_ngay.isoformat(), new_ktv, r["id"])).fetchall()
                                                for ov in ovs:
                                                    def tm(t):
                                                        h, m = map(int, t.split(':'))
                                                        return h*60+m
                                                    s1, e1 = tm(new_gbd.strftime("%H:%M")), tm(new_gkt.strftime("%H:%M"))
                                                    s2, e2 = tm(ov["gio_bat_dau"]), tm(ov["gio_ket_thuc"])
                                                    if e1 <= s1: e1 += 24*60
                                                    if e2 <= s2: e2 += 24*60
                                                    if max(s1, s2) < min(e1, e2):
                                                        st.error(f"❌ KTV {new_ktv} bị trùng giờ với ca tại {ov['ten_cty']} ({ov['gio_bat_dau']} - {ov['gio_ket_thuc']})")
                                                        overlap = True
                                                        break
                                                if overlap:
                                                    conn.close()
                                                    continue
                                            
                                            conn.execute("""UPDATE schedules
                                                SET ngay_du_kien=?,gio_bat_dau=?,gio_ket_thuc=?,ghi_chu=?,nguon='manual',ky_thuat_vien=?,loai_con_trung=?
                                                WHERE id=?""",
                                                (new_ngay.isoformat(), new_gbd.strftime("%H:%M"),
                                                 new_gkt.strftime("%H:%M"), new_gc, new_ktv, new_pest, r["id"]))
                                            if apply_future:
                                                conn.execute("""
                                                    UPDATE schedules 
                                                    SET loai_con_trung=? 
                                                    WHERE ma_hd=? AND lan_thu=? AND ky_thang > ?
                                                """, (new_pest, r["ma_hd"], r["lan_thu"], r["ky_thang"]))
                                            
                                            from utils.google_sync import auto_sync_schedule_to_google
                                            auto_sync_schedule_to_google(conn, r["id"], "upsert")
                                            conn.commit(); conn.close()
                                            st.success("✅ Đã cập nhật!"); st.rerun()
                                        except Exception as e: st.error(f"❌ {e}")
                                    if skip_btn:
                                        try:
                                            conn = get_connection()
                                            conn.execute("UPDATE schedules SET trang_thai='skipped' WHERE id=?",(r["id"],))
                                            from utils.google_sync import auto_sync_schedule_to_google
                                            auto_sync_schedule_to_google(conn, r["id"], "upsert")
                                            conn.commit(); conn.close()
                                            st.info("Ca đã bỏ qua."); st.rerun()
                                        except Exception as e: st.error(f"❌ {e}")
                            else:
                                st.markdown("""
                                <div style="background:#dcfce7;border-radius:8px;padding:14px;text-align:center;">
                                  <div style="font-size:24px;">✅</div>
                                  <div style="font-size:12px;color:#166534;font-weight:600;margin-top:4px;">Đã hoàn thành</div>
                                </div>""", unsafe_allow_html=True)
    
                # Nếu thiếu ca → sinh thêm
            if len(rows) < expected:
                st.markdown(f'<div style="background:#fef9c3;border-radius:8px;padding:10px;margin-top:8px;font-size:13px;color:#854d0e;">⚠️ Còn thiếu <b>{expected-len(rows)}</b> ca</div>', unsafe_allow_html=True)
                if st.button("🤖 Sinh Ca Còn Thiếu", key="gen_miss"):
                    n = auto_generate_schedules(hd["ma_hd"],ky_sel)
                    st.success(f"✅ Sinh thêm {n} ca.") if n else st.info("Đã đủ.")
                    st.rerun()

            # Sinh kỳ kế tiếp
            ky_next = (date(int(ky_sel[:4]),int(ky_sel[5:7]),1)+timedelta(days=32)).strftime("%Y-%m")
            conn = get_connection()
            nc = conn.execute("SELECT COUNT(*) FROM schedules WHERE ma_hd=? AND ky_thang=?",
                              (hd["ma_hd"],ky_next)).fetchone()[0]
            conn.close()
            if nc == 0:
                if st.button(f"📆 Sinh Lịch Kỳ Kế Tiếp ({ky_next})", key="gen_next"):
                    n = auto_generate_schedules(hd["ma_hd"],ky_next)
                    st.success(f"✅ Đã sinh {n} ca cho {ky_next}"); st.rerun()
            else:
                st.markdown(f'<div style="font-size:12px;color:#16a34a;margin-top:8px;">✅ Kỳ {ky_next} đã có {nc} ca</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════
    # CALENDAR
    # ═══════════════════════════════════
    with tab_cal:
        today = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
        c1,c2,c3,_ = st.columns([1, 1, 1, 3], vertical_alignment="bottom")
        with c1: sel_m = st.selectbox("Tháng",range(1,13),index=today.month-1,format_func=lambda x:f"Tháng {x:02d}")
        year_list = list(range(today.year - 2, today.year + 4))
        with c2: sel_y = st.selectbox("Năm", year_list, index=year_list.index(today.year))
        
        with c3:
            if st.button("🔄 Đồng bộ", use_container_width=True):
                google_sync_dialog(sel_m, sel_y)

        conn = get_connection()
        ky_str = f"{sel_y}-{sel_m:02d}"
        md = conn.execute("""
            SELECT s.ngay_du_kien, s.id, s.trang_thai, s.gio_bat_dau, c.ten_cty
            FROM schedules s
            JOIN customers c ON s.ma_kh = c.ma_kh
            WHERE strftime('%Y-%m',s.ngay_du_kien)=?
            ORDER BY s.gio_bat_dau
        """, (ky_str,)).fetchall()
        conn.close()

        day_map = {}
        for r in md:
            d = r["ngay_du_kien"]
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(dict(r))

        cal_wks  = calendar.monthcalendar(sel_y, sel_m)
        dnames   = ["T2","T3","T4","T5","T6","T7","CN"]

        hdr = "".join(f'<th style="padding:8px 4px;font-size:11px;font-weight:700;color:#64748b;text-align:center;background:#f8fafc;width:14.28%;">{d}</th>' for d in dnames)
        body = ""
        for wk in cal_wks:
            body += "<tr>"
            for dow,day in enumerate(wk):
                if day==0:
                    body += '<td style="background:#fafafa;border:1px solid #f1f5f9;padding:5px;height:80px;"></td>'; continue
                ds  = f"{sel_y}-{sel_m:02d}-{day:02d}"
                isd = ds == (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().strftime("%Y-%m-%d")
                isw = dow >= 5
                jobs= day_map.get(ds, [])
                cbg = "#0f172a" if isd else "#fafafa" if isw else "white"
                dcl = "white" if isd else "#94a3b8" if isw else "#0f172a"
                dots= ""
                for job in jobs:
                    stt = job["trang_thai"]
                    bg = "#dbeafe" # pending
                    col = "#1e40af"
                    icon = "📅"
                    if stt == "completed":
                        bg = "#dcfce7"
                        col = "#166534"
                        icon = "✅"
                    elif stt == "skipped":
                        bg = "#f1f5f9"
                        col = "#94a3b8"
                        icon = "—"
                    
                    time_str = job["gio_bat_dau"][:5] if job["gio_bat_dau"] else ""
                    ten_cty = job["ten_cty"]
                    
                    dots += f'<div title="{ten_cty}" style="background:{bg};color:{col};border-radius:4px;padding:2px 4px;font-size:10px;font-weight:600;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{icon} {time_str} {ten_cty}</div>'
                    
                body += f'<td style="background:{cbg};border:1px solid #f1f5f9;padding:5px;height:80px;vertical-align:top;max-width:0;"><div style="font-size:12px;font-weight:{"700" if isd else "500"};color:{dcl};margin-bottom:4px;">{day}</div>{dots}</td>'
            body += "</tr>"

        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.04);">
          <div style="background:#0f172a;padding:12px 20px;text-align:center;">
            <div style="font-size:14px;font-weight:700;color:white;">Lịch Thi Công Tháng {sel_m:02d}/{sel_y}</div>
          </div>
          <table style="width:100%;border-collapse:collapse;"><tr>{hdr}</tr>{body}</table>
        </div>
        <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:5px;"><div style="background:#dbeafe;border-radius:3px;width:12px;height:8px;"></div><span style="font-size:12px;color:#64748b;">Chờ thi công</span></div>
          <div style="display:flex;align-items:center;gap:5px;"><div style="background:#dcfce7;border-radius:3px;width:12px;height:8px;"></div><span style="font-size:12px;color:#64748b;">Hoàn thành</span></div>
          <div style="display:flex;align-items:center;gap:5px;"><div style="background:#f1f5f9;border-radius:3px;width:12px;height:8px;"></div><span style="font-size:12px;color:#64748b;">Bỏ qua</span></div>
          <div style="display:flex;align-items:center;gap:5px;"><div style="background:#0f172a;border-radius:3px;width:12px;height:8px;"></div><span style="font-size:12px;color:#64748b;">Hôm nay</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════
    # HÀNG LOẠT
    # ═══════════════════════════════════
    with tab_bulk:
        conn = get_connection()
        cts  = conn.execute("""
            SELECT ct.ma_hd, ct.ma_kh, c.ten_cty, ct.tan_suat
            FROM contracts ct JOIN customers c ON ct.ma_kh=c.ma_kh
            WHERE ct.trang_thai='active' ORDER BY ct.ma_hd
        """).fetchall()
        conn.close()

        col_b, col_s = st.columns(2)
        today = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()

        with col_b:
            st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px;">', unsafe_allow_html=True)
            st.markdown("**🤖 Sinh Hàng Loạt**")
            st.markdown('<hr style="margin:6px 0 12px">', unsafe_allow_html=True)

            ky_choices = [(today.replace(day=1)+timedelta(days=32*i)).strftime("%Y-%m") for i in range(4)]
            ky_bulk = st.selectbox("Kỳ tháng",ky_choices,key="ky_bulk2")
            hd_bulk = st.multiselect("HĐ (bỏ trống = tất cả)",
                [r["ma_hd"] for r in cts],
                format_func=lambda x: next((f"{r['ma_hd']} — {r['ten_cty']}" for r in cts if r["ma_hd"]==x),x))

            if st.button("🚀 Sinh Tất Cả",use_container_width=True,key="btn_bulk2"):
                targets = hd_bulk if hd_bulk else [r["ma_hd"] for r in cts]
                total = sum(auto_generate_schedules(m,ky_bulk) for m in targets)
                st.success(f"✅ Sinh {total} ca mới cho {ky_bulk}") if total else st.info("Tất cả đã có.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_s:
            st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px;">', unsafe_allow_html=True)
            st.markdown("**➕ Thêm Ca Thủ Công**")
            st.markdown('<hr style="margin:6px 0 12px">', unsafe_allow_html=True)

            with st.form("form_manual_ca"):
                hd_opts3 = {f"{r['ma_hd']} — {r['ten_cty']}": dict(r) for r in cts}
                hd_s3    = st.selectbox("Hợp đồng",list(hd_opts3.keys()))
                hd3      = hd_opts3.get(hd_s3,{})

                c1,c2 = st.columns(2)
                with c1:
                    extra_ngay = st.date_input("Ngày thi công",value=today,key="ex_ngay")
                    h_bd = int(hd3.get("gio_bat_dau","08:00").split(":")[0])
                    m_bd = int(hd3.get("gio_bat_dau","08:00").split(":")[1])
                    extra_gbd  = st.time_input("Giờ bắt đầu",value=dt.time(h_bd,m_bd),key="ex_gbd")
                with c2:
                    h_kt = int(hd3.get("gio_ket_thuc","12:00").split(":")[0])
                    m_kt = int(hd3.get("gio_ket_thuc","12:00").split(":")[1])
                    extra_gkt  = st.time_input("Giờ kết thúc",value=dt.time(h_kt,m_kt),key="ex_gkt")
                    extra_gc   = st.text_input("Ghi chú",key="ex_gc")

                if st.form_submit_button("➕ Thêm Ca",use_container_width=True):
                    try:
                        ky_extra = extra_ngay.strftime("%Y-%m")
                        conn = get_connection()
                        max_lan = conn.execute(
                            "SELECT COALESCE(MAX(lan_thu),0) FROM schedules WHERE ma_hd=? AND ky_thang=?",
                            (hd3["ma_hd"],ky_extra)
                        ).fetchone()[0]
                        rs = conn.execute("""INSERT INTO schedules
                            (ma_hd,ma_kh,ky_thang,lan_thu,ngay_du_kien,gio_bat_dau,gio_ket_thuc,nguon,ghi_chu)
                            VALUES(?,?,?,?,?,?,?,?,?) RETURNING id""",
                            (hd3["ma_hd"],hd3["ma_kh"],ky_extra,max_lan+1,
                             extra_ngay.isoformat(),extra_gbd.strftime("%H:%M"),
                             extra_gkt.strftime("%H:%M"),"manual",extra_gc)).fetchone()
                        if rs:
                            from utils.google_sync import auto_sync_schedule_to_google
                            auto_sync_schedule_to_google(conn, rs["id"], "upsert")
                        conn.commit(); conn.close()
                        st.success(f"✅ Đã thêm ca ngày {extra_ngay.strftime('%d/%m/%Y')}"); st.rerun()
                    except Exception as e: st.error(f"❌ {e}")
            st.markdown("</div>", unsafe_allow_html=True)
