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
    Giữ nguyên màu sắc (Color Document), chỉ tăng tương phản nhẹ và làm nét.
    Sử dụng CLAHE trên kênh độ sáng (L) để làm nổi bật nét chữ mà không hỏng màu.
    """
    # 1. Chuyển sang không gian màu LAB để tách kênh độ sáng (L) ra khỏi màu (A, B)
    lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # 2. Cân bằng tương phản tự động trên kênh L
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    
    # 3. Gộp lại và chuyển về BGR
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # 4. Làm nét nhẹ để chữ sắc sảo (Unsharp Masking)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    
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

        # --- SIÊU BẮT GÓC: Lọc chữ bằng Median Blur + Otsu Threshold + Convex Hull ---
        # Phương pháp này KHÔNG dùng Canny để tránh nhiễu do text trên giấy
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        
        # 1. Median Blur (11x11) xoá sạch chữ và nhiễu, nhưng giữ lại CỰC KỲ SẮC NÉT viền giấy
        blurred = cv2.medianBlur(gray, 11)
        
        # 2. Otsu threshold để tách hẳn mảng giấy trắng và nền tối
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. Morphological close để lấp đầy các lỗ thủng trên mảng giấy (nếu có)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # 4. Tìm viền ngoài cùng (RETR_EXTERNAL) để bỏ qua các chi tiết bên trong tờ giấy
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:3]
        
        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]
        
        if len(cnts) > 0:
            c = cnts[0] # Lấy mảng lớn nhất (chắc chắn là tờ giấy)
            if cv2.contourArea(c) > img_area * 0.05:
                # 5. Dùng Convex Hull để bọc mảng giấy như kéo một sợi dây thun xung quanh, 
                # loại bỏ các phần lõm do bị rách hay nhiễu
                hull = cv2.convexHull(c)
                peri = cv2.arcLength(hull, True)
                
                # 6. Ép về đa giác 4 cạnh
                for eps in np.linspace(0.01, 0.1, 10):
                    approx = cv2.approxPolyDP(hull, eps * peri, True)
                    if len(approx) == 4:
                        doc_cnt = approx.reshape(4, 2)
                        break
                        
                # 7. Fallback CỰC KỲ QUAN TRỌNG: minAreaRect
                if doc_cnt is None:
                    rect = cv2.minAreaRect(c)
                    box = cv2.boxPoints(rect)
                    doc_cnt = np.int32(box)

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