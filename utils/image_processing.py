import cv2
import numpy as np

def order_points(pts):
    """
    Sắp xếp 4 góc theo thứ tự: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left
    rect[2] = pts[np.argmax(s)]   # bottom-right
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    
    return rect

def enhance_scan(warped):
    """
    Xử lý sau (Post-processing):
    Nền giấy trắng sáng, chữ đậm, GIỮ NGUYÊN MÀU SẮC (Color).
    """
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    black_point = np.percentile(gray, 3)
    white_point = np.percentile(gray, 95)
    
    warped_f = warped.astype(np.float32)
    diff = white_point - black_point
    if diff < 10:
        diff = 10 
        
    # Điều chỉnh contrast và brightness
    adjusted = np.clip((warped_f - black_point) * (255.0 / diff), 0, 255).astype(np.uint8)
    
    # Tăng sharpness (Unsharp Masking)
    blurred = cv2.GaussianBlur(adjusted, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(adjusted, 1.5, blurred, -0.5, 0)
    
    return sharpened

def auto_crop_document(image_path):
    """
    Chương trình Document Scanner
    """
    try:
        # 1. Đọc ảnh đầu vào
        raw = np.frombuffer(open(image_path, "rb").read(), dtype=np.uint8)
        orig = cv2.imdecode(raw, cv2.IMREAD_COLOR)

        if orig is None:
            return (False, "Cannot decode image.")

        orig_h, orig_w = orig.shape[:2]
        ratio = orig_h / 800.0
        
        # Resize để xử lý nhanh hơn
        if ratio > 1:
            process_img = cv2.resize(orig, (int(orig_w / ratio), 800), interpolation=cv2.INTER_AREA)
        else:
            process_img = orig.copy()
            ratio = 1.0

        # 2. Tiền xử lý (Preprocessing)
        # Chuyển ảnh sang grayscale
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        
        # Tăng độ tương phản trước khi tìm viền (Contrast Enhancement - CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Áp dụng Gaussian Blur để giảm nhiễu
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 3. Phát hiện biên (Edge Detection) bằng Canny Edge Detection
        edged = cv2.Canny(blurred, 75, 200)

        # 4. Tìm contour và phát hiện trang tài liệu
        # Tìm tất cả contours
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        # Lấy các contour có diện tích lớn nhất
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]

        for c in cnts:
            if cv2.contourArea(c) < img_area * 0.05: # Lọc contour quá nhỏ
                continue
            
            # Xấp xỉ contour đó thành hình 4 cạnh (4 góc) bằng approxPolyDP
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            if len(approx) == 4:
                doc_cnt = approx.reshape(4, 2)
                break
                
        # Nếu không tìm thấy contour 4 cạnh thì thử các cách khác (Fallback)
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.05:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                doc_cnt = np.int32(box)

        if doc_cnt is None:
            # Fallback cuối cùng: lấy nguyên ảnh
            doc_cnt = np.array([
                [0, 0],
                [process_img.shape[1] - 1, 0],
                [process_img.shape[1] - 1, process_img.shape[0] - 1],
                [0, process_img.shape[0] - 1]
            ])

        # Đưa toạ độ về lại ảnh gốc
        doc_cnt = doc_cnt.astype(np.float32) * ratio

        # 5. Căn chỉnh góc nhìn (Perspective Correction)
        # Sắp xếp 4 góc
        rect = order_points(doc_cnt)
        tl, tr, br, bl = rect

        # Tính toán ma trận Perspective Transform (Homography)
        width_top = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        height_left = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)

        max_w = int(max(width_top, width_bottom))
        max_h = int(max(height_left, height_right))

        if max_w == 0 or max_h == 0:
            return (False, "Degenerate contour.")

        # Căn chỉnh trang A4
        a4_ratio = 1.4142
        if max_h >= max_w:
            max_h = int(max_w * a4_ratio)
        else:
            max_h = int(max_w / a4_ratio)

        dst = np.array([
            [0, 0],
            [max_w - 1, 0],
            [max_w - 1, max_h - 1],
            [0, max_h - 1]
        ], dtype="float32")

        # Áp dụng warpPerspective để biến ảnh về góc nhìn trực diện
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # 6. Crop trang tài liệu theo vùng tài liệu đã được chỉnh thẳng
        warped = cv2.warpPerspective(orig, M, (max_w, max_h))

        # 7. Xử lý sau (Post-processing)
        scanned = enhance_scan(warped)

        # Lưu ảnh
        cv2.imencode('.jpg', scanned, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(image_path)
        return (True, f"Cropped {orig_w}x{orig_h} -> {max_w}x{max_h}")

    except Exception as e:
        import traceback
        print(f"[auto_crop_document] Error: {e}")
        return (False, f"Error: {str(e)}")
