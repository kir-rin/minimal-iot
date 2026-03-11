from __future__ import annotations

from fastapi import FastAPI

from sqlalchemy.orm import sessionmaker

from src.config.database import build_session_factory
from src.config.settings import Settings, get_settings
from src.domain.clock import Clock, SystemClock


def create_app(
    *,
    settings: Settings | None = None,
    clock: Clock | None = None,
    session_factory: sessionmaker | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_clock = clock or SystemClock()
    resolved_session_factory = session_factory or build_session_factory(resolved_settings)

    app = FastAPI(title=resolved_settings.app_name, debug=resolved_settings.debug)
    app.state.settings = resolved_settings
    app.state.clock = resolved_clock
    app.state.session_factory = resolved_session_factory

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        now = app.state.clock.now().isoformat()
        return {
            "status": "ok",
            "environment": app.state.settings.app_env,
            "now": now,
        }

    return app


app = create_app()
