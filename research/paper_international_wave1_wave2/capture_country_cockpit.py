"""Capture the isolated International fixture with the canonical evidence owner.

Uses capture_page_evidence.py's real Playwright driver, state application,
measurement, PNG and manifest lifecycle. Chrome starts in fresh anonymous
contexts. Only the built International HTML and local template assets are
served; all external requests are aborted. This does not capture production.
"""
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture

OUTPUT = ROOT / "research/paper_international_wave1_wave2/country_cockpit_preview"
ASSETS = (ROOT / "templates").resolve()


class IsolatedBrowser:
    def __init__(self, browser, html):
        self.browser = browser
        self.html = html

    def new_context(self, **kwargs):
        context = self.browser.new_context(**kwargs)

        def serve(route):
            url = urlparse(route.request.url)
            if url.scheme != "http" or url.hostname != "intl.test":
                return route.abort()
            if url.path == "/intl.html":
                return route.fulfill(body=self.html, content_type="text/html")
            path = (ASSETS / unquote(url.path).lstrip("/")).resolve()
            if not path.is_relative_to(ASSETS):
                return route.abort()
            if path.is_file():
                return route.fulfill(path=str(path))
            return route.fulfill(status=404, body="")

        context.route("**/*", serve)
        return context

    def close(self):
        self.browser.close()


def real_chrome_driver(*, headless, user_agent, observer_config, settle_ms):
    from playwright.sync_api import sync_playwright
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(channel="chrome", headless=headless)
    except Exception as exc:
        manager.stop()
        raise capture.CaptureUnavailable(str(exc)) from exc
    routed = IsolatedBrowser(browser, (OUTPUT / "intl_integrated_preview.html").read_text())
    return capture._PlaywrightDriver(
        manager, routed, user_agent, observer_config, settle_ms
    )


if __name__ == "__main__":
    raise SystemExit(capture.main(sys.argv[1:], driver_factory=real_chrome_driver))
