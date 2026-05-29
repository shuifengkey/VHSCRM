# utils/pdf_generator.py
# Sinh PDF tự động bằng ReportLab - Báo giá, Hợp đồng, Phiếu xác nhận dịch vụ
import io
from datetime import timezone, date, datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

_font_path = os.path.join(os.path.dirname(__file__), "Square-721-Extended-BT.ttf")
if os.path.exists(_font_path):
    pdfmetrics.registerFont(TTFont('Square721', _font_path))
    HEADER_FONT = "Square721"
else:
    HEADER_FONT = "Helvetica-Bold"

# Màu thương hiệu VHS
VHS_GREEN = colors.HexColor("#1a6b3c")
VHS_LIGHT = colors.HexColor("#e8f5ee")
VHS_DARK = colors.HexColor("#0d3d22")

def format_currency(amount: float) -> str:
    """Format số tiền VNĐ, VD: 3500000 → 3.500.000 đ"""
    return f"{int(amount):,}".replace(",", ".") + " đ"

def _build_header(elements, styles, doc_type: str, ma_so: str):
    """Xây dựng phần header chung cho tất cả loại chứng từ"""
    # Tiêu đề công ty
    elements.append(Paragraph(
        "CÔNG TY TNHH VHS",
        ParagraphStyle("CompanyName", parent=styles["Normal"],
                       fontSize=16, textColor=VHS_GREEN,
                       spaceAfter=2, alignment=TA_CENTER, fontName=HEADER_FONT)
    ))
    elements.append(Paragraph(
        "Dịch vụ Kiểm soát Dịch hại Chuyên nghiệp",
        ParagraphStyle("Tagline", parent=styles["Normal"],
                       fontSize=9, textColor=colors.grey,
                       spaceAfter=2, alignment=TA_CENTER)
    ))
    elements.append(Paragraph(
        "📞 1800-VHS-PEST | ✉ contact@vhs.vn | 🌐 www.vhs.vn",
        ParagraphStyle("Contact", parent=styles["Normal"],
                       fontSize=8, textColor=colors.grey,
                       spaceAfter=8, alignment=TA_CENTER)
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=VHS_GREEN))
    elements.append(Spacer(1, 0.3*cm))

    # Tên loại chứng từ
    elements.append(Paragraph(
        f"<b>{doc_type.upper()}</b>",
        ParagraphStyle("DocTitle", parent=styles["Normal"],
                       fontSize=14, textColor=VHS_DARK,
                       spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold")
    ))
    elements.append(Paragraph(
        f"Số: {ma_so} | Ngày: {(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%d/%m/%Y')}",
        ParagraphStyle("DocNum", parent=styles["Normal"],
                       fontSize=9, textColor=colors.grey,
                       spaceAfter=10, alignment=TA_CENTER)
    ))

def generate_bao_gia(customer: dict, contract: dict) -> bytes:
    """
    Sinh PDF Báo giá từ dữ liệu khách hàng và hợp đồng.
    Trả về bytes (dùng để download trực tiếp qua Streamlit).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    elements = []

    # --- Header ---
    _build_header(elements, styles, "BÁO GIÁ DỊCH VỤ", f"BG-{contract.get('ma_hd','')}")

    # --- Thông tin khách hàng ---
    elements.append(Paragraph("<b>THÔNG TIN KHÁCH HÀNG</b>",
        ParagraphStyle("SectionHead", parent=styles["Normal"],
                       fontSize=10, textColor=VHS_GREEN, fontName="Helvetica-Bold", spaceAfter=4)))

    kh_data = [
        ["Tên công ty:", customer.get("ten_phap_ly") or customer.get("ten_cty", "")],
        ["Mã số thuế:", customer.get("ma_so_thue", "")],
        ["Địa chỉ:", customer.get("dia_chi_phap_ly") or customer.get("dia_chi", "")],
        ["Người đại diện:", customer.get("dai_dien", "")],
        ["Điện thoại:", customer.get("sdt", "")],
    ]
    kh_table = Table(kh_data, colWidths=[4*cm, 13*cm])
    kh_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), VHS_DARK),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(kh_table)
    elements.append(Spacer(1, 0.3*cm))

    # --- Chi tiết dịch vụ ---
    elements.append(Paragraph("<b>CHI TIẾT DỊCH VỤ</b>",
        ParagraphStyle("SectionHead", parent=styles["Normal"],
                       fontSize=10, textColor=VHS_GREEN, fontName="Helvetica-Bold", spaceAfter=4)))

    tan_suat_map = {1:"1 lần/tháng", 2:"2 lần/tháng", 4:"4 lần/tháng", 8:"8 lần/tháng"}
    tan_suat_text = tan_suat_map.get(contract.get("tan_suat", 1), f"{contract.get('tan_suat')} lần/tháng")

    service_data = [
        ["STT", "Nội dung dịch vụ", "Tần suất", "Đơn giá/tháng"],
        ["1", "Kiểm soát dịch hại định kỳ\n(Côn trùng, gián, chuột)", tan_suat_text,
         format_currency(contract.get("gia_tri_thang", 0))],
        ["", "Khung giờ thi công:", f"{contract.get('gio_bat_dau','')} - {contract.get('gio_ket_thuc','')}", ""],
    ]
    svc_table = Table(service_data, colWidths=[1.5*cm, 8.5*cm, 3.5*cm, 3.5*cm])
    svc_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VHS_GREEN),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ALIGN", (1,1), (1,-1), "LEFT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [VHS_LIGHT, colors.white]),
        ("BOX", (0,0), (-1,-1), 0.5, VHS_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    elements.append(svc_table)
    elements.append(Spacer(1, 0.2*cm))

    # --- Tổng cộng ---
    gia_tri = contract.get("gia_tri_thang", 0)
    vat = gia_tri * 0.1
    total = gia_tri + vat
    total_data = [
        ["", "Giá chưa VAT:", format_currency(gia_tri)],
        ["", "VAT 10%:", format_currency(vat)],
        ["", "TỔNG CỘNG:", format_currency(total)],
    ]
    total_table = Table(total_data, colWidths=[10.5*cm, 3.5*cm, 3*cm])
    total_table.setStyle(TableStyle([
        ("FONTNAME", (1,2), (2,2), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (2,-1), "RIGHT"),
        ("BACKGROUND", (1,2), (2,2), VHS_LIGHT),
        ("TEXTCOLOR", (1,2), (2,2), VHS_DARK),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.5*cm))

    # --- Điều khoản ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("<b>ĐIỀU KHOẢN BÁO GIÁ</b>",
        ParagraphStyle("Note", parent=styles["Normal"], fontSize=8, textColor=VHS_DARK,
                       fontName="Helvetica-Bold", spaceAfter=2)))
    notes = [
        "• Báo giá có hiệu lực trong vòng 30 ngày kể từ ngày phát hành.",
        "• Giá trên chưa bao gồm chi phí phát sinh ngoài phạm vi dịch vụ.",
        "• Thanh toán theo chu kỳ hàng tháng, trong vòng 15 ngày sau khi nhận hóa đơn.",
        "• VHS cam kết bảo mật thông tin khách hàng.",
    ]
    for note in notes:
        elements.append(Paragraph(note, ParagraphStyle("NoteItem", parent=styles["Normal"],
                                  fontSize=8, textColor=colors.grey, spaceAfter=1)))

    elements.append(Spacer(1, 0.8*cm))

    # --- Chữ ký ---
    sig_data = [
        ["ĐẠI DIỆN KHÁCH HÀNG", "", "ĐẠI DIỆN CÔNG TY VHS"],
        ["\n\n\n(Ký, ghi rõ họ tên)", "", "\n\n\n(Ký, đóng dấu)"],
    ]
    sig_table = Table(sig_data, colWidths=[6*cm, 5*cm, 6*cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TEXTCOLOR", (0,0), (-1,0), VHS_DARK),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    return buffer.getvalue()


def generate_phieu_xac_nhan(customer: dict, contract: dict, logbook_entry: dict) -> bytes:
    """Sinh PDF Phiếu xác nhận dịch vụ sau khi thi công hoàn thành"""
    
    # Check if template exists
    template_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "VHS PCC.pdf"))
    if os.path.exists(template_path):
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io
            
            font_path = os.path.join(os.path.dirname(__file__), "Roboto-Regular.ttf")
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont("Roboto", font_path))
                fnt = "Roboto"
            else:
                fnt = "Helvetica"

            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=A4)
            c.setFont(fnt, 11)

            c.drawString(160, 670, str(customer.get("ten_cty", "")))
            c.drawString(120, 648, str(customer.get("dia_chi", "")))
            c.drawString(140, 628, str(customer.get("sdt", "") or customer.get("so_dt", "")))

            # Thời gian
            ci = logbook_entry.get("checkin_time", "")
            co = logbook_entry.get("checkout_time", "")
            d_str = ""
            m_str = ""
            
            if ci:
                try:
                    dt_ci = datetime.fromisoformat(ci)
                    c.drawString(110, 310, dt_ci.strftime("%H:%M"))
                    d_str = dt_ci.strftime("%d")
                    m_str = dt_ci.strftime("%m")
                except:
                    c.drawString(110, 310, ci[:5])
            if co:
                try:
                    dt_co = datetime.fromisoformat(co)
                    c.drawString(245, 310, dt_co.strftime("%H:%M"))
                except:
                    c.drawString(245, 310, co[:5])

            if d_str:
                c.drawString(345, 310, d_str)
                c.drawString(410, 310, m_str)

            # Checkboxes mapping
            checkbox_coords = {
                "Làm mới": [48.6, 579.0], "Định kì": [202.26, 579.0], "Bổ sung": [311.09, 579.0], "Kiểm tra": [450.26, 579.0],
                "Ruồi": [48.6, 525.3], "Ong": [48.6, 508.96], "Mối": [48.6, 491.25], "Muỗi": [197.13, 525.3], "Nhện": [197.13, 508.28], "Mọt": [197.13, 491.26], "Chuột": [380.89, 525.3], "Kiến": [380.89, 508.28], "Gián": [380.89, 491.94],
                "Nhà hàng": [48.6, 438.24], "Sân vườn": [48.6, 420.53], "Văn phòng": [245.58, 438.25], "Bếp": [245.58, 420.53], "Cửa hàng": [413.1, 437.56], "Toà nhà": [413.1, 421.22],
                "Phun sương": [48.59, 366.84], "Đặt bẫy": [230.71, 366.84], "Phun tồn lưu": [383.7, 366.84], "Phun khói": [48.59, 350.5], "Khử trùng": [230.71, 349.81], "Bả": [383.7, 349.81]
            }
            
            hc = logbook_entry.get("hoa_chat", "").lower()
            kq = logbook_entry.get("ket_qua", "").lower()
            combined_text = f"{hc} {kq}"
            
            for key, (x, y) in checkbox_coords.items():
                if key.lower() in combined_text:
                    c.drawString(x - 13, y + 2, 'x')

            c.setFont(fnt, 12)
            c.drawString(100, 105, str(logbook_entry.get("ky_thuat_vien", "")))

            c.save()
            packet.seek(0)

            new_pdf = PdfReader(packet)
            existing_pdf = PdfReader(open(template_path, "rb"))
            output = PdfWriter()

            page = existing_pdf.pages[0]
            page.merge_page(new_pdf.pages[0])
            output.add_page(page)

            out_buffer = io.BytesIO()
            output.write(out_buffer)
            return out_buffer.getvalue()
        except Exception as e:
            print(f"Error using PCC template: {e}")
            # Fall back to normal generation if error
            pass

    # --- FALLBACK TO NATIVE REPORTLAB ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    elements = []

    ma_phieu = f"PXN-{(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime('%Y%m%d%H%M')}"
    _build_header(elements, styles, "PHIẾU XÁC NHẬN DỊCH VỤ", ma_phieu)

    # Thông tin công trình
    elements.append(Paragraph("<b>THÔNG TIN CÔNG TRÌNH</b>",
        ParagraphStyle("SH", parent=styles["Normal"], fontSize=10, textColor=VHS_GREEN,
                       fontName="Helvetica-Bold", spaceAfter=4)))

    info_data = [
        ["Khách hàng:", customer.get("ten_cty", ""), "Mã HĐ:", contract.get("ma_hd", "")],
        ["Địa chỉ:", customer.get("dia_chi", ""), "Kỹ thuật viên:", logbook_entry.get("ky_thuat_vien", "")],
        ["Thời gian vào:", logbook_entry.get("checkin_time", "")[:16] if logbook_entry.get("checkin_time") else "",
         "Thời gian ra:", logbook_entry.get("checkout_time", "")[:16] if logbook_entry.get("checkout_time") else ""],
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 6.5*cm, 3.5*cm, 3.5*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), VHS_DARK),
        ("TEXTCOLOR", (2,0), (2,-1), VHS_DARK),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [VHS_LIGHT, colors.white]),
        ("BOX", (0,0), (-1,-1), 0.5, VHS_GREEN),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*cm))

    # Hóa chất sử dụng
    elements.append(Paragraph("<b>HÓA CHẤT & PHƯƠNG PHÁP XỬ LÝ</b>",
        ParagraphStyle("SH2", parent=styles["Normal"], fontSize=10, textColor=VHS_GREEN,
                       fontName="Helvetica-Bold", spaceAfter=4)))
    elements.append(Paragraph(
        logbook_entry.get("hoa_chat", "Không có ghi chú"),
        ParagraphStyle("Content", parent=styles["Normal"], fontSize=9,
                       borderPad=5, borderColor=VHS_GREEN, borderWidth=0.5)
    ))
    elements.append(Spacer(1, 0.3*cm))

    # Kết quả
    elements.append(Paragraph("<b>NHẬN XÉT / KẾT QUẢ</b>",
        ParagraphStyle("SH3", parent=styles["Normal"], fontSize=10, textColor=VHS_GREEN,
                       fontName="Helvetica-Bold", spaceAfter=4)))
    elements.append(Paragraph(
        logbook_entry.get("ket_qua", "Hoàn thành tốt"),
        ParagraphStyle("Content2", parent=styles["Normal"], fontSize=9)
    ))
    elements.append(Spacer(1, 1*cm))

    # Chữ ký xác nhận
    sig_data = [
        ["ĐẠI DIỆN KHÁCH HÀNG\n(Xác nhận đã nhận dịch vụ)", "", "KỸ THUẬT VIÊN VHS\n(Người thực hiện)"],
        ["\n\n\n" + customer.get("ten_cty",""), "", "\n\n\n" + logbook_entry.get("ky_thuat_vien", "")],
    ]
    sig_table = Table(sig_data, colWidths=[6*cm, 5*cm, 6*cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TEXTCOLOR", (0,0), (-1,0), VHS_DARK),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    return buffer.getvalue()


def generate_hop_dong(customer: dict, contract: dict) -> bytes:
    """Sinh PDF Hợp đồng dịch vụ đầy đủ"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    elements = []

    _build_header(elements, styles, "HỢP ĐỒNG DỊCH VỤ KIỂM SOÁT DỊCH HẠI",
                  contract.get("ma_hd", ""))

    # Thông tin hai bên
    two_party = [
        ["BÊN A (KHÁCH HÀNG)", "BÊN B (CÔNG TY VHS)"],
        [customer.get("ten_cty",""), "CÔNG TY TNHH VHS"],
        [customer.get("dia_chi",""), "Địa chỉ: 100 Đường ABC, Q1, TP.HCM"],
        [f"Đại diện: {customer.get('dai_dien','')}", "Đại diện: Nguyễn Văn Giám Đốc"],
        [f"ĐT: {customer.get('sdt','')}", "ĐT: 1800-VHS-PEST"],
    ]
    tp_table = Table(two_party, colWidths=[8.5*cm, 8.5*cm])
    tp_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VHS_GREEN),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [VHS_LIGHT, colors.white]),
        ("BOX", (0,0), (-1,-1), 0.5, VHS_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    elements.append(tp_table)
    elements.append(Spacer(1, 0.4*cm))

    # Điều khoản hợp đồng
    clauses = [
        ("ĐIỀU 1: NỘI DUNG DỊCH VỤ",
         "Bên B thực hiện dịch vụ kiểm soát dịch hại định kỳ tại cơ sở của Bên A bao gồm: "
         "diệt trừ côn trùng (gián, kiến, muỗi), kiểm soát và tiêu diệt chuột, xử lý các loại "
         "dịch hại khác theo yêu cầu. Sử dụng hóa chất được Bộ Y tế cấp phép, an toàn cho người và thực phẩm."),
        ("ĐIỀU 2: THỜI HẠN & TẦN SUẤT",
         f"Hợp đồng có hiệu lực từ {contract.get('ngay_ky','')} đến {contract.get('ngay_het_han','')}. "
         f"Tần suất thi công: {contract.get('tan_suat',1)} lần/tháng. "
         f"Khung giờ thi công: {contract.get('gio_bat_dau','')} - {contract.get('gio_ket_thuc','')}."),
        ("ĐIỀU 3: GIÁ TRỊ HỢP ĐỒNG",
         f"Giá trị hợp đồng: {format_currency(contract.get('gia_tri_thang',0))}/tháng (chưa VAT). "
         "Thanh toán theo tháng, trong vòng 15 ngày sau khi nhận hóa đơn. "
         "Phương thức: chuyển khoản hoặc tiền mặt."),
        ("ĐIỀU 4: TRÁCH NHIỆM CÁC BÊN",
         "Bên B đảm bảo chất lượng dịch vụ, sử dụng kỹ thuật viên có chứng chỉ hành nghề. "
         "Bên A tạo điều kiện thuận lợi cho kỹ thuật viên thực hiện công việc đúng giờ đã thỏa thuận."),
        ("ĐIỀU 5: ĐIỀU KHOẢN CHUNG",
         "Hợp đồng được lập thành 02 bản có giá trị pháp lý như nhau. Mỗi bên giữ 01 bản. "
         "Mọi tranh chấp phát sinh được giải quyết trên tinh thần thương lượng, hòa giải."),
    ]

    for title, content in clauses:
        elements.append(Paragraph(f"<b>{title}</b>",
            ParagraphStyle("ClauseTitle", parent=styles["Normal"],
                           fontSize=9, textColor=VHS_DARK, fontName="Helvetica-Bold",
                           spaceBefore=6, spaceAfter=2)))
        elements.append(Paragraph(content,
            ParagraphStyle("ClauseContent", parent=styles["Normal"],
                           fontSize=8.5, leading=13, textColor=colors.black)))

    elements.append(Spacer(1, 0.8*cm))

    # Ký kết
    date_str = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).strftime("TP. Hồ Chí Minh, ngày %d tháng %m năm %Y")
    elements.append(Paragraph(date_str,
        ParagraphStyle("DateSign", parent=styles["Normal"],
                       fontSize=9, alignment=TA_CENTER, spaceAfter=8)))

    sig_data = [
        ["BÊN A\n(Ký, đóng dấu, ghi rõ họ tên)", "", "BÊN B\n(Ký, đóng dấu, ghi rõ họ tên)"],
        ["\n\n\n" + customer.get("dai_dien",""), "", "\n\n\nGiám đốc VHS"],
    ]
    sig_table = Table(sig_data, colWidths=[6*cm, 5*cm, 6*cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TEXTCOLOR", (0,0), (-1,0), VHS_DARK),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    return buffer.getvalue()
