"""Tests for services/satellites.py — TLE parsing and fetch behaviour."""

from __future__ import annotations

import pytest
import httpx

from tests.conftest import (
    ISS_TLE_NAME,
    ISS_TLE_LINE1,
    ISS_TLE_LINE2,
    TWO_SAT_TLE_TEXT,
    ONE_SAT_TLE_TEXT,
)

from services.satellites import (
    _parse_tle_line2,
    _parse_tle_block,
    _parse_tle_text,
    fetch_satellites,
    fetch_satellite_by_norad,
)
from cache import cache

# ---------------------------------------------------------------------------
# The real httpx.AsyncClient, captured before any patching happens.
# Used in mock factories so the lambda doesn't call itself recursively.
# ---------------------------------------------------------------------------
_RealAsyncClient = httpx.AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_client(status: int = 200, text: str = "") -> httpx.AsyncClient:
    """Return a real AsyncClient wired to a MockTransport."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, text=text)
    return _RealAsyncClient(transport=httpx.MockTransport(handler))


def _patch_httpx(monkeypatch, status: int = 200, text: str = ""):
    """Monkeypatch httpx.AsyncClient in the satellites service module."""
    monkeypatch.setattr(
        "services.satellites.httpx.AsyncClient",
        lambda **kw: _mock_client(status, text),
    )


# ===========================================================================
# Unit tests — pure parsing functions (no I/O)
# ===========================================================================

class TestParseTleLine2:
    """_parse_tle_line2 extracts orbital elements from a valid line 2."""

    def test_inclination_parsed(self):
        result = _parse_tle_line2(ISS_TLE_LINE2)
        assert abs(result["inclination_deg"] - 51.6416) < 0.001

    def test_mean_motion_parsed(self):
        result = _parse_tle_line2(ISS_TLE_LINE2)
        assert 15.0 < result["mean_motion"] < 16.0

    def test_eccentricity_parsed(self):
        result = _parse_tle_line2(ISS_TLE_LINE2)
        assert 0.0 < result["eccentricity"] < 0.01

    def test_altitude_km_is_positive(self):
        result = _parse_tle_line2(ISS_TLE_LINE2)
        # ISS altitude ~400 km
        assert 300 < result["altitude_km"] < 500

    def test_malformed_line2_returns_empty_dict(self):
        result = _parse_tle_line2("not a tle line at all")
        assert result == {}

    def test_empty_string_returns_empty_dict(self):
        assert _parse_tle_line2("") == {}


class TestParseTleBlock:
    """_parse_tle_block assembles a TLERecord from a 3-line list."""

    def test_valid_block_returns_record(self):
        rec = _parse_tle_block([ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2])
        assert rec is not None
        assert rec.name == ISS_TLE_NAME
        assert rec.norad_cat_id == "25544"

    def test_epoch_extracted(self):
        rec = _parse_tle_block([ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2])
        assert rec is not None
        assert rec.epoch.startswith("24001")

    def test_line1_and_line2_preserved_verbatim(self):
        rec = _parse_tle_block([ISS_TLE_NAME, ISS_TLE_LINE1, ISS_TLE_LINE2])
        assert rec is not None
        assert rec.line1 == ISS_TLE_LINE1
        assert rec.line2 == ISS_TLE_LINE2

    def test_fewer_than_three_lines_returns_none(self):
        assert _parse_tle_block([ISS_TLE_NAME, ISS_TLE_LINE1]) is None

    def test_empty_list_returns_none(self):
        assert _parse_tle_block([]) is None

    def test_garbage_lines_return_none_or_valid_record(self):
        # Must not raise regardless of content.
        result = _parse_tle_block(["NAME", "GARBAGE LINE1", "GARBAGE LINE2"])
        if result is not None:
            assert result.altitude_km is None or isinstance(result.altitude_km, float)


class TestParseTleText:
    """_parse_tle_text splits a multi-satellite TLE blob into records."""

    def test_two_satellites_parsed(self):
        records = _parse_tle_text(TWO_SAT_TLE_TEXT)
        assert len(records) == 2

    def test_one_satellite_parsed(self):
        records = _parse_tle_text(ONE_SAT_TLE_TEXT)
        assert len(records) == 1

    def test_empty_string_returns_empty_list(self):
        assert _parse_tle_text("") == []

    def test_only_whitespace_returns_empty_list(self):
        assert _parse_tle_text("   \n\n   ") == []

    def test_first_record_name_matches(self):
        records = _parse_tle_text(TWO_SAT_TLE_TEXT)
        assert records[0].name == ISS_TLE_NAME

    def test_records_have_norad_ids(self):
        records = _parse_tle_text(TWO_SAT_TLE_TEXT)
        norad_ids = {r.norad_cat_id for r in records}
        assert "25544" in norad_ids


# ===========================================================================
# Async service tests — HTTP calls stubbed via service-level monkeypatch
# ===========================================================================

@pytest.mark.asyncio
class TestFetchSatellites:
    """fetch_satellites — network success, errors, and the stale-notice path."""

    async def test_successful_fetch_returns_satellites(self, monkeypatch):
        _patch_httpx(monkeypatch, 200, TWO_SAT_TLE_TEXT)
        result = await fetch_satellites("active")
        assert result.count == 2
        assert len(result.satellites) == 2

    async def test_successful_fetch_populates_cache(self, monkeypatch):
        _patch_httpx(monkeypatch, 200, TWO_SAT_TLE_TEXT)
        await fetch_satellites("active")
        assert cache.get("tle:active") is not None

    async def test_cache_hit_skips_network(self, monkeypatch):
        """Once cached, fetch_satellites must not call the network again."""
        call_count = {"n": 0}

        def counting_handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(200, text=TWO_SAT_TLE_TEXT)

        monkeypatch.setattr(
            "services.satellites.httpx.AsyncClient",
            lambda **kw: _RealAsyncClient(transport=httpx.MockTransport(counting_handler)),
        )
        await fetch_satellites("active")  # populates cache
        await fetch_satellites("active")  # must use cache
        assert call_count["n"] == 1

    async def test_timeout_falls_back_to_last_known_good(self, monkeypatch):
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        monkeypatch.setattr(
            "services.satellites.httpx.AsyncClient",
            lambda **kw: _RealAsyncClient(transport=httpx.MockTransport(timeout_handler)),
        )
        result = await fetch_satellites("active")
        assert result.source == "CelesTrak"
        assert result.count == len(result.satellites)

        seeded = await fetch_satellites("stations")
        assert seeded.count > 0, "a seeded group must survive a timeout"

        seeded = await fetch_satellites("stations")
        assert seeded.count > 0, "a seeded group must survive a timeout"

    async def test_http_500_falls_back_to_last_known_good(self, monkeypatch):
        _patch_httpx(monkeypatch, 500, "Server Error")
        result = await fetch_satellites("active")
        assert result.source == "CelesTrak"
        assert result.count == len(result.satellites)

        seeded = await fetch_satellites("stations")
        assert seeded.count > 0, "a seeded group must survive an upstream 500"

    async def test_stale_notice_returns_cached_stale_data(self, monkeypatch):
        """When CelesTrak replies with its 'has not updated' notice, the service
        must return the previously stored stale result rather than an empty list."""
        from datetime import datetime, timezone
        from models import SatelliteListResponse, TLERecord

        stale_satellite = TLERecord(
            name=ISS_TLE_NAME,
            norad_cat_id="25544",
            epoch="24001.5",
            line1=ISS_TLE_LINE1,
            line2=ISS_TLE_LINE2,
        )
        stale_response = SatelliteListResponse(
            count=1,
            fetched_at=datetime.now(timezone.utc),
            source="CelesTrak",
            satellites=[stale_satellite],
        )
        cache.set("tle:stale:active", stale_response, 86400)

        stale_notice = "has not updated since your last successful retrieval"
        _patch_httpx(monkeypatch, 200, stale_notice)

        result = await fetch_satellites("active")

        assert result.satellites == [stale_satellite]
        assert result.count == 1

    async def test_stale_notice_falls_back_to_seed(self, monkeypatch):
        stale_notice = "has not updated since your last successful retrieval"
        _patch_httpx(monkeypatch, 200, stale_notice)
        result = await fetch_satellites("active")
        assert result.source == "CelesTrak"
        assert result.count == len(result.satellites)

        seeded = await fetch_satellites("stations")
        assert seeded.count > 0, "a seeded group must survive a stale-data notice"


@pytest.mark.asyncio
class TestFetchSatelliteByNorad:
    """fetch_satellite_by_norad — single-sat lookup."""

    async def test_returns_detail_for_known_norad(self, monkeypatch):
        _patch_httpx(monkeypatch, 200, ONE_SAT_TLE_TEXT)
        result = await fetch_satellite_by_norad("25544")
        assert result is not None
        assert result.satellite.norad_cat_id == "25544"

    async def test_returns_none_on_empty_body(self, monkeypatch):
        _patch_httpx(monkeypatch, 200, "")
        result = await fetch_satellite_by_norad("99999")
        assert result is None

    async def test_returns_none_on_http_error(self, monkeypatch):
        _patch_httpx(monkeypatch, 404, "Not Found")
        result = await fetch_satellite_by_norad("00001")
        assert result is None

    async def test_result_is_cached(self, monkeypatch):
        _patch_httpx(monkeypatch, 200, ONE_SAT_TLE_TEXT)
        await fetch_satellite_by_norad("25544")
        assert cache.get("tle:norad:25544") is not None
