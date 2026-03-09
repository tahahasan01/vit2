"""
Garments routes — browse catalog, upload garments.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.middleware.auth_middleware import get_current_user
from app.models.garment import Garment, GarmentCatalog
from app.models.tryon import GarmentCategory
from app.models.user import UserProfile

logger = structlog.get_logger("router.garments")
router = APIRouter(prefix="/garments", tags=["garments"])


# ── List Catalog ─────────────────────────────────────────────────────
@router.get("", response_model=GarmentCatalog)
async def list_garments(
    request: Request,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Browse the garment catalog. Public endpoint — no auth required.
    """
    settings = request.app.state.settings

    if settings.use_stubs:
        return _stub_catalog()

    http: httpx.AsyncClient = request.app.state.http_client
    url = (
        f"{settings.supabase.url}/rest/v1/garments"
        f"?select=*&order=created_at.desc&limit={limit}&offset={offset}"
    )
    if category:
        url += f"&category=eq.{category}"

    resp = await http.get(
        url,
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )

    if resp.status_code != 200:
        return GarmentCatalog(garments=[], total=0)

    rows = resp.json()
    garments = [
        Garment(
            id=r["id"],
            name=r["name"],
            category=GarmentCategory(r.get("category", "upper_body")),
            brand=r.get("brand", ""),
            description=r.get("description", ""),
            image_url=r["image_url"],
            thumbnail_url=r.get("thumbnail_url", r["image_url"]),
            created_at=r.get("created_at", datetime.now(timezone.utc)),
        )
        for r in rows
    ]

    return GarmentCatalog(garments=garments, total=len(garments))


# ── Get Single Garment ───────────────────────────────────────────────
@router.get("/{garment_id}", response_model=Garment)
async def get_garment(garment_id: str, request: Request):
    settings = request.app.state.settings

    if settings.use_stubs:
        return _stub_garment(garment_id)

    http: httpx.AsyncClient = request.app.state.http_client
    resp = await http.get(
        f"{settings.supabase.url}/rest/v1/garments?id=eq.{garment_id}&select=*",
        headers={
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        },
        timeout=10.0,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch garment")

    rows = resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Garment not found")

    r = rows[0]
    return Garment(
        id=r["id"],
        name=r["name"],
        category=GarmentCategory(r.get("category", "upper_body")),
        brand=r.get("brand", ""),
        description=r.get("description", ""),
        image_url=r["image_url"],
        thumbnail_url=r.get("thumbnail_url", r["image_url"]),
        created_at=r.get("created_at", datetime.now(timezone.utc)),
    )


# ── Upload Garment (Admin) ──────────────────────────────────────────
@router.post("", response_model=Garment, status_code=201)
async def upload_garment(
    request: Request,
    image: UploadFile = File(..., description="Garment product image"),
    name: str = Form(...),
    category: str = Form("upper_body"),
    brand: str = Form(""),
    description: str = Form(""),
    user: UserProfile = Depends(get_current_user),
):
    """Upload a new garment to the catalog."""
    settings = request.app.state.settings
    storage = request.app.state.storage_service

    try:
        cat = GarmentCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    garment_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    # Upload image to Supabase Storage
    image_bytes = await image.read()
    image_path = f"{garment_id}/image.jpg"
    thumbnail_path = f"{garment_id}/thumbnail.jpg"

    image_url = await storage.upload_file(
        "garments", image_path, image_bytes,
        content_type=image.content_type or "image/jpeg",
    )

    # For now, thumbnail = same as image (can add resize later)
    thumbnail_url = image_url

    # Insert into Supabase DB
    if not settings.use_stubs:
        http: httpx.AsyncClient = request.app.state.http_client
        await http.post(
            f"{settings.supabase.url}/rest/v1/garments",
            headers={
                "apikey": settings.supabase.service_role_key,
                "Authorization": f"Bearer {settings.supabase.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "id": garment_id,
                "name": name,
                "category": cat.value,
                "brand": brand,
                "description": description,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "created_at": now.isoformat(),
            },
            timeout=10.0,
        )

    logger.info("garments.uploaded", garment_id=garment_id, name=name)

    return Garment(
        id=garment_id,
        name=name,
        category=cat,
        brand=brand,
        description=description,
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        created_at=now,
    )


# ── Stubs ────────────────────────────────────────────────────────────
def _stub_catalog() -> GarmentCatalog:
    now = datetime.now(timezone.utc)
    base = "https://stub.supabase.co/storage/v1/object/public/garments"
    return GarmentCatalog(
        garments=[
            Garment(id="g1", name="Classic White T-Shirt", category=GarmentCategory.UPPER_BODY, brand="The Dirty Laundry", description="Essential cotton crew neck", image_url=f"{base}/g1/image.jpg", thumbnail_url=f"{base}/g1/image.jpg", created_at=now),
            Garment(id="g2", name="Black Slim Jeans", category=GarmentCategory.LOWER_BODY, brand="The Dirty Laundry", description="Stretch denim slim fit", image_url=f"{base}/g2/image.jpg", thumbnail_url=f"{base}/g2/image.jpg", created_at=now),
            Garment(id="g3", name="Navy Blazer", category=GarmentCategory.UPPER_BODY, brand="The Dirty Laundry", description="Structured wool blend blazer", image_url=f"{base}/g3/image.jpg", thumbnail_url=f"{base}/g3/image.jpg", created_at=now),
            Garment(id="g4", name="Silk Wrap Dress", category=GarmentCategory.DRESSES, brand="The Dirty Laundry", description="Flowing silk midi dress", image_url=f"{base}/g4/image.jpg", thumbnail_url=f"{base}/g4/image.jpg", created_at=now),
            Garment(id="g5", name="Leather Jacket", category=GarmentCategory.UPPER_BODY, brand="The Dirty Laundry", description="Genuine leather moto jacket", image_url=f"{base}/g5/image.jpg", thumbnail_url=f"{base}/g5/image.jpg", created_at=now),
            Garment(id="g6", name="Wool Overcoat", category=GarmentCategory.UPPER_BODY, brand="The Dirty Laundry", description="Double-breasted wool overcoat", image_url=f"{base}/g6/image.jpg", thumbnail_url=f"{base}/g6/image.jpg", created_at=now),
        ],
        total=6,
    )


def _stub_garment(garment_id: str) -> Garment:
    now = datetime.now(timezone.utc)
    base = "https://stub.supabase.co/storage/v1/object/public/garments"
    return Garment(
        id=garment_id,
        name="Stub Garment",
        category=GarmentCategory.UPPER_BODY,
        brand="The Dirty Laundry",
        description="Stub garment for development",
        image_url=f"{base}/{garment_id}/image.jpg",
        thumbnail_url=f"{base}/{garment_id}/image.jpg",
        created_at=now,
    )
