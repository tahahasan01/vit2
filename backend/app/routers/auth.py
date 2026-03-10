"""
Auth routes — signup, login, logout, consent.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.models.user import (
    AuthResponse,
    ConsentPayload,
    LoginRequest,
    SignUpRequest,
    UserProfile,
)
from app.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(request: Request):
    return request.app.state.auth_service


# ── Sign Up ──────────────────────────────────────────────────────────
@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignUpRequest, request: Request):
    svc = _auth_service(request)
    try:
        return await svc.sign_up(body.email, body.password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Login ────────────────────────────────────────────────────────────
@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request):
    svc = _auth_service(request)
    try:
        return await svc.sign_in(body.email, body.password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# ── Logout ───────────────────────────────────────────────────────────
@router.post("/logout")
async def logout(request: Request, user: UserProfile = Depends(get_current_user)):
    svc = _auth_service(request)
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    await svc.sign_out(token)
    return {"message": "Logged out"}


# ── Get current user ─────────────────────────────────────────────────
@router.get("/me", response_model=UserProfile)
async def me(user: UserProfile = Depends(get_current_user)):
    return user


# ── Consent (Layer 5: Privacy & Consent) ─────────────────────────────
@router.post("/consent", response_model=UserProfile)
async def record_consent(
    body: ConsentPayload,
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    """
    Record user's AI-processing consent — REQUIRED before first VTO use.
    The user is notified that they are interacting with generative AI
    and must confirm understanding of the privacy policy.
    """
    if not body.consent_given or not body.privacy_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="Both consent_given and privacy_acknowledged must be true.",
        )
    svc = _auth_service(request)
    return await svc.record_consent(user.id, body)
