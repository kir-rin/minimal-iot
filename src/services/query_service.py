"""Query Service - 조회 로직을 담당하는 서비스 (Async)"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.reading_repository import ReadingRepository
from src.repositories.sensor_status_repository import SensorStatusRepository
from src.schemas.reading_schemas import (
    ReadingData,
    ReadingQueryResponse,
    PaginationInfo,
    SensorMetrics,
    SensorLocation,
)
from src.schemas.sensor_schemas import (
    SensorStatusData,
    SensorStatusResponse,
)


class QueryService:
    """조회 서비스 (Async)"""

    DEFAULT_PAGE = 1
    DEFAULT_LIMIT = 50
    MAX_LIMIT = 100

    def __init__(
        self,
        session: AsyncSession,
        reading_repo: Optional[ReadingRepository] = None,
        status_repo: Optional[SensorStatusRepository] = None,
    ):
        self._session = session
        self._reading_repo = reading_repo or ReadingRepository(session)
        self._status_repo = status_repo or SensorStatusRepository(session)

    async def query_readings(
        self,
        serial_number: Optional[str] = None,
        mode: Optional[str] = None,
        sensor_from: Optional[datetime] = None,
        sensor_to: Optional[datetime] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        page: int = DEFAULT_PAGE,
        limit: int = DEFAULT_LIMIT,
    ) -> ReadingQueryResponse:
        """측정 데이터 조회

        Args:
            serial_number: 시리얼 번호 필터
            mode: 모드 필터
            sensor_from: 센서 생성 시각 시작
            sensor_to: 센서 생성 시각 종료
            received_from: 서버 수신 시각 시작
            received_to: 서버 수신 시각 종료
            page: 페이지 번호 (1-based)
            limit: 페이지당 항목 수

        Returns:
            ReadingQueryResponse
        """
        # limit 검증
        if limit < 1:
            limit = self.DEFAULT_LIMIT
        elif limit > self.MAX_LIMIT:
            limit = self.MAX_LIMIT

        # page 검증
        if page < 1:
            page = self.DEFAULT_PAGE

        # 데이터 조회
        readings, total_count = await self._reading_repo.get_readings_with_filters(
            serial_number=serial_number,
            mode=mode,
            sensor_from=sensor_from,
            sensor_to=sensor_to,
            received_from=received_from,
            received_to=received_to,
            page=page,
            limit=limit,
        )

        # 페이지네이션 계산
        total_pages = 0 if total_count == 0 else (total_count + limit - 1) // limit
        has_next_page = page < total_pages
        has_prev_page = page > 1

        # 응답 데이터 변환
        data = [
            ReadingData(
                id=reading.id,
                serial_number=reading.serial_number,
                timestamp=reading.sensor_timestamp,
                raw_timestamp=reading.raw_timestamp,
                server_received_at=reading.server_received_at,
                mode=reading.mode,
                metrics=SensorMetrics(
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    pressure=reading.pressure,
                    air_quality=reading.air_quality,
                ),
                location=SensorLocation(
                    lat=reading.latitude,
                    lng=reading.longitude,
                ),
            )
            for reading in readings
        ]

        return ReadingQueryResponse(
            success=True,
            data=data,
            pagination=PaginationInfo(
                total_count=total_count,
                current_page=page,
                limit=limit,
                total_pages=total_pages,
                has_next_page=has_next_page,
                has_prev_page=has_prev_page,
            ),
        )

    async def query_sensor_status(
        self,
        serial_number: Optional[str] = None,
        health_status: Optional[str] = None,
    ) -> SensorStatusResponse:
        """센서 상태 조회 (metrics 포함)

        Args:
            serial_number: 특정 센서 조회
            health_status: HEALTHY 또는 FAULTY 필터

        Returns:
            SensorStatusResponse
        """
        statuses = await self._status_repo.get_status_with_filters(
            serial_number=serial_number,
            health_status=health_status,
        )

        data = [
            SensorStatusData(
                serial_number=status["serial_number"],
                last_sensor_timestamp=status["last_sensor_timestamp"],
                last_server_received_at=status["last_server_received_at"],
                last_reported_mode=status["last_reported_mode"],
                health_status=status["health_status"],
                telemetry_status=status["telemetry_status"],
                health_evaluated_at=status["health_evaluated_at"],
                last_reading_id=status["last_reading_id"],
                temperature=status["temperature"],
                humidity=status["humidity"],
                pressure=status["pressure"],
                air_quality=status["air_quality"],
            )
            for status in statuses
        ]

        return SensorStatusResponse(success=True, data=data)


async def get_query_service(session: AsyncSession) -> QueryService:
    """Dependency injection용 QueryService factory"""
    return QueryService(session)
