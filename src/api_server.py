import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core import config
from src.api import pages, config as api_config, hwa, websockets, monitoring
from src.services.monitoring.websocket import ws_manager
from src.services.monitoring.job_monitor import job_monitor

# --- Lifespan Management for Background Tasks ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Application startup...")
    # Initialize services
    await ws_manager.initialize()
    await job_monitor.initialize()

    # Start background tasks
    pubsub_task = asyncio.create_task(ws_manager.subscribe_to_updates())
    monitoring_task = asyncio.create_task(job_monitor.start_monitoring())

    yield

    # Shutdown
    logging.info("Application shutdown...")
    job_monitor.stop_monitoring()
    monitoring_task.cancel()
    pubsub_task.cancel()
    try:
        await monitoring_task
        await pubsub_task
    except asyncio.CancelledError:
        logging.info("Background tasks cancelled successfully.")

# --- App Setup ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="HWA Neuromorphic Dashboard API",
    lifespan=lifespan
)
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

# --- Static Files ---
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# --- API Routers ---
app.include_router(pages.router)
app.include_router(api_config.router)
app.include_router(hwa.router)
app.include_router(websockets.router)
app.include_router(monitoring.router)

# --- Exception Handlers ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected internal server error occurred."},
    )
