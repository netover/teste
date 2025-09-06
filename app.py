import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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
app = FastAPI()
PORT = 63136
BASE_URL = f"http://localhost:{PORT}"
CONFIG_FILE = 'config/config.ini'
LAYOUT_FILE = 'dashboard_layout.json'
APP_NAME = "HWA Dashboard"
if getattr(sys, 'frozen', False):
    APP_PATH = sys.executable
else:
    APP_PATH = os.path.abspath(__file__)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Pydantic Models for Request Bodies ---
class ConfigModel(BaseModel):
    hostname: str
    port: int
    username: str
    password: Optional[str] = None
    verify_ssl: bool = False

# --- Frontend Web Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renders the main dashboard page, passing the layout configuration to the template."""
    try:
        with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Could not load or parse {LAYOUT_FILE}: {e}")
        layout_data = [{"type": "error", "message": f"Error: Could not load {LAYOUT_FILE}."}]
    return templates.TemplateResponse("index.html", {"request": request, "layout_data": layout_data})

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})

@app.get("/dashboard_editor", response_class=HTMLResponse)
async def dashboard_editor_page(request: Request):
    return templates.TemplateResponse("dashboard_editor.html", {"request": request})

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

@app.get("/oql_help", response_class=HTMLResponse)
async def oql_help_page(request: Request):
    return templates.TemplateResponse("oql_help.html", {"request": request})

# --- Backend API Routes ---
def get_client():
    if not os.path.exists(CONFIG_FILE):
        raise HTTPException(status_code=404, detail="Configuration file not found. Please go to the Configuration page to set up the connection.")
    try:
        return HWAClient(config_path=CONFIG_FILE)
    except Exception as e:
        logging.error(f"Failed to create HWAClient: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize HWA client: {e}")

@app.get("/api/dashboard_data")
async def get_dashboard_data():
    """Main API endpoint to fetch and process all data needed for the dashboard."""
    try:
        client = get_client()
        all_job_streams = client.plan.query_job_streams()
        all_workstations = client.model.query_workstations()

        jobs_abend = [j for j in all_job_streams if j.get('status', '').lower() == 'abend']
        jobs_running = [j for j in all_job_streams if j.get('status', '').lower() == 'exec']

        return {
            "abend_count": len(jobs_abend),
            "running_count": len(jobs_running),
            "total_job_stream_count": len(all_job_streams),
            "total_workstation_count": len(all_workstations),
            "job_streams": all_job_streams,
            "workstations": all_workstations,
            "jobs_abend": jobs_abend,
            "jobs_running": jobs_running,
        }
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Connection Error: Could not connect to the HWA/TWS host. Please check connection settings.")
    except ValueError as e:
        if "Authentication failed" in str(e):
            raise HTTPException(status_code=401, detail="Authentication Failed. Please check your username and password.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/api/oql")
async def execute_oql(q: str, source: str = "plan"):
    """
    API endpoint to execute a raw OQL query against the plan or model.
    Expects a 'q' query parameter with the OQL string.
    Optional 'source' parameter can be 'plan' (default) or 'model'.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Missing 'q' parameter with OQL query.")

    try:
        client = get_client()
        if source == "model":
            result = client.model.execute_oql_query(q)
        else: # Default to plan
            result = client.plan.execute_oql_query(q)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"The OQL query failed. Please check your syntax. (Details: {str(e)})")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=500, detail="Connection Error: Could not connect to the HWA host.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

async def _job_action_endpoint(action: str, plan_id: str, job_id: str):
    """Generic helper for job action endpoints."""
    try:
        client = get_client()
        action_map = {
            "cancel": client.plan.cancel_job,
            "rerun": client.plan.rerun_job,
            "hold": client.plan.hold_job,
            "release": client.plan.release_job,
        }
        if action not in action_map:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

        result = action_map[action](job_id, plan_id)
        return {"success": True, "message": f"'{action.capitalize()}' command sent to job {job_id} in plan {plan_id}.", "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.put("/api/plan/{plan_id}/job/{job_id}/action/cancel")
async def cancel_job_in_plan(plan_id: str, job_id: str):
    return await _job_action_endpoint("cancel", plan_id, job_id)

@app.put("/api/plan/{plan_id}/job/{job_id}/action/rerun")
async def rerun_job_in_plan(plan_id: str, job_id: str):
    return await _job_action_endpoint("rerun", plan_id, job_id)

@app.put("/api/plan/{plan_id}/job/{job_id}/action/hold")
async def hold_job_in_plan(plan_id: str, job_id: str):
    return await _job_action_endpoint("hold", plan_id, job_id)

@app.put("/api/plan/{plan_id}/job/{job_id}/action/release")
async def release_job_in_plan(plan_id: str, job_id: str):
    return await _job_action_endpoint("release", plan_id, job_id)

@app.get("/api/config")
async def get_config_api():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    settings = dict(config['tws']) if 'tws' in config else {}
    if 'verify_ssl' in settings:
        settings['verify_ssl'] = config.getboolean('tws', 'verify_ssl')
    return settings

from src.security import load_key, encrypt_password

@app.post("/api/config")
async def save_config_api(data: ConfigModel):
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    if 'tws' not in config:
        config.add_section('tws')

    config.set('tws', 'hostname', data.hostname)
    config.set('tws', 'port', str(data.port))
    config.set('tws', 'username', data.username)
    config.set('tws', 'verify_ssl', 'true' if data.verify_ssl else 'false')

    if data.password:
        key = load_key()
        encrypted_pass = encrypt_password(data.password, key)
        config.set('tws', 'password', encrypted_pass.decode('utf-8'))

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    return {"success": "Configuration saved successfully."}

@app.get("/api/dashboard_layout")
async def get_dashboard_layout():
    try:
        with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
        return layout_data
    except FileNotFoundError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read layout file: {e}")

@app.post("/api/dashboard_layout")
async def save_dashboard_layout(new_layout: List[Dict[str, Any]]):
    try:
        with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_layout, f, indent=4)
        return {"success": True, "message": "Layout saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving dashboard layout: {e}")


# --- System Tray & Server Logic ---
tray_icon = None
server_thread = None
server = None

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

def open_dashboard():
    webbrowser.open(BASE_URL)

@app.post("/shutdown")
async def shutdown():
    stop_app()
    return {"success": True, "message": "Application is shutting down."}

def stop_app():
    """Stops the application by stopping the tray icon's event loop."""
    global tray_icon, server
    if server:
        server.should_exit = True
    if tray_icon:
        tray_icon.stop()

def setup_tray():
    global tray_icon, server, server_thread
    logging.info("Attempting to set up system tray icon.")
    try:
        from pystray import MenuItem as item, Icon as icon
        from PIL import Image
    except ImportError as e:
        logging.error(f"Failed to import GUI libraries: {e}")
        raise

    if not os.path.exists("icon.png"):
        Image.new('RGB', (64, 64), color='red').save('icon.png')
        logging.warning("icon.png not found. A placeholder icon has been created.")

    image = Image.open("icon.png")

    menu_items = [item('Open Dashboard', open_dashboard, default=True)]
    if sys.platform == 'win32':
        menu_items.append(item('Start with Windows', toggle_startup, checked=lambda item: is_in_startup()))
    menu_items.append(item('Exit', stop_app))

    menu = tuple(menu_items)
    tray_icon = icon(APP_NAME, image, APP_NAME, menu)

    # Setup Uvicorn server in a separate thread
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run)
    server_thread.daemon = True
    server_thread.start()
    logging.info("Uvicorn server started in a background thread.")

    threading.Timer(1, open_dashboard).start()

    tray_icon.run()
    logging.info("System tray icon event loop has finished.")

def run_console():
    logging.warning("No graphical display or required libraries found. Running in console-only mode.")
    logging.info(f"Please open your browser and navigate to {BASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

def initial_setup():
    if not os.path.exists('config'):
        os.makedirs('config')
    if not os.path.exists(CONFIG_FILE):
        logging.info(f"'{CONFIG_FILE}' not found. Creating from template.")
        try:
            import shutil
            shutil.copyfile('config/config.ini.template', CONFIG_FILE)
        except FileNotFoundError:
            logging.error("'config/config.ini.template' not found.")
    if not os.path.exists(LAYOUT_FILE):
        logging.info(f"'{LAYOUT_FILE}' not found. Creating a default layout.")
        default_layout = [
            {"id": "widget_running", "type": "summary_count", "label": "Jobs Running", "icon": "fas fa-running", "api_metric": "running_count", "modal_data_key": "jobs_running", "modal_title": "Running Jobs", "modal_item_renderer": "renderJobItem", "color_class": "color-blue"},
            {"id": "widget_abend", "type": "summary_count", "label": "Jobs Abend", "icon": "fas fa-exclamation-triangle", "api_metric": "abend_count", "modal_data_key": "jobs_abend", "modal_title": "Abended Jobs", "modal_item_renderer": "renderJobItem", "color_class": "color-red"}
        ]
        with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_layout, f, indent=4)

if __name__ == '__main__':
    initial_setup()
    try:
        import pystray
        import PIL
        setup_tray()
    except (ImportError, Exception) as e:
        logging.error(f"Could not start GUI mode: {e}", exc_info=False)
        run_console()
