# Personal CSKH Reporting Assistant 🤖📊

> **Trợ lý báo cáo cá nhân chuyên nghiệp dành cho nhân viên Chăm sóc Khách hàng (CSKH).**  
> Tự động thu thập dữ liệu từ Discord và Meta Business Suite, phân loại hội thoại bằng Google Gemini AI, thống kê số liệu chuẩn xác và tạo báo cáo cuối ca đúng mẫu nội bộ.

---

## 🌟 Tính năng nổi bật

- **Giao diện Desktop hiện đại (PySide6)**: Thiết kế tối ưu cho Windows, giao diện tối (Dark mode) dịu mắt, thao tác nhanh và không bị treo giao diện (sử dụng đa luồng QThread).
- **Tuân thủ API chính thức 100%**:
  - **Discord**: Sử dụng Discord Bot API chính thức (`discord.py`), lọc chính xác theo Discord User ID của nhân viên, loại bỏ hoàn toàn tin nhắn của bot, webhook và đồng nghiệp.
  - **Meta Business Suite**: Sử dụng Meta Graph API (v20.0). Xử lý an toàn giới hạn tác giả của Page thông qua quy trình đối chiếu nhân viên (`unverified_agent`).
- **Phân loại thông minh bằng Google Gemini API**:
  - Trích xuất khách báo mạng chậm và tên thiết bị liên quan (ví dụ: `PC-04`, `May 12`).
  - Phân biệt khách đã thực sự test máy với khách chỉ hẹn sẽ test.
  - Nhận diện phản hồi khách hàng và các trường hợp chuyển cấp (Escalation) cho anh **Dương** hoặc anh **Tùng**.
  - Tự động lưu cache kết quả vào SQLite để tiết kiệm tối đa chi phí và quota AI.
- **Thống kê độc lập**: Tính toán số liệu bằng các phép đếm logic chặt chẽ trong database, không phụ thuộc vào suy đoán của mô hình ngôn ngữ lớn.
- **Mẫu báo cáo chuẩn nội bộ**:
  - Định dạng chuẩn xác cho **Ca 1**, **Ca 2** và **Ca 3** (tự động bổ sung mục checklist đóng ticket và phần **TỔNG KẾT NGÀY** cho Ca 3).
  - Bản xem trước trực quan thời gian thực, cho phép chỉnh sửa số liệu và xem bằng chứng (evidence) từng tin nhắn.
  - Sao chép vào bộ nhớ đệm (Clipboard) chỉ với 1 click hoặc xuất file `.txt`.
  - **An toàn tuyệt đối**: Báo cáo không bao giờ tự động gửi ra ngoài.
- **Bảo mật & Quyền riêng tư (Privacy & PII Sanitization)**:
  - Tự động che số điện thoại, email và username của khách hàng trước khi gửi dữ liệu lên AI.
  - Che dấu toàn bộ token và khóa bí mật trong log hệ thống.
  - Hỗ trợ lưu trữ thông tin an toàn qua Windows Credential Manager / file `.env`.
- **Chế độ DEMO tích hợp sẵn**: Cho phép trải nghiệm toàn bộ tính năng và xem mẫu báo cáo ngay lập tức mà chưa cần cấu hình API credentials thật.

---

## 🏗️ Cấu trúc dự án

```text
dungx/
├── app/
│   ├── main.py                     # Entry point (chạy GUI hoặc CLI demo)
│   ├── main_window.py              # Cửa sổ chính tích hợp 5 Tab nghiệp vụ
│   └── ui/
│       ├── dashboard_widget.py     # Tab 1: Dashboard tổng quan ca & kết nối
│       ├── report_widget.py        # Tab 2: Tạo, xem trước, sửa và xuất báo cáo
│       ├── checklist_widget.py     # Tab 3: Checklist cuối ca & lý do tồn đọng
│       ├── sync_widget.py          # Tab 4: Đồng bộ & đối chiếu tin nhắn thủ công
│       ├── settings_widget.py      # Tab 5: Cấu hình tài khoản & test kết nối
│       ├── styles.py               # Bảng màu và CSS giao diện hiện đại
│       └── workers.py              # Các luồng nền QThread chống treo ứng dụng
├── connectors/
│   ├── discord_connector.py        # Tích hợp Discord Bot API chính thức
│   ├── meta_connector.py           # Tích hợp Meta Graph API (Messenger/Page)
│   └── webhook_server.py           # Server nhận Webhook Meta & kiểm tra HMAC-SHA256
├── services/
│   ├── security_service.py         # Khử định danh PII, che giấu log & bảo mật key
│   ├── shift_service.py            # Tính toán ca làm, xử lý giờ VN & ca qua nửa đêm
│   ├── metrics_service.py          # Bộ đếm thống kê độc lập & trích xuất bằng chứng
│   ├── classification_service.py   # Phân loại hội thoại bằng Google Gemini SDK
│   ├── report_service.py           # Định dạng mẫu báo cáo chuẩn & xuất file
│   ├── sync_service.py             # Điều phối đồng bộ & chống trùng lặp dữ liệu
│   └── demo_service.py             # Bộ sinh dữ liệu mô phỏng thực tế (Demo Dataset)
├── database/
│   ├── connection.py               # Quản lý SQLite engine và SQLAlchemy session
│   └── cleanup.py                  # Dọn dẹp dữ liệu cũ theo thời hạn lưu trữ
├── models/
│   └── orm.py                      # Định nghĩa ORM 12 bảng cơ sở dữ liệu
├── schemas/
│   ├── shift_schema.py             # Schema ca làm và checklist
│   ├── message_schema.py           # Schema tin nhắn chuẩn hóa
│   ├── ai_schema.py                # Schema JSON phân loại có cấu trúc cho Gemini
│   └── report_schema.py            # Schema dữ liệu báo cáo
├── tests/                          # 26 Unit Tests toàn diện (100% Passed)
│   ├── conftest.py
│   ├── test_shift_service.py
│   ├── test_metrics_service.py
│   ├── test_report_service.py
│   ├── test_security_service.py
│   ├── test_gemini_classification.py
│   ├── test_connectors.py
│   └── test_database.py
├── docs/                           # Tài liệu hướng dẫn thiết lập chi tiết
│   ├── DISCORD_SETUP.md            # Hướng dẫn tạo Discord Bot & cấp Intent
│   ├── META_SETUP.md               # Hướng dẫn cấu hình Meta App & Page Token
│   ├── GEMINI_SETUP.md             # Hướng dẫn lấy Gemini API Key & bảo mật
│   ├── WINDOWS_RUN_GUIDE.md        # Hướng dẫn chạy chi tiết trên Windows
│   └── API_LIMITATIONS.md          # Phân tích giới hạn API & giải pháp an toàn
├── .env.example                    # File cấu hình mẫu với các placeholder
├── .gitignore                      # Bảo vệ không commit secrets, db, venv
├── requirements.txt                # Danh sách thư viện phụ thuộc
└── README.md                       # Tài liệu hướng dẫn sử dụng chính
```

---

## ⚡ Hướng dẫn cài đặt và khởi chạy nhanh trên Windows

### 1. Chuẩn bị môi trường
Yêu cầu cài đặt **Python 3.10+** (khuyên dùng Python 3.12).

Mở thư mục dự án trong PowerShell hoặc Command Prompt:

```powershell
# 1. Tạo môi trường ảo
python -m venv .venv

# 2. Kích hoạt môi trường ảo
.venv\Scripts\Activate.ps1

# 3. Nâng cấp pip và cài đặt thư viện
pip install -r requirements.txt
```

### 2. Thiết lập cấu hình ban đầu
Tạo file cấu hình cá nhân từ file mẫu:

```powershell
copy .env.example .env
```
Mở file `.env` và điền tên nhân viên của bạn. Các Token và API Key có thể nhập sau trực tiếp trên giao diện đồ họa.

---

## 🚀 Trải nghiệm ứng dụng

### Chạy Giao diện Desktop (PySide6 GUI)
```powershell
python app/main.py
```
> Trên giao diện, bạn có thể vào tab **⚡ Đồng Bộ & Đối Chiếu** và bấm nút **🧪 Nạp dữ liệu DEMO** để xem toàn bộ dữ liệu mẫu thực tế, sau đó chuyển sang tab **📝 Tạo Báo Cáo** để xem bản preview và bấm nút sao chép.

### Chạy thử chế độ DEMO trên dòng lệnh (CLI)
Nếu muốn kiểm tra nhanh mẫu báo cáo cho cả 3 ca mà không cần mở GUI:
```powershell
python app/main.py --demo
```

### Chạy bộ kiểm thử tự động (Unit Tests)
```powershell
pytest -v
```
Toàn bộ **26 test cases** kiểm tra:
- Không đếm tin bot/webhook vào phản hồi nhân viên.
- Phân biệt rõ tin gửi thông thường và reply trực tiếp khách.
- Xử lý ranh giới ca và ca 3 đi qua nửa đêm.
- Khử sạch số điện thoại và email khách hàng.
- Định dạng chuẩn mẫu báo cáo Ca 1, Ca 2 và Ca 3.

---

## 📋 Mẫu Báo Cáo Chuẩn Nội Bộ

### Ca 1 & Ca 2 (Mẫu chuẩn)
```text
[RP-CSKH] YYYY-MM-DD · Ca N · <Tên>

CHECKLIST
✅ Dọn tồn đọng / đọc bàn giao ca trước
✅ Check ticket pending, đóng nếu quá 12h
✅ Reply Discord + Fanpage SLA < 10 phút
✅ Reply hết comment Fanpage
✅ Reply comment 7 video TikTok/YT
✅ Xin feedback sau test máy

SỐ LIỆU
Tin nhắn đã reply: <số>
Báo cáo mạng chậm: <số> – máy: <tên máy | không có>
Khách test máy: <số> | Feedback nhận được: <số>
Ticket mở: <số> | Đóng: <số>
Escalate: <số> – <Dương/Tùng: lý do ngắn | không có>

BÀN GIAO CA SAU
Case pending: <mô tả ngắn | không có>
Khách cần follow up: <số> – <việc cần làm | không có>
```

### Ca 3 (Bổ sung checklist và Tổng Kết Ngày)
```text
...
✅ Đóng toàn bộ ticket chưa phản hồi trong ngày

...
TỔNG KẾT NGÀY
Feedback tích cực nhất: <ngắn gọn | không có>
Vấn đề cần anh Tùng xem: <mô tả | không có>
```

---

## 📚 Tài liệu chi tiết đính kèm

- [Hướng dẫn thiết lập Discord Bot API](docs/DISCORD_SETUP.md)
- [Hướng dẫn cấu hình Meta Business Suite / Graph API](docs/META_SETUP.md)
- [Hướng dẫn lấy và cấu hình Google Gemini API Key](docs/GEMINI_SETUP.md)
- [Hướng dẫn cài đặt và vận hành trên Windows](docs/WINDOWS_RUN_GUIDE.md)
- [Phân tích giới hạn kỹ thuật của API và cơ chế kiểm soát](docs/API_LIMITATIONS.md)
