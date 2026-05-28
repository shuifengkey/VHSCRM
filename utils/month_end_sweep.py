import os
from datetime import datetime, timezone, timedelta
from utils.database import get_connection

def run_month_end_sweep():
    """
    Quét toàn bộ các hợp đồng theo tháng.
    Nếu KTV làm chưa đủ số lần nhưng đã đến ngày cuối tháng (hoặc bấm chốt),
    hệ thống tự động sinh công nợ tháng đó và đánh dấu ghi chú 'Thiếu ca'.
    """
    conn = get_connection()
    now_dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)
    ky_thang = now_dt.strftime("%Y-%m")
    
          AND don_vi_tinh='/tháng'
    contracts = conn.execute("""
        SELECT ma_hd, ma_kh, gia_tri_thang, tan_suat, vat_pct 
        FROM contracts 
        WHERE trang_thai='active' 
          AND don_vi_tinh='/tháng'
          AND strftime('%Y-%m', ngay_thi_cong_dau) <= ?
    """, (ky_thang,)).fetchall()
    
    count_generated = 0
    count_warnings = 0
    
    for ct in contracts:
        ma_hd = ct["ma_hd"]
        ma_kh = ct["ma_kh"]
        gia_tri = float(ct["gia_tri_thang"] or 0.0)
        vat_pct = float(ct.get("vat_pct") or 0.0)
        total_required = int(ct["tan_suat"] or 1)
        
        if gia_tri <= 0:
            continue
            
        # Kiểm tra xem công nợ tháng này đã được tạo chưa
        debt = conn.execute("SELECT id FROM debts WHERE ma_hd=? AND ky_thanh_toan=?", (ma_hd, ky_thang)).fetchone()
        
        if not debt:
            # Kiểm tra số ca đã hoàn thành trong tháng
            completed_count = conn.execute("SELECT COUNT(id) FROM schedules WHERE ma_hd=? AND ky_thang=? AND trang_thai='completed'", (ma_hd, ky_thang)).fetchone()[0]
            
            ghi_chu = "Tự động sinh (chốt sổ)"
            if completed_count < total_required:
                ghi_chu = f"⚠️ Tự động sinh (chốt sổ). Thiếu ca: Làm {completed_count}/{total_required} ca."
                count_warnings += 1
                
            tien_vat = gia_tri * (vat_pct / 100.0)
            new_can_thu = gia_tri + tien_vat
            conn.execute("INSERT INTO debts (ma_hd, ma_kh, ky_thanh_toan, can_thu, da_thu, ghi_chu, tien_vat) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (ma_hd, ma_kh, ky_thang, new_can_thu, 0.0, ghi_chu, tien_vat))
            count_generated += 1
            
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "generated": count_generated,
        "warnings": count_warnings,
        "ky_thang": ky_thang
    }

if __name__ == "__main__":
    res = run_month_end_sweep()
    print(res)
