"""
Garment catalog schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.tryon import GarmentCategory


class GarmentUpload(BaseModel):
    """POST /api/v1/garments — admin uploads a new garment to the catalog."""

    name: str = Field(..., min_length=1, max_length=200)
    category: GarmentCategory
    brand: str = Field("", max_length=100)
    description: str = Field("", max_length=500)
    # image file is sent as multipart, not in JSON body


class Garment(BaseModel):
    """Garment catalog item returned to the frontend."""

    id: str
    name: str
    category: GarmentCategory
    brand: str = ""
    description: str = ""
    image_url: str = Field(..., description="Full-size garment product image")
    thumbnail_url: str = Field(..., description="Thumbnail for catalog grid")
    created_at: datetime


class GarmentCatalog(BaseModel):
    """GET /api/v1/garments"""

    garments: List[Garment] = []
    total: int = 0
    categories: List[str] = [c.value for c in GarmentCategory]
