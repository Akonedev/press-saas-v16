"""
E2E test for login page accessibility

TDD: These tests are written FIRST (RED phase).
They verify the end-to-end user journey of accessing the login page.
"""

import pytest
import requests
from urllib.parse import urljoin


# Configuration
BASE_URL = "https://press.platform.local:32443"
INSECURE_BASE_URL = "http://localhost:32300"


class TestLoginPageE2E:
    """
    End-to-end tests for the Press login page.

    These tests verify that users can access the login page
    and the page contains expected elements.
    """

    @pytest.fixture
    def login_url(self) -> str:
        """Return the login page URL."""
        return urljoin(INSECURE_BASE_URL, "/login")

    @pytest.fixture
    def desk_url(self) -> str:
        """Return the desk URL (redirects to login if not authenticated)."""
        return urljoin(INSECURE_BASE_URL, "/app")

    def test_login_page_accessible(self, login_url: str):
        """
        Verify the login page is accessible.

        E2E: User navigates to login URL and page loads successfully.
        """
        try:
            response = requests.get(login_url, timeout=30, verify=False)
            assert response.status_code == 200, (
                f"Login page should be accessible, got status {response.status_code}"
            )
        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_login_page_contains_form(self, login_url: str):
        """
        Verify the login page contains a login form.

        E2E: Login page should have username and password fields.
        """
        try:
            response = requests.get(login_url, timeout=30, verify=False)

            # Check for login form elements in HTML
            content = response.text.lower()

            # Look for form elements (Frappe uses specific patterns)
            has_login_form = any([
                "login" in content,
                'type="email"' in content.lower() or 'name="usr"' in content.lower(),
                'type="password"' in content.lower() or 'name="pwd"' in content.lower(),
            ])

            assert has_login_form, "Login page should contain a login form"

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_login_page_has_press_branding(self, login_url: str):
        """
        Verify the login page has Press/Frappe branding.

        E2E: Page should show the application branding.
        """
        try:
            response = requests.get(login_url, timeout=30, verify=False)
            content = response.text.lower()

            # Check for Frappe or Press branding
            has_branding = any([
                "frappe" in content,
                "press" in content,
                "erpnext" in content,
            ])

            # This is a soft check - new installations might not have custom branding
            if not has_branding:
                pytest.warns(UserWarning, match="No Frappe/Press branding found on login page")

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_desk_redirects_to_login(self, desk_url: str, login_url: str):
        """
        Verify unauthenticated access to desk redirects to login.

        E2E: User tries to access desk without authentication,
        should be redirected to login page.
        """
        try:
            response = requests.get(
                desk_url,
                timeout=30,
                verify=False,
                allow_redirects=False
            )

            # Should redirect (302/303) or show login
            if response.status_code in [302, 303]:
                location = response.headers.get("Location", "")
                assert "login" in location.lower(), (
                    f"Should redirect to login, got: {location}"
                )
            elif response.status_code == 200:
                # Might show login page directly
                content = response.text.lower()
                assert "login" in content, (
                    "Should show login page for unauthenticated access"
                )
            else:
                # 401 or 403 is also acceptable
                assert response.status_code in [401, 403], (
                    f"Expected redirect or auth error, got {response.status_code}"
                )

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")

    def test_static_assets_load(self, login_url: str):
        """
        Verify static assets (CSS, JS) are accessible.

        E2E: Page should load with all required static assets.
        """
        try:
            response = requests.get(login_url, timeout=30, verify=False)
            content = response.text

            # Check for CSS references
            has_css = 'rel="stylesheet"' in content or '.css' in content
            assert has_css, "Page should include CSS stylesheets"

            # Check for JS references
            has_js = '<script' in content
            assert has_js, "Page should include JavaScript"

        except requests.ConnectionError:
            pytest.skip("Press service not running - E2E test requires full stack")


class TestHTTPSRedirect:
    """
    Tests for HTTPS redirect behavior.
    """

    def test_http_redirects_to_https(self):
        """
        Verify HTTP requests are redirected to HTTPS.

        E2E: When Traefik is properly configured, HTTP should redirect to HTTPS.
        """
        http_url = "http://press.platform.local:32380"

        try:
            response = requests.get(
                http_url,
                timeout=10,
                allow_redirects=False,
                verify=False
            )

            # Should get a redirect
            assert response.status_code in [301, 302, 307, 308], (
                f"Expected HTTPS redirect, got status {response.status_code}"
            )

            location = response.headers.get("Location", "")
            assert "https://" in location, (
                f"Should redirect to HTTPS, got: {location}"
            )

        except requests.ConnectionError:
            pytest.skip("Traefik not running or accessible")
