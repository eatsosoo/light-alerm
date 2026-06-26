import requests
from configs.config import Config
from models.CH9120Model import CH9120Model
import asyncio
import threading
from services.LoggerService import setup_logger

logger = setup_logger(__name__)
SSL = Config.get_ssl()
class NetworkService:
    def __init__(self, ip, port, timeout=5):
        scheme = "https" if SSL["ENABLED"] else "http"
        self.base_url = f"{scheme}://{ip}:{port}/ch9120"
        self.timeout = timeout

    def fetch_devices_by_line(self, line):
        try:
            devices = CH9120Model.get_by_line('' if line == "All" else line)
            logger.info("Loaded device list | line=%s | devices=%s", line, len(devices))
            return devices
        except Exception as e:
            logger.exception("Failed to load devices | line=%s | error=%s", line, e)
            return []

    def send_command(self, line, command, duration=None):
        if line == "All":
            url = f"{self.base_url}/send-command/all"
        else:
            url = f"{self.base_url}/send-command/line"

        payload = {
            "mode": command,
            "duration": int(duration) if duration else None,
        }
        if line != "All":
            payload["line"] = line

        # Xoá key có giá trị None
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True, None
        except requests.RequestException as e:
            try:
                msg = response.json().get("message", str(e))
            except Exception:
                msg = str(e)
            logger.error("HTTP command request failed | line=%s | command=%s | error=%s", line, command, msg)
            return False, msg
        
    def send_alert_from_app(self, line, command, duration=None):
        def run_command():
            try:
                if line == "All":
                    hex_command = Config.get_commands()[command]
                    asyncio.run(CH9120Model.send_command_to_all(hex_command, duration))
                else:
                    asyncio.run(CH9120Model.send_command_by_line(line, command, duration))
            except Exception as e:
                logger.exception(
                    "Application command worker failed | line=%s | command=%s | error=%s",
                    line,
                    command,
                    e,
                )
        
        try:
            thread = threading.Thread(target=run_command)
            thread.start()
        except Exception as e:
            logger.exception(
                "Failed to start command worker | line=%s | command=%s | error=%s",
                line,
                command,
                e,
            )

    def send_alert_to_devices(self, devices, command, duration=None):
        target_devices = list(devices)

        def run_command():
            try:
                asyncio.run(
                    CH9120Model.send_command_to_devices(
                        target_devices,
                        command,
                        duration,
                        scope="ui-visible",
                    )
                )
            except Exception as e:
                logger.exception(
                    "Application command worker failed | scope=ui-visible | command=%s | devices=%s | error=%s",
                    command,
                    len(target_devices),
                    e,
                )

        try:
            thread = threading.Thread(target=run_command)
            thread.start()
        except Exception as e:
            logger.exception(
                "Failed to start command worker | scope=ui-visible | command=%s | devices=%s | error=%s",
                command,
                len(target_devices),
                e,
            )
