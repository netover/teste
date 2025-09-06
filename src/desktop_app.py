import logging
import webbrowser
import threading
import sys
from PIL import Image

from src.core import config

try:
    import pystray
    if sys.platform == 'win32':
        import winreg
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

server_process = None

def _get_startup_key():
    """Gets the Windows registry key for startup applications."""
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_ALL_ACCESS)

def is_in_startup():
    """Checks if the application is configured to start with Windows."""
    if sys.platform != 'win32':
        return False
    key = _get_startup_key()
    try:
        winreg.QueryValueEx(key, config.APP_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        winreg.CloseKey(key)

def toggle_startup():
    """Adds or removes the application from Windows startup."""
    if sys.platform != 'win32':
        return
    key = _get_startup_key()
    try:
        if is_in_startup():
            winreg.DeleteValue(key, config.APP_NAME)
            logging.info(f"Removed {config.APP_NAME} from startup.")
        else:
            winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_SZ, f'"{config.APP_PATH}"')
            logging.info(f"Added {config.APP_NAME} to startup.")
    finally:
        winreg.CloseKey(key)

def open_dashboard():
    """Opens the dashboard URL in the default web browser."""
    webbrowser.open(config.BASE_URL)

def stop_server(server):
    """Signals the Uvicorn server to shut down."""
    if server:
        server.should_exit = True

def run_tray_app(server):
    """Sets up and runs the system tray icon and its menu."""
    if not PYSTRAY_AVAILABLE:
        logging.warning("pystray or dependencies not found. Cannot create system tray icon.")
        return

    # Ensure the icon file exists
    if not config.ICON_FILE.exists():
        Image.new('RGB', (64, 64), color='red').save(config.ICON_FILE)
        logging.warning(f"Icon file not found. A placeholder has been created at {config.ICON_FILE}")

    image = Image.open(config.ICON_FILE)

    # Define menu items
    menu_items = [pystray.MenuItem('Open Dashboard', open_dashboard, default=True)]
    if sys.platform == 'win32':
        menu_items.append(pystray.MenuItem('Start with Windows', toggle_startup, checked=lambda item: is_in_startup()))

    # Add a separator and the stop function
    menu_items.extend([
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Exit', lambda: stop_server(server))
    ])

    icon = pystray.Icon(config.APP_NAME, image, config.APP_NAME, tuple(menu_items))

    # The stop function needs to also stop the icon loop
    server_shutdown_callback = icon.stop
    server.after_shutdown.append(server_shutdown_callback)

    logging.info("Running system tray icon.")
    icon.run()
    logging.info("System tray icon event loop finished.")
