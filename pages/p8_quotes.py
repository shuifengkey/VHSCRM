import streamlit as st
import pandas as pd
from datetime import date
from utils.database import get_connection
from utils.styles import card, section_header
from utils.quote_export import generate_quote_pdf

def render():
    st.markdown(section_header("Tạo Báo Giá Dịch Vụ", "Báo giá dịch vụ kiểm soát côn trùng (Form theo mẫu BG PC)"), unsafe_allow_html=True)
    
    # 1. Load customers for selection
    conn = get_connection()
    customers = conn.execute("SELECT id, ten_phap_ly, ten_cty, dia_chi, nguoi_lien_he FROM customers ORDER BY ten_cty").fetchall()
    conn.close()
    
    c_options = {"": "--- Chọn khách hàng có sẵn hoặc nhập tay ---"}
    for c in customers:
        label = c["ten_phap_ly"] if c["ten_phap_ly"] else c["ten_cty"]
        c_options[str(c["id"])] = f"{label} ({c['ten_cty']})"
        
    st.markdown(card("""
        <div style="font-size:14px;font-weight:600;margin-bottom:10px;color:#0f172a;">
            <i class="ph-user-list"></i> Thông tin Khách hàng & Báo giá
        </div>
    """, padding="16px", border_left="#16a34a"), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        sel_c_id = st.selectbox("Chọn khách hàng từ Database", options=list(c_options.keys()), format_func=lambda x: c_options[x])
        
        # Auto-fill defaults
        def_name = ""
        def_addr = ""
        def_contact = ""
        if sel_c_id:
            c_data = next((c for c in customers if str(c["id"]) == sel_c_id), None)
            if c_data:
                def_name = c_data["ten_phap_ly"] if c_data["ten_phap_ly"] else c_data["ten_cty"]
                def_addr = c_data["dia_chi"] or ""
                def_contact = c_data["nguoi_lien_he"] or ""
                
        c_name = st.text_input("Kính gửi (Customer Name)*", value=def_name)
        c_contact = st.text_input("Người liên hệ (Contact)", value=def_contact)
        c_address = st.text_area("Địa chỉ (Address)*", value=def_addr, height=68)
        
    with col2:
        q_no = st.text_input("Số báo giá (Quote No.)", value=f"FMM-{date.today().year}-001")
        q_date = st.date_input("Ngày báo giá (Date)", value=date.today())
        q_val = st.text_input("Hiệu lực (Validity)", value="30 ngày (30 days)")
        vat_pct = st.selectbox("Thuế GTGT / VAT (%)", options=[0, 8, 10], index=1)
        
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(card("""
        <div style="font-size:14px;font-weight:600;margin-bottom:10px;color:#0f172a;">
            <i class="ph-list-numbers"></i> Chi tiết Hạng mục Dịch vụ
        </div>
    """, padding="16px", border_left="#d97706"), unsafe_allow_html=True)
    
    # Default items from template
    default_items = [
        {"name": "Kiểm soát Côn trùng bay\n(Flying Insect Control)", "targets": "Muỗi, ruồi...\n(Mosquitoes, flies...)", "chemicals": "Spectra 10SC", "frequency": "1 lần / tháng\n(1 time/month)", "price": 300000, "quantity": 30, "note": "HCM/ Bình Dương"},
        {"name": "Kiểm soát Gián Đức & Kiến\n(Cockroach & Ant Control)", "targets": "Gián Đức, kiến\n(German cockroaches, ants)", "chemicals": "Zentek, Posedon\nBả Gel sinh học / Bait Gel", "frequency": "1 lần / tháng\n(1 times/month)", "price": 500000, "quantity": 3, "note": "Vũng Tàu"},
        {"name": "Kiểm soát Gặm nhấm\n(Rodent Control)", "targets": "Chuột cống, chuột nhắt\n(Rats, mice)", "chemicals": "Bả Storm, bẫy dính\n(Rat Bait Station, Glue Boards)", "frequency": "1 lần / tháng\n(1 times/month)", "price": 320000, "quantity": 4, "note": "Đồng Nai"}
    ]
    
    if "quote_items" not in st.session_state:
        st.session_state.quote_items = default_items
        
    df = pd.DataFrame(st.session_state.quote_items)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Hạng mục dịch vụ", width="large"),
            "targets": st.column_config.TextColumn("Đối tượng", width="medium"),
            "chemicals": st.column_config.TextColumn("Hóa chất & Vật tư", width="medium"),
            "frequency": st.column_config.TextColumn("Tần suất", width="small"),
            "price": st.column_config.NumberColumn("Đơn giá", min_value=0, step=1000, format="%d"),
            "quantity": st.column_config.NumberColumn("SL", min_value=1, step=1, format="%d"),
            "note": st.column_config.TextColumn("Ghi chú", width="medium"),
        },
        hide_index=True
    )
    
    st.session_state.quote_items = edited_df.to_dict('records')
    
    # Calculate preview totals
    subtotal = sum([float(r.get("price", 0) or 0) * int(r.get("quantity", 1) or 1) for r in st.session_state.quote_items if isinstance(r, dict)])
    vat_amt = subtotal * (vat_pct / 100.0)
    grand = subtotal + vat_amt
    
    st.markdown(f"""
    <div style="text-align:right; font-size:14px; margin-top:10px;">
        <div>Cộng tiền dịch vụ: <b>{subtotal:,.0f} VNĐ</b></div>
        <div>Thuế GTGT ({vat_pct}%): <b>{vat_amt:,.0f} VNĐ</b></div>
        <div style="font-size:16px; color:#dc2626;">Tổng cộng: <b>{grand:,.0f} VNĐ</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 20px 0; border-color:#e2e8f0;'/>", unsafe_allow_html=True)
    
    if st.button("Tạo File Báo Giá (PDF)", type="primary", use_container_width=True, icon="🖨️"):
        if not c_name.strip() or not c_address.strip():
            st.error("Vui lòng nhập Tên khách hàng (Kính gửi) và Địa chỉ.")
            return
            
        if len(st.session_state.quote_items) == 0:
            st.error("Vui lòng thêm ít nhất 1 dịch vụ.")
            return
            
        with st.spinner("Đang tạo PDF..."):
            try:
                q_data = {
                    "customer_name": c_name.strip(),
                    "address": c_address.strip(),
                    "contact": c_contact.strip(),
                    "quote_no": q_no.strip(),
                    "quote_date": q_date,
                    "validity": q_val.strip(),
                    "vat_percent": vat_pct
                }
                
                i_data = []
                for row in st.session_state.quote_items:
                    if not row.get("name"): continue
                    p = float(row.get("price", 0) or 0)
                    q = int(row.get("quantity", 1) or 1)
                    i_data.append({
                        "name": row.get("name", ""),
                        "targets": row.get("targets", ""),
                        "chemicals": row.get("chemicals", ""),
                        "frequency": row.get("frequency", ""),
                        "price": p,
                        "quantity": q,
                        "total": p * q,
                        "note": row.get("note", "")
                    })
                    
                pdf_bytes = generate_quote_pdf(q_data, i_data)
                
                st.success("Tạo Báo giá PDF thành công!")
                st.download_button(
                    label="⬇️ TẢI XUỐNG BÁO GIÁ",
                    data=pdf_bytes,
                    file_name=f"BaoGia_{q_no}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Lỗi khi tạo PDF: {e}")
