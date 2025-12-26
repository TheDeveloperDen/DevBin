"""Test data factories for creating test entities with flexible parameters."""

from datetime import UTC, datetime, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dto.paste_dto import CreatePaste, PasteContentLanguage
from app.api.dto.user_meta_data import UserMetaData
from app.services.paste_service import PasteService


@pytest_asyncio.fixture
def paste_factory(paste_service: PasteService, sample_user_metadata: UserMetaData):
    """
    Factory fixture for creating pastes with flexible parameters.

    Returns a function that creates pastes with custom overrides.

    Example usage:
        async def test_something(paste_factory):
            paste = await paste_factory(title="Custom Title")
            paste_with_expiry = await paste_factory(expires_in_hours=24)
    """

    async def _create_paste(
        title: str = "Test Paste",
        content: str = "Test content",
        content_language: PasteContentLanguage = PasteContentLanguage.plain_text,
        expires_in_hours: int | None = None,
        user_metadata: UserMetaData | None = None,
    ):
        """
        Create a paste with the given parameters.

        Args:
            title: Paste title
            content: Paste content
            content_language: Content language/syntax
            expires_in_hours: Hours until expiration (None for no expiration)
            user_metadata: User metadata (uses default if not provided)

        Returns:
            Created paste DTO
        """
        expires_at = None
        if expires_in_hours is not None:
            expires_at = datetime.now(tz=UTC) + timedelta(hours=expires_in_hours)

        paste_dto = CreatePaste(
            title=title,
            content=content,
            content_language=content_language,
            expires_at=expires_at,
        )

        metadata = user_metadata or sample_user_metadata

        return await paste_service.create_paste(paste_dto, metadata)

    return _create_paste


@pytest_asyncio.fixture
def expired_paste_factory(paste_service: PasteService, sample_user_metadata: UserMetaData, db_session: AsyncSession):
    """
    Factory fixture for creating expired pastes.

    This directly manipulates the database to create pastes that are already expired,
    bypassing validation that would prevent creating expired pastes.

    Example usage:
        async def test_expired_behavior(expired_paste_factory):
            paste = await expired_paste_factory(expired_hours_ago=1)
    """

    async def _create_expired_paste(
        title: str = "Expired Paste",
        content: str = "This paste has expired",
        content_language: PasteContentLanguage = PasteContentLanguage.plain_text,
        expired_hours_ago: int = 1,
    ):
        """
        Create an expired paste.

        Args:
            title: Paste title
            content: Paste content
            content_language: Content language/syntax
            expired_hours_ago: How many hours ago the paste expired

        Returns:
            Dictionary with paste info (id, edit_token, delete_token)
        """
        import uuid

        from app.db.models import PasteEntity
        from app.utils.token_utils import hash_token

        paste_id = str(uuid.uuid4())
        edit_token = uuid.uuid4().hex
        delete_token = uuid.uuid4().hex

        # Create paste that expired in the past
        expires_at = datetime.now(tz=UTC) - timedelta(hours=expired_hours_ago)

        paste = PasteEntity(
            id=paste_id,
            title=title,
            content_language=content_language.value,
            edit_token=hash_token(edit_token),
            delete_token=hash_token(delete_token),
            created_at=datetime.now(tz=UTC) - timedelta(hours=expired_hours_ago + 1),
            expires_at=expires_at,
            user_ip=sample_user_metadata.user_ip,
            user_agent=sample_user_metadata.user_agent,
        )

        db_session.add(paste)
        await db_session.commit()
        await db_session.refresh(paste)

        # Also create the file
        import os
        from pathlib import Path

        storage_path = Path(os.getenv("APP_BASE_FOLDER_PATH", "/tmp/devbin_test_files"))
        storage_path.mkdir(parents=True, exist_ok=True)

        paste_file = storage_path / f"{paste_id}.txt"
        paste_file.write_text(content)

        return {
            "id": paste_id,
            "edit_token": edit_token,
            "delete_token": delete_token,
            "title": title,
            "expires_at": expires_at,
        }

    return _create_expired_paste


@pytest_asyncio.fixture
def paste_with_custom_language_factory(paste_service: PasteService, sample_user_metadata: UserMetaData):
    """
    Factory for creating pastes with specific programming languages.

    Example usage:
        async def test_python_paste(paste_with_custom_language_factory):
            paste = await paste_with_custom_language_factory(
                language=PasteContentLanguage.python,
                content="print('hello')"
            )
    """

    async def _create_paste_with_language(
        language: PasteContentLanguage,
        content: str,
        title: str | None = None,
    ):
        """
        Create a paste with specific language.

        Args:
            language: Programming language/syntax
            content: Paste content
            title: Optional title (auto-generated if not provided)

        Returns:
            Created paste DTO
        """
        if title is None:
            title = f"{language.value.capitalize()} Paste"

        paste_dto = CreatePaste(
            title=title,
            content=content,
            content_language=language,
        )

        return await paste_service.create_paste(paste_dto, sample_user_metadata)

    return _create_paste_with_language
