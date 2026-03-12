from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from src.api import readings_router, sensors_router
from src.config.settings import Settings, get_settings
from src.domain.clock import Clock, SystemClock


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

    app = FastAPI(title=resolved_settings.app_name, debug=resolved_settings.debug)
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
