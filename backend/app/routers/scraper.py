"""
Scraper routes — scrape garments from any clothing website URL.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.auth_middleware import get_current_user
from app.models.garment import Garment
from app.models.scraper import ScrapedGarment, ScrapeRequest, ScrapeResponse
from app.models.tryon import GarmentCategory
from app.models.user import UserProfile
from app.services.scraper_service import ScraperService

logger = structlog.get_logger("router.scraper")
router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_garments(
    body: ScrapeRequest,
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    """
    Scrape garments from any clothing website URL.

    Supports product pages and listing/collection pages from virtually
    any e-commerce platform (Shopify, WooCommerce, Magento, custom, etc.)
    via multi-layer extraction (JSON-LD → Open Graph → Microdata → HTML heuristics).
    """
    settings = request.app.state.settings
    http: httpx.AsyncClient = request.app.state.http_client
    scraper = ScraperService(http)

    url_str = str(body.url)
    errors: list[str] = []

    try:
        garments = await scraper.scrape_url(url_str)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Target site returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the target site: {type(exc).__name__}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    imported = 0

    # Optionally import scraped garments into the catalog
    if body.import_to_catalog and garments and not settings.use_stubs:
        imported = await _import_garments(
            garments, settings, http, request, errors
        )

    logger.info(
        "scraper.complete",
        url=url_str,
        found=len(garments),
        imported=imported,
    )

    return ScrapeResponse(
        url=url_str,
        garments=garments,
        total=len(garments),
        imported=imported,
        errors=errors,
    )


async def _import_garments(
    garments: list[ScrapedGarment],
    settings,
    http: httpx.AsyncClient,
    request: Request,
    errors: list[str],
) -> int:
    """Download garment images and insert into Supabase catalog."""
    storage = request.app.state.storage_service
    imported = 0

    for g in garments:
        if not g.image_url:
            continue

        garment_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        try:
            # Download the garment image
            img_resp = await http.get(
                g.image_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15.0,
                follow_redirects=True,
            )
            img_resp.raise_for_status()
            image_bytes = img_resp.content
            content_type = img_resp.headers.get("content-type", "image/jpeg")

            # Upload to Supabase storage
            ext = "jpg"
            if "png" in content_type:
                ext = "png"
            elif "webp" in content_type:
                ext = "webp"

            image_path = f"{garment_id}/image.{ext}"
            image_url = await storage.upload_file(
                "garments", image_path, image_bytes, content_type=content_type,
            )

            # Insert into Supabase DB
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
                    "name": g.name or "Unnamed Garment",
                    "category": g.category.value,
                    "brand": g.brand or g.source_domain,
                    "description": g.description[:500] if g.description else "",
                    "image_url": image_url,
                    "thumbnail_url": image_url,
                    "created_at": now.isoformat(),
                },
                timeout=10.0,
            )

            imported += 1
            logger.info(
                "scraper.imported_garment",
                garment_id=garment_id,
                name=g.name,
            )

        except Exception as exc:
            errors.append(f"Failed to import '{g.name}': {type(exc).__name__}")
            logger.warning(
                "scraper.import_failed",
                name=g.name,
                error=str(exc)[:200],
            )

    return imported
