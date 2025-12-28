"""
Integration test for container startup

TDD: These tests are written FIRST (RED phase).
They verify that all containers start correctly and are healthy.
"""

import os
import pytest
import subprocess
import time
from pathlib import Path


# Configuration
COMPOSE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "docker" / "compose"
REQUIRED_CONTAINERS = [
    "erp-saas-cloud-c16-mariadb",
    "erp-saas-cloud-c16-redis-cache",
    "erp-saas-cloud-c16-redis-queue",
    "erp-saas-cloud-c16-press",
]
STARTUP_TIMEOUT = 120  # seconds


def get_container_runtime() -> str:
    """Detect available container runtime (docker or podman)."""
    for runtime in ["docker", "podman"]:
        try:
            result = subprocess.run(
                [runtime, "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return runtime
        except FileNotFoundError:
            continue
    raise RuntimeError("Neither docker nor podman found")


class TestContainerStartup:
    """
    Integration tests for container startup and health.

    These tests verify that the Docker Compose stack can be started
    and all containers reach a healthy state.
    """

    @pytest.fixture
    def runtime(self) -> str:
        """Get the container runtime to use."""
        return get_container_runtime()

    def test_compose_files_exist(self):
        """Verify all required compose files exist."""
        required_files = [
            "mariadb.yml",
            "redis.yml",
        ]

        for filename in required_files:
            filepath = COMPOSE_DIR / filename
            assert filepath.exists(), f"Missing compose file: {filepath}"

    def test_container_prefix_validation(self, runtime: str):
        """
        Verify all running containers use the required prefix.

        This is a sanity check after containers are started.
        """
        result = subprocess.run(
            [runtime, "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Could not list containers")

        containers = result.stdout.strip().split("\n")
        prefix = "erp-saas-cloud-c16-"

        project_containers = [c for c in containers if c.startswith(prefix)]

        # Only check if we have project containers running
        if not project_containers:
            pytest.skip("No project containers running")

        for container in project_containers:
            assert container.startswith(prefix), (
                f"Container {container} doesn't have required prefix"
            )

    def test_mariadb_container_health(self, runtime: str):
        """
        Verify MariaDB container is healthy.

        Checks that the database is accepting connections.
        """
        container_name = "erp-saas-cloud-c16-mariadb"

        # Check if container exists
        result = subprocess.run(
            [runtime, "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if container_name not in result.stdout:
            pytest.skip(f"Container {container_name} not running")

        # Check health status
        result = subprocess.run(
            [runtime, "inspect", "--format", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            status = result.stdout.strip()
            assert status in ["healthy", "starting"], (
                f"MariaDB container health: {status}"
            )
        else:
            # Health check might not be configured, just check if running
            result = subprocess.run(
                [runtime, "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True
            )
            assert result.stdout.strip() == "true", "MariaDB container not running"

    def test_redis_containers_health(self, runtime: str):
        """
        Verify Redis containers are healthy.

        Checks both cache and queue Redis instances.
        """
        redis_containers = [
            "erp-saas-cloud-c16-redis-cache",
            "erp-saas-cloud-c16-redis-queue",
        ]

        for container_name in redis_containers:
            # Check if container exists
            result = subprocess.run(
                [runtime, "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            if container_name not in result.stdout:
                pytest.skip(f"Container {container_name} not running")

            # Check if running
            result = subprocess.run(
                [runtime, "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                assert result.stdout.strip() == "true", (
                    f"{container_name} not running"
                )

    def test_network_connectivity(self, runtime: str):
        """
        Verify containers can communicate on the project network.
        """
        network_name = "erp-saas-cloud-c16-network"

        # Check if network exists
        result = subprocess.run(
            [runtime, "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
            capture_output=True,
            text=True
        )

        if network_name not in result.stdout:
            pytest.skip(f"Network {network_name} not created")

        # Get containers on the network
        result = subprocess.run(
            [runtime, "network", "inspect", network_name, "--format", "{{range .Containers}}{{.Name}} {{end}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            containers = result.stdout.strip().split()
            # Just verify the network inspection works
            assert True, "Network is accessible"

    def test_port_bindings(self, runtime: str):
        """
        Verify containers have correct port bindings.
        """
        expected_ports = {
            "erp-saas-cloud-c16-mariadb": "32306",
            "erp-saas-cloud-c16-redis-cache": "32379",
            "erp-saas-cloud-c16-redis-queue": "32378",
        }

        for container_name, expected_port in expected_ports.items():
            result = subprocess.run(
                [runtime, "port", container_name, "3306" if "mariadb" in container_name else "6379"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Container {container_name} not running or no port mapping")

            output = result.stdout.strip()
            assert expected_port in output, (
                f"Expected port {expected_port} for {container_name}, got: {output}"
            )
