from zoneinfo import ZoneInfo
# pages/p6_debts.py - Công Nợ v2 — Charts + Aging + Quick Pay
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_connection
from utils.styles import badge, section_header, stat_row, COLORS
from datetime import date
import plotly.graph_objects as go

def render():
    st.markdown(section_header("Quản Lý Công Nợ", "Theo dõi thu chi — Aging report — Ghi nhận thanh toán nhanh", "💰"), unsafe_allow_html=True)

    tab_overview, tab_detail, tab_manage = st.tabs(["📊  Tổng Quan", "📋  Chi Tiết", "⚙️  Quản Lý"])

    with tab_overview:
        conn = get_connection()
        summary = conn.execute("""
            SELECT SUM(can_thu) tong_ct, SUM(da_thu) tong_dt,
                   SUM(can_thu-da_thu) tong_no,
                   COUNT(DISTINCT CASE WHEN can_thu>da_thu THEN ma_kh END) kh_no
            FROM debts
        """).fetchone()
        tong_ct = summary["tong_ct"] or 0
        tong_dt = summary["tong_dt"] or 0
        tong_no = summary["tong_no"] or 0
        kh_no   = summary["kh_no"] or 0
        rate    = int(tong_dt/tong_ct*100) if tong_ct else 100

        # KPI cards
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("📬 Tổng Cần Thu", f"{tong_ct/1e6:.1f}M đ")
        with c2: st.metric("✅ Đã Thu", f"{tong_dt/1e6:.1f}M đ", delta=f"{rate}% tỷ lệ")
        with c3: st.metric("⚠️ Còn Nợ", f"{tong_no/1e6:.1f}M đ")
        with c4: st.metric("🏢 KH Đang Nợ", kh_no)

        # Thanh progress tổng
        st.markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin:16px 0;">
            <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:600;color:#0f172a;margin-bottom:10px;">
                <span>Tiến độ thu nợ tổng thể</span>
                <span style="color:{'#16a34a' if rate>=80 else '#d97706' if rate>=50 else '#dc2626'};">{rate}%</span>
            </div>
            <div style="background:#f1f5f9;border-radius:99px;height:12px;">
                <div style="background:{'#16a34a' if rate>=80 else '#d97706' if rate>=50 else '#dc2626'};
                            height:12px;border-radius:99px;width:{rate}%;transition:width 1s;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-top:6px;">
                <span>Đã thu: {tong_dt/1e6:.2f}M đ</span>
                <span>Còn lại: {tong_no/1e6:.2f}M đ</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_chart, col_top = st.columns([3,2])

        with col_chart:
            # Biểu đồ doanh thu 6 tháng
            monthly = conn.execute("""
                SELECT ky_thanh_toan, SUM(can_thu) ct, SUM(da_thu) dt
                FROM debts GROUP BY ky_thanh_toan ORDER BY ky_thanh_toan DESC LIMIT 6
            """).fetchall()
            monthly = list(reversed(monthly))

            if monthly:
                fig = go.Figure()
                fig.add_scatter(
                    x=[r["ky_thanh_toan"] for r in monthly],
                    y=[r["ct"]/1e6 for r in monthly],
                    name="Cần Thu", line=dict(color="#e2e8f0",width=3),
                    fill="tozeroy", fillcolor="rgba(226,232,240,.3)"
                )
                fig.add_scatter(
                    x=[r["ky_thanh_toan"] for r in monthly],
                    y=[r["dt"]/1e6 for r in monthly],
                    name="Đã Thu", line=dict(color="#16a34a",width=3),
                    fill="tozeroy", fillcolor="rgba(22,163,74,.15)",
                    mode="lines+markers", marker=dict(size=6,color="#16a34a")
                )
                fig.update_layout(
                    height=240, paper_bgcolor="white", plot_bgcolor="white",
                    title=dict(text="Cần Thu vs Đã Thu (triệu đ)", font=dict(size=14,color="#0f172a")),
                    margin=dict(l=10,r=10,t=40,b=30), font=dict(family="Inter"),
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True,gridcolor="#f1f5f9"),
                    legend=dict(orientation="h",y=-0.2)
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with col_top:
            st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:12px;">🔴 Top Nợ Nhiều Nhất</div>', unsafe_allow_html=True)
            top_debtors = conn.execute("""
                SELECT d.ma_kh, c.ten_cty, SUM(d.can_thu-d.da_thu) no
                FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh
                WHERE d.can_thu > d.da_thu GROUP BY d.ma_kh ORDER BY no DESC LIMIT 5
            """).fetchall()
            if top_debtors:
                max_no = top_debtors[0]["no"]
                for t in top_debtors:
                    pct = int(t["no"]/max_no*100)
                    st.markdown(f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
                            <span style="font-weight:600;color:#0f172a;">{t['ten_cty'][:22]}</span>
                            <span style="color:#dc2626;font-weight:700;">{t['no']/1e6:.1f}M</span>
                        </div>
                        <div style="background:#fee2e2;border-radius:99px;height:5px;">
                            <div style="background:#dc2626;height:5px;border-radius:99px;width:{pct}%;"></div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="text-align:center;color:#94a3b8;padding:16px;font-size:13px;">🎉 Không có nợ tồn đọng!</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        conn.close()

    with tab_detail:
        conn = get_connection()
        c1,c2,c3 = st.columns([2,1,1])
        with c1: search = st.text_input("🔍 Tìm kiếm", placeholder="Mã KH, tên, mã HĐ...")
        with c2: filter_ky = st.text_input("Kỳ thanh toán", placeholder="VD: 2025-05")
        with c3: filter_no = st.selectbox("Lọc", ["Tất cả","Còn nợ","Đã thanh toán"])

        q = """SELECT d.*, c.ten_cty, c.sdt, (d.can_thu-d.da_thu) con_no
               FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh WHERE 1=1"""
        p = []
        if search:
            q += " AND (d.ma_kh LIKE ? OR c.ten_cty LIKE ? OR d.ma_hd LIKE ?)"
            p.extend([f"%{search}%"]*3)
        if filter_ky:
            q += " AND d.ky_thanh_toan LIKE ?"; p.append(f"%{filter_ky}%")
        if filter_no == "Còn nợ":   q += " AND d.can_thu > d.da_thu"
        if filter_no == "Đã thanh toán": q += " AND d.can_thu <= d.da_thu"
        q += " ORDER BY d.ky_thanh_toan DESC, d.ma_kh"
        debts = conn.execute(q, p).fetchall()
        conn.close()

        st.markdown(f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;"><b>{len(debts)}</b> bản ghi</div>', unsafe_allow_html=True)

        # Mobile-friendly Card Layout thay cho Table
        rows_html = ""
        for d in debts:
            no = d["can_thu"] - d["da_thu"]
            pct = int(d["da_thu"]/d["can_thu"]*100) if d["can_thu"] else 100
            row_bg = "#fff5f5" if no > 0 else "white"
            no_color = "#dc2626" if no > 0 else "#16a34a"
            border_color = "#fecaca" if no > 0 else "#e2e8f0"
            rows_html += f"""
            <div style="background:{row_bg};border:1px solid {border_color};border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#0f172a;">{d['ten_cty']}</div>
                        <div style="font-size:12px;color:#64748b;margin-top:2px;">
                            📋 {d['ma_hd']} &nbsp;·&nbsp; 🗓️ Kỳ {d['ky_thanh_toan']}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:16px;font-weight:800;color:{no_color};">{no/1e6:.2f}M đ</div>
                        <div style="font-size:11px;color:#94a3b8;">{'Còn Nợ' if no > 0 else 'Đã Xong'}</div>
                    </div>
                </div>
                
                <div style="display:flex;justify-content:space-between;background:#f8fafc;padding:10px;border-radius:8px;margin-bottom:10px;border:1px solid #e2e8f0;">
                    <div style="text-align:center;">
                        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;">Cần Thu</div>
                        <div style="font-size:14px;font-weight:700;color:#0f172a;">{d['can_thu']/1e6:.2f}M</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;">Đã Thu</div>
                        <div style="font-size:14px;font-weight:700;color:#16a34a;">{d['da_thu']/1e6:.2f}M</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700;">Ngày Thu</div>
                        <div style="font-size:13px;font-weight:600;color:#0f172a;">{d['ngay_thu'][:10] if d['ngay_thu'] else '—'}</div>
                    </div>
                </div>
                
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:4px;">
                    <span>Tiến độ thanh toán</span>
                    <span style="font-weight:700;color:#0f172a;">{pct}%</span>
                </div>
                <div style="background:#e2e8f0;border-radius:99px;height:6px;width:100%;">
                    <div style="background:{'#16a34a' if pct>=100 else '#d97706' if pct>=50 else '#dc2626'};height:6px;border-radius:99px;width:{pct}%;"></div>
                </div>
            </div>"""

        st.markdown(f"""<div>{rows_html}</div>""", unsafe_allow_html=True)

    with tab_manage:
        col_pay, col_new = st.columns([1,1])

        with col_pay:
            st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:20px;">', unsafe_allow_html=True)
            st.markdown("**✅ Ghi Nhận Thanh Toán**")
            st.markdown('<hr style="margin:8px 0 14px">', unsafe_allow_html=True)

            conn = get_connection()
            unpaid = conn.execute("""
                SELECT d.id, d.ma_hd, d.ma_kh, d.ky_thanh_toan, d.can_thu, d.da_thu,
                       (d.can_thu-d.da_thu) con_no, c.ten_cty
                FROM debts d JOIN customers c ON d.ma_kh=c.ma_kh
                WHERE d.can_thu > d.da_thu ORDER BY d.ky_thanh_toan, c.ten_cty
            """).fetchall()
            conn.close()

            if not unpaid:
                st.success("🎉 Tất cả đã thanh toán đầy đủ!")
            else:
                debt_opts = {
                    f"[{r['ky_thanh_toan']}] {r['ten_cty']} — còn {r['con_no']/1e6:.2f}M": dict(r)
                    for r in unpaid
                }
                sel = st.selectbox("Chọn Kỳ", list(debt_opts.keys()))
                d = debt_opts[sel]

                st.markdown(f"""
                <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px;margin:8px 0;font-size:13px;">
                    💰 Cần thu: <b>{d['can_thu']/1e6:.2f}M</b> &nbsp;·&nbsp;
                    ✅ Đã thu: <b style="color:#16a34a">{d['da_thu']/1e6:.2f}M</b> &nbsp;·&nbsp;
                    ⚠️ Còn: <b style="color:#dc2626">{d['con_no']/1e6:.2f}M</b>
                </div>""", unsafe_allow_html=True)

                so_tien = st.number_input("Số Tiền Thu Thêm (VNĐ)",
                    min_value=0.0, max_value=float(d["con_no"]),
                    value=float(d["con_no"]), step=100_000.0)

                if st.button("💳 Xác Nhận Thu Tiền", use_container_width=True):
                    try:
                        conn = get_connection()
                        new_da_thu = d["da_thu"] + so_tien
                        conn.execute("UPDATE debts SET da_thu=?,ngay_thu=? WHERE id=?",
                                     (new_da_thu, datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat(), d["id"]))
                        conn.commit(); conn.close()
                        if new_da_thu >= d["can_thu"]:
                            st.success("✅ Thanh toán HOÀN TẤT!"); st.balloons()
                        else:
                            remain = d["can_thu"] - new_da_thu
                            st.success(f"✅ Ghi nhận {so_tien/1e6:.2f}M. Còn lại {remain/1e6:.2f}M")
                        st.rerun()
                    except Exception as e: st.error(f"❌ {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_new:
            st.markdown('<div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:20px;">', unsafe_allow_html=True)
            st.markdown("**➕ Tạo Kỳ Thu Mới**")
            st.markdown('<hr style="margin:8px 0 14px">', unsafe_allow_html=True)

            conn = get_connection()
            contracts = conn.execute("""
                SELECT ct.ma_hd, ct.ma_kh, c.ten_cty, ct.gia_tri_thang
                FROM contracts ct JOIN customers c ON ct.ma_kh=c.ma_kh
                WHERE ct.trang_thai='active' ORDER BY ct.ma_hd
            """).fetchall()
            conn.close()

            with st.form("form_new_debt"):
                hd_opts = {f"{r['ma_hd']} – {r['ten_cty']}": dict(r) for r in contracts}
                hd_sel  = st.selectbox("Hợp Đồng", list(hd_opts.keys()))
                hd = hd_opts.get(hd_sel, {})
                c1,c2 = st.columns(2)
                with c1:
                    ky = st.text_input("Kỳ (YYYY-MM)", value=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().strftime("%Y-%m"))
                    ct = st.number_input("Cần Thu (VNĐ)", value=float(hd.get("gia_tri_thang",0)), step=100_000.0)
                with c2:
                    dt = st.number_input("Đã Thu (VNĐ)", value=0.0, step=100_000.0)
                    gc = st.text_input("Ghi Chú")
                if st.form_submit_button("➕ Tạo Kỳ Thu", use_container_width=True):
                    try:
                        conn = get_connection()
                        conn.execute("INSERT INTO debts (ma_hd,ma_kh,ky_thanh_toan,can_thu,da_thu,ghi_chu) VALUES(?,?,?,?,?,?)",
                                     (hd["ma_hd"],hd["ma_kh"],ky,ct,dt,gc))
                        conn.commit(); conn.close()
                        st.success(f"✅ Đã tạo kỳ {ky}"); st.rerun()
                    except Exception as e: st.error(f"❌ {e}")
            st.markdown("</div>", unsafe_allow_html=True)
