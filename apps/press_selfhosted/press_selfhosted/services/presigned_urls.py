"""
Presigned URL Generator for MinIO

This module generates temporary presigned URLs for secure
file access without exposing MinIO credentials.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class PresignedURLGenerator:
    """
    Generates presigned URLs for MinIO objects.

    Presigned URLs allow temporary access to private objects
    without requiring authentication credentials.
    """

    def __init__(self):
        """Initialize the presigned URL generator."""
        from press_selfhosted.integrations.minio import get_minio_client

        self.client = get_minio_client()

    def generate_download_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Generate a presigned URL for downloading an object.

        Args:
            bucket_name: Target bucket
            object_name: Object name
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL or None on error
        """
        return self.client.get_presigned_url(
            bucket_name,
            object_name,
            expires=expires_in,
        )

    def generate_upload_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Generate a presigned URL for uploading an object.

        Args:
            bucket_name: Target bucket
            object_name: Object name
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned PUT URL or None on error
        """
        return self.client.get_presigned_put_url(
            bucket_name,
            object_name,
            expires=expires_in,
        )

    def generate_file_url(
        self,
        site_name: str,
        file_path: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Generate a presigned URL for a site file.

        Args:
            site_name: Site name
            file_path: File path relative to site
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL or None on error
        """
        object_name = f"{site_name}/files/{file_path}"

        return self.generate_download_url(
            self.client.bucket_files,
            object_name,
            expires_in=expires_in,
        )

    def generate_backup_url(
        self,
        site_name: str,
        backup_name: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Generate a presigned URL for a backup file.

        Args:
            site_name: Site name
            backup_name: Backup file name
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL or None on error
        """
        # Find backup object in MinIO
        backups = self.client.list_objects(
            self.client.bucket_backups,
            prefix=f"{site_name}/backups/",
        )

        # Find matching backup
        for backup in backups:
            if backup_name in backup["name"]:
                return self.generate_download_url(
                    self.client.bucket_backups,
                    backup["name"],
                    expires_in=expires_in,
                )

        return None

    def generate_temporary_upload_url(
        self,
        site_name: str,
        filename: str,
        expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """
        Generate a temporary upload URL for direct client uploads.

        This allows clients to upload directly to MinIO without
        going through the application server.

        Args:
            site_name: Site name
            filename: Name of the file to upload
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Dict with upload URL and metadata
        """
        from datetime import datetime

        # Generate unique object name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        object_name = f"{site_name}/uploads/{timestamp}/{filename}"

        # Generate presigned PUT URL
        url = self.generate_upload_url(
            self.client.bucket_files,
            object_name,
            expires_in=expires_in,
        )

        if url:
            return {
                "success": True,
                "upload_url": url,
                "object_name": object_name,
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=expires_in)
                ).isoformat(),
                "method": "PUT",
            }

        return {
            "success": False,
            "error": "Failed to generate upload URL",
        }

    def generate_batch_download_urls(
        self,
        bucket_name: str,
        object_names: list,
        expires_in: int = 3600,
    ) -> Dict[str, str]:
        """
        Generate presigned URLs for multiple objects.

        Args:
            bucket_name: Target bucket
            object_names: List of object names
            expires_in: URL expiration in seconds

        Returns:
            Dict mapping object names to presigned URLs
        """
        urls = {}

        for object_name in object_names:
            url = self.generate_download_url(
                bucket_name,
                object_name,
                expires_in=expires_in,
            )

            if url:
                urls[object_name] = url

        return urls


def get_file_url(
    site_name: str,
    file_path: str,
    expires_in: int = 3600,
) -> Optional[str]:
    """
    Convenience function to get a file download URL.

    Args:
        site_name: Site name
        file_path: File path
        expires_in: Expiration time in seconds

    Returns:
        Presigned URL or None
    """
    generator = PresignedURLGenerator()
    return generator.generate_file_url(site_name, file_path, expires_in)


def get_backup_url(
    site_name: str,
    backup_name: str,
    expires_in: int = 3600,
) -> Optional[str]:
    """
    Convenience function to get a backup download URL.

    Args:
        site_name: Site name
        backup_name: Backup file name
        expires_in: Expiration time in seconds

    Returns:
        Presigned URL or None
    """
    generator = PresignedURLGenerator()
    return generator.generate_backup_url(site_name, backup_name, expires_in)


def generate_upload_url(
    site_name: str,
    filename: str,
    expires_in: int = 3600,
) -> Dict[str, Any]:
    """
    Convenience function to generate an upload URL.

    Args:
        site_name: Site name
        filename: File name
        expires_in: Expiration time in seconds

    Returns:
        Dict with upload URL and metadata
    """
    generator = PresignedURLGenerator()
    return generator.generate_temporary_upload_url(site_name, filename, expires_in)
