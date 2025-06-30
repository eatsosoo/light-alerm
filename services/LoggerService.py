import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

def setup_logger(name="app"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = TimedRotatingFileHandler(
        log_filename, when="midnight", backupCount=7, encoding="utf-8"
    )
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    # Chỉ thêm handler nếu chưa có (tránh nhân bản khi import nhiều nơi)
    if not logger.handlers:
        logger.addHandler(handler)

    return logger