import uvicorn
import logging
import json
import os
import shutil
import threading
import time

from src.core import config
from src.api_server import app  # Import the FastAPI app


def initial_setup():
    """Ensures necessary configuration files and directories exist on first run."""
    if not config.CONFIG_DIR.exists():
        config.CONFIG_DIR.mkdir(parents=True)

    if not config.CONFIG_FILE.exists():
        template_path = config.CONFIG_DIR / "config.ini.template"
        if template_path.exists():
            logging.info(f"'{config.CONFIG_FILE}' not found. Creating from template.")
            shutil.copyfile(template_path, config.CONFIG_FILE)
        else:
            logging.warning(f"'{template_path}' not found. Cannot create config file.")

    if not config.LAYOUT_FILE.exists():
        logging.info(f"'{config.LAYOUT_FILE}' not found. Creating a default layout.")
        default_layout = [
            {
                "id": "widget_running",
                "type": "summary_count",
                "label": "Jobs Running",
                "icon": "fas fa-running",
                "api_metric": "running_count",
                "modal_data_key": "jobs_running",
                "modal_title": "Running Jobs",
                "modal_item_renderer": "renderJobItem",
                "color_class": "color-blue",
            },
            {
                "id": "widget_abend",
                "type": "summary_count",
                "label": "Jobs Abend",
                "icon": "fas fa-exclamation-triangle",
                "api_metric": "abend_count",
                "modal_data_key": "jobs_abend",
                "modal_title": "Abended Jobs",
                "modal_item_renderer": "renderJobItem",
                "color_class": "color-red",
            },
        ]
        with open(config.LAYOUT_FILE, "w", encoding="utf-8") as f:
            json.dump(default_layout, f, indent=4)


def run_server_in_thread(server):
    """Runs the given server instance in a daemon thread."""
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    logging.info("Uvicorn server started in a background thread.")
    return thread


def main():
    """Main entry point for the application."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    initial_setup()

    server_config = uvicorn.Config(
        app, host=config.SERVER_HOST, port=config.SERVER_PORT, log_level="info"
    )
    server = uvicorn.Server(server_config)

    # Check for GUI libraries at runtime to avoid import errors in headless envs
    pystray_available = False
    if not os.environ.get("FORCE_CONSOLE_MODE") == "1":
        try:
            from src.desktop_app import run_tray_app, open_dashboard

            pystray_available = True
        except Exception as e:
            logging.warning(
                f"Could not import GUI libraries, falling back to console mode. Error: {e}"
            )
            pystray_available = False

    if pystray_available:
        logging.info("pystray found. Attempting to start in system tray mode.")
        run_server_in_thread(server)
        time.sleep(1)  # Give server a moment to start
        open_dashboard()
        run_tray_app(server)  # This is a blocking call
    else:
        logging.warning("Running in console-only mode.")
        logging.info(f"Please open your browser and navigate to {config.BASE_URL}")
        server.run()


if __name__ == "__main__":
    main()
