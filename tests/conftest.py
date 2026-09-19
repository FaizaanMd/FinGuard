"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture
def engineered_frame():
    from tests.helpers import make_engineered_frame
    return make_engineered_frame(n=2000, seed=0)