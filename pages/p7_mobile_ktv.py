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
            tc = check_time_violation(job["gio_bat_dau"], job["gio_ket_thuc"], datetime.now(timezone(timedelta(hours=7))).isoformat(), job["ngay_du_kien"])
            conn.execute("""INSERT INTO logbook (schedule_id,ma_kh,ky_thuat_vien,checkin_time,canh_bao_gio)
                            VALUES(?,?,?,?,?)""",
                         (job["id"], job["ma_kh"], st.session_state.mobile_ktv, datetime.now(timezone(timedelta(hours=7))).isoformat(), 1 if tc["violation"] else 0))
            conn.execute("UPDATE schedules SET ky_thuat_vien=? WHERE id=?", (st.session_state.mobile_ktv, job["id"]))
            conn.commit(); conn.close()
            st.rerun()
    else:
        # ĐANG THI CÔNG -> CHECK OUT
        ci_dt = datetime.fromisoformat(log["checkin_time"])
        elapsed = int((datetime.now(timezone(timedelta(hours=7))) - ci_dt).total_seconds() / 60)
        
        st.warning(f"⏱️ Đang thi công ({elapsed} phút)")
        
        pest_found = st.text_area("Côn trùng phát hiện / Ghi chú", value=log.get("pest_found", ""), height=80)
        chemical   = st.text_area("Hóa chất sử dụng", value=log.get("chemical_used", ""), height=80)
        
        if st.button("✅ HOÀN THÀNH & CHECK-OUT", type="primary", use_container_width=True):
            conn = get_connection()
            conn.execute("""UPDATE logbook 
                            SET checkout_time=?, pest_found=?, chemical_used=? 
                            WHERE id=?""",
                         (datetime.now(timezone(timedelta(hours=7))).isoformat(), pest_found, chemical, log["id"]))
            conn.execute("UPDATE schedules SET trang_thai='completed' WHERE id=?", (job["id"],))
            conn.commit(); conn.close()
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
        
        selected_ktv = st.selectbox("Tên của bạn", ["(Chọn tên)"] + ktv_list, label_visibility="collapsed")
        if st.button("🚀 Bắt đầu ca làm việc", type="primary", use_container_width=True):
            if selected_ktv != "(Chọn tên)":
                st.session_state.mobile_ktv = selected_ktv
                st.rerun()
            else:
                st.error("Vui lòng chọn tên!")
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
        st.rerun()
        
    st.markdown('<hr style="margin: 10px 0 20px 0; border-color: #e2e8f0;">', unsafe_allow_html=True)

    # Lấy dữ liệu ca
    now_dt = datetime.now(timezone(timedelta(hours=7)))
    past3_str = (now_dt - timedelta(days=3)).strftime("%Y-%m-%d")
    tomorrow_str = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = get_connection()
    q = f"""SELECT s.*, c.ten_cty, c.dia_chi, c.sdt,
                   (SELECT COUNT(*) FROM logbook l WHERE l.schedule_id=s.id) as has_log,
                   (SELECT checkout_time FROM logbook l WHERE l.schedule_id=s.id ORDER BY id DESC LIMIT 1) as co_time
            FROM schedules s
            JOIN customers c ON s.ma_kh = c.ma_kh
            WHERE s.trang_thai != 'completed' AND s.ngay_du_kien BETWEEN ? AND ?
            ORDER BY s.ngay_du_kien ASC, s.gio_bat_dau ASC"""
    all_jobs = conn.execute(q, (past3_str, tomorrow_str)).fetchall()
    
    my_jobs = []
    for r in all_jobs:
        job = dict(r)
        if job["co_time"]: continue # Bỏ qua ca đã hoàn thành
        
        # Kiểm tra tính hợp lệ của ca
        if is_job_active_now(job["ngay_du_kien"], job["gio_bat_dau"], job["gio_ket_thuc"]):
            # Lọc theo KTV
            if job.get("ky_thuat_vien") == ktv or not job.get("ky_thuat_vien"):
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
            log = conn.execute("SELECT * FROM logbook WHERE schedule_id=? ORDER BY id DESC LIMIT 1", (job["id"],)).fetchone()
            log = dict(log) if log else None
            
            # Phân tích trạng thái
            is_active = bool(log and not log.get("checkout_time"))
            
            _sch_d = date.fromisoformat(job["ngay_du_kien"])
            _h, _m = 8, 0
            try: _h, _m = map(int, (job["gio_bat_dau"] or "08:00").split(":"))
            except: pass
            _start = datetime(_sch_d.year, _sch_d.month, _sch_d.day, _h, _m)
            is_overdue = ((_start - now_dt).total_seconds() / 3600) < -24
            
            bg_color = "#fffbeb" if is_active else ("#fef2f2" if is_overdue else "white")
            border_color = "#f59e0b" if is_active else ("#ef4444" if is_overdue else "#e2e8f0")
            
            badge_html = ""
            if is_active: badge_html = '<div class="status-badge" style="background:#f59e0b;color:white;">⏱️ Đang thi công</div>'
            elif is_overdue: badge_html = '<div class="status-badge" style="background:#ef4444;color:white;">⚠️ Quá ca</div>'
            
            badge_str = f"\\n                {badge_html}" if badge_html else ""
            st.markdown(f"""
            <div class="mobile-card" style="background:{bg_color};border-color:{border_color};">
                <div class="shift-time">{job['gio_bat_dau']} - {job['gio_ket_thuc']}</div>
                <div class="shift-company">🏢 {job['ten_cty']}</div>{badge_str}
                <div class="shift-address">
                    📍 {str(job['dia_chi']).replace(chr(10), ' ') if job['dia_chi'] else 'Chưa có địa chỉ'}<br>
                    📞 {job['sdt'] or 'Chưa có SĐT'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Buttons actions
            btn_label = "✅ Hoàn Thành Ca" if is_active else "📍 Bắt Đầu (Check-in)"
            btn_type = "secondary" if is_active else "primary"
            
            if st.button(btn_label, key=f"btn_{job['id']}", type=btn_type, use_container_width=True):
                action_dialog(job, log)
                
    conn.close()
