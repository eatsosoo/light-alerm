"""Application entry point for the desktop UI and HTTP server."""

import argparse
import logging
import threading
import sys
import traceback
from pathlib import Path

from werkzeug.serving import make_server

from light_alarm.api import create_app
from light_alarm.runtime import Runtime

logger = logging.getLogger("light_alarm.app")


def create_http_server(settings, application):
    ssl_context = (settings.cert_path, settings.key_path) if settings.ssl_enabled else None
    try:
        return make_server(settings.host, settings.port, application,
                           threaded=True, ssl_context=ssl_context)
    except SystemExit as error:
        raise RuntimeError(
            f"Không mở được HTTP API tại {settings.host}:{settings.port}. "
            "Kiểm tra HOST_IP trong config.yaml có thuộc máy hiện tại và PORT chưa bị chiếm."
        ) from error


def run():
    try:
        main()
    except Exception as error:
        directory = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        error_path = directory / "startup-error.log"
        details = traceback.format_exc()
        try:
            error_path.write_text(details, encoding="utf-8")
            message = f"{error}\n\nChi tiết: {error_path}"
        except OSError:
            message = str(error)
        if "--headless" not in sys.argv:
            try:
                import tkinter as tk
                from tkinter import messagebox
                dialog = tk.Tk()
                dialog.withdraw()
                try:
                    messagebox.showerror("Light Alarm · Không thể khởi động", message, parent=dialog)
                finally:
                    dialog.destroy()
            except Exception:
                pass
        if sys.stderr is not None:
            print(details, file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="CH9120 Light Alarm Control System")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--headless", action="store_true", help="Run only the HTTP API")
    args = parser.parse_args(argv)
    runtime = Runtime.create(args.config)
    server = None
    server_thread = None
    root = None
    try:
        settings = runtime.settings
        server = create_http_server(settings, create_app(runtime))
        logger.info("Started | endpoint=%s:%s | ssl=%s", settings.host, settings.port, settings.ssl_enabled)
        if not settings.api_key:
            logger.warning("API authentication is disabled; configure API_KEY to require credentials.")
        if args.headless:
            server.serve_forever()
        else:
            import tkinter as tk
            from light_alarm.ui.main_window import MainWindow

            root = tk.Tk()
            server_thread = threading.Thread(target=server.serve_forever, name="http-server", daemon=True)
            server_thread.start()
            MainWindow(root, runtime)
            root.mainloop()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception:
        logger.exception("Application failed")
        raise
    finally:
        if server_thread is not None:
            server.shutdown()
            server_thread.join(timeout=10)
        if server is not None:
            server.server_close()
        runtime.close()
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        logger.info("Stopped")


if __name__ == "__main__":
    sys.exit(run())
