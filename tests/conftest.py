import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from ceramicraft_notification_mservice.http.router import create_app, create_router
from ceramicraft_notification_mservice.models.device_token import Base
from ceramicraft_notification_mservice.service import NotificationService


@pytest.fixture(scope="session")
def event_loop():
    """Redefine event_loop fixture to have session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    """Fixture for a test database engine using testcontainers."""
    with PostgresContainer("postgres:16-alpine") as pg:
        # Correct the URL format for asyncpg
        conn_url = pg.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://"
        )
        engine = create_async_engine(conn_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine):
    """Fixture for a session factory."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def clear_db(db_engine):
    """Fixture to clear the database before each test."""
    yield
    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE device_tokens RESTART IDENTITY"))


@pytest.fixture
def svc(session_factory):
    """Fixture for the NotificationService gRPC servicer."""
    return NotificationService(session_factory=session_factory)


@pytest.fixture
def ctx():
    """Fixture for a mock gRPC ServicerContext."""
    mock_context = MagicMock()
    mock_context.abort = AsyncMock()
    return mock_context


@pytest.fixture
async def http_client(session_factory):
    """Fixture for an async HTTP client for testing the FastAPI app."""
    app = create_app(session_factory)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
