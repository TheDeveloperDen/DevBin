import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Coroutine

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import config
from app.db.models import PasteEntity


class CleanupService:
    def __init__(
            self,
            session_maker: sessionmaker[AsyncSession],  # pyright: ignore[reportInvalidTypeArguments]
            paste_base_folder_path: str = "",
    ):
        self.session_maker: sessionmaker[AsyncSession] = session_maker
        self.paste_base_folder_path: str = paste_base_folder_path
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: asyncio.Task[Coroutine[None, None, None]] | None = None
        self._lock_file: Path = Path(".cleanup.lock")

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
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self._release_lock()
            self.logger.info("Background cleanup worker stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop that runs every 5 minutes"""
        # Wait for 5 minutes and retry
        while not self._acquire_lock():
            await asyncio.sleep(300)

        while True:
            self._touch_lock()
            try:
                self.logger.info("Cleaning up expired pastes")
                # Try to acquire lock (only one worker can run cleanup)
                await self._cleanup_expired_pastes()
                if config.KEEP_DELETED_PASTES_TIME_HOURS != -1:
                    self._touch_lock()
                    await self._cleanup_deleted_pastes()

                # Wait 5 minutes before next run
                await asyncio.sleep(600)
            except Exception as exc:
                self.logger.error("Error in cleanup loop: %s", exc)
                await asyncio.sleep(60)  # Retry after 1 minute on error

    def _touch_lock(self):
        self._lock_file.touch()

    def _acquire_lock(self) -> bool:
        """Try to acquire cleanup lock"""
        try:
            if self._lock_file.exists():
                # Check if lock is stale (older than 15 minutes)
                lock_time = self._lock_file.stat().st_mtime
                if datetime.now().timestamp() - lock_time < 900:  # 15 minutes
                    return False  # Lock still valid

            # Create or update lock file
            self._touch_lock()
            self.logger.info("Cleanup lock acquired")
            return True
        except Exception as exc:
            self.logger.error("Failed to acquire cleanup lock: %s", exc)
            return False

    def _release_lock(self):
        """Release cleanup lock"""
        try:
            if self._lock_file.exists():
                self._lock_file.unlink()
        except Exception as exc:
            self.logger.error("Failed to release cleanup lock: %s", exc)

    async def _cleanup_expired_pastes(self):
        """Remove expired pastes and their files"""
        from app.api.subroutes.pastes import cache

        try:
            async with self.session_maker() as session:
                current_time = datetime.now(tz=timezone.utc)
                # Get expired paste IDs
                stmt = select(PasteEntity.id, PasteEntity.content_path).where(
                    PasteEntity.expires_at < current_time
                )
                result = await session.execute(stmt)
                expired_pastes = result.fetchall()

                if not expired_pastes:
                    return

                error: bool = False
                # Delete from database and Files
                for paste_id, content_path in expired_pastes:
                    delete_stmt = delete(PasteEntity).where(PasteEntity.id == paste_id)
                    file_path = Path(self.paste_base_folder_path) / content_path
                    try:
                        if file_path.exists():
                            file_path.unlink()
                        await session.execute(delete_stmt)
                        await session.commit()
                        await cache.delete(paste_id)
                    except Exception as exc:
                        error = True
                        self.logger.error(
                            "Failed to remove file %s: %s", file_path, exc
                        )
                if not error:
                    logging.info("Successfully cleaned up expired pastes")
                else:
                    logging.info("Successfully cleaned up expired pastes, with errors.")
        except Exception as exc:
            self.logger.error("Failed to cleanup expired pastes: %s", exc)

    async def _cleanup_deleted_pastes(self):
        """Remove deleted pastes that have been marked for deletion beyond the configured time"""
        if config.KEEP_DELETED_PASTES_TIME_HOURS == -1:
            self.logger.info(
                "Skipping deletion of deleted pastes, because KEEP_DELETED_PASTES_TIME_HOURS is -1"
            )
            return
        self.logger.info("Cleaning up deleted pastes")
        from app.api.subroutes.pastes import cache

        try:
            async with self.session_maker() as session:
                current_time = datetime.now(tz=timezone.utc)
                delete_time_threshold = current_time.replace(microsecond=0) - timedelta(
                    hours=config.KEEP_DELETED_PASTES_TIME_HOURS
                )

                # Get deleted paste IDs
                stmt = select(PasteEntity.id, PasteEntity.content_path).where(
                    PasteEntity.deleted_at.isnot(None)
                    & (PasteEntity.deleted_at < delete_time_threshold)
                )
                result = await session.execute(stmt)
                deleted_pastes = result.fetchall()

                if not deleted_pastes:
                    return

                error: bool = False
                # Delete from database and files
                for paste_id, content_path in deleted_pastes:
                    self.logger.info("Cleaning up deleted pastes: %s", paste_id)
                    delete_stmt = delete(PasteEntity).where(PasteEntity.id == paste_id)
                    file_path = Path(self.paste_base_folder_path) / content_path
                    try:
                        if file_path.exists():
                            file_path.unlink()
                        await session.execute(delete_stmt)
                        await session.commit()
                        await cache.delete(paste_id)
                        self.logger.info(
                            "Successfully Cleaned up deleted pastes: %s", paste_id
                        )
                    except Exception as exc:
                        error = True
                        self.logger.error(
                            "Failed to remove file %s: %s", file_path, exc
                        )
                if not error:
                    self.logger.info(
                        "Successfully Cleaned up deleted pastes, with no errors"
                    )
                else:
                    self.logger.info(
                        "Successfully Cleaned up deleted pastes, with possible errors"
                    )
        except Exception as exc:
            self.logger.error("Failed to cleanup deleted pastes: %s", exc)
