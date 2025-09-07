import os
import configparser
from pathlib import Path

# --- Core Application Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / 'config'
CONFIG_FILE = CONFIG_DIR / 'config.ini'
LAYOUT_FILE = BASE_DIR / 'dashboard_layout.json'
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
ICON_FILE = BASE_DIR / 'icon.png'

# --- Application Metadata ---
APP_NAME = "HWA Dashboard"
APP_VERSION = "2.0.0" # Updated version

# --- Configuration Loading ---
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# --- Server Configuration ---
SERVER_PORT = config.getint('server', 'PORT', fallback=63136)
SERVER_HOST = config.get('server', 'HOST', fallback="0.0.0.0")
BASE_URL = f"http://localhost:{SERVER_PORT}"

# --- Database and Redis Configuration ---
DATABASE_URL = config.get(
    'database',
    'DATABASE_URL',
    fallback='sqlite+aiosqlite:///./hwa_dashboard.db'
)
REDIS_URL = config.get(
    'redis',
    'REDIS_URL',
    fallback='redis://localhost:6379'
)

# --- Security Configuration ---
CORS_ALLOWED_ORIGINS = ["*"] # Consider making this configurable

# --- Determine Application Path for Startup ---
import sys

if getattr(sys, 'frozen', False):
    # The application is running in a bundled exe from PyInstaller
    APP_PATH = sys.executable
else:
    # The application is running in a normal Python environment
    APP_PATH = str(BASE_DIR / 'main.py')
