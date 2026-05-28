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

        # Preprocessing: Grayscale and Bilateral Filter (keeps edges sharp)
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Edge detection
        edged = cv2.Canny(gray, 30, 200)
        
        # Morphological Closing to connect broken paper edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

        # RETR_EXTERNAL to ignore text inside the document
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        doc_cnt = None
        img_area = process_img.shape[0] * process_img.shape[1]
        
        for c in cnts:
            if cv2.contourArea(c) < img_area * 0.1:
                continue
                
            peri = cv2.arcLength(c, True)
            
            # 1. Try to approx directly
            for eps in np.linspace(0.01, 0.05, 5):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4:
                    doc_cnt = approx
                    break
            
            if doc_cnt is not None:
                break
                
            # 2. Try approx on Convex Hull (smoothes out jagged edges)
            hull = cv2.convexHull(c)
            hull_peri = cv2.arcLength(hull, True)
            for eps in np.linspace(0.01, 0.1, 10):
                approx = cv2.approxPolyDP(hull, eps * hull_peri, True)
                if len(approx) == 4:
                    doc_cnt = approx
                    break
                    
            if doc_cnt is not None:
                break
                
        # 3. Fallback: minAreaRect of the largest contour if it's large enough
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.1:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                doc_cnt = box.reshape(4, 1, 2)
                
        if doc_cnt is None:
            return False
            
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
        alpha = 1.1 # Contrast control
        beta = 5    # Brightness control
        enhanced = cv2.convertScaleAbs(warped, alpha=alpha, beta=beta)
        
        # Sharpen the image slightly
        kernel_sharp = np.array([[0, -0.5, 0], 
                                 [-0.5, 3,-0.5], 
                                 [0, -0.5, 0]])
        scanned = cv2.filter2D(enhanced, -1, kernel_sharp)
        
        cv2.imencode('.jpg', scanned)[1].tofile(image_path)
        return True
        
    except Exception as e:
        print(f"Auto crop error: {e}")
        return False