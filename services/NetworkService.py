import requests
import logging

logger = logging.getLogger(__name__)

class NetworkService:
    def __init__(self, ip, port, timeout=5):
        self.base_url = f"http://{ip}:{port}/ch9120"
        self.timeout = timeout

    def fetch_lines(self):
        url = f"{self.base_url}/get-all-lines"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            try:
                data = response.json()
                return [item["line"] for item in data.get("lines", [])]
            except ValueError:
                logger.error("Invalid JSON in fetch_lines")
                return []   # luôn trả list
        except requests.RequestException as e:
            logger.error(f"fetch_lines failed: {e}")
            return [] 

    def fetch_devices_by_line(self, line):
        url = (
            f"{self.base_url}/get-all-devices"
            if line == "All"
            else f"{self.base_url}/get_devices_by_line/{line}"
        )
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            try:
                data = response.json()
                return data.get("devices", [])
            except ValueError:
                logger.error("Invalid JSON in fetch_devices_by_line")
                return [], "Invalid JSON response."
        except requests.RequestException as e:
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
