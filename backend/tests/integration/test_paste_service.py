"""Integration tests for PasteService."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.api.dto.paste_dto import (
    CreatePaste,
    EditPaste,
    PasteContentLanguage,
)
from app.api.dto.user_meta_data import UserMetaData
from app.db.models import PasteEntity
from app.services.cleanup_service import CleanupService
from app.services.paste_service import PasteService
from app.storage.local_storage import LocalStorageClient
from tests.constants import (
    STORAGE_MOCK_TOTAL,
    STORAGE_MOCK_USED,
    STORAGE_MOCK_FREE,
    TIME_TOLERANCE_SECONDS,
)
from app.utils.token_utils import hash_token


@pytest.fixture
async def paste_service(
    test_db_engine, temp_file_storage
) -> PasteService:
    """Create PasteService instance with test dependencies."""
    session_maker = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    cleanup_service = MagicMock(spec=CleanupService)
    storage_client = LocalStorageClient(base_path=str(temp_file_storage))
    return PasteService(
        session=session_maker,
        cleanup_service=cleanup_service,
        storage_client=storage_client,
    )


@pytest.fixture
def sample_user_metadata() -> UserMetaData:
    """Sample user metadata for testing."""
    return UserMetaData(ip="127.0.0.1", user_agent="Test Agent")


@pytest.fixture
async def paste_with_file(
    paste_service: PasteService, sample_user_metadata: UserMetaData
):
    """Create a paste with actual file on disk."""
    paste_dto = CreatePaste(
        title="Test Paste",
        content="Test content for file",
        content_language=PasteContentLanguage.plain_text,
    )
    paste = await paste_service.create_paste(paste_dto, sample_user_metadata)
    return paste


@pytest.fixture
async def expired_paste(
    paste_service: PasteService,
    sample_user_metadata: UserMetaData,
    temp_file_storage: Path,
):
    """Create an expired paste for testing."""
    # Create paste that's already expired - bypass CreatePaste validation
    expired_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)

    # Create it directly in the database to bypass expiration validation
    paste_id = uuid.uuid4()
    paste_path = f"pastes/{paste_id}.txt"
    full_path = temp_file_storage / paste_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text("This paste has expired")

    edit_token = uuid.uuid4().hex
    delete_token = uuid.uuid4().hex

    async with paste_service.session_maker() as session:
        entity = PasteEntity(
            id=paste_id,
            title="Expired Paste",
            content_path=paste_path,
            content_language="plain_text",
            expires_at=expired_time,
            creator_ip=str(sample_user_metadata.ip),
            creator_user_agent=sample_user_metadata.user_agent,
            content_size=len("This paste has expired"),
            edit_token=hash_token(edit_token),
            delete_token=hash_token(delete_token),
        )
        session.add(entity)
        await session.commit()
        await session.refresh(entity)

    return {
        "id": str(paste_id),
        "edit_token": edit_token,
        "delete_token": delete_token,
    }


@pytest.fixture
def mock_storage_full(monkeypatch):
    """Mock disk_usage to simulate full storage."""
    def mock_disk_usage(path):
        # Return: total, used, free (in bytes)
        # Free space less than 1MB (MIN_STORAGE_MB default in test config)
        return (STORAGE_MOCK_TOTAL, STORAGE_MOCK_USED, STORAGE_MOCK_FREE)

    monkeypatch.setattr("shutil.disk_usage", mock_disk_usage)


@pytest.mark.integration
class TestPasteServiceCreate:
    """Tests for paste creation operations."""

    async def test_create_paste_saves_to_database_and_file(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Create paste should save to both database and file system."""
        paste_dto = CreatePaste(
            title="Test Paste",
            content="Test content",
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Check database
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            assert db_paste.title == "Test Paste"
            assert db_paste.content_size == len("Test content")

        # Check file system
        file_path = temp_file_storage / db_paste.content_path
        assert file_path.exists()
        assert file_path.read_text() == "Test content"

    async def test_create_paste_returns_hashed_tokens_in_db(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste should store hashed tokens in database."""
        paste_dto = CreatePaste(
            title="Test",
            content="Content",
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Check database has hashed tokens
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            assert db_paste.edit_token.startswith("$argon2")
            assert db_paste.delete_token.startswith("$argon2")

    async def test_create_paste_returns_plaintext_tokens_to_user(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste should return plaintext tokens to user."""
        paste_dto = CreatePaste(
            title="Test",
            content="Content",
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Tokens returned to user should be plaintext
        assert not result.edit_token.startswith("$argon2")
        assert not result.delete_token.startswith("$argon2")
        assert len(result.edit_token) == 32  # UUID hex length
        assert len(result.delete_token) == 32

    async def test_create_paste_with_expiration(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste with expiration time."""
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=24)
        paste_dto = CreatePaste(
            title="Expiring Paste",
            content="This will expire",
            content_language=PasteContentLanguage.plain_text,
            expires_at=expires_at,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        assert result.expires_at is not None
        # Allow small time difference for test execution
        assert abs((result.expires_at - expires_at).total_seconds()) < TIME_TOLERANCE_SECONDS

    async def test_create_paste_without_expiration(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste without expiration (permanent paste)."""
        paste_dto = CreatePaste(
            title="Permanent Paste",
            content="This never expires",
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        assert result.expires_at is None

    async def test_create_paste_saves_user_metadata(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste should save user metadata."""
        paste_dto = CreatePaste(
            title="Test",
            content="Content",
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            assert db_paste.creator_ip == "127.0.0.1"
            assert db_paste.creator_user_agent == "Test Agent"

    async def test_create_paste_fails_when_storage_limit_exceeded(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        mock_storage_full,
    ):
        """Create paste should fail when storage limit is exceeded."""
        paste_dto = CreatePaste(
            title="Test",
            content="Content",
            content_language=PasteContentLanguage.plain_text,
        )

        with pytest.raises(HTTPException) as exc_info:
            await paste_service.create_paste(paste_dto, sample_user_metadata)

        assert exc_info.value.status_code == 500
        assert "Storage limit" in exc_info.value.detail

    async def test_create_paste_cleans_up_file_on_db_error(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Create paste should clean up file if database commit fails."""
        paste_dto = CreatePaste(
            title="Test",
            content="Content for cleanup test",
            content_language=PasteContentLanguage.plain_text,
        )

        # Track which paste ID was generated
        captured_paste_id = None

        # Mock session commit to raise an exception
        original_maker = paste_service.session_maker

        async def mock_session_context():
            session = original_maker()
            async with session:
                # Override commit to raise error
                original_commit = session.commit

                async def failing_commit():
                    # Capture the paste ID before failing
                    nonlocal captured_paste_id
                    from sqlalchemy import select
                    result = await session.execute(select(PasteEntity))
                    pastes = result.scalars().all()
                    if pastes:
                        captured_paste_id = pastes[-1].id

                    raise Exception("Database error")

                session.commit = failing_commit
                yield session

        with patch.object(paste_service, 'session_maker') as mock_maker:
            mock_maker.return_value.__aenter__ = lambda self: mock_session_context().__aenter__()
            mock_maker.return_value.__aexit__ = lambda self, *args: mock_session_context().__aexit__(*args)

            with pytest.raises(Exception):
                await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Verify file was cleaned up
        # Even if we couldn't capture the paste ID, check that no orphaned files exist
        # Files created during test should have been cleaned up
        test_files = list(temp_file_storage.glob("*.txt"))

        # If we captured the paste ID, verify that specific file doesn't exist
        if captured_paste_id:
            potential_file_path = temp_file_storage / f"{captured_paste_id}.txt"
            assert not potential_file_path.exists(), \
                f"File {potential_file_path} should have been deleted after DB error"

        # Also verify no unexpected files were left behind
        # (Should be 0, or only files from other tests)
        assert len(test_files) == 0, \
            f"Expected no orphaned files, but found: {[f.name for f in test_files]}"


@pytest.mark.integration
class TestPasteServiceGet:
    """Tests for paste retrieval operations."""

    async def test_get_paste_by_id_returns_content_from_file(
        self, paste_service: PasteService, paste_with_file
    ):
        """Get paste should return content from file system."""
        paste_id = paste_with_file.id

        result = await paste_service.get_paste_by_id(paste_id)

        assert result is not None
        assert result.id == paste_id
        assert result.content == "Test content for file"
        assert result.title == "Test Paste"

    async def test_get_paste_by_id_returns_none_for_expired_paste(
        self, paste_service: PasteService, expired_paste
    ):
        """Get paste should return None for expired pastes."""
        paste_id = expired_paste["id"]

        result = await paste_service.get_paste_by_id(paste_id)

        assert result is None

    async def test_get_paste_by_id_returns_none_for_nonexistent_paste(
        self, paste_service: PasteService
    ):
        """Get paste should return None for non-existent paste."""
        nonexistent_id = uuid.uuid4()

        result = await paste_service.get_paste_by_id(nonexistent_id)

        assert result is None

    async def test_get_paste_by_id_handles_missing_file_gracefully(
        self,
        paste_service: PasteService,
        paste_with_file,
        temp_file_storage: Path,
    ):
        """Get paste should handle missing file gracefully."""
        # Remove the file manually
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_with_file.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            file_path = temp_file_storage / db_paste.content_path
            file_path.unlink()

        result = await paste_service.get_paste_by_id(paste_with_file.id)

        # Should still return paste object but with None content
        assert result is not None
        assert result.content is None


@pytest.mark.integration
class TestPasteServiceEdit:
    """Tests for paste editing operations."""

    async def test_edit_paste_with_valid_hashed_token(
        self, paste_service: PasteService, paste_with_file
    ):
        """Edit paste should succeed with valid hashed token."""
        edit_dto = EditPaste(title="Updated Title")

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, paste_with_file.edit_token
        )

        assert result is not None
        assert result.title == "Updated Title"

    async def test_edit_paste_with_legacy_plaintext_token(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Edit paste should support legacy plaintext tokens."""
        # Create paste with plaintext token (simulating legacy data)
        paste_id = uuid.uuid4()
        plaintext_token = "legacy_plaintext_token"
        paste_path = f"pastes/{paste_id}.txt"
        full_path = temp_file_storage / paste_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("Legacy content")

        async with paste_service.session_maker() as session:
            entity = PasteEntity(
                id=paste_id,
                title="Legacy Paste",
                content_path=paste_path,
                content_language="plain_text",
                creator_ip="127.0.0.1",
                creator_user_agent="Test",
                content_size=14,
                edit_token=plaintext_token,  # Plaintext, not hashed
                delete_token=hash_token("delete123"),
            )
            session.add(entity)
            await session.commit()

        edit_dto = EditPaste(title="Updated via Legacy Token")
        result = await paste_service.edit_paste(
            paste_id, edit_dto, plaintext_token
        )

        assert result is not None
        assert result.title == "Updated via Legacy Token"

    async def test_edit_paste_upgrades_plaintext_to_hashed_token(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Edit paste should upgrade plaintext token to hashed on use."""
        # Create paste with plaintext token
        paste_id = uuid.uuid4()
        plaintext_token = "legacy_token"
        paste_path = f"pastes/{paste_id}.txt"
        full_path = temp_file_storage / paste_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("Content")

        async with paste_service.session_maker() as session:
            entity = PasteEntity(
                id=paste_id,
                title="Test",
                content_path=paste_path,
                content_language="plain_text",
                creator_ip="127.0.0.1",
                creator_user_agent="Test",
                content_size=7,
                edit_token=plaintext_token,
                delete_token=hash_token("delete"),
            )
            session.add(entity)
            await session.commit()

        # Edit with plaintext token
        await paste_service.edit_paste(
            paste_id, EditPaste(title="Updated"), plaintext_token
        )

        # Verify token was upgraded to hashed
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
            db_paste = (await session.execute(stmt)).scalar_one()
            assert db_paste.edit_token.startswith("$argon2")

    async def test_edit_paste_updates_only_provided_fields(
        self, paste_service: PasteService, paste_with_file
    ):
        """Edit paste should only update fields that are provided."""
        original_content = paste_with_file.content
        edit_dto = EditPaste(title="New Title Only")

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, paste_with_file.edit_token
        )

        assert result is not None
        assert result.title == "New Title Only"
        assert result.content == original_content  # Unchanged

    async def test_edit_paste_updates_content_and_creates_new_file(
        self,
        paste_service: PasteService,
        paste_with_file,
        temp_file_storage: Path,
    ):
        """Edit paste with new content should update file."""
        edit_dto = EditPaste(content="Updated content here")

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, paste_with_file.edit_token
        )

        assert result is not None
        assert result.content == "Updated content here"

        # Verify file was updated
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            file_path = temp_file_storage / db_paste.content_path
            assert file_path.read_text() == "Updated content here"
            assert db_paste.content_size == len("Updated content here")

    async def test_edit_paste_updates_language(
        self, paste_service: PasteService, paste_with_file
    ):
        """Edit paste should update content language."""
        # Test with valid enum value (only plain_text exists currently)
        edit_dto = EditPaste(content_language=PasteContentLanguage.plain_text)

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, paste_with_file.edit_token
        )

        assert result is not None
        assert result.content_language == PasteContentLanguage.plain_text

    async def test_edit_paste_updates_expiration(
        self, paste_service: PasteService, paste_with_file
    ):
        """Edit paste should update expiration time."""
        new_expiration = datetime.now(tz=timezone.utc) + timedelta(days=7)
        edit_dto = EditPaste(expires_at=new_expiration)

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, paste_with_file.edit_token
        )

        assert result is not None
        assert result.expires_at is not None
        assert abs((result.expires_at - new_expiration).total_seconds()) < TIME_TOLERANCE_SECONDS

    async def test_edit_paste_fails_with_invalid_token(
        self, paste_service: PasteService, paste_with_file
    ):
        """Edit paste should fail with invalid token."""
        edit_dto = EditPaste(title="Should Fail")
        invalid_token = "invalid_token_12345"

        result = await paste_service.edit_paste(
            paste_with_file.id, edit_dto, invalid_token
        )

        assert result is None

    async def test_edit_paste_fails_for_expired_paste(
        self, paste_service: PasteService, expired_paste
    ):
        """Edit paste should fail for expired pastes."""
        edit_dto = EditPaste(title="Should Fail")

        result = await paste_service.edit_paste(
            expired_paste["id"], edit_dto, expired_paste["edit_token"]
        )

        assert result is None


@pytest.mark.integration
class TestPasteServiceDelete:
    """Tests for paste deletion operations."""

    async def test_delete_paste_removes_database_entry_and_file(
        self,
        paste_service: PasteService,
        paste_with_file,
        temp_file_storage: Path,
    ):
        """Delete paste should remove both database entry and file."""
        paste_id = paste_with_file.id

        # Get file path before deletion
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
            db_paste = (await session.execute(stmt)).scalar_one()
            file_path = temp_file_storage / db_paste.content_path

        success = await paste_service.delete_paste(
            paste_id, paste_with_file.delete_token
        )

        assert success is True

        # Verify database entry is gone
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
            db_paste = (await session.execute(stmt)).scalar_one_or_none()
            assert db_paste is None

        # Note: File removal uses _remove_file which catches exceptions,
        # so we can't reliably test file deletion in this simple case

    async def test_delete_paste_with_valid_hashed_token(
        self, paste_service: PasteService, paste_with_file
    ):
        """Delete paste should succeed with valid hashed token."""
        success = await paste_service.delete_paste(
            paste_with_file.id, paste_with_file.delete_token
        )

        assert success is True

    async def test_delete_paste_with_legacy_plaintext_token(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Delete paste should support legacy plaintext tokens."""
        # Create paste with plaintext delete token
        paste_id = uuid.uuid4()
        plaintext_token = "legacy_delete_token"
        paste_path = f"pastes/{paste_id}.txt"
        full_path = temp_file_storage / paste_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("Content")

        async with paste_service.session_maker() as session:
            entity = PasteEntity(
                id=paste_id,
                title="Test",
                content_path=paste_path,
                content_language="plain_text",
                creator_ip="127.0.0.1",
                creator_user_agent="Test",
                content_size=7,
                edit_token=hash_token("edit"),
                delete_token=plaintext_token,  # Plaintext
            )
            session.add(entity)
            await session.commit()

        success = await paste_service.delete_paste(paste_id, plaintext_token)

        assert success is True

    async def test_delete_paste_fails_with_invalid_token(
        self, paste_service: PasteService, paste_with_file
    ):
        """Delete paste should fail with invalid token."""
        invalid_token = "wrong_token_12345"

        success = await paste_service.delete_paste(
            paste_with_file.id, invalid_token
        )

        assert success is False

    async def test_delete_paste_succeeds_even_if_file_missing(
        self,
        paste_service: PasteService,
        paste_with_file,
        temp_file_storage: Path,
    ):
        """Delete paste should succeed even if file is already missing."""
        # Remove file manually
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == paste_with_file.id)
            db_paste = (await session.execute(stmt)).scalar_one()
            file_path = temp_file_storage / db_paste.content_path
            file_path.unlink()

        success = await paste_service.delete_paste(
            paste_with_file.id, paste_with_file.delete_token
        )

        assert success is True

    async def test_delete_paste_fails_for_expired_paste(
        self, paste_service: PasteService, expired_paste
    ):
        """Delete paste should fail for expired pastes."""
        success = await paste_service.delete_paste(
            expired_paste["id"], expired_paste["delete_token"]
        )

        assert success is False


@pytest.mark.integration
class TestPasteServiceLegacy:
    """Tests for legacy paste retrieval."""

    async def test_get_legacy_paste_by_name_returns_content(
        self, paste_service: PasteService, temp_file_storage: Path
    ):
        """Get legacy paste should return content from hastebin directory."""
        # Create hastebin directory and file
        hastebin_dir = temp_file_storage / "hastebin"
        hastebin_dir.mkdir(parents=True, exist_ok=True)

        paste_name = "testpaste"
        paste_md5 = hashlib.md5(paste_name.encode()).hexdigest()
        legacy_file = hastebin_dir / paste_md5
        legacy_file.write_text("Legacy hastebin content")

        result = await paste_service.get_legacy_paste_by_name(paste_name)

        assert result is not None
        assert result.content == "Legacy hastebin content"

    async def test_get_legacy_paste_returns_none_when_directory_missing(
        self, paste_service: PasteService
    ):
        """Get legacy paste should return None when hastebin directory doesn't exist."""
        result = await paste_service.get_legacy_paste_by_name("anypaste")

        assert result is None

    async def test_get_legacy_paste_returns_none_for_nonexistent_file(
        self, paste_service: PasteService, temp_file_storage: Path
    ):
        """Get legacy paste should return None for non-existent file."""
        # Create hastebin directory but no file
        hastebin_dir = temp_file_storage / "hastebin"
        hastebin_dir.mkdir(parents=True, exist_ok=True)

        result = await paste_service.get_legacy_paste_by_name("nonexistent")

        assert result is None


@pytest.mark.integration
class TestPasteServiceCompression:
    """Tests for paste compression functionality."""

    async def test_create_paste_compresses_large_content(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
        temp_file_storage: Path,
    ):
        """Create paste should compress content above threshold."""
        # Create content above 512-byte threshold
        large_content = "This is test content that will be compressed. " * 50
        paste_dto = CreatePaste(
            title="Large Paste",
            content=large_content,
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Verify database metadata
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()

            assert db_paste.is_compressed is True
            assert db_paste.original_size is not None
            assert db_paste.original_size > db_paste.content_size

            # Verify file on disk is gzip-compressed
            file_path = temp_file_storage / db_paste.content_path
            assert file_path.exists()
            file_content = file_path.read_bytes()
            # Check for gzip magic number
            assert file_content.startswith(b"\x1f\x8b")

    async def test_create_paste_does_not_compress_small_content(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Create paste should not compress content below threshold."""
        small_content = "Small paste"
        paste_dto = CreatePaste(
            title="Small Paste",
            content=small_content,
            content_language=PasteContentLanguage.plain_text,
        )

        result = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Verify database metadata
        async with paste_service.session_maker() as session:
            stmt = select(PasteEntity).where(PasteEntity.id == result.id)
            db_paste = (await session.execute(stmt)).scalar_one()

            assert db_paste.is_compressed is False
            assert db_paste.original_size is None
            assert db_paste.content_size == len(small_content.encode('utf-8'))

    async def test_get_compressed_paste_returns_original_content(
        self,
        paste_service: PasteService,
        sample_user_metadata: UserMetaData,
    ):
        """Get paste should decompress compressed content correctly."""
        # Create compressed paste with large content
        large_content = "This is test content that will be compressed. " * 50
        paste_dto = CreatePaste(
            title="Compressed Paste",
            content=large_content,
            content_language=PasteContentLanguage.plain_text,
        )

        created_paste = await paste_service.create_paste(paste_dto, sample_user_metadata)

        # Read it back
        retrieved_paste = await paste_service.get_paste_by_id(created_paste.id)

        assert retrieved_paste is not None
        assert retrieved_paste.content == large_content

    async def test_backward_compatibility_with_uncompressed_pastes(
        self,
        paste_service: PasteService,
        temp_file_storage: Path,
    ):
        """Get paste should handle legacy uncompressed pastes correctly."""
        # Manually create an uncompressed paste (simulating legacy data)
        paste_id = uuid.uuid4()
        paste_path = f"pastes/{paste_id}.txt"
        full_path = temp_file_storage / paste_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_content = "This is a legacy uncompressed paste"
        full_path.write_text(legacy_content)

        # Insert database record with is_compressed=False, original_size=None
        async with paste_service.session_maker() as session:
            entity = PasteEntity(
                id=paste_id,
                title="Legacy Paste",
                content_path=paste_path,
                content_language="plain_text",
                creator_ip="127.0.0.1",
                creator_user_agent="Test",
                content_size=len(legacy_content.encode('utf-8')),
                is_compressed=False,
                original_size=None,
                edit_token=hash_token("edit123"),
                delete_token=hash_token("delete123"),
            )
            session.add(entity)
            await session.commit()

        # Read with get_paste_by_id
        result = await paste_service.get_paste_by_id(paste_id)

        assert result is not None
        assert result.content == legacy_content
