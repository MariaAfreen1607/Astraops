"""Satellite service — fetches and parses TLE data from CelesTrak GP API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from cache import cache
from config import get_settings
from models import SatelliteListResponse, SatelliteDetailResponse, TLERecord

logger = logging.getLogger(__name__)


def _parse_tle_line2(line2: str) -> dict:
    """Extract orbital elements from TLE line 2."""
    try:
        inclination = float(line2[8:16].strip())
        eccentricity = float("0." + line2[26:33].strip())
        mean_motion = float(line2[52:63].strip())
        # Rough altitude estimate: semi-major axis from mean motion
        # n (rev/day) -> T (s) -> a (km) -> altitude
        import math
        mu = 398600.4418  # km^3/s^2
        n_rad_s = mean_motion * 2 * math.pi / 86400
        a = (mu / (n_rad_s ** 2)) ** (1 / 3)
        altitude_km = round(a - 6371.0, 1)
        return {
            "inclination_deg": round(inclination, 4),
            "eccentricity": round(eccentricity, 7),
            "mean_motion": round(mean_motion, 8),
            "altitude_km": altitude_km,
        }
    except Exception:
        return {}


def _parse_tle_block(lines: list[str]) -> Optional[TLERecord]:
    """Parse a 3-line TLE block into a TLERecord."""
    if len(lines) < 3:
        return None
    try:
        name = lines[0].strip()
        line1 = lines[1].strip()
        line2 = lines[2].strip()
        norad_cat_id = line1[2:7].strip()
        epoch_raw = line1[18:32].strip()
        orbital = _parse_tle_line2(line2)
        return TLERecord(
            name=name,
            norad_cat_id=norad_cat_id,
            epoch=epoch_raw,
            line1=line1,
            line2=line2,
            **orbital,
        )
    except Exception as exc:
        logger.debug("Failed to parse TLE block: %s", exc)
        return None


def _parse_tle_text(text: str) -> list[TLERecord]:
    """Parse raw TLE text (3-line format) into a list of TLERecords."""
    lines = [l for l in text.splitlines() if l.strip()]
    records: list[TLERecord] = []
    for i in range(0, len(lines) - 2, 3):
        rec = _parse_tle_block(lines[i : i + 3])
        if rec:
            records.append(rec)
    return records


async def fetch_satellites(group: str = "active") -> SatelliteListResponse:
    """Fetch TLE data for a satellite group from CelesTrak."""
    settings = get_settings()
    cache_key = f"tle:{group}"

    cached = cache.get(cache_key)
    if cached:
        logger.debug("Cache HIT for TLE group '%s'", group)
        return cached

    url = settings.celestrak_gp_url
    params = {"GROUP": group, "FORMAT": "tle"}

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            satellites = _parse_tle_text(response.text)
    except httpx.TimeoutException:
        logger.warning("CelesTrak request timed out for group '%s'", group)
        satellites = []
    except httpx.HTTPStatusError as exc:
        logger.warning("CelesTrak HTTP error %s for group '%s'", exc.response.status_code, group)
        satellites = []
    except Exception as exc:
        logger.error("Unexpected error fetching TLE data: %s", exc)
        satellites = []

    result = SatelliteListResponse(
        count=len(satellites),
        fetched_at=datetime.now(timezone.utc),
        source="CelesTrak",
        satellites=satellites,
    )
    if satellites:
        cache.set(cache_key, result, settings.tle_cache_ttl)
    return result


async def fetch_satellite_by_norad(norad_id: str) -> Optional[SatelliteDetailResponse]:
    """Fetch a single satellite by NORAD catalog ID."""
    settings = get_settings()
    cache_key = f"tle:norad:{norad_id}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    url = settings.celestrak_gp_url
    params = {"CATNR": norad_id, "FORMAT": "tle"}

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            records = _parse_tle_text(response.text)
    except (httpx.TimeoutException, httpx.HTTPStatusError, Exception) as exc:
        logger.warning("Failed to fetch NORAD %s: %s", norad_id, exc)
        return None

    if not records:
        return None

    result = SatelliteDetailResponse(
        fetched_at=datetime.now(timezone.utc),
        source="CelesTrak",
        satellite=records[0],
    )
    cache.set(cache_key, result, settings.tle_cache_ttl)
    return result
