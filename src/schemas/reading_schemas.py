from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

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


# Query API Schemas

class SensorMetrics(BaseModel):
    """센서 측정 지표"""
    model_config = ConfigDict(strict=True)
    
    temperature: float = Field(..., description="온도")
    humidity: float = Field(..., description="습도")
    pressure: float = Field(..., description="기압")
    air_quality: int = Field(..., description="공기질 지수")


class ReadingData(BaseModel):
    """조회 응답의 reading 데이터"""
    model_config = ConfigDict(strict=True)
    
    id: int = Field(..., description="측정값 ID")
    serial_number: str = Field(..., description="센서 고유 식별 번호")
    timestamp: datetime = Field(..., description="정규화된 센서 생성 시각")
    raw_timestamp: str = Field(..., description="원본 timestamp 문자열")
    server_received_at: datetime = Field(..., description="서버 수신 시각")
    mode: str = Field(..., description="작동 모드")
    metrics: SensorMetrics = Field(..., description="측정 지표")
    location: SensorLocation = Field(..., description="위치 정보")


class PaginationInfo(BaseModel):
    """페이지네이션 정보"""
    model_config = ConfigDict(strict=True)
    
    total_count: int = Field(..., description="전체 항목 수")
    current_page: int = Field(..., description="현재 페이지 번호")
    limit: int = Field(..., description="페이지당 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next_page: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev_page: bool = Field(..., description="이전 페이지 존재 여부")


class ReadingQueryResponse(BaseModel):
    """측정 데이터 조회 응답"""
    model_config = ConfigDict(strict=True)
    
    success: bool = Field(..., description="성공 여부")
    data: list[ReadingData] = Field(default_factory=list, description="측정 데이터 목록")
    pagination: PaginationInfo = Field(..., description="페이지네이션 정보")
