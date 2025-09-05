from flask import Flask, jsonify, render_template, send_from_directory, request
from src.hwa_connector import HWAConnector
import requests
import os
import threading
import webbrowser
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
PORT = 63136
BASE_URL = f"http://localhost:{PORT}"

# --- Web Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# --- API Routes ---

@app.route('/api/jobstreams')
def get_job_streams():
    try:
        connector = HWAConnector()
        job_streams = connector.query_job_streams()
        return jsonify(job_streams)
    except FileNotFoundError as e:
        logging.error(f"Configuration file error: {e}")
        return jsonify({"error": str(e)}), 500
    except (ValueError, requests.exceptions.RequestException) as e:
        logging.error(f"API connection error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Gracefully shuts down the server."""
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_func()
    return 'Server shutting down...'

# --- System Tray & Server Logic ---

def run_flask():
    """Runs the Flask app."""
    logging.info(f"Starting Flask server at {BASE_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

def open_dashboard():
    """Opens the dashboard URL in a web browser."""
    logging.info("Opening dashboard in browser.")
    webbrowser.open(BASE_URL)

def stop_app(tray_icon):
    """Stops the Flask server and the systray icon."""
    logging.info("Shutdown requested from tray menu.")
    try:
        requests.post(f"{BASE_URL}/shutdown")
    except requests.exceptions.ConnectionError:
        logging.info("Server was not running or already shut down.")
    finally:
        tray_icon.stop()

def setup_tray():
    """Creates and runs the system tray icon."""
    # Import GUI libraries here to prevent import errors on headless systems
    from pystray import MenuItem as item, Icon as icon
    from PIL import Image

    image = Image.open("icon.png")
    menu = (item('Open Dashboard', open_dashboard), item('Exit', lambda: stop_app(tray_icon)))
    tray_icon = icon('HWA Dashboard', image, "HWA Dashboard", menu)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    open_dashboard()
    tray_icon.run()

def run_console():
    """Fallback function to run in console if GUI is not available."""
    logging.warning("No graphical display available. Running in console mode.")
    logging.warning(f"Access the dashboard at {BASE_URL}")
    logging.warning("Press CTRL+C to exit.")
    run_flask()

if __name__ == '__main__':
    try:
        setup_tray()
    except Exception as e:
        logging.error(f"Could not start GUI mode: {e}")
        run_console()
