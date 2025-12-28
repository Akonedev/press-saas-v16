"""
Frappe Hooks for Press Self-Hosted

This module defines the hooks that integrate press_selfhosted
with the Frappe framework and Press application.
"""

from . import __version__ as app_version

app_name = "press_selfhosted"
app_title = "Press Self-Hosted"
app_publisher = "ERP SaaS Cloud Team"
app_description = "Local deployment adapter for Frappe Press"
app_email = "admin@platform.local"
app_license = "MIT"

# -----------------------------------------------------------------------------
# App Includes
# -----------------------------------------------------------------------------

# Include JavaScript files in desk
# app_include_js = "/assets/press_selfhosted/js/press_selfhosted.js"

# Include CSS files in desk
# app_include_css = "/assets/press_selfhosted/css/press_selfhosted.css"

# Include JavaScript files in web pages
# web_include_js = "/assets/press_selfhosted/js/press_selfhosted_web.js"

# Include CSS files in web pages
# web_include_css = "/assets/press_selfhosted/css/press_selfhosted_web.css"

# -----------------------------------------------------------------------------
# DocType Overrides
# -----------------------------------------------------------------------------

# Override standard DocTypes with customizations
# override_doctype_class = {
#     "Site": "press_selfhosted.overrides.site.CustomSite",
#     "Bench": "press_selfhosted.overrides.bench.CustomBench",
# }

# -----------------------------------------------------------------------------
# Document Events
# -----------------------------------------------------------------------------

# Hook into document lifecycle events
# doc_events = {
#     "Site": {
#         "before_insert": "press_selfhosted.hooks.site_hooks.before_insert",
#         "after_insert": "press_selfhosted.hooks.site_hooks.after_insert",
#         "on_update": "press_selfhosted.hooks.site_hooks.on_update",
#     },
#     "Backup": {
#         "after_insert": "press_selfhosted.overrides.backup.on_backup_created",
#     }
# }

# -----------------------------------------------------------------------------
# Scheduled Tasks
# -----------------------------------------------------------------------------

# Define scheduled tasks (cron-like)
# scheduler_events = {
#     "cron": {
#         "0 2 * * *": [
#             "press_selfhosted.services.backup_service.scheduled_backup"
#         ]
#     },
#     "daily": [
#         "press_selfhosted.services.cleanup.daily_cleanup"
#     ],
#     "hourly": [
#         "press_selfhosted.services.site_status.check_all_sites"
#     ],
#     "weekly": [],
#     "monthly": []
# }

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

# Tests are organized in apps/press_selfhosted/tests/
# Run with: bench --site <site> run-tests --app press_selfhosted

# -----------------------------------------------------------------------------
# Installation
# -----------------------------------------------------------------------------

# Called before app installation
# before_install = "press_selfhosted.setup.install.before_install"

# Called after app installation
after_install = "press_selfhosted.setup.install.after_install"

# Called before app uninstallation
# before_uninstall = "press_selfhosted.setup.install.before_uninstall"

# Called after app migration
# after_migrate = "press_selfhosted.setup.install.after_migrate"

# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------

# Define custom permission queries
# permission_query_conditions = {
#     "Site": "press_selfhosted.validators.permissions.get_site_permission_query"
# }

# Define custom has_permission logic
# has_permission = {
#     "Site": "press_selfhosted.validators.permissions.has_site_permission"
# }

# -----------------------------------------------------------------------------
# Website
# -----------------------------------------------------------------------------

# Define custom web routes
# website_route_rules = [
#     {"from_route": "/status/<site>", "to_route": "site_status"},
# ]

# -----------------------------------------------------------------------------
# Jinja Customizations
# -----------------------------------------------------------------------------

# Add custom Jinja methods
# jinja = {
#     "methods": [
#         "press_selfhosted.utils.jinja.custom_method"
#     ],
#     "filters": [
#         "press_selfhosted.utils.jinja.custom_filter"
#     ]
# }

# -----------------------------------------------------------------------------
# User Data Protection
# -----------------------------------------------------------------------------

# Define data for GDPR compliance
# user_data_fields = [
#     {
#         "doctype": "{doctype}",
#         "filter_by": "{field_name}",
#         "partial": True,
#     }
# ]

# -----------------------------------------------------------------------------
# Authentication and Authorization
# -----------------------------------------------------------------------------

# Define custom authentication handlers
# authentication_backends = [
#     "press_selfhosted.auth.CustomAuthBackend"
# ]
