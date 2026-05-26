# pages/p5_pdf.py - Module 5: Xuất PDF tự động
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_connection
from utils.pdf_generator import generate_bao_gia, generate_hop_dong, generate_phieu_xac_nhan
from datetime import timezone, datetime

def render():
    st.title("🖨️ Xuất Chứng Từ PDF Tự Động")
    st.markdown("Chọn khách hàng và loại chứng từ - Hệ thống tự truy xuất dữ liệu và sinh PDF.")
    st.markdown("---")
    
    conn = get_connection()
    all_kh = conn.execute("""
        SELECT c.ma_kh, c.ten_cty, ct.ma_hd
        FROM customers c
        LEFT JOIN contracts ct ON c.ma_kh = ct.ma_kh
        ORDER BY c.ma_kh
    """).fetchall()
    conn.close()
    
    if not all_kh:
        st.warning("Chưa có dữ liệu khách hàng.")
        return
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        # Chọn khách hàng (dedup)
        kh_dict = {}
        for r in all_kh:
            if r["ma_kh"] not in kh_dict:
                kh_dict[r["ma_kh"]] = r["ten_cty"]
        
        kh_options = {f"{ma} - {ten}": ma for ma, ten in kh_dict.items()}
        selected_kh_label = st.selectbox("👥 Chọn Khách Hàng", list(kh_options.keys()))
        selected_ma_kh = kh_options[selected_kh_label]
    
    with col2:
        doc_type = st.selectbox("📄 Loại Chứng Từ", [
            "📊 Báo Giá", "📋 Hợp Đồng", "✅ Phiếu Xác Nhận Dịch Vụ"
        ])
    
    # Lấy dữ liệu khách hàng và hợp đồng
    conn = get_connection()
    customer = conn.execute("SELECT * FROM customers WHERE ma_kh=?", (selected_ma_kh,)).fetchone()
    contract = conn.execute(
        "SELECT * FROM contracts WHERE ma_kh=? ORDER BY ngay_ky DESC LIMIT 1", 
        (selected_ma_kh,)
    ).fetchone()
    
    # Nếu xuất phiếu xác nhận, lấy log gần nhất
    logbook_entry = None
    if "Phiếu Xác Nhận" in doc_type:
        logbook_entry = conn.execute("""
            SELECT l.* FROM logbook l
            JOIN schedules s ON l.schedule_id = s.id
            WHERE l.ma_kh=? AND l.checkout_time IS NOT NULL
            ORDER BY l.checkout_time DESC LIMIT 1
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
                🏢 {customer['ten_cty']}<br>
                👤 {customer['dai_dien'] or '-'}<br>
                📞 {customer['sdt'] or '-'}<br>
                📍 {customer['dia_chi'] or '-'}
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            st.markdown(f"""
            <div style="background:#e8f5ee;padding:12px;border-radius:8px;border-left:3px solid #0d3d22;">
                <b>THÔNG TIN HỢP ĐỒNG</b><br>
                📄 Mã HĐ: {contract['ma_hd']}<br>
                📅 Tần suất: {contract['tan_suat']} lần/tháng<br>
                ⏰ Giờ: {contract['gio_bat_dau']} - {contract['gio_ket_thuc']}<br>
                💰 Giá: {contract['gia_tri_thang']:,.0f}đ/tháng
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
                            if not logbook_entry:
                                st.error("❌ Chưa có dữ liệu thi công (check-out) cho khách hàng này!")
                                return
                            logbook_dict = dict(logbook_entry)
                            pdf_bytes = generate_phieu_xac_nhan(customer_dict, contract_dict, logbook_dict)
                            filename = f"PhieuXacNhan_{selected_ma_kh}_{(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%Y%m%d%H%M')}.pdf"
                    
                    # Nút download
                    st.download_button(
                        label="⬇️ TẢI XUỐNG PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success(f"✅ PDF đã sẵn sàng: **{filename}**")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi sinh PDF: {e}")
                    st.exception(e)
        
        with col_info:
            st.markdown(f"""
            <div style="padding:12px;background:#fffbeb;border-radius:8px;font-size:13px;">
                📄 <b>Loại chứng từ:</b> {doc_type}<br>
                🕐 <b>Thời điểm xuất:</b> {(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%H:%M %d/%m/%Y')}<br>
                📂 <b>Định dạng:</b> PDF (A4, tiếng Việt)
            </div>
            """, unsafe_allow_html=True)
    
    elif customer and not contract:
        st.warning(f"⚠️ Khách hàng **{customer['ten_cty']}** chưa có hợp đồng nào!")
    else:
        st.error("❌ Không tìm thấy thông tin khách hàng!")
