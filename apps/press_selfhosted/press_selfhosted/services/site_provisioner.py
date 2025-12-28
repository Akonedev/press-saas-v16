"""
Site Provisioner for Self-Hosted Mode

This module handles the local provisioning of new tenant sites,
replacing cloud-based provisioning with Docker/Podman operations.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional, List
import subprocess
import os
import json
from pathlib import Path


class SiteProvisioner:
    """
    Handles local site provisioning for self-hosted Press.

    This class replaces cloud-based site provisioning with local
    operations using bench CLI and Docker containers.
    """

    def __init__(self):
        """Initialize the site provisioner."""
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )
        self.press_container = f"{self.container_prefix}-press"
        self.mariadb_container = f"{self.container_prefix}-mariadb"
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

    def _exec_in_container(
        self,
        container: str,
        command: List[str],
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command inside a container.

        Args:
            container: Container name
            command: Command to execute as list
            timeout: Timeout in seconds
            env: Optional environment variables

        Returns:
            Dict with success, output, and error
        """
        full_command = [self.runtime, "exec"]

        if env:
            for key, value in env.items():
                full_command.extend(["-e", f"{key}={value}"])

        full_command.append(container)
        full_command.extend(command)

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "return_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "return_code": -1,
            }

    def validate_site_name(self, site_name: str) -> Dict[str, Any]:
        """
        Validate a site name.

        Args:
            site_name: The proposed site name

        Returns:
            Dict with valid status and any error message
        """
        import re

        # Site name requirements
        if not site_name:
            return {"valid": False, "error": "Site name is required"}

        if len(site_name) > 63:
            return {"valid": False, "error": "Site name too long (max 63 chars)"}

        # Must be valid hostname
        pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$"
        if not re.match(pattern, site_name.lower()):
            return {
                "valid": False,
                "error": "Site name must be a valid hostname (lowercase, alphanumeric, hyphens)",
            }

        # Check if site already exists
        sites = self.list_sites()
        if site_name in sites:
            return {"valid": False, "error": f"Site '{site_name}' already exists"}

        return {"valid": True}

    def list_sites(self) -> List[str]:
        """
        List all existing sites.

        Returns:
            List of site names
        """
        result = self._exec_in_container(
            self.press_container,
            ["ls", "/home/frappe/frappe-bench/sites"],
        )

        if result.get("success"):
            items = result["output"].strip().split("\n")
            return [
                item for item in items
                if item and
                not item.startswith(".") and
                item not in ["apps.txt", "common_site_config.json", "assets"]
            ]

        return []

    def create_site(
        self,
        site_name: str,
        database: str,
        admin_password: str = "admin",
        apps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new site.

        Args:
            site_name: Name of the site to create
            database: Database name (created by DatabaseManager)
            admin_password: Admin password for the site
            apps: List of apps to install (optional)

        Returns:
            Dict with success status and details
        """
        # Validate site name
        validation = self.validate_site_name(site_name)
        if not validation.get("valid"):
            return {
                "success": False,
                "error": validation.get("error"),
            }

        # Get database credentials
        db_root_password = frappe.conf.get("mariadb_root_password", "")
        if not db_root_password:
            return {
                "success": False,
                "error": "MariaDB root password not configured",
            }

        # Create site using bench
        result = self._exec_in_container(
            self.press_container,
            [
                "bench", "new-site", site_name,
                "--mariadb-root-password", db_root_password,
                "--admin-password", admin_password,
                "--no-mariadb-socket",
            ],
            timeout=600,  # 10 minutes for site creation
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error"),
                "step": "create_site",
            }

        # Install additional apps if specified
        if apps:
            for app in apps:
                if app == "frappe":
                    continue  # frappe is installed by default

                app_result = self.install_app(site_name, app)
                if not app_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to install {app}: {app_result.get('error')}",
                        "step": f"install_app_{app}",
                    }

        return {
            "success": True,
            "site": site_name,
            "database": database,
            "apps": apps or ["frappe"],
        }

    def install_app(self, site_name: str, app_name: str) -> Dict[str, Any]:
        """
        Install an app on a site.

        Args:
            site_name: Name of the site
            app_name: Name of the app to install

        Returns:
            Dict with success status
        """
        # First check if app is available in bench
        available = self._exec_in_container(
            self.press_container,
            ["bench", "list-apps"],
        )

        if available.get("success"):
            if app_name not in available.get("output", ""):
                return {
                    "success": False,
                    "error": f"App '{app_name}' not available in bench",
                }

        # Install the app
        result = self._exec_in_container(
            self.press_container,
            ["bench", "--site", site_name, "install-app", app_name],
            timeout=600,
        )

        return {
            "success": result.get("success"),
            "error": result.get("error"),
            "app": app_name,
            "site": site_name,
        }

    def get_site_config(self, site_name: str) -> Dict[str, Any]:
        """
        Get the site configuration.

        Args:
            site_name: Name of the site

        Returns:
            Dict with site configuration
        """
        config_path = f"/home/frappe/frappe-bench/sites/{site_name}/site_config.json"

        result = self._exec_in_container(
            self.press_container,
            ["cat", config_path],
        )

        if result.get("success"):
            try:
                return json.loads(result["output"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON in site config"}

        return {"error": result.get("error")}

    def update_site_config(
        self,
        site_name: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update site configuration.

        Args:
            site_name: Name of the site
            config: Configuration dict to merge

        Returns:
            Dict with success status
        """
        for key, value in config.items():
            result = self._exec_in_container(
                self.press_container,
                [
                    "bench", "--site", site_name,
                    "set-config", key, json.dumps(value),
                ],
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to set {key}: {result.get('error')}",
                }

        return {"success": True}

    def delete_site(self, site_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a site.

        Args:
            site_name: Name of the site to delete
            force: If True, skip confirmation

        Returns:
            Dict with success status
        """
        command = ["bench", "drop-site", site_name]

        if force:
            command.append("--force")

        # Get DB root password for dropping database
        db_root_password = frappe.conf.get("mariadb_root_password", "")
        if db_root_password:
            command.extend(["--mariadb-root-password", db_root_password])

        result = self._exec_in_container(
            self.press_container,
            command,
            timeout=300,
        )

        return {
            "success": result.get("success"),
            "error": result.get("error"),
            "site": site_name,
        }


def create_site(
    site_name: str,
    admin_password: str = "admin",
    apps: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to create a new site.

    Args:
        site_name: Name of the site
        admin_password: Admin password
        apps: List of apps to install

    Returns:
        Dict with creation result
    """
    from press_selfhosted.services.database_manager import DatabaseManager

    # Create database first
    db_manager = DatabaseManager()
    db_result = db_manager.create_database(site_name)

    if not db_result.get("success"):
        return db_result

    # Then create site
    provisioner = SiteProvisioner()
    return provisioner.create_site(
        site_name=site_name,
        database=db_result.get("database"),
        admin_password=admin_password,
        apps=apps,
    )
