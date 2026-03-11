from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import Settings


def create_engine_from_settings(settings: Settings) -> Engine:
    return create_engine(settings.effective_database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def build_session_factory(settings: Settings) -> sessionmaker:
    engine = create_engine_from_settings(settings)
    return create_session_factory(engine)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory: Any = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
