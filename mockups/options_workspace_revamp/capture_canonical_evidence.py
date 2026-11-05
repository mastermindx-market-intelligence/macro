"""Capture the published Options fixture with the repository's real evidence tool.

Run from any working directory while the existing repository-root QA server is
listening on http://127.0.0.1:8768:

    python3 mockups/options_workspace_revamp/capture_canonical_evidence.py

The canonical tool owns all 24 screenshots and evidence serialization: eight
resting cells plus hover and focus for each cell. This wrapper only installs the
published fixture router in each real browser context. It does not write a
manifest, substitute screenshots, or claim a capture before the browser runs.

Routing source: capture_published_workspace.py, PR #10494 at
ba7947223ae58f436d4cfadbedc28454b10483fc; blob
0d548ce7598a81eaa4920a26c1d537a50cb0bad4. Its handler is copied unchanged because
importing that original command would immediately start its separate capture.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "fixtures" / "published"
ORIGIN = "http://127.0.0.1:8768"
OUTPUT = "mockups/options_workspace_revamp/canonical"


@contextmanager
def repository_directory():
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        yield
    finally:
        os.chdir(previous)


class RouteInstallingBrowser:
    """Delegate to the real browser, installing the router before navigation."""

    def __init__(self, browser, handler):
        self._browser = browser
        self._handler = handler

    def __getattr__(self, name):
        return getattr(self._browser, name)

    def new_context(self, **kwargs):
        # Match the published harness. Service workers must not bypass routing.
        kwargs["service_workers"] = "block"
        context = self._browser.new_context(**kwargs)
        try:
            context.route("**/*", self._handler)
        except BaseException:
            context.close()
            raise
        return context


def fixture_driver_factory(canonical, payloads):
    PAYLOADS = payloads

    # Exact synchronous handler from the published capture command named above.
    def handle(route):
        url=route.request.url.split("?")[0]
        key=next((k for k in PAYLOADS if url.endswith("/"+k)),None)
        if key:route.fulfill(status=200,content_type="application/json",body=json.dumps(PAYLOADS[key]))
        elif route.request.url.startswith(ORIGIN+"/"):route.continue_()
        else:route.abort()

    def factory(**kwargs):
        # Keep every canonical factory argument; do not start a temporary
        # sync_playwright context that would close before capture begins.
        driver = canonical.playwright_page_driver(**kwargs)
        try:
            driver._browser = RouteInstallingBrowser(driver._browser, handle)
        except BaseException:
            driver.close()
            raise
        # canonical.main closes the real driver in its finally block; the real
        # driver closes each context, its browser, and its Playwright manager.
        return driver

    return factory


def load_current_fixture():
    """Require the prepared fixture to match the source being reviewed."""
    required = (SOURCE / "workspace.html", SOURCE / "payloads.json", SOURCE / "manifest.json")
    for path in required:
        if not path.is_file():
            raise SystemExit(f"Missing published fixture file: {path}")
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    for relative, field in (
        ("templates/options.html.j2", "template_sha256"),
        ("scripts/build_options_command.py", "builder_sha256"),
    ):
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if manifest.get(field) != actual:
            raise SystemExit(
                f"Published fixture is stale for {relative}; regenerate it with "
                "prepare_published_fixture.py before capturing."
            )
    payloads = json.loads((SOURCE / "payloads.json").read_text(encoding="utf-8"))
    if not isinstance(payloads, dict) or not payloads:
        raise SystemExit("The published fixture payload map is missing or empty.")
    return payloads


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    payloads = load_current_fixture()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import capture_page_evidence as canonical

    arguments = [
        "--base-url", ORIGIN,
        "--routes", "/mockups/options_workspace_revamp/fixtures/published/workspace.html",
        "--output-dir", OUTPUT + "/evidence",
        "--manifest", OUTPUT + "/manifest.json",
        "--smells", OUTPUT + "/smells.json",
        "--viewports", "desktop,mobile",
        "--locales", "en,zh",
        "--themes", "light,dark",
        "--max-pages", "1",
        "--settle-ms", "1300",
        "--timeout-s", "30",
        "--force-state", "tab_hover:hover(#tab-flow)",
        "--force-state", "tab_focus:focus(#tab-flow)",
    ]
    with repository_directory():
        return canonical.main(
            arguments, driver_factory=fixture_driver_factory(canonical, payloads)
        )


if __name__ == "__main__":
    raise SystemExit(main())
