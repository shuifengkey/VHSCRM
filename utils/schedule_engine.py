# utils/schedule_engine.py
# Engine tự động sinh & quản lý lịch thi công theo hợp đồng
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from utils.scheduling import auto_generate_schedules

def _get_conn():
    from utils.database import get_connection
    return get_connection()

def auto_generate_month(contract: dict, target_month: date) -> list:
    """Sinh lịch bằng hàm ở utils/scheduling."""
    ky_thang = target_month.strftime("%Y-%m")
    auto_generate_schedules(contract["ma_hd"], ky_thang)
    return []

def generate_next_occurrence(contract: dict, completed_schedule: dict) -> list:
    """
    Sau khi 1 ca hoàn thành → tự tạo ca kế tiếp trong tháng sau (nếu chưa có).
    """
    last_date = date.fromisoformat(completed_schedule["ngay_du_kien"])
    next_month_start = (last_date.replace(day=1) + relativedelta(months=1))
    ky_next = next_month_start.strftime("%Y-%m")
    
    # Hỗ trợ chu kỳ Khách lẻ
    if contract.get("loai_khach") == "Khách lẻ":
        chu_ky_lap = contract.get("chu_ky_lap", "1_lan")
        if chu_ky_lap == "1_lan": return []
        
        if chu_ky_lap.endswith("_thang") or chu_ky_lap.endswith("_nam"):
            parts = chu_ky_lap.split('_')
            x = int(parts[0])
            if parts[1] == "nam": x *= 12
            next_month_start = (last_date.replace(day=1) + relativedelta(months=x))
            ky_next = next_month_start.strftime("%Y-%m")
        elif chu_ky_lap.endswith("_tuan"):
            parts = chu_ky_lap.split('_')
            x = int(parts[0])
            next_date = last_date + timedelta(days=x * 7)
            ky_next = next_date.strftime("%Y-%m")

    n = auto_generate_schedules(contract["ma_hd"], ky_next)
    return [ky_next] if n > 0 else []

def complete_schedule(schedule_id: int, contract: dict) -> dict:
    """
    Đánh dấu 1 ca là completed, tự sinh ca kế tiếp và tự động ghi nhận công nợ.
    """
    conn = _get_conn()
    conn.execute("UPDATE schedules SET trang_thai='completed' WHERE id=?", (schedule_id,))
    sched = dict(conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone())
    
    from utils.google_sync import auto_sync_schedule_to_google
    auto_sync_schedule_to_google(conn, schedule_id, "upsert")
    
    # Auto debt generation logic
    dvt = contract.get("don_vi_tinh", "/tháng")
    gia_tri = float(contract.get("gia_tri_thang") or 0.0)
    ma_hd = contract["ma_hd"]
    ma_kh = contract["ma_kh"]
    ky_thang = sched["ky_thang"]

    if gia_tri > 0:
        if dvt == "/lần thi công":
            completed_count = conn.execute("SELECT COUNT(id) FROM schedules WHERE ma_hd=? AND ky_thang=? AND trang_thai='completed'", (ma_hd, ky_thang)).fetchone()[0]
            new_can_thu = completed_count * gia_tri
            
            debt = conn.execute("SELECT id FROM debts WHERE ma_hd=? AND ky_thanh_toan=?", (ma_hd, ky_thang)).fetchone()
            if debt:
                conn.execute("UPDATE debts SET can_thu = ? WHERE id=?", (new_can_thu, debt["id"]))
            else:
                conn.execute("INSERT INTO debts (ma_hd, ma_kh, ky_thanh_toan, can_thu, da_thu, ghi_chu) VALUES (?, ?, ?, ?, ?, ?)",
                             (ma_hd, ma_kh, ky_thang, new_can_thu, 0.0, "Tự động sinh (theo lần)"))
        else: # /tháng
            total_required = int(contract.get("tan_suat") or 1)
            completed_count = conn.execute("SELECT COUNT(id) FROM schedules WHERE ma_hd=? AND ky_thang=? AND trang_thai='completed'", (ma_hd, ky_thang)).fetchone()[0]
            if completed_count >= total_required:
                debt = conn.execute("SELECT id FROM debts WHERE ma_hd=? AND ky_thanh_toan=?", (ma_hd, ky_thang)).fetchone()
                if not debt:
                    conn.execute("INSERT INTO debts (ma_hd, ma_kh, ky_thanh_toan, can_thu, da_thu, ghi_chu) VALUES (?, ?, ?, ?, ?, ?)",
                                 (ma_hd, ma_kh, ky_thang, gia_tri, 0.0, "Tự động sinh (đủ tháng)"))

    if contract.get("loai_khach") == "Khách lẻ":
        conn.execute("UPDATE contracts SET trang_thai='completed' WHERE ma_hd=?", (ma_hd,))

    conn.commit()
    conn.close()

    next_ids = generate_next_occurrence(contract, sched)
    return {"completed": True, "next_ids": next_ids}
