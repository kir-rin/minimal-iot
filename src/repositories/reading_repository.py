from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.reading import Reading
from src.domain.types import NormalizedReading


class ReadingRepository:
    """Reading 데이터 접근 레포지토리"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def create(self, reading: NormalizedReading, server_received_at: datetime) -> Reading:
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
        self._session.flush()  # ID 할당을 위해 flush
        return db_reading
    
    def get_by_id(self, reading_id: int) -> Optional[Reading]:
        """ID로 조회"""
        return self._session.query(Reading).filter(Reading.id == reading_id).first()
    
    def get_by_serial_number(self, serial_number: str, limit: int = 100) -> list[Reading]:
        """시리얼 번호로 조회"""
        return (
            self._session.query(Reading)
            .filter(Reading.serial_number == serial_number)
            .order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
            .limit(limit)
            .all()
        )
    
    def get_latest_for_sensor(self, serial_number: str) -> Optional[Reading]:
        """센서별 최신 reading 조회"""
        return (
            self._session.query(Reading)
            .filter(Reading.serial_number == serial_number)
            .order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
            .first()
        )
    
    def get_readings_with_filters(
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
        query = self._session.query(Reading)
        
        # 필터 적용
        if serial_number:
            query = query.filter(Reading.serial_number == serial_number)
        if mode:
            query = query.filter(Reading.mode == mode)
        if sensor_from:
            query = query.filter(Reading.sensor_timestamp >= sensor_from)
        if sensor_to:
            query = query.filter(Reading.sensor_timestamp <= sensor_to)
        if received_from:
            query = query.filter(Reading.server_received_at >= received_from)
        if received_to:
            query = query.filter(Reading.server_received_at <= received_to)
        
        # 전체 개수 계산
        total_count = query.count()
        
        # 정렬 및 pagination 적용
        offset = (page - 1) * limit
        readings = (
            query
            .order_by(Reading.sensor_timestamp.desc(), Reading.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return readings, total_count
