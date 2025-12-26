import logging
from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.params import Security
from fastapi.security import APIKeyHeader
from pydantic import UUID4
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from app.api.dto.Error import ErrorResponse
from app.api.dto.paste_dto import (
    CreatePaste,
    CreatePasteResponse,
    EditPaste,
    LegacyPasteResponse,
    PasteResponse,
)
from app.config import config
from app.containers import Container
from app.exceptions import PasteNotFoundError
from app.ratelimit import create_limit_resolver, get_exempt_key, limiter
from app.services.paste_service import PasteService
from app.utils.LRUMemoryCache import LRUMemoryCache
from app.utils.metrics import cache_operations

if TYPE_CHECKING:
    from aiocache import RedisCache


logger = logging.getLogger(__name__)

pastes_route = APIRouter(prefix="/pastes", tags=["Paste"])

# Cache will be set during container initialization
cache: "RedisCache | LRUMemoryCache | None" = None


def set_cache(cache_instance: "RedisCache | LRUMemoryCache"):
    """Set the cache instance from the container."""
    global cache
    cache = cache_instance


edit_token_key_header = APIKeyHeader(name="Authorization", scheme_name="Edit Token")
delete_token_key_header = APIKeyHeader(name="Authorization", scheme_name="Delete Token")


@pastes_route.get(
    "/legacy/{paste_id}",
    responses={404: {"model": ErrorResponse}, 200: {"model": LegacyPasteResponse}},
    summary="Get legacy Hastebin-format paste",
    description="Retrieve a paste stored in legacy Hastebin format by its ID.",
)
@limiter.limit(create_limit_resolver(config, "get_paste_legacy"), key_func=get_exempt_key)
@inject
async def get_legacy_paste(
    request: Request,
    paste_id: str,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """Get a legacy Hastebin-format paste by ID."""
    cached_result = await cache.get(f"legacy:{paste_id}")
    if cached_result:
        cache_operations.labels(operation="get", result="hit").inc()
        return Response(
            cached_result,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": f"public, max-age={config.CACHE_TTL}",
            },
        )

    cache_operations.labels(operation="get", result="miss").inc()
    paste_result = await paste_service.get_legacy_paste_by_name(paste_id)
    if not paste_result:
        raise PasteNotFoundError(paste_id)

    paste_json = paste_result.model_dump_json()
    await cache.set(f"legacy:{paste_id}", paste_json, ttl=config.CACHE_TTL)
    cache_operations.labels(operation="set", result="success").inc()

    return Response(
        paste_json,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={config.CACHE_TTL}",
        },
    )


@pastes_route.get(
    "/{paste_id}",
    responses={404: {"model": ErrorResponse}, 200: {"model": PasteResponse}},
    summary="Get paste by UUID",
    description="Retrieve a paste by its UUID identifier.",
)
@limiter.limit(create_limit_resolver(config, "get_paste"), key_func=get_exempt_key)
@inject
async def get_paste_by_uuid(
    request: Request,
    paste_id: UUID4,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """Get a paste by its UUID."""
    cached_result = await cache.get(str(paste_id))
    if cached_result:
        cache_operations.labels(operation="get", result="hit").inc()
        return Response(
            cached_result,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": f"public, max-age={config.CACHE_TTL}",
            },
        )

    cache_operations.labels(operation="get", result="miss").inc()
    paste_result = await paste_service.get_paste_by_id(paste_id)
    if not paste_result:
        raise PasteNotFoundError(str(paste_id))

    paste_json = paste_result.model_dump_json()
    await cache.set(str(paste_id), paste_json, ttl=config.CACHE_TTL)
    cache_operations.labels(operation="set", result="success").inc()

    return Response(
        paste_json,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={config.CACHE_TTL}",
        },
    )


@pastes_route.get(
    "/{paste_id}/raw",
    response_class=PlainTextResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get raw paste content",
    description="Retrieve only the raw text content of a paste. Useful for curl/wget users.",
)
@limiter.limit(create_limit_resolver(config, "get_paste"), key_func=get_exempt_key)
@inject
async def get_paste_raw(
    request: Request,
    paste_id: UUID4,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """
    Get raw paste content as plain text.

    This endpoint returns only the paste content without any JSON wrapper,
    making it ideal for command-line tools like curl or wget.

    Example usage:
        curl https://api.devbin.dev/pastes/{paste_id}/raw
    """
    # Check cache for raw content
    cache_key = f"raw:{paste_id}"
    cached_content = await cache.get(cache_key)
    if cached_content:
        cache_operations.labels(operation="get", result="hit").inc()
        return PlainTextResponse(
            content=cached_content,
            headers={"Cache-Control": f"public, max-age={config.CACHE_TTL}"},
        )

    cache_operations.labels(operation="get", result="miss").inc()
    paste_result = await paste_service.get_paste_by_id(paste_id)
    if not paste_result:
        raise PasteNotFoundError(str(paste_id))

    content = paste_result.content or ""

    # Cache the raw content
    await cache.set(cache_key, content, ttl=config.CACHE_TTL)
    cache_operations.labels(operation="set", result="success").inc()

    return PlainTextResponse(
        content=content,
        headers={"Cache-Control": f"public, max-age={config.CACHE_TTL}"},
    )


@pastes_route.post(
    "",
    response_model=CreatePasteResponse,
    summary="Create a new paste",
    description="Create a new paste with the provided content and metadata.",
)
@limiter.limit(create_limit_resolver(config, "create_paste"), key_func=get_exempt_key)
@inject
async def create_paste(
    request: Request,
    create_paste_body: CreatePaste,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """Create a new paste and return edit/delete tokens."""
    return await paste_service.create_paste(create_paste_body, request.state.user_metadata)


@pastes_route.put(
    "/{paste_id}",
    response_model=PasteResponse,
    summary="Edit an existing paste",
    description="Update a paste's content or metadata. Requires a valid edit token.",
)
@limiter.limit(create_limit_resolver(config, "edit_paste"), key_func=get_exempt_key)
@inject
async def edit_paste(
    request: Request,
    paste_id: UUID4,
    edit_paste_body: EditPaste,
    edit_token: str = Security(edit_token_key_header),
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """Edit an existing paste. Requires the edit token returned during creation."""
    result = await paste_service.edit_paste(paste_id, edit_paste_body, edit_token)
    if not result:
        raise PasteNotFoundError(str(paste_id))

    # Invalidate all cache entries for this paste
    await _invalidate_paste_cache(paste_id)
    return result


@pastes_route.delete(
    "/{paste_id}",
    summary="Delete a paste",
    description="Permanently delete a paste. Requires a valid delete token.",
)
@limiter.limit(create_limit_resolver(config, "delete_paste"), key_func=get_exempt_key)
@inject
async def delete_paste(
    request: Request,
    paste_id: UUID4,
    delete_token: str = Security(delete_token_key_header),
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    """Delete a paste. Requires the delete token returned during creation."""
    result = await paste_service.delete_paste(paste_id, delete_token)
    if not result:
        raise PasteNotFoundError(str(paste_id))

    # Invalidate all cache entries for this paste
    await _invalidate_paste_cache(paste_id)
    return {"message": "Paste deleted successfully"}


async def _invalidate_paste_cache(paste_id: UUID4) -> None:
    """Invalidate all cache entries related to a paste."""
    cache_keys = [str(paste_id), f"raw:{paste_id}"]
    for key in cache_keys:
        try:
            await cache.delete(key)
            cache_operations.labels(operation="delete", result="success").inc()
        except Exception as exc:
            logger.warning("Failed to invalidate cache key %s: %s", key, exc)
