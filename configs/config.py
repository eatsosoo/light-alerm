import yaml
import pyodbc
import os
import sys
from services.LoggerService import setup_logger

logger = setup_logger()

class Config:
    _config_data = None

    @staticmethod
    def _load_config():
        if Config._config_data is None:
            # ✅ Giả định bạn luôn chạy từ thư mục project root
            base_dir = os.getcwd()
            config_path = os.path.join(base_dir, "config.yaml")

            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Không tìm thấy file cấu hình: {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                Config._config_data = yaml.safe_load(f)

        return Config._config_data
    
    @staticmethod
    def get_db_connection():        
        config = Config._load_config()
        db = config.get("DATABASE", {})
        
        conn_str = (
            f"DRIVER={db.get('SQL_DRIVER')};"
            f"SERVER={db.get('SQL_SERVER')};"
            f"DATABASE={db.get('SQL_DATABASE')};"
            f"UID={db.get('SQL_USER')};"
            f"PWD={db.get('SQL_PASSWORD')}"
        )
        
        try:
            connection = pyodbc.connect(conn_str)
            logger.info("Database connection successful.")
            return connection
        except pyodbc.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @staticmethod
    def get_host():
        config = Config._load_config()
        host = config.get("HOST_IP", "")
        return host
    
    @staticmethod
    def get_port():
        config = Config._load_config()
        host = config.get("PORT", "5000")
        return host
    
    @staticmethod
    def get_commands():
        config = Config._load_config()
        commands = config.get('CH9120', {}).get('COMMANDS', {})
        return commands
    
    @staticmethod
    def get_ssl():
        config = Config._load_config()
        cert = config.get('SSL', {})
        return cert

