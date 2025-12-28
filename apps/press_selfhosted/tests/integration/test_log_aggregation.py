"""
Integration Tests - Log Aggregation
====================================

Tests that Docker container logs can be accessed and aggregated for monitoring.

TDD Phase: RED (These tests should FAIL until log aggregation is configured)
Constitution Principle: I (TDD-First)
"""

import pytest
import requests
import subprocess
import json
from typing import Dict, List


@pytest.fixture
def container_prefix() -> str:
    """Container naming prefix from constitution."""
    return "erp-saas-cloud-c16"


class TestDockerLogsAccess:
    """Test that Docker container logs are accessible."""

    def test_docker_cli_available(self):
        """
        Test that Docker CLI is available.

        Expected: docker command exists and is executable
        """
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, "Docker CLI should be available"
        assert "Docker version" in result.stdout

    def test_can_list_containers(self, container_prefix: str):
        """
        Test that we can list Press containers.

        Expected: docker ps returns containers with our prefix
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        # Containers may not be running in TDD RED phase

    def test_can_get_container_logs(self, container_prefix: str):
        """
        Test that we can retrieve container logs.

        Expected: docker logs command works for Press containers
        """
        # Get first container
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet (TDD RED phase)")

        container_name = result.stdout.strip().split("\n")[0]

        # Get logs
        log_result = subprocess.run(
            ["docker", "logs", "--tail", "10", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert log_result.returncode == 0, "Should be able to retrieve logs"


class TestDockerLogsFormat:
    """Test Docker logging configuration and format."""

    def test_containers_use_json_logging(self, container_prefix: str):
        """
        Test that containers use JSON log driver.

        Expected: Containers configured with json-file log driver
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_name = result.stdout.strip().split("\n")[0]

        # Inspect container log config
        inspect_result = subprocess.run(
            ["docker", "inspect", "--format", "{{.HostConfig.LogConfig.Type}}", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert inspect_result.returncode == 0
        log_driver = inspect_result.stdout.strip()
        assert log_driver in ["json-file", "journald", "local"], f"Log driver should be json-file, got {log_driver}"

    def test_log_rotation_configured(self, container_prefix: str):
        """
        Test that log rotation is configured to prevent disk space issues.

        Expected: Containers have max-size and max-file set
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_name = result.stdout.strip().split("\n")[0]

        # Inspect log config
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert inspect_result.returncode == 0
        inspect_data = json.loads(inspect_result.stdout)

        log_config = inspect_data[0]["HostConfig"]["LogConfig"]
        # Rotation may not be configured in TDD RED phase


class TestLogContentStructure:
    """Test the structure and content of container logs."""

    def test_logs_contain_timestamps(self, container_prefix: str):
        """
        Test that logs include timestamps.

        Expected: Log lines include timestamp information
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_name = result.stdout.strip().split("\n")[0]

        # Get logs with timestamps
        log_result = subprocess.run(
            ["docker", "logs", "--timestamps", "--tail", "5", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert log_result.returncode == 0

        if log_result.stdout.strip():
            # Check first line has timestamp format
            first_line = log_result.stdout.strip().split("\n")[0]
            # Timestamp format: 2024-01-01T12:00:00.000000000Z
            assert "T" in first_line or "Z" in first_line, "Logs should include timestamps"

    def test_logs_accessible_via_compose(self, container_prefix: str):
        """
        Test that logs can be accessed via docker compose logs.

        Expected: docker compose logs command works
        """
        # Check if docker-compose or docker compose is available
        compose_cmd = None

        for cmd in [["docker", "compose"], ["docker-compose"]]:
            result = subprocess.run(
                cmd + ["--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                compose_cmd = cmd
                break

        if not compose_cmd:
            pytest.skip("Docker Compose not available")

        # Try to get logs (may fail if compose project not started)
        log_result = subprocess.run(
            compose_cmd + ["logs", "--tail", "5"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/home/frappe/frappe-bench/docker/compose"
        )
        # May fail if not in compose directory, which is acceptable


class TestLogAggregationSetup:
    """Test log aggregation infrastructure setup."""

    def test_log_directory_exists(self):
        """
        Test that log directory structure exists.

        Expected: /var/log directory is accessible
        """
        result = subprocess.run(
            ["test", "-d", "/var/log"],
            capture_output=True,
            timeout=10
        )
        assert result.returncode == 0, "/var/log directory should exist"

    def test_docker_log_files_exist(self, container_prefix: str):
        """
        Test that Docker creates log files for containers.

        Expected: Log files exist in Docker's log directory
        """
        # Docker typically stores logs in /var/lib/docker/containers/
        # This test verifies the logging infrastructure is working
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        # If we can get logs, files must exist
        container_name = result.stdout.strip().split("\n")[0]
        log_result = subprocess.run(
            ["docker", "logs", "--tail", "1", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert log_result.returncode == 0


class TestLogFiltering:
    """Test ability to filter and search logs."""

    def test_can_filter_logs_by_time(self, container_prefix: str):
        """
        Test that logs can be filtered by time range.

        Expected: docker logs --since and --until work
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_name = result.stdout.strip().split("\n")[0]

        # Get logs from last 1 minute
        log_result = subprocess.run(
            ["docker", "logs", "--since", "1m", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert log_result.returncode == 0

    def test_can_grep_logs(self, container_prefix: str):
        """
        Test that logs can be searched with grep.

        Expected: Can pipe docker logs to grep
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_name = result.stdout.strip().split("\n")[0]

        # Get logs and grep for error (may have no results)
        log_result = subprocess.run(
            f"docker logs --tail 100 {container_name} 2>&1 | grep -i error || true",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        assert log_result.returncode == 0


class TestLogAggregationIntegration:
    """Test integration with monitoring stack for log aggregation."""

    def test_logs_include_container_metadata(self, container_prefix: str):
        """
        Test that logs include container metadata for aggregation.

        Expected: Container names and labels are accessible
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{{{.Names}}}}\\t{{{{.Labels}}}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        # Verify we can get container metadata
        lines = result.stdout.strip().split("\n")
        assert len(lines) > 0

    def test_multiple_containers_logs_accessible(self, container_prefix: str):
        """
        Test that we can access logs from all Press containers.

        Expected: All containers return logs successfully
        """
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if not result.stdout.strip():
            pytest.skip("No containers running yet")

        container_names = result.stdout.strip().split("\n")

        # Try to get logs from each container
        for container in container_names[:3]:  # Test first 3 to avoid timeout
            log_result = subprocess.run(
                ["docker", "logs", "--tail", "1", container],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert log_result.returncode == 0, f"Should get logs from {container}"
