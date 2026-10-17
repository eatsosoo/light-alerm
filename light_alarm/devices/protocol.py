"""Encode the manufacturer's CH9120 command frame and CRC-16."""

import re

# Manufacturer PDF, section 8-1 (page 9).
FLASH_MODES = {
    1: "Tần số nháy 1", 2: "Tần số nháy 2", 3: "Tần số nháy 3",
    4: "Tần số nháy 4", 5: "Tần số nháy 5 (nhanh nhất)",
    6: "1 dài + 1 ngắn", 7: "1 dài + 2 ngắn",
}
CONTROL_RANGES = {"flash": (1, 7), "volume": (0, 8), "play": (0, 16), "track": (1, 250)}
MIN_PACKET_INTERVAL = 0.2


def crc16_modbus(data_hex):
    crc = 0xFFFF
    for byte in bytes.fromhex(data_hex):
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, byteorder="little").hex().upper()


def build_command(flash, volume, play, track):
    values = (flash, volume, play, track)
    if any(not isinstance(value, str) or re.fullmatch(r"[0-9A-Fa-f]{2}", value) is None for value in values):
        raise ValueError("Each control value must contain exactly two HEX characters.")
    for name, value in zip(CONTROL_RANGES, values):
        minimum, maximum = CONTROL_RANGES[name]
        if not minimum <= int(value, 16) <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum} (decimal).")
    content = "0110001A0004" + "".join(values).upper()
    return content + crc16_modbus(content)
