"""Native visual/workflow readback for short Overview field labels.
Runs only on the isolated verifier and serves retained/synthetic fixture HTML.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
import sys
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from scripts.build_crypto_intelligence_r4 import render_view
from test_crypto_intelligence_r4 import relative_integrity_inputs
from lib.crypto_intelligence_view import build_view
from playwright.sync_api import sync_playwright

stage = sys.argv[1]
assert stage in ("parent", "candidate")
out = ROOT / ("overview-labels-" + stage + "-proof-v2")
assert not out.exists()
out.mkdir()
(out / "captures").mkdir()
observations = {"stage": stage, "contexts": 0, "pages": 0, "page_errors": [],
                "blocked_external_requests": 0, "blocked_websockets": 0}
retained = json.loads((ROOT / "site/crypto_intelligence_r4.json").read_text())
cases = [("retained", "en", 320, False), ("retained", "zh", 320, True)]
if stage == "candidate":
    cases += [("unavailable", "en", 390, False), ("history", "zh", 390, True),
              ("retained", "en", 1440, False)]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "site")))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_address[1]}/crypto-r4.html"
origin = urlsplit(url)
records = []
started = time.monotonic()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        observations["browser"] = browser.version
        for variant, lang, width, touch in cases:
            name = f"{variant}-{lang}-{width}"
            view = deepcopy(retained)
            if variant != "retained":
                projected = build_view(*relative_integrity_inputs())
                view = projected
                if variant == "history":
                    view["assets"] = [projected["assets"][2], projected["assets"][1]]
            rendered = out / ("rendered-" + name)
            render_view(view, rendered)
            markup = (rendered / "crypto-r4.html").read_text()
            context = browser.new_context(viewport={"width": width, "height": 844}, is_mobile=touch, has_touch=touch)
            observations["contexts"] += 1
            def request(route):
                target = urlsplit(route.request.url)
                if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                    route.continue_()
                else:
                    observations["blocked_external_requests"] += 1
                    route.abort()
            def socket(route):
                observations["blocked_websockets"] += 1
                route.close()
            context.route("**/*", request)
            context.route_web_socket("**/*", socket)
            page = context.new_page()
            observations["pages"] += 1
            page.on("pageerror", lambda error: observations["page_errors"].append(str(error)))
            page.set_default_timeout(4500)
            page.clock.set_fixed_time(datetime.fromisoformat("2026-10-18T12:00:00+00:00"))
            page.add_init_script("localStorage.setItem('lang'," + json.dumps(lang) + ");localStorage.setItem('theme'," + json.dumps("dark" if lang == "en" else "light") + ");")
            page.route("**/crypto-r4.html?*", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=markup))
            page.goto(url + "?lang=" + lang + "#overview", wait_until="load")
            page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedAddress===location.href")
            page.evaluate("()=>document.fonts.ready")
            section = page.locator('[data-view="overview"] > .cri-section').last
            section.scroll_into_view_if_needed()
            rows = section.locator(".cri-watch-row")
            record = section.evaluate("""(section,lang)=>{
              const rect=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}};
              const range=n=>{const r=document.createRange();r.selectNodeContents(n);return [...r.getClientRects()].filter(b=>b.width>0&&b.height>0).map(b=>({left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width}))};
              return {width:innerWidth,pageWidth:document.documentElement.scrollWidth,section:rect(section),
                rows:[...section.querySelectorAll('.cri-watch-row')].map(row=>{
                  const info=row.firstElementChild,summary=info.querySelector('p'),button=row.querySelector('button');
                  return {text:summary.innerText,fontSize:getComputedStyle(summary).fontSize,fontFamily:getComputedStyle(summary).fontFamily,
                    row:rect(row),info:rect(info),button:rect(button),scrollWidth:row.scrollWidth,clientWidth:row.clientWidth,
                    symbol:button.dataset.open,pairs:[...summary.querySelectorAll(':scope > span')].filter(n=>!n.classList.contains('l-en')&&!n.classList.contains('l-zh')).map(n=>{
                      const localized=n.querySelector('.l-'+lang);return {text:localized?.innerText,rect:rect(n),lines:localized?range(localized):[]};
                    })};
                })};
            }""", lang)
            record.update(name=name, variant=variant, lang=lang, touch=touch)
            assert len(record["rows"]) == 2
            assert record["pageWidth"] <= width
            for row, asset in zip(record["rows"], view["assets"][:2]):
                assert row["fontSize"] == "12.5px"
                assert row["scrollWidth"] <= row["clientWidth"] + 1
                assert row["info"]["right"] <= row["button"]["left"] - 8
                assert row["symbol"] == "asset:" + asset["symbol"]
                if stage == "candidate":
                    expected = [("Vs BTC: " if lang == "en" else "相对 BTC：") + asset["relative_" + lang],
                                ("Risk: " if lang == "en" else "风险：") + asset["risk_" + lang]]
                    assert [p["text"] for p in row["pairs"]] == expected
                    for pair in row["pairs"]:
                        assert pair["lines"]
                        for line in pair["lines"]:
                            assert row["info"]["left"] - 0.5 <= line["left"] <= line["right"] <= row["info"]["right"] + 0.5
            assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
            section.screenshot(path=str(out / "captures" / (name + ".png")))
            for index, asset in enumerate(view["assets"][:2]):
                opener = rows.nth(index).locator("button")
                opener.click()
                page.wait_for_function("(symbol)=>document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel==='asset:'+symbol", arg=asset["symbol"])
                page.locator("#cri-dialog-close").click()
                page.wait_for_function("location.hash==='#overview'&&!document.getElementById('cri-dialog').open")
                assert opener.evaluate("node=>document.activeElement===node")
            record["inspect_and_close_focus"] = True
            assert page.evaluate("localStorage.getItem('mmx.crypto.r4.scenarios.v1')") is None
            records.append(record)
            context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
observations["seconds"] = round(time.monotonic() - started, 3)
assert observations["page_errors"] == []
assert observations["blocked_external_requests"] == 0 and observations["blocked_websockets"] == 0
report = {"observations": observations, "cases": records}
(out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"observations": observations, "cases": [r["name"] for r in records]}))
