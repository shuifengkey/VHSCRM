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
    CamScanner 'Magic Color' effect (Giữ nguyên phần làm nét xuất sắc của phiên bản mới)
    """
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=50)
    gray_f = gray.astype(np.float32)
    bg_f   = bg.astype(np.float32)
    divided = np.clip((gray_f / (bg_f + 1e-6)) * 200.0, 0, 255).astype(np.uint8)
    p2  = int(np.percentile(divided, 2))
    p98 = int(np.percentile(divided, 98))
    if p98 > p2:
        divided = np.clip((divided.astype(np.int32) - p2) * 255 // (p98 - p2), 0, 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(divided, (0, 0), sigmaX=2)
    sharpened = cv2.addWeighted(divided, 1.5, blurred, -0.5, 0)
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

        # --- TRỞ VỀ CÁCH TIẾP CẬN CŨ: Gaussian Blur + Otsu Canny ---
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        high_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        low_thresh = 0.5 * high_thresh
        edged = cv2.Canny(gray, low_thresh, high_thresh)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged = cv2.dilate(edged, kernel, iterations=2)
        edged = cv2.erode(edged, kernel, iterations=1)

        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]
        
        for c in cnts:
            area = cv2.contourArea(c)
            if area < img_area * 0.05:
                continue
                
            peri = cv2.arcLength(c, True)
            for eps in np.linspace(0.01, 0.1, 10):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4:
                    doc_cnt = approx.reshape(4, 2)
                    break
            if doc_cnt is not None:
                break
                
        # --- CÁI CŨ CỰC KỲ QUAN TRỌNG: Fallback minAreaRect ---
        # Nếu tờ giấy bị cắt mất 1 góc (ra 5 cạnh), nó sẽ lấy hình chữ nhật bao quanh
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.05:
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

        scanned = enhance_scan(warped)
        scanned_bgr = cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)

        cv2.imencode('.jpg', scanned_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(image_path)
        return (True, f"Cropped {orig_w}x{orig_h} → {max_w}x{max_h}")

    except Exception as e:
        import traceback
        print(f"[auto_crop_document] Error: {e}")
        return (False, f"Error: {str(e)}")