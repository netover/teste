from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
from typing import Any

from src.core import config
from src.core.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Note: The GET and POST endpoints for /api/config have been removed.
# Application configuration is now managed by environment variables and
# the pydantic settings model, not by writing to a config.ini file via an API.
# This makes the configuration more secure and compliant with 12-factor app principles.

@router.get("/api/layout", tags=["Configuration"])
@limiter.limit("30/minute")
async def get_dashboard_layout(request: Request):
    """Gets the current dashboard layout."""
    layout_file = config.get_layout_file()
    try:
        with open(layout_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # If the file doesn't exist, return a default empty layout.
        return []
    except Exception as e:
        # Log the exception and return an empty list as a fallback.
        print(f"Error reading layout file: {e}")
        return []


@router.post("/api/layout", tags=["Configuration"])
@limiter.limit("10/minute")
async def save_dashboard_layout(request: Request, new_layout: list[dict[str, Any]]):
    """Saves the new dashboard layout."""
    layout_file = config.get_layout_file()
    try:
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(new_layout, f, indent=4)
        return {"success": True, "message": "Layout saved successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}, 500