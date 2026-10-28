"""Audit log API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func

from app.core.dependencies import DbSession, CurrentUser, require_admin
from app.db import models as m

router = APIRouter()


@router.get("", dependencies=[Depends(require_admin())])
async def list_audit_events(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    action: str = Query(default=None),
    actor_email: str = Query(default=None),
):
    q = select(m.AuditEvent)
    if action:
        q = q.where(m.AuditEvent.action.contains(action))
    if actor_email:
        q = q.where(m.AuditEvent.actor_email.contains(actor_email))
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    q = q.order_by(m.AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    events = result.scalars().all()
    return {
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": str(e.id),
            "actor_email": e.actor_email,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "ip_address": e.ip_address,
            "extra": e.extra,
            "created_at": e.created_at,
        } for e in events],
    }
