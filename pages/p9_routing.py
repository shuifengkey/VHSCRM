import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from utils.database import get_connection
from utils.maps_integration import get_coordinates_from_address, get_optimized_motorcycle_route
import folium
from streamlit_folium import st_folium

def ui():
    st.title("🗺️ Tối Ưu Lộ Trình Xe Máy (HERE Maps)")
    
    st.info("Tính năng này sử dụng hoàn toàn HERE Maps API để lấy tọa độ và tính toán đường đi xe máy ngắn nhất cho KTV.")
    
    # Get API keys from secrets
    here_api_key = st.secrets.get("HERE_API_KEY", "")
    
    if not here_api_key:
        st.warning("⚠️ Hệ thống chưa được cấu hình đủ API Keys. Vui lòng thêm `HERE_API_KEY` vào file cấu hình (Streamlit Secrets) để sử dụng tính năng này.")
        return
        
    conn = get_connection()
    
    # Lấy danh sách KTV
    ktvs = conn.execute("SELECT * FROM technicians WHERE active=1").fetchall()
    ktv_options = {k["ma_ktv"]: k["ten"] for k in ktvs}
    
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Chọn ngày làm việc", value=date.today())
    with col2:
        selected_ktv_ma = st.selectbox("Chọn Kỹ Thuật Viên", options=[""] + list(ktv_options.keys()), format_func=lambda x: ktv_options[x] if x else "-- Chọn KTV --")
        
    if selected_ktv_ma:
        selected_ktv_ten = ktv_options[selected_ktv_ma]
        st.markdown(f"### Lịch trình của **{selected_ktv_ten}** ngày **{selected_date.strftime('%d/%m/%Y')}**")
        
        # Lấy lịch trình của KTV trong ngày
        query = """
            SELECT s.id, s.ma_hd, c.ten_cty, c.dia_chi, c.lat, c.lng, s.gio_bat_dau, s.gio_ket_thuc, s.trang_thai
            FROM schedules s
            JOIN contracts ct ON s.ma_hd = ct.ma_hd
            JOIN customers c ON ct.ma_kh = c.ma_kh
            WHERE s.ngay_du_kien = ? 
              AND s.ky_thuat_vien = ?
              AND s.trang_thai != 'skipped'
            ORDER BY s.gio_bat_dau ASC
        """
        schedules = conn.execute(query, (selected_date.isoformat(), selected_ktv_ten)).fetchall()
        
        if not schedules:
            st.success("Không có ca thi công nào trong ngày này.")
            return
            
        st.write(f"Tìm thấy **{len(schedules)}** ca thi công.")
        
        df = pd.DataFrame([dict(s) for s in schedules])
        st.dataframe(df[["ten_cty", "dia_chi", "gio_bat_dau", "gio_ket_thuc", "trang_thai"]], use_container_width=True)
        
        if st.button("🚀 TỐI ƯU LỘ TRÌNH (HERE MAPS)", type="primary"):
            with st.spinner("Đang xử lý tọa độ và tính toán lộ trình tối ưu..."):
                try:
                    # 1. Đảm bảo tất cả khách hàng đều có toạ độ (Geocoding)
                    waypoints = []
                    for idx, s in enumerate(schedules):
                        lat, lng = s["lat"], s["lng"]
                        if not lat or not lng:
                            st.write(f"Đang lấy tọa độ cho: {s['ten_cty']}...")
                            lat, lng = get_coordinates_from_address(s["dia_chi"], here_api_key)
                            if lat and lng:
                                # Lưu vào DB để lần sau không gọi lại
                                conn.execute("UPDATE customers SET lat=?, lng=? WHERE dia_chi=?", (lat, lng, s["dia_chi"]))
                                conn.commit()
                        
                        if lat and lng:
                            waypoints.append({
                                "id": str(s["id"]),
                                "lat": lat,
                                "lng": lng,
                                "name": s["ten_cty"],
                                "time": s["gio_bat_dau"]
                            })
                        else:
                            st.error(f"❌ Không thể lấy tọa độ cho {s['ten_cty']} ({s['dia_chi']}). Bỏ qua điểm này.")
                            
                    if len(waypoints) < 2:
                        st.warning("Cần ít nhất 2 điểm có tọa độ để tính toán lộ trình.")
                        return
                        
                    # Mặc định lấy điểm đầu tiên trong lịch trình hiện tại làm điểm xuất phát (hoặc có thể setup trụ sở công ty)
                    start_point = waypoints[0]
                    destinations = waypoints[1:]
                    
                    st.write("Đang gọi HERE Maps Routing API...")
                    optimized_sequence, polyline_points = get_optimized_motorcycle_route(start_point, destinations, here_api_key)
                    
                    # 2. Hiển thị kết quả lên Bản đồ
                    m = folium.Map(location=[start_point["lat"], start_point["lng"]], zoom_start=13)
                    
                    # Add start point
                    folium.Marker(
                        [start_point["lat"], start_point["lng"]], 
                        popup=f"Xuất phát: {start_point['name']}",
                        icon=folium.Icon(color='green', icon='play')
                    ).add_to(m)
                    
                    # Add destinations with optimized numbers
                    waypoint_map = {wp["id"]: wp for wp in waypoints}
                    for seq in optimized_sequence:
                        wp_info = waypoint_map[seq["id"]]
                        folium.Marker(
                            [seq["lat"], seq["lng"]], 
                            popup=f"Thứ tự {seq['sequence']}: {wp_info['name']} (Dự kiến cũ: {wp_info['time']})",
                            icon=folium.Icon(color='blue', icon='info-sign')
                        ).add_to(m)
                        
                    # Draw polyline
                    if polyline_points:
                        folium.PolyLine(polyline_points, color="red", weight=4, opacity=0.8).add_to(m)
                    
                    st_folium(m, width=700, height=500)
                    
                    # 3. Đề xuất cập nhật lại giờ thi công
                    st.success("Tối ưu thành công!")
                    
                    st.markdown("### Đề xuất thứ tự mới:")
                    new_order_data = []
                    new_order_data.append({"Thứ tự": 1, "Công ty": start_point["name"], "Giờ (Hiện tại)": start_point["time"]})
                    for seq in optimized_sequence:
                        wp_info = waypoint_map[seq["id"]]
                        new_order_data.append({"Thứ tự": seq["sequence"] + 1, "Công ty": wp_info["name"], "Giờ (Hiện tại)": wp_info["time"]})
                        
                    st.dataframe(pd.DataFrame(new_order_data), hide_index=True)
                    
                    st.warning("⚠️ Tính năng tự động đổi Giờ Thi Công theo khoảng cách đang được phát triển. Vui lòng quay lại màn hình Lịch Thi Công để cập nhật giờ thủ công theo thứ tự này.")
                    
                except Exception as e:
                    st.error(f"Lỗi: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    ui()
