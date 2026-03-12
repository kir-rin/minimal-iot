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


# Common sensor setup fixtures for reuse across tests

@pytest_asyncio.fixture
async def setup_sensor_with_reading(async_db_session: AsyncSession) -> tuple[str, int]:
    """테스트용 센서와 reading 데이터 설정 (Integration/E2E 테스트용)"""
    from src.models.reading import Reading
    from src.models.sensor_status import SensorCurrentStatus
    from src.domain.types import Mode, HealthStatus
    
    base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
    serial_number = "TEST-SENSOR-001"
    
    # Reading 생성
    reading = Reading(
        serial_number=serial_number,
        raw_timestamp="2024-05-23T08:30:00+00:00",
        sensor_timestamp=base_time,
        server_received_at=base_time,
        mode=Mode.NORMAL.value,
        temperature=25.0,
        humidity=60.0,
        pressure=1013.0,
        latitude=37.5665,
        longitude=126.9780,
        air_quality=50,
    )
    async_db_session.add(reading)
    await async_db_session.flush()
    
    # SensorCurrentStatus 생성 (HEALTHY 상태)
    status = SensorCurrentStatus(
        serial_number=serial_number,
        last_sensor_timestamp=base_time,
        last_server_received_at=base_time,
        last_reported_mode=Mode.NORMAL.value,
        health_status=HealthStatus.HEALTHY.value,
        telemetry_status="FRESH",
        health_evaluated_at=base_time,
        last_reading_id=reading.id,
    )
    async_db_session.add(status)
    await async_db_session.commit()
    
    return serial_number, reading.id


@pytest_asyncio.fixture
async def setup_multiple_sensors(async_db_session: AsyncSession) -> list[dict]:
    """여러 센서 설정: NORMAL, EMERGENCY, MAINTENANCE"""
    from src.models.reading import Reading
    from src.models.sensor_status import SensorCurrentStatus
    from src.domain.types import Mode, HealthStatus
    
    base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
    
    sensors = [
        {"serial": "SENSOR-NORMAL", "mode": Mode.NORMAL},
        {"serial": "SENSOR-EMERGENCY", "mode": Mode.EMERGENCY},
        {"serial": "SENSOR-MAINTENANCE", "mode": Mode.MAINTENANCE},
    ]
    
    for sensor_data in sensors:
        # Reading 생성
        reading = Reading(
            serial_number=sensor_data["serial"],
            raw_timestamp="2024-05-23T08:30:00+00:00",
            sensor_timestamp=base_time,
            server_received_at=base_time,
            mode=sensor_data["mode"].value,
            temperature=25.0,
            humidity=60.0,
            pressure=1013.0,
            latitude=37.5665,
            longitude=126.9780,
            air_quality=50,
        )
        async_db_session.add(reading)
        await async_db_session.flush()
        
        # SensorCurrentStatus 생성
        status = SensorCurrentStatus(
            serial_number=sensor_data["serial"],
            last_sensor_timestamp=base_time,
            last_server_received_at=base_time,
            last_reported_mode=sensor_data["mode"].value,
            health_status=HealthStatus.HEALTHY.value,
            telemetry_status="FRESH",
            health_evaluated_at=base_time,
            last_reading_id=reading.id,
        )
        async_db_session.add(status)
    
    await async_db_session.commit()
    return sensors
