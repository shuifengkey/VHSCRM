# pages/p5_pdf.py - Module 5: Xuất PDF tự động
import streamlit as st
import sys, os

from utils.database import get_connection
from utils.pdf_generator import generate_bao_gia, generate_hop_dong, generate_phieu_xac_nhan
from datetime import timezone, date, datetime, timedelta
from utils.styles import section_header

def render():
    st.markdown(section_header("Xuất Chứng Từ PDF Tự Động", "Chọn khách hàng và loại chứng từ để sinh PDF", "<i class=\"ph-printer\" style=\"font-size:15px;color:#475569;vertical-align:middle;line-height:1;margin-right:3px;\"></i>"), unsafe_allow_html=True)
    
    conn = get_connection()
    all_kh = conn.execute("""
        SELECT c.ma_kh, c.ten_cty, ct.ma_hd
        FROM customers c
        LEFT JOIN contracts ct ON c.ma_kh = ct.ma_kh
        ORDER BY c.ma_kh
    """).fetchall()
    
    upcoming_kh = conn.execute("""
        SELECT DISTINCT ma_kh FROM schedules WHERE trang_thai='scheduled'
    """).fetchall()
    upcoming_ma_khs = {r['ma_kh'] for r in upcoming_kh}
    conn.close()
    
    if not all_kh:
        st.warning("Chưa có dữ liệu khách hàng.")
        return
    
    st.markdown("### Lọc Khách Hàng")
    only_upcoming = st.checkbox("Chỉ hiển thị khách hàng đang có ca sắp thi công", value=True)
    
    if only_upcoming:
        filtered_kh = [r for r in all_kh if r["ma_kh"] in upcoming_ma_khs]
        if not filtered_kh:
            st.info("Không có khách hàng nào đang có ca sắp thi công. Hiển thị tất cả.")
            filtered_kh = all_kh
    else:
        filtered_kh = all_kh
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        # Chọn khách hàng (dedup)
        kh_dict = {}
        for r in filtered_kh:
            if r["ma_kh"] not in kh_dict:
                kh_dict[r["ma_kh"]] = r["ten_cty"]
        
        if not kh_dict:
            st.warning("Không có khách hàng phù hợp.")
            return
            
        kh_options = {f"{ma} - {ten}": ma for ma, ten in kh_dict.items()}
        selected_kh_label = st.selectbox("👥 Chọn Khách Hàng", list(kh_options.keys()))
        selected_ma_kh = kh_options[selected_kh_label]
    
    with col2:
        doc_type = st.selectbox("📄 Loại Chứng Từ", [
            "📊 Báo Giá", "📋 Hợp Đồng", "✓ Phiếu Xác Nhận Dịch Vụ"
        ])
    
    # Lấy dữ liệu khách hàng và hợp đồng
    conn = get_connection()
    customer = conn.execute("SELECT * FROM customers WHERE ma_kh=?", (selected_ma_kh,)).fetchone()
    contract = conn.execute(
        "SELECT * FROM contracts WHERE ma_kh=? ORDER BY ngay_ky DESC LIMIT 1", 
        (selected_ma_kh,)
    ).fetchone()
    
    # Lấy thông tin ca thi công sắp tới (hoặc gần nhất)
    schedule_entry = None
    if "Phiếu Xác Nhận" in doc_type:
        schedule_entry = conn.execute("""
            SELECT * FROM schedules 
            WHERE ma_kh=? AND trang_thai='scheduled'
            ORDER BY ngay_du_kien ASC LIMIT 1
        """, (selected_ma_kh,)).fetchone()
        
        # Fallback: nếu không có ca scheduled, lấy ca gần nhất bất kì
        if not schedule_entry:
            schedule_entry = conn.execute("""
                SELECT * FROM schedules 
                WHERE ma_kh=? 
                ORDER BY ngay_du_kien DESC LIMIT 1
            """, (selected_ma_kh,)).fetchone()
    conn.close()
    
    # Hiển thị preview thông tin
    if customer and contract:
        st.markdown("---")
        st.markdown("**📋 Preview thông tin sẽ xuất vào PDF:**")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style="background:#f0faf4;padding:12px;border-radius:8px;border-left:3px solid #1a6b3c;">
                <b>THÔNG TIN KHÁCH HÀNG</b><br>
                <i class=\"ph-buildings\" style=\"font-size:15px;color:#475569;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {customer['ten_cty']}<br>
                <i class=\"ph-user\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {customer['dai_dien'] or '-'}<br>
                <i class=\"ph-phone\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {customer['sdt'] or '-'}<br>
                <i class=\"ph-map-pin\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {customer['dia_chi'] or '-'}
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            st.markdown(f"""
            <div style="background:#e8f5ee;padding:12px;border-radius:8px;border-left:3px solid #0d3d22;">
                <b>THÔNG TIN HỢP ĐỒNG</b><br>
                <i class=\"ph-file-text\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Mã HĐ: {contract['ma_hd']}<br>
                <i class=\"ph-calendar\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Tần suất: {contract['tan_suat']} lần/tháng<br>
                ⏰ Giờ: {contract['gio_bat_dau']} - {contract['gio_ket_thuc']}<br>
                <i class=\"ph-currency-circle-dollar\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Giá: {contract['gia_tri_thang']:,.0f}đ/tháng
            </div>
            """.replace(",","."), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Nút xuất PDF
        col_btn, col_info = st.columns([1,2])
        with col_btn:
            if st.button("🖨️ XUẤT PDF NGAY", use_container_width=True):
                try:
                    customer_dict = dict(customer)
                    contract_dict = dict(contract)
                    
                    with st.spinner("⏳ Đang sinh PDF..."):
                        if "Báo Giá" in doc_type:
                            pdf_bytes = generate_bao_gia(customer_dict, contract_dict)
                            filename = f"BaoGia_{selected_ma_kh}_{(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%Y%m%d')}.pdf"
                        elif "Hợp Đồng" in doc_type:
                            pdf_bytes = generate_hop_dong(customer_dict, contract_dict)
                            filename = f"HopDong_{contract_dict['ma_hd']}_{(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%Y%m%d')}.pdf"
                        else:
                            # Phiếu xác nhận
                            schedule_dict = dict(schedule_entry) if schedule_entry else None
                            pdf_bytes = generate_phieu_xac_nhan(customer_dict, contract_dict, schedule_dict)
                            filename = f"PhieuXacNhan_{selected_ma_kh}_{(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%Y%m%d%H%M')}.pdf"
                    
                    # Nút download
                    st.download_button(
                        label="⬇️ TẢI XUỐNG PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success(f"✓ PDF đã sẵn sàng: **{filename}**")
                    
                except Exception as e:
                    st.error(f"× Lỗi sinh PDF: {e}")
                    st.exception(e)
        
        with col_info:
            st.markdown(f"""
            <div style="padding:12px;background:#fffbeb;border-radius:8px;font-size:13px;">
                <i class=\"ph-file-text\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>Loại chứng từ:</b> {doc_type}<br>
                <i class=\"ph-clock\" style=\"font-size:15px;color:#d97706;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>Thời điểm xuất:</b> {(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%H:%M %d/%m/%Y')}<br>
                <i class=\"ph-folder-open\" style=\"font-size:15px;color:#d97706;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>Định dạng:</b> PDF (A4, tiếng Việt)
            </div>
            """, unsafe_allow_html=True)
    
    elif customer and not contract:
        st.warning(f"! Khách hàng **{customer['ten_cty']}** chưa có hợp đồng nào!")
    else:
        st.error("× Không tìm thấy thông tin khách hàng!")
