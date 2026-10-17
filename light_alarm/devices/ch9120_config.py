"""UDP discovery and configuration protocol for WCH CH9120 modules.

The wire format mirrors the CH9120 network configuration utility protocol:
fixed 16-byte marker, command, target MAC, client MAC, payload length and a
255-byte payload. Alarm command traffic uses a separate protocol/client.
"""

import ipaddress
import socket
import struct
import time


MARKER = b"CH9120_CFG_FLAG\0"
CONFIG_PORT = 50000
LOCAL_PORT = 60000
DATA_SIZE = 255
PACKET_SIZE = 16 + 1 + 6 + 6 + 1 + DATA_SIZE
HW_SIZE = 74
PORT_SIZE = 65
CONFIG_SIZE = HW_SIZE + 2 * PORT_SIZE

CMD_SET, CMD_GET, CMD_RESET, CMD_SEARCH = 0x01, 0x02, 0x03, 0x04
ACK_SET, ACK_GET, ACK_RESET, ACK_SEARCH = 0x81, 0x82, 0x83, 0x84
MODES = {0: "TCP Server", 1: "TCP Client", 2: "UDP Server", 3: "UDP Client"}


class CH9120ConfigError(ValueError):
    """Invalid data or an unexpected CH9120 configuration response."""


def _packet(command, mac=b"\0" * 6, payload=b"", client_mac=b"\0" * 6):
    if len(mac) != 6 or len(client_mac) != 6:
        raise CH9120ConfigError("MAC address must contain six bytes.")
    if len(payload) > DATA_SIZE:
        raise CH9120ConfigError("Configuration payload is too large.")
    return MARKER + bytes([command]) + mac + client_mac + bytes([len(payload)]) + payload.ljust(DATA_SIZE, b"\0")


def _response(data, expected_command):
    if len(data) < 30 or data[:16] != MARKER or data[16] != expected_command:
        return None
    return {
        "mac": data[17:23],
        "client_mac": data[23:29],
        "length": data[29],
        "data": data[30:],
    }


def _text(raw):
    return raw.split(b"\0", 1)[0].decode("ascii", errors="replace").strip()


def _ip(raw):
    return str(ipaddress.IPv4Address(raw))


def _put_ip(target, offset, value):
    try:
        target[offset:offset + 4] = ipaddress.IPv4Address(value).packed
    except ipaddress.AddressValueError as error:
        raise CH9120ConfigError(f"Địa chỉ IPv4 không hợp lệ: {value}") from error


def decode_config(mac, payload):
    if len(payload) < CONFIG_SIZE:
        raise CH9120ConfigError(f"Dữ liệu cấu hình thiếu: cần {CONFIG_SIZE} byte, nhận {len(payload)}.")
    data = bytearray(payload[:CONFIG_SIZE])
    hw = data[:HW_SIZE]
    port = data[HW_SIZE + PORT_SIZE:HW_SIZE + 2 * PORT_SIZE]
    mode = port[2]
    return {
        "mac": mac.hex(":"),
        "name": _text(hw[5:26]) or "CH9120",
        "hardware_version": hw[3],
        "firmware_version": hw[4],
        "ip": _ip(hw[32:36]),
        "gateway": _ip(hw[36:40]),
        "subnet": _ip(hw[40:44]),
        "dhcp": bool(hw[44]),
        "mode": mode,
        "mode_name": MODES.get(mode, f"Unknown ({mode})"),
        "local_port": struct.unpack_from("<H", port, 4)[0],
        "destination_ip": _ip(port[6:10]),
        "destination_port": struct.unpack_from("<H", port, 10)[0],
        "baud_rate": struct.unpack_from("<I", port, 12)[0],
        "data_size": port[16],
        "stop_bits": port[17],
        "parity": port[18],
        "_raw": data,
    }


def encode_config(current, updates):
    data = bytearray(current["_raw"])
    hw = memoryview(data)[:HW_SIZE]
    port_offset = HW_SIZE + PORT_SIZE
    port = memoryview(data)[port_offset:port_offset + PORT_SIZE]

    if "name" in updates:
        name = str(updates["name"]).strip().encode("ascii", errors="strict")
        if not name or len(name) > 20:
            raise CH9120ConfigError("Tên thiết bị phải dài từ 1 đến 20 ký tự ASCII.")
        hw[5:26] = name.ljust(21, b"\0")
    for field, offset in (("ip", 32), ("gateway", 36), ("subnet", 40)):
        if field in updates:
            _put_ip(hw, offset, updates[field])
    if "dhcp" in updates:
        hw[44] = 1 if updates["dhcp"] else 0
    if "mode" in updates:
        mode = int(updates["mode"])
        if mode not in MODES:
            raise CH9120ConfigError("Chế độ mạng không hợp lệ.")
        port[2] = mode
    if "local_port" in updates:
        value = int(updates["local_port"])
        if not 1 <= value <= 65535:
            raise CH9120ConfigError("Port phải nằm trong khoảng 1–65535.")
        struct.pack_into("<H", port, 4, value)
    if "destination_ip" in updates:
        _put_ip(port, 6, updates["destination_ip"])
    if "destination_port" in updates:
        value = int(updates["destination_port"])
        if not 1 <= value <= 65535:
            raise CH9120ConfigError("Port đích phải nằm trong khoảng 1–65535.")
        struct.pack_into("<H", port, 10, value)
    if "baud_rate" in updates:
        value = int(updates["baud_rate"])
        if not 300 <= value <= 921600:
            raise CH9120ConfigError("Baud rate phải nằm trong khoảng 300–921600.")
        struct.pack_into("<I", port, 12, value)
    return bytes(data)


class CH9120ConfigClient:
    """Communicate with CH9120 configuration firmware over UDP broadcast."""

    def __init__(self, timeout=0.35, search_duration=1.5):
        self.timeout = timeout
        self.search_duration = search_duration

    @staticmethod
    def local_ipv4_addresses():
        """Return IPv4 addresses available for a NIC selector in the UI."""
        addresses = set()
        try:
            for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM):
                address = item[4][0]
                if not address.startswith("127."):
                    addresses.add(address)
        except OSError:
            pass
        return sorted(addresses)

    def _socket(self, bind_ip="0.0.0.0"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((bind_ip or "0.0.0.0", LOCAL_PORT))
        except OSError:
            sock.close()
            raise
        return sock

    def discover(self, bind_ip="0.0.0.0"):
        found = {}
        packet = _packet(CMD_SEARCH)
        with self._socket(bind_ip) as sock:
            sock.settimeout(0.1)
            sock.sendto(packet, ("255.255.255.255", CONFIG_PORT))
            deadline = time.monotonic() + self.search_duration
            while time.monotonic() < deadline:
                try:
                    data, endpoint = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                response = _response(data, ACK_SEARCH)
                if response is None or response["mac"] == b"\0" * 6:
                    continue
                details = response["data"]
                if len(details) < 4:
                    continue
                mac = response["mac"].hex(":")
                found[mac] = {
                    "mac": mac,
                    "ip": endpoint[0],
                    "name": _text(details[4:25]) or "CH9120",
                    "firmware_version": details[25] if len(details) > 25 else None,
                }
        return sorted(found.values(), key=lambda item: (item["ip"], item["mac"]))

    def _request(self, command, expected, mac, payload=b"", target_ip="255.255.255.255", bind_ip="0.0.0.0"):
        try:
            target_mac = bytes.fromhex(mac.replace(":", "").replace("-", ""))
        except ValueError as error:
            raise CH9120ConfigError("Địa chỉ MAC không hợp lệ.") from error
        if len(target_mac) != 6:
            raise CH9120ConfigError("Địa chỉ MAC không hợp lệ.")
        with self._socket(bind_ip) as sock:
            sock.settimeout(self.timeout)
            sock.sendto(_packet(command, target_mac, payload), (target_ip, CONFIG_PORT))
            deadline = time.monotonic() + self.timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CH9120ConfigError("CH9120 không phản hồi. Kiểm tra cùng subnet, card mạng và tường lửa.")
                sock.settimeout(remaining)
                try:
                    data, endpoint = sock.recvfrom(2048)
                except socket.timeout as error:
                    raise CH9120ConfigError("CH9120 không phản hồi. Kiểm tra cùng subnet, card mạng và tường lửa.") from error
                response = _response(data, expected)
                if response and response["mac"] == target_mac:
                    return response, endpoint[0]

    def get_config(self, module, bind_ip="0.0.0.0"):
        response, endpoint = self._request(CMD_GET, ACK_GET, module["mac"], target_ip=module["ip"], bind_ip=bind_ip)
        config = decode_config(response["mac"], response["data"])
        config["ip"] = endpoint
        return config

    def set_config(self, current, updates, bind_ip="0.0.0.0"):
        payload = encode_config(current, updates)
        response, _ = self._request(CMD_SET, ACK_SET, current["mac"], payload,
                                    target_ip=current["ip"], bind_ip=bind_ip)
        return response

