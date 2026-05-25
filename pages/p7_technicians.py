import streamlit as st
from utils.database import get_connection

def render():
    st.markdown('<div class="main-header"><h2>👷 Quản Lý Kỹ Thuật Viên</h2></div>', unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["📋 Danh Sách KTV", "➕ Thêm KTV"])

    # ===== DANH SÁCH =====
    with tab_list:
        conn = get_connection()
        ktvs = conn.execute("SELECT * FROM technicians ORDER BY ma_ktv").fetchall()
        
        if not ktvs:
            st.info("Chưa có kỹ thuật viên nào.")
        else:
            for r in ktvs:
                with st.container():
                    st.markdown(f"""
                    <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="font-size:16px;font-weight:700;color:#0f172a;">{r['ten']} <span style="font-size:12px;color:#64748b;font-weight:normal;">({r['ma_ktv']})</span></div>
                                <div style="font-size:13px;color:#64748b;margin-top:4px;">📞 {r['sdt'] or 'Chưa cập nhật'}</div>
                            </div>
                            <div>
                                <span style="padding:4px 10px;border-radius:99px;font-size:12px;font-weight:600;
                                      background:{'#dcfce7' if r['active'] else '#fee2e2'};color:{'#166534' if r['active'] else '#991b1b'};">
                                    {'Đang làm việc' if r['active'] else 'Đã nghỉ'}
                                </span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander(f"✏️ Sửa / Xóa {r['ma_ktv']}"):
                        with st.form(f"form_edit_{r['ma_ktv']}"):
                            c1, c2, c3 = st.columns(3)
                            with c1: e_ten = st.text_input("Tên KTV", value=r['ten'])
                            with c2: e_sdt = st.text_input("SĐT", value=r['sdt'] or "")
                            with c3: e_act = st.selectbox("Trạng thái", ["Đang làm việc", "Đã nghỉ"], index=0 if r['active'] else 1)
                            
                            col_save, col_del = st.columns([1,1])
                            with col_save:
                                if st.form_submit_button("💾 Lưu"):
                                    if e_sdt and not e_sdt.isdigit():
                                        st.error("⚠️ Số điện thoại chỉ được nhập số!")
                                    else:
                                        conn_edit = get_connection()
                                        conn_edit.execute("UPDATE technicians SET ten=?, sdt=?, active=? WHERE ma_ktv=?",
                                                          (e_ten, e_sdt, 1 if e_act=="Đang làm việc" else 0, r['ma_ktv']))
                                        conn_edit.commit(); conn_edit.close()
                                        st.success("Đã cập nhật!"); st.rerun()
                            with col_del:
                                xac_nhan_xoa = st.checkbox("Xác nhận xóa KTV này", key=f"del_chk_{r['ma_ktv']}")
                                if st.form_submit_button("🗑️ Xóa"):
                                    if xac_nhan_xoa:
                                        conn_del = get_connection()
                                        conn_del.execute("DELETE FROM technicians WHERE ma_ktv=?", (r['ma_ktv'],))
                                        conn_del.commit(); conn_del.close()
                                        st.success("Đã xóa!"); st.rerun()
                                    else:
                                        st.warning("Vui lòng check xác nhận xóa!")
        conn.close()

    # ===== THÊM MỚI =====
    with tab_add:
        st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:24px;">', unsafe_allow_html=True)
        st.markdown("**📝 Thông Tin Kỹ Thuật Viên Mới**")
        with st.form("form_add_ktv", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ma_ktv = st.text_input("Mã KTV *", placeholder="VD: KTV001")
                ten = st.text_input("Tên Kỹ Thuật Viên *", placeholder="Nguyễn Văn A")
            with c2:
                sdt = st.text_input("Số Điện Thoại", placeholder="0901234567")
                active = st.selectbox("Trạng thái", ["Đang làm việc", "Đã nghỉ"])
                
            if st.form_submit_button("➕ Thêm KTV", use_container_width=True):
                if not ma_ktv or not ten:
                    st.error("⚠️ Mã KTV và Tên KTV là bắt buộc!")
                elif sdt and not sdt.isdigit():
                    st.error("⚠️ Số điện thoại chỉ được nhập số!")
                else:
                    try:
                        conn2 = get_connection()
                        conn2.execute("INSERT INTO technicians (ma_ktv, ten, sdt, active) VALUES (?,?,?,?)",
                                      (ma_ktv.strip(), ten.strip(), sdt.strip(), 1 if active=="Đang làm việc" else 0))
                        conn2.commit(); conn2.close()
                        st.success(f"✅ Đã thêm KTV {ten}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
