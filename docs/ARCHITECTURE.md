# AstraOps — Architecture Reference

This document describes every module in `astraops-api` and every page and component in `astraops-web`. Each description is grounded in the actual source; nothing here describes a feature that does not exist in the code.

---

## `astraops-api` — FastAPI backend

### Entry point and infrastructure

**[`main.py`](../astraops-api/main.py)**
The application factory. `create_app()` constructs the FastAPI instance, attaches `CORSMiddleware` with origins drawn from `settings.cors_origins`, registers a global exception handler that returns a structured JSON error body instead of a raw traceback, and mounts all five routers. A lifespan context manager logs startup and clears the in-memory cache on shutdown. The module-level `load_dotenv()` call ensures `.env` is read before any import of `config.py` resolves settings.

**[`config.py`](../astraops-api/config.py)**
A `pydantic-settings` `BaseSettings` subclass that reads from environment variables and `.env`. Fields cover the application name and version, the CORS allowed-origins list, the CelesTrak GP endpoint URL, NASA DONKI base URL and API key, Watsonx credentials and regional endpoint, RAG directory paths, per-service cache TTLs, and the HTTP client timeout. `get_settings()` is decorated with `@lru_cache` so the settings object is constructed once per process.

**[`models.py`](../astraops-api/models.py)**
All Pydantic request and response models, grouped by domain: `TLERecord`, `SatelliteListResponse`, `SatelliteDetailResponse` for satellites; `ConjunctionEvent`, `ConjunctionScreenResponse` for conjunction screening; `SolarFlare`, `CMEEvent`, `GeomagneticStorm`, `SpaceWeatherResponse` for space weather; `ResearchQuery`, `ResearchSource`, `ResearchAnswer` for the RAG endpoint; and `ErrorDetail` for structured error responses. No business logic lives here.

**[`cache.py`](../astraops-api/cache.py)**
`TTLCache` is a thread-safe in-memory key/value store with per-entry expiry, backed by a `threading.Lock`. `get()` evicts expired entries on access; `set()` writes a `(value, expires_at)` tuple where `expires_at` is a `time.monotonic()` offset. A module-level singleton `cache` is shared across the application. On process exit, `atexit` calls `_persist()`, which serialises all live Pydantic model entries to `.cache_state.json` as JSON so that a cold start after a host sleep can reload the last known-good data instead of making fresh upstream requests.

---

### Routers

**[`routers/satellites.py`](../astraops-api/routers/satellites.py)**
Mounts under `/satellites`. `GET /satellites` accepts a `group` query parameter, validates it against a hard-coded allowlist of CelesTrak group names, delegates to `fetch_satellites`, and returns a 502 if no records come back. `GET /satellites/{norad_id}` fetches a single satellite by NORAD catalog number. `GET /satellites/positions` calls `current_positions` and returns geodetic lat/lon/altitude for up to `limit` objects, used by the globe component.

**[`routers/conjunctions.py`](../astraops-api/routers/conjunctions.py)**
Mounts under `/conjunctions`. `GET /conjunctions` accepts `group`, `threshold_km`, and `max_pairs` and delegates to `screen_conjunctions`. `GET /conjunctions/profile` accepts two NORAD IDs and returns a time-series of separation values and relative velocities across a configurable window, which the frontend plots as a separation-vs-time chart.

**[`routers/spaceweather.py`](../astraops-api/routers/spaceweather.py)**
Mounts under `/spaceweather`. `GET /spaceweather` returns all three event types for a configurable look-back window. Three convenience aliases — `/spaceweather/flares`, `/spaceweather/cmes`, `/spaceweather/storms` — return the same response model with the other two lists zeroed out, so the frontend can request only what it needs.

**[`routers/briefs.py`](../astraops-api/routers/briefs.py)**
Mounts under `/briefs`. `GET /briefs/spaceweather` fetches the current space weather data and passes flares, CMEs, and storms to `brief_space_weather`. `GET /briefs/conjunction` screens the requested group, takes the closest event (index 0, since results are sorted by miss distance), and passes it to `brief_conjunction`. Both endpoints return a `Brief` model with `generated_at`, `model_used`, `subject`, and `brief` fields.

**[`routers/research.py`](../astraops-api/routers/research.py)**
Mounts under `/research`. `POST /research/ask` accepts a `ResearchQuery` body (question, optional context filter, top-k count) and delegates to `answer_question`. Returns a `ResearchAnswer` with the generated text, the list of retrieved source passages with similarity scores, the model name, and a timestamp.

---

### Services

**[`services/satellites.py`](../astraops-api/services/satellites.py)**
Three public functions. `fetch_satellites(group)` requests TLE data from the CelesTrak GP API (`FORMAT=tle`), detects the plain-text "has not updated since your last successful retrieval" notice (returning the stale cache instead of an empty list), parses the 3-line TLE format into `TLERecord` objects, and caches the result for `tle_cache_ttl` seconds plus a 24-hour stale fallback. `fetch_satellite_by_norad(norad_id)` does the same for a single object via `CATNR`. `current_positions(group, limit)` propagates each TLE to the current epoch using `sgp4.api.Satrec`, rotates the resulting TEME vector through Greenwich Mean Sidereal Time to ECEF, and converts to geodetic latitude, longitude, and altitude on a spherical Earth (R = 6 371 km).

**[`services/conjunctions.py`](../astraops-api/services/conjunctions.py)**
Implements real SGP4 pairwise conjunction screening. After fetching TLEs via `fetch_satellites`, it parses each into a `Satrec` object and bails with an empty-events response if fewer than two valid records are available. It builds a Julian-date time grid across `window_minutes` at `step_seconds` resolution and calls `SatrecArray.sgp4` (vectorised NumPy) to propagate all satellites at once. For each time step it computes the full pairwise distance matrix with `np.einsum`, tracking the running minimum and the step index at which it occurs. Pairs whose coarse minimum lies within `threshold_km` are re-propagated at one-second resolution by `_refine()` to find the precise TCA, miss distance, and relative velocity. Pairs whose minimum is below `DOCKED_FLOOR_KM` (50 m) are discarded as co-located objects. Collision probability is computed by `_collision_probability()` using a closed-form isotropic-covariance formula. Results are sorted by miss distance and cached.

**[`services/spaceweather.py`](../astraops-api/services/spaceweather.py)**
`fetch_space_weather(days)` computes start and end dates, calls `_donki_get` once each for the `FLR`, `CME`, and `GST` endpoints, and assembles a `SpaceWeatherResponse`. `_donki_get` handles `TimeoutException`, `HTTPStatusError`, and unexpected exceptions by logging and returning an empty list, so a partial upstream failure degrades gracefully. Results are cached for `spaceweather_cache_ttl` seconds. `_safe_datetime` tries two DONKI timestamp formats and falls back to `None` rather than raising on unparseable strings.

**[`services/granite.py`](../astraops-api/services/granite.py)**
The Granite reasoning layer. `_get_llm()` is `@lru_cache`-wrapped and returns `None` if Watsonx credentials are absent, disabling AI features gracefully. `_invoke(system, user)` sends a `[SystemMessage, HumanMessage]` pair to Granite 4 and retries up to three times with exponential back-off on transient errors (HTTP 429, consumption limit, timeout), returning a human-readable fallback string on permanent failure. `brief_space_weather(flares, cmes, storms)` formats up to eight events per type into a compact text payload and calls `_invoke` with `SPACE_WEATHER_SYSTEM`, a 200-word prompt that enforces orbit-regime separation (VLEO / LEO / MEO / GEO), prohibits invented figures, and requires IMPACT / SUBSYSTEMS / ACTION / CONFIDENCE sections. `brief_conjunction(event)` formats a single `ConjunctionEvent` and calls `_invoke` with `CONJUNCTION_SYSTEM`, a 180-word prompt that explains relative-velocity semantics and requires ASSESSMENT / SEVERITY / ACTION / CAVEAT sections.

**[`services/research.py`](../astraops-api/services/research.py)**
The RAG pipeline. `_load_corpus()` walks `CORPUS_DIR`, dispatches `PyPDFLoader` for `.pdf` files and `TextLoader` for `.txt` files, and splits every document into 800-character chunks with 100-character overlap using `RecursiveCharacterTextSplitter`. Each chunk is stamped with a stable `doc_id` (MD5 of path + chunk index), a human-readable `title` derived from the filename, and a `chunk_index`. `_get_vectorstore()` is `@lru_cache`-wrapped; on first call it opens the persistent ChromaDB collection at `CHROMA_DIR`, checks whether it is empty, and if so calls `_load_corpus` and indexes the documents. `answer_question(query)` checks for credentials, initialises the vector store via `asyncio.to_thread`, calls `similarity_search_with_score`, converts raw L2 distances to `[0, 1]` similarity scores, builds a structured prompt with numbered context passages, and invokes `ChatWatsonx`. Five distinct error states each return a populated `ResearchAnswer` rather than raising an exception.

---

## `astraops-web` — Next.js frontend

### Pages

**[`app/layout.tsx`](../astraops-web/app/layout.tsx)**
The root layout rendered around every page. Loads IBM Plex Sans, IBM Plex Sans Condensed, and IBM Plex Mono from Google Fonts. Renders `StatusStrip` across the full top of the viewport and a two-column shell below it: a fixed-width `<aside>` on the left containing the wordmark and `NavRail`, and a `<main>` that takes the remaining width. On narrow viewports the sidebar collapses to a horizontal strip above the content area.

**[`app/page.tsx`](../astraops-web/app/page.tsx)** — Mission Dashboard
The default route. On mount, three parallel API calls fetch the `stations` TLE group, the current space weather (7-day window), and conjunctions for the stations group within 500 km. Three summary cards show live object count, close-approach count, and the strongest flare class of the past week. Below the cards, `OrbitGlobe` renders all fetched satellites at their current positions. A table shows the five closest current approaches from the conjunction result, with miss distance, relative velocity, and risk badge. Two `Explain` panels describe what the four pages do and how the three-layer architecture works.

**[`app/conjunctions/page.tsx`](../astraops-web/app/conjunctions/page.tsx)** — Conjunction Watch
An interactive screening form. The user picks a CelesTrak group from a dropdown (starlink, stations, oneweb, iridium-NEXT, active) and sets a miss-distance threshold in kilometres, then clicks **Run screening**. Four sequential phase messages are shown during the request (fetching elements, propagating with SGP4, computing pairwise distances, refining TCA) with timed `setTimeout` callbacks. The results table shows primary and secondary satellite names and NORAD IDs, TCA in UTC, miss distance, relative velocity, Pc in scientific notation, and a risk badge. Clicking any row calls `GET /conjunctions/profile` and renders a `SeparationChart` below the table. If events are present, an **AI risk brief** button calls `GET /briefs/conjunction` and renders the Granite-generated text. The page also notes when the screened population has been capped below the total group size.

**[`app/spaceweather/page.tsx`](../astraops-web/app/spaceweather/page.tsx)** — Space Weather Sentinel
Fetches `GET /spaceweather` on mount and displays solar flares, CMEs, and geomagnetic storms in three scrollable panels. Each panel shows the key metric (flare class, CME speed, Kp index) and timestamp. Three informational cards explain what flares, CMEs, and storms are in terms relevant to orbital operations. A **Generate operational brief** button calls `GET /briefs/spaceweather` and renders the Granite output in a styled panel above the data. The page notes explicitly that NOAA's G-scale was calibrated for power grids and not orbital drag, with the February 2022 Starlink event as the concrete example.

**[`app/research/page.tsx`](../astraops-web/app/research/page.tsx)** — Research Copilot
A text input that sends `POST /research/ask` with the question and `top_k: 5`. Three example questions are shown as clickable chips that populate the input and trigger the request immediately. While waiting, an in-progress panel explains that the pipeline is embedding the question, searching the vector index, and asking Granite. The answer is rendered as plain text in a styled brief panel. Below it, each retrieved source passage is shown in a card with its title, similarity score, and a 300-character excerpt, ranked by similarity so the user can verify the reasoning.

---

### Components

**[`components/OrbitGlobe.tsx`](../astraops-web/components/OrbitGlobe.tsx)**
Wraps `react-globe.gl` (dynamically imported with SSR disabled) to render satellite positions on an interactive 3D globe. Fetches `GET /satellites/positions` on mount and then every 15 seconds. Each satellite is a small sphere coloured by altitude band: red below 500 km, dark blue 500–1000 km, green above 1000 km. Altitude is compressed logarithmically so that LEO and GEO objects are both legible at one zoom level. The globe is sized responsively to its container via a `ResizeObserver`-style effect. Hovering a satellite shows its name, lat/lon, and altitude in the header area.

**[`components/SeparationChart.tsx`](../astraops-web/components/SeparationChart.tsx)**
A Recharts `LineChart` rendering the separation-vs-time curve for a single satellite pair, populated from the `/conjunctions/profile` response. A dashed vertical `ReferenceLine` marks the TCA. The chart header shows satellite names, minimum separation, and a characterisation of the encounter based on mean relative velocity: below 2 km/s is flagged as "co-planar drift — low energy, predictable geometry"; above 7 km/s as "crossing encounter — high energy, sensitive to covariance error".

**[`components/NavRail.tsx`](../astraops-web/components/NavRail.tsx)**
A client component that renders the four navigation links (Dashboard, Conjunctions, Space weather, Research) using `next/link`. Active state is detected with `usePathname()` and applied via a `data-active` attribute. On desktop the hint text below each label is visible; on mobile the hint is hidden and the links wrap horizontally.

**[`components/StatusStrip.tsx`](../astraops-web/components/StatusStrip.tsx)**
A persistent top bar rendered in the root layout. Polls `GET /satellites?group=stations` every 30 seconds and displays a coloured live-dot ("Feed live" / "Feed offline"), a live UTC clock ticking every second, and the age of the current element set in minutes. The age indicator turns amber when the element set is more than 120 minutes old, matching the CelesTrak two-hour refresh cycle.

**[`components/Explain.tsx`](../astraops-web/components/Explain.tsx)**
A simple presentational component that renders a titled explanatory panel with multi-column text layout at wider viewports. Used by all four pages to provide contextual background without cluttering the primary data view.

**[`components/Sticker.tsx`](../astraops-web/components/Sticker.tsx)**
Five inline SVG icons in the project palette — `Rocket`, `Satellite`, `Sun`, `Star`, and `Book` — used as section markers on page headings. Each accepts a `size` prop and is `aria-hidden` so it does not add noise to screen readers.

---

### Library

**[`lib/api.ts`](../astraops-web/lib/api.ts)**
A typed HTTP client. `api<T>(path)` prepends `NEXT_PUBLIC_API_URL` (defaulting to `http://localhost:8000`), calls `fetch` with `cache: "no-store"`, and throws on non-2xx responses with the backend's `detail` field as the error message. The file also exports all TypeScript interfaces that mirror the backend's Pydantic models: `TLERecord`, `SatelliteList`, `ConjunctionEvent`, `ConjunctionScreen`, `SolarFlare`, `CMEEvent`, `GeomagneticStorm`, `SpaceWeather`, `Brief`, `SeparationProfile`, `SatPosition`, `PositionSet`, `ResearchSource`, and `ResearchAnswer`.
