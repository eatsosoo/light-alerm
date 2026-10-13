# Kiểm tra API — 13/10/2026

Đã chạy 35 test trong `tests/test_api.py`, tất cả thành công.

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Phạm vi

- Flask routes, xử lý JSON, kiểm tra đầu vào và mã HTTP.
- CRUD, không tìm thấy thiết bị, lọc line chính xác.
- Xác thực API key trên mọi route và khi lấy kết quả job.
- Gửi toàn bộ, theo line, line + OFFICE, tắt bằng GET/POST tương thích.
- Kết quả hoàn tất, một phần, thất bại, bị thay thế và bị hủy.
- Lệnh cũ được tắt trước khi gửi lệnh mới; READ_ALL không thay thế cảnh báo.
- Request ID, metadata, log của các job đồng thời không trộn lẫn.
- Giới hạn body, lịch sử hết hạn và thông báo lỗi database không lộ chi tiết nội bộ.
- Timeout kết nối thật của `asyncio.wait_for` với coroutine giả lập đang chờ: thông báo có IP/port và thời gian chờ, không ghi traceback cho lỗi mạng dự kiến.
- Từ chối kết nối và đóng ứng dụng khi đang kết nối: phân biệt thất bại với hủy chủ động.

Database được thay bằng repository trong bộ nhớ. Thiết bị được thay bằng adapter giả lập; các test transport thay `asyncio.open_connection` để không mở kết nối tới đèn thật. BackgroundWorker, AlarmService, RequestHistory và Flask dùng mã ứng dụng thực tế.

Chưa xác minh SQL Server thực tế, giao thức/phản hồi CH9120, kết nối LAN, giao diện hoặc bản build EXE. Kết quả test API không chứng minh thiết bị ngoài mạng có thể kết nối.

## Lỗi kết nối quan sát trong log vận hành

Log ngày 13/10 ghi nhận kết nối tới `10.30.146.2:6800` hết thời gian chờ sau 5 giây. `CancelledError` trong traceback là ngoại lệ bên trong khi `wait_for` hủy thao tác, sau đó được chuyển thành `TimeoutError`.

Đã bổ sung thông báo lỗi có địa chỉ và thời gian chờ. Lỗi mạng dự kiến được ghi ERROR ngắn gọn, giữ trạng thái yêu cầu thất bại; lỗi chương trình bất ngờ vẫn giữ traceback để chẩn đoán. Thay đổi này không tự khắc phục kết nối mạng hoặc cấu hình thiết bị.
