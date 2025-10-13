# flake8: noqa
"""Database Cleanup Utility

Purpose:
  - Drop legacy/unused tables
  - Truncate (reset) active data tables: llm_calls, audit_sessions, blogs (+ blog_logs)

Safety:
  - Refuses to run if DATABASE_URL not set
  - Refuses to run if RUN_DB_CLEANUP=confirm is not provided
  - Provides a dry-run mode (set DRY_RUN=1) to preview actions

Usage:
  DRY RUN (recommended first):
    DRY_RUN=1 RUN_DB_CLEANUP=confirm python backend/db_cleanup.py

  EXECUTE:
    RUN_DB_CLEANUP=confirm python backend/db_cleanup.py

Optional:
  RESET_USER_GENERATION_COUNTS=1  -> Resets users.monthly_generations to 0 and updates last_generation_reset

Notes:
  - This script is idempotent; drops only tables that exist.
  - Uses asyncpg for direct execution; no Prisma dependency.
  - Does not touch auth tables (users, accounts, sessions, verificationtokens).
"""

import asyncio
import os
from datetime import datetime
from typing import List
from pathlib import Path

import asyncpg

try:
    from dotenv import load_dotenv  # python-dotenv already in requirements
except ImportError:  # graceful fallback
    load_dotenv = None  # type: ignore


def _load_environment():
    """Load environment variables from backend/.env or project root .env if present.

    Order of precedence (first found wins):
      1. Existing process environment (never overwritten)
      2. backend/.env (alongside this script)
      3. project root .env (parent directory)
    """
    if load_dotenv is None:
        return

    script_dir = Path(__file__).resolve().parent
    backend_env = script_dir / ".env"
    root_env = script_dir.parent / ".env"

    # Load backend/.env first (do not override existing vars)
    if backend_env.exists():
        load_dotenv(backend_env, override=False)
    # Then root .env (still not overriding existing)
    if root_env.exists():
        load_dotenv(root_env, override=False)


LEGACY_TABLES = [
    # Legacy audit table no longer referenced in active code
    "audit_llm_calls",
]

TRUNCATE_TABLES_IN_ORDER: List[str] = [
    # Order matters due to FK constraints
    "llm_calls",  # references audit_sessions
    "audit_sessions",  # may reference blogs via blog_id (nullable)
    "blog_logs",  # references blogs
    "blogs",
]

OPTIONAL_RESETS = {
    "user_generation_counts": {
        "enabled_env": "RESET_USER_GENERATION_COUNTS",
        "sql": "UPDATE users SET monthly_generations = 0, last_generation_reset = NOW();",
        "description": "Reset per-user monthly generation counters",
    }
}


async def table_exists(conn: asyncpg.Connection, table: str) -> bool:
    query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = $1
        )
    """
    exists = await conn.fetchval(query, table)
    return bool(exists)


async def drop_legacy_tables(conn: asyncpg.Connection, dry_run: bool):
    for table in LEGACY_TABLES:
        if await table_exists(conn, table):
            if dry_run:
                print(f"[DRY RUN] Would drop legacy table: {table}")
            else:
                print(f"Dropping legacy table: {table}")
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        else:
            print(f"Legacy table not present (skip): {table}")


async def truncate_tables(conn: asyncpg.Connection, dry_run: bool):
    for table in TRUNCATE_TABLES_IN_ORDER:
        if await table_exists(conn, table):
            if dry_run:
                print(f"[DRY RUN] Would TRUNCATE {table} RESTART IDENTITY CASCADE")
            else:
                print(f"Truncating table: {table}")
                # RESTART IDENTITY is harmless if PKs are UUID/text
                await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
        else:
            print(f"Table missing (skip truncate): {table}")


async def apply_optional_resets(conn: asyncpg.Connection, dry_run: bool):
    for key, spec in OPTIONAL_RESETS.items():
        if os.getenv(spec["enabled_env"], "0").lower() in ("1", "true", "yes"):
            if dry_run:
                print(f"[DRY RUN] Would execute optional reset: {spec['description']}")
            else:
                print(f"Applying optional reset: {spec['description']}")
                await conn.execute(spec["sql"])


async def main():
    # Ensure .env files are loaded before reading env vars
    _load_environment()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set. Aborting.")
        return

    if os.getenv("RUN_DB_CLEANUP") != "confirm":
        print("❌ Refusing to run. Set RUN_DB_CLEANUP=confirm to proceed.")
        return

    dry_run = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    mode = "DRY RUN" if dry_run else "EXECUTION"
    print(f"🚀 Starting database cleanup ({mode}) at {datetime.utcnow().isoformat()}Z")

    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(database_url, timeout=10)
        if conn is None:  # safety, though asyncpg.connect should raise on failure
            print("❌ Failed to obtain database connection")
            return

        tx = None
        if not dry_run:
            tx = conn.transaction()
            await tx.start()

        await drop_legacy_tables(conn, dry_run)
        await truncate_tables(conn, dry_run)
        await apply_optional_resets(conn, dry_run)

        if tx is not None:
            await tx.commit()
        print("✅ Cleanup complete")

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        if "tx" in locals() and tx is not None:
            try:
                await tx.rollback()
            except Exception:
                pass
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
