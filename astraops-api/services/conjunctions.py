"""Conjunction screening — real SGP4 propagation with pairwise close-approach detection.

Screening method:
  1. Parse each TLE into an SGP4 satellite record.
  2. Propagate every satellite across a time window on a coarse grid (TEME frame, km).
  3. Compute the full pairwise distance matrix at each step, tracking the running minimum.
  4. For pairs that breach the threshold, re-propagate at 1-second resolution around the
     coarse minimum to refine time of closest approach and miss distance.
  5. Estimate collision probability using a circular-covariance closed form.

Assumptions are declared as module constants so they can be cited and challenged.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import Satrec, SatrecArray, jday

from cache import cache
from config import get_settings
from models import ConjunctionEvent, ConjunctionScreenResponse
from services.satellites import fetch_satellites

logger = logging.getLogger(__name__)

# --- Screening assumptions -------------------------------------------------
HARD_BODY_RADIUS_KM = 0.020    # 20 m combined object radius
POSITION_SIGMA_KM = 0.200      # 200 m isotropic 1-sigma position uncertainty
DEFAULT_WINDOW_MINUTES = 180   # 3-hour look-ahead
DEFAULT_STEP_SECONDS = 30      # coarse grid resolution
REFINE_STEP_SECONDS = 1        # fine grid resolution near TCA
MAX_SATELLITES = 150           # O(N^2 * T) guard
DOCKED_FLOOR_KM = 0.050        # pairs closer than this are treated as co-located, not conjunctions


def _time_grid(start: datetime, minutes: int, step_s: int):
    n = int(minutes * 60 / step_s) + 1
    jd = np.empty(n)
    fr = np.empty(n)
    for i in range(n):
        t = start + timedelta(seconds=i * step_s)
        j, f = jday(t.year, t.month, t.day, t.hour, t.minute,
                    t.second + t.microsecond * 1e-6)
        jd[i] = j
        fr[i] = f
    return jd, fr, n


def _risk_level(range_km: float) -> str:
    if range_km < 1.0:
        return "HIGH"
    if range_km < 5.0:
        return "MEDIUM"
    return "LOW"


def _collision_probability(miss_km: float) -> float:
    """Closed-form Pc for isotropic combined covariance in the encounter plane."""
    s2 = 2.0 * POSITION_SIGMA_KM ** 2
    return math.exp(-(miss_km ** 2) / s2) * (1.0 - math.exp(-(HARD_BODY_RADIUS_KM ** 2) / s2))


def _refine(sat_a: Satrec, sat_b: Satrec, center: datetime, span_s: int):
    """Re-propagate a single pair at 1 s resolution; return (tca, miss_km, rel_vel)."""
    best = (None, float("inf"), None)
    for offset in range(0, span_s + 1, REFINE_STEP_SECONDS):
        t = center + timedelta(seconds=offset)
        j, f = jday(t.year, t.month, t.day, t.hour, t.minute,
                    t.second + t.microsecond * 1e-6)
        ea, ra, va = sat_a.sgp4(j, f)
        eb, rb, vb = sat_b.sgp4(j, f)
        if ea != 0 or eb != 0:
            continue
        d = math.dist(ra, rb)
        if d < best[1]:
            rel_v = math.dist(va, vb)
            best = (t, d, rel_v)
    return best


async def screen_conjunctions(
    group: str = "active",
    threshold_km: float = 10.0,
    max_pairs: int = MAX_SATELLITES,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
    step_seconds: int = DEFAULT_STEP_SECONDS,
) -> ConjunctionScreenResponse:
    """Screen a CelesTrak group for close approaches using SGP4 propagation."""
    settings = get_settings()
    cache_key = f"conjunctions:{group}:{threshold_km}:{window_minutes}:{step_seconds}"

    cached = cache.get(cache_key)
    if cached:
        logger.debug("Cache HIT for conjunctions group='%s'", group)
        return cached

    screened_at = datetime.now(timezone.utc)
    sat_response = await fetch_satellites(group)

    records, satrecs = [], []
    for rec in sat_response.satellites[: min(max_pairs, MAX_SATELLITES)]:
        try:
            s = Satrec.twoline2rv(rec.line1, rec.line2)
        except Exception as exc:
            logger.debug("Skipping unparsable TLE %s: %s", rec.norad_cat_id, exc)
            continue
        records.append(rec)
        satrecs.append(s)

    n = len(satrecs)
    if n < 2:
        logger.warning("Not enough valid TLEs to screen group '%s' (got %d)", group, n)
        return ConjunctionScreenResponse(
            screened_at=screened_at,
            total_pairs_screened=0,
            threshold_km=threshold_km,
            events=[],
        )

    jd, fr, steps = _time_grid(screened_at, window_minutes, step_seconds)
    err, pos, _vel = SatrecArray(satrecs).sgp4(jd, fr)   # (n, steps), (n, steps, 3)

    pos = np.asarray(pos, dtype=float)
    pos[np.asarray(err) != 0] = np.nan

    # Running minimum distance and the step index at which it occurs.
    best_dist = np.full((n, n), np.inf)
    best_step = np.zeros((n, n), dtype=int)

    for t in range(steps):
        p = pos[:, t, :]
        diff = p[:, None, :] - p[None, :, :]
        dist = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        np.fill_diagonal(dist, np.inf)
        dist = np.nan_to_num(dist, nan=np.inf)
        improved = dist < best_dist
        best_dist = np.where(improved, dist, best_dist)
        best_step = np.where(improved, t, best_step)

    iu = np.triu_indices(n, k=1)
    total_pairs = len(iu[0])

    events: list[ConjunctionEvent] = []
    for i, j in zip(*iu):
        coarse = best_dist[i, j]
        if not np.isfinite(coarse) or coarse > threshold_km:
            continue
        center = screened_at + timedelta(seconds=int(best_step[i, j]) * step_seconds)
        tca, miss_km, rel_v = _refine(satrecs[i], satrecs[j], center, step_seconds)
        if tca is None:
            tca, miss_km, rel_v = center, float(coarse), None
        if miss_km > threshold_km or miss_km < DOCKED_FLOOR_KM:
            continue
        events.append(
            ConjunctionEvent(
                sat1_norad=records[i].norad_cat_id,
                sat1_name=records[i].name,
                sat2_norad=records[j].norad_cat_id,
                sat2_name=records[j].name,
                tca=tca,
                min_range_km=round(miss_km, 4),
                relative_velocity_km_s=round(rel_v, 4) if rel_v is not None else None,
                probability_of_collision=_collision_probability(miss_km),
                risk_level=_risk_level(miss_km),
            )
        )

    events.sort(key=lambda e: e.min_range_km)
    logger.info(
        "Screened %d pairs over %d min for group '%s': %d events below %.1f km",
        total_pairs, window_minutes, group, len(events), threshold_km,
    )

    result = ConjunctionScreenResponse(
        screened_at=screened_at,
        total_pairs_screened=total_pairs,
        threshold_km=threshold_km,
        events=events,
    )
    cache.set(cache_key, result, settings.conjunction_cache_ttl)
    return result
