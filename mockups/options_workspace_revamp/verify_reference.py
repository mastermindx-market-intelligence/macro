"""Isolated content-reference capture over local HTTP only.
No connection to the user's browser/profile; no data: navigation or external egress.
Captures scope main.ref; shared-shell integration requires a separate built-page proof.
"""
import json
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
OUT = HERE / "visual"
OUT.mkdir(exist_ok=True)
ORIGIN = "http://127.0.0.1:8768"
rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width, height in [(1440, 1000), (390, 844)]:
        for theme in ["dark", "light"]:
            for lang in ["en", "zh"]:
                context = browser.new_context(viewport={"width":width,"height":height}, device_scale_factor=1)
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(ORIGIN+"/") else route.abort())
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                url = ORIGIN + "/mockups/options_workspace_revamp/reference.html?" + urlencode({"theme":theme,"lang":lang})
                page.goto(url, wait_until="networkidle", timeout=20000)
                page.wait_for_function("document.fonts.status === 'loaded'", timeout=5000)
                metrics = page.evaluate("""() => ({viewport:innerWidth,scroll:document.documentElement.scrollWidth,
                    documentHeight:document.documentElement.scrollHeight,contentHeight:document.querySelector('main.ref').getBoundingClientRect().height,
                    h1:document.querySelector('h1')?.innerText,tabs:[...document.querySelectorAll('.ref-tab')].length,
                    selected:document.querySelector('.ref-tab[aria-selected=true]')?.dataset.mode})""")
                name = f"brief-{width}-{theme}-{lang}"
                page.locator("main.ref").screenshot(path=str(OUT/(name+".png")))
                if (width,theme,lang) in [(1440,"light","en"),(390,"dark","zh")]:
                    page.evaluate("window.scrollTo(0,0)")
                    page.screenshot(path=str(OUT/("shell-"+name+".png")),full_page=False)
                rows.append({"name":name,**metrics,"overflow":metrics["scroll"]>width+1,"errors":errors,
                    "capture_scope":"main.ref","status":"NOT_APPLIED_TO_PAPER"})
                if width==1440 and theme=="light" and lang=="en":
                    for mode in ["flow","scanner","ticker","leaders"]:
                        page.locator(f'.ref-tab[data-mode="{mode}"]').click()
                        page.locator("main.ref").screenshot(path=str(OUT/(mode+"-1440-light-en.png")))
                    page.locator('.ref-tab[data-mode="brief"]').click()
                    page.locator('.ref-tab[data-mode="brief"]').focus()
                    page.keyboard.press("ArrowRight")
                    assert page.locator('.ref-tab[data-mode="flow"]').get_attribute("aria-selected")=="true"
                context.close()
    browser.close()
(OUT/"reference-report.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
print(json.dumps({"captures":len(rows)+6,"overflow":[r["name"] for r in rows if r["overflow"]],
    "errors":[r for r in rows if r["errors"]],"scope":"main.ref; shared shell not accepted","status":"PROVISIONAL_REFERENCE_ONLY"},indent=2))
