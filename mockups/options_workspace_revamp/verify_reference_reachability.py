"""Check the known assistant-overlap boundary on the supporting reference."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent;OUT=HERE/"visual";ORIGIN="http://127.0.0.1:8768";rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for w,h,theme,lang in [(1440,1000,"light","en"),(390,844,"dark","zh")]:
        ctx=browser.new_context(viewport={"width":w,"height":h})
        ctx.route("**/*",lambda r:r.continue_() if r.request.url.startswith(ORIGIN+"/") else r.abort())
        page=ctx.new_page();page.goto(ORIGIN+f"/mockups/options_workspace_revamp/reference.html?theme={theme}&lang={lang}",wait_until="networkidle")
        spy=page.locator('.ref-index[href="#ticker?t=SPY"]')
        spy.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})")
        check=page.evaluate("""() => {
          const card=document.querySelector('.ref-index[href="#ticker?t=SPY"]'),orb=document.querySelector('#mmb-boot,#mmb-launch');
          const box=orb?.getBoundingClientRect();
          const items=[...card.querySelectorAll('.ref-index-price,.ref-regime,.ref-levels b,.ref-index-foot')].map(e=>{
            const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
            return {text:e.innerText,in_view:r.top>=0&&r.bottom<=innerHeight,covered:!!box&&x>=box.left&&x<=box.right&&y>=box.top&&y<=box.bottom};
          });return {items,all_reachable:items.every(x=>x.in_view&&!x.covered)};
        }""")
        page.screenshot(path=str(OUT/f"reachable-spy-{w}-{theme}-{lang}.png"))
        summary=page.locator('#source-availability>summary')
        summary.focus();page.keyboard.press("Enter")
        focused=summary.evaluate("e=>document.activeElement===e")
        opened=page.locator('#source-availability').get_attribute("open") is not None
        summary.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})")
        clickable=summary.evaluate("""e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===hit||e.contains(hit)}""")
        rows.append({"width":w,"theme":theme,"lang":lang,"spy":check,"source_details":{"keyboard_focus":focused,"opened":opened,"center_unobstructed":clickable}})
        ctx.close()
    browser.close()
(OUT/"reference-reachability.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
print(json.dumps(rows,indent=2))
