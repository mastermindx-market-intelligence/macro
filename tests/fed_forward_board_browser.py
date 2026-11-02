"""Exercise the generated macro.html via its launcher. Usage: python tests/fed_forward_board_browser.py OUTPUT_DIR"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(site, output):
    output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=site)
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server, sync_playwright() as pw:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        browser = pw.chromium.launch()
        records = []
        for width, height in [(1440, 940), (390, 844)]:
            for theme, lang in [("dark", "en"), ("light", "en"), ("dark", "zh"), ("light", "zh")]:
                context = browser.new_context(viewport={"width": width, "height": height},
                                              reduced_motion="reduce", timezone_id="America/Chicago")
                context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(origin + "/") else r.abort())
                page = context.new_page()
                page.goto(origin + "/macro.html", wait_until="domcontentloaded")
                page.wait_for_function("typeof window.mx5OpenDlg === 'function'")
                # Repository browser fixture for the existing public / registered boundary.
                page.evaluate("""() => { window.MMXAccessPreview={isAnon:()=>true};
                    window.MMXSharedShell={...window.MMXSharedShell,openAuth:()=>{window.__ffSignin=true}} }""")
                launcher = page.locator('#sx-v5-fed [aria-haspopup="dialog"]').first
                launcher.focus()
                launcher.press("Enter")
                assert page.evaluate("window.__ffSignin === true")
                expect(page.locator("#dlg-fed")).not_to_be_visible()
                page.evaluate("""([theme,lang]) => { window.MMXAccessPreview.isAnon=()=>false;
                    document.documentElement.dataset.theme=theme; document.documentElement.dataset.lang=lang;
                    document.documentElement.lang=lang; }""", [theme, lang])
                launcher.focus()
                launcher.press("Enter")
                dlg = page.locator("#dlg-fed")
                expect(dlg).to_be_visible()
                expect(dlg.locator(".mx5-dlg-close")).to_be_focused()
                dlg.locator(".mx5-dlg-panel").screenshot(path=str(output / f"{width}-{theme}-{lang}.png"))
                page.keyboard.press("Tab")
                first = dlg.locator("summary:visible").first
                select = dlg.locator("[data-ff-contract]")
                if select.count():
                    expect(select).to_be_focused()
                    value = select.locator("option").last
                    select.select_option(label=value.inner_text())
                    expect(dlg.locator("output b")).to_have_text(value.get_attribute("value") + " bp")
                    page.keyboard.press("Tab")
                expect(first).to_be_focused()
                first.press("Enter")
                if dlg.locator(".ff-chart").count():
                    expect(dlg.locator(".ff-table table")).to_be_visible()
                    rows = dlg.locator(".ff-table tbody tr").count()
                    assert rows > 0
                else:
                    expect(dlg.locator(".ff-empty")).to_be_visible()
                    rows = 0
                summary = dlg.locator(".ff-leg summary").first
                if summary.count():
                    summary.focus()
                    summary.press("Enter")
                    expect(dlg.locator(".ff-leg[open] p").first).to_be_visible()
                assert dlg.locator(".mx5-dlg-body").evaluate("e=>e.scrollWidth <= e.clientWidth + 1")
                assert "market ≈ the Fed" not in dlg.inner_text()
                page.keyboard.press("Escape")
                expect(dlg).not_to_be_visible()
                expect(launcher).to_be_focused()
                records.append({"width":width,"theme":theme,"lang":lang,"contract_rows":rows,
                                "anonymous_gate":True,"keyboard_open_expand_close_restore":True,
                                "horizontal_overflow":False})
                context.close()
        browser.close()
        server.shutdown()
    (output / "checks.json").write_text(json.dumps(records, indent=2) + "\n")
    return records


if __name__ == "__main__":
    print(json.dumps(check(ROOT / "site", Path(sys.argv[1])), indent=2))
