from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sensor_status import SensorCurrentStatus
from src.models.reading import Reading
from src.domain.types import NormalizedReading, HealthStatus, TelemetryStatus


class SensorStatusRepository:
    """Sensor Current Status 레포지토리 (Async)"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_serial_number(self, serial_number: str) -> Optional[SensorCurrentStatus]:
        """시리얼 번호로 조회"""
        result = await self._session.execute(
            select(SensorCurrentStatus)
            .where(SensorCurrentStatus.serial_number == serial_number)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        reading: NormalizedReading,
        reading_id: int,
        server_received_at: datetime,
        health_status: HealthStatus,
        telemetry_status: TelemetryStatus,
        is_out_of_order: bool = False,
    ) -> SensorCurrentStatus:
        """센서 상태 생성 또는 갱신"""
        existing = await self.get_by_serial_number(reading.serial_number)

        if existing is None:
            # 새로 생성
            status = SensorCurrentStatus(
                serial_number=reading.serial_number,
                last_sensor_timestamp=reading.sensor_timestamp,
                last_server_received_at=server_received_at,
                last_reported_mode=reading.mode.value,
                health_status=health_status.value,
                telemetry_status=telemetry_status.value,
                health_evaluated_at=server_received_at,
                last_reading_id=reading_id,
            )
            self._session.add(status)
        else:
            # 기존 상태 갱신
            existing.last_server_received_at = server_received_at
            existing.last_reported_mode = reading.mode.value
            existing.health_status = health_status.value
            existing.health_evaluated_at = server_received_at
            existing.last_reading_id = reading_id

            # OUT_OF_ORDER이 아닐 때만 last_sensor_timestamp 갱신
            if not is_out_of_order:
                existing.last_sensor_timestamp = reading.sensor_timestamp
                existing.telemetry_status = telemetry_status.value
            else:
                # OUT_OF_ORDER이면 health_status만 갱신
                existing.telemetry_status = TelemetryStatus.OUT_OF_ORDER.value

        await self._session.flush()
        result = existing if existing else await self.get_by_serial_number(reading.serial_number)
        if result is None:
            raise RuntimeError("Failed to create or update sensor status")
        return result

    async def get_all(self) -> list[SensorCurrentStatus]:
        """전체 센서 상태 조회"""
        result = await self._session.execute(select(SensorCurrentStatus))
        return list(result.scalars().all())

    async def get_by_health_status(self, health_status: HealthStatus) -> list[SensorCurrentStatus]:
        """건강 상태로 필터링 조회"""
        result = await self._session.execute(
            select(SensorCurrentStatus)
            .where(SensorCurrentStatus.health_status == health_status.value)
        )
        return list(result.scalars().all())

    async def get_status_with_filters(
        self,
        serial_number: Optional[str] = None,
        health_status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """필터링된 센서 상태 조회 (metrics 포함)

        Args:
            serial_number: 특정 시리얼 번호 (optional)
            health_status: HEALTHY 또는 FAULTY (optional)

        Returns:
            필터링된 센서 상태 목록 (temperature, humidity 포함)
        """
        stmt = (
            select(
                SensorCurrentStatus,
                Reading.temperature,
                Reading.humidity,
                Reading.pressure,
                Reading.air_quality,
            )
            .join(Reading, SensorCurrentStatus.last_reading_id == Reading.id)
        )

        if serial_number:
            stmt = stmt.where(SensorCurrentStatus.serial_number == serial_number)
        if health_status:
            stmt = stmt.where(SensorCurrentStatus.health_status == health_status)

        result = await self._session.execute(stmt)
        rows = result.all()
        
        # Convert to dict with metrics
        status_list = []
        for row in rows:
            status = row[0]
            status_dict = {
                "serial_number": status.serial_number,
                "last_sensor_timestamp": status.last_sensor_timestamp,
                "last_server_received_at": status.last_server_received_at,
                "last_reported_mode": status.last_reported_mode,
                "health_status": status.health_status,
                "telemetry_status": status.telemetry_status,
                "health_evaluated_at": status.health_evaluated_at,
                "last_reading_id": status.last_reading_id,
                "temperature": row[1],
                "humidity": row[2],
                "pressure": row[3],
                "air_quality": row[4],
            }
            status_list.append(status_dict)
        
        return status_list
