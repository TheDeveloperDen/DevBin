from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from app.api.dto.paste_dto import CreatePaste
from app.containers import Container
from app.ratelimit import limiter
from app.services.paste_service import PasteService

pastes_route = APIRouter(
    prefix="/pastes",
    tags=["Paste"]
)


@pastes_route.get("/{paste_id}")
@limiter.limit("10/minute")
@inject
async def get_paste(request: Request, paste_id: str,
                    paste_service: PasteService = Depends(Provide[Container.paste_service])):
    return Response(
        await paste_service.get_paste_by_id(paste_id),
        headers={
            "Cache-Control": "public, max-age=3600",
        }
    )


@pastes_route.post("")
@limiter.limit("4/minute")
@inject
async def create_paste(request: Request,
                       create_paste_body: CreatePaste,
                       paste_service: PasteService = Depends(Provide[Container.paste_service])):
    return await paste_service.create_paste(create_paste_body, request.state.user_metadata)
