# HƯỚNG DẪN CẤU HÌNH META BUSINESS SUITE / GRAPH API

Tài liệu này hướng dẫn cách cấu hình Meta App, cấp quyền Page Access Token chính thức và thiết lập Webhooks phục vụ thu thập tin nhắn Messenger và bình luận trên Fanpage.

---

## 1. Nguyên tắc tuân thủ điều khoản Meta (Facebook)

- **Chỉ sử dụng Meta Graph API chính thức**: Ứng dụng không sử dụng cookie phiên, tiện ích giả lập trình duyệt hoặc password cá nhân để cào dữ liệu trái phép.
- **Giới hạn API về danh tính nhân viên trực Page**:
  - Khi một nhân viên trả lời khách hàng qua hộp thư Meta Business Suite, Meta Graph API mặc định gán người gửi là đối tượng **Page** (`from.id == Page_ID`), không trả về User ID cá nhân của nhân viên trực trừ khi hệ thống doanh nghiệp sử dụng giải pháp Live Chat Extension chuyên biệt.
  - **Cơ chế xử lý an toàn của ứng dụng**: Mọi phản hồi từ Page được đánh dấu là `unverified_agent` (Chưa xác minh nhân viên), hiển thị trong mục **Đồng Bộ & Đối Chiếu** để bạn chỉ cần nhấp một nút xác nhận các phản hồi do chính mình xử lý. Ứng dụng **không tự ý cộng dồn** vào số liệu xác minh khi chưa được đối chiếu.

---

## 2. Các bước tạo Meta App & Lấy Page Access Token

### Bước 1: Đăng ký tài khoản Meta for Developers
1. Truy cập [Meta for Developers](https://developers.facebook.com/).
2. Đăng nhập bằng tài khoản Facebook quản lý Page CSKH.

### Bước 2: Tạo App mới
1. Nhấp vào **My Apps** -> **Create App**.
2. Chọn mục đích sử dụng: **Business** (Doanh nghiệp) hoặc **Other** -> Bấm **Next**.
3. Điền tên App (ví dụ: `CSKH Personal Assistant`) và email liên hệ.
4. Bấm **Create App**.

### Bước 3: Lấy Meta App ID và App Secret
1. Trong thanh menu bên trái, vào **App Settings** -> **Basic**.
2. Sao chép **App ID** (`META_APP_ID`).
3. Nhấp **Show** bên cạnh **App Secret** và sao chép (`META_APP_SECRET`).

### Bước 4: Cấp quyền và lấy Page Access Token qua Graph API Explorer
1. Truy cập [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Chọn App của bạn tại ô **Meta App**.
3. Tại ô **User or Page**, chọn **Get Page Access Token**, sau đó chọn Fanpage bạn đang trực.
4. Trong mục **Permissions**, bấm **Add a Permission** và cấp các quyền sau:
   - `pages_read_engagement` (Đọc tương tác, bài viết, bình luận Fanpage)
   - `pages_manage_metadata` (Đọc cấu hình và danh sách tin)
   - `pages_messaging` (Đọc và nhận tin nhắn Messenger của Page)
5. Nhấp nút **Generate Access Token**.
6. Đồng ý với các hộp thoại xác nhận quyền của Facebook.
7. Chuỗi token sinh ra chính là **Page Access Token**.

> 💡 **Mẹo**: Để token không bị hết hạn sau vài giờ, bạn hãy chuyển đổi token ngắn hạn thành Long-lived Page Access Token bằng công cụ **Access Token Tool** của Meta:
> `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}`

---

## 3. Lấy Page ID
1. Mở Fanpage của bạn trên Facebook.
2. Vào phần **Giới thiệu (About)** -> Cuộn xuống đáy trang để thấy mục **ID Trang (Page ID)** (chuỗi số, ví dụ: `102938475610293`).
3. Hoặc gọi lệnh đơn giản trong Graph API Explorer: `GET /me?fields=id,name`.

---

## 4. Thiết lập Webhooks cho Sự kiện Thời gian thực (Tùy chọn)

Nếu bạn muốn ứng dụng cập nhật tin nhắn Messenger ngay lập tức mà không cần bấm nút quét lịch sử:

1. **Khởi chạy Webhook Server**: Ứng dụng tích hợp sẵn Webhook Server tại cổng `8080` (`META_WEBHOOK_PORT`).
2. **Tạo Public HTTPS Tunnel**:
   - Meta bắt buộc địa chỉ Callback URL phải là HTTPS công khai.
   - Bạn có thể dùng [ngrok](https://ngrok.com/) hoặc Cloudflare Tunnel:
     ```bash
     ngrok http 8080
     ```
   - Nhận URL dạng: `https://abc-123.ngrok-free.app`
3. **Cấu hình trên Meta Developer Portal**:
   - Vào App của bạn -> chọn sản phẩm **Webhooks** -> Chọn Page.
   - Nhập Callback URL: `https://abc-123.ngrok-free.app/webhook`
   - Nhập Verify Token: Giá trị bạn đã điền trong `.env` (`META_WEBHOOK_VERIFY_TOKEN`).
   - Chọn đăng ký các trường: `messages`, `messaging_postbacks`, `feed`.
