"""
ARQ Worker — Async job processor for the 5-layer VTO pipeline.

Pipeline per job (~70 seconds, ~$0.09):
  1. Body Estimation   (HMR 2.0 / MediaPipe)  →  10%
  2. Garment Synthesis  (IDM-VTON / Replicate)  →  40%
  3. 360° Mesh + Video  (TRELLIS + Wan 2.2)     →  90%
  4. Finalize & store                            → 100%

Each step updates the `tryon_jobs` table in Supabase Postgres,
which triggers a Supabase Realtime push to the subscribed client.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

from app.config import Settings, get_settings
from app.models.tryon import JobStatus, PipelineStep
from app.services.body_estimation_service import BodyEstimationService
from app.services.storage_service import StorageService
from app.services.synthesis_service import SynthesisService
from app.services.video_service import VideoService
from app.utils.monitoring import metrics

logger = structlog.get_logger("worker.tryon")


# ── Supabase DB helper ──────────────────────────────────────────────
async def _update_job_status(
    http: httpx.AsyncClient,
    settings: Settings,
    job_id: str,
    status: JobStatus,
    progress: int,
    current_step: PipelineStep,
    result: Optional[Dict] = None,
    error: Optional[str] = None,
):
    """
    Update the tryon_jobs row in Supabase Postgres.
    This triggers Supabase Realtime → pushes to the subscribed frontend client.
    """
    payload: Dict[str, Any] = {
        "status": status.value,
        "progress": progress,
        "current_step": current_step.value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result:
        payload["result_photo_url"] = result.get("photo_url")
        payload["result_video_url"] = result.get("video_url")
        payload["result_mesh_url"] = result.get("mesh_url")
    if error:
        payload["error"] = error

    if settings.use_stubs:
        logger.info(
            "worker.stub_status_update",
            job_id=job_id,
            status=status.value,
            progress=progress,
        )
        return

    try:
        resp = await http.patch(
            f"{settings.supabase.url}/rest/v1/tryon_jobs?id=eq.{job_id}",
            headers={
                "apikey": settings.supabase.service_role_key,
                "Authorization": f"Bearer {settings.supabase.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("worker.status_update_failed", job_id=job_id, error=str(exc))


# ── Main pipeline task ──────────────────────────────────────────────
async def process_tryon_job(
    ctx: Dict[str, Any],
    job_id: str,
    user_id: str,
    selfie_url: str,
    fullbody_url: str,
    garment_id: str,
    garment_image_url: str,
    category: str = "upper_body",
    garment_description: str = "",
) -> Dict[str, Any]:
    """
    ARQ task: Execute the full 5-layer VTO pipeline.

    Args:
        ctx: ARQ context (contains shared resources from startup)
        job_id: Unique job identifier
        user_id: User who submitted the job
        selfie_url: Supabase URL to user's selfie
        fullbody_url: Supabase URL to user's full-body photo
        garment_id: Garment catalog ID
        garment_image_url: Supabase URL to garment product image
        category: upper_body | lower_body | dresses
        garment_description: Text description for VTO model
    """
    pipeline_start = time.monotonic()
    settings: Settings = ctx["settings"]
    http: httpx.AsyncClient = ctx["http_client"]
    storage: StorageService = ctx["storage"]
    body_service: BodyEstimationService = ctx["body_estimation"]
    synthesis: SynthesisService = ctx["synthesis"]
    video_service: VideoService = ctx["video_service"]

    logger.info("worker.pipeline_start", job_id=job_id, user_id=user_id)

    try:
        # ════════════════════════════════════════════════════════════
        # STEP 1: Body Estimation (Layer 1) — ~10s
        # ════════════════════════════════════════════════════════════
        await _update_job_status(
            http, settings, job_id,
            JobStatus.BODY_ESTIMATION, 5, PipelineStep.BODY_ESTIMATION,
        )

        # Download user photos from Supabase
        selfie_bytes = await storage.download_file("user-uploads", selfie_url) if not settings.use_stubs else b""
        fullbody_bytes = await storage.download_file("user-uploads", fullbody_url) if not settings.use_stubs else b""

        async with metrics.track("pipeline.body_estimation"):
            body_result = await body_service.estimate_body(selfie_bytes, fullbody_bytes)

        if not body_result.is_valid:
            await _update_job_status(
                http, settings, job_id,
                JobStatus.FAILED, 10, PipelineStep.BODY_ESTIMATION,
                error=body_result.validation_error or "Body estimation failed",
            )
            return {"status": "failed", "error": body_result.validation_error}

        await _update_job_status(
            http, settings, job_id,
            JobStatus.BODY_ESTIMATION, 15, PipelineStep.BODY_ESTIMATION,
        )
        logger.info(
            "worker.body_estimation_done",
            job_id=job_id,
            confidence=body_result.pose_confidence,
            time_ms=body_result.processing_time_ms,
        )

        # ════════════════════════════════════════════════════════════
        # STEP 2: Garment Synthesis (Layer 2) — ~18s
        # ════════════════════════════════════════════════════════════
        await _update_job_status(
            http, settings, job_id,
            JobStatus.GARMENT_SYNTHESIS, 20, PipelineStep.GARMENT_SYNTHESIS,
        )

        # Use full-body photo URL for VTO (Supabase public URL)
        human_photo_url = storage.get_public_url("user-uploads", fullbody_url)

        async with metrics.track("pipeline.garment_synthesis"):
            synthesis_result = await synthesis.synthesize(
                human_image_url=human_photo_url,
                garment_image_url=garment_image_url,
                category=category,
                garment_description=garment_description,
                user_id=user_id,
                job_id=job_id,
            )

        tryon_photo_url = synthesis_result["photo_url"]

        await _update_job_status(
            http, settings, job_id,
            JobStatus.GARMENT_SYNTHESIS, 45, PipelineStep.GARMENT_SYNTHESIS,
        )
        logger.info(
            "worker.synthesis_done",
            job_id=job_id,
            model=synthesis_result.get("model_used"),
            time_ms=synthesis_result.get("processing_time_ms"),
        )

        # ════════════════════════════════════════════════════════════
        # STEP 3: 360° Video + Mesh Generation (Layer 3) — ~30s
        # ════════════════════════════════════════════════════════════
        await _update_job_status(
            http, settings, job_id,
            JobStatus.VIDEO_RENDERING, 50, PipelineStep.VIDEO_GENERATION,
        )

        async with metrics.track("pipeline.video_360"):
            video_result = await video_service.generate_360(
                tryon_photo_url=tryon_photo_url,
                user_id=user_id,
                job_id=job_id,
            )

        await _update_job_status(
            http, settings, job_id,
            JobStatus.VIDEO_RENDERING, 90, PipelineStep.SNAPSHOT,
        )
        logger.info(
            "worker.video_360_done",
            job_id=job_id,
            has_mesh=video_result.get("mesh_url") is not None,
            has_video=video_result.get("video_url") is not None,
            time_ms=video_result.get("processing_time_ms"),
        )

        # ════════════════════════════════════════════════════════════
        # STEP 4: Finalize — mark complete, store all URLs
        # ════════════════════════════════════════════════════════════
        final_result = {
            "photo_url": tryon_photo_url,
            "video_url": video_result.get("video_url"),
            "mesh_url": video_result.get("mesh_url"),
        }

        await _update_job_status(
            http, settings, job_id,
            JobStatus.COMPLETED, 100, PipelineStep.DONE,
            result=final_result,
        )

        total_ms = (time.monotonic() - pipeline_start) * 1000
        metrics.record("pipeline.total", total_ms)
        logger.info(
            "worker.pipeline_complete",
            job_id=job_id,
            total_ms=total_ms,
            photo=bool(tryon_photo_url),
            video=bool(video_result.get("video_url")),
            mesh=bool(video_result.get("mesh_url")),
        )

        return {"status": "completed", "result": final_result}

    except Exception as exc:
        total_ms = (time.monotonic() - pipeline_start) * 1000
        metrics.record("pipeline.total", total_ms, error=str(exc))
        logger.error(
            "worker.pipeline_failed",
            job_id=job_id,
            error=str(exc),
            total_ms=total_ms,
        )
        await _update_job_status(
            http, settings, job_id,
            JobStatus.FAILED, 0, PipelineStep.DONE,
            error=str(exc)[:500],
        )
        return {"status": "failed", "error": str(exc)}
