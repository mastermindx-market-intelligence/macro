import json,sys,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(__file__).parent;phase=sys.argv[1];src=out/("render-"+phase);dest=out/("capture-"+phase);dest.mkdir(exist_ok=True)
cells=[(390,844,"light","zh")] if phase=="before" else [(w,h,t,l) for w,h in [(1440,900),(390,844)] for t in ["dark","light"] for l in ["en","zh"]]
if phase.startswith("frame-"):cells=[(1440,900,"dark","en"),(390,844,"light","zh")]
records=[]
with sync_playwright() as p:
 browser=p.chromium.launch()
 for w,h,t,l in cells:
  stem=f"{w}-{t}-{l}";html=(src/(stem+".html")).read_text();ctx=browser.new_context(viewport={"width":w,"height":h},reduced_motion="reduce",has_touch=w==390,is_mobile=w==390)
  fulfilled=[];blocked=[];errors=[]
  def route(r):
   if r.request.url.split("#")[0]=="https://bonds-fixture.invalid/bonds.html":fulfilled.append(r.request.url);r.fulfill(status=200,content_type="text/html",body=html)
   elif r.request.url.startswith("https://bonds-fixture.invalid/fonts/"):
    font=out/"retained-fonts"/r.request.url.rsplit("/",1)[-1]
    if font.is_file():fulfilled.append(r.request.url);r.fulfill(status=200,content_type="font/woff2",body=font.read_bytes())
    else:blocked.append(r.request.url);r.abort()
   else:blocked.append(r.request.url);r.abort()
  ctx.route("**/*",route);page=ctx.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
  page.goto("https://bonds-fixture.invalid/bonds.html#deeper",wait_until="domcontentloaded")
  page.evaluate("document.fonts.ready")
  opener=page.locator('#deeper a[href="#global-detail"]');opener.focus();page.keyboard.press("Enter");page.wait_for_url("**/bonds.html#global-detail")
  rows=page.locator('#global-detail .sc-tbl tr');jp=rows.filter(has=page.locator('.cty',has_text="Japan"));assert jp.count()==1
  rowtext=jp.inner_text();rowshot=dest/(stem+"-row.png");page.screenshot(path=str(rowshot))
  row={"viewport":[w,h],"theme":t,"locale":l,"japan_row_text":rowtext,"stale_tags":jp.locator('.stale-tag').count(),"source_detail_count":page.locator('#global-detail details').count(),"row_screenshot":rowshot.name,"fulfilled_local_documents":fulfilled,"blocked_external_intents":blocked,"page_errors":errors}
  if phase!="before":
   assert "JPY" in rowtext and jp.locator('.stale-tag').count()==1
   details=page.locator('#global-detail details.mx-disc');assert details.count()==1
   summary=details.locator('summary');summary.focus();page.keyboard.press("Enter");assert details.get_attribute('open') is not None
   text=details.inner_text();assert "2026-09-30" in text
   hrefs=details.locator('a').evaluate_all("els=>els.map(e=>e.href)");assert "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv" in hrefs
   if "missing" in phase:
    assert not any("fred.stlouisfed.org/series/DGS10" in a for a in hrefs)
    assert ("Observation date unavailable" in text if l=="en" else "观测日期未知" in text)
   else:assert any("fred.stlouisfed.org/series/DGS10" in a for a in hrefs)
   if phase.startswith("frame-"):
    assert all(e["width"]>=40 and e["height"]>=40 for e in details.locator("summary,a").evaluate_all("es=>es.map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height}})"))
   details.locator("div.note").filter(has_text="Japan").scroll_into_view_if_needed()
   shot=dest/(stem+"-sources.png");page.screenshot(path=str(shot));row.update(source_text=text,source_hrefs=hrefs,source_screenshot=shot.name,keyboard_disclosure=True,source_link_color=details.locator("a").first.evaluate("e=>getComputedStyle(e).color"),source_link_decoration=details.locator("a").first.evaluate("e=>getComputedStyle(e).textDecorationLine"),source_card_background=details.evaluate("e=>getComputedStyle(e.closest(\".card\")).backgroundColor"))
   if w==390:
    summary.tap();assert details.get_attribute('open') is None;summary.tap();assert details.get_attribute('open') is not None;row['touch_disclosure']=True
  else:
   assert jp.locator('.stale-tag').count()==0
  page.go_back();page.wait_for_url("**/bonds.html#deeper");row['return_url']=page.url;row['returned_to_same_document_and_entry']=True
  row['document_overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth');assert not row['document_overflow'];assert not blocked and not errors
  row['row_screenshot_sha256']=hashlib.sha256(rowshot.read_bytes()).hexdigest();records.append(row);ctx.close()
 browser.close()
record={"scope":"Controlled offline native owner + actual authored Bonds fragments, incumbent page/shared CSS and retained Inter fonts; normal keyboard hash drill, native source disclosure, in-document history return only. No hosted Shell/bridge, auth, chart, remote source response or served proof.","phase":phase,"external_transport_requests":0,"cells":records}
(dest/'observations.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n");print(json.dumps({"phase":phase,"cells":len(records),"errors":sum(len(c['page_errors']) for c in records),"overflow":sum(c['document_overflow'] for c in records)}))
