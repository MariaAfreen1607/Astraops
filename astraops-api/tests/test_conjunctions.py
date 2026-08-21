"""Tests for services/conjunctions.py — SGP4 screening, floor filter, and edge cases."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import (
    ISS_TLE_NAME,
    ISS_TLE_LINE1,
    ISS_TLE_LINE2,
    SAT2_TLE_NAME,
    SAT2_TLE_LINE1,
    SAT2_TLE_LINE2,
    TWO_SAT_TLE_TEXT,
    ONE_SAT_TLE_TEXT,
)
from models import SatelliteListResponse, TLERecord
from services.conjunctions import (
    DOCKED_FLOOR_KM,
    _risk_level,
    _collision_probability,
    screen_conjunctions,
)
from cache import cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sat_list(*pairs) -> SatelliteListResponse:
    """Build a SatelliteListResponse from (name, line1, line2) tuples."""
    sats = [
        TLERecord(
            name=name,
            norad_cat_id=line1[2:7].strip(),
            epoch=line1[18:32].strip(),
            line1=line1,
            line2=line2,
        )
        for name, line1, line2 in pairs
    ]
    return SatelliteListResponse(
        count=len(sats),
        fetched_at=datetime.now(timezone.utc),
        source="CelesTrak",
        satellites=sats,
    )


# ===========================================================================
# Unit tests — pure functions
# ===========================================================================

class TestRiskLevel:
    def test_below_1km_is_high(self):
        assert _risk_level(0.5) == "HIGH"

    def test_exact_1km_is_medium(self):
        # boundary: < 1.0 → HIGH, so 1.0 itself is MEDIUM
        assert _risk_level(1.0) == "MEDIUM"

    def test_between_1_and_5km_is_medium(self):
        assert _risk_level(3.0) == "MEDIUM"

    def test_5km_and_above_is_low(self):
        assert _risk_level(5.0) == "LOW"
        assert _risk_level(100.0) == "LOW"


class TestCollisionProbability:
    def test_returns_float_between_0_and_1(self):
        pc = _collision_probability(1.0)
        assert 0.0 <= pc <= 1.0

    def test_closer_approach_has_higher_probability(self):
        pc_close = _collision_probability(0.1)
        pc_far = _collision_probability(5.0)
        assert pc_close > pc_far

    def test_zero_miss_distance_gives_nonzero_probability(self):
        # At zero range the formula gives max possible Pc (still < 1 due to model).
        assert _collision_probability(0.0) > 0.0


class TestDockedFloorConstant:
    def test_floor_is_positive_and_small(self):
        """DOCKED_FLOOR_KM must be > 0 and < 1 km to filter co-located objects."""
        assert 0.0 < DOCKED_FLOOR_KM < 1.0


# ===========================================================================
# Async service tests
# ===========================================================================

@pytest.mark.asyncio
class TestScreenConjunctions:
    """screen_conjunctions — exercised via fetch_satellites monkeypatch."""

    async def test_fewer_than_two_valid_tles_returns_empty_events(self, monkeypatch):
        """When only one valid TLE is available, no pairs can be formed."""
        one_sat = _sat_list((ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2))
        monkeypatch.setattr(
            "services.conjunctions.fetch_satellites",
            AsyncMock(return_value=one_sat),
        )
        result = await screen_conjunctions(group="test", threshold_km=10.0)

        assert result.events == []
        assert result.total_pairs_screened == 0

    async def test_zero_satellites_returns_empty_events(self, monkeypatch):
        """An empty group must not cause any error and must return zero events."""
        empty = SatelliteListResponse(
            count=0,
            fetched_at=datetime.now(timezone.utc),
            source="CelesTrak",
            satellites=[],
        )
        monkeypatch.setattr(
            "services.conjunctions.fetch_satellites",
            AsyncMock(return_value=empty),
        )
        result = await screen_conjunctions(group="empty", threshold_km=10.0)
        assert result.events == []
        assert result.total_pairs_screened == 0

    async def test_two_real_satellites_screened_without_error(self, monkeypatch):
        """Two structurally valid TLEs must complete the full SGP4 pipeline."""
        two_sats = _sat_list(
            (ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2),
            (SAT2_TLE_NAME, SAT2_TLE_LINE1, SAT2_TLE_LINE2),
        )
        monkeypatch.setattr(
            "services.conjunctions.fetch_satellites",
            AsyncMock(return_value=two_sats),
        )
        # Use a very short window to keep the test fast.
        result = await screen_conjunctions(
            group="test",
            threshold_km=10000.0,   # large threshold so at least 0-1 events pass
            window_minutes=1,
            step_seconds=60,
        )
        # The structural assertion: response model is well-formed
        assert isinstance(result.total_pairs_screened, int)
        assert result.total_pairs_screened >= 0
        assert isinstance(result.events, list)

    async def test_docked_floor_filters_zero_separation(self, monkeypatch):
        """A satellite paired with itself (or a clone at the same TLE) must be
        filtered out by the DOCKED_FLOOR_KM guard, yielding no conjunction event."""
        # Two identical TLEs → separation is identically 0 at every time step.
        clone_name = "ISS-CLONE"
        # Use same TLE lines but a different NORAD-like name so they pass the
        # uniqueness check — the service only deduplicates by list position.
        clone_line1 = ISS_TLE_LINE1.replace("25544", "99999")
        clone = _sat_list(
            (ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2),
            (clone_name, clone_line1, ISS_TLE_LINE2),
        )
        monkeypatch.setattr(
            "services.conjunctions.fetch_satellites",
            AsyncMock(return_value=clone),
        )
        result = await screen_conjunctions(
            group="test",
            threshold_km=500.0,    # large enough to capture even zero-range pairs
            window_minutes=1,
            step_seconds=60,
        )
        # Zero-separation pairs must be excluded by the DOCKED_FLOOR_KM filter.
        for evt in result.events:
            assert evt.min_range_km >= DOCKED_FLOOR_KM, (
                f"Event {evt.sat1_norad}/{evt.sat2_norad} has range "
                f"{evt.min_range_km} km which is below DOCKED_FLOOR_KM={DOCKED_FLOOR_KM}"
            )

    async def test_result_is_cached(self, monkeypatch):
        two_sats = _sat_list(
            (ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2),
            (SAT2_TLE_NAME, SAT2_TLE_LINE1, SAT2_TLE_LINE2),
        )
        mock_fetch = AsyncMock(return_value=two_sats)
        monkeypatch.setattr("services.conjunctions.fetch_satellites", mock_fetch)

        await screen_conjunctions(
            group="test",
            threshold_km=10.0,
            window_minutes=1,
            step_seconds=60,
        )
        # The fetch function should have been called exactly once; the second
        # screen_conjunctions call (with same args) must use the cache.
        await screen_conjunctions(
            group="test",
            threshold_km=10.0,
            window_minutes=1,
            step_seconds=60,
        )
        assert mock_fetch.call_count == 1

    async def test_events_sorted_by_min_range(self, monkeypatch):
        """Returned events must be sorted closest-first."""
        two_sats = _sat_list(
            (ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2),
            (SAT2_TLE_NAME, SAT2_TLE_LINE1, SAT2_TLE_LINE2),
        )
        monkeypatch.setattr(
            "services.conjunctions.fetch_satellites",
            AsyncMock(return_value=two_sats),
        )
        result = await screen_conjunctions(
            group="test",
            threshold_km=10000.0,
            window_minutes=2,
            step_seconds=60,
        )
        ranges = [e.min_range_km for e in result.events]
        assert ranges == sorted(ranges)
