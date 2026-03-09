"""
Auth middleware — JWT extraction + Supabase verification.

Used as a FastAPI dependency: `user = Depends(get_current_user)`
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request

from app.models.user import UserProfile


async def get_current_user(request: Request) -> UserProfile:
    """
    FastAPI dependency — extracts Bearer token from Authorization header
    and verifies it against Supabase Auth.

    In stub mode: returns a test user without hitting any API.
    """
    settings = request.app.state.settings

    # ── Stub mode ────────────────────────────────────────────────
    if settings.use_stubs:
        return UserProfile(
            id="stub-user-id",
            email="dev@thedirtylaundry.com",
            consent_given=True,
            consent_given_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

    # ── Extract token ────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )
    token = auth_header[7:]  # strip "Bearer "

    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    # ── Verify with Supabase ─────────────────────────────────────
    auth_service = request.app.state.auth_service
    user = await auth_service.get_user(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return user
