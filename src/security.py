from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from src.core.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to verify the X-API-Key header.
    It now reads the expected API key from the centralized Pydantic settings.
    """
    # If no API key is provided by the client, raise an unauthorized error.
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing.",
        )

    # Check the provided key against the one from settings.
    # The settings object ensures there's always a value (even if it's the default).
    if api_key == settings.API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )