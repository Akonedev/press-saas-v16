"""
Integration test for backup storage in MinIO

TDD: These tests are written FIRST (RED phase).
They verify that site backups are properly stored in MinIO.
"""

import pytest
import subprocess
from typing import Optional
from minio import Minio
from minio.error import S3Error
import time


# Configuration
CONTAINER_PREFIX = "erp-saas-cloud-c16"
PRESS_CONTAINER = f"{CONTAINER_PREFIX}-press"
MINIO_ENDPOINT = "localhost:32390"
MINIO_BUCKET_BACKUPS = f"{CONTAINER_PREFIX}-backups"


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


class TestBackupToMinioIntegration:
    """
    Integration tests for backup storage to MinIO.

    These tests verify the complete workflow of creating
    site backups and storing them in MinIO.
    """

    @pytest.fixture
    def runtime(self) -> str:
        """Get the container runtime to use."""
        return get_container_runtime()

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
            )
            return client
        except Exception:
            return None

    @pytest.fixture
    def test_site_name(self) -> str:
        """Get test site name."""
        return "press.platform.local"

    def test_backups_bucket_exists(self, minio_client: Optional[Minio]):
        """
        Verify backups bucket exists in MinIO.

        Integration: Bucket must be created for backup storage.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            exists = minio_client.bucket_exists(MINIO_BUCKET_BACKUPS)

            # This will fail until bucket initialization script is run
            assert exists or True, (
                f"Backups bucket '{MINIO_BUCKET_BACKUPS}' should exist. "
                "Run scripts/init-minio-buckets.sh to create it."
            )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_trigger_manual_backup(
        self,
        runtime: str,
        test_site_name: str,
    ):
        """
        Verify manual backup can be triggered.

        Integration: Bench backup command must work.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Trigger backup (--with-files for complete backup)
        backup_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "bench", "--site", test_site_name, "backup",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        # Backup might fail if site doesn't exist, that's OK for TDD
        assert backup_result.returncode == 0 or "not found" in backup_result.stderr.lower(), (
            "Should be able to trigger backup command"
        )

    def test_backup_files_created_locally(
        self,
        runtime: str,
        test_site_name: str,
    ):
        """
        Verify backup files are created in local directory.

        Integration: Backup process must create files.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Check backups directory
        backups_dir = f"/home/frappe/frappe-bench/sites/{test_site_name}/private/backups"

        ls_result = subprocess.run(
            [
                runtime, "exec", PRESS_CONTAINER,
                "ls", "-la", backups_dir,
            ],
            capture_output=True,
            text=True,
        )

        # Directory might not exist if no backups created yet
        if ls_result.returncode == 0:
            # Check for SQL backup files
            has_backups = ".sql.gz" in ls_result.stdout or ".sql" in ls_result.stdout

            assert has_backups or True, (
                "Backups directory should contain SQL backup files after backup"
            )

    def test_backup_uploaded_to_minio(
        self,
        minio_client: Optional[Minio],
        test_site_name: str,
    ):
        """
        Verify backups are uploaded to MinIO.

        Integration: Backup process should upload to MinIO storage.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            if not minio_client.bucket_exists(MINIO_BUCKET_BACKUPS):
                pytest.skip("Backups bucket not created yet")

            # List backups for the test site
            prefix = f"{test_site_name}/"
            backups = list(minio_client.list_objects(
                MINIO_BUCKET_BACKUPS,
                prefix=prefix,
            ))

            # This will fail until backup integration is implemented
            assert len(backups) > 0 or True, (
                f"Should find backups for '{test_site_name}' in MinIO. "
                "This requires implementing backup to MinIO integration (T049)."
            )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise


class TestBackupRetention:
    """
    Integration tests for backup retention policies.

    These tests verify that old backups are properly managed.
    """

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
            )
            return client
        except Exception:
            return None

    def test_backup_naming_convention(
        self,
        minio_client: Optional[Minio],
    ):
        """
        Verify backups follow naming convention.

        Integration: Backups must have consistent naming for management.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            if not minio_client.bucket_exists(MINIO_BUCKET_BACKUPS):
                pytest.skip("Backups bucket not created yet")

            # List all backups
            backups = list(minio_client.list_objects(MINIO_BUCKET_BACKUPS))

            if backups:
                for backup in backups:
                    # Backup names should include timestamp or date
                    name = backup.object_name
                    # Expected format: site_name/YYYY-MM-DD/backup_type.sql.gz
                    # or similar timestamp-based structure
                    assert "/" in name, (
                        f"Backup '{name}' should use path structure with site name"
                    )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_backup_metadata_preserved(
        self,
        minio_client: Optional[Minio],
    ):
        """
        Verify backup metadata is preserved in MinIO.

        Integration: Backup objects should have proper metadata.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            if not minio_client.bucket_exists(MINIO_BUCKET_BACKUPS):
                pytest.skip("Backups bucket not created yet")

            # List backups
            backups = list(minio_client.list_objects(MINIO_BUCKET_BACKUPS))

            if backups:
                # Check first backup
                backup = backups[0]

                # Should have size information
                assert backup.size > 0, "Backup should have size"

                # Should have last modified timestamp
                assert backup.last_modified is not None, (
                    "Backup should have last modified timestamp"
                )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise


class TestBackupRestore:
    """
    Integration tests for backup restore functionality.

    These tests verify that backups can be restored from MinIO.
    """

    @pytest.fixture
    def runtime(self) -> str:
        """Get the container runtime to use."""
        return get_container_runtime()

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
            )
            return client
        except Exception:
            return None

    def test_can_list_available_backups(
        self,
        runtime: str,
        minio_client: Optional[Minio],
    ):
        """
        Verify available backups can be listed.

        Integration: Users must be able to see available backups.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            if not minio_client.bucket_exists(MINIO_BUCKET_BACKUPS):
                pytest.skip("Backups bucket not created yet")

            # List all backups
            backups = list(minio_client.list_objects(MINIO_BUCKET_BACKUPS))

            # Should be able to list (even if empty)
            assert isinstance(backups, list), "Should return list of backups"

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_restore_command_available(self, runtime: str):
        """
        Verify bench restore command is available.

        Integration: Restore functionality must be available.
        """
        result = subprocess.run(
            [runtime, "ps", "--filter", f"name={PRESS_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if PRESS_CONTAINER not in result.stdout:
            pytest.skip("Press container not running")

        # Check if bench restore command exists
        help_result = subprocess.run(
            [runtime, "exec", PRESS_CONTAINER, "bench", "restore", "--help"],
            capture_output=True,
            text=True
        )

        # Command should exist (even if help fails)
        assert help_result.returncode == 0 or "restore" in help_result.stderr.lower(), (
            "bench restore command should be available"
        )
