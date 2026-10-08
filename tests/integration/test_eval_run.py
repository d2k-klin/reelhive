"""`reelhive eval` end to end on the smoke set: real graphs, fake providers, fixture site, no video."""

import asyncio
import json

from conftest import VERDICT_PASS, FakeModel, make_plan, words

from evals.run import gate, run_eval_async
from reelhive.config import Config
from reelhive.nodes.timing_node import target_words
from reelhive.schemas.brief import Brief

JUDGE = {
    "ScriptJudgement": {"hook": 4, "clarity": 4, "audience_fit": 4, "storyline": 5, "cta": 4, "notes": "fine"},
    "PromptJudgement": {"scores": [{"scene": 1, "relevance": 4, "style": 5, "no_product_ui": 5}]},
}


def script_for(brief: Brief) -> dict:
    roles = ["hook", *([] if brief.duration < 30 else ["problem"]), *(["feature"] * len(brief.features)), "cta"]
    per = target_words(brief) // len(roles)
    beats = []
    for role, feature in zip(
        roles, [None] * (len(roles) - len(brief.features) - 1) + brief.features + [None], strict=True
    ):
        text = words(per - len(brief.closing.split())) + " " + brief.closing if role == "cta" else words(per)
        beats.append({"role": role, "narration": text, "feature": feature})
    return {"title": "eval", "beats": beats}


def plan_for(brief: Brief, beats: int, drop_feature: bool) -> dict:
    plan = make_plan(brief, drop_feature=1 if drop_feature else None)
    if beats < len(plan["scenes"]):  # short briefs have no problem beat
        plan["scenes"].pop(1)
    plan["scenes"][0]["visual_request"] = {"kind": "concept", "prompt": "a lighthouse in fog"}
    plan["scenes"][-2]["visual_request"] = {"kind": "product_ui"}
    return plan


class BriefAwareFake(FakeModel):
    """Answers each request for the brief named in its prompt, so one model serves many briefs at once."""

    def __init__(self, drop_feature: bool = False) -> None:
        super().__init__({})
        self.drop_feature = drop_feature

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        name = tool_specs[0]["name"]
        text = " ".join(c.get("text", "") for m in messages if m["role"] == "user" for c in m["content"])
        brief = Brief.model_validate(json.JSONDecoder().raw_decode(text[text.index("Brief:\n") + 7 :])[0])
        script = script_for(brief)
        payload = {
            "Script": script,
            "ScenePlan": plan_for(brief, len(script["beats"]), self.drop_feature),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "fits"},
            "Verdict": VERDICT_PASS,
        }[name]
        self.calls.append(name)
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{len(self.calls)}", "name": name}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(payload)}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        usage = {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}
        yield {"metadata": {"usage": usage, "metrics": {"latencyMs": 1}}}


def test_smoke_eval_compares_providers_and_gates(tmp_path):
    fakes = {"good": BriefAwareFake(), "lossy": BriefAwareFake(drop_feature=True)}
    report = asyncio.run(
        run_eval_async(
            ["good", "lossy"],
            Config(),
            "smoke",
            judge=FakeModel({k: [v] * 10 for k, v in JUDGE.items()}),
            out_dir=tmp_path,
            models_for=lambda p: {"strong": fakes[p], "fast": fakes[p]},
            concurrency=3,
        )
    )
    good, lossy = report["providers"]["good"], report["providers"]["lossy"]
    assert good["briefs"] == lossy["briefs"] == 5
    assert good["success"] == 1.0 and good["schema_first_try"] == 1.0, [
        (r["brief"], r["outcome"], r.get("error")) for r in report["records"] if r["provider"] == "good"
    ]
    assert good["closing_match"] == good["feature_coverage"] == good["duration_ok"] == good["pace_ok"] == 1.0
    assert good["product_ui_generated"] == 0
    assert 0 < good["visual_coverage"] <= 1  # the screenshot brief resolves its product UI scene locally
    assert good["image_count"] > 0 and good["judge_prompt_relevance"] == 4  # the generate brief's prompt
    assert good["judge_storyline"] == 5 and good["tokens"] > 0 and "script" in good["node_seconds"]

    assert lossy["feature_coverage"] < 1 and lossy["success"] < 1 and lossy["fix_iterations"] == 1
    assert any("Feature coverage" in p for p in gate({"good": lossy}, {"good": good}))
    assert gate({"good": good}, {"good": good}) == []

    out = tmp_path / next(p.name for p in tmp_path.iterdir())
    assert {"results.json", "report.md", "report.html"} <= {p.name for p in out.iterdir()}
    assert not list(out.rglob("*.mp4"))  # evals never render video
    assert "| Metric | good | lossy |" in (out / "report.md").read_text()
