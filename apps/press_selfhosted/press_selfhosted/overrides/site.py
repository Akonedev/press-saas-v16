"""
Site DocType Override for Self-Hosted Mode

This module extends the Press Site DocType to support local provisioning
instead of cloud-based deployment.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
from typing import Optional, Dict, Any
import subprocess
import os


class SelfHostedSite:
    """
    Mixin class for Site DocType to support self-hosted operations.

    This class provides methods that override cloud-based operations
    with local Docker/Podman equivalents.
    """

    def __init__(self, site_doc):
        """
        Initialize with a Site document.

        Args:
            site_doc: The Frappe Site document
        """
        self.site = site_doc
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )

    def provision_local(self) -> Dict[str, Any]:
        """
        Provision a new site locally instead of on cloud.

        Returns:
            Dict with provisioning result including status and any errors
        """
        from press_selfhosted.services.site_provisioner import SiteProvisioner
        from press_selfhosted.services.database_manager import DatabaseManager

        result = {
            "site": self.site.name,
            "status": "Pending",
            "steps": [],
            "errors": [],
        }

        try:
            # Step 1: Create database for the site
            db_manager = DatabaseManager()
            db_result = db_manager.create_database(self.site.name)

            if db_result.get("success"):
                result["steps"].append({
                    "step": "create_database",
                    "status": "success",
                    "database": db_result.get("database"),
                })
            else:
                result["errors"].append({
                    "step": "create_database",
                    "error": db_result.get("error"),
                })
                result["status"] = "Failed"
                return result

            # Step 2: Create site directory and config
            provisioner = SiteProvisioner()
            site_result = provisioner.create_site(
                site_name=self.site.name,
                database=db_result.get("database"),
                admin_password=self.site.get("admin_password") or "admin",
            )

            if site_result.get("success"):
                result["steps"].append({
                    "step": "create_site",
                    "status": "success",
                })
                result["status"] = "Installing"
            else:
                result["errors"].append({
                    "step": "create_site",
                    "error": site_result.get("error"),
                })
                result["status"] = "Failed"
                return result

            # Step 3: Install apps
            apps_to_install = self.site.get("apps") or ["frappe"]
            for app in apps_to_install:
                app_result = provisioner.install_app(self.site.name, app)
                if app_result.get("success"):
                    result["steps"].append({
                        "step": f"install_app_{app}",
                        "status": "success",
                    })
                else:
                    result["errors"].append({
                        "step": f"install_app_{app}",
                        "error": app_result.get("error"),
                    })

            # Mark as active if all steps succeeded
            if not result["errors"]:
                result["status"] = "Active"

        except Exception as e:
            result["errors"].append({
                "step": "provision_local",
                "error": str(e),
            })
            result["status"] = "Broken"

        return result

    def get_local_status(self) -> Dict[str, Any]:
        """
        Get the status of a locally provisioned site.

        Returns:
            Dict with site status information
        """
        from press_selfhosted.services.site_status import SiteStatusChecker

        checker = SiteStatusChecker()
        return checker.get_status(self.site.name)

    def suspend_local(self) -> Dict[str, Any]:
        """
        Suspend a locally provisioned site.

        Returns:
            Dict with operation result
        """
        from press_selfhosted.services.site_operations import SiteOperations

        operations = SiteOperations()
        return operations.suspend_site(self.site.name)

    def unsuspend_local(self) -> Dict[str, Any]:
        """
        Unsuspend a locally provisioned site.

        Returns:
            Dict with operation result
        """
        from press_selfhosted.services.site_operations import SiteOperations

        operations = SiteOperations()
        return operations.unsuspend_site(self.site.name)

    def archive_local(self) -> Dict[str, Any]:
        """
        Archive a locally provisioned site.

        This removes the site but keeps backups.

        Returns:
            Dict with operation result
        """
        from press_selfhosted.services.site_operations import SiteOperations
        from press_selfhosted.services.backup_service import BackupService

        # Create final backup before archiving
        backup_service = BackupService()
        backup_result = backup_service.create_backup(self.site.name)

        operations = SiteOperations()
        return operations.archive_site(self.site.name)


def override_site_methods():
    """
    Override Press Site DocType methods for self-hosted mode.

    This function is called during app installation to patch
    the Site DocType with self-hosted methods.
    """
    try:
        from press.press.doctype.site.site import Site

        # Store original methods
        Site._original_provision = getattr(Site, "provision", None)

        def selfhosted_provision(self):
            """Provision site locally in self-hosted mode."""
            if frappe.conf.get("press_selfhosted_mode"):
                selfhosted = SelfHostedSite(self)
                return selfhosted.provision_local()
            elif self._original_provision:
                return self._original_provision()

        Site.provision = selfhosted_provision

        frappe.logger().info("Site DocType methods overridden for self-hosted mode")

    except ImportError:
        frappe.logger().warning(
            "Press app not installed, Site override not applied"
        )


def get_selfhosted_site(site_name: str) -> Optional[SelfHostedSite]:
    """
    Get a SelfHostedSite wrapper for a given site.

    Args:
        site_name: The name of the site document

    Returns:
        SelfHostedSite instance or None if site not found
    """
    try:
        site_doc = frappe.get_doc("Site", site_name)
        return SelfHostedSite(site_doc)
    except frappe.DoesNotExistError:
        return None
