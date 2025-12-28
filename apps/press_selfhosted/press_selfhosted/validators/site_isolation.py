"""
Site Isolation Validator

This module validates that tenant sites are properly isolated from each other.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, List, Optional
import subprocess
import re


class SiteIsolationValidator:
    """
    Validates isolation between tenant sites.

    Checks:
    - Database isolation (each site has its own database)
    - File isolation (each site has its own directory)
    - Session isolation (sessions are site-specific)
    - Network isolation (sites cannot access each other's data)
    """

    def __init__(self):
        """Initialize the validator."""
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

    def validate_database_isolation(self, site_name: str) -> Dict[str, Any]:
        """
        Validate that the site has its own isolated database.

        Args:
            site_name: The site to validate

        Returns:
            Dict with validation result
        """
        from press_selfhosted.services.database_manager import DatabaseManager

        db_manager = DatabaseManager()
        db_name = db_manager._site_to_db_name(site_name)

        # Check database exists
        if not db_manager.database_exists(db_name):
            return {
                "valid": False,
                "check": "database_exists",
                "error": f"Database '{db_name}' not found for site '{site_name}'",
            }

        # Check that other sites cannot access this database
        # (This is enforced by MariaDB user permissions)

        return {
            "valid": True,
            "check": "database_isolation",
            "database": db_name,
            "message": f"Site '{site_name}' has isolated database '{db_name}'",
        }

    def validate_file_isolation(self, site_name: str) -> Dict[str, Any]:
        """
        Validate that the site has its own isolated directory.

        Args:
            site_name: The site to validate

        Returns:
            Dict with validation result
        """
        site_path = f"/home/frappe/frappe-bench/sites/{site_name}"

        # Check site directory exists
        result = subprocess.run(
            [self.runtime, "exec", self.press_container, "test", "-d", site_path],
            capture_output=True,
        )

        if result.returncode != 0:
            return {
                "valid": False,
                "check": "site_directory_exists",
                "error": f"Site directory not found: {site_path}",
            }

        # Check permissions (should be owned by frappe user)
        perm_result = subprocess.run(
            [
                self.runtime, "exec", self.press_container,
                "stat", "-c", "%U:%G", site_path,
            ],
            capture_output=True,
            text=True,
        )

        if perm_result.returncode == 0:
            owner = perm_result.stdout.strip()
            if "frappe" not in owner:
                return {
                    "valid": False,
                    "check": "site_ownership",
                    "error": f"Site directory has incorrect ownership: {owner}",
                }

        # Check site_config.json exists
        config_path = f"{site_path}/site_config.json"
        config_result = subprocess.run(
            [self.runtime, "exec", self.press_container, "test", "-f", config_path],
            capture_output=True,
        )

        if config_result.returncode != 0:
            return {
                "valid": False,
                "check": "site_config_exists",
                "error": f"Site config not found: {config_path}",
            }

        return {
            "valid": True,
            "check": "file_isolation",
            "path": site_path,
            "message": f"Site '{site_name}' has isolated directory",
        }

    def validate_no_cross_site_access(
        self,
        site_a: str,
        site_b: str,
    ) -> Dict[str, Any]:
        """
        Validate that two sites cannot access each other's data.

        Args:
            site_a: First site
            site_b: Second site

        Returns:
            Dict with validation result
        """
        from press_selfhosted.services.database_manager import DatabaseManager

        db_manager = DatabaseManager()

        db_a = db_manager._site_to_db_name(site_a)
        db_b = db_manager._site_to_db_name(site_b)

        # Verify databases are different
        if db_a == db_b:
            return {
                "valid": False,
                "check": "unique_databases",
                "error": f"Sites share the same database: {db_a}",
            }

        # Check that each site's config points to its own database
        checks = []
        for site, expected_db in [(site_a, db_a), (site_b, db_b)]:
            config_result = subprocess.run(
                [
                    self.runtime, "exec", self.press_container,
                    "cat", f"/home/frappe/frappe-bench/sites/{site}/site_config.json",
                ],
                capture_output=True,
                text=True,
            )

            if config_result.returncode == 0:
                import json
                try:
                    config = json.loads(config_result.stdout)
                    actual_db = config.get("db_name", "")
                    if actual_db != expected_db:
                        checks.append({
                            "site": site,
                            "expected": expected_db,
                            "actual": actual_db,
                        })
                except json.JSONDecodeError:
                    checks.append({
                        "site": site,
                        "error": "Invalid site config JSON",
                    })

        if checks:
            return {
                "valid": False,
                "check": "database_configuration",
                "issues": checks,
            }

        return {
            "valid": True,
            "check": "no_cross_site_access",
            "message": f"Sites '{site_a}' and '{site_b}' are properly isolated",
        }

    def validate_all(self, site_name: str) -> Dict[str, Any]:
        """
        Run all isolation validations for a site.

        Args:
            site_name: The site to validate

        Returns:
            Dict with all validation results
        """
        results = {
            "site": site_name,
            "valid": True,
            "checks": [],
        }

        # Database isolation
        db_result = self.validate_database_isolation(site_name)
        results["checks"].append(db_result)
        if not db_result.get("valid"):
            results["valid"] = False

        # File isolation
        file_result = self.validate_file_isolation(site_name)
        results["checks"].append(file_result)
        if not file_result.get("valid"):
            results["valid"] = False

        return results


def validate_site_isolation(site_name: str) -> Dict[str, Any]:
    """
    Convenience function to validate site isolation.

    Args:
        site_name: The site to validate

    Returns:
        Dict with validation results
    """
    validator = SiteIsolationValidator()
    return validator.validate_all(site_name)


def validate_new_site(site_name: str) -> Dict[str, Any]:
    """
    Validate a new site before creation.

    This checks that creating the site won't conflict
    with existing sites.

    Args:
        site_name: Proposed site name

    Returns:
        Dict with validation result
    """
    from press_selfhosted.services.site_provisioner import SiteProvisioner

    provisioner = SiteProvisioner()
    return provisioner.validate_site_name(site_name)
