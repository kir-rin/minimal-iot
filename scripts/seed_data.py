"""
Database seed script for initial test data.

Usage:
    docker-compose exec backend python scripts/seed_data.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import build_async_session_factory
from src.config.settings import get_settings
from src.models.reading import Reading
from src.models.sensor_status import SensorCurrentStatus
from src.domain.status import HealthStatus, TelemetryStatus


async def seed_data(session: AsyncSession) -> None:
    """Insert initial test data."""
    now = datetime.now(timezone.utc)
    
    # Create test readings
    test_readings = [
        Reading(
            serial_number="SN-TEST-001",
            sensor_timestamp=now - timedelta(minutes=5),
            raw_timestamp=(now - timedelta(minutes=5)).isoformat(),
            server_received_at=now - timedelta(minutes=4, seconds=55),
            mode="NORMAL",
            temperature=23.5,
            humidity=45.2,
            pressure=1013.25,
            air_quality=42,
            latitude=37.5665,
            longitude=126.9780,
        ),
        Reading(
            serial_number="SN-TEST-001",
            sensor_timestamp=now - timedelta(minutes=10),
            raw_timestamp=(now - timedelta(minutes=10)).isoformat(),
            server_received_at=now - timedelta(minutes=9, seconds=55),
            mode="NORMAL",
            temperature=23.8,
            humidity=44.9,
            pressure=1013.10,
            air_quality=41,
            latitude=37.5667,
            longitude=126.9782,
        ),
        Reading(
            serial_number="SN-TEST-002",
            sensor_timestamp=now - timedelta(minutes=2),
            raw_timestamp=(now - timedelta(minutes=2)).isoformat(),
            server_received_at=now - timedelta(minutes=1, seconds=55),
            mode="EMERGENCY",
            temperature=28.5,
            humidity=55.0,
            pressure=1012.80,
            air_quality=65,
            latitude=37.5700,
            longitude=126.9820,
        ),
    ]
    
    for reading in test_readings:
        session.add(reading)
    
    await session.flush()
    
    # Create sensor statuses
    test_statuses = [
        SensorCurrentStatus(
            serial_number="SN-TEST-001",
            last_sensor_timestamp=now - timedelta(minutes=5),
            last_server_received_at=now - timedelta(minutes=4, seconds=55),
            last_reported_mode="NORMAL",
            health_status=HealthStatus.HEALTHY,
            telemetry_status=TelemetryStatus.FRESH,
            health_evaluated_at=now,
            last_reading_id=test_readings[0].id,
        ),
        SensorCurrentStatus(
            serial_number="SN-TEST-002",
            last_sensor_timestamp=now - timedelta(minutes=2),
            last_server_received_at=now - timedelta(minutes=1, seconds=55),
            last_reported_mode="EMERGENCY",
            health_status=HealthStatus.HEALTHY,
            telemetry_status=TelemetryStatus.FRESH,
            health_evaluated_at=now,
            last_reading_id=test_readings[2].id,
        ),
    ]
    
    for status in test_statuses:
        session.add(status)
    
    await session.commit()
    print("✅ Seed data inserted successfully!")
    print(f"   - {len(test_readings)} readings")
    print(f"   - {len(test_statuses)} sensor statuses")


async def main() -> None:
    """Main entry point."""
    settings = get_settings()
    session_factory = build_async_session_factory(settings)
    
    if session_factory is None:
        print("❌ Failed to connect to database")
        return
    
    async with session_factory() as session:
        await seed_data(session)


if __name__ == "__main__":
    asyncio.run(main())
