# pages/p1_customers.py - Module Khách Hàng - nâng cấp v2
import streamlit as st
import sys, os

from utils.database import get_connection
from utils.styles import card, badge, section_header, COLORS
from datetime import date
import plotly.graph_objects as go

def render():
    st.markdown(section_header("Quản Lý Khách Hàng", "Master Data — CRUD toàn bộ thông tin khách hàng", "👥"), unsafe_allow_html=True)

    tab_list, tab_add, tab_detail = st.tabs(["📋  Danh Sách", "➕  Thêm Mới", "📊  Phân Tích"])
    
    st.markdown("""
    <style>
    /* Float the Edit button to the right inside its column ONLY on mobile */
    @media (max-width: 768px) {
        div[data-testid="column"]:has(.align-right) div[data-testid="stPopover"] {
            display: flex;
            justify-content: flex-end;
        }
    }
    
    /* Force rows with 4 or more columns (Filters, List View) to stack on screens smaller than 1024px to prevent overlapping */
    @media (max-width: 1024px) {
        div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) {
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 0.5rem !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
        }
    }
    
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
    .align-right { display: none; }
    </style>
    """, unsafe_allow_html=True)

    def render_edit_popover(r, suffix):
        with st.popover("✏️", use_container_width=False):
            with st.form(f"edit_{r['ma_kh']}_{suffix}"):
                ten = st.text_input("Tên công ty", value=r["ten_cty"], key=f"ten_{r['ma_kh']}_{suffix}")
                dd  = st.text_input("Đại diện", value=r["dai_dien"] or "", key=f"dd_{r['ma_kh']}_{suffix}")
                sp  = st.text_input("SĐT", value=r["sdt"] or "", key=f"sp_{r['ma_kh']}_{suffix}")
                da  = st.text_input("Địa chỉ", value=r["dia_chi"] or "", key=f"da_{r['ma_kh']}_{suffix}")
                gc  = st.text_area("Ghi chú", value=r["ghi_chu"] or "", key=f"gc_{r['ma_kh']}_{suffix}", height=60)
                
                if st.form_submit_button("💾 Lưu Cập Nhật", type="primary", use_container_width=True):
                    sp_clean = ''.join(filter(str.isdigit, sp)) if sp else ""
                    try:
                        conn2 = get_connection()
                        conn2.execute("UPDATE customers SET ten_cty=?,dai_dien=?,sdt=?,dia_chi=?,ghi_chu=? WHERE ma_kh=?",
                                      (ten,dd,sp_clean,da,gc,r["ma_kh"]))
                        conn2.commit(); conn2.close()
                        st.success("✅ Đã cập nhật!"); st.rerun()
                    except Exception as e: st.error(e)
                
                st.markdown("---")
                msg_del = "Xác nhận xóa (bao gồm cả HĐ và Lịch)" if r["so_hd"] else "Xác nhận xóa Khách Hàng này"
                xac_nhan = st.checkbox(msg_del, key=f"xac_nhan_{r['ma_kh']}_{suffix}")
                if st.form_submit_button("🗑️ Xóa Khách Hàng", use_container_width=True):
                    if xac_nhan:
                        try:
                            conn2 = get_connection()
                            conn2.execute("DELETE FROM logbook WHERE ma_kh=?", (r["ma_kh"],))
                            
                            to_delete = conn2.execute("SELECT google_event_id FROM schedules WHERE ma_kh=?", (r["ma_kh"],)).fetchall()
                            from utils.google_sync import auto_sync_schedule_to_google
                            for row in to_delete:
                                if row["google_event_id"]:
                                    auto_sync_schedule_to_google(conn2, row["google_event_id"], "delete")
                                    
                            conn2.execute("DELETE FROM schedules WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.execute("DELETE FROM contracts WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.execute("DELETE FROM customers WHERE ma_kh=?", (r["ma_kh"],))
                            conn2.commit(); conn2.close()
                            st.success("Đã xóa Khách Hàng và các HĐ/Lịch liên quan!"); st.rerun()
                        except Exception as e: st.error(e)
                    else:
                        st.warning("Vui lòng check 'Xác nhận xóa' trước khi bấm Xóa.")

    # ===== DANH SÁCH =====
    with tab_list:
        conn = get_connection()
        c1, c2, c3, c4 = st.columns([2.5, 1.2, 1, 1])
        with c1: search = st.text_input("🔍 Tìm kiếm", placeholder="Tên công ty, mã KH, số điện thoại...")
        with c2: filter_pk = st.selectbox("Phân khúc", ["Tất cả","Nhà hàng", "Khách sạn", "Căn hộ/Biệt thự", "KCC", "Nhà Kho/Xưởng"])
        with c3: sort_by = st.selectbox("Sắp xếp", ["Mã KH","Tên A-Z","Mới nhất"])
        with c4: view_mode = st.selectbox("Hiển thị", ["Dạng Thẻ", "Dạng Dòng"])

        query = "SELECT k.*, (SELECT COUNT(*) FROM contracts c WHERE c.ma_kh=k.ma_kh AND c.trang_thai='active') as so_hd FROM customers k WHERE 1=1"
        params = []
        if search:
            query += " AND (ma_kh LIKE ? OR ten_cty LIKE ? OR sdt LIKE ? OR dai_dien LIKE ?)"
            params.extend([f"%{search}%"]*4)
        if filter_pk != "Tất cả":
            query += " AND phan_khuc=?"
            params.append(filter_pk)
        query += {"Mã KH":" ORDER BY ma_kh", "Tên A-Z":" ORDER BY ten_cty", "Mới nhất":" ORDER BY created_at DESC"}.get(sort_by, " ORDER BY ma_kh")

        rows = conn.execute(query, params).fetchall()
        conn.close()

        # Tổng số đếm
        st.markdown(f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;">Tìm thấy <b style="color:#0f172a">{len(rows)}</b> khách hàng</div>', unsafe_allow_html=True)

        if not rows:
            st.markdown(card('<div style="text-align:center;padding:32px;color:#94a3b8;">😔 Không tìm thấy kết quả nào</div>'), unsafe_allow_html=True)

        if view_mode == "Dạng Thẻ":
            # Grid card layout
            cols = st.columns(3)
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                    pk_color = pk_colors.get(r["phan_khuc"], "gray")
                    hd_text = f"{r['so_hd']} HĐ active" if r["so_hd"] else "Chưa có HĐ"
                    hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"
    
                    with st.container(border=True):
                        st.markdown(f"""
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
""", unsafe_allow_html=True)
    
                        c_hd, c_act = st.columns([3, 1], vertical_alignment="bottom")
                        with c_hd:
                            st.markdown(f'<div style="font-size:12px;font-weight:600;color:{hd_color};margin-top:8px;">📄 {hd_text}</div>', unsafe_allow_html=True)
                        with c_act:
                            st.markdown('<div class="align-right"></div>', unsafe_allow_html=True)
                            render_edit_popover(r, "grid")
        else:
            # List layout
            for r in rows:
                pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                pk_color = pk_colors.get(r["phan_khuc"], "gray")
                hd_text = f"{r['so_hd']} HĐ" if r["so_hd"] else "0 HĐ"
                hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"

                with st.container(border=True):
                    lc1, lc2, lc3, lc4, lc5 = st.columns([2, 1.5, 1.5, 1, 0.7], vertical_alignment="center")
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
                        st.markdown('<div class="align-right"></div>', unsafe_allow_html=True)
                        render_edit_popover(r, "list")

    # ===== THÊM MỚI =====
    with tab_add:
        col_form, col_preview = st.columns([2, 1])
        with col_form:
            st.markdown('<div class="vhs-card">', unsafe_allow_html=True)
            st.markdown("**📝 Thông Tin Khách Hàng Mới**")
            st.markdown('<hr style="margin:12px 0">', unsafe_allow_html=True)
            if st.session_state.get("add_kh_success"):
                st.toast(st.session_state.add_kh_success, icon="✅")
                st.balloons()
                st.session_state.add_kh_success = None
                
            with st.form("form_add_kh", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    ma_kh  = st.text_input("Mã KH *", placeholder="VD: KH007")
                    ten    = st.text_input("Tên Công Ty *", placeholder="Công ty TNHH ABC")
                    dai_dien = st.text_input("Người Đại Diện", placeholder="Nguyễn Văn A")
                with c2:
                    sdt    = st.text_input("Số Điện Thoại", placeholder="090xxxxxxx")
                    pk     = st.selectbox("Phân Khúc", ["Nhà hàng", "Khách sạn", "Căn hộ/Biệt thự", "KCC", "Nhà Kho/Xưởng"])
                    email  = st.text_input("Email (tuỳ chọn)", placeholder="contact@company.vn")
                dia_chi = st.text_input("Địa Chỉ Đầy Đủ", placeholder="Số nhà, đường, phường, quận, TP")
                ghi_chu = st.text_area("Ghi Chú Nội Bộ", placeholder="Thông tin thêm về khách hàng...", height=80)

                submitted = st.form_submit_button("➕ Tạo Khách Hàng Mới", use_container_width=True)
                if submitted:
                    if not ma_kh or not ten:
                        st.error("⚠️ Mã KH và Tên công ty là bắt buộc!")
                    else:
                        sdt_clean = ''.join(filter(str.isdigit, sdt)) if sdt else ""
                        try:
                            conn = get_connection()
                            conn.execute("INSERT INTO customers (ma_kh,ten_cty,dai_dien,sdt,dia_chi,phan_khuc,ghi_chu) VALUES (?,?,?,?,?,?,?)",
                                         (ma_kh.strip(), ten.strip(), dai_dien, sdt_clean, dia_chi, pk, ghi_chu))
                            conn.commit(); conn.close()
                            st.session_state.add_kh_success = f"✅ Đã thêm **{ten}** ({ma_kh})"
                            st.rerun()
                        except Exception as e: st.error(f"❌ {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_preview:
            st.markdown(card("""
            <div style="text-align:center;padding:16px 0;">
                <div style="font-size:48px;margin-bottom:12px;">💡</div>
                <div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:8px;">Hướng dẫn</div>
                <div style="font-size:12px;color:#64748b;line-height:1.7;text-align:left;">
                    • <b>Mã KH</b>: Định danh duy nhất (VD: KH001)<br>
                    • <b>Phân khúc</b>:<br>
                    &nbsp;&nbsp;— Nhà hàng, Khách sạn, Căn hộ/Biệt thự, KCC, Nhà Kho/Xưởng<br>
                    • Sau khi tạo KH, vào <b>Hợp Đồng</b> để thiết lập hợp đồng dịch vụ
                </div>
            </div>
            """), unsafe_allow_html=True)

    # ===== PHÂN TÍCH =====
    with tab_detail:
        conn = get_connection()
        seg = conn.execute("SELECT phan_khuc, COUNT(*) cnt FROM customers GROUP BY phan_khuc").fetchall()
        rev = conn.execute("""
            SELECT c.phan_khuc, SUM(ct.gia_tri_thang) rev
            FROM customers c JOIN contracts ct ON c.ma_kh=ct.ma_kh
            WHERE ct.trang_thai='active' GROUP BY c.phan_khuc
        """).fetchall()
        growth = conn.execute("""
            SELECT substr(created_at,1,7) as mo, COUNT(*) cnt
            FROM customers GROUP BY mo ORDER BY mo DESC LIMIT 6
        """).fetchall()
        conn.close()

        if not seg:
            st.info("Chưa có dữ liệu.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                # Donut chart
                fig = go.Figure(go.Pie(
                    labels=[r["phan_khuc"] for r in seg],
                    values=[r["cnt"] for r in seg],
                    hole=.6,
                    marker=dict(colors=["#16a34a","#2563eb","#d97706", "#7c3aed", "#64748b"], line=dict(color="white",width=3)),
                    textinfo="label+value+percent",
                ))
                fig.add_annotation(text=f"<b>{sum(r['cnt'] for r in seg)}</b><br>KH", x=.5, y=.5,
                                   font=dict(size=18, color="#0f172a"), showarrow=False)
                fig.update_layout(height=280, paper_bgcolor="white", showlegend=False,
                                  title=dict(text="Phân Bổ Khách Hàng", font=dict(size=14,color="#0f172a")),
                                  margin=dict(l=10,r=10,t=40,b=10), font=dict(family="Inter"))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

            with col2:
                # Doanh thu theo phân khúc
                fig2 = go.Figure(go.Bar(
                    x=[r["phan_khuc"] for r in rev],
                    y=[r["rev"] for r in rev],
                    marker=dict(color=["#16a34a","#2563eb","#d97706", "#7c3aed", "#64748b"],
                                line=dict(color="white",width=2)),
                    text=[f"{format_money(r[\'rev\'])}" for r in rev],
                    textposition="outside",
                ))
                fig2.update_layout(
                    height=280, paper_bgcolor="white", plot_bgcolor="white",
                    title=dict(text="Doanh Thu/Tháng theo Phân Khúc (triệu đ)", font=dict(size=14,color="#0f172a")),
                    margin=dict(l=10,r=10,t=40,b=10), font=dict(family="Inter"),
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
