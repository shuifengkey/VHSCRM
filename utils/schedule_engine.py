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
    Đánh dấu 1 ca là completed và tự sinh ca kế tiếp.
    """
    conn = _get_conn()
    conn.execute("UPDATE schedules SET trang_thai='completed' WHERE id=?", (schedule_id,))
    sched = dict(conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone())
    conn.commit()
    conn.close()

    next_ids = generate_next_occurrence(contract, sched)
    return {"completed": True, "next_ids": next_ids}
