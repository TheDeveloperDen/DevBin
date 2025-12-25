from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.middlewares import (
    HTTPSRedirectMiddleware,
    SecurityHeadersMiddleware,
    UserMetadataMiddleware,
)
from app.config import config
from app.containers import Container
from app.exceptions import (
    ContentTooLargeError,
    DevBinException,
    InvalidTokenError,
    PasteExpiredError,
    PasteNotFoundError,
    StorageError,
    StorageQuotaExceededError,
    UnauthorizedError,
)
from app.ratelimit import limiter
from app.services.cleanup_service import CleanupService
from app.utils.logging import configure_logging

# Configure logging at module level
configure_logging(level=config.LOG_LEVEL, log_format=config.LOG_FORMAT)


# Set the custom encoder
def _build_container() -> Container:
    container = Container()
    return container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = _build_container()
    app.container = container

    # Initialize resources (e.g., DB engine) and wire dependencies
    await container.init_resources()
    container.wire()

    # Set cache for pastes route
    from app.api.subroutes.pastes import set_cache
    cache_instance = container.cache_client()
    set_cache(cache_instance)

    cleanup_service: CleanupService = (
        await container.cleanup_service()
    )  # or however you resolve it
    cleanup_service.start_cleanup_worker()
    try:
        yield
    finally:
        await cleanup_service.stop_cleanup_worker()
        await container.shutdown_resources()


def apply_rate_limiter(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def create_app() -> FastAPI:
    from app.api.routes import router

    app = FastAPI(
        title="DevBins API",
        version="0.1.0-alpha",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    apply_rate_limiter(app)

    # Register custom exception handlers
    logger = logging.getLogger(__name__)

    @app.exception_handler(PasteNotFoundError)
    async def paste_not_found_handler(request: Request, exc: PasteNotFoundError):
        logger.warning("Paste not found: %s", exc.paste_id)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(PasteExpiredError)
    async def paste_expired_handler(request: Request, exc: PasteExpiredError):
        logger.warning("Paste expired: %s", exc.paste_id)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError):
        logger.warning("Invalid token for %s", exc.operation)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        logger.warning("Unauthorized access attempt to %s", request.url.path)
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
            headers={"WWW-Authenticate": exc.www_authenticate}
        )

    @app.exception_handler(StorageQuotaExceededError)
    async def storage_quota_handler(request: Request, exc: StorageQuotaExceededError):
        logger.error("Storage quota exceeded: required=%.2fMB, available=%.2fMB", exc.required_mb, exc.available_mb)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(ContentTooLargeError)
    async def content_too_large_handler(request: Request, exc: ContentTooLargeError):
        logger.warning("Content too large: size=%d, max=%d", exc.content_size, exc.max_size)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError):
        logger.error("Storage error during %s: %s", exc.operation, exc.message)
        return ORJSONResponse(status_code=exc.status_code, content={"error": "Internal server error"})

    @app.exception_handler(DevBinException)
    async def devbin_exception_handler(request: Request, exc: DevBinException):
        logger.error("DevBin error: %s", exc.message)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    # Add HTTPS redirect middleware (if enabled)
    if config.ENFORCE_HTTPS:
        app.add_middleware(HTTPSRedirectMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_DOMAINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add user metadata middleware
    app.add_middleware(UserMetadataMiddleware)

    app.include_router(router)
    return app


# Expose ASGI app
app = create_app()


def main():
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=int(config.PORT),
        reload=config.RELOAD,
        server_header=False,
        workers=os.cpu_count() or 1 if config.WORKERS is True else config.WORKERS,
        log_level=None if config.DEBUG else "info",
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
