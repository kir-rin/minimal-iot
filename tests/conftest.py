from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.settings import Settings
from src.domain.clock import FixedClock
from src.main import create_app
from src.models import Base


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc))


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        test_database_url="sqlite+aiosqlite:///:memory:",
    )


@pytest_asyncio.fixture
async def async_db_engine():
    """테스트용 인메모리 SQLite 비동기 엔진"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db_session_factory(async_db_engine):
    """테스트용 비동기 세션 팩토리"""
    return async_sessionmaker(
        bind=async_db_engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession
    )


@pytest_asyncio.fixture
async def async_db_session(async_db_session_factory):
    """테스트용 비동기 DB 세션"""
    async with async_db_session_factory() as session:
        yield session


@pytest.fixture
def app(test_settings: Settings, fixed_clock: FixedClock, async_db_session_factory):
    return create_app(
        settings=test_settings,
        clock=fixed_clock,
        async_session_factory=async_db_session_factory,
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
