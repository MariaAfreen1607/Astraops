# AstraOps API

A **FastAPI** backend for the AstraOps space mission intelligence platform.

## Features

| Router | Path | Description |
|---|---|---|
| Satellites | `/satellites` | Fetches & caches TLE data from CelesTrak GP API |
| Conjunctions | `/conjunctions` | Screens satellite pairs for close approaches |
| Space Weather | `/spaceweather` | Proxies NASA DONKI for solar flares, CMEs, geomagnetic storms |
| Research | `/research` | Placeholder RAG Q&A endpoint |

---

## Project structure

```
astraops-api/
├── main.py               # FastAPI app factory, CORS, routers, health endpoints
├── config.py             # pydantic-settings Settings + get_settings()
├── models.py             # Pydantic response/request models
├── cache.py              # Thread-safe in-memory TTL cache
├── routers/
│   ├── satellites.py
│   ├── conjunctions.py
│   ├── spaceweather.py
│   └── research.py
├── services/
│   ├── satellites.py     # CelesTrak TLE fetch + parse
│   ├── conjunctions.py   # Altitude-difference screening (swap in SGP4)
│   ├── spaceweather.py   # NASA DONKI proxy
│   └── research.py       # RAG placeholder
├── requirements.txt
└── .env.example
```

---

## Quick start

```bash
cd astraops-api

# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set NASA_API_KEY at minimum

# 4. Run the development server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `false` | Enable debug logging |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON array) |
| `CELESTRAK_GP_URL` | CelesTrak GP endpoint | TLE data source |
| `NASA_API_KEY` | `DEMO_KEY` | NASA API key (rate-limited without one) |
| `NASA_DONKI_BASE_URL` | NASA DONKI WS | Space weather source |
| `TLE_CACHE_TTL` | `3600` | TLE cache lifetime in seconds |
| `SPACEWEATHER_CACHE_TTL` | `900` | Space weather cache lifetime |
| `CONJUNCTION_CACHE_TTL` | `1800` | Conjunction cache lifetime |
| `HTTP_TIMEOUT` | `30.0` | External HTTP request timeout |

---

## API endpoints

### Satellites
- `GET /satellites?group=active` — list all satellites in a group
- `GET /satellites/{norad_id}` — fetch single satellite by NORAD ID

### Conjunctions
- `GET /conjunctions?group=active&threshold_km=10.0&max_pairs=500`

### Space Weather
- `GET /spaceweather?days=7` — all events
- `GET /spaceweather/flares?days=7`
- `GET /spaceweather/cmes?days=7`
- `GET /spaceweather/storms?days=7`

### Research
- `POST /research/ask` — body: `{"question": "...", "top_k": 5}`

### Meta
- `GET /` — root info
- `GET /health` — health check + cache stats
- `DELETE /cache` — flush in-memory cache

---

## Extending the RAG pipeline

Open [`services/research.py`](services/research.py) and replace the body of `answer_question` with:

1. Embed `query.question` using an embedding model
2. Query a vector store (Pinecone, pgvector, Chroma, etc.)
3. Build a prompt with retrieved chunks and call an LLM
4. Return a populated `ResearchAnswer`

## Upgrading conjunction screening

Open [`services/conjunctions.py`](services/conjunctions.py) and replace `_estimate_separation_km`
with an SGP4 propagator (e.g. `python-sgp4`) that propagates both TLEs over a time window and
finds the true minimum range.
