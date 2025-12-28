"""
Contract test for Site Info API

TDD: These tests are written FIRST (RED phase).
They define the expected API contract for site information retrieval.

API Endpoint: GET /method/press.api.site.info
Expected by: Press dashboard, site management pages
"""

import pytest
import requests
from typing import Dict, Any


# Configuration
BASE_URL = "http://localhost:32300"


class TestSiteInfoAPIContract:
    """
    Contract tests for the site info retrieval API.

    These tests verify the API contract that Press dashboard
    and external integrations depend on.
    """

    @pytest.fixture
    def api_url(self) -> str:
        """Return the full API URL for site info."""
        return f"{BASE_URL}/api/method/press.api.site.info"

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Return authentication headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": "token api_key:api_secret",
        }

    def test_endpoint_exists(self, api_url: str):
        """
        Verify the site info endpoint exists.

        Contract: The endpoint must be accessible.
        """
        try:
            response = requests.get(
                api_url,
                timeout=10,
            )
            assert response.status_code != 404, (
                f"Site info endpoint not found at {api_url}"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_returns_json_content_type(self, api_url: str):
        """
        Verify response content type is JSON.

        Contract: All API responses must be JSON.
        """
        try:
            response = requests.get(
                api_url,
                params={"name": "test-site"},
                timeout=10,
            )

            content_type = response.headers.get("Content-Type", "")
            assert "application/json" in content_type, (
                f"Expected JSON content type, got: {content_type}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_info_response_schema(self, api_url: str, auth_headers: Dict[str, str]):
        """
        Verify site info response follows expected schema.

        Contract: Response must include essential site metadata.
        """
        try:
            response = requests.get(
                api_url,
                params={"name": "press.platform.local"},
                headers=auth_headers,
                timeout=10,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Auth required for schema test")

            if response.status_code in [404, 417]:
                pytest.skip("Site not found - expected in clean environment")

            if response.status_code == 200:
                data = response.json()

                # Frappe API structure
                assert "message" in data, "Response must have 'message' key"

                message = data["message"]
                if isinstance(message, dict):
                    # Essential fields for site info
                    essential_fields = ["name"]
                    for field in essential_fields:
                        assert field in message, (
                            f"Site info missing essential field: {field}"
                        )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_site_status_values(self, api_url: str, auth_headers: Dict[str, str]):
        """
        Verify site status follows expected enum values.

        Contract: Status must be one of defined values.
        """
        valid_statuses = {
            "Pending",
            "Installing",
            "Active",
            "Inactive",
            "Suspended",
            "Broken",
            "Archived",
        }

        try:
            response = requests.get(
                api_url,
                params={"name": "press.platform.local"},
                headers=auth_headers,
                timeout=10,
            )

            if response.status_code not in [200]:
                pytest.skip("Site not available for status check")

            data = response.json()
            message = data.get("message", {})

            if isinstance(message, dict) and "status" in message:
                status = message["status"]
                assert status in valid_statuses, (
                    f"Invalid site status: {status}. "
                    f"Expected one of: {valid_statuses}"
                )

        except requests.ConnectionError:
            pytest.skip("Press service not running")


class TestSiteListAPIContract:
    """
    Contract tests for the site list API.

    These tests verify the API contract for listing all sites.
    """

    @pytest.fixture
    def api_url(self) -> str:
        """Return the site list API URL."""
        return f"{BASE_URL}/api/method/press.api.site.all"

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Return authentication headers."""
        return {
            "Authorization": "token api_key:api_secret",
        }

    def test_endpoint_exists(self, api_url: str):
        """
        Verify the site list endpoint exists.
        """
        try:
            response = requests.get(api_url, timeout=10)
            assert response.status_code != 404, (
                "Site list endpoint not found"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_returns_list_structure(self, api_url: str, auth_headers: Dict[str, str]):
        """
        Verify response is a list structure.

        Contract: Response message must be a list of sites.
        """
        try:
            response = requests.get(
                api_url,
                headers=auth_headers,
                timeout=10,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Auth required for list test")

            if response.status_code == 200:
                data = response.json()
                message = data.get("message")

                # Message should be a list (possibly empty)
                assert isinstance(message, list), (
                    f"Expected list, got {type(message)}"
                )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_list_items_have_required_fields(
        self,
        api_url: str,
        auth_headers: Dict[str, str],
    ):
        """
        Verify each site in list has required fields.

        Contract: Each site object must have minimum fields.
        """
        try:
            response = requests.get(
                api_url,
                headers=auth_headers,
                timeout=10,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Auth required for list test")

            if response.status_code == 200:
                data = response.json()
                sites = data.get("message", [])

                if sites:
                    required_fields = ["name", "status"]
                    for site in sites:
                        for field in required_fields:
                            assert field in site, (
                                f"Site missing required field: {field}"
                            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_pagination_support(self, api_url: str, auth_headers: Dict[str, str]):
        """
        Verify pagination parameters are accepted.

        Contract: API should accept limit_start and limit_page_length.
        """
        try:
            response = requests.get(
                api_url,
                params={
                    "limit_start": 0,
                    "limit_page_length": 10,
                },
                headers=auth_headers,
                timeout=10,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Auth required for pagination test")

            # Should not error on pagination params
            assert response.status_code in [200, 417], (
                f"Pagination params caused error: {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")


class TestSiteOperationsAPIContract:
    """
    Contract tests for site operations (suspend, unsuspend, archive).
    """

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Return authentication headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": "token api_key:api_secret",
        }

    def test_suspend_endpoint_exists(self):
        """Verify suspend endpoint exists."""
        url = f"{BASE_URL}/api/method/press.api.site.suspend"
        try:
            response = requests.post(url, json={}, timeout=10)
            assert response.status_code != 404, "Suspend endpoint not found"
        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_unsuspend_endpoint_exists(self):
        """Verify unsuspend endpoint exists."""
        url = f"{BASE_URL}/api/method/press.api.site.unsuspend"
        try:
            response = requests.post(url, json={}, timeout=10)
            assert response.status_code != 404, "Unsuspend endpoint not found"
        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_archive_endpoint_exists(self):
        """Verify archive endpoint exists."""
        url = f"{BASE_URL}/api/method/press.api.site.archive"
        try:
            response = requests.post(url, json={}, timeout=10)
            assert response.status_code != 404, "Archive endpoint not found"
        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_operations_require_site_name(self, auth_headers: Dict[str, str]):
        """
        Verify all operations require site name.

        Contract: Operations without site name must fail.
        """
        endpoints = [
            "/api/method/press.api.site.suspend",
            "/api/method/press.api.site.unsuspend",
            "/api/method/press.api.site.archive",
        ]

        for endpoint in endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                response = requests.post(
                    url,
                    json={},  # No site name
                    headers=auth_headers,
                    timeout=10,
                )

                if response.status_code in [401, 403]:
                    continue  # Skip auth-required endpoints

                # Should fail without site name
                assert response.status_code in [400, 417] or (
                    "error" in str(response.json())
                ), f"Endpoint {endpoint} should require site name"

            except requests.ConnectionError:
                pytest.skip("Press service not running")
                break
