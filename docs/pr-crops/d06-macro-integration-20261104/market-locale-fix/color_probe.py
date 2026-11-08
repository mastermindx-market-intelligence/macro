from pathlib import Path
import sys,json,hashlib,math,http.server,functools,threading,collections
root=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/d06-macro-implementation-20261104-c4")
sys.path.insert(0,str(root))
from scripts import verify_d06_macro as v
phase=sys.argv[1];assert phase in ("baseline","fixed")
out=root/"docs/pr-crops/d06-macro-integration-20261104/market-locale-fix";out.mkdir(parents=True,exist_ok=True);v.OUT=out
payload=json.loads((root/"data/market_structure/latest.json").read_text())
history=[x for x in payload["gamma"]["history"] if isinstance(x.get("net_gex_bn"),(int,float)) and math.isfinite(x["net_gex_bn"])]
assert collections.Counter(x["regime"] for x in history)=={"long":50,"short":25}
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(v.QuietHandler,directory=str(root/"site")))
threading.Thread(target=server.serve_forever,daemon=True).start();base="http://127.0.0.1:"+str(server.server_port)
sources=["templates/market_structure.html.j2","site/market_structure.html","site/theme.css","data/market_structure/latest.json"]
before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources}
receipt={"phase":phase,"producer_regimes":dict(collections.Counter(x["regime"] for x in history)),"source_before":before,"contexts":[],"status":"started"}
try:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,channel="chrome",timeout=30000)
  contexts=[(390,"light","zh")] if phase=="baseline" else [(1440,"dark","en"),(390,"light","en"),(1440,"dark","zh"),(390,"light","zh")]
  for width,theme,locale in contexts:
   ctx,page,errors=v.make_page(browser,base,width,theme,locale)
   page.goto(base+"/market_structure.html",wait_until="networkidle")
   page.locator('#gex-range-btns button[data-range="9999"]').click()
   page.wait_for_function("document.querySelectorAll('#gex-chart rect').length===75")
   v.assert_reflow(page)
   actual=page.locator("#gex-chart rect").evaluate_all("(xs)=>xs.map(e=>({fill:e.getAttribute('fill'),color:getComputedStyle(e).fill}))")
   palette=page.evaluate("""() => {
     const c=getComputedStyle(document.documentElement);
     const rgb=s=>{s=s.trim();if(/^#[0-9a-f]{6}$/i.test(s)){return 'rgb('+[1,3,5].map(i=>parseInt(s.slice(i,i+2),16)).join(', ')+')';}return s;};
     return {up:rgb(c.getPropertyValue('--up')),down:rgb(c.getPropertyValue('--down')||c.getPropertyValue('--dn')),legacyDown:rgb(c.getPropertyValue('--dn'))};
   }""")
   assert palette["up"]!=palette["down"],palette
   matches=[x["color"]==palette["up" if h["regime"]=="long" else "down"] for h,x in zip(history,actual)]
   if phase=="baseline":
    assert sum(matches)==50 and all(x["color"]==palette["legacyDown"] for h,x in zip(history,actual) if h["regime"]=="short"),(palette,collections.Counter(x["color"] for x in actual))
   else:assert all(matches),(palette,[(h["date"],h["regime"],x) for h,x,ok in zip(history,actual,matches) if not ok][:4])
   shot=v.capture(page,f"gex-colors-{phase}-{width}-{theme}-{locale}")
   receipt["contexts"].append({"width":width,"theme":theme,"locale":locale,"palette":palette,"bars":len(actual),"classification_color_matches":sum(matches),"colors":dict(collections.Counter(x["color"] for x in actual)),"all_producer_regimes_retained":True,"image":shot})
   assert not errors,errors
   ctx.close()
  browser.close()
 receipt["status"]="expected_failure_reproduced" if phase=="baseline" else "passed"
finally:
 server.shutdown();server.server_close()
 receipt["source_after"]={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources};receipt["source_stable"]=receipt["source_after"]==before
 (out/(phase+"-colors.json")).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"phase":phase,"status":receipt["status"],"contexts":len(receipt["contexts"]),"matches":[x["classification_color_matches"] for x in receipt["contexts"]],"source_stable":receipt["source_stable"]}))
