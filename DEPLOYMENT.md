# AstraOps — Deployment Guide

This guide covers deploying the **AstraOps API** (FastAPI) to [Render](https://render.com)
and the **AstraOps Web** (Next.js) frontend to [Vercel](https://vercel.com).

---

## Repository layout

```
astraops/
├── astraops-api/        # FastAPI backend
│   ├── Dockerfile
│   ├── .dockerignore
│   └── render.yaml      # (referenced from repo root)
├── astraops-web/        # Next.js 16 frontend
│   └── vercel.json
├── render.yaml          # Render infrastructure definition (repo root)
└── DEPLOYMENT.md        # this file
```

---

## Part 1 — Backend on Render

### Prerequisites
- A [Render](https://render.com) account connected to your GitHub/GitLab repository.
- An [IBM Cloud](https://cloud.ibm.com) account with a Watsonx project (for the RAG endpoint).
- A [NASA API key](https://api.nasa.gov) (the `DEMO_KEY` default is rate-limited to 30 req/hr).

### Step 1 — Create the web service

1. In the Render dashboard click **New → Web Service**.
2. Connect your repository and select the branch you want to deploy (e.g. `main`).
3. Choose **Docker** as the runtime.
4. Set **Dockerfile Path** to `astraops-api/Dockerfile`.
5. Set **Docker Build Context** to `astraops-api`.
6. Leave the **Start Command** blank — the `CMD` in the Dockerfile handles it.
7. Choose the **Free** plan (or upgrade to eliminate cold starts — see note below).
8. Click **Create Web Service**. The first deploy will start automatically.

> **Infrastructure-as-code alternative:** `render.yaml` at the repo root defines
> the same service. Render will detect it automatically if you enable **Blueprint**
> sync in your account settings.

### Step 2 — Set environment variables

Navigate to your service → **Environment** and add the following variables.
Leave values blank until you have them; Render will not redeploy until you
explicitly trigger one.

| Variable | Description |
|---|---|
| `NASA_API_KEY` | Your NASA API key from api.nasa.gov |
| `WATSONX_APIKEY` | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | Watsonx project ID |
| `WATSONX_URL` | Watsonx region endpoint, e.g. `https://us-south.ml.cloud.ibm.com` |
| `CORS_ORIGINS` | JSON array of allowed origins — **set after Step 4 below** |

> `PORT` is injected by Render automatically. Do **not** set it manually.

### Step 3 — Confirm the health check

After the deploy completes, open:

```
https://<your-service>.onrender.com/health
```

You should see:

```json
{ "status": "ok", "timestamp": "...", "cache_entries": 0 }
```

The Swagger UI is available at `/docs`.

### Step 4 — Note your Render URL

Copy the public URL shown in the Render dashboard, e.g.:

```
https://astraops-api.onrender.com
```

You'll need this in Part 2.

---

## Part 2 — Frontend on Vercel

### Prerequisites
- A [Vercel](https://vercel.com) account connected to your repository.
- The Render backend URL from Step 4 above.

### Step 1 — Import the project

1. In the Vercel dashboard click **Add New → Project**.
2. Import your repository.
3. Vercel will auto-detect Next.js. Confirm the following settings:

   | Setting | Value |
   |---|---|
   | Framework Preset | Next.js |
   | Root Directory | `astraops-web` |
   | Build Command | `npm run build` |
   | Output Directory | `.next` |
   | Install Command | `npm ci` |

### Step 2 — Set the API URL environment variable

Before clicking **Deploy**, add:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://astraops-api.onrender.com` (no trailing slash) |

This variable is baked into the client bundle at build time by Next.js.
If you change the backend URL you must **redeploy** the frontend.

### Step 3 — Deploy

Click **Deploy**. Vercel will build and publish the frontend. Once live you
will see a deployment URL like:

```
https://astraops-web.vercel.app
```

---

## Part 3 — Wire CORS

Now that the Vercel domain is known, go back to Render → **Environment** and
update `CORS_ORIGINS`:

```
["https://astraops-web.vercel.app"]
```

If you have a custom domain or multiple preview deployments, add them all:

```
["https://astraops-web.vercel.app", "https://www.yourdomain.com"]
```

The value must be a valid JSON array. `pydantic-settings` parses it directly
into the `cors_origins: list[str]` field in `config.py`.

After saving, Render will redeploy the backend automatically. Verify by
loading the frontend and checking that requests to `/health` succeed without
CORS errors in the browser console.

---

## Local development

```bash
# Terminal 1 — backend
cd astraops-api
cp .env.example .env          # fill in keys
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd astraops-web
cp .env.local.example .env.local   # if it exists, else create manually
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Docker smoke test (optional)

Before pushing to Render you can build and run the image locally:

```bash
cd astraops-api

docker build -t astraops-api:local .

docker run --rm \
  -p 8000:8000 \
  -e NASA_API_KEY=DEMO_KEY \
  -e WATSONX_APIKEY=your-key \
  -e WATSONX_PROJECT_ID=your-project \
  -e WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  -e CORS_ORIGINS='["http://localhost:3000"]' \
  astraops-api:local
```

Open `http://localhost:8000/health` to confirm the container is healthy.

---

## Render free tier — cold start note

> ⚠️ **The Render free tier suspends your service after 15 minutes of
> inactivity.** The first HTTP request after the service sleeps will block for
> approximately 30–60 seconds while the container restarts.
>
> To avoid this:
> - Upgrade to a **Starter** plan ($7/month) for always-on instances, or
> - Use an external uptime monitor (e.g. UptimeRobot, Better Stack) to ping
>   `/health` every 10 minutes and keep the service warm, or
> - Accept the cold start for low-traffic or demo deployments.

---

## Environment variable reference

### Backend (`astraops-api`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | auto | `8000` | Injected by Render; do not set manually |
| `NASA_API_KEY` | yes | `DEMO_KEY` | NASA API key for DONKI space weather |
| `WATSONX_APIKEY` | yes (RAG) | `""` | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | yes (RAG) | `""` | Watsonx project ID |
| `WATSONX_URL` | yes (RAG) | `https://us-south.ml.cloud.ibm.com` | Watsonx regional endpoint |
| `CORS_ORIGINS` | yes | `["http://localhost:3000"]` | JSON array of allowed origins |
| `DEBUG` | no | `false` | Enable verbose logging |
| `TLE_CACHE_TTL` | no | `14400` | TLE cache lifetime in seconds |
| `SPACEWEATHER_CACHE_TTL` | no | `900` | Space weather cache lifetime |
| `CONJUNCTION_CACHE_TTL` | no | `1800` | Conjunction cache lifetime |
| `HTTP_TIMEOUT` | no | `30.0` | External API request timeout |

### Frontend (`astraops-web`)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | yes | Full URL of the backend, no trailing slash |
