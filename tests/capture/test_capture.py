import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PIL import Image

from reelhive.schemas.brief import Screenshots
from reelhive.visuals.capture import capture, discover


@pytest.fixture
def site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/lazy-image.png":
                image = io.BytesIO()
                Image.new("RGB", (200, 100), "blue").save(image, format="PNG")
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(image.getvalue())
                return
            if self.path == "/missing":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Missing page")
                return
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            logged_in = "session=ok" in self.headers.get("Cookie", "")
            html = f"""<title>{"Signed in" if logged_in else "Public"}</title>
            <style>body{{margin:0;background:white}}#secret{{position:absolute;left:10px;top:10px;width:200px;height:80px;background:red}}</style>
            <div id="secret"><h2>secret account</h2></div>
            <section class="account"><h1>Dashboard <span class="private">secret email</span></h1></section>
            <a href="/">Home</a><a href="https://external.invalid">outside</a>
            {"".join(f'<a href="/page{i}">Page {i}</a>' for i in range(14))}"""
            if self.path == "/lazy":
                html = """<title>Lazy page</title><style>body{margin:0;background:white}
                img{display:block;margin-top:8000px;width:200px;height:100px}</style>
                <h1>Lazy image below the fold</h1><img loading="lazy" src="/lazy-image.png">
                <img style="display:none" loading="lazy" src="/hidden-image.png">"""
            elif self.path == "/live":
                html = """<title>Live page</title><h1>Ready content</h1>
                <script>setInterval(() => fetch('/stream'), 50)</script>"""
            elif self.path == "/stream":
                # Keep fetches overlapping so network-idle is never a readiness signal.
                import time

                time.sleep(0.8)
                html = "live update"
            try:
                self.wfile.write(html.encode())
            except BrokenPipeError:
                pass  # a live update may finish after the capture context closes

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_discovery_cap_routes_and_saved_login(site, tmp_path):
    state = tmp_path / "auth.json"
    state.write_text(
        json.dumps(
            {
                "cookies": [
                    {
                        "name": "session",
                        "value": "ok",
                        "domain": "127.0.0.1",
                        "path": "/",
                        "expires": -1,
                        "httpOnly": False,
                        "secure": False,
                        "sameSite": "Lax",
                    }
                ],
                "origins": [],
            }
        )
    )
    options = Screenshots(url=site, storage_state=str(state), mask=["#secret", ".account .private"])
    pages = discover(options, "16:9")
    assert len(pages) == 10
    assert len({p["route"] for p in pages}) == 10
    assert sum(p["route"] == site + "/" for p in pages) == 1
    assert all("secret" not in p["headings"] for p in pages)
    assert all(p["route"].startswith(site) and p["title"] == "Signed in" for p in pages)
    options.routes = ["/chosen"]
    assert [p["route"] for p in discover(options, "1:1")] == [site + "/chosen"]
    options.routes = ["https://outside.invalid"]
    with pytest.raises(ValueError, match="origin"):
        discover(options, "16:9")


@pytest.mark.parametrize("format,size", [("16:9", (1920, 1080)), ("9:16", (1080, 1920)), ("1:1", (1080, 1080))])
def test_mask_is_solid_black_and_viewport_follows_format(site, tmp_path, format, size):
    output = tmp_path / "capture.png"
    capture(Screenshots(url=site, mask=["#secret"]), format, "/", output)
    with Image.open(output) as image:
        assert image.size == size
        assert image.crop((15, 15, 205, 85)).getextrema() == ((0, 0), (0, 0), (0, 0))


def test_capture_loads_images_below_the_first_viewport(site, tmp_path):
    output = tmp_path / "lazy.png"
    capture(Screenshots(url=site), "16:9", "/lazy", output)
    with Image.open(output) as image:
        assert image.height > 8000
        assert image.getpixel((100, image.height - 50)) == (0, 0, 255)


def test_capture_and_discovery_do_not_wait_for_live_updates_to_stop(site, tmp_path):
    options = Screenshots(url=site, routes=["/live"])
    assert discover(options, "16:9")[0]["title"] == "Live page"
    output = tmp_path / "live.png"
    capture(options, "16:9", "/live", output)
    assert output.is_file()


def test_capture_rejects_http_error_pages(site, tmp_path):
    output = tmp_path / "missing.png"
    with pytest.raises(ValueError, match="HTTP 404"):
        capture(Screenshots(url=site), "16:9", "/missing", output)
    assert not output.exists()
