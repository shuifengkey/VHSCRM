from zoneinfo import ZoneInfo
import streamlit as st
from datetime import date, datetime, time, timedelta
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
        if not d_str: return datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
        try: return date.fromisoformat(d_str)
        except: return datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()

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
            kieu_opts = ["Ngày cố định", "Thứ cố định"]
            k_idx = 0 if kieu_lap_val == "ngay_co_dinh" else 1
            kieu_lap = st.selectbox("Kiểu Lặp", kieu_opts, index=k_idx, key=f"e_kl_{ma_hd}")
            kieu_lap_val = "ngay_co_dinh" if kieu_lap == "Ngày cố định" else "thu_co_dinh"

        if kieu_lap_val == "ngay_co_dinh":
            cols = st.columns(min(tan_suat, 4))
            selected_days = []
            
            # Khôi phục các ngày đã lưu nếu có
            saved_days = [d.strip() for d in str(tuan_lap_lai_val).split(',') if d.strip().isdigit()]
            interval = 30 // tan_suat
            
            for i in range(tan_suat):
                col_idx = i % 4
                with cols[col_idx]:
                    if i < len(saved_days):
                        default_day = int(saved_days[i])
                    else:
                        default_day = min(1 + interval * i, 31)
                    idx_ngay = min(default_day - 1, 30)
                    d = st.selectbox(f"Ngày lần {i+1}", list(range(1, 32)), index=idx_ngay, key=f"e_ntt_{ma_hd}_{i}")
                    selected_days.append(str(d))
            
            tuan_lap_lai_val = ",".join(selected_days)
            
            # Tính ngày bắt đầu lặp dựa trên lần thi công thứ 1
            first_day = int(selected_days[0])
            year = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().year
            month = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().month
            max_d = calendar.monthrange(year, month)[1]
            d = min(first_day, max_d)
            suggested_date = date(year, month, d)
            if suggested_date < datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date():
                m = 1 if month == 12 else month + 1
                y = year + 1 if month == 12 else year
                max_d_next = calendar.monthrange(y, m)[1]
                d_next = min(first_day, max_d_next)
                suggested_date = date(y, m, d_next)
            
            # Gợi ý nhưng có thể cho phép sửa tay nếu muốn (khách lẻ)
            ngay_thi_cong_dau = st.date_input("Ngày Bắt Đầu Lặp", value=suggested_date, key=f"e_ntcd_{ma_hd}")
            lap_thu_val = None
        else:
            thu_opts = {"Chủ Nhật":0, "Thứ Hai":1, "Thứ Ba":2, "Thứ Tư":3, "Thứ Năm":4, "Thứ Sáu":5, "Thứ Bảy":6}
            curr_thu = "Chủ Nhật"
            for k, v in thu_opts.items():
                if v == lap_thu_val: curr_thu = k
            
            c_thu, c_tuan, c_date = st.columns([1,1,2])
            with c_thu:
                thu_sel = st.selectbox("Thi Công Thứ", list(thu_opts.keys()), index=list(thu_opts.keys()).index(curr_thu), key=f"e_thu_{ma_hd}")
                lap_thu_val = thu_opts[thu_sel]
            with c_tuan:
                def_tuan = tuan_lap_lai_val.split(",") if tuan_lap_lai_val else ["1"]
                tuan_sel = st.multiselect("Các Tuần", ["1", "2", "3", "4", "Cuối"], default=def_tuan, max_selections=tan_suat, key=f"e_tuan_{ma_hd}")
                tuan_lap_lai_val = ",".join(tuan_sel)
                if len(tuan_sel) < tan_suat:
                    st.warning(f"Vui lòng chọn đủ {tan_suat} tuần!")
            with c_date:
                ngay_thi_cong_dau = st.date_input("Ngày Đầu Tiên", value=ngay_thi_cong_dau, key=f"e_ntcd2_{ma_hd}")

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

    st.markdown("""
        <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:8px 12px;margin:10px 0;font-size:12px;color:#c2410c;">
            ⚠️ <b>Lưu ý:</b> Sửa cấu hình lặp sẽ <b>không</b> tự động xóa hay sinh lại các ca thi công đã có. Bạn cần tự xóa và bấm Sinh lịch lại nếu muốn áp dụng cấu hình mới cho toàn bộ lịch.
        </div>
    """, unsafe_allow_html=True)

    if st.button("💾 Lưu Thay Đổi Hợp Đồng", type="primary", use_container_width=True, key=f"btn_save_{ma_hd}"):
        try:
            gia_tri = int(gia_tri_str.replace(".", "").replace(",", "").strip())
            
            c = get_connection()
            c.execute("""
                UPDATE contracts SET 
                    ma_kh=?, ngay_ky=?, ngay_het_han=?, loai_khach=?,
                    gia_tri_thang=?, don_vi_tinh=?, khu_vuc_xu_ly=?, loai_con_trung=?, phuong_phap_xu_ly=?,
                    tan_suat=?, kieu_lap=?, lap_thu=?, chu_ky_lap=?, tuan_lap_lai=?,
                    ngay_thi_cong_dau=?, gio_bat_dau=?, gio_ket_thuc=?, ghi_chu=?
                WHERE ma_hd=?
            """, (kh_opts[kh_sel], ngay_ky.isoformat(), ngay_ht.isoformat(), loai_khach,
                  gia_tri, don_vi_tinh, khu_vuc_xu_ly, loai_con_trung, phuong_phap_xu_ly,
                  tan_suat, kieu_lap_val, lap_thu_val, chu_ky_lap, tuan_lap_lai_val,
                  ngay_thi_cong_dau.isoformat(), gbd.strftime("%H:%M"), gkt.strftime("%H:%M"), ghi_chu,
                  ma_hd))
            c.commit()
            c.close()
            st.session_state.add_hd_success = f"✅ Đã cập nhật hợp đồng {ma_hd} thành công!"
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")
