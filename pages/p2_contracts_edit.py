import streamlit as st
from datetime import timezone, date, datetime, time, timedelta
from utils.database import get_connection
import calendar

@st.dialog("Sửa Toàn Bộ Hợp Đồng", width="large")
def edit_contract_dialog(ma_hd):
    conn = get_connection()
    hd = conn.execute("SELECT * FROM contracts WHERE ma_hd=?", (ma_hd,)).fetchone()
    if not hd:
        st.error("Không tìm thấy hợp đồng")
        conn.close()
        return
    hd = dict(hd)
    
    all_kh = conn.execute("SELECT ma_kh, ten_cty FROM customers ORDER BY ma_kh").fetchall()
    conn.close()
    
    kh_opts = {f"{r['ma_kh']} – {r['ten_cty']}": r['ma_kh'] for r in all_kh}
    curr_kh_idx = 0
    for i, (k, v) in enumerate(kh_opts.items()):
        if v == hd['ma_kh']:
            curr_kh_idx = i
            break

    def get_date(d_str):
        if not d_str: return (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
        try: return date.fromisoformat(d_str)
        except: return (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Mã Hợp Đồng", value=hd['ma_hd'], disabled=True)
        ngay_ky = st.date_input("Ngày Ký", value=get_date(hd['ngay_ky']), key=f"e_nk_{ma_hd}")
    with c2:
        kh_sel = st.selectbox("Khách Hàng", list(kh_opts.keys()), index=curr_kh_idx, key=f"e_kh_{ma_hd}")
        ngay_ht = st.date_input("Ngày Hết Hạn", value=get_date(hd['ngay_het_han']), key=f"e_nhh_{ma_hd}")
    with c3:
        loai_khach = st.selectbox("Loại Khách", ["Định kỳ", "Khách lẻ"], index=0 if hd['loai_khach']=="Định kỳ" else 1, key=f"e_lk_{ma_hd}")
        
        c_gia, c_dvt = st.columns(2)
        with c_gia:
            val_str = f"{int(hd['gia_tri_thang']):,.0f}".replace(",", ".") if hd['gia_tri_thang'] else "0"
            gia_tri_str = st.text_input("Giá Trị (VNĐ)", value=val_str, key=f"e_gt_{ma_hd}")
        with c_dvt:
            idx_dvt = 0 if hd['don_vi_tinh'] == "/tháng" else 1
            don_vi_tinh = st.selectbox("Đơn Vị", ["/tháng", "/lần thi công"], index=idx_dvt, key=f"e_dvt_{ma_hd}")

    # Thông tin thi công
    c4, c5, c6 = st.columns(3)
    with c4:
        khu_vuc_xu_ly = st.text_input("Khu Vực", value=hd.get('khu_vuc_xu_ly') or "", key=f"e_kv_{ma_hd}")
    with c5:
        loai_con_trung = st.text_input("Dịch Hại", value=hd.get('loai_con_trung') or "", key=f"e_ct_{ma_hd}")
    with c6:
        phuong_phap_xu_ly = st.text_input("Phương Pháp", value=hd.get('phuong_phap_xu_ly') or "", key=f"e_pp_{ma_hd}")

    st.markdown("---")
    
    # ── TẦN SUẤT & KHUNG GIỜ
    kieu_lap_val = hd.get("kieu_lap") or "ngay_co_dinh"
    tan_suat = hd.get("tan_suat") or 1
    lap_thu_val = hd.get("lap_thu")
    chu_ky_lap = hd.get("chu_ky_lap") or "1_lan"
    tuan_lap_lai_val = hd.get("tuan_lap_lai") or ""
    ngay_thi_cong_dau = get_date(hd.get("ngay_thi_cong_dau"))

    def _parse_time(t_str, is_end=False):
        if not t_str: return time(6,30) if is_end else time(6,0)
        try: return datetime.strptime(t_str, "%H:%M").time()
        except: return time(6,30) if is_end else time(6,0)
    
    gbd_val = _parse_time(hd.get("gio_bat_dau"))
    gkt_val = _parse_time(hd.get("gio_ket_thuc"), is_end=True)

    if loai_khach == "Định kỳ":
        tan_suat_opts = {1:"1 lần/tháng", 2:"2 lần/tháng", 3:"3 lần/tháng", 4:"4 lần/tháng", 5:"Khác (nhập tay)"}
        curr_ts_idx = min(tan_suat - 1, 4) if tan_suat else 0
        c_ts1, c_ts2 = st.columns(2)
        with c_ts1:
            tan_suat_sel = st.selectbox("Tần Suất", list(tan_suat_opts.values()), index=curr_ts_idx, key=f"e_ts_{ma_hd}")
            if tan_suat_sel == "Khác (nhập tay)":
                tan_suat = st.number_input("Số lần / tháng", min_value=1, value=tan_suat, key=f"e_tsn_{ma_hd}")
            else:
                tan_suat = list(tan_suat_opts.keys())[list(tan_suat_opts.values()).index(tan_suat_sel)]
        with c_ts2:
            st.markdown(" ") # Spacer
            st.markdown("⚙️ **Cấu hình chi tiết**")

        configs_loaded = []
        import json
        if kieu_lap_val == "mixed" and tuan_lap_lai_val:
            try: configs_loaded = json.loads(tuan_lap_lai_val)
            except: pass
        elif kieu_lap_val == "ngay_co_dinh" and tuan_lap_lai_val:
            saved_days = [d.strip() for d in str(tuan_lap_lai_val).split(',') if d.strip().isdigit()]
            for d in saved_days: configs_loaded.append({"type": "ngay", "val": int(d)})
        elif kieu_lap_val == "thu_co_dinh":
            weeks = [w.strip() for w in str(tuan_lap_lai_val).split(',') if w.strip()]
            for w in weeks: configs_loaded.append({"type": "thu", "thu": lap_thu_val or 1, "tuan": w})

        configs_new = []
        for i in range(tan_suat):
            conf = configs_loaded[i] if i < len(configs_loaded) else {"type": "ngay", "val": min(1 + (30//tan_suat)*i, 31)}
            
            st.markdown(f"**Lần {i+1}**")
            c_loai, c_val1, c_val2 = st.columns([1,1,1])
            with c_loai:
                type_idx = 0 if conf.get("type") == "ngay" else 1
                type_sel = st.selectbox("Loại", ["Ngày cố định", "Thứ cố định"], index=type_idx, key=f"e_type_{ma_hd}_{i}", label_visibility="hidden")
            
            if type_sel == "Ngày cố định":
                with c_val1:
                    day_num = st.selectbox("Ngày", list(range(1, 32)), index=min(int(conf.get("val", 1))-1, 30), key=f"e_day_{ma_hd}_{i}")
                configs_new.append({"type": "ngay", "val": day_num})
            else:
                thu_options = {"Chủ Nhật": 0, "Thứ Hai": 1, "Thứ Ba": 2, "Thứ Tư": 3, "Thứ Năm": 4, "Thứ Sáu": 5, "Thứ Bảy": 6}
                curr_thu = 1
                for k, v in thu_options.items():
                    if v == conf.get("thu", 1): curr_thu = list(thu_options.values()).index(v)
                
                with c_val1:
                    thu_sel = st.selectbox("Thứ", list(thu_options.keys()), index=curr_thu, key=f"e_thu_{ma_hd}_{i}")
                with c_val2:
                    tuan_opts = ["1", "2", "3", "4", "Cuối"]
                    curr_tuan = 0
                    if str(conf.get("tuan")) in tuan_opts: curr_tuan = tuan_opts.index(str(conf.get("tuan")))
                    tuan_sel = st.selectbox("Tuần", tuan_opts, index=curr_tuan, key=f"e_tuan_{ma_hd}_{i}")
                configs_new.append({"type": "thu", "thu": thu_options[thu_sel], "tuan": tuan_sel})
                
        tuan_lap_lai_val = json.dumps(configs_new)
        kieu_lap_val = "mixed"
        lap_thu_val = None
        
        ngay_thi_cong_dau = st.date_input("Kỳ Thi Công Bắt Đầu Lặp", value=ngay_thi_cong_dau, key=f"e_ntcd_{ma_hd}")

        c_bd, c_kt = st.columns(2)
        with c_bd: gbd = st.time_input("Giờ Bắt Đầu", value=gbd_val, key=f"e_gbd_{ma_hd}")
        with c_kt: gkt = st.time_input("Giờ Kết Thúc", value=gkt_val, key=f"e_gkt_{ma_hd}")
        
    else:
        # KHÁCH LẺ
        c_ngay, c_gio = st.columns(2)
        with c_ngay:
            ngay_thi_cong_dau = st.date_input("Ngày Thi Công Đầu Tiên", value=ngay_thi_cong_dau, key=f"e_ntcd3_{ma_hd}")
        with c_gio:
            c_bd, c_kt = st.columns(2)
            with c_bd: gbd = st.time_input("Bắt Đầu", value=gbd_val, key=f"e_gbd2_{ma_hd}")
            with c_kt: gkt = st.time_input("Kết Thúc", value=gkt_val, key=f"e_gkt2_{ma_hd}")
            
        c_loai, c_so = st.columns(2)
        loai_opts = ["Chỉ 1 lần duy nhất", "Tuần", "Tháng", "Năm"]
        loai_idx = 0
        if "_" in chu_ky_lap:
            if "tuan" in chu_ky_lap: loai_idx = 1
            elif "thang" in chu_ky_lap: loai_idx = 2
            elif "nam" in chu_ky_lap: loai_idx = 3
        with c_loai:
            loai_ck = st.selectbox("Lặp theo", loai_opts, index=loai_idx, key=f"e_lck_{ma_hd}")
        
        if loai_ck == "Chỉ 1 lần duy nhất":
            chu_ky_lap = "1_lan"
        else:
            with c_so:
                so_val = 1
                try: so_val = int(chu_ky_lap.split("_")[0])
                except: pass
                so_ck = st.number_input(f"Số {loai_ck.lower()} / lần", min_value=1, value=so_val, step=1, key=f"e_sck_{ma_hd}")
            don_vi = "tuan" if loai_ck == "Tuần" else "thang" if loai_ck == "Tháng" else "nam"
            chu_ky_lap = f"{so_ck}_{don_vi}"

        kieu_lap_val = "ngay_co_dinh"
        tan_suat = 1
        lap_thu_val = None
        tuan_lap_lai_val = ""

    ghi_chu = st.text_area("Ghi Chú", value=hd.get("ghi_chu") or "", height=60, key=f"e_gc_{ma_hd}")



    if st.button("💾 Lưu Thay Đổi Hợp Đồng", type="primary", use_container_width=True, key=f"btn_save_{ma_hd}"):
        try:
            gia_tri = int(gia_tri_str.replace(".", "").replace(",", "").strip())
            
            c = get_connection()
            c.execute("""
                UPDATE contracts SET 
                    ma_kh=?, ngay_ky=?, ngay_het_han=?, loai_khach=?,
                    gia_tri_thang=?, don_vi_tinh=?, khu_vuc_xu_ly=?, loai_con_trung=?, phuong_phap_xu_ly=?,
                    tan_suat=?, kieu_lap=?, lap_thu=?, chu_ky_lap=?, tuan_lap_lai=?,
                    ngay_thi_cong_dau=?, gio_bat_dau=?, gio_ket_thuc=?, ghi_chu=?, vat_pct=?
                WHERE ma_hd=?
            """, (kh_opts[kh_sel], ngay_ky.isoformat(), ngay_ht.isoformat(), loai_khach,
                  gia_tri, don_vi_tinh, khu_vuc_xu_ly, loai_con_trung, phuong_phap_xu_ly,
                  tan_suat, kieu_lap_val, lap_thu_val, chu_ky_lap, tuan_lap_lai_val,
                  ngay_thi_cong_dau.isoformat(), gbd.strftime("%H:%M"), gkt.strftime("%H:%M"), ghi_chu, vat_pct,
                  ma_hd))
            c.commit()
            
            # Xóa các ca chưa làm (không nằm trong logbook) để sinh lại theo cấu hình mới
            to_delete = c.execute("""
                SELECT google_event_id FROM schedules 
                WHERE ma_hd=? AND trang_thai='scheduled' 
                  AND id NOT IN (SELECT schedule_id FROM logbook)
            """, (ma_hd,)).fetchall()
            from utils.google_sync import auto_sync_schedule_to_google
            for row in to_delete:
                if row["google_event_id"]:
                    auto_sync_schedule_to_google(c, row["google_event_id"], "delete")
                    
            c.execute("""
                DELETE FROM schedules 
                WHERE ma_hd=? AND trang_thai='scheduled' 
                  AND id NOT IN (SELECT schedule_id FROM logbook)
            """, (ma_hd,))
            c.commit()
            c.close()
            
            # Sinh lại lịch mới cho tháng bắt đầu + 2 tháng tới
            from utils.scheduling import auto_generate_schedules
            start = ngay_thi_cong_dau.replace(day=1)
            n = 0
            for _ in range(3):
                n += auto_generate_schedules(ma_hd, start.strftime("%Y-%m"))
                start = (start + timedelta(days=32)).replace(day=1)
                
            st.session_state.add_hd_success = f"✅ Đã cập nhật hợp đồng {ma_hd} và sinh lại {n} ca thi công mới!"
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")
