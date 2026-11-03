"""Verify in-place Plan failure/retry with the real detail template, CSS and UI owners.

Uses an explicitly synthetic, anonymous fixture, with all external requests blocked.
This is not an authenticated account, native producer or production acceptance.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace", type=Path, required=True)
cli.add_argument("--output", type=Path, required=True)
args = cli.parse_args()
root = args.workspace.resolve()
sys.path.insert(0, str(root))
from tests.test_dashboard_template_render import _base_vm, _env
from tests.test_prophet_plan_relation import _lfus_book, _relation
from tests.test_prophet_setup_sections import _body_html

head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
paths = ["templates/dashboard.html.j2", "templates/_prophet_setup_detail.html.j2",
         "templates/_prophet_workspace.css.j2", "templates/theme.js", "templates/theme.css"]
hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
for path, digest in hashes.items():
    assert hashlib.sha256(subprocess.check_output(["git", "show", head + ":" + path], cwd=root)).hexdigest() == digest, path
source = (root / paths[0]).read_text()
theme = (root / "templates/theme.js").read_text()
marker = "/* Packet2: enhance existing entitled row details;"
dialog_owner = marker + theme.split(marker, 1)[1]
def script_at(marker):
    at = source.index(marker)
    start = source.rfind("<script>", 0, at) if marker.startswith("P0 #6185") else source.index("<script>", at)
    end = source.index("</script>", start)
    return source[start + len("<script>"):end]
navigation = script_at("P0 #6185 — Candidates | Plans source toggle")
lifecycle = script_at("P-MP1-SHELL §7 — the lifecycle ladder's filter + URL law")
rendered = _env().get_template("dashboard.html.j2").render(**_base_vm(), mode="stocks")
styles = "\n".join(s.get_text() for s in BeautifulSoup(rendered, "html.parser").select("style"))
styles = (root / "templates/theme.css").read_text() + "\n" + styles
detail = str(_body_html(plan_rel=_relation(_lfus_book())))
body = """
<main class="wrap"><h1>Prophet interaction fixture · synthetic data</h1>
<section id="us-standouts" class="panel notable" data-prophet-src="candidates"
 data-board-asof="2026-10-09" data-lifef="resolved">
 <div class="pb-hdrow"><span id="us-src-toggle" class="st-view-toggle" role="group">
  <button type="button" data-src="candidates">Screener</button>
  <button type="button" data-src="plans">Plans</button>
 </span></div>
 <div class="nb-grid-section" id="us-candidates"><div class="nbgrid" id="us-cand-grid">
  <article id="pv-card-LFUS" class="pvcard pv-has-setup po-card" data-ticker="LFUS">
   <a class="pv-setup-stock-link" href="stock.html#LFUS">LFUS · synthetic candidate</a>
   <details class="pv-setup-inline" data-setup-ticker="LFUS">
    <summary class="po-setup">View setup / 查看形态</summary>
    __DETAIL__
   </details>
  </article>
 </div></div>
 <section id="us-plan-block"><button id="us-life-clear" type="button" hidden>Clear filter</button>
  <p id="us-life-filter-zero" hidden>No matching plans</p>
  <div id="us-life-grid" class="nbgrid">
   <article id="pv-LFUS-BULL-20260810" class="pvcard pv-record sm-hidden sm-reveal"
    data-ticker="LFUS" data-record-only="1" data-life="entered">
    <a class="pv-record-link" href="stock.html#LFUS">LFUS · synthetic model record</a>
   </article>
  </div>
 </section>
</section></main>
""".replace("__DETAIL__", detail)
args.output.mkdir(parents=True, exist_ok=False)
report = {"source_head": head, "source_sha256": hashes,
          "scope": "Synthetic anonymous fixture; actual template/CSS/dialog/lifecycle/navigation owners; no live/authenticated acceptance",
          "cases": []}
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for width, theme_name, locale in [(1440, "light", "en"), (1440, "dark", "zh"),
                                       (390, "light", "en"), (320, "dark", "zh")]:
        label = f"{width}-{theme_name}-{locale}"
        ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 1000 else 844},
                                  color_scheme=theme_name, locale="zh-CN" if locale == "zh" else "en-US",
                                  service_workers="block")
        html = ('<!doctype html><html lang="' + locale + '" data-lang="' + locale +
                '" data-theme="' + theme_name + '"><head><meta charset="utf-8"><style>' +
                styles + '</style></head><body class="page-stocks">' + body + '<script>' +
                dialog_owner + '\n' + lifecycle + '\n' + navigation + '</script></body></html>')
        ctx.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
                  if route.request.url == "https://prophet.fixture.test/us_stocks.html" else route.abort())
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("https://prophet.fixture.test/us_stocks.html", wait_until="domcontentloaded")
        page.locator("#pv-card-LFUS > details.pv-setup-inline > summary").click()
        dialog = page.locator("#pv-setup-dialog[open]")
        dialog.locator('[role="tab"][aria-controls$="-sources-panel"]').click()
        link = dialog.locator(".pvs-plan-link")
        link.scroll_into_view_if_needed()
        link.focus()
        before = page.evaluate("""() => ({
          dialogScroll: document.querySelector('#pv-setup-dialog').scrollTop,
          pageScroll: scrollY,
          target: document.querySelector('#pv-setup-dialog .pvs-plan-link').getAttribute('data-pvs-plan-target')
        })""")
        link.evaluate("(el) => el.setAttribute('data-pvs-plan-target', 'pv-UNAVAILABLE')")
        for attempt in range(2):
            page.keyboard.press("Enter")
            assert dialog.is_visible()
            assert link.evaluate("el => el === document.activeElement")
            assert page.locator("#us-standouts").get_attribute("data-prophet-src") == "candidates"
            assert dialog.locator('[data-pvs-section="sources"]').is_visible()
            assert abs(dialog.evaluate("el => el.scrollTop") - before["dialogScroll"]) <= 1
            assert abs(page.evaluate("scrollY") - before["pageScroll"]) <= 1
            feedback = dialog.locator('.pvs-plan-feedback[data-state="unavailable"]')
            assert feedback.is_visible()
            assert ("not available" if locale == "en" else "无法") in feedback.inner_text()
            assert page.locator("[data-pvs-return]").count() == 0
        shot = args.output / ("plan-unavailable-" + label + ".png")
        page.screenshot(path=str(shot))
        link.evaluate("(el, target) => el.setAttribute('data-pvs-plan-target', target)", before["target"])
        page.keyboard.press("Enter")
        assert page.locator("#pv-setup-dialog").evaluate("el => !el.open")
        assert page.locator("#us-standouts").get_attribute("data-prophet-src") == "plans"
        card = page.locator("#" + before["target"])
        assert card.is_visible() and card.evaluate("el => el === document.activeElement")
        assert page.locator("#us-life-filter-zero").evaluate("el => el.hidden"), "no false zero state after preflight"
        assert page.locator(".pvs-plan-feedback").inner_text() == ""
        back = page.locator("[data-pvs-return]")
        assert back.count() == 1
        back.focus()
        page.keyboard.press("Enter")
        assert dialog.is_visible()
        assert dialog.locator('[data-pvs-section="sources"]').is_visible()
        assert link.evaluate("el => el === document.activeElement")
        assert abs(dialog.evaluate("el => el.scrollTop") - before["dialogScroll"]) <= 1
        assert abs(page.evaluate("scrollY") - before["pageScroll"]) <= 1
        assert page.locator("#us-standouts").get_attribute("data-prophet-src") == "candidates"
        assert page.locator("[data-pvs-return]").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
        assert not errors, errors
        report["cases"].append({"case": label, "passed": True, "keyboard_retry_and_return": True,
                                "same_sources_section_focus_scroll": True, "false_zero_state": False,
                                "page_errors": errors, "screenshot": shot.name,
                                "sha256": hashlib.sha256(shot.read_bytes()).hexdigest()})
        (args.output / "qa.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print("PASS", label, flush=True)
        ctx.close()
    browser.close()
assert hashes == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
print("PLAN_RECOVERY_BROWSER_PASS", flush=True)
