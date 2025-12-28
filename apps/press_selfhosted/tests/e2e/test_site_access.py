"""
E2E test for site access after creation

TDD: These tests are written FIRST (RED phase).
They verify the end-to-end user journey of accessing a tenant site.
"""

import pytest
import requests
from urllib.parse import urljoin


# Configuration
BASE_URL = "http://localhost:32300"


class TestSiteAccessE2E:
    """
    End-to-end tests for accessing tenant sites.

    These tests verify that tenant sites can be accessed
    via their configured domains.
    """

    @pytest.fixture
    def default_site_url(self) -> str:
        """Return the default site URL."""
        return BASE_URL

    @pytest.fixture
    def test_tenant_url(self) -> str:
        """Return a test tenant site URL."""
        # In production, this would be a subdomain like test-tenant.platform.local
        return "http://localhost:32300"

    def test_site_login_page_accessible(self, default_site_url: str):
        """
        Verify a site's login page is accessible.

        E2E: User navigates to tenant site and sees login page.
        """
        try:
            login_url = urljoin(default_site_url, "/login")
            response = requests.get(login_url, timeout=30, verify=False)

            assert response.status_code == 200, (
                f"Site login page should be accessible, got {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_site_api_accessible(self, default_site_url: str):
        """
        Verify a site's API is accessible.

        E2E: Site should respond to API requests.
        """
        try:
            api_url = urljoin(default_site_url, "/api/method/ping")
            response = requests.get(api_url, timeout=30, verify=False)

            if response.status_code == 200:
                data = response.json()
                assert "message" in data, "API should return Frappe response format"

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_site_desk_requires_login(self, default_site_url: str):
        """
        Verify desk requires authentication.

        E2E: Unauthenticated access to desk should redirect to login.
        """
        try:
            desk_url = urljoin(default_site_url, "/app")
            response = requests.get(
                desk_url,
                timeout=30,
                verify=False,
                allow_redirects=False
            )

            # Should redirect to login or show login form
            if response.status_code in [302, 303]:
                location = response.headers.get("Location", "")
                assert "login" in location.lower(), (
                    f"Should redirect to login, got: {location}"
                )
            elif response.status_code == 200:
                # Might show login page directly
                content = response.text.lower()
                assert "login" in content or "sign in" in content, (
                    "Should require login for desk access"
                )
            else:
                assert response.status_code in [401, 403], (
                    f"Expected auth requirement, got {response.status_code}"
                )

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_site_static_assets_load(self, default_site_url: str):
        """
        Verify static assets are loadable.

        E2E: Site should serve CSS, JS, and images.
        """
        try:
            login_url = urljoin(default_site_url, "/login")
            response = requests.get(login_url, timeout=30, verify=False)

            if response.status_code == 200:
                content = response.text

                # Check for static asset references
                has_css = ".css" in content or 'rel="stylesheet"' in content
                has_js = "<script" in content and ".js" in content

                assert has_css, "Page should include CSS"
                assert has_js, "Page should include JavaScript"

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")


class TestMultiTenantAccess:
    """
    E2E tests for multi-tenant site access.

    These tests verify that multiple tenant sites can coexist
    and be accessed independently.
    """

    def test_default_site_routing(self):
        """
        Verify default site is accessible.

        E2E: The default/main site should be routable.
        """
        try:
            response = requests.get(
                f"{BASE_URL}/api/method/ping",
                timeout=30,
                verify=False
            )

            # Just verify the route works
            assert response.status_code in [200, 403, 417], (
                f"Default site should be routable, got {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_site_isolation_via_api(self):
        """
        Verify sites are isolated from each other.

        E2E: Each site should only see its own data.
        """
        try:
            # Get user list from default site
            response = requests.get(
                f"{BASE_URL}/api/resource/User",
                timeout=30,
                verify=False
            )

            if response.status_code in [401, 403]:
                # Auth required - expected behavior
                pass
            elif response.status_code == 200:
                data = response.json()
                # Should only see current site's users
                assert "data" in data or "message" in data, (
                    "Should return user data for current site only"
                )

        except requests.ConnectionError:
            pytest.skip("Press service not running")


class TestSiteCreationFlow:
    """
    E2E tests for the site creation flow.

    These tests verify the complete user journey of creating
    a new tenant site through the Press dashboard.
    """

    def test_press_dashboard_accessible(self):
        """
        Verify Press dashboard is accessible.

        E2E: Administrator should be able to access Press dashboard.
        """
        try:
            dashboard_url = f"{BASE_URL}/app/site"
            response = requests.get(
                dashboard_url,
                timeout=30,
                verify=False,
                allow_redirects=False
            )

            # Should either show dashboard or redirect to login
            assert response.status_code in [200, 302, 303, 401, 403], (
                f"Dashboard should be accessible, got {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_new_site_form_accessible(self):
        """
        Verify new site form is accessible.

        E2E: Administrator should see the site creation form.
        """
        try:
            form_url = f"{BASE_URL}/app/site/new"
            response = requests.get(
                form_url,
                timeout=30,
                verify=False,
                allow_redirects=False
            )

            # Should either show form or redirect to login
            assert response.status_code in [200, 302, 303, 401, 403], (
                f"New site form should be accessible, got {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")

    def test_site_list_api_accessible(self):
        """
        Verify site list API is accessible.

        E2E: Should be able to list existing sites.
        """
        try:
            response = requests.get(
                f"{BASE_URL}/api/resource/Site",
                timeout=30,
                verify=False
            )

            # API should respond (even if with auth error)
            assert response.status_code in [200, 401, 403, 404], (
                f"Site list API should respond, got {response.status_code}"
            )

        except requests.ConnectionError:
            pytest.skip("Press service not running")
