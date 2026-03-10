"""
AuthService — Supabase Auth wrapper with consent tracking.

Layer 5 of the pipeline: Privacy & Consent.
Before using VTO, the user must accept the AI processing consent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from app.config import Settings
from app.models.user import AuthResponse, ConsentPayload, UserProfile

logger = structlog.get_logger(__name__)


class AuthService:
    """Wraps Supabase GoTrue auth + consent tracking in Supabase DB."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._http = http_client
        self._auth_url = f"{settings.supabase.url}/auth/v1"
        self._rest_url = f"{settings.supabase.url}/rest/v1"
        self._anon_key = settings.supabase.anon_key
        self._service_key = settings.supabase.service_role_key

    def _anon_headers(self) -> dict:
        return {
            "apikey": self._anon_key,
            "Content-Type": "application/json",
        }

    def _service_headers(self) -> dict:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Content-Type": "application/json",
        }

    def _user_headers(self, token: str) -> dict:
        return {
            "apikey": self._anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Sign Up ──────────────────────────────────────────────────────
    async def sign_up(self, email: str, password: str) -> AuthResponse:
        if self._settings.use_stubs:
            return self._stub_auth_response(email)

        resp = await self._http.post(
            f"{self._auth_url}/signup",
            headers=self._anon_headers(),
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        user_id = data["user"]["id"]

        # Create user_profiles row
        await self._ensure_profile(user_id, email)

        return AuthResponse(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            user=UserProfile(
                id=user_id,
                email=email,
                consent_given=False,
                created_at=datetime.now(timezone.utc),
            ),
        )

    # ── Sign In ──────────────────────────────────────────────────────
    async def sign_in(self, email: str, password: str) -> AuthResponse:
        if self._settings.use_stubs:
            return self._stub_auth_response(email)

        resp = await self._http.post(
            f"{self._auth_url}/token?grant_type=password",
            headers=self._anon_headers(),
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        user_id = data["user"]["id"]

        profile = await self._get_profile(user_id)

        return AuthResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            user=profile
            or UserProfile(
                id=user_id,
                email=email,
                consent_given=False,
                created_at=datetime.now(timezone.utc),
            ),
        )

    # ── Get Current User ─────────────────────────────────────────────
    async def get_user(self, token: str) -> Optional[UserProfile]:
        if self._settings.use_stubs:
            return UserProfile(
                id="stub-user-id",
                email="stub@example.com",
                consent_given=True,
                consent_given_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )

        resp = await self._http.get(
            f"{self._auth_url}/user",
            headers=self._user_headers(token),
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        return await self._get_profile(data["id"])

    # ── Sign Out ─────────────────────────────────────────────────────
    async def sign_out(self, token: str) -> None:
        if self._settings.use_stubs:
            return

        await self._http.post(
            f"{self._auth_url}/logout",
            headers=self._user_headers(token),
        )

    # ── Consent ──────────────────────────────────────────────────────
    async def record_consent(
        self, user_id: str, consent: ConsentPayload
    ) -> UserProfile:
        """Record user's AI-processing consent — GDPR Layer 5."""
        now = datetime.now(timezone.utc).isoformat()

        if self._settings.use_stubs:
            return UserProfile(
                id=user_id,
                email="stub@example.com",
                consent_given=consent.consent_given,
                consent_given_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )

        await self._http.patch(
            f"{self._rest_url}/user_profiles?id=eq.{user_id}",
            headers=self._service_headers(),
            json={
                "consent_given": consent.consent_given,
                "privacy_acknowledged": consent.privacy_acknowledged,
                "consent_given_at": now,
            },
        )
        logger.info("auth.consent_recorded", user_id=user_id, consent=consent.consent_given)

        profile = await self._get_profile(user_id)
        return profile or UserProfile(
            id=user_id,
            email="",
            consent_given=consent.consent_given,
            consent_given_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

    async def check_consent(self, user_id: str) -> bool:
        """Check if user has given consent — gate VTO submissions behind this."""
        if self._settings.use_stubs:
            return True
        profile = await self._get_profile(user_id)
        return profile.consent_given if profile else False

    # ── Private helpers ──────────────────────────────────────────────
    async def _ensure_profile(self, user_id: str, email: str) -> None:
        """Create user_profiles row if it doesn't exist."""
        if self._settings.use_stubs:
            return

        await self._http.post(
            f"{self._rest_url}/user_profiles",
            headers={
                **self._service_headers(),
                "Prefer": "resolution=ignore-duplicates",
            },
            json={
                "id": user_id,
                "email": email,
                "consent_given": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _get_profile(self, user_id: str) -> Optional[UserProfile]:
        if self._settings.use_stubs:
            return None

        resp = await self._http.get(
            f"{self._rest_url}/user_profiles?id=eq.{user_id}&select=*",
            headers=self._service_headers(),
        )
        if resp.status_code != 200:
            return None

        rows = resp.json()
        if not rows:
            return None

        row = rows[0]
        return UserProfile(
            id=row["id"],
            email=row.get("email", ""),
            consent_given=row.get("consent_given", False),
            consent_given_at=row.get("consent_given_at"),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
        )

    # ── Stubs ────────────────────────────────────────────────────────
    @staticmethod
    def _stub_auth_response(email: str) -> AuthResponse:
        return AuthResponse(
            access_token="stub-jwt-token",
            refresh_token="stub-refresh-token",
            user=UserProfile(
                id="stub-user-id",
                email=email,
                consent_given=False,
                created_at=datetime.now(timezone.utc),
            ),
        )
