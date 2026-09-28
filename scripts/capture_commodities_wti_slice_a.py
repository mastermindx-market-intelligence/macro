"""Capture the real generated WTI view through the canonical evidence owner.

Uses capture_page_evidence's PageDriver seam and manifest, not a new format.
The only setup action beyond that owner is clicking the existing Oil detail tab.
Anonymous ephemeral Chrome; external network is deliberately disabled for this
local build check and every blocked URL is recorded. Not live-provider proof.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as owner


def verify_served_page(body: bytes, expected_sha256: str) -> None:
    """Refuse evidence if the HTTP response is not the bound generated page."""
    if hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError("page identity mismatch: served bytes differ from bound page")


def focus_source_receipt(page, panel) -> None:
    """Exercise keyboard navigation inside the receipt, not a preceding tooltip.

    Shift+Tab from a closed receipt used to focus the unrelated oscillator help
    trigger. Its delayed mobile sheet polluted the later screenshot despite the
    source summary being document.activeElement.
    """
    summary = panel.locator("summary")
    summary.focus()
    page.keyboard.press("Enter")
    assert panel.locator("details").get_attribute("open") is not None
    page.keyboard.press("Tab")
    link = panel.locator('a[href="https://www.eia.gov/petroleum/supply/weekly/"]')
    assert link.evaluate("e => e === document.activeElement"), "source link did not receive keyboard focus"
    page.keyboard.press("Shift+Tab")
    assert summary.evaluate("e => e === document.activeElement"), "focus did not return to source summary"
    page.keyboard.press("Enter")
    assert panel.locator("details").get_attribute("open") is None
    assert summary.evaluate("e => e === document.activeElement && e.matches(':focus-visible')")


def require_clear_source_focus(summary) -> None:
    """Reject an active-but-covered control after screenshot-driven scrolling."""
    clear = summary.evaluate("""e => {
        const r = e.getBoundingClientRect();
        const x = r.left + Math.min(r.width / 2, 100);
        const y = r.top + r.height / 2;
        const top = document.elementFromPoint(x, y);
        return e === document.activeElement && e.matches(':focus-visible') &&
            r.width > 0 && r.height > 0 && top !== null &&
            (top === e || e.contains(top));
    }""")
    assert clear, "source focus is obscured or not visibly focused"


class WtiDriver:
    def __init__(self, **kwargs):
        self.page_sha256 = hashlib.sha256((ROOT / "site/commodities.html").read_bytes()).hexdigest()
        from playwright.sync_api import sync_playwright
        self.manager = sync_playwright().start()
        self.browser = self.manager.chromium.launch(channel="chrome", headless=True)
        self.observer = kwargs.get("observer_config") or owner.DEFAULT_OBSERVER_CONFIG

    def capture(self, *, url, cell, timeout_s):
        state = {"theme": cell.theme, "locale": cell.locale}
        ctx = self.browser.new_context(viewport={"width": cell.width, "height": cell.height},
            locale="zh-CN" if cell.locale == "zh" else "en-US", color_scheme=cell.theme,
            device_scale_factor=1, reduced_motion="reduce")
        ctx.add_init_script(owner.state_seed_source(state))
        blocked, errors, failures = [], [], []
        def route(request):
            if urlparse(request.request.url).hostname in ("127.0.0.1", "localhost"):
                request.continue_()
            else:
                blocked.append(request.request.url)
                request.abort()
        ctx.route("**/*", route)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append({"text": str(e), "source_url": None}))
        page.on("response", lambda r: failures.append({"url": r.url, "status": r.status}) if r.status >= 400 else None)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            assert response and response.ok, "generated page did not load"
            verify_served_page(response.body(), self.page_sha256)
            page.evaluate(owner._APPLY_STATE_SCRIPT, state)
            page.wait_for_timeout(1300)
            page.locator('button[data-det="oil"]').click()
            panel = page.locator('.dpanel[data-detpanel="oil"] .oil-phys')
            panel.wait_for(state="visible")
            panel.scroll_into_view_if_needed()
            applied_force = None
            if cell.force_state:
                applied_force = owner._apply_interaction_force(page, cell.force_state, timeout_ms=5000)
                focus_source_receipt(page, panel)
            observed = page.evaluate(owner._OBSERVER_SCRIPT, self.observer)
            observed.update({
                "selected_commodity": "oil", "interaction_setup": "clicked existing Oil detail tab",
                "evidence_state": panel.get_attribute("data-evidence-state"),
                "source_clock_text": panel.locator('.oil-phys-clocks').inner_text(),
                "document_scroll_width": page.evaluate('document.documentElement.scrollWidth'),
                "document_client_width": page.evaluate('document.documentElement.clientWidth'),
                "external_network": "blocked for local offline test",
                "blocked_external_urls": sorted(set(blocked)),
            })
            assert observed['document_scroll_width'] <= observed['document_client_width'], "horizontal page overflow"
            assert page.locator('.oil-phys:visible').count() == 1
            assert not page.locator('.dpanel[data-detpanel="gold"] .oil-phys').count()
            if not cell.force_state:
                # Verify actual keyboard expansion/collapse, then return to rest.
                summary = panel.locator('summary')
                summary.focus(); page.keyboard.press('Enter')
                assert panel.locator('details').get_attribute('open') is not None
                assert panel.locator('a[href="https://www.eia.gov/petroleum/supply/weekly/"]').is_visible()
                page.keyboard.press('Enter')
                assert panel.locator('details').get_attribute('open') is None
                summary.evaluate('(e) => e.blur()')
                panel.scroll_into_view_if_needed()
                observed['keyboard_details_toggle'] = True
            # Native scrolling centers the review subject above the fixed
            # launcher; no product element, stylesheet or overlay is hidden.
            panel.evaluate("e => e.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'})")
            out = ROOT/'mockups/evidence/commodities-wti-slice-a/sections'
            out.mkdir(parents=True, exist_ok=True)
            panel.screenshot(path=str(out/f'{cell.viewport}-{cell.locale}-{cell.theme}-{cell.force_state.name if cell.force_state else "rest"}.png'))
            if cell.force_state:
                require_clear_source_focus(panel.locator("summary"))
            verify_served_page((ROOT / "site/commodities.html").read_bytes(), self.page_sha256)
            return owner.CellObservation(cell_id=cell.cell_id, loaded=True,
                screenshot_png=page.screenshot(full_page=False), observed=observed,
                console_errors=tuple(errors), failed_responses=tuple(failures),
                applied_theme=page.get_attribute('html','data-theme'),
                applied_locale=page.get_attribute('html','data-lang'), applied_force_state=applied_force)
        except Exception as exc:
            return owner.CellObservation(cell_id=cell.cell_id, loaded=False,
                error=f'{type(exc).__name__}: {exc}', console_errors=tuple(errors), failed_responses=tuple(failures))
        finally:
            ctx.close()

    def close(self):
        self.browser.close()
        self.manager.stop()


if __name__ == '__main__':
    raise SystemExit(owner.main(driver_factory=lambda **kwargs: WtiDriver(**kwargs)))
