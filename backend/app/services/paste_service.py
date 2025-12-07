from __future__ import annotations

import logging
import uuid
from datetime import datetime
from http.client import HTTPResponse
from os import path
from typing import Any
from warnings import catch_warnings

import aiofiles
from aiofiles import os
from fastapi import HTTPException
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker

from app.api.dto.paste_dto import CreatePaste, PasteResponse, PasteContentLanguage
from app.api.dto.user_meta_data import UserMetaData
from app.db.models import PasteEntity


class PasteServiuce:
    def __init__(self, session: sessionmaker, paste_base_url: str = "http://localhost:8000",
                 paste_base_folder_path: str = ""):
        self.session_maker = session
        self.paste_base_url = paste_base_url  # like https://mydomain.com/p/
        self.paste_base_folder_path = paste_base_folder_path  # if it is in a subfolder
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _read_content(self, paste_path: str) -> str:
        try:
            async with aiofiles.open(paste_path) as f:
                return await f.read()
        except Exception as exc:
            self.logger.error("Failed to read paste content: %s", exc)
            raise HTTPException(
                status_code=404,
                detail="Paste not found",
            ) from exc

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

    async def get_paste_by_id(self, paste_id: str) -> PasteResponse | None:
        async with self.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_id).limit(1)
            result: PasteEntity | None = (await session.execute(stmt)).scalar_one_or_none()
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

    async def create_paste(self, paste: CreatePaste, user_data: UserMetaData) -> PasteResponse:
        paste_id = uuid.uuid4()
        paste_path = await self._save_content(
            str(paste_id), paste.content,
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
                    creator_ip=user_data.ip,
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
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to create paste",
                headers={"Retry-After": "60"},
            )
