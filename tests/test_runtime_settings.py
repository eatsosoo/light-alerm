"""Applying settings uses the shared loop and never opens database or TCP I/O."""

import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from light_alarm.config import Settings
from light_alarm.runtime import Runtime
from light_alarm.services.background_worker import BackgroundWorker
from light_alarm.services.request_history import RequestHistory


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.original = Settings(Path.cwd(), "127.0.0.1", 7000, {"TURN_OFF": "00"}, {})
        self.history = RequestHistory()
        worker = BackgroundWorker(self.history)
        self.runtime = Runtime(self.original, SimpleNamespace(settings=self.original),
                               SimpleNamespace(settings=self.original, client=None), worker, None)
        self.addCleanup(self.runtime.close)

    def test_commands_and_timeouts_apply_without_restart(self):
        settings = replace(self.original, commands={"TURN_OFF": "00", "NEW": "01"},
                           connect_timeout=12, default_duration=8, api_key="new-key")
        self.assertFalse(self.runtime.apply_settings(settings).result(timeout=3))
        self.assertEqual(self.runtime.alarms.settings.commands["NEW"], "01")
        self.assertEqual(self.runtime.alarms.client.connect_timeout, 12)
        self.assertEqual(self.runtime.settings.api_key, "new-key")
        self.assertEqual(self.runtime.repository.settings.default_duration, 8)

    def test_server_address_is_deferred_until_restart(self):
        settings = replace(self.original, host="0.0.0.0", port=9000, connect_timeout=12)
        self.assertTrue(self.runtime.apply_settings(settings).result(timeout=3))
        self.assertEqual((self.runtime.settings.host, self.runtime.settings.port), ("127.0.0.1", 7000))
        self.assertEqual(self.runtime.settings.connect_timeout, 12)

    def test_running_request_blocks_application(self):
        self.history.create("active", {"source": "api"})
        self.history.update("active", status="running")
        with self.assertRaisesRegex(ValueError, "Chờ"):
            self.runtime.apply_settings(replace(self.original, default_duration=9)).result(timeout=3)
        self.assertIs(self.runtime.settings, self.original)


if __name__ == "__main__":
    unittest.main()
