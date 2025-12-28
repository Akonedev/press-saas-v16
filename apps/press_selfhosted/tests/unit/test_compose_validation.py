"""
Test Docker Compose file validation

TDD: These tests are written FIRST (RED phase).
They will FAIL until the implementation is complete.
"""

import os
import pytest
import yaml
from pathlib import Path


# Configuration
COMPOSE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "docker" / "compose"
REQUIRED_PREFIX = "erp-saas-cloud-c16-"
MIN_PORT = 32300
MAX_PORT = 32500


class TestComposeFileValidation:
    """Test suite for Docker Compose file validation."""

    def test_compose_directory_exists(self):
        """Verify the compose directory exists."""
        assert COMPOSE_DIR.exists(), f"Compose directory not found: {COMPOSE_DIR}"

    def test_compose_files_are_valid_yaml(self):
        """Verify all compose files are valid YAML."""
        if not COMPOSE_DIR.exists():
            pytest.skip("Compose directory not yet created")

        yaml_files = list(COMPOSE_DIR.glob("*.yml")) + list(COMPOSE_DIR.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No compose files found yet")

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {yaml_file}: {e}")

    def test_container_names_have_required_prefix(self):
        """Verify all container names use the required prefix."""
        if not COMPOSE_DIR.exists():
            pytest.skip("Compose directory not yet created")

        yaml_files = list(COMPOSE_DIR.glob("*.yml")) + list(COMPOSE_DIR.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No compose files found yet")

        invalid_names = []

        for yaml_file in yaml_files:
            with open(yaml_file, "r") as f:
                content = yaml.safe_load(f)

            if not content or "services" not in content:
                continue

            for service_name, service_config in content.get("services", {}).items():
                container_name = service_config.get("container_name")
                if container_name and not container_name.startswith(REQUIRED_PREFIX):
                    # Skip variable references like ${CONTAINER_PREFIX}
                    if not container_name.startswith("${"):
                        invalid_names.append(
                            f"{yaml_file.name}: {container_name}"
                        )

        assert not invalid_names, (
            f"Container names must start with '{REQUIRED_PREFIX}': {invalid_names}"
        )

    def test_exposed_ports_in_allowed_range(self):
        """Verify all exposed host ports are in the allowed range (32300-32500)."""
        if not COMPOSE_DIR.exists():
            pytest.skip("Compose directory not yet created")

        yaml_files = list(COMPOSE_DIR.glob("*.yml")) + list(COMPOSE_DIR.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No compose files found yet")

        invalid_ports = []

        for yaml_file in yaml_files:
            with open(yaml_file, "r") as f:
                content = yaml.safe_load(f)

            if not content or "services" not in content:
                continue

            for service_name, service_config in content.get("services", {}).items():
                ports = service_config.get("ports", [])
                for port_mapping in ports:
                    # Parse port mapping (could be "32300:80" or just "80")
                    port_str = str(port_mapping)

                    # Skip variable references
                    if "${" in port_str:
                        continue

                    # Extract host port
                    if ":" in port_str:
                        host_port = port_str.split(":")[0]
                    else:
                        continue  # No host port mapping

                    try:
                        host_port_num = int(host_port)
                        if not (MIN_PORT <= host_port_num <= MAX_PORT):
                            invalid_ports.append(
                                f"{yaml_file.name}/{service_name}: {host_port_num}"
                            )
                    except ValueError:
                        # Skip non-numeric ports (variables)
                        pass

        assert not invalid_ports, (
            f"Host ports must be in range {MIN_PORT}-{MAX_PORT}: {invalid_ports}"
        )

    def test_no_default_ports_exposed(self):
        """Verify no default/reserved ports are exposed."""
        reserved_ports = [80, 443, 3306, 5432, 6379, 8080, 8000, 27017]

        if not COMPOSE_DIR.exists():
            pytest.skip("Compose directory not yet created")

        yaml_files = list(COMPOSE_DIR.glob("*.yml")) + list(COMPOSE_DIR.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No compose files found yet")

        violations = []

        for yaml_file in yaml_files:
            with open(yaml_file, "r") as f:
                content = yaml.safe_load(f)

            if not content or "services" not in content:
                continue

            for service_name, service_config in content.get("services", {}).items():
                ports = service_config.get("ports", [])
                for port_mapping in ports:
                    port_str = str(port_mapping)

                    if "${" in port_str:
                        continue

                    if ":" in port_str:
                        host_port = port_str.split(":")[0]
                        try:
                            host_port_num = int(host_port)
                            if host_port_num in reserved_ports:
                                violations.append(
                                    f"{yaml_file.name}/{service_name}: "
                                    f"reserved port {host_port_num}"
                                )
                        except ValueError:
                            pass

        assert not violations, f"Reserved ports must not be used: {violations}"

    def test_network_configuration(self):
        """Verify network configuration uses the project network."""
        if not COMPOSE_DIR.exists():
            pytest.skip("Compose directory not yet created")

        yaml_files = list(COMPOSE_DIR.glob("*.yml")) + list(COMPOSE_DIR.glob("*.yaml"))

        if not yaml_files:
            pytest.skip("No compose files found yet")

        # Check if main compose file defines the network
        main_compose = COMPOSE_DIR / "docker-compose.yml"
        if not main_compose.exists():
            pytest.skip("Main docker-compose.yml not yet created")

        with open(main_compose, "r") as f:
            content = yaml.safe_load(f)

        networks = content.get("networks", {})
        assert networks, "At least one network must be defined"

        # Check for project network
        expected_network = f"{REQUIRED_PREFIX.rstrip('-')}-network"
        assert any(
            expected_network in str(net) for net in networks.keys()
        ) or any(
            "${" in str(net) for net in networks.keys()
        ), f"Expected network '{expected_network}' or variable reference"
