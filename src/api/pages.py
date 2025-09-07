from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import json

from src.core import config
from fastapi.templating import Jinja2Templates

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

@router.get("/", response_class=HTMLResponse, tags=["Pages"])
@limiter.limit("100/minute")
async def index(request: Request):
    try:
        with open(config.LAYOUT_FILE, 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
    except Exception:
        layout_data = [{"type": "error", "message": "Could not load layout file."}]
    return templates.TemplateResponse("index.html", {"request": request, "layout_data": layout_data})

@router.get("/config", response_class=HTMLResponse, tags=["Pages"])
@limiter.limit("100/minute")
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})

@router.get("/dashboard_editor", response_class=HTMLResponse, tags=["Pages"])
@limiter.limit("100/minute")
async def dashboard_editor_page(request: Request):
    return templates.TemplateResponse("dashboard_editor.html", {"request": request})

@router.get("/help", response_class=HTMLResponse, tags=["Pages"])
@limiter.limit("100/minute")
async def help_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

@router.get("/oql_help", response_class=HTMLResponse, tags=["Pages"])
@limiter.limit("100/minute")
async def oql_help_page(request: Request):
    return templates.TemplateResponse("oql_help.html", {"request": request})

@router.get("/health", tags=["Pages"])
@limiter.limit("120/minute")
async def health_check(request: Request):
    return {"status": "ok"}
