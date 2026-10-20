# HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY ỨNG DỤNG TRÊN WINDOWS

Ứng dụng **Personal CSKH Reporting Assistant** được thiết kế chạy trực tiếp trên Windows 10 và Windows 11 với giao diện đồ họa PySide6 (Qt6) hiện đại, mượt mà và trực quan.

---

## 1. Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10 hoặc Windows 11 (64-bit).
- **Python**: Phiên bản 3.10, 3.11 hoặc 3.12 (Khuyến nghị Python 3.12).
  - Tải tại [python.org/downloads/windows](https://www.python.org/downloads/windows/).
  - Khi cài đặt, hãy **tích chọn ô: "Add python.exe to PATH"**.
- **Visual Studio Code** (Tùy chọn nhưng khuyến nghị): Để thuận tiện chỉnh sửa và quản lý dự án.

---

## 2. Các bước cài đặt chi tiết

### Bước 1: Mở thư mục dự án
1. Mở thư mục `dungx` (hoặc thư mục dự án của bạn) trong VS Code.
2. Mở cửa sổ Terminal (phím tắt: `Ctrl + ~` hoặc menu `Terminal` -> `New Terminal`).

### Bước 2: Tạo môi trường ảo (Virtual Environment)
Trong cửa sổ PowerShell hoặc Command Prompt của VS Code, chạy lệnh:

```powershell
# Tạo môi trường ảo .venv
python -m venv .venv
```

### Bước 3: Kích hoạt môi trường ảo
Trên PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

> ⚠️ **Lưu ý nếu gặp lỗi Execution Policy trên PowerShell**:
> Nếu PowerShell báo lỗi script bị chặn (`running scripts is disabled on this system`), hãy mở PowerShell với quyền Administrator và chạy lệnh:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Hoặc kích hoạt trong Command Prompt (CMD) thông thường:
> ```cmd
> .venv\Scripts\activate.bat
> ```

### Bước 4: Cài đặt thư viện phụ thuộc
Sau khi terminal hiển thị tiền tố `(.venv)`, chạy lệnh:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 5: Cấu hình file môi trường (.env)
1. Tạo một bản sao từ file mẫu `.env.example` và đổi tên thành `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Mở file `.env` để điền thông tin nhân viên của bạn (hoặc bạn có thể điền trực tiếp trong giao diện cài đặt của ứng dụng):
   ```ini
   EMPLOYEE_NAME=Nguyễn Văn A
   APP_TIMEZONE=Asia/Ho_Chi_Minh
   ```

---

## 3. Chạy ứng dụng

### Cách 1: Chạy Giao diện Desktop (PySide6 GUI)
Khởi động ứng dụng đồ họa:

```powershell
python app/main.py
```

Cửa sổ ứng dụng **Personal CSKH Reporting Assistant** sẽ hiển thị với 5 tab chức năng:
1. **📊 Dashboard**: Xem thông tin ca hiện tại, tình trạng kết nối Discord / Meta / Gemini, và tổng số phản hồi.
2. **📝 Tạo Báo Cáo**: Bản xem trước báo cáo thời gian thực đúng mẫu chuẩn nội bộ, cho phép chỉnh sửa số liệu, xem bằng chứng và bấm nút sao chép vào bộ nhớ tạm (Clipboard).
3. **✅ Checklist Cuối Ca**: Đánh dấu các đầu việc bắt buộc kèm lý do nếu chưa xong.
4. **⚡ Đồng Bộ & Đối Chiếu**: Nạp dữ liệu từ bot hoặc nạp dữ liệu Demo, đối chiếu các trường hợp chưa xác minh.
5. **⚙️ Cấu Hình Tài Khoản**: Cấu hình token, API key và kiểm tra kết nối từng nền tảng.

### Cách 2: Chạy Thử nghiệm Chế độ DEMO (CLI)
Nếu bạn chưa có API credentials từ Discord hoặc Meta nhưng muốn xem thử ứng dụng tạo báo cáo cho cả 3 ca như thế nào:

```powershell
python app/main.py --demo
```

Ứng dụng sẽ nạp dữ liệu mô phỏng thực tế và in ra mẫu báo cáo chuẩn cho **Ca 1**, **Ca 2** và **Ca 3 (kèm Tổng Kết Ngày)**.

---

## 4. Chạy kiểm thử tự động (Unit Tests)

Dự án đi kèm bộ test toàn diện kiểm tra tất cả các quy tắc nghiệp vụ:

```powershell
pytest -v
```

Kết quả mong đợi: Toàn bộ 26/26 tests vượt qua (100% Passed) trong vòng ~1-2 giây.
