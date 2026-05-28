import cv2
import numpy as np

def order_points(pts):
    # Khởi tạo ma trận tọa độ, pts chứa 4 điểm
    rect = np.zeros((4, 2), dtype="float32")

    # Điểm trên cùng bên trái có tổng tọa độ (x+y) nhỏ nhất
    # Điểm dưới cùng bên phải có tổng tọa độ (x+y) lớn nhất
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Điểm trên cùng bên phải có hiệu (y-x) nhỏ nhất (do y nhỏ, x lớn)
    # Điểm dưới cùng bên trái có hiệu (y-x) lớn nhất (do y lớn, x nhỏ)
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def auto_crop_document(image_path):
    """
    Nhận đường dẫn ảnh, sử dụng OpenCV để tìm và nắn thẳng tài liệu.
    Ghi đè file ảnh mới sau khi crop thành công. Trả về True/False.
    """
    try:
        # Đọc ảnh với hỗ trợ unicode path nếu cần
        # Vì filepath có thể chứa ký tự lạ, dùng np.fromfile
        stream = open(image_path, "rb")
        bytes_img = bytearray(stream.read())
        numpyarray = np.asarray(bytes_img, dtype=np.uint8)
        image = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
        stream.close()

        if image is None:
            return False

        orig = image.copy()
        
        # Để tăng tốc và nhận diện tốt hơn, thu nhỏ ảnh về kích thước xử lý (vd height = 800)
        ratio = image.shape[0] / 800.0
        new_width = int(image.shape[1] / ratio)
        if ratio > 1:
            process_img = cv2.resize(image, (new_width, 800))
        else:
            process_img = orig.copy()
            ratio = 1.0

        # Chuyển xám, làm mờ và tìm cạnh
        gray = cv2.cvtColor(process_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)

        # Tìm các đường viền
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        doc_cnt = None
        
        # Duyệt qua các contour lớn nhất
        for c in cnts:
            # Xấp xỉ đa giác
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            # Nếu tìm thấy đa giác 4 cạnh, khả năng rất cao là tờ giấy
            if len(approx) == 4:
                # Kiểm tra xem diện tích có đủ lớn so với khung hình không
                area = cv2.contourArea(c)
                img_area = process_img.shape[0] * process_img.shape[1]
                if area > img_area * 0.15: # Tối thiểu 15% diện tích hình
                    doc_cnt = approx
                    break
                    
        # Nếu không tìm thấy contour nào hợp lệ, giữ nguyên ảnh gốc
        if doc_cnt is None:
            return False
            
        # Nhân lại toạ độ 4 điểm với tỷ lệ zoom ban đầu
        doc_cnt = doc_cnt.reshape(4, 2) * ratio
        
        # Nắn ảnh (Perspective Transform)
        rect = order_points(doc_cnt)
        (tl, tr, br, bl) = rect
        
        # Tính chiều rộng tờ giấy mới
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        # Tính chiều dài tờ giấy mới
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # Toạ độ điểm đích (hình chữ nhật hoàn hảo)
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # Chuyển đổi perspective
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # Áp dụng thêm filter để chữ rõ hơn nếu cần (Optional)
        # Bỏ qua vì người dùng thường muốn giữ màu gốc
        
        # Ghi đè file
        cv2.imencode('.jpg', warped)[1].tofile(image_path)
        return True
        
    except Exception as e:
        print(f"Auto crop error: {e}")
        return False
