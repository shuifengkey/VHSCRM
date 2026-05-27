# pages/p4_logbook.py - Logbook KTV v2 — Mobile-first + Timeline
import streamlit as st
import sys, os

from utils.database import get_connection
from utils.scheduling import is_job_active_now, check_time_violation
from utils.styles import badge, section_header, COLORS
from datetime import timezone, datetime, date, timedelta

def render():
    st.markdown("""
    <style>
    /* Color ALL popover buttons with dark gradient in this page */
    div[data-testid="stPopover"] > button {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a2f 60%, #166534 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
    }
    div[data-testid="stPopover"] > button:hover {
        background: linear-gradient(135deg, #1e293b 0%, #294d3f 60%, #22c55e 100%) !important;
        box-shadow: 0 4px 12px rgba(22,163,74,0.3) !important;
        color: white !important;
    }
    .color-bosung { display: none; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(section_header("Work Log Kỹ Thuật Viên", "Check-in / Check-out · Ghi chú hóa chất · Lịch sử thi công", "📓"), unsafe_allow_html=True)

    tab_work, tab_history, tab_stats = st.tabs(["🔧  Check-in / Out", "📋  Lịch Sử", "📊  Thống Kê KTV"])

    with tab_work:
        now_dt = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
        today_str = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().strftime("%Y-%m-%d")
        tomorrow_str = ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()+timedelta(days=1)).strftime("%Y-%m-%d")
        past3_str = ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()-timedelta(days=3)).strftime("%Y-%m-%d")

        conn = get_connection()
        pending = conn.execute("""
            SELECT s.id, s.ma_hd, s.ma_kh, s.ngay_du_kien, s.gio_bat_dau, s.gio_ket_thuc, s.trang_thai, s.ky_thuat_vien, s.loai_con_trung as s_loai_con_trung,
                   c.ten_cty, c.dia_chi, c.sdt, ct.khu_vuc_xu_ly, ct.loai_con_trung, ct.phuong_phap_xu_ly
            FROM schedules s 
            JOIN customers c ON s.ma_kh=c.ma_kh
            JOIN contracts ct ON s.ma_hd=ct.ma_hd
            WHERE s.trang_thai = 'scheduled' AND s.ngay_du_kien <= ?
            ORDER BY s.ngay_du_kien ASC, s.gio_bat_dau ASC
        """, (tomorrow_str,)).fetchall()
        conn.close()

        # Phân loại upcoming (24h) vs overdue (quá ca)
        upcoming_jobs = []
        overdue_jobs = []
        for r in pending:
            j = dict(r)
            sch_date = date.fromisoformat(j["ngay_du_kien"])
            h_bd, m_bd = 8, 0
            try: h_bd, m_bd = map(int, (j["gio_bat_dau"] or "08:00").split(":"))
            except: pass
            start_dt = datetime(sch_date.year, sch_date.month, sch_date.day, h_bd, m_bd)
            diff_hours = (start_dt - now_dt).total_seconds() / 3600
            
            # Quá ca: quá 24h hoặc quá 2h so với giờ bắt đầu (nếu muốn) 
            # Nhưng giữ logic cũ: < -24 là overdue, -24 đến 24 là upcoming. Nếu xa hơn tương lai thì không hiện.
            if -24 <= diff_hours <= 24:
                upcoming_jobs.append(j)
            elif diff_hours < -24:
                overdue_jobs.append(j)

        jobs = upcoming_jobs + overdue_jobs

        if not jobs:
            st.markdown("""
            <div class="vhs-card" style="text-align:center;padding:60px;">
                <div style="font-size:56px;">🎉</div>
                <div style="font-size:18px;font-weight:700;color:#0f172a;margin-top:12px;">Không có ca nào trong 24h tới!</div>
            </div>""", unsafe_allow_html=True)
        else:
            conn_t = get_connection()
            active_techs = [r["ten"] for r in conn_t.execute("SELECT ten FROM technicians WHERE active=1 ORDER BY ten").fetchall()]
            conn_t.close()

            for job in jobs:
                current_ktv = job.get('ky_thuat_vien')
                opts = active_techs.copy()
                if current_ktv and current_ktv not in opts:
                    opts.insert(0, current_ktv)
                if not opts:
                    opts = ["(Chưa có)"]

                # Info card
                is_night = False
                try: is_night = int(job["gio_ket_thuc"].split(":")[0]) < int(job["gio_bat_dau"].split(":")[0])
                except: pass
        
                night_html = f'<span style="background:#7c3aed20;color:#7c3aed;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;margin-left:8px;">🌙 CA ĐÊM</span>' if is_night else ""
                # Check overdue
                _sch_d = date.fromisoformat(job["ngay_du_kien"])
                _h, _m = 8, 0
                try: _h, _m = map(int, (job["gio_bat_dau"] or "08:00").split(":"))
                except: pass
                _start = datetime(_sch_d.year, _sch_d.month, _sch_d.day, _h, _m)
                _is_overdue = ((_start - now_dt).total_seconds() / 3600) < -24
                overdue_html = '<span style="background:#dc2626;color:white;padding:2px 8px;border-radius:10px;font-size:10px;margin-left:6px;font-weight:700;">⚠️ QUÁ CA</span>' if _is_overdue else ""
        
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
                        <div>
                            <div style="font-size:18px;font-weight:800;color:#0f172a;margin-bottom:4px;">
                                🏢 {job['ten_cty']} {night_html} {overdue_html}
                            </div>
                            <div style="font-size:13px;color:#64748b;margin-top:6px;line-height:1.7;">
                                📋 Hợp đồng: <b>{job['ma_hd']}</b><br>
                                📍 Địa chỉ: {job['dia_chi'] or '-'}<br>
                                📞 SĐT: {job['sdt'] or '-'}
                            </div>
                            <div style="margin-top:10px;padding:10px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;font-size:12px;color:#0f172a;line-height:1.6;">
                                <b style="color:#2563eb;">📌 Hạng mục thi công:</b><br>
                                🏠 <b>Khu vực:</b> {job['khu_vuc_xu_ly'] or '—'}<br>
                                🕷️ <b>Dịch hại:</b> {(job.get('s_loai_con_trung') or job.get('loai_con_trung')) or '—'}<br>
                                💊 <b>Phương pháp:</b> {job['phuong_phap_xu_ly'] or '—'}
                            </div>
                        </div>
                        <div style="text-align:center;background:#f0fdf4;border-radius:12px;padding:12px 20px;">
                            <div style="font-size:11px;color:#16a34a;font-weight:700;">NGÀY {job['ngay_du_kien']}</div>
                            <div style="font-size:22px;font-weight:800;color:#0f172a;">{job['gio_bat_dau']}</div>
                            <div style="font-size:12px;color:#94a3b8;">đến {job['gio_ket_thuc']}</div>
                        </div>
                        </div>
                    """, unsafe_allow_html=True)
        
                    conn = get_connection()
                    log = conn.execute("SELECT * FROM logbook WHERE schedule_id=?", (job["id"],)).fetchone()
                    log = dict(log) if log else None
                    conn.close()
        
                    # Trạng thái check-in
                    if log and log.get("checkout_time"):
                        dur_str = ""
                        try:
                            ci = datetime.fromisoformat(log["checkin_time"]).replace(tzinfo=None)
                            co = datetime.fromisoformat(log["checkout_time"]).replace(tzinfo=None)
                            mins = int((co - ci).total_seconds() / 60)
                            dur_str = f"{mins // 60}h {mins % 60}m"
                        except: pass
        
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1], vertical_alignment="center")
                            with c1:
                                st.markdown(f"""
    <div style="color:#166534;">
        <div style="font-size:16px;font-weight:700;">✅ Ca Đã Hoàn Thành</div>
        <div style="font-size:13px;color:#4ade80;margin-top:2px;">
            {log['checkin_time'][11:16]} → {log['checkout_time'][11:16]}
            {f' · Thời gian: {dur_str}' if dur_str else ''}
        </div>
        {'<div style="background:#fef9c3;border-radius:8px;padding:4px 8px;margin-top:6px;font-size:11px;color:#854d0e;display:inline-block;">⚠️ Có cảnh báo sai giờ</div>' if log.get('canh_bao_gio') else ''}
        <div style="font-size:12px;color:#475569;margin-top:4px;"><b>👷 KTV:</b> {log.get('ky_thuat_vien','-')} &nbsp;|&nbsp; <b>💊 Hóa chất:</b> {log.get('hoa_chat','-')} &nbsp;|&nbsp; <b>📝 KQ:</b> {log.get('ket_qua','-')}</div>
    </div>
    """, unsafe_allow_html=True)
                            with c2:
                                st.markdown('<div class="color-bosung"></div>', unsafe_allow_html=True)
                                with st.popover("➕ Bổ sung"):
                                    with st.form(f"form_attach_{job['id']}"):
                                        extra_att = st.file_uploader("Thêm ảnh/tài liệu", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True, key=f"extra_file_{job['id']}")
                                        if st.form_submit_button("Lưu bổ sung", use_container_width=True):
                                            if extra_att:
                                                import os, uuid
                                                uploaded_paths = []
                                                upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
                                                os.makedirs(upload_dir, exist_ok=True)
                                                for f in extra_att:
                                                    filename = f"{uuid.uuid4().hex[:8]}_{f.name}"
                                                    filepath = os.path.join(upload_dir, filename)
                                                    with open(filepath, "wb") as out:
                                                        out.write(f.getbuffer())
                                                    uploaded_paths.append(filename)
                                                new_att_str = ",".join(uploaded_paths)
                                                old_att = log.get("attachments", "")
                                                final_att = (old_att + "," + new_att_str).strip(",") if old_att else new_att_str
                                                conn_u = get_connection()
                                                conn_u.execute("UPDATE logbook SET attachments=? WHERE id=?", (final_att, log["id"]))
                                                conn_u.commit()
                                                conn_u.close()
                                                st.success("✅ Đã bổ sung tài liệu!")
                                                st.rerun()
                                            else:
                                                st.warning("⚠️ Chưa chọn file nào!")
                    
                        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
        
                    elif log and log.get("checkin_time"):
                        # Đang thi công
                        ci_dt = datetime.fromisoformat(log["checkin_time"]).replace(tzinfo=None)
                        elapsed = int(((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)) - ci_dt).total_seconds() / 60)
        
                        time_check = check_time_violation(job["gio_bat_dau"], job["gio_ket_thuc"], log["checkin_time"], job["ngay_du_kien"])
        
                        st.markdown(f"""
                        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:16px;text-align:center;margin-top:16px;">
                            <div style="font-size:14px;color:#854d0e;font-weight:700;">⏱️ ĐANG THI CÔNG</div>
                            <div style="font-size:28px;font-weight:800;color:#0f172a;">Check-in {log['checkin_time'][11:16]}</div>
                            <div style="font-size:13px;color:#d97706;margin-bottom:12px;">Đã {elapsed} phút · KTV: {log.get('ky_thuat_vien','-')}</div>
                        """, unsafe_allow_html=True)
        
                        if time_check["violation"]:
                            st.warning(time_check["message"])
        
                        with st.form(f"form_checkout_{job['id']}"):
                            hoa_chat = st.text_area("💊 Hóa Chất Sử Dụng",
                                value=log.get("hoa_chat",""),
                                placeholder="VD: Permethrin 0.5% phun tường + Bẫy dính 10 chiếc...",
                                height=100)
                            ket_qua = st.text_area("📊 Kết Quả / Nhận Xét",
                                placeholder="VD: Phát hiện ổ gián lớn tại khu bếp, đã xử lý...",
                                height=80)
                            attachments = st.file_uploader("📷 Đính kèm Hình ảnh / Tài liệu", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True, key=f"file_{job['id']}")
                            if st.form_submit_button("🚪 CHECK-OUT — KẾT THÚC CA", type="primary", use_container_width=True):
                                checkin_time = datetime.fromisoformat(log["checkin_time"]).replace(tzinfo=None)
                                if ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)) - checkin_time).total_seconds() < 300:
                                    st.error("⚠️ Phải thi công ít nhất 5 phút mới được Check-out!")
                                else:
                                    try:
                                        import os, uuid
                                        uploaded_paths = []
                                        if attachments:
                                            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
                                            os.makedirs(upload_dir, exist_ok=True)
                                            for f in attachments:
                                                filename = f"{uuid.uuid4().hex[:8]}_{f.name}"
                                                filepath = os.path.join(upload_dir, filename)
                                                with open(filepath, "wb") as out:
                                                    out.write(f.getbuffer())
                                                uploaded_paths.append(filename)
                                        attachments_str = ",".join(uploaded_paths) if uploaded_paths else ""
    
                                        conn = get_connection()
                                        conn.execute("UPDATE logbook SET checkout_time=?,hoa_chat=?,ket_qua=?,attachments=? WHERE id=?",
                                                     ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), hoa_chat, ket_qua, attachments_str, log["id"]))
                                        conn.commit()
                                        conn.close()
                                    
                                        from utils.schedule_engine import complete_schedule as cs_fn
                                        conn_ct = __import__('utils.database', fromlist=['get_connection']).get_connection()
                                        ct_row = conn_ct.execute('SELECT * FROM contracts WHERE ma_hd=?',(job['ma_hd'],)).fetchone()
                                        conn_ct.close()
                                    
                                        if ct_row:
                                            result = cs_fn(job['id'], dict(ct_row))
                                            if result.get('next_ids'):
                                                st.info(f"📅 Đã tự động tạo {len(result['next_ids'])} ca kỳ tiếp theo cho {job['ten_cty']}!")
                                        else:
                                            conn_fallback = __import__('utils.database', fromlist=['get_connection']).get_connection()
                                            conn_fallback.execute("UPDATE schedules SET trang_thai='completed' WHERE id=?", (job['id'],))
                                            from utils.google_sync import auto_sync_schedule_to_google
                                            auto_sync_schedule_to_google(conn_fallback, job['id'], "upsert")
                                            conn_fallback.commit()
                                            conn_fallback.close()
                                        st.success("✅ Check-out thành công! Ca hoàn thành.")
                                        st.balloons(); st.rerun()
                                    except Exception as e: st.error(f"❌ {e}")
                    
                        st.markdown("</div>", unsafe_allow_html=True)
        
                    else:
                        # Chưa check-in
                        now_str = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime("%H:%M")
                        time_preview = check_time_violation(job["gio_bat_dau"], job["gio_ket_thuc"], (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), job["ngay_du_kien"])
        
                        st.markdown(f"""
                        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-top:16px;">
                            <div style="font-size:12px;color:#64748b;margin-bottom:12px;">Giờ hiện tại: <b style="color:#0f172a;">{now_str}</b>
                            &nbsp;·&nbsp; Khung giờ HĐ: <b>{job['gio_bat_dau']} – {job['gio_ket_thuc']}</b>
                            &nbsp;·&nbsp; {time_preview['message']}</div>
                        """, unsafe_allow_html=True)
        
                        c_lbl, c_sel = st.columns([2, 3], vertical_alignment="center")
                        with c_lbl:
                            st.markdown("<div style='font-size:14px;font-weight:600;color:#334155;text-transform:uppercase;'>👷 Chọn KTV phụ trách</div>", unsafe_allow_html=True)
                        with c_sel:
                            ktv = st.selectbox("👷 Chọn KTV phụ trách", opts, index=opts.index(current_ktv) if current_ktv in opts else 0, key=f"ktv_sel_{job['id']}", label_visibility="collapsed")
                    
                        if not ktv or ktv == "(Chưa có)":
                            st.warning("⚠️ Vui lòng chọn kỹ thuật viên để check-in!")
                        else:
                            if st.button("📍 CHECK-IN — BẮT ĐẦU CA", type="primary", use_container_width=True, key=f"btn_ci_{job['id']}"):
                                conn = get_connection()
                                active_other = conn.execute("SELECT c.ten_cty, l.checkin_time FROM logbook l JOIN schedules s ON l.schedule_id=s.id JOIN customers c ON l.ma_kh=c.ma_kh WHERE l.ky_thuat_vien=? AND l.checkout_time IS NULL AND l.schedule_id!=?", (ktv, job["id"])).fetchone()
                            
                                if active_other:
                                    conn.close()
                                    st.error(f"❌ KTV **{ktv}** đang thi công tại **{active_other['ten_cty']}** (từ {active_other['checkin_time'][11:16]}). Phải Check-out ca đó trước khi Check-in ca mới!")
                                else:
                                    try:
                                        tc = check_time_violation(job["gio_bat_dau"], job["gio_ket_thuc"], (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), job["ngay_du_kien"])
                                        conn.execute("""INSERT INTO logbook (schedule_id,ma_kh,ky_thuat_vien,checkin_time,canh_bao_gio)
                                                        VALUES(?,?,?,?,?)""",
                                                     (job["id"],job["ma_kh"],ktv,(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), 1 if tc["violation"] else 0))
                                        conn.execute("UPDATE schedules SET ky_thuat_vien=? WHERE id=?", (ktv, job["id"]))
                                        conn.commit(); conn.close()
                                        if tc["violation"]: st.warning(tc["message"])
                                        st.success(f"✅ Check-in lúc {(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%H:%M')} — Chúc làm tốt!")
                                        st.rerun()
                                    except Exception as e: 
                                        conn.close()
                                        st.error(f"❌ {e}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    
        with tab_history:
            conn = get_connection()
            ktvs = [r["ten"] for r in conn.execute("SELECT ten FROM technicians ORDER BY ten").fetchall()]
            ktv_opts = ["Tất cả"] + ktvs
            
            c1,c2 = st.columns(2)
            with c1: filter_date = st.date_input("Từ ngày", value=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()-timedelta(days=30))
            with c2: filter_ktv = st.selectbox("Lọc theo KTV", ktv_opts)
    
            q = """SELECT l.*, c.ten_cty FROM logbook l JOIN customers c ON l.ma_kh=c.ma_kh
                   WHERE DATE(l.checkin_time) >= ?"""
            p = [filter_date.strftime("%Y-%m-%d")]
            if filter_ktv != "Tất cả":
                q += " AND l.ky_thuat_vien = ?"
                p.append(filter_ktv)
            q += " ORDER BY l.checkin_time DESC LIMIT 50"
            logs = conn.execute(q, p).fetchall()
            conn.close()
    
            if not logs:
                st.info("Không có lịch sử trong khoảng thời gian này.")
            else:
                st.markdown(f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;">Hiển thị <b>{len(logs)}</b> bản ghi</div>', unsafe_allow_html=True)
                for log in logs:
                    log = dict(log)
                    done = bool(log["checkout_time"])
                    warn = bool(log["canh_bao_gio"])
                    dur = ""
                    try:
                        ci = datetime.fromisoformat(log["checkin_time"]).replace(tzinfo=None)
                        co = datetime.fromisoformat(log["checkout_time"]).replace(tzinfo=None)
                        m = int((co-ci).total_seconds()/60)
                        dur = f"· {m//60}h{m%60}m"
                    except: pass
                    left_color = "#16a34a" if done else "#d97706"
                    status_icon = "✅" if done else "⏳"
                    att_html = ""
                    if log.get("attachments"):
                        import os, base64, io
                        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
                        for filename in log["attachments"].split(","):
                            filepath = os.path.join(upload_dir, filename)
                            if os.path.exists(filepath):
                                ext = filename.lower().split('.')[-1]
                                if ext in ['png', 'jpg', 'jpeg', 'gif']:
                                    try:
                                        from PIL import Image
                                        with Image.open(filepath) as img:
                                            img.thumbnail((64, 64))
                                            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                                            tb = io.BytesIO()
                                            img.save(tb, format="JPEG", quality=75)
                                            tb64 = base64.b64encode(tb.getvalue()).decode()
                                            
                                            img_f = Image.open(filepath)
                                            img_f.thumbnail((1200, 1200))
                                            if img_f.mode in ("RGBA", "P"): img_f = img_f.convert("RGB")
                                            fb = io.BytesIO()
                                            img_f.save(fb, format="JPEG", quality=80)
                                            fb64 = base64.b64encode(fb.getvalue()).decode()
                                            
                                            att_html += f'<a href="data:image/jpeg;base64,{fb64}" target="_blank" title="Xem ảnh lớn"><img src="data:image/jpeg;base64,{tb64}" style="width:36px;height:36px;border-radius:4px;object-fit:cover;border:1px solid #cbd5e1;cursor:pointer;margin-left:4px;box-shadow:0 1px 2px rgba(0,0,0,0.05);"></a>'
                                    except: pass
                                else:
                                    try:
                                        with open(filepath, "rb") as f:
                                            fb64 = base64.b64encode(f.read()).decode()
                                        mime = "application/pdf" if ext == "pdf" else "application/octet-stream"
                                        att_html += f'<a href="data:{mime};base64,{fb64}" download="{filename}" title="Tải file {filename}" style="display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:4px;text-decoration:none;font-size:16px;margin-left:4px;box-shadow:0 1px 2px rgba(0,0,0,0.05);">📄</a>'
                                    except: pass

                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1], vertical_alignment="center")
                        with c1:
                            st.markdown(f"""
<div style="font-size:15px;font-weight:700;color:#0f172a;">{status_icon} {log['ten_cty']} {'<span style="font-size:10px;background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:8px;margin-left:8px;font-weight:700;display:inline-block;vertical-align:middle;">⚠️ SAI GIỜ</span>' if warn else ''}</div>
<div style="font-size:12px;color:#64748b;margin-top:3px;">
    👷 {log['ky_thuat_vien'] or '-'} &nbsp;·&nbsp;
    🕐 {log['checkin_time'][11:16] if log['checkin_time'] else '-'} → {log['checkout_time'][11:16] if log['checkout_time'] else '...'} &nbsp;{dur}
</div>
<div style="margin-top:6px;display:flex;align-items:center;gap:4px;">
    <div style="font-size:11px;color:#94a3b8;margin-right:6px;">{log['checkin_time'][:10] if log['checkin_time'] else ''}</div>
    {att_html}
</div>
""", unsafe_allow_html=True)
                        with c2:
                            st.markdown('<div class="color-bosung"></div>', unsafe_allow_html=True)
                            with st.popover("➕ Bổ sung", use_container_width=True):
                                with st.form(f"hist_form_attach_{log['id']}"):
                                    extra_att = st.file_uploader("Thêm ảnh/tài liệu", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True, key=f"hist_extra_file_{log['id']}")
                                    if st.form_submit_button("Lưu bổ sung", use_container_width=True):
                                        if extra_att:
                                            import os, uuid
                                            uploaded_paths = []
                                            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
                                            os.makedirs(upload_dir, exist_ok=True)
                                            for f in extra_att:
                                                filename = f"{uuid.uuid4().hex[:8]}_{f.name}"
                                                filepath = os.path.join(upload_dir, filename)
                                                with open(filepath, "wb") as out:
                                                    out.write(f.getbuffer())
                                                uploaded_paths.append(filename)
                                            new_att_str = ",".join(uploaded_paths)
                                            old_att = log.get("attachments", "")
                                            final_att = (old_att + "," + new_att_str).strip(",") if old_att else new_att_str
                                            conn_u = get_connection()
                                            conn_u.execute("UPDATE logbook SET attachments=? WHERE id=?", (final_att, log["id"]))
                                            conn_u.commit()
                                            conn_u.close()
                                            st.success("✅ Đã bổ sung tài liệu!")
                                            st.rerun()
                                        else:
                                            st.warning("⚠️ Chưa chọn file nào!")
    
    with tab_stats:
        conn = get_connection()
        ktv_stats = conn.execute("""
            SELECT ky_thuat_vien,
                   COUNT(*) total,
                   SUM(CASE WHEN checkout_time IS NOT NULL THEN 1 ELSE 0 END) done,
                   SUM(canh_bao_gio) warnings
            FROM logbook WHERE ky_thuat_vien IS NOT NULL AND ky_thuat_vien != ''
            GROUP BY ky_thuat_vien ORDER BY done DESC
        """).fetchall()
        conn.close()
        if not ktv_stats:
            st.info("Chưa có dữ liệu thi công.")
        else:
            import plotly.graph_objects as go
            fig = go.Figure()
            names = [r["ky_thuat_vien"] for r in ktv_stats]
            fig.add_bar(name="Hoàn thành", x=names, y=[r["done"] for r in ktv_stats], marker_color="#16a34a")
            fig.add_bar(name="Cảnh báo giờ", x=names, y=[r["warnings"] for r in ktv_stats], marker_color="#f59e0b")
            fig.update_layout(
                barmode="group", height=280, paper_bgcolor="white", plot_bgcolor="white",
                title=dict(text="Hiệu Suất Kỹ Thuật Viên", font=dict(size=14,color="#0f172a")),
                margin=dict(l=10,r=10,t=40,b=10), font=dict(family="Inter"),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True,gridcolor="#f1f5f9"),
                legend=dict(orientation="h",y=-0.2)
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

            # Table chi tiết
            for r in ktv_stats:
                rate = int(r["done"]/r["total"]*100) if r["total"] else 0
                warn_pct = int(r["warnings"]/r["total"]*100) if r["total"] else 0
                st.markdown(f"""
                <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="font-size:15px;font-weight:700;color:#0f172a;">👷 {r['ky_thuat_vien']}</div>
                            <div style="font-size:12px;color:#64748b;">{r['done']}/{r['total']} ca hoàn thành · {r['warnings']} cảnh báo giờ</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:20px;font-weight:800;color:{'#16a34a' if rate>=80 else '#d97706' if rate>=50 else '#dc2626'};">{rate}%</div>
                            <div style="font-size:11px;color:#94a3b8;">tỷ lệ HT</div>
                        </div>
                    </div>
                    <div style="background:#f1f5f9;border-radius:99px;height:5px;margin-top:10px;">
                        <div style="background:{'#16a34a' if rate>=80 else '#d97706'};height:5px;border-radius:99px;width:{rate}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
