from pathlib import Path
import functools,http.server,json,math,threading
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
out=Path("/tmp/rr-paper-latest-r2-20261104-c3")
html=(out/"risk-radar-component.html").read_text()
soup=BeautifulSoup(html,"html.parser")
model=json.loads(soup.select_one("#risk-radar-workspace-data").string)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=str(out)))
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f"http://127.0.0.1:{server.server_port}"
errors=[]; horizon_rows=[]; frames=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1440,"height":900})
        context.route("**/*",lambda r:r.continue_() if r.request.url.startswith(origin+"/") else r.abort())
        page=context.new_page()
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(origin+"/risk-radar-component.html",wait_until="domcontentloaded")
        page.wait_for_selector("#dlg-risk.rkw-ready.open")
        page.evaluate("document.documentElement.dataset.lang='en';document.documentElement.dataset.theme='dark'")
        for day in ("5","10","21"):
            page.locator(f'button[data-rkw-horizon="{day}"]').click()
            prob=model["horizons"][day]["probability"]
            expected=f"{math.floor(prob*100+.5)}%" if isinstance(prob,(float,int)) and not isinstance(prob,bool) and 0<=prob<=1 else "—"
            actual=page.locator(".rkw-probability").inner_text()
            assert actual==expected,(day,actual,expected)
            horizon_rows.append({"day":day,"source_probability":prob,"rendered":actual})
        for i in range(4):
            page.locator(".rkw-driver").nth(i).click()
            assert page.locator("#rkw-inspector-title").inner_text().strip()
            assert page.locator("#risk-envelope-band").count()==1
            page.keyboard.press("Escape")
            assert not page.locator("#dlg-risk").evaluate("(e)=>e.classList.contains('rkw-detail-open')")
        for width,theme,lang in ((1440,"dark","en"),(390,"light","zh")):
            page.set_viewport_size({"width":width,"height":900 if width==1440 else 844})
            page.evaluate("(s)=>{document.documentElement.dataset.theme=s[0];document.documentElement.dataset.lang=s[1]}",[theme,lang])
            page.locator("#dlg-risk .mx5-dlg-body").evaluate("(e)=>e.scrollTop=0")
            page.wait_for_timeout(250)
            assert page.locator(".rkw-layout").evaluate("(e)=>e.scrollWidth<=e.clientWidth+1")
            name=f"latest-{width}-{theme}-{lang}.png"
            page.screenshot(path=str(out/name))
            frames.append(name)
        page.evaluate("document.documentElement.dataset.lang='en'")
        reading={"state":page.locator(".rkw-state-slot").inner_text(),"index":page.locator(".rkw-score-slot").inner_text(),"session":page.locator(".riskdlg-asof").inner_text(),"internals":page.locator(".rkw-completeness").inner_text()}
        assert not errors,errors
        browser.close()
finally: server.shutdown()
report={"presentation_source_revision":"9b424c673bd5e0d6c5f5aaa48caeca2d130c6134","input_source_revision":"734f54bae23cf5ef15c6adecbebe2d018bad1f47","production_authenticated":False,"horizons":horizon_rows,"driver_views_opened":4,"reading":reading,"screenshots":frames,"page_errors":errors}
(out/"latest-snapshot-smoke.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
print(json.dumps(report,ensure_ascii=False))
