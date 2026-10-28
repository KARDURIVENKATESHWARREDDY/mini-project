"""
Seed script — creates an initial admin user.

Usage:
    cd backend
    python seed_admin.py

Environment: reads DATABASE_URL from .env (or defaults).
"""
import asyncio
import sys
import os

# Allow running from the backend directory
sys.path.insert(0, os.path.dirname(__file__))

from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.db import models as m


async def seed():
    # Ensure tables exist (dev convenience; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)

    async with async_session_factory() as db:
        from sqlalchemy import select
        existing = await db.scalar(select(m.User).where(m.User.email == "admin@cardnet.local"))
        if existing:
            print("Admin user already exists:", existing.email)
            return

        admin = m.User(
            email="23eg106b26@anurag.edu.in",
            full_name="anurag",
            hashed_password=hash_password("anurag"),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print("✅  Admin user created:")
        print("    Email:23eg106b26@anurag.edu.in")
        print("    Password:anurag")
        print("    ⚠️  Change this password immediately after first login!")


if __name__ == "__main__":
    asyncio.run(seed())
