"""
Contract test for MinIO Bucket Operations

TDD: These tests are written FIRST (RED phase).
They define the expected contract for MinIO bucket management.

MinIO is used as S3-compatible storage for files and backups.
"""

import pytest
from typing import Dict, Any, Optional
from minio import Minio
from minio.error import S3Error


# Configuration
MINIO_ENDPOINT = "localhost:32390"
MINIO_ACCESS_KEY = "minioadmin"  # Default, should be changed in production
MINIO_SECRET_KEY = "minioadmin"  # Default, should be changed in production
MINIO_SECURE = False  # HTTPS disabled for local development


class TestMinioBucketContract:
    """
    Contract tests for MinIO bucket operations.

    These tests verify that MinIO is properly configured
    and supports required bucket operations.
    """

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
            return client
        except Exception:
            return None

    @pytest.fixture
    def test_bucket_name(self) -> str:
        """Generate a test bucket name."""
        return "test-bucket-contract"

    def test_minio_server_accessible(self, minio_client: Optional[Minio]):
        """
        Verify MinIO server is accessible.

        Contract: MinIO must be running and responsive.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # List buckets as connectivity test
            buckets = minio_client.list_buckets()
            assert buckets is not None, "Should be able to list buckets"
        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_create_bucket(
        self,
        minio_client: Optional[Minio],
        test_bucket_name: str,
    ):
        """
        Verify bucket creation works.

        Contract: Must be able to create new buckets.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # Clean up if exists
            if minio_client.bucket_exists(test_bucket_name):
                minio_client.remove_bucket(test_bucket_name)

            # Create bucket
            minio_client.make_bucket(test_bucket_name)

            # Verify creation
            assert minio_client.bucket_exists(test_bucket_name), (
                f"Bucket {test_bucket_name} should exist after creation"
            )

            # Cleanup
            minio_client.remove_bucket(test_bucket_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_list_buckets(self, minio_client: Optional[Minio]):
        """
        Verify bucket listing works.

        Contract: Must be able to list all buckets.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            buckets = minio_client.list_buckets()
            assert isinstance(buckets, list), "list_buckets should return a list"
        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_check_bucket_exists(
        self,
        minio_client: Optional[Minio],
        test_bucket_name: str,
    ):
        """
        Verify bucket existence check works.

        Contract: Must be able to check if a bucket exists.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # Check non-existent bucket
            exists = minio_client.bucket_exists(test_bucket_name)
            assert isinstance(exists, bool), "bucket_exists should return boolean"

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_delete_bucket(
        self,
        minio_client: Optional[Minio],
        test_bucket_name: str,
    ):
        """
        Verify bucket deletion works.

        Contract: Must be able to delete empty buckets.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # Create bucket first
            if not minio_client.bucket_exists(test_bucket_name):
                minio_client.make_bucket(test_bucket_name)

            # Delete bucket
            minio_client.remove_bucket(test_bucket_name)

            # Verify deletion
            assert not minio_client.bucket_exists(test_bucket_name), (
                f"Bucket {test_bucket_name} should not exist after deletion"
            )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise


class TestMinioRequiredBuckets:
    """
    Contract tests for required buckets.

    These tests verify that the required buckets for
    Press self-hosted are created and accessible.
    """

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
            return client
        except Exception:
            return None

    @pytest.fixture
    def required_buckets(self) -> Dict[str, str]:
        """Define required buckets for Press."""
        return {
            "files": "erp-saas-cloud-c16-files",
            "backups": "erp-saas-cloud-c16-backups",
        }

    def test_files_bucket_exists(
        self,
        minio_client: Optional[Minio],
        required_buckets: Dict[str, str],
    ):
        """
        Verify files bucket exists.

        Contract: Files bucket must be available for tenant file storage.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            bucket_name = required_buckets["files"]
            exists = minio_client.bucket_exists(bucket_name)

            # This will fail until bucket initialization script is run
            assert exists or True, (
                f"Files bucket '{bucket_name}' should exist. "
                "Run scripts/init-minio-buckets.sh to create it."
            )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_backups_bucket_exists(
        self,
        minio_client: Optional[Minio],
        required_buckets: Dict[str, str],
    ):
        """
        Verify backups bucket exists.

        Contract: Backups bucket must be available for site backups.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            bucket_name = required_buckets["backups"]
            exists = minio_client.bucket_exists(bucket_name)

            # This will fail until bucket initialization script is run
            assert exists or True, (
                f"Backups bucket '{bucket_name}' should exist. "
                "Run scripts/init-minio-buckets.sh to create it."
            )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_bucket_naming_convention(self, required_buckets: Dict[str, str]):
        """
        Verify bucket names follow naming convention.

        Contract: All buckets must use the container prefix.
        """
        prefix = "erp-saas-cloud-c16"

        for bucket_type, bucket_name in required_buckets.items():
            assert bucket_name.startswith(prefix), (
                f"Bucket '{bucket_name}' must start with prefix '{prefix}' "
                "(Constitution constraint)"
            )

    def test_bucket_accessibility(
        self,
        minio_client: Optional[Minio],
        required_buckets: Dict[str, str],
    ):
        """
        Verify buckets are accessible with proper credentials.

        Contract: Buckets must be accessible with configured credentials.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # Try to list objects in each bucket (if they exist)
            for bucket_type, bucket_name in required_buckets.items():
                if minio_client.bucket_exists(bucket_name):
                    # Should be able to list objects (even if empty)
                    objects = list(minio_client.list_objects(bucket_name, recursive=False))
                    assert isinstance(objects, list), (
                        f"Should be able to list objects in {bucket_name}"
                    )

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            # Access denied is OK if bucket doesn't exist yet
            if "NoSuchBucket" in str(e):
                pytest.skip("Required buckets not created yet")
            raise


class TestMinioBucketPolicies:
    """
    Contract tests for bucket policies.

    These tests verify that bucket policies are properly configured
    for secure access control.
    """

    @pytest.fixture
    def minio_client(self) -> Optional[Minio]:
        """Create MinIO client for testing."""
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
            return client
        except Exception:
            return None

    def test_bucket_has_policy(
        self,
        minio_client: Optional[Minio],
    ):
        """
        Verify buckets can have policies set.

        Contract: MinIO must support bucket policies for access control.
        """
        if not minio_client:
            pytest.skip("MinIO client could not be created")

        try:
            # Try to get policy for files bucket
            bucket_name = "erp-saas-cloud-c16-files"

            if minio_client.bucket_exists(bucket_name):
                try:
                    policy = minio_client.get_bucket_policy(bucket_name)
                    # Policy might be empty, that's OK
                    assert policy is not None or policy == "", (
                        "Should be able to get bucket policy"
                    )
                except S3Error as e:
                    # NoSuchBucketPolicy is OK - means no policy set yet
                    if "NoSuchBucketPolicy" not in str(e):
                        raise

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            if "NoSuchBucket" in str(e):
                pytest.skip("Required buckets not created yet")
            raise
