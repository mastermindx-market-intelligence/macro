#!/usr/bin/env python3
"""Exercise the real Radar page across a failed render using synthetic market inputs.

Run from the repository with Python Playwright/Chromium installed:
  python3 research/design_candidates/production_design_20261102/evidence/d03-radar-render-coherence-20261104/verify_browser.py

This serves a temporary fixture tree on loopback and closes the server/browser at exit.
It does not touch tracked site/data artifacts or contact a production service.
"""
from __future__ import annotations

import contextlib
import functools
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import threading
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
OUTPUT = Path(__file__).resolve().parent / "browser"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "radar_fixture_helpers", ROOT / "tests" / "test_build_leader_radar.py"
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    evidence = {"fixture": "synthetic stale market inputs; not production market data", "states": []}
    with tempfile.TemporaryDirectory(prefix="d03-radar-browser-") as scratch:
        root = helpers._build_fixture_root(Path(scratch), ["NVDA"])
        shutil.copytree(ROOT / "templates", root / "templates")
        for path in (root / "templates").iterdir():
            if path.is_file() and path.suffix in {".css", ".js", ".svg", ".ico"}:
                shutil.copy2(path, root / "site" / path.name)
        assets = root / "templates" / "assets"
        if assets.exists():
            shutil.copytree(assets, root / "site" / "assets", dirs_exist_ok=True)
        page_file = root / "site" / "leader_radar.html"
        data_file = root / "site" / "leaderradar" / "radar.json"
        template = root / "templates" / "leader_radar.html.j2"
        template_source = template.read_bytes()

        first = helpers._run_build_no_lane(root)
        assert page_file.is_file()
        initial_hashes = {"html": digest(page_file), "json": digest(data_file)}

        handler = functools.partial(QuietHandler, directory=str(root / "site"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/leader_radar.html"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
                    context.add_init_script("""
                        if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light');
                        if (!localStorage.getItem('lang')) localStorage.setItem('lang', 'en');
                    """)
                    context.route("**/*", lambda route: (
                        route.continue_() if route.request.url.startswith(
                            f"http://127.0.0.1:{server.server_port}/"
                        ) else route.abort()
                    ))
                    page = context.new_page()
                    page_errors = []
                    page.on("pageerror", lambda error: page_errors.append(str(error)))

                    def observe(name, expected_as_of, language="en"):
                        response = page.goto(url, wait_until="load")
                        assert response.status == 200
                        page.locator(".lr-eyebrow").wait_for(state="visible")
                        visible = page.locator(".page-wrap").inner_text()
                        clock = date.fromisoformat(expected_as_of)
                        token = (
                            f"Data through {clock.strftime('%b')} {clock.day} close"
                            if language == "en" else f"数据截至{clock.month}月{clock.day}日收盘"
                        )
                        assert token in visible, (name, token, visible[:1800])
                        fetched = context.request.get(
                            f"http://127.0.0.1:{server.server_port}/leaderradar/radar.json"
                        )
                        assert fetched.status == 200
                        published = fetched.json()
                        assert published["as_of"] == expected_as_of
                        page.screenshot(path=str(OUTPUT / f"{name}.png"), animations="disabled")
                        result = {
                            "name": name, "viewport": page.viewport_size,
                            "title": page.title(), "heading": page.locator(".lr-eyebrow").inner_text(),
                            "freshness_text": page.locator(".header-meta").inner_text(),
                            "visible_price_token": token, "json_as_of": published["as_of"],
                            "language": language, "theme": page.locator("html").get_attribute("data-theme"),
                            "json_built_at": published["built_at"],
                            "html_sha256": digest(page_file), "json_sha256": digest(data_file),
                            "page_errors": list(page_errors),
                        }
                        evidence["states"].append(result)
                        return page.locator(".header-meta").inner_text()

                    before_text = observe("01-before-failure-desktop", first["as_of"])

                    # Advance the fixture input vintage, then break only the template.
                    helpers._write_spy(root, n=401)
                    helpers._write_ohlcv(root, "NVDA", helpers._make_ohlcv(401, seed=0))
                    template.write_text("{% if %}")
                    warnings = io.StringIO()
                    with contextlib.redirect_stdout(warnings):
                        candidate = helpers._run_build_no_lane(root)
                    assert candidate["as_of"] != first["as_of"]
                    assert digest(page_file) == initial_hashes["html"]
                    assert digest(data_file) == initial_hashes["json"]
                    assert "unchanged" in warnings.getvalue()
                    after_text = observe("02-after-failure-desktop", first["as_of"])
                    assert after_text == before_text
                    evidence["failed_candidate_as_of"] = candidate["as_of"]
                    evidence["failure_warning"] = warnings.getvalue().splitlines()

                    template.write_bytes(template_source)
                    repaired = helpers._run_build_no_lane(root)
                    assert repaired["as_of"] == candidate["as_of"]
                    assert digest(page_file) != initial_hashes["html"]
                    assert digest(data_file) != initial_hashes["json"]
                    observe("03-after-recovery-desktop", repaired["as_of"])
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.evaluate("localStorage.setItem('lang', 'zh'); localStorage.setItem('theme', 'dark')")
                    observe("04-after-recovery-mobile", repaired["as_of"], language="zh")
                    assert not page_errors, page_errors
                    assert not list((root / "site").glob(".leader_radar-*.html"))
                    assert not list(data_file.parent.glob(".radar-*.json"))
                    evidence["result"] = "PASS: failed rendering preserves the served pair; repaired render advances both"
                    (OUTPUT / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
                    print(json.dumps(evidence, indent=2))
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
