from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
import configparser
import json
import os
from typing import Any

from src.core import config
from src.security import load_key, encrypt_password

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class ConfigModel(BaseModel):
    hostname: str = Field(..., max_length=255, pattern=r'^[a-zA-Z0-9.-]+$')
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str | None = None
    verify_ssl: bool = False

@router.get("/api/config", tags=["Configuration"])
@limiter.limit("30/minute")
async def get_config_api(request: Request):
    config_parser = configparser.ConfigParser()
    if config.CONFIG_FILE.exists():
        config_parser.read(config.CONFIG_FILE)
    settings = dict(config_parser['tws']) if 'tws' in config_parser else {}
    if 'verify_ssl' in settings:
        settings['verify_ssl'] = config_parser.getboolean('tws', 'verify_ssl')
    return settings

@router.post("/api/config", tags=["Configuration"])
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

@router.get("/api/dashboard_layout", tags=["Configuration"])
@limiter.limit("30/minute")
async def get_dashboard_layout(request: Request):
    try:
        with open(config.LAYOUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        raise

@router.post("/api/dashboard_layout", tags=["Configuration"])
@limiter.limit("10/minute")
async def save_dashboard_layout(request: Request, new_layout: list[dict[str, Any]]):
    with open(config.LAYOUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_layout, f, indent=4)
    return {"success": True, "message": "Layout saved successfully."}
