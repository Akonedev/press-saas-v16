"""
MinIO Integration for Self-Hosted Press

This module provides a wrapper around the MinIO Python SDK
for seamless integration with Press self-hosted platform.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional, List, BinaryIO
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import os
from pathlib import Path


class MinIOClient:
    """
    MinIO client wrapper for Press self-hosted.

    This class provides high-level methods for interacting
    with MinIO storage, abstracting away the S3 API details.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False,
    ):
        """
        Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (default: from config)
            access_key: Access key (default: from config)
            secret_key: Secret key (default: from config)
            secure: Use HTTPS (default: False for local)
        """
        self.endpoint = endpoint or frappe.conf.get(
            "minio_endpoint", "erp-saas-cloud-c16-minio:9000"
        )
        self.access_key = access_key or frappe.conf.get(
            "minio_access_key", "minioadmin"
        )
        self.secret_key = secret_key or frappe.conf.get(
            "minio_secret_key", "minioadmin"
        )
        self.secure = secure

        # Container prefix for bucket names
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )

        # Bucket names
        self.bucket_files = f"{self.container_prefix}-files"
        self.bucket_backups = f"{self.container_prefix}-backups"

        # Initialize client
        self.client = self._create_client()

    def _create_client(self) -> Minio:
        """Create MinIO client instance."""
        return Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def check_connection(self) -> Dict[str, Any]:
        """
        Check MinIO connection.

        Returns:
            Dict with connection status
        """
        try:
            # List buckets as connectivity test
            buckets = self.client.list_buckets()
            return {
                "connected": True,
                "endpoint": self.endpoint,
                "buckets": [b.name for b in buckets],
            }
        except S3Error as e:
            return {
                "connected": False,
                "error": str(e),
                "endpoint": self.endpoint,
            }

    def ensure_buckets_exist(self) -> Dict[str, Any]:
        """
        Ensure required buckets exist.

        Returns:
            Dict with creation results
        """
        results = {"created": [], "existing": [], "errors": []}

        for bucket_name in [self.bucket_files, self.bucket_backups]:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    results["created"].append(bucket_name)
                else:
                    results["existing"].append(bucket_name)
            except S3Error as e:
                results["errors"].append({
                    "bucket": bucket_name,
                    "error": str(e),
                })

        return results

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to MinIO.

        Args:
            bucket_name: Target bucket
            object_name: Object name in bucket
            file_path: Local file path
            content_type: Optional content type

        Returns:
            Dict with upload result
        """
        try:
            result = self.client.fput_object(
                bucket_name,
                object_name,
                file_path,
                content_type=content_type,
            )

            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "etag": result.etag,
            }

        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def upload_data(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """
        Upload data stream to MinIO.

        Args:
            bucket_name: Target bucket
            object_name: Object name in bucket
            data: Data stream
            length: Data length in bytes
            content_type: Content type

        Returns:
            Dict with upload result
        """
        try:
            result = self.client.put_object(
                bucket_name,
                object_name,
                data,
                length,
                content_type=content_type,
            )

            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "etag": result.etag,
            }

        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def download_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Download a file from MinIO.

        Args:
            bucket_name: Source bucket
            object_name: Object name in bucket
            file_path: Local file path to save

        Returns:
            Dict with download result
        """
        try:
            self.client.fget_object(
                bucket_name,
                object_name,
                file_path,
            )

            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
                "path": file_path,
            }

        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_object(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Dict[str, Any]:
        """
        Get an object from MinIO.

        Args:
            bucket_name: Source bucket
            object_name: Object name in bucket

        Returns:
            Dict with object data
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            return {
                "success": True,
                "data": data,
                "bucket": bucket_name,
                "object": object_name,
            }

        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def delete_object(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Dict[str, Any]:
        """
        Delete an object from MinIO.

        Args:
            bucket_name: Target bucket
            object_name: Object name to delete

        Returns:
            Dict with deletion result
        """
        try:
            self.client.remove_object(bucket_name, object_name)

            return {
                "success": True,
                "bucket": bucket_name,
                "object": object_name,
            }

        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List objects in a bucket.

        Args:
            bucket_name: Target bucket
            prefix: Optional prefix filter
            recursive: List recursively

        Returns:
            List of object dictionaries
        """
        try:
            objects = self.client.list_objects(
                bucket_name,
                prefix=prefix,
                recursive=recursive,
            )

            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag,
                    "content_type": obj.content_type,
                }
                for obj in objects
            ]

        except S3Error:
            return []

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        Get presigned URL for temporary access.

        Args:
            bucket_name: Target bucket
            object_name: Object name
            expires: Expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL or None on error
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url

        except S3Error:
            return None

    def get_presigned_put_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        Get presigned PUT URL for direct upload.

        Args:
            bucket_name: Target bucket
            object_name: Object name
            expires: Expiration time in seconds (default: 1 hour)

        Returns:
            Presigned PUT URL or None on error
        """
        try:
            url = self.client.presigned_put_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url

        except S3Error:
            return None

    def get_object_stat(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get object metadata.

        Args:
            bucket_name: Target bucket
            object_name: Object name

        Returns:
            Dict with metadata or None on error
        """
        try:
            stat = self.client.stat_object(bucket_name, object_name)

            return {
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata,
            }

        except S3Error:
            return None


def get_minio_client() -> MinIOClient:
    """
    Get a configured MinIO client instance.

    Returns:
        MinIOClient instance
    """
    return MinIOClient()


def upload_file_to_minio(
    file_path: str,
    site_name: str,
    object_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to upload a file for a site.

    Args:
        file_path: Local file path
        site_name: Site name (for path prefix)
        object_name: Optional custom object name

    Returns:
        Dict with upload result
    """
    client = get_minio_client()

    # Generate object name if not provided
    if not object_name:
        object_name = f"{site_name}/files/{Path(file_path).name}"

    return client.upload_file(
        client.bucket_files,
        object_name,
        file_path,
    )


def upload_backup_to_minio(
    backup_path: str,
    site_name: str,
    backup_type: str = "database",
) -> Dict[str, Any]:
    """
    Convenience function to upload a backup to MinIO.

    Args:
        backup_path: Local backup file path
        site_name: Site name
        backup_type: Type of backup (database, files, etc.)

    Returns:
        Dict with upload result
    """
    client = get_minio_client()

    # Generate backup object name with timestamp
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = Path(backup_path).name
    object_name = f"{site_name}/backups/{backup_type}/{timestamp}/{backup_name}"

    return client.upload_file(
        client.bucket_backups,
        object_name,
        backup_path,
    )
