from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import uuid
from datetime import datetime, timezone
from os import path
from pathlib import Path
from typing import Coroutine

import aiofiles
from aiofiles import os
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.api.dto.paste_dto import (
    CreatePaste,
    CreatePasteResponse,
    EditPaste,
    LegacyPasteResponse,
    PasteContentLanguage,
    PasteResponse,
)
from app.api.dto.user_meta_data import UserMetaData
from app.config import config
from app.db.models import PasteEntity
from app.services.cleanup_service import CleanupService
from app.utils.token_utils import hash_token, is_token_hashed, verify_token


class PasteService:
    def __init__(
        self,
        session: sessionmaker[AsyncSession],
        cleanup_service: CleanupService,
        paste_base_folder_path: str = "",
    ):
        self.session_maker: sessionmaker[AsyncSession] = session
        self.paste_base_folder_path: str = (
            paste_base_folder_path  # if it is in a subfolder of the project
        )
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: asyncio.Task[Coroutine[None, None, None]] | None = None
        self._lock_file: Path = Path(".cleanup.lock")
        self._cleanup_service: CleanupService = cleanup_service


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
                last_updated_at=result.last_updated_at,
            )

    async def edit_paste(
        self, paste_id: UUID4, edit_paste: EditPaste, edit_token: str
    ) -> PasteResponse | None:
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

            # Verify token - support both hashed (new) and plaintext (legacy)
            token_valid = False
            if is_token_hashed(result.edit_token):
                # New hashed token
                token_valid = verify_token(edit_token, result.edit_token)
            else:
                # Legacy plaintext token (during migration period)
                token_valid = result.edit_token == edit_token
                if token_valid:
                    # Opportunistically upgrade to hashed token
                    result.edit_token = hash_token(edit_token)
                    self.logger.info(
                        "Upgraded edit token to hashed format for paste %s", paste_id
                    )

            if not token_valid:
                return None

            # Update only the fields that are provided (not None)
            if (
                edit_paste.title is not None
            ):  # Using ellipsis as sentinel for "not provided"
                result.title = edit_paste.title
            if edit_paste.content_language is not None:
                result.content_language = edit_paste.content_language.value
            if edit_paste.is_expires_at_set():
                result.expires_at = edit_paste.expires_at

            # Handle content update separately
            if edit_paste.content is not None:
                new_content_path = await self._save_content(
                    str(paste_id), edit_paste.content
                )
                if not new_content_path:
                    return None
                result.content_path = new_content_path
                result.content_size = len(edit_paste.content)

            result.last_updated_at = datetime.now(tz=timezone.utc)

            await session.commit()
            await session.refresh(result)

            # Re-read content if updated
            content = (
                edit_paste.content
                if edit_paste.content is not None
                else await self._read_content(
                    path.join(self.paste_base_folder_path, result.content_path)
                )
            )

            return PasteResponse(
                id=result.id,
                title=result.title,
                content=content,
                content_language=PasteContentLanguage(result.content_language),
                expires_at=result.expires_at,
                created_at=result.created_at,
                last_updated_at=result.last_updated_at,
            )

    async def delete_paste(self, paste_id: UUID4, delete_token: str) -> bool:
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
                return False

            # Verify token - support both hashed (new) and plaintext (legacy)
            token_valid = False
            if is_token_hashed(result.delete_token):
                # New hashed token
                token_valid = verify_token(delete_token, result.delete_token)
            else:
                # Legacy plaintext token (during migration period)
                token_valid = result.delete_token == delete_token
                # No need to upgrade here since we're deleting anyway

            if not token_valid:
                return False

            # Remove file
            try:
                await self._remove_file(result.content_path)
            except Exception:
                pass  # File might already be deleted

            # Delete from database
            await session.delete(result)
            await session.commit()
            return True

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
            # Generate plaintext tokens to return to user
            edit_token_plaintext = uuid.uuid4().hex
            delete_token_plaintext = uuid.uuid4().hex

            # Hash tokens for storage
            edit_token_hashed = hash_token(edit_token_plaintext)
            delete_token_hashed = hash_token(delete_token_plaintext)

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
                    edit_token=edit_token_hashed,
                    delete_token=delete_token_hashed,
                )
                session.add(entity)
                await session.commit()
                await session.refresh(entity)

                return CreatePasteResponse(
                    id=entity.id,
                    title=entity.title,
                    content=paste.content,
                    content_language=PasteContentLanguage(entity.content_language),
                    created_at=entity.created_at,
                    last_updated_at=entity.last_updated_at,
                    expires_at=entity.expires_at,
                    edit_token=edit_token_plaintext,
                    delete_token=delete_token_plaintext,
                )
        except Exception as exc:
            self.logger.error("Failed to create paste: %s", exc)
            await self._remove_file(paste_path)
            raise HTTPException(
                status_code=500,
                detail="Failed to create paste",
                headers={"Retry-After": "60"},
            )
