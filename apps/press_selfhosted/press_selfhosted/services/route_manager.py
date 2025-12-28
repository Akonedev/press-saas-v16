"""
Dynamic Route Manager - Traefik Configuration Generator
========================================================

This service manages dynamic Traefik routing configuration for tenant sites.
Generates and updates routing rules when sites are created, updated, or archived.

Constitution Constraint: Part of erp-saas-cloud-c16 infrastructure
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import frappe
from frappe.utils import get_site_url


class RouteManager:
    """
    Manages dynamic Traefik routing configuration for multi-tenant sites.

    Attributes:
        config_dir: Path to Traefik dynamic configuration directory
        container_prefix: Container naming prefix (erp-saas-cloud-c16)
        backend_service: Name of the Press backend service
    """

    def __init__(self):
        """Initialize the route manager with configuration paths."""
        # Path to Traefik dynamic configuration directory
        self.config_dir = Path("/home/frappe/frappe-bench/docker/config/traefik/dynamic")

        # Container naming convention from constitution
        self.container_prefix = "erp-saas-cloud-c16"

        # Backend service name
        self.backend_service = f"{self.container_prefix}-press"
        self.backend_url = f"http://{self.backend_service}:8000"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def generate_site_routes(self, site_name: str, domain: str, priority: int = 100) -> Dict[str, Any]:
        """
        Generate Traefik routing configuration for a site.

        Args:
            site_name: Internal site name (e.g., tenant1)
            domain: External domain (e.g., tenant1.platform.local)
            priority: Route priority (higher = checked first)

        Returns:
            Dict containing the routing configuration

        Example:
            >>> manager = RouteManager()
            >>> config = manager.generate_site_routes("tenant1", "tenant1.platform.local")
            >>> config['http']['routers']['tenant1-web']
            {'rule': 'Host(`tenant1.platform.local`)', ...}
        """
        # Sanitize site name for use in router/service names
        router_name = site_name.replace(".", "-").replace("_", "-")

        config = {
            "http": {
                "routers": {
                    # Main router for the site
                    f"{router_name}-web": {
                        "entryPoints": ["web", "websecure"],
                        "rule": f"Host(`{domain}`)",
                        "service": f"{router_name}-backend",
                        "priority": priority,
                        "middlewares": [
                            "security-headers",
                            "compress",
                        ],
                        "tls": {
                            "certResolver": "letsencrypt"
                        }
                    },
                    # API router with higher priority and rate limiting
                    f"{router_name}-api": {
                        "entryPoints": ["web", "websecure"],
                        "rule": f"Host(`{domain}`) && PathPrefix(`/api`)",
                        "service": f"{router_name}-backend",
                        "priority": priority + 10,
                        "middlewares": [
                            "security-headers",
                            "rate-limit",
                        ],
                        "tls": {
                            "certResolver": "letsencrypt"
                        }
                    },
                    # Static assets with caching
                    f"{router_name}-assets": {
                        "entryPoints": ["web", "websecure"],
                        "rule": f"Host(`{domain}`) && PathPrefix(`/assets`, `/files`)",
                        "service": f"{router_name}-backend",
                        "priority": priority + 5,
                        "middlewares": [
                            "security-headers",
                            "compress",
                        ],
                        "tls": {
                            "certResolver": "letsencrypt"
                        }
                    }
                },
                "services": {
                    # Backend service definition
                    f"{router_name}-backend": {
                        "loadBalancer": {
                            "servers": [
                                {"url": self.backend_url}
                            ],
                            "healthCheck": {
                                "path": "/api/method/ping",
                                "interval": "30s",
                                "timeout": "5s"
                            },
                            "sticky": {
                                "cookie": {
                                    "name": f"{router_name}_session",
                                    "httpOnly": True,
                                    "secure": True
                                }
                            }
                        }
                    }
                }
            }
        }

        return config

    def create_route_config(self, site_name: str, domain: str, priority: int = 100) -> str:
        """
        Create and write Traefik configuration file for a site.

        Args:
            site_name: Internal site name
            domain: External domain
            priority: Route priority

        Returns:
            Path to the created configuration file

        Raises:
            OSError: If unable to write configuration file

        Example:
            >>> manager = RouteManager()
            >>> config_file = manager.create_route_config("tenant1", "tenant1.platform.local")
            >>> Path(config_file).exists()
            True
        """
        # Generate configuration
        config = self.generate_site_routes(site_name, domain, priority)

        # Write to file
        config_file = self.config_dir / f"site-{site_name}.yml"

        try:
            with open(config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            frappe.log(f"Created Traefik route config for {site_name}: {config_file}")
            return str(config_file)

        except OSError as e:
            frappe.log_error(f"Failed to write Traefik config for {site_name}: {e}")
            raise

    def update_route_config(self, site_name: str, domain: str, priority: int = 100) -> str:
        """
        Update existing Traefik configuration for a site.

        This method is identical to create_route_config (overwrites the file).
        Traefik watches for file changes and reloads automatically.

        Args:
            site_name: Internal site name
            domain: External domain
            priority: Route priority

        Returns:
            Path to the updated configuration file
        """
        return self.create_route_config(site_name, domain, priority)

    def delete_route_config(self, site_name: str) -> bool:
        """
        Delete Traefik configuration file for a site.

        Args:
            site_name: Internal site name

        Returns:
            True if deleted, False if file didn't exist

        Example:
            >>> manager = RouteManager()
            >>> manager.create_route_config("temp", "temp.local")
            >>> manager.delete_route_config("temp")
            True
        """
        config_file = self.config_dir / f"site-{site_name}.yml"

        try:
            if config_file.exists():
                config_file.unlink()
                frappe.log(f"Deleted Traefik route config for {site_name}")
                return True
            return False

        except OSError as e:
            frappe.log_error(f"Failed to delete Traefik config for {site_name}: {e}")
            raise

    def list_route_configs(self) -> List[Dict[str, str]]:
        """
        List all site route configuration files.

        Returns:
            List of dicts with site_name and config_file path

        Example:
            >>> manager = RouteManager()
            >>> configs = manager.list_route_configs()
            >>> isinstance(configs, list)
            True
        """
        configs = []

        try:
            for config_file in self.config_dir.glob("site-*.yml"):
                # Extract site name from filename: site-tenant1.yml -> tenant1
                site_name = config_file.stem.replace("site-", "")

                configs.append({
                    "site_name": site_name,
                    "config_file": str(config_file)
                })

            return configs

        except OSError as e:
            frappe.log_error(f"Failed to list Traefik configs: {e}")
            return []

    def validate_config(self, config_file: str) -> bool:
        """
        Validate YAML syntax of a configuration file.

        Args:
            config_file: Path to the configuration file

        Returns:
            True if valid YAML, False otherwise
        """
        try:
            with open(config_file, "r") as f:
                yaml.safe_load(f)
            return True

        except yaml.YAMLError as e:
            frappe.log_error(f"Invalid YAML in {config_file}: {e}")
            return False
        except OSError as e:
            frappe.log_error(f"Failed to read {config_file}: {e}")
            return False


def create_route_for_site(site_name: str, domain: Optional[str] = None) -> str:
    """
    Helper function to create Traefik route for a site.

    Args:
        site_name: Site name (e.g., tenant1.platform.local)
        domain: Custom domain (optional, defaults to site_name)

    Returns:
        Path to the created configuration file

    Example:
        >>> config_file = create_route_for_site("tenant1.platform.local")
        >>> Path(config_file).exists()
        True
    """
    manager = RouteManager()

    # Use site_name as domain if not provided
    if not domain:
        domain = site_name

    # Extract internal name from site_name (remove domain suffix)
    internal_name = site_name.split(".")[0]

    return manager.create_route_config(internal_name, domain)


def delete_route_for_site(site_name: str) -> bool:
    """
    Helper function to delete Traefik route for a site.

    Args:
        site_name: Site name

    Returns:
        True if deleted, False if didn't exist
    """
    manager = RouteManager()

    # Extract internal name from site_name
    internal_name = site_name.split(".")[0]

    return manager.delete_route_config(internal_name)


def update_route_for_site(site_name: str, domain: Optional[str] = None) -> str:
    """
    Helper function to update Traefik route for a site.

    Args:
        site_name: Site name
        domain: New domain (optional)

    Returns:
        Path to the updated configuration file
    """
    manager = RouteManager()

    if not domain:
        domain = site_name

    internal_name = site_name.split(".")[0]

    return manager.update_route_config(internal_name, domain)
