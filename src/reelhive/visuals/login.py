"""The user signs in by hand; only Playwright storage state is saved."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from reelhive.schemas.brief import Screenshots


def login(url: str, output: Path, confirm=input) -> None:
    Screenshots(url=url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            confirm("Sign in in the browser, then press Enter here to save the session. ")
            output.parent.mkdir(parents=True, exist_ok=True)
            # Create with owner-only permissions before writing cookies/tokens.
            fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as f:
                import json

                json.dump(context.storage_state(), f)
        finally:
            browser.close()
