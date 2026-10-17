"""A new cut of a finished video: the brief it gets, what it carries over, and what the writer is told."""

import json

import pytest

from reelhive.agents.script_writer import ScriptWriterNode
from reelhive.core.context import RunContext
from reelhive.core.cut import CUT_FILE, cut_block, cut_brief, seed
from reelhive.core.events import EventBus
from reelhive.schemas.scene_spec import HookScene, HookText
from reelhive.schemas.script import Beat, Script


def test_a_platform_cut_takes_its_defaults_and_drops_scenes_timed_for_the_parent(brief):
    brief.level = "high"
    brief.scenes = [HookScene(index=1, narration="x", text=HookText(headline="h"))]
    reel = cut_brief(brief, platform="reels")
    assert (reel.platform, reel.format, reel.pacing, reel.captions, reel.cold_open) == (
        "reels",
        "9:16",
        "punchy",
        True,
        True,
    )
    assert reel.duration == 30 and reel.scenes is None and reel.features == brief.features
    assert cut_brief(brief, platform="shorts", duration=45).duration == 45
    assert cut_brief(brief.model_copy(update={"duration": 20}), platform="tiktok").duration == 20  # never longer
    square = cut_brief(brief, format="1:1")
    assert (square.format, square.platform, square.duration) == ("1:1", None, brief.duration)
    with pytest.raises(ValueError):
        cut_brief(brief, platform="myspace")


def test_seed_carries_research_photos_and_script_and_needs_a_script(tmp_path):
    parent, child = tmp_path / "parent", tmp_path / "child"
    (parent / "visuals" / "product").mkdir(parents=True)
    child.mkdir()
    with pytest.raises(ValueError, match="script"):
        seed(parent, child)
    script = Script(
        title="t", beats=[Beat(role="hook", narration="Cloud bills grow."), Beat(role="cta", narration="Try it.")]
    )
    (parent / "script.json").write_text(script.model_dump_json())
    (parent / "research.json").write_text('{"product": "CostHive"}')
    (parent / "visuals" / "product" / "product-1.jpg").write_bytes(b"jpg")
    seed(parent, child)
    assert json.loads((child / "research.json").read_text()) == {"product": "CostHive"}
    assert (child / "visuals" / "product" / "product-1.jpg").exists()
    assert json.loads((child / CUT_FILE).read_text())["run"] == "parent"
    assert "1. [hook] Cloud bills grow." in cut_block(child) and cut_block(parent) == ""


def test_the_writer_is_handed_the_original_script_to_condense(tmp_path, brief):
    (tmp_path / CUT_FILE).write_text(json.dumps({"run": "p", "beats": [{"role": "hook", "narration": "Bills grow."}]}))
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None)
    prompt = ScriptWriterNode().build_prompt(ctx)
    assert "new cut of a finished one" in prompt and "1. [hook] Bills grow." in prompt
