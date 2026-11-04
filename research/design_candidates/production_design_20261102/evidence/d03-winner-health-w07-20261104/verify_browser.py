"""W07 actual Winner Health build()/write_page browser proof, not live acceptance.

Only temporary synthetic inputs/outputs are written. The normal live-artifact
path is used; --fixture never bypasses freshness. Every browser HTTP request is
intercepted, and all successful asset responses use the candidate's own bytes.
No server, producer, ledger, production URL, auth mutation or deployment is used.

Requires the repository's existing test dependencies and Playwright/Chromium.
Run with --repo CANDIDATE_WORKTREE --out NEW_EMPTY_DIRECTORY_OUTSIDE_WORKTREE.
The runner itself makes no claim until a completed browser-proof.json says PASS.
"""
from __future__ import annotations

import argparse
import copy
import datetime
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import mimetypes
from pathlib import Path
import subprocess
import sys
import traceback
from unittest.mock import patch
from urllib.parse import unquote, urlparse

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright


BASE = "f9e62dfbecfcf33579ead45ad27cf7a38de734a7"
TODAY = datetime.date(2026, 11, 4)
RAW_REASON = "W07_RAW_REASON_MUST_NOT_RENDER /private/synthetic-store <script>W07_LEAK</script>"
TITLE = {
    "missing": {"en": "No read is available", "zh": "暂无可用判读"},
    "unreadable": {"en": "Latest read could not be loaded", "zh": "无法载入最新判读"},
    "invalid_artifact": {"en": "Latest read is not usable", "zh": "最新判读无法使用"},
    "invalid_date": {"en": "Read date is unavailable", "zh": "判读日期不可用"},
    "stale": {"en": "Latest read is out of date", "zh": "最新判读已过期"},
    "producer_unavailable": {"en": "Latest read did not complete", "zh": "最新判读未完成"},
    "unavailable": {"en": "Read unavailable", "zh": "判读不可用"},
}
ASSET_SUFFIXES = {".css", ".js", ".mjs", ".woff2", ".woff", ".ttf", ".svg",
                  ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"}
CRITICAL_TYPES = {"stylesheet", "script", "font", "image"}


class FixtureDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 4)


# Contrast includes translucent ancestor backgrounds and the actual computed
# gradient stops. Sampling the computed backgroundColor alone is incorrect for
# the incumbent .nullhero, whose background is a gradient over the page canvas.
MEASURE = r"""el => {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
  const cx=canvas.getContext('2d',{willReadFrequently:true});
  function rgba(color){
    if(!CSS.supports('color',color))throw Error('Unparsed background color: '+color);
    cx.clearRect(0,0,1,1);cx.fillStyle=color;cx.fillRect(0,0,1,1);
    const p=[...cx.getImageData(0,0,1,1).data];return [p[0],p[1],p[2],p[3]/255];
  }
  function over(f,b){const a=f[3]+b[3]*(1-f[3]);return a?
    [0,1,2].map(i=>(f[i]*f[3]+b[i]*b[3]*(1-f[3]))/a).concat(a):[0,0,0,0];}
  function splitTop(s){let d=0,start=0,out=[];for(let i=0;i<s.length;i++){
    if(s[i]==='(')d++;else if(s[i]===')')d--;else if(s[i]===','&&!d){out.push(s.slice(start,i));start=i+1;}}
    out.push(s.slice(start));return out;}
  function stopColor(s){s=s.trim();let m=s.match(/^#[0-9a-f]+|^[a-z]+/i);if(!m)return null;
    let token=m[0];if(s[token.length]==='('){let d=0;for(let i=token.length;i<s.length;i++){
      if(s[i]==='(')d++;if(s[i]===')'&&!--d){token=s.slice(0,i+1);break;}}}
    return CSS.supports('color',token)?rgba(token):null;}
  function backgrounds(node){
    const chain=[];for(let n=node;n;n=n.parentElement)chain.unshift(n);
    let colors=[[255,255,255,1]];const images=[];
    for(const n of chain){const s=getComputedStyle(n);colors=colors.map(b=>over(rgba(s.backgroundColor),b));
      if(s.backgroundImage==='none')continue;
      const layers=splitTop(s.backgroundImage).reverse();
      for(const layer of layers){
        if(!/^(linear|radial)-gradient\(/.test(layer.trim()))throw Error('Unsupported painted background: '+layer);
        const stops=splitTop(layer.slice(layer.indexOf('(')+1,-1)).map(stopColor).filter(Boolean);
        if(stops.length<2)throw Error('Gradient has no measurable stops: '+layer);
        const samples=[];for(let j=1;j<stops.length;j++)for(let k=0;k<=20;k++){
          const t=k/20;samples.push(stops[j-1].map((v,i)=>v*(1-t)+stops[j][i]*t));}
        colors=colors.flatMap(b=>samples.map(f=>over(f,b)));images.push(layer);
      }
    }
    return {colors,images};
  }
  function lum(c){return c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;})
    .reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);}
  const panel=el.getBoundingClientRect(),texts=[],walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const n=walker.currentNode,e=n.parentElement;if(!n.textContent.trim()||!e)continue;
    const s=getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden')continue;
    const range=document.createRange();range.selectNodeContents(n);
    const rects=[...range.getClientRects()].filter(r=>r.width&&r.height);if(!rects.length)continue;
    const fg=rgba(s.color),bg=backgrounds(e),ratios=bg.colors.map(b=>{
      const f=lum(over(fg,b)),v=lum(b);return (Math.max(f,v)+.05)/(Math.min(f,v)+.05);});
    const size=parseFloat(s.fontSize),weight=parseFloat(s.fontWeight)||400;
    texts.push({text:n.textContent.trim(),color:s.color,font_size:size,font_weight:weight,
      contrast:Math.min(...ratios),required_contrast:size>=24||(size>=18.66&&weight>=700)?3:4.5,
      background_images:[...new Set(bg.images)],
      rects:rects.map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom})),
      horizontal_clipping:rects.some(r=>r.left<panel.left-1||r.right>panel.right+1)});
  }
  return {left:panel.left,right:panel.right,width:panel.width,height:panel.height,
    viewport:innerWidth,page_scroll_width:document.documentElement.scrollWidth,
    scroll_width:el.scrollWidth,client_width:el.clientWidth,texts};
}"""

MOTION = """() => [...document.querySelectorAll('.wrap .rise,.wrap .row,.wrap .sh-row,.wrap .rung')]
  .flatMap(e=>[null,'::before','::after'].map(p=>{const s=getComputedStyle(e,p);return {
    selector:e.className,pseudo:p,animation:s.animationName,animation_duration:s.animationDuration,
    transition_duration:s.transitionDuration};}))"""


def seconds(value):
    return [float(v.strip()[:-2]) / 1000 if v.strip().endswith("ms")
            else float(v.strip().removesuffix("s")) for v in value.split(",")]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def payloads(fixture):
    empty = fixture._ctx(schema="winner_health.v2", asof=TODAY.isoformat(),
                         data_last_day="2026-11-04", tape_lag_sessions=0,
                         tiers=[fixture._v2_tier(k) for k in ("primary", "r63", "atrz")],
                         theme_counts=[], macro_backdrop={})
    full = fixture._row("FULL", legs=[], analog="full")
    full["state"] = "extended_healthy"
    full["analog"].update(n=12, topped_63td=4)
    thin = fixture._row("THIN", analog="thin")
    thin["analog"].update(n=11, topped_63td=4)
    no_match = fixture._row("NONE", analog=None)
    no_match["state"] = "thinning"
    unread = fixture._row("UNREAD", analog=None, legs=[])
    unread.update(state="no_read", checks={"total": 7, "evaluated": 2})
    populated = copy.deepcopy(empty)
    populated["tiers"] = [
        fixture._v2_tier("primary", {"extended_healthy": [full], "extended_watch": [thin],
                                    "thinning": [no_match], "no_read": [unread]}),
        fixture._v2_tier("r63", {"extended_watch": [dict(copy.deepcopy(full), r63=.41)]}),
        fixture._v2_tier("atrz", readable=False),
    ]
    producer_null = copy.deepcopy(populated)
    producer_null.update(null_state=True, null_reason=RAW_REASON,
                         macro_backdrop={"froth_quadrant": "visible_stress", "stage3_count": 12345})
    bad_date = copy.deepcopy(empty)
    bad_date["asof"] = "2026-02-30"
    stale = copy.deepcopy(populated)
    stale.update(asof="2026-10-28", data_last_day="2026-10-28", tape_lag_sessions=0)
    lag5 = copy.deepcopy(populated)
    lag5.update(tape_lag_sessions=5, data_last_day="2026-10-28")
    lag6 = copy.deepcopy(populated)
    lag6.update(tape_lag_sessions=6, data_last_day="2026-10-27")
    age6_lag6 = copy.deepcopy(populated)
    age6_lag6.update(asof="2026-10-29", tape_lag_sessions=6, data_last_day="2026-10-21")
    return {
        "missing": {"status": "missing", "input": "missing"},
        "unreadable": {"status": "unreadable", "input": "directory"},
        "invalid-json": {"status": "invalid_artifact", "input": "invalid-json"},
        "nonobject": {"status": "invalid_artifact", "payload": ["not", "an", "object"]},
        "invalid-date": {"status": "invalid_date", "payload": bad_date},
        "stale": {"status": "stale", "payload": stale, "source_asof": "2026-10-28"},
        "producer-null": {"status": "producer_unavailable", "payload": producer_null},
        "empty": {"status": "available", "payload": empty, "rows": 0, "lag": 0},
        "populated": {"status": "available", "payload": populated, "rows": 5, "lag": 0},
        "lag-five": {"status": "available", "payload": lag5, "rows": 5, "lag": 5},
        "lag-six": {"status": "available", "payload": lag6, "rows": 5, "lag": 6},
        "age-six-lag-six": {"status": "available", "payload": age6_lag6, "rows": 5, "lag": 6},
    }


def input_signature(path):
    if not path.exists():
        return {"kind": "missing"}
    if path.is_dir():
        return {"kind": "directory", "entries": sorted(p.name for p in path.iterdir())}
    return {"kind": "file", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    assert root.is_dir() and (root / "scripts/build_winner_health_page.py").is_file()
    assert not out.is_relative_to(root), "Keep synthetic proof outputs outside the candidate worktree"
    out.mkdir(parents=True, exist_ok=True)
    assert not list(out.iterdir()), "Use a new empty evidence directory"
    sys.path.insert(0, str(root))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    hashes, source_bytes, provenance = {}, {}, {}

    def read_source(relative, *, git_fallback=False):
        if relative in source_bytes:
            return source_bytes[relative]
        path = (root / relative).resolve()
        assert path.is_relative_to(root), relative
        if path.is_file():
            data, origin = path.read_bytes(), "worktree"
        elif git_fallback:
            data = subprocess.check_output(["git", "show", f"{head}:{relative}"], cwd=root)
            origin = f"git:{head}"
        else:
            raise FileNotFoundError(path)
        source_bytes[relative] = data
        hashes[relative] = hashlib.sha256(data).hexdigest()
        provenance[relative] = origin
        return data

    required = ["scripts/build_winner_health_page.py", "templates/winner_health.html.j2",
                "tests/test_winner_health_page.py", "tests/test_winner_health_source_dates.py",
                "templates/_lens.html.j2", "templates/_site_nav.html.j2",
                "templates/_navlinks.html.j2", "templates/_seo_head.html.j2",
                "templates/theme.css", "templates/theme.js", "templates/data_base.js",
                "templates/shared_shell.css", "templates/shared_shell_bridge.js",
                "lib/pages.py", "lib/shared_shell.py", "lib/config.py", "engine/i18n.py"]
    for relative in required:
        read_source(relative)
    live_config = read_source("site/live_config.js", git_fallback=True)
    # No mutation of site/start.html is needed to prove the first retained link
    # has a real candidate-tree referent. Navigation to that separate page is
    # deliberately not included in W07 acceptance.
    start_html = read_source("site/start.html", git_fallback=True)
    assert b"<html" in start_html.lower() or b"<!doctype" in start_html.lower()
    from lib import config, pages
    from scripts import build_winner_health_page as bwh
    fixture = load_module("d03_w07_retained_fixture", root / "tests/test_winner_health_page.py")
    cases = payloads(fixture)
    build_evidence = {}
    for name, case in cases.items():
        case_root = out / "fixtures" / name
        site, data = case_root / "site", case_root / "data"
        artifact = data / "top_maturation" / "latest.json"
        site.mkdir(parents=True)
        artifact.parent.mkdir(parents=True)
        (case_root / "templates").symlink_to(root / "templates", target_is_directory=True)
        for asset in ("theme.css", "theme.js", "data_base.js"):
            (site / asset).write_bytes(read_source("templates/" + asset))
        (site / "live_config.js").write_bytes(live_config)
        if case.get("input") == "directory":
            artifact.mkdir()  # Real read_text() failure, including under a root user.
        elif case.get("input") == "invalid-json":
            artifact.write_text("{", encoding="utf-8")
        elif "payload" in case:
            artifact.write_text(json.dumps(case["payload"], ensure_ascii=False), encoding="utf-8")
        before = input_signature(artifact)
        output = site / "winner_health.html"
        output.write_text("PREVIOUS_BOARD_MUST_NOT_SURVIVE", encoding="utf-8")
        with ExitStack() as stack:
            stack.enter_context(patch.object(config, "ROOT", case_root))
            stack.enter_context(patch.object(bwh, "_data_dir", lambda _root, d=data: d))
            stack.enter_context(patch("datetime.date", FixtureDate))
            if hasattr(bwh, "date"):
                stack.enter_context(patch.object(bwh, "date", FixtureDate))
            assert pages._site_root() == site.resolve(), "write_page assets must stay inside the isolated fixture"
            assert not bwh._is_stale({"asof": "2026-10-29"})
            assert bwh._is_stale({"asof": "2026-10-28"})
            result = bwh.build(case_root)  # NORMAL live path; never fixture=.
        assert result == output and output.is_file(), (name, result)
        html = output.read_text(encoding="utf-8")
        assert "PREVIOUS_BOARD_MUST_NOT_SURVIVE" not in html
        assert "W07_RAW_REASON_MUST_NOT_RENDER" not in html and "W07_LEAK" not in html
        assert "/private/synthetic-store" not in html
        assert input_signature(artifact) == before, (name, "input was mutated")
        if case["status"] == "invalid_date":
            assert "2026-02-30" not in html
        case["site"], case["artifact"], case["input_before"] = site, artifact, before
        build_evidence[name] = {"expected_state": case["status"], "input": before,
                                "html_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                                "previous_board_replaced": True, "normal_live_path": True}
    print(json.dumps({"phase": "actual_build_fixtures_ready", "cases": len(cases), "out": str(out)}), flush=True)

    blocked, served, results = [], set(), []

    def route_request(route):
        request, parsed = route.request, urlparse(route.request.url)
        relative = unquote(parsed.path).lstrip("/")
        parts = relative.split("/", 2)
        if parsed.hostname == "127.0.0.1":
            if len(parts) == 3 and parts[0] == "case" and parts[1] in cases:
                site = cases[parts[1]]["site"]
                relative = parts[2]
                candidate = (site / relative).resolve()
                if candidate.is_relative_to(site) and candidate.is_file():
                    served.add("generated:" + parts[1] + "/" + relative)
                    route.fulfill(status=200, content_type=mimetypes.guess_type(candidate)[0] or "application/octet-stream",
                                  body=candidate.read_bytes())
                    return
            if Path(relative).suffix.lower() in ASSET_SUFFIXES:
                for prefix in ("templates", "site"):
                    path = (root / prefix / relative).resolve()
                    if path.is_relative_to(root / prefix) and path.is_file():
                        key = str(path.relative_to(root))
                        served.add(key)
                        route.fulfill(status=200, content_type=mimetypes.guess_type(path)[0] or "application/octet-stream",
                                      body=read_source(key))
                        return
        blocked.append({"url": request.url, "resource_type": request.resource_type})
        route.abort()

    version, current_cell = None, None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            version = browser.version
            try:
                for width in (320, 390, 1440):
                    for theme in ("light", "dark"):
                        for lang in ("en", "zh"):
                            context = browser.new_context(viewport={"width": width, "height": 900},
                                device_scale_factor=1, has_touch=width <= 390,
                                reduced_motion="no-preference", service_workers="block")
                            context.add_init_script(
                                f"localStorage.setItem('theme',{json.dumps(theme)});"
                                f"localStorage.setItem('lang',{json.dumps(lang)});")
                            context.route("**/*", route_request)
                            page = context.new_page()
                            page.set_default_timeout(7000)
                            errors, failures, bad_responses = [], [], []
                            page.on("pageerror", lambda e: errors.append(str(e)))
                            page.on("requestfailed", lambda r: failures.append({"url": r.url, "type": r.resource_type}))
                            page.on("response", lambda r: bad_responses.append({"url": r.url, "status": r.status,
                                "type": r.request.resource_type}) if r.status >= 400 else None)
                            for name, case in cases.items():
                                current_cell = {"case": name, "width": width, "theme": theme, "language": lang}
                                errors.clear(); failures.clear(); bad_responses.clear()
                                page.emulate_media(reduced_motion="no-preference")
                                original_url = f"http://127.0.0.1/case/{name}/winner_health.html"
                                page.goto(original_url, wait_until="load")
                                page.evaluate("document.fonts.ready")
                                font_proof = page.evaluate("""async()=>{
                                    const faces=await document.fonts.load('700 14px Inter');
                                    return {faces:faces.map(f=>({family:f.family,status:f.status})),
                                    body:getComputedStyle(document.body).fontFamily,
                                    errors:[...document.fonts].filter(f=>f.status==='error').map(f=>f.family)};}""")
                                assert font_proof["faces"] and all(f["status"] == "loaded" for f in font_proof["faces"]), font_proof
                                assert not font_proof["errors"], font_proof
                                actual = page.evaluate("""({theme:document.documentElement.dataset.theme,
                                    lang:document.documentElement.dataset.lang,
                                    panel:getComputedStyle(document.documentElement).getPropertyValue('--panel').trim(),
                                    runtime:document.documentElement.classList.contains('soft-contrast')})""")
                                assert actual["theme"] == theme and actual["lang"] == lang and actual["runtime"], actual
                                assert actual["panel"] == ("#ffffff" if theme == "light" else "#151820"), actual
                                normal_motion = page.locator(".pghead.rise").evaluate("e=>({name:getComputedStyle(e).animationName,duration:getComputedStyle(e).animationDuration})")
                                assert normal_motion["name"] == "rise" and max(seconds(normal_motion["duration"])) > 0
                                page.emulate_media(reduced_motion="reduce")
                                assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
                                reduced_motion = page.evaluate(MOTION)
                                assert reduced_motion and all(m["animation"] == "none" and max(seconds(m["transition_duration"])) == 0 for m in reduced_motion), reduced_motion
                                null = page.locator("section.nullhero")
                                expected = case["status"]
                                source_date = None
                                if expected != "available":
                                    assert null.count() == 1 and null.is_visible()
                                    assert null.get_attribute("data-wh-availability") == expected
                                    title = null.locator("#wh-source-title")
                                    assert title.count() == 1 and title.inner_text().strip() == TITLE[expected][lang]
                                    assert title.locator(".l-" + lang).is_visible()
                                    assert not title.locator(".l-" + ("zh" if lang == "en" else "en")).is_visible()
                                    assert page.locator(".wrap .row, .wrap .tier, .wrap .lag").count() == 0
                                    assert "12345" not in page.locator(".wrap").inner_text()
                                    clocks = null.locator(".source-asof")
                                    assert clocks.count() == (1 if expected == "stale" else 0)
                                    if clocks.count():
                                        assert expected == "stale" and clocks.count() == 1
                                        source_date = clocks.inner_text().strip()
                                        assert case["source_asof"] in source_date
                                        assert ("Last source read" if lang == "en" else "上次来源判读") in source_date
                                    if expected == "stale" and lang == "en":
                                        assert "This read is older than the six-calendar-day limit. No current reading is shown." in null.inner_text()
                                    assert "nothing is being withheld" not in null.inner_text().lower()
                                    assert "as soon as the nightly read finishes" not in null.inner_text().lower()
                                    panel = null
                                else:
                                    assert null.count() == 0
                                    assert page.locator(".wrap .tier").count() == 3
                                    assert page.locator(".wrap .row").count() == case["rows"]
                                    assert page.locator(".wrap .lag").count() == (1 if case["lag"] > 5 else 0)
                                    if case["lag"] > 5:
                                        assert "6" in page.locator(".wrap .lag").inner_text()
                                    if case["rows"]:
                                        assert page.locator('.row .tk[href="/stocks/FULL.html"]').count() == 2
                                        unread = page.locator(".row").filter(has=page.locator('.tk[href="/stocks/UNREAD.html"]'))
                                        assert unread.count() == 1 and unread.locator(".wear").count() == 0
                                        assert ("no similar runs to compare" if lang == "en" else "没有可比的历史行情") in unread.inner_text()
                                        no_match = page.locator(".row").filter(has=page.locator('.tk[href="/stocks/NONE.html"]'))
                                        assert no_match.locator(".lib-null").inner_text().strip() == ("no match" if lang == "en" else "无相似样本")
                                        thin = page.locator(".row").filter(has=page.locator('.tk[href="/stocks/THIN.html"]'))
                                        assert "too few to read as a pattern" in thin.text_content()
                                        assert "dropped 20% or more" not in thin.text_content()
                                    panel = page.locator(".pghead")
                                panel.scroll_into_view_if_needed()
                                measured = panel.evaluate(MEASURE)
                                assert measured["left"] >= -1 and measured["right"] <= width + 1, measured
                                assert measured["page_scroll_width"] <= width + 1, measured
                                assert measured["scroll_width"] <= measured["client_width"] + 1, measured
                                assert measured["texts"], measured
                                for text in measured["texts"]:
                                    assert not text["horizontal_clipping"], text
                                    assert text["contrast"] >= text["required_contrast"], text
                                screenshot = f"{name}-{width}-{theme}-{lang}.png"
                                panel.screenshot(path=str(out / screenshot), animations="disabled")
                                if (width, theme, lang, name) in {
                                    (320, "dark", "zh", "stale"), (390, "light", "en", "producer-null"),
                                    (1440, "dark", "en", "populated"), (390, "dark", "zh", "empty")
                                }:
                                    page.screenshot(path=str(out / ("page-" + screenshot)), full_page=True, animations="disabled")
                                # Real Tab events must reach a retained header link.
                                # The collapsed mobile header hides Home and exposes
                                # Terminal first. Neither destination is loaded here.
                                keyboard = None
                                for tab_count in range(1, 41):
                                    page.keyboard.press("Tab")
                                    focused = page.evaluate("""()=>{const e=document.activeElement,s=getComputedStyle(e),b=e.getBoundingClientRect();
                                        return {tag:e.tagName,href:e.getAttribute('href'),label:e.getAttribute('aria-label')||e.innerText,
                                        visible:!!e.getClientRects().length,left:b.left,right:b.right,top:b.top,bottom:b.bottom,
                                        outline:s.outlineStyle,outline_width:s.outlineWidth,shadow:s.boxShadow};}""")
                                    if focused["tag"] == "A" and focused["href"]:
                                        keyboard = {"tabs": tab_count, **focused}
                                        break
                                assert keyboard and keyboard["visible"], keyboard
                                assert keyboard["href"] in ("start.html", "https://app.mastermind-x.com"), keyboard
                                assert keyboard["left"] >= -1 and keyboard["right"] <= width + 1, keyboard
                                assert (keyboard["outline"] != "none" and float(keyboard["outline_width"].removesuffix("px")) > 0) or keyboard["shadow"] != "none", keyboard
                                keyboard["link_source_verified"] = (
                                    "site/start.html" if keyboard["href"] == "start.html"
                                    else "templates/_site_nav.html.j2"
                                )
                                keyboard["destination_page_loaded"] = False
                                # The available board's retained local jump is exercised
                                # by native Enter against its actual existing DOM target.
                                jump = None
                                if expected == "available":
                                    link = page.locator('.wrap a.sh-row[href^="#"]').first
                                    assert link.count() == 1
                                    href = link.get_attribute("href")
                                    target = page.locator(href)
                                    assert target.count() == 1 and target.is_visible()
                                    link.focus()
                                    page.keyboard.press("Enter")
                                    page.wait_for_url(original_url + href)
                                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                                    jump = {"href": href, "native_enter": True, "url": page.url,
                                            "destination_visible": target.is_visible()}
                                assert "W07_RAW_REASON_MUST_NOT_RENDER" not in page.content()
                                asset_errors = [r for r in failures + bad_responses if r["type"] in CRITICAL_TYPES]
                                assert not errors and not asset_errors, {"page_errors": errors, "asset_errors": asset_errors}
                                results.append({**current_cell, "status": expected, "screenshot": screenshot,
                                    "actual_theme_locale": actual, "font_proof": font_proof,
                                    "source_asof_copy": source_date, "geometry_contrast": measured,
                                    "normal_motion": normal_motion, "reduced_motion_rule_count": len(reduced_motion),
                                    "native_keyboard": keyboard, "retained_hash_jump": jump,
                                    "page_errors": list(errors), "asset_errors": asset_errors,
                                    "failed_nonessential_requests": list(failures)})
                                print(json.dumps({"passed_cell": current_cell}), flush=True)
                            context.close()
            finally:
                browser.close()
    except BaseException:
        (out / "browser-proof-failure.json").write_text(json.dumps({
            "status": "FAIL", "cell": current_cell, "completed_case_count": len(results),
            "chromium": version, "error": traceback.format_exc(), "results": results,
            "blocked_requests": blocked, "source_sha256": hashes,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise

    expected_count = len(cases) * 3 * 2 * 2
    assert len(results) == expected_count
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == head
    for relative, digest in hashes.items():
        data = ((root / relative).read_bytes() if provenance[relative] == "worktree" else
                subprocess.check_output(["git", "show", f"{head}:{relative}"], cwd=root))
        assert hashlib.sha256(data).hexdigest() == digest, (relative, "source changed during proof")
    for name, case in cases.items():
        assert input_signature(case["artifact"]) == case["input_before"], (name, "input changed during proof")
    minimum = min(t["contrast"] for row in results for t in row["geometry_contrast"]["texts"])
    report = {"status": "PASS", "kind": "synthetic actual-builder browser proof; not deployment or live-market acceptance",
              "source_head": head, "historical_base": BASE, "fixture_calendar_day": TODAY.isoformat(),
              "chromium": version, "case_count": len(results), "build_evidence": build_evidence,
              "source_sha256": hashes, "source_provenance": provenance, "source_unchanged": True,
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "minimum_measured_text_contrast": minimum, "served_assets": sorted(served),
              "network_policy": "All HTTP requests intercepted; successful responses use candidate/generated fixture bytes only",
              "blocked_requests": blocked, "fallback_unavailable": "not synthetically forced; requires unit coverage",
              "results": results}
    (out / "browser-proof.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": "PASS", "case_count": len(results), "chromium": version,
                      "minimum_measured_text_contrast": minimum, "out": str(out)}), flush=True)


if __name__ == "__main__":
    main()
