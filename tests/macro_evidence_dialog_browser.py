"""Exercise the Signals dialog through the real rendered macro page in a clean test browser."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from scripts.capture_page_evidence import serve_site_dir
from tests.risk_radar_workspace_browser import render_fixture


def prepare(output, source_ref):
    receipt = render_fixture(output, source_ref)
    # The standard evidence collector visits a standalone, already-open component.
    # The actual entry, tier check, dismissal and return are exercised on macro.html below.
    soup = BeautifulSoup((output / "macro.html").read_text(), "html.parser")
    specimen = BeautifulSoup((output / "risk-radar-component.html").read_text(), "html.parser")
    for script in specimen.select("script"):
        script.decompose()
    dialog = soup.select_one("#dlg-evidence")
    specimen.select_one("#dlg-risk").replace_with(dialog)
    dialog["class"] = ["mx5-dlg", "open", "mx5-dlg-in"]
    specimen.body["class"] = ["page-macro", "mx4-grid", "mx5-dlg-open"]
    specimen.html["class"] = ["mx5-dlg-lock"]
    specimen.title.string = "Evidence breakdown · source-rendered specimen"
    (output / "evidence.html").write_text(str(specimen))
    return receipt


def exercise(output):
    from contextlib import ExitStack

    with ExitStack() as stack:
        server, port = serve_site_dir(output)
        stack.callback(server.server_close)
        stack.callback(server.shutdown)
        runtime = stack.enter_context(sync_playwright())
        origin = f"http://127.0.0.1:{port}"
        browser = runtime.chromium.launch()
        context = browser.new_context(reduced_motion="reduce")
        context.route("**/*", lambda route: route.continue_()
                      if route.request.url.startswith(origin + "/") else route.abort())
        page = context.new_page()
        page.goto(origin + "/macro.html", wait_until="domcontentloaded")
        trigger = page.locator("#sx-evidence .mx5-card-face")
        dialog = page.locator("#dlg-evidence")
        # The fixture has no credentials. Exercise both sides of the host's registration gate.
        page.evaluate("""() => {
            window.MMXAccessPreview = {isAnon: () => true};
            window.MMXSharedShell = {openAuth: () => {window.__signinObserved = true;}};
        }""")
        trigger.focus()
        page.keyboard.press("Enter")
        assert page.evaluate("window.__signinObserved") and not dialog.is_visible()
        page.evaluate("window.MMXAccessPreview.isAnon = () => false")
        page.keyboard.press("Enter")
        dialog.wait_for(state="visible")
        close = dialog.locator(".mx5-dlg-close")
        assert close.evaluate("e => e === document.activeElement")
        sources = dialog.locator(".ev-sources summary")
        page.keyboard.press("Shift+Tab")
        assert sources.evaluate("e => e === document.activeElement")
        page.keyboard.press("Tab")
        assert close.evaluate("e => e === document.activeElement")
        risk = dialog.locator("details.ev-factor").nth(1)
        risk.locator("summary").focus()
        page.keyboard.press("Enter")
        assert risk.locator("dd").first.is_visible()
        page.keyboard.press("Enter")
        assert not risk.locator("dd").first.is_visible()
        checks = []
        for width, height in [(1440, 900), (390, 844)]:
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    page.set_viewport_size({"width": width, "height": height})
                    page.evaluate("""([theme,lang]) => {
                        document.documentElement.dataset.theme=theme;
                        document.documentElement.dataset.lang=lang;
                        document.documentElement.lang=lang;
                    }""", [theme, lang])
                    assert dialog.locator("#evidence-title .l-" + lang).is_visible()
                    assert dialog.locator(".mx5-dlg-body").evaluate("e => e.scrollWidth <= e.clientWidth+1")
                    assert dialog.locator(".mx5-dlg-panel").evaluate(
                        "e => e.getBoundingClientRect().left >= -1 && e.getBoundingClientRect().right <= innerWidth+1")
                    checks.append([width, theme, lang])
        sources.click()
        assert dialog.locator(".ev-sources dd").first.is_visible()
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        assert trigger.evaluate("e => e === document.activeElement")
        assert not page.evaluate("document.documentElement.classList.contains('mx5-dlg-lock')")
        browser.close()
        return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-ref", default="HEAD")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        directory = args.output or Path(temporary)
        receipt = prepare(directory, args.source_ref)
        checks = exercise(directory)
        print(json.dumps({"source": receipt["source_ref"], "layout_checks": checks,
                          "registered_entry_and_keyboard_return": "passed"}))
