"""Products a website describes in its structured data (schema.org JSON-LD, which Shopify, WooCommerce and most
store themes publish): their name, price, rating and reviews as facts, and their photos as images to show.

Facts are read, never written by a model, so the critic can hold an on-screen price or quote to them. Photos are
downloaded from public addresses only, capped in size and re-encoded before anything else opens them.
"""

from __future__ import annotations

import io
import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from PIL import Image

# The page's own JSON-LD, parsed in the browser: every Product (or ProductGroup), including those in an @graph.
PRODUCTS_JS = """() => {
  const found = [];
  const visit = node => {
    if (Array.isArray(node)) return node.forEach(visit);
    if (!node || typeof node !== 'object') return;
    const type = [].concat(node['@type'] || []);
    if (type.includes('Product') || type.includes('ProductGroup')) found.push(node);
    if (node['@graph']) visit(node['@graph']);
  };
  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    try { visit(JSON.parse(script.textContent)); } catch (e) {}
  }
  return found.slice(0, 5);
}"""
MAX_PRODUCTS = 5
MAX_REVIEWS = 5
MAX_PHOTOS = 6
PHOTO_BYTES = 10 * 1024 * 1024  # the same cap as an upload
MIN_SIDE = 720  # resolver.MINIMUM_SIZE: smaller photos could never be shown
MAX_PIXELS = 30_000_000  # the same cap as an upload
REDIRECTS = 3


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _text(value: Any, limit: int) -> str | None:
    value = _first(value)
    if isinstance(value, dict):
        value = value.get("name")
    return " ".join(str(value).split())[:limit] or None if value not in (None, "") else None


def _images(value: Any) -> list[str]:
    images = value if isinstance(value, list) else [value]
    urls = [i.get("url") or i.get("contentUrl") if isinstance(i, dict) else i for i in images]
    return [u for u in urls if isinstance(u, str) and u.strip()][:MAX_PHOTOS]


def facts(raw: dict[str, Any]) -> dict[str, Any]:
    """The parts of one JSON-LD Product a video can use, trimmed and flattened."""
    offers = raw.get("offers") or {}
    variants = raw.get("hasVariant") or []
    if not offers and variants:  # a ProductGroup prices its variants
        offers = _first(variants).get("offers") or {} if isinstance(_first(variants), dict) else {}
    offer = _first(offers) if isinstance(offers, list) else offers
    offer = offer if isinstance(offer, dict) else {}
    rating = raw.get("aggregateRating")
    rating = rating if isinstance(rating, dict) else {}
    reviews = raw.get("review") or []
    reviews = reviews if isinstance(reviews, list) else [reviews]
    result = {
        "name": _text(raw.get("name"), 120),
        "brand": _text(raw.get("brand"), 80),
        "description": _text(raw.get("description"), 400),
        "price": _text(offer.get("price") or offer.get("lowPrice"), 20),
        "currency": _text(offer.get("priceCurrency"), 8),
        "availability": _text(offer.get("availability"), 80),
        "rating": _text(rating.get("ratingValue"), 8),
        "rating_count": _text(rating.get("reviewCount") or rating.get("ratingCount"), 12),
        "reviews": [
            {
                "quote": _text(r.get("reviewBody") or r.get("description"), 400),
                "author": _text(r.get("author"), 60),
                "rating": _text((r.get("reviewRating") or {}).get("ratingValue"), 8)
                if isinstance(r.get("reviewRating"), dict)
                else None,
            }
            for r in reviews[:MAX_REVIEWS]
            if isinstance(r, dict) and (r.get("reviewBody") or r.get("description"))
        ],
        "images": _images(raw.get("image")),
    }
    return {k: v for k, v in result.items() if v not in (None, [], "")}


def collect(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every product the crawled pages describe, once each (a product page and a listing often repeat one)."""
    found: dict[str, dict[str, Any]] = {}
    for page in pages:
        for raw in page.get("products") or []:
            product = facts(raw) if isinstance(raw, dict) else {}
            if product.get("name") and product["name"] not in found:
                product["images"] = [urljoin(page.get("route", ""), u) for u in product.get("images", [])]
                found[product["name"]] = product
    return list(found.values())[:MAX_PRODUCTS]


def public(url: str) -> bool:
    """http(s) on a host that resolves only to public addresses: a page's data must not reach the local network."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        addresses = {str(info[4][0]) for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses)


def fetch(url: str, client: httpx.Client) -> bytes:
    """One image, following at most a few redirects, each to a public address, and at most PHOTO_BYTES."""
    for _ in range(REDIRECTS + 1):
        if not public(url):
            raise ValueError(f"not a public http(s) address: {url}")
        with client.stream("GET", url) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers.get("location", ""))
                continue
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data += chunk
                if len(data) > PHOTO_BYTES:
                    raise ValueError(f"image over {PHOTO_BYTES // 1024 // 1024} MB: {url}")
            return bytes(data)
    raise ValueError(f"too many redirects: {url}")


def save_photos(products: list[dict[str, Any]], folder: Path, client: httpx.Client | None = None) -> list[str]:
    """Download the products' photos into `folder` as JPEGs, with a captions.yaml naming the product in each, so the
    folder reads like the user's own image folder. Returns what could not be used, for the run log."""
    folder.mkdir(parents=True, exist_ok=True)
    captions: dict[str, str] = {}
    skipped: list[str] = []
    own = client is None
    client = client or httpx.Client(timeout=15.0, follow_redirects=False, headers={"User-Agent": "ReelHive"})
    try:
        for product in products:
            for url in product.get("images", []):
                if len(captions) >= MAX_PHOTOS:
                    break
                try:
                    data = fetch(url, client)
                    with Image.open(io.BytesIO(data)) as image:
                        image.verify()
                    with Image.open(io.BytesIO(data)) as image:
                        if min(image.size) < MIN_SIDE or image.width * image.height > MAX_PIXELS:
                            raise ValueError(f"{image.width}x{image.height}: needs {MIN_SIDE}px a side, at most 30 MP")
                        name = f"product-{len(captions) + 1}.jpg"
                        image.convert("RGB").save(folder / name, "JPEG", quality=92)
                    captions[name] = f"Product photo: {product['name']}"
                except Exception as error:  # one bad photo must not stop the others
                    skipped.append(f"{url}: {error}")
    finally:
        if own:
            client.close()
    (folder / "captions.yaml").write_text(yaml.safe_dump(captions))
    return skipped
