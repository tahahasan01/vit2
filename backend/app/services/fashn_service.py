"""
Fashn.ai Service — Primary VTO + Video Provider

Fashn.ai offers:
  - tryon-v1.6: Virtual try-on (garment synthesis onto human photo)
  - image-to-video: Generate 360° orbital video from try-on result

This is the PRIMARY provider. Replicate (IDM-VTON, Flux-VTON) is the fallback.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import structlog

from app.config import Settings
from app.utils.circuit_breaker import create_breaker

logger = structlog.get_logger(__name__)


class FashnService:
    """
    Fashn.ai integration for virtual try-on and image-to-video.

    API docs: https://docs.fashn.ai
    """

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._http = http_client
        self._api_key = settings.fashn.api_key
        self._base_url = settings.fashn.base_url.rstrip("/")
        self._tryon_model = settings.fashn.tryon_model
        self._video_model = settings.fashn.video_model

        self._breaker_tryon = create_breaker(
            "fashn_tryon", fail_max=3, reset_timeout=60
        )
        self._breaker_video = create_breaker(
            "fashn_video", fail_max=3, reset_timeout=120
        )

        logger.info(
            "fashn.initialized",
            base_url=self._base_url,
            tryon_model=self._tryon_model,
            video_model=self._video_model,
        )

    # ── Headers ──────────────────────────────────────────────────────
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    # ── Category mapping ─────────────────────────────────────────────
    @staticmethod
    def _map_category(category: str) -> str:
        """Map our category names to Fashn API category values."""
        mapping = {
            "upper_body": "tops",
            "lower_body": "bottoms",
            "dresses": "one-pieces",
        }
        return mapping.get(category, "tops")

    # ── Try-On ───────────────────────────────────────────────────────
    async def try_on(
        self,
        human_image_url: str,
        garment_image_url: str,
        category: str = "upper_body",
    ) -> str:
        """
        Run virtual try-on via Fashn tryon-v1.6.

        Returns: ephemeral result image URL (caller must snapshot to storage).
        """
        fashn_category = self._map_category(category)

        payload = {
            "model_id": self._tryon_model,
            "model_image": human_image_url,
            "garment_image": garment_image_url,
            "category": fashn_category,
        }

        logger.info(
            "fashn.tryon.starting",
            category=fashn_category,
            model=self._tryon_model,
        )

        # Submit the run
        resp = await self._http.post(
            f"{self._base_url}/v1/run",
            headers=self._headers(),
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        run_id = data.get("id")

        if not run_id:
            raise RuntimeError(f"Fashn tryon: no run ID in response: {data}")

        # Poll for result
        result_url = await self._poll(run_id, max_wait=120)

        logger.info("fashn.tryon.complete", run_id=run_id)
        return result_url

    # ── Image-to-Video ───────────────────────────────────────────────
    async def image_to_video(self, image_url: str) -> str:
        """
        Generate 360° orbital video from a try-on image via Fashn image-to-video.

        Returns: ephemeral video URL (caller must snapshot to storage).
        """
        payload = {
            "model_id": self._video_model,
            "input_image": image_url,
        }

        logger.info("fashn.video.starting", model=self._video_model)

        resp = await self._http.post(
            f"{self._base_url}/v1/run",
            headers=self._headers(),
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        run_id = data.get("id")

        if not run_id:
            raise RuntimeError(f"Fashn video: no run ID in response: {data}")

        result_url = await self._poll(run_id, max_wait=180)

        logger.info("fashn.video.complete", run_id=run_id)
        return result_url

    # ── Poll ─────────────────────────────────────────────────────────
    async def _poll(self, run_id: str, max_wait: int = 120) -> str:
        """Poll Fashn API until the run completes."""
        poll_url = f"{self._base_url}/v1/run/{run_id}"
        deadline = time.monotonic() + max_wait

        while time.monotonic() < deadline:
            resp = await self._http.get(
                poll_url,
                headers=self._headers(),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "").lower()

            if status == "completed":
                output = data.get("output")
                if isinstance(output, str):
                    return output
                if isinstance(output, list) and output:
                    return output[0]
                if isinstance(output, dict):
                    return output.get("url") or output.get("image") or output.get("video", "")
                raise RuntimeError(f"Fashn run {run_id}: unexpected output format: {output}")

            if status in ("failed", "error", "cancelled"):
                error = data.get("error") or data.get("message") or "Unknown error"
                raise RuntimeError(f"Fashn run {run_id} {status}: {error}")

            await asyncio.sleep(3)

        raise TimeoutError(f"Fashn run {run_id} timed out after {max_wait}s")

    # ── Health ───────────────────────────────────────────────────────
    def get_circuit_states(self) -> dict:
        return {
            "fashn_tryon": str(self._breaker_tryon.current_state),
            "fashn_video": str(self._breaker_video.current_state),
        }
