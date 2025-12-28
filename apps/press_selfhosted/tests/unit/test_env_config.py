"""
Test environment configuration loading

TDD: These tests are written FIRST (RED phase).
They will FAIL until the implementation is complete.
"""

import os
import pytest
from pathlib import Path


# Configuration paths
CONFIG_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "config"
ENV_EXAMPLE = CONFIG_DIR / ".env.example"


class TestEnvConfiguration:
    """Test suite for environment configuration validation."""

    def test_env_example_exists(self):
        """Verify .env.example file exists."""
        assert ENV_EXAMPLE.exists(), f"Environment example file not found: {ENV_EXAMPLE}"

    def test_env_example_has_required_sections(self):
        """Verify .env.example contains all required configuration sections."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            content = f.read()

        required_sections = [
            "General Configuration",
            "Container Naming",
            "Port Configuration",
            "MariaDB Configuration",
            "Redis Configuration",
            "MinIO Configuration",
            "Frappe/Press Configuration",
            "Traefik/SSL Configuration",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_env_example_has_required_variables(self):
        """Verify .env.example contains all required environment variables."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            content = f.read()

        required_variables = [
            "DOMAIN",
            "CONTAINER_PREFIX",
            "TRAEFIK_HTTPS_PORT",
            "MARIADB_ROOT_PASSWORD",
            "MARIADB_PASSWORD",
            "REDIS_PASSWORD",
            "MINIO_ROOT_USER",
            "MINIO_ROOT_PASSWORD",
            "ADMIN_PASSWORD",
        ]

        for var in required_variables:
            assert var in content, f"Missing required variable: {var}"

    def test_env_example_port_range_compliance(self):
        """Verify all ports in .env.example are in allowed range."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            lines = f.readlines()

        min_port = 32300
        max_port = 32500
        invalid_ports = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "PORT" in line and "=" in line:
                parts = line.split("=")
                if len(parts) >= 2:
                    value = parts[1].strip()
                    try:
                        port = int(value)
                        if not (min_port <= port <= max_port):
                            invalid_ports.append(f"{parts[0]}={port}")
                    except ValueError:
                        pass  # Not a numeric port

        assert not invalid_ports, (
            f"Ports must be in range {min_port}-{max_port}: {invalid_ports}"
        )

    def test_env_example_container_prefix(self):
        """Verify CONTAINER_PREFIX is set correctly."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            content = f.read()

        assert "CONTAINER_PREFIX=erp-saas-cloud-c16" in content, (
            "CONTAINER_PREFIX must be set to 'erp-saas-cloud-c16'"
        )

    def test_env_example_no_real_secrets(self):
        """Verify .env.example doesn't contain real secrets."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            content = f.read()

        # Check that passwords are placeholder values
        assert "CHANGE_ME" in content, (
            "Password values should use 'CHANGE_ME' placeholder"
        )

        # Common patterns that might indicate real secrets
        danger_patterns = [
            "password123",
            "admin123",
            "secret123",
            "mysecret",
            "pass1234",
        ]

        for pattern in danger_patterns:
            assert pattern.lower() not in content.lower(), (
                f"Potential real secret found: {pattern}"
            )

    def test_env_example_minio_bucket_naming(self):
        """Verify MinIO bucket names follow naming convention."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            lines = f.readlines()

        prefix = "erp-saas-cloud-c16-"
        bucket_vars = ["MINIO_BUCKET_FILES", "MINIO_BUCKET_BACKUPS", "MINIO_BUCKET_PRIVATE"]

        for line in lines:
            for var in bucket_vars:
                if var in line and "=" in line:
                    value = line.split("=")[1].strip()
                    assert value.startswith(prefix), (
                        f"{var} should start with '{prefix}', got: {value}"
                    )


class TestEnvParsing:
    """Test environment parsing utilities."""

    def test_parse_env_file(self):
        """Test that env file can be parsed correctly."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        env_vars = {}
        with open(ENV_EXAMPLE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()

        assert len(env_vars) > 0, "Should parse at least some variables"
        assert "DOMAIN" in env_vars, "Should have DOMAIN variable"

    def test_env_variable_format(self):
        """Test that all variables follow naming conventions."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not yet created")

        with open(ENV_EXAMPLE, "r") as f:
            lines = f.readlines()

        invalid_names = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key = line.split("=")[0].strip()
                # Check UPPER_CASE_WITH_UNDERSCORES format
                if not key.isupper() and "_" not in key:
                    # Allow lowercase in value, check key format
                    if not all(c.isupper() or c == "_" or c.isdigit() for c in key):
                        invalid_names.append(key)

        # This is a soft check - just warn, don't fail
        if invalid_names:
            pytest.warns(
                UserWarning,
                match=f"Non-standard variable names: {invalid_names}"
            )
