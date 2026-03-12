from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_session
from src.domain.clock import Clock
from src.domain.types import Mode
from src.schemas.sensor_schemas import ModeChangeResponse, SensorStatusResponse
from src.services.mode_service import ModeService
from src.services.query_service import QueryService, get_query_service


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


class ModeChangeRequest(BaseModel):
    """모드 변경 요청 바디"""
    mode: str
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """모드 값 검증"""
        valid_modes = [m.value for m in Mode]
        if v not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
        return v


def get_clock(request: Request) -> Clock:
    """Request에서 clock 가져오기"""
    return request.app.state.clock


async def get_mode_service(
    session: AsyncSession = Depends(get_async_session),
    clock: Clock = Depends(get_clock),
) -> ModeService:
    """ModeService DI factory"""
    return ModeService(session, clock)


@router.post(
    "/{serial_number}/mode",
    response_model=ModeChangeResponse,
    summary="모드 변경 요청",
    description="특정 센서의 모드 변경을 요청합니다.",
)
async def request_mode_change(
    serial_number: str,
    request: ModeChangeRequest,
    service: ModeService = Depends(get_mode_service),
):
    """모드 변경 요청 API
    
    - 센서가 알려진 센서이면 sensor_known: true
    - 센서를 처음 보는 경우에도 sensor_known: false로 요청은 저장됨
    - 실제 적용 여부는 센서가 보낸 텔레메트리의 mode 필드를 통해 확인
    """
    try:
        # Mode Enum 변환
        mode = Mode(request.mode)
        
        # 모드 변경 요청 처리
        result = await service.request_mode_change(serial_number, mode)
        
        return ModeChangeResponse(
            success=result.success,
            sensor_known=result.sensor_known,
            requested_mode=result.requested_mode,
            requested_at=result.requested_at,
            message=result.message,
        )
    except ValueError as e:
        # 유효하지 않은 모드 값
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
