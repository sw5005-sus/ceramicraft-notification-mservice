from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from ceramicraft_notification_mservice.http.router import create_app
from ceramicraft_notification_mservice.models.device_token import Base
from ceramicraft_notification_mservice.service import NotificationService


@pytest.fixture(scope="session")
def pg_container():
    """Start a postgres testcontainer for the whole test session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
async def db_engine(pg_container):
    """Session-scoped async engine with schema created."""
    url = pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine):
    """Session-scoped async session factory."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def clear_db(db_engine):
    """Truncate device_tokens before each test."""
    yield
    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE device_tokens RESTART IDENTITY"))


@pytest.fixture
def svc(session_factory):
    """gRPC servicer fixture."""
    return NotificationService(session_factory=session_factory)


@pytest.fixture
def ctx():
    """Mock gRPC ServicerContext."""
    mock_context = MagicMock()
    mock_context.abort = AsyncMock()
    return mock_context


@pytest.fixture
async def http_client(session_factory):
    """Async HTTP client for FastAPI testing."""
    app = create_app(session_factory)
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
