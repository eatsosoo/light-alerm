
# 💡 Light-Alarm Control System

Ứng dụng điều khiển thiết bị đèn cảnh báo (CH9120) qua mạng TCP bằng lệnh Hex, hỗ trợ gửi theo line hoặc toàn bộ thiết bị.

---

## 🚀 Hướng dẫn cài đặt & chạy ứng dụng

### 1. Tạo môi trường ảo (nếu chưa có)
```bash
python -m venv venv
```

### 2. Kích hoạt môi trường ảo
- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

### 3. Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### 4. Khởi động ứng dụng
```bash
python app.py
```

---

## 🛠️ Build file `.exe` với PyInstaller

```bash
pyinstaller --onefile --noconsole app.py ^
  --add-data "configs;configs" ^
  --add-data "controllers;controllers" ^
  --add-data "models;models" ^
  --add-data "services;services" ^
  --add-data "routes;routes"
```

```bash
pyinstaller --onefile --noconsole app.py --add-data "configs;configs" --add-data "controllers;controllers" --add-data "models;models" --add-data "services;services" --add-data "routes;routes"
```

> 📦 File `.exe` sẽ nằm trong thư mục `dist/`.

---

## 📟 Giải thích cấu trúc lệnh `hex_command`

Lệnh Hex gửi đến thiết bị đèn cảnh báo có định dạng theo chuẩn Modbus TCP như sau:

| Byte / Nhóm byte         | Giá trị mẫu              | Ý nghĩa                                                                 |
|--------------------------|--------------------------|------------------------------------------------------------------------|
| Thiết bị địa chỉ         | `01`                     | Địa chỉ thiết bị (thường là `01`)                                     |
| Mã chức năng             | `10`                     | Ghi nhiều thanh ghi (Function code 0x10)                              |
| Địa chỉ thanh ghi bắt đầu| `00 1A`                  | Địa chỉ thanh ghi bắt đầu (`0x001A` = thanh ghi 26)                   |
| Số lượng thanh ghi       | `00 04`                  | Số thanh ghi cần ghi (4 = 4 byte)                                     |
| Dữ liệu điều khiển       | `01 01 00 01`            | 4 byte gồm: Flash, Volume, Play Mode, Track (giải thích bên dưới)     |
| CRC (Checksum)           | `37 FA`                  | CRC-16 Modbus, định dạng little-endian                                |

Để lấy đúng giá trị CRC:
```bash
python CRC16.py --f 01 --v 01 --p 00 --t 01
```

### 📋 Giải thích dữ liệu điều khiển (`01 01 00 01`):

| Byte | Ý nghĩa             | Giá trị  | Ghi chú                                            |
|------|---------------------|----------|----------------------------------------------------|
| 1    | Flash mode          | `01`     | Chế độ nhấp nháy (1 = nhanh nhất)                  |
| 2    | Âm lượng            | `01`     | Mức âm lượng (01 = nhỏ nhất, 08 = max, 00 = tắt)   |
| 3    | Play mode           | `00`     | `00` = phát lặp, `01-16` = số lần phát             |
| 4    | Track (bài âm thanh)| `01`     | Chọn bài số 1 trong bộ nhớ thiết bị                |

---

## 📄 Tham khảo thêm

- Thiết bị hỗ trợ: CH9120 TCP Sound-Light Alarm
- Tài liệu cấu hình HEX: đi kèm trong thư mục `docs/` (hoặc yêu cầu bên cung cấp)

---

## 📬 Góp ý / Liên hệ

Nếu bạn gặp lỗi hoặc muốn đóng góp thêm, vui lòng mở issue hoặc liên hệ trực tiếp với người phát triển.

---
