"""A story told through the user's photos, by a narrator with a voice of their own."""

import asyncio
import io

import pytest
import yaml
from PIL import Image

from reelhive.agents.critic import hard_checks
from reelhive.agents.plan import PlannedScene, keep_direction
from reelhive.agents.script_writer import ScriptWriterNode, photos_block, photos_for
from reelhive.config import Config
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.core.workspace import Workspace
from reelhive.levels import LEVELS
from reelhive.schemas.brief import Brief, Images
from reelhive.schemas.scene_spec import PhotoScene, PhotoText, SceneSpec, VisualRequest
from reelhive.schemas.voice import Voice
from reelhive.visuals import provided

ORIENTATION, TAKEN_AT = 0x0112, 0x0132


def photo(path, taken: str | None = None, sideways: bool = False, size=(1600, 1200)):
    """A landscape photo with a white band along its top; `sideways` stores it as a phone does, rotated with a tag."""
    image = Image.new("RGB", size, "navy")
    image.paste((255, 255, 255), (0, 0, size[0], 80))
    exif = Image.Exif()
    if taken:
        exif[TAKEN_AT] = taken
    if sideways:
        image, exif[ORIENTATION] = image.rotate(90, expand=True), 6
    image.save(path, "JPEG", exif=exif)
    return path


def test_a_named_voice_brings_its_own_accent_and_gender_even_at_the_low_level(brief):
    assert (Voice(name="bm_fable").gender, Voice(name="bm_fable").accent) == ("male", "uk")
    assert (Voice(name="af_bella", gender="male").gender, Voice(name="af_bella").accent) == ("female", "us")
    with pytest.raises(ValueError):
        Voice(name="hal_9000")
    brief.voice = Voice(name="bm_fable", speed=1.1)
    low = LEVELS["low"].defaults(brief)["voice"]
    assert (low.name, low.accent, low.speed) == ("bm_fable", "uk", 1.0)
    brief.voice = Voice(accent="uk")
    assert LEVELS["low"].defaults(brief)["voice"].accent == "us"  # unchanged: low narrates in the default voice


def test_photos_are_listed_with_when_they_were_taken_and_copied_upright(tmp_path):
    folder = tmp_path / "trip"
    folder.mkdir()
    photo(folder / "b.jpg", "2024:06:02 09:15:00", sideways=True)
    photo(folder / "a.jpg", "2024:06:01 18:40:00")
    photo(folder / "c.jpg")
    entries = provided.catalog(Images(dir=str(folder)))
    assert [(e["image"], e.get("taken")) for e in entries] == [
        ("a.jpg", "2024-06-01 18:40"),
        ("b.jpg", "2024-06-02 09:15"),
        ("c.jpg", None),
    ]
    provided.copy_upright(folder / "b.jpg", tmp_path / "upright.jpg")
    with Image.open(tmp_path / "upright.jpg") as upright:
        assert upright.size == (1600, 1200) and upright.getpixel((800, 20)) == (255, 255, 255)
        assert upright.getexif().get(ORIENTATION) is None
    provided.copy_upright(folder / "a.jpg", tmp_path / "same.jpg")
    assert (tmp_path / "same.jpg").read_bytes() == (folder / "a.jpg").read_bytes()  # upright already: copied as is


def test_studio_uploads_are_turned_upright_and_keep_when_they_were_taken(tmp_path):
    workspace = Workspace(Config(runs_dir=tmp_path / "runs"))
    brief = Brief(audience="Friends", storyline="Our trip", features=["The beach"], closing="Come next time")
    run = workspace.create(brief, start=False)
    data = io.BytesIO()
    photo(data, "2024:06:01 18:40:00", sideways=True)
    workspace.upload(run.id, data.getvalue(), "beach.jpg", caption="Sunset at the beach")
    [saved] = (workspace.path(run.id) / "uploads").glob("*.png")
    with Image.open(saved) as image:
        assert image.size == (1600, 1200) and image.getpixel((800, 20))[:3] == (255, 255, 255)
    assert provided.taken(saved) == "2024-06-01 18:40"


def test_the_writer_sees_the_photos_in_the_order_they_were_taken(tmp_path, brief):
    folder = tmp_path / "trip"
    folder.mkdir()
    photo(folder / "dinner.jpg", "2024:06:01 20:00:00")
    photo(folder / "beach.jpg", "2024:06:01 10:00:00")
    (folder / "captions.yaml").write_text(yaml.safe_dump({"beach.jpg": "Dad asleep under a newspaper"}))
    brief.visuals.images = Images(dir=str(folder))
    brief.narrator = "a deadpan nature documentary narrator"
    ctx = RunContext(tmp_path / "run", brief, EventBus(), {}, None, None)
    asyncio.run(photos_for(ctx))
    block = photos_block(ctx)
    assert block.index("beach.jpg (taken 2024-06-01 10:00): Dad asleep under a newspaper") < block.index("dinner.jpg")
    prompt = ScriptWriterNode().build_prompt(ctx)
    assert "deadpan nature documentary narrator" in prompt and "dinner.jpg" in prompt
    brief.visuals.source = "screenshots"
    ctx.photos = []
    asyncio.run(photos_for(ctx))
    assert photos_block(ctx) == ""


def test_a_planned_photo_keeps_its_camera_move_through_a_repair():
    planned = PlannedScene(
        template="photo", headline="", motion="pan_left", visual_request={"kind": "concept", "image": "beach.jpg"}
    )
    scene = planned.to_scene(1, "And here, the rare tourist.")
    assert isinstance(scene, PhotoScene) and scene.motion == "pan_left" and scene.text.headline == ""
    repair = PlannedScene(template="photo", headline="Day one")
    repaired = repair.to_scene(1, "x")
    keep_direction(repair, repaired, scene)
    assert repaired.motion == "pan_left" and repaired.visual_request.image == "beach.jpg"


def test_a_photo_needs_its_picture_and_appears_once(brief):
    def shot(index, name):
        request = VisualRequest(kind="concept", image=name)
        return PhotoScene(index=index, narration="x", text=PhotoText(), visual_request=request)

    spec = SceneSpec(scenes=[shot(1, "beach.jpg"), shot(2, "cat.jpg"), shot(3, "beach.jpg")])
    failed = {c.name: c.message for c in hard_checks(spec, brief, {}) if not c.passed}
    assert "beach.jpg" in failed["repeats"] and "cat.jpg" not in failed["repeats"]
    assert "[1, 2, 3]" in failed["images"]  # none resolved to a picture
