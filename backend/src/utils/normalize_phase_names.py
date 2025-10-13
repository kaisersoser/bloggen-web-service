# flake8: noqa
"""Standalone utility to normalize legacy phase names in llm_calls.

Usage:
    python normalize_phase_names.py

Requires DATABASE_URL to be set. Safely maps historical variant phase
names to the current canonical set used by BlogGenerationFlow:
    initialization, research, content_generation, fact_checking, finalization

Any phase not recognized is left untouched.
"""

from __future__ import annotations
import asyncio
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker


async def main():
    async def _pool_provider():
        tracker = EnhancedDatabaseAuditTracker(
            session_type="phase_normalization", user_id="system", blog_id=None
        )
        return await tracker._get_database_connection()  # type: ignore

    results = await EnhancedDatabaseAuditTracker.normalize_phase_names(_pool_provider)
    if results:
        print("Normalization complete:")
        for phase, count in results.items():
            print(f"  {phase}: {count} row(s) updated")
    else:
        print("No phase name updates were necessary.")


if __name__ == "__main__":
    asyncio.run(main())
