from __future__ import annotations

import logging

from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from starlette.responses import Response


class HealthService:
    def __init__(self, session: sessionmaker):
        self.session_maker = session

    async def check(self) -> Response:
        status = "ok"
        # Try a lightweight DB roundtrip
        try:
            async with self.session_maker() as session:
                await session.execute(text("SELECT 1"))
                db_status = "ok"
        except Exception as exc:  # pragma: no cover - minimal bootstrap
            logging.exception(exc)
            db_status = f"error: {exc.__class__.__name__}"
            status = "error"

        return ORJSONResponse({"status": status, "dependencies": {"database": db_status}},
                              status_code=200 if status == "ok" else 503, )
