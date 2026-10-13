"""Construct shared dependencies at application startup."""

import asyncio
from dataclasses import dataclass

from light_alarm.config import Settings
from light_alarm.devices.ch9120_client import CH9120Client
from light_alarm.logging_setup import configure_logging
from light_alarm.repositories.device_repository import DeviceRepository
from light_alarm.services.alarm_service import AlarmService
from light_alarm.services.background_worker import BackgroundWorker


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
        return self.worker.submit(self.alarms.send_devices(list(devices), mode, duration))


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
        configure_logging(settings.log_directory)
        repository = DeviceRepository(settings)
        alarms = AlarmService(repository, CH9120Client(settings), settings)
        worker = BackgroundWorker()
        return cls(settings, repository, alarms, worker, DeviceActions(repository, alarms, worker))

    def close(self):
        self.worker.close()
