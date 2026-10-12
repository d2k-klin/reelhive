"""HTTP for the platform adapters: bounded retries on rate limits and server errors, readable failures."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}
ATTEMPTS = 4
TIMEOUT = httpx.Timeout(30.0, write=300.0, read=120.0)
sleep = time.sleep  # tests replace this


class PublishError(RuntimeError):
    """A platform refused or failed a request. The message is safe to show: it never contains a token."""


def client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, follow_redirects=False)


def _detail(response: httpx.Response) -> str:
    try:
        body: Any = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or error)[:300]
        return str(body.get("message") or body.get("error_description") or error or body)[:300]
    return str(body)[:300]


def send(
    http: httpx.Client,
    method: str,
    url: str,
    *,
    ok: set[int] | None = None,
    what: str = "request",
    **kwargs: Any,
) -> httpx.Response:
    """One request, retried with exponential backoff on 429, 5xx and dropped connections.

    `ok` lists the statuses the caller handles itself (e.g. 308 for a resumable upload); anything else that isn't
    2xx raises PublishError naming `what` and the platform's own reason."""
    allowed = ok or set()
    for attempt in range(ATTEMPTS):
        try:
            response = http.request(method, url, **kwargs)
        except httpx.TransportError as error:
            if attempt == ATTEMPTS - 1:
                raise PublishError(f"{what} failed: {type(error).__name__}") from error
            sleep(2**attempt)
            continue
        if response.status_code in allowed or response.is_success:
            return response
        if response.status_code in RETRY_STATUS and attempt < ATTEMPTS - 1:
            wait = response.headers.get("retry-after", "")
            sleep(float(wait) if wait.replace(".", "", 1).isdigit() else 2**attempt)
            continue
        raise PublishError(f"{what} failed ({response.status_code}): {_detail(response)}")
    raise PublishError(f"{what} failed")  # unreachable: the loop returns or raises


def ranges(size: int, chunk: int) -> Iterator[tuple[int, int]]:
    """(first, last) inclusive byte ranges covering `size` bytes in `chunk`-sized parts."""
    for first in range(0, size, chunk):
        yield first, min(first + chunk, size) - 1


def read(path: Path, first: int, last: int) -> bytes:
    with path.open("rb") as file:
        file.seek(first)
        return file.read(last - first + 1)
