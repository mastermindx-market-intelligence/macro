from pathlib import Path
import importlib.util,json,mimetypes
from urllib.parse import urlparse,unquote
from playwright.sync_api import sync_playwright
ROOT=Path("/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/d03-winner-t44-proof-20261104-c2-05a1d4b6b06d54cc")
E=ROOT/"research/design_candidates/production_design_20261102/evidence/d03-winner-t44-20261104"
spec=importlib.util.spec_from_file_location("t44_driver",E/"verify_browser.py")
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
html=(E/"diagnostics/pilot/rendered/n11-w.html").read_bytes()
TRACE=r"""(() => {
 window.__t44Trace=[];
 const state=()=>{const p=document.querySelector('.lens-pop');
   return {popup:p&&p.className,kind:p&&p.getAttribute('data-kind'),
     active:document.activeElement&&document.activeElement.tagName+'.'+document.activeElement.className,
     locked:document.documentElement.classList.contains('lens-lock')};};
 for(const capture of [true,false])for(const type of ['pointerdown','pointerup','touchstart','touchend','mousedown','mouseup','focusin','click']){
  document.addEventListener(type,e=>{
   const x={event:type,phase:capture?'capture':'bubble',target:e.target.tagName+'.'+e.target.className,...state()};
   window.__t44Trace.push(x);
   queueMicrotask(()=>window.__t44Trace.push({after:type,phase:x.phase,...state()}));
  },capture);
 }
})();"""
def route_request(route):
 p=urlparse(route.request.url);path=unquote(p.path).removeprefix("/case/").lstrip("/")
 if p.hostname!="127.0.0.1":route.abort();return
 if path=="n11-w.html":route.fulfill(status=200,content_type="text/html; charset=utf-8",body=html);return
 if path=="live_config.js":route.fulfill(status=200,content_type="text/javascript",body=driver.LIVE_CONFIG_FIXTURE);return
 for base in [ROOT/"templates",ROOT/"site"]:
  f=(base/path).resolve()
  if f.is_relative_to(base) and f.is_file():
   route.fulfill(status=200,content_type=mimetypes.guess_type(f)[0] or "application/octet-stream",body=f.read_bytes());return
 route.fulfill(status=404,body="")
def snapshot(page):
 return page.evaluate("""() => {const p=document.querySelector('.lens-pop');return {
   trace:window.__t44Trace,open:!!document.querySelector('.lens-pop.open'),
   trigger:document.querySelector('.row .lens-term.lib').outerHTML.slice(0,250),
   popup:p&&{class:p.className,kind:p.dataset.kind,text:p.innerText,rect:p.getBoundingClientRect().toJSON(),
   opacity:getComputedStyle(p).opacity,display:getComputedStyle(p).display},
   hoverNone:matchMedia('(hover:none)').matches,sheet:matchMedia('(max-width:640px)').matches,
   active:document.activeElement&&document.activeElement.outerHTML.slice(0,180)
 };}""")
out={}
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 for mode in ["touch","keyboard"]:
  c=b.new_context(viewport={"width":320,"height":900},is_mobile=mode=="touch",has_touch=mode=="touch",device_scale_factor=1)
  c.add_init_script("localStorage.setItem('theme','light');localStorage.setItem('lang','en');")
  c.add_init_script(TRACE);c.route("**/*",route_request);p=c.new_page()
  p.goto("http://127.0.0.1/case/n11-w.html",wait_until="load");p.evaluate("document.fonts.ready")
  t=p.locator(driver.TRIGGER);t.scroll_into_view_if_needed()
  if mode=="touch":
   t.tap();p.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
   out["first_tap"]=snapshot(p);p.screenshot(path=str(E/"diagnostics/touch-first.png"))
   p.evaluate("window.__t44Trace=[]")
   t.tap();p.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
   out["second_tap"]=snapshot(p);p.screenshot(path=str(E/"diagnostics/touch-second.png"))
  else:
   driver.open_card(p,False);out["mobile_keyboard"]=snapshot(p)
   p.screenshot(path=str(E/"diagnostics/mobile-keyboard.png"))
  c.close()
 b.close()
(E/"diagnostics/touch-events.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:{"open":v["open"],"popup":v["popup"],"trace":v["trace"]} for k,v in out.items()},ensure_ascii=False))
