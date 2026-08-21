# AstraOps — Build Status

## What this is
Mission intelligence platform for the IBM AI Builders August Challenge (Advance Space
Exploration with AI). Deadline Aug 31, 11:59 PM ET.

Thesis: the data exists, the warnings don't. Public feeds (CelesTrak, NASA DONKI) are
published raw; nobody translates them into operator-facing decisions. Fang et al. 2022
(Space Weather) documents exactly this gap — NOAA issues no drag-focused alerts for
satellite operators. AstraOps builds the missing translation layer.

Architecture is three layers: ingest (real feeds) → compute (deterministic physics:
SGP4, NOAA scales) → interpret (Granite writes the brief). The LLM never does arithmetic.

## Done
- FastAPI backend, `astraops-api/` — scaffolded by IBM Bob (one prompt, 17 files)
- Fixed Bob's hallucinated CelesTrak URL (was /gp.php, correct is /NORAD/elements/gp.php)
- Replaced Bob's altitude-difference approximation with real SGP4 conjunction screening:
  pairwise propagation, 1-second TCA refinement, closed-form Pc, docked-pair filter
- NASA DONKI space weather with real API key
- Granite (ibm/granite-4-h-small) on watsonx — space weather + conjunction briefs
- Next.js frontend, `astraops-web/` — dashboard, conjunction watch, space weather, research stub

## Remaining
- RAG research pipeline (research.py is still Bob's placeholder) — assign to Bob
- pytest suite — assign to Bob (Prompt 6)
- README + architecture diagram — assign to Bob (Prompt 7), run last
- docs/RESEARCH.md — cited problem statement (sources gathered, not yet written)
- IBM SkillsBuild learning activity — REQUIRED for eligibility, every team member
- Push to GitHub (currently local-only), demo video

## Gotchas
- watsonx trial ends Sep 19; Bob budget was 0.96/40 used as of Aug 20
- `.env` overrides `config.py` — change both when editing config
- Run backend: `cd astraops-api && .venv/bin/uvicorn main:app --reload --port 8000`
- Run frontend: `cd astraops-web && npm run dev`
- granite-3-3-8b-instruct is NOT available in this region; use granite-4-h-small
