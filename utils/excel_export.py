import io
import os
from datetime import datetime, timezone, timedelta

_HERE = os.path.dirname(__file__)
_FONT_REG  = os.path.join(_HERE, "Roboto-Regular.ttf")
_FONT_BOLD = os.path.join(_HERE, "Roboto-Bold.ttf")
_LOGO_PATH = os.path.normpath(os.path.join(_HERE, "..", "LOGO TEN.png"))


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("Roboto")
        return "Roboto", "Roboto-Bold"
    except Exception:
        pass
    if os.path.exists(_FONT_REG) and os.path.exists(_FONT_BOLD):
        pdfmetrics.registerFont(TTFont("Roboto",      _FONT_REG))
        pdfmetrics.registerFont(TTFont("Roboto-Bold", _FONT_BOLD))
        return "Roboto", "Roboto-Bold"
    return "Helvetica", "Helvetica-Bold"


def number_to_words_vn(n):
    if n == 0:
        return "Không đồng"
    units = ["", "nghìn", "triệu", "tỷ"]
    words = ["không", "một", "hai", "ba", "bốn", "năm",
             "sáu", "bảy", "tám", "chín"]

    def read_block(num, is_first=False):
        res = ""
        h, t, u = num // 100, (num % 100) // 10, num % 10
        if not is_first or h > 0:
            res += words[h] + " trăm "
            if t == 0 and u > 0:
                res += "lẻ "
        if t == 1:
            res += "mười "
        elif t > 1:
            res += words[t] + " mươi "
        if u == 1 and t > 1:
            res += "mốt "
        elif u == 5 and t > 0:
            res += "lăm "
        elif u > 0:
            res += words[u] + " "
        return res.strip()

    blocks = []
    tmp = n
    while tmp > 0:
        blocks.append(tmp % 1000)
        tmp //= 1000

    parts = []
    for i in range(len(blocks) - 1, -1, -1):
        b = blocks[i]
        if b > 0:
            part = read_block(b, is_first=(i == len(blocks) - 1))
            if units[i]:
                part += " " + units[i]
            parts.append(part)

    return (" ".join(parts).strip() + " đồng").capitalize()


def generate_payment_request_pdf(debt_data, attachments=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable, Image)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    F, FB = _register_fonts()

    VHS_BLUE  = colors.HexColor("#1e3a5f")
    LIGHT_BG  = colors.HexColor("#f0f4ff")
    BLUE_BG   = colors.HexColor("#dce8ff")
    CK_BG     = colors.HexColor("#f0f4ff")
    GREY_LINE = colors.HexColor("#cccccc")

    def P(text, font=None, size=9, align=TA_LEFT, color=colors.black,
          bold=False, leading=None):
        fn = FB if bold else (font or F)
        kw = dict(fontName=fn, fontSize=size, alignment=align,
                  textColor=color, wordWrap='CJK')
        if leading:
            kw["leading"] = leading
        style = ParagraphStyle("_", **kw)
        return Paragraph(text, style)

    def fmt(val):
        return f"{int(val):,}".replace(",", ".")

    # ── Dữ liệu ──────────────────────────────────────────────
    now        = datetime.now(timezone.utc) + timedelta(hours=7)
    ky         = debt_data.get("ky_thanh_toan", "")
    year       = ky[:4] if ky else now.strftime("%Y")
    month_num  = ky[5:7] if len(ky) >= 7 else now.strftime("%m")
    ky_display = f"Tháng {month_num}/{year}"

    tien_vat = float(debt_data.get("tien_vat", 0) or 0)
    can_thu  = float(debt_data.get("can_thu",  0) or 0)
    goc      = can_thu - tien_vat
    ten_cty  = debt_data.get("ten_cty", "") or ""
    ma_hd    = debt_data.get("ma_hd",   "") or ""
    debt_id  = debt_data.get("id",       "")
    so_phieu = f"PYC-{year}-{debt_id}"
    nguoi_lh = debt_data.get("nguoi_lien_he", "") or ""

    if tien_vat > 0 and goc > 0:
        vat_pct   = round(tien_vat / goc * 100)
        vat_label = f"Thuế GTGT / VAT ({vat_pct}%):"
        vat_value = fmt(tien_vat)
    else:
        vat_label = "Thuế GTGT / VAT:"
        vat_value = "—"

    # Nội dung CK
    noidung_ck = (f"{ten_cty} thanh toan phi dich vu kiem soat con trung "
                  f"thang {month_num} cho VHS")

    # ── Build doc ─────────────────────────────────────────────
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.0*cm,  bottomMargin=1.5*cm,
    )
    W = A4[0] - 3*cm   # usable width
    content = []

    # ── HEADER: Logo + thông tin công ty + Số phiếu ──────────
    if os.path.exists(_LOGO_PATH):
        logo_img = Image(_LOGO_PATH, width=2.6*cm, height=2.6*cm,
                         kind='proportional')
        logo_cell = logo_img
    else:
        logo_cell = P("<b>VHS</b>", size=18, bold=True, color=VHS_BLUE)

    company_block = [
        P("<b>CÔNG TY TNHH VHS</b>", size=12, bold=True, color=VHS_BLUE),
        Spacer(1, 3),
        P("Địa chỉ: 67 Đường số 3, KP2, An Khánh, TP. HCM", size=8),
        P("Hotline: 0783 487 586", size=8),
        P("Email: congtytnhhvhs@gmail.com", size=8),
    ]

    phieu_block = [
        P(f"<b>Số phiếu:</b>  {so_phieu}",    size=9, align=TA_RIGHT),
        Spacer(1, 5),
        P(f"<b>Ngày:</b>  {now.strftime('%d/%m/%Y')}", size=9, align=TA_RIGHT),
        P(f"<b>Hợp đồng:</b>  {ma_hd}",       size=9, align=TA_RIGHT),
    ]

    hdr = Table([[logo_cell, company_block, phieu_block]],
                colWidths=[3.6*cm, 9.8*cm, 4.6*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
    ]))
    content.append(hdr)
    content.append(Spacer(1, 0.25*cm))
    content.append(HRFlowable(width="100%", thickness=2, color=VHS_BLUE))
    content.append(Spacer(1, 0.3*cm))

    # ── TIÊU ĐỀ (2 dòng riêng, không chồng nhau) ─────────────
    content.append(P(
        "<b>PHIẾU YÊU CẦU THANH TOÁN</b>",
        size=15, align=TA_CENTER, bold=True, color=VHS_BLUE, leading=20,
    ))
    content.append(Spacer(1, 0.1*cm))
    content.append(P(
        "(PAYMENT REQUEST / DEBIT NOTE)",
        size=9, align=TA_CENTER, color=colors.HexColor("#666666"), leading=13,
    ))
    content.append(Spacer(1, 0.4*cm))

    # ── KÍNH GỬI ─────────────────────────────────────────────
    kg = Table([
        [P("<b>Kính gửi (To):</b>",        size=10, bold=True),
         P(f"<b>{ten_cty}</b>",             size=10, bold=True)],
        [P("<b>Người liên hệ (Attn):</b>",  size=9,  bold=True),
         P(nguoi_lh,                         size=9)],
    ], colWidths=[5*cm, W - 5*cm])
    kg.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
    ]))
    content.append(kg)
    content.append(Spacer(1, 0.35*cm))

    # ── BẢNG DỊCH VỤ ─────────────────────────────────────────
    TH  = ParagraphStyle("TH",  fontName=FB, fontSize=9,
                          alignment=TA_CENTER, textColor=colors.white,
                          leading=13, wordWrap='CJK')
    TD  = ParagraphStyle("TD",  fontName=F,  fontSize=9,
                          alignment=TA_CENTER, wordWrap='CJK')
    TDL = ParagraphStyle("TDL", fontName=F,  fontSize=9,
                          alignment=TA_LEFT,   wordWrap='CJK', leading=13)
    TDR = ParagraphStyle("TDR", fontName=F,  fontSize=9,
                          alignment=TA_RIGHT,  wordWrap='CJK')
    TDRb= ParagraphStyle("TDRb",fontName=FB, fontSize=10,
                          alignment=TA_RIGHT,  textColor=VHS_BLUE,
                          wordWrap='CJK')
    TDRlabel = ParagraphStyle("TDRl", fontName=FB, fontSize=9,
                               alignment=TA_RIGHT, wordWrap='CJK')
    TDRlabel_blue = ParagraphStyle("TDRlb", fontName=FB, fontSize=10,
                                   alignment=TA_RIGHT, textColor=VHS_BLUE,
                                   wordWrap='CJK')

    col_w = [1.4*cm, 6.1*cm, 2.9*cm, 1.4*cm, 3.7*cm, 2.5*cm]

    TH_SM = ParagraphStyle("TH_SM", fontName=FB, fontSize=8,
                            alignment=TA_CENTER, textColor=colors.white,
                            leading=11, wordWrap='CJK')

    svc_data = [
        # Header
        [Paragraph("STT<br/>(No.)",                                    TH_SM),
         Paragraph("Nội dung thanh toán<br/>(Description of Services)",TH),
         Paragraph("Kỳ thanh toán<br/>(Period)",                       TH),
         Paragraph("SL<br/>(Qty)",                                     TH_SM),
         Paragraph("Đơn giá<br/>(Unit Price)",                          TH),
         Paragraph("Thành tiền<br/>(Amount)",                           TH)],
        # Dòng dữ liệu
        [Paragraph("1",                                                 TD),
         Paragraph("Dịch vụ kiểm soát côn trùng định kỳ\n"
                   "(Pest Control Services)",                           TDL),
         Paragraph(ky_display,                                          TD),
         Paragraph("1",                                                 TD),
         Paragraph(fmt(goc),                                            TDR),
         Paragraph(fmt(goc),                                            TDR)],
        # Subtotal
        ["", "", "", "",
         Paragraph("Cộng tiền dịch vụ / Subtotal:",                    TDRlabel),
         Paragraph(fmt(goc),                                            TDR)],
        ["", "", "", "",
         Paragraph(vat_label,                                           TDRlabel),
         Paragraph(vat_value,                                           TDR)],
        ["", "", "", "",
         Paragraph("<b>TỔNG CỘNG / GRAND TOTAL:</b>",                  TDRlabel_blue),
         Paragraph(f"<b>{fmt(can_thu)}</b>",                           TDRb)],
    ]

    svc_table = Table(svc_data, colWidths=col_w)
    svc_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  VHS_BLUE),
        ("FONTNAME",      (0, 0), (-1, 0),  FB),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Grid data row
        ("GRID",          (0, 0), (-1, 1),  0.5, GREY_LINE),
        ("BOX",           (0, 0), (-1, 1),  1,   VHS_BLUE),
        ("BACKGROUND",    (0, 1), (-1, 1),  LIGHT_BG),
        # Subtotal rows
        ("LINEABOVE",     (-2, 2), (-1, 2), 0.5, GREY_LINE),
        ("LINEABOVE",     (-2, 3), (-1, 3), 0.5, GREY_LINE),
        ("LINEABOVE",     (-2, 4), (-1, 4), 1.2, VHS_BLUE),
        ("LINEBELOW",     (-2, 4), (-1, 4), 1.2, VHS_BLUE),
        ("BOX",           (-2, 2), (-1, 4), 0.5, GREY_LINE),
        ("BACKGROUND",    (-2, 4), (-1, 4), BLUE_BG),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    content.append(svc_table)
    content.append(Spacer(1, 0.3*cm))

    # ── BẰNG CHỮ ─────────────────────────────────────────────
    bang_chu = number_to_words_vn(int(can_thu))
    content.append(P(
        f"<i>Bằng chữ (In words): {bang_chu}</i>",
        size=9, color=colors.HexColor("#444444"),
    ))
    content.append(Spacer(1, 0.4*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    content.append(Spacer(1, 0.3*cm))

    # ── THÔNG TIN CHUYỂN KHOẢN ───────────────────────────────
    content.append(P(
        "<b>THÔNG TIN CHUYỂN KHOẢN (BANKING INFO)</b>",
        size=10, bold=True, color=VHS_BLUE,
    ))
    content.append(Spacer(1, 0.2*cm))

    ck_rows = [
        ("Tên tài khoản:", "CÔNG TY TNHH VHS"),
        ("Số tài khoản:",  "64066666"),
        ("Ngân hàng:",      "Á Châu (ACB)"),
        ("Nội dung CK:",    noidung_ck),
    ]
    ck_table = Table(
        [[P(f"<b>{r[0]}</b>", size=9, bold=True),
          P(r[1], size=9)]
         for r in ck_rows],
        colWidths=[4*cm, W - 4*cm],
    )
    ck_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CK_BG),
        ("BOX",           (0, 0), (-1, -1), 0.8, VHS_BLUE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    content.append(ck_table)
    content.append(Spacer(1, 0.6*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    content.append(Spacer(1, 0.4*cm))

    # ── KÝ TÊN ───────────────────────────────────────────────
    sign = Table([
        [P("<b>NGƯỜI LẬP PHIẾU</b><br/>(Prepared by)",
           size=9, align=TA_CENTER, bold=True),
         "",
         P("<b>ĐẠI DIỆN KHÁCH HÀNG</b><br/>(Approved by)",
           size=9, align=TA_CENTER, bold=True)],
        [P("<i>(Ký, ghi rõ họ tên)</i>",
           size=8, align=TA_CENTER, color=colors.grey),
         "", ""],
        *[["", "", ""] for _ in range(4)],
        [P("<b>TRẦN THỊ THÚY AN</b>",
           size=9, align=TA_CENTER, bold=True),
         "", ""],
    ], colWidths=[8*cm, 2*cm, 8*cm])
    sign.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    content.append(sign)

    # ── ĐÍNH KÈM (ATTACHMENTS) ───────────────────────────────
    if attachments:
        from reportlab.platypus import PageBreak
        try:
            from PIL import Image as PILImage
            for fname, fpath in attachments:
                content.append(PageBreak())
                content.append(P(f"<b>ĐÍNH KÈM:</b> {fname}", size=11, align=TA_CENTER, bold=True, color=VHS_BLUE))
                content.append(Spacer(1, 0.5*cm))
                
                if fpath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    try:
                        with PILImage.open(fpath) as img:
                            orig_w, orig_h = img.size
                        
                        max_w = A4[0] - 3*cm
                        max_h = A4[1] - 4*cm
                        ratio = min(max_w / orig_w, max_h / orig_h)
                        
                        # Chỉ zoom in tối đa 1.5x để ảnh không bị vỡ quá mức
                        if ratio > 1.5: ratio = 1.5
                        
                        new_w = orig_w * ratio
                        new_h = orig_h * ratio
                        
                        content.append(Image(fpath, width=new_w, height=new_h))
                    except Exception as e:
                        content.append(P(f"(Lỗi đọc file ảnh: {e})", size=9, align=TA_CENTER, color=colors.red))
                elif fpath.lower().endswith('.pdf'):
                    pass # Will be appended after build
                else:
                    content.append(P("(File đính kèm không hỗ trợ chèn trực tiếp)", size=9, align=TA_CENTER))
        except ImportError:
            content.append(PageBreak())
            content.append(P("Thiếu thư viện Pillow để hiển thị ảnh đính kèm.", size=10, align=TA_CENTER, color=colors.red))

    doc.build(content)
    output.seek(0)
    
    final_output = output
    if attachments:
        try:
            from pypdf import PdfWriter
            import io as _io
            
            has_pdf = any(fpath.lower().endswith('.pdf') for _, fpath in attachments)
            if has_pdf:
                merger = PdfWriter()
                merger.append(output)
                for fname, fpath in attachments:
                    if fpath.lower().endswith('.pdf'):
                        try:
                            merger.append(fpath)
                        except Exception:
                            pass
                
                merged_output = _io.BytesIO()
                merger.write(merged_output)
                merger.close()
                merged_output.seek(0)
                final_output = merged_output
        except ImportError:
            pass

    return final_output.getvalue(), f"PYC_{ma_hd}_{ky}.pdf", "application/pdf"
