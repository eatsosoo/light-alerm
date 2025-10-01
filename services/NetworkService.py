import requests
import logging
from configs.config import Config
from models.CH9120Model import CH9120Model

logger = logging.getLogger(__name__)
SSL = Config.get_ssl()
class NetworkService:
    def __init__(self, ip, port, timeout=5):
        scheme = "https" if SSL["ENABLED"] else "http"
        self.base_url = f"{scheme}://{ip}:{port}/ch9120"
        self.timeout = timeout

    def fetch_devices_by_line(self, line):
        try:
            devices = CH9120Model.get_by_line('' if line == "All" else line)
            logger.info("Fetched %s devices for line %s", len(devices), line)
            return devices
        except Exception as e:
            logger.error(f"fetch_devices_by_line failed: {e}")
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
            logger.error(f"send_command failed: {msg}")
            return False, msg
