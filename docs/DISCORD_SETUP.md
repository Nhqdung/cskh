# HƯỚNG DẪN THIẾT LẬP DISCORD BOT (API CHÍNH THỨC)

Tài liệu này hướng dẫn chi tiết cách tạo Bot Discord, cấp quyền chính thức và lấy thông tin cấu hình cho ứng dụng **Personal CSKH Reporting Assistant**.

---

## 1. Nguyên tắc tuân thủ điều khoản Discord

- **Chỉ sử dụng Bot API chính thức**: Ứng dụng tuyệt đối không hỗ trợ hoặc sử dụng User Token (Self-bot) vì vi phạm nghiêm trọng Điều khoản Dịch vụ của Discord (ToS) và có nguy cơ bị khóa tài khoản vĩnh viễn.
- **Phân quyền tối thiểu (Least Privilege)**: Bot chỉ được cấp quyền đọc các server, kênh và ticket thread được chỉ định phục vụ công việc CSKH.

---

## 2. Các bước tạo Discord Bot

### Bước 1: Tạo Application trên Discord Developer Portal
1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Đăng nhập bằng tài khoản Discord của bạn.
3. Nhấp vào nút **New Application** ở góc trên bên phải.
4. Đặt tên ứng dụng (ví dụ: `Personal CSKH Reporter`) và bấm **Create**.

### Bước 2: Thiết lập Bot & Lấy Bot Token
1. Trong menu bên trái, chọn mục **Bot**.
2. Nhấp vào **Reset Token** (hoặc **Add Bot** nếu chưa có) để tạo Token mới.
3. Sao chép chuỗi Token này.
   > ⚠️ **CẢNH BÁO BẢO MẬT**: Bot Token tương đương với mật khẩu của Bot. Tuyệt đối không gửi Token này cho người khác, không commit vào GitHub. Ứng dụng sẽ lưu Token này an toàn trong file `.env` hoặc Windows Credential Manager.

### Bước 3: Bật Privileged Gateway Intents (Bắt buộc)
Để đọc được nội dung tin nhắn của khách hàng và đối chiếu câu hỏi mạng chậm / thiết bị test:
1. Cuộn xuống phần **Privileged Gateway Intents** trong trang **Bot**.
2. Bật công tắc:
   - **MESSAGE CONTENT INTENT** (Bắt buộc để đọc nội dung tin nhắn phục vụ phân loại).
   - **SERVER MEMBERS INTENT** (Khuyến nghị để kiểm tra vai trò).
3. Nhấp **Save Changes**.

---

## 3. Cấp quyền và Mời Bot vào Server làm việc

### Bước 1: Chọn Scopes
1. Trong menu bên trái, vào **OAuth2** -> **URL Generator**.
2. Trong phần **Scopes**, tích chọn:
   - `bot`

### Bước 2: Chọn Bot Permissions
Trong bảng **Bot Permissions** hiện ra bên dưới, tích chọn các quyền:
- **View Channels** (Xem kênh)
- **Read Message History** (Đọc lịch sử tin nhắn)
- **Send Messages** (Gửi tin nhắn – chỉ cần nếu bạn muốn bot gửi thông báo nội bộ)

### Bước 3: Mời Bot vào Server
1. Sao chép đường link URL sinh ra ở đáy trang.
2. Dán link vào trình duyệt, chọn Server CSKH mà bạn làm việc và có quyền quản trị/mời bot, sau đó bấm **Authorize**.

---

## 4. Lấy Discord User ID của bạn

Để ứng dụng phân biệt được tin nhắn nào do **chính bạn** gửi (không tính tin của đồng nghiệp hay bot khác):
1. Mở ứng dụng Discord trên máy tính hoặc web.
2. Vào **User Settings** (biểu tượng bánh răng) -> **Advanced** -> Bật **Developer Mode**.
3. Quay lại danh sách chat hoặc danh sách thành viên server, nhấp chuột phải vào ảnh đại diện/tên của chính bạn.
4. Chọn **Copy User ID** (chuỗi 18-19 số, ví dụ: `345678901234567890`).

---

## 5. Lấy Channel ID hoặc Ticket Category ID
1. Nhấp chuột phải vào kênh text hoặc forum ticket mà bạn phụ trách.
2. Chọn **Copy Channel ID**.
3. Nếu có nhiều kênh, bạn điền cách nhau bởi dấu phẩy trong mục cấu hình của ứng dụng.
