"""
FastAPI entry point — The Dirty Laundry V2 Backend Orchestrator.

Lifespan:
  startup  → shared httpx client, Supabase services, ARQ Redis pool, bucket init
  shutdown → graceful cleanup

Routes:
  /api/v1/auth/*      → signup, login, logout, consent
  /api/v1/tryon/*     → submit VTO jobs, poll status, history
  /api/v1/garments/*  → browse & upload garment catalog
  /api/v1/health      → service health & circuit breaker states
  /api/v1/metrics     → Prometheus-format metrics
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth_router, garments_router, health_router, tryon_router
from app.services.auth_service import AuthService
from app.services.body_estimation_service import BodyEstimationService
from app.services.storage_service import StorageService
from app.services.synthesis_service import SynthesisService
from app.services.video_service import VideoService

# ── Structured logging setup ─────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if get_settings().is_development
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(get_settings().log_level)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("app")


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — initialise shared resources on startup,
    clean up on shutdown.
    """
    settings = get_settings()

    logger.info(
        "app.starting",
        environment=settings.environment.value,
        stubs=settings.use_stubs,
    )

    # ── Shared HTTP client (connection pool) ─────────────────────
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
        limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
        follow_redirects=True,
    )
    app.state.http_client = http_client
    app.state.settings = settings

    # ── Services ─────────────────────────────────────────────────
    storage = StorageService(settings, http_client)
    auth_service = AuthService(settings, http_client)
    body_estimation = BodyEstimationService(settings, http_client)
    synthesis = SynthesisService(settings, http_client, storage)
    video_service = VideoService(settings, http_client, storage)

    app.state.storage_service = storage
    app.state.auth_service = auth_service
    app.state.body_estimation_service = body_estimation
    app.state.synthesis_service = synthesis
    app.state.video_service = video_service

    # ── Supabase bucket init ─────────────────────────────────────
    await storage.initialize_buckets()

    # ── ARQ Redis pool ───────────────────────────────────────────
    redis_pool = None
    try:
        from arq.connections import create_pool
        from app.workers.worker_config import WorkerSettings

        redis_pool = await create_pool(WorkerSettings.redis_settings)
        logger.info("app.redis_connected")
    except Exception as exc:
        logger.warning("app.redis_unavailable", error=str(exc))

    app.state.redis_pool = redis_pool

    logger.info("app.started")

    yield  # ── Application runs here ─────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("app.shutting_down")
    await http_client.aclose()
    if redis_pool:
        redis_pool.close()
        await redis_pool.wait_closed()
    logger.info("app.shutdown_complete")


# ── App factory ──────────────────────────────────────────────────────
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="The Dirty Laundry V2 — Virtual Try-On API",
        description=(
            "Production-grade Virtual Try-On pipeline. "
            "5-layer architecture: Body Estimation → Garment Synthesis → "
            "360° Video → Async Jobs → Privacy & Consent."
        ),
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
    )

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware ─────────────────────────────────────────
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # ── Routers ──────────────────────────────────────────────────
    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(tryon_router, prefix=api_prefix)
    app.include_router(garments_router, prefix=api_prefix)
    app.include_router(health_router, prefix=api_prefix)

    # ── Global exception handler ─────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "app.unhandled_exception",
            path=request.url.path,
            error=str(exc)[:500],
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error. Our team has been notified.",
                "error_type": type(exc).__name__,
            },
        )

    # ── Root redirect ────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "service": "The Dirty Laundry V2",
            "version": "2.0.0",
            "docs": "/api/docs",
            "health": "/api/v1/health",
        }

    return app


# ── Module-level app instance (for uvicorn) ──────────────────────────
app = create_app()
