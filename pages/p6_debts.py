import streamlit as st
import sys, os
from utils.database import get_connection
from utils.styles import badge, section_header, stat_row, COLORS
from datetime import timezone, date, datetime, timedelta
import plotly.graph_objects as go
import pandas as pd

def format_money(val):
    if not val: return "0"
    return f"{int(val):,}".replace(",", ".")

def render():
    st.markdown(section_header("Tài Chính & Kế Toán", "Quản lý dòng tiền, công nợ, hóa đơn VAT và chi phí đầu vào", "💵"), unsafe_allow_html=True)

    tab_overview, tab_debts, tab_invoices, tab_expenses = st.tabs(["📊 Tổng Quan", "📋 Công Nợ", "🧾 Hóa Đơn", "💸 Chi Phí Đầu Vào"])

    with tab_overview:
        conn = get_connection()
        
        # Lấy dữ liệu công nợ
        summary_debt = conn.execute("SELECT SUM(can_thu) tong_ct, SUM(da_thu) tong_dt, SUM(can_thu-da_thu) tong_no FROM debts").fetchone()
        tong_ct = summary_debt["tong_ct"] or 0
        tong_dt = summary_debt["tong_dt"] or 0
        tong_no = summary_debt["tong_no"] or 0
        
        # Lấy dữ liệu chi phí
        summary_exp = conn.execute("SELECT SUM(so_tien) tong_chi FROM expenses").fetchone()
        tong_chi = summary_exp["tong_chi"] or 0
        
        loi_nhuan = tong_dt - tong_chi
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("📬 Tổng Cần Thu", f"{format_money(tong_ct)} đ")
        with c2: st.metric("✅ Thực Thu (Doanh thu)", f"{format_money(tong_dt)} đ")
        with c3: st.metric("💸 Chi Phí Đầu Vào", f"{format_money(tong_chi)} đ")
        with c4: st.metric("📈 Lợi Nhuận Gộp", f"{format_money(loi_nhuan)} đ")
        
        st.markdown('<hr style="margin:16px 0">', unsafe_allow_html=True)
        col_chart, col_top = st.columns([3,2])
        
        with col_chart:
            # Biểu đồ Dòng tiền 6 tháng
            monthly = conn.execute('''
                SELECT k, SUM(dt) dt, SUM(chi) chi FROM (
                    SELECT ky_thanh_toan as k, da_thu as dt, 0 as chi FROM debts
                    UNION ALL
                    SELECT strftime('%Y-%m', ngay_chi) as k, 0 as dt, so_tien as chi FROM expenses
                ) GROUP BY k ORDER BY k DESC LIMIT 6
            ''').fetchall()
            monthly = list(reversed(monthly))
            
            if monthly:
                fig = go.Figure()
                fig.add_scatter(x=[r["k"] for r in monthly], y=[r["dt"] for r in monthly], name="Thu (VND)", line=dict(color="#16a34a",width=3), mode="lines+markers")
                fig.add_scatter(x=[r["k"] for r in monthly], y=[r["chi"] for r in monthly], name="Chi (VND)", line=dict(color="#dc2626",width=3), mode="lines+markers")
                fig.update_layout(height=260, title="Thu Chi 6 Tháng Gần Nhất", margin=dict(l=10,r=10,t=40,b=20), paper_bgcolor="white", plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)
                
        with col_top:
            st.markdown('<div class="vhs-card" style="padding:18px;">', unsafe_allow_html=True)
            st.markdown('**🔴 Top Nợ Tồn Đọng**')
            top_debtors = conn.execute("""
                SELECT d.ma_kh, c.ten_cty, SUM(d.can_thu-d.da_thu) no
                FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh
                WHERE d.can_thu > d.da_thu GROUP BY d.ma_kh ORDER BY no DESC LIMIT 5
            """).fetchall()
            if top_debtors:
                max_no = top_debtors[0]["no"]
                for t in top_debtors:
                    pct = int(t["no"]/max_no*100)
                    st.markdown(f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
                            <span style="font-weight:600;">{t['ten_cty'][:22]}</span>
                            <span style="color:#dc2626;font-weight:700;">{format_money(t['no'])} đ</span>
                        </div>
                        <div style="background:#fee2e2;border-radius:99px;height:5px;">
                            <div style="background:#dc2626;height:5px;border-radius:99px;width:{pct}%;"></div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        conn.close()

    with tab_debts:
        c1, c2, c3 = st.columns([2,1,1])
        with c1: search_d = st.text_input("🔍 Tìm kiếm", placeholder="Mã KH, HĐ...", key="search_d")
        with c2: filter_ky = st.text_input("Kỳ (YYYY-MM)", key="filter_ky")
        with c3: filter_no = st.selectbox("Lọc", ["Tất cả","Còn nợ","Đã thanh toán"], key="filter_no")
        
        conn = get_connection()
        q = "SELECT d.*, c.ten_cty, c.sdt FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh WHERE 1=1"
        p = []
        if search_d: q += " AND (d.ma_kh LIKE ? OR c.ten_cty LIKE ? OR d.ma_hd LIKE ?)"; p.extend([f"%{search_d}%"]*3)
        if filter_ky: q += " AND d.ky_thanh_toan LIKE ?"; p.append(f"%{filter_ky}%")
        if filter_no == "Còn nợ": q += " AND d.can_thu > d.da_thu"
        if filter_no == "Đã thanh toán": q += " AND d.can_thu <= d.da_thu"
        q += " ORDER BY d.ky_thanh_toan DESC, d.ma_kh"
        debts = conn.execute(q, p).fetchall()
        
        st.markdown(f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;"><b>{len(debts)}</b> bản ghi</div>', unsafe_allow_html=True)
        
        col_list, col_action = st.columns([2, 1], gap="large")
        with col_list:
            for d in debts:
                no = d["can_thu"] - d["da_thu"]
                row_bg = "#fff5f5" if no > 0 else "#f0fdf4"
                no_color = "#dc2626" if no > 0 else "#16a34a"
                tien_vat = d.get('tien_vat', 0) or 0
                st.markdown(f"""
                <div class="vhs-list-item" style="background:{row_bg};padding:14px;margin-bottom:12px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <b style="color:#0f172a;">{d['ten_cty']}</b>
                        <b style="color:{no_color};">{format_money(no)} đ</b>
                    </div>
                    <div style="font-size:12px;color:#64748b;">
                        HĐ: {d['ma_hd']} &nbsp;·&nbsp; Kỳ: {d['ky_thanh_toan']} &nbsp;·&nbsp; VAT: {format_money(tien_vat)}đ<br>
                        Thu: {format_money(d['da_thu'])} / {format_money(d['can_thu'])} &nbsp;·&nbsp; Ngày: {d['ngay_thu'][:10] if d['ngay_thu'] else '—'}
                    </div>
                </div>""", unsafe_allow_html=True)
                
        with col_action:
            st.markdown('<div class="vhs-card" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown("**💰 Ghi Nhận Thanh Toán**")
            unpaid = [d for d in debts if d["can_thu"] > d["da_thu"]]
            if not unpaid:
                st.success("Tất cả đã thanh toán đầy đủ!")
            else:
                opts = {f"[{u['ky_thanh_toan']}] {u['ten_cty'][:15]} - còn {format_money(u['can_thu']-u['da_thu'])}": u for u in unpaid}
                sel = st.selectbox("Chọn Khoản Nợ", list(opts.keys()), key="pay_sel")
                u = opts[sel]
                con_no = u["can_thu"] - u["da_thu"]
                so_tien = st.number_input("Số tiền khách trả (gồm VAT nếu có)", min_value=0, value=int(con_no), step=100000, key="pay_amount")
                if st.button("Xác nhận thu", type="primary"):
                    now_iso = (datetime.now(timezone.utc) + timedelta(hours=7)).date().isoformat()
                    conn.execute("UPDATE debts SET da_thu=da_thu+?, ngay_thu=? WHERE id=?", (so_tien, now_iso, u["id"]))
                    conn.commit()
                    st.success(f"Đã ghi nhận thu {format_money(so_tien)}")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="vhs-card" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown("**💸 Thu Tiền Trước (Chưa có trong danh sách)**")
            st.caption("💡 Dùng khi khách trả trước cho kỳ tới.")
            
            contracts = conn.execute("""
                SELECT ma_hd, ma_kh FROM contracts WHERE trang_thai='active'
            """).fetchall()
            if contracts:
                hd_opts = {f"[{c['ma_hd']}] {c['ma_kh']}": c for c in contracts}
                hd_sel = st.selectbox("Chọn Hợp Đồng", list(hd_opts.keys()), key="adv_hd_sel")
                hd = hd_opts[hd_sel]
                
                ky = st.text_input("Kỳ thu (YYYY-MM)", value=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().strftime("%Y-%m"))
                dt_adv = st.number_input("Số Tiền Khách Trả Trước", min_value=0, step=100000, key="adv_dt")
                
                if st.button("💰 Xác Nhận Thu Trước", type="primary", use_container_width=True):
                    if dt_adv <= 0:
                        st.warning("Vui lòng nhập số tiền hợp lệ!")
                    else:
                        now_iso = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().isoformat()
                        existing = conn.execute("SELECT id FROM debts WHERE ma_hd=? AND ky_thanh_toan=?", (hd["ma_hd"], ky)).fetchone()
                        if existing:
                            conn.execute("UPDATE debts SET da_thu = da_thu + ?, ngay_thu=? WHERE id=?", (dt_adv, now_iso, existing["id"]))
                        else:
                            conn.execute("INSERT INTO debts (ma_hd,ma_kh,ky_thanh_toan,can_thu,da_thu,ghi_chu,ngay_thu) VALUES(?,?,?,?,?,?,?)",
                                         (hd["ma_hd"],hd["ma_kh"],ky,0,dt_adv,"Thu trước",now_iso))
                        conn.commit()
                        st.success(f"Đã ghi nhận thu trước {format_money(dt_adv)} cho kỳ {ky}"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            if st.button("🧹 Quét Chốt Sổ Cuối Tháng", type="primary", use_container_width=True):
                from utils.month_end_sweep import run_month_end_sweep
                res = run_month_end_sweep()
                st.success(f"Đã quét kỳ {res['ky_thang']}! Sinh {res['generated']} công nợ ({res['warnings']} cảnh báo).")
                st.rerun()
                
        conn.close()

    with tab_invoices:
        c_inv_list, c_inv_add = st.columns([2, 1], gap="large")
        conn = get_connection()
        
        with c_inv_add:
            st.markdown('<div class="vhs-card" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown("**🧾 Xuất Hóa Đơn Mới**")
            # Chọn khoản nợ để xuất hóa đơn
            debts_for_inv = conn.execute("""
                SELECT d.*, c.ten_cty FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh 
                WHERE d.tien_vat > 0 AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.ma_hd=d.ma_hd AND i.ky_thang=d.ky_thanh_toan)
            """).fetchall()
            
            if debts_for_inv:
                inv_opts = {f"[{d['ky_thanh_toan']}] {d['ten_cty']} - {format_money(d['can_thu'])}": d for d in debts_for_inv}
                sel_inv = st.selectbox("Chọn công nợ cần xuất HĐ", list(inv_opts.keys()))
                d_inv = inv_opts[sel_inv]
                
                so_hoa_don = st.text_input("Số Hóa Đơn *")
                ngay_xuat = st.date_input("Ngày Xuất")
                trang_thai = st.selectbox("Trạng Thái", ["Chưa gửi", "Đã gửi khách", "Đã thanh toán HĐ"])
                
                if st.button("Lưu Hóa Đơn", type="primary", use_container_width=True):
                    if so_hoa_don:
                        gia_truoc_vat = d_inv['can_thu'] - d_inv['tien_vat']
                        vat_pct = (d_inv['tien_vat'] / gia_truoc_vat * 100) if gia_truoc_vat > 0 else 0
                        conn.execute("""
                            INSERT INTO invoices (ma_hd, ma_kh, ky_thang, so_hoa_don, ngay_xuat, gia_truoc_vat, vat_pct, tien_vat, tong_tien, trang_thai)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (d_inv['ma_hd'], d_inv['ma_kh'], d_inv['ky_thanh_toan'], so_hoa_don, ngay_xuat.isoformat(), gia_truoc_vat, vat_pct, d_inv['tien_vat'], d_inv['can_thu'], trang_thai))
                        conn.commit()
                        st.success("Tạo hóa đơn thành công!"); st.rerun()
                    else:
                        st.warning("Vui lòng nhập số hóa đơn")
            else:
                st.info("Không có công nợ nào cần xuất VAT (hoặc đã xuất hết).")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_inv_list:
            st.markdown("**Danh Sách Hóa Đơn Đã Xuất**")
            invoices = conn.execute("SELECT i.*, c.ten_cty FROM invoices i JOIN customers c ON i.ma_kh=c.ma_kh ORDER BY i.ngay_xuat DESC").fetchall()
            for inv in invoices:
                st.markdown(f"""
                <div class="vhs-list-item" style="padding:14px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <b style="color:#0f172a;">{inv['ten_cty']} - HĐ: {inv['so_hoa_don']}</b>
                        <b style="color:#0369a1;">{format_money(inv['tong_tien'])} đ</b>
                    </div>
                    <div style="font-size:12px;color:#64748b;">
                        Ngày xuất: {inv['ngay_xuat']} &nbsp;·&nbsp; Trạng thái: <b>{inv['trang_thai']}</b><br>
                        Giá trước VAT: {format_money(inv['gia_truoc_vat'])} &nbsp;·&nbsp; Thuế VAT ({int(inv['vat_pct'])}%): {format_money(inv['tien_vat'])}
                    </div>
                </div>""", unsafe_allow_html=True)
        conn.close()

    with tab_expenses:
        c_exp_list, c_exp_add = st.columns([2, 1], gap="large")
        conn = get_connection()
        
        with c_exp_add:
            st.markdown('<div class="vhs-card" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown("**💸 Thêm Chi Phí Mới**")
            with st.form("form_add_exp", clear_on_submit=True):
                ngay_chi = st.date_input("Ngày chi")
                loai_cp = st.selectbox("Loại chi phí", ["Hóa chất", "Thiết bị & Dụng cụ", "Xăng xe & Di chuyển", "Lương & Thưởng", "Khác"])
                so_tien = st.number_input("Số tiền chi (VNĐ)", min_value=0, step=10000)
                nguoi_chi = st.text_input("Người chi / Duyệt")
                ghi_chu = st.text_area("Ghi chú")
                submitted = st.form_submit_button("Lưu Chi Phí", type="primary", use_container_width=True)
                if submitted:
                    if so_tien > 0:
                        conn.execute("INSERT INTO expenses (ngay_chi, loai_chi_phi, so_tien, nguoi_chi, ghi_chu) VALUES (?, ?, ?, ?, ?)",
                                     (ngay_chi.isoformat(), loai_cp, so_tien, nguoi_chi, ghi_chu))
                        conn.commit()
                        st.toast("Thêm chi phí thành công!", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Vui lòng nhập số tiền hợp lệ")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_exp_list:
            st.markdown("**Lịch Sử Chi Phí**")
            expenses = conn.execute("SELECT * FROM expenses ORDER BY ngay_chi DESC LIMIT 50").fetchall()
            for ex in expenses:
                st.markdown(f"""
                <div class="vhs-list-item" style="padding:14px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <b style="color:#0f172a;">{ex['loai_chi_phi']}</b>
                        <b style="color:#dc2626;">-{format_money(ex['so_tien'])} đ</b>
                    </div>
                    <div style="font-size:12px;color:#64748b;">
                        Ngày chi: {ex['ngay_chi']} &nbsp;·&nbsp; Người chi: {ex['nguoi_chi'] or '—'}<br>
                        Ghi chú: {ex['ghi_chu'] or '—'}
                    </div>
                </div>""", unsafe_allow_html=True)
        conn.close()