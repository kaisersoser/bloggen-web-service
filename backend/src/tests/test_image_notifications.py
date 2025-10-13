# flake8: noqa
"""Legacy image notification test retired with stdout capture removal."""

import pytest

pytest.skip(
    "Legacy stdout-capture based image notification test retired; callbacks provide coverage now.",
    allow_module_level=True,
)
