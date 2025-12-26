"""Test helper functions and assertion utilities."""

from pathlib import Path
from typing import Any

from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PasteEntity


async def assert_paste_in_db(session: AsyncSession, paste_id: str) -> PasteEntity:
    """
    Verify paste exists in database and return it.

    Args:
        session: Database session
        paste_id: ID of the paste to check

    Returns:
        The paste entity from the database

    Raises:
        AssertionError: If paste doesn't exist
    """
    stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
    result = await session.execute(stmt)
    paste = result.scalar_one_or_none()

    assert paste is not None, f"Paste {paste_id} not found in database"
    return paste


async def assert_paste_not_in_db(session: AsyncSession, paste_id: str):
    """
    Verify paste does NOT exist in database.

    Args:
        session: Database session
        paste_id: ID of the paste to check

    Raises:
        AssertionError: If paste exists
    """
    stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
    result = await session.execute(stmt)
    paste = result.scalar_one_or_none()

    assert paste is None, f"Paste {paste_id} should not exist in database but was found"


def assert_paste_file_exists(storage_path: Path, paste_id: str):
    """
    Verify paste file exists on disk.

    Args:
        storage_path: Path to the storage directory
        paste_id: ID of the paste

    Raises:
        AssertionError: If file doesn't exist
    """
    paste_file = storage_path / f"{paste_id}.txt"
    assert paste_file.exists(), f"Paste file {paste_file} should exist but doesn't"


def assert_paste_file_not_exists(storage_path: Path, paste_id: str):
    """
    Verify paste file does NOT exist on disk.

    Args:
        storage_path: Path to the storage directory
        paste_id: ID of the paste

    Raises:
        AssertionError: If file exists
    """
    paste_file = storage_path / f"{paste_id}.txt"
    assert not paste_file.exists(), f"Paste file {paste_file} should not exist but was found"


def assert_error_response(
    response: Response, status_code: int, error_type: str | None = None, error_message_contains: str | None = None
):
    """
    Standardized error response validation.

    Args:
        response: HTTP response object
        status_code: Expected status code
        error_type: Expected error type/code (optional)
        error_message_contains: Substring that should be in error message (optional)

    Raises:
        AssertionError: If response doesn't match expectations
    """
    assert response.status_code == status_code, f"Expected status code {status_code}, got {response.status_code}"

    data = response.json()

    # Check for error field (can be at root or in detail)
    if error_type:
        if "error" in data:
            assert data["error"] == error_type, f"Expected error type '{error_type}', got '{data['error']}'"
        elif "detail" in data and isinstance(data["detail"], dict) and "error" in data["detail"]:
            assert data["detail"]["error"] == error_type, (
                f"Expected error type '{error_type}', got '{data['detail']['error']}'"
            )
        else:
            raise AssertionError(f"Error type '{error_type}' not found in response: {data}")

    # Check error message contains expected substring
    if error_message_contains:
        response_str = str(data).lower()
        assert error_message_contains.lower() in response_str, (
            f"Expected error message to contain '{error_message_contains}', got: {data}"
        )


def assert_successful_paste_response(response: Response) -> dict[str, Any]:
    """
    Verify a successful paste creation/retrieval response.

    Args:
        response: HTTP response object

    Returns:
        The response data as a dictionary

    Raises:
        AssertionError: If response doesn't match expectations
    """
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    data = response.json()

    # Must have paste ID
    assert "id" in data, "Response should contain 'id' field"
    assert isinstance(data["id"], str), "Paste ID should be a string"
    assert len(data["id"]) > 0, "Paste ID should not be empty"

    return data


def assert_tokens_valid(paste_data: dict[str, Any]):
    """
    Verify paste tokens are present and properly formatted.

    Args:
        paste_data: Paste data dictionary

    Raises:
        AssertionError: If tokens are invalid
    """
    from tests.constants import TEST_TOKEN_LENGTH

    assert "edit_token" in paste_data, "Response should contain 'edit_token'"
    assert "delete_token" in paste_data, "Response should contain 'delete_token'"

    # Tokens should be plaintext (not hashed) when returned to user
    assert not paste_data["edit_token"].startswith("$argon2"), "Edit token should be plaintext, not hashed"
    assert not paste_data["delete_token"].startswith("$argon2"), "Delete token should be plaintext, not hashed"

    # Tokens should be proper length
    assert len(paste_data["edit_token"]) == TEST_TOKEN_LENGTH, f"Edit token should be {TEST_TOKEN_LENGTH} characters"
    assert len(paste_data["delete_token"]) == TEST_TOKEN_LENGTH, (
        f"Delete token should be {TEST_TOKEN_LENGTH} characters"
    )


async def assert_paste_content_matches(session: AsyncSession, storage_path: Path, paste_id: str, expected_content: str):
    """
    Verify paste content matches both in database and file system.

    Args:
        session: Database session
        storage_path: Path to file storage
        paste_id: Paste ID
        expected_content: Expected content

    Raises:
        AssertionError: If content doesn't match
    """
    # Check database
    await assert_paste_in_db(session, paste_id)

    # Check file
    paste_file = storage_path / f"{paste_id}.txt"
    assert paste_file.exists(), f"Paste file {paste_file} should exist"

    actual_content = paste_file.read_text()
    assert actual_content == expected_content, (
        f"Content mismatch. Expected: {expected_content[:100]}, Got: {actual_content[:100]}"
    )
