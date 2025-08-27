import tkinter as tk
import threading
from flask import Flask
from flask_cors import CORS
from routes.api import blueprint
from configs.config import Config
import logging
import os
from services.LoggerService import setup_logger
from ui.DeviceControlUI import DeviceControlUI

logger = setup_logger()

HOST_IP = Config.get_host()
PORT = Config.get_port()
COMMANDS = Config.get_commands()

app = Flask(__name__)
CORS(app)
app.register_blueprint(blueprint, url_prefix="/ch9120")

def run_flask():
    app.run(host=HOST_IP, port=PORT)

def create_ui():
    root = tk.Tk()
    DeviceControlUI(root, HOST_IP, PORT, COMMANDS)
    root.mainloop()

if __name__ == '__main__':
    os.makedirs("logs", exist_ok=True)
    logging.getLogger('werkzeug').disabled = True
    logger.info('Started')

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    create_ui()
    logger.info('Turn down')