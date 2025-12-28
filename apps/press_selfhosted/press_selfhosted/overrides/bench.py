"""
Bench DocType Override for Self-Hosted Mode

This module extends the Press Bench DocType to support local operations
instead of cloud-based server management.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Optional, Dict, Any, List
import subprocess
import os


class SelfHostedBench:
    """
    Mixin class for Bench DocType to support self-hosted operations.

    In self-hosted mode, a "Bench" represents the local Frappe-bench
    installation running in Docker containers.
    """

    def __init__(self, bench_doc=None):
        """
        Initialize with an optional Bench document.

        Args:
            bench_doc: The Frappe Bench document (optional in self-hosted mode)
        """
        self.bench = bench_doc
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )
        self.press_container = f"{self.container_prefix}-press"

    def get_runtime(self) -> str:
        """
        Detect available container runtime.

        Returns:
            "docker" or "podman"
        """
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

    def execute_bench_command(
        self,
        command: List[str],
        site: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a bench command in the Press container.

        Args:
            command: List of command arguments (e.g., ["migrate"])
            site: Optional site name for site-specific commands

        Returns:
            Dict with success status and output/error
        """
        runtime = self.get_runtime()

        # Build full command
        full_command = [runtime, "exec", self.press_container, "bench"]

        if site:
            full_command.extend(["--site", site])

        full_command.extend(command)

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "command": " ".join(full_command),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 5 minutes",
                "command": " ".join(full_command),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(full_command),
            }

    def get_installed_apps(self) -> List[str]:
        """
        Get list of installed apps in the bench.

        Returns:
            List of app names
        """
        result = self.execute_bench_command(["list-apps"])

        if result.get("success"):
            apps = result["output"].strip().split("\n")
            return [app.strip() for app in apps if app.strip()]

        return []

    def get_available_sites(self) -> List[str]:
        """
        Get list of available sites in the bench.

        Returns:
            List of site names
        """
        runtime = self.get_runtime()

        try:
            result = subprocess.run(
                [
                    runtime, "exec", self.press_container,
                    "ls", "/home/frappe/frappe-bench/sites",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                items = result.stdout.strip().split("\n")
                # Filter out non-site items
                sites = [
                    item for item in items
                    if item and
                    not item.startswith(".") and
                    item not in ["apps.txt", "common_site_config.json", "assets"]
                ]
                return sites

        except Exception:
            pass

        return []

    def install_app(self, app_name: str, site: str) -> Dict[str, Any]:
        """
        Install an app on a specific site.

        Args:
            app_name: Name of the app to install
            site: Name of the site

        Returns:
            Dict with operation result
        """
        return self.execute_bench_command(
            ["install-app", app_name],
            site=site,
        )

    def migrate(self, site: Optional[str] = None) -> Dict[str, Any]:
        """
        Run migrations.

        Args:
            site: Optional site name (migrates all if not specified)

        Returns:
            Dict with operation result
        """
        return self.execute_bench_command(["migrate"], site=site)

    def build_assets(self) -> Dict[str, Any]:
        """
        Build frontend assets.

        Returns:
            Dict with operation result
        """
        return self.execute_bench_command(["build"])

    def restart(self) -> Dict[str, Any]:
        """
        Restart the bench services.

        In Docker mode, this restarts the containers.

        Returns:
            Dict with operation result
        """
        runtime = self.get_runtime()

        containers_to_restart = [
            f"{self.container_prefix}-press",
            f"{self.container_prefix}-worker-short",
            f"{self.container_prefix}-worker-long",
            f"{self.container_prefix}-worker-default",
            f"{self.container_prefix}-scheduler",
        ]

        results = []
        for container in containers_to_restart:
            try:
                result = subprocess.run(
                    [runtime, "restart", container],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                results.append({
                    "container": container,
                    "success": result.returncode == 0,
                    "error": result.stderr if result.returncode != 0 else None,
                })
            except Exception as e:
                results.append({
                    "container": container,
                    "success": False,
                    "error": str(e),
                })

        all_success = all(r.get("success") for r in results)

        return {
            "success": all_success,
            "containers": results,
        }

    def get_bench_info(self) -> Dict[str, Any]:
        """
        Get information about the bench.

        Returns:
            Dict with bench information
        """
        return {
            "mode": "self-hosted",
            "container_prefix": self.container_prefix,
            "press_container": self.press_container,
            "apps": self.get_installed_apps(),
            "sites": self.get_available_sites(),
        }


def get_local_bench() -> SelfHostedBench:
    """
    Get the local SelfHostedBench instance.

    In self-hosted mode, there's only one bench (the local installation).

    Returns:
        SelfHostedBench instance
    """
    return SelfHostedBench()


def override_bench_methods():
    """
    Override Press Bench DocType methods for self-hosted mode.

    This function is called during app installation to patch
    the Bench DocType with self-hosted methods.
    """
    try:
        from press.press.doctype.bench.bench import Bench

        # Store original methods
        Bench._original_restart = getattr(Bench, "restart", None)

        def selfhosted_restart(self):
            """Restart bench locally in self-hosted mode."""
            if frappe.conf.get("press_selfhosted_mode"):
                selfhosted = SelfHostedBench(self)
                return selfhosted.restart()
            elif self._original_restart:
                return self._original_restart()

        Bench.restart = selfhosted_restart

        frappe.logger().info("Bench DocType methods overridden for self-hosted mode")

    except ImportError:
        frappe.logger().warning(
            "Press app not installed, Bench override not applied"
        )
