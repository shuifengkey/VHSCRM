import io
import os
from datetime import datetime, timezone, timedelta

# Đường dẫn font - bundle cùng với project
_HERE = os.path.dirname(__file__)
_FONT_REGULAR = os.path.join(_HERE, "DejaVuSans.ttf")
_FONT_BOLD    = os.path.join(_HERE, "DejaVuSans-Bold.ttf")


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.getFont("DejaVuSans")
        return "DejaVuSans", "DejaVuSans-Bold"
    except Exception:
        pass
    if os.path.exists(_FONT_REGULAR) and os.path.exists(_FONT_BOLD):
        pdfmetrics.registerFont(TTFont("DejaVuSans",      _FONT_REGULAR))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _FONT_BOLD))
        return "DejaVuSans", "DejaVuSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def number_to_words_vn(n):
    if n == 0:
        return "Không đồng"

    units = ["", "nghìn", "triệu", "tỷ"]
    words = ["không", "một", "hai", "ba", "bốn", "năm",
             "sáu", "bảy", "tám", "chín"]

    def read_block(num, is_first=False):
        res = ""
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
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


def generate_payment_request_pdf(debt_data):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable, Image)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    FONT, FONT_BOLD = _register_fonts()

    def S(name, fontSize=9, alignment=TA_LEFT, bold=False, color=colors.black, leading=None):
        kw = dict(fontName=FONT_BOLD if bold else FONT,
                  fontSize=fontSize, alignment=alignment,
                  textColor=color,
                  wordWrap='CJK')
        if leading:
            kw['leading'] = leading
        return ParagraphStyle(name, **kw)

    VHS_BLUE = colors.HexColor("#1e3a5f")
    LIGHT_BG  = colors.HexColor("#f8f9fc")
    BLUE_BG   = colors.HexColor("#eef3ff")
    CK_BG     = colors.HexColor("#f0f4ff")
    GREY_LINE = colors.HexColor("#cccccc")

    def fmt(val):
        return f"{int(val):,}".replace(",", ".")

    # --- Dữ liệu ---
    now       = datetime.now(timezone.utc) + timedelta(hours=7)
    ky        = debt_data.get("ky_thanh_toan", "")
    year      = ky[:4] if ky else now.strftime("%Y")
    month_num = ky[5:7] if len(ky) >= 7 else now.strftime("%m")
    ky_display = f"Tháng {month_num}/{year}"

    tien_vat = float(debt_data.get("tien_vat", 0) or 0)
    can_thu  = float(debt_data.get("can_thu", 0) or 0)
    goc      = can_thu - tien_vat
    ten_cty  = debt_data.get("ten_cty", "")
    ma_hd    = debt_data.get("ma_hd", "")
    debt_id  = debt_data.get("id", "")
    so_phieu = f"PYC-{year}-{debt_id}"
    nguoi_lh = debt_data.get("nguoi_lien_he", "") or ""

    if tien_vat > 0 and goc > 0:
        vat_pct = round(tien_vat / goc * 100)
        vat_label = f"Thuế GTGT / VAT ({vat_pct}%):"
        vat_value = fmt(tien_vat)
    else:
        vat_label = "Thuế GTGT / VAT:"
        vat_value = "—"

    # --- Build doc ---
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.2*cm,  bottomMargin=1.5*cm,
    )

    content = []

    # ── HEADER: Logo + Thông tin công ty + Số phiếu ──
    logo_path = os.path.join(_HERE, "..", "logo.png")
    logo_path = os.path.normpath(logo_path)

    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=2.8*cm, height=2.8*cm,
                         kind='proportional')
        logo_cell = logo_img
    else:
        logo_cell = Paragraph("<b>VHS</b>",
                              S("logo_fb", fontSize=18, bold=True, color=VHS_BLUE))

    company_info = [
        Paragraph("<b>CÔNG TY TNHH VHS</b>",
                  S("ci1", fontSize=11, bold=True, color=VHS_BLUE)),
        Spacer(1, 2),
        Paragraph("Địa chỉ: 67 Đường số 3, KP2, An Khánh, HCM",
                  S("ci2", fontSize=8)),
        Paragraph("Hotline: 0783 487 586",
                  S("ci3", fontSize=8)),
        Paragraph("Email: congtytnhhvhs@gmail.com",
                  S("ci4", fontSize=8)),
    ]

    phieu_info = [
        Paragraph(f"<b>Số phiếu:</b> {so_phieu}",
                  S("pi1", fontSize=9, alignment=TA_RIGHT)),
        Spacer(1, 4),
        Paragraph(f"<b>Ngày:</b> {now.strftime('%d/%m/%Y')}",
                  S("pi2", fontSize=9, alignment=TA_RIGHT)),
        Paragraph(f"<b>Hợp đồng:</b> {ma_hd}",
                  S("pi3", fontSize=9, alignment=TA_RIGHT)),
    ]

    header_table = Table(
        [[logo_cell, company_info, phieu_info]],
        colWidths=[3.2*cm, 9.5*cm, 5.3*cm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 0.2*cm))
    content.append(HRFlowable(width="100%", thickness=2, color=VHS_BLUE))
    content.append(Spacer(1, 0.35*cm))

    # ── TIÊU ĐỀ ──
    content.append(Paragraph(
        "<b>PHIẾU YÊU CẦU THANH TOÁN</b>",
        S("title", fontSize=16, alignment=TA_CENTER, bold=True, color=VHS_BLUE),
    ))
    content.append(Paragraph(
        "(PAYMENT REQUEST / DEBIT NOTE)",
        S("subtitle", fontSize=9, alignment=TA_CENTER,
          color=colors.HexColor("#666666")),
    ))
    content.append(Spacer(1, 0.4*cm))

    # ── KÍNH GỬI ──
    kg_table = Table([
        [Paragraph("<b>Kính gửi (To):</b>",   S("kg",  fontSize=10, bold=True)),
         Paragraph(f"<b>{ten_cty}</b>",        S("kgv", fontSize=10, bold=True))],
        [Paragraph("<b>Người liên hệ (Attn):</b>", S("nl", fontSize=9, bold=True)),
         Paragraph(nguoi_lh,                   S("nlv", fontSize=9))],
    ], colWidths=[5*cm, 13*cm])
    kg_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(kg_table)
    content.append(Spacer(1, 0.35*cm))

    # ── BẢNG DỊCH VỤ ──
    TH = S("th", fontSize=9, alignment=TA_CENTER, bold=True,
           color=colors.white, leading=13)
    TD  = S("td",  fontSize=9, alignment=TA_CENTER)
    TDL = S("tdl", fontSize=9, alignment=TA_LEFT)
    TDR = S("tdr", fontSize=9, alignment=TA_RIGHT)

    table_data = [
        # Header
        [Paragraph("STT\n(No.)",                  TH),
         Paragraph("Nội dung thanh toán\n(Description of Services)", TH),
         Paragraph("Kỳ thanh toán\n(Period)",      TH),
         Paragraph("SL\n(Qty)",                    TH),
         Paragraph("Đơn giá\n(Unit Price)",         TH),
         Paragraph("Thành tiền\n(Amount)",          TH)],
        # Dòng dịch vụ
        [Paragraph("1",                                             TD),
         Paragraph("Dịch vụ kiểm soát côn trùng định kỳ\n(Pest Control Services)", TDL),
         Paragraph(ky_display,                                      TD),
         Paragraph("1",                                             TD),
         Paragraph(fmt(goc),                                        TDR),
         Paragraph(fmt(goc),                                        TDR)],
    ]

    sub_style = dict(fontSize=9, alignment=TA_RIGHT, bold=True)
    subtotal_rows = [
        ["", "", "", "",
         Paragraph("Cộng tiền dịch vụ / Subtotal:",          S("sub", **sub_style)),
         Paragraph(fmt(goc), TDR)],
        ["", "", "", "",
         Paragraph(vat_label,                                  S("vat", **sub_style)),
         Paragraph(vat_value, TDR)],
        ["", "", "", "",
         Paragraph("<b>TỔNG CỘNG / GRAND TOTAL:</b>",
                   S("tot", fontSize=10, alignment=TA_RIGHT, bold=True, color=VHS_BLUE)),
         Paragraph(f"<b>{fmt(can_thu)}</b>",
                   S("totv", fontSize=10, alignment=TA_RIGHT, bold=True, color=VHS_BLUE))],
    ]
    table_data.extend(subtotal_rows)

    col_w = [1*cm, 7*cm, 3*cm, 1*cm, 4*cm, 3*cm]
    svc_table = Table(table_data, colWidths=col_w)
    svc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  VHS_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, 1),  0.5, GREY_LINE),
        ("BOX",           (0, 0), (-1, 1),  1,   VHS_BLUE),
        ("BACKGROUND",    (0, 1), (-1, 1),  LIGHT_BG),
        # subtotal section
        ("LINEABOVE",     (-2, 2), (-1, 2), 0.5, GREY_LINE),
        ("LINEABOVE",     (-2, 3), (-1, 3), 0.5, GREY_LINE),
        ("LINEABOVE",     (-2, 4), (-1, 4), 1,   VHS_BLUE),
        ("LINEBELOW",     (-2, 4), (-1, 4), 1,   VHS_BLUE),
        ("BOX",           (-2, 2), (-1, 4), 0.5, GREY_LINE),
        ("BACKGROUND",    (-2, 4), (-1, 4), BLUE_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    content.append(svc_table)
    content.append(Spacer(1, 0.3*cm))

    # ── BẰNG CHỮ ──
    bang_chu = number_to_words_vn(int(can_thu))
    content.append(Paragraph(
        f"<i>Bằng chữ (In words): {bang_chu}</i>",
        S("bc", fontSize=9, color=colors.HexColor("#444444")),
    ))
    content.append(Spacer(1, 0.4*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    content.append(Spacer(1, 0.3*cm))

    # ── THÔNG TIN CHUYỂN KHOẢN ──
    short_name = ten_cty[:25] if ten_cty else "Khach hang"
    noidung_ck = f"VHS {short_name} thanh toan"

    content.append(Paragraph(
        "<b>THÔNG TIN CHUYỂN KHOẢN (BANKING INFO)</b>",
        S("ck_title", fontSize=10, bold=True, color=VHS_BLUE),
    ))
    content.append(Spacer(1, 0.2*cm))

    ck_rows = [
        ["Tên tài khoản:", "CÔNG TY TNHH VHS"],
        ["Số tài khoản:",  "64066666"],
        ["Ngân hàng:",      "Á Châu (ACB)"],
        ["Nội dung CK:",    noidung_ck],
    ]
    ck_table = Table(
        [[Paragraph(r[0], S(f"ckl{i}", fontSize=9, bold=True)),
          Paragraph(r[1], S(f"ckv{i}", fontSize=9))]
         for i, r in enumerate(ck_rows)],
        colWidths=[4*cm, 14*cm],
    )
    ck_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CK_BG),
        ("BOX",           (0, 0), (-1, -1), 0.5, VHS_BLUE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    content.append(ck_table)
    content.append(Spacer(1, 0.6*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=GREY_LINE))
    content.append(Spacer(1, 0.4*cm))

    # ── KÝ TÊN ──
    sign_data = [
        [Paragraph("<b>NGƯỜI LẬP PHIẾU</b><br/>(Prepared by)",
                   S("sl", fontSize=9, alignment=TA_CENTER, bold=True)),
         "",
         Paragraph("<b>ĐẠI DIỆN KHÁCH HÀNG</b><br/>(Approved by)",
                   S("sr", fontSize=9, alignment=TA_CENTER, bold=True))],
        [Paragraph("<i>(Ký, ghi rõ họ tên)</i>",
                   S("sl2", fontSize=8, alignment=TA_CENTER,
                     color=colors.grey)), "", ""],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        [Paragraph("<b>TRẦN THỊ THÚY AN</b>",
                   S("sn", fontSize=9, alignment=TA_CENTER, bold=True)),
         "", ""],
    ]
    sign_table = Table(sign_data, colWidths=[8*cm, 2*cm, 8*cm])
    sign_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    content.append(sign_table)

    doc.build(content)
    output.seek(0)
    filename = f"PYC_{ma_hd}_{ky}.pdf"
    return output.getvalue(), filename, "application/pdf"
