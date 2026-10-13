"""Application entry point for the desktop UI and HTTP server."""

import argparse
import logging
import threading

from werkzeug.serving import make_server

from light_alarm.api import create_app
from light_alarm.runtime import Runtime

logger = logging.getLogger("light_alarm.app")


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
        ssl_context = (settings.cert_path, settings.key_path) if settings.ssl_enabled else None
        server = make_server(settings.host, settings.port, create_app(runtime),
                             threaded=True, ssl_context=ssl_context)
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
    main()
