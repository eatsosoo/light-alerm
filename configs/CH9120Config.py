import yaml
import os
import sys


if getattr(sys, 'frozen', False):
    base_path = os.path.join(sys._MEIPASS, "configs")
else:
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))


config_path = os.path.join(base_path, 'config.yaml')

if not os.path.exists(config_path):
    raise FileNotFoundError(f"Không tìm thấy file cấu hình: {config_path}")

with open(config_path, encoding="utf-8") as f:
    config = yaml.safe_load(f)

CH9120_COMMANDS = config.get('CH9120', {}).get('COMMANDS', {})



