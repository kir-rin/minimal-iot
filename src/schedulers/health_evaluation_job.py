"""Health Evaluation Job - 센서 건강 상태 재평가 스케줄러"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.clock import Clock
from src.domain.status import evaluate_health_status, StatusThresholds
from src.domain.types import HealthStatus, Mode
from src.repositories.sensor_status_repository import SensorStatusRepository


class HealthEvaluationJob:
    """센서 건강 상태 재평가 작업"""
    
    def __init__(self, session: AsyncSession, clock: Clock):
        """
        Args:
            session: 데이터베이스 세션
            clock: 시간 주입 인터페이스
        """
        self._session = session
        self._clock = clock
        self._status_repo = SensorStatusRepository(session)
    
    async def evaluate_all_sensors(self) -> dict:
        """모든 센서의 건강 상태를 재평가
        
        Returns:
            dict: {
                "evaluated_count": 평가된 센서 수,
                "transitioned_to_faulty": FAULTY로 전환된 센서 수,
                "already_faulty": 이미 FAULTY였던 센서 수,
            }
        """
        current_time = self._clock.now()
        thresholds = StatusThresholds()
        
        # 모든 센서 상태 조회
        all_statuses = await self._status_repo.get_all()
        
        evaluated_count = 0
        transitioned_to_faulty = 0
        already_faulty = 0
        
        for status in all_statuses:
            evaluated_count += 1
            
            # 이미 FAULTY인지 확인
            if status.health_status == HealthStatus.FAULTY.value:
                already_faulty += 1
            
            # 새로운 건강 상태 평가
            new_health_status = evaluate_health_status(
                last_mode=status.last_reported_mode,
                last_server_received_at=status.last_server_received_at,
                now=current_time,
                thresholds=thresholds,
            )
            
            # 상태 변경이 필요한 경우
            if new_health_status.value != status.health_status:
                if new_health_status == HealthStatus.FAULTY:
                    transitioned_to_faulty += 1
                
                # 상태 업데이트
                status.health_status = new_health_status.value
                status.health_evaluated_at = current_time
        
        # 변경사항 커밋
        await self._session.commit()
        
        return {
            "evaluated_count": evaluated_count,
            "transitioned_to_faulty": transitioned_to_faulty,
            "already_faulty": already_faulty,
        }
    
    async def evaluate_single_sensor(self, serial_number: str) -> HealthStatus | None:
        """단일 센서 건강 상태 재평가
        
        Args:
            serial_number: 센서 시리얼 번호
            
        Returns:
            새로운 건강 상태 또는 None (센서 없음)
        """
        current_time = self._clock.now()
        thresholds = StatusThresholds()
        
        # 센서 상태 조회
        status = await self._status_repo.get_by_serial_number(serial_number)
        if status is None:
            return None
        
        # 새로운 건강 상태 평가
        new_health_status = evaluate_health_status(
            last_mode=status.last_reported_mode,
            last_server_received_at=status.last_server_received_at,
            now=current_time,
            thresholds=thresholds,
        )
        
        # 상태 변경이 필요한 경우
        if new_health_status.value != status.health_status:
            status.health_status = new_health_status.value
            status.health_evaluated_at = current_time
            await self._session.commit()
        
        return new_health_status
