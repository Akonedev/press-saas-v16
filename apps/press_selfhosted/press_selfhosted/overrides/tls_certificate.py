"""
TLS Certificate DocType Extension - Self-Hosted Mode
=====================================================

Extends Press TLS Certificate DocType to support local certificate management
using Let's Encrypt with Traefik ACME integration.

Constitution Constraint: Part of erp-saas-cloud-c16 infrastructure
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import frappe
from frappe import _
from frappe.utils import get_datetime, add_days


class SelfHostedTLSCertificate:
    """
    Extension for Press TLS Certificate DocType to handle self-hosted certificates.

    This class intercepts Press certificate operations and:
    1. Uses Traefik's ACME integration for Let's Encrypt certificates
    2. Manages certificate storage in Traefik's acme.json file
    3. Tracks certificate status and renewal
    4. Provides development mode with mkcert certificates
    """

    def __init__(self, doc):
        """
        Initialize with TLS Certificate document.

        Args:
            doc: Frappe TLS Certificate document
        """
        self.doc = doc
        self.container_prefix = "erp-saas-cloud-c16"

        # Path to Traefik ACME storage
        self.acme_storage = Path("/home/frappe/frappe-bench/docker/config/traefik/acme/acme.json")

        # Path to development certificates
        self.dev_cert_dir = Path("/home/frappe/frappe-bench/docker/config/traefik/acme")

    def validate_local(self) -> None:
        """
        Validate certificate configuration before save.

        Checks:
        - Domain is valid
        - ACME storage is accessible
        - No duplicate certificates for the same domain
        """
        if not self.doc.domain:
            frappe.throw(_("Domain is required for TLS certificate"))

        # Check for duplicates
        existing = frappe.get_all(
            "TLS Certificate",
            filters={
                "domain": self.doc.domain,
                "name": ["!=", self.doc.name]
            }
        )

        if existing:
            frappe.throw(_("Certificate already exists for domain {0}").format(self.doc.domain))

        # Validate ACME storage directory exists
        if not self.dev_cert_dir.exists():
            frappe.throw(_("ACME storage directory not found: {0}").format(self.dev_cert_dir))

    def obtain_certificate_local(self) -> Dict[str, Any]:
        """
        Obtain TLS certificate using Traefik ACME integration.

        Traefik handles the actual ACME protocol with Let's Encrypt.
        This method monitors the acme.json file for certificate availability.

        Returns:
            Dict with certificate information

        Raises:
            frappe.ValidationError: If certificate obtaining fails
        """
        domain = self.doc.domain

        frappe.log(f"Requesting Let's Encrypt certificate for {domain} via Traefik ACME")

        # In self-hosted mode, Traefik handles ACME automatically
        # We just need to ensure routing is configured for the domain
        from press_selfhosted.services.route_manager import create_route_for_site

        try:
            # Create route (triggers Traefik to obtain certificate)
            create_route_for_site(domain)

            # Wait for Traefik to obtain certificate
            # In production, this happens automatically
            # In development, we use mkcert certificates
            cert_info = self._wait_for_certificate(domain, timeout=300)

            if not cert_info:
                frappe.throw(_("Failed to obtain certificate for {0}").format(domain))

            # Update document
            self.doc.status = "Active"
            self.doc.issued_at = get_datetime()
            self.doc.expires_at = cert_info.get("not_after")

            return {
                "success": True,
                "domain": domain,
                "issued_at": self.doc.issued_at,
                "expires_at": self.doc.expires_at,
                "issuer": cert_info.get("issuer", "Let's Encrypt")
            }

        except Exception as e:
            frappe.log_error(f"Certificate obtain failed for {domain}: {e}")
            self.doc.status = "Failed"
            frappe.throw(_("Failed to obtain certificate: {0}").format(str(e)))

    def _wait_for_certificate(self, domain: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Wait for Traefik to obtain certificate from Let's Encrypt.

        Args:
            domain: Domain name
            timeout: Maximum wait time in seconds

        Returns:
            Certificate information dict or None if timeout
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            cert_info = self._read_certificate_from_acme(domain)

            if cert_info:
                return cert_info

            # Wait 5 seconds before checking again
            time.sleep(5)

        return None

    def _read_certificate_from_acme(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Read certificate information from Traefik's acme.json file.

        Args:
            domain: Domain name

        Returns:
            Certificate information or None if not found
        """
        try:
            if not self.acme_storage.exists():
                return None

            with open(self.acme_storage, "r") as f:
                acme_data = json.load(f)

            # Navigate ACME JSON structure
            # Format: acme_data[resolver][domain]
            resolver_data = acme_data.get("letsencrypt", {})
            certificates = resolver_data.get("Certificates", [])

            # Find certificate for this domain
            for cert in certificates:
                cert_domain = cert.get("domain", {}).get("main", "")

                if cert_domain == domain:
                    return {
                        "domain": domain,
                        "not_after": cert.get("notAfter"),
                        "not_before": cert.get("notBefore"),
                        "issuer": "Let's Encrypt"
                    }

            return None

        except Exception as e:
            frappe.log_error(f"Failed to read ACME storage: {e}")
            return None

    def renew_certificate_local(self) -> Dict[str, Any]:
        """
        Renew TLS certificate.

        Traefik handles renewal automatically when certificate is within 30 days of expiry.
        This method triggers a manual renewal if needed.

        Returns:
            Dict with renewal result
        """
        domain = self.doc.domain

        frappe.log(f"Renewing certificate for {domain}")

        try:
            # Check current certificate status
            cert_info = self._read_certificate_from_acme(domain)

            if not cert_info:
                # Certificate doesn't exist, obtain new one
                return self.obtain_certificate_local()

            # Parse expiry date
            expires_at = get_datetime(cert_info.get("not_after"))
            days_until_expiry = (expires_at - get_datetime()).days

            if days_until_expiry > 30:
                # Certificate is still valid for more than 30 days
                frappe.log(f"Certificate for {domain} is still valid for {days_until_expiry} days")
                return {
                    "success": True,
                    "message": "Certificate is still valid",
                    "days_until_expiry": days_until_expiry
                }

            # Force renewal by deleting from ACME storage
            # Traefik will automatically obtain a new certificate
            self._delete_certificate_from_acme(domain)

            # Wait for new certificate
            new_cert_info = self._wait_for_certificate(domain, timeout=300)

            if not new_cert_info:
                frappe.throw(_("Failed to renew certificate for {0}").format(domain))

            # Update document
            self.doc.renewed_at = get_datetime()
            self.doc.expires_at = new_cert_info.get("not_after")
            self.doc.status = "Active"

            return {
                "success": True,
                "domain": domain,
                "renewed_at": self.doc.renewed_at,
                "expires_at": self.doc.expires_at
            }

        except Exception as e:
            frappe.log_error(f"Certificate renewal failed for {domain}: {e}")
            frappe.throw(_("Failed to renew certificate: {0}").format(str(e)))

    def _delete_certificate_from_acme(self, domain: str) -> bool:
        """
        Delete certificate from Traefik's ACME storage to force renewal.

        Args:
            domain: Domain name

        Returns:
            True if deleted, False otherwise
        """
        try:
            if not self.acme_storage.exists():
                return False

            with open(self.acme_storage, "r") as f:
                acme_data = json.load(f)

            # Find and remove certificate
            resolver_data = acme_data.get("letsencrypt", {})
            certificates = resolver_data.get("Certificates", [])

            # Filter out the certificate for this domain
            updated_certs = [
                cert for cert in certificates
                if cert.get("domain", {}).get("main", "") != domain
            ]

            # Update ACME data
            resolver_data["Certificates"] = updated_certs

            # Write back to file
            with open(self.acme_storage, "w") as f:
                json.dump(acme_data, f, indent=2)

            frappe.log(f"Deleted certificate for {domain} from ACME storage")
            return True

        except Exception as e:
            frappe.log_error(f"Failed to delete certificate from ACME storage: {e}")
            return False

    def revoke_certificate_local(self) -> Dict[str, Any]:
        """
        Revoke TLS certificate.

        Removes certificate from ACME storage and updates status.

        Returns:
            Dict with revocation result
        """
        domain = self.doc.domain

        frappe.log(f"Revoking certificate for {domain}")

        try:
            # Delete from ACME storage
            deleted = self._delete_certificate_from_acme(domain)

            if not deleted:
                frappe.throw(_("Failed to revoke certificate for {0}").format(domain))

            # Update status
            self.doc.status = "Revoked"
            self.doc.revoked_at = get_datetime()

            return {
                "success": True,
                "domain": domain,
                "revoked_at": self.doc.revoked_at
            }

        except Exception as e:
            frappe.log_error(f"Certificate revocation failed for {domain}: {e}")
            frappe.throw(_("Failed to revoke certificate: {0}").format(str(e)))

    def check_expiry_local(self) -> Dict[str, Any]:
        """
        Check certificate expiry status.

        Returns:
            Dict with expiry information including days until expiry
        """
        domain = self.doc.domain

        try:
            cert_info = self._read_certificate_from_acme(domain)

            if not cert_info:
                return {
                    "exists": False,
                    "domain": domain
                }

            expires_at = get_datetime(cert_info.get("not_after"))
            now = get_datetime()
            days_until_expiry = (expires_at - now).days

            return {
                "exists": True,
                "domain": domain,
                "expires_at": expires_at,
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry <= 30,
                "is_expired": days_until_expiry < 0
            }

        except Exception as e:
            frappe.log_error(f"Failed to check certificate expiry for {domain}: {e}")
            return {
                "exists": False,
                "error": str(e)
            }


def check_and_renew_certificates() -> None:
    """
    Background job to check and renew certificates nearing expiry.

    This function should be scheduled to run daily.
    """
    frappe.log("Checking TLS certificates for renewal")

    # Get all active certificates
    certificates = frappe.get_all(
        "TLS Certificate",
        filters={"status": "Active"},
        fields=["name", "domain", "expires_at"]
    )

    renewed_count = 0
    failed_count = 0

    for cert in certificates:
        try:
            doc = frappe.get_doc("TLS Certificate", cert.name)
            handler = SelfHostedTLSCertificate(doc)

            # Check expiry
            expiry_info = handler.check_expiry_local()

            if expiry_info.get("needs_renewal"):
                frappe.log(f"Renewing certificate for {cert.domain}")
                handler.renew_certificate_local()
                doc.save(ignore_permissions=True)
                renewed_count += 1

        except Exception as e:
            frappe.log_error(f"Failed to renew certificate for {cert.domain}: {e}")
            failed_count += 1

    frappe.log(f"Certificate renewal check complete: {renewed_count} renewed, {failed_count} failed")
