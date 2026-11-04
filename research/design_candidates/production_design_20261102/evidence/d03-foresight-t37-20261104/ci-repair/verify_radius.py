"""T37 CI radius repair: actual-template computed-style and visual proof only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,mimetypes,subprocess
from urllib.parse import urlparse,unquote
from playwright.sync_api import sync_playwright
EXPECTED_TEMPLATE="96c024b2122afd75c444d1945fd840bea9180cbef77662fb6d447dc9fdc957dc"
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    root=a.root.resolve();out=a.out.resolve();out.mkdir(exist_ok=True)
    source=root/"templates/foresight.html.j2"
    assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED_TEMPLATE
    fixture=module("t37_fixture",root/"tests/test_foresight_page_flag_ledger.py")
    previous=module("t37_accepted_browser",out.parent/"verify_browser.py")
    html=fixture._render(fixture._track(fixture.RECENT_TWO),grade=fixture._t37_grade(n_pending=229))
    (out/"radius-fixture.html").write_text(html)
    assets={};stubbed=set();blocked=set()
    def route_request(route):
        parsed=urlparse(route.request.url);path=unquote(parsed.path).lstrip("/")
        if parsed.hostname!="127.0.0.1":blocked.add(parsed.hostname);route.abort();return
        if path=="foresight.html":
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body=html);return
        if path=="live_config.js":
            route.fulfill(status=200,content_type="text/javascript",
                          body="window.LIVE_ENABLED=false;window.LIVE_WS_TAPE=false;");return
        for base in (root/"templates",root/"site"):
            f=(base/path).resolve()
            if f.is_relative_to(base) and f.is_file() and f.suffix in {".js",".css",".svg",".png",".woff2",".woff",".ico"}:
                assets[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()
                route.fulfill(status=200,content_type=mimetypes.guess_type(f)[0] or
                              "application/octet-stream",body=f.read_bytes());return
        stubbed.add(parsed.path);route.fulfill(status=200,content_type="application/json",body="{}")
    cases=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True);version=b.version
        for width,theme,lang in [(320,"light","en"),(320,"dark","zh"),
                                 (390,"light","zh"),(1440,"dark","en")]:
            name=f"radius-{width}-{theme}-{lang}";errs=[]
            c=b.new_context(viewport={"width":width,"height":900},device_scale_factor=1)
            c.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});")
            c.route("**/*",route_request);page=c.new_page();page.set_default_timeout(5000)
            page.on("pageerror",lambda e:errs.append(str(e)))
            page.goto("http://127.0.0.1/foresight.html",wait_until="load");page.evaluate("document.fonts.ready")
            record=page.locator("details").filter(has_text="Track record — graded forward vs SPY")
            summary=record.locator("summary");summary.focus();page.keyboard.press("Enter")
            assert record.evaluate("e=>e.open")
            text=" ".join(record.inner_text().split())
            assert ("229 pending 90d" if lang=="en" else "229 待90天") in text
            radii=record.locator(".fx-rchip:visible").evaluate_all("""es=>es.map(e=>{
              const s=getComputedStyle(e);return {text:e.innerText,radius:s.borderRadius,font:s.fontSize};
            })""")
            assert radii and all(x["radius"]=="8px" and x["font"]=="12px" for x in radii),radii
            measures=page.evaluate(previous.MEASURE)
            assert measures["pageScrollWidth"]<=width
            assert measures["theme"]==theme and measures["lang"]==lang
            assert all(x["contrast"]>=4.5 and x["fontSize"]>=12 and not x["overflow"] for x in measures["text"])
            assert not errs,errs
            record.screenshot(path=str(out/(name+".png")))
            cases.append({"case":name,"status":"PASS","radii":radii,"measures":measures,
                          "javascript_errors":errs})
            print(json.dumps({"case":name,"status":"PASS","chip_radius":"8px","font_size":"12px"}),flush=True)
            c.close()
        b.close()
    report={"task":"T37 radius token CI repair","checkout_head":subprocess.check_output(
        ["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        "uncommitted_candidate_template_sha256":EXPECTED_TEMPLATE,
        "change":"border-radius:8px -> var(--r-ctl,8px)",
        "browser":f"Chromium {version}","cases":cases,"assets":assets,
        "stubbed_unrelated_json":sorted(stubbed),"blocked_external":sorted(blocked),
        "limits":"Four focused computed-style/render cells; existing 60-case semantic/interaction proof is retained at its original head. No live data, deployment, or new Paper geometry."}
    (out/"radius-browser-proof.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":True,"passed":len(cases),"template_sha256":EXPECTED_TEMPLATE}))
if __name__=="__main__":main()
