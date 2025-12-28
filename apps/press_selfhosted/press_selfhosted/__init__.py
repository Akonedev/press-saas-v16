"""
Press Self-Hosted - Local deployment adapter for Frappe Press

This app provides adaptations for running Frappe Press in a fully
self-hosted containerized environment, replacing cloud providers
with local alternatives (MinIO, Traefik, etc.).
"""

__version__ = "0.0.1"
__title__ = "Press Self-Hosted"
__description__ = "Local deployment adapter for Frappe Press"
__author__ = "ERP SaaS Cloud Team"
__license__ = "MIT"

# Frappe app metadata
app_name = "press_selfhosted"
app_title = "Press Self-Hosted"
app_publisher = "ERP SaaS Cloud Team"
app_description = "Local deployment adapter for Frappe Press"
app_icon = "octicon octicon-server"
app_color = "#3498db"
app_email = "admin@platform.local"
app_version = __version__
