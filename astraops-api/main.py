"""AstraOps API — FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cache import cache
from config import get_settings
from routers import conjunctions, research, satellites, spaceweather

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("astraops")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down — clearing in-memory cache (%d entries)", cache.size())
    cache.clear()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Space mission intelligence platform. "
            "Provides satellite TLE data, conjunction screening, "
            "space weather events, and a RAG research interface."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS — allow Next.js dev server at localhost:3000
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Global exception handler — surface unexpected errors cleanly
    # -----------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc), "fallback_used": False},
        )

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    app.include_router(satellites.router)
    app.include_router(conjunctions.router)
    app.include_router(spaceweather.router)
    app.include_router(research.router)

    # -----------------------------------------------------------------------
    # Health / meta endpoints
    # -----------------------------------------------------------------------
    @app.get("/", tags=["Meta"], summary="API root")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "status": "ok",
        }

    @app.get("/health", tags=["Meta"], summary="Health check")
    async def health():
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_entries": cache.size(),
        }

    @app.delete("/cache", tags=["Meta"], summary="Flush in-memory cache")
    async def flush_cache():
        before = cache.size()
        cache.clear()
        return {"cleared_entries": before}

    return app


app = create_app()
