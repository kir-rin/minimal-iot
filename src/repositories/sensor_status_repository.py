from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models.sensor_status import SensorCurrentStatus
from src.domain.types import NormalizedReading, HealthStatus, TelemetryStatus


class SensorStatusRepository:
    """Sensor Current Status 레포지토리"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def get_by_serial_number(self, serial_number: str) -> Optional[SensorCurrentStatus]:
        """시리얼 번호로 조회"""
        return (
            self._session.query(SensorCurrentStatus)
            .filter(SensorCurrentStatus.serial_number == serial_number)
            .first()
        )
    
    def upsert(
        self,
        reading: NormalizedReading,
        reading_id: int,
        server_received_at: datetime,
        health_status: HealthStatus,
        telemetry_status: TelemetryStatus,
        is_out_of_order: bool = False,
    ) -> SensorCurrentStatus:
        """센서 상태 생성 또는 갱신"""
        existing = self.get_by_serial_number(reading.serial_number)
        
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
        
        self._session.flush()
        result = existing if existing else self.get_by_serial_number(reading.serial_number)
        if result is None:
            raise RuntimeError("Failed to create or update sensor status")
        return result
    
    def get_all(self) -> list[SensorCurrentStatus]:
        """전체 센서 상태 조회"""
        return self._session.query(SensorCurrentStatus).all()
    
    def get_by_health_status(self, health_status: HealthStatus) -> list[SensorCurrentStatus]:
        """건강 상태로 필터링 조회"""
        return (
            self._session.query(SensorCurrentStatus)
            .filter(SensorCurrentStatus.health_status == health_status.value)
            .all()
        )
