"""API integration checks using real jobs/services and in-memory I/O adapters.

No configuration, SQL connection, TCP device or desktop window is used.
"""

import asyncio
import copy
import logging
import threading
import time
import unittest
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager
from types import SimpleNamespace

from light_alarm.api import create_app
from light_alarm.devices.ch9120_client import CH9120Client
from light_alarm.services.alarm_service import AlarmService
from light_alarm.services.background_worker import BackgroundWorker
from light_alarm.services.request_history import RequestHistory, request_id


PREFIX = "/ch9120"


class MemoryRepository:
    def __init__(self):
        self.devices = [
            dict(keyid=1, station_name="Station A", ip="fake-a", port=6800, line="LINE1"),
            dict(keyid=2, station_name="Station B", ip="fake-b", port=6800, line="LINE1"),
            dict(keyid=3, station_name="Station C", ip="fake-c", port=6800, line="LINE10"),
            dict(keyid=4, station_name="Office", ip="fake-office", port=6800, line="OFFICE"),
        ]

    def get_all(self):
        return copy.deepcopy(self.devices)

    def get_by_id(self, keyid):
        return next((copy.deepcopy(item) for item in self.devices if item["keyid"] == keyid), None)

    def get_by_line(self, line):
        return [copy.deepcopy(item) for item in self.devices if item["line"] == line]

    def get_lines(self):
        return [{"line": line} for line in sorted({item["line"] for item in self.devices})]

    def get_device_office(self):
        return self.get_by_line("OFFICE")

    def create(self, user, station, ip, port, line, remark=None):
        keyid = max((item["keyid"] for item in self.devices), default=0) + 1
        self.devices.append(dict(keyid=keyid, user_code_created=user, station_name=station,
                                 ip=ip, port=port, line=line, remark=remark))
        return 1

    def update(self, keyid, user, station, ip, port, line, remark=None):
        for item in self.devices:
            if item["keyid"] == keyid:
                item.update(user_code_updated=user, station_name=station, ip=ip,
                            port=port, line=line, remark=remark)
                return 1
        return 0

    def delete(self, keyid):
        before = len(self.devices)
        self.devices = [item for item in self.devices if item["keyid"] != keyid]
        return before - len(self.devices)


class MemoryDeviceClient:
    def __init__(self):
        self.calls = []
        self.fail_endpoints = set()
        self.started = threading.Event()
        self.lock = threading.Lock()

    @asynccontextmanager
    async def connection(self, ip, port):
        if ip in self.fail_endpoints:
            raise OSError("Simulated unreachable device")
        client = self

        class Connection:
            async def write(self, command):
                with client.lock:
                    client.calls.append((request_id.get(), ip, port, command))
                client.started.set()
                return asyncio.get_running_loop().time()

            async def read(self, timeout):
                return "aabb"

        yield Connection()

    async def send_once(self, ip, port, command):
        async with self.connection(ip, port) as connection:
            await connection.write(command)
            return await connection.read(0)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        self.device_client = MemoryDeviceClient()
        self.history = RequestHistory()
        self.settings = SimpleNamespace(
            api_key="", default_duration=1, response_timeout=0.05,
            commands={"ALARM": "01", "FLASH_ONLY": "02", "OFFICE": "03", "TURN_OFF": "00", "READ_ALL": "04"},
        )
        self.logger = logging.getLogger("light_alarm")
        self.old_level, self.old_propagate = self.logger.level, self.logger.propagate
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.history)
        self.worker = BackgroundWorker(self.history)
        self.alarms = AlarmService(self.repository, self.device_client, self.settings, self.history)
        self.runtime = SimpleNamespace(settings=self.settings, repository=self.repository,
                                       alarms=self.alarms, worker=self.worker)
        self.app = create_app(self.runtime)
        self.client = self.app.test_client()

    def tearDown(self):
        self.worker.close()
        self.logger.removeHandler(self.history)
        self.history.close()
        self.logger.setLevel(self.old_level)
        self.logger.propagate = self.old_propagate

    def send(self, path="/send-command/line", **payload):
        return self.client.post(PREFIX + path, json={"mode": "ALARM", "duration": 0, "line": "LINE1", **payload})

    def wait_job(self, response, timeout=3):
        self.assertEqual(response.status_code, 202, response.get_json())
        accepted = response.get_json()
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(response.headers["Location"], accepted["status_url"])
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.client.get(accepted["status_url"])
            self.assertEqual(status.status_code, 200)
            job = status.get_json()
            if job["status"] not in ("queued", "running"):
                self.assertEqual(job["job_id"], accepted["job_id"])
                self.assertIsNotNone(job["finished_at"])
                return job
            time.sleep(0.005)
        self.fail(f"Job did not finish: {accepted['job_id']}")

    def fields(self, **overrides):
        return {"user_code_created": "tester", "station_name": "New station", "ip": "fake-new",
                "port": "6800", "line": "LINE2", "remark": None, **overrides}

    def test_read_all_devices_and_lines(self):
        response = self.client.get(PREFIX + "/get-all-devices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["devices"]), 4)
        lines = self.client.get(PREFIX + "/get-all-lines").get_json()["lines"]
        self.assertEqual(lines, [{"line": "LINE1"}, {"line": "LINE10"}, {"line": "OFFICE"}])

    def test_read_single_device_and_missing_device(self):
        response = self.client.get(PREFIX + "/get_device/1")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json()["device"], dict)
        self.assertEqual(response.get_json()["device"]["keyid"], 1)
        self.assertEqual(self.client.get(PREFIX + "/get_device/999").status_code, 404)

    def test_read_line_uses_exact_match(self):
        response = self.client.get(PREFIX + "/get_devices_by_line/LINE1")
        self.assertEqual([item["keyid"] for item in response.get_json()["devices"]], [1, 2])
        self.assertEqual(self.client.get(PREFIX + "/get_devices_by_line/missing").get_json()["devices"], [])

    def test_create_update_delete_lifecycle(self):
        response = self.client.post(PREFIX + "/create_device", json=self.fields())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.repository.get_by_id(5)["port"], 6800)
        data = self.fields(station_name="Updated", user_code_updated=123)
        response = self.client.put(PREFIX + "/update_device/5", json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repository.get_by_id(5)["station_name"], "Updated")
        self.assertEqual(self.client.delete(PREFIX + "/delete_device/5").status_code, 200)
        self.assertEqual(self.client.get(PREFIX + "/get_device/5").status_code, 404)

    def test_update_delete_missing_device(self):
        self.assertEqual(self.client.put(PREFIX + "/update_device/999",
                         json=self.fields(user_code_updated="tester")).status_code, 404)
        self.assertEqual(self.client.delete(PREFIX + "/delete_device/999").status_code, 404)

    def test_invalid_device_fields_are_rejected_without_writes(self):
        cases = [{"port": value} for value in (None, True, 0, -1, 65536, 1.5, "1.5", "bad")]
        cases += [{key: value} for key in ("station_name", "ip", "line", "user_code_created")
                  for value in (None, "", "  ", True, [])]
        cases += [{"remark": 123}]
        for fields in cases:
            with self.subTest(fields=fields):
                response = self.client.post(PREFIX + "/create_device", json=self.fields(**fields))
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(len(self.repository.devices), 4)

    def test_invalid_json_bodies(self):
        for data in (None, [], "text", 12, True):
            with self.subTest(data=data):
                response = self.client.post(PREFIX + "/send-command/all", data=__import__("json").dumps(data),
                                            content_type="application/json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(PREFIX + "/send-command/all", data="{",
                                         content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(PREFIX + "/send-command/all", data="text",
                                         content_type="text/plain").status_code, 415)

    def test_body_size_limit(self):
        response = self.client.post(PREFIX + "/send-command/all", json={"padding": "x" * 70000})
        self.assertEqual(response.status_code, 413)

    def test_invalid_modes_are_rejected_before_job_creation(self):
        for mode in (None, "missing", [], {}, True):
            with self.subTest(mode=mode):
                self.assertEqual(self.send(mode=mode).status_code, 400)
        self.assertEqual(self.history.list(), [])

    def test_invalid_duration_is_rejected_before_job_creation(self):
        for duration in (-1, True, 1.5, "-1", "1.5", "abc", [], {}, "１"):
            with self.subTest(duration=duration):
                self.assertEqual(self.send(duration=duration).status_code, 400)
        self.assertEqual(self.history.list(), [])

    def test_invalid_line_is_rejected(self):
        for line in (None, "", "  ", True, []):
            with self.subTest(line=line):
                self.assertEqual(self.send(line=line).status_code, 400)

    def test_all_command_and_job_metadata(self):
        job = self.wait_job(self.send("/send-command/all"))
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"]["success"], 4)
        self.assertEqual(job["target_count"], 4)
        self.assertEqual((job["source"], job["scope"], job["mode"]), ("api", "All", "ALARM"))
        self.assertNotIn("events", job)

    def test_line_command_targets_every_device_on_exact_line(self):
        job = self.wait_job(self.send())
        self.assertEqual(job["result"]["success"], 2)
        self.assertEqual({item["ip"] for item in job["result"]["devices"]}, {"fake-a", "fake-b"})

    def test_zero_duration_sends_on_then_off(self):
        job = self.wait_job(self.send(line="LINE10", duration=0))
        calls = [item[3] for item in self.device_client.calls if item[0] == job["job_id"]]
        self.assertEqual(calls, ["01", "00"])
        self.assertEqual(job["duration"], 0)

    def test_default_and_string_duration(self):
        response = self.client.post(PREFIX + "/send-command/line", json={"line": "LINE10", "mode": "TURN_OFF"})
        self.assertEqual(self.wait_job(response)["duration"], 1)
        self.assertEqual(self.wait_job(self.send(line="LINE10", duration="0"))["duration"], 0)

    def test_device_office_targets_entire_line_and_office(self):
        job = self.wait_job(self.send("/send-command/device-office"))
        self.assertEqual(job["result"]["success"], 3)
        office = next(item for item in job["result"]["devices"] if item["line"] == "OFFICE")
        self.assertEqual(office["mode"], "OFFICE")

    def test_office_targets_are_deduplicated(self):
        job = self.wait_job(self.send("/send-command/device-office", line="OFFICE"))
        self.assertEqual(job["target_count"], 1)

    def test_missing_office_mode_is_rejected(self):
        del self.settings.commands["OFFICE"]
        self.assertEqual(self.send("/send-command/device-office").status_code, 400)
        self.assertEqual(self.history.list(), [])

    def test_turn_off_does_not_require_office_mode(self):
        del self.settings.commands["OFFICE"]
        job = self.wait_job(self.send("/send-command/device-office", mode="TURN_OFF"))
        self.assertEqual(job["result"]["success"], 3)
        self.assertTrue(all(item[3] == "00" for item in self.device_client.calls))

    def test_legacy_get_and_post_turn_off_routes(self):
        for method in ("get", "post"):
            with self.subTest(method=method):
                job = self.wait_job(getattr(self.client, method)(PREFIX + "/send-command/turn-off-all/LINE1"))
                self.assertEqual(job["result"]["success"], 3)

    def test_missing_targets_produce_failed_job(self):
        job = self.wait_job(self.send(line="missing"))
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(job["result"])
        self.assertIn("see system logs", job["message"])
        self.assertIn("No target devices", self.history.get(job["job_id"])["message"])

    def test_partial_device_failure(self):
        self.device_client.fail_endpoints.add("fake-b")
        job = self.wait_job(self.send())
        self.assertEqual(job["status"], "partial")
        self.assertEqual(job["counts"], dict(success=1, failure=1, superseded=0))

    def test_all_devices_failed(self):
        self.device_client.fail_endpoints.update(("fake-a", "fake-b"))
        self.assertEqual(self.wait_job(self.send())["status"], "failed")

    def test_database_failure_is_logged_and_hidden_in_response(self):
        def broken():
            raise RuntimeError("private database failure details")
        self.repository.get_all = broken
        response = self.client.get(PREFIX + "/get-all-devices")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private", response.get_data(as_text=True))
        job = self.wait_job(self.send("/send-command/all"))
        self.assertEqual(job["status"], "failed")
        self.assertNotIn("private", job["message"])

    def test_authentication_covers_every_route(self):
        self.settings.api_key = "test-secret"
        for rule in self.app.url_map.iter_rules():
            if not rule.rule.startswith(PREFIX):
                continue
            path = rule.rule.replace("<int:keyid>", "1").replace("<line>", "LINE1").replace("<job_id>", "missing")
            for method in rule.methods - {"HEAD", "OPTIONS"}:
                with self.subTest(path=path, method=method):
                    self.assertEqual(self.client.open(path, method=method).status_code, 401)
        self.assertEqual(self.client.get(PREFIX + "/get-all-devices", headers={"X-API-Key": "wrong"}).status_code, 401)
        self.assertEqual(self.client.get(PREFIX + "/get-all-devices", headers={"X-API-Key": "test-secret"}).status_code, 200)

    def test_authorized_command_and_job_poll(self):
        self.settings.api_key = "test-secret"
        headers = {"X-API-Key": "test-secret"}
        response = self.client.post(PREFIX + "/send-command/line", json={"line": "LINE10", "mode": "TURN_OFF"}, headers=headers)
        self.assertEqual(response.status_code, 202)
        url = response.get_json()["status_url"]
        self.assertEqual(self.client.get(url).status_code, 401)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            job = self.client.get(url, headers=headers).get_json()
            if job["status"] == "completed":
                break
            time.sleep(0.005)
        self.assertEqual(job["status"], "completed")

    def test_unknown_job_route_and_wrong_method(self):
        self.assertEqual(self.client.get(PREFIX + "/jobs/missing").status_code, 404)
        self.assertEqual(self.client.get(PREFIX + "/missing").status_code, 404)
        self.assertEqual(self.client.get(PREFIX + "/send-command/all").status_code, 405)

    def test_request_logs_do_not_mix_concurrent_jobs(self):
        first = self.send(line="LINE1")
        second = self.send(line="LINE10", mode="FLASH_ONLY")
        a, b = self.wait_job(first), self.wait_job(second)
        self.assertNotEqual(a["job_id"], b["job_id"])
        a_events = "\n".join(event["message"] for event in self.history.get(a["job_id"])["events"])
        b_events = "\n".join(event["message"] for event in self.history.get(b["job_id"])["events"])
        self.assertIn("fake-a", a_events)
        self.assertNotIn("fake-c", a_events)
        self.assertIn("fake-c", b_events)
        self.assertNotIn("fake-a", b_events)

    def test_new_alarm_supersedes_old_and_turns_off_before_new_on(self):
        old = self.send(line="LINE10", duration=1)
        self.assertTrue(self.device_client.started.wait(2))
        new = self.send(line="LINE10", duration=0, mode="FLASH_ONLY")
        self.assertEqual(self.wait_job(old)["status"], "superseded")
        self.assertEqual(self.wait_job(new)["status"], "completed")
        self.assertEqual([item[3] for item in self.device_client.calls], ["01", "00", "02", "00"])

    def test_read_all_does_not_replace_alarm_or_send_off(self):
        old = self.send(line="LINE10", duration=1)
        self.assertTrue(self.device_client.started.wait(2))
        read = self.wait_job(self.send(line="LINE10", mode="READ_ALL"))
        self.assertEqual(read["status"], "completed")
        self.assertEqual([item[3] for item in self.device_client.calls if item[0] == read["job_id"]], ["04"])
        self.assertIn(self.worker.get_job(old.get_json()["job_id"])["status"], ("queued", "running"))
        self.wait_job(self.send(line="LINE10", mode="TURN_OFF"))
        self.assertEqual(self.wait_job(old)["status"], "superseded")

    def test_shutdown_cancels_job_and_attempts_turn_off(self):
        response = self.send(line="LINE10", duration=10)
        self.assertTrue(self.device_client.started.wait(2))
        self.worker.close()
        job = self.client.get(response.get_json()["status_url"]).get_json()
        self.assertEqual(job["status"], "cancelled")
        self.assertEqual([item[3] for item in self.device_client.calls], ["01", "00"])
        self.assertFalse(self.worker.thread.is_alive())

    def test_completed_history_retention_and_expired_job(self):
        self.history.limit = 2
        jobs = [self.wait_job(self.send(line="LINE10", mode="TURN_OFF")) for _ in range(3)]
        self.assertEqual(len(self.history.list()), 2)
        self.assertEqual(self.client.get(PREFIX + "/jobs/" + jobs[0]["job_id"]).status_code, 404)
        self.assertEqual(self.client.get(PREFIX + "/jobs/" + jobs[-1]["job_id"]).status_code, 200)

    def test_real_connection_timeout_has_clear_error_and_no_traceback(self):
        self.settings.connect_timeout = 0.02
        self.alarms.client = CH9120Client(self.settings)

        async def stalled_connection(*args, **kwargs):
            await asyncio.sleep(60)

        with patch("light_alarm.devices.ch9120_client.asyncio.open_connection",
                   new=AsyncMock(side_effect=stalled_connection)):
            job = self.wait_job(self.send(line="LINE10"))
        self.assertEqual(job["status"], "failed")
        error = job["result"]["devices"][0]["error"]
        self.assertIn("fake-c:6800", error)
        self.assertIn("0.02", error)
        events = "\n".join(event["message"] for event in self.history.get(job["job_id"])["events"])
        self.assertNotIn("Traceback", events)
        self.assertNotIn("CancelledError", events)

    def test_connection_refused_has_clear_error_without_traceback(self):
        self.settings.connect_timeout = 0.02
        self.alarms.client = CH9120Client(self.settings)
        with patch("light_alarm.devices.ch9120_client.asyncio.open_connection",
                   new=AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))):
            job = self.wait_job(self.send(line="LINE10"))
        self.assertEqual(job["status"], "failed")
        self.assertIn("fake-c:6800", job["result"]["devices"][0]["error"])
        self.assertIn("Connection refused", job["result"]["devices"][0]["error"])
        self.assertFalse(any("Traceback" in event["message"] for event in self.history.get(job["job_id"])["events"]))

    def test_shutdown_while_connecting_remains_cancelled_not_failed(self):
        self.settings.connect_timeout = 60
        self.alarms.client = CH9120Client(self.settings)
        connecting = threading.Event()

        async def stalled_connection(*args, **kwargs):
            connecting.set()
            await asyncio.sleep(60)

        with patch("light_alarm.devices.ch9120_client.asyncio.open_connection",
                   new=AsyncMock(side_effect=stalled_connection)):
            response = self.send(line="LINE10")
            self.assertTrue(connecting.wait(2))
            self.worker.close()
        job = self.client.get(response.get_json()["status_url"]).get_json()
        self.assertEqual(job["status"], "cancelled")
        self.assertFalse(any(event["level"] == "ERROR" for event in self.history.get(job["job_id"])["events"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
