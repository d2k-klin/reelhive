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
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            logged_in = "session=ok" in self.headers.get("Cookie", "")
            html = f"""<title>{"Signed in" if logged_in else "Public"}</title>
            <style>body{{margin:0;background:white}}#secret{{position:absolute;left:10px;top:10px;width:200px;height:80px;background:red}}</style>
            <div id="secret"><h2>secret account</h2></div>
            <section class="account"><h1>Dashboard <span class="private">secret email</span></h1></section>
            <a href="https://external.invalid">outside</a>
            {"".join(f'<a href="/page{i}">Page {i}</a>' for i in range(14))}"""
            self.wfile.write(html.encode())

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
