@echo off
chcp 65001 >nul
title CSKH Assistant - Demo Mode

if not exist ".venv\Scripts\activate.bat" (
    echo Chưa tìm thấy môi trường ảo .venv. Đang chạy cài đặt tự động...
    call setup_windows.bat
)

echo Đang khởi tạo dữ liệu mô phỏng và tạo mẫu báo cáo ca...
call .venv\Scripts\activate.bat
python app/main.py --demo
echo.
pause
