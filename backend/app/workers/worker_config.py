"""
ARQ Worker settings — configures the async job queue.

Run the worker:
  arq app.workers.worker_config.WorkerSettings

This starts an async event loop that:
  1. Connects to Redis
  2. Initialises shared HTTP client, Supabase services etc.
  3. Processes VTO pipeline jobs from the queue
"""
from __future__ import annotations

from typing import Any, Dict

import httpx
import structlog
from arq.connections import RedisSettings as ArqRedisSettings

from app.config import get_settings
from app.services.body_estimation_service import BodyEstimationService
from app.services.fashn_service import FashnService
from app.services.storage_service import StorageService
from app.services.synthesis_service import SynthesisService
from app.services.video_service import VideoService
from app.workers.tryon_worker import process_tryon_job

logger = structlog.get_logger("worker.config")


async def startup(ctx: Dict[str, Any]) -> None:
    """Initialise shared resources on worker start."""
    settings = get_settings()
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        follow_redirects=True,
    )
    storage = StorageService(settings, http_client)
    body_estimation = BodyEstimationService(settings, http_client)

    # Fashn.ai (primary VTO provider)
    fashn_service = None
    if settings.fashn.api_key:
        fashn_service = FashnService(settings, http_client)

    synthesis = SynthesisService(
        settings, http_client, storage, fashn_service=fashn_service
    )
    video_service = VideoService(
        settings, http_client, storage, fashn_service=fashn_service
    )

    ctx["settings"] = settings
    ctx["http_client"] = http_client
    ctx["storage"] = storage
    ctx["body_estimation"] = body_estimation
    ctx["synthesis"] = synthesis
    ctx["video_service"] = video_service

    logger.info(
        "worker.started",
        environment=settings.environment.value,
        stubs=settings.use_stubs,
    )


async def shutdown(ctx: Dict[str, Any]) -> None:
    """Cleanup on worker shutdown."""
    http_client: httpx.AsyncClient = ctx.get("http_client")
    if http_client:
        await http_client.aclose()
    logger.info("worker.shutdown")


def _parse_redis_url(url: str) -> ArqRedisSettings:
    """Parse a Redis URL into arq RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    ssl = parsed.scheme in ("rediss",)
    return ArqRedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password or None,
        database=int(parsed.path.lstrip("/") or 0),
        ssl=ssl,
    )


class WorkerSettings:
    """ARQ worker configuration — imported by `arq` CLI."""

    functions = [process_tryon_job]
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection
    redis_settings = _parse_redis_url(get_settings().redis.url)

    # Job settings
    max_jobs = get_settings().pipeline.max_concurrent_jobs
    job_timeout = get_settings().pipeline.timeout_seconds
    max_tries = 2  # Retry once on failure
    health_check_interval = 30  # seconds

    # Queue name
    queue_name = "arq:vto-pipeline"
