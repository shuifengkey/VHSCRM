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
        {"name": "Kiểm soát Côn trùng bay\n(Flying Insect Control)", "targets": "Muỗi, ruồi...\n(Mosquitoes, flies...)", "chemicals": "Spectra 10SC", "frequency": "1 lần / tháng (1 time/month)", "price": 300000, "quantity": 30, "note": "HCM/ Bình Dương"},
        {"name": "Kiểm soát Gián Đức & Kiến\n(Cockroach & Ant Control)", "targets": "Gián Đức, kiến\n(German cockroaches, ants)", "chemicals": "Zentek, Posedon\nBả Gel sinh học / Bait Gel", "frequency": "1 lần / tháng (1 time/month)", "price": 500000, "quantity": 3, "note": "Vũng Tàu"},
        {"name": "Kiểm soát Gặm nhấm\n(Rodent Control)", "targets": "Chuột cống, chuột nhắt\n(Rats, mice)", "chemicals": "Bả Storm, bẫy dính\n(Rat Bait Station, Glue Boards)", "frequency": "1 lần / tháng (1 time/month)", "price": 320000, "quantity": 4, "note": "Đồng Nai"}
    ]
    
    PRESETS = {
        "Côn trùng bay (Ruồi, Muỗi)": {
            "name": "Kiểm soát Côn trùng bay (Flying Insect Control)",
            "targets": "Muỗi, ruồi... (Mosquitoes, flies...)",
            "chemicals": "Spectra 10SC",
            "frequency": "1 lần / tháng (1 time/month)"
        },
        "Gián Đức & Kiến": {
            "name": "Kiểm soát Gián Đức & Kiến (Cockroach & Ant Control)",
            "targets": "Gián Đức, kiến (German cockroaches, ants)",
            "chemicals": "Zentek, Posedon Bả Gel sinh học",
            "frequency": "1 lần / tháng (1 time/month)"
        },
        "Gặm nhấm (Chuột)": {
            "name": "Kiểm soát Gặm nhấm (Rodent Control)",
            "targets": "Chuột cống, chuột nhắt (Rats, mice)",
            "chemicals": "Bả Storm, bẫy dính (Rat Bait Station, Glue Boards)",
            "frequency": "1 lần / tháng (1 time/month)"
        },
        "Khử trùng diệt khuẩn": {
            "name": "Khử trùng diệt khuẩn (Disinfection Service)",
            "targets": "Vi khuẩn, virus (Bacteria, viruses)",
            "chemicals": "Chlorine / Cloramin B",
            "frequency": "1 lần / tháng (1 time/month)"
        },
        "Kiểm soát Mối": {
            "name": "Kiểm soát Mối (Termite Control)",
            "targets": "Mối gỗ ẩm, mối đất (Subterranean termites)",
            "chemicals": "Mythic 240SC / Termize 200SC",
            "frequency": "Bảo hành 1 năm (1 year warranty)"
        }
    }
    
    with st.expander("📚 Chèn dịch vụ mẫu (Có thể chỉnh sửa sau khi chèn)", expanded=False):
        st.markdown("<span style='font-size:13px; color:#64748b;'>Chọn một dịch vụ có sẵn để thêm nhanh vào bảng bên dưới. Sau khi thêm, anh có thể sửa chữ trực tiếp trong bảng.</span>", unsafe_allow_html=True)
        pc1, pc2 = st.columns([3, 1])
        with pc1:
            preset_choice = st.selectbox("Chọn dịch vụ mẫu:", list(PRESETS.keys()), label_visibility="collapsed")
        with pc2:
            if st.button("➕ Thêm vào bảng", use_container_width=True):
                st.session_state.quote_items.append({
                    "name": PRESETS[preset_choice]["name"],
                    "targets": PRESETS[preset_choice]["targets"],
                    "chemicals": PRESETS[preset_choice]["chemicals"],
                    "frequency": PRESETS[preset_choice]["frequency"],
                    "price": 0,
                    "quantity": 1,
                    "note": ""
                })
                st.rerun()

    if "quote_items" not in st.session_state:
        st.session_state.quote_items = default_items
        
    # Always ensure columns exist even if empty
    cols = ["name", "targets", "chemicals", "frequency", "price", "quantity", "note"]
    df = pd.DataFrame(st.session_state.quote_items, columns=cols)
    
    # Enforce text types
    for c in ["name", "targets", "chemicals", "frequency", "note"]:
        df[c] = df[c].fillna("").astype(str)
        
    # Enforce numeric types properly (works even on empty dataframe)
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0).astype('int64')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype('int64')
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="quote_editor_key",
        column_config={
            "name": st.column_config.Column("Hạng mục dịch vụ", width="large"),
            "targets": st.column_config.Column("Đối tượng", width="medium"),
            "chemicals": st.column_config.Column("Hóa chất & Vật tư", width="medium"),
            "frequency": st.column_config.SelectboxColumn(
                "Tần suất", 
                width="medium",
                options=[
                    "1 lần / tháng (1 time/month)",
                    "2 lần / tháng (2 times/month)",
                    "3 lần / tháng (3 times/month)",
                    "4 lần / tháng (4 times/month)",
                    "1 lần / quý (1 time/quarter)",
                    "Bảo hành 1 năm (1 year warranty)",
                    "Theo yêu cầu (On demand)"
                ]
            ),
            "price": st.column_config.NumberColumn("Đơn giá", min_value=0, step=1000, format="%,d"),
            "quantity": st.column_config.NumberColumn("SL", min_value=0, step=1),
            "note": st.column_config.Column("Ghi chú", width="medium"),
        },
        hide_index=True
    )
    
    # Calculate preview totals safely using Pandas
    safe_price = pd.to_numeric(edited_df['price'], errors='coerce').fillna(0)
    safe_qty = pd.to_numeric(edited_df['quantity'], errors='coerce').fillna(0)
    # If qty is 0, treat it as 1 for total calculation (lump sum)
    calc_qty = safe_qty.replace(0, 1)
    subtotal = (safe_price * calc_qty).sum()
    
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
            
        if edited_df.empty or len(edited_df) == 0:
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
                for idx, row in edited_df.iterrows():
                    name = str(row.get("name", "")).replace('nan', '').strip()
                    targets = str(row.get("targets", "")).replace('nan', '').strip()
                    chemicals = str(row.get("chemicals", "")).replace('nan', '').strip()
                    freq = str(row.get("frequency", "")).replace('nan', '').strip()
                    note = str(row.get("note", "")).replace('nan', '').strip()
                    
                    p = float(safe_price[idx])
                    q = int(safe_qty[idx])
                    
                    # Chỉ bỏ qua nếu dòng thực sự trống trơn hoàn toàn
                    if not name and not targets and not chemicals and not note and p == 0:
                        continue
                        
                    actual_q_for_calc = 1 if q == 0 else q
                    display_q = "" if q == 0 else q
                        
                    i_data.append({
                        "name": name,
                        "targets": targets,
                        "chemicals": chemicals,
                        "frequency": freq,
                        "price": p,
                        "quantity": display_q,
                        "total": p * actual_q_for_calc,
                        "note": note
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
