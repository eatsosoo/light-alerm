"""Load application settings without opening network or database connections."""

import os
import sys
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

    @property
    def log_directory(self):
        return self.directory / "logs"

    @classmethod
    def load(cls, path=None):
        config_path = Path(path or os.environ.get("LIGHT_ALARM_CONFIG") or application_directory() / "config.yaml").resolve()
        with config_path.open(encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file)
        if not isinstance(data, dict):
            raise ValueError("Configuration must contain a YAML mapping.")

        commands = data.get("CH9120", {}).get("COMMANDS", {})
        if not isinstance(commands, dict) or "TURN_OFF" not in commands:
            raise ValueError("CH9120.COMMANDS must include TURN_OFF.")
        for name, command in commands.items():
            if not isinstance(name, str) or not isinstance(command, str):
                raise ValueError("Command names and HEX values must be quoted strings.")
            try:
                if not bytes.fromhex(command):
                    raise ValueError("Empty command")
            except ValueError as error:
                raise ValueError(f"Invalid HEX command: {name}") from error

        database = data.get("DATABASE", {})
        required = ("SQL_DRIVER", "SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD")
        if not isinstance(database, dict) or any(not database.get(key) for key in required):
            raise ValueError("DATABASE is missing required connection settings.")
        ssl = data.get("SSL") or {}
        enabled = ssl.get("ENABLED", False)
        if not isinstance(enabled, bool):
            raise ValueError("SSL.ENABLED must be true or false.")

        def resolve_file(value):
            return str((config_path.parent / value).resolve()) if value else ""

        cert = resolve_file(ssl.get("CERT_PATH", ""))
        key = resolve_file(ssl.get("KEY_PATH", ""))
        if enabled and (not Path(cert).is_file() or not Path(key).is_file()):
            raise ValueError("SSL certificate and key files are required when SSL is enabled.")
        port = int(data.get("PORT", 5000))
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535.")
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
        )
