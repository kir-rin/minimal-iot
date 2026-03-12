from __future__ import annotations

from datetime import datetime
from typing import Optional

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
