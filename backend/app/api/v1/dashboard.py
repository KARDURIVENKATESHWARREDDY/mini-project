"""Dashboard analytics endpoints."""
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Query
from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, CurrentUser
from app.db import models as m
from app.schemas import dashboard as s

router = APIRouter()


@router.get("/summary", response_model=s.DashboardSummary)
async def get_summary(db: DbSession, current_user: CurrentUser):
    """KPI counters for dashboard cards."""
    # Total transactions
    total_tx = await db.scalar(select(func.count()).select_from(m.Transaction))
    # Transactions with high-risk predictions
    high_risk = await db.scalar(
        select(func.count()).select_from(m.Prediction)
        .where(m.Prediction.risk_category == "high")
    )
    # Confirmed fraud (analyst-labelled, not model predictions)
    confirmed_fraud = await db.scalar(
        select(func.count()).select_from(m.Investigation)
        .where(m.Investigation.confirmed_label == 1)
    )
    # Pending review
    pending_review = await db.scalar(
        select(func.count()).select_from(m.Prediction)
        .where(m.Prediction.review_status == "pending")
    )
    # Open investigations
    open_investigations = await db.scalar(
        select(func.count()).select_from(m.Investigation)
        .where(m.Investigation.status.in_(["open", "assigned", "escalated"]))
    )
    # Active model info
    model_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.is_active == True).limit(1)
    )
    active_model = model_result.scalar_one_or_none()
    # Latest evaluation run for active model
    eval_result = None
    if active_model:
        eval_q = await db.execute(
            select(m.EvaluationRun)
            .where(m.EvaluationRun.model_version_id == active_model.id,
                   m.EvaluationRun.status == "completed")
            .order_by(m.EvaluationRun.completed_at.desc())
            .limit(1)
        )
        eval_result = eval_q.scalar_one_or_none()

    return s.DashboardSummary(
        total_transactions=total_tx or 0,
        high_risk_count=high_risk or 0,
        confirmed_fraud_count=confirmed_fraud or 0,
        pending_review_count=pending_review or 0,
        open_investigations=open_investigations or 0,
        active_model=s.ActiveModelInfo(
            id=str(active_model.id),
            name=active_model.name,
            version_tag=active_model.version_tag,
            channel=active_model.channel,
        ) if active_model else None,
        latest_metrics=s.LatestMetrics(
            precision=eval_result.precision,
            recall=eval_result.recall,
            f1_score=eval_result.f1_score,
            pr_auc=eval_result.pr_auc,
            roc_auc=eval_result.roc_auc,
        ) if eval_result else None,
    )


@router.get("/volume-trend", response_model=List[s.TimeSeriesPoint])
async def get_volume_trend(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
):
    """Transaction volume over the last N days (grouped by day)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    from app.core.config import settings
    is_sqlite = (db.bind.dialect.name == "sqlite") if db.bind else ("sqlite" in settings.DATABASE_URL)
    date_expr = "DATE(imported_at)" if is_sqlite else "DATE(imported_at AT TIME ZONE 'UTC')"
    result = await db.execute(
        text(f"""
            SELECT {date_expr} as day,
                   COUNT(*) as count
            FROM transactions
            WHERE imported_at >= :since
            GROUP BY day
            ORDER BY day ASC
        """),
        {"since": since},
    )
    rows = result.fetchall()
    return [s.TimeSeriesPoint(date=str(r.day), value=r.count) for r in rows]


@router.get("/fraud-trend", response_model=List[s.TimeSeriesPoint])
async def get_fraud_trend(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
):
    """High-risk prediction count over the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    from app.core.config import settings
    is_sqlite = (db.bind.dialect.name == "sqlite") if db.bind else ("sqlite" in settings.DATABASE_URL)
    date_expr = "DATE(predicted_at)" if is_sqlite else "DATE(predicted_at AT TIME ZONE 'UTC')"
    result = await db.execute(
        text(f"""
            SELECT {date_expr} as day,
                   COUNT(*) as count
            FROM predictions
            WHERE risk_category = 'high' AND predicted_at >= :since
            GROUP BY day
            ORDER BY day ASC
        """),
        {"since": since},
    )
    rows = result.fetchall()
    return [s.TimeSeriesPoint(date=str(r.day), value=r.count) for r in rows]


@router.get("/risk-distribution", response_model=s.RiskDistribution)
async def get_risk_distribution(db: DbSession, current_user: CurrentUser):
    """Count of predictions in each risk tier."""
    result = await db.execute(
        select(m.Prediction.risk_category, func.count().label("count"))
        .group_by(m.Prediction.risk_category)
    )
    rows = result.fetchall()
    dist = {"low": 0, "medium": 0, "high": 0}
    for row in rows:
        if row.risk_category in dist:
            dist[row.risk_category] = row.count
    return s.RiskDistribution(**dist)


@router.get("/recent-alerts", response_model=List[s.RecentAlert])
async def get_recent_alerts(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Most recent high-risk predictions."""
    result = await db.execute(
        select(m.Prediction, m.Transaction)
        .join(m.Transaction, m.Prediction.transaction_id == m.Transaction.id)
        .where(m.Prediction.risk_category == "high")
        .order_by(m.Prediction.predicted_at.desc())
        .limit(limit)
    )
    rows = result.fetchall()
    return [
        s.RecentAlert(
            prediction_id=str(pred.id),
            transaction_id=str(tx.id),
            fraud_probability=pred.fraud_probability,
            risk_category=pred.risk_category,
            amount=tx.amount,
            predicted_at=pred.predicted_at,
            review_status=pred.review_status,
        )
        for pred, tx in rows
    ]


@router.get("/model-health", response_model=s.ModelHealthStatus)
async def get_model_health(db: DbSession, current_user: CurrentUser):
    """Active model health and availability status."""
    model_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.is_active == True).limit(1)
    )
    active_model = model_result.scalar_one_or_none()
    return s.ModelHealthStatus(
        tab_net_available=active_model is not None and active_model.channel == "tab_net",
        seq_net_available=False,   # Requires per-customer sequence IDs — not in benchmark
        geo_net_available=False,   # Requires geographic metadata — not in benchmark
        prof_net_available=False,  # Requires genuine spending profiles — not in benchmark
        fusion_available=False,    # Full fusion requires all channels
        active_model_name=active_model.name if active_model else None,
        active_model_version=active_model.version_tag if active_model else None,
        notes=(
            "SEQ-Net, GEO-Net, and PROF-Net are unavailable: "
            "the benchmark dataset does not provide customer IDs, "
            "geographic metadata, or genuine spending profiles."
        ),
    )
