"""Off-screen Tk layout checks; no server, database or device is started."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from light_alarm.config import Settings
from light_alarm.ui.main_window import MainWindow
from light_alarm.ui.settings_tab import SettingsTab
from light_alarm.ui.theme import COLORS, tabs


class SettingsLayoutTests(unittest.TestCase):
    def test_command_editor_and_actions_fit_supported_window_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(yaml.safe_dump({
                "CH9120": {"COMMANDS": {"TURN_OFF": "00", "FLASH_ONLY": "01", "READ_ALL": "02"}},
                "DATABASE": dict(SQL_DRIVER="fake", SQL_SERVER="fake", SQL_DATABASE="fake",
                                 SQL_USER="fake", SQL_PASSWORD=""),
            }), encoding="utf-8")
            runtime = SimpleNamespace(settings=Settings.load(path))
            for width, height, scaling in ((1240, 860, 1.0), (1040, 740, 1.0),
                                            (1240, 860, 1.5), (1040, 740, 1.5)):
                with self.subTest(width=width, height=height, scaling=scaling):
                    root = tk.Tk()
                    root.withdraw()
                    tab = None
                    try:
                        root.tk.call("tk", "scaling", scaling)
                        root.option_add("*Font", ("Segoe UI", 10))
                        root.geometry(f"{width}x{height}+-10000+-10000")
                        style_owner = MainWindow.__new__(MainWindow)
                        style_owner.root, style_owner.colors = root, COLORS
                        style_owner.setup_styles()
                        notebook = tabs(root)
                        notebook.place(x=18, y=107, width=width - 36, height=height - 156)
                        tab = SettingsTab(root, notebook, runtime, lambda settings: None)
                        tab.pages.select(tab.command_page)
                        root.deiconify()
                        root.update()
                        self.assertGreater(tab.command_page.winfo_height(), 200)
                        for row in (0, 1, 2, 3):
                            child = tab.command_page.grid_slaves(row=row)[0]
                            self.assertGreater(child.winfo_height(), 0)
                            self.assertGreaterEqual(child.winfo_y(), 0)
                            self.assertLessEqual(child.winfo_y() + child.winfo_height(),
                                                 tab.command_page.winfo_height())
                        actions = tab.command_page.grid_slaves(row=3)[0]
                        self.assertEqual(len(actions.winfo_children()), 2)
                        for control in actions.winfo_children():
                            self.assertTrue(control.winfo_ismapped())
                            self.assertLessEqual(control.winfo_x() + control.winfo_width(), actions.winfo_width())
                        self.assertLessEqual(tab.save_button.winfo_rooty() + tab.save_button.winfo_height(),
                                             root.winfo_rooty() + height)
                    finally:
                        if tab is not None:
                            tab.close()
                        root.destroy()


if __name__ == "__main__":
    unittest.main()
