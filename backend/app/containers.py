from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_config


@asynccontextmanager
async def _engine_resource(db_url: str, echo: bool = False) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(db_url, echo=echo, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@asynccontextmanager
async def _session_resource(factory: sessionmaker) -> AsyncIterator[AsyncSession]:
    session: AsyncSession = factory()
    try:
        yield session
    finally:
        await session.close()


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=[
        "app.api.routes",
        "app.api.subroutes.pastes",
        "app.services",
        "app.dependencies.db",
    ])

    config = providers.Callable(get_config)

    # Database engine (async) as a managed resource
    engine = providers.Resource(
        _engine_resource,
        db_url=config().DATABASE_URL,
        echo=config().SQLALCHEMY_ECHO,
    )

    # SQLAlchemy session factory
    session_factory = providers.Factory(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Services
    from app.services.paste_service import PasteService
    from app.services.health_service import HealthService  # local import to avoid cycles during tooling
    health_service = providers.Factory(HealthService, session_factory)

    paste_service = providers.Factory(
        PasteService,
        session_factory,
        config().BASE_FOLDER_PATH
    )
