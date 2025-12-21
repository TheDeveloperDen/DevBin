"""API tests for paste endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPasteCreationAPI:
    """API tests for paste creation endpoint."""

    async def test_create_paste_returns_plaintext_tokens(
            self, test_client: AsyncClient, sample_paste_data
    ):
        """POST /pastes should return plaintext tokens to user."""
        response = await test_client.post("/pastes", json=sample_paste_data)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "edit_token" in data
        assert "delete_token" in data
        assert not data["edit_token"].startswith("$argon2")  # Plaintext
        assert not data["delete_token"].startswith("$argon2")
        assert len(data["edit_token"]) == 32  # UUID hex
        assert len(data["delete_token"]) == 32

    async def test_get_paste_by_id_returns_content(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """GET /pastes/{id} should return paste content."""
        paste_id = authenticated_paste["id"]

        response = await test_client.get(f"/pastes/{paste_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == paste_id
        assert data["title"] == "Test Paste"
        assert data["content"] == "This is test content"
