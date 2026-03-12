"""모드 변경 서비스"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.clock import Clock
from src.domain.types import Mode
from src.models.mode_request import ModeChangeRequest
from src.repositories.mode_request_repository import ModeRequestRepository
from src.repositories.sensor_status_repository import SensorStatusRepository


@dataclass
class ModeChangeResult:
    """모드 변경 요청 결과"""
    success: bool
    sensor_known: bool
    requested_mode: str
    requested_at: datetime
    request_status: str
    message: str


@dataclass
class ReconcileResult:
    """Reconcile 결과"""
    reconciled: bool
    request_id: Optional[int] = None
    message: str = ""


class ModeService:
    """모드 변경 서비스"""

    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        mode_request_repo: Optional[ModeRequestRepository] = None,
        sensor_status_repo: Optional[SensorStatusRepository] = None,
    ):
        self._session = session
        self._clock = clock
        self._mode_request_repo = mode_request_repo or ModeRequestRepository(session)
        self._sensor_status_repo = sensor_status_repo or SensorStatusRepository(session)

    async def request_mode_change(
        self,
        serial_number: str,
        mode: Mode,
    ) -> ModeChangeResult:
        """모드 변경 요청
        
        Args:
            serial_number: 센서 시리얼 번호
            mode: 변경할 모드
            
        Returns:
            ModeChangeResult: 요청 결과
        """
        # 센서가 알려진 센서인지 확인
        sensor_status = await self._sensor_status_repo.get_by_serial_number(serial_number)
        sensor_known = sensor_status is not None

        # 현재 시각
        now = self._clock.now()

        # 모드 변경 요청 저장
        request = await self._mode_request_repo.create(
            serial_number=serial_number,
            requested_mode=mode.value,
            requested_at=now,
        )

        return ModeChangeResult(
            success=True,
            sensor_known=sensor_known,
            requested_mode=mode.value,
            requested_at=request.requested_at,
            request_status=request.request_status,
            message="Mode change request created" if sensor_known else "Sensor not found, but request recorded",
        )

    async def reconcile_mode_change(
        self,
        serial_number: str,
        reported_mode: Mode,
        server_received_at: datetime,
    ) -> ReconcileResult:
        """텔레메트리 수신 시 모드 변경 reconcile
        
        Args:
            serial_number: 센서 시리얼 번호
            reported_mode: 센서가 보고한 모드
            server_received_at: 서버 수신 시각
            
        Returns:
            ReconcileResult: reconcile 결과
        """
        # 가장 최근 PENDING 요청 조회
        pending_request = await self._mode_request_repo.get_latest_pending_request(serial_number)

        if pending_request is None:
            return ReconcileResult(
                reconciled=False,
                message="No pending mode change request found",
            )

        # reconcile 조건 검사: server_received_at >= requested_at
        if server_received_at < pending_request.requested_at:
            return ReconcileResult(
                reconciled=False,
                request_id=pending_request.id,
                message="Telemetry received before request was made",
            )

        # 모드 일치 여부 확인
        if reported_mode.value != pending_request.requested_mode:
            return ReconcileResult(
                reconciled=False,
                request_id=pending_request.id,
                message=f"Mode mismatch: expected {pending_request.requested_mode}, got {reported_mode.value}",
            )

        # reconcile 성공: 요청을 APPLIED 상태로 변경
        await self._mode_request_repo.mark_as_applied(
            request=pending_request,
            observed_applied_at=server_received_at,
        )

        return ReconcileResult(
            reconciled=True,
            request_id=pending_request.id,
            message="Mode change request marked as applied",
        )

    async def validate_mode(self, mode_value: str) -> Mode:
        """모드 값 검증
        
        Args:
            mode_value: 검증할 모드 값 문자열
            
        Returns:
            Mode: 검증된 Mode Enum
            
        Raises:
            ValueError: 유효하지 않은 모드 값
        """
        try:
            return Mode(mode_value)
        except ValueError:
            valid_modes = [m.value for m in Mode]
            raise ValueError(f"Invalid mode: {mode_value}. Valid modes: {valid_modes}")
