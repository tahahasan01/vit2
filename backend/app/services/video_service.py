"""
Layer 3 — 360° Video Generation Service

Pipeline:
  Step A: Front-view VTO photo → TRELLIS (Replicate) → textured .glb mesh  (~30s, ~$0.04)
  Step B: Front-view VTO photo → Wan 2.2 I2V (Replicate) → orbital MP4 video (~20s, ~$0.03)

Both steps run in parallel.  Combined output: .glb (interactive 3D) + .mp4 (video playback).
All assets snapshotted to Supabase Storage.

Graceful degradation:
  - TRELLIS fails → skip mesh, return video only
  - Wan fails → skip video, return mesh only
  - Both fail → return photo only (Layer 2 result stands alone)
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.services.storage_service import StorageService
from app.utils.circuit_breaker import create_breaker

logger = structlog.get_logger(__name__)


class VideoService:
    """
    Layer 3: 360° Video Generation.

    Dual-output pipeline:
    - TRELLIS: Single image → textured 3D .glb mesh (for R3F interactive viewer)
    - Fashn image-to-video (PRIMARY) / Wan 2.2 I2V (FALLBACK): orbital rotation video
    """

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        storage: StorageService,
        fashn_service=None,
    ):
        self._settings = settings
        self._http = http_client
        self._storage = storage
        self._fashn = fashn_service
        self._replicate_token = settings.replicate.api_token
        self._trellis_model = settings.replicate.trellis_model_id
        self._video_model = settings.replicate.video_model_id
        self._breaker_trellis = create_breaker("replicate_trellis", fail_max=3, reset_timeout=120)
        self._breaker_video = create_breaker("replicate_wan_video", fail_max=3, reset_timeout=120)

    # ── Main entry ───────────────────────────────────────────────────
    async def generate_360(
        self,
        tryon_photo_url: str,
        user_id: str,
        job_id: str,
    ) -> dict:
        """
        Generate both 3D mesh and orbital video from the try-on photo.
        Runs TRELLIS and Wan 2.2 in parallel for speed.

        Returns: {
            "mesh_url": str | None,     # Supabase permanent .glb URL
            "video_url": str | None,    # Supabase permanent .mp4 URL
            "processing_time_ms": float,
        }
        """
        start = time.monotonic()

        if self._settings.use_stubs:
            return self._stub_360(start, user_id, job_id)

        # Run both in parallel — each handles its own errors
        mesh_task = asyncio.create_task(
            self._generate_mesh(tryon_photo_url, user_id, job_id)
        )
        video_task = asyncio.create_task(
            self._generate_video(tryon_photo_url, user_id, job_id)
        )

        mesh_url, video_url = await asyncio.gather(
            mesh_task, video_task, return_exceptions=False
        )

        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "video_service.360_complete",
            has_mesh=mesh_url is not None,
            has_video=video_url is not None,
            time_ms=elapsed,
            job_id=job_id,
        )

        return {
            "mesh_url": mesh_url,
            "video_url": video_url,
            "processing_time_ms": elapsed,
        }

    # ── TRELLIS: Image → 3D .glb Mesh ───────────────────────────────
    async def _generate_mesh(
        self, photo_url: str, user_id: str, job_id: str
    ) -> Optional[str]:
        """Generate textured .glb mesh via TRELLIS on Replicate."""
        try:
            headers = {
                "Authorization": f"Bearer {self._replicate_token}",
                "Content-Type": "application/json",
            }

            # Submit TRELLIS prediction
            resp = await self._http.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={
                    "model": self._trellis_model,
                    "input": {
                        "image": photo_url,
                        "ss_sampling_steps": 12,
                        "slat_sampling_steps": 12,
                    },
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            prediction = resp.json()

            # Poll for result
            result = await self._poll_prediction(
                prediction["id"], headers, max_wait=180
            )

            # Extract .glb URL from TRELLIS output
            output = result.get("output", {})
            glb_url = None
            if isinstance(output, dict):
                glb_url = output.get("model_file") or output.get("glb")
            elif isinstance(output, list):
                # Some TRELLIS versions return [glb_url, preview_url]
                for item in output:
                    if isinstance(item, str) and ".glb" in item:
                        glb_url = item
                        break
                if not glb_url and output:
                    glb_url = output[0]  # Take first output
            elif isinstance(output, str):
                glb_url = output

            if not glb_url:
                logger.warning("video_service.trellis_no_glb", output=str(output)[:200])
                return None

            # Snapshot to Supabase
            path = StorageService.generate_path(user_id, job_id, "model.glb")
            permanent_url = await self._storage.snapshot_external_url(
                external_url=glb_url,
                bucket="tryon-results",
                path=path,
                content_type="model/gltf-binary",
            )

            logger.info("video_service.mesh_generated", job_id=job_id)
            return permanent_url

        except Exception as exc:
            logger.warning(
                "video_service.mesh_failed",
                error=str(exc),
                job_id=job_id,
            )
            return None  # Graceful degradation — skip mesh

    # ── Wan 2.2: Image → Orbital MP4 Video ───────────────────────────
    async def _generate_video(
        self, photo_url: str, user_id: str, job_id: str
    ) -> Optional[str]:
        """Generate 360° orbital rotation video. Fashn primary, Wan 2.2 fallback."""
        # ── Try Fashn image-to-video first ───────────────────────
        if self._fashn:
            try:
                video_url = await self._fashn.image_to_video(photo_url)
                if video_url:
                    path = StorageService.generate_path(user_id, job_id, "rotation.mp4")
                    permanent_url = await self._storage.snapshot_external_url(
                        external_url=video_url,
                        bucket="tryon-results",
                        path=path,
                        content_type="video/mp4",
                    )
                    logger.info("video_service.fashn_video_generated", job_id=job_id)
                    return permanent_url
            except Exception as exc:
                logger.warning(
                    "video_service.fashn_video_failed",
                    error=str(exc),
                    job_id=job_id,
                )

        # ── Fallback: Wan 2.2 I2V on Replicate ──────────────────
        try:
            headers = {
                "Authorization": f"Bearer {self._replicate_token}",
                "Content-Type": "application/json",
            }

            resp = await self._http.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={
                    "model": self._video_model,
                    "input": {
                        "image": photo_url,
                        "prompt": (
                            "Slow 360 degree smooth camera orbit rotation around "
                            "a person standing in a professional fashion studio, "
                            "soft studio lighting, clean white background, "
                            "fashion catalog style, smooth steady camera movement"
                        ),
                        "num_frames": 81,
                        "num_inference_steps": 20,
                    },
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            prediction = resp.json()

            result = await self._poll_prediction(
                prediction["id"], headers, max_wait=240
            )

            output = result.get("output")
            video_url = None
            if isinstance(output, str):
                video_url = output
            elif isinstance(output, list) and output:
                video_url = output[0]

            if not video_url:
                logger.warning("video_service.wan_no_video", output=str(output)[:200])
                return None

            # Snapshot to Supabase
            path = StorageService.generate_path(user_id, job_id, "rotation.mp4")
            permanent_url = await self._storage.snapshot_external_url(
                external_url=video_url,
                bucket="tryon-results",
                path=path,
                content_type="video/mp4",
            )

            logger.info("video_service.video_generated", job_id=job_id)
            return permanent_url

        except Exception as exc:
            logger.warning(
                "video_service.video_failed",
                error=str(exc),
                job_id=job_id,
            )
            return None  # Graceful degradation — skip video

    # ── Poll Replicate ───────────────────────────────────────────────
    async def _poll_prediction(
        self, prediction_id: str, headers: dict, max_wait: int = 180
    ) -> dict:
        """Poll a Replicate prediction until terminal state."""
        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        deadline = time.monotonic() + max_wait

        while time.monotonic() < deadline:
            resp = await self._http.get(poll_url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            prediction = resp.json()
            status = prediction.get("status")

            if status == "succeeded":
                return prediction
            elif status in ("failed", "canceled"):
                error = prediction.get("error", "Unknown")
                raise RuntimeError(
                    f"Prediction {prediction_id} {status}: {error}"
                )

            await asyncio.sleep(4)

        raise TimeoutError(f"Prediction {prediction_id} timed out")

    # ── Stub ─────────────────────────────────────────────────────────
    def _stub_360(self, start: float, user_id: str, job_id: str) -> dict:
        elapsed = (time.monotonic() - start) * 1000
        base = f"https://stub.supabase.co/storage/v1/object/public/tryon-results/{user_id}/{job_id}"
        logger.info("video_service.stub_used", job_id=job_id)
        return {
            "mesh_url": f"{base}/model.glb",
            "video_url": f"{base}/rotation.mp4",
            "processing_time_ms": elapsed,
        }

    # ── Health ───────────────────────────────────────────────────────
    def get_circuit_states(self) -> dict:
        states = {
            "replicate_trellis": str(self._breaker_trellis.current_state),
            "replicate_wan_video": str(self._breaker_video.current_state),
        }
        if self._fashn:
            states.update(self._fashn.get_circuit_states())
        return states
