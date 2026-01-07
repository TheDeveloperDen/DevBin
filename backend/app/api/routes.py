from __future__ import annotations

import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request
from starlette.responses import Response

from app.api.subroutes.pastes import pastes_route
from app.config import config
from app.containers import Container
from app.exceptions import UnauthorizedError
from app.ratelimit import create_limit_resolver, limiter
from app.services.health_service import HealthService

router = APIRouter()

logger = logging.getLogger(__name__)


# Metrics authentication
metrics_security = HTTPBearer(auto_error=False, description="Metrics access token")


def verify_metrics_token(credentials: HTTPAuthorizationCredentials | None = Depends(metrics_security)) -> None:
    """
    Verify Bearer token for metrics endpoint.

    If METRICS_TOKEN is not configured, endpoint is publicly accessible.
    If configured, valid Bearer token is required.

    Raises:
        UnauthorizedError: If token is missing or invalid when authentication is required
    """
    # If no token configured, allow public access
    if not config.METRICS_TOKEN and config.ENVIRONMENT != "prod":
        return
    elif not config.METRICS_TOKEN:
        logger.warning("No METRICS_TOKEN configured and ENVIRONMENT is prod")
        raise UnauthorizedError("Invalid metrics token")

    # Token is configured, authentication required
    if not credentials:
        raise UnauthorizedError("Bearer token required for metrics access")

    # Validate token (plain string comparison)
    if credentials.credentials != config.METRICS_TOKEN:
        raise UnauthorizedError("Invalid metrics token")


@router.get("/health")
@limiter.limit(create_limit_resolver(config, "health"))
@inject
async def health(
    request: Request,
    health_service: HealthService = Depends(Provide[Container.health_service]),
):
    return await health_service.check()


@router.get("/ready")
@limiter.limit(create_limit_resolver(config, "health"))
@inject
async def ready(
    request: Request,
    health_service: HealthService = Depends(Provide[Container.health_service]),
):
    """Readiness endpoint for load balancers."""
    return await health_service.ready()


@router.get("/metrics")
async def metrics(_: None = Depends(verify_metrics_token)):
    """
    Prometheus metrics endpoint.

    Requires Bearer token authentication if APP_METRICS_TOKEN is configured.
    """
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


router.include_router(pastes_route)
