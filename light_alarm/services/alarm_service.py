"""Coordinate device targets and replace earlier alarms per TCP endpoint."""

import asyncio
import logging

from light_alarm.services.request_history import request_id

logger = logging.getLogger(__name__)


class AlarmService:
    def __init__(self, repository, client, settings, history):
        self.repository = repository
        self.client = client
        self.settings = settings
        self.history = history
        self._active = {}
        self._locks = {}

    def validate_command(self, mode, duration=None):
        if not isinstance(mode, str) or mode not in self.settings.commands:
            raise ValueError("Invalid mode.")
        if duration is None or duration == "":
            duration = self.settings.default_duration
        if isinstance(duration, bool):
            raise ValueError("Duration must be a non-negative integer.")
        if isinstance(duration, str):
            if not duration.isascii() or not duration.isdigit():
                raise ValueError("Duration must be a non-negative integer.")
            duration = int(duration)
        if not isinstance(duration, int) or duration < 0:
            raise ValueError("Duration must be a non-negative integer.")
        return duration

    @staticmethod
    def validate_line(line):
        if not isinstance(line, str) or not line.strip():
            raise ValueError("A non-empty line is required.")
        return line.strip()

    async def send_all(self, mode, duration=None):
        duration = self.validate_command(mode, duration)
        devices = await asyncio.to_thread(self.repository.get_all)
        return await self.send_devices(devices, mode, duration)

    async def send_line(self, line, mode, duration=None):
        line = self.validate_line(line)
        duration = self.validate_command(mode, duration)
        devices = await asyncio.to_thread(self.repository.get_by_line, line)
        return await self.send_devices(devices, mode, duration)

    async def send_device_office(self, line, mode, duration=None):
        line = self.validate_line(line)
        duration = self.validate_command(mode, duration)
        office_mode = "TURN_OFF" if mode == "TURN_OFF" else "OFFICE"
        self.validate_command(office_mode, duration)
        devices = await asyncio.to_thread(self.repository.get_by_line, line)
        if not devices:
            raise ValueError("No devices found for this line.")
        offices = await asyncio.to_thread(self.repository.get_device_office)
        targets = [(device, mode) for device in devices]
        # An endpoint appears once, even when the requested line is OFFICE.
        targets.extend((device, office_mode) for device in offices)
        return await self._send_targets(targets, duration)

    async def send_devices(self, devices, mode, duration=None):
        duration = self.validate_command(mode, duration)
        return await self._send_targets([(device, mode) for device in devices], duration)

    async def _send_targets(self, targets, duration):
        unique = {}
        for device, mode in targets:
            endpoint = (str(device["ip"]).strip(), int(device["port"]))
            if not endpoint[0] or not 1 <= endpoint[1] <= 65535:
                raise ValueError("Invalid device endpoint.")
            unique.setdefault(endpoint, (dict(device), mode))
        if not unique:
            raise ValueError("No target devices found.")
        self.history.update(request_id.get(), target_count=len(unique))
        logger.info("Targets resolved | devices=%s | duration=%ss", len(unique), duration)
        results = await asyncio.gather(*(
            self._replace(endpoint, device, mode, duration)
            for endpoint, (device, mode) in unique.items()
        ))
        summary = {"success": 0, "failure": 0, "superseded": 0, "devices": results}
        for result in results:
            summary[result["status"]] += 1
        logger.info("Command finished | success=%s | failure=%s | superseded=%s",
                    summary["success"], summary["failure"], summary["superseded"])
        return summary

    async def _replace(self, endpoint, device, mode, duration):
        if mode == "READ_ALL":
            return await self._send(device, mode, duration)
        lock = self._locks.setdefault(endpoint, asyncio.Lock())
        async with lock:
            previous = self._active.get(endpoint)
            if previous and not previous.done():
                logger.info("Replacing active command | endpoint=%s:%s", *endpoint)
                if not previous.cancelling():
                    previous.cancel()
                # Complete the previous TURN_OFF before starting the next alarm.
                await asyncio.shield(asyncio.gather(previous, return_exceptions=True))
            task = asyncio.create_task(self._send(device, mode, duration))
            self._active[endpoint] = task
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling():
                if not task.done() and not task.cancelling():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
            return self._result(device, "superseded", mode)
        finally:
            if self._active.get(endpoint) is task and task.done():
                self._active.pop(endpoint, None)

    @staticmethod
    def _result(device, status, mode, response="", error=None):
        return {
            "station": device.get("station_name"), "line": device.get("line"),
            "ip": device["ip"], "port": device["port"], "mode": mode,
            "status": status, "response": response, "error": error,
        }

    async def _send(self, device, mode, duration):
        try:
            logger.info("Sending command | station=%s | line=%s | endpoint=%s:%s | mode=%s",
                        device.get("station_name"), device.get("line"), device["ip"], device["port"], mode)
            timed = mode not in ("TURN_OFF", "READ_ALL")
            async with self.client.connection(device["ip"], device["port"]) as connection:
                attempted = False
                try:
                    # A failed drain may still have delivered bytes to the device.
                    attempted = True
                    started = await connection.write(self.settings.commands[mode])
                    logger.info("Command written | endpoint=%s:%s | mode=%s", device["ip"], device["port"], mode)
                    elapsed = asyncio.get_running_loop().time() - started
                    timeout = self.settings.response_timeout
                    if timed:
                        timeout = min(timeout, max(0, duration - elapsed))
                    response = await connection.read(timeout)
                    if timed:
                        remaining = duration - (asyncio.get_running_loop().time() - started)
                        if remaining > 0:
                            await asyncio.sleep(remaining)
                finally:
                    if attempted and timed:
                        await self._turn_off(connection, device)
            logger.info("Command sent | endpoint=%s:%s | mode=%s", device["ip"], device["port"], mode)
            return self._result(device, "success", mode, response=response)
        except asyncio.CancelledError:
            logger.info("Device command cancelled or replaced | endpoint=%s:%s | mode=%s",
                        device["ip"], device["port"], mode)
            raise
        except (OSError, asyncio.TimeoutError) as error:
            message = str(error) or f"Thao tác TCP tới {device['ip']}:{device['port']} hết thời gian chờ."
            logger.error("Command failed | endpoint=%s:%s | mode=%s | error=%s",
                         device["ip"], device["port"], mode, message)
            return self._result(device, "failure", mode, error=message)
        except Exception as error:
            logger.exception("Command failed | endpoint=%s:%s | mode=%s", device["ip"], device["port"], mode)
            return self._result(device, "failure", mode, error=str(error))

    async def _turn_off(self, connection, device):
        command = self.settings.commands["TURN_OFF"]
        logger.info("Sending automatic TURN_OFF | endpoint=%s:%s", device["ip"], device["port"])
        try:
            await connection.write(command)
        except (OSError, RuntimeError, asyncio.TimeoutError):
            logger.warning("Retrying TURN_OFF on a new connection | endpoint=%s:%s",
                           device["ip"], device["port"])
            await self.client.send_once(device["ip"], device["port"], command)
