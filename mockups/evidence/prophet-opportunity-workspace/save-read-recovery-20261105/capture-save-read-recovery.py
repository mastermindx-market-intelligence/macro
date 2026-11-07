
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image
import hashlib,json,re,datetime
w=Path("/home/ubuntu0/lanes/wt/d03-9495-ci-registration-c2-20261105")
out=Path("/tmp/prophet-save-recovery-browser-ec24a85")
assert not out.exists(),str(out)+" exists; inspect original run before retry"
out.mkdir()
assert (w/"templates/prophet_save.js").read_bytes()==(w/"site/prophet_save.js").read_bytes()
source_names=["templates/prophet_save.js","site/prophet_save.js","templates/prophet_save.css","templates/theme.css","templates/watchstore.js"]
pins={n:hashlib.sha256((w/n).read_bytes()).hexdigest() for n in source_names}
assert pins["templates/prophet_save.js"]=="63364e5bf444b4ebcd3ca7689362b7f393a64ea0b5d9539445c14ba4631fa193"
def fixture(theme,lang,mode):
    setup="""
window.__proof={writes:0,inspections:0,listReads:0,mode:MODE};
window.WatchStore={
 checkedSession:()=>({state:'ready',userId:'fixture-user',generation:1}),
 lists:{refresh:()=>{__proof.listReads++;return Promise.resolve([{id:'fixture-list',name:'Research'}]);}},
 symbols:{
  saveChecked:(id,names)=>{if(id!=='fixture-list'||names.join(',')!=='FLS')throw Error('fixture binding mismatch');__proof.writes++;return Promise.resolve({state:'uncertain'});},
  inspect:(id,ticker)=>{if(id!=='fixture-list'||ticker!=='FLS')throw Error('fixture read binding mismatch');__proof.inspections++;
   if(__proof.mode==='unexpected')return Promise.reject(Error('private-provider-detail'));
   return Promise.resolve({state:__proof.inspections===1?'unavailable':'present',readRetryAllowed:true,writeRetryAllowed:false});}
 }
};
""".replace("MODE",json.dumps(mode))
    return """<!doctype html><html data-theme="THEME" data-lang="LANG"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/theme.css"><link rel="stylesheet" href="/prophet_save.css">
<title>Prophet Save recovery fixture</title></head><body class="page-stocks" style="margin:0;padding:16px">
<div data-watchstore-checked-save></div>
<main><section id="us-standouts" data-board-asof="2026-11-03"><div id="us-cand-grid">
<article class="pvcard po-card" data-ticker="FLS" data-po-id="fixture-screener-0">
<a class="pv-setup-stock-link" href="stock.html#FLS">FLS</a>
<footer class="po-footer"></footer>
<details class="pv-setup-inline"><summary>Setup</summary><div class="pv-setup-body">Synthetic local fixture</div></details>
</article></div></section></main>
<script>SETUP</script><script src="/prophet_save.js"></script></body></html>""".replace("THEME",theme).replace("LANG",lang).replace("SETUP",setup)
def lum(css):
    vals=[float(v)/255 for v in re.findall(r"[0-9.]+",css)[:3]]
    assert len(vals)==3,css
    vals=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in vals]
    return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]
def contrast(a,b):
    x,y=lum(a),lum(b);return (max(x,y)+.05)/(min(x,y)+.05)
observations=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    try:
        for width in (320,390):
            for theme in ("light","dark"):
                for lang in ("en","zh"):
                    for mode in ("recoverable","unexpected"):
                        context=browser.new_context(viewport={"width":width,"height":900},device_scale_factor=1,has_touch=True)
                        page=context.new_page();page.emulate_media(reduced_motion="reduce")
                        errors=[];blocked=[];served=[];console_errors=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.on("console",lambda m:console_errors.append(m.text) if m.type=="error" else None)
                        document=fixture(theme,lang,mode)
                        def route(req):
                            path=urlparse(req.request.url).path
                            mappings={"/theme.css":("templates/theme.css","text/css"),"/prophet_save.css":("templates/prophet_save.css","text/css"),"/prophet_save.js":("templates/prophet_save.js","application/javascript"),"/product-nav-icons.css":("site/product-nav-icons.css","text/css")}
                            if path=="/fixture":
                                req.fulfill(status=200,content_type="text/html",body=document);return
                            if path in mappings:
                                name,mime=mappings[path];served.append(path);req.fulfill(status=200,content_type=mime,body=(w/name).read_bytes());return
                            if path.startswith("/fonts/") and Path(path).suffix in (".woff2",".woff"):
                                asset=(w/"site"/path.lstrip("/")).resolve()
                                assert asset.is_relative_to((w/"site/fonts").resolve()) and asset.is_file(),path
                                served.append(path);req.fulfill(status=200,content_type="font/woff2",body=asset.read_bytes());return
                            if path=="/favicon.ico":req.fulfill(status=204,body="");return
                            blocked.append(req.request.url);req.abort()
                        page.route("**/*",route)
                        page.goto("http://prophet.test/fixture",wait_until="networkidle")
                        page.evaluate("document.fonts.ready")
                        pick=page.locator(".pvs-save-pick");assert pick.count()==1
                        pick.click()
                        page.wait_for_function("document.getElementById('prophet-save-dialog').getAttribute('data-save-state')==='choose'")
                        dialog=page.locator("#prophet-save-dialog")
                        dialog.locator("select").select_option("fixture-list")
                        dialog.locator("button").filter(has_text="Save ticker").click()
                        page.wait_for_function("document.getElementById('prophet-save-dialog').getAttribute('data-save-state')==='uncertain'")
                        inspect=dialog.locator("button").filter(has_text="Check account list")
                        inspect.click()
                        page.wait_for_function("window.__proof.inspections===1")
                        if mode=="recoverable":
                            page.wait_for_function("!Array.from(document.querySelectorAll('#prophet-save-dialog button')).find(b=>b.textContent.includes('Check account list')).disabled")
                            page.keyboard.press("Shift+Tab");page.keyboard.press("Tab")
                            assert inspect.evaluate("(e)=>document.activeElement===e && e.matches(':focus-visible')")
                        else:
                            page.wait_for_function("document.querySelector('.prophet-save-status').textContent.includes('Membership could not be checked')")
                            assert inspect.is_disabled()
                        status=dialog.locator(".prophet-save-status")
                        assert status.locator(".l-"+lang).is_visible()
                        assert not status.locator(".l-"+("zh" if lang=="en" else "en")).is_visible()
                        geometry=dialog.evaluate("""(e)=>({rect:{x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height},documentOverflow:document.documentElement.scrollWidth>innerWidth,buttons:Array.from(e.querySelectorAll('button,a')).map(x=>({width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height,overflow:x.scrollWidth>x.clientWidth})),fg:getComputedStyle(e.querySelector('.prophet-save-status')).color,bg:getComputedStyle(e).backgroundColor,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches})""")
                        assert not geometry["documentOverflow"],geometry
                        assert all(b["width"]>=44 and b["height"]>=44 and not b["overflow"] for b in geometry["buttons"]),geometry
                        assert geometry["rect"]["x"]>=0 and geometry["rect"]["x"]+geometry["rect"]["width"]<=width+.1,geometry
                        ratio=contrast(geometry["fg"],geometry["bg"]);assert ratio>=4.5,ratio
                        assert geometry["reducedMotion"]
                        name=f"{mode}-{width}-{theme}-{lang}.png"
                        dialog.screenshot(path=str(out/name))
                        after_first=page.evaluate("({...window.__proof})")
                        assert after_first["writes"]==1 and after_first["inspections"]==1
                        if mode=="recoverable":
                            page.keyboard.press("Enter")
                            page.wait_for_function("document.getElementById('prophet-save-dialog').getAttribute('data-save-state')==='observed'")
                            assert inspect.is_disabled()
                            assert "does not prove the earlier save" in status.text_content()
                            assert page.evaluate("window.__proof.inspections")==2
                        else:
                            assert "private-provider-detail" not in dialog.text_content()
                        dialog.locator("button").filter(has_text="Close").click()
                        assert pick.evaluate("(e)=>document.activeElement===e")
                        pick.click()
                        page.wait_for_function("document.getElementById('prophet-save-dialog').getAttribute('data-save-state')==='uncertain'")
                        assert dialog.locator("select").count()==0
                        final=page.evaluate("({...window.__proof})")
                        assert final["writes"]==1
                        assert final["inspections"]==(2 if mode=="recoverable" else 1)
                        assert not errors,errors
                        assert not blocked,blocked
                        raw=(out/name).read_bytes()
                        with Image.open(out/name) as im:dimensions=list(im.size)
                        observations.append({"width":width,"theme":theme,"lang":lang,"mode":mode,"geometry":geometry,"status_contrast":round(ratio,3),"proof":final,"page_errors":errors,"console_errors":console_errors,"blocked_requests":blocked,"served_asset_paths":sorted(set(served)),"capture":{"file":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"dimensions":dimensions}})
                        context.close()
    finally:browser.close()
for name,pin in pins.items():assert hashlib.sha256((w/name).read_bytes()).hexdigest()==pin,name
receipt={"schema":"prophet.save_read_recovery_browser.v1","scope":"hermetic component fixture using actual controller/CSS/local fonts and synthetic account-service boundary","real_account_calls":False,"production_acceptance":False,"source_sha256":pins,"cell_count":len(observations),"all_passed":len(observations)==16,"cells":observations,"completed_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/"observations.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"output_dir":str(out),"cell_count":len(observations),"all_passed":receipt["all_passed"],"png_count":len(list(out.glob("*.png"))),"source_sha256":pins,"page_errors":sum(len(v["page_errors"]) for v in observations),"blocked_requests":sum(len(v["blocked_requests"]) for v in observations)},indent=2),flush=True)
