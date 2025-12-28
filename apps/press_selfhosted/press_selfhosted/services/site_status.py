"""
Site Status Tracker for Self-Hosted Mode

This module tracks and reports the status of tenant sites.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional, List
import subprocess
import json
from datetime import datetime
from enum import Enum


class SiteStatus(Enum):
    """Possible site statuses."""
    PENDING = "Pending"
    INSTALLING = "Installing"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    SUSPENDED = "Suspended"
    BROKEN = "Broken"
    ARCHIVED = "Archived"
    UNKNOWN = "Unknown"


class SiteStatusChecker:
    """
    Checks and reports site status.

    This class provides methods to determine the current status
    of tenant sites based on their database, files, and configuration.
    """

    def __init__(self):
        """Initialize the status checker."""
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )
        self.press_container = f"{self.container_prefix}-press"
        self.runtime = self._detect_runtime()

    def _detect_runtime(self) -> str:
        """Detect available container runtime."""
        for runtime in ["podman", "docker"]:
            try:
                result = subprocess.run(
                    [runtime, "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return runtime
            except FileNotFoundError:
                continue
        raise RuntimeError("Neither docker nor podman found")

    def get_status(self, site_name: str) -> Dict[str, Any]:
        """
        Get comprehensive status for a site.

        Args:
            site_name: Name of the site

        Returns:
            Dict with status information
        """
        status_info = {
            "site": site_name,
            "status": SiteStatus.UNKNOWN.value,
            "checks": {},
            "last_checked": datetime.utcnow().isoformat(),
        }

        # Check if site directory exists
        dir_check = self._check_site_directory(site_name)
        status_info["checks"]["directory"] = dir_check

        if not dir_check.get("exists"):
            status_info["status"] = SiteStatus.PENDING.value
            return status_info

        # Check if site config exists
        config_check = self._check_site_config(site_name)
        status_info["checks"]["config"] = config_check

        if not config_check.get("exists"):
            status_info["status"] = SiteStatus.INSTALLING.value
            return status_info

        # Check if database is accessible
        db_check = self._check_site_database(site_name)
        status_info["checks"]["database"] = db_check

        if not db_check.get("accessible"):
            status_info["status"] = SiteStatus.BROKEN.value
            return status_info

        # Check if site is suspended
        if config_check.get("maintenance_mode"):
            status_info["status"] = SiteStatus.SUSPENDED.value
            return status_info

        # Check site accessibility
        access_check = self._check_site_accessibility(site_name)
        status_info["checks"]["accessibility"] = access_check

        if access_check.get("accessible"):
            status_info["status"] = SiteStatus.ACTIVE.value
        else:
            status_info["status"] = SiteStatus.INACTIVE.value

        return status_info

    def _check_site_directory(self, site_name: str) -> Dict[str, Any]:
        """Check if site directory exists."""
        site_path = f"/home/frappe/frappe-bench/sites/{site_name}"

        result = subprocess.run(
            [self.runtime, "exec", self.press_container, "test", "-d", site_path],
            capture_output=True,
        )

        return {
            "exists": result.returncode == 0,
            "path": site_path,
        }

    def _check_site_config(self, site_name: str) -> Dict[str, Any]:
        """Check site configuration."""
        config_path = f"/home/frappe/frappe-bench/sites/{site_name}/site_config.json"

        result = subprocess.run(
            [self.runtime, "exec", self.press_container, "cat", config_path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return {
                "exists": False,
                "path": config_path,
            }

        try:
            config = json.loads(result.stdout)
            return {
                "exists": True,
                "path": config_path,
                "maintenance_mode": config.get("maintenance_mode", False),
                "has_encryption_key": "encryption_key" in config,
            }
        except json.JSONDecodeError:
            return {
                "exists": True,
                "valid": False,
                "error": "Invalid JSON",
            }

    def _check_site_database(self, site_name: str) -> Dict[str, Any]:
        """Check if site database is accessible."""
        from press_selfhosted.services.database_manager import DatabaseManager

        db_manager = DatabaseManager()
        db_name = db_manager._site_to_db_name(site_name)

        exists = db_manager.database_exists(db_name)

        return {
            "accessible": exists,
            "database": db_name,
        }

    def _check_site_accessibility(self, site_name: str) -> Dict[str, Any]:
        """Check if site is accessible via bench."""
        result = subprocess.run(
            [
                self.runtime, "exec", self.press_container,
                "bench", "--site", site_name, "doctor",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Doctor command returns status information
        output = result.stdout + result.stderr

        has_errors = "error" in output.lower() or "fail" in output.lower()

        return {
            "accessible": result.returncode == 0 and not has_errors,
            "doctor_output": output[:500] if output else None,
        }

    def get_all_sites_status(self) -> List[Dict[str, Any]]:
        """
        Get status for all sites.

        Returns:
            List of status dictionaries for each site
        """
        # Get list of sites
        result = subprocess.run(
            [
                self.runtime, "exec", self.press_container,
                "ls", "/home/frappe/frappe-bench/sites",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return []

        items = result.stdout.strip().split("\n")
        sites = [
            item for item in items
            if item and
            not item.startswith(".") and
            item not in ["apps.txt", "common_site_config.json", "assets"]
        ]

        statuses = []
        for site in sites:
            try:
                status = self.get_status(site)
                statuses.append(status)
            except Exception as e:
                statuses.append({
                    "site": site,
                    "status": SiteStatus.UNKNOWN.value,
                    "error": str(e),
                })

        return statuses

    def is_site_active(self, site_name: str) -> bool:
        """
        Quick check if a site is active.

        Args:
            site_name: Name of the site

        Returns:
            True if site is active
        """
        status = self.get_status(site_name)
        return status.get("status") == SiteStatus.ACTIVE.value

    def get_site_uptime(self, site_name: str) -> Optional[float]:
        """
        Get site uptime in seconds.

        This is approximated based on the site directory's modification time.

        Args:
            site_name: Name of the site

        Returns:
            Uptime in seconds or None if not available
        """
        site_path = f"/home/frappe/frappe-bench/sites/{site_name}"

        result = subprocess.run(
            [
                self.runtime, "exec", self.press_container,
                "stat", "-c", "%Y", site_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            try:
                mtime = int(result.stdout.strip())
                now = int(datetime.utcnow().timestamp())
                return now - mtime
            except ValueError:
                pass

        return None


def get_site_status(site_name: str) -> Dict[str, Any]:
    """
    Convenience function to get site status.

    Args:
        site_name: Name of the site

    Returns:
        Dict with status information
    """
    checker = SiteStatusChecker()
    return checker.get_status(site_name)


def list_all_sites_with_status() -> List[Dict[str, Any]]:
    """
    List all sites with their status.

    Returns:
        List of site status dictionaries
    """
    checker = SiteStatusChecker()
    return checker.get_all_sites_status()
