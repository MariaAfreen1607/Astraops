"""Conjunctions router — /conjunctions"""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from models import ConjunctionScreenResponse
from services.conjunctions import screen_conjunctions

router = APIRouter(prefix="/conjunctions", tags=["Conjunctions"])


@router.get(
    "",
    response_model=ConjunctionScreenResponse,
    summary="Screen satellite pairs for close approaches",
    description=(
        "Screens the given CelesTrak satellite group for pairs with estimated "
        "separation below *threshold_km*. Results are cached for 30 minutes. "
        "**Note:** The current separation model uses altitude difference as a proxy; "
        "connect an SGP4 propagator for production-grade screening."
    ),
)
async def screen(
    group: str = Query("active", description="CelesTrak group to screen"),
    threshold_km: float = Query(
        10.0, ge=0.1, le=500.0, description="Maximum separation to flag (km)"
    ),
    max_pairs: int = Query(
        500, ge=10, le=2000, description="Cap on number of satellites considered"
    ),
) -> ConjunctionScreenResponse:
    return await screen_conjunctions(
        group=group,
        threshold_km=threshold_km,
        max_pairs=max_pairs,
    )


@router.get("/profile", summary="Separation-vs-time curve for a satellite pair")
async def conjunction_profile(
    norad_a: str,
    norad_b: str,
    group: str = "starlink",
    window_minutes: int = 180,
    step_seconds: int = 10,
    start_at: datetime | None = None,
):
    from services.conjunctions import separation_profile
    result = await separation_profile(
        norad_a, norad_b, group, window_minutes, step_seconds, start_at
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
