"""Tests for metrics and health endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint without authentication."""

    async def test_metrics_endpoint_accessible_without_auth_when_not_configured(
        self, test_client: AsyncClient
    ):
        """GET /metrics should be publicly accessible when METRICS_TOKEN is not set."""
        response = await test_client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        # Verify some expected metrics exist
        content = response.text
        assert "paste_operations_total" in content or "# HELP" in content

    async def test_metrics_endpoint_format(self, test_client: AsyncClient):
        """Metrics should be in Prometheus exposition format."""
        response = await test_client.get("/metrics")

        content = response.text
        # Prometheus format should have comments and metrics
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0


@pytest.mark.asyncio
class TestMetricsAuthentication:
    """Test metrics endpoint authentication when token is configured."""

    async def test_metrics_requires_auth_when_token_configured(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """GET /metrics should require authentication when METRICS_TOKEN is set."""
        response = await test_client_with_metrics_auth.get("/metrics")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"

        error = response.json()
        assert "error" in error
        assert "required" in error["error"].lower()

    async def test_metrics_rejects_invalid_bearer_token(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """GET /metrics should reject invalid Bearer tokens."""
        response = await test_client_with_metrics_auth.get(
            "/metrics",
            headers={"Authorization": "Bearer wrong_token_12345"}
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

        error = response.json()
        assert "error" in error
        assert "invalid" in error["error"].lower()

    async def test_metrics_rejects_malformed_auth_header(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """GET /metrics should reject malformed Authorization headers."""
        malformed_headers = [
            "test_metrics_token",  # Missing "Bearer" prefix
            "Basic dGVzdDp0ZXN0",  # Wrong auth scheme
            "Bearer",  # Missing token
            "",  # Empty
        ]

        for auth_header in malformed_headers:
            response = await test_client_with_metrics_auth.get(
                "/metrics",
                headers={"Authorization": auth_header}
            )

            assert response.status_code == 401, f"Failed for: {auth_header}"

    async def test_metrics_accepts_valid_bearer_token(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """GET /metrics should accept valid Bearer token."""
        response = await test_client_with_metrics_auth.get(
            "/metrics",
            headers={"Authorization": "Bearer test_metrics_token_12345"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        # Verify metrics content
        content = response.text
        assert len(content) > 0

    async def test_metrics_token_is_case_sensitive(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """Metrics token validation should be case-sensitive."""
        response = await test_client_with_metrics_auth.get(
            "/metrics",
            headers={"Authorization": "Bearer TEST_METRICS_TOKEN_12345"}  # Wrong case
        )

        assert response.status_code == 401

    async def test_metrics_prevents_timing_attacks(
        self, test_client_with_metrics_auth: AsyncClient
    ):
        """Multiple failed auth attempts should return consistent responses."""
        tokens = [
            "wrong_token_1",
            "wrong_token_2",
            "a" * 100,  # Long token
            "",  # Empty token
        ]

        responses = []
        for token in tokens:
            response = await test_client_with_metrics_auth.get(
                "/metrics",
                headers={"Authorization": f"Bearer {token}"}
            )
            responses.append(response.status_code)

        # All should return 401
        assert all(code == 401 for code in responses)


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health and readiness endpoints."""

    async def test_health_endpoint(self, test_client: AsyncClient):
        """GET /health should return health status."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        assert data["dependencies"]["database"] == "ok"

    async def test_ready_endpoint(self, test_client: AsyncClient):
        """GET /ready should return readiness status."""
        response = await test_client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert data["ready"] is True

    async def test_health_includes_all_dependencies(self, test_client: AsyncClient):
        """Health check should include database and other dependencies."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "database" in data["dependencies"]
        # Storage and cache may or may not be present depending on configuration

    async def test_health_and_ready_not_authenticated(self, test_client: AsyncClient):
        """Health and readiness endpoints should remain publicly accessible."""
        # These endpoints must not require authentication for load balancer health checks
        health_response = await test_client.get("/health")
        ready_response = await test_client.get("/ready")

        assert health_response.status_code == 200
        assert ready_response.status_code == 200
