from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class HealthService:
    async def check(self, session: AsyncSession) -> Dict[str, Any]:
        # Try a lightweight DB roundtrip
        try:
            await session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:  # pragma: no cover - minimal bootstrap
            db_status = f"error: {exc.__class__.__name__}"

        return {"status": "ok", "dependencies": {"database": db_status}}
