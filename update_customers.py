import re

filepath = r"c:\Users\nguye\Downloads\vhs_crm_v4 (2)\vhs_crm\VHSCRM\pages\p1_customers.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Define the helper function to insert
helper_func = """def render():
    st.markdown(section_header("Quản lý Khách Hàng", "Thêm mới · Cập nhật · Theo dõi lịch sử", "<i class=\"ph-users\" style=\"font-size:15px;color:#6366f1;vertical-align:middle;line-height:1;margin-right:3px;\"></i>"), unsafe_allow_html=True)

    def render_edit_popover(r, suffix):
        with st.popover("✏️ Sửa"):
            with st.form(f"edit_{r['ma_kh']}_{suffix}"):
                ten = st.text_input("Tên công ty", value=r["ten_cty"], key=f"ten_{r['ma_kh']}_{suffix}")
                dd  = st.text_input("Đại diện", value=r["dai_dien"] or "", key=f"dd_{r['ma_kh']}_{suffix}")
                sp  = st.text_input("SĐT", value=r["sdt"] or "", key=f"sp_{r['ma_kh']}_{suffix}")
                da  = st.text_input("Địa chỉ", value=r["dia_chi"] or "", key=f"da_{r['ma_kh']}_{suffix}")
                gc  = st.text_area("Ghi chú", value=r["ghi_chu"] or "", key=f"gc_{r['ma_kh']}_{suffix}", height=60)
                
                if st.form_submit_button("💾 Lưu Cập Nhật", type="primary", use_container_width=True):
                    if sp and not sp.isdigit():
                        st.error("! Số điện thoại chỉ được nhập số!")
                    else:
                        try:
                            conn2 = get_connection()
                            conn2.execute("UPDATE customers SET ten_cty=?,dai_dien=?,sdt=?,dia_chi=?,ghi_chu=? WHERE ma_kh=?",
                                          (ten,dd,sp,da,gc,r["ma_kh"]))
                            conn2.commit(); conn2.close()
                            st.success("✓ Đã cập nhật!"); st.rerun()
                        except Exception as e: st.error(e)
                
                st.markdown("---")
                msg_del = "Xác nhận xóa (bao gồm cả HĐ và Lịch)" if r["so_hd"] else "Xác nhận xóa Khách Hàng này"
                xac_nhan = st.checkbox(msg_del, key=f"xac_nhan_{r['ma_kh']}_{suffix}")
                if st.form_submit_button("🗑️ Xóa Khách Hàng", use_container_width=True):
                    if xac_nhan:
                        try:
                            conn2 = get_connection()
                            conn2.execute("DELETE FROM logbook WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.execute("DELETE FROM schedules WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.execute("DELETE FROM contracts WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.execute("DELETE FROM customers WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.commit(); conn2.close()
                            st.success("Đã xóa Khách Hàng và các HĐ/Lịch liên quan!"); st.rerun()
                        except Exception as e: st.error(e)
                    else:
                        st.warning("Vui lòng check 'Xác nhận xóa' trước khi bấm Xóa.")

    tab_list, tab_add = st.tabs(["📋 Danh Sách Khách Hàng", "➕ Thêm Mới"])"""

# Replace the beginning of render()
content = re.sub(r'def render\(\):\n\s*st\.markdown\(section_header\("Quản lý Khách Hàng", "Thêm mới · Cập nhật · Theo dõi lịch sử", "👥"\), unsafe_allow_html=True\)\n\n\s*tab_list, tab_add = st\.tabs\(\["📋 Danh Sách Khách Hàng", "➕ Thêm Mới"\]\)', helper_func, content)

# Replace the filter row
filter_old = """        c1, c2, c3 = st.columns([3, 1, 1])
        with c1: search = st.text_input("🔍 Tìm kiếm", placeholder="Tên công ty, mã KH, số điện thoại...")
        with c2: filter_pk = st.selectbox("Phân khúc", ["Tất cả","Nhà hàng", "Khách sạn", "Căn hộ/Biệt thự", "KCC", "Nhà Kho/Xưởng"])
        with c3: sort_by = st.selectbox("Sắp xếp", ["Mã KH","Tên A-Z","Mới nhất"])"""

filter_new = """        c1, c2, c3, c4 = st.columns([2.5, 1.2, 1, 1])
        with c1: search = st.text_input("🔍 Tìm kiếm", placeholder="Tên công ty, mã KH, số điện thoại...")
        with c2: filter_pk = st.selectbox("Phân khúc", ["Tất cả","Nhà hàng", "Khách sạn", "Căn hộ/Biệt thự", "KCC", "Nhà Kho/Xưởng"])
        with c3: sort_by = st.selectbox("Sắp xếp", ["Mã KH","Tên A-Z","Mới nhất"])
        with c4: view_mode = st.selectbox("Hiển thị", ["Dạng Thẻ", "Dạng Dòng"])"""

content = content.replace(filter_old, filter_new)

# Replace the layout
layout_old = """        # Grid card layout
        cols = st.columns(3)
        for i, r in enumerate(rows):
            with cols[i % 3]:
                pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                pk_color = pk_colors.get(r["phan_khuc"], "gray")
                hd_text = f"{r['so_hd']} HĐ active" if r["so_hd"] else "Chưa có HĐ"
                hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"

                with st.container(border=True):
                    st.markdown(f\"\"\"
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
<div style="width:40px;height:40px;border-radius:10px;
            background:linear-gradient(135deg,#16a34a20,#16a34a10);
            display:flex;align-items:center;justify-content:center;
            font-size:18px;">🏢</div>
{badge(r["phan_khuc"], pk_color)}
</div>
<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:2px;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r["ten_cty"]}</div>
<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">{r["ma_kh"]}</div>
<div style="font-size:12px;color:#64748b;line-height:1.8;">
{'👤 ' + r["dai_dien"] if r["dai_dien"] else ''}{'<br>' if r["dai_dien"] else ''}
{'📞 ' + r["sdt"] if r["sdt"] else ''}
</div>
\"\"\", unsafe_allow_html=True)

                    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
                    with c1:
                        st.markdown(f'<div style="font-size:12px;font-weight:600;color:{hd_color};margin-top:8px;">📄 {hd_text}</div>', unsafe_allow_html=True)
                    with c2:
                        with st.popover("✏️ Sửa"):
                            with st.form(f"edit_{r['ma_kh']}"):
                                ten = st.text_input("Tên công ty", value=r["ten_cty"], key=f"ten_{r['ma_kh']}")
                                dd  = st.text_input("Đại diện", value=r["dai_dien"] or "", key=f"dd_{r['ma_kh']}")
                                sp  = st.text_input("SĐT", value=r["sdt"] or "", key=f"sp_{r['ma_kh']}")
                                da  = st.text_input("Địa chỉ", value=r["dia_chi"] or "", key=f"da_{r['ma_kh']}")
                                gc  = st.text_area("Ghi chú", value=r["ghi_chu"] or "", key=f"gc_{r['ma_kh']}", height=60)
                                
                                if st.form_submit_button("💾 Lưu Cập Nhật", type="primary", use_container_width=True):
                                    if sp and not sp.isdigit():
                                        st.error("! Số điện thoại chỉ được nhập số!")
                                    else:
                                        try:
                                            conn2 = get_connection()
                                            conn2.execute("UPDATE customers SET ten_cty=?,dai_dien=?,sdt=?,dia_chi=?,ghi_chu=? WHERE ma_kh=?",
                                                          (ten,dd,sp,da,gc,r["ma_kh"]))
                                            conn2.commit(); conn2.close()
                                            st.success("✓ Đã cập nhật!"); st.rerun()
                                        except Exception as e: st.error(e)
                                
                                st.markdown("---")
                                msg_del = "Xác nhận xóa (bao gồm cả HĐ và Lịch)" if r["so_hd"] else "Xác nhận xóa Khách Hàng này"
                                xac_nhan = st.checkbox(msg_del, key=f"xac_nhan_{r['ma_kh']}")
                                if st.form_submit_button("🗑️ Xóa Khách Hàng", use_container_width=True):
                                    if xac_nhan:
                                        try:
                                            conn2 = get_connection()
                                            conn2.execute("DELETE FROM logbook WHERE ma_kh=?", (r["ma_kh"],))
                                            conn2.execute("DELETE FROM schedules WHERE ma_kh=?", (r["ma_kh"],))
                                            conn2.execute("DELETE FROM contracts WHERE ma_kh=?", (r["ma_kh"],))
                                            conn2.execute("DELETE FROM customers WHERE ma_kh=?", (r["ma_kh"],))
                                            conn2.commit(); conn2.close()
                                            st.success("Đã xóa Khách Hàng và các HĐ/Lịch liên quan!"); st.rerun()
                                        except Exception as e: st.error(e)
                                    else:
                                        st.warning("Vui lòng check 'Xác nhận xóa' trước khi bấm Xóa.")"""

layout_new = """        if view_mode == "Dạng Thẻ":
            # Grid card layout
            cols = st.columns(3)
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                    pk_color = pk_colors.get(r["phan_khuc"], "gray")
                    hd_text = f"{r['so_hd']} HĐ active" if r["so_hd"] else "Chưa có HĐ"
                    hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"
    
                    with st.container(border=True):
                        st.markdown(f\"\"\"
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
<div style="width:40px;height:40px;border-radius:10px;
            background:linear-gradient(135deg,#16a34a20,#16a34a10);
            display:flex;align-items:center;justify-content:center;
            font-size:18px;">🏢</div>
{badge(r["phan_khuc"], pk_color)}
</div>
<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:2px;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r["ten_cty"]}</div>
<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">{r["ma_kh"]}</div>
<div style="font-size:12px;color:#64748b;line-height:1.8;">
{'👤 ' + r["dai_dien"] if r["dai_dien"] else ''}{'<br>' if r["dai_dien"] else ''}
{'📞 ' + r["sdt"] if r["sdt"] else ''}
</div>
\"\"\", unsafe_allow_html=True)
    
                        c_hd, c_act = st.columns([3, 1], vertical_alignment="bottom")
                        with c_hd:
                            st.markdown(f'<div style="font-size:12px;font-weight:600;color:{hd_color};margin-top:8px;">📄 {hd_text}</div>', unsafe_allow_html=True)
                        with c_act:
                            render_edit_popover(r, "grid")
        else:
            # List layout
            for r in rows:
                pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                pk_color = pk_colors.get(r["phan_khuc"], "gray")
                hd_text = f"{r['so_hd']} HĐ" if r["so_hd"] else "0 HĐ"
                hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"

                with st.container(border=True):
                    lc1, lc2, lc3, lc4, lc5 = st.columns([2, 1.5, 1.5, 1, 0.5], vertical_alignment="center")
                    with lc1:
                        st.markdown(f'<div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"><b style="color:#0f172a;font-size:14px;">{r["ten_cty"]}</b><br><span style="font-size:11px;color:#64748b;">{r["ma_kh"]}</span></div>', unsafe_allow_html=True)
                    with lc2:
                        dd = r["dai_dien"] or ""
                        sdt = r["sdt"] or ""
                        sep = " - " if (dd and sdt) else ""
                        st.markdown(f'<div style="font-size:12px;color:#475569;">👤 {dd}{sep}📞 {sdt}</div>' if (dd or sdt) else '<div style="font-size:12px;color:#94a3b8;">—</div>', unsafe_allow_html=True)
                    with lc3:
                        st.markdown(badge(r["phan_khuc"], pk_color), unsafe_allow_html=True)
                    with lc4:
                        st.markdown(f'<div style="font-size:12px;font-weight:600;color:{hd_color};">📄 {hd_text}</div>', unsafe_allow_html=True)
                    with lc5:
                        render_edit_popover(r, "list")"""

content = content.replace(layout_old, layout_new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
