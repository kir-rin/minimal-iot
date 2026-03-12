from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_session
from src.services.query_service import QueryService, get_query_service
from src.schemas.sensor_schemas import SensorStatusResponse


router = APIRouter(prefix="/api/v1/sensors", tags=["sensors"])


@router.get(
    "/status",
    response_model=SensorStatusResponse,
    summary="센서 상태 조회",
    description="센서별 현재 상태를 조회합니다.",
)
async def get_sensor_status(
    serial_number: str | None = Query(None, description="특정 센서 조회"),
    health_status: str | None = Query(None, description="건강 상태 필터 (HEALTHY/FAULTY)"),
    session: AsyncSession = Depends(get_async_session),
) -> SensorStatusResponse:
    """센서 상태 조회 API

    - 프론트엔드가 별도 계산 없이 상태를 표시할 수 있도록 상태 정보 제공
    - readings API와는 별도로 상태 정보 제공
    """
    # health_status 값 검증
    if health_status is not None and health_status not in ("HEALTHY", "FAULTY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="health_status must be either 'HEALTHY' or 'FAULTY'",
        )

    service = QueryService(session)
    result = await service.query_sensor_status(
        serial_number=serial_number,
        health_status=health_status,
    )

    return result


@router.post(
    "/{serial_number}/mode",
    summary="모드 변경 요청",
    description="특정 센서의 모드 변경을 요청합니다.",
)
async def request_mode_change(
    serial_number: str,
    request: dict,  # Phase 5에서 구현
    session: AsyncSession = Depends(get_async_session),
):
    """모드 변경 요청 API (Phase 5에서 구현)"""
    # TODO: Phase 5에서 구현
    return {
        "success": True,
        "serial_number": serial_number,
        "requested_mode": request.get("target_mode"),
        "requested_at": "2024-05-23T08:31:00Z",
        "sensor_known": True,
    }
