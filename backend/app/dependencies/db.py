from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.containers import Container


@asynccontextmanager
async def _session_scope(factory: sessionmaker) -> AsyncIterator[AsyncSession]:
    session: AsyncSession = factory()
    try:
        yield session
    finally:
        await session.close()


@inject
async def get_session(
    factory: sessionmaker = Provide[Container.session_factory],
) -> AsyncIterator[AsyncSession]:
    async with _session_scope(factory) as session:
        yield session
