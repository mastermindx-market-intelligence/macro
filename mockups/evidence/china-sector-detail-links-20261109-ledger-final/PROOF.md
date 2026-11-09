# Current-page China sector-link qualification after the ledger landing

## Exact source and scope

Receiving main: `75e018ac775dcebb459d43d77a5fe46ae7951efd`. Prior accepted PR head: `f3ed96830032050bd615bb0902d85f7c485949f6`. Actual captured and exercised page blob: `05a89adbcbeadb9840b74d84394d8421cef9fd58`. Template `69e5ba0157cc49a3368a308b8c45914012e6962e` and CSS `99feca51197fd2006c1857e9fab7d46b2f170a77` remain the accepted contribution.

The composed page preserves current main's data, rank/order, content, all20 script blocks and17:35UTC footer. Only41 existing labels acquire canonical sector links (overview2, Markets8, Sector chips12, rotation10, playbook9), the primary stylesheet reference changes, and one bilingual explanation is retained. All16 canonical destination pages were materialized from the exact receiver. The complete inverse recovers current main byte for byte. The same source compositor applied to the earlier base reproduces accepted page d8434b45ed3ef08a990f3f8d0404cb2b19d716b9 exactly.

## Actual affected checks

- The existing current-row/canonical-destination test passed. The focus/CSS test initially lacked two transitive stylesheet fixture files, then passed after exact committed materialization. All five stylesheet includes were verified B=H=M. Only the affected failed test was repeated; the original successful current-row result is retained.
- Actual canonical CI metadata and197-owner curated parity passed: unrun-template-chips31→34, commands9→10, test tokens11→12, joined characters707→767. All400owners/399siblings and current ledger definition remain. Ceilings5951/5972/5709 retain jobcaps137/138/131 and ten packs. This does not claim a new full-tree paired planner run.
- Canonical browser capture produced **8/8 genuine REST cells** across desktop1440×900/mobile390×844, EN/ZH and dark/light. All applied states, PNG signatures, dimensions, byte lengths and SHA256 digests were checked. Final capture reports **zero console errors and zero failed HTTP responses**. Both viewports report no document horizontal overflow; the mobile inner-element metric remains recorded unchanged.
- Root visually inspected desktop EN dark/light, mobile EN dark and mobile ZH light actual PNGs. The current layout is coherent, labels wrap within the page, and the sector links remain visible. These are source-scope observations, not approval of every pre-existing UI/data state.
- The original five-family keyboard procedure passed **40/40 real Tab+Enter journeys**, one representative target per family across all eight state combinations. Actual canonical href,200 destination, title, localized heading/ticker and2px solid focus ring with2px offset passed. All eight overview activations recorded one trusted click, zero bubbled card activations and zero Sector-dialog openings. No locator.focus fallback was added.
- The current receiver's exact visual-evidence consumer `f4973ba99ab6c66d343485d9999c147ffef0d013` passed against the exact visual source diff. Its entire **231-receipt current catalog**, every referenced byte for the actual five owning receipts, and all59 historical subject files were present. Unrelated PNGs are not inputs to this scoped consumer; no claim is made that all11954 mockup files were copied.
- C3 process94231 completed EXIT0: capture40.902771seconds; keyboard52.224881seconds; total96.09seconds. All505 public fixture source files, including the page, were verified unchanged before and after. Consumer process37301 completed EXIT0. See the original execution/consumer receipts for precise data.

The manifest's per-page `page_tree_sha` was attached after actual before/after page-byte verification; the original capture manifest digest is retained in consumer-receipt.json. The capture tool's nearest Git HEAD is context only. No old screenshot was relabeled as this new page.

## Reused evidence and retained diagnostics

All59 historical PR evidence files remain exact original blobs. The earlier24-cell package remains bound to d843 and supplies unchanged hover/focus presentation evidence. This package supplies new8-cell REST and40-journey proof for05a. The unchanged template/CSS/config/i18n and complete five-include stylesheet closure justify that separation; eight fresh REST cells are not represented as24 new interaction screenshots.

The first fresh capture used an incomplete local root-asset fixture:16 JS/CSS requests returned404, and the first keyboard journey lacked theme variables and failed focus. Those images are not accepted evidence. Initial fixture/test/capture/keyboard receipts are conserved as exact original text and blob hashes in initial-fixture-diagnostics.json. Adding198 exact current root assets corrected the fixture without changing page05a; the full affected browser matrix then ran. No failed observation was overwritten or silently converted to PASS.

## Gaps and authority ceiling

These are anonymous local committed-snapshot checks. Authenticated free/essential/pro and loading/empty/stale/error cells remain explicit gaps. The keyboard context blocks external origins, including TradingView tv.js; destination pages retain the observed “TradingView is not defined” errors. Navigation, headings and focus passed; external charts are not qualified. Snapshot dates, UI status and missing-price notices are retained output, not an independent market-data freshness assertion.

No provider refresh, collector, VM/full renderer, saved login, private/live origin, production deployment, empirical/scientific claim or trading authority. The former public proof workspace was closed before this new operation; private/refused workspaces were not adopted. Natural successor CI and scoped source release remain required after publication.

## Reproduction

Use the exact public fixture identities in fixture-provenance.json and an owned anonymous local origin. The canonical capture invocation is in execution-receipt.json; no forced hover/focus states were requested in this new8-cell run. The actual keyboard source below differs from the original verified harness only in the owned fixture/output locations and exact page/receiving-main pins. Its Git-blob hash is `ff2ab37d1983db10f18cccb3ffb301a6f5b5f46b`.


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
ROOT=Path("/Volumes/Mastermind/agent-workspaces/macro/web/macro-8184-current-page-proof-20261109-c3-0467/proof-fixtures/pr8184-ledger-20261109");SITE=ROOT/"site";OUT=ROOT/"mockups/evidence/china-sector-detail-links-20261109-ledger-final/keyboard-journeys.json"
sys.path.insert(0,str(ROOT))
from scripts.capture_page_evidence import state_seed_source,_APPLY_STATE_SCRIPT
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
assert blob(SITE/"china.html")=="05a89adbcbeadb9840b74d84394d8421cef9fd58"
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
 proof={"schema":"mastermind.china_sector_keyboard_proof.v1","receiving_main":"75e018ac775dcebb459d43d77a5fe46ae7951efd","page_blob":blob(SITE/"china.html"),"css_blob":blob(SITE/"assets/css/aeabd751.css"),"duration_seconds":time.time()-started,"planned_journeys":40,"completed_journeys":len(rows),"passed_journeys":sum(r["status"]=="passed" for r in rows),"external_network":"External origins blocked explicitly; current pinned local snapshot only","journeys":rows}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 print(json.dumps({"proof":str(OUT),"completed":len(rows),"passed":proof["passed_journeys"],"seconds":proof["duration_seconds"]}),flush=True)
assert len(rows)==40 and all(r["status"]=="passed" for r in rows)

```
