"""Verify dropdown selections produce the correct protocol bytes."""

import tkinter as tk
import unittest

from light_alarm.devices.protocol import build_command
from light_alarm.ui.crc_tab import CRCTab
from light_alarm.ui.main_window import MainWindow
from light_alarm.ui.theme import COLORS, tabs


class CRCSelectTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        owner = MainWindow.__new__(MainWindow)
        owner.root, owner.colors = self.root, COLORS
        owner.setup_styles()
        self.notebook = tabs(self.root)
        self.tab = CRCTab(self.root, self.notebook)
        self.addCleanup(self.tab.close)

    def test_inputs_are_readonly_selects_with_valid_defaults(self):
        for control in self.tab.inputs.values():
            self.assertEqual(str(control.input.cget("state")), "readonly")
            self.assertTrue(control.input.cget("values"))
        self.assertEqual(self.tab.command.get(), "0110001A00040101000137FF")

    def test_selected_labels_map_to_hex_bytes_and_invalidate_previous_result(self):
        for key, value in {"flash": "07", "volume": "08", "play": "10", "track": "FA"}.items():
            self.tab.values[key].set(self.tab.option_label(key, value))
        self.assertEqual(self.tab.command.get(), "")
        self.assertEqual(self.tab._generated, "")
        self.tab.generate()
        self.assertEqual(self.tab.command.get(), build_command("07", "08", "10", "FA"))

    def test_dropdown_ranges_match_pdf(self):
        for key, minimum, maximum in (("flash", 1, 7), ("volume", 0, 8), ("play", 0, 16), ("track", 1, 250)):
            self.assertEqual({int(value, 16) for value in self.tab.OPTIONS[key].values()}, set(range(minimum, maximum + 1)))

    def test_reset_restores_original_command(self):
        self.tab.values["volume"].set(self.tab.option_label("volume", "00"))
        self.tab.generate()
        self.assertNotEqual(self.tab.command.get(), "0110001A00040101000137FF")
        self.tab.reset()
        self.assertEqual(self.tab.command.get(), "0110001A00040101000137FF")


if __name__ == "__main__":
    unittest.main()
