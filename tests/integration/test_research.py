"""Notes in, story out: research reads the product website and the writers build on it (fake model)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.agents.critic import hard_checks
from reelhive.core.service import Service
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import CtaScene, CtaText, HookScene, HookText, SceneSpec

NOTES = {
    "product": "Scancomb is a compliance hub for small software teams.",
    "names": ["Scancomb", "WardBee"],
    "offerings": ["Open-source compliance tools", "WardBee compliance platform"],
    "audience_pains": ["Audits take weeks"],
    "proof_points": ["Maps controls to SOC 2"],
    "note_readings": ["The free scanners on the tools page", "WardBee, the paid platform"],
}


@pytest.fixture
def site():
    pages = {
        "/": '<title>Scancomb</title><h1>Compliance for builders</h1><a href="/tools">Tools</a>'
        '<p>Scancomb helps small teams pass audits.</p><p class="secret">internal-key-123</p>',
        "/tools": "<title>Tools</title><h1>Open-source tools</h1><p>Free scanners and WardBee, our platform.</p>",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = pages.get(self.path.split("?")[0])
            self.send_response(200 if body else 404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write((body or "").encode())

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


class RecordingModel(FakeModel):
    """Remembers the user prompt of every request, by output model name."""

    def __init__(self, responses):
        super().__init__(responses)
        self.prompts: dict[str, str] = {}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        text = " ".join(c.get("text", "") for m in messages if m["role"] == "user" for c in m["content"])
        self.prompts.setdefault(tool_specs[0]["name"], text)
        async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield event


def rough_brief(site: str | None, **extra) -> Brief:
    return Brief.model_validate(
        {
            "audience": "User of scancomb.coom",
            "storyline": "What's scancomb, which services it offers, whatsoever is the story behind",
            "features": ["offered Opensource tools", "offered compliance platform WardBee"],
            "closing": "Automate your compliance and protect what you build with War",
            "website": site,
            "visuals": {"source": "none"},
            **extra,
        }
    )


def test_research_reads_the_site_and_the_writers_build_on_it(config, site):
    brief = rough_brief(site)
    model = RecordingModel(
        {
            "ProductNotes": NOTES,
            "Script": make_script(brief),
            "ScenePlan": make_plan(brief),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "fits"},
            "Verdict": VERDICT_PASS,
        }
    )
    events = []
    result = Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer).run(brief, events.append)

    assert result.status == "done"
    assert json.loads((result.run_dir / "research.json").read_text())["names"] == ["Scancomb", "WardBee"]
    research_prompt = model.prompts["ProductNotes"]
    assert "Free scanners and WardBee" in research_prompt and "Compliance for builders" in research_prompt
    for writer in ("Script", "ScenePlan", "Verdict"):
        assert "Product research from the website" in model.prompts[writer] and "WardBee" in model.prompts[writer]
    assert "polish it, don't copy it" in model.prompts["Script"]
    assert "Key points:\n1. offered Opensource tools" in model.prompts["Script"]
    tasks = [e.data["task"] for e in events if e.type == "node.task" and e.data["node"] == "research"]
    assert any(t.startswith("Read 2 pages") for t in tasks)


def test_research_skips_without_a_website_or_when_the_site_is_down(config):
    for website, expected in ((None, "No product website"), ("http://127.0.0.1:9", "Could not read the website")):
        brief = rough_brief(website)
        model = FakeModel({"Script": make_script(brief)})
        events = []
        result = Service(config, {"strong": model}, StubTTS(), stub_renderer).run(
            brief.model_copy(update={"level": "medium"}), events.append
        )
        assert result.status == "awaiting_script"  # the video carries on from the brief alone
        assert "ProductNotes" not in model.calls and not (result.run_dir / "research.json").exists()
        assert any(expected in e.data.get("task", "") for e in events if e.type == "node.task")


def test_masked_text_never_reaches_the_research_prompt(config, site):
    brief = rough_brief(site, visuals={"source": "auto", "screenshots": {"url": site, "mask": [".secret"]}})
    model = RecordingModel({"ProductNotes": NOTES, "Script": make_script(brief)})
    Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer).run(
        brief.model_copy(update={"level": "medium"})
    )
    assert "internal-key-123" not in model.prompts["ProductNotes"]


def test_a_website_becomes_the_screenshot_source_unless_told_otherwise():
    brief = Brief.model_validate(
        {"audience": "abc", "storyline": "abc", "features": ["x"], "closing": "abc", "website": "https://scancomb.com"}
    )
    assert brief.visuals.screenshots.url == "https://scancomb.com"
    images = Brief.model_validate({**brief.model_dump(), "visuals": {"source": "images", "images": "."}})
    assert images.visuals.screenshots is None
    with pytest.raises(ValueError, match="http"):
        Brief.model_validate({**brief.model_dump(exclude={"visuals"}), "website": "ftp://scancomb.com"})


def test_a_public_app_url_is_researched_but_a_local_one_is_not():
    from types import SimpleNamespace

    from reelhive.agents.researcher import site_options

    for url, expected in (("https://scancomb.com", "https://scancomb.com"), ("http://localhost:3000", None)):
        brief = rough_brief(None, visuals={"source": "auto", "screenshots": {"url": url}})
        site = site_options(SimpleNamespace(brief=brief))
        assert (site.url if site else None) == expected


def test_one_scene_can_tell_several_notes(brief):
    spec = SceneSpec(
        duration=60.0,
        scenes=[
            HookScene(index=1, narration="word " * 70, covers=[1, 2], text=HookText(headline="One story")),
            CtaScene(index=2, narration="word " * 70, covers=[3], text=CtaText(headline="Start today")),
        ],
    )
    narrated = {s.index: (s.narration, 25.0) for s in spec.scenes}
    checks = {c.name: c for c in hard_checks(spec, brief, narrated)}
    assert checks["features"].passed and checks["features"].value == "3/3"
