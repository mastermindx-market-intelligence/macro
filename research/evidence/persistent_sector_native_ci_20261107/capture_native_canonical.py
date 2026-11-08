"""Reproduce native Sector Central evidence with the incumbent page capture tool.

This bounded fixture driver serves the existing full-template probe and captured
preview API bytes. It does not contact production or establish authentication.
The house capture tool owns the matrix, interaction, screenshot and manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--generation-wire", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    root = args.repo.resolve()
    out = args.output.resolve()
    if out.exists():
        raise SystemExit("Choose a new evidence directory; existing receipts are not overwritten.")
    sys.path.insert(0, str(root))
    from scripts import capture_page_evidence as capture

    spec = importlib.util.spec_from_file_location(
        "leadership_evidence_probe", root / "tests/probe_leadership_evidence_browser.py"
    )
    probe = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(probe)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert head == args.source_sha, (head, args.source_sha)
    raw = args.generation_wire.read_bytes()
    wire = json.loads(raw)
    assert wire["schema"] == "sector_generation.read/v1" and wire["audience"] == "preview"
    receipt = wire["projection"]["receipt"]
    html = probe._html("en", "dark", full_page=True, native_generation=True)
    requests: list[dict] = []
    observations: list[dict] = []
    asset_requests: list[dict] = []
    full_route = probe._route(
        None, "en", "dark", full_page=True,
        requests=asset_requests, native_generation=True,
    )

    def fixture_route(route):
        url = urlsplit(route.request.url)
        if url.scheme != "http" or url.netloc != "leadership-evidence.test":
            route.abort()
            return
        if url.path == "/sector_central.html":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
        elif url.path == "/api/sector-generation":
            assert route.request.method == "GET"
            assert parse_qs(url.query) == {"audience": ["preview"]}
            requests.append({"method": "GET", "path": url.path, "query": url.query})
            route.fulfill(
                status=200, content_type="application/json; charset=utf-8",
                headers={"Cache-Control": "private, no-store", "Vary": "Cookie"}, body=raw,
            )
        else:
            full_route(route)

    class Page:
        def __init__(self, page):
            self.page = page

        def __getattr__(self, name):
            return getattr(self.page, name)

        def goto(self, *positional, **kwargs):
            response = self.page.goto(*positional, **kwargs)
            self.page.wait_for_selector('#si-measured[data-native-state="ready"]')
            return response

        def screenshot(self, *positional, **kwargs):
            page = self.page
            assert page.locator("#mr-list .mr-row").count() == 11
            assert page.locator("#mr-exact [data-exact-window]").count() == 3
            assert page.locator("#si-measured").get_attribute("data-native-generation") == receipt["generation_id"]
            assert page.locator("#si-measured").get_attribute("data-native-content") == receipt["content_sha256"]
            facts = page.evaluate("""() => ({
                theme: document.documentElement.dataset.theme,
                locale: document.documentElement.lang,
                width: innerWidth,
                overflow: document.documentElement.scrollWidth - innerWidth,
                radii: Object.fromEntries(['.mr-exact', '.mr-xselect', '.mr-xwindow', '.mr-cl-members li']
                    .map(s => [s, getComputedStyle(document.querySelector(s)).borderRadius]))
            })""")
            assert facts["overflow"] <= 1, facts
            assert facts["radii"] == {
                ".mr-exact": "12px", ".mr-xselect": "8px",
                ".mr-xwindow": "8px", ".mr-cl-members li": "8px",
            }, facts
            observations.append(facts)
            return page.screenshot(*positional, **kwargs)

    class Context:
        def __init__(self, context):
            self.context = context

        def __getattr__(self, name):
            return getattr(self.context, name)

        def new_page(self):
            return Page(self.context.new_page())

    class Browser:
        def __init__(self, browser):
            self.browser = browser

        def new_context(self, **kwargs):
            context = self.browser.new_context(**kwargs)
            context.route("**/*", fixture_route)
            return Context(context)

        def close(self):
            self.browser.close()

    def fixture_driver(**kwargs):
        driver = capture.playwright_page_driver(**kwargs)
        driver._browser = Browser(driver._browser)
        return driver

    argv = [
        "--base-url", "http://leadership-evidence.test",
        "--routes", "/sector_central.html?g=XLK#map",
        "--viewports", "desktop,mobile", "--locales", "en,zh", "--themes", "dark,light",
        "--force-state", "measured_hover:hover(#mr-list .mr-row)",
        "--force-state", "context_focus:focus(#mr-context details > summary)",
        "--settle-ms", "1200", "--delay-ms", "0",
        "--output-dir", str(out / "screenshots"),
        "--manifest", str(out / "manifest.json"),
        "--smells", str(out / "smells.json"),
    ]
    code = capture.main(argv, driver_factory=fixture_driver)
    source_paths = [
        "templates/sector_central.html.j2", "templates/theme.css",
        "templates/_sector_prophet_context.js.j2", "tests/probe_leadership_evidence_browser.py",
        "scripts/capture_us_stocks_compression_evidence.py", "scripts/capture_page_evidence.py",
    ]
    sources = {}
    for path in source_paths:
        data = (root / path).read_bytes()
        assert data == subprocess.check_output(["git", "show", head + ":" + path], cwd=root)
        sources[path] = hashlib.sha256(data).hexdigest()
    binding = {
        "source_revision": head,
        "scope": "local full-template native preview fixture; no authenticated production acceptance",
        "capture_argv": argv,
        "source_sha256": sources,
        "rendered_html_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "generation_wire_sha256": hashlib.sha256(raw).hexdigest(),
        "generation_identity": {k: receipt[k] for k in ("generation_id", "content_sha256")},
        "observations": observations,
        "native_requests": requests,
        "fixture_asset_requests": asset_requests,
        "capture_exit": code,
    }
    (out / "source-binding.json").write_text(json.dumps(binding, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"capture_exit": code, "observations": len(observations), "source_revision": head}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
