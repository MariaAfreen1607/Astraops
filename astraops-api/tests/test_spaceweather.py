"""Tests for services/spaceweather.py — DONKI proxy, parsing, and error handling."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from services.spaceweather import (
    _safe_datetime,
    _parse_flares,
    _parse_cmes,
    _parse_storms,
    _donki_get,
    fetch_space_weather,
)
from cache import cache

# Capture the real AsyncClient before any monkeypatching.
_RealAsyncClient = httpx.AsyncClient


# ---------------------------------------------------------------------------
# Helper — mock client factory for spaceweather service namespace
# ---------------------------------------------------------------------------

def _patch_donki(monkeypatch, handler):
    """Patch httpx.AsyncClient in the spaceweather service module only."""
    monkeypatch.setattr(
        "services.spaceweather.httpx.AsyncClient",
        lambda **kw: _RealAsyncClient(transport=httpx.MockTransport(handler)),
    )


def _json_handler(status: int, payload):
    """Return a handler that always responds with the given status and JSON payload."""
    body = json.dumps(payload)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status,
            text=body,
            headers={"content-type": "application/json"},
        )
    return handler


# ===========================================================================
# Unit tests — pure parsing helpers
# ===========================================================================

class TestSafeDatetime:
    def test_parses_donki_format(self):
        dt = _safe_datetime("2024-01-15T06:30Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.tzinfo == timezone.utc

    def test_parses_date_only_format(self):
        dt = _safe_datetime("2024-06-01")
        assert dt is not None
        assert dt.year == 2024

    def test_returns_none_for_empty_string(self):
        assert _safe_datetime("") is None

    def test_returns_none_for_none_input(self):
        assert _safe_datetime(None) is None  # type: ignore[arg-type]

    def test_returns_none_for_garbage(self):
        assert _safe_datetime("not-a-date") is None


class TestParseFlares:
    _FLARE = {
        "flrID": "2024-001-FLR-001",
        "beginTime": "2024-01-01T06:00Z",
        "peakTime": "2024-01-01T06:05Z",
        "endTime": "2024-01-01T06:20Z",
        "classType": "X1.5",
        "sourceLocation": "N20W10",
        "activeRegionNum": 13546,
        "link": "https://example.com/flare",
    }

    def test_valid_flare_parsed(self):
        results = _parse_flares([self._FLARE])
        assert len(results) == 1
        f = results[0]
        assert f.flare_id == "2024-001-FLR-001"
        assert f.class_type == "X1.5"

    def test_empty_list_returns_empty(self):
        assert _parse_flares([]) == []

    def test_malformed_record_skipped_not_raised(self):
        # Pass a record that will cause an internal parse error — must not propagate.
        bad = {"flrID": None, "classType": object()}
        results = _parse_flares([bad])
        assert isinstance(results, list)

    def test_multiple_flares_all_parsed(self):
        results = _parse_flares([self._FLARE, self._FLARE])
        assert len(results) == 2


class TestParseCmes:
    _CME = {
        "activityID": "2024-001-CME-001",
        "startTime": "2024-01-02T08:00Z",
        "sourceLocation": "S15E20",
        "note": "Halo CME",
        "cmeAnalyses": [{"speed": 1200.0}],
        "type": "C",
        "link": "https://example.com/cme",
    }

    def test_valid_cme_parsed(self):
        results = _parse_cmes([self._CME])
        assert len(results) == 1
        c = results[0]
        assert c.activity_id == "2024-001-CME-001"
        assert c.speed_km_s == 1200.0

    def test_speed_extracted_from_analyses(self):
        results = _parse_cmes([self._CME])
        assert results[0].speed_km_s == 1200.0

    def test_missing_analyses_gives_none_speed(self):
        cme = {**self._CME, "cmeAnalyses": []}
        results = _parse_cmes([cme])
        assert results[0].speed_km_s is None

    def test_empty_list_returns_empty(self):
        assert _parse_cmes([]) == []


class TestParseStorms:
    _STORM = {
        "gstID": "2024-001-GST-001",
        "startTime": "2024-01-03T12:00Z",
        "allKpIndex": [
            {"kpIndex": "5.0"},
            {"kpIndex": "7.3"},
            {"kpIndex": "6.0"},
        ],
        "link": "https://example.com/storm",
    }

    def test_valid_storm_parsed(self):
        results = _parse_storms([self._STORM])
        assert len(results) == 1

    def test_kp_index_max_extracted(self):
        results = _parse_storms([self._STORM])
        assert results[0].kp_index_max == pytest.approx(7.3)

    def test_empty_kp_index_gives_none(self):
        storm = {**self._STORM, "allKpIndex": []}
        results = _parse_storms([storm])
        assert results[0].kp_index_max is None

    def test_empty_list_returns_empty(self):
        assert _parse_storms([]) == []


# ===========================================================================
# Async tests — _donki_get stub patterns
# ===========================================================================

@pytest.mark.asyncio
class TestDonkiGet:
    """_donki_get — error handling for upstream failures."""

    async def test_returns_list_on_200(self, monkeypatch):
        payload = [{"flrID": "x"}]
        _patch_donki(monkeypatch, _json_handler(200, payload))
        result = await _donki_get("FLR", {"startDate": "2024-01-01"})
        assert result == payload

    async def test_upstream_500_returns_empty_list(self, monkeypatch):
        """A 500 from DONKI must be handled gracefully — no exception propagated."""
        _patch_donki(monkeypatch, _json_handler(500, "Internal Server Error"))
        result = await _donki_get("FLR", {"startDate": "2024-01-01"})
        assert result == []

    async def test_upstream_503_returns_empty_list(self, monkeypatch):
        _patch_donki(monkeypatch, _json_handler(503, "Service Unavailable"))
        result = await _donki_get("CME", {"startDate": "2024-01-01"})
        assert result == []

    async def test_timeout_returns_empty_list(self, monkeypatch):
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        _patch_donki(monkeypatch, timeout_handler)
        result = await _donki_get("GST", {"startDate": "2024-01-01"})
        assert result == []

    async def test_non_list_json_returns_empty_list(self, monkeypatch):
        """DONKI occasionally returns a dict error payload — must be normalised to []."""
        _patch_donki(monkeypatch, _json_handler(200, {"error": "no data"}))
        result = await _donki_get("FLR", {"startDate": "2024-01-01"})
        assert result == []


# ===========================================================================
# Async tests — fetch_space_weather integration
# ===========================================================================

_FLARE_PAYLOAD = [
    {
        "flrID": "2024-001-FLR-001",
        "beginTime": "2024-01-01T06:00Z",
        "peakTime": "2024-01-01T06:05Z",
        "classType": "M2.3",
        "sourceLocation": "N10W05",
        "activeRegionNum": 13500,
        "link": "https://example.com/f",
    }
]

_CME_PAYLOAD = [
    {
        "activityID": "2024-001-CME-001",
        "startTime": "2024-01-01T10:00Z",
        "cmeAnalyses": [{"speed": 800.0}],
        "type": "C",
        "link": "https://example.com/c",
    }
]

_GST_PAYLOAD = [
    {
        "gstID": "2024-001-GST-001",
        "startTime": "2024-01-02T00:00Z",
        "allKpIndex": [{"kpIndex": "6.0"}],
        "link": "https://example.com/g",
    }
]


def _make_router_handler(flr=None, cme=None, gst=None, status: int = 200):
    """Return a handler that routes responses by endpoint path segment."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/FLR" in path:
            data = flr if flr is not None else []
        elif "/CME" in path:
            data = cme if cme is not None else []
        elif "/GST" in path:
            data = gst if gst is not None else []
        else:
            data = []
        if status != 200:
            return httpx.Response(status, text="Error")
        return httpx.Response(
            200,
            text=json.dumps(data),
            headers={"content-type": "application/json"},
        )
    return handler


@pytest.mark.asyncio
class TestFetchSpaceWeather:

    async def test_full_response_populated(self, monkeypatch):
        handler = _make_router_handler(
            flr=_FLARE_PAYLOAD, cme=_CME_PAYLOAD, gst=_GST_PAYLOAD
        )
        _patch_donki(monkeypatch, handler)
        result = await fetch_space_weather(days=7)

        assert len(result.solar_flares) == 1
        assert len(result.cmes) == 1
        assert len(result.geomagnetic_storms) == 1
        assert result.solar_flares[0].class_type == "M2.3"

    async def test_donki_500_for_all_endpoints_gives_empty_lists(self, monkeypatch):
        """All three DONKI endpoints returning 500 must produce empty lists."""
        _patch_donki(monkeypatch, _make_router_handler(status=500))
        result = await fetch_space_weather(days=7)
        assert result.solar_flares == []
        assert result.cmes == []
        assert result.geomagnetic_storms == []

    async def test_result_is_cached_on_success(self, monkeypatch):
        handler = _make_router_handler(
            flr=_FLARE_PAYLOAD, cme=_CME_PAYLOAD, gst=_GST_PAYLOAD
        )
        _patch_donki(monkeypatch, handler)
        await fetch_space_weather(days=3)
        assert cache.get("spaceweather:3") is not None

    async def test_cache_hit_does_not_call_network(self, monkeypatch):
        call_count = {"n": 0}

        def counting(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(
                200,
                text=json.dumps([]),
                headers={"content-type": "application/json"},
            )

        _patch_donki(monkeypatch, counting)
        await fetch_space_weather(days=1)   # first call — hits network (3 endpoints)
        await fetch_space_weather(days=1)   # second call — must use cache
        assert call_count["n"] == 3

    async def test_start_and_end_date_in_response(self, monkeypatch):
        _patch_donki(monkeypatch, _make_router_handler())
        result = await fetch_space_weather(days=7)
        datetime.strptime(result.start_date, "%Y-%m-%d")
        datetime.strptime(result.end_date, "%Y-%m-%d")

    async def test_donki_500_result_not_cached_with_data(self, monkeypatch):
        """An all-failure response — if cached — must contain empty lists (not real data)."""
        _patch_donki(monkeypatch, _make_router_handler(status=500))
        await fetch_space_weather(days=5)
        cached = cache.get("spaceweather:5")
        if cached is not None:
            assert cached.solar_flares == []
            assert cached.cmes == []
            assert cached.geomagnetic_storms == []
