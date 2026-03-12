from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SensorStatusData(BaseModel):
    """센서 상태 데이터"""
    model_config = ConfigDict(strict=True)
    
    serial_number: str = Field(..., description="센서 고유 식별 번호")
    last_sensor_timestamp: Optional[datetime] = Field(None, description="마지막 센서 시각")
    last_server_received_at: Optional[datetime] = Field(None, description="마지막 서버 수신 시각")
    last_reported_mode: Optional[str] = Field(None, description="마지막 보고된 모드")
    health_status: str = Field(..., description="건강 상태 (HEALTHY/FAULTY)")
    telemetry_status: str = Field(..., description="텔레메트리 상태 (FRESH/DELAYED/CLOCK_SKEW/OUT_OF_ORDER)")
    health_evaluated_at: Optional[datetime] = Field(None, description="건강 상태 평가 시각")
    last_reading_id: Optional[int] = Field(None, description="마지막 측정값 ID")


class SensorStatusResponse(BaseModel):
    """센서 상태 조회 응답"""
    model_config = ConfigDict(strict=True)
    
    success: bool = Field(..., description="성공 여부")
    data: list[SensorStatusData] = Field(default_factory=list, description="센서 상태 목록")
