import os
import configparser
from pathlib import Path
import logging.config
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
# This is useful for local development.
load_dotenv()

# --- Core Application Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.ini"
LAYOUT_FILE = BASE_DIR / "dashboard_layout.json"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
ICON_FILE = BASE_DIR / "icon.png"

# --- Application Metadata ---
APP_NAME = "HWA Dashboard"
APP_VERSION = "2.0.0"

# --- Environment Configuration ---
APP_ENV = os.getenv("APP_ENV", "production")  # "development" or "production"
TESTING = os.getenv("TESTING_MODE", "0") == "1"

# --- Configuration Loading ---
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# --- Server Configuration ---
# Load from environment variable first, then fallback to config file, then to a hardcoded default.
SERVER_PORT = int(
    os.getenv("SERVER_PORT", config.get("server", "PORT", fallback=63136))
)
SERVER_HOST = os.getenv("SERVER_HOST", config.get("server", "HOST", fallback="0.0.0.0"))
BASE_URL = f"http://localhost:{SERVER_PORT}"

# --- HWA Connection Configuration ---
HWA_HOSTNAME = os.getenv("HWA_HOSTNAME", config.get("tws", "hostname", fallback=None))
HWA_PORT = int(os.getenv("HWA_PORT", config.get("tws", "port", fallback=31116)))
HWA_USERNAME = os.getenv("HWA_USERNAME", config.get("tws", "username", fallback=None))
HWA_PASSWORD = os.getenv("HWA_PASSWORD", config.get("tws", "password", fallback=None))

# --- Database and Redis Configuration ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    config.get(
        "database", "DATABASE_URL", fallback="sqlite+aiosqlite:///./hwa_dashboard.db"
    ),
)
REDIS_URL = os.getenv(
    "REDIS_URL", config.get("redis", "REDIS_URL", fallback="redis://localhost:6379")
)

# --- Monitoring Configuration ---
_critical_statuses_str = config.get(
    "monitoring", "critical_statuses", fallback="ABEND,ERROR,FAIL"
)
CRITICAL_STATUSES = [
    status.strip().upper() for status in _critical_statuses_str.split(",")
]
MONITORING_POLL_INTERVAL = config.getint(
    "monitoring", "poll_interval_seconds", fallback=30
)

# --- HWA Client Configuration ---
HWA_HOW_MANY_LIMIT = config.getint("tws", "how_many_limit", fallback=500)

# --- Security Configuration ---
API_KEY = os.getenv("API_KEY", config.get("security", "API_KEY", fallback=None))
CORS_ALLOWED_ORIGINS = ["*"]  # Consider making this configurable

# --- Determine Application Path for Startup ---
import sys

if getattr(sys, "frozen", False):
    APP_PATH = sys.executable
else:
    APP_PATH = str(BASE_DIR / "main.py")

# --- Structured Logging Configuration ---
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
