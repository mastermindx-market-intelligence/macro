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

    def _release(self) -> None:
        """Close partial or complete browser state without masking another error."""
        try:
            if self.context is not None:
                try:
                    self.context.close()
                except Exception as e:  # noqa: BLE001 - cleanup is best-effort
                    log.warning("browser context close failed: %s", e)
        finally:
            if self._pw is not None:
                try:
                    self._pw.stop()
                except Exception as e:  # noqa: BLE001 - still clear both references
                    log.warning("playwright driver stop failed: %s", e)
            self.context = None
            self._pw = None

    def __enter__(self) -> "BrowserSession":
        from playwright.sync_api import sync_playwright

        try:
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
        except Exception:
            self._release()
            raise
        return self

    def __exit__(self, *exc: Any) -> None:
        self._release()

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


def library_ready(context: Any, cfg: Config) -> bool:
    """True iff latest IDs work *and* browse returns an array.

    ``is_authenticated`` only probes ``latest/latest``. That stays green during
    the T&Cs overlay that blocks library metadata. Browse goes through the
    client's one-shot ``/terms/consent`` heal, so a True here means intake can
    actually walk the tree.
    """
    from .marketdesk import MarketDeskClient, MarketDeskError, SessionExpired

    client = MarketDeskClient(context, cfg)
    if not client.session_alive():
        return False
    try:
        years = client.browse_current()
        return isinstance(years, list)
    except (SessionExpired, MarketDeskError):
        return False


def try_silent_relogin(context: Any, cfg: Config) -> bool:
    """Best-effort Firebase restore + ``POST /api/user/login``. No password.

    Uses the persistent profile's IndexedDB. Returns True only when the
    subsequent session probe sees an ID array. Missing Playwright page APIs
    (unit-test fakes) are a no-op. Tokens are never logged.
    """
    new_page = getattr(context, "new_page", None)
    if not callable(new_page):
        return False
    page = None
    try:
        page = new_page()
        page.goto(f"{cfg.base_url}/", wait_until="domcontentloaded")
        try:
            page.locator("button.accept-terms").click(timeout=2500)
        except Exception:  # noqa: BLE001 - overlay is optional
            pass
        result = page.evaluate(
            """async () => {
              const fb = window.firebase;
              if (!fb || !fb.auth) return {ok: false, reason: 'no-firebase'};
              const user = await new Promise((resolve) => {
                const existing = fb.auth().currentUser;
                if (existing) { resolve(existing); return; }
                const t = setTimeout(() => resolve(fb.auth().currentUser), 8000);
                const unsub = fb.auth().onAuthStateChanged((u) => {
                  clearTimeout(t); unsub(); resolve(u);
                });
              });
              if (!user) return {ok: false, reason: 'no-user'};
              const token = await user.getIdToken(true);
              const res = await fetch('/api/user/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({F: token})
              });
              let data = null;
              try { data = await res.json(); } catch (e) { data = null; }
              return {ok: !!(data && data.success === true), http: res.status};
            }"""
        )
        ok = bool(isinstance(result, dict) and result.get("ok"))
        if ok:
            log.info("silent Firebase relogin exchanged a fresh MarketDesk session")
        else:
            log.info("silent Firebase relogin did not restore a session")
        return ok
    except Exception as e:  # noqa: BLE001 - silent heal must not kill the daemon
        log.warning("silent relogin failed: %s", e)
        return False
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:  # noqa: BLE001
                pass


def run_auth_flow(
    cfg: Config, *, timeout_s: int = 300, force: bool = False,
) -> bool:
    """Open a headed browser, let the user log in, save the session. Returns success.

    ``force`` skips the 'already authenticated' short-circuit. That short-circuit
    is wrong for the T&Cs overlay: ``latest/latest`` still returns an array, so
    a plain ``marketdesk auth`` would exit without showing a window.
    """
    log.info("Launching headed Chromium for interactive login…")
    with BrowserSession(cfg, headless=False) as sess:
        if not force and library_ready(sess.context, cfg):
            log.info("Already authenticated — library browse is usable.")
            return True
        page = sess.context.pages[0] if sess.context.pages else sess.context.new_page()
        page.goto(f"{cfg.base_url}/", wait_until="domcontentloaded")
        print(
            "\n>>> Log in to MarketDesk in the opened browser window.\n"
            ">>> Waiting until library browse returns report metadata "
            f"(up to {timeout_s}s)…\n"
        )
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                page.locator("button.accept-terms").click(timeout=500)
            except Exception:  # noqa: BLE001
                pass
            if library_ready(sess.context, cfg):
                log.info("Login detected — session saved to profile: %s",
                         cfg.profile_dir)
                return True
            time.sleep(3)
        log.error("Timed out waiting for login.")
        return False
