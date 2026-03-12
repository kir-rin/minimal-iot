"""모드 변경 요청 레포지토리"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.mode_request import ModeChangeRequest


class ModeRequestRepository:
    """모드 변경 요청 레포지토리 (Async)"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        serial_number: str,
        requested_mode: str,
        requested_at: datetime,
    ) -> ModeChangeRequest:
        """모드 변경 요청 생성"""
        request = ModeChangeRequest(
            serial_number=serial_number,
            requested_mode=requested_mode,
            requested_at=requested_at,
        )
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> Optional[ModeChangeRequest]:
        """ID로 모드 변경 요청 조회"""
        result = await self._session.execute(
            select(ModeChangeRequest)
            .where(ModeChangeRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_serial_number(
        self,
        serial_number: str,
    ) -> list[ModeChangeRequest]:
        """특정 센서의 모든 모드 변경 요청 조회"""
        result = await self._session.execute(
            select(ModeChangeRequest)
            .where(ModeChangeRequest.serial_number == serial_number)
            .order_by(desc(ModeChangeRequest.requested_at))
        )
        return list(result.scalars().all())
