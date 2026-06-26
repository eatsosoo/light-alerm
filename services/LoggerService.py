import logging
import os
from datetime import datetime, timedelta


LOG_DIR = "logs"
LOG_RETENTION_DAYS = 14


def get_today_log_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"app_{today}.log")


def get_log_path_for_time(timestamp):
    log_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"app_{log_date}.log")


def cleanup_old_logs():
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)

    for filename in os.listdir(LOG_DIR):
        if not filename.startswith("app_") or not filename.endswith(".log"):
            continue

        date_part = filename.removeprefix("app_").removesuffix(".log")
        try:
            log_date = datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue

        if log_date < cutoff:
            try:
                os.remove(os.path.join(LOG_DIR, filename))
            except OSError:
                pass


class DailyLogFileHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.current_path = None
        self.file_handler = None

    def emit(self, record):
        try:
            log_path = get_log_path_for_time(record.created)
            self._switch_file_if_needed(log_path)
            self.file_handler.emit(record)
        except Exception:
            self.handleError(record)

    def close(self):
        if self.file_handler:
            self.file_handler.close()
        super().close()

    def _switch_file_if_needed(self, log_path):
        if self.current_path == log_path and self.file_handler:
            return

        if self.file_handler:
            self.file_handler.close()

        self.current_path = log_path
        self.file_handler = logging.FileHandler(log_path, encoding="utf-8")
        self.file_handler.setLevel(self.level)
        self.file_handler.setFormatter(self.formatter)


def setup_logger(name="app"):
    os.makedirs(LOG_DIR, exist_ok=True)
    cleanup_old_logs()

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    has_daily_handler = any(isinstance(handler, DailyLogFileHandler) for handler in logger.handlers)

    if not has_daily_handler:
        handler = DailyLogFileHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
