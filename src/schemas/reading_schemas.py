from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SensorLocation(BaseModel):
    """센서 위치 정보"""
    model_config = ConfigDict(strict=True)
    
    lat: float = Field(..., ge=-90, le=90, description="위도")
    lng: float = Field(..., ge=-180, le=180, description="경도")


class ReadingPayload(BaseModel):
    """센서 측정 데이터 페이로드"""
    model_config = ConfigDict(strict=True)
    
    serial_number: str = Field(..., min_length=1, description="센서 고유 식별 번호")
    timestamp: str = Field(..., description="센서 기준 데이터 생성 시간 (ISO8601)")
    mode: str = Field(..., pattern="^(NORMAL|EMERGENCY)$", description="작동 모드")
    temperature: float = Field(..., description="온도")
    humidity: float = Field(..., description="습도")
    pressure: float = Field(..., description="기압")
    location: SensorLocation = Field(..., description="위치 정보")
    air_quality: int = Field(..., description="공기질 지수")


# Request는 단일 객체 또는 배열 - union type으로 처리
ReadingIngestRequest = ReadingPayload | list[ReadingPayload]


class RecordError(BaseModel):
    """레코드 단위 오류"""
    model_config = ConfigDict(strict=True)
    
    index: int = Field(..., description="배열 내 인덱스")
    field: str = Field(..., description="오류 필드명")
    reason: str = Field(..., description="오류 사유")


class ReadingIngestResponse(BaseModel):
    """수집 응답"""
    model_config = ConfigDict(strict=True)
    
    success: bool = Field(..., description="전체 성공 여부")
    ingest_mode: str = Field(..., description="수집 모드 (atomic/partial)")
    accepted_count: int = Field(..., description="성공적으로 저장된 레코드 수")
    rejected_count: int = Field(..., description="거절된 레코드 수")
    errors: list[RecordError] = Field(default_factory=list, description="오류 목록")
