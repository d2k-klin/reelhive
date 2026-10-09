"""Force the actual CLI renderer's browser close to stall, then verify automatic recovery."""

import subprocess

import pytest

from reelhive.audio.mixer import probe
from reelhive.config import REPO_ROOT
from reelhive.schemas.scene_spec import Credit, CtaScene, CtaText, SceneSpec

pytestmark = pytest.mark.slow


def test_cli_recovers_when_its_rendering_browser_will_not_close(tmp_path):
    spec = SceneSpec(
        duration=2,
        credit=Credit(mode="corner", duration=0),
        scenes=[CtaScene(index=1, narration="", duration=2, text=CtaText(headline="Ready to watch"))],
    )
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(spec.model_dump_json())
    output = tmp_path / "video.mp4"
    entry = REPO_ROOT / "renderer/render.ts"
    driver = tmp_path / "stalled-close.mts"
    driver.write_text(
        """import {createRequire} from 'node:module';
const entry = process.argv[4];
const require = createRequire(entry);
const rendererRequire = createRequire(require.resolve('@revideo/renderer'));
const puppeteer = rendererRequire('puppeteer').default;
const launch = puppeteer.launch.bind(puppeteer);
puppeteer.launch = async options => {
  const browser = await launch(options);
  const child = browser.process();
  // A test-only fallback also cleans up the browser if the production guard is disconnected again.
  const cleanup = setTimeout(() => child.kill('SIGKILL'), 20000);
  cleanup.unref();
  child.once('exit', () => clearTimeout(cleanup));
  browser.close = () => new Promise(resolve => child.once('exit', resolve));
  return browser;
};
await import(entry);
"""
    )
    result = subprocess.run(
        ["node", "--import", "tsx", str(driver), str(spec_path), str(output), str(entry)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "terminating it" in result.stderr
    assert "done" in result.stdout and "progress 1.000" in result.stdout
    media = probe(output)
    assert media["has_video"] and media["duration"] == pytest.approx(2, abs=0.2)
    assert (media["width"], media["height"]) == (1920, 1080)
