"""
Layer 1 — Body Estimation Service

Pipeline: User photos → MediaPipe pose validation → HMR 2.0 (SMPL mesh) → BodyEstimation result.

- MediaPipe runs locally on CPU for fast pose validation (reject bad photos)
- HMR 2.0 runs on HuggingFace Spaces (free) for full SMPL body mesh extraction
- In stub mode: returns pre-computed default body parameters
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.utils.circuit_breaker import create_breaker

logger = structlog.get_logger(__name__)


@dataclass
class BodyLandmarks:
    """Simplified pose landmarks from MediaPipe."""
    landmarks: List[Dict[str, float]] = field(default_factory=list)
    confidence: float = 0.0
    is_standing: bool = False
    is_full_body_visible: bool = False


@dataclass
class BodyEstimation:
    """Result of Layer 1 — everything needed for Layer 2 & 3."""
    # SMPL parameters (from HMR 2.0)
    smpl_body_pose: Optional[List[float]] = None   # 69 floats (23 joints × 3)
    smpl_betas: Optional[List[float]] = None        # 10 shape coefficients
    smpl_global_orient: Optional[List[float]] = None  # 3 floats
    # Body measurements estimate
    estimated_height_cm: float = 170.0
    estimated_build: str = "average"  # slim / average / athletic
    # Validation
    pose_confidence: float = 0.0
    is_valid: bool = False
    validation_error: Optional[str] = None
    # Raw mesh (if available)
    mesh_vertices: Optional[Any] = None
    processing_time_ms: float = 0.0


class BodyEstimationService:
    """
    Layer 1: Input & Body Estimation.
    
    Uses MediaPipe for fast local pose validation, then HMR 2.0
    on HuggingFace Spaces for full SMPL mesh extraction.
    """

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._http = http_client
        self._hmr_url = settings.pipeline.hmr_space_url
        self._breaker = create_breaker("hmr_body_estimation", fail_max=5, reset_timeout=120)

    # ── Main entry point ─────────────────────────────────────────────
    async def estimate_body(
        self,
        selfie_bytes: bytes,
        fullbody_bytes: bytes,
    ) -> BodyEstimation:
        """
        Full Layer 1 pipeline:
        1. Validate poses via MediaPipe (local, CPU)
        2. Extract SMPL mesh via HMR 2.0 (HuggingFace Space)
        """
        start = time.monotonic()

        if self._settings.use_stubs:
            return self._stub_estimation(start)

        # Step 1: Local pose validation
        validation = await self._validate_pose(fullbody_bytes)
        if not validation.is_full_body_visible:
            return BodyEstimation(
                is_valid=False,
                validation_error="Full body not visible in the photo. Please upload a clear full-body standing photo.",
                processing_time_ms=(time.monotonic() - start) * 1000,
            )
        if not validation.is_standing:
            return BodyEstimation(
                is_valid=False,
                validation_error="Please upload a photo where you are standing upright.",
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

        # Step 2: HMR 2.0 — SMPL mesh extraction
        try:
            smpl_result = await self._run_hmr(fullbody_bytes)
        except Exception as exc:
            logger.warning("body_estimation.hmr_failed", error=str(exc))
            # Graceful degradation: return valid but without SMPL params
            # VTO can still work with just the photo
            return BodyEstimation(
                is_valid=True,
                validation_error=None,
                pose_confidence=validation.confidence,
                estimated_height_cm=170.0,
                estimated_build="average",
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

        elapsed = (time.monotonic() - start) * 1000
        logger.info("body_estimation.complete", time_ms=elapsed)

        return BodyEstimation(
            smpl_body_pose=smpl_result.get("body_pose"),
            smpl_betas=smpl_result.get("betas"),
            smpl_global_orient=smpl_result.get("global_orient"),
            estimated_height_cm=smpl_result.get("estimated_height", 170.0),
            estimated_build=smpl_result.get("build", "average"),
            pose_confidence=validation.confidence,
            is_valid=True,
            processing_time_ms=elapsed,
        )

    # ── MediaPipe Pose Validation (local, CPU) ───────────────────────
    async def _validate_pose(self, image_bytes: bytes) -> BodyLandmarks:
        """
        Run MediaPipe Pose on the image to validate:
        - Full body is visible (all major landmarks detected)
        - Person is roughly standing (hip-knee-ankle alignment)
        """
        try:
            import mediapipe as mp
            import numpy as np
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)

            mp_pose = mp.solutions.pose
            with mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.5,
            ) as pose:
                results = pose.process(img_array)

            if not results.pose_landmarks:
                return BodyLandmarks(confidence=0.0, is_standing=False, is_full_body_visible=False)

            landmarks = results.pose_landmarks.landmark
            landmark_list = [
                {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                for lm in landmarks
            ]

            # Check key body points are visible
            key_indices = [0, 11, 12, 23, 24, 25, 26, 27, 28]  # nose, shoulders, hips, knees, ankles
            visible_count = sum(
                1 for idx in key_indices if landmarks[idx].visibility > 0.5
            )
            is_full_body = visible_count >= 7

            # Check standing posture (hips above knees above ankles in y-axis)
            left_hip_y = landmarks[23].y
            left_knee_y = landmarks[25].y
            left_ankle_y = landmarks[27].y
            is_standing = left_hip_y < left_knee_y < left_ankle_y

            avg_visibility = sum(lm.visibility for lm in landmarks) / len(landmarks)

            return BodyLandmarks(
                landmarks=landmark_list,
                confidence=avg_visibility,
                is_standing=is_standing,
                is_full_body_visible=is_full_body,
            )

        except ImportError:
            logger.warning("body_estimation.mediapipe_not_installed")
            # If mediapipe not installed, skip validation
            return BodyLandmarks(confidence=0.8, is_standing=True, is_full_body_visible=True)
        except Exception as exc:
            logger.warning("body_estimation.validation_error", error=str(exc))
            # Don't block the pipeline on validation failure
            return BodyLandmarks(confidence=0.5, is_standing=True, is_full_body_visible=True)

    # ── HMR 2.0 on HuggingFace Spaces ───────────────────────────────
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def _run_hmr(self, image_bytes: bytes) -> Dict:
        """
        Call HMR 2.0 HuggingFace Space API for SMPL mesh extraction.
        Uses the Gradio API protocol.
        """
        try:
            # HuggingFace Spaces Gradio API
            # POST to /api/predict or /run/predict
            import base64

            img_b64 = base64.b64encode(image_bytes).decode("utf-8")

            resp = await self._http.post(
                f"{self._hmr_url}/api/predict",
                json={
                    "data": [f"data:image/jpeg;base64,{img_b64}"],
                    "fn_index": 0,
                },
                timeout=120.0,
            )

            if resp.status_code == 200:
                result = resp.json()
                # Parse HMR output — contains SMPL params
                return self._parse_hmr_output(result)
            else:
                logger.warning(
                    "body_estimation.hmr_api_error",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return self._default_smpl_params()

        except Exception as exc:
            logger.error("body_estimation.hmr_exception", error=str(exc))
            return self._default_smpl_params()

    def _parse_hmr_output(self, result: Dict) -> Dict:
        """Parse HMR 2.0 Gradio API response into our format."""
        try:
            data = result.get("data", [])
            if data and isinstance(data[0], dict):
                return {
                    "body_pose": data[0].get("body_pose", [0.0] * 69),
                    "betas": data[0].get("betas", [0.0] * 10),
                    "global_orient": data[0].get("global_orient", [0.0, 0.0, 0.0]),
                    "estimated_height": 170.0,
                    "build": "average",
                }
        except Exception:
            pass
        return self._default_smpl_params()

    @staticmethod
    def _default_smpl_params() -> Dict:
        return {
            "body_pose": [0.0] * 69,
            "betas": [0.0] * 10,
            "global_orient": [0.0, 0.0, 0.0],
            "estimated_height": 170.0,
            "build": "average",
        }

    def _stub_estimation(self, start: float) -> BodyEstimation:
        """Return pre-computed default body for development."""
        elapsed = (time.monotonic() - start) * 1000
        logger.info("body_estimation.stub_used")
        return BodyEstimation(
            smpl_body_pose=[0.0] * 69,
            smpl_betas=[0.0] * 10,
            smpl_global_orient=[0.0, 0.0, 0.0],
            estimated_height_cm=170.0,
            estimated_build="average",
            pose_confidence=0.95,
            is_valid=True,
            processing_time_ms=elapsed,
        )
