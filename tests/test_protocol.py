"""CRC reference vectors and strict one-byte control validation."""

import unittest

from light_alarm.devices.protocol import build_command, crc16_modbus


class ProtocolTests(unittest.TestCase):
    def test_modbus_reference_vector(self):
        self.assertEqual(crc16_modbus("313233343536373839"), "374B")

    def test_original_command_example(self):
        self.assertEqual(build_command("01", "01", "00", "01"), "0110001A00040101000137FF")

    def test_lowercase_is_normalized(self):
        self.assertEqual(build_command("0a", "01", "00", "ff"), build_command("0A", "01", "00", "FF"))

    def test_invalid_control_values(self):
        for value in ("", "1", "000", "  ", "0 ", "GG", "+1", "é1", None, 1):
            for index in range(4):
                with self.subTest(value=value, index=index):
                    values = ["01", "01", "00", "01"]
                    values[index] = value
                    with self.assertRaises(ValueError):
                        build_command(*values)


if __name__ == "__main__":
    unittest.main()
