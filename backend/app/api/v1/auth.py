"""Authentication API endpoints."""
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import DbSession, CurrentUser
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, decode_token
)
from app.db import models as m
from app.schemas import auth as s
from app.services.audit import log_audit_event

router = APIRouter()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=s.TokenResponse)
async def login(
    request: Request,
    db: DbSession,
    form: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(m.User).where(m.User.email == form.username, m.User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    # Store hashed refresh token
    from datetime import timedelta
    session = m.Session(
        user_id=user.id,
        refresh_token_hash=_hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.add(session)
    await db.commit()
    await log_audit_event(
        db, actor_id=user.id, actor_email=user.email,
        action="user.login", resource_type="user", resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return s.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=s.UserInfo(
            id=str(user.id), email=user.email,
            full_name=user.full_name, role=user.role,
        ),
    )


@router.post("/refresh", response_model=s.TokenResponse)
async def refresh_token(body: s.RefreshRequest, db: DbSession):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    token_hash = _hash_token(body.refresh_token)
    result = await db.execute(
        select(m.Session).where(
            m.Session.refresh_token_hash == token_hash,
            m.Session.is_revoked == False,
        )
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")
    # Revoke old session
    session.is_revoked = True
    user_result = await db.execute(select(m.User).where(m.User.id == session.user_id))
    user = user_result.scalar_one()
    # Issue new pair
    new_access = create_access_token(subject=str(user.id), extra_claims={"role": user.role, "email": user.email})
    new_refresh = create_refresh_token(subject=str(user.id))
    from datetime import timedelta
    new_session = m.Session(
        user_id=user.id,
        refresh_token_hash=_hash_token(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)
    await db.commit()
    return s.TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=s.UserInfo(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role),
    )


@router.post("/logout")
async def logout(body: s.RefreshRequest, db: DbSession, current_user: CurrentUser):
    token_hash = _hash_token(body.refresh_token)
    result = await db.execute(
        select(m.Session).where(m.Session.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_revoked = True
        await db.commit()
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email, action="user.logout")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=s.UserInfo)
async def get_me(current_user: CurrentUser):
    return s.UserInfo(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        last_login_at=current_user.last_login_at,
    )
