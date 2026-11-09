# Current-source China sector-link qualification

## Bound source

Receiving main: b84bd66ab8313db879f68f97995486cf0aa7f782. Candidate China page blob: d8434b45ed3ef08a990f3f8d0404cb2b19d716b9. Template:69e5ba0157cc49a3368a308b8c45914012e6962e. CSS:99feca51197fd2006c1857e9fab7d46b2f170a77. The capture tool's nearest Git HEAD field is context only; the manifest's page_tree_sha binds the actual captured page bytes. Root verified those bytes before and after capture. The generated page retains current main's November6 data, ranks, values and November9 13:27UTC footer;53 anchors, their CSS reference and one bilingual explanatory receipt are the only HTML changes. The complete inverse reconstructs main byte for byte.

## Actual checks

- Canonical lib.pages.write_page is idempotent on the candidate. Its owned site root and422 existing JS/CSS asset hashes were verified unchanged.
- tests/test_china_sector_detail_links.py:11 passed in5.45seconds, real Jinja/PyYAML/BeautifulSoup and repository conftest.
- Full paired planner:4457 discovered suites, new suite staged in the Git inventory before both measurements, zero unreadable Python paths. Same candidate product universe for both catalogs. Actual weights5945/5966/5703→5948/5969/5706, selected jobs137/137/131 unchanged,10packs each, no new or removed selected owners, no breaches. Measurement183.031848542seconds; processEXIT0. See paired-planner.json.
- Canonical capture:24/24 real PNGs across desktop1440×900/mobile390×844, EN/ZH, dark/light, rest/hover/focus. Final capture has zero console errors and zero failed HTTP responses. Root visually inspected desktop dark rest/light focus and mobile ZH dark focus/EN light rest. Focus rings are visible, text and layout remain coherent; both viewports report no document horizontal overflow. Mobile's single wider inner element is preserved and recorded by the tool.
- Keyboard:40/40 real Tab+Enter journeys across five families and eight state cells, checking independent canonical ticker lookup, exact href,200 destination,title,localized h1/ticker and2px solid semantic focus outline with2px offset. All eight overview activations record one trusted anchor click, zero bubbled card activations and zero Sector dialog openings. No locator.focus fallback is used. See keyboard-journeys.json.
- Initial keyboard matrix exposed a missing local Markets heatmap fixture in all eight Markets cells. Root materialized exact main blob057bf8fe7691dc3caa34ffda3a975a27886d2d30, then repeated only those eight affected journeys:8/8 passed, zero failed HTTP responses. The other32 accepted journeys were not repeated. See keyboard-markets-complete-fixture.json. The original40-row receipt is retained with its actual initial errors.

- Repository visual-evidence consumer: EXIT0 against all11954 current-main mockup files plus the27 exact historical PR evidence files and this new package. Its initial sparse-fixture refusal was resolved through the canonical worktree_sparse.py add mockups operation; no guard was disabled. The add operation omitted the two staged site postimages from the out-of-cone working directory while preserving their exact index objects; root restored those exact candidate blobs, verified all six source postimages, then ran the consumer successfully. No visual or navigation result is attributed to a different page blob.

## Scope and gaps

These are anonymous local snapshot checks. Authenticated free/essential/pro cells and loading/empty/stale/error states were not synthesized; canonical manifest gaps remain intact. The keyboard harness explicitly blocks external origins, including TradingView's tv.js, so destination pages record TradingView-is-not-defined errors. Navigation,title and localized heading assertions passed; external charts are not qualified. No provider refresh, collector, China VM renderer, login, private/live origin, production deployment or trading authority is claimed.

The first canonical capture completed against an incomplete local fixture (fonts and three live JSON files absent). Its diagnostic output was retained in the owned workspace, then the exact committed fonts/JSON were materialized and the final24-cell capture above was produced. Those incomplete-preview PNGs are not presented as final evidence. All27 older evidence files in the original evidence directory remain untouched historical records.

## Reproduction

Use a qualified Python with Playwright and Chromium installed, serve the exact current site fixtures locally, and run scripts/capture_page_evidence.py with --site-dir site --routes /china.html --viewports desktop,mobile --locales en,zh --themes dark,light --max-pages 1 --settle-ms 1400 and the force states sector-hover:hover(body.page-china .cnx-sector-link) and sector-focus:focus(body.page-china .cnx-sector-link). Supply the output/manifest/smells paths in this directory. CLI flags and their values require separate arguments.

Actual keyboard source below has Git-blob SHA3b831b67d729d880811185c84a901994e403ca04. Change only the ROOT fixture location when reproducing. The eight-cell follow-up used this same procedure filtered to family markets and an8-row expected total; its actual script blob is87ce718de1002e08b800eb6825c620d27fd863cb. This is an auditable browser-proof procedure in documentation, not a new CI test owner or watcher.

```python
"""Forty real Tab/Enter journeys through the current China sector links."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from urllib.parse import urlparse
import os,sys,json,hashlib,threading,time,traceback
from bs4 import BeautifulSoup
import yaml
from playwright.sync_api import sync_playwright
ROOT=Path("/Volumes/Mastermind/agent-workspaces/macro/web/macro-pr8184-source-proof-20261109-c3-0467");SITE=ROOT/"site";OUT=ROOT/"mockups/evidence/china-sector-detail-links-20261109/keyboard-journeys.json"
sys.path.insert(0,str(ROOT))
from scripts.capture_page_evidence import state_seed_source,_APPLY_STATE_SCRIPT
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
assert blob(SITE/"china.html")=="d8434b45ed3ef08a990f3f8d0404cb2b19d716b9"
config=yaml.safe_load((ROOT/"config.yml").read_text())["china"]["yahoo"]["sector_etfs"]
by_name={meta[0]:ticker for ticker,meta in config.items()}
families=[
 ("overview","[onclick=\"cnxOpenDlg('cnx-dlg-sector')\"] .cnx-chips a.cnx-sector-link",None),
 ("markets","#cnx-dlg-markets .cnx-ledd > a.cnx-sector-link","cnx-dlg-markets"),
 ("sector_chips","#cnx-dlg-sector .cnx-chips a.cnx-sector-link","cnx-dlg-sector"),
 ("rotation","#cnx-dlg-sector table.cnx-mt tr td:first-child a.cnx-sector-link","cnx-dlg-sector"),
 ("playbook","#cnx-dlg-playbook .cnx-cols2 .cnx-kv > .k a.cnx-sector-link","cnx-dlg-playbook")]
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(SITE)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin="http://127.0.0.1:"+str(server.server_port);rows=[];started=time.time()
def tab_to(page,target):
 trace=[]
 for count in range(401):
  if target.evaluate("(el)=>el===document.activeElement"):return count,trace[-12:]
  if count==400:raise AssertionError("Unreachable with400 real Tabs: "+json.dumps(trace[-12:]))
  page.keyboard.press("Tab")
  if count%20==0:trace.append(page.evaluate("()=>({tag:document.activeElement.tagName,id:document.activeElement.id,href:document.activeElement.getAttribute('href')})"))
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  try:
   for viewport,width,height in [("desktop",1440,900),("mobile",390,844)]:
    for locale in ["en","zh"]:
     for theme in ["dark","light"]:
      context=browser.new_context(viewport={"width":width,"height":height},color_scheme=theme)
      context.add_init_script(state_seed_source({"locale":locale,"theme":theme}))
      blocked=[]
      def route(req):
       if urlparse(req.request.url).hostname not in {"127.0.0.1","localhost"}:
        blocked.append(req.request.url);req.abort("blockedbyclient")
       else:req.continue_()
      context.route("**/*",route)
      try:
       for family,selector,dialog in families:
        page=context.new_page();errors=[];failed=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        page.on("response",lambda response:failed.append({"url":response.url,"status":response.status}) if response.status>=400 else None)
        row={"viewport":viewport,"width":width,"height":height,"locale":locale,"theme":theme,"family":family}
        try:
         response=page.goto(origin+"/china.html",wait_until="domcontentloaded");assert response.status==200
         page.wait_for_function("typeof window.cnxOpenDlg === 'function'")
         state=page.evaluate(_APPLY_STATE_SCRIPT,{"locale":locale,"theme":theme})
         assert state=={"theme":theme,"locale":locale},state
         page.evaluate("()=>document.fonts.ready")
         row["applied_state"]=state
         if dialog:
          card=page.locator("[onclick=\"cnxOpenDlg('"+dialog+"')\"]").first
          card_tabs,card_trace=tab_to(page,card);page.keyboard.press("Enter")
          assert page.locator("#"+dialog).evaluate("el=>el.classList.contains('open')") and page.locator("#"+dialog).is_visible()
          row["dialog_tabs"]=card_tabs;row["dialog_open"]=dialog
         anchor=page.locator(selector).first
         name=anchor.locator(".l-en").text_content().strip();ticker=by_name[name];href=anchor.get_attribute("href")
         assert href=="sectors/"+ticker+".html",(name,ticker,href)
         assert anchor.locator(".l-"+locale).is_visible()
         expected=BeautifulSoup((SITE/href).read_text(),"html.parser")
         expected_title=expected.title.get_text()
         expected_local=expected.select_one("h1 .l-"+locale).get_text(strip=True)
         row.update(name=name,ticker=ticker,href=href,expected_localized_heading=expected_local)
         tabs,trace=tab_to(page,anchor);row["anchor_tabs"]=tabs;row["focus_trace"]=trace
         ring=anchor.evaluate("""el=>{const s=getComputedStyle(el);return {focused:el===document.activeElement,visible:el.matches(':focus-visible'),width:s.outlineWidth,style:s.outlineStyle,offset:s.outlineOffset,color:s.outlineColor,semantic:getComputedStyle(el).getPropertyValue('--link').trim()}}""")
         assert ring["focused"] and ring["visible"] and ring["width"]=="2px" and ring["style"]=="solid" and ring["offset"]=="2px" and ring["color"] not in {"transparent","rgba(0, 0, 0, 0)"},ring
         row["focus_ring"]=ring
         anchor.evaluate("""(a,overview)=>{
          const initial={trusted_clicks:0,bubbled:0,sector_open_calls:0};
          sessionStorage.setItem('8184-activation',JSON.stringify(initial));
          const inc=k=>{const x=JSON.parse(sessionStorage.getItem('8184-activation'));x[k]++;sessionStorage.setItem('8184-activation',JSON.stringify(x));};
          a.addEventListener('click',e=>{if(e.isTrusted)inc('trusted_clicks');});
          if(overview){
           const card=a.closest('[onclick]');
           const parent=a.parentElement.closest('[onclick]');
           if(!parent)throw Error('Overview parent card missing');
           parent.addEventListener('click',()=>inc('bubbled'));
           const old=window.cnxOpenDlg;
           window.cnxOpenDlg=function(...args){if(args[0]==='cnx-dlg-sector')inc('sector_open_calls');return old.apply(this,args);};
          }
         }""",family=="overview")
         with page.expect_navigation(wait_until="domcontentloaded") as navigation:
          page.keyboard.press("Enter")
         landed=navigation.value;assert landed and landed.status==200
         assert page.url==origin+"/"+href,page.url
         page.evaluate(_APPLY_STATE_SCRIPT,{"locale":locale,"theme":theme})
         assert page.title()==expected_title,(page.title(),expected_title)
         actual_local=page.locator("h1 .l-"+locale).inner_text().strip();assert actual_local==expected_local
         heading=page.locator("h1").inner_text();assert ticker in heading
         activation=page.evaluate("()=>JSON.parse(sessionStorage.getItem('8184-activation'))")
         assert activation["trusted_clicks"]==1,activation
         if family=="overview":assert activation["bubbled"]==0 and activation["sector_open_calls"]==0,activation
         row.update(status="passed",destination_status=landed.status,destination_url=page.url,destination_title=page.title(),destination_heading=heading,activation=activation,page_errors=errors,failed_responses=failed,external_requests_blocked=sorted(set(blocked)))
         rows.append(row);print(json.dumps({k:row[k] for k in ["viewport","locale","theme","family","ticker","anchor_tabs","status"]}),flush=True)
        except Exception as exc:
         row.update(status="failed",error=str(exc),page_errors=errors,failed_responses=failed,external_requests_blocked=sorted(set(blocked)));rows.append(row);raise
        finally:page.close()
      finally:context.close()
  finally:browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
 proof={"schema":"mastermind.china_sector_keyboard_proof.v1","receiving_main":"b84bd66ab8313db879f68f97995486cf0aa7f782","page_blob":blob(SITE/"china.html"),"css_blob":blob(SITE/"assets/css/aeabd751.css"),"duration_seconds":time.time()-started,"planned_journeys":40,"completed_journeys":len(rows),"passed_journeys":sum(r["status"]=="passed" for r in rows),"external_network":"External origins blocked explicitly; current pinned local snapshot only","journeys":rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 print(json.dumps({"proof":str(OUT),"completed":len(rows),"passed":proof["passed_journeys"],"seconds":proof["duration_seconds"]}),flush=True)
assert len(rows)==40 and all(r["status"]=="passed" for r in rows)

```
