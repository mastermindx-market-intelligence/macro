"""Bounded anonymous production UI proof; never bypass access or rewrite styles/data."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--accepted", required=True)
ap.add_argument("--output", required=True)
args = ap.parse_args()
assert re.fullmatch(r"[0-9a-f]{40}", args.accepted)
root = Path.cwd()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(root / ".cache/playwright"))
origin = "https://www.mastermind-x.com"
cases, errors = [], []
panel_script = """scope => [...scope.querySelectorAll('.aib2-stance,.aib2-lead,.aib2-card')]
 .filter(el => el.getBoundingClientRect().width > 0).map(el => {
 const s = getComputedStyle(el), r = el.getBoundingClientRect();
 return {classes:el.className,left:s.borderLeftWidth,right:s.borderRightWidth,
 leftColor:s.borderLeftColor,rightColor:s.borderRightColor,
 x:r.left,rightEdge:r.right,viewport:innerWidth,background:s.backgroundColor};
 })"""

def capture(page, row, name):
    path = out / (name + ".png")
    page.screenshot(path=str(path), full_page=False)
    row.update(screenshot=path.name, screenshot_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    cases.append(row)
    print(json.dumps({k: row.get(k) for k in ("page", "viewport", "theme", "lang", "status", "screenshot")}), flush=True)

def goto(page, route):
    response = page.goto(origin + route, wait_until="domcontentloaded", timeout=45000)
    assert response and response.status == 200, (route, response.status if response else None)
    page.wait_for_timeout(700)

def preference(page, selector):
    target = page.locator(selector).first
    if not target.is_visible():
        page.locator(".nav-settings-btn").first.click()
        target.wait_for(state="visible")
    return target

def set_preferences(page, theme, lang):
    if page.locator("html").get_attribute("data-theme") != theme:
        preference(page, ".theme-switch").click()
        page.wait_for_function("(t)=>document.documentElement.dataset.theme===t", arg=theme)
    if (page.locator("html").get_attribute("data-lang") or "en") != lang:
        preference(page, ".lang-toggle").click()
        page.wait_for_function("(l)=>document.documentElement.dataset.lang===l", arg=lang)
    menu = page.locator(".nav-settings-btn[aria-expanded=true]")
    if menu.count():
        menu.first.click()
    page.wait_for_timeout(300)

def check_panels(panels):
    assert panels, "No visible brief panels"
    assert all(p["left"] == p["right"] and p["leftColor"] == p["rightColor"] for p in panels), panels
    assert all(p["x"] >= -1 and p["rightEdge"] <= p["viewport"] + 1 for p in panels), panels

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    version = browser.version
    for viewport in [dict(width=1440, height=900), dict(width=390, height=844)]:
        for theme in ["dark", "light"]:
            for lang in ["en", "zh"]:
                context = browser.new_context(viewport=viewport, color_scheme=theme, reduced_motion="reduce")
                page = context.new_page()
                row = dict(page="/aibrief.html", viewport=viewport, theme=theme, lang=lang)
                try:
                    goto(page, row["page"])
                    set_preferences(page, theme, lang)
                    panels = page.locator("body").evaluate(panel_script)
                    check_panels(panels)
                    page.locator(".aib2-stance:visible,.aib2-lead:visible,.aib2-card:visible").first.scroll_into_view_if_needed()
                    row.update(status="passed", panels=panels)
                    capture(page, row, f"brief-{viewport['width']}-{theme}-{lang}")
                except Exception as exc:
                    errors.append(dict(case=row, error=type(exc).__name__ + ": " + str(exc)))
                finally:
                    context.close()
        context = browser.new_context(viewport=viewport, reduced_motion="reduce")
        page = context.new_page()
        try:
            goto(page, "/products/market-terminal.html")
            chapter = page.locator(".chap-x.on").evaluate("""el=>({
              weight:getComputedStyle(el).fontWeight,after:getComputedStyle(el,'::after').content})""")
            assert chapter == dict(weight="800", after="none"), chapter
            selected = page.locator(".mt-wl .r.sel").first
            selected.scroll_into_view_if_needed()
            state = selected.evaluate("""el=>{const s=getComputedStyle(el);return {
              shadow:s.boxShadow,left:s.borderLeftWidth,right:s.borderRightWidth,
              symbolWeight:getComputedStyle(el.querySelector('.sy')).fontWeight};}""")
            assert "inset" in state["shadow"] and "0px 0px 0px 1px" in state["shadow"], state
            assert state["left"] == state["right"] and int(state["symbolWeight"]) >= 700, state
            capture(page, dict(page="/products/market-terminal.html", viewport=viewport,
                theme=page.locator("html").get_attribute("data-theme"), lang="en",
                status="passed", chapter=chapter, selected=state), f"terminal-{viewport['width']}")
        except Exception as exc:
            errors.append(dict(case=dict(page="/products/market-terminal.html", viewport=viewport),
                error=type(exc).__name__ + ": " + str(exc)))
        finally:
            context.close()
        context = browser.new_context(viewport=viewport, color_scheme="dark", reduced_motion="reduce")
        page = context.new_page()
        try:
            goto(page, "/macro.html")
            set_preferences(page, "dark", "en")
            page.locator('[onclick*="mx5OpenDlg"][onclick*="dlg-aibrief"]').first.click()
            page.wait_for_timeout(1000)
            dialog = page.locator("#dlg-aibrief")
            row = dict(page="/macro.html", viewport=viewport, theme="dark", lang="en")
            if dialog.is_visible():
                panels = dialog.evaluate(panel_script)
                check_panels(panels)
                row.update(status="passed", panels=panels, access="anonymous real card click")
                capture(page, row, f"macro-dialog-{viewport['width']}")
                dialog.locator(".mx5-dlg-close").click()
                dialog.wait_for(state="hidden")
                row["close_verified"] = True
            else:
                visible_dialogs = page.locator('[role="dialog"]:visible').all_text_contents()
                row.update(status="dialog_not_opened", access="anonymous; no entitlement override",
                    observed_dialog_text=[s[:1200] for s in visible_dialogs])
                capture(page, row, f"macro-access-{viewport['width']}")
        except Exception as exc:
            errors.append(dict(case=dict(page="/macro.html", viewport=viewport),
                error=type(exc).__name__ + ": " + str(exc)))
        finally:
            context.close()
    browser.close()
report = dict(schema="mastermind.container_edge_production_browser.v1",
    observed_at=datetime.now(timezone.utc).isoformat(), accepted_commit=args.accepted,
    origin=origin, browser="Chromium " + version,
    honesty="Fresh anonymous contexts; normal public URLs; actual theme/language/card controls. No account, injected entitlement, response interception, style override, or market-data mutation. Reduced motion is a browser preference. Macro dialog access limitations are recorded separately from successful panel checks.",
    cases=cases, errors=errors, completed_panel_checks=sum(r["status"] == "passed" for r in cases),
    passed=not errors and all(r["status"] == "passed" for r in cases),
    dialog_access_limits=sum(r["status"] == "dialog_not_opened" for r in cases))
(out / "browser-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(dict(passed=report["passed"], cases=len(cases), errors=len(errors),
    dialog_access_limits=report["dialog_access_limits"])), flush=True)
raise SystemExit(0 if report["passed"] else 1)
