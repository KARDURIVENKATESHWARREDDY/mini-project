"""User management API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr

from app.core.dependencies import DbSession, CurrentUser, require_admin
from app.core.security import hash_password
from app.db import models as m
from app.services.audit import log_audit_event

router = APIRouter()


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "viewer"


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", dependencies=[Depends(require_admin())])
async def list_users(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    total = await db.scalar(select(func.count()).select_from(m.User))
    result = await db.execute(
        select(m.User).order_by(m.User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    return {
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "items": [_user_to_dict(u) for u in users],
    }


@router.post("", dependencies=[Depends(require_admin())])
async def create_user(body: CreateUserRequest, db: DbSession, current_user: CurrentUser):
    existing = await db.scalar(select(m.User).where(m.User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=422, detail="Role must be admin, analyst, or viewer.")
    user = m.User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="user.created", resource_type="user",
                          extra={"email": body.email, "role": body.role})
    await db.commit()
    await db.refresh(user)
    return _user_to_dict(user)


@router.put("/{user_id}", dependencies=[Depends(require_admin())])
async def update_user(user_id: str, body: UpdateUserRequest, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.User).where(m.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        if body.role not in ("admin", "analyst", "viewer"):
            raise HTTPException(status_code=422, detail="Invalid role.")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="user.updated", resource_type="user", resource_id=user_id)
    await db.commit()
    return _user_to_dict(user)


def _user_to_dict(u: m.User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "last_login_at": u.last_login_at,
        "created_at": u.created_at,
    }
