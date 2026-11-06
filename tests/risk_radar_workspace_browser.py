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
            page.keyboard.press("Escape")
            record("Escape returns without closing", page.locator("#dlg-risk").evaluate(
                "(d)=>d.classList.contains('open')&&!d.classList.contains('rkw-detail-open')"))
            record("Back restores driver focus", page.locator(".rkw-driver").nth(3).evaluate("(e)=>document.activeElement===e"))
            record("Back restores overview scroll", abs(page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop") - saved_scroll) <= 2)
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
            record("one live consumer, same nodes", page.evaluate("""
                document.getElementById('risk-envelope-band')===window.__rkwOriginalBand &&
                document.getElementById('gde-live-stage')===window.__rkwOriginalLive &&
                document.querySelectorAll('#gde-live-stage').length===1 &&
                document.querySelectorAll('#risk-envelope-band').length===1
            """))
            page.keyboard.press("Escape")
            page.locator(".rkw-driver").nth(1).click()
            record("calendar does not show invented quantitative bars",
                   page.locator('.rkw-inspector-content .rlx-bar-track').count() == 0)
            page.keyboard.press("Escape")

            for width, theme, language in [(1440, "dark", "en"), (1440, "light", "en"),
                                           (390, "dark", "en"), (390, "light", "zh"),
                                           (320, "light", "en"), (768, "dark", "zh")]:
                page.set_viewport_size({"width": width, "height": 844 if width < 900 else 900})
                page.evaluate("""(s)=>{document.documentElement.dataset.theme=s[0];
                    document.documentElement.dataset.lang=s[1];document.documentElement.lang=s[1];}""",
                              [theme, language])
                page.wait_for_timeout(250)  # Let the native theme transitions settle before capture.
                page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop=0")
                record(f"modal fits {width}px {theme}/{language}", page.locator("#dlg-risk .mx5-dlg-panel").evaluate(
                    "(e)=>{let r=e.getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1&&e.scrollWidth<=e.clientWidth+1;}"))
                record(f"content fits {width}px", page.locator(".rkw-layout").evaluate("(e)=>e.scrollWidth<=e.clientWidth+1"))
                page.screenshot(path=str(shots / f"overview-{width}-{theme}-{language}.png"))
                if width == 390:
                    page.locator(".rkw-driver").first.click()
                    record("live context stays visible on mobile detail " + language,
                           page.locator("#risk-envelope-band").is_visible())
                    page.wait_for_timeout(230)  # Capture the settled inspector, not an animation frame.
                    page.screenshot(path=str(shots / f"detail-{width}-{theme}-{language}.png"))
                    page.keyboard.press("Escape")

            page.emulate_media(reduced_motion="reduce")
            page.locator(".rkw-driver").first.click()
            record("reduced motion removes inspector animation",
                   page.locator(".rkw-inspector").evaluate("(e)=>getComputedStyle(e).animationName") == "none")
            page.keyboard.press("Escape")
            page.keyboard.press("Tab")
            record("focus stays within the open dialog", page.evaluate("document.getElementById('dlg-risk').contains(document.activeElement)"))

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
