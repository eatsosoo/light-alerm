"""Construct shared dependencies at application startup."""

import asyncio
from dataclasses import dataclass, replace

from light_alarm.config import Settings
from light_alarm.devices.ch9120_client import CH9120Client
from light_alarm.logging_setup import configure_logging
from light_alarm.repositories.device_repository import DeviceRepository
from light_alarm.services.alarm_service import AlarmService
from light_alarm.services.background_worker import BackgroundWorker
from light_alarm.services.request_history import RequestHistory


class DeviceActions:
    """Desktop adapter returning futures without accessing Tk widgets."""

    def __init__(self, repository, alarms, worker):
        self.repository = repository
        self.alarms = alarms
        self.worker = worker

    def load_devices(self):
        return self.worker.submit(asyncio.to_thread(self.repository.get_all))

    def send_devices(self, devices, mode, duration=None):
        duration = self.alarms.validate_command(mode, duration)
        targets = list(devices)
        lines = sorted({str(device.get("line") or "") for device in targets})
        job_id, future = self.worker.submit_tracked(
            self.alarms.send_devices(targets, mode, duration),
            {"source": "desktop", "mode": mode, "scope": ", ".join(lines),
             "duration": duration, "target_count": len(targets)},
        )
        return job_id, future


@dataclass
class Runtime:
    settings: Settings
    repository: DeviceRepository
    alarms: AlarmService
    worker: BackgroundWorker
    actions: DeviceActions

    @classmethod
    def create(cls, config_path=None):
        settings = Settings.load(config_path)
        history = RequestHistory()
        configure_logging(settings.log_directory, history)
        repository = DeviceRepository(settings)
        alarms = AlarmService(repository, CH9120Client(settings), settings, history)
        worker = BackgroundWorker(history)
        return cls(settings, repository, alarms, worker, DeviceActions(repository, alarms, worker))

    def close(self):
        self.worker.close()

    def apply_settings(self, settings):
        async def apply():
            if any(item["status"] in ("queued", "running") for item in self.worker.history.list()):
                raise ValueError("Cấu hình đã lưu. Chờ các yêu cầu kết thúc rồi bấm Áp dụng lại.")
            old = self.settings
            restart = any(getattr(settings, key) != getattr(old, key)
                          for key in ("host", "port", "ssl_enabled", "cert_path", "key_path"))
            active = replace(settings, host=old.host, port=old.port, ssl_enabled=old.ssl_enabled,
                             cert_path=old.cert_path, key_path=old.key_path)
            self.repository.settings = active
            self.alarms.settings = active
            self.alarms.client = CH9120Client(active)
            self.settings = active
            return restart
        return self.worker.submit(apply())
