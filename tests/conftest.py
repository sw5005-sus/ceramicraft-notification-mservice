import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from ceramicraft_notification_mservice.http.router import create_app
from ceramicraft_notification_mservice.models.device_token import Base
from ceramicraft_notification_mservice.service import NotificationService


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for all async fixtures."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_container():
    """Start a postgres testcontainer for the whole session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(pg_container):
    """Return asyncpg-compatible DB URL."""
    return pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
def db_engine(event_loop, db_url):
    """Session-scoped async engine with schema created."""

    async def _create():
        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return engine

    engine = event_loop.run_until_complete(_create())
    yield engine
    event_loop.run_until_complete(engine.dispose())


@pytest.fixture(scope="session")
def session_factory(db_engine):
    """Session-scoped async session factory."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clear_db(event_loop, db_engine):
    """Truncate device_tokens before each test."""
    yield

    async def _truncate():
        async with db_engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE device_tokens RESTART IDENTITY"))

    event_loop.run_until_complete(_truncate())


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
def http_client(event_loop, session_factory):
    """Async HTTP client for FastAPI testing."""
    app = create_app(session_factory)
    transport = ASGITransport(app=app)  # type: ignore[arg-type]

    async def _make_client():
        return AsyncClient(transport=transport, base_url="http://test")

    client = event_loop.run_until_complete(_make_client())
    yield client
    event_loop.run_until_complete(client.aclose())
