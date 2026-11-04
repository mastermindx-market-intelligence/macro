"""D03 T37: actual-template browser proof using synthetic grading summaries.

Only the existing template/assets and test fixture helpers are loaded.
No builder, live data, server, site/data writes, auth or deployment.
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
  const text=['.fx-rchip','.fx-rchip b'].flatMap(selector=>
    [...document.querySelectorAll(selector)].map(el=>{
      const rect=el.getBoundingClientRect(),style=getComputedStyle(el);
      const chain=[]; for(let p=el;p;p=p.parentElement)chain.unshift(p);
      let bg=[255,255,255];for(const p of chain)bg=blend(rgba(getComputedStyle(p).backgroundColor),bg);
      const fg=blend(rgba(style.color),bg),a=lum(fg),b=lum(bg);
      return {selector,text:el.innerText,fontSize:parseFloat(style.fontSize),
        contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),x:rect.x,right:rect.right,
        width:rect.width,height:rect.height,overflow:el.scrollWidth>el.clientWidth+1};
    }).filter(x=>x.width>0&&x.height>0));
  return {viewport:innerWidth,pageScrollWidth:document.documentElement.scrollWidth,
    theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,text};
}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    assert out.is_dir() and not list(out.iterdir()), "use a new empty proof directory"
    spec = importlib.util.spec_from_file_location(
        "t37_fixture", root / "tests/test_foresight_page_flag_ledger.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    unknown = fixture._t37_grade()
    unknown.pop("n_pending")
    states = {
        "mixed": fixture._t37_grade(),
        "all-pending": fixture._t37_grade(
            n_total=229, n_graded=0, n_pending=229,
            pooled_hit_rate=None, pooled_n_directional=0, by_stage={}),
        "zero-pending": fixture._t37_grade(n_pending=0),
        "unavailable-pending": unknown,
        "control-only": fixture._t37_grade(
            n_total=300, n_graded=71, n_pending=229,
            pooled_hit_rate=None, pooled_n_directional=0,
            by_stage={"RE-RATING": {"n": 71, "hit_rate": None, "avg_excess_pct": 1.7}}),
    }
    pages = {name: fixture._render(fixture._track(fixture.RECENT_TWO), grade=grade)
             for name, grade in states.items()}
    templates = root / "templates"
    stubbed, errors, results = set(), [], []
    source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [templates / "foresight.html.j2", templates / "theme.css",
                               templates / "theme.js",
                               root / "tests/test_foresight_page_flag_ledger.py"]}

    def route_request(route):
        parsed = urlparse(route.request.url)
        path = unquote(parsed.path).removeprefix("/case/")
        if parsed.hostname != "127.0.0.1":
            stubbed.add("external:" + str(parsed.hostname) + parsed.path)
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
        stubbed.add(parsed.path)
        route.fulfill(status=200, content_type="application/json", body="{}")

    print(json.dumps({"phase": "start", "out": str(out)}), flush=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
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
                    for name, grade in states.items():
                        label = f"{name}-{width}-{theme}-{lang}"
                        try:
                            page.goto(f"http://127.0.0.1/case/{name}.html", wait_until="load")
                            page.evaluate("document.fonts.ready")
                            record = page.locator("details").filter(
                                has_text="Track record — graded forward vs SPY")
                            summary = record.locator("summary")
                            assert not record.evaluate("e=>e.open")
                            summary.focus()
                            page.keyboard.press("Enter")
                            assert record.evaluate("e=>e.open")
                            assert summary.evaluate("e=>e===document.activeElement")
                            summary_box = summary.bounding_box()
                            assert summary_box["height"] >= 44, (label, summary_box)
                            record.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
                            measured = page.evaluate(MEASURE)
                            assert measured["theme"] == theme and measured["lang"] == lang
                            assert measured["pageScrollWidth"] <= width + 1, (label, measured)
                            for item in measured["text"]:
                                assert not item["overflow"], (label, item)
                                assert item["x"] >= -1 and item["right"] <= width + 1, (label, item)
                                assert item["contrast"] >= 4.5, (label, item)
                                assert item["fontSize"] >= 12, (label, item)
                            chips = [" ".join(c.inner_text().split())
                                     for c in record.locator(".fx-rchip").all()]
                            pending = [c for c in chips
                                       if ("pending 90d" if lang == "en" else "待90天") in c]
                            expected = grade.get("n_pending")
                            if expected is None:
                                assert pending == [], (label, pending)
                            else:
                                assert len(pending) == 1, (label, pending)
                                assert pending[0].startswith(str(expected) + " "), (label, pending)
                            if name in ("mixed", "zero-pending", "unavailable-pending"):
                                pooled = next(c for c in chips if
                                              ("pooled 90d" if lang == "en" else "合计90天") in c)
                                assert "22% (51)" in pooled and "(122)" not in pooled
                            if name in ("mixed", "zero-pending", "unavailable-pending", "control-only"):
                                control = next(c for c in chips if
                                               ("control arm" if lang == "en" else "对照组") in c)
                                assert "(n=71)" in control and "+1.7%" in control
                                assert ("Late" if lang == "en" else "偏晚") in control
                                assert ("hit-rate" if lang == "en" else "命中率") not in control
                            history = record.locator("table").inner_text()
                            assert "2026-10-18" in history and "2026-10-17" in history
                            for member in ("LLY", "AMGN", "HIMS", "CF", "MOS", "AGCO"):
                                assert member in history
                            assert ("Early" if lang == "en" else "早期") in history
                            screenshot = None
                            if name == "mixed" or (width, theme, lang) in {
                                    (320, "light", "en"), (390, "dark", "zh")}:
                                screenshot = f"{label}.png"
                                record.screenshot(path=str(out / screenshot), animations="disabled")
                            if name == "mixed" and (width, theme, lang) in {
                                    (320, "light", "en"), (1440, "dark", "zh")}:
                                page.screenshot(path=str(out / f"page-{label}.png"),
                                                full_page=True, animations="disabled")
                            # Capture the default position before the keyboard scroll journey.
                            ledger_scroll = record.locator(".tbl-scroll")
                            scroll_geometry = ledger_scroll.evaluate(
                                "e=>({client:e.clientWidth,scroll:e.scrollWidth})")
                            if scroll_geometry["scroll"] > scroll_geometry["client"] + 1:
                                summary.focus()
                                page.keyboard.press("Tab")
                                assert ledger_scroll.evaluate("e=>e===document.activeElement"), label
                                page.keyboard.press("ArrowRight")
                                page.wait_for_function(
                                    "()=>[...document.querySelectorAll('.tbl-scroll')].some(e=>e.scrollLeft>0)")
                                assert ledger_scroll.evaluate("e=>e.scrollLeft") > 0, label
                                ledger_scroll.evaluate("e=>e.scrollTo({left:e.scrollWidth,behavior:'instant'})")
                                member = record.locator(".fx-tk").last
                                member_box = member.bounding_box()
                                scroll_box = ledger_scroll.bounding_box()
                                assert member_box["x"] >= scroll_box["x"]-1, label
                                assert member_box["x"]+member_box["width"] <= scroll_box["x"]+scroll_box["width"]+1, label
                                if name == "mixed" and width == 320:
                                    record.screenshot(path=str(out / f"members-{label}.png"),
                                                      animations="disabled")
                            page.emulate_media(reduced_motion="reduce")
                            assert all(c.evaluate("e=>getComputedStyle(e).animationName") == "none"
                                       for c in record.locator(".fx-rchip").all())
                            page.emulate_media(reduced_motion="no-preference")
                            summary.focus()
                            page.keyboard.press("Space")
                            assert not record.evaluate("e=>e.open")
                            assert summary.evaluate("e=>e===document.activeElement")
                            results.append({"case": name, "viewport": width, "theme": theme,
                                            "lang": lang, "screenshot": screenshot,
                                            "pending_text": pending, "keyboard_open_close": "PASS",
                                            "summary_height": summary_box["height"], **measured})
                        except Exception as exc:
                            page.screenshot(path=str(out / f"failure-{label}.png"),
                                            full_page=True, animations="disabled")
                            (out / "failure.json").write_text(json.dumps({
                                "case": label, "error": str(exc), "source_hashes": source_hashes,
                                "completed": results, "page_errors": errors}, ensure_ascii=False, indent=2))
                            raise
                    context.close()
                    print(json.dumps({"phase": "context-complete", "width": width,
                                      "theme": theme, "lang": lang, "cases": len(results)}), flush=True)
        browser.close()
    assert not errors, errors
    report = {"fixture_only": True, "browser": f"Chromium {version}",
              "case_count": len(results), "source_hashes": source_hashes,
              "track_record_keyboard": "PASS", "mobile_ledger_keyboard_scroll": "PASS",
              "pending_static_reduced_motion": "PASS",
              "unrelated_requests_stubbed": sorted(stubbed),
              "page_errors": sorted(set(errors)), "results": results}
    (out / "browser-proof.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"phase": "complete", "case_count": len(results),
                      "min_contrast": min(t["contrast"] for r in results for t in r["text"]),
                      "min_font_size": min(t["fontSize"] for r in results for t in r["text"]),
                      "page_overflow_cases": sum(r["pageScrollWidth"] > r["viewport"]+1 for r in results),
                      "page_errors": sorted(set(errors))}), flush=True)


if __name__ == "__main__":
    main()
