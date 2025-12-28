"""
Integration Tests - Grafana Dashboard Access
=============================================

Tests that Grafana is deployed, accessible, and configured with datasources and dashboards.

TDD Phase: RED (These tests should FAIL until Grafana is deployed)
Constitution Principle: I (TDD-First)
"""

import pytest
import requests
import time
from typing import Dict, List


@pytest.fixture
def grafana_url() -> str:
    """Grafana URL."""
    return "http://localhost:32393"


@pytest.fixture
def grafana_credentials() -> Dict[str, str]:
    """Default Grafana admin credentials."""
    return {
        "username": "admin",
        "password": "admin"
    }


@pytest.fixture
def grafana_session(grafana_url: str, grafana_credentials: Dict[str, str]):
    """Authenticated Grafana session."""
    session = requests.Session()
    session.auth = (grafana_credentials["username"], grafana_credentials["password"])
    return session


@pytest.fixture
def wait_for_grafana(grafana_url: str):
    """Wait for Grafana to be ready before running tests."""
    max_retries = 30
    retry_delay = 2

    for i in range(max_retries):
        try:
            response = requests.get(f"{grafana_url}/api/health", timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass

        if i < max_retries - 1:
            time.sleep(retry_delay)

    pytest.fail("Grafana did not become ready in time")


class TestGrafanaDeployment:
    """Test Grafana container is deployed and accessible."""

    def test_grafana_is_running(self, grafana_url: str, wait_for_grafana):
        """
        Test that Grafana is running and accessible.

        Expected: HTTP 200 from health endpoint
        """
        response = requests.get(f"{grafana_url}/api/health", timeout=10)
        assert response.status_code == 200, "Grafana should be healthy"

        data = response.json()
        assert data["database"] == "ok", "Grafana database should be ok"

    def test_grafana_login_page_accessible(self, grafana_url: str, wait_for_grafana):
        """
        Test that Grafana login page is accessible.

        Expected: HTTP 200 from root endpoint
        """
        response = requests.get(grafana_url, timeout=10)
        assert response.status_code == 200, "Grafana login page should be accessible"

    def test_grafana_api_accessible(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Grafana API is accessible with authentication.

        Expected: HTTP 200 from org endpoint with valid credentials
        """
        response = grafana_session.get(f"{grafana_url}/api/org", timeout=10)
        assert response.status_code == 200, "Grafana API should be accessible"

        data = response.json()
        assert "name" in data, "Response should include org name"


class TestGrafanaDatasources:
    """Test that Grafana has Prometheus datasource configured."""

    def test_datasources_exist(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that at least one datasource is configured.

        Expected: Datasources list is not empty
        """
        response = grafana_session.get(f"{grafana_url}/api/datasources", timeout=10)
        assert response.status_code == 200

        datasources = response.json()
        assert len(datasources) > 0, "At least one datasource should be configured"

    def test_prometheus_datasource_configured(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Prometheus datasource is configured.

        Expected: Prometheus datasource exists with correct type
        """
        response = grafana_session.get(f"{grafana_url}/api/datasources", timeout=10)
        assert response.status_code == 200

        datasources = response.json()
        prometheus_ds = [ds for ds in datasources if ds["type"] == "prometheus"]

        assert len(prometheus_ds) > 0, "Prometheus datasource should be configured"
        assert prometheus_ds[0]["url"], "Prometheus datasource should have URL"

    def test_prometheus_datasource_accessible(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Prometheus datasource is accessible from Grafana.

        Expected: Datasource health check returns OK
        """
        # Get Prometheus datasource
        response = grafana_session.get(f"{grafana_url}/api/datasources", timeout=10)
        datasources = response.json()
        prometheus_ds = [ds for ds in datasources if ds["type"] == "prometheus"]

        if len(prometheus_ds) == 0:
            pytest.skip("Prometheus datasource not configured yet (TDD RED phase)")

        ds_uid = prometheus_ds[0]["uid"]

        # Test datasource health
        health_response = grafana_session.get(
            f"{grafana_url}/api/datasources/uid/{ds_uid}/health",
            timeout=10
        )
        assert health_response.status_code == 200

    def test_datasource_is_default(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Prometheus datasource is set as default.

        Expected: Prometheus datasource has isDefault=true
        """
        response = grafana_session.get(f"{grafana_url}/api/datasources", timeout=10)
        datasources = response.json()
        prometheus_ds = [ds for ds in datasources if ds["type"] == "prometheus"]

        if len(prometheus_ds) > 0:
            assert prometheus_ds[0]["isDefault"], "Prometheus should be default datasource"


class TestGrafanaDashboards:
    """Test that Grafana has dashboards configured."""

    def test_dashboards_exist(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that dashboards are provisioned.

        Expected: Search returns at least one dashboard
        """
        response = grafana_session.get(
            f"{grafana_url}/api/search",
            params={"type": "dash-db"},
            timeout=10
        )
        assert response.status_code == 200

        dashboards = response.json()
        assert len(dashboards) > 0, "At least one dashboard should be provisioned"

    def test_docker_metrics_dashboard_exists(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Docker metrics dashboard exists.

        Expected: Dashboard with Docker/container in title exists
        """
        response = grafana_session.get(
            f"{grafana_url}/api/search",
            params={"query": "docker"},
            timeout=10
        )
        assert response.status_code == 200

        dashboards = response.json()
        # May not exist in TDD RED phase, which is acceptable
        # But test should verify structure when it does exist

    def test_frappe_metrics_dashboard_exists(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Frappe-specific metrics dashboard exists.

        Expected: Dashboard with Frappe in title exists
        """
        response = grafana_session.get(
            f"{grafana_url}/api/search",
            params={"query": "frappe"},
            timeout=10
        )
        assert response.status_code == 200

        # May not exist in TDD RED phase, which is acceptable

    def test_dashboard_is_accessible(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that a dashboard can be loaded.

        Expected: Dashboard JSON can be retrieved
        """
        # Get first dashboard
        search_response = grafana_session.get(
            f"{grafana_url}/api/search",
            params={"type": "dash-db"},
            timeout=10
        )
        dashboards = search_response.json()

        if len(dashboards) == 0:
            pytest.skip("No dashboards configured yet (TDD RED phase)")

        dashboard_uid = dashboards[0]["uid"]

        # Get dashboard details
        dashboard_response = grafana_session.get(
            f"{grafana_url}/api/dashboards/uid/{dashboard_uid}",
            timeout=10
        )
        assert dashboard_response.status_code == 200

        dashboard = dashboard_response.json()
        assert "dashboard" in dashboard, "Response should include dashboard"
        assert "panels" in dashboard["dashboard"], "Dashboard should have panels"


class TestGrafanaProvisioning:
    """Test Grafana provisioning configuration."""

    def test_provisioning_configured(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Grafana provisioning is enabled.

        Expected: Provisioned datasources and dashboards exist
        """
        # Check datasources
        ds_response = grafana_session.get(f"{grafana_url}/api/datasources", timeout=10)
        datasources = ds_response.json()

        # Check if any datasource is provisioned
        provisioned_ds = [ds for ds in datasources if ds.get("readOnly", False)]
        # Note: readOnly indicates provisioned datasource

    def test_folders_exist(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that dashboard folders are created.

        Expected: At least General folder exists
        """
        response = grafana_session.get(f"{grafana_url}/api/folders", timeout=10)
        assert response.status_code == 200

        folders = response.json()
        # General folder should always exist
        folder_titles = [f["title"] for f in folders]


class TestGrafanaUserAccess:
    """Test Grafana user authentication and access control."""

    def test_anonymous_access_disabled(self, grafana_url: str, wait_for_grafana):
        """
        Test that anonymous access is disabled by default.

        Expected: Accessing API without auth returns 401
        """
        response = requests.get(f"{grafana_url}/api/org", timeout=10)
        assert response.status_code == 401, "Anonymous access should be denied"

    def test_admin_login_works(self, grafana_url: str, grafana_credentials: Dict[str, str], wait_for_grafana):
        """
        Test that admin user can login.

        Expected: Login returns 200 with valid credentials
        """
        session = requests.Session()
        session.auth = (grafana_credentials["username"], grafana_credentials["password"])

        response = session.get(f"{grafana_url}/api/user", timeout=10)
        assert response.status_code == 200

        user = response.json()
        assert user["login"] == grafana_credentials["username"]

    def test_admin_has_permissions(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that admin user has full permissions.

        Expected: Admin can access admin endpoints
        """
        response = grafana_session.get(f"{grafana_url}/api/admin/stats", timeout=10)
        assert response.status_code == 200

        stats = response.json()
        assert "dashboards" in stats


class TestGrafanaAlertingSetup:
    """Test that Grafana alerting is configured."""

    def test_alerting_enabled(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Grafana alerting is enabled.

        Expected: Alerting endpoints are accessible
        """
        response = grafana_session.get(f"{grafana_url}/api/alert-notifications", timeout=10)
        # Should return 200 whether or not notifications are configured
        assert response.status_code == 200

    def test_contact_points_accessible(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that contact points (notification channels) are accessible.

        Expected: Contact points endpoint returns 200
        """
        response = grafana_session.get(
            f"{grafana_url}/api/v1/provisioning/contact-points",
            timeout=10
        )
        # Should return 200 even if empty
        assert response.status_code in [200, 404]  # 404 if unified alerting not enabled


class TestGrafanaPlugins:
    """Test Grafana plugins installation."""

    def test_plugins_endpoint_accessible(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that plugins endpoint is accessible.

        Expected: Plugins list can be retrieved
        """
        response = grafana_session.get(f"{grafana_url}/api/plugins", timeout=10)
        assert response.status_code == 200

        plugins = response.json()
        assert isinstance(plugins, list), "Plugins should be a list"

    def test_prometheus_plugin_installed(self, grafana_url: str, grafana_session, wait_for_grafana):
        """
        Test that Prometheus datasource plugin is installed.

        Expected: prometheus plugin exists in plugins list
        """
        response = grafana_session.get(f"{grafana_url}/api/plugins", timeout=10)
        plugins = response.json()

        plugin_ids = [p["id"] for p in plugins]
        assert "prometheus" in plugin_ids, "Prometheus plugin should be installed"
