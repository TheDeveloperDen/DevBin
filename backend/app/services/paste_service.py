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
from sqlalchemy import or_, select
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
from app.storage import StorageClient
from app.utils.token_utils import hash_token, is_token_hashed, verify_token


class PasteService:
    def __init__(
            self,
            session: sessionmaker[AsyncSession],
            cleanup_service: CleanupService,
            storage_client: StorageClient,
    ):
        self.session_maker: sessionmaker[AsyncSession] = session
        self.storage_client: StorageClient = storage_client
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: asyncio.Task[Coroutine[None, None, None]] | None = None
        self._lock_file: Path = Path(".cleanup.lock")
        self._cleanup_service: CleanupService = cleanup_service

    async def _read_content(
        self, paste_path: str, is_compressed: bool = False
    ) -> str | None:
        """
        Read paste content, handling decompression if needed.

        Args:
            paste_path: Storage key for the paste
            is_compressed: Whether the content is compressed

        Returns:
            Decompressed content string or None on error
        """
        try:
            data = await self.storage_client.get_object(paste_path)
            if data is None:
                self.logger.error("Paste content not found: %s", paste_path)
                return None

            if is_compressed:
                from app.utils.compression import CompressionError, decompress_content

                try:
                    return decompress_content(data)
                except CompressionError as exc:
                    self.logger.error(
                        "Failed to decompress paste at %s: %s", paste_path, exc
                    )
                    return None
            else:
                return data.decode('utf-8')
        except Exception as exc:
            self.logger.error("Failed to read paste content: %s", exc)
            return None

    async def _save_content(
        self, paste_id: str, content: str
    ) -> tuple[str, int, bool, int | None] | None:
        """
        Save paste content, optionally compressed.

        Returns:
            Tuple of (content_path, content_size, is_compressed, original_size) or None
        """
        try:
            from app.utils.compression import (
                CompressionError,
                compress_content,
                should_compress,
            )

            # Determine if we should compress
            use_compression = False
            compressed_data = None
            original_size = len(content.encode('utf-8'))

            if config.COMPRESSION_ENABLED and should_compress(
                content, config.COMPRESSION_THRESHOLD_BYTES
            ):
                try:
                    compressed_data, original_size = compress_content(
                        content, config.COMPRESSION_LEVEL
                    )
                    # Only use compression if it actually saves space
                    if len(compressed_data) < original_size:
                        use_compression = True
                        self.logger.info(
                            "Compressed paste %s: %d -> %d bytes (%.1f%% reduction)",
                            paste_id,
                            original_size,
                            len(compressed_data),
                            100 * (1 - len(compressed_data) / original_size),
                        )
                    else:
                        self.logger.debug(
                            "Compression not beneficial for paste %s, storing uncompressed",
                            paste_id,
                        )
                except CompressionError as exc:
                    self.logger.warning(
                        "Compression failed for paste %s, storing uncompressed: %s",
                        paste_id,
                        exc,
                    )

            # Prepare storage key
            storage_key = f"pastes/{paste_id}.txt"

            # Write content (compressed or uncompressed)
            if use_compression and compressed_data:
                await self.storage_client.put_object(storage_key, compressed_data)
                content_size = len(compressed_data)
                return storage_key, content_size, True, original_size
            else:
                await self.storage_client.put_object(storage_key, content.encode('utf-8'))
                content_size = original_size
                return storage_key, content_size, False, None

        except Exception as exc:
            self.logger.error("Failed to save paste content: %s", exc)
            return None

    async def _remove_file(self, storage_key: str):
        """Remove paste file from storage."""
        try:
            await self.storage_client.delete_object(storage_key)
        except Exception as exc:
            self.logger.error("Failed to remove file %s: %s", storage_key, exc)

    def verify_storage_limit(self):
        """Verify storage limit (only applicable for local storage)."""
        try:
            # Only check disk usage for local storage
            from app.storage.local_storage import LocalStorageClient

            if not isinstance(self.storage_client, LocalStorageClient):
                # Skip storage limit check for cloud storage (S3, MinIO)
                return True

            # Get the total, used, and free disk space for the base folder path
            total, used, free = shutil.disk_usage(self.storage_client.base_path)
            # Check if we have enough free space
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
        """Get legacy Hastebin-format paste."""
        paste_md5: str = hashlib.md5(paste_id.encode()).hexdigest()
        storage_key = f"hastebin/{paste_md5}"

        try:
            data = await self.storage_client.get_object(storage_key)
            if data is not None:
                content = data.decode('utf-8')
                return LegacyPasteResponse(content=content)
        except Exception as exc:
            self.logger.debug("Legacy paste not found: %s", exc)
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
                result.content_path,
                is_compressed=result.is_compressed,
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
                save_result = await self._save_content(
                    str(paste_id), edit_paste.content
                )
                if not save_result:
                    return None
                (
                    new_content_path,
                    content_size,
                    is_compressed,
                    original_size,
                ) = save_result
                result.content_path = new_content_path
                result.content_size = content_size
                result.is_compressed = is_compressed
                result.original_size = original_size

            result.last_updated_at = datetime.now(tz=timezone.utc)

            await session.commit()
            await session.refresh(result)

            # Re-read content if updated
            content = (
                edit_paste.content
                if edit_paste.content is not None
                else await self._read_content(
                    result.content_path,
                    is_compressed=result.is_compressed,
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
        save_result = await self._save_content(
            str(paste_id),
            paste.content,
        )
        if not save_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to save paste content",
                headers={"Retry-After": "60"},
            )

        paste_path, content_size, is_compressed, original_size = save_result

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
                    content_size=content_size,
                    is_compressed=is_compressed,
                    original_size=original_size,
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
