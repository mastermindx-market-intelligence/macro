"""Reproduce the Risk Radar UI against immutable, committed source snapshots.

Usage: python tests/risk_radar_workspace_browser.py --output /tmp/risk-radar-ui
This never uses a saved browser session, credentials, live market endpoints, or
a deployed preview. The anonymous component harness is for the canonical
capture_page_evidence.py tool. The full-page interaction check separately
simulates registration in an isolated browser to exercise the unchanged modal
controller. Neither fixture is written into site/.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import http.server
import json
from pathlib import Path
import re
import subprocess
import sys
import threading

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def render_fixture(output: Path, source_ref: str) -> dict:
    from tests.test_dashboard_template_render import _base_vm, _env

    output.mkdir(parents=True, exist_ok=True)
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Preview output must be outside the repository")
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "--verify", source_ref + "^{commit}"], cwd=ROOT, text=True
    ).strip()
    inputs = {}

    def snapshot(path):
        raw = subprocess.check_output(["git", "show", f"{source_sha}:{path}"], cwd=ROOT)
        value = json.loads(raw)
        inputs[path] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "as_of": value.get("asof") or value.get("as_of") or value.get("date") or value.get("source_session"),
        }
        return value

    vm = _base_vm()
    vm["latest"].update(snapshot("data/regime/latest.json"))
    vm["market_state"] = snapshot("data/market_state/latest.json")
    vm["risk_envelope"] = snapshot("site/riskdata/risk_envelope.json")
    radar = vm["market_state"]["radar"]
    # The same display-only attachments made by build_site.py. No recomputation.
    contagion = snapshot("data/contagion_links/latest.json")
    radar["contagion"] = (contagion.get("pressure") or {}).get("us")
    cross = vm["latest"].get("cross_asset") or {}
    shadow = snapshot("data/crossasset_shadow/latest.json")
    if cross:
        radar["cross_asset"] = {
            "verdict": cross.get("verdict"),
            "absorption_pctile": cross.get("absorption_pctile_5y"),
            "dominant_cluster": (cross.get("dominant_cluster") or [])[:3],
            "shadow_escalated": shadow.get("escalated"),
        }
    vm["fear_greed"] = snapshot("site/basketdata/fear_greed.json")
    # Keep the separately published appetite lens in the immutable fixture too.
    # The render owner already synthesized it; this harness never recomputes it.
    vm["fear_euphoria"] = snapshot("site/macrodata/macro_signals.json").get("fear_euphoria")
    vm["vol_weather"] = snapshot("site/basketdata/vol_weather.json")
    vm["leadership_crack"] = snapshot("data/leadership_crack/latest.json")
    pulse = snapshot("site/basketdata/sector_pulse.json")
    rotation_ids = ["ai_software", "ai_agents", "non_ai_software", "ai_semiconductors",
                    "ai_infrastructure", "ai_energy", "ai_hardware"]
    themes = {row.get("id"): row for row in pulse.get("themes", [])}
    vm["sector_heat"] = {
        "as_of": pulse.get("as_of"), "heating": [], "cooling": [],
        "rotation": [
            {"id": key, "short_name": themes[key].get("name") or key,
             "short_name_zh": themes[key].get("name_zh") or themes[key].get("name") or key,
             "rank": themes[key].get("rank"), "rank_delta_5d": themes[key].get("rank_delta_5d")}
            for key in rotation_ids if key in themes
        ],
    }
    env = _env()
    env.filters["regex_replace"] = lambda value, pattern, replacement: (
        re.sub(pattern, replacement, value) if isinstance(value, str) else value
    )
    html = env.get_template("dashboard.html.j2").render(**vm, mode="macro")
    (output / "macro.html").write_text(html)
    for path in (ROOT / "site").iterdir():
        target = output / path.name
        if path.name != "macro.html" and not target.exists():
            target.symlink_to(path, target_is_directory=path.is_dir())

    # A public, anonymous component specimen using the real rendered dialog,
    # styles and controller. It is staged directly in its open presentation state;
    # it does not invoke or override the registered page opener. That opener is
    # tested separately below. No sessions, remote scripts, data fetching, or new
    # production route are involved.
    soup = BeautifulSoup(html, "html.parser")
    dialog = soup.select_one("#dlg-risk")
    controller = next(s.string for s in soup.find_all("script")
                      if s.string and "window.mx5OpenDlg = function" in s.string)
    styles = "\n".join(str(node) for node in soup.find_all(["style", "link"])
                       if node.name == "style" or
                       ("stylesheet" in node.get("rel", []) and
                        not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", node.get("href", ""), re.I)))
    specimen = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Risk Radar · anonymous component fixture</title>' + styles + '</head>'
        '<body class="page-macro mx4-grid rkw-component-fixture">' + str(dialog) +
        '<script>' + controller + '</script>'
        '<script defer src="risk_radar_workspace.js"></script>'
        '<script>window.addEventListener("DOMContentLoaded",function(){'
        'var fixture=document.getElementById("dlg-risk");'
        'fixture.classList.add("open","mx5-dlg-in");'
        'fixture.setAttribute("aria-modal","true");'
        'document.documentElement.classList.add("mx5-dlg-lock");'
        'document.body.classList.add("mx5-dlg-open");});</script></body></html>'
    )
    (output / "risk-radar-component.html").write_text(specimen)
    receipt = {
        "source_ref": source_sha, "inputs": inputs,
        "presentation_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ["templates/dashboard.html.j2", "templates/_risk_radar_workspace.html.j2",
                         "templates/risk_radar_workspace.js", "templates/risk_radar_workspace.css"]
        },
    }
    (output / "source-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def check_ui(output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(output))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    checks, errors = [], []
    shots = output / "interaction-shots"
    shots.mkdir(exist_ok=True)
    original_html = (output / "macro.html").read_text()

    def record(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("**/*", lambda route: route.continue_()
                          if route.request.url.startswith(origin + "/") else route.abort())
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/macro.html", wait_until="domcontentloaded")
            page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
            # Test only: no cookie, account, saved session, or external request.
            page.evaluate("window.MMXAccessPreview={isAnon:function(){return false;}}")
            trigger = page.locator('[onclick*="mx5OpenDlg"][onclick*="dlg-risk"]').first
            trigger.click()
            page.wait_for_selector("#dlg-risk.mx5-dlg-in")
            page.wait_for_timeout(230)
            record("overview is the initial reading", page.locator('.rkw-hero').evaluate(
                "(e)=>e.getBoundingClientRect().top-document.querySelector('#dlg-risk .mx5-dlg-body').getBoundingClientRect().top<=28"))
            record("registered evidence stays secondary on first open", page.locator('.rkw-owner-updates').evaluate(
                "(e)=>e.childElementCount===0"))
            record("four comparable driver buttons", page.locator(".rkw-driver").count() == 4)
            record("known warning survives partial coverage",
                   "Caution" in page.locator(".rkw-state-slot").inner_text() and
                   page.locator("#risk-envelope-band .gde-context-line").is_visible())
            # Paper parity: the native source panels belong to the first scan, and
            # they are the same nodes the inspector later borrows.
            record("driver ladder is visible in the overview",
                   page.locator(".rkw-ladder-slot .riskdlg-ladder").is_visible())
            record("sentiment panel is visible in the overview",
                   page.locator(".rkw-sentiment-slot #sentiment-regime").is_visible())
            record("each sentiment lens has its own source-labelled scale",
                   page.locator(".rkc-mood-lens .rkc-mood-axis").count() == 2)
            original_soup = BeautifulSoup(original_html, "html.parser")
            original_axis = "".join(original_soup.select_one(".rkc-mood-axis").get_text().split())
            record("both sentiment scales retain every source tick in both languages",
                   all("".join(text.split()) == original_axis for text in
                       page.locator(".rkc-mood-lens .rkc-mood-axis").all_text_contents()))
            source_lenses = original_soup.select(".rkc-mood-lens")
            for i, lens in enumerate(source_lenses):
                score = "".join(lens.select_one(".rkc-mood-score").get_text().split())
                pin = lens.select_one(".rkc-mood-pin").get("style")
                record("sentiment lens keeps its own value and pin " + str(i),
                       "".join(page.locator(".rkc-mood-score").nth(i).text_content().split()) == score and
                       page.locator(".rkc-mood-pin").nth(i).get_attribute("style") == pin)
            record("leadership panel is visible in the overview",
                   page.locator(".rkw-leadership-slot .riskdlg-leadership").is_visible())
            record("envelope band sits beside the ladder",
                   page.locator(".rkw-band-slot #risk-envelope-band").is_visible())
            record("settled internals context and source session stay visible at first scan",
                   page.locator(".rkw-completeness").is_visible() and
                   "2026-11-02" in page.locator(".rkw-completeness").inner_text())
            record("the signal index keeps its own scale",
                   page.locator("#dlg-risk .rkw-odds .rkw-score-slot .riskdlg-score").count() == 1)
            record("the signal index is never presented as odds",
                   "not odds" in page.locator(".rkw-index-label").inner_text().lower())
            record("each horizon keeps its own value",
                   page.locator(".rkw-horizon-value").count() == 3)
            page.evaluate("""window.__rkwNodes={
                ladder:document.querySelector('.rkw-ladder-slot .riskdlg-ladder'),
                sentiment:document.querySelector('.rkw-sentiment-slot #sentiment-regime'),
                leadership:document.querySelector('.rkw-leadership-slot .riskdlg-leadership'),
                band:document.getElementById('risk-envelope-band')};""")
            page.evaluate("""window.__rkwMeta={
                help:document.querySelector('.rkw-sentiment-panel .rkw-panel-heading .help'),
                date:document.querySelector('.rkw-leadership-panel .rkw-panel-heading small')};""")
            record("overview retains native sentiment help and leadership date",
                   page.evaluate("!!window.__rkwMeta.help && !!window.__rkwMeta.date"))
            record("the overview panels are single live nodes",
                   page.evaluate("""!!window.__rkwNodes.ladder && !!window.__rkwNodes.sentiment &&
                       !!window.__rkwNodes.leadership && !!window.__rkwNodes.band &&
                       document.querySelectorAll('.riskdlg-ladder').length===1 &&
                       document.querySelectorAll('#sentiment-regime').length===1 &&
                       document.querySelectorAll('.riskdlg-leadership').length===1"""))
            page.evaluate("""window.__rkwOriginalBand=document.getElementById('risk-envelope-band');
                window.__rkwOriginalLive=document.getElementById('gde-live-stage');""")
            page.locator('button[data-rkw-horizon="5"]').click()
            record("horizon updates probability", page.locator(".rkw-probability").inner_text() == "5%")
            record("horizon uses its own baseline", "4%" in page.locator(".rkw-baseline").inner_text())
            page.keyboard.press("ArrowRight")
            record("keyboard advances horizon", page.locator('button[data-rkw-horizon="10"]').get_attribute("aria-pressed") == "true")
            page.keyboard.press("End")
            record("keyboard selects final horizon", page.locator(".rkw-probability").inner_text() == "22%")
            page.locator(".rkw-driver").nth(3).scroll_into_view_if_needed()
            saved_scroll = page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop")
            page.locator(".rkw-driver").nth(3).click()
            record("driver opens integrated inspector", page.locator("#rkw-inspector-title").inner_text() == "Correlation")
            record("the inspector borrows the live envelope band",
                   page.evaluate("""(function(){var b=window.__rkwNodes.band;
                       return !!b && b===document.getElementById('risk-envelope-band') && !!b.closest('#rkw-inspector');})()"""))
            record("the detail view uses the full panel width",
                   page.evaluate("""(function(){var p=document.querySelector('#dlg-risk .mx5-dlg-panel');
                       var i=document.querySelector('#dlg-risk .rkw-inspector');
                       if(!p||!i) return false;
                       return i.getBoundingClientRect().width >= p.getBoundingClientRect().width - 40;})()"""))
            page.keyboard.press("Escape")
            record("Escape returns without closing", page.locator("#dlg-risk").evaluate(
                "(d)=>d.classList.contains('open')&&!d.classList.contains('rkw-detail-open')"))
            record("Back restores driver focus", page.locator(".rkw-driver").nth(3).evaluate("(e)=>document.activeElement===e"))
            record("Back restores overview scroll", abs(page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop") - saved_scroll) <= 2)
            record("the band returns to its exact overview slot",
                   page.evaluate("""(function(){var b=window.__rkwNodes.band;
                       return !!b && b===document.getElementById('risk-envelope-band') && !!b.closest('.rkw-band-slot');})()"""))
            page.keyboard.press("Escape")
            page.wait_for_selector("#dlg-risk.open", state="hidden")
            record("close restores dashboard trigger", trigger.evaluate("(e)=>document.activeElement===e"))
            record("close releases page scroll lock", page.evaluate("!document.documentElement.classList.contains('mx5-dlg-lock')"))
            trigger.click()
            page.wait_for_selector("#dlg-risk.mx5-dlg-in")
            page.locator('.rkw-explore [data-rkw-view="sentiment"]').click()
            for key, heading in [
                ("sentiment", "Market sentiment"), ("leadership", "Market leadership"),
                ("volatility", "Volatility & correlation"), ("signals", "All risk signals"),
                ("sources", "Sources & freshness"), ("method", "Method & track record"),
            ]:
                if key != "sentiment":
                    page.locator(f'.rkw-context-nav [data-rkw-view="{key}"]').click()
                record("reachable " + key, page.locator("#rkw-inspector-title").inner_text() == heading)
                if key == "sentiment":
                    record("sentiment detail keeps the original scale help",
                           page.evaluate("""!!window.__rkwMeta.help &&
                             !!window.__rkwMeta.help.closest('.rkw-inspector-content') &&
                             window.__rkwMeta.help.getClientRects().length>0"""))
                if key == "leadership":
                    record("leadership detail keeps the original as-of date",
                           page.evaluate("""!!window.__rkwMeta.date &&
                             !!window.__rkwMeta.date.closest('.rkw-inspector-content') &&
                             window.__rkwMeta.date.getClientRects().length>0"""))
            record("one live consumer, same nodes", page.evaluate("""
                document.getElementById('risk-envelope-band')===window.__rkwOriginalBand &&
                document.getElementById('gde-live-stage')===window.__rkwOriginalLive &&
                document.querySelectorAll('#gde-live-stage').length===1 &&
                document.querySelectorAll('#risk-envelope-band').length===1
            """))
            page.keyboard.press("Escape")
            # Move, never clone: the panel that leaves the overview for the
            # inspector is the same node, and it returns to the same slot.
            page.locator('.rkw-explore [data-rkw-view="sentiment"]').click()
            record("the inspector borrows the overview sentiment panel",
                   page.evaluate("""(function(){var n=window.__rkwNodes.sentiment;
                       return !!n && !!n.closest('.rkw-inspector-content');})()"""))
            record("the borrowed panel is not duplicated",
                   page.evaluate("document.querySelectorAll('#sentiment-regime').length===1"))
            page.keyboard.press("Escape")
            record("source metadata returns to its overview headings",
                   page.evaluate("""!!window.__rkwMeta.help.closest('.rkw-sentiment-panel .rkw-panel-heading') &&
                     !!window.__rkwMeta.date.closest('.rkw-leadership-panel .rkw-panel-heading')"""))
            record("the panel returns to its exact overview slot",
                   page.evaluate("""(function(){var n=window.__rkwNodes.sentiment;
                       return !!n && !!n.closest('.rkw-sentiment-slot');})()"""))
            record("the ladder returns to its exact overview slot",
                   page.evaluate("""(function(){var n=window.__rkwNodes.ladder;
                       return !!n && !!n.closest('.rkw-ladder-slot');})()"""))
            record("the leadership panel returns to its exact overview slot",
                   page.evaluate("""(function(){var n=window.__rkwNodes.leadership;
                       return !!n && !!n.closest('.rkw-leadership-slot');})()"""))
            page.locator(".rkw-driver").nth(1).click()
            record("calendar does not show invented quantitative bars",
                   page.locator('.rkw-inspector-content .rlx-bar-track').count() == 0)
            page.keyboard.press("Escape")

            risk_band_colors = {}
            for width, theme, language in [(w, t, l) for w in (1440, 768, 390, 320)
                                           for t in ("dark", "light") for l in ("en", "zh")]:
                page.set_viewport_size({"width": width, "height": 844 if width < 900 else 900})
                page.evaluate("""(s)=>{document.documentElement.dataset.theme=s[0];
                    document.documentElement.dataset.lang=s[1];document.documentElement.lang=s[1];}""",
                              [theme, language])
                page.wait_for_timeout(250)  # Let the native theme transitions settle before capture.
                colors = [page.locator(".riskdlg-scare .sc-band-" + band).first.evaluate(
                    "(e)=>getComputedStyle(e).color") for band in ("high", "calm")]
                if language == "en":
                    risk_band_colors[(width, theme)] = colors
                else:
                    record(f"risk severity ink stays consistent across languages {width}px/{theme}",
                           colors == risk_band_colors[(width, theme)] and colors[0] != colors[1])
                page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop=0")
                record(f"modal fits {width}px {theme}/{language}", page.locator("#dlg-risk .mx5-dlg-panel").evaluate(
                    "(e)=>{let r=e.getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1&&e.scrollWidth<=e.clientWidth+1;}"))
                record(f"content fits {width}px {theme}/{language}", page.locator(".rkw-layout").evaluate("(e)=>e.scrollWidth<=e.clientWidth+1"))
                record(f"page has no sideways overflow {width}px {theme}/{language}",
                       page.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
                page.screenshot(path=str(shots / f"overview-{width}-{theme}-{language}.png"))
                if width in (1440, 390):
                    for selector, section in [(".rkw-analytical", "analysis"), (".rkw-sentiment-panel", "context")]:
                        page.locator(selector).scroll_into_view_if_needed()
                        page.screenshot(path=str(shots / f"{section}-{width}-{theme}-{language}.png"))
                    page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop=0")
                if width == 390:
                    page.locator(".rkw-driver").first.click()
                    record("live context stays visible on mobile detail " + language,
                           page.locator("#risk-envelope-band").is_visible())
                    page.wait_for_timeout(230)  # Capture the settled inspector, not an animation frame.
                    page.screenshot(path=str(shots / f"detail-{width}-{theme}-{language}.png"))
                    page.keyboard.press("Escape")
                # Keyboard focus must reach the driver strip and keep a visible ring
                # at every width, in both art directions and both languages.
                reached = False
                for _ in range(40):
                    page.keyboard.press("Tab")
                    if page.evaluate("!!(document.activeElement && document.activeElement.classList.contains('rkw-driver'))"):
                        reached = True
                        break
                record(f"driver strip is keyboard reachable {width}px {theme}/{language}", reached)
                if reached:
                    record(f"focus ring stays visible {width}px {theme}/{language}",
                           page.locator(".rkw-driver:focus").evaluate(
                               "(e)=>{var s=getComputedStyle(e);return s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>=2;}")
                           if page.locator(".rkw-driver:focus").count() else False)
                # Tabbing can land on a native lens trigger, which opens the shared
                # popover. Dismiss it without touching the shared modal's own Escape.
                page.evaluate("if(document.activeElement) document.activeElement.blur()")
                page.wait_for_timeout(60)

            # Text-only resize exercises fixed-size labels and controls as well as
            # rem text. It changes only this isolated anonymous test document.
            for width, language in [(w, l) for w in (1440, 390) for l in ("en", "zh")]:
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(origin + "/risk-radar-component.html", wait_until="domcontentloaded")
                page.wait_for_selector("#dlg-risk.rkw-ready.open", state="attached")
                page.evaluate("""(lang)=>{
                    document.documentElement.dataset.lang=lang;
                    document.documentElement.lang=lang;
                    const sizes=Array.from(document.querySelectorAll('#dlg-risk, #dlg-risk *'))
                      .map(e=>[e,parseFloat(getComputedStyle(e).fontSize)]);
                    sizes.forEach(([e,size])=>{if(Number.isFinite(size))e.style.fontSize=(size*2)+'px';});
                }""", language)
                record(f"200% text fits the dialog {width}px/{language}",
                       page.locator("#dlg-risk .mx5-dlg-panel").evaluate(
                           "(e)=>e.scrollWidth<=e.clientWidth+1") and
                       page.locator(".rkw-layout").evaluate("(e)=>e.scrollWidth<=e.clientWidth+1"))
                record(f"200% text keeps horizon controls readable {width}px/{language}",
                       page.locator(".rkw-horizon").evaluate_all(
                           "(nodes)=>nodes.every(e=>e.scrollWidth<=e.clientWidth+1&&e.scrollHeight<=e.clientHeight+1)"))
                record(f"200% text keeps stance text clear of its icon {width}px/{language}",
                       page.locator(".rkw-stance").evaluate("""(e)=>{
                           const icon=e.querySelector('.rkw-stance-icon');
                           const text=e.querySelector(':scope > div');
                           const range=document.createRange(); range.selectNodeContents(icon);
                           return text.getBoundingClientRect().left>=range.getBoundingClientRect().right;
                       }"""))
                page.screenshot(path=str(shots / f"text-200-{width}-{language}.png"))
            page.goto(origin + "/risk-radar-component.html", wait_until="domcontentloaded")
            page.wait_for_selector("#dlg-risk.rkw-ready.open", state="attached")
            page.emulate_media(reduced_motion="reduce")
            page.locator(".rkw-driver").first.click()
            record("reduced motion removes inspector animation",
                   page.locator(".rkw-inspector").evaluate("(e)=>getComputedStyle(e).animationName") == "none")
            page.keyboard.press("Escape")
            page.keyboard.press("Tab")
            record("focus stays within the open dialog", page.evaluate("document.getElementById('dlg-risk').contains(document.activeElement)"))

            # Settled coherence is source text, not an inferred global quality verdict.
            for coherence, context, older in [
                ("Signals diverge", "The trend is positive, but underlying stress remains.", False),
                ("Signals align", "", True),
                ("Incomplete picture", "Some inputs are unavailable; this is not an all-clear.", False),
            ]:
                coverage = BeautifulSoup(original_html, "html.parser")
                band = coverage.select_one("#risk-envelope-band")
                label = band.select_one(".gde-coherence")
                label.clear()
                en = coverage.new_tag("span", attrs={"class": "l-en"})
                en.string = coherence
                label.append(en)
                for node in band.select(".gde-context-line, .gde-input-caveat:not(#gde-live-fallback)"):
                    node.decompose()
                if context:
                    node = coverage.new_tag("p", attrs={"class": "gde-context-line"})
                    node.string = context
                    band.append(node)
                if older:
                    node = coverage.new_tag("p", attrs={"class": "gde-input-caveat"})
                    node.string = "Trend includes older inputs."
                    band.append(node)
                (output / "coverage.html").write_text(str(coverage))
                page.goto(origin + "/coverage.html", wait_until="domcontentloaded")
                page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
                copied = page.locator(".rkw-completeness").text_content()
                record("source coherence remains literal: " + coherence,
                       coherence in copied and "All inputs present" not in copied and
                       "Partial data" not in copied and "Live update unavailable" not in copied and "Settled " in copied)
                if context:
                    record("context qualification survives: " + coherence, context in copied)
                if older:
                    record("older-input qualification stays beside the reading",
                           "Trend includes older inputs." in copied)

            single_lens = BeautifulSoup(original_html, "html.parser")
            for lens in single_lens.select(".rkc-mood-lens")[1:]:
                lens.decompose()
            (output / "single-lens.html").write_text(str(single_lens))
            page.goto(origin + "/single-lens.html", wait_until="domcontentloaded")
            page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
            record("one available sentiment lens stays one instrument",
                   page.locator(".rkc-mood-lens").count() == 1 and
                   page.locator(".rkc-mood-lens .rkc-mood-axis").count() == 1 and
                   "".join(page.locator(".rkc-mood-lens .rkc-mood-axis").text_content().split()) == original_axis)

            for raw, unavailable in [("", True), ("  ", True), ("—", True), ("0/100", False)]:
                indexed = BeautifulSoup(original_html, "html.parser")
                indexed.select_one("#dlg-risk .riskdlg-score").string = raw
                (output / "index-boundary.html").write_text(str(indexed))
                page.goto(origin + "/index-boundary.html", wait_until="domcontentloaded")
                page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
                record("index missingness boundary " + repr(raw),
                       page.locator(".rkw-index-meter").evaluate("(e)=>e.hidden") == unavailable)

            # Boundary tests modify only the local JSON response, not production.
            soup = BeautifulSoup(original_html, "html.parser")
            config = soup.select_one("#risk-radar-workspace-data")
            original_model = json.loads(config.string)
            for value, expected in [(None, "—"), (0, "0%"), (False, "—"), (-0.1, "—"), (1.1, "—"), ("0.22", "—")]:
                model = copy.deepcopy(original_model)
                model["horizons"]["21"]["probability"] = value
                config.string = json.dumps(model).replace("<", "\\u003c")
                (output / "boundary.html").write_text(str(soup))
                page.goto(origin + "/boundary.html", wait_until="domcontentloaded")
                page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
                record("probability boundary " + repr(value), page.locator(".rkw-probability").text_content() == expected)
            config.string = json.dumps(original_model).replace("<", "\\u003c")
            owner_panel = soup.new_tag("section", id="upstream-risk-warning")
            owner_panel.string = "Additional source-owned warning"
            soup.select_one("#dlg-risk .mx5-dlg-body").append(owner_panel)
            (output / "boundary.html").write_text(str(soup))
            page.goto(origin + "/boundary.html", wait_until="domcontentloaded")
            page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
            record("future owner panels remain in the visible overview", page.locator(
                ".rkw-owner-updates #upstream-risk-warning").count() == 1)
            config.string = "{"
            (output / "boundary.html").write_text(str(soup))
            page.goto(origin + "/boundary.html", wait_until="domcontentloaded")
            record("invalid JSON preserves the original dialog",
                   page.locator("#dlg-risk .riskdlg-brief").count() == 1 and
                   page.locator("#dlg-risk.rkw-ready").count() == 0)
            page.goto(origin + "/risk-radar-component.html", wait_until="domcontentloaded")
            page.wait_for_selector("#dlg-risk.rkw-ready.open", state="attached")
            record("anonymous specimen preserves Macro styling", page.locator('body.page-macro.mx4-grid').count() == 1)
            record("anonymous specimen opens at the risk overview", page.locator('.rkw-hero').evaluate(
                "(e)=>e.getBoundingClientRect().top-document.querySelector('#dlg-risk .mx5-dlg-body').getBoundingClientRect().top<=28"))
            record("no JavaScript exceptions", not errors)
            browser.close()
    finally:
        server.shutdown()
    result = {"passed": len(checks), "checks": checks, "page_errors": errors}
    (output / "ui-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-ref", default="HEAD")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    receipt = render_fixture(args.output.resolve(), args.source_ref)
    result = {"source_ref": receipt["source_ref"], "output": str(args.output)}
    if not args.build_only:
        result.update(check_ui(args.output.resolve()))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
