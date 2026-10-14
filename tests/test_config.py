"""Configuration validation and disk persistence without external services."""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from light_alarm.config import Settings
from light_alarm.config_document import ConfigDocument
from light_alarm.devices.protocol import build_command


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "custom.yaml"
        self.data = {
            "HOST_IP": "127.0.0.1", "PORT": 7000,
            "CH9120": {"COMMANDS": {"TURN_OFF": "00", "ALARM": "01"}},
            "DATABASE": dict(SQL_DRIVER="driver", SQL_SERVER="server", SQL_DATABASE="db",
                             SQL_USER="user", SQL_PASSWORD=""),
            "EXTRA": {"preserve": True},
        }
        self.path.write_text(yaml.safe_dump(self.data), encoding="utf-8")

    def test_load_correct_file_and_allow_empty_password(self):
        settings = Settings.load(self.path)
        self.assertEqual(settings.config_path, self.path.resolve())
        self.assertEqual(settings.database["SQL_PASSWORD"], "")
        self.assertEqual(settings.default_duration, 5)

    def test_first_run_creates_default_config_from_bundled_template(self):
        directory = Path(self.temp.name)
        resource_directory = Path(__file__).resolve().parent.parent
        with patch.dict(os.environ, {}, clear=True), \
                patch("light_alarm.config.application_directory", return_value=directory), \
                patch("light_alarm.config.local_host_ip", return_value="10.20.30.40"), \
                patch("light_alarm.config.sys._MEIPASS", str(resource_directory), create=True):
            settings = Settings.load()
        self.assertEqual(settings.host, "10.20.30.40")
        self.assertEqual(settings.config_path, (directory / "config.yaml").resolve())
        self.assertTrue(settings.config_path.is_file())
        self.assertIn("TURN_OFF", settings.commands)
        self.assertEqual(set(settings.commands), {"FLASH_ONLY", "TURN_OFF", "SOUND_FLASH"})
        self.assertEqual(settings.commands["FLASH_ONLY"], build_command("01", "00", "00", "01"))
        self.assertEqual(settings.commands["SOUND_FLASH"], build_command("01", "01", "00", "01"))
        self.assertFalse(settings.ssl_enabled)
        ConfigDocument(settings.config_path)

    def test_first_run_preserves_existing_default_config(self):
        default_path = Path(self.temp.name) / "config.yaml"
        original = self.path.read_bytes()
        default_path.write_bytes(original)
        with patch.dict(os.environ, {}, clear=True), \
                patch("light_alarm.config.application_directory", return_value=default_path.parent):
            Settings.load()
        self.assertEqual(default_path.read_bytes(), original)

    def test_missing_explicit_config_is_not_replaced_with_template(self):
        missing = Path(self.temp.name) / "missing.yaml"
        with self.assertRaises(FileNotFoundError):
            Settings.load(missing)
        with patch.dict(os.environ, {"LIGHT_ALARM_CONFIG": str(missing)}):
            with self.assertRaises(FileNotFoundError):
                Settings.load()
        self.assertFalse(missing.exists())

    def test_missing_database_field_is_identified(self):
        del self.data["DATABASE"]["SQL_SERVER"]
        with self.assertRaisesRegex(ValueError, "SQL_SERVER"):
            Settings.from_mapping(self.data, self.path)

    def test_timing_values_come_from_yaml(self):
        self.data["TIMING"] = dict(DEFAULT_DURATION=0, CONNECT_TIMEOUT=2.5,
                                   RESPONSE_TIMEOUT=3, DATABASE_TIMEOUT=7)
        settings = Settings.from_mapping(self.data, self.path)
        self.assertEqual((settings.default_duration, settings.connect_timeout,
                          settings.response_timeout, settings.database_timeout), (0, 2.5, 3, 7))

    def test_invalid_timing_and_port_values(self):
        for key, value in (("CONNECT_TIMEOUT", 0), ("CONNECT_TIMEOUT", "nan"),
                           ("RESPONSE_TIMEOUT", float("inf")), ("DATABASE_TIMEOUT", 1.5),
                           ("DEFAULT_DURATION", -1), ("DEFAULT_DURATION", True)):
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.data)
                data["TIMING"] = {key: value}
                with self.assertRaises(ValueError):
                    Settings.from_mapping(data, self.path)
        for value in (True, 1.5, 0, 65536):
            with self.subTest(port=value):
                data = {**self.data, "PORT": value}
                with self.assertRaises(ValueError):
                    Settings.from_mapping(data, self.path)

    def test_save_creates_backup_and_preserves_unknown_fields(self):
        original = self.path.read_bytes()
        document = ConfigDocument(self.path)
        data = document.reload()
        data["CH9120"]["COMMANDS"]["NEW_COMMAND"] = "AABB"
        document.save(data)
        self.assertEqual(self.path.with_suffix(".yaml.bak").read_bytes(), original)
        saved = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["EXTRA"], {"preserve": True})
        self.assertEqual(Settings.load(self.path).commands["NEW_COMMAND"], "AABB")

    def test_invalid_save_keeps_original_file(self):
        document = ConfigDocument(self.path)
        original = self.path.read_bytes()
        data = document.reload()
        data["CH9120"]["COMMANDS"].pop("TURN_OFF")
        with self.assertRaises(ValueError):
            document.save(data)
        self.assertEqual(self.path.read_bytes(), original)

    def test_external_edit_is_not_overwritten(self):
        document = ConfigDocument(self.path)
        self.path.write_text("# external edit\n" + self.path.read_text(encoding="utf-8"), encoding="utf-8")
        external = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "bên ngoài"):
            document.save(document.data)
        self.assertEqual(self.path.read_bytes(), external)

    def test_environment_api_key_remains_preferred(self):
        self.data["API_KEY"] = "from-file"
        with patch.dict(os.environ, {"LIGHT_ALARM_API_KEY": "from-env"}):
            settings = Settings.from_mapping(self.data, self.path)
        self.assertEqual(settings.api_key, "from-env")

    def test_invalid_yaml_has_clear_error(self):
        self.path.write_text("bad: [", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "YAML"):
            ConfigDocument(self.path)


if __name__ == "__main__":
    unittest.main()
