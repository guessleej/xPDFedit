"""pytest fixtures — in-memory SQLite + 完整 app 依賴覆寫"""
from __future__ import annotations
import os

# init_data 在建立預設 admin 時會讀這個變數，必須在匯入 app 之前設定
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    from app.database import Base
    import app.models  # 確保所有 model 已 import，Base.metadata 才包含所有 table  # noqa
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(engine):
    """給 service 層測試直接使用的 AsyncSession"""
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        # 建立基礎資料（realm + admin user）
        from app.core.init_data import seed_database
        await seed_database(session)
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(engine):
    """覆寫 get_db 的 httpx.AsyncClient，指向測試 DB"""
    from app.main import app
    from app.database import get_db

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with Session() as session:
            from app.core.init_data import seed_database
            await seed_database(session)
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client):
    """取得 admin JWT token"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": os.environ["ADMIN_PASSWORD"],
        "realm": "local",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
