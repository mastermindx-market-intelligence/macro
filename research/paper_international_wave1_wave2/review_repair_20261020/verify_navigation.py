"""Real Chrome reproductions for the independent country-navigation findings.

Renders the current component source against the retained integrated assessment.
No network, production store or authenticated session is used.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import i18n
from research.paper_international_wave1_wave2.preview_country_cockpit import DOCUMENT
from research.paper_international_wave1_wave2.capture_country_cockpit import IsolatedBrowser

OUT = Path(__file__).resolve().parent
R1 = ROOT / "research/paper_international_wave1_wave2/publisher_reconciliation_20261020/preview"
phase = sys.argv[1]
assert phase in ("before", "after", "final")
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
a = json.loads(((OUT / "preview" if phase == "final" else R1) / "assessment.json").read_text())
html = env.from_string(DOCUMENT).render(intl_analysis=a)
partial = deepcopy(a)
partial["countries"] = [c for c in a["countries"] if c["cc"] == "JP"]
partial["display_countries"] = partial["countries"]
partial["focus_cc"], partial["count"] = "JP", 1
partial_html = env.from_string(DOCUMENT).render(intl_analysis=partial)
(OUT / ("navigation_" + phase + ".html")).write_text(html)
(OUT / ("partial_" + phase + ".html")).write_text(partial_html)
result = {"phase":phase, "started_at":datetime.now(timezone.utc).isoformat(),
          "html_sha256":sha256(html.encode()).hexdigest(), "checks":[], "page_errors":[]}
def snap(page):
    page.evaluate("() => new Promise(requestAnimationFrame)")
    return page.evaluate("""() => ({hash:location.hash,
        open:[...document.querySelectorAll('.imc-country[open]')].map(x=>x.id)})""")
def check(name, actual, expected):
    result["checks"].append({"name":name,"actual":actual,"expected":expected,"passed":actual == expected})
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = IsolatedBrowser(browser, html).new_context(viewport={"width":1440,"height":900})
    page = context.new_page()
    page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
    page.goto("http://intl.test/intl.html")
    page.locator('.imc-country-rail a[data-imc-country="KR"]').click()
    page.locator("#imc-country-JP > summary").click()
    expected = {"hash":"#imc-country-JP", "open":["imc-country-JP"]}
    check("native_summary_updates_url", snap(page), expected)
    page.go_back()
    check("native_summary_back", snap(page), {"hash":"#imc-country-KR","open":["imc-country-KR"]})
    page.go_forward()
    check("native_summary_forward", snap(page), expected)
    page.reload()
    check("native_summary_reload", snap(page), expected)
    for key in ("Enter", "Space"):
        page.locator('.imc-country-rail a[data-imc-country="KR"]').click()
        page.locator("#imc-country-JP > summary").focus()
        page.keyboard.press(key)
        check("summary_keyboard_" + key, snap(page), expected)
    # A second activation retains the native ability to collapse a disclosure.
    page.locator("#imc-country-JP > summary").click()
    check("native_summary_can_collapse", page.locator("#imc-country-JP").get_attribute("open"), None)
    context.close()
    context = IsolatedBrowser(browser, partial_html).new_context(viewport={"width":390,"height":844})
    page = context.new_page()
    page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
    page.goto("http://intl.test/intl.html")
    missing = page.locator('.imc-connections a[data-imc-country]:not([data-imc-country="JP"])').count()
    check("partial_coverage_has_no_dead_country_links", missing, 0)
    # A stale anchor must be harmless even if supplied by old markup.
    page.evaluate("""() => {const a=document.createElement('a');
        a.href='#imc-country-KR'; a.dataset.imcCountry='KR'; a.id='stale-country';
        a.textContent='Stale country reference'; document.querySelector('.imc-connections').append(a);}""")
    page.locator("#stale-country").click()
    check("stale_anchor_does_not_rewrite_url", page.evaluate("location.hash"), "")
    context.close()
    for theme in ("light", "dark"):
        for lang in ("en", "zh"):
            context = IsolatedBrowser(browser, html).new_context(viewport={"width":390,"height":844})
            page = context.new_page()
            page.goto("http://intl.test/intl.html")
            page.evaluate("""({theme,lang}) => {document.documentElement.dataset.theme=theme;
                document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;}""",
                {"theme":theme,"lang":lang})
            page.evaluate("document.fonts.ready")
            page.locator(".imc-nav a").last.focus()
            found = False
            for _ in range(40):
                page.keyboard.press("Tab")
                found = page.evaluate("document.activeElement.matches('.imc-country-rail a')")
                if found:
                    break
            assert found
            page.evaluate("document.activeElement.scrollIntoView({block:'center'})")
            focus = page.evaluate("""() => {const e=document.activeElement,r=e.getBoundingClientRect(),
                c=e.parentElement.getBoundingClientRect(),s=getComputedStyle(e);
                const extent=parseFloat(s.outlineOffset)+parseFloat(s.outlineWidth);
                return {outline:s.outlineStyle,width:s.outlineWidth,offset:s.outlineOffset,
                vertical_ring_inside_scrollport:r.top-extent>=c.top && r.bottom+extent<=c.bottom,
                horizontal_ring_inside_scrollport:r.left-extent>=c.left && r.right+extent<=c.right};}""")
            check("focus_ring_inside_scrollport_"+theme+"_"+lang,
                  focus["vertical_ring_inside_scrollport"] and focus["horizontal_ring_inside_scrollport"], True)
            result.setdefault("focus",[]).append({"theme":theme,"lang":lang,**focus})
            page.screenshot(path=str(OUT / ("focus_"+phase+"_"+theme+"_"+lang+".png")))
            context.close()
    browser.close()
check("no_page_exceptions", result["page_errors"], [])
result["finished_at"] = datetime.now(timezone.utc).isoformat()
result["passed"] = sum(c["passed"] for c in result["checks"])
result["total"] = len(result["checks"])
(OUT / ("navigation_"+phase+".json")).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"phase":phase,"passed":result["passed"],"total":result["total"],
                  "failed":[c["name"] for c in result["checks"] if not c["passed"]],
                  "page_errors":result["page_errors"]}))
if phase in ("after", "final"):
    assert result["passed"] == result["total"]
