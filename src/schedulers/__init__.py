"""Scheduler package - 센서 상태 재평가 스케줄러

APScheduler 기반으로 주기적으로 센서 건강 상태를 재평가합니다.

Usage:
    # FastAPI 앱 시작 시 자동으로 스케줄러 시작
    app = create_app()
    
    # 수동으로 스케줄러 실행 (테스트용)
    from src.schedulers.scheduler_runner import ManualSchedulerRunner
    runner = ManualSchedulerRunner(session_factory, clock)
    await runner.start()
    await runner.stop()
"""

from src.schedulers.health_evaluation_job import HealthEvaluationJob
from src.schedulers.scheduler_runner import ManualSchedulerRunner, SchedulerRunner

__all__ = [
    "HealthEvaluationJob",
    "SchedulerRunner",
    "ManualSchedulerRunner",
]
