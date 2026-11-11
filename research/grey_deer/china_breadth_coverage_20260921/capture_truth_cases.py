"""Synthetic full-page truth proof using the existing page-evidence capture owner."""
from __future__ import annotations
import argparse
import hashlib
import http.server
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from scripts import capture_page_evidence as capture
from test_china_archetype_d_s1 import _render_china_risk_case
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--work-dir", type=Path, required=True)
parser.add_argument("--browser", type=Path, required=True)
args = parser.parse_args()
site = args.work_dir / "site"
site.mkdir(parents=True, exist_ok=False)
for source in (ROOT / "site").iterdir():
    if source.name != "china.html":
        (site / source.name).symlink_to(source, target_is_directory=source.is_dir())
html = _render_china_risk_case(None)
(site / "china.html").write_text(html)
out = ROOT / "mockups/evidence/china-integrity-7592"
out.mkdir(parents=True, exist_ok=True)


def driver_factory(**kwargs):
    manager = sync_playwright().start()
    browser = manager.chromium.launch(executable_path=str(args.browser), headless=True)
    return capture._PlaywrightDriver(manager, browser, kwargs.get("user_agent", capture.USER_AGENT),
        dict(kwargs.get("observer_config") or capture.DEFAULT_OBSERVER_CONFIG),
        kwargs.get("settle_ms", 1200))


code = capture.main([
    "--site-dir", str(site), "--routes", "/china.html", "--max-pages", "1",
    "--output-dir", str(out), "--manifest", str(out / "manifest.json"),
    "--smells", str(args.work_dir / "smells.json"),
    "--themes", "dark,light", "--locales", "en,zh", "--viewports", "desktop,mobile",
    "--settle-ms", "1200", "--timeout-s", "30"], driver_factory=driver_factory)
if code:
    raise SystemExit(code)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(site), **kw)
    def log_message(self, *_):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
feed = {"schema": "china_risk_state.v1", "built": "2026-09-18T20:00:00Z",
        "nightly_asof": "2026-09-18", "live_active": False, "realtime": False,
        "display": {"score": 38, "verdict": "RISK_OFF", "label_en": "Risk-off", "label_zh": "避险"},
        "nightly": {"verdict": "RISK_OFF", "headline_en": "Synthetic refreshed headline",
                    "headline_zh": "合成刷新标题"}}
cases = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(args.browser), headless=True)
        for width in (1440, 390):
            for theme in ("dark", "light"):
                for locale in ("en", "zh"):
                    context = browser.new_context(viewport={"width": width, "height": 900})
                    context.add_init_script(
                        f"localStorage.setItem('theme', {json.dumps(theme)});"
                        f"localStorage.setItem('lang', {json.dumps(locale)});"
                        "localStorage.removeItem('themeAuto');")
                    page = context.new_page()
                    page.route("**/live/china_risk_state.json*", lambda route:
                        route.fulfill(status=200, content_type="application/json", body=json.dumps(feed)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/china.html", wait_until="domcontentloaded")
                    page.wait_for_function("document.querySelector('.v-thesis .l-en')?.textContent === 'Synthetic refreshed headline'")
                    page.wait_for_timeout(1200)
                    card = page.locator(".cnx-card").filter(has=page.locator(".cnx-ctitle", has_text="Pullback Risk"))
                    slow = card.locator(".cnx-kv").filter(has_text="Economic slowdown").locator(".v")
                    assert slow.inner_text().strip().lower() in ("unavailable", "暂不可用")
                    guide = card.locator(".cnx-foot").inner_text()
                    assert "size down" not in guide and "缩仓" not in guide
                    assert "unavailable" in guide.lower() or "暂不可用" in guide
                    playbook = page.locator(".cnx-playbook-context").text_content()
                    assert "Playbook posture unavailable." in playbook
                    assert "Synthetic refreshed" not in playbook
                    assert page.locator(".v-thesis .l-zh").text_content() == "合成刷新标题"
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    assert not overflow
                    card.click()
                    assert page.locator("#cnx-dlg-risk").is_visible()
                    cases.append({"width": width, "theme": theme, "locale": locale,
                                  "slowdown": slow.inner_text(), "guidance": guide,
                                  "headline_refreshed": True, "playbook_preserved": True,
                                  "risk_dialog_opened": True, "horizontal_overflow": overflow})
                    context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

paths = ["engine/china_tier1.py", "scripts/build_china.py", "templates/china.html.j2",
         "templates/china_risk_state_live.js", "tests/test_china_archetype_d_s1.py"]
receipt = {"proof_class": "synthetic_full_page_browser", "production": False,
           "browser_executable": str(args.browser), "cases": cases,
           "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
           "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
           "feed": feed, "local_server_closed": True}
(out / "interaction-proof.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
(out / "EVIDENCE.yml").write_text("schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n  - templates/china.html.j2\nmanifest: mockups/evidence/china-integrity-7592/manifest.json\n")
print(json.dumps({"captured_interaction_cases": len(cases), "production": False, "server_closed": True}))
