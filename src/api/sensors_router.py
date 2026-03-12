from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from src.config.database import get_db_session
from src.repositories.sensor_status_repository import SensorStatusRepository
from src.schemas.sensor_schemas import SensorStatusResponse, SensorStatusData


router = APIRouter(prefix="/api/v1/sensors", tags=["sensors"])


@router.get(
    "/status",
    response_model=SensorStatusResponse,
    summary="센서 상태 조회",
    description="센서별 현재 상태를 조회합니다.",
)
async def get_sensor_status(
    serial_number: str | None = Query(None, description="특정 센서 조회"),
    health_status: str | None = Query(None, description="건강 상태 필터"),
    session: Session = Depends(get_db_session),
) -> SensorStatusResponse:
    """센서 상태 조회 API"""
    repo = SensorStatusRepository(session)
    
    if serial_number:
        # 특정 센서 조회
        status = repo.get_by_serial_number(serial_number)
        if status is None:
            return SensorStatusResponse(success=True, data=[])
        
        data = [
            SensorStatusData(
                serial_number=status.serial_number,
                last_sensor_timestamp=status.last_sensor_timestamp,
                last_server_received_at=status.last_server_received_at,
                last_reported_mode=status.last_reported_mode,
                health_status=status.health_status,
                telemetry_status=status.telemetry_status,
                health_evaluated_at=status.health_evaluated_at,
                last_reading_id=status.last_reading_id,
            )
        ]
    else:
        # 전체 또는 필터링된 조회
        statuses = repo.get_all()
        
        if health_status:
            statuses = [s for s in statuses if s.health_status == health_status]
        
        data = [
            SensorStatusData(
                serial_number=s.serial_number,
                last_sensor_timestamp=s.last_sensor_timestamp,
                last_server_received_at=s.last_server_received_at,
                last_reported_mode=s.last_reported_mode,
                health_status=s.health_status,
                telemetry_status=s.telemetry_status,
                health_evaluated_at=s.health_evaluated_at,
                last_reading_id=s.last_reading_id,
            )
            for s in statuses
        ]
    
    return SensorStatusResponse(success=True, data=data)


@router.post(
    "/{serial_number}/mode",
    summary="모드 변경 요청",
    description="특정 센서의 모드 변경을 요청합니다.",
)
async def request_mode_change(
    serial_number: str,
    request: dict,  # Phase 5에서 구현
    session: Session = Depends(get_db_session),
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
