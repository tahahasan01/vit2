"""
StorageService — Supabase Storage wrapper.

CRITICAL: Every external API result is downloaded and re-uploaded to
Supabase before any URL is returned to the frontend.
This is the "snapshot-first" architecture — we NEVER rely on ephemeral
external URLs as the source of truth.
"""
from __future__ import annotations

import io
import uuid
from typing import Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings

logger = structlog.get_logger(__name__)


class StorageService:
    """Manages all asset storage via Supabase Storage API."""

    REQUIRED_BUCKETS = ["avatars", "garments", "tryon-results", "user-uploads"]

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._http = http_client
        self._base_url = f"{settings.supabase.url}/storage/v1"
        self._headers = {
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        }

    # ── Lifecycle ────────────────────────────────────────────────────
    async def initialize_buckets(self) -> None:
        """Create required buckets if they don't already exist."""
        if self._settings.use_stubs:
            logger.info("storage.stubs_enabled", msg="Skipping bucket init")
            return

        for bucket_name in self.REQUIRED_BUCKETS:
            try:
                resp = await self._http.post(
                    f"{self._base_url}/bucket",
                    headers=self._headers,
                    json={
                        "id": bucket_name,
                        "name": bucket_name,
                        "public": bucket_name in ("garments",),
                    },
                )
                if resp.status_code == 200:
                    logger.info("storage.bucket_created", bucket=bucket_name)
                elif resp.status_code == 409:
                    logger.debug("storage.bucket_exists", bucket=bucket_name)
                else:
                    logger.warning(
                        "storage.bucket_create_failed",
                        bucket=bucket_name,
                        status=resp.status_code,
                        body=resp.text,
                    )
            except Exception as exc:
                logger.error(
                    "storage.bucket_init_error",
                    bucket=bucket_name,
                    error=str(exc),
                )

    # ── Upload ───────────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def upload_file(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to Supabase Storage. Returns the permanent URL."""
        if self._settings.use_stubs:
            fake_url = f"https://stub.supabase.co/storage/v1/object/public/{bucket}/{path}"
            logger.info("storage.stub_upload", bucket=bucket, path=path)
            return fake_url

        resp = await self._http.post(
            f"{self._base_url}/object/{bucket}/{path}",
            headers={
                **self._headers,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            content=data,
        )
        resp.raise_for_status()
        logger.info("storage.uploaded", bucket=bucket, path=path, size=len(data))
        return self.get_public_url(bucket, path)

    # ── Snapshot external URL → Supabase ────────────────────────────
    async def snapshot_external_url(
        self,
        external_url: str,
        bucket: str,
        path: str,
        content_type: str = "image/png",
    ) -> str:
        """
        Download from an ephemeral external URL and re-upload to Supabase.
        This is the CRITICAL path — ensures we own all assets.
        """
        if self._settings.use_stubs:
            return f"https://stub.supabase.co/storage/v1/object/public/{bucket}/{path}"

        logger.info(
            "storage.snapshot_start",
            source=external_url[:80],
            target=f"{bucket}/{path}",
        )
        resp = await self._http.get(external_url, timeout=60.0)
        resp.raise_for_status()
        data = resp.content

        return await self.upload_file(bucket, path, data, content_type)

    # ── Download ─────────────────────────────────────────────────────
    async def download_file(self, bucket: str, path: str) -> bytes:
        if self._settings.use_stubs:
            return b""

        resp = await self._http.get(
            f"{self._base_url}/object/{bucket}/{path}",
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.content

    # ── URL helpers ──────────────────────────────────────────────────
    def get_public_url(self, bucket: str, path: str) -> str:
        return f"{self._settings.supabase.url}/storage/v1/object/public/{bucket}/{path}"

    async def get_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str:
        if self._settings.use_stubs:
            return self.get_public_url(bucket, path) + "?token=stub"

        resp = await self._http.post(
            f"{self._base_url}/object/sign/{bucket}/{path}",
            headers=self._headers,
            json={"expiresIn": expires_in},
        )
        resp.raise_for_status()
        data = resp.json()
        return f"{self._settings.supabase.url}/storage/v1{data['signedURL']}"

    # ── Delete ───────────────────────────────────────────────────────
    async def delete_file(self, bucket: str, path: str) -> None:
        if self._settings.use_stubs:
            return

        await self._http.delete(
            f"{self._base_url}/object/{bucket}/{path}",
            headers=self._headers,
        )
        logger.info("storage.deleted", bucket=bucket, path=path)

    # ── List ─────────────────────────────────────────────────────────
    async def list_files(
        self, bucket: str, prefix: str = ""
    ) -> list[dict]:
        if self._settings.use_stubs:
            return []

        resp = await self._http.post(
            f"{self._base_url}/object/list/{bucket}",
            headers=self._headers,
            json={"prefix": prefix, "limit": 1000},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Utility ──────────────────────────────────────────────────────
    @staticmethod
    def generate_path(user_id: str, job_id: str, filename: str) -> str:
        return f"{user_id}/{job_id}/{filename}"

    @staticmethod
    def generate_unique_name(extension: str = "png") -> str:
        return f"{uuid.uuid4().hex}.{extension}"
