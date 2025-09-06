import os
from pathlib import Path

# --- Core Application Paths and Constants ---

# Base directory of the application
# This allows the app to find its files regardless of where it's run from.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configuration files
CONFIG_DIR = BASE_DIR / 'config'
CONFIG_FILE = CONFIG_DIR / 'config.ini'
LAYOUT_FILE = BASE_DIR / 'dashboard_layout.json'

# Static and Template files
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
ICON_FILE = BASE_DIR / 'icon.png'

# --- Application Metadata ---
APP_NAME = "HWA Dashboard"
APP_VERSION = "1.0.0"

# --- Server Configuration ---
# Port and host for the Uvicorn server
SERVER_PORT = 63136
SERVER_HOST = "0.0.0.0"
BASE_URL = f"http://localhost:{SERVER_PORT}"

# --- Security Configuration ---
# Note: In a real production environment, this should be a specific list of allowed origins.
CORS_ALLOWED_ORIGINS = ["*"]

# --- Determine Application Path for Startup ---
import sys

# This is used for the "Start with Windows" feature
if getattr(sys, 'frozen', False):
    # The application is running in a bundled exe from PyInstaller
    APP_PATH = sys.executable
else:
    # The application is running in a normal Python environment
    APP_PATH = str(BASE_DIR / 'main.py') # Should point to the new entrypoint
