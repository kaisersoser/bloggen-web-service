"""
Database Configuration and Path Management

Centralized database configuration to eliminate hardcoded paths
and provide consistent database connection management.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from core.config import config
from core.logging_utils import get_logger


@dataclass
class DatabasePaths:
    """Centralized database path configuration"""

    chroma_db: Path
    logs_db: Path
    backup_dir: Path
    migrations_dir: Optional[Path] = None


class DatabaseConfig:
    """Centralized database configuration management"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._paths = self._initialize_paths()

    def _initialize_paths(self) -> DatabasePaths:
        """Initialize all database-related paths"""
        base_db_dir = config.paths.bloggen_dir / "db"

        # Ensure base database directory exists
        base_db_dir.mkdir(parents=True, exist_ok=True)

        paths = DatabasePaths(
            chroma_db=base_db_dir / "chroma.sqlite3",
            logs_db=base_db_dir / "application_logs.db",
            backup_dir=base_db_dir / "backups",
            migrations_dir=base_db_dir / "migrations",
        )

        # Create directories if they don't exist
        paths.backup_dir.mkdir(exist_ok=True)
        if paths.migrations_dir:
            paths.migrations_dir.mkdir(exist_ok=True)

        return paths

    @property
    def paths(self) -> DatabasePaths:
        """Get database paths"""
        return self._paths

    def get_chroma_db_url(self) -> str:
        """Get ChromaDB connection URL"""
        if config.database.url and not config.database.url.endswith("chroma.sqlite3"):
            # Use configured database URL if it's not the default
            return config.database.url

        # Use centralized path
        return f"sqlite:///{self.paths.chroma_db}"

    def get_chroma_db_path(self) -> str:
        """Get ChromaDB file path as string"""
        return str(self.paths.chroma_db)

    def get_application_db_url(self) -> str:
        """Get application database URL (for Prisma/SQLite)"""
        if config.database.url and "chroma" not in config.database.url:
            return config.database.url

        # Default to PostgreSQL-style URL or SQLite fallback
        return f"file:{self.paths.logs_db}"

    def validate_database_config(self) -> Dict[str, Any]:
        """Validate database configuration and paths"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths_status": {},
            "permissions": {},
        }

        # Check if paths exist and are writable
        for name, path in {
            "chroma_db": self.paths.chroma_db,
            "logs_db": self.paths.logs_db,
            "backup_dir": self.paths.backup_dir,
        }.items():
            try:
                # Check if parent directory exists and is writable
                parent_dir = path.parent
                if not parent_dir.exists():
                    validation["errors"].append(
                        f"Database directory does not exist: {parent_dir}"
                    )
                    validation["valid"] = False
                elif not os.access(parent_dir, os.W_OK):
                    validation["errors"].append(
                        f"No write permission for database directory: {parent_dir}"
                    )
                    validation["valid"] = False
                else:
                    validation["paths_status"][name] = "accessible"
                    validation["permissions"][name] = "writable"
            except Exception as e:
                validation["errors"].append(f"Error checking {name}: {str(e)}")
                validation["valid"] = False

        # Check ChromaDB specific requirements
        try:
            chroma_dir = self.paths.chroma_db.parent
            if chroma_dir.exists():
                # Check for existing ChromaDB files
                chroma_files = list(chroma_dir.glob("*.bin")) + list(
                    chroma_dir.glob("*.sqlite3")
                )
                if chroma_files:
                    validation["warnings"].append(
                        f"Existing ChromaDB files found: {len(chroma_files)} files"
                    )
        except Exception as e:
            validation["warnings"].append(f"Could not check ChromaDB files: {str(e)}")

        return validation

    def create_backup_path(self, backup_type: str = "manual") -> Path:
        """Create a backup file path with timestamp"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{backup_type}_backup_{timestamp}"

        return self.paths.backup_dir / backup_name

    def get_database_summary(self) -> str:
        """Get formatted database configuration summary"""
        lines = ["Database Configuration Summary:"]
        lines.append("=" * 50)

        # Paths
        lines.append("Database Paths:")
        lines.append(f"  ChromaDB: {self.paths.chroma_db}")
        lines.append(f"  App Database: {self.paths.logs_db}")
        lines.append(f"  Backups: {self.paths.backup_dir}")

        # URLs
        lines.append("\nConnection URLs:")
        lines.append(f"  ChromaDB URL: {self.get_chroma_db_url()}")
        lines.append(f"  App DB URL: {self.get_application_db_url()}")

        # Validation
        validation = self.validate_database_config()
        status = "✅ VALID" if validation["valid"] else "❌ INVALID"
        lines.append(f"\nValidation Status: {status}")

        if validation["errors"]:
            lines.append("Errors:")
            for error in validation["errors"]:
                lines.append(f"  - {error}")

        if validation["warnings"]:
            lines.append("Warnings:")
            for warning in validation["warnings"]:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


# Global database configuration instance
db_config = DatabaseConfig()


# Convenience functions
def get_chroma_db_path() -> str:
    """Get ChromaDB file path"""
    return db_config.get_chroma_db_path()


def get_chroma_db_url() -> str:
    """Get ChromaDB connection URL"""
    return db_config.get_chroma_db_url()


def get_database_summary() -> str:
    """Get database configuration summary"""
    return db_config.get_database_summary()


def validate_database_config() -> Dict[str, Any]:
    """Validate database configuration"""
    return db_config.validate_database_config()


def ensure_database_directories() -> None:
    """Ensure all database directories exist"""
    db_config._initialize_paths()


def get_backup_path(backup_type: str = "manual") -> Path:
    """Get a new backup file path"""
    return db_config.create_backup_path(backup_type)
