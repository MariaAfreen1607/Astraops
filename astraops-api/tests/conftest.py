"""Shared pytest fixtures and test constants for the AstraOps API test suite."""

from __future__ import annotations

import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so all source modules are importable
# without an install step.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

# ---------------------------------------------------------------------------
# Real TLE blocks used across multiple test modules.
# ISS (ZARYA) — NORAD 25544, epoch 2024-001 (synthetic but structurally valid).
# ---------------------------------------------------------------------------

ISS_TLE_NAME = "ISS (ZARYA)"
ISS_TLE_LINE1 = "1 25544U 98067A   24001.50000000  .00001764  00000-0  40218-4 0  9993"
ISS_TLE_LINE2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50377579432900"

# A second satellite for pair-screening tests (NORAD 43226, Starlink-placeholder).
SAT2_TLE_NAME = "STARLINK-0001"
SAT2_TLE_LINE1 = "1 44235U 19029D   24001.50000000  .00002135  00000-0  14636-3 0  9998"
SAT2_TLE_LINE2 = "2 44235  53.0000 200.0000 0001230  90.0000 270.0000 15.06390949270000"

# Three-block TLE text (ISS + STARLINK) used to mock CelesTrak responses.
TWO_SAT_TLE_TEXT = "\n".join([
    ISS_TLE_NAME,
    ISS_TLE_LINE1,
    ISS_TLE_LINE2,
    SAT2_TLE_NAME,
    SAT2_TLE_LINE1,
    SAT2_TLE_LINE2,
])

ONE_SAT_TLE_TEXT = "\n".join([
    ISS_TLE_NAME,
    ISS_TLE_LINE1,
    ISS_TLE_LINE2,
])

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    """Wipe the global in-memory cache before every test for isolation."""
    from cache import cache
    cache.clear()
    yield
    cache.clear()
