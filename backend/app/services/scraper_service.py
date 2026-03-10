"""
Universal garment scraper service.

Extracts product information from any clothing e-commerce website using a
layered extraction strategy:

  1. JSON-LD structured data  (schema.org Product — highest fidelity)
  2. Open Graph / meta tags   (og:title, og:image, etc.)
  3. Microdata attributes      (itemprop="name", itemprop="image", etc.)
  4. Generic HTML heuristics   (product cards, img tags, headings)

This makes it work across Shopify, WooCommerce, Magento, Squarespace,
custom builds, and virtually any site that renders product data in HTML.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from app.models.scraper import ScrapedGarment
from app.models.tryon import GarmentCategory

logger = structlog.get_logger("service.scraper")

# ── Category inference keywords ──────────────────────────────────────────
_UPPER_KEYWORDS = {
    "shirt", "t-shirt", "tee", "top", "blouse", "sweater", "hoodie",
    "jacket", "coat", "blazer", "cardigan", "vest", "polo", "henley",
    "tank", "pullover", "sweatshirt", "parka", "windbreaker", "cape",
    "crop top", "tunic", "jersey", "flannel",
}
_LOWER_KEYWORDS = {
    "pant", "jeans", "trouser", "short", "skirt", "legging", "jogger",
    "chino", "cargo", "bermuda", "capri", "culottes", "palazzo",
    "sweatpant", "trackpant",
}
_DRESS_KEYWORDS = {
    "dress", "gown", "romper", "jumpsuit", "overall", "maxi", "midi",
    "bodysuit", "playsuit", "kaftan", "kimono wrap dress", "saree", "sari",
}

# User-Agent to look like a normal browser
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Max garments to return per scrape to avoid massive payloads
_MAX_GARMENTS = 100


class ScraperService:
    """Stateless universal garment scraper."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client

    async def scrape_url(self, url: str) -> List[ScrapedGarment]:
        """Scrape garments from the given URL."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP(S) URLs are supported")

        domain = parsed.netloc.lower().removeprefix("www.")

        logger.info("scraper.fetching", url=url, domain=domain)

        resp = await self._http.get(
            url,
            headers=_HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        resp.raise_for_status()

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        garments: List[ScrapedGarment] = []

        # Layer 1: JSON-LD structured data
        garments.extend(self._extract_jsonld(soup, url, domain))

        # Layer 2: Open Graph / meta (for single-product pages)
        if not garments:
            og = self._extract_opengraph(soup, url, domain)
            if og:
                garments.append(og)

        # Layer 3: Microdata
        if not garments:
            garments.extend(self._extract_microdata(soup, url, domain))

        # Layer 4: Generic HTML heuristics (product cards)
        if not garments:
            garments.extend(self._extract_generic(soup, url, domain))

        # Deduplicate by image URL
        seen_images: set[str] = set()
        unique: List[ScrapedGarment] = []
        for g in garments:
            if g.image_url and g.image_url not in seen_images:
                seen_images.add(g.image_url)
                unique.append(g)
            elif not g.image_url:
                unique.append(g)

        result = unique[:_MAX_GARMENTS]
        logger.info("scraper.done", url=url, found=len(result))
        return result

    # ── Layer 1: JSON-LD ─────────────────────────────────────────────────

    def _extract_jsonld(
        self, soup: BeautifulSoup, base_url: str, domain: str
    ) -> List[ScrapedGarment]:
        garments: List[ScrapedGarment] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            self._walk_jsonld(data, base_url, domain, garments)
        return garments

    def _walk_jsonld(
        self,
        data,
        base_url: str,
        domain: str,
        out: List[ScrapedGarment],
    ):
        if isinstance(data, list):
            for item in data:
                self._walk_jsonld(item, base_url, domain, out)
            return

        if not isinstance(data, dict):
            return

        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""

        if schema_type in ("Product", "ClothingStore", "IndividualProduct"):
            g = self._product_from_jsonld(data, base_url, domain)
            if g:
                out.append(g)

        # ItemList / product collections
        if schema_type == "ItemList":
            for elem in data.get("itemListElement", []):
                item = elem.get("item", elem)
                self._walk_jsonld(item, base_url, domain, out)

        # Nested @graph
        if "@graph" in data:
            self._walk_jsonld(data["@graph"], base_url, domain, out)

    def _product_from_jsonld(
        self, data: dict, base_url: str, domain: str
    ) -> Optional[ScrapedGarment]:
        name = data.get("name", "")
        if not name:
            return None

        # Image — can be string, list, or object
        image = data.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        if isinstance(image, dict):
            image = image.get("url", image.get("contentUrl", ""))
        image = self._abs_url(image, base_url)

        description = data.get("description", "")
        brand_raw = data.get("brand", "")
        if isinstance(brand_raw, dict):
            brand_raw = brand_raw.get("name", "")

        # Price
        price = ""
        currency = ""
        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            price = str(offers.get("price", ""))
            currency = offers.get("priceCurrency", "")
            if not price:
                price = str(offers.get("lowPrice", ""))

        product_url = data.get("url", "")
        product_url = self._abs_url(product_url, base_url) or base_url

        return ScrapedGarment(
            name=str(name)[:200],
            brand=str(brand_raw)[:100],
            description=str(description)[:500],
            price=price,
            currency=currency,
            image_url=image,
            product_url=product_url,
            category=self._infer_category(name, description),
            source_domain=domain,
        )

    # ── Layer 2: Open Graph / Meta Tags ──────────────────────────────────

    def _extract_opengraph(
        self, soup: BeautifulSoup, base_url: str, domain: str
    ) -> Optional[ScrapedGarment]:
        og_type = self._meta(soup, "og:type")
        og_title = self._meta(soup, "og:title")
        og_image = self._meta(soup, "og:image")

        # Only extract if it looks like a product page
        if not og_title or not og_image:
            return None

        is_product = og_type in ("product", "product.item", "og:product")
        # Also check for price meta
        price = (
            self._meta(soup, "product:price:amount")
            or self._meta(soup, "og:price:amount")
            or ""
        )
        currency = (
            self._meta(soup, "product:price:currency")
            or self._meta(soup, "og:price:currency")
            or ""
        )

        description = self._meta(soup, "og:description") or ""
        og_url = self._meta(soup, "og:url") or base_url

        # If not explicitly a product and no price, skip on listing pages
        if not is_product and not price:
            # Still useful for single-product pages — check <title> for clues
            title_tag = soup.find("title")
            page_title = title_tag.get_text(strip=True) if title_tag else ""
            if not any(
                kw in page_title.lower()
                for kw in ("buy", "shop", "product", "price", "$", "£", "€")
            ):
                return None

        return ScrapedGarment(
            name=og_title[:200],
            brand=self._meta(soup, "og:site_name") or domain,
            description=description[:500],
            price=price,
            currency=currency,
            image_url=self._abs_url(og_image, base_url),
            product_url=og_url,
            category=self._infer_category(og_title, description),
            source_domain=domain,
        )

    # ── Layer 3: Microdata ───────────────────────────────────────────────

    def _extract_microdata(
        self, soup: BeautifulSoup, base_url: str, domain: str
    ) -> List[ScrapedGarment]:
        garments: List[ScrapedGarment] = []
        scopes = soup.find_all(
            attrs={"itemtype": re.compile(r"schema\.org/(Product|ClothingStore)", re.I)}
        )
        for scope in scopes:
            name_el = scope.find(attrs={"itemprop": "name"})
            img_el = scope.find(attrs={"itemprop": "image"})
            desc_el = scope.find(attrs={"itemprop": "description"})
            brand_el = scope.find(attrs={"itemprop": "brand"})
            price_el = scope.find(attrs={"itemprop": "price"})
            url_el = scope.find(attrs={"itemprop": "url"})

            name = self._text_or_attr(name_el, "content") if name_el else ""
            if not name:
                continue

            image = ""
            if img_el:
                image = (
                    img_el.get("src")
                    or img_el.get("content")
                    or img_el.get("href")
                    or ""
                )
            image = self._abs_url(str(image), base_url)

            garments.append(
                ScrapedGarment(
                    name=name[:200],
                    brand=(
                        self._text_or_attr(brand_el, "content") if brand_el else domain
                    )[:100],
                    description=(
                        self._text_or_attr(desc_el, "content") if desc_el else ""
                    )[:500],
                    price=(
                        self._text_or_attr(price_el, "content") if price_el else ""
                    ),
                    image_url=image,
                    product_url=(
                        self._abs_url(
                            self._text_or_attr(url_el, "href") if url_el else "",
                            base_url,
                        )
                        or base_url
                    ),
                    category=self._infer_category(name, ""),
                    source_domain=domain,
                )
            )
        return garments

    # ── Layer 4: Generic HTML Heuristics ─────────────────────────────────

    def _extract_generic(
        self, soup: BeautifulSoup, base_url: str, domain: str
    ) -> List[ScrapedGarment]:
        """
        Fallback: look for common product card patterns used across
        e-commerce platforms (Shopify, WooCommerce, Magento, etc.).
        """
        garments: List[ScrapedGarment] = []

        # Common product card selectors
        product_selectors = [
            "article.product-card",
            "div.product-card",
            "li.product",
            "div.product-item",
            "div.product-tile",
            "div.grid-product",
            "div.product-grid-item",
            "div[data-product]",
            "div[data-product-id]",
            "div.card--product",           # Shopify Dawn
            "product-card",                 # Custom elements
            "li.grid__item",                # Shopify
            "div.product-list-item",
            "div.collection-product",
            "li.product-item",              # Magento
            "div.woocommerce-product",      # WooCommerce
            "li.type-product",              # WooCommerce
        ]

        cards: List[Tag] = []
        for selector in product_selectors:
            cards.extend(soup.select(selector))
            if len(cards) >= 5:
                break

        # If selectors didn't work, find link+image combos
        if not cards:
            cards = self._find_product_cards_heuristic(soup)

        for card in cards[:_MAX_GARMENTS]:
            g = self._parse_product_card(card, base_url, domain)
            if g:
                garments.append(g)

        return garments

    def _find_product_cards_heuristic(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Heuristic: find container divs/lis that each contain both an <a>
        and an <img> — likely product cards.
        """
        candidates: List[Tag] = []
        # Look for grid-like containers
        for container in soup.find_all(["ul", "div"], class_=re.compile(
            r"(product|catalog|collection|grid|items|listing)", re.I
        )):
            children = container.find_all(["li", "div", "article"], recursive=False)
            if len(children) >= 2:
                # Check that children have images
                valid = [
                    c for c in children
                    if c.find("img") and c.find("a")
                ]
                if len(valid) >= 2:
                    candidates.extend(valid[:_MAX_GARMENTS])
                    break
        return candidates

    def _parse_product_card(
        self, card: Tag, base_url: str, domain: str
    ) -> Optional[ScrapedGarment]:
        """Extract garment info from a product card element."""
        # Image
        img = card.find("img")
        image_url = ""
        if img:
            image_url = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-srcset", "").split(",")[0].split(" ")[0]
                or img.get("data-lazy-src")
                or ""
            )
            image_url = str(image_url).strip()

        image_url = self._abs_url(image_url, base_url)

        # Skip tiny icons / UI elements
        if image_url and self._is_icon(img):
            return None

        # Name — from heading, link text, or img alt
        name = ""
        for tag in card.find_all(["h2", "h3", "h4", "p", "span", "a"]):
            cls = " ".join(tag.get("class", []))
            text = tag.get_text(strip=True)
            if re.search(r"(product.?name|product.?title|card.?title)", cls, re.I):
                name = text
                break
            if tag.name in ("h2", "h3", "h4") and text and len(text) < 200:
                name = text
                break

        if not name and img:
            name = img.get("alt", "")
        if not name:
            # Try first <a> with meaningful text
            link = card.find("a")
            if link:
                name = link.get_text(strip=True)

        name = str(name).strip()[:200]
        if not name or not image_url:
            return None

        # Product URL
        link = card.find("a", href=True)
        product_url = self._abs_url(str(link["href"]), base_url) if link else base_url

        # Price
        price = ""
        price_el = card.find(
            class_=re.compile(r"(price|amount|cost)", re.I)
        ) or card.find(attrs={"data-price": True})
        if price_el:
            price = price_el.get_text(strip=True)
            if not price:
                price = str(price_el.get("data-price", ""))

        return ScrapedGarment(
            name=name,
            brand=domain,
            description="",
            price=price,
            image_url=image_url,
            product_url=product_url,
            category=self._infer_category(name, ""),
            source_domain=domain,
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _meta(soup: BeautifulSoup, prop: str) -> str:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag:
            return str(tag.get("content", "")).strip()
        return ""

    @staticmethod
    def _text_or_attr(el: Tag, attr: str) -> str:
        val = el.get(attr)
        if val:
            return str(val).strip()
        return el.get_text(strip=True)

    @staticmethod
    def _abs_url(url: str, base: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("data:"):
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/") or not url.startswith("http"):
            return urljoin(base, url)
        return url

    @staticmethod
    def _is_icon(img: Optional[Tag]) -> bool:
        if not img:
            return False
        w = img.get("width")
        h = img.get("height")
        try:
            if w and int(w) < 50:
                return True
            if h and int(h) < 50:
                return True
        except (ValueError, TypeError):
            pass
        return False

    @staticmethod
    def _infer_category(name: str, description: str) -> GarmentCategory:
        text = f"{name} {description}".lower()
        tokens = set(re.findall(r"[a-z]+(?:-[a-z]+)*", text))

        if tokens & _DRESS_KEYWORDS:
            return GarmentCategory.DRESSES
        if tokens & _LOWER_KEYWORDS:
            return GarmentCategory.LOWER_BODY
        if tokens & _UPPER_KEYWORDS:
            return GarmentCategory.UPPER_BODY

        # Check partial matches for compound words
        for kw in _DRESS_KEYWORDS:
            if kw in text:
                return GarmentCategory.DRESSES
        for kw in _LOWER_KEYWORDS:
            if kw in text:
                return GarmentCategory.LOWER_BODY
        for kw in _UPPER_KEYWORDS:
            if kw in text:
                return GarmentCategory.UPPER_BODY

        return GarmentCategory.UPPER_BODY
