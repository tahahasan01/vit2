"""
Scraper schemas — request / response contracts for the universal garment scraper.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

from app.models.tryon import GarmentCategory


class ScrapeRequest(BaseModel):
    """POST /api/v1/scraper/scrape — scrape garments from any clothing URL."""

    url: HttpUrl = Field(..., description="Product or listing page URL to scrape")
    import_to_catalog: bool = Field(
        False,
        description="If True, automatically import scraped garments into the catalog",
    )


class ScrapedGarment(BaseModel):
    """A single garment extracted from a scraped page."""

    name: str = ""
    brand: str = ""
    description: str = ""
    price: str = ""
    currency: str = ""
    image_url: str = ""
    product_url: str = ""
    category: GarmentCategory = GarmentCategory.UPPER_BODY
    source_domain: str = ""


class ScrapeResponse(BaseModel):
    """Response from a scrape request."""

    url: str
    garments: List[ScrapedGarment] = []
    total: int = 0
    imported: int = 0
    errors: List[str] = []
