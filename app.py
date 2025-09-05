from flask import Flask, jsonify, render_template, send_from_directory, request
from src.hwa_connector import HWAClient
import requests
import os
import sys
import threading
import webbrowser
import logging
import configparser
import json

# --- Platform Specific Imports ---
if sys.platform == 'win32':
    import winreg

# --- Application Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__, template_folder='templates', static_folder='static')
PORT = 63136
BASE_URL = f"http://localhost:{PORT}"
CONFIG_FILE = 'config/config.ini'
LAYOUT_FILE = 'dashboard_layout.json'
APP_NAME = "HWA Dashboard"
if getattr(sys, 'frozen', False):
    APP_PATH = sys.executable
else:
    APP_PATH = os.path.abspath(__file__)

# --- Frontend Web Routes ---
@app.route('/')
def index():
    """Renders the main dashboard page, passing the layout configuration to the template."""
    try:
        with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Could not load or parse {LAYOUT_FILE}: {e}")
        # Provide an empty layout to prevent crashing the page, with an error message.
        layout_data = [{"type": "error", "message": f"Error: Could not load {LAYOUT_FILE}."}]
    return render_template('index.html', layout_data=layout_data)

@app.route('/config')
def config_page():
    return render_template('config.html')

@app.route('/dashboard_editor')
def dashboard_editor_page():
    return render_template('dashboard_editor.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/oql_help')
def oql_help_page():
    return render_template('oql_help.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


# --- Backend API Routes ---
@app.route('/api/dashboard_data')
def get_dashboard_data():
    """
    Main API endpoint to fetch and process all data needed for the dashboard.
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            return jsonify({"error": "Configuration file not found. Please go to the Configuration page to set up the connection."}), 404

        client = HWAClient(config_path=CONFIG_FILE)

        # Fetch all data
        all_job_streams = client.plan.query_job_streams()
        all_workstations = client.model.query_workstations()

        # Process Job Data for widgets and modals
        jobs_abend = [j for j in all_job_streams if j.get('status', '').lower() == 'abend']
        jobs_running = [j for j in all_job_streams if j.get('status', '').lower() == 'exec']

        # Prepare response data matching frontend expectations
        response_data = {
            "abend_count": len(jobs_abend),
            "running_count": len(jobs_running),
            "total_job_stream_count": len(all_job_streams),
            "total_workstation_count": len(all_workstations),

            "job_streams": all_job_streams,
            "workstations": all_workstations,

            # Full lists for modals
            "jobs_abend": jobs_abend,
            "jobs_running": jobs_running,
        }
        return jsonify(response_data)

    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection Error in get_dashboard_data: {e}")
        return jsonify({"error": "Connection Error: Could not connect to the HWA/TWS host. Please check the hostname, port, and SSL verification settings in the configuration."}), 500
    except Exception as e:
        logging.error(f"Error in get_dashboard_data: {e}")
        error_message = str(e)
        if "Authentication failed" in error_message:
             return jsonify({"error": "Authentication Failed. Please check your username and password in the configuration."}), 401
        return jsonify({"error": f"An unexpected error occurred: {error_message}"}), 500

@app.route('/api/oql', methods=['GET'])
def execute_oql():
    """
    API endpoint to execute a raw OQL query.
    Expects a 'q' query parameter with the OQL string.
    """
    oql_query = request.args.get('q')
    if not oql_query:
        return jsonify({"error": "Missing 'q' parameter with OQL query."}), 400

    try:
        if not os.path.exists(CONFIG_FILE):
            return jsonify({"error": "Configuration file not found. Please configure the connection."}), 404

        client = HWAClient(config_path=CONFIG_FILE)
        result = client.plan.execute_oql_query(oql_query)

        return jsonify(result)

    except ValueError as e:
        # Catches HTTP errors from the HWA API, which are wrapped in ValueError
        logging.error(f"OQL Query Error: {e}")
        return jsonify({"error": f"The OQL query failed. Please check your syntax. (Details: {str(e)})"}), 400
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection Error in OQL query: {e}")
        return jsonify({"error": "Connection Error: Could not connect to the HWA host."}), 500
    except Exception as e:
        logging.error(f"Error in execute_oql: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/plan/<plan_id>/job/<job_id>/action/cancel', methods=['PUT'])
def cancel_job_in_plan(plan_id, job_id):
    """
    API endpoint to cancel a specific job in a given plan.
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            return jsonify({"error": "Configuration file not found."}), 404

        client = HWAClient(config_path=CONFIG_FILE)
        result = client.plan.cancel_job(job_id, plan_id)

        return jsonify({"success": True, "message": f"Cancel command sent to job {job_id} in plan {plan_id}.", "details": result})

    except Exception as e:
        logging.error(f"Error in cancel_job_in_plan: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    settings = dict(config['tws']) if 'tws' in config else {}
    # Ensure verify_ssl is a boolean for the frontend
    if 'verify_ssl' in settings:
        settings['verify_ssl'] = config.getboolean('tws', 'verify_ssl')
    return jsonify(settings)

@app.route('/api/dashboard_layout', methods=['GET'])
def get_dashboard_layout():
    try:
        with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
        return jsonify(layout_data)
    except FileNotFoundError:
        return jsonify([]) # Return empty layout if file doesn't exist
    except Exception as e:
        logging.error(f"Error reading layout file: {e}")
        return jsonify({"error": "Could not read layout file."}), 500

@app.route('/api/dashboard_layout', methods=['POST'])
def save_dashboard_layout():
    try:
        new_layout = request.json
        with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_layout, f, indent=4)
        return jsonify({"success": True, "message": "Layout saved successfully."})
    except Exception as e:
        logging.error(f"Error saving dashboard layout: {e}")
        return jsonify({"error": str(e)}), 500

from src.security import load_key, encrypt_password

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

    # Update non-sensitive values
    for key in ['hostname', 'port', 'username']:
        if key in data:
            config.set('tws', key, str(data[key]))
    if 'verify_ssl' in data:
        config.set('tws', 'verify_ssl', 'true' if data['verify_ssl'] else 'false')

    # Handle password encryption
    if data.get('password'):
        key = load_key()
        encrypted_pass = encrypt_password(data['password'], key)
        config.set('tws', 'password', encrypted_pass.decode('utf-8')) # Store as string

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    return jsonify({"success": "Configuration saved successfully."})



# --- System Tray & Server Logic ---
tray_icon = None

def get_startup_key():
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_ALL_ACCESS)

def is_in_startup():
    key = get_startup_key()
    try:
        winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        winreg.CloseKey(key)

def toggle_startup():
    key = get_startup_key()
    try:
        if is_in_startup():
            winreg.DeleteValue(key, APP_NAME)
        else:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{APP_PATH}"')
    finally:
        winreg.CloseKey(key)

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False)

def open_dashboard():
    webbrowser.open(BASE_URL)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    stop_app()
    return jsonify({"success": True, "message": "Application is shutting down."})

def stop_app():
    """Stops the application by stopping the tray icon's event loop."""
    global tray_icon
    if tray_icon:
        tray_icon.stop()

def setup_tray():
    global tray_icon
    logging.info("Attempting to set up system tray icon.")
    try:
        from pystray import MenuItem as item, Icon as icon
        from PIL import Image
        logging.info("Successfully imported pystray and PIL.")
    except ImportError as e:
        logging.error(f"Failed to import GUI libraries: {e}")
        raise

    # Check if icon.png exists, otherwise create a blank one to avoid crashing
    if not os.path.exists("icon.png"):
        Image.new('RGB', (64, 64), color = 'red').save('icon.png')
        logging.warning("icon.png not found. A placeholder icon has been created.")

    try:
        image = Image.open("icon.png")
        logging.info("Icon image loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load icon.png: {e}")
        raise

    menu_items = [item('Open Dashboard', open_dashboard, default=True)]
    if sys.platform == 'win32':
        menu_items.append(item('Start with Windows', toggle_startup, checked=lambda item: is_in_startup()))
    menu_items.append(item('Exit', stop_app))

    menu = tuple(menu_items)

    try:
        # Assign to the global variable
        tray_icon = icon(APP_NAME, image, APP_NAME, menu)
        logging.info("System tray icon object created.")
    except Exception as e:
        logging.error(f"Failed to create pystray icon object: {e}")
        raise

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logging.info("Flask server started in a background thread.")

    # Give the server a moment to start before opening the browser
    threading.Timer(1, open_dashboard).start()

    logging.info("Running the system tray icon. This is a blocking call that starts the event loop.")
    tray_icon.run()
    logging.info("System tray icon event loop has finished.")

def run_console():
    logging.warning("No graphical display or required libraries found. Running in console-only mode.")
    logging.info(f"Please open your browser and navigate to {BASE_URL}")
    run_flask()

def initial_setup():
    """
    Ensures that necessary configuration files exist on first run.
    """
    # Create config directory if it doesn't exist
    if not os.path.exists('config'):
        os.makedirs('config')

    # 1. Check for config.ini
    if not os.path.exists(CONFIG_FILE):
        logging.info(f"'{CONFIG_FILE}' not found. Creating from template.")
        try:
            import shutil
            shutil.copyfile('config/config.ini.template', CONFIG_FILE)
        except FileNotFoundError:
            logging.error("'config/config.ini.template' not found. Cannot create config file.")
        except Exception as e:
            logging.error(f"Error creating config file: {e}")

    # 2. Check for dashboard_layout.json
    if not os.path.exists(LAYOUT_FILE):
        logging.info(f"'{LAYOUT_FILE}' not found. Creating a default layout.")
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
                "color_class": "color-blue"
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
                "color_class": "color-red"
            }
        ]
        try:
            with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_layout, f, indent=4)
        except Exception as e:
            logging.error(f"Error creating default layout file: {e}")

if __name__ == '__main__':
    initial_setup()
    try:
        import pystray
        import PIL
        logging.info("GUI libraries seem to be available. Attempting to start in system tray mode.")
        setup_tray()
    except (ImportError, Exception) as e:
        logging.error(f"Could not start GUI mode due to an error: {e}", exc_info=True)
        logging.error("This is expected if you are running in an environment without a graphical display (e.g., a standard terminal).")
        run_console()
