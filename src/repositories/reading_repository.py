from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.reading import Reading
from src.domain.types import NormalizedReading


class ReadingRepository:
    """Reading 데이터 접근 레포지토리 (Async)"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, reading: NormalizedReading, server_received_at: datetime) -> Reading:
        """새로운 reading 저장"""
        db_reading = Reading(
            serial_number=reading.serial_number,
            raw_timestamp=reading.raw_timestamp,
            sensor_timestamp=reading.sensor_timestamp,
            server_received_at=server_received_at,
            mode=reading.mode.value,
            temperature=reading.temperature,
            humidity=reading.humidity,
            pressure=reading.pressure,
            latitude=reading.latitude,
            longitude=reading.longitude,
            air_quality=reading.air_quality,
        )
        self._session.add(db_reading)
        await self._session.flush()  # ID 할당을 위해 flush
        return db_reading

    async def get_by_id(self, reading_id: int) -> Optional[Reading]:
        """ID로 조회"""
        result = await self._session.execute(
            select(Reading).where(Reading.id == reading_id)
        )
        return result.scalar_one_or_none()

    async def get_by_serial_number(self, serial_number: str, limit: int = 100) -> list[Reading]:
        """시리얼 번호로 조회"""
        result = await self._session.execute(
            select(Reading)
            .where(Reading.serial_number == serial_number)
            .order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_for_sensor(self, serial_number: str) -> Optional[Reading]:
        """센서별 최신 reading 조회"""
        result = await self._session.execute(
            select(Reading)
            .where(Reading.serial_number == serial_number)
            .order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_readings_with_filters(
        self,
        serial_number: Optional[str] = None,
        mode: Optional[str] = None,
        sensor_from: Optional[datetime] = None,
        sensor_to: Optional[datetime] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Reading], int]:
        """필터링된 readings 조회 (pagination 지원)

        Returns:
            tuple: (readings 리스트, 전체 개수)
        """
        # 기본 쿼리
        stmt = select(Reading)

        # 필터 적용
        if serial_number:
            stmt = stmt.where(Reading.serial_number == serial_number)
        if mode:
            stmt = stmt.where(Reading.mode == mode)
        if sensor_from:
            stmt = stmt.where(Reading.sensor_timestamp >= sensor_from)
        if sensor_to:
            stmt = stmt.where(Reading.sensor_timestamp <= sensor_to)
        if received_from:
            stmt = stmt.where(Reading.server_received_at >= received_from)
        if received_to:
            stmt = stmt.where(Reading.server_received_at <= received_to)

        # 전체 개수 계산
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # 정렬 및 pagination 적용
        offset = (page - 1) * limit
        stmt = stmt.order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        readings = result.scalars().all()

        return list(readings), total_count
