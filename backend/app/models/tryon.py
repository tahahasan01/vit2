"""
Try-On schemas — the core service contract between Frontend ↔ Backend.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────
class GarmentCategory(str, Enum):
    UPPER_BODY = "upper_body"
    LOWER_BODY = "lower_body"
    DRESSES = "dresses"


class JobStatus(str, Enum):
    QUEUED = "queued"
    BODY_ESTIMATION = "body_estimation"
    GARMENT_SYNTHESIS = "garment_synthesis"
    VIDEO_RENDERING = "video_rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    UPLOAD = "upload"
    BODY_ESTIMATION = "body_estimation"
    GARMENT_SYNTHESIS = "garment_synthesis"
    MESH_GENERATION = "mesh_generation"
    VIDEO_GENERATION = "video_generation"
    SNAPSHOT = "snapshot"
    DONE = "done"


# ── Request / Response ───────────────────────────────────────────────────
class TryOnRequest(BaseModel):
    """POST /api/v1/tryon — submitted by frontend."""

    garment_id: str = Field(..., description="Garment catalog ID")
    category: GarmentCategory = Field(
        GarmentCategory.UPPER_BODY, description="Garment category"
    )
    garment_description: str = Field(
        "", description="Optional text description for VTO model"
    )
    # user_images are sent as multipart form files, not in JSON body


class TryOnJobCreated(BaseModel):
    """Immediate response after submitting a try-on job."""

    job_id: str
    status: JobStatus = JobStatus.QUEUED
    estimated_seconds: int = Field(
        70, description="Approximate pipeline duration"
    )
    created_at: datetime


class TryOnResult(BaseModel):
    """Final result URLs — all assets are Supabase permanent URLs."""

    photo_url: Optional[str] = Field(
        None, description="High-res front-view photorealistic try-on"
    )
    video_url: Optional[str] = Field(
        None, description="360° orbital rotation MP4"
    )
    mesh_url: Optional[str] = Field(
        None, description="Interactive .glb 3D mesh"
    )


class TryOnJobStatus(BaseModel):
    """
    GET /api/v1/tryon/{job_id} — polled or pushed via Supabase Realtime.
    This is THE service contract for real-time progress tracking.
    """

    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100, description="0-100 percent")
    current_step: PipelineStep = PipelineStep.UPLOAD
    result: Optional[TryOnResult] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TryOnHistoryItem(BaseModel):
    """Single item in the user's 'My Looks' gallery."""

    job_id: str
    garment_id: str
    garment_name: str
    garment_thumbnail: str
    category: GarmentCategory
    result: TryOnResult
    created_at: datetime


class TryOnHistory(BaseModel):
    """GET /api/v1/tryon/history"""

    looks: List[TryOnHistoryItem] = []
    total: int = 0
