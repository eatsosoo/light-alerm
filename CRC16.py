import argparse

def crc16_modbus(data_hex):
    """
    Calculate the CRC16 MODBUS checksum of *data_hex*.
    
    :param data_hex: The input data as a hexadecimal string
    :return: The calculated CRC as a hexadecimal string
    """
    crc = 0xFFFF
    poly = 0xA001  # 0x8005 reverse polynomial
    data = bytearray.fromhex(data_hex)

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if (crc & 0x0001):
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1

    crc_bytes = crc.to_bytes(2, byteorder='little')
    return crc_bytes.hex().upper()

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--f', '--flash', dest='f', type=str, required=True, help='Flash mode (1 byte hex)')
parser.add_argument('--v', '--volume', dest='v', type=str, required=True, help='Volume (1 byte hex)')
parser.add_argument('--p', '--play', dest='p', type=str, required=True, help='Play mode (1 byte hex)')
parser.add_argument('--t', '--track', dest='t', type=str, required=True, help='Track (1 byte hex)')

args = parser.parse_args()

# Example usage:
alarm_num = '01'
function = '10'
initial_address = '001A'
data_number = '0004'
data_content = f'{args.f}{args.v}{args.p}{args.t}'
command = f'{alarm_num}{function}{initial_address}{data_number}{data_content}'

crc_value = crc16_modbus(command)

print(f'The CRC value is: {crc_value}')
print(f'The hex command: {command}{crc_value}')