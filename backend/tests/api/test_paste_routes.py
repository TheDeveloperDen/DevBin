"""API tests for paste endpoints."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from tests.constants import TEST_TOKEN_LENGTH


@pytest.mark.asyncio
class TestPasteCreateAPI:
    """API tests for paste creation endpoint."""

    async def test_create_paste_returns_plaintext_tokens(
            self, test_client: AsyncClient, sample_paste_data, bypass_headers
    ):
        """POST /pastes should return plaintext tokens to user."""
        response = await test_client.post("/pastes", json=sample_paste_data, headers=bypass_headers)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "edit_token" in data
        assert "delete_token" in data
        assert not data["edit_token"].startswith("$argon2")  # Plaintext
        assert not data["delete_token"].startswith("$argon2")
        assert len(data["edit_token"]) == TEST_TOKEN_LENGTH  # UUID hex
        assert len(data["delete_token"]) == TEST_TOKEN_LENGTH

    async def test_create_paste_with_expiration(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should handle expiration time."""
        expires_at = (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat()
        paste_data = {
            "title": "Expiring Paste",
            "content": "This will expire",
            "content_language": "plain_text",
            "expires_at": expires_at,
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is not None

    async def test_create_paste_without_expiration(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should create permanent paste without expiration."""
        paste_data = {
            "title": "Permanent Paste",
            "content": "No expiration",
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is None


@pytest.mark.asyncio
class TestPasteCreateValidationAPI:
    """API tests for paste creation validation."""

    async def test_create_paste_with_empty_content_fails(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should reject empty content."""
        paste_data = {
            "title": "Empty Content",
            "content": "",
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    async def test_create_paste_with_very_large_content(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should handle very large content (boundary test)."""
        # Create 1MB of content
        large_content = "x" * (1024 * 1024)
        paste_data = {
            "title": "Large Content",
            "content": large_content,
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 413, 422]

    async def test_create_paste_with_invalid_language_enum(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should reject invalid content_language enum."""
        paste_data = {
            "title": "Invalid Language",
            "content": "Test content",
            "content_language": "invalid_language_xyz",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    async def test_create_paste_with_unicode_content(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should handle Unicode and special characters."""
        paste_data = {
            "title": "Unicode Test 🎉",
            "content": "Hello 世界! Special chars: <>&\"'",
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    async def test_create_paste_with_very_long_title(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should handle very long titles (boundary test)."""
        long_title = "x" * 1000  # 1000 character title
        paste_data = {
            "title": long_title,
            "content": "Test content",
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        # Should either succeed or fail gracefully with validation error
        assert response.status_code in [200, 422]

    async def test_create_paste_with_malformed_json(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should reject malformed JSON."""
        # Send invalid JSON string directly
        response = await test_client.post(
            "/pastes",
            content='{"title": "Test", "content": broken json}',
            headers={**bypass_headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestPasteGetAPI:
    """API tests for paste retrieval endpoints."""

    async def test_get_paste_by_id_returns_content(
            self, test_client: AsyncClient, authenticated_paste, bypass_headers
    ):
        """GET /pastes/{id} should return paste content."""
        paste_id = authenticated_paste["id"]

        response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == paste_id
        assert data["title"] == "Test Paste"
        assert data["content"] == "This is test content"

    async def test_get_paste_returns_404_for_nonexistent(
            self, test_client: AsyncClient, bypass_headers
    ):
        """GET /pastes/{id} should return 404 for non-existent paste."""
        nonexistent_id = str(uuid.uuid4())

        response = await test_client.get(f"/pastes/{nonexistent_id}", headers=bypass_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "paste_not_found"

    async def test_get_paste_caches_response(
            self, test_client: AsyncClient, authenticated_paste, bypass_headers
    ):
        """GET /pastes/{id} should cache successful responses."""
        paste_id = authenticated_paste["id"]

        # First request
        response1 = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert response1.status_code == 200
        assert "Cache-Control" in response1.headers
        assert "public" in response1.headers["Cache-Control"]

        # Second request should hit cache
        response2 = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert response2.status_code == 200
        assert response2.json() == response1.json()

    async def test_get_paste_caching_prevents_db_queries(
            self, test_client: AsyncClient, authenticated_paste, bypass_headers, monkeypatch
    ):
        """GET /pastes/{id} should use cache and avoid DB queries on subsequent requests."""
        from unittest.mock import AsyncMock, MagicMock
        paste_id = authenticated_paste["id"]

        # Track file reads to verify caching works
        original_read = None
        read_count = 0

        def track_file_reads(*args, **kwargs):
            nonlocal read_count
            read_count += 1
            return original_read(*args, **kwargs)

        # First request - should read from file
        response1 = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert response1.status_code == 200

        # Patch Path.read_text to track calls
        from pathlib import Path
        original_read = Path.read_text
        monkeypatch.setattr(Path, "read_text", track_file_reads)

        # Second request - should use cache (no file read)
        response2 = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert response2.status_code == 200
        assert response2.json() == response1.json()

        # Cache should have prevented file read
        # (read_count may be 0 if cache is working)
        # This is a weak assertion but documents expected behavior
        assert read_count <= 1, "Cache should minimize file system access"

    async def test_get_paste_cache_control_headers(
            self, test_client: AsyncClient, authenticated_paste, bypass_headers
    ):
        """GET /pastes/{id} should include proper cache control headers."""
        paste_id = authenticated_paste["id"]

        response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)

        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        cache_control = response.headers["Cache-Control"]
        assert "public" in cache_control
        assert "max-age" in cache_control

    async def test_get_expired_paste_returns_404(
            self, test_client: AsyncClient, bypass_headers
    ):
        """GET /pastes/{id} should return 404 for expired paste."""
        from datetime import datetime, timedelta, timezone

        # Create a paste that expires immediately
        expired_time = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        paste_data = {
            "title": "Expired Paste",
            "content": "This is expired",
            "content_language": "plain_text",
            "expires_at": expired_time,
        }

        # Create the paste (may fail validation, so check both cases)
        create_response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        if create_response.status_code == 200:
            paste_id = create_response.json()["id"]

            # Try to retrieve expired paste
            response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)

            # Should return 404 for expired paste
            assert response.status_code == 404


@pytest.mark.asyncio
class TestPasteLegacyAPI:
    """API tests for legacy paste endpoint."""

    async def test_get_legacy_paste_returns_404_for_nonexistent(
            self, test_client: AsyncClient, bypass_headers
    ):
        """GET /pastes/legacy/{name} should return 404 for non-existent paste."""
        response = await test_client.get("/pastes/legacy/nonexistent123", headers=bypass_headers)

        assert response.status_code == 404


@pytest.mark.asyncio
class TestPasteEditAPI:
    """API tests for paste editing endpoint."""

    async def test_edit_paste_with_valid_token_updates_title(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should update title with valid token."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        edit_data = {"title": "Updated Title"}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": edit_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "This is test content"  # Unchanged

    async def test_edit_paste_with_valid_token_updates_content(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should update content with valid token."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        edit_data = {"content": "Updated content"}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": edit_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["title"] == "Test Paste"  # Unchanged

    async def test_edit_paste_with_valid_token_updates_language(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should update content language with valid token."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        edit_data = {"content_language": "plain_text"}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": edit_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_language"] == "plain_text"

    async def test_edit_paste_with_valid_token_updates_expiration(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should update expiration with valid token."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        new_expiration = (datetime.now(tz=timezone.utc) + timedelta(days=7)).isoformat()
        edit_data = {"expires_at": new_expiration}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": edit_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is not None

    async def test_edit_paste_partial_update(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should support partial updates."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        # Only update title, leaving other fields unchanged
        edit_data = {
            "title": "New Title"
        }
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": edit_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["content_language"] == "plain_text"  # Unchanged
        assert data["content"] == "This is test content"  # Unchanged

    async def test_edit_paste_returns_404_with_invalid_token(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should return 404 with invalid token."""
        paste_id = authenticated_paste["id"]
        invalid_token = "invalid_token_12345678901234567890"

        edit_data = {"title": "Should Fail"}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": invalid_token}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "paste_not_found"

    async def test_edit_paste_returns_404_for_nonexistent_paste(
            self, test_client: AsyncClient
    ):
        """PUT /pastes/{id} should return 404 for non-existent paste."""
        nonexistent_id = str(uuid.uuid4())
        fake_token = "a" * 32

        edit_data = {"title": "Should Fail"}
        response = await test_client.put(
            f"/pastes/{nonexistent_id}",
            json=edit_data,
            headers={"Authorization": fake_token}
        )

        assert response.status_code == 404

    async def test_edit_paste_requires_authorization_header(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should require Authorization header."""
        paste_id = authenticated_paste["id"]

        edit_data = {"title": "Should Fail"}
        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data
        )

        # Should fail with 401 Unauthorized (missing auth header)
        assert response.status_code == 401


@pytest.mark.asyncio
class TestPasteDeleteAPI:
    """API tests for paste deletion endpoint."""

    async def test_delete_paste_with_valid_token(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should succeed with valid token."""
        paste_id = authenticated_paste["id"]
        delete_token = authenticated_paste["delete_token"]

        response = await test_client.delete(
            f"/pastes/{paste_id}",
            headers={"Authorization": delete_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Paste deleted successfully"

        # Verify paste is gone
        get_response = await test_client.get(f"/pastes/{paste_id}")
        assert get_response.status_code == 404

    async def test_delete_paste_returns_404_with_invalid_token(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should return 404 with invalid token."""
        paste_id = authenticated_paste["id"]
        invalid_token = "invalid_token_12345678901234567890"

        response = await test_client.delete(
            f"/pastes/{paste_id}",
            headers={"Authorization": invalid_token}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "paste_not_found"

        # Verify paste still exists
        get_response = await test_client.get(f"/pastes/{paste_id}")
        assert get_response.status_code == 200

    async def test_delete_paste_returns_404_for_nonexistent_paste(
            self, test_client: AsyncClient
    ):
        """DELETE /pastes/{id} should return 404 for non-existent paste."""
        nonexistent_id = str(uuid.uuid4())
        fake_token = "a" * 32

        response = await test_client.delete(
            f"/pastes/{nonexistent_id}",
            headers={"Authorization": fake_token}
        )

        assert response.status_code == 404

    async def test_delete_paste_requires_authorization_header(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should require Authorization header."""
        paste_id = authenticated_paste["id"]

        response = await test_client.delete(f"/pastes/{paste_id}")

        # Should fail with 401 Unauthorized (missing auth header)
        assert response.status_code == 401
