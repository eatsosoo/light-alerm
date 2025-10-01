import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

def setup_logger(name="app"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "app.log")  # ✅ luôn giữ tên file chính là app.log

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
        utc=False  # hoặc True nếu bạn dùng UTC
    )
    
    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger