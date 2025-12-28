"""
Backup Override for Self-Hosted Mode

This module extends Frappe backup functionality to automatically
upload backups to MinIO storage.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional, List
import os
from pathlib import Path
from datetime import datetime


class SelfHostedBackup:
    """
    Handles backup operations with MinIO integration.

    This class extends standard Frappe backup to automatically
    upload completed backups to MinIO storage.
    """

    def __init__(self, site_name: Optional[str] = None):
        """
        Initialize backup handler.

        Args:
            site_name: Site name (defaults to current site)
        """
        self.site_name = site_name or frappe.local.site

    def create_backup(
        self,
        with_files: bool = False,
        upload_to_minio: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a backup and optionally upload to MinIO.

        Args:
            with_files: Include files in backup
            upload_to_minio: Upload to MinIO after creation

        Returns:
            Dict with backup details
        """
        from press_selfhosted.services.site_provisioner import SiteProvisioner

        provisioner = SiteProvisioner()

        # Trigger bench backup command
        command = ["backup"]
        if with_files:
            command.append("--with-files")

        result = provisioner._exec_in_container(
            provisioner.press_container,
            ["bench", "--site", self.site_name] + command,
            timeout=600,  # 10 minutes for large backups
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error"),
                "step": "create_backup",
            }

        # Parse backup output to get file paths
        backup_info = self._parse_backup_output(result.get("output", ""))

        # Upload to MinIO if requested
        if upload_to_minio:
            upload_result = self.upload_backups_to_minio(backup_info)
            backup_info["minio_upload"] = upload_result

        return {
            "success": True,
            "backup": backup_info,
        }

    def _parse_backup_output(self, output: str) -> Dict[str, Any]:
        """
        Parse backup command output to extract file paths.

        Args:
            output: Backup command output

        Returns:
            Dict with backup file information
        """
        import re

        info = {
            "timestamp": datetime.utcnow().isoformat(),
            "files": [],
        }

        # Extract database backup path
        db_match = re.search(r"database.*?:\s*(.+\.sql\.gz)", output, re.IGNORECASE)
        if db_match:
            info["database"] = db_match.group(1).strip()
            info["files"].append(db_match.group(1).strip())

        # Extract files backup path
        files_match = re.search(r"(public|private) files.*?:\s*(.+\.tar)", output, re.IGNORECASE)
        if files_match:
            info["files_backup"] = files_match.group(2).strip()
            info["files"].append(files_match.group(2).strip())

        return info

    def upload_backups_to_minio(
        self,
        backup_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Upload backup files to MinIO.

        Args:
            backup_info: Backup information with file paths

        Returns:
            Dict with upload results
        """
        from press_selfhosted.integrations.minio import upload_backup_to_minio

        results = {
            "uploaded": [],
            "errors": [],
        }

        # Upload each backup file
        for file_path in backup_info.get("files", []):
            # Determine backup type
            if ".sql" in file_path:
                backup_type = "database"
            elif ".tar" in file_path:
                backup_type = "files"
            else:
                backup_type = "other"

            # Upload to MinIO
            upload_result = upload_backup_to_minio(
                file_path,
                self.site_name,
                backup_type=backup_type,
            )

            if upload_result.get("success"):
                results["uploaded"].append({
                    "local_path": file_path,
                    "object_name": upload_result.get("object"),
                    "type": backup_type,
                })
            else:
                results["errors"].append({
                    "file": file_path,
                    "error": upload_result.get("error"),
                })

        return results

    def list_available_backups(self) -> List[Dict[str, Any]]:
        """
        List available backups in MinIO for this site.

        Returns:
            List of backup dictionaries
        """
        from press_selfhosted.integrations.minio import get_minio_client

        client = get_minio_client()
        prefix = f"{self.site_name}/backups/"

        backups = client.list_objects(
            client.bucket_backups,
            prefix=prefix,
        )

        return backups

    def restore_from_backup(
        self,
        backup_object_name: str,
        download_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Restore a site from a MinIO backup.

        Args:
            backup_object_name: Object name in MinIO
            download_path: Optional local download path

        Returns:
            Dict with restore result
        """
        from press_selfhosted.integrations.minio import get_minio_client
        from press_selfhosted.services.site_provisioner import SiteProvisioner

        client = get_minio_client()
        provisioner = SiteProvisioner()

        # Download backup from MinIO
        if not download_path:
            download_path = f"/tmp/{Path(backup_object_name).name}"

        download_result = client.download_file(
            client.bucket_backups,
            backup_object_name,
            download_path,
        )

        if not download_result.get("success"):
            return {
                "success": False,
                "error": "Failed to download backup",
                "details": download_result.get("error"),
            }

        # Restore using bench
        restore_result = provisioner._exec_in_container(
            provisioner.press_container,
            [
                "bench", "--site", self.site_name,
                "restore", download_path,
            ],
            timeout=1200,  # 20 minutes for large restores
        )

        # Cleanup downloaded file
        try:
            os.remove(download_path)
        except Exception:
            pass

        if restore_result.get("success"):
            return {
                "success": True,
                "message": f"Site '{self.site_name}' restored from backup",
            }

        return {
            "success": False,
            "error": restore_result.get("error"),
        }

    def cleanup_old_backups(
        self,
        keep_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Cleanup backups older than specified days.

        Args:
            keep_days: Number of days to keep backups

        Returns:
            Dict with cleanup results
        """
        from press_selfhosted.integrations.minio import get_minio_client
        from datetime import datetime, timedelta

        client = get_minio_client()
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)

        # Get all backups for this site
        backups = self.list_available_backups()

        results = {
            "deleted": [],
            "kept": [],
            "errors": [],
        }

        for backup in backups:
            # Parse last modified date
            last_modified = backup.get("last_modified")
            if last_modified:
                backup_date = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))

                if backup_date < cutoff_date:
                    # Delete old backup
                    delete_result = client.delete_object(
                        client.bucket_backups,
                        backup["name"],
                    )

                    if delete_result.get("success"):
                        results["deleted"].append(backup["name"])
                    else:
                        results["errors"].append({
                            "backup": backup["name"],
                            "error": delete_result.get("error"),
                        })
                else:
                    results["kept"].append(backup["name"])

        return results


def create_backup(
    site_name: Optional[str] = None,
    with_files: bool = False,
    upload_to_minio: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to create a backup.

    Args:
        site_name: Site name (defaults to current site)
        with_files: Include files in backup
        upload_to_minio: Upload to MinIO

    Returns:
        Dict with backup result
    """
    backup = SelfHostedBackup(site_name)
    return backup.create_backup(with_files, upload_to_minio)


def restore_backup(
    site_name: str,
    backup_object_name: str,
) -> Dict[str, Any]:
    """
    Convenience function to restore from backup.

    Args:
        site_name: Site name
        backup_object_name: Backup object in MinIO

    Returns:
        Dict with restore result
    """
    backup = SelfHostedBackup(site_name)
    return backup.restore_from_backup(backup_object_name)
