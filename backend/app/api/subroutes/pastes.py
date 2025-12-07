from fastapi import APIRouter

app = APIRouter(
    prefix="/pastes",
)

@app.post("")
async def create_paste(

):
