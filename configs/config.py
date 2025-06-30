import yaml
import pyodbc
import os

class Config:
    _config_data = None

    @staticmethod
    def _load_config(yaml_path="configs/config.yaml"):
        if Config._config_data is None:
            if not os.path.exists(yaml_path):
                raise FileNotFoundError(f"Không tìm thấy file cấu hình: {yaml_path}")
            with open(yaml_path, "r", encoding="utf-8") as f:
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
        
        return pyodbc.connect(conn_str)
