from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class SensorCurrentStatus(Base):
    """센서 현재 상태 모델"""
    
    __tablename__ = "sensor_current_status"
    
    serial_number: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_sensor_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_server_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reported_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    health_status: Mapped[str] = mapped_column(String(50), nullable=False, default="HEALTHY")
    telemetry_status: Mapped[str] = mapped_column(String(50), nullable=False, default="FRESH")
    health_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reading_id: Mapped[int] = mapped_column(Integer, ForeignKey("readings.id"), nullable=False)
    
    def __repr__(self) -> str:
        return f"<SensorCurrentStatus(serial={self.serial_number}, health={self.health_status})>"
