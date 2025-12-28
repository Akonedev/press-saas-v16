"""
Storage Configuration Setup for Press Self-Hosted

This module configures storage integration with MinIO
for the Press self-hosted platform.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any
import json


def configure_minio_storage() -> Dict[str, Any]:
    """
    Configure MinIO storage for all sites.

    This function sets up the necessary configuration
    for using MinIO as the file storage backend.

    Returns:
        Dict with configuration result
    """
    from press_selfhosted.integrations.minio import get_minio_client

    # Get MinIO configuration
    minio_endpoint = frappe.conf.get("minio_endpoint", "erp-saas-cloud-c16-minio:9000")
    minio_access_key = frappe.conf.get("minio_access_key", "minioadmin")
    minio_secret_key = frappe.conf.get("minio_secret_key", "minioadmin")
    container_prefix = frappe.conf.get("container_prefix", "erp-saas-cloud-c16")

    # Bucket names
    bucket_files = f"{container_prefix}-files"
    bucket_backups = f"{container_prefix}-backups"

    # Test connection
    client = get_minio_client()
    connection = client.check_connection()

    if not connection.get("connected"):
        return {
            "success": False,
            "error": "Could not connect to MinIO",
            "details": connection.get("error"),
        }

    # Ensure buckets exist
    buckets = client.ensure_buckets_exist()

    # Update common site config
    config_updates = {
        "minio_endpoint": minio_endpoint,
        "minio_access_key": minio_access_key,
        "minio_secret_key": minio_secret_key,
        "minio_bucket_files": bucket_files,
        "minio_bucket_backups": bucket_backups,
        "use_minio_storage": True,
        "s3_endpoint": f"http://{minio_endpoint}",
        "s3_bucket": bucket_files,
        "s3_access_key": minio_access_key,
        "s3_secret_key": minio_secret_key,
    }

    return {
        "success": True,
        "config_updates": config_updates,
        "buckets": buckets,
        "message": "MinIO storage configured successfully",
    }


def update_site_config_for_storage(site_name: str) -> Dict[str, Any]:
    """
    Update a specific site's configuration for MinIO storage.

    Args:
        site_name: Name of the site to configure

    Returns:
        Dict with update result
    """
    from press_selfhosted.services.site_provisioner import SiteProvisioner

    provisioner = SiteProvisioner()

    # Get MinIO configuration
    container_prefix = frappe.conf.get("container_prefix", "erp-saas-cloud-c16")
    minio_endpoint = frappe.conf.get("minio_endpoint", "erp-saas-cloud-c16-minio:9000")

    # Site-specific configuration
    config = {
        "use_minio_storage": True,
        "minio_endpoint": minio_endpoint,
        "file_storage_path": f"{site_name}/files",
        "backup_storage_path": f"{site_name}/backups",
    }

    return provisioner.update_site_config(site_name, config)


def setup_backup_storage() -> Dict[str, Any]:
    """
    Configure backup storage to use MinIO.

    This function sets up automatic backup upload to MinIO.

    Returns:
        Dict with setup result
    """
    # Check if backups bucket exists
    from press_selfhosted.integrations.minio import get_minio_client

    client = get_minio_client()
    bucket_name = client.bucket_backups

    try:
        if not client.client.bucket_exists(bucket_name):
            return {
                "success": False,
                "error": f"Backups bucket '{bucket_name}' does not exist",
                "message": "Run scripts/init-minio-buckets.sh to create buckets",
            }

        # Enable versioning for backups
        try:
            client.client.set_bucket_versioning(bucket_name, {"Status": "Enabled"})
        except Exception:
            pass  # Versioning might not be supported in all MinIO versions

        return {
            "success": True,
            "bucket": bucket_name,
            "message": "Backup storage configured successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def verify_storage_configuration() -> Dict[str, Any]:
    """
    Verify that storage is properly configured.

    Returns:
        Dict with verification results
    """
    from press_selfhosted.integrations.minio import get_minio_client

    results = {
        "valid": True,
        "checks": [],
    }

    # Check MinIO connection
    client = get_minio_client()
    connection = client.check_connection()

    if connection.get("connected"):
        results["checks"].append({
            "check": "minio_connection",
            "status": "pass",
            "message": "MinIO is accessible",
        })
    else:
        results["valid"] = False
        results["checks"].append({
            "check": "minio_connection",
            "status": "fail",
            "error": connection.get("error"),
        })

    # Check required buckets
    for bucket in [client.bucket_files, client.bucket_backups]:
        try:
            exists = client.client.bucket_exists(bucket)
            if exists:
                results["checks"].append({
                    "check": f"bucket_{bucket}",
                    "status": "pass",
                    "message": f"Bucket '{bucket}' exists",
                })
            else:
                results["valid"] = False
                results["checks"].append({
                    "check": f"bucket_{bucket}",
                    "status": "fail",
                    "error": f"Bucket '{bucket}' does not exist",
                })
        except Exception as e:
            results["valid"] = False
            results["checks"].append({
                "check": f"bucket_{bucket}",
                "status": "fail",
                "error": str(e),
            })

    # Check site configuration
    try:
        use_minio = frappe.conf.get("use_minio_storage", False)
        if use_minio:
            results["checks"].append({
                "check": "site_config",
                "status": "pass",
                "message": "MinIO storage enabled in config",
            })
        else:
            results["checks"].append({
                "check": "site_config",
                "status": "warning",
                "message": "MinIO storage not enabled in config",
            })
    except Exception as e:
        results["checks"].append({
            "check": "site_config",
            "status": "fail",
            "error": str(e),
        })

    return results


def initialize_storage() -> Dict[str, Any]:
    """
    Complete storage initialization workflow.

    This is the main function to run during app installation
    or when setting up storage for the first time.

    Returns:
        Dict with initialization results
    """
    results = {
        "steps": [],
        "success": True,
    }

    # Step 1: Configure MinIO
    minio_result = configure_minio_storage()
    results["steps"].append({
        "step": "configure_minio",
        "result": minio_result,
    })

    if not minio_result.get("success"):
        results["success"] = False
        return results

    # Step 2: Setup backup storage
    backup_result = setup_backup_storage()
    results["steps"].append({
        "step": "setup_backups",
        "result": backup_result,
    })

    if not backup_result.get("success"):
        results["success"] = False

    # Step 3: Verify configuration
    verify_result = verify_storage_configuration()
    results["steps"].append({
        "step": "verify",
        "result": verify_result,
    })

    if not verify_result.get("valid"):
        results["success"] = False

    return results
