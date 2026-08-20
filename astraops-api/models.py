from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Satellites
# ---------------------------------------------------------------------------

class TLERecord(BaseModel):
    name: str = Field(..., description="Satellite common name")
    norad_cat_id: str = Field(..., description="NORAD catalog number")
    epoch: str = Field(..., description="TLE epoch string")
    line1: str = Field(..., description="TLE line 1")
    line2: str = Field(..., description="TLE line 2")
    mean_motion: Optional[float] = Field(None, description="Revolutions per day")
    eccentricity: Optional[float] = None
    inclination_deg: Optional[float] = None
    altitude_km: Optional[float] = Field(None, description="Approximate altitude in km")


class SatelliteListResponse(BaseModel):
    count: int
    fetched_at: datetime
    source: str = "CelesTrak"
    satellites: list[TLERecord]


class SatelliteDetailResponse(BaseModel):
    fetched_at: datetime
    source: str = "CelesTrak"
    satellite: TLERecord


# ---------------------------------------------------------------------------
# Conjunctions
# ---------------------------------------------------------------------------

class ConjunctionEvent(BaseModel):
    sat1_norad: str
    sat1_name: str
    sat2_norad: str
    sat2_name: str
    tca: datetime = Field(..., description="Time of Closest Approach (UTC)")
    min_range_km: float = Field(..., description="Minimum separation in km")
    relative_velocity_km_s: Optional[float] = None
    probability_of_collision: Optional[float] = None
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH")


class ConjunctionScreenResponse(BaseModel):
    screened_at: datetime
    total_pairs_screened: int
    threshold_km: float
    events: list[ConjunctionEvent]


# ---------------------------------------------------------------------------
# Space Weather
# ---------------------------------------------------------------------------

class SolarFlare(BaseModel):
    flare_id: str
    begin_time: Optional[datetime] = None
    peak_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    class_type: Optional[str] = Field(None, description="e.g. X1.5, M3.2")
    source_location: Optional[str] = None
    active_region: Optional[str] = None
    link: Optional[str] = None


class CMEEvent(BaseModel):
    activity_id: str
    start_time: Optional[datetime] = None
    source_location: Optional[str] = None
    note: Optional[str] = None
    speed_km_s: Optional[float] = None
    type: Optional[str] = None
    link: Optional[str] = None


class GeomagneticStorm(BaseModel):
    gst_id: str
    start_time: Optional[datetime] = None
    kp_index_max: Optional[float] = None
    link: Optional[str] = None


class SpaceWeatherResponse(BaseModel):
    fetched_at: datetime
    start_date: str
    end_date: str
    solar_flares: list[SolarFlare]
    cmes: list[CMEEvent]
    geomagnetic_storms: list[GeomagneticStorm]


# ---------------------------------------------------------------------------
# Research / RAG
# ---------------------------------------------------------------------------

class ResearchQuery(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    context_filter: Optional[str] = Field(
        None,
        description="Optional domain filter: 'satellites' | 'spaceweather' | 'missions'",
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of context chunks to retrieve")


class ResearchSource(BaseModel):
    document_id: str
    title: str
    excerpt: str
    score: float = Field(..., ge=0.0, le=1.0)


class ResearchAnswer(BaseModel):
    model_config = {"protected_namespaces": ()}

    question: str
    answer: str
    sources: list[ResearchSource]
    model_used: str
    answered_at: datetime


# ---------------------------------------------------------------------------
# Shared / Error
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    error: str
    detail: Optional[str] = None
    fallback_used: bool = False
