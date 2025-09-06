import logging
import json
import configparser
import re
import os
from typing import List, Dict, Any

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field

from src.core import config
from src.hwa_connector import HWAClient
from src.security import load_key, encrypt_password

# --- App Setup ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static Files and Templates ---
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# --- Pydantic Models ---
class ConfigModel(BaseModel):
    hostname: str = Field(..., max_length=255, pattern=r'^[a-zA-Z0-9.-]+$')
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str | None = None
    verify_ssl: bool = False

# --- Exception Handlers ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected internal server error occurred."},
    )

# --- Services ---
def get_client() -> HWAClient:
    if not config.CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="Configuration file not found.")
    try:
        return HWAClient(config_path=str(config.CONFIG_FILE))
    except Exception as e:
        logging.error(f"Failed to create HWAClient: {e}")
        raise

def is_oql_query_safe(query: str) -> bool:
    blocked_keywords = ['DELETE', 'UPDATE', 'INSERT', 'CARRYFORWARD', 'CANCEL', 'HOLD', 'RELEASE', 'RERUN', 'SUBMIT']
    for keyword in blocked_keywords:
        if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
            logging.warning(f"Blocked OQL query with keyword: {keyword}")
            return False
    return True

# --- HTML Routes ---
@app.get("/", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def index(request: Request):
    try:
        with open(config.LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
    except Exception:
        layout_data = [{"type": "error", "message": "Could not load layout file."}]
    return templates.TemplateResponse("index.html", {"request": request, "layout_data": layout_data})

@app.get("/config", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})

@app.get("/dashboard_editor", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def dashboard_editor_page(request: Request):
    return templates.TemplateResponse("dashboard_editor.html", {"request": request})

@app.get("/help", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

@app.get("/oql_help", response_class=HTMLResponse)
@limiter.limit("100/minute")
async def oql_help_page(request: Request):
    return templates.TemplateResponse("oql_help.html", {"request": request})

# --- API Routes ---
@app.get("/api/dashboard_data")
@limiter.limit("30/minute")
async def get_dashboard_data(request: Request):
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

@app.get("/api/oql")
@limiter.limit("60/minute")
async def execute_oql(request: Request, q: str, source: str = "plan"):
    if not is_oql_query_safe(q):
        raise HTTPException(status_code=400, detail="Query contains potentially harmful keywords.")
    client = get_client()
    if source == "model":
        return client.model.execute_oql_query(q)
    return client.plan.execute_oql_query(q)

async def _job_action_endpoint(action: str, plan_id: str, job_id: str):
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
    return {"success": True, "message": f"'{action.capitalize()}' command sent.", "details": result}

@app.put("/api/plan/{plan_id}/job/{job_id}/action/{action}")
@limiter.limit("10/minute")
async def job_action(request: Request, plan_id: str, job_id: str, action: str):
    return await _job_action_endpoint(action, plan_id, job_id)

@app.get("/api/config")
@limiter.limit("30/minute")
async def get_config_api(request: Request):
    config_parser = configparser.ConfigParser()
    if config.CONFIG_FILE.exists():
        config_parser.read(config.CONFIG_FILE)
    settings = dict(config_parser['tws']) if 'tws' in config_parser else {}
    if 'verify_ssl' in settings:
        settings['verify_ssl'] = config_parser.getboolean('tws', 'verify_ssl')
    return settings

@app.post("/api/config")
@limiter.limit("10/minute")
async def save_config_api(request: Request, data: ConfigModel):
    config_parser = configparser.ConfigParser()
    if config.CONFIG_FILE.exists():
        config_parser.read(config.CONFIG_FILE)
    if 'tws' not in config_parser:
        config_parser.add_section('tws')

    config_parser.set('tws', 'hostname', data.hostname)
    config_parser.set('tws', 'port', str(data.port))
    config_parser.set('tws', 'username', data.username)
    config_parser.set('tws', 'verify_ssl', 'true' if data.verify_ssl else 'false')

    if data.password:
        key = load_key()
        encrypted_pass = encrypt_password(data.password, key)
        config_parser.set('tws', 'password', encrypted_pass.decode('utf-8'))

    os.makedirs(config.CONFIG_DIR, exist_ok=True)
    with open(config.CONFIG_FILE, 'w') as f:
        config_parser.write(f)
    return {"success": "Configuration saved successfully."}

@app.get("/api/dashboard_layout")
@limiter.limit("30/minute")
async def get_dashboard_layout(request: Request):
    try:
        with open(config.LAYOUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        raise

@app.post("/api/dashboard_layout")
@limiter.limit("10/minute")
async def save_dashboard_layout(request: Request, new_layout: List[Dict[str, Any]]):
    with open(config.LAYOUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_layout, f, indent=4)
    return {"success": True, "message": "Layout saved successfully."}

@app.get("/health")
@limiter.limit("120/minute")
async def health_check(request: Request):
    return {"status": "ok"}
