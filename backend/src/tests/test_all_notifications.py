# flake8: noqa
"""Legacy comprehensive notification test retired with stdout capture removal."""

import pytest

pytest.skip(
    "Legacy stdout-capture based all-notifications test retired; callback pipeline exercises coverage elsewhere.",
    allow_module_level=True,
)
