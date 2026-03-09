"""
Try-On routes — submit VTO jobs, poll status, view history.

POST /tryon       → Upload photos + garment → enqueue ARQ job → return job_id
GET  /tryon/{id}  → Read job status from Supabase DB
GET  /tryon/history → User's "My Looks" gallery
DELETE /tryon/{id}  → Remove a look
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.middleware.auth_middleware import get_current_user
from app.models.tryon import (
    GarmentCategory,
    JobStatus,
    PipelineStep,
    TryOnHistory,
    TryOnHistoryItem,
    TryOnJobCreated,
    TryOnJobStatus,
    TryOnResult,
)
from app.models.user import UserProfile

logger = structlog.get_logger("router.tryon")
router = APIRouter(prefix="/tryon", tags=["tryon"])


# ── Submit Try-On Job ────────────────────────────────────────────────
@router.post("", response_model=TryOnJobCreated, status_code=202)
async def submit_tryon(
    request: Request,
    selfie: UploadFile = File(..., description="User selfie photo"),
    fullbody: UploadFile = File(..., description="User full-body standing photo"),
    garment_id: str = Form(..., description="Garment catalog ID"),
    category: str = Form("upper_body", description="upper_body | lower_body | dresses"),
    garment_description: str = Form("", description="Optional text description"),
    user: UserProfile = Depends(get_current_user),
):
    """
    Submit a new Virtual Try-On job.

    1. Validates consent (Layer 5)
    2. Uploads user photos to Supabase Storage
    3. Creates job record in Supabase DB
    4. Enqueues ARQ pipeline task
    5. Returns job_id immediately (202 Accepted)

    Client subscribes to Supabase Realtime for job status updates.
    """
    settings = request.app.state.settings
    storage = request.app.state.storage_service
    auth_svc = request.app.state.auth_service

    # Layer 5: Verify consent
    has_consent = await auth_svc.check_consent(user.id)
    if not has_consent:
        raise HTTPException(
            status_code=403,
            detail="You must accept the AI-processing consent before using Virtual Try-On. POST /api/v1/auth/consent first.",
        )

    # Validate category
    try:
        cat = GarmentCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    # Generate job ID
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    # Upload user photos to Supabase Storage
    selfie_bytes = await selfie.read()
    fullbody_bytes = await fullbody.read()

    selfie_path = f"{user.id}/{job_id}/selfie.jpg"
    fullbody_path = f"{user.id}/{job_id}/fullbody.jpg"

    await storage.upload_file(
        "user-uploads", selfie_path, selfie_bytes,
        content_type=selfie.content_type or "image/jpeg",
    )
    await storage.upload_file(
        "user-uploads", fullbody_path, fullbody_bytes,
        content_type=fullbody.content_type or "image/jpeg",
    )

    # Look up garment image URL from catalog
    garment_image_url = await _get_garment_image_url(request, garment_id)

    # Create job record in Supabase DB
    await _create_job_record(request, job_id, user.id, garment_id, cat.value, now)

    # Enqueue ARQ task
    redis_pool = request.app.state.redis_pool
    if redis_pool:
        from arq.connections import ArqRedis

        pool: ArqRedis = redis_pool
        await pool.enqueue_job(
            "process_tryon_job",
            job_id=job_id,
            user_id=user.id,
            selfie_url=selfie_path,
            fullbody_url=fullbody_path,
            garment_id=garment_id,
            garment_image_url=garment_image_url,
            category=cat.value,
            garment_description=garment_description,
            _job_id=f"vto-{job_id}",
            _queue_name="arq:vto-pipeline",
        )
        logger.info("tryon.job_enqueued", job_id=job_id, user_id=user.id)
    else:
        logger.warning("tryon.no_redis", job_id=job_id, msg="Job created but worker not available")

    return TryOnJobCreated(
        job_id=job_id,
        status=JobStatus.QUEUED,
        estimated_seconds=70,
        created_at=now,
    )


# ── Poll Job Status ─────────────────────────────────────────────────
@router.get("/{job_id}", response_model=TryOnJobStatus)
async def get_job_status(
    job_id: str,
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    """
    Read current job status from Supabase DB.

    Prefer Supabase Realtime subscriptions on the frontend instead
    of polling this endpoint.
    """
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)

    if settings.use_stubs:
        return TryOnJobStatus(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_step=PipelineStep.DONE,
            result=TryOnResult(
                photo_url=f"https://stub.supabase.co/tryon-results/{user.id}/{job_id}/tryon_photo.png",
                video_url=f"https://stub.supabase.co/tryon-results/{user.id}/{job_id}/rotation.mp4",
                mesh_url=f"https://stub.supabase.co/tryon-results/{user.id}/{job_id}/model.glb",
            ),
            created_at=now,
            updated_at=now,
        )

    http: httpx.AsyncClient = request.app.state.http_client
    resp = await http.get(
        f"{settings.supabase.url}/rest/v1/tryon_jobs?id=eq.{job_id}&user_id=eq.{user.id}&select=*",
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to read job status")

    rows = resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Job not found")

    row = rows[0]
    result = None
    if row.get("result_photo_url"):
        result = TryOnResult(
            photo_url=row.get("result_photo_url"),
            video_url=row.get("result_video_url"),
            mesh_url=row.get("result_mesh_url"),
        )

    return TryOnJobStatus(
        job_id=row["id"],
        status=JobStatus(row.get("status", "queued")),
        progress=row.get("progress", 0),
        current_step=PipelineStep(row.get("current_step", "upload")),
        result=result,
        error=row.get("error"),
        created_at=row.get("created_at", now),
        updated_at=row.get("updated_at", now),
    )


# ── My Looks (History) ──────────────────────────────────────────────
@router.get("/history", response_model=TryOnHistory)
async def get_history(
    request: Request,
    user: UserProfile = Depends(get_current_user),
    limit: int = 50,
):
    """
    User's 'My Looks' gallery — completed try-on results.
    """
    settings = request.app.state.settings

    if settings.use_stubs:
        return TryOnHistory(looks=[], total=0)

    http: httpx.AsyncClient = request.app.state.http_client
    resp = await http.get(
        (
            f"{settings.supabase.url}/rest/v1/tryon_jobs"
            f"?user_id=eq.{user.id}"
            f"&status=eq.completed"
            f"&select=*"
            f"&order=created_at.desc"
            f"&limit={limit}"
        ),
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )

    if resp.status_code != 200:
        return TryOnHistory(looks=[], total=0)

    rows = resp.json()
    looks = []
    for row in rows:
        looks.append(
            TryOnHistoryItem(
                job_id=row["id"],
                garment_id=row.get("garment_id", ""),
                garment_name=row.get("garment_name", "Unknown"),
                garment_thumbnail=row.get("garment_thumbnail", ""),
                category=GarmentCategory(row.get("category", "upper_body")),
                result=TryOnResult(
                    photo_url=row.get("result_photo_url"),
                    video_url=row.get("result_video_url"),
                    mesh_url=row.get("result_mesh_url"),
                ),
                created_at=row.get("created_at"),
            )
        )

    return TryOnHistory(looks=looks, total=len(looks))


# ── Delete Look ──────────────────────────────────────────────────────
@router.delete("/{job_id}")
async def delete_look(
    job_id: str,
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    settings = request.app.state.settings

    if settings.use_stubs:
        return {"message": "Deleted"}

    http: httpx.AsyncClient = request.app.state.http_client
    # Delete from DB
    await http.delete(
        f"{settings.supabase.url}/rest/v1/tryon_jobs?id=eq.{job_id}&user_id=eq.{user.id}",
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )

    # Delete storage assets
    storage = request.app.state.storage_service
    for filename in ("tryon_photo.png", "model.glb", "rotation.mp4"):
        try:
            await storage.delete_file(
                "tryon-results",
                f"{user.id}/{job_id}/{filename}",
            )
        except Exception:
            pass

    return {"message": "Deleted"}


# ── Helpers ──────────────────────────────────────────────────────────
async def _get_garment_image_url(request: Request, garment_id: str) -> str:
    """Look up garment product image URL from catalog."""
    settings = request.app.state.settings

    if settings.use_stubs:
        return f"https://stub.supabase.co/storage/v1/object/public/garments/{garment_id}/image.jpg"

    http: httpx.AsyncClient = request.app.state.http_client
    resp = await http.get(
        f"{settings.supabase.url}/rest/v1/garments?id=eq.{garment_id}&select=image_url",
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )
    if resp.status_code == 200:
        rows = resp.json()
        if rows:
            return rows[0].get("image_url", "")

    raise HTTPException(status_code=404, detail=f"Garment {garment_id} not found")


async def _create_job_record(
    request: Request,
    job_id: str,
    user_id: str,
    garment_id: str,
    category: str,
    created_at: datetime,
) -> None:
    """Insert a new tryon_jobs row in Supabase Postgres."""
    settings = request.app.state.settings

    if settings.use_stubs:
        return

    http: httpx.AsyncClient = request.app.state.http_client
    await http.post(
        f"{settings.supabase.url}/rest/v1/tryon_jobs",
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json={
            "id": job_id,
            "user_id": user_id,
            "garment_id": garment_id,
            "category": category,
            "status": "queued",
            "progress": 0,
            "current_step": "upload",
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
        },
        timeout=10.0,
    )
