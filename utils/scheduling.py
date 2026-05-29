# utils/scheduling.py — VHS CRM v4 — Logic lập lịch linh hoạt
from datetime import timezone, date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

# ============================================================
# HELPERS
# ============================================================

THU_NAMES = {0:"Chủ nhật",1:"Thứ Hai",2:"Thứ Ba",3:"Thứ Tư",
             4:"Thứ Năm",5:"Thứ Sáu",6:"Thứ Bảy"}
# Python weekday(): 0=T2,6=CN  |  Ta dùng: 0=CN,1=T2,...,6=T7
# Mapping: lap_thu → python weekday
LAP_THU_TO_PY = {0:6, 1:0, 2:1, 3:2, 4:3, 5:4, 6:5}

def _last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]

def _clamp_to_month(d: date, year: int, month: int) -> date:
    """Nếu ngày d vượt ra ngoài tháng year-month, trả về cuối tháng."""
    last = _last_day_of_month(year, month)
    if d.month != month or d.year != year:
        return date(year, month, last)
    return d

def _all_weekday_in_month(year: int, month: int, py_weekday: int) -> list[date]:
    """Trả về tất cả các ngày có weekday=py_weekday trong tháng year-month."""
    result = []
    d = date(year, month, 1)
    while d.month == month:
        if d.weekday() == py_weekday:
            result.append(d)
        d += timedelta(days=1)
    return result

# ============================================================
# THUẬT TOÁN CHÍNH: tính danh sách ngày cho 1 kỳ tháng
# ============================================================

def calc_dates_for_month(hd: dict, ky_thang: str) -> list[date]:
    """
    Tính danh sách ngày thi công (list[date]) cho hợp đồng hd trong kỳ ky_thang.

    Hai kiểu lặp:
    ─────────────────────────────────────────────────────────
    A) kieu_lap = 'ngay_co_dinh'
       Anchor = ngày thi công đầu tiên (ngay_thi_cong_dau)
       → Dùng đúng ngày đó (ngày mấy) cho mỗi tháng
       → Khoảng cách giữa các lần = 30 / tan_suat ngày (làm tròn)
       VD: ngay_dau=05, tan_suat=2
           Tháng 05 → 05/05 và 20/05

    B) kieu_lap = 'thu_co_dinh'
       → Thi công vào thứ X (lap_thu) trong tháng
       → Phân bổ đều tan_suat lần vào các tuần có thứ X đó
       VD: tan_suat=2, thứ Hai
           Tháng 05 có 4 thứ Hai → chọn thứ Hai tuần 1 và tuần 3
       VD: tan_suat=3, thứ Tư
           Tháng 05 có 5 thứ Tư → chọn tuần 1, 2, 4 (phân bổ đều)
    ─────────────────────────────────────────────────────────
    """
    year, month = map(int, ky_thang.split("-"))
    tan_suat  = hd["tan_suat"]
    kieu_lap  = hd.get("kieu_lap", "ngay_co_dinh")
    loai_khach = hd.get("loai_khach", "Định kỳ")
    chu_ky_lap = hd.get("chu_ky_lap", "1_thang")
    ngay_dau_str = hd.get("ngay_thi_cong_dau") or hd.get("ngay_ky")
    
    try:
        ngay_dau_date = date.fromisoformat(ngay_dau_str)
        anchor_day = ngay_dau_date.day
    except:
        ngay_dau_date = date(year, month, 1)
        anchor_day = 1

    # ── XỬ LÝ KHÁCH LẺ ──
    if loai_khach == "Khách lẻ":
        dates = []
        if chu_ky_lap == "1_lan":
            if year == ngay_dau_date.year and month == ngay_dau_date.month:
                dates.append(ngay_dau_date)
        elif chu_ky_lap.endswith("_thang") or chu_ky_lap.endswith("_nam"):
            # x_thang or x_nam
            parts = chu_ky_lap.split('_')
            x = int(parts[0])
            if parts[1] == "nam": x *= 12
            
            month_diff = (year - ngay_dau_date.year) * 12 + (month - ngay_dau_date.month)
            if month_diff >= 0 and month_diff % x == 0:
                try:
                    d = date(year, month, anchor_day)
                except ValueError:
                    d = date(year, month, _last_day_of_month(year, month))
                dates.append(_clamp_to_month(d, year, month))
        elif chu_ky_lap.endswith("_tuan"):
            parts = chu_ky_lap.split('_')
            x = int(parts[0])
            
            # Start from ngay_dau_date, keep adding x * 7 days until we pass the target month
            current_date = ngay_dau_date
            while True:
                if current_date.year == year and current_date.month == month:
                    dates.append(current_date)
                elif (current_date.year > year) or (current_date.year == year and current_date.month > month):
                    break
                current_date += timedelta(days=x * 7)
        return dates

    # ── XỬ LÝ KHÁCH ĐỊNH KỲ ──

    if kieu_lap == "ngay_co_dinh":
        dates = []
        tuan_lap_lai = hd.get("tuan_lap_lai")
        
        if tuan_lap_lai:
            # New logic: explicitly selected days
            days_str = [d.strip() for d in str(tuan_lap_lai).split(',') if d.strip().isdigit()]
            for d_str in days_str[:tan_suat]: # Ensure we only generate up to tan_suat times
                day_num = int(d_str)
                try:
                    d = date(year, month, day_num)
                except ValueError:
                    d = date(year, month, _last_day_of_month(year, month))
                d = _clamp_to_month(d, year, month)
                dates.append(d)
        else:
            # Old logic (fallback)
            try:
                anchor_day = date.fromisoformat(ngay_dau_str).day
            except:
                anchor_day = 1

            interval = 30 // tan_suat
            for i in range(tan_suat):
                day_num = anchor_day + interval * i
                try:
                    d = date(year, month, day_num)
                except ValueError:
                    d = date(year, month, _last_day_of_month(year, month))
                d = _clamp_to_month(d, year, month)
                dates.append(d)
                
        # Remove duplicates but preserve order
        dates = list(dict.fromkeys(dates))
        # If set removes duplicates making len < tan_suat, we might need to add fallback days,
        # but for explicit selections the user shouldn't select duplicate days.
        return dates

    # ── MIXED: TÙY CHỈNH TỪNG LẦN ──
    elif kieu_lap == "mixed":
        dates = []
        tuan_lap_lai = hd.get("tuan_lap_lai")
        if tuan_lap_lai:
            try:
                import json
                configs = json.loads(tuan_lap_lai)
                for conf in configs[:tan_suat]:
                    if conf.get("type") == "ngay":
                        day_num = int(conf.get("val", 1))
                        try:
                            d = date(year, month, day_num)
                        except ValueError:
                            d = date(year, month, _last_day_of_month(year, month))
                        dates.append(_clamp_to_month(d, year, month))
                    elif conf.get("type") == "thu":
                        lap_thu = int(conf.get("thu", 1)) # 0=CN, 1=T2...
                        tuan = conf.get("tuan", "1") # "1", "2", "3", "4", "Cuối"
                        
                        py_wd = LAP_THU_TO_PY.get(lap_thu, 0)
                        all_days = _all_weekday_in_month(year, month, py_wd)
                        if not all_days: continue
                        
                        if str(tuan).isdigit():
                            idx = int(tuan) - 1
                            if 0 <= idx < len(all_days):
                                dates.append(all_days[idx])
                            else:
                                dates.append(all_days[-1]) # Fallback to last if week not exists
                        elif str(tuan).lower() == "cuối":
                            dates.append(all_days[-1])
            except Exception as e:
                print(f"Error parsing mixed config: {e}")
        return list(dict.fromkeys(dates))

    # ── B: THỨ CỐ ĐỊNH ──
    else:
        lap_thu  = hd.get("lap_thu") or 1   # 0=CN,1=T2,...
        py_wd    = LAP_THU_TO_PY.get(lap_thu, 0)
        all_days = _all_weekday_in_month(year, month, py_wd)  # VD: [5,12,19,26/5]

        if not all_days:
            return []

        tuan_lap_lai = hd.get("tuan_lap_lai")
        if tuan_lap_lai:
            weeks = [w.strip() for w in str(tuan_lap_lai).split(',') if w.strip()]
            chosen = []
            for w in weeks:
                if w.isdigit():
                    idx = int(w) - 1
                    if 0 <= idx < len(all_days):
                        chosen.append(all_days[idx])
                elif w.lower() == "cuối":
                    chosen.append(all_days[-1])
            
            chosen = list(dict.fromkeys(chosen))
            return chosen

        n_avail = len(all_days)    # số thứ X có trong tháng (thường 4-5)

        if tan_suat >= n_avail:
            # Cần nhiều hơn số thứ X có → lấy tất cả
            return all_days[:tan_suat]

        # Phân bổ đều: chọn tan_suat ngày từ all_days sao cho khoảng cách đều nhất
        # Dùng kỹ thuật "Bresenham-style" chia đều index
        # VD: n_avail=5, tan_suat=3 → index = 0, 2, 4 → tuần 1,3,5
        # VD: n_avail=4, tan_suat=2 → index = 0, 2   → tuần 1,3
        step   = n_avail / tan_suat
        chosen = [all_days[round(i * step)] for i in range(tan_suat)]
        # Đảm bảo không trùng
        chosen = list(dict.fromkeys(chosen))
        # Nếu vẫn thiếu (edge case rounding), thêm ngày kế tiếp
        while len(chosen) < tan_suat:
            for d in all_days:
                if d not in chosen:
                    chosen.append(d); break
        return sorted(chosen[:tan_suat])


def describe_schedule(hd: dict) -> str:
    """Tóm tắt lịch lặp dạng text để hiển thị UI."""
    loai_khach = hd.get("loai_khach", "Định kỳ")
    chu_ky_lap = hd.get("chu_ky_lap", "1_lan")
    
    if loai_khach == "Khách lẻ":
        if chu_ky_lap == "1_lan":
            ck_str = "1 lần duy nhất"
        else:
            parts = chu_ky_lap.split('_')
            if len(parts) == 2:
                unit = "tuần" if parts[1]=="tuan" else "tháng" if parts[1]=="thang" else "năm"
                ck_str = f"1 lần / {parts[0]} {unit}"
            else:
                ck_str = chu_ky_lap
        return f"{ck_str} · {hd['gio_bat_dau']}–{hd['gio_ket_thuc']}"
        
    ts   = hd["tan_suat"]
    kieu = hd.get("kieu_lap","ngay_co_dinh")
    ts_label = {1:"1 lần",2:"2 lần",3:"3 lần",4:"4 lần"}.get(ts,f"{ts} lần")

    if kieu == "ngay_co_dinh":
        try:
            day = date.fromisoformat(hd["ngay_thi_cong_dau"]).day
        except:
            day = "?"
        return f"{ts_label}/tháng · Ngày {day} mỗi tháng · {hd['gio_bat_dau']}–{hd['gio_ket_thuc']}"
    elif kieu == "mixed":
        tuan_lap_lai = hd.get("tuan_lap_lai")
        desc = []
        if tuan_lap_lai:
            try:
                import json
                configs = json.loads(tuan_lap_lai)
                for i, conf in enumerate(configs[:ts]):
                    if conf.get("type") == "ngay":
                        desc.append(f"L{i+1}: Ngày {conf.get('val')}")
                    elif conf.get("type") == "thu":
                        thu_name = THU_NAMES.get(int(conf.get("thu", 1)), "?")
                        desc.append(f"L{i+1}: {thu_name} (T{conf.get('tuan')})")
            except:
                pass
        mixed_str = ", ".join(desc) if desc else "Cấu hình tùy chỉnh"
        return f"{ts_label}/tháng · {mixed_str} · {hd['gio_bat_dau']}–{hd['gio_ket_thuc']}"
    else:
        thu = THU_NAMES.get(hd.get("lap_thu",1), "?")
        return f"{ts_label}/tháng · {thu} hàng tuần (phân bổ đều) · {hd['gio_bat_dau']}–{hd['gio_ket_thuc']}"


# ============================================================
# SINH LỊCH TỰ ĐỘNG
# ============================================================

def auto_generate_schedules(ma_hd: str, ky_thang: str, overwrite=False, future_only=False) -> int:
    """
    Sinh các ca thi công cho hợp đồng ma_hd trong kỳ ky_thang.
    Không ghi đè ca đã được điều chỉnh thủ công (nguon='manual').
    Trả về số ca tạo mới.
    """
    from utils.database import get_connection
    conn = get_connection()
    hd = conn.execute("SELECT * FROM contracts WHERE ma_hd=?", (ma_hd,)).fetchone()
    if not hd:
        conn.close(); return 0
    hd = dict(hd)

    if overwrite:
        # Delete from Google Calendar first
        to_delete = conn.execute("SELECT id, google_event_id FROM schedules WHERE ma_hd=? AND ky_thang=? AND nguon='auto'", (ma_hd, ky_thang)).fetchall()
        from utils.google_sync import auto_sync_schedule_to_google
        for r in to_delete:
            if r["google_event_id"]:
                auto_sync_schedule_to_google(conn, r["google_event_id"], "delete")
        conn.execute(
            "DELETE FROM schedules WHERE ma_hd=? AND ky_thang=? AND nguon='auto'",
            (ma_hd, ky_thang)
        )
    elif future_only:
        to_delete = conn.execute("SELECT id, google_event_id FROM schedules WHERE ma_hd=? AND ky_thang=? AND nguon='auto' AND ngay_du_kien >= date('now', 'localtime')", (ma_hd, ky_thang)).fetchall()
        from utils.google_sync import auto_sync_schedule_to_google
        for r in to_delete:
            if r["google_event_id"]:
                auto_sync_schedule_to_google(conn, r["google_event_id"], "delete")
        # Delete only schedules that are not yet executed
        conn.execute(
            "DELETE FROM schedules WHERE ma_hd=? AND ky_thang=? AND nguon='auto' AND ngay_du_kien >= date('now', 'localtime')",
            (ma_hd, ky_thang)
        )

    dates  = calc_dates_for_month(hd, ky_thang)
    created = 0

    for i, d in enumerate(dates):
        lan_thu = i + 1
        exists  = conn.execute(
            "SELECT id FROM schedules WHERE ma_hd=? AND ky_thang=? AND lan_thu=?",
            (ma_hd, ky_thang, lan_thu)
        ).fetchone()
        if exists:
            continue

        # Bỏ qua ngày thi công trước ngày bắt đầu hợp đồng
        ngay_bat_dau_hd_str = hd.get("ngay_thi_cong_dau") or hd.get("ngay_ky")
        if ngay_bat_dau_hd_str:
            try:
                ngay_bat_dau_hd = date.fromisoformat(ngay_bat_dau_hd_str)
                if d < ngay_bat_dau_hd:
                    continue
            except:
                pass
            
        # Tìm dịch hại của lần thi công tương ứng (lan_thu) ở tháng gần nhất trước đó
        prev_sch = conn.execute(
            "SELECT loai_con_trung FROM schedules WHERE ma_hd=? AND lan_thu=? AND ky_thang < ? ORDER BY ky_thang DESC LIMIT 1",
            (ma_hd, lan_thu, ky_thang)
        ).fetchone()
        pest_val = prev_sch["loai_con_trung"] if prev_sch and prev_sch["loai_con_trung"] else hd.get("loai_con_trung")

        # Lấy KTV từ lịch lần trước hoặc từ hợp đồng
        prev_ktv = conn.execute(
            "SELECT ky_thuat_vien FROM schedules WHERE ma_hd=? AND lan_thu=? AND ky_thang < ? AND ky_thuat_vien IS NOT NULL ORDER BY ky_thang DESC LIMIT 1",
            (ma_hd, lan_thu, ky_thang)
        ).fetchone()
        ktv_val = prev_ktv["ky_thuat_vien"] if prev_ktv else hd.get("ky_thuat_vien")

        rs = conn.execute("""
            INSERT INTO schedules
              (ma_hd, ma_kh, ky_thang, lan_thu, ngay_du_kien,
               gio_bat_dau, gio_ket_thuc, nguon, loai_con_trung, ky_thuat_vien)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            RETURNING id
        """, (ma_hd, hd["ma_kh"], ky_thang, lan_thu,
              d.isoformat(), hd["gio_bat_dau"], hd["gio_ket_thuc"], "auto", pest_val, ktv_val)).fetchone()
        
        if rs:
            from utils.google_sync import auto_sync_schedule_to_google
            auto_sync_schedule_to_google(conn, rs["id"], "upsert")
            
        created += 1

    conn.commit()
    conn.close()
    return created


def auto_generate_next_ky(ma_hd: str, ky_hien_tai: str):
    """Sau khi hoàn thành ca cuối kỳ này, tự sinh lịch kỳ kế tiếp nếu chưa có."""
    from utils.database import get_connection
    y, m   = map(int, ky_hien_tai.split("-"))
    next_d  = date(y, m, 1) + relativedelta(months=1)
    next_ky = next_d.strftime("%Y-%m")
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM schedules WHERE ma_hd=? AND ky_thang=?",
        (ma_hd, next_ky)
    ).fetchone()[0]
    conn.close()
    if count == 0:
        auto_generate_schedules(ma_hd, next_ky)


# ============================================================
# MIDNIGHT CROSSING
# ============================================================

def is_job_active_now(ngay_du_kien: str, gio_bat_dau: str, gio_ket_thuc: str) -> bool:
    try:
        now = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7))
        h_bd, m_bd = map(int, gio_bat_dau.split(":"))
        sch_date = date.fromisoformat(ngay_du_kien)
        start_dt = datetime(sch_date.year, sch_date.month, sch_date.day, h_bd, m_bd)
        
        diff_hours = (start_dt - now).total_seconds() / 3600
        
        # Ca trong 24h qua (để quên check-out) hoặc ca trong 12h tới (upcoming)
        if -24 <= diff_hours <= 12:
            return True
            
        # Hoặc là ca thuộc về ngày hôm nay (hiển thị trọn ngày)
        if sch_date == now.date():
            return True
            
        return False
    except:
        return False


def check_time_violation(gio_bat_dau_hd: str, gio_ket_thuc_hd: str,
                          checkin_time_str: str, ngay_du_kien: str = None) -> dict:
    try:
        ci = datetime.fromisoformat(checkin_time_str).replace(tzinfo=None)
        h_bd, m_bd = map(int, gio_bat_dau_hd.split(":"))

        # Xác định ngày dự kiến thi công
        if ngay_du_kien:
            sch_date = date.fromisoformat(ngay_du_kien)
        else:
            sch_date = ci.date()

        start_dt = datetime(sch_date.year, sch_date.month, sch_date.day, h_bd, m_bd)

        # Tính chênh lệch bằng phút (so sánh cả ngày + giờ)
        diff = int((ci - start_dt).total_seconds() / 60)

        if diff < -30:
            return {"violation":True,"type":"early",
                    "message":f"⚠️ Check-in sớm hơn {abs(diff)} phút (khung giờ: {gio_bat_dau_hd})"}
        if diff > 30:
            return {"violation":True,"type":"late",
                    "message":f"⚠️ Check-in trễ hơn {diff} phút (khung giờ: {gio_bat_dau_hd})"}
        return {"violation":False,"type":"ok","message":"✓ Đúng khung giờ"}
    except Exception as e:
        return {"violation":False,"type":"error","message":str(e)}

def auto_generate_all_future_schedules(months: int = 2) -> int:
    """
    Sinh lịch tự động cho tất cả hợp đồng định kỳ active.
    Bao gồm: tháng trước, tháng này, và 'months' tháng tiếp theo.
    Được gọi mỗi lần app load (1 lần/ngày để tránh load nặng).
    """
    from utils.database import get_connection
    conn = get_connection()
    cts = conn.execute(
        "SELECT ma_hd FROM contracts WHERE trang_thai='active' AND loai_khach != 'Khách lẻ'"
    ).fetchall()
    conn.close()
    
    if not cts:
        return 0
        
    created = 0
    today = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
    
    # Bắt đầu từ tháng hiện tại → 2 tháng tới
    start = today.replace(day=1)
    
    for i in range(months + 1):  # tháng này + months tháng tới
        ky_thang = start.strftime("%Y-%m")
        for ct in cts:
            try:
                created += auto_generate_schedules(ct["ma_hd"], ky_thang, overwrite=False)
            except:
                pass
        start = (start + timedelta(days=32)).replace(day=1)
            
    return created

# ============================================================
# CONFLICT CHECKING
# ============================================================

def check_ktv_schedule_conflict(ktv_name: str, ma_hd_exclude: str, dates_list: list, gio_bat_dau: str, gio_ket_thuc: str) -> list:
    """
    Kiểm tra xem ktv_name có bị trùng lịch vào các ngày dates_list với khung giờ gio_bat_dau - gio_ket_thuc không.
    Trả về list dict chứa thông tin các ca bị trùng.
    """
    if not ktv_name or ktv_name == "(Chưa chọn)":
        return []
        
    if not dates_list:
        return []
        
    from utils.database import get_connection
    conn = get_connection()
    
    # Lấy các lịch của KTV trong tương lai (từ ngày nhỏ nhất trong list)
    min_date = min(dates_list).strftime("%Y-%m-%d")
    max_date = max(dates_list).strftime("%Y-%m-%d")
    
    query = """
        SELECT s.ngay_du_kien, s.gio_bat_dau, s.gio_ket_thuc, s.ma_hd, c.ten_cty
        FROM schedules s
        JOIN contracts ct ON s.ma_hd = ct.ma_hd
        JOIN customers c ON ct.ma_kh = c.ma_kh
        WHERE s.ky_thuat_vien = ? 
        AND s.ngay_du_kien >= ? AND s.ngay_du_kien <= ?
        AND s.trang_thai != 'skipped'
    """
    params = [ktv_name, min_date, max_date]
    
    if ma_hd_exclude:
        query += " AND s.ma_hd != ?"
        params.append(ma_hd_exclude)
        
    existing = conn.execute(query, params).fetchall()
    conn.close()
    
    if not existing:
        return []
        
    def get_dts(date_str, time_str_start, time_str_end):
        # Trả về start_dt, end_dt
        # Nếu ca qua đêm thì end_dt + 1 ngày
        try:
            d = date.fromisoformat(date_str)
            h_s, m_s = map(int, time_str_start.split(":"))
            h_e, m_e = map(int, time_str_end.split(":"))
            dt_start = datetime(d.year, d.month, d.day, h_s, m_s)
            dt_end = datetime(d.year, d.month, d.day, h_e, m_e)
            if dt_start > dt_end: # ca qua đêm
                dt_end += timedelta(days=1)
            return dt_start, dt_end
        except:
            return None, None

    conflicts = []
    
    for d_obj in dates_list:
        d_str = d_obj.strftime("%Y-%m-%d")
        new_start, new_end = get_dts(d_str, gio_bat_dau, gio_ket_thuc)
        if not new_start: continue
        
        for ex in existing:
            # Chỉ check nếu cùng ngày hoặc lệch 1 ngày (do ca đêm)
            ex_d_str = ex["ngay_du_kien"]
            ex_start, ex_end = get_dts(ex_d_str, ex["gio_bat_dau"], ex["gio_ket_thuc"])
            if not ex_start: continue
            
            # Check overlap logic
            # (StartA < EndB) and (EndA > StartB)
            if new_start < ex_end and new_end > ex_start:
                conflicts.append({
                    "date": d_str,
                    "ma_hd": ex["ma_hd"],
                    "ten_cty": ex["ten_cty"],
                    "gio_bat_dau": ex["gio_bat_dau"],
                    "gio_ket_thuc": ex["gio_ket_thuc"]
                })
                
    return conflicts
