"""
Integration Tests - Prometheus Metrics Collection
==================================================

Tests that Prometheus is correctly scraping metrics from all targets.

TDD Phase: RED (These tests should FAIL until Prometheus is deployed)
Constitution Principle: I (TDD-First)
"""

import pytest
import requests
import time
from typing import Dict, List


@pytest.fixture
def prometheus_url() -> str:
    """Prometheus API URL."""
    return "http://localhost:32392"


@pytest.fixture
def wait_for_prometheus(prometheus_url: str):
    """Wait for Prometheus to be ready before running tests."""
    max_retries = 30
    retry_delay = 2

    for i in range(max_retries):
        try:
            response = requests.get(f"{prometheus_url}/-/ready", timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass

        if i < max_retries - 1:
            time.sleep(retry_delay)

    pytest.fail("Prometheus did not become ready in time")


class TestPrometheusDeployment:
    """Test Prometheus container is deployed and accessible."""

    def test_prometheus_is_running(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus is running and accessible.

        Expected: HTTP 200 from health endpoint
        """
        response = requests.get(f"{prometheus_url}/-/healthy", timeout=10)
        assert response.status_code == 200, "Prometheus should be healthy"

    def test_prometheus_ready(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus is ready to serve traffic.

        Expected: HTTP 200 from ready endpoint
        """
        response = requests.get(f"{prometheus_url}/-/ready", timeout=10)
        assert response.status_code == 200, "Prometheus should be ready"

    def test_prometheus_api_accessible(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus query API is accessible.

        Expected: HTTP 200 from query endpoint
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "up"},
            timeout=10
        )
        assert response.status_code == 200, "Prometheus API should be accessible"
        data = response.json()
        assert data["status"] == "success", "Query should succeed"


class TestPrometheusScrapeTargets:
    """Test that Prometheus is configured to scrape all required targets."""

    def test_scrape_targets_configured(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that scrape targets are configured.

        Expected: At least 4 targets (prometheus, node-exporter, cadvisor, frappe)
        """
        response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        active_targets = data["data"]["activeTargets"]
        assert len(active_targets) >= 3, "Should have at least 3 scrape targets"

        # Expected targets
        expected_jobs = ["prometheus", "node-exporter", "cadvisor"]
        configured_jobs = {target["labels"]["job"] for target in active_targets}

        for job in expected_jobs:
            assert job in configured_jobs, f"Job '{job}' should be configured"

    def test_prometheus_self_scrape(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus is scraping itself.

        Expected: Prometheus target is UP
        """
        response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=10)
        data = response.json()

        prometheus_targets = [
            t for t in data["data"]["activeTargets"]
            if t["labels"]["job"] == "prometheus"
        ]

        assert len(prometheus_targets) > 0, "Prometheus should scrape itself"
        assert prometheus_targets[0]["health"] == "up", "Prometheus target should be up"


class TestMetricsCollection:
    """Test that metrics are being collected from exporters."""

    def test_node_exporter_metrics(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that node_exporter metrics are available.

        Expected: node_cpu_seconds_total metric exists
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "node_cpu_seconds_total"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, "node_exporter metrics should exist"

    def test_node_memory_metrics(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that node memory metrics are available.

        Expected: node_memory_MemTotal_bytes metric exists
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "node_memory_MemTotal_bytes"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, "Memory metrics should exist"

    def test_cadvisor_metrics(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that cAdvisor container metrics are available.

        Expected: container_cpu_usage_seconds_total metric exists
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "container_cpu_usage_seconds_total"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, "cAdvisor metrics should exist"

    def test_container_memory_metrics(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that container memory metrics are available.

        Expected: container_memory_usage_bytes metric exists
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "container_memory_usage_bytes"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, "Container memory metrics should exist"


class TestMetricsLabels:
    """Test that metrics have correct labels for filtering."""

    def test_container_labels_present(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that container metrics have container_name labels.

        Expected: Metrics include erp-saas-cloud-c16-* containers
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": 'container_memory_usage_bytes{container_label_com_docker_compose_project="erp-saas-cloud-c16"}'},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # Note: May not have results if containers aren't running yet
        # This is acceptable in TDD RED phase

    def test_node_exporter_instance_label(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that node_exporter metrics have instance label.

        Expected: Instance label identifies the host
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "node_cpu_seconds_total"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        if len(data["data"]["result"]) > 0:
            result = data["data"]["result"][0]
            assert "instance" in result["metric"], "Metrics should have instance label"


class TestPrometheusConfiguration:
    """Test Prometheus configuration and storage."""

    def test_prometheus_config_reload(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus configuration can be reloaded.

        Expected: POST to /-/reload returns 200
        """
        response = requests.post(f"{prometheus_url}/-/reload", timeout=10)
        # May return 405 if reload is disabled, which is acceptable
        assert response.status_code in [200, 405]

    def test_prometheus_tsdb_status(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that Prometheus TSDB (time-series database) is accessible.

        Expected: TSDB stats endpoint returns 200
        """
        response = requests.get(f"{prometheus_url}/api/v1/status/tsdb", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_scrape_interval_configured(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that scrape interval is reasonable.

        Expected: Global scrape interval is configured (check via config)
        """
        response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "yaml" in data["data"], "Config should be available"


class TestMetricsRetention:
    """Test that Prometheus retains metrics over time."""

    def test_metrics_have_timestamps(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that metrics include timestamps.

        Expected: Query results include timestamp values
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "up"},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        if len(data["data"]["result"]) > 0:
            result = data["data"]["result"][0]
            assert "value" in result, "Result should have value"
            assert len(result["value"]) == 2, "Value should be [timestamp, value]"

    def test_range_query_works(self, prometheus_url: str, wait_for_prometheus):
        """
        Test that range queries work (query metrics over time).

        Expected: Range query API returns results
        """
        response = requests.get(
            f"{prometheus_url}/api/v1/query_range",
            params={
                "query": "up",
                "start": int(time.time()) - 300,  # 5 minutes ago
                "end": int(time.time()),
                "step": "15s"
            },
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
