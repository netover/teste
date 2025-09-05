from flask import Flask, jsonify, render_template, send_from_directory, request
from src.hwa_connector import HWAConnector
import requests
import os
import sys
import threading
import webbrowser
import logging
import configparser

# --- Platform Specific Imports ---
# Import winreg only on Windows to handle startup functionality
if sys.platform == 'win32':
    import winreg

# --- Application Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
PORT = 63136
BASE_URL = f"http://localhost:{PORT}"
CONFIG_FILE = 'config/config.ini'
APP_NAME = "HWA Dashboard"
# Get the absolute path to the executable if running as a bundled app
if getattr(sys, 'frozen', False):
    APP_PATH = sys.executable
else:
    APP_PATH = os.path.abspath(__file__)

# --- Frontend Web Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config_page():
    return render_template('config.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


# --- Backend API Routes ---
@app.route('/api/jobstreams')
def get_job_streams():
    try:
        connector = HWAConnector(config_path=CONFIG_FILE)
        job_streams = connector.query_job_streams()
        return jsonify(job_streams)
    except FileNotFoundError as e:
        return jsonify({"error": str(e), "setup_required": True}), 500
    except (ValueError, requests.exceptions.RequestException) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    settings = dict(config['tws']) if 'tws' in config else {}
    return jsonify(settings)

@app.route('/api/config', methods=['POST'])
def save_config():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    if 'tws' not in config:
        config.add_section('tws')
    for key in ['hostname', 'port', 'username', 'verify_ssl']:
        if key in data:
            config.set('tws', key, str(data[key]))
    if data.get('password'):
        config.set('tws', 'password', data['password'])
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    return jsonify({"success": "Configuration saved successfully."})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_func()
    return 'Server shutting down...'


# --- System Tray & Server Logic ---
def get_startup_key():
    """Returns the Windows registry key for startup programs."""
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_ALL_ACCESS)

def is_in_startup():
    """Checks if the application is set to run at startup."""
    key = get_startup_key()
    try:
        winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        winreg.CloseKey(key)

def toggle_startup():
    """Adds or removes the application from Windows startup."""
    key = get_startup_key()
    try:
        if is_in_startup():
            logging.info("Removing app from startup.")
            winreg.DeleteValue(key, APP_NAME)
        else:
            logging.info("Adding app to startup.")
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{APP_PATH}"')
    finally:
        winreg.CloseKey(key)

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False)

def open_dashboard():
    webbrowser.open(BASE_URL)

def stop_app(tray_icon):
    requests.post(f"{BASE_URL}/shutdown")
    tray_icon.stop()

def setup_tray():
    from pystray import MenuItem as item, Icon as icon
    from PIL import Image
    image = Image.open("icon.png")

    menu_items = [item('Open Dashboard', open_dashboard)]
    if sys.platform == 'win32':
        # Only add the startup option on Windows
        menu_items.append(item('Start with Windows', toggle_startup, checked=lambda item: is_in_startup()))
    menu_items.append(item('Exit', lambda: stop_app(tray_icon)))

    menu = tuple(menu_items)
    tray_icon = icon(APP_NAME, image, APP_NAME, menu)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    open_dashboard()
    tray_icon.run()

def run_console():
    logging.warning("No graphical display available. Running in console mode.")
    run_flask()

if __name__ == '__main__':
    try:
        setup_tray()
    except Exception as e:
        logging.error(f"Could not start GUI mode: {e}")
        run_console()
