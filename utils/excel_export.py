import io
import os
from datetime import datetime, timezone, timedelta

def number_to_words_vn(n):
    if n == 0:
        return "Không đồng"

    units = ["", "nghìn", "triệu", "tỷ"]
    words = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_block_3(num, is_first=False):
        res = ""
        hundred = num // 100
        ten = (num % 100) // 10
        unit = num % 10

        if not is_first or hundred > 0:
            res += words[hundred] + " trăm "
            if ten == 0 and unit > 0:
                res += "lẻ "

        if ten == 1:
            res += "mười "
        elif ten > 1:
            res += words[ten] + " mươi "

        if unit == 1 and ten > 1:
            res += "mốt "
        elif unit == 5 and ten > 0:
            res += "lăm "
        elif unit > 0:
            res += words[unit] + " "

        return res.strip()

    blocks = []
    n_copy = n
    while n_copy > 0:
        blocks.append(n_copy % 1000)
        n_copy //= 1000

    parts = []
    for i in range(len(blocks) - 1, -1, -1):
        b = blocks[i]
        if b > 0:
            is_first = (i == len(blocks) - 1)
            part = read_block_3(b, is_first)
            if units[i]:
                part += " " + units[i]
            parts.append(part)

    result = " ".join(parts).strip() + " đồng"
    return result.capitalize()


def generate_payment_request_pdf(debt_data):
    """
    Tạo file PDF Phiếu Yêu Cầu Thanh Toán bằng reportlab.
    debt_data: dict chứa thông tin nợ
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Đăng ký font hỗ trợ tiếng Việt
    # Dùng Helvetica mặc định nếu không có font Việt
    try:
        import reportlab
        base_dir = os.path.dirname(reportlab.__file__)
        # Thử dùng DejaVu nếu có
        font_path = os.path.join(base_dir, "fonts", "DejaVuSans.ttf")
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(base_dir, "fonts", "DejaVuSans-Bold.ttf")))
            FONT = "DejaVuSans"
            FONT_BOLD = "DejaVuSans-Bold"
        else:
            FONT = "Helvetica"
            FONT_BOLD = "Helvetica-Bold"
    except:
        FONT = "Helvetica"
        FONT_BOLD = "Helvetica-Bold"

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=1.2*cm,
    )

    W, H = A4
    content = []
    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        return ParagraphStyle(name, fontName=FONT, **kwargs)

    def style_bold(name, **kwargs):
        return ParagraphStyle(name, fontName=FONT_BOLD, **kwargs)

    # --- THÔNG TIN CÔNG TY ---
    now = datetime.now(timezone.utc) + timedelta(hours=7)
    ky = debt_data.get("ky_thanh_toan", "")
    year = ky[:4] if ky else now.strftime("%Y")
    month_num = ky[5:7] if len(ky) >= 7 else now.strftime("%m")
    ky_display = f"Tháng {month_num}/{year}"

    tien_vat = float(debt_data.get("tien_vat", 0) or 0)
    can_thu = float(debt_data.get("can_thu", 0) or 0)
    goc = can_thu - tien_vat

    ten_cty = debt_data.get("ten_cty", "")
    ma_hd = debt_data.get("ma_hd", "")
    debt_id = debt_data.get("id", "")
    so_phieu = f"PYC-{year}-{debt_id}"

    def fmt(val):
        return f"{int(val):,}".replace(",", ".")

    # Header: Logo + Thông tin công ty + Số phiếu
    header_data = [
        [
            Paragraph("<b>CÔNG TY TNHH VHS</b>", style_bold("h1", fontSize=11)),
            "",
            Paragraph(f"<b>Số phiếu:</b> {so_phieu}", style("h1r", fontSize=9, alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Địa chỉ: 67 Đường số 3, KP2, An Khánh, HCM", style("addr", fontSize=8)),
            "",
            Paragraph(f"<b>Ngày:</b> {now.strftime('%d/%m/%Y')}", style("h1r", fontSize=9, alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Hotline: 0783 487 586  |  Email: congtytnhhvhs@gmail.com", style("addr", fontSize=8)),
            "",
            Paragraph(f"<b>Hợp đồng:</b> {ma_hd}", style("h1r", fontSize=9, alignment=TA_RIGHT)),
        ],
    ]
    header_table = Table(header_data, colWidths=[9*cm, 2*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    content.append(header_table)
    content.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a5f")))
    content.append(Spacer(1, 0.3*cm))

    # Tiêu đề chính
    content.append(Paragraph(
        "<b>PHIẾU YÊU CẦU THANH TOÁN</b>",
        style_bold("title", fontSize=16, alignment=TA_CENTER, textColor=colors.HexColor("#1e3a5f"))
    ))
    content.append(Paragraph(
        "(PAYMENT REQUEST / DEBIT NOTE)",
        style("subtitle", fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor("#666666"))
    ))
    content.append(Spacer(1, 0.4*cm))

    # Kính gửi
    kinhgui_data = [
        [Paragraph("<b>Kính gửi (To):</b>", style_bold("kg", fontSize=10)),
         Paragraph(f"<b>{ten_cty}</b>", style_bold("kgv", fontSize=10))],
        [Paragraph("<b>Người liên hệ (Attn):</b>", style_bold("nl", fontSize=9)),
         Paragraph(debt_data.get("nguoi_lien_he", ""), style("nlv", fontSize=9))],
    ]
    kg_table = Table(kinhgui_data, colWidths=[5.5*cm, 12.5*cm])
    kg_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    content.append(kg_table)
    content.append(Spacer(1, 0.3*cm))

    # Bảng chi tiết dịch vụ
    COL_HEADER_STYLE = style_bold("th", fontSize=9, alignment=TA_CENTER, textColor=colors.white)
    COL_DATA_STYLE = style("td", fontSize=9, alignment=TA_CENTER)
    COL_DATA_LEFT = style("tdl", fontSize=9, alignment=TA_LEFT)
    COL_DATA_RIGHT = style("tdr", fontSize=9, alignment=TA_RIGHT)

    table_data = [
        [
            Paragraph("STT\n(No.)", COL_HEADER_STYLE),
            Paragraph("Nội dung thanh toán\n(Description of Services)", COL_HEADER_STYLE),
            Paragraph("Kỳ thanh toán\n(Period)", COL_HEADER_STYLE),
            Paragraph("SL\n(Qty)", COL_HEADER_STYLE),
            Paragraph("Đơn giá\n(Unit Price)", COL_HEADER_STYLE),
            Paragraph("Thành tiền\n(Amount)", COL_HEADER_STYLE),
        ],
        [
            Paragraph("1", COL_DATA_STYLE),
            Paragraph("Dịch vụ kiểm soát côn trùng định kỳ\n(Pest Control Services)", COL_DATA_LEFT),
            Paragraph(ky_display, COL_DATA_STYLE),
            Paragraph("1", COL_DATA_STYLE),
            Paragraph(fmt(goc), COL_DATA_RIGHT),
            Paragraph(fmt(goc), COL_DATA_RIGHT),
        ],
    ]

    # Nếu không có VAT
    if tien_vat == 0:
        vat_label = "—"
        vat_value = "—"
        vat_pct_label = "VAT:"
    else:
        vat_pct = round((tien_vat / goc * 100)) if goc > 0 else 0
        vat_label = f"{vat_pct}%"
        vat_value = fmt(tien_vat)
        vat_pct_label = f"Thuế GTGT / VAT ({vat_pct}%):"

    # Subtotal rows
    subtotal_rows = [
        ["", "", "", "", Paragraph("Cộng tiền dịch vụ / Subtotal:", style_bold("sub", fontSize=9, alignment=TA_RIGHT)), Paragraph(fmt(goc), COL_DATA_RIGHT)],
        ["", "", "", "", Paragraph(vat_pct_label, style_bold("vat", fontSize=9, alignment=TA_RIGHT)), Paragraph(vat_value, COL_DATA_RIGHT)],
        ["", "", "", "", Paragraph("<b>TỔNG CỘNG / GRAND TOTAL:</b>", style_bold("tot", fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor("#1e3a5f"))), Paragraph(f"<b>{fmt(can_thu)}</b>", style_bold("totv", fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor("#1e3a5f")))],
    ]
    table_data.extend(subtotal_rows)

    col_widths = [1*cm, 6.5*cm, 3*cm, 1.2*cm, 4.3*cm, 3*cm]
    svc_table = Table(table_data, colWidths=col_widths)
    svc_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Grid
        ("GRID", (0, 0), (-1, 1), 0.5, colors.HexColor("#cccccc")),
        ("BOX", (0, 0), (-1, 1), 1, colors.HexColor("#1e3a5f")),
        # Subtotal rows: chỉ border cột cuối
        ("LINEABOVE", (-2, 2), (-1, 2), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (-2, 3), (-1, 3), 0.5, colors.HexColor("#cccccc")),
        ("LINEABOVE", (-2, 4), (-1, 4), 1, colors.HexColor("#1e3a5f")),
        ("LINEBELOW", (-2, 4), (-1, 4), 1, colors.HexColor("#1e3a5f")),
        ("BOX", (-2, 2), (-1, 4), 0.5, colors.HexColor("#cccccc")),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Background row dữ liệu
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8f9fc")),
        # Grand total highlight
        ("BACKGROUND", (-2, 4), (-1, 4), colors.HexColor("#eef3ff")),
    ]))
    content.append(svc_table)
    content.append(Spacer(1, 0.3*cm))

    # Bằng chữ
    bang_chu = number_to_words_vn(int(can_thu))
    content.append(Paragraph(
        f"<i>Bằng chữ (In words): {bang_chu}</i>",
        style("bchu", fontSize=9, textColor=colors.HexColor("#444444"))
    ))
    content.append(Spacer(1, 0.4*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    content.append(Spacer(1, 0.3*cm))

    # Thông tin chuyển khoản
    short_name = ten_cty[:25] if ten_cty else "Khach hang"
    noidung_ck = f"VHS {short_name} thanh toan"

    content.append(Paragraph("<b>THÔNG TIN CHUYỂN KHOẢN (BANKING INFO)</b>", style_bold("ck_title", fontSize=10, textColor=colors.HexColor("#1e3a5f"))))
    content.append(Spacer(1, 0.2*cm))

    ck_data = [
        [Paragraph("Tên tài khoản:", style_bold("ck", fontSize=9)), Paragraph("CÔNG TY TNHH VHS", style("ckv", fontSize=9))],
        [Paragraph("Số tài khoản:", style_bold("ck", fontSize=9)), Paragraph("64066666", style("ckv", fontSize=9))],
        [Paragraph("Ngân hàng:", style_bold("ck", fontSize=9)), Paragraph("Á Châu (ACB)", style("ckv", fontSize=9))],
        [Paragraph("Nội dung CK:", style_bold("ck", fontSize=9)), Paragraph(noidung_ck, style("ckv", fontSize=9))],
    ]
    ck_table = Table(ck_data, colWidths=[4*cm, 14*cm])
    ck_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a5f")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    content.append(ck_table)
    content.append(Spacer(1, 0.6*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    content.append(Spacer(1, 0.4*cm))

    # Ký tên
    sign_data = [
        [
            Paragraph("<b>NGƯỜI LẬP PHIẾU</b>\n(Prepared by)", style_bold("sign", fontSize=9, alignment=TA_CENTER)),
            "",
            Paragraph("<b>ĐẠI DIỆN KHÁCH HÀNG</b>\n(Approved by)", style_bold("sign", fontSize=9, alignment=TA_CENTER)),
        ],
        [
            Paragraph("<i>(Ký, ghi rõ họ tên)</i>", style("sign_hint", fontSize=8, alignment=TA_CENTER, textColor=colors.grey)),
            "",
            Paragraph("<i>(Ký, ghi rõ họ tên)</i>", style("sign_hint", fontSize=8, alignment=TA_CENTER, textColor=colors.grey)),
        ],
        [
            Paragraph(" ", style("sign_space", fontSize=8)),
            "",
            Paragraph(" ", style("sign_space", fontSize=8)),
        ],
        [
            Paragraph(" ", style("sign_space", fontSize=8)),
            "",
            Paragraph(" ", style("sign_space", fontSize=8)),
        ],
        [
            Paragraph(" ", style("sign_space", fontSize=8)),
            "",
            Paragraph(" ", style("sign_space", fontSize=8)),
        ],
        [
            Paragraph("<b>TRẦN THỊ THÚY AN</b>", style_bold("sign_name", fontSize=9, alignment=TA_CENTER)),
            "",
            Paragraph(" ", style("sign_name", fontSize=9, alignment=TA_CENTER)),
        ],
    ]
    sign_table = Table(sign_data, colWidths=[8*cm, 2*cm, 8*cm])
    sign_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    content.append(sign_table)

    doc.build(content)
    output.seek(0)
    filename = f"PYC_{ma_hd}_{ky}.pdf"
    return output.getvalue(), filename, "application/pdf"
