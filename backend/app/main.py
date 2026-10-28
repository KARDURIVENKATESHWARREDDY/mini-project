"""
CARD-Net Backend — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.db import models as db_models
from app.api.v1 import router as api_v1_router

configure_logging()


import logging

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Tables are managed by Alembic migrations; this is a safety net for dev.
    # If Postgres is not available, log a warning instead of crashing.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(db_models.Base.metadata.create_all)
        _log.info("Database connected and schema verified.")
    except Exception as exc:
        _log.warning(
            "Could not connect to the database on startup: %s. "
            "API will start but database-dependent endpoints will fail. "
            "Ensure PostgreSQL is running and DATABASE_URL is correct in .env",
            exc,
        )
    yield
    await engine.dispose()


limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="CARD-Net API",
    description=(
        "Credit Card Fraud Detection — Research & Decision-Support Prototype\n\n"
        "**Institution:** Anurag University, Department of Artificial Intelligence\n\n"
        "⚠️ This is a research prototype. It does not automatically block real banking transactions."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

if settings.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

# API routes
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "card-net-api", "version": "1.0.0"}
