from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import Settings


def create_async_engine_from_settings(settings: Settings) -> AsyncEngine:
    """Async 엔진 생성"""
    url = settings.effective_database_url
    # psycopg2에서 psycopg로 변경
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")
    return create_async_engine(url, pool_pre_ping=True, future=True)


def create_async_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Async 세션 팩토리 생성"""
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession
    )


def build_async_session_factory(settings: Settings) -> async_sessionmaker | None:
    """Async 세션 팩토리 빌드"""
    try:
        engine = create_async_engine_from_settings(settings)
        return create_async_session_factory(engine)
    except Exception:
        # DB 연결 실패 시 None 반환 (테스트 환경 등)
        return None


async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """AsyncSession 의존성 주입"""
    session_factory: Any = request.app.state.async_session_factory
    if session_factory is None:
        raise RuntimeError("Database session factory not initialized")
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
