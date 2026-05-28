import cv2
import numpy as np

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   
    rect[2] = pts[np.argmax(s)]   
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  
    rect[3] = pts[np.argmax(diff)]  
    return rect

def enhance_scan(warped):
    """
    Nền giấy trắng sáng (White Paper), chữ đậm (Dark Text), GIỮ NGUYÊN MÀU SẮC (Color).
    Sử dụng kỹ thuật Stretch Contrast dựa trên phân vị (Percentile) để làm trắng nền.
    """
    # Lấy ảnh xám để phân tích độ sáng
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    # Tìm điểm tối nhất (chữ) và sáng nhất (nền giấy)
    # Loại bỏ 3% nhiễu ở hai đầu để không bị nhiễu do điểm đen/trắng bất thường
    black_point = np.percentile(gray, 3)
    white_point = np.percentile(gray, 95)
    
    # Kéo giãn dải màu (Stretch Contrast) trên từng kênh BGR
    # Điểm sáng nhất thành 255 (trắng tinh), điểm tối nhất thành 0 (đen thui)
    warped_f = warped.astype(np.float32)
    diff = white_point - black_point
    if diff < 10:
        diff = 10  # Tránh lỗi chia cho 0 nếu ảnh quá mờ
        
    # Công thức: Pixel_mới = (Pixel_cũ - Black) * (255 / Diff)
    adjusted = np.clip((warped_f - black_point) * (255.0 / diff), 0, 255).astype(np.uint8)
    
    # Làm nét nhẹ (Unsharp Masking) để chữ sắc sảo hơn
    blurred = cv2.GaussianBlur(adjusted, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(adjusted, 1.5, blurred, -0.5, 0)
    
    return sharpened

def auto_crop_document(image_path):
    try:
        raw = np.frombuffer(open(image_path, "rb").read(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)

        if image is None:
            return (False, "Cannot decode image.")

        orig = image.copy()
        orig_h, orig_w = orig.shape[:2]

        # --- TRỞ VỀ CÁCH TIẾP CẬN CŨ: Resize về 800px ---
        ratio = orig_h / 800.0
        if ratio > 1:
            proc_w = int(orig_w / ratio)
            process_img = cv2.resize(image, (proc_w, 800), interpolation=cv2.INTER_AREA)
        else:
            process_img = orig.copy()
            ratio = 1.0

        # --- SIÊU BẮT GÓC V2: Kết hợp Canny Edge và Convex Hull ---
        # Khắc phục lỗi: Mặt bàn có màu sáng/bóng mờ làm Otsu Threshold bị lem ra ngoài mặt bàn.
        # Dùng Canny để tìm sự thay đổi đột ngột giữa mép giấy và mặt bàn.
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        
        # 1. Blur nhẹ để giảm nhiễu (giữ lại các mép rõ ràng)
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 2. Canny Edge Detection với ngưỡng tự động (Otsu)
        high_thresh, _ = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        edged = cv2.Canny(gray_blur, 0.5 * high_thresh, high_thresh)
        
        # 3. Dilate để nối liền các đứt gãy ở mép giấy
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged = cv2.dilate(edged, kernel, iterations=2)
        edged = cv2.erode(edged, kernel, iterations=1)
        
        # 4. Tìm TẤT CẢ các đường viền
        cnts, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
        
        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]
        best_area = 0
        
        for c in cnts:
            if cv2.contourArea(c) < img_area * 0.05:
                continue
            
            # Dùng Convex Hull để quấn dây thun quanh hình (bỏ qua các nét lõm/rách)
            hull = cv2.convexHull(c)
            
            # TUYỆT KỸ: Thay vì dùng approxPolyDP (dễ thất bại nếu giấy cong làm thành 5-6 góc),
            # ta chủ động trích xuất ĐÚNG 4 ĐIỂM GÓC NGOÀI CÙNG từ bao lồi (Top-Left, Top-Right, Bottom-Right, Bottom-Left)
            pts = hull.reshape(-1, 2)
            if len(pts) < 4:
                continue
                
            s = pts.sum(axis=1)
            diff = np.diff(pts, axis=1)
            
            tl = pts[np.argmin(s)]
            br = pts[np.argmax(s)]
            tr = pts[np.argmin(diff)]
            bl = pts[np.argmax(diff)]
            
            approx = np.array([tl, tr, br, bl], dtype=np.int32)
            area = cv2.contourArea(approx)
            
            # Lấy mảng 4 góc có diện tích lớn nhất (chính là tờ giấy)
            if area > best_area:
                best_area = area
                doc_cnt = approx.reshape(4, 2)

        # Nếu hoàn toàn không thấy gì, lấy nguyên cái ảnh
        if doc_cnt is None:
            doc_cnt = np.array([
                [0, 0],
                [process_img.shape[1] - 1, 0],
                [process_img.shape[1] - 1, process_img.shape[0] - 1],
                [0, process_img.shape[0] - 1]
            ])
            
        doc_cnt = doc_cnt.astype(np.float32) * ratio
        rect = order_points(doc_cnt)
        tl, tr, br, bl = rect

        width_top    = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        height_left  = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)

        max_w = int(max(width_top, width_bottom))
        max_h = int(max(height_left, height_right))

        if max_w == 0 or max_h == 0:
            return (False, "Degenerate contour.")

        # --- Ép tỷ lệ A4 (luôn ra form dọc/ngang chuẩn) ---
        a4_ratio = 1.4142
        if max_h >= max_w:
            max_h = int(max_w * a4_ratio)
        else:
            max_h = int(max_w / a4_ratio)

        dst = np.array([
            [0,         0        ],
            [max_w - 1, 0        ],
            [max_w - 1, max_h - 1],
            [0,         max_h - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (max_w, max_h))

        scanned_bgr = enhance_scan(warped)
        
        cv2.imencode('.jpg', scanned_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(image_path)
        return (True, f"Cropped {orig_w}x{orig_h} → {max_w}x{max_h}")

    except Exception as e:
        import traceback
        print(f"[auto_crop_document] Error: {e}")
        return (False, f"Error: {str(e)}")