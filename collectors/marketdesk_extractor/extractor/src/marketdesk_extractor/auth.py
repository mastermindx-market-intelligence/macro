"""Playwright session/auth lifecycle.

We use a **persistent browser context** (a real Chromium profile on disk). The user logs
in once, interactively, via ``marketdesk auth`` (headed). Every later run reuses the saved
cookies from that profile — headless, no password ever stored by us.
"""
from __future__ import annotations

import time
from contextlib import AbstractContextManager
from typing import Any

from .config import Config
from .utils import get_logger

log = get_logger("auth")

# A normal desktop UA; the persistent profile already carries one, this is belt-and-braces.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class BrowserSession(AbstractContextManager):
    """Context manager yielding an authenticated Playwright ``BrowserContext``."""

    def __init__(self, cfg: Config, headless: bool | None = None):
        self.cfg = cfg
        self.headless = cfg.headless if headless is None else headless
        self._pw: Any = None
        self.context: Any = None

    def __enter__(self) -> "BrowserSession":
        from playwright.sync_api import sync_playwright

        self.cfg.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        self.context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(self.cfg.profile_dir),
            headless=self.headless,
            user_agent=_UA,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context.set_default_timeout(30_000)
        return self

    def __exit__(self, *exc: Any) -> None:
        try:
            if self.context:
                self.context.close()
        finally:
            if self._pw:
                self._pw.stop()

    # --- session check -----------------------------------------------------
    def is_authenticated(self) -> bool:
        """True iff the session cookie yields a valid API response (not a login redirect)."""
        try:
            resp = self.context.request.post(
                self.cfg.api("latest/latest"),
                data={},
                headers={
                    "Accept": "application/json",
                    "Referer": f"{self.cfg.base_url}/library/browse",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=20_000,
            )
            if not resp.ok:
                return False
            body = resp.json()
            return isinstance(body, list)
        except Exception as e:  # noqa: BLE001 - session probe is best-effort
            log.warning("auth probe failed: %s", e)
            return False


def run_auth_flow(cfg: Config, *, timeout_s: int = 300) -> bool:
    """Open a headed browser, let the user log in, save the session. Returns success."""
    log.info("Launching headed Chromium for interactive login…")
    with BrowserSession(cfg, headless=False) as sess:
        if sess.is_authenticated():
            log.info("Already authenticated — session profile is valid.")
            return True
        page = sess.context.pages[0] if sess.context.pages else sess.context.new_page()
        page.goto(f"{cfg.base_url}/library/browse", wait_until="domcontentloaded")
        print(
            "\n>>> Log in to MarketDesk in the opened browser window.\n"
            ">>> Waiting for a valid authenticated session "
            f"(up to {timeout_s}s)…\n"
        )
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if sess.is_authenticated():
                log.info("Login detected — session saved to profile: %s",
                         cfg.profile_dir)
                return True
            time.sleep(3)
        log.error("Timed out waiting for login.")
        return False
