import streamlit as st
import sys, os
from datetime import timezone, date, datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_connection
from utils.scheduling import is_job_active_now, check_time_violation

MOBILE_CSS = """
<style>
/* CSS Tối ưu cho Mobile */
[data-testid="stAppViewContainer"] {
    background-color: #f8fafc;
}
/* Nút to, bo tròn mượt */
.stButton > button {
    height: 54px !important;
    border-radius: 16px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}
/* Card thiết kế chuẩn mobile */
.mobile-card {
    background: white;
    color: #0f172a;
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    border: 1px solid #f1f5f9;
}
.mobile-header {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 24px;
    text-align: center;
}
.shift-time {
    font-size: 24px;
    font-weight: 900;
    color: #2563eb;
    margin-bottom: 4px;
}
.shift-company {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
}
.shift-address {
    font-size: 13px;
    color: #64748b;
    margin-top: 8px;
    line-height: 1.5;
}
.action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #f1f5f9;
    color: #334155;
    padding: 8px 16px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    margin-top: 12px;
    margin-right: 8px;
}
.status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    margin-top: 12px;
}
</style>
"""

@st.dialog("📋 Xác nhận thi công")
def action_dialog(job, log):
    st.markdown(f"**🏢 {job['ten_cty']}**")
    
    if not log:
        # CHECK IN
        st.info(f"Khung giờ: {job['gio_bat_dau']} - {job['gio_ket_thuc']}")
        if st.button("📍 CHECK-IN NGAY", type="primary", use_container_width=True):
            conn = get_connection()
            tc = check_time_violation(job["gio_bat_dau"], job["gio_ket_thuc"], (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), job["ngay_du_kien"])
            conn.execute("""INSERT INTO logbook (schedule_id,ma_kh,ky_thuat_vien,checkin_time,canh_bao_gio)
                            VALUES(?,?,?,?,?)""",
                         (job["id"], job["ma_kh"], st.session_state.mobile_ktv, (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), 1 if tc["violation"] else 0))
            conn.execute("UPDATE schedules SET ky_thuat_vien=? WHERE id=?", (st.session_state.mobile_ktv, job["id"]))
            conn.commit(); conn.close()
            st.rerun()
    else:
        # ĐANG THI CÔNG -> CHECK OUT
        ci_dt = datetime.fromisoformat(log["checkin_time"]).replace(tzinfo=None)
        elapsed = int(((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)) - ci_dt).total_seconds() / 60)
        
        st.warning(f"⏱️ Đang thi công ({elapsed} phút)")
        
        pest_found = st.text_area("Côn trùng phát hiện / Ghi chú", value=log.get("ket_qua", ""), height=80)
        chemical   = st.text_area("Hóa chất sử dụng", value=log.get("hoa_chat", ""), height=80)
        
        if st.button("✅ HOÀN THÀNH & CHECK-OUT", type="primary", use_container_width=True):
            conn = get_connection()
            conn.execute("""UPDATE logbook 
                            SET checkout_time=?, ket_qua=?, hoa_chat=? 
                            WHERE id=?""",
                         ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).isoformat(), pest_found, chemical, log["id"]))
            conn.commit(); conn.close()
            
            # Dùng engine để hoàn thành ca, tự sinh ca kế tiếp và sinh công nợ
            from utils.schedule_engine import complete_schedule as cs_fn
            conn_ct = get_connection()
            ct_row = conn_ct.execute('SELECT * FROM contracts WHERE ma_hd=?', (job['ma_hd'],)).fetchone()
            conn_ct.close()
            
            if ct_row:
                cs_fn(job['id'], dict(ct_row))
                
            st.rerun()

def render():
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    
    # 1. Màn hình chọn KTV (Đăng nhập)
    if "mobile_ktv" not in st.session_state:
        st.session_state.mobile_ktv = None
        
    conn = get_connection()
    ktv_list = [r["ten"] for r in conn.execute("SELECT ten FROM technicians WHERE active=1 ORDER BY ten").fetchall()]
    conn.close()
    
    if not st.session_state.mobile_ktv:
        st.markdown('<div class="mobile-card" style="margin-top: 40px;">', unsafe_allow_html=True)
        st.markdown('<div class="mobile-header">👨‍🔧 Kỹ Thuật Viên</div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#64748b;'>Vui lòng chọn tên của bạn để bắt đầu ca làm việc.</p>", unsafe_allow_html=True)
        
        options = ktv_list if ktv_list else ["(Chưa có KTV)"]
        selected_ktv = st.selectbox("Tên của bạn", options, label_visibility="collapsed")
        if st.button("🚀 Bắt đầu ca làm việc", type="primary", use_container_width=True):
            if selected_ktv and selected_ktv != "(Chưa có KTV)":
                st.session_state.mobile_ktv = selected_ktv
                st.rerun()
            else:
                st.error("Chưa có KTV nào trong hệ thống!")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # 2. Màn hình chính của KTV
    ktv = st.session_state.mobile_ktv
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:10px 0;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">👋 Chào, {ktv}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Đăng xuất", key="logout_mobile"):
        st.session_state.mobile_ktv = None
        if st.session_state.get("auth_role") == "ktv":
            st.session_state.authenticated = False
            st.session_state.auth_role = None
        st.rerun()
        
    st.markdown('<hr style="margin: 10px 0 20px 0; border-color: #e2e8f0;">', unsafe_allow_html=True)

    # Lấy dữ liệu ca
    now_dt = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
    past3_str = (now_dt - timedelta(days=3)).strftime("%Y-%m-%d")
    tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = get_connection()
    q = f"""SELECT s.*, c.ten_cty, c.dia_chi, c.sdt,
                   l.checkout_time as co_time, l.checkin_time, l.ket_qua, l.hoa_chat, l.id as log_id
            FROM schedules s
            JOIN customers c ON s.ma_kh = c.ma_kh
            LEFT JOIN logbook l ON l.schedule_id = s.id
            WHERE  s.ngay_du_kien BETWEEN ? AND ?
            ORDER BY s.ngay_du_kien ASC, s.gio_bat_dau ASC"""
    all_jobs = conn.execute(q, (past3_str, tomorrow_str)).fetchall()
    
    my_jobs = []
    today_str = now_dt.strftime("%Y-%m-%d")
    yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    
    for r in all_jobs:
        job = dict(r)
        assigned_ktv = job.get("ky_thuat_vien")
        
        # 1. Chỉ lấy ca của mình hoặc ca chưa ai nhận
        if assigned_ktv and assigned_ktv != ktv:
            continue
            
        is_completed = bool(job.get("co_time") or job.get("trang_thai") == "completed")
        sch_date = job["ngay_du_kien"]
        
        # 2. Quyết định hiển thị
        show_job = False
        
        if sch_date >= today_str:
            # Ca hôm nay hoặc tương lai (ngày mai) -> luôn hiện
            show_job = True
        elif not is_completed and sch_date >= yesterday_str:
            # Ca hôm qua chưa hoàn thành (bị quá hạn) -> hiện để xử lý
            show_job = True
        elif is_completed:
            if job.get("co_time"):
                try:
                    co_dt = datetime.fromisoformat(job["co_time"])
                    if co_dt.tzinfo is not None: co_dt = co_dt.replace(tzinfo=None)
                    if (now_dt - co_dt).total_seconds() <= 6 * 3600:
                        show_job = True
                except: pass
            elif sch_date == today_str:
                show_job = True
        elif job.get("checkin_time") and not is_completed:
            # Ca đang thi công từ mấy hôm trước (quên checkout) -> luôn hiện
            show_job = True

        if show_job:
            my_jobs.append(job)

    if not my_jobs:
        st.markdown("""
        <div class="mobile-card" style="text-align:center;padding:40px 20px;">
            <div style="font-size:40px;margin-bottom:10px;">🎉</div>
            <div style="font-size:18px;font-weight:700;color:#166534;">Bạn không có ca nào đang chờ!</div>
            <div style="font-size:14px;color:#64748b;margin-top:5px;">Tuyệt vời, hãy nghỉ ngơi nhé.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='font-weight:700;color:#64748b;margin-bottom:12px;'>BẠN CÓ {len(my_jobs)} CA SẮP TỚI</div>", unsafe_allow_html=True)
        
        for job in my_jobs:
            # Dữ liệu log đã được JOIN sẵn từ câu lệnh SQL chính
            log = {"id": job["log_id"], "checkin_time": job["checkin_time"], "checkout_time": job["co_time"], "ket_qua": job["ket_qua"], "hoa_chat": job["hoa_chat"]} if job["log_id"] else None
            
            # Phân tích trạng thái
            is_completed = bool(job.get("co_time") or job.get("trang_thai") == "completed")
            is_active = bool(log and not log.get("checkout_time")) and not is_completed
            
            _sch_d = date.fromisoformat(job["ngay_du_kien"])
            _h, _m = 8, 0
            try: _h, _m = map(int, (job["gio_bat_dau"] or "08:00").split(":"))
            except: pass
            _start = datetime(_sch_d.year, _sch_d.month, _sch_d.day, _h, _m)
            is_overdue = ((_start - now_dt).total_seconds() / 3600) < -24 and not is_completed
            
            bg_color = "#e2e8f0" if is_completed else ("#fffbeb" if is_active else ("#fef2f2" if is_overdue else "white"))
            border_color = "#cbd5e1" if is_completed else ("#f59e0b" if is_active else ("#ef4444" if is_overdue else "#e2e8f0"))
            
            badge_html = ""
            if is_completed: badge_html = '<div class="status-badge" style="background:#22c55e;color:white;">✅ Đã hoàn thành</div>'
            elif is_active: badge_html = '<div class="status-badge" style="background:#f59e0b;color:white;">⏱️ Đang thi công</div>'
            elif is_overdue: badge_html = '<div class="status-badge" style="background:#ef4444;color:white;">⚠️ Quá ca</div>'
            
            badge_str = f" {badge_html}" if badge_html else ""
            
            date_str = ""
            if not is_completed:
                try:
                    _d = date.fromisoformat(job['ngay_du_kien'])
                    date_str = f" <span style='font-size:16px;color:#64748b;'>({_d.strftime('%d/%m')})</span>"
                except: pass

            st.markdown(f"""
            <div class="mobile-card" style="background:{bg_color};border-color:{border_color};">
                <div class="shift-time">{job['gio_bat_dau']} - {job['gio_ket_thuc']}{date_str}</div>
                <div class="shift-company">🏢 {job['ten_cty']}</div>{badge_str}
                <div class="shift-address">
                    📍 {str(job['dia_chi']).replace(chr(10), ' ') if job['dia_chi'] else 'Chưa có địa chỉ'}<br>
                    📞 {job['sdt'] or 'Chưa có SĐT'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Buttons actions
            if not is_completed:
                btn_label = "✅ Hoàn Thành Ca" if is_active else "📍 Bắt Đầu (Check-in)"
                btn_type = "primary"
                
                if st.button(btn_label, key=f"btn_{job['id']}", type=btn_type, use_container_width=True):
                    action_dialog(job, log)
                
    conn.close()
