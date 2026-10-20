@echo off
chcp 65001 >nul
echo =======================================================
echo   CÀI ĐẶT PERSONAL CSKH REPORTING ASSISTANT TRÊN WINDOWS
echo =======================================================
echo.

:: 1. Kiểm tra Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trong hệ thống!
    echo Vui lòng cài đặt Python (3.10, 3.11 hoặc 3.12) từ https://www.python.org/
    echo Nhớ tích chọn ô "Add python.exe to PATH" khi cài đặt.
    echo.
    pause
    exit /b 1
)

echo [1/4] Đã tìm thấy Python:
python --version

:: 2. Khởi tạo môi trường ảo .venv
echo.
echo [2/4] Đang khởi tạo môi trường ảo .venv...
if not exist ".venv" (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [LỖI] Không thể tạo môi trường ảo .venv!
        pause
        exit /b 1
    )
    echo Đã tạo môi trường ảo .venv thành công.
) else (
    echo Môi trường ảo .venv đã tồn tại sẵn.
)

:: 3. Cài đặt các thư viện phụ thuộc
echo.
echo [3/4] Đang cài đặt các thư viện phụ thuộc từ requirements.txt...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [LỖI] Có lỗi trong quá trình cài đặt thư viện!
    pause
    exit /b 1
)

:: 4. Thiết lập file .env nếu chưa có
echo.
echo [4/4] Khởi tạo cấu hình môi trường...
if not exist ".env" (
    copy .env.example .env >nul
    echo Đã tạo file .env từ .env.example
) else (
    echo File .env đã tồn tại sẵn.
)

echo.
echo =======================================================
echo   CÀI ĐẶT HOÀN TẤT THÀNH CÔNG!
echo =======================================================
echo.
echo Bạn có thể:
echo 1. Nhấp đúp vào file 'run_app.bat' để mở ứng dụng giao diện Desktop.
echo 2. Nhấp đúp vào file 'run_demo.bat' để chạy thử chế độ Demo dữ liệu mẫu.
echo.
pause
