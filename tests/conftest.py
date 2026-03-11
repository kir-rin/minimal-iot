from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.clock import FixedClock
from src.main import create_app


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc))


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+psycopg://user:password@localhost:5432/iot_db",
        test_database_url="postgresql+psycopg://user:password@localhost:5432/iot_db_test",
    )


@pytest.fixture
def app(test_settings: Settings, fixed_clock: FixedClock):
    return create_app(settings=test_settings, clock=fixed_clock)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
