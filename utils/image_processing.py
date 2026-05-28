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
            return (False, "Cannot decode image.")

        orig = image.copy()
        
        # Resize for faster processing
        ratio = image.shape[0] / 800.0
        new_width = int(image.shape[1] / ratio)
        if ratio > 1:
            process_img = cv2.resize(image, (new_width, 800))
        else:
            process_img = orig.copy()
            ratio = 1.0

        # --- STEP 1: ROBUST PAPER DETECTION ---
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        
        # Blur to remove noise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use Otsu's thresholding to determine optimal Canny thresholds
        high_thresh, thresh_im = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        low_thresh = 0.5 * high_thresh
        edged = cv2.Canny(gray, low_thresh, high_thresh)
        
        # Dilate edges to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged = cv2.dilate(edged, kernel, iterations=2)
        edged = cv2.erode(edged, kernel, iterations=1)

        # Find contours
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
                    doc_cnt = approx
                    break
            if doc_cnt is not None:
                break
                
        # Fallback: minAreaRect for the largest contour if it's significant
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.05:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                doc_cnt = box.reshape(4, 1, 2)
                
        if doc_cnt is None:
            doc_cnt = np.array([[0,0], [process_img.shape[1],0], [process_img.shape[1],process_img.shape[0]], [0,process_img.shape[0]]])
            
        doc_cnt = doc_cnt.reshape(4, 2) * ratio
        rect = order_points(doc_cnt)
        (tl, tr, br, bl) = rect
        
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight_orig = max(int(heightA), int(heightB))
        
        if maxHeight_orig >= maxWidth:
            maxHeight = int(maxWidth * 1.414)
        else:
            maxHeight = int(maxWidth / 1.414)
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # --- STEP 2: CAMSCANNER "MAGIC COLOR" EFFECT (LÀM RÕ CHỮ, TRẮNG GIẤY) ---
        # Convert to grayscale for clear text contrast
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # 1. Estimate background illumination using a large median blur (acts like a low-pass filter)
        bg = cv2.medianBlur(warped_gray, 51)
        
        # 2. Divide original by background to remove shadows and equalize lighting
        # cv2.divide requires float32 or scale factor
        result = 255 - cv2.absdiff(warped_gray, bg)
        
        # 3. Normalize to stretch contrast (makes background pure white, text pure black)
        result = cv2.normalize(result, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        
        # 4. Apply a slight Sharpening kernel to make handwriting/text crispy
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        scanned = cv2.filter2D(result, -1, kernel)
        
        # Convert back to BGR for saving
        scanned_color = cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)
        
        cv2.imencode('.jpg', scanned_color)[1].tofile(image_path)
        return (True, "Cropped and enhanced with Magic Scanner effect.")
        
    except Exception as e:
        print(f"Auto crop error: {e}")
        return (False, f"Python error: {str(e)}")