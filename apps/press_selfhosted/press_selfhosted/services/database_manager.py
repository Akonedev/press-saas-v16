"""
Database Manager for Self-Hosted Mode

This module handles database creation and management for tenant sites,
using the local MariaDB container.

Constitution Constraint: Part of press_selfhosted app
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional, List
import subprocess
import re


class DatabaseManager:
    """
    Manages MariaDB databases for tenant sites.

    This class handles:
    - Database creation for new sites
    - User management per site
    - Database cleanup on site deletion
    """

    def __init__(self):
        """Initialize the database manager."""
        self.container_prefix = frappe.conf.get(
            "container_prefix", "erp-saas-cloud-c16"
        )
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

    def _execute_sql(
        self,
        sql: str,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute SQL in the MariaDB container.

        Args:
            sql: SQL statement to execute
            database: Optional database to use

        Returns:
            Dict with success status and output/error
        """
        root_password = frappe.conf.get("mariadb_root_password", "")

        command = [
            self.runtime, "exec", self.mariadb_container,
            "mysql", "-u", "root", f"-p{root_password}",
        ]

        if database:
            command.extend(["-D", database])

        command.extend(["-e", sql])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "SQL execution timed out",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _site_to_db_name(self, site_name: str) -> str:
        """
        Convert site name to valid database name.

        Args:
            site_name: The site name (e.g., "tenant1.platform.local")

        Returns:
            Valid database name (e.g., "_tenant1_platform_local")
        """
        # Replace dots and hyphens with underscores
        db_name = site_name.replace(".", "_").replace("-", "_")

        # Prefix with underscore to avoid starting with number
        if db_name[0].isdigit():
            db_name = f"_{db_name}"

        # Truncate if too long (MariaDB limit is 64 characters)
        return db_name[:64]

    def check_connection(self) -> Dict[str, Any]:
        """
        Check if MariaDB is accessible.

        Returns:
            Dict with connection status
        """
        result = self._execute_sql("SELECT 1 as ping;")

        if result.get("success"):
            return {
                "connected": True,
                "message": "MariaDB connection successful",
            }

        return {
            "connected": False,
            "error": result.get("error"),
        }

    def database_exists(self, db_name: str) -> bool:
        """
        Check if a database exists.

        Args:
            db_name: Database name to check

        Returns:
            True if database exists
        """
        result = self._execute_sql(
            f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
            f"WHERE SCHEMA_NAME = '{db_name}';"
        )

        if result.get("success"):
            return db_name in result.get("output", "")

        return False

    def create_database(self, site_name: str) -> Dict[str, Any]:
        """
        Create a database for a new site.

        Args:
            site_name: The site name

        Returns:
            Dict with success status and database name
        """
        db_name = self._site_to_db_name(site_name)

        # Check if already exists
        if self.database_exists(db_name):
            return {
                "success": False,
                "error": f"Database '{db_name}' already exists",
                "database": db_name,
            }

        # Create database with proper character set
        sql = (
            f"CREATE DATABASE `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )

        result = self._execute_sql(sql)

        if result.get("success"):
            return {
                "success": True,
                "database": db_name,
                "message": f"Database '{db_name}' created successfully",
            }

        return {
            "success": False,
            "error": result.get("error"),
            "database": db_name,
        }

    def create_user(
        self,
        username: str,
        password: str,
        database: str,
    ) -> Dict[str, Any]:
        """
        Create a database user for a site.

        Args:
            username: User name
            password: User password
            database: Database to grant access to

        Returns:
            Dict with success status
        """
        # Create user
        create_sql = (
            f"CREATE USER IF NOT EXISTS '{username}'@'%' "
            f"IDENTIFIED BY '{password}';"
        )

        result = self._execute_sql(create_sql)
        if not result.get("success"):
            return result

        # Grant privileges
        grant_sql = (
            f"GRANT ALL PRIVILEGES ON `{database}`.* "
            f"TO '{username}'@'%';"
        )

        result = self._execute_sql(grant_sql)
        if not result.get("success"):
            return result

        # Flush privileges
        self._execute_sql("FLUSH PRIVILEGES;")

        return {
            "success": True,
            "username": username,
            "database": database,
        }

    def drop_database(self, site_name: str) -> Dict[str, Any]:
        """
        Drop a database for a site.

        Args:
            site_name: The site name

        Returns:
            Dict with success status
        """
        db_name = self._site_to_db_name(site_name)

        # Check if exists
        if not self.database_exists(db_name):
            return {
                "success": False,
                "error": f"Database '{db_name}' does not exist",
            }

        # Drop database
        result = self._execute_sql(f"DROP DATABASE `{db_name}`;")

        if result.get("success"):
            return {
                "success": True,
                "database": db_name,
                "message": f"Database '{db_name}' dropped successfully",
            }

        return {
            "success": False,
            "error": result.get("error"),
        }

    def list_databases(self) -> List[str]:
        """
        List all databases.

        Returns:
            List of database names
        """
        result = self._execute_sql("SHOW DATABASES;")

        if result.get("success"):
            # Parse output
            lines = result["output"].strip().split("\n")
            # Skip header
            databases = [
                line.strip() for line in lines[1:]
                if line.strip() and line.strip() not in [
                    "information_schema",
                    "mysql",
                    "performance_schema",
                    "sys",
                ]
            ]
            return databases

        return []

    def list_site_databases(self) -> List[str]:
        """
        List databases that belong to Frappe sites.

        Returns:
            List of site database names
        """
        all_dbs = self.list_databases()

        # Frappe site databases typically start with underscore
        # or contain underscored domain names
        site_dbs = [
            db for db in all_dbs
            if db.startswith("_") or "_" in db
        ]

        return site_dbs

    def get_database_size(self, db_name: str) -> Dict[str, Any]:
        """
        Get the size of a database.

        Args:
            db_name: Database name

        Returns:
            Dict with size information
        """
        sql = (
            f"SELECT table_schema AS 'database', "
            f"ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'size_mb' "
            f"FROM information_schema.tables "
            f"WHERE table_schema = '{db_name}' "
            f"GROUP BY table_schema;"
        )

        result = self._execute_sql(sql)

        if result.get("success"):
            # Parse output
            output = result["output"]
            match = re.search(r"(\d+\.?\d*)", output.split("\n")[-1])
            if match:
                return {
                    "database": db_name,
                    "size_mb": float(match.group(1)),
                }

        return {
            "database": db_name,
            "size_mb": 0,
            "error": result.get("error"),
        }

    def backup_database(self, db_name: str, output_path: str) -> Dict[str, Any]:
        """
        Create a backup of a database.

        Args:
            db_name: Database name
            output_path: Path to save the backup

        Returns:
            Dict with success status
        """
        root_password = frappe.conf.get("mariadb_root_password", "")

        command = [
            self.runtime, "exec", self.mariadb_container,
            "mysqldump", "-u", "root", f"-p{root_password}",
            "--single-transaction", "--quick",
            db_name,
        ]

        try:
            with open(output_path, "w") as f:
                result = subprocess.run(
                    command,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600,  # 10 minutes for large databases
                )

            if result.returncode == 0:
                return {
                    "success": True,
                    "database": db_name,
                    "path": output_path,
                }

            return {
                "success": False,
                "error": result.stderr,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
