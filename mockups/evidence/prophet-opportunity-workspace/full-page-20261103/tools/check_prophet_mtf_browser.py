"""Browser proof for the actual Prophet MTF owner, using synthetic source fixtures.

This is interaction/component evidence, not a production publication build.
All network is fulfilled or blocked locally; no signed-in session is used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = args.workspace.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(root))
from tests.test_dashboard_template_render import _base_vm, _env

template = (root / "templates/dashboard.html.j2").read_text()
marker = "/* TS-U3 dash-tape-band + dash-mtf-section JS"
start = template.index(marker)
owner = template[start:template.index("// See-more folds", start)] + "\n})();"
rendered = _env().get_template("dashboard.html.j2").render(**_base_vm(), mode="stocks")
doc = BeautifulSoup(rendered, "html.parser")
panel = str(doc.select_one("#dash-mtf-section"))
styles = (root / "templates/theme.css").read_text() + "\n" + "\n".join(s.get_text() for s in doc.select("style"))
fixture = {
    "schema": "mtf_upturn.v1", "as_of": "2026-10-30", "universe_n": 2,
    "evaluated_n": 1, "failed_n": 1,
    "tickers": {
        "ACME": {
            "state": "UPTURN_WATCH", "k": 2, "since": "2026-10-29", "htf_coverage": False,
            "legs": {"d_macd": True, "d3_confluence": True, "w_macd": "none", "w2_macd": False},
            "trend": {key: {"pos": False, "bars_since_cross": None} for key in ("d", "d3", "w", "w2")},
            "monthly_phase": 'below_water/rising" onmouseover="alert(1)<img src=x>',
            "basket_ids": ["consumer_staples"],
        },
    },
    "cohort": {"confirmed": [], "watch": ["ACME"]},
}
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width, theme, lang in ((320, "light", "en"), (390, "dark", "zh"),
                               (768, "light", "zh"), (1440, "dark", "en")):
        context = browser.new_context(viewport={"width": width, "height": 960}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        requests = []
        html = (
            '<!doctype html><html data-lang="' + lang + '" data-theme="' + theme + '">'
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'
            + styles + '</style></head><body class="page-stocks"><main style="max-width:1000px;margin:16px auto;padding:0 12px;box-sizing:border-box">'
            + panel + '</main><script>' + owner + '</script></body></html>'
        )

        def route(req):
            url = req.request.url
            if url.endswith("/fixture.html"):
                req.fulfill(status=200, content_type="text/html", body=html)
            elif url.endswith("/stockdata/mtf_upturn.json"):
                requests.append(url)
                if len(requests) == 1:
                    req.fulfill(status=503, content_type="application/json", body='{"error":"private"}')
                else:
                    req.fulfill(status=200, content_type="application/json", body=json.dumps(fixture))
            elif url.endswith("/basketdata/baskets.json"):
                req.fulfill(status=200, content_type="application/json",
                            body='{"baskets":[{"id":"consumer_staples","name":"Consumer staples","name_zh":"必需消费"}]}')
            else:
                req.fulfill(status=404, content_type="application/json", body="{}")

        context.route("**/*", route)
        page.goto("https://prophet.test/fixture.html")
        page.wait_for_function("document.querySelector('#dash-mtf-section').dataset.mtfState==='unavailable'")
        status = page.locator("#dash-mtf-status")
        assert "private" not in status.inner_text()
        assert page.locator("#dash-mtf-body").get_attribute("aria-busy") == "false"
        assert page.locator(".mtf-skel").count() == 0
        retry = page.locator("#dash-mtf-retry")
        assert retry.is_visible() and retry.is_enabled()
        retry.focus()
        assert retry.evaluate("(el)=>el===document.activeElement")
        retry.press("Enter")
        page.wait_for_function("document.querySelector('#dash-mtf-section').dataset.mtfState==='ready'")
        assert page.locator("#dash-mtf-heading").evaluate("(el)=>el===document.activeElement")
        assert retry.is_hidden() and len(requests) == 2
        assert page.locator("#dash-mtf-body").get_attribute("aria-busy") == "false"
        assert page.locator(".dash-mtf-tbl tbody tr").count() == 1
        assert page.locator(".dash-mtf-leg.unknown").count() == 1
        assert ("2W history limited" if lang == "en" else "双周历史不足") in page.locator(".dash-mtf-coverage").inner_text()
        assert page.locator("#dash-mtf-body [onmouseover],#dash-mtf-body img").count() == 0
        visible = status.inner_text()
        assert ("Partial" if lang == "en" else "部分结果") in visible, (width, lang, visible, status.inner_html())
        assert ("qualifying" if lang == "zh" else "部分结果") not in visible
        assert page.locator(".dash-mtf-baskets").inner_text().strip() == ("Consumer staples" if lang == "en" else "必需消费")
        table_region = page.locator(".dash-mtf-scroll")
        assert table_region.get_attribute("role") == "region"
        assert table_region.get_attribute("aria-labelledby") == "dash-mtf-heading"
        assert table_region.get_attribute("tabindex") == "0"
        if width < 640:
            assert page.locator(".dash-mtf-scroll-hint").is_visible()
            table_region.focus()
            table_region.press("ArrowRight")
            page.wait_for_function("document.querySelector('.dash-mtf-scroll').scrollLeft>0")
            sticky_left = page.locator(".dash-mtf-tbl tbody td").first.bounding_box()["x"]
            assert abs(sticky_left - table_region.bounding_box()["x"]) < 4
            table_region.evaluate("(el)=>el.scrollLeft=0")
            page.locator("#dash-mtf-heading").focus()
        overflow = page.evaluate("document.documentElement.scrollWidth>innerWidth")
        assert not overflow and not errors, (width, errors, overflow)
        name = f"mtf-{width}-{theme}-{lang}.png"
        page.screenshot(path=str(out / name), full_page=True)
        checks.append({"width": width, "theme": theme, "language": lang, "requests": len(requests),
                       "state": "ready", "partial_disclosure": True, "focus": "dash-mtf-heading",
                       "overflow": overflow, "errors": errors, "screenshot": name})
        context.close()

    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.route("**/*", lambda req: req.fulfill(status=200, content_type="text/html", body=html))
    page.goto("https://prophet.test/fixture.html")
    assert page.locator("#dash-mtf-section").get_attribute("data-mtf-state") == "idle"
    assert page.locator(".mtf-skel").is_hidden()
    assert page.locator("noscript").is_visible()
    assert "Enable JavaScript" in page.locator("noscript").inner_text()
    checks.append({"javascript": False, "state": "idle", "skeleton_hidden": True, "fallback_visible": True})
    context.close()
    browser.close()

receipt = {"kind": "synthetic-component-interaction-proof", "source_sha256": hashlib.sha256(template.encode()).hexdigest(),
           "checks": checks, "public_network": False}
(out / "qa.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
