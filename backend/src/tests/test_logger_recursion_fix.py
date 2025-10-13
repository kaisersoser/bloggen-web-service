"""
Legacy logging recursion test for stdout capture (deprecated).

This test verifies that the re-entrancy guard and scoped logger capture
prevents infinite recursion under concurrent load.

Related to: UNIFIED_MODERNIZATION_PLAN.md - Phase 1.1
"""

import pytest

pytest.skip(
    "Stdout capture removed during Phase 2; see test_blog_event_listener.py for callback coverage.",
    allow_module_level=True,
)
