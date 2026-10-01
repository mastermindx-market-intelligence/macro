"""Browser contract for the R23/R24 selected-path Brain handoff.

Every owner value in this test is synthetic. The test exercises the current
``templates/ontology.js`` and ``templates/ontology.css`` against a snapshot
composed by the real read-only ontology composer, then uses a tiny local Brain
loader stub only to observe the page-owned handoff. The shared Brain bundle's
close/fallback behavior is pinned separately in ``test_mm_brain_asset.py``.

The DOM-measured test skips cleanly when Playwright/Chromium is unavailable.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engine.ontology_explorer import compose_snapshot
from tests.ontology_explorer_fixtures import SLUG, build_root

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JS = ROOT / "templates" / "ontology.js"
ONTOLOGY_CSS = ROOT / "templates" / "ontology.css"

SHELL = """<!doctype html>
<html lang="en" data-lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#F7F8FA;--panel:#FFFFFF;--panel-2:#EEF1F6;--text:#1C2430;
  --muted:#5D6B7E;--line:#C9CCD1;--up:#1F9A55;--down:#CF4040;
  --warn:#B9791A;--act:#C43D3D;--ok:#2F8A52;--info:#285FFF;
  --ink-link:#2758E6;--ink-info:#2758E6;--ink-warn:#7D5922;
  --font-ui:Inter,Arial,sans-serif;--font-mono:Menlo,monospace;
  --fs-micro:10px;--fs-label:11px;--fs-sm:12.5px;--fs-body:14px;
  --fs-h2:17px;--fs-h1:28px;--r-ctl:8px;--r-btn:10px;
  --card-shadow:0 8px 24px rgba(28,36,48,.08);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}
#mmb-boot{position:fixed;right:12px;bottom:12px;width:48px;height:48px}
</style>
</head>
<body>
  <button id="mmb-boot" type="button">Brain</button>
  <main class="ox-wrap"><div id="ox-root" aria-busy="true"></div></main>
  <div id="mock-brain" tabindex="-1"></div>
</body>
</html>
"""


@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    manager = sync_playwright()
    try:
        playwright = manager.__enter__()
    except Exception as exc:  # pragma: no cover - runtime-specific
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            launched = playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            launched = playwright.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover - runtime-specific
        manager.__exit__(None, None, None)
        pytest.skip(f"Chromium unavailable: {exc}")
    yield launched
    launched.close()
    manager.__exit__(None, None, None)


@pytest.fixture()
def synthetic_snapshot(tmp_path: Path) -> dict:
    source_root = build_root(tmp_path)
    return compose_snapshot(
        source_root,
        chain=SLUG,
        now=datetime(2026, 1, 4, tzinfo=UTC),
    )


def _open(browser, snapshot: dict, *, width: int, height: int):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.route(
        "http://ontology.test/ontology.html",
        lambda route: route.fulfill(status=200, content_type="text/html", body=SHELL),
    )
    page.goto("http://ontology.test/ontology.html", wait_until="load")
    page.add_style_tag(path=str(ONTOLOGY_CSS))
    page.evaluate(
        """snapshot => {
          window.__brainBoots = 0;
          window.__brainOpens = 0;
          window.fetch = () => Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(snapshot)
          });
          document.getElementById('mmb-boot').addEventListener('click', () => {
            window.__brainBoots += 1;
            window.MMBrain = {
              mounted: true,
              open: () => { window.__brainOpens += 1; }
            };
            window.MMBrain.open();
          });
        }""",
        snapshot,
    )
    page.add_script_tag(path=str(ONTOLOGY_JS))
    page.wait_for_selector("#ox-steps .ox-leg", state="attached")
    page.evaluate("document.getElementById('ox-steps').open = true")
    page.wait_for_selector("#ox-steps .ox-brain-action", state="visible")
    return context, page


@pytest.mark.parametrize("size", ((1440, 900), (390, 844)))
def test_selected_leg_opens_existing_brain_with_bounded_context_and_exact_return(
    browser,
    synthetic_snapshot: dict,
    size: tuple[int, int],
) -> None:
    context, page = _open(
        browser,
        synthetic_snapshot,
        width=size[0],
        height=size[1],
    )
    try:
        asks = page.locator("#ox-steps .ox-brain-action")
        assert asks.count() == 4
        first = asks.first
        first.scroll_into_view_if_needed()
        box = first.bounding_box()
        assert box is not None and box["height"] >= 44
        if size[0] == 390:
            assert box["width"] >= 300

        first.click()
        handoff = page.evaluate(
            """() => ({
              boots: window.__brainBoots,
              opens: window.__brainOpens,
              hash: location.hash,
              ctx: window.MM_BRAIN_CFG.getAiContext()
            })"""
        )
        assert handoff["boots"] == 1
        assert handoff["opens"] == 1
        assert handoff["hash"] == "#ox-leg-n1"
        assert handoff["ctx"]["schema"] == "ai_context_client.v1"
        assert handoff["ctx"]["ambient"] == {
            "symbol": None,
            "timeframe": "rev-2",
            "page": "synthetic-linear-probe",
            "panel": "n1",
        }
        assert handoff["ctx"]["pinned"] == []
        assert handoff["ctx"]["active"] is None

        returned = page.evaluate(
            """() => {
              document.getElementById('mock-brain').focus();
              const ok = window.MM_BRAIN_CFG.onClose();
              return {
                ok,
                focused: document.activeElement.classList.contains('ox-brain-action'),
                cleared: window.MM_BRAIN_CFG.getAiContext().ambient
              };
            }"""
        )
        assert returned["ok"] is True
        assert returned["focused"] is True
        assert returned["cleared"] == {
            "symbol": None,
            "timeframe": None,
            "page": "ontology",
            "panel": None,
        }

        metrics = page.evaluate(
            """() => ({
              scrollWidth: document.documentElement.scrollWidth,
              clientWidth: document.documentElement.clientWidth,
              ontologyStorageKeys: Object.keys(localStorage)
                .concat(Object.keys(sessionStorage))
                .filter(key => key.toLowerCase().includes('ontology'))
            })"""
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"]
        assert metrics["ontologyStorageKeys"] == []
    finally:
        context.close()


def test_mounted_brain_is_reused_without_clicking_the_lazy_loader(
    browser,
    synthetic_snapshot: dict,
) -> None:
    context, page = _open(browser, synthetic_snapshot, width=390, height=844)
    try:
        page.evaluate(
            """() => {
              window.__brainBoots = 0;
              window.__brainOpens = 0;
              window.MMBrain = {
                mounted: true,
                open: () => { window.__brainOpens += 1; }
              };
            }"""
        )
        first = page.locator("#ox-steps .ox-brain-action").first
        first.scroll_into_view_if_needed()
        first.click()
        counts = page.evaluate(
            "() => ({boots: window.__brainBoots, opens: window.__brainOpens})"
        )
        assert counts == {"boots": 0, "opens": 1}
    finally:
        context.close()
