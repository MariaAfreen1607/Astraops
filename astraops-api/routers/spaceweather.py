"""Space weather router — /spaceweather"""

from __future__ import annotations

from fastapi import APIRouter, Query

from models import SpaceWeatherResponse
from services.spaceweather import fetch_space_weather

router = APIRouter(prefix="/spaceweather", tags=["Space Weather"])


@router.get(
    "",
    response_model=SpaceWeatherResponse,
    summary="Fetch solar flares, CMEs, and geomagnetic storms",
    description=(
        "Proxies the NASA DONKI API to return solar flare, CME, and geomagnetic storm "
        "events for the requested look-back window. Results are cached for 15 minutes."
    ),
)
async def get_space_weather(
    days: int = Query(
        7, ge=1, le=30, description="Number of look-back days (1–30)"
    ),
) -> SpaceWeatherResponse:
    return await fetch_space_weather(days=days)


@router.get(
    "/flares",
    response_model=SpaceWeatherResponse,
    summary="Fetch solar flare events only (convenience alias)",
)
async def get_flares(
    days: int = Query(7, ge=1, le=30),
) -> SpaceWeatherResponse:
    result = await fetch_space_weather(days=days)
    return result.model_copy(update={"cmes": [], "geomagnetic_storms": []})


@router.get(
    "/cmes",
    response_model=SpaceWeatherResponse,
    summary="Fetch CME events only (convenience alias)",
)
async def get_cmes(
    days: int = Query(7, ge=1, le=30),
) -> SpaceWeatherResponse:
    result = await fetch_space_weather(days=days)
    return result.model_copy(update={"solar_flares": [], "geomagnetic_storms": []})


@router.get(
    "/storms",
    response_model=SpaceWeatherResponse,
    summary="Fetch geomagnetic storm events only (convenience alias)",
)
async def get_storms(
    days: int = Query(7, ge=1, le=30),
) -> SpaceWeatherResponse:
    result = await fetch_space_weather(days=days)
    return result.model_copy(update={"solar_flares": [], "cmes": []})
