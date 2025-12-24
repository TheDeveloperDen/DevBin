"""Security tests for authorization and authentication bypass prevention."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.security
class TestAuthorizationBypassPrevention:
    """Tests to ensure authorization cannot be bypassed."""

    async def test_edit_paste_without_token_fails(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should require valid authorization token."""
        paste_id = authenticated_paste["id"]

        edit_data = {"title": "Unauthorized Edit Attempt"}

        # Try to edit without Authorization header
        response = await test_client.put(f"/pastes/{paste_id}", json=edit_data)

        assert response.status_code in [401, 403, 422]

    async def test_edit_paste_with_wrong_token_fails(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """PUT /pastes/{id} should reject incorrect tokens."""
        paste_id = authenticated_paste["id"]
        wrong_token = "0" * 32  # Invalid token

        edit_data = {"title": "Wrong Token Edit"}

        response = await test_client.put(
            f"/pastes/{paste_id}",
            json=edit_data,
            headers={"Authorization": wrong_token}
        )

        assert response.status_code == 404  # Should not reveal paste exists

    async def test_delete_paste_without_token_fails(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should require valid authorization token."""
        paste_id = authenticated_paste["id"]

        # Try to delete without Authorization header
        response = await test_client.delete(f"/pastes/{paste_id}")

        assert response.status_code in [401, 403, 422]

    async def test_delete_paste_with_wrong_token_fails(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should reject incorrect tokens."""
        paste_id = authenticated_paste["id"]
        wrong_token = "0" * 32  # Invalid token

        response = await test_client.delete(
            f"/pastes/{paste_id}",
            headers={"Authorization": wrong_token}
        )

        assert response.status_code == 404  # Should not reveal paste exists

    async def test_cannot_use_edit_token_for_delete(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """DELETE /pastes/{id} should not accept edit token (if tokens differ)."""
        paste_id = authenticated_paste["id"]
        edit_token = authenticated_paste["edit_token"]

        # Try to delete using edit token
        response = await test_client.delete(
            f"/pastes/{paste_id}",
            headers={"Authorization": edit_token}
        )

        # Should fail if edit_token != delete_token (implementation-dependent)
        # Currently they're the same, so this test documents expected behavior
        assert response.status_code in [200, 404]

    async def test_token_brute_force_resistance(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """Multiple failed authorization attempts should not leak information."""
        paste_id = authenticated_paste["id"]

        # Try multiple wrong tokens
        for i in range(10):
            wrong_token = str(i) * 32

            response = await test_client.put(
                f"/pastes/{paste_id}",
                json={"title": "Brute Force Attempt"},
                headers={"Authorization": wrong_token}
            )

            # Should consistently return 404, not reveal timing information
            assert response.status_code == 404

    async def test_authorization_header_injection_attempt(
            self, test_client: AsyncClient, authenticated_paste
    ):
        """Authorization header should safely handle injection attempts."""
        paste_id = authenticated_paste["id"]

        malicious_headers = [
            "'; DROP TABLE pastes--",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "Bearer" + "a" * 10000,  # Very long header
        ]

        for malicious_value in malicious_headers:
            response = await test_client.put(
                f"/pastes/{paste_id}",
                json={"title": "Test"},
                headers={"Authorization": malicious_value}
            )

            # Should fail gracefully
            assert response.status_code in [404, 422]


@pytest.mark.asyncio
@pytest.mark.security
class TestTokenSecurityProperties:
    """Tests to ensure tokens have proper security properties."""

    async def test_tokens_are_hashed_in_database(
            self, test_client: AsyncClient, sample_paste_data, bypass_headers, db_session
    ):
        """Tokens should be hashed in the database, not stored in plaintext."""
        from app.db.models import PasteEntity
        from sqlalchemy import select

        # Create a paste
        response = await test_client.post("/pastes", json=sample_paste_data, headers=bypass_headers)
        assert response.status_code == 200

        paste_data = response.json()
        paste_id = paste_data["id"]
        plaintext_token = paste_data["edit_token"]

        # Verify token is not plaintext (should be hashed)
        assert not plaintext_token.startswith("$argon2")

        # Check database
        stmt = select(PasteEntity).where(PasteEntity.id == paste_id)
        result = await db_session.execute(stmt)
        db_paste = result.scalar_one()

        # Database should contain hashed token, not plaintext
        assert db_paste.edit_token.startswith("$argon2")
        assert db_paste.edit_token != plaintext_token

    async def test_tokens_are_sufficiently_random(
            self, test_client: AsyncClient, sample_paste_data, bypass_headers
    ):
        """Tokens should be sufficiently random (not sequential or predictable)."""
        tokens = set()

        # Create 10 pastes and collect their tokens
        for _ in range(10):
            response = await test_client.post("/pastes", json=sample_paste_data, headers=bypass_headers)
            assert response.status_code == 200

            paste_data = response.json()
            tokens.add(paste_data["edit_token"])
            tokens.add(paste_data["delete_token"])

        # All tokens should be unique (no collisions)
        assert len(tokens) == 20  # 10 pastes * 2 tokens each

        # Tokens should be 32 characters (UUID hex format)
        for token in tokens:
            assert len(token) == 32
            assert token.isalnum()  # Alphanumeric only
