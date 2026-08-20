"""Satellites router — /satellites"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models import ErrorDetail, SatelliteDetailResponse, SatelliteListResponse
from services.satellites import fetch_satellite_by_norad, fetch_satellites

router = APIRouter(prefix="/satellites", tags=["Satellites"])

_ALLOWED_GROUPS = {
    "active", "stations", "visual", "weather", "noaa", "goes",
    "resource", "sarsat", "dmc", "tdrss", "argos", "geo",
    "intelsat", "ses", "iridium", "iridium-NEXT", "starlink",
    "oneweb", "orbcomm", "globalstar", "amateur", "x-comm",
    "other-comm", "satnogs", "gps-ops", "glo-ops", "galileo",
    "beidou", "sbas", "nnss", "radar",
}


@router.get(
    "",
    response_model=SatelliteListResponse,
    responses={502: {"model": ErrorDetail}},
    summary="List satellites by group",
    description=(
        "Fetches TLE data for a named CelesTrak satellite group. "
        "Results are cached for 1 hour."
    ),
)
async def list_satellites(
    group: str = Query(
        "active",
        description="CelesTrak group name (e.g. 'active', 'starlink', 'stations')",
    ),
) -> SatelliteListResponse:
    if group not in _ALLOWED_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown group '{group}'. Allowed: {sorted(_ALLOWED_GROUPS)}",
        )
    result = await fetch_satellites(group)
    if not result.satellites:
        raise HTTPException(
            status_code=502,
            detail=f"No TLE data returned for group '{group}'. CelesTrak may be unavailable.",
        )
    return result


@router.get(
    "/{norad_id}",
    response_model=SatelliteDetailResponse,
    responses={404: {"model": ErrorDetail}, 502: {"model": ErrorDetail}},
    summary="Get satellite by NORAD catalog ID",
)
async def get_satellite(norad_id: str) -> SatelliteDetailResponse:
    if not norad_id.isdigit():
        raise HTTPException(status_code=400, detail="NORAD ID must be a numeric string.")
    result = await fetch_satellite_by_norad(norad_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Satellite with NORAD ID '{norad_id}' not found or CelesTrak unavailable.",
        )
    return result
