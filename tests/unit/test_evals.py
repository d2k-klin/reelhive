"""The eval harness pieces: dataset, stand-ins, deterministic scores, aggregation, gate and report."""

import copy

import pytest
import soundfile as sf
import yaml
from PIL import Image

from evals.harness import DATASET, EstimateTTS, PromptRecorder, load_set, serve_site
from evals.report import to_html, to_markdown
from evals.run import METRICS, aggregate, gate


def test_dataset_covers_the_plan_matrix():
    briefs = load_set("core", "http://127.0.0.1:1")
    assert 20 <= len(briefs) <= 30
    assert {b.format for b in briefs.values()} == {"16:9", "9:16", "1:1"}
    assert min(b.duration for b in briefs.values()) == 15 and max(b.duration for b in briefs.values()) == 180
    assert {len(b.features) for b in briefs.values()} >= {1, 8}
    assert {b.level for b in briefs.values()} == {"low", "medium"}
    assert any("/" in b.closing or "." in b.closing.rstrip(".") for b in briefs.values())  # URLs
    assert any(any(c.isdigit() for c in b.closing) for b in briefs.values())  # numbers

    def kinds(b):
        v = b.visuals
        sources = {"screenshots": v.screenshots, "images": v.images, "generate": v.generate}
        return frozenset(k for k, on in sources.items() if on)

    combos = {kinds(b) for b in briefs.values()}
    assert {frozenset(), frozenset({"screenshots"}), frozenset({"images"}), frozenset({"generate"})} <= combos
    assert any(len(c) >= 2 for c in combos)  # mixed
    smoke = yaml.safe_load((DATASET / "sets.yaml").read_text())["smoke"]
    assert len(smoke) == 5 and set(smoke) <= set(briefs)


def test_estimate_tts_matches_kokoro_rate(tmp_path):
    seconds = EstimateTTS().synth(" ".join(["word"] * 161), tmp_path / "a.wav", "female", "us", 1.0)
    assert seconds == pytest.approx(60, abs=0.1)
    assert sf.info(tmp_path / "a.wav").duration == pytest.approx(60, abs=0.1)


def test_prompt_recorder_writes_placeholders_without_calling_anything(tmp_path):
    recorder = PromptRecorder()
    usage = recorder.generate("a lighthouse", "1024x1536", tmp_path / "x.png")
    assert recorder.prompts == ["a lighthouse"] and usage["placeholder"]
    assert Image.open(tmp_path / "x.png").size == (1024, 1536)


def test_fixture_site_serves_locally():
    import urllib.request

    with serve_site() as site:
        assert site.startswith("http://127.0.0.1:")
        assert b"Dashboard" in urllib.request.urlopen(site + "/dashboard.html").read()


def record(**overrides):
    base = {key: 1.0 for key, _, higher in METRICS if higher}
    base.update(product_ui_generated=0, tokens=100, node_seconds={"script": 2.0}, node_tokens={"script": 100})
    return {**base, **overrides}


def test_aggregate_means_skip_missing_values():
    agg = aggregate([record(visual_coverage=None), record(visual_coverage=0.5, success=False)])
    assert agg["visual_coverage"] == 0.5 and agg["success"] == 0.5 and agg["briefs"] == 2
    assert agg["node_seconds"] == {"script": 2.0}


def test_gate_flags_regressions_beyond_five_percent():
    baseline = {"claude": aggregate([record(judge_hook=4.0)])}
    assert gate({"claude": aggregate([record(judge_hook=3.85)])}, baseline) == []  # -3.75%
    problems = gate({"claude": aggregate([record(judge_hook=3.7)])}, baseline)  # -7.5%
    assert len(problems) == 1 and "hook" in problems[0]
    problems = gate({"claude": aggregate([record(product_ui_generated=1)])}, baseline)
    assert "product UI" in problems[0]
    assert "no baseline" in gate({"ollama": aggregate([record()])}, baseline)[0]


def test_reports_have_a_row_per_metric_and_a_column_per_provider():
    providers = {"claude": aggregate([record()]), "ollama": aggregate([record(success=False)])}
    report = {
        "set": "smoke",
        "created": "now",
        "briefs": ["a"],
        "judge": True,
        "providers": providers,
        "records": [{"provider": "ollama", "brief": "a", "outcome": "failed", "error": "boom"}],
    }
    md = to_markdown(report)
    assert "| Metric | claude | ollama |" in md and "| Reached render | 100% | 0% |" in md
    assert "ollama · a: failed boom" in md and "`script` seconds / tokens" in md
    html = to_html(copy.deepcopy(report))
    assert "<th>ollama</th>" in html and html.count("<tr>") == len(METRICS) + 2
