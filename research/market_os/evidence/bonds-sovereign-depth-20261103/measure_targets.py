import sys,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(__file__).parent;phase=sys.argv[1];folder=sys.argv[2]
cells=[(1440,900,"dark","en"),(390,844,"light","zh")] if phase=="red" else [(w,h,t,l) for w,h in [(1440,900),(390,844)] for t in ["dark","light"] for l in ["en","zh"]]
rows=[]
with sync_playwright() as p:
 b=p.chromium.launch()
 for w,h,t,l in cells:
  html=(out/folder/f"{w}-{t}-{l}.html").read_text();ctx=b.new_context(viewport={"width":w,"height":h},has_touch=w==390,is_mobile=w==390,reduced_motion="reduce");blocked=[]
  def route(r):
   if r.request.url.split("#")[0]=="https://bonds-fixture.invalid/bonds.html":r.fulfill(status=200,content_type="text/html",body=html)
   elif r.request.url.startswith("https://bonds-fixture.invalid/fonts/"):
    f=out/"retained-fonts"/r.request.url.rsplit("/",1)[-1]
    if f.is_file():r.fulfill(status=200,content_type="font/woff2",body=f.read_bytes())
    else:blocked.append(r.request.url);r.abort()
   else:blocked.append(r.request.url);r.abort()
  ctx.route("**/*",route);page=ctx.new_page();page.goto("https://bonds-fixture.invalid/bonds.html#global-detail");page.evaluate("document.fonts.ready")
  summary=page.locator('#global-detail details.mx-disc summary');summary.focus();before=summary.bounding_box();page.keyboard.press("Enter");assert page.locator('#global-detail details.mx-disc').get_attribute('open') is not None
  controls=page.locator('#global-detail details.mx-disc summary, #global-detail details.mx-disc a').evaluate_all("es=>es.map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,text:e.innerText,width:r.width,height:r.height,href:e.getAttribute('href'),display:s.display,listStyleType:s.listStyleType,outlineStyle:s.outlineStyle}})")
  if phase!="red":
   assert all(x['width']>=40 and x['height']>=40 for x in controls),controls
   assert controls[0]['display']=='list-item' and 'disclosure' in controls[0]['listStyleType']
   assert controls[0]['outlineStyle']!='none'
   assert before['height']>=40 and before['width']>=40
   for a in page.locator('#global-detail details.mx-disc a').all():
    a.scroll_into_view_if_needed();a.focus();assert a.evaluate("e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2).closest('a')===e}")
    assert a.evaluate("e=>getComputedStyle(e).outlineStyle")!='none'
   if w==390:
    summary.tap();assert page.locator('#global-detail details.mx-disc').get_attribute('open') is None;summary.tap();assert page.locator('#global-detail details.mx-disc').get_attribute('open') is not None
  assert not blocked
  rows.append({'viewport':[w,h],'theme':t,'locale':l,'summary_closed_box':before,'controls':controls,'all_at_least40':all(x['width']>=40 and x['height']>=40 for x in controls),'external_transport':0});ctx.close()
 b.close()
result={'phase':phase,'fixture':folder,'scope':'Only NEW sovereign disclosure summary/source links; original native controls, hrefs, focus and marker','cells':rows};(out/f'target-metrics-{phase}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({'phase':phase,'cells':len(rows),'controls_measured':sum(len(r['controls']) for r in rows),'min_width':min(c['width'] for r in rows for c in r['controls']),'min_height':min(c['height'] for r in rows for c in r['controls']),'all_at_least40':all(r['all_at_least40'] for r in rows)}))
