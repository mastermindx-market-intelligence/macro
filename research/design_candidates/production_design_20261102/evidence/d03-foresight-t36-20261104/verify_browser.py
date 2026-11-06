"""D03 T36: real-template Chromium proof with explicitly synthetic source rows.

No builder, live data, server, repository site/ writes or deployment. Every
request is intercepted; template assets are served and unrelated JSON is stubbed.
The existing T35 fixture verifier supplied the browser/asset-serving pattern.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

MEASURE = r"""() => {
  const canvas=document.createElement('canvas'); canvas.width=canvas.height=1;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  const rgba=c=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=c;ctx.fillRect(0,0,1,1);
    return [...ctx.getImageData(0,0,1,1).data].map((v,i)=>i===3?v/255:v);};
  const blend=(fg,bg)=>fg.slice(0,3).map((v,i)=>v*fg[3]+bg[i]*(1-fg[3]));
  const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;})
    .reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const selectors=['.fx-verdict','.fx-tag','.fx-heat-meta','.fx-heat-badge',
    '.fx-card .fx-badge','.fx-stance-line.fx-unconfirmed','.fx-filing-depth',
    '.fx-heat .fx-prov'];
  const text=selectors.flatMap(selector=>[...document.querySelectorAll(selector)].map(el=>{
    const rect=el.getBoundingClientRect(),style=getComputedStyle(el);
    const chain=[]; for(let p=el;p;p=p.parentElement)chain.unshift(p);
    let bg=[255,255,255];for(const p of chain)bg=blend(rgba(getComputedStyle(p).backgroundColor),bg);
    const fg=blend(rgba(style.color),bg), a=lum(fg),b=lum(bg);
    return {selector,text:el.innerText,fontSize:parseFloat(style.fontSize),
      contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),x:rect.x,right:rect.right,
      width:rect.width,height:rect.height,overflow:el.scrollWidth>el.clientWidth+1};
  }).filter(x=>x.width>0&&x.height>0));
  return {viewport:innerWidth,pageScrollWidth:document.documentElement.scrollWidth,
    theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,text};
}"""

TOOLTIP = r"""el=>{
  const r=el.getBoundingClientRect();
  const clipped=[];
  for(let p=el.parentElement;p;p=p.parentElement){
    const s=getComputedStyle(p),b=p.getBoundingClientRect();
    if(/hidden|clip/.test(s.overflowX)&& (r.x<b.x-1||r.right>b.right+1))clipped.push(p.className);
    if(/hidden|clip/.test(s.overflowY)&& (r.y<b.y-1||r.bottom>b.bottom+1))clipped.push(p.className);
  }
  return {x:r.x,right:r.right,width:r.width,height:r.height,viewport:innerWidth,
    display:getComputedStyle(el).display,clipped};
}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    assert out.is_dir() and not list(out.iterdir()), "use a new empty proof directory"
    print(json.dumps({"phase": "start", "out": str(out)}), flush=True)
    spec = importlib.util.spec_from_file_location(
        "t36_fixture", root / "tests/test_foresight_page_fingerprint_depth.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    track = {"foresight": 12, "bottleneck": 2, "glut": 0, "revisions": 5,
             "guidance": 1, "emergence": 0, "subsector": 0,
             "recent": [{"theme": "medical_devices", "asof": "2026-08-01",
                         "stage": "PRECIPICE (fingerprint)",
                         "bottleneck_band": "TIGHTENING (fingerprint)",
                         "members": ["AAA", "BBB"]}]}
    grade = {"n_graded": 4, "pooled_hit_rate": 0.75, "pooled_n_directional": 4,
             "pooled_ci95": [0.3, 0.95], "n_significant_fdr": 0,
             "by_stage": {"PRECIPICE": {"n": 4, "n_dir": 4, "hit_rate": 0.75,
                                      "hits": 3, "avg_excess_pct": 2.5}}}
    states = {"limited-hot": ("CONFIRMER-ONLY", True),
              "limited-empty": ("CONFIRMER-ONLY", False),
              "full-hot": ("FULL", True)}
    pages = {}
    for name, (mode, hot) in states.items():
        pages[name] = fixture._render(
            [fixture._row(fingerprint=fixture.FP_GLP1)],
            convergence=fixture._t36_convergence(hot=hot, physical_confirmed=True),
            health={"mode": mode, "legs": {
                "t1_fred": {"status": "LIVE" if mode == "FULL" else "DARK",
                            "why": "synthetic source-health fixture", "detail": None}}},
            track=track, grade=grade,
            dislocation={"active": False, "verdict": "neutral",
                         "headline": "Synthetic known closed source read."},
        )
    templates = root / "templates"
    requests_stubbed, errors, results, journeys = set(), [], [], []

    def route_request(route):
        parsed = urlparse(route.request.url)
        path = unquote(parsed.path).removeprefix("/case/")
        if parsed.hostname != "127.0.0.1":
            requests_stubbed.add("external:" + str(parsed.hostname) + parsed.path)
            route.abort()
            return
        if path.endswith(".html") and path[:-5] in pages:
            route.fulfill(status=200, content_type="text/html; charset=utf-8",
                          body=pages[path[:-5]])
            return
        asset = (templates / path.lstrip("/")).resolve()
        if (asset.is_relative_to(templates) and asset.is_file()
                and asset.suffix in {".css", ".js", ".woff2", ".svg", ".png"}):
            route.fulfill(status=200, content_type=mimetypes.guess_type(asset)[0]
                          or "application/octet-stream", body=asset.read_bytes())
            return
        requests_stubbed.add(parsed.path)
        route.fulfill(status=200, content_type="application/json", body="{}")

    source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [templates / "foresight.html.j2",
                               templates / "theme.css", templates / "theme.js",
                               root / "tests/test_foresight_page_fingerprint_depth.py"]}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        version = browser.version
        for width in (320, 390, 1440):
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    context = browser.new_context(
                        viewport={"width": width, "height": 900}, device_scale_factor=1)
                    context.add_init_script(
                        f"localStorage.setItem('theme',{json.dumps(theme)});"
                        f"localStorage.setItem('lang',{json.dumps(lang)});")
                    context.route("**/*", route_request)
                    page = context.new_page()
                    page.set_default_timeout(5000)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for name, (mode, hot) in states.items():
                        label = f"{name}-{width}-{theme}-{lang}"
                        try:
                            page.goto(f"http://127.0.0.1/case/{name}.html", wait_until="load")
                            page.evaluate("document.fonts.ready")
                            target = page.locator(".fx-heat-grid" if hot else ".fx-empty").first
                            target.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
                            target.screenshot(path=str(out / f"{label}.png"), animations="disabled")
                            measured = page.evaluate(MEASURE)
                            assert measured["theme"] == theme and measured["lang"] == lang
                            assert measured["pageScrollWidth"] <= width + 1, (label, measured)
                            for item in measured["text"]:
                                assert not item["overflow"], (label, item)
                                assert item["x"] >= -1 and item["right"] <= width + 1, (label, item)
                                assert item["contrast"] >= 4.5, (label, item)
                                assert item["fontSize"] >= 12, (label, item)
                            hero = page.locator(".fx-verdict").inner_text()
                            badge = page.locator(".fx-card .fx-badge").inner_text()
                            depth = page.locator(".fx-filing-depth").inner_text()
                            assert "FY2022" in depth and "FY2025" in depth
                            assert ("too few members" if lang == "en" else "成员过少") in depth
                            assert "0.33" not in depth and "None" not in depth
                            assert page.locator(".fx-card").count() == 1
                            if mode == "CONFIRMER-ONLY":
                                assert ("Early status is unconfirmed" if lang == "en"
                                        else "早期状态尚未确认") in hero
                                assert ("Supply unconfirmed" if lang == "en"
                                        else "供给待确认").lower() in badge.lower()
                                if hot:
                                    meta = page.locator(".fx-heat-meta").inner_text()
                                    assert ("still early" if lang == "en" else "仍属早期") not in meta
                                    assert ("Supply read unconfirmed" if lang == "en"
                                            else "供给读数待确认") in meta
                            else:
                                assert ("sit early in the cycle right now" if lang == "en"
                                        else "处于周期早段") in hero
                                assert ("still early" if lang == "en"
                                        else "仍属早期") in page.locator(".fx-heat-meta").inner_text()
                            if name == "limited-hot" and (width, theme, lang) in {
                                (320, "dark", "zh"), (390, "light", "en"),
                                (1440, "dark", "zh"), (1440, "light", "en")}:
                                page.screenshot(path=str(out / f"page-{label}.png"),
                                                full_page=True, animations="disabled")
                            if hot:
                                mark = page.locator(".fx-heat .fx-prov").first
                                mark.focus()
                                tip = mark.locator(".fxq-tip")
                                assert tip.is_visible()
                                geometry = tip.evaluate(TOOLTIP)
                                assert not geometry["clipped"], (label, geometry)
                                assert geometry["x"] >= -1 and geometry["right"] <= width + 1, (label, geometry)
                                assert ("provisional" if lang == "en" else "暂定") in tip.inner_text()
                                mark.evaluate("el=>el.blur()")
                                page.mouse.move(0, 0)
                                assert not tip.is_visible()
                            page.emulate_media(reduced_motion="reduce")
                            for el in page.locator(".fx-card,.fx-heat").all():
                                assert el.evaluate("e=>getComputedStyle(e).animationName") == "none"
                                assert el.evaluate("e=>getComputedStyle(e,'::before').content") == "none"
                            page.emulate_media(reduced_motion="no-preference")
                            results.append({"case": name, "viewport": width, "theme": theme,
                                            "lang": lang, "screenshot": f"{label}.png", **measured})
                        except Exception as exc:
                            page.screenshot(path=str(out / f"failure-{label}.png"),
                                            full_page=True, animations="disabled")
                            (out / "failure.json").write_text(json.dumps({
                                "case": label, "error": str(exc), "source_hashes": source_hashes,
                                "completed": results, "page_errors": errors}, ensure_ascii=False, indent=2))
                            raise
                    # Keyboard disclosure opens the existing historical record.
                    record = page.locator("details").filter(has_text="Track record — graded forward vs SPY")
                    record.locator("summary").focus()
                    page.keyboard.press("Enter")
                    assert record.evaluate("e=>e.open")
                    history = record.inner_text()
                    assert "2026-08-01" in history and "AAA" in history and "BBB" in history
                    assert ("Early" if lang == "en" else "早期") in history
                    page.keyboard.press("Enter")
                    assert not record.evaluate("e=>e.open")
                    if width in (390, 1440) and theme == "light" and lang == "en":
                        # The existing theme.js focusin handler opens settings.
                        # Enter on the gear would toggle that already-open pane closed.
                        # Keep the pointer outside and use real keyboard control events.
                        page.mouse.move(0, 0)
                        page.locator("#settings-open").focus()
                        page.wait_for_function("document.querySelector('#settings-open').getAttribute('aria-expanded')==='true'")
                        page.locator("#set-theme-dark").wait_for(state="visible")
                        page.locator("#set-theme-dark").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.theme==='dark'")
                        page.locator(".lang-toggle").wait_for(state="visible")
                        page.locator(".lang-toggle").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.lang==='zh'")
                        assert "仍属早期" in page.locator(".fx-heat-meta").inner_text()
                        page.locator("#set-theme-light").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.theme==='light'")
                        page.locator(".lang-toggle").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.lang==='en'")
                        page.keyboard.press("Escape")
                        page.wait_for_function("document.querySelector('#settings-open').getAttribute('aria-expanded')==='false'")
                        journeys.append({"viewport": width, "settings_theme_locale_keyboard_escape": "PASS"})
                    context.close()
                    print(json.dumps({"phase": "context-complete", "width": width,
                                      "theme": theme, "lang": lang, "cases": len(results)}), flush=True)
        browser.close()
    report = {"fixture_only": True, "browser": f"Chromium {version}",
              "case_count": len(results), "source_hashes": source_hashes,
              "new_provisional_help_focus_and_bounds": "PASS",
              "historical_disclosure_keyboard": "PASS",
              "settings_journeys": journeys, "reduced_motion": "PASS",
              "unrelated_requests_stubbed": sorted(requests_stubbed),
              "page_errors": sorted(set(errors)), "results": results}
    (out / "browser-proof.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    assert not errors, errors
    print(json.dumps({"phase": "complete", "out": str(out), "case_count": len(results),
                      "min_contrast": min(t["contrast"] for r in results for t in r["text"]),
                      "page_overflow_cases": sum(r["pageScrollWidth"] > r["viewport"]+1 for r in results),
                      "page_errors": sorted(set(errors))}), flush=True)


if __name__ == "__main__":
    main()
