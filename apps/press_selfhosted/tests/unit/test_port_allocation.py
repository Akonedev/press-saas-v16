"""
Test port allocation and validation

TDD: These tests are written FIRST (RED phase).
They will FAIL until the implementation is complete.
"""

import pytest
import yaml
from pathlib import Path


# Configuration
CONFIG_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "config"
PORTS_YAML = CONFIG_DIR / "ports.yaml"
MIN_PORT = 32300
MAX_PORT = 32500
RESERVED_PORTS = [80, 443, 3306, 5432, 6379, 8080, 8000, 27017]


class TestPortAllocationRegistry:
    """Test suite for port allocation registry."""

    def test_ports_yaml_exists(self):
        """Verify ports.yaml file exists."""
        assert PORTS_YAML.exists(), f"Port allocation file not found: {PORTS_YAML}"

    def test_ports_yaml_is_valid(self):
        """Verify ports.yaml is valid YAML."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        try:
            with open(PORTS_YAML, "r") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_ports_yaml_has_constraint_section(self):
        """Verify ports.yaml defines port constraints."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        assert "constraint" in content, "Missing 'constraint' section"
        assert content["constraint"].get("min_port") == MIN_PORT
        assert content["constraint"].get("max_port") == MAX_PORT

    def test_ports_yaml_has_services_section(self):
        """Verify ports.yaml defines services."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        assert "services" in content, "Missing 'services' section"
        services = content["services"]

        required_services = ["traefik", "press", "mariadb", "redis-cache", "minio"]
        for service in required_services:
            assert service in services, f"Missing service definition: {service}"

    def test_all_ports_in_allowed_range(self):
        """Verify all defined ports are in the allowed range."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        invalid_ports = []

        def check_ports(section, path=""):
            """Recursively check all port values."""
            if isinstance(section, dict):
                for key, value in section.items():
                    new_path = f"{path}/{key}" if path else key
                    if key == "ports" and isinstance(value, dict):
                        for port_name, port_num in value.items():
                            if isinstance(port_num, int):
                                if not (MIN_PORT <= port_num <= MAX_PORT):
                                    invalid_ports.append(f"{new_path}/{port_name}: {port_num}")
                    elif key in ["start", "end"] and isinstance(value, int):
                        if not (MIN_PORT <= value <= MAX_PORT):
                            invalid_ports.append(f"{new_path}: {value}")
                    else:
                        check_ports(value, new_path)
            elif isinstance(section, list):
                for i, item in enumerate(section):
                    check_ports(item, f"{path}[{i}]")

        check_ports(content)

        assert not invalid_ports, (
            f"Ports outside allowed range {MIN_PORT}-{MAX_PORT}: {invalid_ports}"
        )

    def test_no_duplicate_ports(self):
        """Verify no duplicate port assignments."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        all_ports = []

        def collect_ports(section):
            """Recursively collect all port values."""
            if isinstance(section, dict):
                for key, value in section.items():
                    if key == "ports" and isinstance(value, dict):
                        for port_name, port_num in value.items():
                            if isinstance(port_num, int):
                                all_ports.append(port_num)
                    else:
                        collect_ports(value)
            elif isinstance(section, list):
                for item in section:
                    collect_ports(item)

        collect_ports(content.get("services", {}))
        collect_ports(content.get("monitoring", {}))

        duplicates = [p for p in all_ports if all_ports.count(p) > 1]
        assert not duplicates, f"Duplicate port assignments: {set(duplicates)}"

    def test_no_reserved_ports(self):
        """Verify no reserved/default ports are used."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        violations = []

        def check_reserved(section, path=""):
            """Recursively check for reserved ports."""
            if isinstance(section, dict):
                for key, value in section.items():
                    new_path = f"{path}/{key}" if path else key
                    if key == "ports" and isinstance(value, dict):
                        for port_name, port_num in value.items():
                            if isinstance(port_num, int) and port_num in RESERVED_PORTS:
                                violations.append(f"{new_path}/{port_name}: {port_num}")
                    else:
                        check_reserved(value, new_path)
            elif isinstance(section, list):
                for i, item in enumerate(section):
                    check_reserved(item, f"{path}[{i}]")

        check_reserved(content)

        assert not violations, f"Reserved ports used: {violations}"

    def test_container_names_follow_convention(self):
        """Verify all container names use required prefix."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        prefix = "erp-saas-cloud-c16-"
        invalid_names = []

        def check_container_names(section, path=""):
            """Recursively check container names."""
            if isinstance(section, dict):
                for key, value in section.items():
                    new_path = f"{path}/{key}" if path else key
                    if key == "container" and isinstance(value, str):
                        if not value.startswith(prefix):
                            invalid_names.append(f"{new_path}: {value}")
                    else:
                        check_container_names(value, new_path)
            elif isinstance(section, list):
                for i, item in enumerate(section):
                    check_container_names(item, f"{path}[{i}]")

        check_container_names(content)

        assert not invalid_names, (
            f"Container names must start with '{prefix}': {invalid_names}"
        )

    def test_validation_rules_defined(self):
        """Verify validation rules are defined in the registry."""
        if not PORTS_YAML.exists():
            pytest.skip("ports.yaml not yet created")

        with open(PORTS_YAML, "r") as f:
            content = yaml.safe_load(f)

        assert "validation" in content, "Missing 'validation' section"
        assert "rules" in content["validation"], "Missing validation rules"
        assert "excluded_ports" in content["validation"], "Missing excluded_ports list"

        excluded = content["validation"]["excluded_ports"]
        for port in RESERVED_PORTS:
            assert port in excluded, f"Reserved port {port} not in excluded list"
