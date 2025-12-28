"""
Health Check API - ERP SaaS Cloud PRESSE v16

This module provides health check endpoints for monitoring
the Press Self-Hosted platform status.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
import time
from typing import Dict, Any, Optional
import redis
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns:
        Dict containing health status of all components

    Example response:
        {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "0.0.1",
            "components": {
                "database": {"status": "healthy", "latency_ms": 5},
                "redis_cache": {"status": "healthy", "latency_ms": 2},
                "redis_queue": {"status": "healthy", "latency_ms": 2},
                "storage": {"status": "healthy"}
            }
        }
    """
    start_time = time.time()

    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": get_app_version(),
        "components": {},
    }

    # Check database
    db_status = check_database()
    response["components"]["database"] = db_status
    if db_status["status"] != "healthy":
        response["status"] = "degraded"

    # Check Redis cache
    cache_status = check_redis_cache()
    response["components"]["redis_cache"] = cache_status
    if cache_status["status"] != "healthy":
        response["status"] = "degraded"

    # Check Redis queue
    queue_status = check_redis_queue()
    response["components"]["redis_queue"] = queue_status
    if queue_status["status"] != "healthy":
        response["status"] = "degraded"

    # Check storage (MinIO)
    storage_status = check_storage()
    response["components"]["storage"] = storage_status
    if storage_status["status"] != "healthy":
        response["status"] = "degraded"

    # Calculate total response time
    response["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

    # Set overall status to unhealthy if any critical component is down
    critical_components = ["database", "redis_queue"]
    for component in critical_components:
        if response["components"].get(component, {}).get("status") == "unhealthy":
            response["status"] = "unhealthy"
            break

    return response


@frappe.whitelist(allow_guest=True)
def ping() -> Dict[str, str]:
    """
    Simple ping endpoint for basic liveness check.

    Returns:
        {"status": "pong"}
    """
    return {"status": "pong"}


@frappe.whitelist(allow_guest=True)
def ready() -> Dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes/container orchestration.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if critical components are not available.
    """
    health = check()

    if health["status"] == "unhealthy":
        frappe.local.response.http_status_code = 503
        return {
            "ready": False,
            "reason": "Critical components unavailable",
            "components": health["components"],
        }

    return {
        "ready": True,
        "components": health["components"],
    }


def get_app_version() -> str:
    """Get the press_selfhosted app version."""
    try:
        from press_selfhosted import __version__
        return __version__
    except (ImportError, AttributeError):
        return "unknown"


def check_database() -> Dict[str, Any]:
    """Check MariaDB connectivity and latency."""
    start_time = time.time()

    try:
        # Simple query to check database connectivity
        result = frappe.db.sql("SELECT 1 as ping", as_dict=True)

        if result and result[0].get("ping") == 1:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Unexpected database response",
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_redis_cache() -> Dict[str, Any]:
    """Check Redis cache connectivity."""
    start_time = time.time()

    try:
        cache_url = frappe.conf.get("redis_cache")
        if not cache_url:
            return {
                "status": "unhealthy",
                "error": "Redis cache not configured",
            }

        # Parse Redis URL and connect
        client = _get_redis_client(cache_url)
        if client.ping():
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Redis cache ping failed",
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_redis_queue() -> Dict[str, Any]:
    """Check Redis queue connectivity."""
    start_time = time.time()

    try:
        queue_url = frappe.conf.get("redis_queue")
        if not queue_url:
            return {
                "status": "unhealthy",
                "error": "Redis queue not configured",
            }

        client = _get_redis_client(queue_url)
        if client.ping():
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Redis queue ping failed",
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_storage() -> Dict[str, Any]:
    """Check MinIO/S3 storage connectivity."""
    try:
        minio_endpoint = frappe.conf.get("minio_endpoint")

        if not minio_endpoint:
            # Storage not configured, this is acceptable for basic setup
            return {
                "status": "healthy",
                "message": "Storage not configured (optional)",
            }

        # Try to import and check MinIO
        try:
            from minio import Minio
            from urllib.parse import urlparse

            # Parse endpoint
            parsed = urlparse(f"http://{minio_endpoint}")
            host = parsed.netloc or minio_endpoint

            client = Minio(
                host,
                access_key=frappe.conf.get("minio_access_key", ""),
                secret_key=frappe.conf.get("minio_secret_key", ""),
                secure=False,
            )

            # List buckets as health check
            client.list_buckets()

            return {
                "status": "healthy",
                "endpoint": minio_endpoint,
            }

        except ImportError:
            return {
                "status": "healthy",
                "message": "MinIO client not installed",
            }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
        }


def _get_redis_client(url: str) -> redis.Redis:
    """Create a Redis client from URL."""
    return redis.Redis.from_url(url, socket_timeout=5)
