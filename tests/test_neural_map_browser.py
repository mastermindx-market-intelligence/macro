"""Real-browser regression journeys for the shared Neural Web map.

Run with pytest tests/test_neural_map_browser.py after Playwright/Chromium are
installed. No sessions, credentials, or production endpoints are used.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import threading
from pathlib import Path

import pytest

if os.environ.get("MM_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright
else:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

from tests.neural_map_fixture import write_fixture


class FixtureHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.path = self.path.replace("/research-tools/", "/", 1)
        return super().do_GET()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def origin(tmp_path_factory):
    directory = (Path(os.environ["NEURAL_MAP_FIXTURE_DIR"]) if os.environ.get("NEURAL_MAP_FIXTURE_DIR")
                 else write_fixture(tmp_path_factory.mktemp("neural-map")))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(FixtureHandler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def loaded(page, origin, path="committee.html"):
    page.goto(f"{origin}/{path}")
    page.locator('[data-neural-map-version="living-map-v1"]').wait_for()
    page.wait_for_function("document.querySelector('#graph_canvas').width > 0")


def pixels(page):
    return page.locator("#graph_canvas").evaluate("c => c.toDataURL()")


def select(page, query):
    page.locator("#nm-search").fill(query)
    page.locator(".nm-result").first.click()


def test_search_evidence_keyboard_and_layer(browser, origin):
    page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    loaded(page, origin)
    snapshot = page.request.get(f"{origin}/neuralwebdata/confluence_graph.json").json()
    assert page.locator("time").inner_text() == snapshot["asof"][:10]
    page.locator("#nm-search").fill("US Board")
    page.locator("#nm-search").press("ArrowDown")
    page.keyboard.press("Enter")
    assert page.locator(".nm-inspector h3").inner_text() == "US Board"
    assert page.locator(".nm-inspector h3").evaluate("e => e === document.activeElement")
    page.locator(".nm-inspector [data-node]").first.click()
    assert page.locator(".nm-inspector h3").evaluate("e => e === document.activeElement")
    page.locator("[data-action=clear]").click()
    page.locator("#nm-search").focus()
    page.keyboard.press("Enter")
    assert page.locator(".nm-inspector h3").inner_text() == "Follow your curiosity."
    page.locator("#nm-search").fill("module:")
    page.locator(".nm-result").filter(has_text="Expanded map").first.click()
    assert page.locator("#gc_wire").get_attribute("aria-pressed") == "true"
    page.locator("#gc_wire").click()
    assert page.locator(".nm-inspector h3").inner_text() == "Follow your curiosity."
    # Source notes survive the curated display graph rather than silently
    # becoming claims of validated predictive relationships.
    data = page.request.get(f"{origin}/neuralwebdata/confluence_graph.json").json()
    edge = next(e for e in data["edges"] if e.get("note") and e["edge_type"] in ("confirms", "contradicts"))
    select(page, edge["src"])
    page.locator(".nm-evidence summary").click()
    details = json.loads(page.locator(".nm-evidence pre").inner_text())
    assert any(e.get("note") == edge["note"] and e.get("n") == edge.get("n") for e in details["connections"])
    assert not errors
    page.close()


def test_reduced_motion_controls_repaint_and_drag_does_not_select(browser, origin):
    page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    loaded(page, origin)
    assert page.locator("#gc_pause").is_disabled()
    before = pixels(page)
    page.locator("#gc_plus").click()
    page.wait_for_function("document.querySelector('#gc_fit').textContent !== '100%'")
    page.wait_for_timeout(80)
    assert pixels(page) != before
    page.locator("#graph_canvas").focus()
    before = pixels(page)
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(80)
    assert pixels(page) != before
    box = page.locator("#graph_canvas").bounding_box()
    page.mouse.move(box["x"]+box["width"]/2, box["y"]+box["height"]/2)
    page.mouse.down()
    page.mouse.move(box["x"]+box["width"]+40, box["y"]+box["height"]/2, steps=8)
    page.mouse.up()
    assert page.locator(".nm-inspector h3").inner_text() == "Follow your curiosity."
    page.locator("#gc_fit").click()
    page.wait_for_timeout(80)
    fitted = pixels(page)
    page.locator("#gc_plus").click()
    page.locator("#gc_fit").click()
    page.wait_for_timeout(80)
    assert pixels(page) == fitted
    page.close()


def test_pause_theme_language_resize_and_reinitialization(browser, origin):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    loaded(page, origin)
    page.locator("#gc_pause").click()
    page.wait_for_timeout(80)
    paused = pixels(page)
    page.wait_for_timeout(150)
    assert pixels(page) == paused
    select(page, "US Board")
    page.wait_for_function("document.querySelector('#gc_fit').textContent === '100%'")
    zoom = page.locator("#gc_fit").inner_text()
    page.evaluate("document.documentElement.dataset.theme='light';document.documentElement.dataset.lang='zh'")
    page.wait_for_timeout(80)
    assert page.locator(".nm-inspector h3").inner_text() == "美股板"
    assert page.locator("#gc_pause").get_attribute("aria-pressed") == "true"
    assert page.locator("#gc_fit").inner_text() == zoom
    page.set_viewport_size({"width": 1200, "height": 900})
    page.wait_for_timeout(80)
    assert page.locator("#gc_fit").inner_text() == zoom
    page.evaluate("neuralFixture.reload()")
    page.locator("#nm-search").wait_for()
    assert page.locator("#graph_canvas").count() == 1
    page.close()


def test_mobile_and_shared_iframe(browser, origin):
    page = browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,reduced_motion="reduce")
    loaded(page, origin)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    scene = page.locator(".nm-scene").bounding_box()
    inspector = page.locator(".nm-inspector").bounding_box()
    assert inspector["y"] >= scene["y"]+scene["height"]-1
    select(page, "US Board")
    assert page.locator(".nm-inspector h3").inner_text() == "US Board"
    page.goto(f"{origin}/embed.html")
    frame = page.frame_locator("#nw-synapse-frame")
    frame.locator("#nm-search").wait_for()
    assert page.locator("iframe").get_attribute("allowfullscreen") is not None
    page.evaluate("document.documentElement.dataset.theme='light';document.documentElement.dataset.lang='zh'")
    page.wait_for_timeout(150)
    assert frame.locator("html").get_attribute("data-theme") == "light"
    assert frame.locator("html").get_attribute("data-lang") == "zh"
    assert frame.locator(".nm-disclosure").is_visible()
    height = frame.locator("#graph_wrap").bounding_box()["height"]
    assert page.locator("iframe").bounding_box()["height"] >= height
    page.evaluate("document.documentElement.removeAttribute('data-theme');document.documentElement.removeAttribute('data-lang')")
    page.wait_for_timeout(80)
    assert frame.locator("html").get_attribute("data-theme") is None
    assert frame.locator("html").get_attribute("data-lang") is None
    page.close()


def test_touch_pinch_release_and_offscreen_animation(browser, origin):
    page = browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
    loaded(page, origin)
    assert page.locator("#gc_pause").is_disabled()
    box = page.locator("#graph_canvas").bounding_box()
    x, y = box["x"] + box["width"]/2, box["y"] + box["height"]/2
    cdp = page.context.new_cdp_session(page)
    def touch(kind, points):
        cdp.send("Input.dispatchTouchEvent", {"type":kind,"touchPoints":[{"x":px,"y":py,"id":i} for i,px,py in points]})
    before = pixels(page)
    touch("touchStart", [(1,x-35,y),(2,x+35,y)])
    touch("touchMove", [(1,x-75,y-12),(2,x+75,y+12)])
    touch("touchEnd", [(1,x-75,y-12)])
    touch("touchMove", [(1,x-55,y+8)])
    touch("touchEnd", [])
    page.wait_for_timeout(80)
    assert pixels(page) != before
    assert page.locator(".nm-inspector h3").inner_text() == "Follow your curiosity."
    page.close()
    page = browser.new_page(viewport={"width":1440,"height":900})
    page.add_init_script("window.fixtureFrames=0;const original=requestAnimationFrame;window.requestAnimationFrame=fn=>original.call(window,t=>{window.fixtureFrames++;fn(t)})")
    loaded(page, origin)
    page.evaluate("const spacer=document.createElement('div');spacer.style.height='2000px';document.body.appendChild(spacer);scrollTo(0,1800)")
    page.wait_for_timeout(120)
    count = page.evaluate("fixtureFrames")
    page.wait_for_timeout(120)
    assert page.evaluate("fixtureFrames") == count
    page.evaluate("scrollTo(0,0)")
    page.wait_for_timeout(100)
    assert page.evaluate("fixtureFrames") > count
    page.close()


def test_failed_empty_and_retry_states(browser, origin):
    page = browser.new_page()
    page.route("**/confluence_graph.json",lambda route:route.fulfill(status=503,body="unavailable"))
    page.goto(f"{origin}/committee.html")
    page.locator("[data-graph-retry]").wait_for()
    assert page.locator("#graph_canvas").count() == 0
    page.unroute("**/confluence_graph.json")
    page.locator("[data-graph-retry]").click()
    page.locator("#nm-search").wait_for()
    page.route("**/confluence_graph.json",lambda route:route.fulfill(json={"nodes":[],"edges":[]}))
    page.evaluate("neuralFixture.reload()")
    page.locator("[data-graph-retry]").wait_for()
    assert "No graph snapshot" in page.locator("#graph_wrap").inner_text()
    assert page.locator("#graph_canvas").count() == 0
    page.close()
