"""AI briefing endpoints — Granite reasoning over computed space data."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.conjunctions import screen_conjunctions
from services.granite import MODEL_ID, brief_conjunction, brief_posture, brief_space_weather
from services.spaceweather import fetch_space_weather

router = APIRouter(prefix="/briefs", tags=["AI Briefs"])


class Brief(BaseModel):
    model_config = {"protected_namespaces": ()}
    generated_at: datetime
    model_used: str
    subject: str
    brief: str
    computed: dict | None = None


@router.get("/spaceweather", response_model=Brief, summary="AI operational impact brief for current space weather")
async def spaceweather_brief(days: int = Query(7, ge=1, le=30)):
    sw = await fetch_space_weather(days=days)
    text = brief_space_weather(sw.solar_flares, sw.cmes, sw.geomagnetic_storms)
    from services.drag import estimate_drag
    return Brief(
        generated_at=datetime.now(timezone.utc),
        model_used=MODEL_ID,
        subject=f"Space weather impact assessment, last {days} days",
        brief=text,
        computed=estimate_drag(sw.cmes, sw.geomagnetic_storms),
    )


@router.get("/conjunction", response_model=Brief, summary="AI risk brief for the highest-risk screened conjunction")
async def conjunction_brief(
    group: str = Query("starlink"),
    threshold_km: float = Query(20.0, gt=0, le=500),
):
    result = await screen_conjunctions(group=group, threshold_km=threshold_km)
    if not result.events:
        raise HTTPException(404, f"No conjunctions below {threshold_km} km found for group '{group}'.")
    top = result.events[0]
    return Brief(
        generated_at=datetime.now(timezone.utc),
        model_used=MODEL_ID,
        subject=f"{top.sat1_name} / {top.sat2_name} — {top.min_range_km} km at {top.tca}",
        brief=brief_conjunction(top),
    )


@router.get("/posture", response_model=Brief, summary="One-line operational posture for the dashboard")
async def posture_brief(group: str = Query("stations")):
    from services.satellites import fetch_satellites

    sats = await fetch_satellites(group=group)
    sw = await fetch_space_weather(days=7)
    screen = await screen_conjunctions(group=group, threshold_km=500.0)
    top = screen.events[0] if screen.events else None

    return Brief(
        generated_at=datetime.now(timezone.utc),
        model_used=MODEL_ID,
        subject="Current operational posture",
        brief=brief_posture(
            len(sats.satellites), top, sw.solar_flares, sw.cmes, sw.geomagnetic_storms
        ),
    )
