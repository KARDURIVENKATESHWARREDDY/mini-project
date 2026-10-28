"""FastAPI dependency injection — current user, DB session, role guards."""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import async_session_factory
from app.db import models as m

bearer_scheme = HTTPBearer(auto_error=True)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> m.User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id: str = payload.get("sub", "")
    from sqlalchemy import select
    result = await db.execute(select(m.User).where(m.User.id == user_id, m.User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


CurrentUser = Annotated[m.User, Depends(get_current_user)]


def require_roles(*roles: str):
    """Dependency factory: ensures the current user has at least one of the given roles."""
    async def _check(user: CurrentUser):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {list(roles)}",
            )
        return user
    return _check


def require_admin():
    return require_roles("admin")


def require_analyst_or_admin():
    return require_roles("analyst", "admin")
