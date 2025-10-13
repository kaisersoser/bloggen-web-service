# flake8: noqa
"""Legacy direct image capture test retired with stdout capture removal."""

import pytest

pytest.skip(
    "Direct stdout-based image capture deprecated; native callbacks cover image telemetry.",
    allow_module_level=True,
)
