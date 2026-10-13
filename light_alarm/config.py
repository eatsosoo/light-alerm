"""Load application settings without opening network or database connections."""

import os
import sys
import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def application_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    directory: Path
    host: str
    port: int
    commands: dict
    database: dict = field(repr=False)
    ssl_enabled: bool = False
    cert_path: str = ""
    key_path: str = ""
    api_key: str = field(default="", repr=False)
    default_duration: int = 5
    connect_timeout: float = 5.0
    response_timeout: float = 5.0
    database_timeout: int = 5
    config_path: Path = field(default=None, repr=False)

    @property
    def log_directory(self):
        return self.directory / "logs"

    @classmethod
    def load(cls, path=None):
        config_path = Path(path or os.environ.get("LIGHT_ALARM_CONFIG") or application_directory() / "config.yaml").resolve()
        with config_path.open(encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
        return cls.from_mapping(data, config_path)

    @classmethod
    def from_mapping(cls, data, config_path):
        config_path = Path(config_path).resolve()
        if not isinstance(data, dict):
            raise ValueError("Configuration must contain a YAML mapping.")

        device = data.get("CH9120") or {}
        if not isinstance(device, dict):
            raise ValueError("CH9120 must be a YAML mapping.")
        commands = device.get("COMMANDS", {})
        if not isinstance(commands, dict) or "TURN_OFF" not in commands:
            raise ValueError("CH9120.COMMANDS must include TURN_OFF.")
        for name, command in commands.items():
            if not isinstance(name, str) or not name.strip() or name != name.strip() or not isinstance(command, str):
                raise ValueError("Command names and HEX values must be quoted strings.")
            try:
                if not bytes.fromhex(command):
                    raise ValueError("Empty command")
            except ValueError as error:
                raise ValueError(f"Invalid HEX command: {name}") from error

        database = data.get("DATABASE", {})
        required = ("SQL_DRIVER", "SQL_SERVER", "SQL_DATABASE", "SQL_USER")
        if not isinstance(database, dict):
            raise ValueError("DATABASE must be a YAML mapping.")
        missing = [key for key in required if not isinstance(database.get(key), str) or not database[key].strip()]
        if "SQL_PASSWORD" not in database or not isinstance(database["SQL_PASSWORD"], str):
            missing.append("SQL_PASSWORD")
        if missing:
            raise ValueError("DATABASE: thiếu hoặc sai giá trị " + ", ".join(missing))
        ssl = data.get("SSL") or {}
        if not isinstance(ssl, dict):
            raise ValueError("SSL must be a YAML mapping.")
        enabled = ssl.get("ENABLED", False)
        if not isinstance(enabled, bool):
            raise ValueError("SSL.ENABLED must be true or false.")

        def resolve_file(value):
            return str((config_path.parent / value).resolve()) if value else ""

        cert = resolve_file(ssl.get("CERT_PATH", ""))
        key = resolve_file(ssl.get("KEY_PATH", ""))
        if enabled and (not Path(cert).is_file() or not Path(key).is_file()):
            raise ValueError("SSL certificate and key files are required when SSL is enabled.")
        port_value = data.get("PORT", 5000)
        if isinstance(port_value, bool) or not isinstance(port_value, (int, str)):
            raise ValueError("PORT must be an integer.")
        port = int(port_value)
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535.")
        timing = data.get("TIMING") or {}
        if not isinstance(timing, dict):
            raise ValueError("TIMING must be a YAML mapping.")

        def number(key, default, integer=False, allow_zero=False):
            value = timing.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                raise ValueError(f"TIMING.{key} must be a number.")
            converted = float(value)
            if not math.isfinite(converted) or converted < 0 or (converted == 0 and not allow_zero):
                raise ValueError(f"TIMING.{key} must be {'non-negative' if allow_zero else 'positive'}.")
            if integer and not converted.is_integer():
                raise ValueError(f"TIMING.{key} must be an integer.")
            return int(converted) if integer else converted

        return cls(
            directory=config_path.parent,
            host=str(data.get("HOST_IP") or "127.0.0.1"),
            port=port,
            commands=dict(commands),
            database=dict(database),
            ssl_enabled=enabled,
            cert_path=cert,
            key_path=key,
            api_key=os.environ.get("LIGHT_ALARM_API_KEY") or str(data.get("API_KEY") or ""),
            default_duration=number("DEFAULT_DURATION", 5, integer=True, allow_zero=True),
            connect_timeout=number("CONNECT_TIMEOUT", 5),
            response_timeout=number("RESPONSE_TIMEOUT", 5),
            database_timeout=number("DATABASE_TIMEOUT", 5, integer=True),
            config_path=config_path,
        )
