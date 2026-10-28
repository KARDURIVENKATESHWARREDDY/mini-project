"""Transactions API endpoints — list, import, detail."""
import csv
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, CurrentUser, require_admin, require_analyst_or_admin
from app.db import models as m
from app.schemas import transactions as s

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_SORT_COLS = {"imported_at", "amount", "time_seconds"}


@router.get("", response_model=s.PaginatedTransactions)
async def list_transactions(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    risk_category: Optional[str] = Query(default=None, pattern="^(low|medium|high)$"),
    review_status: Optional[str] = Query(default=None),
    sort_by: str = Query(default="imported_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    has_prediction: Optional[bool] = Query(default=None),
):
    if sort_by not in ALLOWED_SORT_COLS:
        sort_by = "imported_at"

    # Build query
    q = select(m.Transaction).options(selectinload(m.Transaction.predictions))
    filters = []
    if search:
        filters.append(
            or_(m.Transaction.id.contains(search), m.Transaction.external_id.contains(search))
        )
    # Filter by risk category via latest prediction subquery
    if risk_category or review_status or has_prediction is not None:
        # Join to latest prediction
        latest_pred_subq = (
            select(m.Prediction.transaction_id,
                   func.max(m.Prediction.predicted_at).label("max_pred_at"))
            .group_by(m.Prediction.transaction_id)
            .subquery()
        )
        q = q.outerjoin(
            latest_pred_subq, m.Transaction.id == latest_pred_subq.c.transaction_id
        ).outerjoin(
            m.Prediction,
            and_(
                m.Prediction.transaction_id == m.Transaction.id,
                m.Prediction.predicted_at == latest_pred_subq.c.max_pred_at,
            )
        )
        if risk_category:
            filters.append(m.Prediction.risk_category == risk_category)
        if review_status:
            filters.append(m.Prediction.review_status == review_status)
        if has_prediction is True:
            filters.append(m.Prediction.id.isnot(None))
        elif has_prediction is False:
            filters.append(m.Prediction.id.is_(None))

    if filters:
        q = q.where(and_(*filters))

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = await db.scalar(count_q) or 0

    # Sort + paginate
    sort_col = getattr(m.Transaction, sort_by, m.Transaction.imported_at)
    if sort_dir == "desc":
        sort_col = sort_col.desc()
    q = q.order_by(sort_col).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    txs = result.scalars().unique().all()

    return s.PaginatedTransactions(
        total=total,
        page=page,
        page_size=page_size,
        items=[_tx_to_schema(tx) for tx in txs],
    )


@router.get("/{transaction_id}", response_model=s.TransactionDetail)
async def get_transaction(
    transaction_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(m.Transaction)
        .options(
            selectinload(m.Transaction.predictions).selectinload(m.Prediction.model_version),
            selectinload(m.Transaction.investigation),
        )
        .where(m.Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _tx_detail_to_schema(tx)


def _tx_to_schema(tx: m.Transaction) -> s.TransactionListItem:
    latest = max(tx.predictions, key=lambda p: p.predicted_at, default=None) if tx.predictions else None
    return s.TransactionListItem(
        id=str(tx.id),
        external_id=tx.external_id,
        amount=tx.amount,
        time_seconds=tx.time_seconds,
        imported_at=tx.imported_at,
        fraud_probability=latest.fraud_probability if latest else None,
        risk_category=latest.risk_category if latest else None,
        review_status=latest.review_status if latest else None,
        model_version=latest.model_version_id if latest else None,
        ground_truth_label=tx.ground_truth_label,
    )


def _tx_detail_to_schema(tx: m.Transaction) -> s.TransactionDetail:
    preds = sorted(tx.predictions, key=lambda p: p.predicted_at, reverse=True) if tx.predictions else []
    return s.TransactionDetail(
        id=str(tx.id),
        external_id=tx.external_id,
        amount=tx.amount,
        time_seconds=tx.time_seconds,
        imported_at=tx.imported_at,
        ground_truth_label=tx.ground_truth_label,
        features=s.TransactionFeatures(
            v1=tx.v1, v2=tx.v2, v3=tx.v3, v4=tx.v4, v5=tx.v5,
            v6=tx.v6, v7=tx.v7, v8=tx.v8, v9=tx.v9, v10=tx.v10,
            v11=tx.v11, v12=tx.v12, v13=tx.v13, v14=tx.v14, v15=tx.v15,
            v16=tx.v16, v17=tx.v17, v18=tx.v18, v19=tx.v19, v20=tx.v20,
            v21=tx.v21, v22=tx.v22, v23=tx.v23, v24=tx.v24, v25=tx.v25,
            v26=tx.v26, v27=tx.v27, v28=tx.v28,
        ),
        predictions=[s.PredictionSummary(
            id=str(p.id),
            model_version_id=str(p.model_version_id),
            model_name=p.model_version.name if p.model_version else None,
            channel=p.channel,
            fraud_probability=p.fraud_probability,
            risk_category=p.risk_category,
            shap_values=p.shap_values,
            review_status=p.review_status,
            predicted_at=p.predicted_at,
        ) for p in preds],
        investigation_id=str(tx.investigation.id) if tx.investigation else None,
    )
