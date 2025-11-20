from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from contextlib import asynccontextmanager

from app.routers import auth, subscriptions, analytics, devices, settings, business, reminders
from app.scheduler.reminder_scheduler import reminder_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting up...")
    try:
        reminder_scheduler.start()
        logger.info("Reminder scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start reminder scheduler: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    try:
        reminder_scheduler.stop()
        logger.info("Reminder scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping reminder scheduler: {str(e)}")


# Get API root path from environment (for nginx /api/ prefix)
api_root = os.getenv("API_ROOT", "")

app = FastAPI(
    title="Subscription Tracking API (FastAPI)",
    lifespan=lifespan,
    openapi_url=f"{api_root}/openapi.json",
    docs_url=f"{api_root}/docs",
    redoc_url=f"{api_root}/redoc",
)

frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = (
    [o.strip() for o in frontend_url.split(",") if o.strip()] if frontend_url else []
)

# Default dev origins similar to NestJS
allowed_origins = allowed_origins or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:19006",
    "http://127.0.0.1:19006",
    "http://localhost:8081",  # Expo dev server
    "http://127.0.0.1:8081",  # Expo dev server
    "http://54.164.79.71",     # Production frontend (port 80)
    "http://54.164.79.71:3000", # Production frontend (port 3000)
    "http://subsy.tech",
    "https://subsy.tech",
]

# CORS configuration - must be added before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "X-Requested-With",
        "Accept-Language",
        "Content-Language",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "X-Account-Context",
    ],
    expose_headers=["Authorization"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(business.router, prefix="/business", tags=["business"])
app.include_router(reminders.router, prefix="/reminders", tags=["reminders"])


@app.get("/health")
def health():
    return {"status": "ok"}


