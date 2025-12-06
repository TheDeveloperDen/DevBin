from __future__ import annotations

from fastapi import APIRouter, Depends
from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession

from app.containers import Container
from app.dependencies.db import get_session
from app.services.health_service import HealthService


router = APIRouter()


@router.get("/health")
@inject
async def health(
    health_service: HealthService = Depends(Provide[Container.health_service]),
    session: AsyncSession = Depends(get_session),
):
    return await health_service.check(session)
