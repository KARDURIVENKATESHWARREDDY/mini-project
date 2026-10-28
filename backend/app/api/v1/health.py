"""Health check endpoints — liveness and readiness."""
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import async_session_factory
from app.ml.inference.tabnet_inference import is_model_loaded

router = APIRouter()


@router.get("")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness():
    checks = {"api": "ok", "database": "unknown", "model": "unknown"}
    # DB check
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    # Model check
    checks["model"] = "loaded" if is_model_loaded() else "not_loaded"
    overall = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": overall, "checks": checks}
