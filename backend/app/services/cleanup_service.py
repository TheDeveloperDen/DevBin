import asyncio
import contextlib
import logging
import time
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import config
from app.db.models import PasteEntity
from app.locks import DistributedLock
from app.utils.active_pastes_counter import get_active_pastes_counter
from app.utils.metrics import cleanup_duration


class CleanupService:
    def __init__(
        self,
        session_maker: sessionmaker[AsyncSession],
        paste_base_folder_path: str = "",
        lock: DistributedLock | None = None,
    ):
        self.session_maker: sessionmaker[AsyncSession] = session_maker
        self.paste_base_folder_path: str = paste_base_folder_path
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: asyncio.Task[Coroutine[None, None, None]] | None = None
        self._lock: DistributedLock = lock

    def start_cleanup_worker(self):
        """Start the background cleanup worker"""
        self.logger.info("Starting cleanup worker")
        if self._cleanup_task is not None:
            return  # Already running

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("Background cleanup worker started")

    async def stop_cleanup_worker(self):
        """Stop the background cleanup worker"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
            if self._lock:
                self._lock.release("cleanup")
            self.logger.info("Background cleanup worker stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop that runs every 5 minutes"""
        # Wait for 5 minutes and retry if lock not acquired
        while not self._lock or not self._lock.acquire("cleanup"):
            self.logger.debug("Cleanup lock not acquired, waiting...")
            await asyncio.sleep(300)

        while True:
            if self._lock:
                self._lock.touch("cleanup")
            try:
                self.logger.info("Cleaning up expired pastes")
                # Try to acquire lock (only one worker can run cleanup)
                await self._cleanup_expired_pastes()
                if config.KEEP_DELETED_PASTES_TIME_HOURS != -1:
                    if self._lock:
                        self._lock.touch("cleanup")
                    await self._cleanup_deleted_pastes()

                # Wait 5 minutes before next run
                await asyncio.sleep(600)
            except Exception as exc:
                self.logger.error("Error in cleanup loop: %s", exc)
                await asyncio.sleep(60)  # Retry after 1 minute on error

    async def _cleanup_expired_pastes(self):
        """Remove expired pastes and their files"""
        from app.api.subroutes.pastes import cache

        start_time = time.monotonic()
        try:
            BATCH_SIZE = 100
            total_cleaned = 0
            error: bool = False

            async with self.session_maker() as session:
                current_time = datetime.now(tz=UTC)

                while True:
                    # Process in batches of 100 to avoid loading all records into memory
                    stmt = (
                        select(PasteEntity.id, PasteEntity.content_path)
                        .where(PasteEntity.expires_at < current_time)
                        .limit(BATCH_SIZE)
                    )
                    result = await session.execute(stmt)
                    batch = result.fetchall()

                    if not batch:
                        break

                    # Delete files first
                    for paste_id, content_path in batch:
                        file_path = Path(self.paste_base_folder_path) / content_path
                        try:
                            if file_path.exists():
                                file_path.unlink()
                        except Exception as exc:
                            error = True
                            self.logger.error("Failed to remove file %s: %s", file_path, exc)

                    # Bulk delete from database
                    paste_ids = [paste_id for paste_id, _ in batch]
                    delete_stmt = delete(PasteEntity).where(PasteEntity.id.in_(paste_ids))
                    await session.execute(delete_stmt)
                    await session.commit()

                    # Clear cache entries
                    for paste_id in paste_ids:
                        try:
                            await cache.delete(paste_id)
                        except Exception as exc:
                            self.logger.error("Failed to clear cache for %s: %s", paste_id, exc)

                    total_cleaned += len(batch)

                if total_cleaned > 0:
                    # Update active_pastes counter
                    counter = get_active_pastes_counter()
                    if counter:
                        counter.dec(total_cleaned)
                    if not error:
                        self.logger.info("Successfully cleaned up %d expired pastes", total_cleaned)
                    else:
                        self.logger.info("Cleaned up %d expired pastes with some errors", total_cleaned)
        except Exception as exc:
            self.logger.error("Failed to cleanup expired pastes: %s", exc)
        finally:
            duration = time.monotonic() - start_time
            cleanup_duration.observe(duration)

    async def _cleanup_deleted_pastes(self):
        """Remove deleted pastes that have been marked for deletion beyond the configured time"""
        if config.KEEP_DELETED_PASTES_TIME_HOURS == -1:
            self.logger.info("Skipping deletion of deleted pastes, because KEEP_DELETED_PASTES_TIME_HOURS is -1")
            return

        self.logger.info("Cleaning up deleted pastes")
        from app.api.subroutes.pastes import cache

        start_time = time.monotonic()
        try:
            BATCH_SIZE = 100
            total_cleaned = 0
            error: bool = False

            async with self.session_maker() as session:
                current_time = datetime.now(tz=UTC)
                delete_time_threshold = current_time.replace(microsecond=0) - timedelta(
                    hours=config.KEEP_DELETED_PASTES_TIME_HOURS
                )

                while True:
                    # Process in batches of 100 to avoid loading all records into memory
                    stmt = (
                        select(PasteEntity.id, PasteEntity.content_path)
                        .where(PasteEntity.deleted_at.isnot(None) & (PasteEntity.deleted_at < delete_time_threshold))
                        .limit(BATCH_SIZE)
                    )
                    result = await session.execute(stmt)
                    batch = result.fetchall()

                    if not batch:
                        break

                    # Delete files first
                    for paste_id, content_path in batch:
                        file_path = Path(self.paste_base_folder_path) / content_path
                        try:
                            if file_path.exists():
                                file_path.unlink()
                        except Exception as exc:
                            error = True
                            self.logger.error("Failed to remove file %s: %s", file_path, exc)

                    # Bulk delete from database
                    paste_ids = [paste_id for paste_id, _ in batch]
                    delete_stmt = delete(PasteEntity).where(PasteEntity.id.in_(paste_ids))
                    await session.execute(delete_stmt)
                    await session.commit()

                    # Clear cache entries
                    for paste_id in paste_ids:
                        try:
                            await cache.delete(paste_id)
                        except Exception as exc:
                            self.logger.error("Failed to clear cache for %s: %s", paste_id, exc)

                    total_cleaned += len(batch)

                if total_cleaned > 0:
                    if not error:
                        self.logger.info("Successfully cleaned up %d deleted pastes", total_cleaned)
                    else:
                        self.logger.info("Cleaned up %d deleted pastes with some errors", total_cleaned)
        except Exception as exc:
            self.logger.error("Failed to cleanup deleted pastes: %s", exc)
        finally:
            duration = time.monotonic() - start_time
            cleanup_duration.observe(duration)
