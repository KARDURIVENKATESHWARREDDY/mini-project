"""Investigations API endpoints."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, CurrentUser, require_analyst_or_admin
from app.db import models as m
from app.services.audit import log_audit_event

router = APIRouter()


@router.post("", dependencies=[Depends(require_analyst_or_admin())])
async def open_investigation(
    transaction_id: str,
    priority: str = "medium",
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    # Check transaction exists
    tx_result = await db.execute(select(m.Transaction).where(m.Transaction.id == transaction_id))
    tx = tx_result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Check no open investigation already exists
    existing = await db.execute(
        select(m.Investigation).where(
            m.Investigation.transaction_id == transaction_id,
            m.Investigation.status.in_(["open", "assigned", "escalated"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An open investigation already exists for this transaction.")
    inv = m.Investigation(
        transaction_id=transaction_id,
        opened_by_id=current_user.id,
        priority=priority,
        status=m.InvestigationStatus.open,
    )
    db.add(inv)
    await db.flush()
    event = m.InvestigationEvent(
        investigation_id=inv.id,
        actor_id=current_user.id,
        event_type="opened",
        notes="Investigation opened.",
    )
    db.add(event)
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="investigation.opened", resource_type="investigation", resource_id=inv.id)
    await db.commit()
    return {"id": str(inv.id), "status": inv.status, "message": "Investigation opened."}


@router.get("")
async def list_investigations(
    db: DbSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    from sqlalchemy import func
    q = select(m.Investigation).options(
        selectinload(m.Investigation.opened_by),
        selectinload(m.Investigation.assigned_to),
        selectinload(m.Investigation.transaction),
    )
    if status:
        q = q.where(m.Investigation.status == status)
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    q = q.order_by(m.Investigation.opened_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    invs = result.scalars().unique().all()
    return {
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": str(inv.id),
            "transaction_id": str(inv.transaction_id),
            "status": inv.status,
            "priority": inv.priority,
            "opened_by": inv.opened_by.full_name if inv.opened_by else None,
            "assigned_to": inv.assigned_to.full_name if inv.assigned_to else None,
            "opened_at": inv.opened_at,
            "updated_at": inv.updated_at,
            "amount": inv.transaction.amount if inv.transaction else None,
        } for inv in invs],
    }


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(m.Investigation).options(
            selectinload(m.Investigation.events).selectinload(m.InvestigationEvent.actor),
            selectinload(m.Investigation.opened_by),
            selectinload(m.Investigation.assigned_to),
            selectinload(m.Investigation.transaction).selectinload(m.Transaction.predictions),
        ).where(m.Investigation.id == investigation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "id": str(inv.id),
        "transaction_id": str(inv.transaction_id),
        "status": inv.status,
        "priority": inv.priority,
        "confirmed_label": inv.confirmed_label,
        "resolution_notes": inv.resolution_notes,
        "opened_by": inv.opened_by.full_name if inv.opened_by else None,
        "assigned_to": inv.assigned_to.full_name if inv.assigned_to else None,
        "opened_at": inv.opened_at,
        "resolved_at": inv.resolved_at,
        "events": [{
            "id": str(e.id),
            "event_type": e.event_type,
            "actor": e.actor.full_name if e.actor else None,
            "notes": e.notes,
            "created_at": e.created_at,
        } for e in inv.events],
        "transaction": {
            "amount": inv.transaction.amount,
            "time_seconds": inv.transaction.time_seconds,
            "ground_truth_label": inv.transaction.ground_truth_label,
        } if inv.transaction else None,
    }


@router.post("/{investigation_id}/events", dependencies=[Depends(require_analyst_or_admin())])
async def add_investigation_event(
    investigation_id: str,
    event_type: str,
    notes: Optional[str] = None,
    confirmed_label: Optional[int] = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    result = await db.execute(select(m.Investigation).where(m.Investigation.id == investigation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    event = m.InvestigationEvent(
        investigation_id=investigation_id,
        actor_id=current_user.id,
        event_type=event_type,
        notes=notes,
    )
    db.add(event)

    if event_type in ("resolve_fraud", "resolve_legitimate", "dismiss"):
        inv.status = m.InvestigationStatus.resolved
        inv.confirmed_label = confirmed_label
        inv.resolution_notes = notes
        inv.resolved_at = datetime.now(timezone.utc)
    elif event_type == "escalate":
        inv.status = m.InvestigationStatus.escalated
    inv.updated_at = datetime.now(timezone.utc)

    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action=f"investigation.{event_type}", resource_type="investigation",
                          resource_id=investigation_id)
    await db.commit()
    return {"message": f"Event '{event_type}' recorded.", "investigation_status": inv.status}
