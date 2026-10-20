@echo off
chcp 65001 >nul
title Personal CSKH Reporting Assistant

:: Nếu chưa có môi trường ảo, tự động chạy cài đặt
if not exist ".venv\Scripts\activate.bat" (
    echo Chưa tìm thấy môi trường ảo .venv. Đang chạy cài đặt tự động lần đầu...
    call setup_windows.bat
)

echo Đang khởi động Personal CSKH Reporting Assistant...
call .venv\Scripts\activate.bat
python app/main.py

if %errorlevel% neq 0 (
    echo.
    echo [THÔNG BÁO] Ứng dụng đã thoát với mã lỗi %errorlevel%.
    pause
)
