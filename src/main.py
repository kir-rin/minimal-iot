from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import readings_router, sensors_router
from src.config.settings import Settings, get_settings
from src.domain.clock import Clock, SystemClock
from src.schedulers.scheduler_runner import SchedulerRunner

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    clock: Clock | None = None,
    async_session_factory: Any | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_clock = clock or SystemClock()
    resolved_session_factory = async_session_factory
    if resolved_session_factory is None:
        try:
            from src.config.database import build_async_session_factory
        except ModuleNotFoundError:
            resolved_session_factory = None
        else:
            resolved_session_factory = build_async_session_factory(resolved_settings)
            if resolved_session_factory is None:
                # DB 연결 실패 시 None
                pass

    # Lifespan context manager for graceful shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        scheduler_runner: SchedulerRunner | None = None
        
        if resolved_session_factory is not None and resolved_settings.scheduler.enabled:
            try:
                scheduler_runner = SchedulerRunner(
                    session_factory=resolved_session_factory,
                    clock=resolved_clock,
                    settings=resolved_settings.scheduler,
                )
                await scheduler_runner.start()
                logger.info(
                    "scheduler_initialized",
                    extra={
                        "interval_seconds": resolved_settings.scheduler.health_evaluation_interval_seconds,
                    },
                )
            except Exception as e:
                logger.error(
                    "failed_to_start_scheduler",
                    extra={"error": str(e)},
                    exc_info=True,
                )
        
        yield
        
        # Shutdown
        if scheduler_runner is not None:
            try:
                await scheduler_runner.stop(timeout=30.0)
            except Exception as e:
                logger.error(
                    "failed_to_stop_scheduler_gracefully",
                    extra={"error": str(e)},
                    exc_info=True,
                )

    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.state.settings = resolved_settings
    app.state.clock = resolved_clock
    app.state.async_session_factory = resolved_session_factory

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        now = app.state.clock.now().isoformat()
        return {
            "status": "ok",
            "environment": app.state.settings.app_env,
            "now": now,
        }

    # 라우터 등록
    app.include_router(readings_router)
    app.include_router(sensors_router)

    return app


app = create_app()
