# GIỚI HẠN API NỀN TẢNG VÀ PHƯƠNG ÁN XỬ LÝ AN TOÀN

Tài liệu này trình bày chi tiết các giới hạn kỹ thuật của các API chính thức (Discord Bot API, Meta Graph API) và giải pháp kiến trúc của ứng dụng **Personal CSKH Reporting Assistant** nhằm tuân thủ nguyên tắc: **Không tự bịa dữ liệu, không dùng kỹ thuật vượt quyền (hack/self-bot) và luôn đảm bảo sự kiểm soát của con người (Human-in-the-Loop)**.

---

## 1. Giới hạn của Discord Bot API

| Đặc điểm | Giới hạn kỹ thuật từ Discord | Giải pháp kiến trúc của ứng dụng |
| :--- | :--- | :--- |
| **Quyền đọc nội dung tin nhắn** | Discord yêu cầu **Message Content Intent** (Privileged Intent) để bot đọc được trường `content`. Nếu không bật, trường `content` trả về rỗng. | Ứng dụng kiểm tra và cảnh báo rõ ràng khi `Message Content Intent` chưa được bật trong Developer Portal. |
| **Phạm vi kênh truy cập** | Bot chỉ đọc được các kênh và ticket thread mà Bot được mời và cấp quyền `View Channel` & `Read Message History`. Bot không thể đọc tin nhắn Direct Message (DM) riêng của nhân viên. | Cung cấp danh sách `DISCORD_ALLOWED_CHANNEL_IDS` trong cấu hình. Nhân viên chỉ cần mời Bot vào các kênh / category ticket CSKH của server. |
| **Nhận diện tin nhắn phản hồi (Reply)** | Tin nhắn reply qua tính năng Reply của Discord luôn có trường `message.reference.message_id`. Tuy nhiên, nếu nhân viên chỉ gõ tin nhắn thường vào kênh mà không bấm Reply, Discord không có liên kết trực tiếp. | Ứng dụng phân biệt rõ: **Tổng tin nhắn nhân viên gửi**, **Số tin phản hồi trực tiếp khách (Reply)** và **Số cuộc hội thoại có phản hồi**. Không tự ý đồng nhất các chỉ số này. |
| **Chống đếm tin của đồng nghiệp & Bot** | Trong cùng một kênh ticket có thể có nhiều đồng nghiệp cùng trực và bot tự động gửi thông báo. | Bộ lọc của ứng dụng yêu cầu so khớp chính xác `DISCORD_USER_ID` của nhân viên và tự động loại bỏ mọi tin nhắn có cờ `is_bot=True` hoặc `webhook_id`. |

---

## 2. Giới hạn của Meta Graph API (Business Suite)

| Đặc điểm | Giới hạn kỹ thuật từ Meta | Giải pháp kiến trúc của ứng dụng |
| :--- | :--- | :--- |
| **Định danh nhân viên trả lời Page** | Khi nhân viên trực Page trả lời khách qua Meta Business Suite, Meta Graph API trả về tác giả là chính Fanpage (`from.id == Page_ID`). API không tiết lộ User ID Facebook cá nhân của nhân viên đó vì chính sách bảo mật của Meta. | **Ứng dụng tuyệt đối không tự bịa dữ liệu**. Mọi phản hồi từ Page được gắn nhãn `unverified_agent`. Tại tab **Đồng Bộ & Đối Chiếu**, nhân viên có danh sách trực quan để nhấp 1 nút xác nhận các phản hồi do chính mình phụ trách. Số liệu chưa xác minh không được tính vào báo cáo. |
| **Nhận Webhook sự kiện thời gian thực** | Meta Webhooks yêu cầu một Callback URL công khai sử dụng giao thức HTTPS hợp lệ. Một ứng dụng desktop chạy trên máy tính cá nhân không thể tự nhận webhook từ Internet nếu không có Domain/IP tĩnh hoặc đường hầm (tunnel). | Ứng dụng tích hợp sẵn Webhook server cục bộ hỗ trợ xác thực chữ ký HMAC-SHA256, đồng thời cung cấp hướng dẫn thiết lập qua Ngrok hoặc Cloudflare Tunnel. Nếu không dùng webhook, nhân viên có thể sử dụng cơ chế **Đồng bộ lịch sử ca (Graph API Backfill)** thông qua Page Access Token. |
| **Quyền truy cập hộp thư Messenger** | Cần quyền `pages_messaging` và quyền quản trị viên hoặc biên tập viên trên Trang. | Ứng dụng cung cấp nút kiểm tra quyền và hiển thị mã lỗi chi tiết từ Meta (ví dụ mã 190: token hết hạn, mã 200: thiếu quyền). |

---

## 3. Các nền tảng chưa tích hợp API tự động (TikTok, YouTube)

- **Thực tế nghiệp vụ**: Mục checklist *“Reply comment 7 video TikTok/YT”* hiện nay không có API kiểm tra phân quyền cá nhân khả thi trong phạm vi ứng dụng desktop nội bộ.
- **Quy tắc an toàn**: Ứng dụng **không bao giờ tự động tích xanh (✅)** mục này dựa trên phỏng đoán. Nhân viên phải chủ động xác nhận trạng thái (Hoàn thành hoặc Chưa hoàn thành kèm lý do như: *“Kênh chưa đăng video mới”*).

---

## 4. Tóm tắt quy trình kiểm soát của con người (Human-in-the-Loop)

```
Dữ liệu thô từ Discord / Meta
              │
              ▼
   Lớp lọc bảo mật & PII Scrubbing
              │
              ▼
    Phân loại thông minh (Gemini API)
              │
              ▼
   Bảng đối chiếu & Xác minh thủ công
   (Cho phép sửa số liệu, chọn lý do)
              │
              ▼
     Bản xem trước báo cáo chuẩn
              │
              ▼
Sao chép vào Clipboard để nhân viên tự gửi
(Tuyệt đối không tự động gửi ra ngoài)
```
