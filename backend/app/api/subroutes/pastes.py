import logging
from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Security
from fastapi.security import APIKeyHeader
from pydantic import UUID4
from starlette.requests import Request
from starlette.responses import Response

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
)
@limiter.limit(create_limit_resolver(config, "get_paste_legacy"), key_func=get_exempt_key)
@inject
async def get_paste(
    request: Request,
    paste_id: str,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    cached_result = await cache.get(paste_id)
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
        return Response(
            ErrorResponse(
                error="legacy_paste_not_found",
                message=f"Paste {paste_id} not found",
            ).model_dump_json(),
            status_code=404,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, immutable",
            },
        )
    paste_result = paste_result.model_dump_json()

    await cache.set(paste_id, paste_result, ttl=config.CACHE_TTL)
    cache_operations.labels(operation="set", result="success").inc()

    return Response(
        paste_result,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={config.CACHE_TTL}",
        },
    )


@pastes_route.get(
    "/{paste_id}",
    responses={404: {"model": ErrorResponse}, 200: {"model": PasteResponse}},
)
@limiter.limit(create_limit_resolver(config, "get_paste"), key_func=get_exempt_key)
@inject
async def get_paste(
    request: Request,
    paste_id: UUID4,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    cached_result = await cache.get(paste_id)
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
        return Response(
            ErrorResponse(
                error="paste_not_found",
                message=f"Paste {paste_id} not found",
            ).model_dump_json(),
            status_code=404,
            headers={
                "Content-Type": "application/json",
            },
        )
    paste_result = paste_result.model_dump_json()

    await cache.set(paste_id, paste_result, ttl=config.CACHE_TTL)
    cache_operations.labels(operation="set", result="success").inc()

    return Response(
        paste_result,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={config.CACHE_TTL}",
        },
    )


@pastes_route.post("", response_model=CreatePasteResponse)
@limiter.limit(create_limit_resolver(config, "create_paste"), key_func=get_exempt_key)
@inject
async def create_paste(
    request: Request,
    create_paste_body: CreatePaste,
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    return await paste_service.create_paste(create_paste_body, request.state.user_metadata)


@pastes_route.put("/{paste_id}")
@limiter.limit(create_limit_resolver(config, "edit_paste"), key_func=get_exempt_key)
@inject
async def edit_paste(
    request: Request,
    paste_id: UUID4,
    edit_paste_body: EditPaste,
    edit_token: str = Security(edit_token_key_header),
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    result = await paste_service.edit_paste(paste_id, edit_paste_body, edit_token)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="paste_not_found",
                message=f"Paste {paste_id} not found",
            ).model_dump(),
        )
    # Invalidate cache after successful edit
    await cache.delete(paste_id)
    cache_operations.labels(operation="delete", result="success").inc()
    return result


@pastes_route.delete("/{paste_id}")
@limiter.limit(create_limit_resolver(config, "delete_paste"), key_func=get_exempt_key)
@inject
async def delete_paste(
    request: Request,
    paste_id: UUID4,
    delete_token: str = Security(delete_token_key_header),
    paste_service: PasteService = Depends(Provide[Container.paste_service]),
):
    result = await paste_service.delete_paste(paste_id, delete_token)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="paste_not_found",
                message=f"Paste {paste_id} not found",
            ).model_dump(),
        )
    # Invalidate cache after successful delete
    await cache.delete(paste_id)
    cache_operations.labels(operation="delete", result="success").inc()
    return {"message": "Paste deleted successfully"}
