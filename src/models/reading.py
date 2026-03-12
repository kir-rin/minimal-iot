from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Reading(Base):
    """센서 측정 데이터 모델"""
    
    __tablename__ = "readings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_timestamp: Mapped[str] = mapped_column(String(50), nullable=False)
    sensor_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    server_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    pressure: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Reading(id={self.id}, serial={self.serial_number}, timestamp={self.sensor_timestamp})>"
