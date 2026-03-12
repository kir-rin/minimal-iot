from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from src.config.database import get_db_session
from src.domain.clock import Clock
from src.domain.types import IngestMode
from src.schemas.reading_schemas import (
    ReadingIngestRequest,
    ReadingIngestResponse,
    RecordError,
)
from src.services.ingestion_service import IngestionService


router = APIRouter(prefix="/api/v1/readings", tags=["readings"])


def get_clock(request: Request) -> Clock:
    """Request에서 clock 가져오기"""
    return request.app.state.clock


@router.post(
    "",
    summary="센서 데이터 수집",
    description="단일 또는 배치 형태의 센서 데이터를 수집합니다.",
)
async def create_readings(
    request: Request,
    payload: Any = Body(...),  # 단일 객체 또는 배열 모두 허용
    ingest_mode: IngestMode = Query(IngestMode.ATOMIC, description="수집 모드: atomic 또는 partial"),
    session: Session = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
):
    """센서 데이터 수집 API"""
    service = IngestionService(session, clock)
    
    try:
        result = service.ingest(payload, ingest_mode)
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
    
    return Response(
        content=response_data.model_dump_json(),
        status_code=response_status,
        media_type="application/json",
    )


@router.get(
    "",
    summary="측정 데이터 조회",
    description="저장된 측정 데이터를 필터링하여 조회합니다.",
)
async def get_readings(
    serial_number: str | None = Query(None, description="시리얼 번호 필터"),
    mode: str | None = Query(None, description="모드 필터"),
    session: Session = Depends(get_db_session),
):
    """측정 데이터 조회 API (Phase 4에서 구현)"""
    # TODO: Phase 4에서 구현
    return {"success": True, "data": [], "pagination": {}}
