"""
Installation and migration hooks for Press Self-Hosted

This module handles app installation, uninstallation, and migration events.
"""

import frappe


def after_install():
    """
    Called after press_selfhosted app is installed.

    Sets up:
    - Default storage configuration for MinIO
    - Local registry configuration
    - Self-hosted specific settings
    """
    try:
        setup_storage_configuration()
        setup_default_settings()
        frappe.db.commit()
        print("Press Self-Hosted: Installation complete")
    except Exception as e:
        print(f"Press Self-Hosted: Installation warning - {e}")
        # Don't fail installation on non-critical errors


def setup_storage_configuration():
    """
    Configure default S3/MinIO storage settings.

    Reads from environment or uses defaults.
    """
    import os

    # Check if storage_integration is available
    if "storage_integration" not in frappe.get_installed_apps():
        print("Press Self-Hosted: storage_integration not installed, skipping storage setup")
        return

    # Get MinIO settings from environment
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "http://erp-saas-cloud-c16-minio:9000")
    minio_access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    minio_secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "")
    minio_bucket = os.environ.get("MINIO_BUCKET_FILES", "erp-saas-cloud-c16-files")

    # Update site config with MinIO settings
    frappe.conf.s3_endpoint_url = minio_endpoint
    frappe.conf.s3_access_key_id = minio_access_key
    frappe.conf.s3_secret_access_key = minio_secret_key
    frappe.conf.s3_bucket = minio_bucket
    frappe.conf.s3_force_path_style = True
    frappe.conf.s3_region = "us-east-1"

    print(f"Press Self-Hosted: Storage configured for MinIO at {minio_endpoint}")


def setup_default_settings():
    """
    Configure default Press settings for self-hosted mode.
    """
    # Set self-hosted mode flag
    frappe.conf.press_self_hosted = True

    # Disable cloud provider integrations
    frappe.conf.disable_cloud_providers = True

    # Set container prefix for validation
    frappe.conf.container_prefix = "erp-saas-cloud-c16-"

    print("Press Self-Hosted: Default settings configured")


def before_uninstall():
    """
    Called before press_selfhosted app is uninstalled.

    Cleanup tasks if needed.
    """
    print("Press Self-Hosted: Preparing for uninstall")


def after_migrate():
    """
    Called after database migration.

    Updates any settings that may have changed.
    """
    try:
        setup_storage_configuration()
        frappe.db.commit()
        print("Press Self-Hosted: Migration complete")
    except Exception as e:
        print(f"Press Self-Hosted: Migration warning - {e}")
