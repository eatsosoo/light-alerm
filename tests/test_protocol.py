"""CRC reference vectors and strict one-byte control validation."""

import unittest

from light_alarm.devices.protocol import build_command, crc16_modbus


class ProtocolTests(unittest.TestCase):
    def test_modbus_reference_vector(self):
        self.assertEqual(crc16_modbus("313233343536373839"), "374B")

    def test_original_command_example(self):
        self.assertEqual(build_command("01", "01", "00", "01"), "0110001A00040101000137FF")

    def test_lowercase_is_normalized(self):
        self.assertEqual(build_command("07", "08", "10", "fa"), build_command("07", "08", "10", "FA"))

    def test_manufacturer_pdf_examples(self):
        self.assertEqual(build_command("05", "08", "00", "02"), "0110001A000405080002A6CC")
        self.assertEqual(build_command("05", "00", "00", "01"), "0110001A000405000001670F")

    def test_manufacturer_ranges_are_enforced(self):
        for index, invalid in ((0, "00"), (0, "08"), (1, "09"), (2, "11"), (3, "00"), (3, "FB")):
            with self.subTest(index=index, value=invalid):
                values = ["01", "01", "00", "01"]
                values[index] = invalid
                with self.assertRaises(ValueError):
                    build_command(*values)

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
