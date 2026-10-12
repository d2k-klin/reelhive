"""Sign in to a platform: OAuth 2.0 authorization code with a loopback redirect (RFC 8252), state and PKCE.

The consent page opens in the browser; the platform redirects to `http://localhost:<port>/callback`, where a
one-shot listener on 127.0.0.1 takes the code (only with the state it sent), the code is exchanged for a token,
and the account is saved. Register that exact redirect URI in each developer app.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import httpx

from reelhive.config import Publishing
from reelhive.publish import accounts
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, client
from reelhive.publish.platforms import ADAPTERS
from reelhive.schemas.publish import Platform

TIMEOUT = 600.0  # ten minutes to finish signing in
PAGE = (
    "<!doctype html><meta charset=utf-8><title>ReelHive</title>"
    "<body style='font:16px system-ui;margin:3rem'><h1>{title}</h1><p>{text}</p></body>"
)


def redirect_uri(settings: Publishing) -> str:
    return f"http://localhost:{settings.redirect_port}/callback"


@dataclass(frozen=True)
class Consent:
    platform: Platform
    url: str
    state: str
    verifier: str | None
    redirect_uri: str


def begin(platform: Platform, settings: Publishing) -> Consent:
    adapter = ADAPTERS[platform]
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64) if adapter.pkce else None
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode() if verifier else None
    )
    uri = redirect_uri(settings)
    return Consent(platform, adapter.authorize_url(uri, state, challenge, settings), state, verifier, uri)


def wait_for_code(consent: Consent, port: int, timeout: float = TIMEOUT, ready: threading.Event | None = None) -> str:
    """Serve one redirect on 127.0.0.1:`port` and return its code; PublishError on denial, a wrong state or timeout."""
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's name)
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path != "/callback":
                self.send_error(404)
                return
            if query.get("state") != consent.state:
                result["error"] = "the sign-in response did not match this request; try again"
            elif "code" in query:
                result["code"] = query["code"]
            else:
                result["error"] = query.get("error_description") or query.get("error") or "sign-in was cancelled"
            done = "code" in result
            body = PAGE.format(
                title="Signed in" if done else "Sign-in failed",
                text="You can close this tab and return to ReelHive." if done else result["error"],
            ).encode()
            self.send_response(200 if done else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:  # the query holds the code: never print it
            pass

    try:
        server = HTTPServer(("127.0.0.1", port), Callback)
    except OSError as error:
        raise PublishError(f"port {port} is busy; set publishing.redirect_port (and the app's redirect URI)") from error
    server.timeout = 0.5
    if ready:
        ready.set()
    deadline = threading.Event()
    timer = threading.Timer(timeout, deadline.set)
    timer.start()
    try:
        while not result and not deadline.is_set():
            server.handle_request()
    finally:
        timer.cancel()
        server.server_close()
    if "code" in result:
        return result["code"]
    raise PublishError(result.get("error", "sign-in timed out"))


def finish(consent: Consent, code: str, settings: Publishing, http: httpx.Client | None = None) -> Account:
    adapter = ADAPTERS[consent.platform]
    with http or client() as session:
        token = adapter.exchange(session, code, consent.redirect_uri, consent.verifier)
        return accounts.save(adapter.identify(session, token, settings))


def connect(
    platform: Platform,
    settings: Publishing,
    open_browser: Callable[[str], object] = webbrowser.open,
    timeout: float = TIMEOUT,
    http: httpx.Client | None = None,
) -> Account:
    """The whole sign-in, for the CLI and the studio: consent in the browser, then the saved account."""
    consent = begin(platform, settings)
    ready = threading.Event()
    opener = threading.Thread(target=lambda: ready.wait(5) and open_browser(consent.url), daemon=True)
    opener.start()
    code = wait_for_code(consent, settings.redirect_port, timeout, ready)
    return finish(consent, code, settings, http)
