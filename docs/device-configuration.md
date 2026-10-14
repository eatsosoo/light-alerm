# Đối chiếu thiết bị theo PDF nhà cung cấp

Nguồn: `[2025-06-06]Instructions For Ethernet Type Sound-Light Alarm.pdf` trong thư mục này. Đã đọc toàn bộ 11 trang và kiểm tra hình ảnh các trang 7–10. Các điều chỉnh dưới đây dựa trên bảng 8-1, ví dụ 8-2 và hướng dẫn mạng của PDF.

## Tham số tạo lệnh (trang 9)

| Tham số | Giá trị thập phân | Byte HEX | Ý nghĩa |
| --- | --- | --- | --- |
| Flash | 1–5 | 01–05 | Tần số nháy; 5 nhanh nhất theo ví dụ trang 10 |
| Flash | 6 | 06 | Một nháy dài + một ngắn |
| Flash | 7 | 07 | Một nháy dài + hai ngắn |
| Volume | 0 | 00 | Tắt âm thanh |
| Volume | 1–8 | 01–08 | Mức âm lượng tăng dần |
| Play | 0 | 00 | Phát lặp một bài |
| Play | 1–16 | 01–10 | Phát một bài số lần tương ứng |
| Track | 1–250 | 01–FA | Chọn bài đã nạp |

PDF không mô tả Flash=0 trong lệnh ghi đủ bốn byte, nên bộ tạo mã chỉ cho chọn 1–7. Không dùng Volume=0 để hiểu là tắt đèn: giá trị này chỉ tắt âm thanh. Các lệnh HEX tùy chỉnh trong YAML vẫn được giữ; chức năng tắt hiện dùng lệnh TURN_OFF đã cấu hình.

Trang 6 xác định track theo thứ tự chép file vào thiết bị, không theo tên file. Track 1 là file được chép đầu tiên. Thiết bị nhận MP3 và WAV; số track thực tế còn phụ thuộc những file đã nạp.

## Frame lệnh (trang 8–10)

Lệnh ghi: địa chỉ thiết bị 01, chức năng 10, địa chỉ bắt đầu 001A, số byte dữ liệu 0004, bốn byte Flash/Volume/Play/Track, cuối cùng CRC16 little-endian. Đây là frame thiết bị có CRC truyền qua TCP; không tự thêm MBAP header của Modbus TCP chuẩn.

Hai ví dụ đã được đưa vào test:

- `0110001A000405080002A6CC`: nháy nhanh nhất, âm lượng 8, phát lặp bài 2.
- `0110001A000405000001670F`: nháy nhanh nhất và tắt âm thanh.

PDF ghi chức năng đọc 09 tại địa chỉ 001A; chức năng ghi 10. READ_ALL hiện tại là lệnh tùy chỉnh của cấu hình dự án, không tự thay bằng frame đọc mới vì PDF không đưa ví dụ request đầy đủ cho tên lệnh này. Phản hồi ví dụ cho lệnh ghi có dạng địa chỉ/chức năng/số byte/bốn byte dữ liệu/CRC. Ứng dụng vẫn lưu phản hồi HEX, chưa giải mã và đối chiếu ACK để xác nhận trạng thái vật lý.

## Khoảng cách gói lệnh (trang 8)

PDF yêu cầu khoảng nghỉ giữa các gói ít nhất 200 ms. Đã thêm PacketPacer dùng chung theo IP/port, áp dụng cả khi mở kết nối khác hoặc gửi TURN_OFF tự động. Các thiết bị khác nhau không chờ chung một bộ hẹn giờ. Bộ điều phối được giữ qua lần áp dụng cấu hình trong phiên chạy.

Vì ràng buộc này, duration=0 vẫn có khoảng nghỉ tối thiểu trước gói tắt kế tiếp. Test API dùng adapter giả lập không đo tốc độ mạng; test riêng PacketPacer xác minh thời gian gửi bằng writer giả.

## Vai trò TCP và timeout (trang 4, 5, 7)

Thiết bị có TCP Client (mặc định), TCP Server, UDP Client và UDP Server. Nhà cung cấp đề xuất thiết bị TCP Client, máy tính chạy TCP listener và gửi lệnh qua kết nối thiết bị đã mở tới máy tính.

Ứng dụng hiện triển khai chiều ngược lại: máy tính chủ động mở kết nối tới IP/port thiết bị. Do đó cần cấu hình thiết bị ở TCP Server bằng công cụ mạng của nhà cung cấp. Nếu giữ TCP Client mặc định, thiết bị có thể không lắng nghe tại IP/port mà ứng dụng đang gọi; đây là một nguyên nhân có thể giải thích timeout đã quan sát, chưa phải kết luận đã xác minh trên thiết bị thật.

HOST_IP/PORT/SSL trong YAML cấu hình HTTP API, không tạo listener TCP cho thiết bị. Muốn dùng thiết bị TCP Client theo kiến trúc PDF cần bổ sung listener riêng và quản lý kết nối thiết bị; chức năng này chưa được triển khai. Không tự sửa thông số mạng trên phần cứng hoặc các lệnh trong config.yaml thực tế.
