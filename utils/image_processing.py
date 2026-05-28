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

def auto_crop_document(image_path):
    try:
        stream = open(image_path, "rb")
        bytes_img = bytearray(stream.read())
        numpyarray = np.asarray(bytes_img, dtype=np.uint8)
        image = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
        stream.close()

        if image is None:
            return False

        orig = image.copy()
        
        # Resize for processing
        ratio = image.shape[0] / 800.0
        new_width = int(image.shape[1] / ratio)
        if ratio > 1:
            process_img = cv2.resize(image, (new_width, 800))
        else:
            process_img = orig.copy()
            ratio = 1.0

        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 1. Use static threshold 75, 200 which works perfectly for subtle paper edges
        edged = cv2.Canny(gray, 75, 200)

        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]
        
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(c)
                if area > img_area * 0.15:
                    doc_cnt = approx
                    break
                    
        # Fallback 1: Try slightly larger epsilon if strict one failed
        if doc_cnt is None:
            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.05 * peri, True)
                if len(approx) == 4:
                    area = cv2.contourArea(c)
                    if area > img_area * 0.15:
                        doc_cnt = approx
                        break

        # Fallback 2: minAreaRect of largest contour
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.15:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                doc_cnt = box.reshape(4, 1, 2)
                
        # Fallback 3: Global Convex Hull of all significant text boxes
        if doc_cnt is None:
            all_pts = []
            for c in cnts:
                if cv2.contourArea(c) > img_area * 0.005: # At least 0.5% of image (a block of text)
                    all_pts.extend(c)
            if len(all_pts) > 0:
                all_pts = np.array(all_pts)
                hull = cv2.convexHull(all_pts)
                if cv2.contourArea(hull) > img_area * 0.2:
                    rect = cv2.minAreaRect(hull)
                    box = cv2.boxPoints(rect)
                    box = np.int32(box)
                    doc_cnt = box.reshape(4, 1, 2)
                
        if doc_cnt is None:
            # Fallback: Geometric crop failed. Just enhance the original image.
            alpha = 1.2
            beta = 10
            enhanced = cv2.convertScaleAbs(orig, alpha=alpha, beta=beta)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            scanned = cv2.filter2D(enhanced, -1, kernel)
            cv2.imencode('.jpg', scanned)[1].tofile(image_path)
            return True
            
        doc_cnt = doc_cnt.reshape(4, 2) * ratio
        rect = order_points(doc_cnt)
        (tl, tr, br, bl) = rect
        
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # --- ENHANCE TO LOOK LIKE SCANNED DOCUMENT ---
        alpha = 1.2
        beta = 10
        enhanced = cv2.convertScaleAbs(warped, alpha=alpha, beta=beta)
        kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
        scanned = cv2.filter2D(enhanced, -1, kernel)
        
        cv2.imencode('.jpg', scanned)[1].tofile(image_path)
        return True
        
    except Exception as e:
        print(f"Auto crop error: {e}")
        return False