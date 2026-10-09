"""Same-origin discovery and masked screenshots using an isolated browser context."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from PIL import Image
from playwright.sync_api import TimeoutError as BrowserTimeout
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
    return b._replace(path=b.path or "/").geturl()


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


TEXT_PER_PAGE = 3000  # research reads this much visible text per page


def _open_page(page, options: Screenshots, url: str) -> str:
    # Analytics and live apps may never become network-idle; use bounded page readiness instead.
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    resolved = same_origin(options.url, page.url)
    if response and response.status >= 400:
        raise ValueError(f"page returned HTTP {response.status}: {resolved}")
    try:
        page.wait_for_load_state("load", timeout=5000)
    except BrowserTimeout:
        pass  # screenshot preparation waits separately for the content we actually capture
    return resolved


def _prepare_screenshot(page) -> None:
    page.evaluate(
        """async () => {
          const frame = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          const ready = async () => {
            // Trigger native lazy images and scroll-triggered image/background loaders.
            for (let step = 0; step < 40; step++) {
              const bottom = Math.max(0, document.documentElement.scrollHeight - innerHeight);
              const top = Math.min(step * Math.max(1, Math.floor(innerHeight * 0.8)), bottom);
              scrollTo({top, left: 0, behavior: 'instant'});
              await frame();
              if (top >= bottom) break;
            }
            scrollTo({top: 0, left: 0, behavior: 'instant'});
            await frame();
            await document.fonts.ready;
            // Hidden responsive variants never load; wait only for images with a rendered box.
            const images = [...document.images].filter(image => image.getClientRects().length);
            await Promise.all(images.map(image => image.decode().catch(() => {})));
          };
          let timer;
          try {
            await Promise.race([ready(), new Promise((_, reject) => {
              timer = setTimeout(() => reject(new Error('Page images did not finish loading in 10 seconds')), 10000);
            })]);
          } finally { clearTimeout(timer); }
        }"""
    )


def discover(options: Screenshots, format: str, with_text: bool = False) -> list[dict[str, str]]:
    queue = [same_origin(options.url, route) for route in (options.routes or [options.url])]
    seen: set[str] = set()
    pages: list[dict[str, str]] = []
    with browser_context(options, format) as page:
        while queue and len(pages) < 10:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            resolved = _open_page(page, options, url)
            if resolved != url and resolved in seen:
                continue
            seen.add(resolved)
            pages.append(
                {
                    "route": resolved,
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
                    **({"text": _visible_text(page, options.mask)} if with_text else {}),
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


def _visible_text(page, masks: list[str]) -> str:
    """The page's readable text for research, without masked elements, collapsed and capped."""
    text = page.evaluate(
        """masks => { masks.forEach(s => document.querySelectorAll(s).forEach(n => n.remove()));
                     return document.body ? document.body.innerText : ''; }""",
        masks,
    )
    return " ".join(str(text).split())[:TEXT_PER_PAGE]


def capture(options: Screenshots, format: str, route: str, output: Path) -> None:
    url = same_origin(options.url, route)
    output.parent.mkdir(parents=True, exist_ok=True)
    with browser_context(options, format) as page:
        _open_page(page, options, url)
        _prepare_screenshot(page)
        page.screenshot(
            path=str(output),
            full_page=True,
            mask=[page.locator(selector) for selector in options.mask],
            mask_color="#000000",
            animations="disabled",
        )

    with Image.open(output) as image:
        image.convert("RGB").save(output, format="PNG")
