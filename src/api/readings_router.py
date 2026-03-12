from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_session
from src.domain.clock import Clock
from src.domain.types import IngestMode
from src.schemas.reading_schemas import (
    ReadingIngestRequest,
    ReadingIngestResponse,
    RecordError,
    ReadingQueryResponse,
)
from src.services.ingestion_service import IngestionService
from src.services.query_service import QueryService


router = APIRouter(prefix="/api/v1/readings", tags=["readings"])


def get_clock(request: Request) -> Clock:
    """Request에서 clock 가져오기"""
    return request.app.state.clock


def parse_iso_datetime(value: str | None) -> datetime | None:
    """ISO8601 문자열을 datetime으로 파싱"""
    if value is None:
        return None
    try:
        # timezone-aware ISO8601 파싱
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError("Timezone-aware ISO8601 required")
        return dt
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO8601 datetime format: {value}",
        )


def validate_time_range(from_val: datetime | None, to_val: datetime | None, name: str) -> None:
    """시간 범위 검증"""
    if from_val is not None and to_val is not None and from_val > to_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{name}_from must be less than or equal to {name}_to",
        )


async def get_ingestion_service(
    session: AsyncSession = Depends(get_async_session),
    clock: Clock = Depends(get_clock),
) -> IngestionService:
    """IngestionService DI factory"""
    return IngestionService(session, clock)


@router.post(
    "",
    summary="센서 데이터 수집",
    description="단일 또는 배치 형태의 센서 데이터를 수집합니다.",
)
async def create_readings(
    request: Request,
    payload: Any = Body(...),  # 단일 객체 또는 배열 모두 허용
    ingest_mode: IngestMode = Query(IngestMode.ATOMIC, description="수집 모드: atomic 또는 partial"),
    service: IngestionService = Depends(get_ingestion_service),
):
    """센서 데이터 수집 API"""
    try:
        result = await service.ingest(payload, ingest_mode)
    except Exception as e:
        # 저장 실패 등 예상치 못한 에러
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )

    # 응답 코드 결정
    response_status = status.HTTP_201_CREATED
    if not result.success:
        if result.is_request_level_error:
            # 요청 수준 오류는 422
            response_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif result.ingest_mode == IngestMode.ATOMIC:
            response_status = status.HTTP_400_BAD_REQUEST
        else:
            # partial: 전체 실패도 200
            response_status = status.HTTP_200_OK
    elif result.accepted_count == 0 and result.rejected_count == 0:
        # 빈 배열 no-op
        response_status = status.HTTP_200_OK
    elif result.ingest_mode == IngestMode.PARTIAL and result.rejected_count > 0:
        # partial: 일부 성공/일부 실패는 200
        response_status = status.HTTP_200_OK

    # 오류 변환
    errors = [
        RecordError(
            index=e.index if e.index is not None else 0,
            field=e.field,
            reason=e.reason,
        )
        for e in result.errors
    ]

    response_data = ReadingIngestResponse(
        success=result.success,
        ingest_mode=result.ingest_mode.value,
        accepted_count=result.accepted_count,
        rejected_count=result.rejected_count,
        errors=errors,
    )

    return JSONResponse(
        content=response_data.model_dump(),
        status_code=response_status,
    )


@router.get(
    "",
    response_model=ReadingQueryResponse,
    summary="측정 데이터 조회",
    description="저장된 측정 데이터를 필터링하여 조회합니다.",
)
async def get_readings(
    serial_number: str | None = Query(None, description="시리얼 번호 필터"),
    mode: str | None = Query(None, description="모드 필터 (NORMAL/EMERGENCY)"),
    sensor_from: str | None = Query(None, description="센서 생성 시각 시작 (ISO8601)"),
    sensor_to: str | None = Query(None, description="센서 생성 시각 종료 (ISO8601)"),
    received_from: str | None = Query(None, description="서버 수신 시각 시작 (ISO8601)"),
    received_to: str | None = Query(None, description="서버 수신 시각 종료 (ISO8601)"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(50, ge=1, le=100, description="페이지당 항목 수 (최대 100)"),
    session: AsyncSession = Depends(get_async_session),
):
    """측정 데이터 조회 API

    - 정렬: sensor_timestamp DESC, id DESC (안정 정렬)
    - total_count == 0이면 total_pages == 0
    """
    # 시간 파싱
    sensor_from_dt = parse_iso_datetime(sensor_from)
    sensor_to_dt = parse_iso_datetime(sensor_to)
    received_from_dt = parse_iso_datetime(received_from)
    received_to_dt = parse_iso_datetime(received_to)

    # 시간 범위 검증
    validate_time_range(sensor_from_dt, sensor_to_dt, "sensor")
    validate_time_range(received_from_dt, received_to_dt, "received")

    # 모드 값 검증
    if mode is not None and mode not in ("NORMAL", "EMERGENCY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mode must be either 'NORMAL' or 'EMERGENCY'",
        )

    # 서비스 호출
    service = QueryService(session)
    result = await service.query_readings(
        serial_number=serial_number,
        mode=mode,
        sensor_from=sensor_from_dt,
        sensor_to=sensor_to_dt,
        received_from=received_from_dt,
        received_to=received_to_dt,
        page=page,
        limit=limit,
    )

    return result
