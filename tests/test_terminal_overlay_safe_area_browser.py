"""Real Chromium geometry for the persistent parent Terminal return control.

Only the shipping overlay and synthetic documents are served. No account or
live Terminal is used. CDP supplies real CSS env() safe-area values; a computed
sentinel proves that override before any nonocclusion assertion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

if os.environ.get("MM_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright
else:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HOST = "www.mastermind-x.com"
URL = f"https://{HOST}/overlay-geometry.html?return=exact#origin"
DOCUMENT = """<!doctype html>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
:root { --bg:#10151f; --panel:#192231; --panel2:#263348; --text:#f4f7ff;
        --line:#56657a; --link:#88b7ff; --r-btn:10px; }
body { margin:0; min-height:1800px; }
#safe-area-probe { position:fixed; visibility:hidden; pointer-events:none;
  padding-top:env(safe-area-inset-top); padding-left:env(safe-area-inset-left);
  padding-right:env(safe-area-inset-right); }
</style>
<div id="safe-area-probe"></div><button id="launch">Open Terminal</button>
<script src="/terminal_overlay.js"></script>
<script>
document.getElementById('launch').onclick = function () {
  window.MDXTerminalOverlay.open({
    url:'https://app.mastermind-x.com/terminal?symbol=AAPL&embed=dashboard',
    symbol:'AAPL', trigger:this, returnFocus:this
  });
};
</script>
"""
TERMINAL = """<!doctype html><title>Synthetic Terminal</title>
<script>
requestAnimationFrame(function () {
  parent.postMessage({source:'mastermind-terminal',
    type:'terminal:visual-ready',symbol:'AAPL'},'https://www.mastermind-x.com');
});
</script>
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        instance = p.chromium.launch(headless=True)
        yield instance
        instance.close()


def geometry(page):
    return page.evaluate("""() => {
      const back = document.querySelector('.mmto-back');
      const stage = document.querySelector('.mmto-stage');
      const frame = document.querySelector('.mmto-frame');
      const box = el => {
        const r = el.getBoundingClientRect();
        return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
                width:r.width, height:r.height};
      };
      const b = box(back);
      const hit = document.elementFromPoint(b.left+b.width/2, b.top+b.height/2);
      return {back:b, stage:box(stage), frame:box(frame),
        backHit:hit===back || back.contains(hit),
        viewport:{width:innerWidth,height:innerHeight}};
    }""")


def assert_nonoccluding(measured, safe_top, safe_left, safe_right):
    back, stage, frame = (measured[key] for key in ("back", "stage", "frame"))
    assert back["height"] >= 44, measured
    assert back["width"] >= 44, measured
    assert back["top"] >= max(14, safe_top) - 0.5, measured
    assert back["left"] >= max(14, safe_left) - 0.5, measured
    assert back["right"] <= measured["viewport"]["width"] - max(14, safe_right) + 0.5, measured
    assert stage["top"] >= back["bottom"] + 14 - 0.5, measured
    assert frame["top"] >= back["bottom"] + 14 - 0.5, measured
    assert frame["height"] > 0, measured
    assert abs(stage["bottom"] - measured["viewport"]["height"]) <= 0.5, measured
    for edge in ("top", "bottom", "left", "right"):
        assert abs(frame[edge] - stage[edge]) <= 0.5, measured
    assert measured["backHit"], measured


@pytest.mark.parametrize("width", [390, 1440], ids=["mobile", "desktop"])
@pytest.mark.parametrize(
    "safe_top,safe_left,safe_right",
    [(0, 0, 0), (47, 0, 0), (47, 31, 29)],
    ids=["zero-inset", "top-inset", "top-and-side-insets"],
)
def test_return_control_stays_outside_frame_at_actual_height(
    browser, width, safe_top, safe_left, safe_right, record_property,
):
    context = browser.new_context(
        viewport={"width": width, "height": 844},
        is_mobile=width == 390, has_touch=width == 390,
        reduced_motion="reduce",
    )
    overlay = (ROOT / "site/terminal_overlay.js").read_text()

    def route(request):
        parsed = urlsplit(request.request.url)
        if parsed.hostname == HOST and parsed.path == "/overlay-geometry.html":
            request.fulfill(content_type="text/html", body=DOCUMENT)
        elif parsed.hostname == HOST and parsed.path == "/terminal_overlay.js":
            request.fulfill(content_type="application/javascript", body=overlay)
        elif parsed.hostname == "app.mastermind-x.com" and parsed.path == "/terminal":
            request.fulfill(content_type="text/html", body=TERMINAL)
        else:
            request.abort()

    context.route("**/*", route)
    try:
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {
            "top": safe_top, "topMax": safe_top,
            "left": safe_left, "leftMax": safe_left,
            "right": safe_right, "rightMax": safe_right,
            "bottom": 0, "bottomMax": 0,
        }})
        page.goto(URL, wait_until="load")
        observed = page.locator("#safe-area-probe").evaluate("""el => {
          const s=getComputedStyle(el);
          return [parseFloat(s.paddingTop),parseFloat(s.paddingLeft),parseFloat(s.paddingRight)];
        }""")
        assert observed == [safe_top, safe_left, safe_right], observed
        original_history = page.evaluate("() => history.state")
        page.locator("#launch").click()
        page.wait_for_function("""() => {
          const root=document.querySelector('#mm-terminal-overlay');
          const stage=document.querySelector('.mmto-stage');
          return root && root.classList.contains('is-ready') &&
            getComputedStyle(stage).transform === 'none';
        }""")
        normal = geometry(page)
        record_property("normal_geometry", json.dumps(normal, sort_keys=True))
        assert_nonoccluding(normal, safe_top, safe_left, safe_right)

        # Real text wrapping / enlarged type changes the measured control
        # height. No stage rule, offset, or safe-area expression is substituted.
        page.locator(".mmto-back").evaluate("""back => {
          back.style.fontSize='28px';
          back.style.maxWidth='180px';
          back.textContent='Return to the previous market dashboard';
        }""")
        grown = geometry(page)
        record_property("wrapped_geometry", json.dumps(grown, sort_keys=True))
        assert grown["back"]["height"] > normal["back"]["height"], grown
        assert_nonoccluding(grown, safe_top, safe_left, safe_right)

        page.locator(".mmto-back").click()
        page.wait_for_function("() => !window.MDXTerminalOverlay.isOpen()")
        page.wait_for_function(
            "expected => JSON.stringify(history.state) === JSON.stringify(expected)",
            arg=original_history,
        )
        assert page.url == URL
    finally:
        context.close()
