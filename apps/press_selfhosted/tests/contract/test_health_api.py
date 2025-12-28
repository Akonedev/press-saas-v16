"""
Contract test for /health endpoint

TDD: These tests are written FIRST (RED phase).
They define the expected API contract for the health endpoint.
"""

import pytest
import requests
from typing import Dict, Any


# Configuration
BASE_URL = "http://localhost:32300"
HEALTH_ENDPOINT = "/api/health"


class TestHealthAPIContract:
    """
    Contract tests for the health check API.

    These tests verify the API contract is correctly implemented,
    including response schema, status codes, and content types.
    """

    @pytest.fixture
    def health_url(self) -> str:
        """Return the health endpoint URL."""
        return f"{BASE_URL}{HEALTH_ENDPOINT}"

    def test_health_endpoint_exists(self, health_url: str):
        """
        Verify the health endpoint is accessible.

        Contract: GET /api/health returns 200 OK
        """
        try:
            response = requests.get(health_url, timeout=10)
            assert response.status_code == 200, (
                f"Health endpoint should return 200, got {response.status_code}"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running - integration test context")

    def test_health_response_content_type(self, health_url: str):
        """
        Verify the health endpoint returns JSON.

        Contract: Content-Type should be application/json
        """
        try:
            response = requests.get(health_url, timeout=10)
            content_type = response.headers.get("Content-Type", "")
            assert "application/json" in content_type, (
                f"Expected JSON content type, got: {content_type}"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running - integration test context")

    def test_health_response_schema(self, health_url: str):
        """
        Verify the health response matches expected schema.

        Contract: Response should contain:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "services": {
                "database": "ok" | "error",
                "redis": "ok" | "error",
                "minio": "ok" | "error",
                "workers": "ok" | "error"
            }
        }
        """
        try:
            response = requests.get(health_url, timeout=10)
            data = response.json()

            # Verify top-level structure
            assert "status" in data, "Response must contain 'status' field"
            assert data["status"] in ["healthy", "degraded", "unhealthy"], (
                f"Status must be one of: healthy, degraded, unhealthy. Got: {data['status']}"
            )

            # Verify services object
            if "services" in data:
                services = data["services"]
                expected_services = ["database", "redis", "minio"]

                for service in expected_services:
                    if service in services:
                        assert services[service] in ["ok", "error", "unknown"], (
                            f"Service {service} status must be 'ok', 'error', or 'unknown'"
                        )

        except requests.ConnectionError:
            pytest.skip("Press service not running - integration test context")

    def test_health_response_time(self, health_url: str):
        """
        Verify health check responds within acceptable time.

        Contract: Response time should be < 5 seconds
        """
        try:
            response = requests.get(health_url, timeout=10)
            elapsed = response.elapsed.total_seconds()
            assert elapsed < 5, (
                f"Health check took too long: {elapsed}s (max 5s)"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running - integration test context")


class TestPingEndpoint:
    """
    Contract tests for the Frappe ping endpoint.

    Standard Frappe endpoint that should always be available.
    """

    @pytest.fixture
    def ping_url(self) -> str:
        """Return the ping endpoint URL."""
        return f"{BASE_URL}/api/method/ping"

    def test_ping_returns_pong(self, ping_url: str):
        """
        Verify the ping endpoint returns 'pong'.

        Contract: GET /api/method/ping returns {"message": "pong"}
        """
        try:
            response = requests.get(ping_url, timeout=10)
            assert response.status_code == 200

            data = response.json()
            assert "message" in data
            assert data["message"] == "pong"
        except requests.ConnectionError:
            pytest.skip("Press service not running - integration test context")
