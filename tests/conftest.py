from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

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
        database_url="sqlite:///:memory:",
        test_database_url="sqlite:///:memory:",
    )


@pytest.fixture
def db_engine():
    """테스트용 인메모리 SQLite 엔진 - 모든 연결이 동일한 DB 사용"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 모든 연결이 동일한 DB 사용
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session_factory(db_engine):
    """테스트용 세션 팩토리"""
    return sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(db_session_factory):
    """테스트용 DB 세션"""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(test_settings: Settings, fixed_clock: FixedClock, db_engine, db_session_factory):
    return create_app(
        settings=test_settings,
        clock=fixed_clock,
        session_factory=db_session_factory,
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
