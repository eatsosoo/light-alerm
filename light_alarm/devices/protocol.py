"""Encode the manufacturer's CH9120 command frame and CRC-16."""


def crc16_modbus(data_hex):
    crc = 0xFFFF
    for byte in bytes.fromhex(data_hex):
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, byteorder="little").hex().upper()


def build_command(flash, volume, play, track):
    values = (flash, volume, play, track)
    if any(not isinstance(value, str) or len(value) != 2 for value in values):
        raise ValueError("Each control value must contain exactly two HEX characters.")
    content = "0110001A0004" + "".join(values).upper()
    return content + crc16_modbus(content)
