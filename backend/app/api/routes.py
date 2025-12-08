from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from dependency_injector.wiring import Provide, inject

from app.api.subroutes.pastes import pastes_route
from app.containers import Container
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health")
@inject
async def health(
        health_service: HealthService = Depends(Provide[Container.health_service]),
) -> dict[str, Any]:
    return await health_service.check()


router.include_router(pastes_route)
