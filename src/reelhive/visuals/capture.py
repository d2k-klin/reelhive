"""Same-origin discovery and masked screenshots using an isolated browser context."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

from reelhive.schemas.brief import Screenshots
from reelhive.schemas.scene_spec import FORMATS


def same_origin(base: str, route: str) -> str:
    url = urldefrag(urljoin(base, route))[0]
    a, b = urlparse(base), urlparse(url)

    def origin(p):
        return p.scheme, p.hostname, p.port or (443 if p.scheme == "https" else 80)

    if origin(a) != origin(b) or b.username or b.password:
        raise ValueError(f"screenshot route must stay on the configured origin: {route}")
    return url


@contextmanager
def browser_context(options: Screenshots, format: str):
    width, height = FORMATS[format]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=format == "9:16",
                has_touch=format == "9:16",
                storage_state=options.storage_state,
                locale="en-US",
                color_scheme="light",
                reduced_motion="reduce",
                device_scale_factor=1,
                accept_downloads=False,
                service_workers="block",
            )

            # Cookies from auth.json must never accompany a cross-origin navigation.
            def guard(route):
                if route.request.is_navigation_request():
                    if route.request.frame.page != page:
                        route.abort()
                        return
                    try:
                        same_origin(options.url, route.request.url)
                    except ValueError:
                        route.abort()
                        return
                route.continue_()

            page = context.new_page()
            context.route("**/*", guard)
            context.on("page", lambda opened: opened.close() if opened != page else None)
            page.on("download", lambda download: download.cancel())
            yield page
        finally:
            browser.close()


def discover(options: Screenshots, format: str) -> list[dict[str, str]]:
    queue = [same_origin(options.url, route) for route in (options.routes or [options.url])]
    seen: set[str] = set()
    pages: list[dict[str, str]] = []
    with browser_context(options, format) as page:
        while queue and len(pages) < 10:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            page.goto(url, wait_until="networkidle", timeout=30000)
            same_origin(options.url, page.url)
            pages.append(
                {
                    "route": url,
                    "title": page.title(),
                    "headings": " | ".join(
                        page.locator("h1,h2").evaluate_all(
                            """(nodes, masks) => nodes.map(node => {
                              const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                              const parts = [];
                              while (walker.nextNode()) {
                                const text = walker.currentNode;
                                if (!masks.some(s => text.parentElement.closest(s))) parts.push(text.textContent);
                              }
                              return parts.join('');
                            })""",
                            options.mask,
                        )
                    )[:1000],
                }
            )
            if not options.routes:
                for href in page.locator("a[href]").evaluate_all("nodes => nodes.map(a => a.href)"):
                    try:
                        link = same_origin(options.url, href)
                    except ValueError:
                        continue
                    if link not in seen and link not in queue:
                        queue.append(link)
    return pages


def capture(options: Screenshots, format: str, route: str, output: Path) -> None:
    url = same_origin(options.url, route)
    output.parent.mkdir(parents=True, exist_ok=True)
    with browser_context(options, format) as page:
        page.goto(url, wait_until="networkidle", timeout=30000)
        same_origin(options.url, page.url)
        page.screenshot(
            path=str(output),
            full_page=True,
            mask=[page.locator(selector) for selector in options.mask],
            mask_color="#000000",
        )

    with Image.open(output) as image:
        image.convert("RGB").save(output, format="PNG")
