"""
Test suite for CARD-Net API endpoints.
Uses httpx + AsyncClient against an in-memory SQLite database.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.models import Base
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.db import models as m

# ── In-memory SQLite test DB ──────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(client: AsyncClient):
    """Create a test admin user (if not exists) and return login tokens."""
    from sqlalchemy import select
    async with TestSessionFactory() as db:
        existing = await db.scalar(select(m.User).where(m.User.email == "admin@test.com"))
        if not existing:
            user = m.User(
                email="admin@test.com",
                full_name="Test Admin",
                hashed_password=hash_password("testpassword123"),
                role="admin",
            )
            db.add(user)
            await db.commit()
    # Login to get tokens
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "testpassword123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_success(admin_user: dict):
    assert "access_token" in admin_user
    assert admin_user["user"]["email"] == "admin@test.com"
    assert admin_user["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_dashboard_summary_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_summary_authenticated(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_transactions" in data
    assert "high_risk_count" in data


@pytest.mark.asyncio
async def test_list_transactions_authenticated(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_batch_jobs(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/batch/jobs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_audit_log_requires_admin(client: AsyncClient):
    response = await client.get("/api/v1/audit")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_audit_log_as_admin(client: AsyncClient, admin_user: dict):
    token = admin_user["access_token"]
    response = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
