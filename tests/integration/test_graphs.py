"""Both graphs end to end with FakeModel, StubTTS and an ffmpeg stand-in for Revideo."""

import copy
import json

import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer, words

from reelhive.audio.mixer import probe
from reelhive.core.events import replay
from reelhive.core.service import Service
from reelhive.graphs.production import MAX_PLAN_REPAIRS
from reelhive.schemas.scene_spec import CREDIT_TEXT, IntroText

MUSIC = {"mood": "tech", "bpm": 110, "reason": "fits a developer audience"}


def service(config, responses):
    model = FakeModel(responses)
    tts = StubTTS()
    return Service(config, models={"strong": model, "fast": model}, tts=tts, renderer=stub_renderer), model, tts


def run(svc, brief):
    events = []
    result = svc.run(brief, on_event=events.append)
    return result, events


def of_type(events, type_):
    return [e.data for e in events if e.type == type_]


def test_pass_path_renders_a_video(config, brief):
    svc, model, tts = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, events = run(svc, brief)

    assert result.status == "done"
    info = probe(result.video)
    assert info["has_audio"] and info["comment"] == CREDIT_TEXT
    assert info["has_subtitles"] and (result.run_dir / "video.srt").read_text().startswith("1\n00:00:")
    assert info["duration"] == pytest.approx(brief.duration, rel=0.05)
    assert sorted(model.calls) == ["MusicChoice", "ScenePlan", "Script", "Verdict"]
    assert len(tts.calls) == len(make_script(brief)["beats"])  # one voiced beat per shot

    started = [d["node"] for d in of_type(events, "node.started")]
    assert started[:3] == ["brief", "research", "script"]  # research is skipped without a website
    assert set(started[3:6]) == {"scenes", "narrate", "music"}  # parallel branches
    assert started[6:] == ["visuals", "timing", "critic", "render", "review", "sound", "master"]
    assert [d["node"] for d in of_type(events, "node.skipped")] == ["fix", "recheck"]
    assert all(d["passed"] for d in of_type(events, "gate.result"))
    assert of_type(events, "critic.verdict")[0]["passed"]
    assert any(d["node"] == "script" for d in of_type(events, "agent.text"))
    assert of_type(events, "run.finished")[0]["status"] == "done"
    assert {d["node"]: d["tokens"] for d in of_type(events, "node.finished")}["script"] == 150

    run_dir = result.run_dir
    for name in ("brief.yaml", "script.json", "spec.json", "audio/mix.wav", "video.mp4", "run.log.jsonl"):
        assert (run_dir / name).exists(), name
    spec = json.loads((run_dir / "spec.json").read_text())
    assert spec["credit"]["mode"] == "end" and spec["music"].endswith("tech-110.mp3")
    assert [e.type for e in replay(run_dir / "run.log.jsonl")] == [e.type for e in events]


def test_hard_check_failure_takes_the_fix_path(config, brief):
    script = make_script(brief, drop=1)  # the writer forgot key point 1
    fixed_narration = [b["narration"] for b in script["beats"]]
    told = next(i for i, b in enumerate(script["beats"]) if b["role"] == "feature")  # where note 1 should have been
    fixed_narration[told] = words(len(fixed_narration[told].split()), "now telling the first key point")
    svc, model, tts = service(
        config,
        {
            "Script": script,
            "ScenePlan": [make_plan(brief, drop_feature=1), make_plan(brief, narration=fixed_narration)],
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
        },
    )
    result, events = run(svc, brief)

    assert result.status == "done"
    # No story review while the hard checks fail; once the repair passes them, the repaired plan is reviewed.
    assert model.calls.count("Verdict") == 1 and of_type(events, "critic.verdict")[0]["passed"]
    gates = of_type(events, "gate.result")
    assert {(d["node"], d["check"]) for d in gates if not d["passed"]} == {("critic", "features")}
    assert all(d["passed"] for d in gates if d["node"] == "recheck")
    diff = of_type(events, "fix.diff")[0]["changes"]
    assert [c["scene"] for c in diff] == [told + 1]
    assert len(tts.calls) == len(script["beats"]) + 1  # every beat + the one re-voiced scene
    assert of_type(events, "node.skipped") == []


def test_recheck_failure_stops_with_a_report(config, brief):
    broken = make_plan(brief, drop_feature=2)
    plans = [broken] + [copy.deepcopy(broken) for _ in range(MAX_PLAN_REPAIRS)]  # the planner, then every repair
    svc, _, _ = service(config, {"Script": make_script(brief, drop=2), "ScenePlan": plans, "MusicChoice": MUSIC})
    result, events = run(svc, brief)

    assert result.status == "stopped" and result.video is None
    started = [d["node"] for d in of_type(events, "node.started")]
    assert started.count("fix") == started.count("recheck") == MAX_PLAN_REPAIRS  # bounded, then it stops
    assert any("key points not told" in line and brief.features[1] in line for line in result.report)
    assert [d["node"] for d in of_type(events, "node.skipped")] == ["render", "review", "sound", "master"]
    assert of_type(events, "run.finished")[0]["status"] == "stopped"


def test_critic_rejection_goes_through_fix_and_the_repair_is_reviewed_again(config, brief):
    script = make_script(brief)
    narration = [b["narration"] for b in script["beats"]]
    verdict = {**VERDICT_PASS, "hook": 2, "passed": False, "reasons": ["hook is flat"]}
    svc, model, _ = service(
        config,
        {
            "Script": script,
            "ScenePlan": [make_plan(brief), make_plan(brief, narration=narration)],
            "MusicChoice": MUSIC,
            "Verdict": [verdict, VERDICT_PASS],
        },
    )
    result, events = run(svc, brief)
    assert result.status == "done"
    verdicts = of_type(events, "critic.verdict")
    assert [v["passed"] for v in verdicts] == [False, True] and verdicts[0]["reasons"] == ["hook is flat"]
    assert model.calls.count("ScenePlan") == 2  # the planner, then one repair the second review approved
    assert of_type(events, "fix.diff")[0]["changes"] == []


def test_a_story_review_that_never_approves_gets_bounded_repairs_then_the_video_goes_ahead(config, brief):
    from reelhive.agents.critic import MAX_STORY_REPAIRS

    script = make_script(brief)
    narration = [b["narration"] for b in script["beats"]]
    verdict = {**VERDICT_PASS, "hook": 2, "passed": False, "reasons": ["hook is flat"]}
    svc, model, _ = service(
        config,
        {
            "Script": script,
            "ScenePlan": [make_plan(brief)] + [make_plan(brief, narration=narration)] * MAX_STORY_REPAIRS,
            "MusicChoice": MUSIC,
            "Verdict": verdict,
        },
    )
    result, events = run(svc, brief)
    assert result.status == "done"  # every hard check passes, so taste alone doesn't stop the video
    assert model.calls.count("Verdict") == 1 + MAX_STORY_REPAIRS
    assert model.calls.count("ScenePlan") == 1 + MAX_STORY_REPAIRS
    notes = [d["task"] for d in of_type(events, "node.task") if d["node"] == "recheck" and "Going ahead" in d["task"]]
    assert notes == ["Going ahead; the story review still notes: hook is flat"]


def test_disabling_the_credit_keeps_the_metadata_tag(config, brief, monkeypatch):
    monkeypatch.setenv("REELHIVE_DISABLE_CREDIT", "true")
    svc, _, _ = service(
        config,
        {
            "Script": make_script(brief),  # sized for the time the missing credit gives back
            "ScenePlan": make_plan(brief),
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
        },
    )
    result, events = run(svc, brief)
    assert json.loads((result.run_dir / "spec.json").read_text())["credit"] is None
    assert any("credit disabled" in d["task"] for d in of_type(events, "node.task"))  # plan §3.7: logged
    assert probe(result.video)["comment"] == CREDIT_TEXT


def test_node_errors_fail_the_run(config, brief):
    plan = make_plan(brief)
    plan["scenes"].pop()  # one scene short of the beats
    svc, _, _ = service(config, {"Script": make_script(brief), "ScenePlan": plan, "MusicChoice": MUSIC})
    events = []
    beats = len(make_script(brief)["beats"])
    with pytest.raises(Exception, match=f"returned {beats - 1} scenes for {beats} beats"):
        svc.run(brief, on_event=events.append)
    assert of_type(events, "run.finished")[0]["status"] == "failed"


def test_preview_renders_one_scene_silently(config, brief):
    svc, _, _ = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, _ = run(svc, brief)
    out = svc.preview_scene(result.run_dir, 2)
    assert out == result.run_dir / "previews" / "scene_02.mp4"
    scene = json.loads((result.run_dir / "spec.json").read_text())["scenes"][1]
    assert probe(out)["duration"] == pytest.approx(scene["duration"], abs=0.1)
    assert not list(result.run_dir.glob(".preview_*.json"))  # the temporary spec is cleaned up
    with pytest.raises(ValueError, match="scene 99 does not exist"):
        svc.preview_scene(result.run_dir, 99)


def test_render_progress_is_logged_per_percent_not_per_frame(config, brief):
    def chatty_renderer(spec, out, on_progress):
        for frame in range(2700):  # a 90s video at 30 fps reports every frame
            on_progress(frame / 2699)
        stub_renderer(spec, out, lambda _: None)

    model = FakeModel(
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    svc = Service(config, models={"strong": model, "fast": model}, tts=StubTTS(), renderer=chatty_renderer)
    result, events = run(svc, brief)
    frames = [d for d in of_type(events, "node.task") if d["task"] == "Rendering frames"]
    assert result.status == "done" and len(frames) == 100  # 0% .. 99%
    finalized = [d for d in of_type(events, "node.task") if d["task"] == "Finalizing video frames"]
    assert len(finalized) == 1 and finalized[0]["progress"] == 1.0


def test_the_intro_opens_the_video_and_the_address_shows_twice(config, brief):
    brief.cta_url = "https://www.costhive.dev/pricing/?ref=x"
    svc, _, tts = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, events = run(svc, brief)
    assert result.status == "done"
    spec = json.loads((result.run_dir / "spec.json").read_text())
    assert spec["intro"] == {
        "title": "CostHive",
        "tagline": "Find and fix cloud waste",
        "url": "costhive.dev/pricing",
        "duration": 3.0,
    }
    # The title screen opens the video; the hook follows it.
    assert spec["intro_at"] == 0 and spec["scenes"][0]["start"] == pytest.approx(3.0, abs=1 / 30)
    assert spec["scenes"][-1]["text"]["url"] == "costhive.dev/pricing"
    assert len(tts.calls) == len(spec["scenes"])  # the intro has no narration
    assert probe(result.video)["duration"] == pytest.approx(brief.duration, rel=0.05)
    assert any(d["task"] == "Intro: CostHive" for d in of_type(events, "node.task"))


def test_a_cold_open_plays_the_hook_before_the_intro(config, brief):
    brief.cold_open = True
    svc, _, _ = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, _ = run(svc, brief)
    spec = json.loads((result.run_dir / "spec.json").read_text())
    assert spec["intro_at"] == 1 and spec["scenes"][0]["start"] == 0.0
    # Boundaries snap to whole frames, so the second scene starts within a frame of hook + intro.
    assert spec["scenes"][1]["start"] == pytest.approx(spec["scenes"][0]["duration"] + 3.0, abs=1.5 / 30)


def test_the_briefs_own_intro_text_beats_the_agents(config, brief):
    brief.intro = IntroText(title="ScanComb", tagline="Next-level platform for IT security and compliance")
    svc, _, _ = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, _ = run(svc, brief)
    spec = json.loads((result.run_dir / "spec.json").read_text())
    assert spec["intro"]["title"] == "ScanComb"
    assert spec["intro"]["tagline"] == "Next-level platform for IT security and compliance"


def test_scene_preview_leaves_out_the_intro(config, brief):
    rendered = []

    def recording_renderer(spec, out, on_progress):
        rendered.append(json.loads(spec.read_text()))
        stub_renderer(spec, out, on_progress)

    model = FakeModel(
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    svc = Service(config, models={"strong": model, "fast": model}, tts=StubTTS(), renderer=recording_renderer)
    result, _ = run(svc, brief)
    svc.preview_scene(result.run_dir, 2)
    assert rendered[0]["intro"]["title"] == "CostHive"  # the real video has it
    assert rendered[-1]["intro"] is None and rendered[-1]["scenes"][0]["start"] == 0.0


def test_a_reel_with_an_offer_runs_end_to_end_vertical_safe_and_mastered(config, brief):
    from reelhive.audio.mixer import measure_loudness
    from reelhive.schemas.brief import Brief
    from reelhive.schemas.scene_spec import PLATFORM_SAFE_AREAS

    own = brief.model_dump(exclude_unset=True, exclude={"format"})
    reel = Brief.model_validate(own | {"platform": "reels", "duration": 30, "context": "Launch price: $89."})
    plan = make_plan(reel)
    for scene in plan["scenes"]:  # a punchy shot is read at a glance: the headline alone
        scene.pop("secondary", None)
    plan["scenes"][-2] = {"template": "offer", "headline": "CostHive Pro", "price": "$89", "covers": []}
    svc, _, _ = service(
        config, {"Script": make_script(reel), "ScenePlan": plan, "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    result, events = run(svc, reel)

    assert result.status == "done"
    info = probe(result.video)
    assert info["duration"] == pytest.approx(30, rel=0.05)
    spec = json.loads((result.run_dir / "spec.json").read_text())
    assert (spec["width"], spec["height"]) == (1080, 1920)  # the stand-in renderer draws a small black frame
    assert spec["safe_area"] == PLATFORM_SAFE_AREAS["reels"].model_dump()
    assert spec["motion"]["open"] == 0 and spec["intro"]["duration"] == 1.5 and spec["intro_at"] == 1
    assert spec["captions"] and spec["scenes"][-2]["template"] == "offer"
    assert all(d["passed"] for d in of_type(events, "gate.result"))
    assert float(measure_loudness(result.run_dir / "audio" / "mix.wav")["input_i"]) == pytest.approx(-14, abs=1)


def test_a_finished_video_is_cut_into_a_reel_from_its_own_research_and_script(config, brief):
    from reelhive.core.cut import cut_brief, parent_brief

    svc, _, _ = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    parent, _ = run(svc, brief)
    (parent.run_dir / "research.json").write_text(json.dumps({"product": "CostHive finds cloud waste"}))

    reel = cut_brief(parent_brief(parent.run_dir), platform="reels")
    plan = make_plan(reel)
    for scene in plan["scenes"]:
        scene.pop("secondary", None)
    cutter, model, _ = service(
        config, {"Script": make_script(reel), "ScenePlan": plan, "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    events = []
    result = cutter.cut(parent.run_dir, reel, on_event=events.append)

    assert result.status == "done" and result.run_dir != parent.run_dir
    assert probe(result.video)["duration"] == pytest.approx(30, rel=0.05)
    tasks = [d["task"] for d in of_type(events, "node.task") if d["node"] == "research"]
    assert tasks == ["Using the research of the original video"]  # the website isn't read again
    assert json.loads((result.run_dir / "research.json").read_text())["product"] == "CostHive finds cloud waste"
    spec = json.loads((result.run_dir / "spec.json").read_text())
    assert (spec["width"], spec["height"], spec["captions"]) == (1080, 1920, True)


def test_a_photo_story_is_told_by_a_named_narrator_through_the_users_photos(config, brief, tmp_path):
    from PIL import Image

    from reelhive.schemas.brief import Brief

    folder = tmp_path / "trip"
    folder.mkdir()
    story = Brief.model_validate(
        brief.model_dump(exclude_unset=True)
        | {
            "features": ["The beach", "The dinner"],
            "narrator": "a deadpan nature documentary narrator",
            "voice": {"name": "bm_fable"},
            "visuals": {"source": "images", "images": {"dir": str(folder)}},
        }
    )
    beats = make_script(story)["beats"]
    for n in range(len(beats)):
        Image.new("RGB", (1600, 1200), "navy").save(folder / f"photo-{n + 1}.jpg")
    plan = make_plan(story)
    for n, scene in enumerate(plan["scenes"][:-1], start=1):  # every moment a photo; the closing stays a cta
        scene.clear()
        scene |= {"template": "photo", "headline": "", "motion": "push_in" if n % 2 else "pan_left"}
        scene["visual_request"] = {"kind": "concept", "image": f"photo-{n}.jpg"}
    plan["scenes"][0]["covers"], plan["scenes"][1]["covers"] = [1], [2]
    svc, _, tts = service(
        config, {"Script": make_script(story), "ScenePlan": plan, "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    result, events = run(svc, story)

    assert result.status == "done", [d for d in of_type(events, "gate.result") if not d["passed"]]
    assert set(tts.voices) == {"bm_fable"}  # every beat in the narrator's voice
    spec = json.loads((result.run_dir / "spec.json").read_text())
    photos = [s for s in spec["scenes"] if s["template"] == "photo"]
    assert len(photos) == len(beats) - 1 and all(s["visual"]["source"] == "provided" for s in photos)
    assert [s["motion"] for s in photos[:2]] == ["push_in", "pan_left"]
