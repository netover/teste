import os
from pathlib import Path
from .settings import settings  # Import the centralized settings object

# --- Core Application Paths ---
# These are derived from the file system and are not part of runtime configuration.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
ICON_FILE = BASE_DIR / "icon.png"

def get_layout_file() -> Path:
    """
    Determines the correct dashboard layout file to use.
    It prioritizes the LAYOUT_FILE_OVERRIDE from settings,
    which is useful for testing, and falls back to the default file.
    """
    # Use the value from the new settings object
    if settings.LAYOUT_FILE_OVERRIDE:
        return Path(settings.LAYOUT_FILE_OVERRIDE)
    return CONFIG_DIR / "dashboard_layout.json"

# --- Determine Application Path for Startup ---
import sys

if getattr(sys, "frozen", False):
    # The application is running in a bundled executable (e.g., from PyInstaller)
    APP_PATH = sys.executable
else:
    # The application is running as a standard Python script
    APP_PATH = str(BASE_DIR / "main.py")


# --- Structured Logging Configuration ---
# This remains here as it's a static dictionary configuration.
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["default"],
        "level": "INFO",
    },
    "loggers": {
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "handlers": [], # Disable uvicorn's default access logger
            "propagate": True,
        },
    },
}