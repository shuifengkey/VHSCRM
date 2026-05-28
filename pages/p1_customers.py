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
    
    /* Refined popover button for Edit */
    div[data-testid="stPopover"] > button {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        color: #475569 !important;
        padding: 4px 8px !important;
        min-height: 32px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stPopover"] > button:hover {
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
        color: #0f172a !important;
    }
    div[data-testid="stPopover"] > button p {
        font-size: 13px !important;
    }
    .align-right { display: none; }
    </style>
    """, unsafe_allow_html=True)

    def render_edit_popover(r, suffix):
        with st.popover("✏️", use_container_width=False):
            with st.form(f"edit_{r['ma_kh']}_{suffix}"):
                st.markdown("##### 👤 Thông Tin Chung")
                ten = st.text_input("Tên Khách Hàng", value=r["ten_cty"], key=f"ten_{r['ma_kh']}_{suffix}")
                
                st.markdown("##### 📞 Liên Hệ")
                lh  = st.text_input("Người liên hệ", value=r.get("nguoi_lien_he", "") or "", key=f"lh_{r['ma_kh']}_{suffix}")
                sp  = st.text_input("SĐT", value=r["sdt"] or "", key=f"sp_{r['ma_kh']}_{suffix}")
                
                st.markdown("##### ⚖️ Pháp Lý")
                tpl = st.text_input("Tên công ty (Pháp lý)", value=r.get("ten_phap_ly", "") or "", key=f"tpl_{r['ma_kh']}_{suffix}")
                mst = st.text_input("Mã số thuế", value=r.get("ma_so_thue", "") or "", key=f"mst_{r['ma_kh']}_{suffix}")
                dd  = st.text_input("Người đại diện", value=r["dai_dien"] or "", key=f"dd_{r['ma_kh']}_{suffix}")
                dc_pl = st.text_input("Địa chỉ pháp lý", value=r.get("dia_chi_phap_ly", "") or "", key=f"dcpl_{r['ma_kh']}_{suffix}")
                da  = st.text_input("Địa chỉ thi công/liên hệ", value=r["dia_chi"] or "", key=f"da_{r['ma_kh']}_{suffix}")
                
                gc  = st.text_area("Ghi chú", value=r["ghi_chu"] or "", key=f"gc_{r['ma_kh']}_{suffix}", height=60)

                if st.form_submit_button("💾 Lưu Cập Nhật", type="primary", use_container_width=True):
                    sp_clean = ''.join(filter(str.isdigit, sp)) if sp else ""
                    try:
                        conn2 = get_connection()
                        conn2.execute("UPDATE customers SET ten_cty=?,dai_dien=?,sdt=?,dia_chi=?,ghi_chu=?,nguoi_lien_he=?,ten_phap_ly=?,ma_so_thue=?,dia_chi_phap_ly=? WHERE ma_kh=?",
                                      (ten,dd,sp_clean,da,gc,lh,tpl,mst,dc_pl,r["ma_kh"]))
                        conn2.commit(); conn2.close()
                        import time
                        st.toast(f"✅ Đã lưu cập nhật cho {ten}!", icon="🎉")
                        st.balloons()
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e: st.error(e)
                
                st.markdown("---")
                msg_del = "Xác nhận xóa (bao gồm cả HĐ và Lịch)" if r["so_hd"] else "Xác nhận xóa Khách Hàng này"
                xac_nhan = st.checkbox(msg_del, key=f"xac_nhan_{r['ma_kh']}_{suffix}")
                if st.form_submit_button("🗑️ Xóa Khách Hàng", use_container_width=True):
                    if st.session_state.get('auth_role') != 'admin':
                        st.error("❌ Chỉ Admin mới có quyền xóa dữ liệu!")
                    elif xac_nhan:
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

        raw_rows = conn.execute(query, params).fetchall()
        conn.close()
        
        import html
        rows = []
        for r in raw_rows:
            d = dict(r)
            d["ten_cty"] = html.escape(d["ten_cty"] or "")
            d["dai_dien"] = html.escape(d["dai_dien"] or "")
            d["sdt"] = html.escape(d["sdt"] or "")
            d["dia_chi"] = html.escape(d["dia_chi"] or "")
            d["ghi_chu"] = html.escape(d["ghi_chu"] or "")
            rows.append(d)

        # Tổng số đếm
        st.markdown(f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;">Tìm thấy <b style="color:#0f172a">{len(rows)}</b> khách hàng</div>', unsafe_allow_html=True)

        if not rows:
            st.markdown(card('<div style="text-align:center;padding:32px;color:#94a3b8;">😔 Không tìm thấy kết quả nào</div>'), unsafe_allow_html=True)

        if view_mode == "Dạng Thẻ":
            # Grid card layout
            cols = st.columns(3, gap="large")
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                    pk_color = pk_colors.get(r["phan_khuc"], "gray")
                    hd_text = f"{r['so_hd']} HĐ active" if r["so_hd"] else "Chưa có HĐ"
                    hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"
    
                    with st.container(border=True):
                        char = r["ten_cty"][0].upper() if r["ten_cty"] else 'C'
                        st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; gap:8px;">
    <div style="display:flex; align-items:center; gap:10px; min-width:0; flex:1;">
        <img src="https://api.dicebear.com/9.x/adventurer/svg?seed={r['ma_kh']}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffdfbf,ffd5dc" style="width:40px; height:40px; min-width:40px; border-radius:50%; box-shadow:0 2px 4px rgba(0,0,0,0.1); object-fit:cover;" alt="avatar">
        <div style="min-width:0; flex:1;">
            <div style="font-size:14px; font-weight:700; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{r["ten_cty"]}">{r["ten_cty"]}</div>
            <div style="font-size:11px; font-weight:600; color:#64748b; background:#f1f5f9; padding:2px 6px; border-radius:4px; display:inline-block; margin-top:4px;">#{r["ma_kh"]}</div>
        </div>
    </div>
    <div style="flex-shrink:0;">{badge(r["phan_khuc"], pk_color)}</div>
</div>
<div style="background:#f8fafc; border-radius:8px; padding:10px; margin-bottom:12px; border:1px solid #e2e8f0;">
    <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:#475569; margin-bottom:6px;" title="Liên hệ">
        <span style="background:#e0e7ff; color:#4338ca; border-radius:4px; padding:2px 5px; font-size:11px;">👤</span>
        <b style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{r.get("nguoi_lien_he") or "Chưa có NLH"}</b>
    </div>
    <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:#475569; margin-bottom:6px;" title="SĐT">
        <span style="background:#dcfce7; color:#15803d; border-radius:4px; padding:2px 5px; font-size:11px;">📞</span>
        <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{r["sdt"] or "Chưa có SĐT"}</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:#475569; padding-top:6px; border-top:1px dashed #cbd5e1;" title="Pháp lý">
        <span style="background:#fef08a; color:#a16207; border-radius:4px; padding:2px 5px; font-size:11px;">⚖️</span>
        <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:11px;">{r.get("ten_phap_ly") or r["ten_cty"]} | {r.get("ma_so_thue") or "Chưa có MST"}</span>
    </div>
</div>
""", unsafe_allow_html=True)
    
                        c_hd, c_act = st.columns([3, 1], vertical_alignment="center")
                        with c_hd:
                            hd_bg = "#dcfce7" if r["so_hd"] else "#f1f5f9"
                            hd_col = "#16a34a" if r["so_hd"] else "#64748b"
                            icon = "📄" if r["so_hd"] else "📁"
                            st.markdown(f'<div style="background:{hd_bg}; color:{hd_col}; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; display:inline-flex; align-items:center; gap:6px;"><span>{icon}</span> {hd_text}</div>', unsafe_allow_html=True)
                        with c_act:
                            st.markdown('<div class="align-right"></div>', unsafe_allow_html=True)
                            render_edit_popover(r, "grid")
                    st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)
        else:
            # List layout
            st.markdown("""
            <style>
            /* Slim down padding for List view boxes */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.vhs-list-marker) {
                padding-top: 0.2rem !important;
                padding-bottom: 0.2rem !important;
            }
            </style>
            """, unsafe_allow_html=True)
            for r in rows:
                pk_colors = {"Nhà hàng":"orange", "Khách sạn":"blue", "Căn hộ/Biệt thự":"green", "KCC":"purple", "Nhà Kho/Xưởng":"gray"}
                pk_color = pk_colors.get(r["phan_khuc"], "gray")
                hd_text = f"{r['so_hd']} HĐ" if r["so_hd"] else "0 HĐ"
                hd_color = "#16a34a" if r["so_hd"] else "#94a3b8"

                with st.container(border=True):
                    lc1, lc2, lc3, lc4, lc5 = st.columns([2, 1.5, 1.5, 1, 0.7], vertical_alignment="center")
                    with lc1:
                        st.markdown(f'<div class="vhs-list-marker" style="display:none;"></div><div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"><b style="color:#0f172a;font-size:14px;">{r["ten_cty"]}</b><br><span style="font-size:11px;color:#64748b;">{r["ma_kh"]}</span></div>', unsafe_allow_html=True)
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
                st.markdown("<div style='height: 2px'></div>", unsafe_allow_html=True)

    # ===== THÊM MỚI =====
    with tab_add:
        col_form, _ = st.columns([2, 1])
        with col_form:
            st.markdown('<div class="vhs-card">', unsafe_allow_html=True)
            st.markdown("**📝 Thông Tin Khách Hàng Mới**")
            st.markdown('<hr style="margin:12px 0">', unsafe_allow_html=True)
            if st.session_state.get("add_kh_success"):
                st.toast(st.session_state.add_kh_success, icon="✅")
                st.balloons()
                st.session_state.add_kh_success = None
                
            with st.form("form_add_kh", clear_on_submit=True):
                st.markdown("##### 👤 Thông Tin Khách Hàng (Tên gọi/Thương hiệu)")
                c1, c2 = st.columns(2)
                with c1:
                    ma_kh  = st.text_input("Mã KH *", placeholder="VD: KH007")
                    ten    = st.text_input("Tên Khách Hàng *", placeholder="VD: Lão Trư BBQ")
                with c2:
                    pk     = st.selectbox("Phân Khúc", ["Nhà hàng", "Khách sạn", "Căn hộ/Biệt thự", "KCC", "Nhà Kho/Xưởng", "Văn phòng", "Khác"])
                
                st.markdown("##### 📞 Mục Người Liên Hệ")
                c3, c4 = st.columns(2)
                with c3:
                    nguoi_lh = st.text_input("Người Liên Hệ", placeholder="Nguyễn Văn A")
                with c4:
                    sdt    = st.text_input("Số Điện Thoại", placeholder="090xxxxxxx")
                    
                st.markdown("##### ⚖️ Thông Tin Pháp Lý")
                ten_pl = st.text_input("Tên Công Ty (Pháp lý)", placeholder="Công ty TNHH ABC")
                c5, c6 = st.columns(2)
                with c5:
                    mst = st.text_input("Mã Số Thuế", placeholder="0312345678")
                with c6:
                    dai_dien = st.text_input("Người Đại Diện", placeholder="Trần Văn B")
                dia_chi_pl = st.text_input("Địa Chỉ Pháp Lý", placeholder="Ghi trên ĐKKD/MST")
                dia_chi = st.text_input("Địa Chỉ Thi Công/Liên Hệ", placeholder="Số nhà, đường, phường, quận, TP")
                
                st.markdown("##### 📝 Khác")
                ghi_chu = st.text_area("Ghi Chú Nội Bộ", placeholder="Thông tin thêm về khách hàng...", height=80)

                submitted = st.form_submit_button("➕ Tạo Khách Hàng Mới", use_container_width=True)
                if submitted:
                    if not ma_kh or not ten:
                        st.error("⚠️ Mã KH và Tên Khách Hàng là bắt buộc!")
                    else:
                        sdt_clean = ''.join(filter(str.isdigit, sdt)) if sdt else ""
                        try:
                            conn = get_connection()
                            conn.execute("INSERT INTO customers (ma_kh,ten_cty,dai_dien,sdt,dia_chi,phan_khuc,ghi_chu,nguoi_lien_he,ten_phap_ly,ma_so_thue,dia_chi_phap_ly) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                         (ma_kh.strip(), ten.strip(), dai_dien, sdt_clean, dia_chi, pk, ghi_chu, nguoi_lh, ten_pl, mst, dia_chi_pl))
                            conn.commit(); conn.close()
                            st.session_state.add_kh_success = f"✅ Đã thêm **{ten}** ({ma_kh})"
                            st.rerun()
                        except Exception as e: st.error(f"❌ {e}")
            st.markdown('</div>', unsafe_allow_html=True)



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
                    text=[f"{int(r['rev'] or 0):,}".replace(",", ".") for r in rev],
                    textposition="outside",
                ))
                fig2.update_layout(
                    height=280, paper_bgcolor="white", plot_bgcolor="white",
                    title=dict(text="Doanh Thu/Tháng theo Phân Khúc (triệu đ)", font=dict(size=14,color="#0f172a")),
                    margin=dict(l=10,r=10,t=40,b=10), font=dict(family="Inter"),
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
