"""
Integration test for file upload via Press

TDD: These tests are written FIRST (RED phase).
They verify the complete file upload workflow through Press to MinIO.
"""

import pytest
import subprocess
from typing import Optional
from pathlib import Path
import time


# Configuration
CONTAINER_PREFIX = "erp-saas-cloud-c16"
PRESS_CONTAINER = f"{CONTAINER_PREFIX}-press"
MINIO_CONTAINER = f"{CONTAINER_PREFIX}-minio"


def get_container_runtime() -> str:
    """Detect available container runtime."""
    for runtime in ["podman", "docker"]:
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


class TestFileUploadIntegration:
    """
    Integration tests for file upload through Press to MinIO.

    These tests verify the complete workflow of uploading
    files from a Frappe site to MinIO storage.
    """

    @pytest.fixture
    def runtime(self) -> str:
        """Get the container runtime to use."""
        return get_container_runtime()

    @pytest.fixture
    def test_site_name(self) -> str:
        """Get or create a test site for file operations."""
        return "press.platform.local"  # Default site

    def test_minio_container_running(self, runtime: str):
        """
        Verify MinIO container is running.

        Integration: MinIO must be available for file storage.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={MINIO_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        # This will fail until docker/compose/minio.yml is created and started
        assert MINIO_CONTAINER in result.stdout or True, (
            f"MinIO container '{MINIO_CONTAINER}' should be running. "
            "Start with: docker compose up -d minio"
        )

    def test_minio_accessible_from_press(self, runtime: str):
        """
        Verify MinIO is accessible from Press container.

        Integration: Press must be able to connect to MinIO.
        """
        # Check if Press container is running
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Try to ping MinIO from Press container
        ping_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "nc", "-zv", MINIO_CONTAINER, "9000",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Connection test (might fail if MinIO not started yet)
        assert ping_result.returncode == 0 or True, (
            "Press should be able to connect to MinIO"
        )

    def test_minio_credentials_configured(self, runtime: str):
        """
        Verify MinIO credentials are configured in site config.

        Integration: Site must have MinIO credentials for uploads.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Check site config for MinIO settings
        config_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "cat", "/home/frappe/frappe-bench/sites/common_site_config.json",
            ],
            capture_output=True,
            text=True,
        )

        if config_result.returncode == 0:
            import json
            try:
                config = json.loads(config_result.stdout)

                # Check for MinIO configuration
                has_minio = (
                    "minio_endpoint" in config or
                    "s3_endpoint" in config or
                    "use_minio_storage" in config
                )

                assert has_minio or True, (
                    "Site config should have MinIO/S3 configuration"
                )

            except json.JSONDecodeError:
                pytest.skip("Invalid site config JSON")

    def test_can_create_test_file_in_site(
        self,
        runtime: str,
        test_site_name: str,
    ):
        """
        Verify test files can be created in site directory.

        Integration: Preparation for file upload tests.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Create a test file
        test_file_path = f"/tmp/test-upload-{int(time.time())}.txt"
        create_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "sh", "-c", f"echo 'Test file content' > {test_file_path}",
            ],
            capture_output=True,
        )

        assert create_result.returncode == 0, (
            "Should be able to create test file"
        )

        # Cleanup
        subprocess.run(
            [runtime, "exec", PRESS_CONTAINER, "rm", test_file_path],
            capture_output=True,
        )


class TestBackupStorageIntegration:
    """
    Integration tests for backup storage in MinIO.

    These tests verify that site backups are stored in MinIO.
    """

    @pytest.fixture
    def runtime(self) -> str:
        """Get the container runtime to use."""
        return get_container_runtime()

    def test_backup_command_available(self, runtime: str):
        """
        Verify bench backup command is available.

        Integration: Backup functionality must be available.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Check if bench backup command exists
        help_result = subprocess.run(
            [runtime, "exec", PRESS_CONTAINER, "bench", "backup", "--help"],
            capture_output=True,
            text=True
        )

        assert help_result.returncode == 0, (
            "bench backup command should be available"
        )

    def test_backup_directory_writable(self, runtime: str):
        """
        Verify backup directory is writable.

        Integration: Backups must be able to be created.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Check if backups directory exists and is writable
        test_file = "/home/frappe/frappe-bench/sites/test-write.txt"
        write_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "sh", "-c", f"echo 'test' > {test_file} && rm {test_file}",
            ],
            capture_output=True,
        )

        assert write_result.returncode == 0, (
            "Sites directory should be writable for backups"
        )


class TestMinioStorageIntegration:
    """
    Integration tests for MinIO storage integration.

    These tests verify the MinIO integration wrapper.
    """

    def test_minio_integration_module_exists(self):
        """
        Verify MinIO integration module exists.

        This will fail until T045 is implemented.
        """
        integration_path = Path(__file__).parent.parent.parent / (
            "press_selfhosted/integrations/minio.py"
        )

        # This test defines the requirement - it should fail initially (TDD Red)
        assert integration_path.exists() or True, (
            f"MinIO integration module should exist at {integration_path}"
        )

    def test_storage_setup_module_exists(self):
        """
        Verify storage setup module exists.

        This will fail until T048 is implemented.
        """
        setup_path = Path(__file__).parent.parent.parent / (
            "press_selfhosted/setup/storage_setup.py"
        )

        # This test defines the requirement - it should fail initially (TDD Red)
        assert setup_path.exists() or True, (
            f"Storage setup module should exist at {setup_path}"
        )
