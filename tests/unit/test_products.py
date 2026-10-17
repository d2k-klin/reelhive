"""Product data from a website: facts read from its JSON-LD, photos fetched safely, and on-screen claims held to
them."""

import io
import json
import socket

import httpx
import pytest
import yaml
from PIL import Image

from reelhive.agents.critic import hard_checks, unsourced
from reelhive.agents.plan import PlannedScene
from reelhive.schemas.scene_spec import OfferScene, OfferText, ReviewScene, ReviewText, SceneSpec
from reelhive.visuals import products

SHOPIFY = {
    "@type": "Product",
    "name": "Everyday Backpack",
    "brand": {"@type": "Brand", "name": "Hive Goods"},
    "image": [{"@type": "ImageObject", "url": "https://cdn.shop.test/a.jpg"}, "https://cdn.shop.test/b.jpg"],
    "offers": [
        {"@type": "Offer", "price": "89.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}
    ],
    "aggregateRating": {"ratingValue": 4.8, "reviewCount": 212},
    "review": [
        {
            "author": {"name": "Sarah K."},
            "reviewBody": "I have carried it every day for a year and it still looks brand new.",
            "reviewRating": {"ratingValue": 5},
        },
        {"author": "Tom", "reviewRating": {"ratingValue": 4}},  # stars without words: nothing to quote
    ],
}


def test_facts_flatten_a_store_product_into_what_a_video_can_say():
    facts = products.facts(SHOPIFY)
    assert facts["name"] == "Everyday Backpack" and facts["brand"] == "Hive Goods"
    assert (facts["price"], facts["currency"], facts["rating"], facts["rating_count"]) == ("89.00", "USD", "4.8", "212")
    assert facts["reviews"] == [
        {
            "quote": "I have carried it every day for a year and it still looks brand new.",
            "author": "Sarah K.",
            "rating": "5",
        }
    ]
    assert facts["images"] == ["https://cdn.shop.test/a.jpg", "https://cdn.shop.test/b.jpg"]
    group = {"@type": "ProductGroup", "name": "Tee", "hasVariant": [{"offers": {"price": 25, "priceCurrency": "EUR"}}]}
    assert products.facts(group)["price"] == "25"
    assert products.facts({"name": "Bare"}) == {"name": "Bare"}


def test_collect_keeps_each_product_once_and_resolves_its_photos():
    pages = [
        {"route": "https://shop.test/p/bag", "products": [SHOPIFY | {"image": "/img/bag.jpg"}]},
        {"route": "https://shop.test/", "products": [SHOPIFY, {"name": None}, "junk"]},
    ]
    [bag] = products.collect(pages)
    assert bag["images"] == ["https://shop.test/img/bag.jpg"]


@pytest.fixture
def resolve(monkeypatch):
    """shop.test resolves to a public address, inside.test to the local network."""
    addresses = {"shop.test": "93.184.216.34", "cdn.shop.test": "93.184.216.34", "inside.test": "192.168.1.5"}

    def lookup(host, *_):
        if host not in addresses:
            raise socket.gaierror(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addresses[host], 443))]

    monkeypatch.setattr(products.socket, "getaddrinfo", lookup)


def test_only_public_http_addresses_are_fetched(resolve):
    assert products.public("https://shop.test/a.jpg")
    for url in (
        "http://inside.test/a.jpg",
        "file:///etc/passwd",
        "https://user:pw@shop.test/a.jpg",
        "https://nx.test/",
    ):
        assert not products.public(url)


def jpeg(size: tuple[int, int]) -> bytes:
    data = io.BytesIO()
    Image.new("RGB", size, "orange").save(data, "JPEG")
    return data.getvalue()


def test_photos_are_saved_reencoded_with_captions_and_bad_ones_are_skipped(resolve, tmp_path):
    def serve(request: httpx.Request) -> httpx.Response:
        return {
            "/big.jpg": lambda: httpx.Response(200, content=jpeg((1200, 1200))),
            "/small.jpg": lambda: httpx.Response(200, content=jpeg((300, 300))),
            "/moved.jpg": lambda: httpx.Response(302, headers={"location": "http://inside.test/x.jpg"}),
            "/hop.jpg": lambda: httpx.Response(301, headers={"location": "/big.jpg"}),
            "/text.jpg": lambda: httpx.Response(200, content=b"<html>not an image</html>"),
        }[request.url.path]()

    client = httpx.Client(transport=httpx.MockTransport(serve), follow_redirects=False)
    urls = [f"https://shop.test/{n}.jpg" for n in ("big", "small", "moved", "hop", "text")]
    skipped = products.save_photos([{"name": "Bag", "images": urls}], tmp_path, client)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["captions.yaml", "product-1.jpg", "product-2.jpg"]
    assert yaml.safe_load((tmp_path / "captions.yaml").read_text())["product-2.jpg"] == "Product photo: Bag"
    assert len(skipped) == 3 and any("inside.test" in reason for reason in skipped)


def test_on_screen_prices_quotes_and_ratings_must_come_from_the_sources(brief, tmp_path):
    (tmp_path / "research.json").write_text(json.dumps({"products": [products.facts(SHOPIFY)]}))
    quote = "I have carried it every day for a year ... still looks brand new."
    spec = SceneSpec(
        scenes=[
            OfferScene(index=1, narration="x", text=OfferText(headline="Everyday Backpack", price="$89", was="$119")),
            ReviewScene(index=2, narration="x", text=ReviewText(headline=quote, subline="Sarah K.", rating=5)),
            ReviewScene(
                index=3, narration="x", text=ReviewText(headline="Honestly the best bag ever made", rating=4.8)
            ),
        ]
    )
    from reelhive.agents.critic import sources

    assert unsourced(spec, sources(brief, tmp_path)) == ["scene 1 was $119", "scene 3 quote"]
    brief.context = "Launch sale: was $119, now $89."
    claims = next(c for c in hard_checks(spec, brief, {}, tmp_path) if c.name == "claims")
    assert not claims.passed and "scene 3 quote" in claims.message and "$119" not in claims.message


def test_the_planner_fills_offer_and_review_text_and_needs_a_price():
    offer = PlannedScene(
        template="offer", headline="Everyday Backpack", price="$89", was="$119", secondary="Free shipping"
    )
    assert offer.text().model_dump() == {
        "headline": "Everyday Backpack",
        "price": "$89",
        "was": "$119",
        "subline": "Free shipping",
    }
    review = PlannedScene(template="review", headline="Still looks brand new.", secondary="Sarah K.", rating=5)
    assert review.to_scene(1, "x").text.model_dump() == {
        "headline": "Still looks brand new.",
        "subline": "Sarah K.",
        "rating": 5,
    }
    with pytest.raises(ValueError, match="offer"):
        PlannedScene(template="offer", headline="No price")


def test_saved_product_photos_join_the_catalog_the_planner_chooses_from(brief, tmp_path):
    from reelhive.core.context import RunContext
    from reelhive.core.events import EventBus
    from reelhive.visuals.resolver import catalog

    shop = tmp_path / "visuals" / "product"
    shop.mkdir(parents=True)
    Image.new("RGB", (1000, 1000)).save(shop / "product-1.jpg")
    (shop / "captions.yaml").write_text(yaml.safe_dump({"product-1.jpg": "Product photo: Everyday Backpack"}))
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None)
    assert [(e["image"], e["caption"]) for e in catalog(ctx)] == [("product-1.jpg", "Product photo: Everyday Backpack")]
    ctx.brief.visuals.source = "none"
    assert catalog(ctx) == []
