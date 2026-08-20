"""Space weather service — proxies NASA DONKI API for solar events."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from cache import cache
from config import get_settings
from models import (
    CMEEvent,
    GeomagneticStorm,
    SolarFlare,
    SpaceWeatherResponse,
)

logger = logging.getLogger(__name__)


def _safe_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_flares(data: list[dict]) -> list[SolarFlare]:
    flares: list[SolarFlare] = []
    for item in data:
        try:
            flares.append(
                SolarFlare(
                    flare_id=item.get("flrID", ""),
                    begin_time=_safe_datetime(item.get("beginTime")),
                    peak_time=_safe_datetime(item.get("peakTime")),
                    end_time=_safe_datetime(item.get("endTime")),
                    class_type=item.get("classType"),
                    source_location=item.get("sourceLocation"),
                    active_region=str(item.get("activeRegionNum", "")) or None,
                    link=item.get("link"),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed flare record: %s", exc)
    return flares


def _parse_cmes(data: list[dict]) -> list[CMEEvent]:
    cmes: list[CMEEvent] = []
    for item in data:
        try:
            # Speed is nested in analysisData list
            speed = None
            for analysis in item.get("cmeAnalyses") or []:
                if analysis.get("speed") is not None:
                    speed = float(analysis["speed"])
                    break
            cmes.append(
                CMEEvent(
                    activity_id=item.get("activityID", ""),
                    start_time=_safe_datetime(item.get("startTime")),
                    source_location=item.get("sourceLocation"),
                    note=item.get("note"),
                    speed_km_s=speed,
                    type=item.get("type"),
                    link=item.get("link"),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed CME record: %s", exc)
    return cmes


def _parse_storms(data: list[dict]) -> list[GeomagneticStorm]:
    storms: list[GeomagneticStorm] = []
    for item in data:
        try:
            kp_max = None
            for activity in item.get("allKpIndex") or []:
                kp = activity.get("kpIndex")
                if kp is not None:
                    val = float(kp)
                    if kp_max is None or val > kp_max:
                        kp_max = val
            storms.append(
                GeomagneticStorm(
                    gst_id=item.get("gstID", ""),
                    start_time=_safe_datetime(item.get("startTime")),
                    kp_index_max=kp_max,
                    link=item.get("link"),
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed storm record: %s", exc)
    return storms


async def _donki_get(endpoint: str, params: dict) -> list[dict]:
    """GET a single NASA DONKI endpoint; returns empty list on failure."""
    settings = get_settings()
    url = f"{settings.nasa_donki_base_url}/{endpoint}"
    params = {**params, "api_key": settings.nasa_api_key}
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
    except httpx.TimeoutException:
        logger.warning("NASA DONKI timeout for endpoint '%s'", endpoint)
    except httpx.HTTPStatusError as exc:
        logger.warning("NASA DONKI HTTP %s for endpoint '%s'", exc.response.status_code, endpoint)
    except Exception as exc:
        logger.error("Unexpected error from NASA DONKI '%s': %s", endpoint, exc)
    return []


async def fetch_space_weather(days: int = 7) -> SpaceWeatherResponse:
    """Fetch solar flares, CMEs, and geomagnetic storms for the last *days* days."""
    settings = get_settings()
    cache_key = f"spaceweather:{days}"

    cached = cache.get(cache_key)
    if cached:
        logger.debug("Cache HIT for space weather (days=%s)", days)
        return cached

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")
    date_params = {"startDate": start_date, "endDate": end_date}

    flare_data, cme_data, storm_data = await _donki_get("FLR", date_params), \
        await _donki_get("CME", date_params), \
        await _donki_get("GST", date_params)

    result = SpaceWeatherResponse(
        fetched_at=datetime.now(timezone.utc),
        start_date=start_date,
        end_date=end_date,
        solar_flares=_parse_flares(flare_data),
        cmes=_parse_cmes(cme_data),
        geomagnetic_storms=_parse_storms(storm_data),
    )
    cache.set(cache_key, result, settings.spaceweather_cache_ttl)
    return result
