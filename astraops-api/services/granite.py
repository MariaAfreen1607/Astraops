"""Granite reasoning layer — turns computed space data into operator-facing briefs.

Deterministic math happens upstream (SGP4, NOAA scales). Granite is used only
where natural language is the right output: explanation, impact translation,
and recommended action.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL_ID = "ibm/granite-4-h-small"

SPACE_WEATHER_SYSTEM = """You are a space weather operations analyst.
You translate raw NOAA/NASA event data into operational impact for satellite operators.

Critical context: NOAA's G-scale was calibrated for ground effects (power grids, HF radio),
not for orbital drag. A G1 storm destroyed 38 Starlink satellites in February 2022 because
thermospheric density rose ~50% at 210 km. Never equate a low G-number with low orbital risk.

Write a brief with exactly these sections:
IMPACT: one line per affected orbit regime (VLEO <300km, LEO 300-2000km, MEO, GEO)
SUBSYSTEMS: which are affected (drag, radiation/SEU, comms, GPS accuracy)
ACTION: concrete recommended steps for an operator in the next 24-72 hours
CONFIDENCE: high/medium/low with one clause of justification

Rules you must not break:
- Use only numbers present in the input. Where a COMPUTED block appears, those figures
  are authoritative and you must cite them explicitly: arrival time, density increase,
  and the altitude loss for each band. Any figure NOT in the input (GPS error magnitudes,
  fuel cost) must be described in words, never invented.
- Open the brief with a single ARRIVAL line stating when the disturbance reaches Earth and
  how many hours remain, taken from the COMPUTED block. If no CME arrival is given, say the
  disturbance is already in progress.
- Then lead IMPACT with how much altitude is lost in each band.
- For bands with no meaningful effect, write "no significant drag effect at this altitude"
  rather than "no data". Reserve "no data" for cases where the input is genuinely silent.
- Distinguish observed from forecast. The COMPUTED block labels Kp as either "observed" or
  "forecast from CME speed". A forecast Kp, and the density increase derived from it, must
  never be described as observed or measured. If the basis is forecast, CONFIDENCE cannot
  be high — use medium and say the storm level is inferred from CME speed, not measured.
- Assign each altitude to exactly one band. VLEO is below 300 km, LEO is 300-2000 km.
  A satellite at 210 km is VLEO and must not appear under LEO.
- Recommend only actions that physically address the effect. Drag is countered by
  raising altitude, reducing cross-section, or expending propellant. It is not
  countered by power, and you must never suggest that it is.
- Do not assign a G-rating unless a geomagnetic storm with a Kp value appears in the
  input. If none is listed, say no storm has been recorded and treat CME speeds as an
  indication of what may arrive, not as an observed storm level.
- If the data does not support a claim, omit the claim.

Under 200 words total."""

CONJUNCTION_SYSTEM = """You are a conjunction assessment analyst.
You receive the output of an SGP4 screening run and explain it to a satellite operator.

Interpret relative velocity correctly. LOW relative velocity (under ~2 km/s) means the objects
are near-co-planar and drifting slowly past each other — lower energy, lower consequence, and the
geometry is more predictable. HIGH relative velocity (over ~7 km/s) means a crossing encounter:
higher kinetic energy, shorter warning, and greater sensitivity to covariance error. Never describe
high relative velocity as reducing severity.

Relative velocity determines severity as much as miss distance: a sub-km approach at
0.3 km/s between co-planar satellites is a formation-keeping matter, while 15 km at
11 km/s is a high-energy crossing encounter with far greater consequence if the
covariance is underestimated.

Write:
ASSESSMENT: what this event is, in plain language
SEVERITY: your read, and why velocity/geometry supports it
ACTION: what the operator should do and by when
CAVEAT: state that Pc assumes isotropic 200m covariance and a 20m hard-body radius;
these are screening defaults, not operator-supplied covariances.

Under 180 words. Do not invent data."""


POSTURE_SYSTEM = """You are the duty officer writing the top-line status for a mission
operations dashboard. You receive the current tracked-object count, the closest screened
approach, and the strongest recent solar activity.

Output exactly two lines and nothing else:
Line 1: a single status word — NOMINAL, ELEVATED, or ACTION REQUIRED
Line 2: one sentence, under 30 words, citing the specific numbers that justify it.

Choose the status from the data:
- ACTION REQUIRED only if a conjunction is under 5 km, or a storm is observed with Kp>=6.
- ELEVATED if a conjunction is under 25 km at over 7 km/s, or M/X class flares are present,
  or a fast CME is inbound.
- NOMINAL otherwise.

Never invent figures. Never add headings, bullets, or extra commentary."""


@lru_cache(maxsize=1)
def _get_llm():
    """Lazily construct the Granite chat model; None if credentials are absent."""
    api_key = os.getenv("WATSONX_APIKEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        logger.warning("watsonx credentials missing; Granite features disabled")
        return None

    try:
        from langchain_ibm import ChatWatsonx
    except ImportError:
        logger.error("langchain-ibm not installed")
        return None

    try:
        return ChatWatsonx(
            model_id=MODEL_ID,
            url=url,
            apikey=api_key,
            project_id=project_id,
            params={"temperature": 0.2, "max_new_tokens": 500},
        )
    except Exception as exc:
        logger.error("Failed to initialise Granite: %s", exc)
        return None


def _invoke(system: str, user: str, attempts: int = 3) -> str:
    """Call Granite, retrying transient failures.

    The watsonx trial plan caps concurrent requests per model, so a burst of
    clicks returns 429. That is transient and worth waiting out; a bad request
    or bad credentials is not, and fails immediately.
    """
    import time

    llm = _get_llm()
    if llm is None:
        return "AI briefing unavailable — watsonx credentials are not configured."

    from langchain_core.messages import HumanMessage, SystemMessage
    msgs = [SystemMessage(content=system), HumanMessage(content=user)]

    for attempt in range(attempts):
        try:
            return llm.invoke(msgs).content.strip()
        except Exception as exc:
            text = str(exc)
            transient = "429" in text or "consumption_limit" in text or "timeout" in text.lower()
            if transient and attempt < attempts - 1:
                wait = 2 ** attempt
                logger.warning("Granite busy (attempt %d/%d); retrying in %ds", attempt + 1, attempts, wait)
                time.sleep(wait)
                continue
            logger.error("Granite invocation failed: %s", exc)
            if transient:
                return ("The watsonx free tier is at its concurrent-request limit right now. "
                        "Wait a few seconds and generate the brief again.")
            return "AI briefing unavailable — the model could not be reached."


def brief_space_weather(flares, cmes, storms) -> str:
    """Generate an operational impact brief from DONKI event data."""
    lines = []
    for f in flares[:8]:
        lines.append(f"FLARE {f.class_type or '?'} peak={f.peak_time} region={f.active_region or '?'}")
    for c in cmes[:8]:
        lines.append(f"CME speed={c.speed_km_s or '?'}km/s start={c.start_time} src={c.source_location or '?'}")
    for s in storms[:8]:
        lines.append(f"GEOMAGNETIC_STORM kp_max={s.kp_index_max or '?'} start={s.start_time}")

    if not lines:
        return "No significant space weather events in the requested window."

    from services.drag import estimate_drag, format_for_prompt
    payload = "Events:\n" + "\n".join(lines)
    est = estimate_drag(cmes, storms)
    if est:
        payload += "\n\n" + format_for_prompt(est)

    return _invoke(SPACE_WEATHER_SYSTEM, payload)


def brief_conjunction(event) -> str:
    """Generate a risk brief for a single screened conjunction event."""
    payload = (
        f"Primary: {event.sat1_name} (NORAD {event.sat1_norad})\n"
        f"Secondary: {event.sat2_name} (NORAD {event.sat2_norad})\n"
        f"TCA: {event.tca}\n"
        f"Miss distance: {event.min_range_km} km\n"
        f"Relative velocity: {event.relative_velocity_km_s} km/s\n"
        f"Screening Pc: {event.probability_of_collision}\n"
        f"Risk band: {event.risk_level}"
    )
    return _invoke(CONJUNCTION_SYSTEM, payload)


def brief_posture(sat_count, top_event, flares, cmes, storms) -> str:
    """One-line operational posture synthesising the dashboard's three feeds."""
    lines = [f"Tracked objects: {sat_count}"]

    if top_event is not None:
        lines.append(
            f"Closest approach: {top_event.sat1_name} / {top_event.sat2_name} at "
            f"{top_event.min_range_km} km, relative velocity "
            f"{top_event.relative_velocity_km_s} km/s, TCA {top_event.tca}"
        )
    else:
        lines.append("Closest approach: none below screening threshold")

    strongest = None
    for f in flares:
        if f.class_type and (strongest is None or f.class_type > strongest):
            strongest = f.class_type
    lines.append(f"Strongest flare in window: {strongest or 'none'}")

    fastest = None
    for c in cmes:
        if c.speed_km_s and (fastest is None or c.speed_km_s > fastest):
            fastest = c.speed_km_s
    lines.append(f"Fastest CME: {str(round(fastest)) + ' km/s' if fastest else 'none'}")

    kp = None
    for st in storms:
        if st.kp_index_max and (kp is None or st.kp_index_max > kp):
            kp = st.kp_index_max
    lines.append(f"Observed geomagnetic storm Kp: {kp if kp else 'none recorded'}")

    return _invoke(POSTURE_SYSTEM, "\n".join(lines))
