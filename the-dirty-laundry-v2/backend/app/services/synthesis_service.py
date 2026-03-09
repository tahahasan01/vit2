"""
Layer 2 — Garment Synthesis Service (VTO Diffusion Core)

Pipeline: User photo + Garment image → IDM-VTON (Replicate) → Photorealistic try-on photo.

Primary:  cuuupid/idm-vton   (~$0.024/run, ~18s, 1.4M+ runs)
Fallback: subhash25rawat/flux-vton (Flux-based alternative)

All result images are snapshotted to Supabase Storage immediately.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.services.storage_service import StorageService
from app.utils.circuit_breaker import create_breaker

logger = structlog.get_logger(__name__)


class SynthesisService:
    """
    Layer 2: Garment Draping — Diffusion model core.

    Uses IDM-VTON (ECCV 2024) via Replicate:
    - High-level garment semantics via visual encoder → cross-attention
    - Low-level features via parallel UNet → self-attention
    - Produces photorealistic 768×1024 try-on images
    """

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        storage: StorageService,
    ):
        self._settings = settings
        self._http = http_client
        self._storage = storage
        self._replicate_token = settings.replicate.api_token
        self._primary_model = settings.replicate.vto_model_id
        self._fallback_model = settings.replicate.vto_fallback_model_id
        self._breaker_primary = create_breaker("replicate_idm_vton", fail_max=3, reset_timeout=60)
        self._breaker_fallback = create_breaker("replicate_flux_vton", fail_max=3, reset_timeout=60)

    # ── Main entry ───────────────────────────────────────────────────
    async def synthesize(
        self,
        human_image_url: str,
        garment_image_url: str,
        category: str = "upper_body",
        garment_description: str = "",
        user_id: str = "",
        job_id: str = "",
    ) -> dict:
        """
        Run garment synthesis and snapshot result to Supabase.

        Returns: {
            "photo_url": str (Supabase permanent URL),
            "processing_time_ms": float,
            "model_used": str
        }
        """
        start = time.monotonic()

        if self._settings.use_stubs:
            return self._stub_synthesis(start, user_id, job_id)

        # Try primary model (IDM-VTON)
        try:
            result_url = await self._run_prediction(
                model_id=self._primary_model,
                human_image_url=human_image_url,
                garment_image_url=garment_image_url,
                category=category,
                garment_description=garment_description,
                breaker=self._breaker_primary,
            )
            model_used = self._primary_model
        except Exception as primary_exc:
            logger.warning(
                "synthesis.primary_failed",
                model=self._primary_model,
                error=str(primary_exc),
            )
            # Fallback to Flux-VTON
            try:
                result_url = await self._run_prediction(
                    model_id=self._fallback_model,
                    human_image_url=human_image_url,
                    garment_image_url=garment_image_url,
                    category=category,
                    garment_description=garment_description,
                    breaker=self._breaker_fallback,
                )
                model_used = self._fallback_model
            except Exception as fallback_exc:
                logger.error(
                    "synthesis.all_models_failed",
                    primary_error=str(primary_exc),
                    fallback_error=str(fallback_exc),
                )
                raise RuntimeError(
                    "All VTO synthesis models are unavailable. Please try again later."
                ) from fallback_exc

        # CRITICAL: Snapshot to Supabase
        path = StorageService.generate_path(user_id, job_id, "tryon_photo.png")
        permanent_url = await self._storage.snapshot_external_url(
            external_url=result_url,
            bucket="tryon-results",
            path=path,
            content_type="image/png",
        )

        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "synthesis.complete",
            model=model_used,
            time_ms=elapsed,
            job_id=job_id,
        )

        return {
            "photo_url": permanent_url,
            "processing_time_ms": elapsed,
            "model_used": model_used,
        }

    # ── Replicate Prediction ─────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _run_prediction(
        self,
        model_id: str,
        human_image_url: str,
        garment_image_url: str,
        category: str,
        garment_description: str,
        breaker,
    ) -> str:
        """
        Submit prediction to Replicate and poll until complete.
        Returns the raw result image URL (Replicate ephemeral).
        """
        headers = {
            "Authorization": f"Bearer {self._replicate_token}",
            "Content-Type": "application/json",
            "Prefer": "wait",   # Replicate sync mode — waits up to 60s
        }

        # Build input based on model
        if "idm-vton" in model_id:
            prediction_input = {
                "human_img": human_image_url,
                "garm_img": garment_image_url,
                "garment_des": garment_description or "garment",
                "category": category,
                "steps": 30,
            }
        else:
            # Flux-VTON or generic
            prediction_input = {
                "human_image": human_image_url,
                "garment_image": garment_image_url,
                "category": category,
            }

        # Create prediction
        resp = await self._http.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "model": model_id,
                "input": prediction_input,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        prediction = resp.json()

        # If sync mode returned completed
        if prediction.get("status") == "succeeded":
            return self._extract_output_url(prediction)

        # Otherwise poll
        prediction_id = prediction["id"]
        return await self._poll_prediction(prediction_id, headers)

    async def _poll_prediction(
        self, prediction_id: str, headers: dict, max_wait: int = 180
    ) -> str:
        """Poll Replicate prediction until complete."""
        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        deadline = time.monotonic() + max_wait

        while time.monotonic() < deadline:
            resp = await self._http.get(poll_url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            prediction = resp.json()
            status = prediction.get("status")

            if status == "succeeded":
                return self._extract_output_url(prediction)
            elif status == "failed":
                error = prediction.get("error", "Unknown error")
                raise RuntimeError(f"Replicate prediction failed: {error}")
            elif status == "canceled":
                raise RuntimeError("Replicate prediction was canceled")

            # Still processing — wait and retry
            await asyncio.sleep(3)

        raise TimeoutError(f"Prediction {prediction_id} timed out after {max_wait}s")

    @staticmethod
    def _extract_output_url(prediction: dict) -> str:
        """Extract the result image URL from Replicate prediction output."""
        output = prediction.get("output")
        if isinstance(output, str):
            return output
        if isinstance(output, list) and output:
            return output[0] if isinstance(output[0], str) else str(output[0])
        raise ValueError(f"Unexpected Replicate output format: {output}")

    # ── Stub ─────────────────────────────────────────────────────────
    def _stub_synthesis(self, start: float, user_id: str, job_id: str) -> dict:
        elapsed = (time.monotonic() - start) * 1000
        logger.info("synthesis.stub_used", job_id=job_id)
        return {
            "photo_url": f"https://stub.supabase.co/storage/v1/object/public/tryon-results/{user_id}/{job_id}/tryon_photo.png",
            "processing_time_ms": elapsed,
            "model_used": "stub",
        }

    # ── Health ───────────────────────────────────────────────────────
    def get_circuit_states(self) -> dict:
        return {
            "idm_vton": str(self._breaker_primary.current_state),
            "flux_vton": str(self._breaker_fallback.current_state),
        }
