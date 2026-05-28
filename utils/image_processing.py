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
            return (False, "OpenCV could not decode.")

        orig = image.copy()
        
        ratio = image.shape[0] / 800.0
        new_width = int(image.shape[1] / ratio)
        if ratio > 1:
            process_img = cv2.resize(image, (new_width, 800))
        else:
            process_img = orig.copy()
            ratio = 1.0

        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        img_area = process_img.shape[0] * process_img.shape[1]
        doc_cnt = None

        # METHOD 1: Auto Canny
        v = np.median(gray)
        lower = int(max(0, (1.0 - 0.33) * v))
        upper = int(min(255, (1.0 + 0.33) * v))
        edged = cv2.Canny(gray, lower, upper)
        
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        for c in cnts:
            peri = cv2.arcLength(c, True)
            for eps in np.linspace(0.02, 0.08, 5):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4 and cv2.contourArea(c) > img_area * 0.05: # Lowered to 5%
                    doc_cnt = approx
                    break
            if doc_cnt is not None:
                break
                
        # METHOD 2: Otsu Thresholding
        if doc_cnt is None:
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            for binary_img in [thresh, cv2.bitwise_not(thresh)]:
                cnts_thresh, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts_thresh = sorted(cnts_thresh, key=cv2.contourArea, reverse=True)[:5]
                for c in cnts_thresh:
                    peri = cv2.arcLength(c, True)
                    for eps in np.linspace(0.02, 0.08, 5):
                        approx = cv2.approxPolyDP(c, eps * peri, True)
                        if len(approx) == 4 and cv2.contourArea(c) > img_area * 0.05:
                            doc_cnt = approx
                            break
                    if doc_cnt is not None:
                        break
                if doc_cnt is not None:
                    break

        # METHOD 3: minAreaRect Fallback
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.05:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                doc_cnt = box.reshape(4, 1, 2)
                
        if doc_cnt is None:
            # Fallback: Enhance full image if really can't find anything
            alpha = 1.2
            beta = 10
            enhanced = cv2.convertScaleAbs(orig, alpha=alpha, beta=beta)
            cv2.imencode('.jpg', enhanced)[1].tofile(image_path)
            return (True, "Document corners not found. Enhanced original.")
            
        doc_cnt = doc_cnt.reshape(4, 2) * ratio
        rect = order_points(doc_cnt)
        (tl, tr, br, bl) = rect
        
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight_orig = max(int(heightA), int(heightB))
        
        # --- ENFORCE A4 PROPORTIONS ---
        if maxHeight_orig >= maxWidth:
            # Portrait A4: Height = Width * 1.414
            maxHeight = int(maxWidth * 1.414)
        else:
            # Landscape A4: Height = Width / 1.414
            maxHeight = int(maxWidth / 1.414)
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # --- ENHANCE TO LOOK EXACTLY LIKE A BLACK & WHITE SCANNER ---
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # Use Adaptive Thresholding to simulate a clean black & white scan
        # This completely removes shadows and gradients on the paper
        scanned = cv2.adaptiveThreshold(warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
        
        # Convert back to BGR so it saves as a normal color image format (though content is B&W)
        scanned_color = cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)
        
        cv2.imencode('.jpg', scanned_color)[1].tofile(image_path)
        return (True, "Document successfully cropped, deskewed, proportioned to A4, and converted to B&W scan.")
        
    except Exception as e:
        print(f"Auto crop error: {e}")
        return (False, f"Python error: {str(e)}")