"""Audit service — helper to log events to the audit_events table."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models as m


async def log_audit_event(
    db: AsyncSession,
    *,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Append a record to the immutable audit log."""
    event = m.AuditEvent(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        ip_address=ip_address,
        user_agent=user_agent,
        extra=extra,
    )
    db.add(event)
    # Flush without commit — caller controls transaction
    await db.flush()
