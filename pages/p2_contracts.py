# pages/p2_contracts.py — Hợp Đồng v4
import streamlit as st
import sys, os

from utils.database import get_connection
from utils.styles import badge, section_header, COLORS
from utils.scheduling import (auto_generate_schedules, calc_dates_for_month,
                               describe_schedule, THU_NAMES)
from datetime import timezone, date, datetime, timedelta, time
import calendar
from pages.p2_contracts_edit import edit_contract_dialog

TAN_SUAT_OPTS = {1:"1 lần/tháng", 2:"2 lần/tháng",
                 3:"3 lần/tháng", 4:"4 lần/tháng",
                 5:"5 lần/tháng", 6:"6 lần/tháng"}

KHU_VUC_OPTIONS = [
    "Nhà hàng", "Văn phòng", "Cửa hàng",
    "Sân vườn", "Bếp", "Tòa nhà", "Căn hộ/nhà ở"
]
DICH_HAI_OPTIONS = [
    "Ruồi", "Muỗi", "Chuột",
    "Ong", "Nhện", "Kiến",
    "Mối", "Mọt", "Gián"
]
PHUONG_PHAP_OPTIONS = [
    "Phun sương", "Đặt bẫy",
    "Phun tồn lưu", "Phun khói",
    "Khử trùng", "Bả"
]

def _time_input_row(label_bd, label_kt, key_bd, key_kt,
                    default_bd="06:00", default_kt="06:30"):
    """
    Hiển thị 2 ô giờ dạng time_input.
    Trả về (gio_bat_dau_str, gio_ket_thuc_str, is_valid).
    """
    c1, c2 = st.columns(2)
    h_bd, m_bd = map(int, default_bd.split(":"))
    h_kt, m_kt = map(int, default_kt.split(":"))
    
    with c1:
        gbd = st.time_input(label_bd, value=time(h_bd, m_bd), key=key_bd)
    with c2:
        gkt = st.time_input(label_kt, value=time(h_kt, m_kt), key=key_kt)
    
    gbd_str = gbd.strftime("%H:%M")
    gkt_str = gkt.strftime("%H:%M")
    
    # Night-shift notice
    if gkt < gbd:
        st.caption("🌙 Ca đêm — kết thúc sang ngày hôm sau. Hệ thống tự xử lý.")
        
    return gbd_str, gkt_str, True



def _preview_schedule(hd_dict: dict, ky_thang: str):
    """Hiển thị preview các ngày thi công cho kỳ cho trước."""
    dates = calc_dates_for_month(hd_dict, ky_thang)
    thu_map = {0:"T2", 1:"T3", 2:"T4", 3:"T5", 4:"T6", 5:"T7", 6:"CN"}
    pills = "".join(
        f'<div style="background:#dbeafe;color:#1e40af;border-radius:10px;'
        f'padding:8px 12px;font-size:12px;font-weight:700;text-align:center;min-width:90px;">'
        f'Lần {i+1}<br>'
        f'<span style="font-size:14px;">{d.strftime("%d/%m")}</span><br>'
        f'<span style="font-weight:400;font-size:10px;">{thu_map[d.weekday()]}</span>'
        f'</div>'
        for i, d in enumerate(dates)
    )
    return f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">{pills}</div>'


def render():
    import plotly.graph_objects as go
    st.markdown(section_header("Hợp Đồng",
        "Tạo hợp đồng · Setup lịch thi công · Tự sinh lịch kỳ", "📄"),
        unsafe_allow_html=True)

    tab_list, tab_add, tab_chart = st.tabs(
        ["📋  Danh Sách", "➕  Tạo Hợp Đồng Mới", "📊  Phân Tích"]
    )

    # =========================================================
    # DANH SÁCH
    # =========================================================
    with tab_list:
        today     = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
        today_str = today.strftime("%Y-%m-%d")

        conn = get_connection()
        c1, c2, c3 = st.columns([3,1,1])
        with c1: search   = st.text_input("🔍 Tìm kiếm", placeholder="Mã HĐ / Tên KH...")
        with c2: f_status = st.selectbox("Trạng thái",["Tất cả","🟢 Hiệu lực","🟡 Sắp hết hạn","🔴 Hết hạn"])
        with c3: f_ts     = st.selectbox("Tần suất",["Tất cả"]+list(TAN_SUAT_OPTS.values()))

        raw_rows = conn.execute("""
            SELECT ct.*, k.ten_cty, k.sdt, k.dai_dien,
              CAST(julianday(ct.ngay_het_han)-julianday('now') AS INT) as days_left,
              (SELECT COUNT(*) FROM schedules s WHERE s.ma_hd=ct.ma_hd AND s.trang_thai='completed') as so_xong,
              (SELECT COUNT(*) FROM schedules s WHERE s.ma_hd=ct.ma_hd) as tong_ca
            FROM contracts ct JOIN customers k ON ct.ma_kh=k.ma_kh
            ORDER BY ct.ngay_het_han
        """).fetchall()
        conn.close()
        
        import html
        rows = []
        for r in raw_rows:
            d = dict(r)
            d["ten_cty"] = html.escape(d.get("ten_cty", "") or "")
            d["dai_dien"] = html.escape(d.get("dai_dien", "") or "")
            d["sdt"] = html.escape(d.get("sdt", "") or "")
            rows.append(d)

        def match(r):
            d = r["days_left"] if r["days_left"] is not None else 999
            if search and not any(search.lower() in str(r[f]).lower()
                                  for f in ["ma_hd","ma_kh","ten_cty"]): return False
            if f_status == "🟢 Hiệu lực"    and d <= 30: return False
            if f_status == "🟡 Sắp hết hạn" and not (0 < d <= 30): return False
            if f_status == "🔴 Hết hạn"     and d > 0:  return False
            if f_ts != "Tất cả" and TAN_SUAT_OPTS.get(r["tan_suat"]) != f_ts: return False
            return True

        filtered = [r for r in rows if match(r)]
        def get_d(r): return r["days_left"] if r["days_left"] is not None else 999
        exp  = sum(1 for r in rows if get_d(r) <= 0)
        warn = sum(1 for r in rows if 0 < get_d(r) <= 30)
        ok   = len(rows) - exp - warn

        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
          <div style="background:#dcfce7;border:1px solid #bbf7d0;border-radius:10px;padding:8px 16px;">
            <span style="font-size:13px;color:#166534;font-weight:700;"><i class=\"ph-circle-fill\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {ok} Hiệu lực</span></div>
          <div style="background:#fef9c3;border:1px solid #fde68a;border-radius:10px;padding:8px 16px;">
            <span style="font-size:13px;color:#854d0e;font-weight:700;"><i class=\"ph-circle-fill\" style=\"font-size:15px;color:#d97706;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {warn} Sắp hết (≤30n)</span></div>
          <div style="background:#fee2e2;border:1px solid #fecaca;border-radius:10px;padding:8px 16px;">
            <span style="font-size:13px;color:#991b1b;font-weight:700;"><i class=\"ph-circle-fill\" style=\"font-size:15px;color:#dc2626;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {exp} Hết hạn</span></div>
        </div>
        """, unsafe_allow_html=True)

        if not filtered:
            st.info("Không tìm thấy kết quả.")

        for r in filtered:
            d = r["days_left"] if r["days_left"] is not None else 999
            sc = "#dc2626" if d<=0 else "#d97706" if d<=30 else "#16a34a"
            sb = "#fff5f5" if d<=0 else "#fffbeb" if d<=30 else "#f0fdf4"
            st_txt = "HẾT HẠN" if d<=0 else f"Còn {d} ngày"

            is_night = False
            try: is_night = int(r["gio_ket_thuc"].split(":")[0]) < int(r["gio_bat_dau"].split(":")[0])
            except: pass

            # Tóm tắt lịch lặp
            sched_desc = describe_schedule(dict(r))

            try:
                total_d  = (date.fromisoformat(r["ngay_het_han"]) - date.fromisoformat(r["ngay_ky"])).days
                elapsed  = (today - date.fromisoformat(r["ngay_ky"])).days
                pct_life = max(0, min(100, int(elapsed/total_d*100))) if total_d else 100
            except: pct_life = 0

            freq_str = TAN_SUAT_OPTS.get(r['tan_suat'], '?') if r.get('loai_khach') == 'Định kỳ' else r.get('chu_ky_lap', '1_lan').replace('_lan', ' lần').replace('_thang', ' tháng').replace('_tuan', ' tuần').replace('_nam', ' năm')
            with st.expander(
                f"**{r['ma_hd']}** — {r['ten_cty']}  "
                f"| {r.get('loai_khach', 'Định kỳ')} ({freq_str})  "
                f"{'🌙 ' if is_night else ''}| {st_txt}"
            ):
                c_info, c_action = st.columns([5, 1], vertical_alignment="center")
                with c_info:
                    st.markdown(f"""
                    <div class="vhs-list-item" style="border-left:5px solid {sc}; padding:16px;">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;">
                        <div>
                          <div style="font-size:16px;font-weight:700;color:#0f172a;">{r['ten_cty']}</div>
                          <div style="font-size:12px;color:#64748b;margin-top:3px;">
                            <i class=\"ph-user\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {r['dai_dien'] or '—'} · <i class=\"ph-phone\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {r['sdt'] or '—'}
                          </div>
                          <div style="font-size:12px;color:#2563eb;margin-top:6px;font-weight:600;">
                            <i class=\"ph-calendar-check\" style=\"font-size:15px;color:#16a34a;vertical-align:middle;line-height:1;margin-right:3px;\"></i> {sched_desc}
                          </div>
                        </div>
                        <div style="text-align:right;">
                          <div style="font-size:24px;font-weight:800;color:{sc};">{f"{int(r['gia_tri_thang']):,.0f}".replace(",", ".")} đ</div>
                          <div style="font-size:11px;color:#94a3b8;">{r.get('don_vi_tinh', '/tháng')}</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c_action:
                    if st.button("✏️ Sửa", key=f"btn_edit_dialog_{r['ma_hd']}"):
                        edit_contract_dialog(r['ma_hd'])

                # 4 stat boxes
                col1,col2,col3,col4 = st.columns(4)
                for col,(lbl,val,vc) in zip(
                    [col1,col2,col3,col4],
                    [("Ngày Ký",r["ngay_ky"],"#0f172a"),
                     ("Hết Hạn",r["ngay_het_han"] or "—", sc),
                     ("TC Đầu Tiên",r["ngay_thi_cong_dau"] or "—","#2563eb"),
                     ("Ca Hoàn Thành",f"{r['so_xong']}/{r['tong_ca']}","#16a34a")]
                ):
                    with col:
                        st.markdown(f"""
                        <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;
                                    padding:11px;text-align:center;">
                          <div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;">{lbl}</div>
                          <div style="font-size:14px;font-weight:700;color:{vc};margin-top:3px;">{val}</div>
                        </div>""", unsafe_allow_html=True)

                # Progress bar
                st.markdown(f"""
                <div class="vhs-sub-card" style="background:white;">
                  <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:5px;">
                    <span>Vòng đời hợp đồng</span>
                    <span><b style="color:#0f172a;">{pct_life}%</b> đã trôi qua</span>
                  </div>
                  <div style="background:#f1f5f9;border-radius:99px;height:7px;">
                    <div style="background:{'#dc2626' if pct_life>=90 else '#d97706' if pct_life>=70 else '#16a34a'};
                                height:7px;border-radius:99px;width:{pct_life}%;"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Preview lịch tháng này
                ky_hien_tai = today.strftime("%Y-%m")
                prev_html   = _preview_schedule(dict(r), ky_hien_tai)
                st.markdown(f"""
                <div class="vhs-sub-card">
                  <div style="font-size:12px;font-weight:700;color:#0f172a;margin-bottom:8px;">
                    <i class=\"ph-calendar\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Dự kiến lịch tháng {ky_hien_tai}
                  </div>
                  {prev_html}
                </div>
                """, unsafe_allow_html=True)

                # Sinh lịch & Action
                st.markdown("---")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🤖 Sinh lịch (2 tháng gần nhất)", key=f"gen_{r['ma_hd']}", type="primary"):
                        ky_next = (today.replace(day=1)+timedelta(days=32)).strftime("%Y-%m")
                        n1 = auto_generate_schedules(r["ma_hd"], ky_hien_tai)
                        n2 = 0
                        if r["loai_khach"] == "Định kỳ" or r["chu_ky_lap"] != "1_lan":
                            n2 = auto_generate_schedules(r["ma_hd"], ky_next)
                        n = n1 + n2
                        st.success(f"✓ Đã sinh {n} ca mới." if n else "Lịch đã đủ hoặc không có lịch sinh thêm.")
                        st.rerun()
                with col_b:
                    if st.button("🗑️ Xóa Hợp Đồng", key=f"del_{r['ma_hd']}"):
                        st.session_state[f"confirm_del_{r['ma_hd']}"] = True

                if st.session_state.get(f"confirm_del_{r['ma_hd']}"):
                    st.warning(f"! Bạn có chắc chắn muốn xóa hợp đồng **{r['ma_hd']}** và **toàn bộ lịch thi công** không?")
                    c_yes, c_no = st.columns([1, 4])
                    with c_yes:
                        if st.button("✓ Xác nhận xóa", key=f"yes_{r['ma_hd']}"):
                            if st.session_state.get('auth_role') != 'admin':
                                st.error("× Chỉ Admin mới có quyền xóa dữ liệu!")
                            else:
                                conn = get_connection()
                                conn.execute("DELETE FROM logbook WHERE schedule_id IN (SELECT id FROM schedules WHERE ma_hd=?)", (r['ma_hd'],))
                                
                                to_delete = conn.execute("SELECT google_event_id FROM schedules WHERE ma_hd=?", (r['ma_hd'],)).fetchall()
                                from utils.google_sync import auto_sync_schedule_to_google
                                for row in to_delete:
                                    if row["google_event_id"]:
                                        auto_sync_schedule_to_google(conn, row["google_event_id"], "delete")
                                        
                                conn.execute("DELETE FROM schedules WHERE ma_hd=?", (r['ma_hd'],))
                                conn.execute("DELETE FROM contracts WHERE ma_hd=?", (r['ma_hd'],))
                                conn.commit(); conn.close()
                                st.session_state[f"confirm_del_{r['ma_hd']}"] = False
                                st.success("Đã xóa thành công!"); st.rerun()
                    with c_no:
                        if st.button("× Hủy", key=f"no_{r['ma_hd']}"):
                            st.session_state[f"confirm_del_{r['ma_hd']}"] = False
                            st.rerun()

    # =========================================================
    # TẠO MỚI
    # =========================================================
    with tab_add:
        col_form = st.container()

        with col_form:
            conn = get_connection()
            all_kh = conn.execute(
                "SELECT ma_kh, ten_cty FROM customers ORDER BY ma_kh"
            ).fetchall()
            conn.close()

            if not all_kh:
                st.warning("! Chưa có khách hàng. Bạn cần thêm Khách Hàng trước!")
            else:
                st.markdown('<div class="vhs-card">', unsafe_allow_html=True)
                st.markdown("**📋 Thông Tin Hợp Đồng**")
                st.markdown('<hr style="margin:8px 0 16px">', unsafe_allow_html=True)

                if st.session_state.get("add_hd_success"):
                    st.toast(st.session_state.add_hd_success, icon="✅")
                    st.balloons()
                    st.session_state.add_hd_success = None

                with st.container():
                    # ── Thông tin cơ bản ──
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        ma_hd   = st.text_input("Mã Hợp Đồng *", placeholder="VD: HD2025-006")
                        ngay_ky = st.date_input("Ngày Ký *", value=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date())
                    with c2:
                        kh_opts = {f"{r['ma_kh']} – {r['ten_cty']}": r['ma_kh'] for r in all_kh}
                        kh_sel  = st.selectbox("Khách Hàng *", list(kh_opts.keys()))
                        ngay_ht = st.date_input("Ngày Hết Hạn", value=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().replace(year=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().year+1))
                    with c3:
                        loai_khach = st.selectbox("Loại Khách", ["Định kỳ", "Khách lẻ"])
                        if 'fmt_gia_tri' not in st.session_state:
                            st.session_state.fmt_gia_tri = ""
                        def format_currency():
                            val = st.session_state.raw_gia_tri
                            if not val.strip():
                                st.session_state.fmt_gia_tri = ""
                                return
                            try:
                                num = int(val.replace(".", "").replace(",", "").strip())
                                st.session_state.fmt_gia_tri = f"{num:,}".replace(",", ".")
                            except: pass

                        c_gia, c_dvt, c_vat = st.columns([2, 1, 1])
                        with c_gia:
                            gia_tri_str = st.text_input("Giá Trị (VNĐ) *", key="raw_gia_tri", value=st.session_state.fmt_gia_tri, placeholder="3.500.000", on_change=format_currency)
                        with c_dvt:
                            don_vi_tinh = st.selectbox("Đơn Vị", ["/tháng", "/lần"])
                        with c_vat:
                            vat_pct = st.selectbox("VAT (%)", [0, 8, 10], index=0)
    
                    st.markdown("**🏠 Khu vực xử lý**")
                    khu_vuc_sel = st.multiselect(
                        "Chọn khu vực", KHU_VUC_OPTIONS,
                        help="Chọn một hoặc nhiều khu vực cần xử lý"
                    )
                    khu_vuc_xu_ly = ", ".join(khu_vuc_sel)
    
                    st.markdown("**🕷️ Dịch hại kiểm soát**")
                    dich_hai_sel = st.multiselect(
                        "Chọn loại dịch hại", DICH_HAI_OPTIONS,
                        help="Chọn một hoặc nhiều loại côn trùng / dịch hại"
                    )
                    loai_con_trung = ", ".join(dich_hai_sel)
    
                    st.markdown("**💊 Phương pháp xử lý**")
                    pp_sel = st.multiselect(
                        "Chọn phương pháp", PHUONG_PHAP_OPTIONS,
                        help="Chọn một hoặc nhiều phương pháp xử lý"
                    )
                    pp_khac = st.text_input("Phương pháp khác (nếu có)", placeholder="VD: Xông hơi...")
                    phuong_phap_list = pp_sel + ([pp_khac] if pp_khac.strip() else [])
                    phuong_phap_xu_ly = ", ".join(phuong_phap_list)
    
                    st.markdown('<hr style="margin:12px 0">', unsafe_allow_html=True)
                    st.markdown("**🗓️ Cấu Hình Lịch Thi Công**")
                    
                    chu_ky_lap = "1_thang"
                    tan_suat = 1
                    tuan_lap_lai_val = ""
                    
                    if loai_khach == "Định kỳ":
                        c_ts, _ = st.columns(2)
                        with c_ts:
                            tan_suat = st.selectbox(
                                "Số Lần Thi Công / Tháng *",
                                [1,2,3,4,5,6], format_func=lambda x: TAN_SUAT_OPTS[x]
                            )
                        
                        st.markdown("""
                        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;margin:6px 0;font-size:12px;color:#1e40af;">
                          <i class=\"ph-gear\" style=\"font-size:15px;color:#64748b;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>Cấu hình chi tiết:</b> Bạn có thể chọn Ngày cố định hoặc Thứ cố định cho từng lần thi công trong tháng.
                        </div>
                        """, unsafe_allow_html=True)
                        
                        configs = []
                        for i in range(tan_suat):
                            st.markdown(f"**Lần {i+1}**")
                            c_loai, c_val1, c_val2 = st.columns([1,1,1])
                            with c_loai:
                                type_sel = st.selectbox("Loại", ["Ngày cố định", "Thứ cố định"], key=f"type_add_{i}", label_visibility="hidden")
                            
                            if type_sel == "Ngày cố định":
                                with c_val1:
                                    day_num = st.selectbox("Ngày", list(range(1, 32)), index=min(1 + (30//tan_suat)*i, 31)-1, key=f"day_add_{i}")
                                configs.append({"type": "ngay", "val": day_num})
                            else:
                                thu_options = {
                                    "Chủ Nhật": 0, "Thứ Hai": 1, "Thứ Ba": 2,
                                    "Thứ Tư": 3,  "Thứ Năm": 4, "Thứ Sáu": 5, "Thứ Bảy": 6
                                }
                                with c_val1:
                                    thu_sel = st.selectbox("Thứ", list(thu_options.keys()), key=f"thu_add_{i}")
                                with c_val2:
                                    tuan_sel = st.selectbox("Tuần", ["1", "2", "3", "4", "Cuối"], index=min(i, 3), key=f"tuan_add_{i}")
                                configs.append({"type": "thu", "thu": thu_options[thu_sel], "tuan": tuan_sel})
                        
                        import json
                        tuan_lap_lai_val = json.dumps(configs)
                        kieu_lap_val = "mixed"
                        lap_thu_val = None
                        
                        suggestion = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date()
                        ngay_thi_cong_dau = st.date_input(
                            "Kỳ Thi Công Bắt Đầu Lặp *",
                            value=suggestion,
                            help="Hệ thống sẽ dựa vào Tháng và Năm của ngày này để bắt đầu sinh lịch."
                        )
    
                        st.markdown('<hr style="margin:12px 0">', unsafe_allow_html=True)
                        st.markdown("**⏰ Khung Giờ Thi Công**")
    
                        gbd, gkt, time_valid = _time_input_row(
                            "Giờ Bắt Đầu *", "Giờ Kết Thúc *",
                            "form_gbd", "form_gkt"
                        )
    
                    else:
                        # ── KHÁCH LẺ ──
                        st.markdown("""
                        <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;margin:6px 0;font-size:12px;color:#92400e;">
                          <i class=\"ph-push-pin\" style=\"font-size:15px;color:#dc2626;vertical-align:middle;line-height:1;margin-right:3px;\"></i> <b>Khách lẻ:</b> Chọn ngày giờ thi công đầu tiên và thiết lập chu kỳ lặp (nếu có).
                        </div>
                        """, unsafe_allow_html=True)
    
                        c_ngay, c_gio = st.columns(2)
                        with c_ngay:
                            ngay_thi_cong_dau = st.date_input(
                                "📅 Ngày Thi Công (Đầu tiên) *",
                                value=(datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date(),
                                help="Ngày cụ thể sẽ thi công cho khách lẻ."
                            )
                        with c_gio:
                            gbd, gkt, time_valid = _time_input_row(
                                "⏰ Bắt Đầu *", "Kết Thúc *",
                                "form_gbd", "form_gkt"
                            )
                            
                        st.markdown("**🔄 Chu Kỳ Lặp**")
                        c_loai, c_so = st.columns(2)
                        with c_loai:
                            loai_ck = st.selectbox("Lặp theo", ["Chỉ 1 lần duy nhất", "Tuần", "Tháng", "Năm"])
                        
                        if loai_ck == "Chỉ 1 lần duy nhất":
                            chu_ky_lap = "1_lan"
                        else:
                            with c_so:
                                so_ck = st.number_input(f"Số {loai_ck.lower()} / lần thi công", min_value=1, value=1, step=1)
                            don_vi = "tuan" if loai_ck == "Tuần" else "thang" if loai_ck == "Tháng" else "nam"
                            chu_ky_lap = f"{so_ck}_{don_vi}"
                            
                        kieu_lap_val = "ngay_co_dinh"
                        tan_suat = 1
                        lap_thu_val = None
                        tuan_lap_lai_val = ""
    
                    ghi_chu  = st.text_area("Ghi Chú", height=60)

                    # KTV mặc định cho hợp đồng
                    conn_ktv = get_connection()
                    ktv_list = [r["ten"] for r in conn_ktv.execute("SELECT ten FROM technicians WHERE active=1 ORDER BY ten").fetchall()]
                    conn_ktv.close()
                    ktv_options = ["(Chưa chọn)"] + ktv_list
                    ktv_hd = st.selectbox("👷 Kỹ Thuật Viên phụ trách", ktv_options, help="KTV sẽ được gán mặc định cho các ca thi công của HĐ này")
                    ktv_val = ktv_hd if ktv_hd != "(Chưa chọn)" else None

                    gen_now  = st.checkbox("🤖 Tự sinh lịch ngay sau khi tạo", value=True)
    
                    # ── Live Preview ──
                    try:
                        hd_preview = {
                            "ngay_thi_cong_dau": ngay_thi_cong_dau.isoformat(),
                            "tan_suat": tan_suat,
                            "kieu_lap": kieu_lap_val,
                            "lap_thu":  lap_thu_val,
                            "tuan_lap_lai": tuan_lap_lai_val,
                            "gio_bat_dau": gbd, "gio_ket_thuc": gkt,
                            "loai_khach": loai_khach,
                            "chu_ky_lap": chu_ky_lap
                        }
                        ky_preview = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().strftime("%Y-%m")
                        prev_html = _preview_schedule(hd_preview, ky_preview)
                        st.markdown(f"""
                        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px;margin:10px 0;">
                          <div style="font-size:12px;font-weight:700;color:#166534;margin-bottom:8px;">
                            <i class=\"ph-calendar\" style=\"font-size:15px;color:#2563eb;vertical-align:middle;line-height:1;margin-right:3px;\"></i> Preview lịch tháng {ky_preview} — {TAN_SUAT_OPTS.get(tan_suat, str(tan_suat))}
                          </div>
                          {prev_html}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        from utils.scheduling import check_ktv_schedule_conflict, calc_dates_for_month
                        dates_preview = calc_dates_for_month(hd_preview, ky_preview)
                        
                        ky_next = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)).date().replace(day=1) + timedelta(days=32)
                        ky_next_str = ky_next.strftime("%Y-%m")
                        dates_next = calc_dates_for_month(hd_preview, ky_next_str)
                        
                        all_preview_dates = dates_preview + dates_next
                        conflicts = check_ktv_schedule_conflict(ktv_val, None, all_preview_dates, gbd, gkt)
                        if conflicts:
                            c_lines = []
                            for c in conflicts[:5]: # Chỉ hiện max 5
                                c_lines.append(f"<li>Ngày <b>{datetime.strptime(c['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}</b>: Trùng với <b>{c['ten_cty']}</b> ({c['gio_bat_dau']} - {c['gio_ket_thuc']})</li>")
                            if len(conflicts) > 5:
                                c_lines.append(f"<li><i>...và {len(conflicts)-5} ca khác</i></li>")
                            c_html = "".join(c_lines)
                            st.markdown(f"""
                            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;margin:10px 0;">
                              <div style="font-size:13px;font-weight:700;color:#dc2626;margin-bottom:6px;">
                                ⚠️ CẢNH BÁO: KTV {ktv_val} bị trùng lịch
                              </div>
                              <ul style="margin:0;padding-left:20px;font-size:12px;color:#991b1b;">
                                {c_html}
                              </ul>
                            </div>
                            """, unsafe_allow_html=True)
                            
                    except Exception as e:
                        print("Error in live preview:", e)
    
                    submitted = st.button("📄 Tạo Hợp Đồng", use_container_width=True)
                    if submitted:
                        try:
                            gia_tri = int(gia_tri_str.replace(".", "").replace(",", "").strip())
                        except ValueError:
                            gia_tri = -1
                            
                        if conflicts:
                            st.error(f"❌ Không thể tạo hợp đồng! KTV {ktv_val} bị trùng lịch. Vui lòng đổi KTV hoặc đổi khung giờ thi công.")
                        elif not ma_hd:
                            st.error("! Phải nhập mã hợp đồng!")
                        elif gia_tri < 0:
                            st.error("! Giá trị hợp đồng không hợp lệ!")
                        elif not time_valid:
                            st.error("! Định dạng giờ không hợp lệ!")
                        else:
                            try:
                                conn = get_connection()
                                conn.execute("""
                                    INSERT INTO contracts
                                      (ma_hd,ma_kh,ngay_ky,ngay_het_han,
                                       ngay_thi_cong_dau,gio_bat_dau,gio_ket_thuc,
                                       tan_suat,kieu_lap,lap_thu,gia_tri_thang,ghi_chu,
                                       don_vi_tinh,loai_khach,khu_vuc_xu_ly,loai_con_trung,chu_ky_lap,phuong_phap_xu_ly,tuan_lap_lai,ky_thuat_vien,vat_pct)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                """, (ma_hd, kh_opts[kh_sel],
                                      ngay_ky.isoformat(), ngay_ht.isoformat(),
                                      ngay_thi_cong_dau.isoformat(),
                                      gbd, gkt, tan_suat, kieu_lap_val, lap_thu_val,
                                      gia_tri, ghi_chu, don_vi_tinh, loai_khach, khu_vuc_xu_ly, loai_con_trung, chu_ky_lap, phuong_phap_xu_ly, tuan_lap_lai_val, ktv_val, vat_pct))
                                conn.commit(); conn.close()
                                if gen_now:
                                    # Sinh lịch từ tháng bắt đầu HĐ + 2 tháng tới
                                    start = ngay_thi_cong_dau.replace(day=1)
                                    n = 0
                                    for _ in range(3):  # tháng bắt đầu HĐ + 2 tháng tới
                                        n += auto_generate_schedules(ma_hd, start.strftime("%Y-%m"))
                                        start = (start + timedelta(days=32)).replace(day=1)
                                    st.session_state.add_hd_success = f"✓ Tạo HĐ **{ma_hd}** + sinh {n} ca!"
                                else:
                                    st.session_state.add_hd_success = f"✓ Tạo HĐ **{ma_hd}** thành công!"
                                st.rerun()
                            except Exception as e:
                                import traceback
                                traceback.print_exc()
                                st.error(f"× Có lỗi xảy ra: {e}")

            st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # PHÂN TÍCH
    # =========================================================
    with tab_chart:
        conn = get_connection()
        top8 = conn.execute("""
            SELECT ct.ma_hd, k.ten_cty, 
                   CASE 
                       WHEN ct.don_vi_tinh LIKE '%lần%' THEN ct.gia_tri_thang * ct.tan_suat 
                       ELSE ct.gia_tri_thang 
                   END as true_value
            FROM contracts ct JOIN customers k ON ct.ma_kh=k.ma_kh
            WHERE ct.trang_thai='active' ORDER BY true_value DESC LIMIT 8
        """).fetchall()
        freq = conn.execute("""
            SELECT tan_suat, kieu_lap, COUNT(*) cnt
            FROM contracts GROUP BY tan_suat, kieu_lap ORDER BY tan_suat
        """).fetchall()
        conn.close()

        c1, c2 = st.columns(2)
        with c1:
            if top8:
                fig = go.Figure(go.Bar(
                    y=[r["ten_cty"][:22] for r in top8],
                    x=[r["true_value"]/1e6 for r in top8],
                    orientation="h",
                    marker_color=["#16a34a","#22c55e","#4ade80","#86efac"]*2,
                    text=[f"{int(r['true_value'] or 0):,}".replace(",", ".") for r in top8],
                    textposition="outside",
                ))
                fig.update_layout(
                    height=300, paper_bgcolor="white", plot_bgcolor="white",
                    title=dict(text="Top HĐ Theo Giá Trị (triệu đ)",font=dict(size=13,color="#0f172a")),
                    margin=dict(l=10,r=60,t=40,b=10), font=dict(family="Inter"),
                    xaxis=dict(showgrid=True,gridcolor="#f1f5f9"), yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        with c2:
            if freq:
                labels = [f"{TAN_SUAT_OPTS[r['tan_suat']]} ({'Ngày cố định' if r['kieu_lap']=='ngay_co_dinh' else 'Thứ cố định'})" for r in freq]
                fig2 = go.Figure(go.Bar(
                    x=labels, y=[r["cnt"] for r in freq],
                    marker=dict(color=["#16a34a","#0d9488","#2563eb","#7c3aed",
                                       "#d97706","#dc2626","#64748b","#0f172a"]),
                    text=[str(r["cnt"]) for r in freq], textposition="outside",
                ))
                fig2.update_layout(
                    height=300, paper_bgcolor="white", plot_bgcolor="white",
                    title=dict(text="Phân Bổ HĐ Theo Tần Suất & Kiểu Lịch",font=dict(size=13,color="#0f172a")),
                    margin=dict(l=10,r=10,t=40,b=10), font=dict(family="Inter"),
                    xaxis=dict(showgrid=False,tickangle=-20),
                    yaxis=dict(showgrid=True,gridcolor="#f1f5f9"),
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
