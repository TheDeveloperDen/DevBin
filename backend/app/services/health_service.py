from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from starlette.responses import Response

if TYPE_CHECKING:
    from app.storage.storage_client import StorageClient

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(
        self,
        session: sessionmaker,
        storage_client: StorageClient | None = None,
        cache_client=None,
    ):
        self.session_maker = session
        self.storage_client = storage_client
        self.cache_client = cache_client

    async def check(self) -> Response:
        """Comprehensive health check for all system dependencies."""
        status = "healthy"
        dependencies = {}

        # Database check
        try:
            async with self.session_maker() as session:
                await session.execute(text("SELECT 1"))
                dependencies["database"] = "ok"
        except Exception as exc:  # pragma: no cover
            logger.exception("Database health check failed")
            dependencies["database"] = f"error: {exc.__class__.__name__}"
            status = "unhealthy"

        # Storage check
        if self.storage_client:
            try:
                # Simple connectivity check - try to list keys with empty prefix
                await self.storage_client.list_keys(prefix="__health__")
                dependencies["storage"] = "ok"
            except Exception as exc:  # pragma: no cover
                logger.exception("Storage health check failed")
                dependencies["storage"] = f"error: {exc.__class__.__name__}"
                status = "degraded" if status == "healthy" else status

        # Cache check
        if self.cache_client:
            try:
                # Try a simple cache operation
                test_key = "__health_check__"
                await self.cache_client.set(test_key, "ok", ttl=1)
                result = await self.cache_client.get(test_key)
                if result == "ok":
                    dependencies["cache"] = "ok"
                else:
                    dependencies["cache"] = "degraded"
                    status = "degraded" if status == "healthy" else status
            except Exception as exc:  # pragma: no cover
                logger.exception("Cache health check failed")
                dependencies["cache"] = f"error: {exc.__class__.__name__}"
                status = "degraded" if status == "healthy" else status

        status_code = 200 if status == "healthy" else (503 if status == "unhealthy" else 200)

        return ORJSONResponse(
            {"status": status, "dependencies": dependencies},
            status_code=status_code,
        )

    async def ready(self) -> Response:
        """Readiness check for load balancers - only checks critical dependencies."""
        # Database is the only critical dependency for readiness
        try:
            async with self.session_maker() as session:
                await session.execute(text("SELECT 1"))
            return ORJSONResponse({"ready": True}, status_code=200)
        except Exception as exc:  # pragma: no cover
            logger.exception("Readiness check failed")
            return ORJSONResponse(
                {"ready": False, "reason": exc.__class__.__name__},
                status_code=503,
            )
