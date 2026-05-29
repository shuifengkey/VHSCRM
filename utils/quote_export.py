import io
import os
from datetime import datetime, timezone, timedelta

_HERE = os.path.dirname(__file__)
_SIGN_PATH = os.path.normpath(os.path.join(_HERE, "..", "Thuyansign.png.enc"))
_SEAL_PATH = os.path.normpath(os.path.join(_HERE, "..", "VHS SEAL.png.enc"))

def generate_quote_pdf(quote_data, items_data):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    from utils.excel_export import _register_fonts
    F, FB = _register_fonts()
    
    def P(text, font=None, size=9, align=TA_LEFT, color=colors.black, bold=False, leading=None):
        fn = FB if bold else (font or F)
        kw = dict(fontName=fn, fontSize=size, alignment=align, textColor=color, wordWrap='CJK')
        kw["leading"] = leading if leading else size * 1.3
        style = ParagraphStyle("_", **kw)
        return Paragraph(text, style)

    def fmt(val):
        try:
            return f"{int(val):,}".replace(",", ".")
        except:
            return str(val)

    # 1. Header Information
    c_name = quote_data.get("customer_name", "")
    c_address = quote_data.get("address", "")
    c_contact = quote_data.get("contact", "")
    q_no = quote_data.get("quote_no", "")
    
    date_val = quote_data.get("quote_date")
    if hasattr(date_val, 'strftime'):
        q_date = date_val.strftime("%d/%m/%Y")
    else:
        q_date = str(date_val)
        
    q_val = quote_data.get("validity", "30 ngày (30 days)")

    # 2. Start Document
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, pagesize=landscape(A4),
        rightMargin=1.2*cm, leftMargin=1.2*cm,
        topMargin=1.2*cm, bottomMargin=1.2*cm
    )
    content = []

    # --- TOP HEADER ---
    logo_path = os.path.normpath(os.path.join(_HERE, "..", "logo.png"))
    if os.path.exists(logo_path):
        img_w = 2.0*cm
        img_h = img_w * (1024/905)
        logo_img = Image(logo_path, width=img_w, height=img_h)
    else:
        logo_img = ""

    header_table = Table([
        [logo_img, P("<b>CÔNG TY TNHH VHS</b>", font="Square721", size=14, color=colors.HexColor("#1e3a5f")), ""],
        ["", P("Địa chỉ (Address): 67 Đường số 3, KP2, An Khánh, HCM", size=8), ""],
        ["", P("Hotline: 0783 487 586", size=8), ""],
        ["", P("Email: congtytnhhvhs@gmail.com", size=8), ""],
    ], colWidths=[2.2*cm, 18*cm, 7*cm])
    
    header_table.setStyle(TableStyle([
        ('SPAN', (0,0), (0,-1)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (1,0), (1,-1), 0),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 0.5*cm))

    # --- TITLE ---
    content.append(P("<b>BẢNG BÁO GIÁ DỊCH VỤ KIỂM SOÁT CÔN TRÙNG</b>", size=16, align=TA_CENTER, bold=True, color=colors.HexColor("#0f172a")))
    content.append(P("SERVICE QUOTATION FOR PEST CONTROL", size=11, align=TA_CENTER, color=colors.HexColor("#475569")))
    content.append(Spacer(1, 0.8*cm))

    # --- META INFO ---
    meta_table = Table([
        [P("<b>Kính gửi (To):</b>", size=10, bold=True), P(c_name, size=10, bold=True), P("<b>Số báo giá (Quote No.):</b>", size=10, bold=True), P(q_no, size=10)],
        [P("<b>Người liên hệ (Contact):</b>", size=10, bold=True), P(c_contact, size=10), P("<b>Ngày (Date):</b>", size=10, bold=True), P(q_date, size=10)],
        [P("<b>Địa chỉ (Address):</b>", size=10, bold=True), P(c_address, size=10), P("<b>Hiệu lực (Validity):</b>", size=10, bold=True), P(q_val, size=10)],
    ], colWidths=[4*cm, 14*cm, 4.5*cm, 4.5*cm])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    content.append(meta_table)
    content.append(Spacer(1, 0.5*cm))

    # --- ITEMS TABLE ---
    # Column widths for Landscape A4 (usable ~27cm)
    col_w = [1.2*cm, 4*cm, 3.5*cm, 4.5*cm, 3.5*cm, 3.5*cm, 2.5*cm, 3.5*cm, 1.1*cm]
    
    t_data = [[
        P("<b>STT</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Hạng mục dịch vụ<br/>(Service Item)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Đối tượng kiểm soát<br/>(Target Pests)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Hóa chất & Vật tư<br/>(Chemicals & Materials)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Tần suất / Tháng<br/>(Frequency)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Đơn giá / Điểm<br/>(Unit Price)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Số lượng điểm<br/>(Quantity)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Thành tiền / Tháng<br/>(Total Amount / Month)</b>", align=TA_CENTER, size=8, bold=True, color=colors.white),
        P("<b>Ghi chú</b>", align=TA_CENTER, size=8, bold=True, color=colors.white)
    ]]

    subtotal = 0
    for idx, row in enumerate(items_data):
        amt = float(row.get("total", 0))
        subtotal += amt
        t_data.append([
            P(str(idx+1), align=TA_CENTER, size=8),
            P(row.get("name", ""), size=8),
            P(row.get("targets", ""), size=8),
            P(row.get("chemicals", ""), size=8),
            P(row.get("frequency", ""), align=TA_CENTER, size=8),
            P(fmt(row.get("price", 0)), align=TA_RIGHT, size=8),
            P(str(row.get("quantity", 1)), align=TA_CENTER, size=8),
            P(fmt(amt), align=TA_RIGHT, size=8, bold=True),
            P(row.get("note", ""), size=8)
        ])

    vat_pct = float(quote_data.get("vat_percent", 8))
    vat_amt = subtotal * (vat_pct / 100.0)
    grand_total = subtotal + vat_amt

    # Subtotals
    t_data.append([
        "", P("<b>Cộng tiền dịch vụ / Subtotal (VNĐ):</b>", align=TA_RIGHT, size=9, bold=True), "", "", "", "", "",
        P(f"<b>{fmt(subtotal)}</b>", align=TA_RIGHT, size=9, bold=True), ""
    ])
    t_data.append([
        "", P(f"<b>Thuế GTGT / VAT ({int(vat_pct)}%):</b>", align=TA_RIGHT, size=9, bold=True), "", "", "", "", "",
        P(f"<b>{fmt(vat_amt)}</b>", align=TA_RIGHT, size=9, bold=True), ""
    ])
    t_data.append([
        "", P("<b>TỔNG CỘNG THANH TOÁN / GRAND TOTAL:</b>", align=TA_RIGHT, size=10, bold=True, color=colors.HexColor("#1e3a5f")), "", "", "", "", "",
        P(f"<b>{fmt(grand_total)}</b>", align=TA_RIGHT, size=10, bold=True, color=colors.HexColor("#1e3a5f")), ""
    ])

    items_table = Table(t_data, colWidths=col_w, repeatRows=1)
    
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a5f")),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('INNERGRID', (0,0), (-1,-4), 0.5, colors.grey),
        ('BOX', (0,0), (-1,-4), 1, colors.HexColor("#1e3a5f")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]
    # Merge subtotal cells
    num_rows = len(t_data)
    for r in range(num_rows - 3, num_rows):
        t_style.append(('SPAN', (1, r), (6, r)))
        # Hide borders for bottom 3 rows except total column
        t_style.append(('LINEBELOW', (7, r), (7, r), 0.5, colors.grey))

    items_table.setStyle(TableStyle(t_style))
    content.append(items_table)
    content.append(Spacer(1, 0.8*cm))

    # --- TERMS & CONDITIONS ---
    content.append(P("<b>ĐIỀU KHOẢN & CAM KẾT DỊCH VỤ (TERMS & CONDITIONS):</b>", size=10, bold=True, color=colors.HexColor("#1e3a5f")))
    content.append(Spacer(1, 0.2*cm))
    
    terms = [
        ("1. Hóa chất sử dụng\n(Chemicals used):", "Cam kết 100% chính hãng, có chứng nhận an toàn (MSDS) và giấy phép Bộ Y tế.\n(100% genuine, with Material Safety Data Sheet and Ministry of Health license.)"),
        ("2. Chế độ bảo hành\n(Warranty):", "Bảo hành miễn phí toàn bộ hệ thống cửa hàng nếu phát sinh côn trùng trong thời hạn hợp đồng.\n(Free warranty for the entire store system if pests arise during the contract period.)"),
        ("3. Thời gian xử lý\n(Service time):", "Linh hoạt theo ca vắng của chuỗi không gây gián đoạn kinh doanh.\n(Flexible execution during off-peak hours to avoid business disruption.)"),
        ("4. Thanh toán\n(Payment):", "Chuyển khoản theo chu kỳ hàng tháng, xuất đầy đủ hóa đơn GTGT (VAT).\n(Monthly bank transfer, full legal VAT invoice provided.)"),
    ]
    term_t_data = []
    for th, td in terms:
        term_t_data.append([
            P(f"<b>{th.split(chr(10))[0]}</b><br/><font size='8'>{th.split(chr(10))[1]}</font>", size=9),
            P(f"{td.split(chr(10))[0]}<br/><font size='8' color='grey'><i>{td.split(chr(10))[1]}</i></font>", size=9)
        ])
    term_table = Table(term_t_data, colWidths=[5*cm, 22*cm])
    term_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    content.append(term_table)
    content.append(Spacer(1, 1*cm))

    # --- SIGNATURES ---
    sign_cell = ""
    if os.path.exists(_SIGN_PATH) and os.path.exists(_SEAL_PATH):
        try:
            import streamlit as st
            from cryptography.fernet import Fernet
            from PIL import Image as PILImage
            from reportlab.platypus import Flowable
            from reportlab.lib.utils import ImageReader
            
            enc_key = st.secrets.get("IMAGE_ENCRYPTION_KEY")
            if enc_key:
                fernet = Fernet(enc_key)
                with open(_SIGN_PATH, 'rb') as f:
                    sign_bytes = fernet.decrypt(f.read())
                with open(_SEAL_PATH, 'rb') as f:
                    seal_bytes = fernet.decrypt(f.read())
                    
                sign_stream = io.BytesIO(sign_bytes)
                seal_stream = io.BytesIO(seal_bytes)
                
                with PILImage.open(sign_stream) as img_sign_pil:
                    w_sign, h_sign = img_sign_pil.size
                with PILImage.open(seal_stream) as img_seal_pil:
                    w_seal, h_seal = img_seal_pil.size
                    
                sign_stream.seek(0)
                seal_stream.seek(0)
                
                img_sign_reader = ImageReader(sign_stream)
                img_seal_reader = ImageReader(seal_stream)
                
                class SignatureOverlay(Flowable):
                    def __init__(self, sign_img, seal_img, sign_w, sign_h, seal_w, seal_h):
                        Flowable.__init__(self)
                        self.sign_img = sign_img
                        self.seal_img = seal_img
                        self.width = 8.0*cm
                        self.height = 1.8*cm
                        self.w_sign_pt = sign_w
                        self.h_sign_pt = sign_h
                        self.w_seal_pt = seal_w
                        self.h_seal_pt = seal_h
                        
                    def draw(self):
                        sign_x = 2.0*cm
                        sign_y = 0.0*cm
                        self.canv.drawImage(self.sign_img, sign_x, sign_y, 
                                            width=self.w_sign_pt, height=self.h_sign_pt, mask='auto')
                        
                        seal_x = 1.2*cm
                        seal_y = 0.4*cm
                        self.canv.drawImage(self.seal_img, seal_x, seal_y, 
                                            width=self.w_seal_pt, height=self.h_seal_pt, mask='auto')

                w_sign_pt = 4.7*cm
                h_sign_pt = w_sign_pt * (h_sign / w_sign)
                w_seal_pt = 3.55*cm
                h_seal_pt = w_seal_pt * (h_seal / w_seal)
                
                sign_cell = SignatureOverlay(img_sign_reader, img_seal_reader, w_sign_pt, h_sign_pt, w_seal_pt, h_seal_pt)
        except Exception as e:
            print(f"Error loading signature: {e}")
            sign_cell = Spacer(1, 1.5*cm)
    else:
        sign_cell = Spacer(1, 1.5*cm)

    sign = Table([
        [P("<b>ĐẠI DIỆN KHÁCH HÀNG / CLIENT REP.</b><br/><font size='8' color='grey'><i>(Ký & Ghi rõ họ tên / Sign & Name)</i></font>", size=9, align=TA_CENTER, bold=True),
         "",
         P("<b>ĐẠI DIỆN VHS PEST CONTROL</b><br/><font size='8' color='grey'><i>(Ký, đóng dấu & Ghi rõ họ tên)</i></font>", size=9, align=TA_CENTER, bold=True)],
        ["", "", sign_cell],
        ["", "", P("<b>TRẦN THỊ THÚY AN</b>", size=9, align=TA_CENTER, bold=True)],
    ], colWidths=[10*cm, 7*cm, 10*cm])
    sign.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    content.append(sign)

    doc.build(content)
    return pdf_buffer.getvalue()
