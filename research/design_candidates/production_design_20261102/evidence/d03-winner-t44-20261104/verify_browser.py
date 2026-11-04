"""D03 T44: source-pinned Winner Health boundary/disclosure browser evidence.
Evidence-only: actual builder, page writer, template and shared assets; four synthetic
v2 fixtures. No analogue engine, live market data, auth, deployment or product edits.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import unquote, urlparse

BASE = "ffda5424b75bbbb26e33a4d328043bbfb480e6ff"
BUILDER_HASH = "be6fb99b48d9de9a432d063557e93574ad8336837abd7571006e5e4978d7bd3e"
SOURCE_FILES = (
    "scripts/build_winner_health_page.py", "templates/winner_health.html.j2",
    "templates/theme.css", "templates/theme.js", "lib/pages.py",
    "lib/shared_shell.py", "lib/config.py", "engine/top_maturation.py",
)
TRIGGER = ".row .lens-term.lib"
LIVE_CONFIG_FIXTURE = "/* Synthetic fixture: live overlays disabled; production config key contract. */\nwindow.LIVE_QUOTES_URL='';window.LIVE_SNAPSHOT_URL='';window.LIVE_POLL_SEC=60;window.LIVE_STALE_MIN=20;window.LIVE_DELAYED_MIN=0;window.LIVE_FEED_LABEL='';window.LIVE_FEED_LABEL_ZH='';window.LIVE_WS_TAPE=false;window.LIVE_ENABLED=false;\n"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fixture(n, track):
    row = {
        "ticker": f"T44{track}{n}", "name": "Synthetic boundary fixture",
        "name_zh": "合成边界样本", "href": f"/stocks/T44{track}{n}.html",
        "r126": 0.62, "r21": 0.08, "days_in_episode": 88,
        "state": "extended_watch", "spark": [100 + i * 0.4 for i in range(63)],
        "episode_high": 142.87,
        "legs": [{"key": "updown_volume",
                  "words_en": "selling days now heavier", "words_zh": "下跌日成交更重",
                  "tip_en": "Down-day volume has outweighed up-day volume in 12 of the last 21 sessions.",
                  "tip_zh": "最近 21 个交易日中，有 12 天的下跌日成交量超过了上涨日。"}],
        # Outcomes are deliberately populated even for N=11. Their suppression
        # must come from the threshold, not absent fixture values.
        "analog": {"n": n, "n_h63": n, "topped_63td": 4,
                   "median_further_gain": 0.11, "median_drop_from_high": -0.24,
                   "track": track},
    }
    states = {key: [] for key in
              ("extended_healthy", "extended_watch", "thinning", "breaking", "no_read")}
    states["extended_watch"] = [row]
    return {
        "schema": "winner_health.v2", "fixture_only": True,
        "asof": "2026-11-04", "data_last_day": "2026-11-03",
        "universe_n": 100, "null_state": False, "macro_backdrop": None,
        "tiers": [{"key": "primary", "readable": True, "figure": "r126",
                   "extended_n": 1, "states": states, "theme_counts": [],
                   "library": {"track": track, "window_start": "2022-07",
                               "window_end": "2026-07", "horizon_td": 63,
                               "drawdown_pct": 20}}],
    }

def require(value, message):
    if not value:
        raise AssertionError(message)

GEOMETRY = r"""pop => {
 const r=pop.getBoundingClientRect(), style=getComputedStyle(pop);
 const receipt=pop.querySelector('.lens-receipt');
 const rr=receipt.getBoundingClientRect();
 const all=[], walk=document.createTreeWalker(pop,NodeFilter.SHOW_TEXT);
 let node;
 while(node=walk.nextNode()){
  if(!node.textContent.trim()) continue;
  const parent=node.parentElement;
  if(!parent || !parent.getClientRects().length || getComputedStyle(parent).visibility==='hidden') continue;
  const range=document.createRange();range.selectNodeContents(node);
  for(const x of range.getClientRects()) if(x.width && x.height)
   all.push({left:x.left,right:x.right,top:x.top,bottom:x.bottom,text:node.textContent.trim().slice(0,100)});
 }
 const obscured=[];
 const rw=document.createTreeWalker(receipt,NodeFilter.SHOW_TEXT);
 let rn;
 while(rn=rw.nextNode()){
  if(!rn.textContent.trim() || !rn.parentElement.getClientRects().length) continue;
  const range=document.createRange();range.selectNodeContents(rn);
  for(const box of range.getClientRects()){
   if(!box.width||!box.height)continue;
   for(const fraction of [.1,.3,.5,.7,.9]){
    const x=box.left+box.width*fraction,y=(box.top+box.bottom)/2;
    const top=document.elementFromPoint(x,y);
    if(top && !pop.contains(top))obscured.push({
      text:rn.textContent.trim(),x,y,
      top:top.tagName+(top.id?'#'+top.id:'')+'.'+top.className,
      owner:top.closest('[id]')?.id||null,
      root:top.closest('[id]')?.outerHTML.slice(0,250)||null
    });
   }
  }
 }
 const visible=[...pop.querySelectorAll('.lens-title,.lens-body,.lensx-v,.lensx-note,.r-i')]
   .filter(e=>e.getClientRects().length).map(e=>{
    const s=getComputedStyle(e);return {selector:e.className,fontSize:s.fontSize,
    lineHeight:s.lineHeight,color:s.color,background:s.backgroundColor,text:e.innerText};
   });
 return {
   viewport:{width:innerWidth,height:innerHeight},
   popup:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom,
          scrollWidth:pop.scrollWidth,clientWidth:pop.clientWidth,
          scrollHeight:pop.scrollHeight,clientHeight:pop.clientHeight,scrollTop:pop.scrollTop},
   receipt:{x:rr.x,y:rr.y,right:rr.right,bottom:rr.bottom},
   pageOverflow:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-innerWidth,
   receiptOcclusion:obscured,
   horizontalTextOverflow:all.filter(x=>x.left<r.left-1||x.right>r.right+1),
   style:{background:style.backgroundColor,color:style.color,
          animationName:style.animationName,transitionProperty:style.transitionProperty,
          transitionDuration:style.transitionDuration,
          beforeAnimation:getComputedStyle(pop,'::before').animationName},
   textStyles:visible,
   receiptItems:[...receipt.querySelectorAll('.r-i')].map(e=>e.innerText)
 };
}"""

def open_card(page, mobile):
    trigger = page.locator(TRIGGER)
    require(trigger.count() == 1, "expected exactly one synthetic analogue opener")
    trigger.scroll_into_view_if_needed()
    method = {"primary_input": "native touchscreen tap" if mobile else "native keyboard Tab",
              "first_tap_persisted": None, "keyboard_fallback": False}
    need_keyboard = not mobile
    if mobile:
        trigger.tap()
        page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        method["first_tap_persisted"] = page.locator(".lens-pop.open[data-kind='record']").count() == 1
        if not method["first_tap_persisted"]:
            # Retain the failed tap; keyboard is a separate content qualification,
            # never a substitute acceptance result for the tap journey.
            method["keyboard_fallback"] = True
            need_keyboard = True
    if need_keyboard:
        previous = trigger.evaluate(r"""target => {
          const candidates=[...document.querySelectorAll(
            'a[href],button,input,select,textarea,[tabindex]')].filter(e=>
            e.tabIndex>=0 && !e.disabled && e.getClientRects().length &&
            getComputedStyle(e).visibility!=='hidden');
          const i=candidates.indexOf(target);
          if(i<1) throw new Error('no preceding visible tab stop');
          const p=candidates[i-1];p.focus();
          return {tag:p.tagName,id:p.id,text:(p.innerText||'').slice(0,70)};
        }""")
        page.keyboard.press("Tab")
        require(trigger.evaluate("e=>e===document.activeElement"), "Tab did not reach analogue opener")
        method["previous_tab_stop"] = previous
    pop = page.locator(".lens-pop.open[data-kind='record']")
    pop.wait_for(state="visible")
    page.wait_for_function("""() => {
      const p=document.querySelector('.lens-pop.open[data-kind="record"]');
      return p && Number(getComputedStyle(p).opacity)>0.99 &&
        p.getAnimations({subtree:true}).every(a =>
          a.effect.getComputedTiming().iterations===Infinity || a.playState!=='running');
    }""")
    require(trigger.get_attribute("aria-describedby") == "lensPop", "missing active description relation")
    return trigger, pop, method

def check_semantics(pop, n, track, lang):
    text = " ".join(pop.inner_text().split())
    receipt = " ".join(pop.locator(".lens-receipt").inner_text().split())
    opposite = "zh" if lang == "en" else "en"
    require(pop.locator(f".l-{opposite}:visible").count() == 0, "opposite language is visible")
    require(pop.locator(f".l-{lang}:visible").count() > 0, "selected language missing")
    require(str(n) in receipt and ("episodes" if lang == "en" else "段行情") in receipt,
            "episode denominator missing from receipt")
    require("2022-07" in receipt and "2026-07" in receipt, "history window missing")
    names = ("whole US market" if track == "W" else "curated") if lang == "en" else (
        "全市场" if track == "W" else "精选池")
    require(names in receipt, "wrong history track receipt")
    opposite_names = ("curated" if track == "W" else "whole US market") if lang == "en" else (
        "精选池" if track == "W" else "全市场")
    require(opposite_names not in receipt, "conflicting history track receipt")
    thin = "too few to read as a pattern" if lang == "en" else "太少，不足以当作规律来看"
    curated = "under-represented" if lang == "en" else "样本中偏少"
    whole = "includes names that later delisted" if lang == "en" else "包含了后来退市的个股"
    if n == 11:
        require(thin in text, "thin-record explanation missing at N=11")
        require(pop.locator(".lensx-rows").count() == 0, "N=11 exposed outcome rows")
        for word in (("Fell back hard","Kept going","When they fell","11%","24%") if lang=="en"
                     else ("大幅回落","继续上行","回落时","11%","24%")):
            require(word not in text, f"N=11 exposed outcome content: {word}")
        require(whole not in text, "thin W fixture unexpectedly used rich-card disclosure")
    else:
        require(thin not in text, "N=12 still shows thin-history warning")
        require(pop.locator(".lensx-row").count() == 3, "N=12 expected three populated outcome rows")
        for phrase in (("4 of 12","The other 8","11%","24%","history, not a forecast",
                        "about 1 in 3","also cleared this group's bar") if lang=="en" else
                       ("12 段里有 4 段","其余 8 段","11%","24%","是历史，不是预测",
                        "大约每 3 段有 1 段","同样达到本组门槛")):
            require(phrase in text, f"N=12 missing historical disclosure: {phrase}")
        require((whole in text) == (track=="W"), "wrong whole-market delisting disclosure")
    require((curated in text) == (track=="D"), "wrong curated survivorship disclosure")
    return {"visible_text":text,"receipt":receipt,"n":n,"track":track}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--pilot",action="store_true")
    ap.add_argument("--preflight",action="store_true")
    args=ap.parse_args()
    root=args.root.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    drift=subprocess.check_output(["git","diff","--name-only",BASE,"--",
        "templates","scripts","lib","engine","site","config.yml"],cwd=root,text=True)
    require(not drift.strip(),f"product source differs from pinned baseline: {drift}")
    hashes={p:digest(root/p) for p in SOURCE_FILES}
    require(hashes["scripts/build_winner_health_page.py"]==BUILDER_HASH,"builder hash drift")
    require(hashes["templates/winner_health.html.j2"]==
            "545454c3650de638e82fec0b06582ad994adb3efe385a3baf293531577f3997f","template hash drift")
    if args.preflight:
        print(json.dumps({"preflight":"PASS","source_baseline":BASE,"checkout_head":head,
                          "product_source_matches_baseline":True,"source_hashes":hashes}))
        return 0
    for folder in ("fixtures","rendered","screenshots"):
        (out/folder).mkdir(exist_ok=True)
    sys.path.insert(0,str(root))
    from scripts import build_winner_health_page as builder
    from lib import config, pages
    from playwright.sync_api import sync_playwright
    cases={f"n{n}-{track.lower()}":fixture(n,track) for n in (11,12) for track in ("W","D")}
    rendered={}
    with tempfile.TemporaryDirectory(prefix="d03-t44-fixture-") as td:
        temp=Path(td)
        (temp/"templates").symlink_to(root/"templates",target_is_directory=True)
        (temp/"config.yml").write_text("storage:\n  data_dir: data\n  site_dir: site\n")
        with patch.object(config,"ROOT",temp),patch.object(pages,"_shim_checked",False), \
             patch.object(socket.socket,"connect",side_effect=AssertionError("builder network is forbidden")):
            for name,ctx in cases.items():
                fp=out/"fixtures"/f"{name}.json"
                fp.write_text(json.dumps(ctx,ensure_ascii=False,indent=2)+"\n")
                actual=builder.build(temp,fixture=fp)
                require(actual==temp/"site"/"winner_health.html","unexpected writer path")
                rendered[name]=actual.read_bytes()
                (out/"rendered"/f"{name}.html").write_bytes(rendered[name])
    assets={};stubs=set();blocked=set();missing=set();page_errors=[]
    def route_request(route):
        parsed=urlparse(route.request.url)
        if parsed.hostname!="127.0.0.1":
            blocked.add(str(parsed.hostname)+parsed.path);route.abort();return
        path=unquote(parsed.path).removeprefix("/case/").lstrip("/")
        if path.endswith(".html") and path[:-5] in rendered:
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body=rendered[path[:-5]])
            return
        if path=="live_config.js":
            route.fulfill(status=200,content_type="text/javascript",body=LIVE_CONFIG_FIXTURE)
            return
        for source_root in (root/"templates",root/"site"):
            asset=(source_root/path).resolve()
            if asset.is_relative_to(source_root) and asset.is_file() and asset.suffix in {
                ".css",".js",".woff2",".woff",".ttf",".svg",".png",".jpg",".ico"}:
                rel=str(asset.relative_to(root));assets[rel]=digest(asset)
                route.fulfill(status=200,content_type=mimetypes.guess_type(asset)[0] or
                              "application/octet-stream",body=asset.read_bytes());return
        if parsed.path.endswith(".json"):
            stubs.add(parsed.path);route.fulfill(status=200,content_type="application/json",body="{}");return
        missing.add(parsed.path);route.fulfill(status=404,content_type="text/plain",body="Unavailable in bounded fixture proof")
    results=[]
    specs=[(name,width,theme,lang,"no-preference")
           for width in (320,390,1440) for theme in ("light","dark") for lang in ("en","zh")
           for name in cases]
    if args.pilot:
        specs=[("n11-w",320,"light","en","no-preference"),
               ("n12-d",1440,"dark","zh","no-preference")]
    else:
        specs += [("n11-w",320,"light","en","reduce"),("n12-d",1440,"dark","zh","reduce")]
    print(json.dumps({"phase":"start","source_head":head,"cases":len(specs),"pilot":args.pilot}),flush=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);version=browser.version
        for name,width,theme,lang,motion in specs:
            label=f"{name}-{width}-{theme}-{lang}"+("-reduce" if motion=="reduce" else "")
            mobile=width<=640
            context=browser.new_context(viewport={"width":width,"height":900},
                device_scale_factor=1,is_mobile=mobile,has_touch=mobile,reduced_motion=motion)
            context.add_init_script(
                f"localStorage.setItem('theme',{json.dumps(theme)});"
                f"localStorage.setItem('lang',{json.dumps(lang)});")
            context.route("**/*",route_request);page=context.new_page();page.set_default_timeout(5000)
            local_errors=[]
            page.on("pageerror",lambda error:local_errors.append(str(error)))
            record={"case":label,"fixture":name,"width":width,"theme":theme,"lang":lang,
                    "motion":motion,"status":"FAIL"}
            try:
                page.goto(f"http://127.0.0.1/case/{name}.html",wait_until="load")
                page.evaluate("document.fonts.ready")
                require(page.locator("html").get_attribute("data-lang")==lang,"language setting drift")
                require(page.locator("html").get_attribute("data-theme")==theme,"theme setting drift")
                trigger,pop,method=open_card(page,mobile)
                row=cases[name]["tiers"][0]["states"]["extended_watch"][0]
                semantic=check_semantics(pop,row["analog"]["n"],row["analog"]["track"],lang)
                record.update(content_status="PASS",semantic=semantic,input=method)
                before=pop.evaluate(GEOMETRY)
                pop.evaluate("e=>e.scrollTop=e.scrollHeight")
                after=pop.evaluate(GEOMETRY)
                p=after["popup"];r=after["receipt"]
                require(p["x"]>=-1 and p["right"]<=width+1 and p["y"]>=-1 and p["bottom"]<=901,
                        f"popup outside viewport: {p}")
                require(p["scrollWidth"]<=p["clientWidth"]+1,"popup horizontal overflow")
                require(after["pageOverflow"]<=1,f"page overflow {after['pageOverflow']}")
                require(not after["horizontalTextOverflow"],f"clipped text {after['horizontalTextOverflow']}")
                require(r["y"]>=p["y"]-1 and r["bottom"]<=p["bottom"]+1,"receipt not reachable in popup")
                require(not local_errors,f"JavaScript errors: {local_errors}")
                if motion=="reduce":
                    s=after["style"]
                    require(s["animationName"]=="none" and s["beforeAnimation"]=="none","reduced-motion animation active")
                    require(s["transitionProperty"]=="opacity","reduced-motion transform transition active")
                screenshot = args.pilot or motion=="reduce" or (
                    (width==320 and theme=="light" and lang=="en") or
                    (width==1440 and theme=="dark" and lang=="zh") or
                    (width==390 and theme=="dark" and lang=="en" and name in ("n11-d","n12-w")))
                if screenshot:
                    pop.evaluate("e=>e.scrollTop=0")
                    page.screenshot(path=str(out/"screenshots"/f"{label}.png"))
                    pop.screenshot(path=str(out/"screenshots"/f"{label}-card.png"))
                if mobile:
                    pop.locator(".lens-x").tap()
                    require(page.locator(".lens-pop.open").count()==0,"touch close did not dismiss")
                    require("lens-lock" not in (page.locator("html").get_attribute("class") or ""),"touch scroll lock remained")
                    dismissal="native close-button tap"
                else:
                    page.keyboard.press("Escape")
                    require(page.locator(".lens-pop.open").count()==0,"Escape did not dismiss")
                    require(trigger.evaluate("e=>e===document.activeElement"),"Escape moved trigger focus")
                    require(trigger.get_attribute("aria-describedby") is None,"stale active description after Escape")
                    dismissal="Escape; focus retained"
                blockers=[]
                if method["first_tap_persisted"] is False: blockers.append("first_tap_self_dismissal_owned_by_PR6860")
                if after["receiptOcclusion"]: blockers.append("receipt_obscured_by_shared_assistant")
                record.update(status="BLOCKED" if blockers else "PASS",blockers=blockers,input=method,dismissal=dismissal,semantic=semantic,
                              initial_geometry=before,receipt_geometry=after,
                              trigger_box=trigger.bounding_box())
            except Exception as exc:
                record["error"]=f"{type(exc).__name__}: {exc}"
                page.screenshot(path=str(out/"screenshots"/f"{label}-FAIL.png"))
            record["javascript_errors"]=local_errors
            page_errors.extend({"case":label,"error":e} for e in local_errors)
            results.append(record)
            print(json.dumps({"case":label,"status":record["status"],"error":record.get("error")}),flush=True)
            context.close()
        browser.close()
    source_after={p:digest(root/p) for p in SOURCE_FILES}
    source_unchanged=hashes==source_after
    failures=[r for r in results if r["status"]=="FAIL"]
    blocked_cases=[r for r in results if r["status"]=="BLOCKED"]
    report={
      "task":"D03 T44","created_at":datetime.now(timezone.utc).isoformat(),"source_head":head,"source_baseline":BASE,
      "fixture_only":True,"current_schema":"winner_health.v2","browser":f"Chromium {version}",
      "builder_path":"actual build(root, fixture) -> lib.pages.write_page in temporary root",
      "browser_origin":"Playwright-intercepted http://127.0.0.1; no network server",
      "source_hashes":hashes,"source_after":source_after,"source_unchanged":source_unchanged,
      "served_asset_hashes":assets,"stubbed_unrelated_json":sorted(stubs),
      "synthetic_live_config":{"live_enabled":False,"live_ws_tape":False,
                               "sha256":hashlib.sha256(LIVE_CONFIG_FIXTURE.encode()).hexdigest()},
      "blocked_external_requests":sorted(blocked),"missing_local_resources":sorted(missing),
      "rendered_hashes":{name:hashlib.sha256(body).hexdigest() for name,body in rendered.items()},
      "fixture_hashes":{name:digest(out/"fixtures"/f"{name}.json") for name in cases},
      "cases":results,"total":len(results),"passed":sum(r["status"]=="PASS" for r in results),
      "content_passed":sum(r.get("content_status")=="PASS" for r in results),
      "blocked":len(blocked_cases),
      "first_tap_failures":sum(r.get("input",{}).get("first_tap_persisted") is False for r in results),
      "receipt_occlusions":sum(bool(r.get("receipt_geometry",{}).get("receiptOcclusion")) for r in results),
      "acceptance":"NOT_ACCEPTED" if blocked_cases or failures else "SCOPED_BROWSER_PROOF",
      "failed":len(failures),"javascript_errors":page_errors,
      "limits":[
        "Synthetic fully matured primary-tier cases; no engine/model/collector execution.",
        "No acceptance of held #7073 rounding or partial-maturity changes.",
        "Keyboard proof is local Tab focus opening and Escape dismissal, not all keyboard semantics.",
        "Mobile first-tap failure is retained; fallback keyboard opening qualifies content only.",
        "Mobile proof is browser touch emulation, not a physical device.",
        "Track-specific N=11/W card identifies whole market in the receipt; rich-only prose is not required.",
        "No live data freshness, authentication, production navigation, deployment or user acceptance claim."
      ]}
    (out/"browser-proof.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"phase":"complete","total":len(results),"passed":report["passed"],
      "content_passed":report["content_passed"],"blocked":report["blocked"],
      "first_tap_failures":report["first_tap_failures"],"receipt_occlusions":report["receipt_occlusions"],
      "failed":report["failed"],"source_unchanged":source_unchanged,
      "missing":sorted(missing),"external":sorted(blocked),"output":str(out/"browser-proof.json")}),flush=True)
    return 1 if failures or blocked_cases or not source_unchanged or missing or page_errors else 0

if __name__=="__main__":
    raise SystemExit(main())
