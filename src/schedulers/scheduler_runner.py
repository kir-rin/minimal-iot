"""Scheduler Runner - APScheduler 기반 스케줄러 실행 관리

Health evaluation job을 주기적으로 실행하는 스케줄러입니다.
Production 환경에서는 APScheduler를 사용하고,
Test 환경에서는 직접 실행할 수 있습니다.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import SchedulerSettings
from src.domain.clock import Clock
from src.schedulers.health_evaluation_job import HealthEvaluationJob

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """APScheduler 기반 스케줄러 실행기
    
    10초 주기(설정 가능)로 health_evaluation_job을 실행합니다.
    Graceful shutdown을 지원하며, 실행 중인 job이 완료될 때까지 기다립니다.
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
        settings: SchedulerSettings | None = None,
    ):
        """
        Args:
            session_factory: 비동기 DB 세션 팩토리
            clock: 시간 주입 인터페이스
            settings: 스케줄러 설정 (None이면 기본값 사용)
        """
        self._session_factory = session_factory
        self._clock = clock
        self._settings = settings or SchedulerSettings()
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running = False
    
    async def start(self) -> None:
        """스케줄러 시작
        
        설정이 비활성화된 경우 로그만 남기고 종료합니다.
        """
        if not self._settings.enabled:
            logger.info("scheduler_disabled_by_configuration")
            return
        
        if self._is_running:
            logger.warning("scheduler_already_running")
            return
        
        self._scheduler = AsyncIOScheduler()
        
        # Health evaluation job 등록
        trigger = IntervalTrigger(
            seconds=self._settings.health_evaluation_interval_seconds,
        )
        
        self._scheduler.add_job(
            self._run_health_evaluation,
            trigger=trigger,
            id="health_evaluation_job",
            name="Health Evaluation Job",
            replace_existing=True,
            max_instances=1,  # 동시 실행 방지
        )
        
        self._scheduler.start()
        self._is_running = True
        
        logger.info(
            "scheduler_started",
            extra={
                "interval_seconds": self._settings.health_evaluation_interval_seconds,
                "job_id": "health_evaluation_job",
            },
        )
    
    async def stop(self, timeout: float | None = None) -> None:
        """스케줄러 중지 (Graceful shutdown)
        
        실행 중인 job이 완료될 때까지 기다립니다.
        
        Args:
            timeout: 최대 대기 시간 (초), None이면 무제한 대기
        """
        if not self._is_running or self._scheduler is None:
            logger.info("scheduler_not_running")
            return
        
        logger.info("stopping_scheduler")
        
        # 실행 중인 job 중지 및 대기
        self._scheduler.shutdown(wait=True, timeout=timeout)
        self._is_running = False
        
        logger.info("scheduler_stopped_gracefully")
    
    async def _run_health_evaluation(self) -> dict[str, Any]:
        """Health evaluation job 실행
        
        예외가 발생해도 스케줄러는 계속 실행됩니다.
        
        Returns:
            job 실행 결과
        """
        async with self._session_factory() as session:
            job = HealthEvaluationJob(session, self._clock)
            
            try:
                result = await job.evaluate_all_sensors()
                logger.debug(
                    "health_evaluation_job_completed",
                    extra={
                        "evaluated_count": result.get("evaluated_count", 0),
                        "transitioned_to_faulty": result.get("transitioned_to_faulty", 0),
                        "failed_count": result.get("failed_count", 0),
                    },
                )
                return result
            except Exception as e:
                logger.error(
                    "health_evaluation_job_failed",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # 예외를 다시 발생시키지 않음 - 스케줄러는 계속 실행되어야 함
                return {
                    "evaluated_count": 0,
                    "transitioned_to_faulty": 0,
                    "already_faulty": 0,
                    "failed_count": 0,
                    "error": str(e),
                }
    
    @property
    def is_running(self) -> bool:
        """스케줄러 실행 중 여부"""
        return self._is_running


class ManualSchedulerRunner:
    """수동 실행용 스케줄러 (테스트/디버깅용)
    
    APScheduler 없이 직접 asyncio로 job을 실행합니다.
    테스트 환경에서 사용하기 좋습니다.
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
        interval_seconds: int = 10,
    ):
        self._session_factory = session_factory
        self._clock = clock
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
    
    async def start(self) -> None:
        """스케줄러 시작"""
        if self._task is not None:
            logger.warning("manual_scheduler_already_running")
            return
        
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info(
            "manual_scheduler_started",
            extra={"interval_seconds": self._interval_seconds},
        )
    
    async def stop(self, timeout: float | None = None) -> None:
        """스케줄러 중지"""
        if self._task is None:
            logger.info("manual_scheduler_not_running")
            return
        
        logger.info("stopping_manual_scheduler")
        self._stop_event.set()
        
        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("manual_scheduler_stop_timeout")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self._task = None
        logger.info("manual_scheduler_stopped")
    
    async def _run_loop(self) -> None:
        """메인 실행 루프"""
        while not self._stop_event.is_set():
            try:
                async with self._session_factory() as session:
                    job = HealthEvaluationJob(session, self._clock)
                    await job.evaluate_all_sensors()
            except Exception as e:
                logger.error(
                    "manual_scheduler_job_failed",
                    extra={"error": str(e)},
                    exc_info=True,
                )
            
            # interval_seconds 동안 대기 (stop_event로 중단 가능)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except asyncio.TimeoutError:
                pass  # 정상적인 interval 완료
    
    @property
    def is_running(self) -> bool:
        """스케줄러 실행 중 여부"""
        return self._task is not None and not self._task.done()
