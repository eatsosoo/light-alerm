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
    config_document.py            Đọc/lưu YAML, kiểm tra xung đột và tạo bản sao
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
    request_history.py          Lịch sử yêu cầu và liên kết log theo Request ID
  devices/
    ch9120_client.py            Kết nối TCP và gửi lệnh
    protocol.py                 Tạo frame HEX, tính CRC-16
  ui/
    main_window.py              Cửa sổ và style
    device_tab.py               Danh sách, bộ lọc và lệnh điều khiển
    log_tab.py                  Đọc log tăng dần
    request_log_tab.py          Bảng trạng thái và log từng yêu cầu
    theme.py                    Màu sắc, nút, ô nhập và thẻ thống kê dùng chung
    widgets.py                  Nút và ô nhập bo góc, tab phẳng, thanh cuộn tự ẩn
    settings_tab.py             Sửa cấu hình YAML và danh sách lệnh trên UI
    network_config_tab.py       Tìm, đọc và cấu hình module mạng CH9120 qua UDP
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

Các endpoint gửi lệnh trả HTTP `202` sau khi nhận yêu cầu, với `status: accepted`, `job_id` và `status_url`. Client cần đọc `status_url` để biết kết quả. Job có trạng thái `queued`, `running`, `completed`, `partial`, `failed`, `cancelled` hoặc `superseded`; kết quả chứa số thiết bị `success`, `failure`, `superseded` và chi tiết từng thiết bị.

Job được lưu trong bộ nhớ, mất khi khởi động lại ứng dụng. Hệ thống giữ các job đang chạy và tối đa 200 job đã kết thúc. Một job bị thay thế toàn bộ trả trạng thái `superseded`.

Các endpoint CRUD nhận `station_name`, `ip`, `port`, `line`, `remark` và `user_code_created` hoặc `user_code_updated` tùy thao tác. Mã người dùng chấp nhận chuỗi hoặc số nguyên. Thiết bị không tồn tại trả `404`; dữ liệu không hợp lệ trả `400`.

GET cho `/send-command/turn-off-all/<line>` vẫn được giữ để tương thích client cũ; client mới nên dùng POST.

## Bảng theo dõi yêu cầu

Tab `Yêu cầu` hiển thị mỗi lần gửi lệnh từ API hoặc desktop thành một dòng: thời gian, Request ID, nguồn, lệnh, phạm vi line, số thiết bị, trạng thái và số lượng gửi thành công / lỗi / bị thay thế. Danh sách tự cập nhật mỗi 500 ms, hỗ trợ tìm theo mã yêu cầu, lệnh, line, nguồn và lọc theo trạng thái. Thẻ thống kê hiển thị tổng yêu cầu trong lịch sử, số đang xử lý và số lỗi / một phần.

Chọn một dòng để xem Request ID đầy đủ, thời điểm bắt đầu/kết thúc, thời gian đã chạy, kết quả từng thiết bị và log chỉ thuộc yêu cầu đó. Phần chi tiết có hai tab `Kết quả thiết bị` và `Log của yêu cầu`; yêu cầu chưa có kết quả mở tab log trước. Nút `Sao chép mã` sao chép mã đầy đủ; `Sao chép log` sao chép log kèm Request ID. Mã này trùng với `job_id` trả về từ API và mã rút gọn xuất hiện trên tab `Điều khiển`.

Trạng thái gồm chờ xử lý, đang chạy, hoàn tất, một phần, lỗi, đã hủy và đã thay thế. Kết quả thiết bị xuất hiện sau khi yêu cầu kết thúc; log các bước gửi và tắt được cập nhật trong khi chạy. “Đã gửi” phản ánh kết quả thao tác TCP, chưa xác nhận trạng thái vật lý của đèn.

Mỗi yêu cầu giữ tối đa 500 sự kiện log trong bộ nhớ; nếu vượt giới hạn, giao diện thông báo số dòng đã lược bớt. File log theo ngày giữ đầy đủ log với trường `request=<Request ID>`; log hệ thống ngoài yêu cầu có `request=-`. Tab `Nhật ký hệ thống` tiếp tục hiển thị file log của ngày hiện tại, hỗ trợ sao chép và bật/tắt theo dõi dòng mới.

Bảng Yêu cầu chỉ chứa lịch sử của phiên chạy hiện tại. Log văn bản cũ vẫn còn trên đĩa theo chính sách lưu 14 ngày; các dòng log được tạo trước khi có tính năng này không có Request ID để tự nhóm lại.

## Giao diện điều khiển

Giao diện dùng bảng màu tối và nhãn tiếng Việt. Các nút và ô nhập có góc bo nhẹ, chiều cao thống nhất, trạng thái hover / focus bàn phím; tab không có khung nổi. Thanh cuộn mảnh không có nút mũi tên và tự ẩn khi nội dung vừa khung. Các thành phần được vẽ bằng Tk hiện có, không cần thêm dependency giao diện.

Tab `Điều khiển` có danh sách bên trái, bảng gửi lệnh bên phải và các thẻ tổng số thiết bị đã tải, số thiết bị đang hiển thị / nhận lệnh và số line. Danh sách hỗ trợ sắp xếp theo cột, tìm kiếm, lọc line và trạng thái trống / lỗi tải. Vùng lệnh hỗ trợ cuộn bằng con lăn khi danh sách lệnh dài.

Phạm vi gửi luôn là toàn bộ thiết bị đang hiển thị. Nút `Tắt cảnh báo` có màu đỏ và nằm đầu danh sách lệnh. Ô thời lượng được điền sẵn theo cấu hình; lệnh tắt và đọc không dùng thời lượng. Các nút lệnh bị vô hiệu hóa khi đang tải danh sách hoặc không có mục tiêu.

Sau khi gửi, nút `Xem yêu cầu vừa gửi` mở thẳng dòng tương ứng trên tab Yêu cầu. Nếu yêu cầu đã bị loại khỏi lịch sử giới hạn, giao diện thông báo thay vì chọn nhầm dòng khác. Thanh cuối cửa sổ hiển thị số yêu cầu trong lịch sử và số đang xử lý.

## Các thay đổi cần lưu ý khi nâng cấp

Khi chạy lần đầu mà chưa có `config.yaml` cạnh ứng dụng, app tự tạo file từ cấu hình mẫu được đóng gói, tự lấy IPv4 của máy và dùng port `7000`. Khi không tìm thấy IPv4 phù hợp, dùng `127.0.0.1`. Mặc định dùng HTTP; bật switch HTTPS / SSL trong tab Cấu hình để nhập đường dẫn chứng chỉ và private key. Ba lệnh mặc định là `FLASH_ONLY` (chỉ nháy đèn), `TURN_OFF`, `SOUND_FLASH` (nháy đèn và phát âm thanh). Cấu hình đã lưu được giữ nguyên. Nhập thông tin SQL trong tab `Cấu hình` để tải danh sách thiết bị; tab `Cấu hình mạng` có thể dùng ngay mà không cần SQL. Đường dẫn cấu hình được chỉ định bằng `--config` hoặc `LIGHT_ALARM_CONFIG` vẫn phải tồn tại.

- Các module `configs`, `controllers`, `models`, `routes`, `services`, `ui` ở thư mục gốc được thay bằng package `light_alarm`. Code Python bên ngoài import các đường dẫn cũ cần cập nhật.
- API gửi lệnh chuyển từ `200/success` sang `202/accepted`, kèm endpoint lấy kết quả.
- `get_device` trả một object thay vì danh sách; thao tác thêm trả `201`, sửa/xóa không tồn tại trả `404`.
- API lọc line dùng kết quả chính xác; tìm kiếm gần đúng vẫn có trên giao diện.
- CORS mở cho mọi origin đã được bỏ; client trình duyệt khác origin cần cấu hình proxy cùng origin hoặc bổ sung danh sách origin được phép theo môi trường triển khai.
- `requests` chỉ còn phục vụ công cụ Google Form; ứng dụng chính không gọi HTTP tới chính nó.

## Cấu hình YAML trên giao diện

Tab `Cấu hình` đọc đúng file YAML được chọn khi khởi động (kể cả `--config` hoặc `LIGHT_ALARM_CONFIG`). Có thể sửa Máy chủ, Database, Thời gian và thêm/sửa/xóa lệnh HEX. Mật khẩu SQL và API key được che mặc định. Lệnh `TURN_OFF` bắt buộc, không thể xóa hoặc đổi tên.

Bấm `Lưu và áp dụng` để kiểm tra dữ liệu, tạo bản sao `<file>.yaml.bak`, ghi YAML và cập nhật ứng dụng. Lệnh, database, API key và timeout áp dụng cho yêu cầu mới; danh sách nút Điều khiển được dựng lại từ cấu hình. IP / port / SSL server cần khởi động lại vì server đang lắng nghe địa chỉ cũ. Biến môi trường `LIGHT_ALARM_API_KEY` tiếp tục được ưu tiên hơn giá trị trong UI.

Nếu đang có yêu cầu chờ/chạy, file vẫn được lưu nhưng cấu hình chưa áp dụng; chờ hoàn tất rồi bấm `Áp dụng lại`. Nút này áp dụng bản đã lưu, không lưu các thay đổi mới trên form. `Đọc lại YAML` thay thế nội dung đang sửa bằng nội dung file trên đĩa. Nếu file bị sửa bên ngoài sau lần đọc gần nhất, thao tác lưu bị chặn để tránh ghi đè.

Các giá trị `TIMING.DEFAULT_DURATION`, `CONNECT_TIMEOUT`, `RESPONSE_TIMEOUT` và `DATABASE_TIMEOUT` tính bằng giây. Thời lượng mặc định có thể là 0; các timeout phải lớn hơn 0. Timeout database phải là số nguyên. Khi lưu, các khóa YAML ngoài form được giữ nguyên; comment và cách trình bày YAML được chuẩn hóa lại bởi PyYAML. File cấu hình thực tế không được thay đổi trong quá trình triển khai tính năng.

## Công cụ CRC

Trên giao diện, mở tab `Tạo mã CRC16` để chọn Flash, Volume, Play và Track từ các danh sách chỉ đọc. Theo PDF nhà cung cấp, Flash 01–07 (6: một dài + một ngắn; 7: một dài + hai ngắn), Volume 00–08, Play phát lặp hoặc 1–16 lần (HEX 01–10), Track 1–250 (HEX 01–FA). Track theo thứ tự chép file, không theo tên file. Kết quả gồm mã HEX đầy đủ, CRC16 little-endian và bản xem theo từng byte; nút `Sao chép mã HEX` sao chép chuỗi đầy đủ. Khi đổi lựa chọn, kết quả cũ được xóa để tránh sao chép nhầm. Nút `Giá trị mẫu` khôi phục `01 / 01 / 00 / 01`.

Đã đối chiếu hai frame mẫu trong PDF và thêm khoảng cách gói tối thiểu 200 ms theo từng thiết bị. Ứng dụng đang chủ động mở TCP tới đèn nên cần thiết bị ở TCP Server; TCP Client mặc định của nhà cung cấp cần một TCP listener riêng, hiện chưa có trong ứng dụng. HOST_IP/PORT của YAML là HTTP API. Xem `docs/device-configuration.md` để phân biệt vai trò mạng và giới hạn xác minh.

Tab này dùng chung `light_alarm/devices/protocol.py` với công cụ dòng lệnh bên dưới và chỉ tính mã cục bộ.

Tab `Cấu hình mạng` tìm module CH9120 trên cùng mạng LAN bằng broadcast UDP, cho chọn địa chỉ card mạng, đọc cấu hình theo MAC và ghi lại các thông số tên, IP tĩnh/DHCP, subnet, gateway, chế độ TCP/UDP, port nguồn/đích và baud rate. Sau khi ghi, module khởi động lại; quét lại để xác nhận IP mới. Máy tính cần ở cùng subnet và cho phép UDP broadcast qua cổng cấu hình 50000, cổng cục bộ 60000. Tính năng dùng giao thức cấu hình module, tách biệt với lệnh điều khiển đèn và API HTTP. Thiết bị thật chưa được xác minh từ ứng dụng này.

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
.\build.cmd
```

Lệnh tự dùng Python trong `venv` nếu có, hoặc `python` trên PATH, và đóng gói theo `app.spec`. Có thể truyền thêm tùy chọn, ví dụ `.\build.cmd --clean`. Kết quả nằm ở `dist/app.exe`.

Nếu chưa có `dist/config.yaml`, lệnh build chép cấu hình từ thư mục dự án (hoặc cấu hình mẫu nếu chưa có cấu hình thực tế). Cấu hình đã tồn tại trong `dist` được giữ nguyên. `HOST_IP` phải là địa chỉ IP hiện có trên máy chạy ứng dụng; có thể dùng `127.0.0.1` để chỉ phục vụ máy đó. Khi khởi động thất bại, ứng dụng hiện thông báo và ghi chi tiết vào `startup-error.log` cạnh file `.exe`.

Đặt `config.yaml` cạnh `dist/app.exe`; nếu bật SSL, triển khai thêm file chứng chỉ và private key theo đường dẫn cấu hình. PyInstaller thu thập package Python qua import; cấu hình mẫu được kèm trong bundle, còn cấu hình thực tế được đọc từ file bên ngoài.

## Trạng thái xác minh

Đã chạy 51 test gồm 35 test API, 4 test CRC, 9 test cấu hình/lưu YAML và 3 test áp dụng cấu hình; tất cả thành công. API dùng Flask test client, repository và thiết bị giả lập. Chạy lại bằng `python -m unittest discover -s tests -v`. Chi tiết phạm vi API ở `docs/api-testing.md`.

Đã kiểm tra riêng layout trình sửa lệnh YAML bằng Tk ngoài màn hình: ô nhập và hàng nút thao tác nằm trong khung ở 1240×860 và 1040×740, với hai mức scaling 1.0 và 1.5. Chạy lại bằng `python -m unittest discover -s tests -p test_settings_layout.py -v`.

Chưa xác minh SQL Server và thiết bị thật, toàn bộ luồng giao diện hoặc build `.exe`. Test API không xác nhận khả năng kết nối thiết bị ngoài mạng.
