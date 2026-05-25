# VHS CRM - Pest Control Management System

## Cài đặt & Chạy

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cấu trúc thư mục

```
vhs_crm/
├── app.py                    # Điểm vào chính + Dashboard
├── requirements.txt
├── vhs_crm.db               # SQLite DB (tự tạo khi chạy lần đầu)
├── utils/
│   ├── database.py          # Khởi tạo DB, CRUD helpers
│   ├── scheduling.py        # Logic lịch + xử lý ca đêm
│   └── pdf_generator.py     # Sinh PDF bằng ReportLab
└── pages/
    ├── p1_customers.py      # Module 1: Master Data
    ├── p2_contracts.py      # Module 2: Hợp đồng
    ├── p3_scheduling.py     # Module 3: Smart Scheduling
    ├── p4_logbook.py        # Module 4: Logbook KTV
    ├── p5_pdf.py            # Module 5: Xuất PDF
    └── p6_debts.py          # Module 6: Công nợ
```

## Các tính năng đặc biệt

### Logic Ca Đêm (Midnight Crossing)
Ca thi công 23:00-02:00 ngày 22/05: Nếu kiểm tra lúc 01:30 ngày 23/05,
hệ thống vẫn hiển thị ca này trong "Việc Hôm Nay".

### Tính Ngày Tiếp Theo
Dùng `dateutil.relativedelta` - tự động xử lý cuối tháng:
- 31/01 + 1 tháng → 28/02 (không crash)

### Cảnh Báo Giờ Check-in
So sánh giờ check-in thực tế vs khung giờ HĐ, cảnh báo nếu sai > 30 phút.
