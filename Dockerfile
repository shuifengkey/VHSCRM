# Sử dụng Python 3.12 bản nhẹ
FROM python:3.12-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các gói hệ thống cơ bản
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements.txt
COPY requirements.txt .

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào
COPY . .

# Mở port 8080 (Cloud Run yêu cầu cổng này)
EXPOSE 8080

# Lệnh chạy ứng dụng
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
