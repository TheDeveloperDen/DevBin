from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.api.subroutes.pastes import pastes_route
from app.containers import Container
from app.ratelimit import limiter
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health")
@limiter.limit("60/minute")
@inject
async def health(
        request: Request,
        health_service: HealthService = Depends(Provide[Container.health_service]),
):
    return await health_service.check()


router.include_router(pastes_route)
