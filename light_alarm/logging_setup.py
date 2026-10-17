"""Daily file logging shared by the API, desktop UI and workers."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from light_alarm.services.request_history import RequestContextFilter, RequestHistory


def today_log_path(directory):
    return Path(directory) / f"app_{datetime.now():%Y-%m-%d}.log"


class DailyLogFileHandler(logging.Handler):
    def __init__(self, directory):
        super().__init__(logging.INFO)
        self.directory = Path(directory)
        self.current_path = None
        self.file_handler = None

    def emit(self, record):
        try:
            path = self.directory / f"app_{datetime.fromtimestamp(record.created):%Y-%m-%d}.log"
            if path != self.current_path:
                if self.file_handler:
                    self.file_handler.close()
                self.file_handler = logging.FileHandler(path, encoding="utf-8")
                self.file_handler.setFormatter(self.formatter)
                self.current_path = path
                self.cleanup()
            self.file_handler.emit(record)
        except Exception:
            self.handleError(record)

    def cleanup(self):
        cutoff = datetime.now().date() - timedelta(days=14)
        for path in self.directory.glob("app_*.log"):
            try:
                if datetime.strptime(path.stem[4:], "%Y-%m-%d").date() < cutoff:
                    path.unlink()
            except (ValueError, OSError):
                continue

    def close(self):
        self.acquire()
        try:
            if self.file_handler:
                self.file_handler.close()
                self.file_handler = None
            super().close()
        finally:
            self.release()


def configure_logging(directory, history):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("light_alarm")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for existing in list(logger.handlers):
        if isinstance(existing, RequestHistory):
            logger.removeHandler(existing)
    logger.addHandler(history)
    for existing in list(logger.handlers):
        if isinstance(existing, DailyLogFileHandler):
            if existing.directory == directory:
                return
            logger.removeHandler(existing)
            existing.close()
    handler = DailyLogFileHandler(directory)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | request=%(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
