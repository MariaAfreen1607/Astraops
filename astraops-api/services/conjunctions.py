"""Conjunction screening service — identifies close satellite approaches."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from cache import cache
from config import get_settings
from models import ConjunctionEvent, ConjunctionScreenResponse
from services.satellites import fetch_satellites

logger = logging.getLogger(__name__)


def _mean_motion_to_altitude_km(mean_motion: float) -> float:
    """Convert TLE mean motion (rev/day) to approximate circular altitude in km."""
    mu = 398600.4418
    n_rad_s = mean_motion * 2 * math.pi / 86400
    a = (mu / (n_rad_s ** 2)) ** (1 / 3)
    return a - 6371.0


def _estimate_separation_km(sat1_alt: float, sat2_alt: float) -> float:
    """
    Rough separation estimate using altitude difference as a proxy.
    A real implementation would propagate TLEs with SGP4.
    This placeholder drives the risk classification logic.
    """
    return abs(sat1_alt - sat2_alt)


def _risk_level(range_km: float) -> str:
    if range_km < 1.0:
        return "HIGH"
    if range_km < 5.0:
        return "MEDIUM"
    return "LOW"


async def screen_conjunctions(
    group: str = "active",
    threshold_km: float = 10.0,
    max_pairs: int = 500,
) -> ConjunctionScreenResponse:
    """
    Screen satellite pairs for potential close approaches.

    This implementation uses altitude-difference as a first-order filter
    (a full SGP4 propagation would replace `_estimate_separation_km`).
    Only pairs whose estimated separation is below *threshold_km* are returned.
    """
    settings = get_settings()
    cache_key = f"conjunctions:{group}:{threshold_km}"

    cached = cache.get(cache_key)
    if cached:
        logger.debug("Cache HIT for conjunctions group='%s' threshold=%.1f", group, threshold_km)
        return cached

    sat_response = await fetch_satellites(group)
    satellites = sat_response.satellites

    # Only consider satellites with altitude data and cap list size
    eligible = [s for s in satellites if s.altitude_km is not None and s.mean_motion is not None]
    eligible = eligible[:max_pairs]

    total_pairs = len(eligible) * (len(eligible) - 1) // 2
    events: list[ConjunctionEvent] = []
    screened_at = datetime.now(timezone.utc)

    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            s1 = eligible[i]
            s2 = eligible[j]
            sep_km = _estimate_separation_km(s1.altitude_km, s2.altitude_km)  # type: ignore[arg-type]
            if sep_km > threshold_km:
                continue
            # Synthetic TCA: now + random offset based on mean-motion difference
            delta_minutes = abs((s1.mean_motion or 0) - (s2.mean_motion or 0)) * 10
            tca = screened_at + timedelta(minutes=delta_minutes)
            events.append(
                ConjunctionEvent(
                    sat1_norad=s1.norad_cat_id,
                    sat1_name=s1.name,
                    sat2_norad=s2.norad_cat_id,
                    sat2_name=s2.name,
                    tca=tca,
                    min_range_km=round(sep_km, 3),
                    relative_velocity_km_s=None,
                    probability_of_collision=None,
                    risk_level=_risk_level(sep_km),
                )
            )

    # Sort by closest approach first
    events.sort(key=lambda e: e.min_range_km)

    result = ConjunctionScreenResponse(
        screened_at=screened_at,
        total_pairs_screened=total_pairs,
        threshold_km=threshold_km,
        events=events,
    )
    if satellites:
        cache.set(cache_key, result, settings.conjunction_cache_ttl)
    return result
