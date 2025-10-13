#!/usr/bin/env python3
"""
Quick notification harness retired with stdout capture removal.
"""

import pytest

pytest.skip(
    "Legacy quick notification harness removed; callbacks stream structured events natively.",
    allow_module_level=True,
)