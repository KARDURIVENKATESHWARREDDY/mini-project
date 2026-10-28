"""
API v1 router — aggregates all route handlers.
"""
from fastapi import APIRouter
from app.api.v1 import auth, dashboard, transactions, predictions, batch, models, evaluation, investigations, audit, users, health

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
router.include_router(batch.router, prefix="/batch", tags=["Batch Screening"])
router.include_router(models.router, prefix="/models", tags=["Model Registry"])
router.include_router(evaluation.router, prefix="/evaluation", tags=["Evaluation"])
router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
router.include_router(audit.router, prefix="/audit", tags=["Audit"])
router.include_router(users.router, prefix="/users", tags=["User Management"])
router.include_router(health.router, prefix="/health", tags=["Health"])
