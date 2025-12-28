"""
Contract test for MinIO Object Operations

TDD: These tests are written FIRST (RED phase).
They define the expected contract for MinIO object storage operations.
"""

import pytest
from typing import Optional
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import time


# Configuration
MINIO_ENDPOINT = "localhost:32390"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_SECURE = False


class TestMinioObjectOperations:
    """
    Contract tests for MinIO object operations.

    These tests verify that MinIO supports required object
    operations for file storage and backups.
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
    def test_bucket(self, minio_client: Optional[Minio]) -> Optional[str]:
        """Create a test bucket for object operations."""
        if not minio_client:
            return None

        bucket_name = "test-objects"

        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
            return bucket_name
        except S3Error:
            return None

    @pytest.fixture
    def test_data(self) -> bytes:
        """Generate test data for upload."""
        return b"Test file content for MinIO object operations"

    def test_can_upload_object(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
        test_data: bytes,
    ):
        """
        Verify object upload works.

        Contract: Must be able to upload objects to buckets.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = f"test-upload-{int(time.time())}.txt"
            data_stream = BytesIO(test_data)

            # Upload object
            result = minio_client.put_object(
                test_bucket,
                object_name,
                data_stream,
                length=len(test_data),
                content_type="text/plain",
            )

            assert result is not None, "Upload should return a result"
            assert result.object_name == object_name, "Object name should match"

            # Cleanup
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_download_object(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
        test_data: bytes,
    ):
        """
        Verify object download works.

        Contract: Must be able to download uploaded objects.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = f"test-download-{int(time.time())}.txt"

            # Upload first
            data_stream = BytesIO(test_data)
            minio_client.put_object(
                test_bucket,
                object_name,
                data_stream,
                length=len(test_data),
            )

            # Download
            response = minio_client.get_object(test_bucket, object_name)
            downloaded_data = response.read()

            assert downloaded_data == test_data, (
                "Downloaded data should match uploaded data"
            )

            # Cleanup
            response.close()
            response.release_conn()
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_list_objects(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
        test_data: bytes,
    ):
        """
        Verify object listing works.

        Contract: Must be able to list objects in a bucket.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = f"test-list-{int(time.time())}.txt"

            # Upload an object
            data_stream = BytesIO(test_data)
            minio_client.put_object(
                test_bucket,
                object_name,
                data_stream,
                length=len(test_data),
            )

            # List objects
            objects = list(minio_client.list_objects(test_bucket))

            assert len(objects) > 0, "Should find at least one object"
            object_names = [obj.object_name for obj in objects]
            assert object_name in object_names, "Uploaded object should be in list"

            # Cleanup
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_delete_object(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
        test_data: bytes,
    ):
        """
        Verify object deletion works.

        Contract: Must be able to delete objects.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = f"test-delete-{int(time.time())}.txt"

            # Upload object
            data_stream = BytesIO(test_data)
            minio_client.put_object(
                test_bucket,
                object_name,
                data_stream,
                length=len(test_data),
            )

            # Delete object
            minio_client.remove_object(test_bucket, object_name)

            # Verify deletion
            objects = list(minio_client.list_objects(test_bucket, prefix=object_name))
            assert len(objects) == 0, "Object should be deleted"

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_get_object_stat(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
        test_data: bytes,
    ):
        """
        Verify object stat/metadata retrieval works.

        Contract: Must be able to get object metadata without downloading.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = f"test-stat-{int(time.time())}.txt"

            # Upload object
            data_stream = BytesIO(test_data)
            minio_client.put_object(
                test_bucket,
                object_name,
                data_stream,
                length=len(test_data),
                content_type="text/plain",
            )

            # Get stat
            stat = minio_client.stat_object(test_bucket, object_name)

            assert stat is not None, "Should return stat object"
            assert stat.size == len(test_data), "Size should match"
            assert stat.content_type == "text/plain", "Content type should match"

            # Cleanup
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise


class TestMinioPresignedUrls:
    """
    Contract tests for presigned URLs.

    These tests verify that MinIO supports presigned URLs
    for temporary access to objects.
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
    def test_bucket(self, minio_client: Optional[Minio]) -> Optional[str]:
        """Create a test bucket."""
        if not minio_client:
            return None

        bucket_name = "test-presigned"

        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
            return bucket_name
        except S3Error:
            return None

    def test_can_generate_presigned_get_url(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
    ):
        """
        Verify presigned GET URL generation works.

        Contract: Must be able to generate presigned URLs for downloads.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = "test-file.txt"

            # Upload a test object first
            data = b"Test content"
            minio_client.put_object(
                test_bucket,
                object_name,
                BytesIO(data),
                length=len(data),
            )

            # Generate presigned URL
            from datetime import timedelta
            url = minio_client.presigned_get_object(
                test_bucket,
                object_name,
                expires=timedelta(hours=1),
            )

            assert url is not None, "Should generate presigned URL"
            assert isinstance(url, str), "URL should be a string"
            assert test_bucket in url, "URL should contain bucket name"
            assert object_name in url, "URL should contain object name"

            # Cleanup
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise

    def test_can_generate_presigned_put_url(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
    ):
        """
        Verify presigned PUT URL generation works.

        Contract: Must be able to generate presigned URLs for uploads.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            object_name = "test-upload.txt"

            # Generate presigned PUT URL
            from datetime import timedelta
            url = minio_client.presigned_put_object(
                test_bucket,
                object_name,
                expires=timedelta(hours=1),
            )

            assert url is not None, "Should generate presigned PUT URL"
            assert isinstance(url, str), "URL should be a string"
            assert test_bucket in url, "URL should contain bucket name"
            assert object_name in url, "URL should contain object name"

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise


class TestMinioPathStructure:
    """
    Contract tests for object path structure.

    These tests verify that MinIO supports the required
    path/prefix structure for organizing files.
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
    def test_bucket(self, minio_client: Optional[Minio]) -> Optional[str]:
        """Create a test bucket."""
        if not minio_client:
            return None

        bucket_name = "test-paths"

        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
            return bucket_name
        except S3Error:
            return None

    def test_supports_nested_paths(
        self,
        minio_client: Optional[Minio],
        test_bucket: Optional[str],
    ):
        """
        Verify nested path structure is supported.

        Contract: Must support objects with path-like names.
        """
        if not minio_client or not test_bucket:
            pytest.skip("MinIO not available")

        try:
            # Create nested path structure
            object_name = f"sites/demo.local/files/document-{int(time.time())}.pdf"
            data = b"PDF content"

            minio_client.put_object(
                test_bucket,
                object_name,
                BytesIO(data),
                length=len(data),
            )

            # Verify object exists
            stat = minio_client.stat_object(test_bucket, object_name)
            assert stat is not None, "Object should exist"

            # List objects with prefix
            objects = list(minio_client.list_objects(
                test_bucket,
                prefix="sites/demo.local/",
            ))
            assert len(objects) > 0, "Should find objects with prefix"

            # Cleanup
            minio_client.remove_object(test_bucket, object_name)

        except S3Error as e:
            if "connection" in str(e).lower():
                pytest.skip("MinIO server not running")
            raise
