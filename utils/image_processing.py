import cv2
import numpy as np
import traceback

class DocumentScanner:
    """
    Class xử lý ảnh scan tài liệu (Document Scanner) sử dụng OpenCV.
    """
    def __init__(self, debug=False):
        self.debug = debug

    def order_points(self, pts):
        """
        Sắp xếp 4 góc theo thứ tự: top-left, top-right, bottom-right, bottom-left
        """
        rect = np.zeros((4, 2), dtype="float32")
        # Tính tổng x + y
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]   # top-left có tổng nhỏ nhất
        rect[2] = pts[np.argmax(s)]   # bottom-right có tổng lớn nhất
        
        # Tính hiệu y - x
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right có hiệu nhỏ nhất
        rect[3] = pts[np.argmax(diff)]  # bottom-left có hiệu lớn nhất
        
        return rect

    def preprocess(self, image):
        """
        Tiền xử lý (Preprocessing):
        - Chuyển ảnh sang grayscale
        - Tăng độ tương phản (Contrast Enhancement)
        - Áp dụng Gaussian Blur để giảm nhiễu
        """
        # 1. Chuyển ảnh sang grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 2. Tăng độ tương phản (sử dụng CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # 3. Áp dụng Gaussian Blur để giảm nhiễu
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        return blurred

    def detect_edges(self, blurred_img):
        """
        Phát hiện biên (Edge Detection): Sử dụng Canny Edge Detection
        Kết hợp với Morphological Closing để nối liền các đường đứt nét.
        """
        edged = cv2.Canny(blurred_img, 75, 200)
        
        # Dùng phép toán hình thái học (Closing) để nối các nét đứt trên viền giấy
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        return edged

    def find_document_contour(self, edged, img_area):
        """
        Tìm contour và phát hiện trang tài liệu
        """
        # 1. Tìm viền ngoài cùng (RETR_EXTERNAL) để lờ đi các text/nhiễu bên trong giấy
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sắp xếp theo diện tích giảm dần
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        doc_cnt = None
        
        for c in cnts:
            # 2. Bỏ qua các contour quá nhỏ
            if cv2.contourArea(c) < img_area * 0.05:
                continue
                
            # 3. Xấp xỉ contour đó thành hình 4 cạnh (4 góc) bằng approxPolyDP
            peri = cv2.arcLength(c, True)
            
            # Thử nhiều hệ số epsilon để tăng tỷ lệ tìm thấy 4 góc
            for eps in np.linspace(0.01, 0.08, 10):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4:
                    doc_cnt = approx.reshape(4, 2)
                    break
                    
            if doc_cnt is not None:
                break
                
        # 4. Fallback: Nếu không tìm thấy contour 4 cạnh thì thử lấy bounding box của contour lớn nhất
        if doc_cnt is None and len(cnts) > 0:
            c = cnts[0]
            if cv2.contourArea(c) > img_area * 0.05:
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                doc_cnt = np.int32(box)

        return doc_cnt

    def perspective_transform(self, image, pts):
        """
        Căn chỉnh góc nhìn (Perspective Correction):
        Áp dụng warpPerspective để biến ảnh về góc nhìn trực diện (top-down view)
        """
        rect = self.order_points(pts)
        tl, tr, br, bl = rect

        # Bước 1: Tính kích thước trang sau khi sửa góc nhìn
        # width = max( khoảng cách giữa 2 góc trên, khoảng cách giữa 2 góc dưới )
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        width = max(int(widthA), int(widthB))

        # height = max( khoảng cách giữa 2 góc trái, khoảng cách giữa 2 góc phải )
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        height = max(int(heightA), int(heightB))

        if width == 0 or height == 0:
            return None

        # Bước 2: Định nghĩa tọa độ đích (hình chữ nhật hoàn hảo)
        dst_pts = np.array([
            [0, 0],                    # top-left
            [width-1, 0],              # top-right  
            [width-1, height-1],       # bottom-right
            [0, height-1]              # bottom-left
        ], dtype="float32")

        # Bước 3: Tính ma trận biến đổi
        M = cv2.getPerspectiveTransform(rect, dst_pts)
        
        # Bước 4: Warp ảnh → đồng thời crop luôn
        warped = cv2.warpPerspective(image, M, (width, height))
        
        return warped

    def post_process(self, warped):
        """
        Xử lý sau (Post-processing):
        Giữ nguyên màu sắc, ép nền giấy thành trắng tinh (Stretch Contrast), chữ nét và đậm.
        Đây là phương pháp thay thế ưu việt hơn Adaptive Threshold (tránh lỗi trắng xóa).
        """
        # Chuyển sang ảnh xám để phân tích cường độ sáng nền giấy
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # Tìm điểm tối nhất (chữ) và sáng nhất (nền giấy) - bỏ vài % nhiễu hai đầu
        black_point = np.percentile(gray, 3)
        white_point = np.percentile(gray, 95)
        
        warped_f = warped.astype(np.float32)
        diff = white_point - black_point
        if diff < 10:
            diff = 10
            
        # Kéo giãn dải màu (Stretch Contrast) cho cả 3 kênh màu BGR
        # Điểm sáng nhất thành 255 (trắng tinh), điểm tối nhất thành 0 (đen)
        adjusted = np.clip((warped_f - black_point) * (255.0 / diff), 0, 255).astype(np.uint8)
        
        # Làm nét chữ (Unsharp Mask)
        blurred = cv2.GaussianBlur(adjusted, (0, 0), sigmaX=3)
        final = cv2.addWeighted(adjusted, 1.5, blurred, -0.5, 0)
        
        return final

    def scan(self, image_path):
        """
        Hàm chính chạy luồng scan tài liệu. Input là đường dẫn file ảnh.
        Output là ảnh đã scan sạch sẽ (căn chỉnh + crop) lưu đè vào file gốc.
        """
        try:
            # 1. Đọc ảnh đầu vào
            raw = np.frombuffer(open(image_path, "rb").read(), dtype=np.uint8)
            orig = cv2.imdecode(raw, cv2.IMREAD_COLOR)

            if orig is None:
                return (False, "Không thể đọc file ảnh.")

            orig_h, orig_w = orig.shape[:2]
            img_area = orig_h * orig_w
            
            # Resize để xử lý logic tìm khung cho nhanh và ổn định
            ratio = orig_h / 800.0
            if ratio > 1:
                process_img = cv2.resize(orig, (int(orig_w / ratio), 800), interpolation=cv2.INTER_AREA)
            else:
                process_img = orig.copy()
                ratio = 1.0

            # 2. Tiền xử lý
            blurred = self.preprocess(process_img)
            
            # 3. Phát hiện biên
            edged = self.detect_edges(blurred)
            
            # 4. Tìm contour tài liệu
            proc_area = process_img.shape[0] * process_img.shape[1]
            doc_cnt = self.find_document_contour(edged, proc_area)
            
            if doc_cnt is None:
                # Xử lý trường hợp không tìm thấy tài liệu
                print("⚠️ Cảnh báo: Không tìm thấy tài liệu, lấy toàn bộ ảnh.")
                doc_cnt = np.array([
                    [0, 0],
                    [process_img.shape[1] - 1, 0],
                    [process_img.shape[1] - 1, process_img.shape[0] - 1],
                    [0, process_img.shape[0] - 1]
                ])

            # Đưa toạ độ về scale của ảnh gốc ban đầu
            doc_cnt = doc_cnt.astype(np.float32) * ratio
            
            # 5 & 6. Căn chỉnh góc nhìn và Crop
            warped = self.perspective_transform(orig, doc_cnt)
            
            if warped is None:
                return (False, "Lỗi tính toán kích thước ảnh crop.")

            # 7. Xử lý sau (Đen trắng + Nét chữ)
            final_img = self.post_process(warped)

            # Lưu ảnh đè lên file cũ
            cv2.imencode('.jpg', final_img, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(image_path)
            
            return (True, "Scan thành công.")
            
        except Exception as e:
            return (False, f"Lỗi xử lý ảnh: {str(e)}\n{traceback.format_exc()}")

# Interface function tương thích với code app hiện tại
def auto_crop_document(image_path):
    scanner = DocumentScanner()
    return scanner.scan(image_path)
