from fastapi import APIRouter

pastes_route = APIRouter(
    prefix="/pastes",
)


@pastes_route.post("")
async def create_paste(

):
    pass
