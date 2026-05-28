import cv2
import numpy as np


def order_points(pts):
    """
    Order 4 corner points: [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]   # bottom-right: largest sum
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right: smallest diff
    rect[3] = pts[np.argmax(diff)]  # bottom-left: largest diff
    return rect


def find_document_contour(process_img):
    """
    Try multiple strategies to find the document's 4-corner contour.
    Returns a (4,2) numpy array of corners, or None if not found.
    """
    img_h, img_w = process_img.shape[:2]
    img_area = img_h * img_w

    gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 0)

    def search_contours(edge_img, min_area_ratio=0.10):
        """Search for 4-point quadrilateral in an edge map."""
        cnts, _ = cv2.findContours(edge_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]
        for c in cnts:
            area = cv2.contourArea(c)
            if area < img_area * min_area_ratio:
                continue
            peri = cv2.arcLength(c, True)
            # Try progressively looser approximations
            for eps in np.linspace(0.01, 0.12, 15):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4:
                    return approx
        return None

    # --- Strategy 1: Otsu-Canny (best for paper on desk) ---
    otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    canny1 = cv2.Canny(gray, otsu_val * 0.5, otsu_val)
    kernel = np.ones((5, 5), np.uint8)
    canny1 = cv2.dilate(canny1, kernel, iterations=2)
    canny1 = cv2.erode(canny1, kernel, iterations=1)
    cnt = search_contours(canny1, min_area_ratio=0.10)
    if cnt is not None:
        return cnt

    # --- Strategy 2: Auto-Canny based on median brightness ---
    v = np.median(gray)
    lo = int(max(0, (1.0 - 0.33) * v))
    hi = int(min(255, (1.0 + 0.33) * v))
    canny2 = cv2.Canny(gray, lo, hi)
    canny2 = cv2.dilate(canny2, kernel, iterations=2)
    canny2 = cv2.erode(canny2, kernel, iterations=1)
    cnt = search_contours(canny2, min_area_ratio=0.08)
    if cnt is not None:
        return cnt

    # --- Strategy 3: Otsu threshold on inverted image (dark paper on light bg) ---
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh = cv2.dilate(thresh, kernel, iterations=2)
    cnt = search_contours(thresh, min_area_ratio=0.08)
    if cnt is not None:
        return cnt

    # --- Strategy 4: minAreaRect of largest contour (last resort) ---
    cnts_all, _ = cv2.findContours(canny1, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if cnts_all:
        biggest = max(cnts_all, key=cv2.contourArea)
        if cv2.contourArea(biggest) > img_area * 0.05:
            rect = cv2.minAreaRect(biggest)
            box = cv2.boxPoints(rect)
            return np.int32(box)

    return None  # Couldn't find a document


def enhance_scan(warped):
    """
    CamScanner 'Magic Color' effect:
    - Estimates background illumination via large Gaussian blur
    - Divides original by background (removes shadows & uneven lighting)
    - Normalizes contrast so paper becomes pure white, ink becomes pure black
    - Sharpens to make text crispy
    Returns a grayscale image that looks exactly like a B&W scanner output.
    """
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    # Estimate background: large blur captures only low-freq illumination
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=50)

    # Divide original by background: removes shadows and yellowing
    # safe divide: multiply to scale, avoid division-by-zero
    gray_f = gray.astype(np.float32)
    bg_f   = bg.astype(np.float32)
    divided = np.clip((gray_f / (bg_f + 1e-6)) * 200.0, 0, 255).astype(np.uint8)

    # Stretch contrast: paper → 255, ink → 0
    # Use percentile clip for robustness (ignore 1% outliers at each end)
    p2  = int(np.percentile(divided, 2))
    p98 = int(np.percentile(divided, 98))
    if p98 > p2:
        divided = np.clip((divided.astype(np.int32) - p2) * 255 // (p98 - p2), 0, 255).astype(np.uint8)

    # Sharpen: unsharp mask (much better than simple kernel for fine text)
    blurred = cv2.GaussianBlur(divided, (0, 0), sigmaX=2)
    sharpened = cv2.addWeighted(divided, 1.5, blurred, -0.5, 0)

    return sharpened


def auto_crop_document(image_path):
    """
    Main function:
    1. Detect the 4 corners of a document (paper/form) in the photo
    2. Apply perspective transform (deskew + crop)
    3. Enhance to look like a professional B&W scanner
    """
    try:
        # --- Load image safely (handles Unicode paths) ---
        raw = np.frombuffer(open(image_path, "rb").read(), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)

        if image is None:
            return (False, "Cannot decode image.")

        orig = image.copy()
        orig_h, orig_w = orig.shape[:2]

        # --- Resize to 1200px tall for fast processing (keeps enough detail) ---
        PROC_H = 1200
        ratio = orig_h / PROC_H
        if ratio > 1:
            proc_w = int(orig_w / ratio)
            process_img = cv2.resize(image, (proc_w, PROC_H), interpolation=cv2.INTER_AREA)
        else:
            process_img = orig.copy()
            ratio = 1.0

        # --- Find document corners ---
        doc_cnt = find_document_contour(process_img)

        if doc_cnt is None:
            # No document found → assume the entire image is the document
            doc_cnt = np.array([
                [0, 0],
                [process_img.shape[1] - 1, 0],
                [process_img.shape[1] - 1, process_img.shape[0] - 1],
                [0, process_img.shape[0] - 1]
            ])

        # --- Scale corners back to original resolution ---
        doc_cnt = doc_cnt.reshape(4, 2).astype(np.float32) * ratio

        # --- Compute perspective-corrected dimensions ---
        rect = order_points(doc_cnt)
        tl, tr, br, bl = rect

        width_top    = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        height_left  = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)

        max_w = int(max(width_top, width_bottom))
        max_h = int(max(height_left, height_right))

        if max_w == 0 or max_h == 0:
            return (False, "Degenerate contour (zero width or height).")

        # Decide orientation: if it looks like A4 portrait or landscape
        # Clamp to A4 aspect ratio (1.414) to avoid extreme distortion
        a4_ratio = 1.4142
        if max_h >= max_w:
            max_h = int(max_w * a4_ratio)   # portrait
        else:
            max_h = int(max_w / a4_ratio)   # landscape

        dst = np.array([
            [0,         0        ],
            [max_w - 1, 0        ],
            [max_w - 1, max_h - 1],
            [0,         max_h - 1]
        ], dtype="float32")

        # --- Perspective transform ---
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (max_w, max_h))

        # --- Enhance like a scanner ---
        scanned = enhance_scan(warped)
        scanned_bgr = cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)

        # Save at high quality
        cv2.imencode('.jpg', scanned_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(image_path)
        return (True, f"Cropped {orig_w}x{orig_h} → {max_w}x{max_h}, scanner enhanced.")

    except Exception as e:
        import traceback
        print(f"[auto_crop_document] Error: {e}\n{traceback.format_exc()}")
        return (False, f"Error: {str(e)}")