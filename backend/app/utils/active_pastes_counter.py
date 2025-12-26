"""
Active pastes counter with periodic DB refresh for accuracy.

Initializes the active_pastes gauge from the database and periodically
refreshes it to ensure accuracy across restarts and in multi-instance deployments.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.utils.metrics import active_pastes
import contextlib

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60


class ActivePastesCounter:
    """
    Manages the active_pastes gauge with periodic DB refresh.

    Periodically queries the database to ensure the gauge value is accurate,
    which is especially important in multi-instance deployments.
    """

    def __init__(self, session_factory: sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._refresh_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize the counter from the database."""
        count = await self._get_count_from_db()
        active_pastes.set(count)
        logger.info("Initialized active_pastes gauge to %d", count)

    def start_refresh_task(self) -> None:
        """Start the periodic refresh task."""
        if self._refresh_task is None:
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            logger.info("Started active_pastes refresh task (interval: %ds)", REFRESH_INTERVAL_SECONDS)

    async def stop_refresh_task(self) -> None:
        """Stop the periodic refresh task."""
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._refresh_task
            self._refresh_task = None
            logger.info("Stopped active_pastes refresh task")

    async def _refresh_loop(self) -> None:
        """Periodically refresh the gauge from the database."""
        while True:
            try:
                await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
                count = await self._get_count_from_db()
                active_pastes.set(count)
                logger.debug("Refreshed active_pastes to %d", count)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in active_pastes refresh loop: %s", exc)
                await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

    async def _get_count_from_db(self) -> int:
        """Get the current count of active pastes from the database."""
        from sqlalchemy import func, or_, select

        from app.db.models import PasteEntity

        try:
            async with self._session_factory() as session:
                stmt = (
                    select(func.count())
                    .select_from(PasteEntity)
                    .where(
                        or_(
                            PasteEntity.expires_at > datetime.now(tz=UTC),
                            PasteEntity.expires_at.is_(None),
                        ),
                        PasteEntity.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                return result.scalar() or 0
        except Exception as exc:
            logger.error("Failed to get active paste count from DB: %s", exc)
            return 0

    def inc(self, amount: int = 1) -> None:
        """Increment the active pastes counter."""
        active_pastes.inc(amount)

    def dec(self, amount: int = 1) -> None:
        """Decrement the active pastes counter."""
        active_pastes.dec(amount)


# Global instance - will be initialized during app startup
_counter: ActivePastesCounter | None = None


def get_active_pastes_counter() -> ActivePastesCounter | None:
    """Get the global ActivePastesCounter instance."""
    return _counter


def set_active_pastes_counter(counter: ActivePastesCounter) -> None:
    """Set the global ActivePastesCounter instance."""
    global _counter
    _counter = counter
