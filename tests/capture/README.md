# `tests/capture`

**Overview.** Screenshot tests with real headless Chromium (Playwright) against a small site the test serves itself on 127.0.0.1. No internet, and no real accounts.

## What's here

| File | Covers |
| --- | --- |
| [`test_capture.py`](test_capture.py) | Discovery with the 10-page cap, unique home-page URLs, explicit routes and a saved login cookie; solid black masks; desktop/mobile viewports; pixels from below-fold lazy images; capture with continuous background requests; HTTP error rejection |

Needs Chromium: `uv run playwright install chromium` (part of `make setup`; CI installs it with `--with-deps`).

## Extending

Add pages or behaviour to the `site` fixture's handler (it serves HTML from a string), then assert on the files `capture()` writes. Check pixels with Pillow rather than eyeballing. Any new privacy behaviour (masking, cookie scoping, cross-origin blocking) needs a test here.
