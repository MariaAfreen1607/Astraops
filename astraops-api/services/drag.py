"""Deterministic drag-decay estimation from space weather inputs.

Granite explains these numbers; it does not produce them. Every value here is
computed from published relations with stated assumptions, so the brief can
cite figures without inventing them.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

AU_KM = 1.496e8
MU = 3.986e14
R_EARTH_M = 6.371e6

BASE_DENSITY = {210: 2.5e-10, 400: 2.8e-12, 550: 5.0e-13}

CD = 2.2
AREA_TO_MASS = 0.01


def _transit_hours(speed_km_s: float) -> float:
    return AU_KM / speed_km_s / 3600.0


def _forecast_kp(speed_km_s: float) -> float:
    if speed_km_s >= 1200:
        return 7.0
    if speed_km_s >= 900:
        return 6.0
    if speed_km_s >= 700:
        return 5.0
    if speed_km_s >= 500:
        return 4.0
    return 3.0


def _density_multiplier(kp: float) -> float:
    return 1.0 + 0.10 * kp


def _decay_m_per_day(alt_km: int, multiplier: float) -> float:
    a_m = R_EARTH_M + alt_km * 1000.0
    rho = BASE_DENSITY[alt_km] * multiplier
    da_per_rev = 2 * math.pi * (CD * AREA_TO_MASS) * rho * a_m**2
    period_s = 2 * math.pi * math.sqrt(a_m**3 / MU)
    revs_per_day = 86400.0 / period_s
    return da_per_rev * revs_per_day


def estimate_drag(cmes, storms) -> dict | None:
    fastest = None
    for c in cmes:
        if c.speed_km_s and (fastest is None or c.speed_km_s > fastest.speed_km_s):
            fastest = c

    observed_kp = None
    for s in storms:
        if s.kp_index_max and (observed_kp is None or s.kp_index_max > observed_kp):
            observed_kp = s.kp_index_max

    if fastest is None and observed_kp is None:
        return None

    if observed_kp is not None:
        kp, basis = observed_kp, "observed"
    else:
        kp, basis = _forecast_kp(fastest.speed_km_s), "forecast from CME speed"

    multiplier = _density_multiplier(kp)

    result = {
        "kp": round(kp, 1),
        "kp_basis": basis,
        "density_increase_pct": round((multiplier - 1) * 100),
        "decay_72h_m": {
            alt: round(_decay_m_per_day(alt, multiplier) * 3.0) for alt in BASE_DENSITY
        },
        "quiet_decay_72h_m": {
            alt: round(_decay_m_per_day(alt, 1.0) * 3.0) for alt in BASE_DENSITY
        },
    }

    if fastest is not None and fastest.start_time is not None:
        hours = _transit_hours(fastest.speed_km_s)
        arrival = fastest.start_time + timedelta(hours=hours)
        remaining = (arrival - datetime.now(timezone.utc)).total_seconds() / 3600.0
        result["fastest_cme_km_s"] = round(fastest.speed_km_s)
        result["transit_hours"] = round(hours)
        result["arrival_utc"] = arrival.strftime("%Y-%m-%d %H:%M UTC")
        result["hours_until_arrival"] = round(remaining)

    return result


def format_for_prompt(est: dict) -> str:
    lines = ["COMPUTED (deterministic figures, cite these directly):"]
    if "fastest_cme_km_s" in est:
        h = est["hours_until_arrival"]
        if h >= 0:
            when = f"arrives in {h}h"
        else:
            when = f"ALREADY ARRIVED {abs(h)}h ago; effects are in progress now"
        lines.append(
            f"Fastest CME {est['fastest_cme_km_s']} km/s; Sun-Earth transit "
            f"{est['transit_hours']}h; arrival {est['arrival_utc']} ({when})"
        )
    lines.append(f"Kp {est['kp']} ({est['kp_basis']})")
    lines.append(f"Thermospheric density increase {est['density_increase_pct']}%")
    for alt in sorted(est["decay_72h_m"]):
        loss = est["decay_72h_m"][alt]
        base = est["quiet_decay_72h_m"][alt]
        if loss > 5000:
            lines.append(
                f"At {alt}km (VLEO band) the 72h loss is {round(loss/1000)} km against a "
                f"{round(base/1000)} km quiet baseline. Decay accelerates as altitude "
                f"drops, so treat this as 'orbit not sustainable, reentry in days', "
                f"not a precise figure."
            )
        else:
            lines.append(
                f"Altitude loss over 72h at {alt}km (LEO band): {loss} m "
                f"(quiet baseline {base} m), 3U CubeSat, Cd 2.2, A/m 0.01 m^2/kg"
            )
    return "\n".join(lines)
