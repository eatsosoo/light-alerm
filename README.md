# Light Alarm Control System

Ứng dụng desktop và HTTP API để quản lý, điều khiển đèn cảnh báo CH9120 qua TCP. Có thể gửi lệnh cho các thiết bị đang hiển thị trên giao diện, một line chính xác, toàn bộ thiết bị hoặc một line kèm thiết bị OFFICE.

## Cài đặt và chạy

Yêu cầu Python 3.11 trở lên, Tkinter cho giao diện desktop và SQL Server ODBC Driver phù hợp với máy chạy ứng dụng.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.yaml.example config.yaml
```

Điền thông tin database, địa chỉ server, port và các lệnh HEX trong `config.yaml`, sau đó chạy:

```powershell
python app.py
```

Các chế độ khác:

```powershell
python app.py --config D:\Config\light-alarm.yaml
python app.py --headless
```

Mặc định cấu hình được tìm cạnh `app.py`, hoặc cạnh file `.exe` khi đóng gói. Có thể đặt biến môi trường `LIGHT_ALARM_CONFIG` thay cho `--config`. Đường dẫn chứng chỉ SSL tương đối được tính từ thư mục chứa cấu hình. Log được lưu trong thư mục `logs` cạnh cấu hình và giữ 14 ngày.

Nếu đã có `config.yaml`, có thể tiếp tục sử dụng. `SSL.ENABLED` mặc định là `false`; `PORT` mặc định là `5000`. Cấu hình mẫu mới dùng port `7000`. Các giá trị HEX cần được đặt trong dấu nháy để YAML đọc thành chuỗi.

## Tổ chức mã nguồn

```text
app.py                          Khởi tạo và đóng ứng dụng
light_alarm/
  config.py                     Đọc, kiểm tra cấu hình
  logging_setup.py              Log theo ngày
  runtime.py                    Ghép dependency và adapter cho desktop
  api/
    __init__.py                 Flask app factory, xác thực, xử lý lỗi
    routes.py                   Request, response và endpoint
  repositories/
    device_repository.py        Truy vấn SQL và vòng đời kết nối
  services/
    alarm_service.py            Chọn mục tiêu và điều phối cảnh báo
    background_worker.py        Event loop dùng chung và kết quả job
  devices/
    ch9120_client.py            Kết nối TCP và gửi lệnh
    protocol.py                 Tạo frame HEX, tính CRC-16
  ui/
    main_window.py              Cửa sổ và style
    device_tab.py               Danh sách, bộ lọc và lệnh điều khiển
    log_tab.py                  Đọc log tăng dần
tools/
  crc16_cli.py                   Công cụ tạo lệnh
  google_form.py                 Tiện ích độc lập, chỉ chạy khi gọi CLI
docs/                           Tài liệu nhà cung cấp và ghi chú kiến trúc
```

API và desktop dùng chung `AlarmService` và một event loop. SQL chạy qua repository; tải dữ liệu trên desktop được thực hiện ngoài luồng Tkinter. Không có kết nối database, TCP hay server được mở chỉ bởi thao tác import module.

## Hành vi điều khiển

- Line được chọn bằng so sánh chính xác; chuỗi `1` không khớp line `10`.
- Lệnh trên giao diện tác động toàn bộ thiết bị đang hiển thị sau khi lọc, không chỉ hàng đang chọn.
- `duration` là số nguyên không âm, tính theo giây; bỏ trống dùng 5 giây. Giá trị `0` không bị đổi thành mặc định.
- Với lệnh cảnh báo, thời gian được tính từ lúc gửi lệnh bật. Hết thời gian, hệ thống gửi `TURN_OFF`.
- Lệnh mới cho cùng IP/port thay thế lệnh cũ; bước dọn dẹp lệnh cũ hoàn tất trước khi gửi lệnh mới.
- `TURN_OFF` gửi một lần. `READ_ALL` đọc một lần, không tạo bộ hẹn giờ tắt và không thay thế cảnh báo đang chạy.
- Luồng device-office xử lý toàn bộ thiết bị của line và OFFICE, loại trùng theo IP/port. Cần khai báo `CH9120.COMMANDS.OFFICE` để bật cảnh báo OFFICE; tắt không cần khóa này.
- Kết quả thành công phản ánh việc gửi TCP và hoàn tất thao tác theo lịch; phản hồi của thiết bị được lưu nguyên dạng HEX, chưa giải mã để xác nhận trạng thái phần cứng. Không nhận được phản hồi sẽ ghi cảnh báo vào log.

## HTTP API

Prefix của tất cả endpoint là `/ch9120`. Có thể cấu hình `API_KEY` hoặc biến môi trường `LIGHT_ALARM_API_KEY`; client khi đó gửi header `X-API-Key`. Biến môi trường được ưu tiên. Nếu để trống cả hai, API tiếp tục cho phép truy cập không cần khóa. API không tự bật CORS cho mọi origin.

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| POST | `/send-command/all` | Gửi cho toàn bộ thiết bị |
| POST | `/send-command/line` | Gửi cho một line chính xác |
| POST | `/send-command/device-office` | Gửi cho line và OFFICE |
| POST | `/send-command/turn-off-all/<line>` | Tắt line và OFFICE |
| GET | `/jobs/<job_id>` | Xem tiến độ và kết quả |
| POST | `/create_device` | Thêm thiết bị |
| PUT | `/update_device/<keyid>` | Sửa thiết bị |
| DELETE | `/delete_device/<keyid>` | Xóa thiết bị |
| GET | `/get_device/<keyid>` | Lấy một thiết bị |
| GET | `/get_devices_by_line/<line>` | Lấy thiết bị theo line |
| GET | `/get-all-devices` | Lấy toàn bộ thiết bị |
| GET | `/get-all-lines` | Lấy các line |

Body gửi lệnh theo line:

```json
{"line": "LINE_1", "mode": "TQC1", "duration": 5}
```

Các endpoint gửi lệnh trả HTTP `202` sau khi nhận yêu cầu, với `status: accepted`, `job_id` và `status_url`. Client cần đọc `status_url` để biết kết quả. Job có trạng thái `running`, `completed`, `partial`, `failed` hoặc `cancelled`; kết quả chứa số thiết bị `success`, `failure`, `superseded` và chi tiết từng thiết bị.

Job được lưu trong bộ nhớ, mất khi khởi động lại ứng dụng. Hệ thống giữ các job đang chạy và tối đa 200 job đã kết thúc, dọn khi nhận job mới. Một job bị thay thế toàn bộ cũng trả `partial`; chi tiết có `superseded`.

Các endpoint CRUD nhận `station_name`, `ip`, `port`, `line`, `remark` và `user_code_created` hoặc `user_code_updated` tùy thao tác. Mã người dùng chấp nhận chuỗi hoặc số nguyên. Thiết bị không tồn tại trả `404`; dữ liệu không hợp lệ trả `400`.

GET cho `/send-command/turn-off-all/<line>` vẫn được giữ để tương thích client cũ; client mới nên dùng POST.

## Các thay đổi cần lưu ý khi nâng cấp

- Các module `configs`, `controllers`, `models`, `routes`, `services`, `ui` ở thư mục gốc được thay bằng package `light_alarm`. Code Python bên ngoài import các đường dẫn cũ cần cập nhật.
- API gửi lệnh chuyển từ `200/success` sang `202/accepted`, kèm endpoint lấy kết quả.
- `get_device` trả một object thay vì danh sách; thao tác thêm trả `201`, sửa/xóa không tồn tại trả `404`.
- API lọc line dùng kết quả chính xác; tìm kiếm gần đúng vẫn có trên giao diện.
- CORS mở cho mọi origin đã được bỏ; client trình duyệt khác origin cần cấu hình proxy cùng origin hoặc bổ sung danh sách origin được phép theo môi trường triển khai.
- `requests` chỉ còn phục vụ công cụ Google Form; ứng dụng chính không gọi HTTP tới chính nó.

## Công cụ CRC

```powershell
python -m tools.crc16_cli --f 01 --v 01 --p 00 --t 01
```

Frame được tạo theo định dạng CH9120 đã có trong dự án, kèm CRC-16 Modbus little-endian. Tham khảo tài liệu nhà cung cấp trong `docs` khi xác định byte điều khiển. Chỉ thao tác tính CRC; công cụ không kết nối thiết bị.

## Công cụ Google Form

Tiện ích độc lập nhận URL và file JSON dữ liệu qua tham số. Không còn URL hoặc nội dung form cố định trong mã; mặc định gửi một lần. Import module không gửi yêu cầu.

```powershell
python -m tools.google_form --url "<formResponse URL>" --data "form-data.json" --count 1
```

## Đóng gói Windows

```powershell
pyinstaller app.spec
```

Đặt `config.yaml` cạnh `dist/app.exe`; nếu bật SSL, triển khai thêm file chứng chỉ và private key theo đường dẫn cấu hình. PyInstaller thu thập package Python qua import; cấu hình mẫu được kèm trong bundle, còn cấu hình thực tế được đọc từ file bên ngoài.

## Trạng thái xác minh

Đợt refactor này chưa chạy test, chưa khởi động ứng dụng, chưa build `.exe`, chưa kết nối SQL và chưa gửi lệnh thiết bị theo yêu cầu của người dùng. Cần xác minh trên môi trường vận hành trước khi sử dụng bản refactor.
