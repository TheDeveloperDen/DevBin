from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import uuid
from datetime import datetime, timezone
from os import path
from pathlib import Path
from typing import Coroutine, final

import aiofiles
from aiofiles import os
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.util import md5_hex

from app.api.dto.paste_dto import (
    CreatePaste,
    LegacyPasteResponse,
    PasteContentLanguage,
    PasteResponse,
)
from app.api.dto.user_meta_data import UserMetaData
from app.config import config
from app.db.models import PasteEntity


class PasteService:
    def __init__(
        self,
        session: sessionmaker[AsyncSession],  # pyright: ignore[reportInvalidTypeArguments]
        paste_base_folder_path: str = "",
    ):
        self.session_maker: sessionmaker[AsyncSession] = session  # pyright: ignore[reportInvalidTypeArguments]
        self.paste_base_folder_path: str = (
            paste_base_folder_path  # if it is in a subfolder of the project
        )
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: asyncio.Task[Coroutine[None, None, None]] | None = None
        self._lock_file: Path = Path(".cleanup.lock")

    def start_cleanup_worker(self):
        """Start the background cleanup worker"""
        self.logger.info("Starting cleanup worker")
        if self._cleanup_task is not None or self._lock_file.exists():
            return  # Already running
        _ = self._acquire_lock()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("Background cleanup worker started")

    async def stop_cleanup_worker(self):
        """Stop the background cleanup worker"""
        if self._cleanup_task is not None:
            _ = self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self._release_lock()
            self.logger.info("Background cleanup worker stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop that runs every 10 minutes"""
        while True:
            self._touch_lock()
            try:
                logging.info("Cleaning up expired pastes")
                # Try to acquire lock (only one worker can run cleanup)
                await self._cleanup_expired_pastes()

                # Wait 5 minutes before next run
                await asyncio.sleep(300)
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
            logging.info("Cleanup lock acquired")
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
                    await cache.delete(paste_id)

                    delete_stmt = delete(PasteEntity).where(PasteEntity.id == paste_id)
                    file_path = Path(self.paste_base_folder_path) / content_path
                    try:
                        if file_path.exists():
                            file_path.unlink()
                        await session.execute(delete_stmt)
                        await session.commit()
                    except Exception as exc:
                        error = True
                        self.logger.error(
                            "Failed to remove file %s: %s", file_path, exc
                        )
                if not error:
                    delete_stmt = delete(PasteEntity).where(
                        PasteEntity.expires_at < current_time
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
        except Exception as exc:
            self.logger.error("Failed to cleanup expired pastes: %s", exc)

    async def _read_content(self, paste_path: str) -> str | None:
        try:
            async with aiofiles.open(paste_path) as f:
                return await f.read()
        except Exception as exc:
            self.logger.error("Failed to read paste content: %s", exc)
            return None

    async def _save_content(self, paste_id: str, content: str) -> str | None:
        try:
            base_file_path = path.join("pastes", f"{paste_id}.txt")
            file_path = path.join(self.paste_base_folder_path, base_file_path)
            await os.makedirs(path.dirname(file_path), exist_ok=True)
            async with aiofiles.open(file_path, "w") as f:
                await f.write(content)

            return base_file_path
        except Exception as exc:
            self.logger.error("Failed to save paste content: %s", exc)
            return None

    async def _remove_file(self, paste_path: str):
        try:
            await os.remove(paste_path)
        except Exception as exc:
            self.logger.error("Failed to remove file %s: %s", paste_path, exc)

    def verify_storage_limit(self):
        try:
            # Get the total, used, and free disk space for the base folder path
            total, used, free = shutil.disk_usage(self.paste_base_folder_path)
            # Check if we have enough free space (let's say 100MB minimum)
            min_free_space = config.MIN_STORAGE_MB * 1024 * 1024
            if free < min_free_space:
                self.logger.warning(
                    "Not enough disk space available. Total: %d, Used: %d, Free: %d",
                    total,
                    used,
                    free,
                )
                return False

            return True
        except Exception as exc:
            self.logger.error("Failed to verify storage limit: %s", exc)
            # If we can't check, better to allow the operation to proceed
            return True

    async def get_legacy_paste_by_name(
        self, paste_id: str
    ) -> LegacyPasteResponse | None:
        if not (await os.path.exists(self.paste_base_folder_path)) or not (
            await os.path.isdir(path.join(self.paste_base_folder_path, "hastebin"))
        ):
            return None
        paste_md5: str = hashlib.md5(paste_id.encode()).hexdigest()
        file_path = path.join(self.paste_base_folder_path, "hastebin", paste_md5)

        try:
            if await os.path.exists(file_path):
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                return LegacyPasteResponse(content=content)
        except (OSError, IOError):
            pass
        return None

    async def get_paste_by_id(self, paste_id: UUID4) -> PasteResponse | None:
        async with self.session_maker() as session:
            stmt = (
                select(PasteEntity)
                .where(
                    PasteEntity.id == paste_id,
                    or_(
                        PasteEntity.expires_at > datetime.now(tz=timezone.utc),
                        PasteEntity.expires_at.is_(None),
                    ),
                )
                .limit(1)
            )
            result: PasteEntity | None = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if result is None:
                return None
            content = await self._read_content(
                path.join(self.paste_base_folder_path, result.content_path),
            )
            return PasteResponse(
                id=result.id,
                title=result.title,
                content=content,
                content_language=PasteContentLanguage(result.content_language),
                created_at=result.created_at,
                expires_at=result.expires_at,
            )

    async def create_paste(
        self, paste: CreatePaste, user_data: UserMetaData
    ) -> PasteResponse:
        if not self.verify_storage_limit():
            raise HTTPException(
                status_code=500,
                detail="Storage limit reached, contact administration",
            )

        paste_id = uuid.uuid4()
        paste_path = await self._save_content(
            str(paste_id),
            paste.content,
        )
        if not paste_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to save paste content",
                headers={"Retry-After": "60"},
            )
        try:
            async with self.session_maker() as session:
                entity: PasteEntity = PasteEntity(
                    id=paste_id,
                    title=paste.title,
                    content_path=paste_path,
                    content_language=paste.content_language.value,
                    expires_at=paste.expires_at,
                    creator_ip=str(user_data.ip),
                    creator_user_agent=user_data.user_agent,
                    content_size=len(paste.content),
                )
                session.add(entity)
                await session.commit()
                await session.refresh(entity)

                return PasteResponse(
                    id=entity.id,
                    title=entity.title,
                    content=paste.content,
                    content_language=PasteContentLanguage(entity.content_language),
                    created_at=entity.created_at,
                    expires_at=entity.expires_at,
                )
        except Exception as exc:
            self.logger.error("Failed to create paste: %s", exc)
            await self._remove_file(paste_path)
            raise HTTPException(
                status_code=500,
                detail="Failed to create paste",
                headers={"Retry-After": "60"},
            )
