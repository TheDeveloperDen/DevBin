"""API tests for paste endpoints."""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


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
        assert len(data["edit_token"]) == 32  # UUID hex
        assert len(data["delete_token"]) == 32

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
        import uuid
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
        import uuid
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
        import uuid
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
