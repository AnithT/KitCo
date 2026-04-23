"""
KitCo — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

# Register event handlers at import time
import app.events.handlers  # noqa: F401

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("🚀 KitCo starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("🛑 KitCo shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="Menu Messaging & Order Orchestration for Cloud Kitchens",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──
app.include_router(api_router, prefix=settings.API_PREFIX)


# ── Health check ──
@app.get("/health", tags=["infra"])
async def health():
    return {"status": "healthy", "app": settings.APP_NAME, "env": settings.APP_ENV}
