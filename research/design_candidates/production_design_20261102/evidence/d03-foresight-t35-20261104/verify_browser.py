"""Render the real Foresight template/assets in an isolated Chromium fixture.

No server, live data, production requests, repository site/ writes or deploys.
Every request is intercepted. Only template static assets and fixture HTML are
served; unrelated data requests are empty fixture responses and are disclosed.
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


MEASURE = """el => {
  const b = el.getBoundingClientRect(), s = getComputedStyle(el);
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', {willReadFrequently:true});
  function rgb(color) {
    cx.clearRect(0,0,1,1); cx.fillStyle = color; cx.fillRect(0,0,1,1);
    return [...cx.getImageData(0,0,1,1).data].slice(0,3);
  }
  function lum(color) {
    return rgb(color).map(v=>{ v/=255; return v<=.04045?v/12.92:((v+.055)/1.055)**2.4; })
      .reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  }
  const bg=lum(s.backgroundColor);
  const text = ['.fx-gate-k','.fx-gate-v','.fx-gate-d'].map(sel=>{
    const e=el.querySelector(sel), c=getComputedStyle(e), r=e.getBoundingClientRect();
    const fg=lum(c.color);
    return {selector:sel, text:e.innerText, fontSize:parseFloat(c.fontSize),
      contrast:(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05),
      x:r.x, right:r.right, width:r.width, height:r.height,
      overflow:e.scrollWidth>e.clientWidth+1};
  });
  return {state:el.dataset.state, x:b.x, right:b.right, width:b.width, height:b.height,
    clientWidth:el.clientWidth, scrollWidth:el.scrollWidth,
    viewport:innerWidth, pageScrollWidth:document.documentElement.scrollWidth,
    animation:s.animationName, background:s.backgroundColor,
    borderWidths:[s.borderTopWidth,s.borderRightWidth,s.borderBottomWidth,s.borderLeftWidth],
    borderColors:[s.borderTopColor,s.borderRightColor,s.borderBottomColor,s.borderLeftColor],
    iconsHidden:[...el.querySelectorAll('svg')].every(e=>e.getAttribute('aria-hidden')==='true'),
    text};
}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.repo.resolve(), args.out.resolve()
    assert out.is_dir() and not list(out.iterdir()), "output must be a new empty directory"
    print(json.dumps({"phase": "start", "out": str(out)}), flush=True)
    spec = importlib.util.spec_from_file_location(
        "trend_fixture", root / "tests/test_foresight_page_trend_state.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    states = {"unavailable": None, "closed": {"active": False},
              "open": {"active": False, "verdict": "buyable_washout"}}
    pages = {name: fixture._render([fixture._row()], dislocation=value)
             for name, value in states.items()}
    templates = root / "templates"
    requests_stubbed, errors = set(), []

    def route_request(route):
        parsed = urlparse(route.request.url)
        path = unquote(parsed.path).removeprefix("/case/")
        if parsed.hostname != "127.0.0.1":
            requests_stubbed.add("external:" + parsed.hostname + parsed.path)
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

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        version = browser.version
        for width in (320, 390, 1440):
            for theme in ("light", "dark"):
                for lang in ("en", "zh"):
                    context = browser.new_context(viewport={"width": width, "height": 900},
                                                  device_scale_factor=1)
                    context.add_init_script(
                        f"localStorage.setItem('theme',{json.dumps(theme)});"
                        f"localStorage.setItem('lang',{json.dumps(lang)});")
                    context.route("**/*", route_request)
                    page = context.new_page()
                    page.set_default_timeout(5000)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for name in states:
                        page.goto(f"http://127.0.0.1/case/{name}.html", wait_until="load")
                        page.evaluate("document.fonts.ready")
                        gate = page.locator(".fx-gate")
                        # Read at a normal centred scroll position, not directly
                        # underneath the existing fixed chat launcher.
                        gate.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
                        screenshot = f"{name}-{width}-{theme}-{lang}.png"
                        gate.screenshot(path=str(out / screenshot), animations="disabled")
                        measured = gate.evaluate(MEASURE)
                        assert measured["state"] == name
                        assert measured["x"] >= -1 and measured["right"] <= width + 1
                        assert measured["scrollWidth"] <= measured["clientWidth"] + 1
                        assert measured["iconsHidden"]
                        assert len(set(measured["borderWidths"])) == 1
                        assert len(set(measured["borderColors"])) == 1
                        for text in measured["text"]:
                            assert not text["overflow"], (screenshot, text)
                            assert text["contrast"] >= 4.5, (screenshot, text)
                        assert measured["text"][0]["fontSize"] >= 12
                        assert measured["text"][2]["fontSize"] >= 14
                        expected = {
                            "en": {"unavailable": "Unavailable", "closed": "Closed", "open": "Open"},
                            "zh": {"unavailable": "暂不可用", "closed": "关闭", "open": "开启"},
                        }[lang][name]
                        assert measured["text"][1]["text"].startswith(expected)
                        assert page.locator(".fx-card").count() == 1
                        if name == "unavailable" and width in (390, 1440):
                            page.screenshot(path=str(out / f"page-{width}-{theme}-{lang}.png"),
                                            full_page=True, animations="disabled")
                        page.emulate_media(reduced_motion="reduce")
                        assert gate.evaluate("e=>getComputedStyle(e).animationName") == "none"
                        page.emulate_media(reduced_motion="no-preference")
                        results.append({"viewport": width, "theme": theme, "lang": lang,
                                        "screenshot": screenshot, **measured})
                    if width in (390, 1440) and theme == "light" and lang == "en":
                        page.locator("#settings-open").click()
                        page.locator("#set-theme-dark").click()
                        page.wait_for_function("document.documentElement.dataset.theme==='dark'")
                        page.locator('.lang-toggle [data-l="zh"]').click()
                        page.wait_for_function("document.documentElement.dataset.lang==='zh'")
                        assert "开启" in gate.inner_text()
                        page.locator("#set-theme-light").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.theme==='light'")
                        page.locator(".lang-toggle").focus()
                        page.keyboard.press("Enter")
                        page.wait_for_function("document.documentElement.dataset.lang==='en'")
                        page.keyboard.press("Escape")
                        page.wait_for_function("document.querySelector('#settings-open').getAttribute('aria-expanded')==='false'")
                    context.close()
        browser.close()
    report = {
        "fixture_only": True, "browser": f"Chromium {version}",
        "case_count": len(results), "source_template_sha256": hashlib.sha256(
            (templates / "foresight.html.j2").read_bytes()).hexdigest(),
        "theme_css_sha256": hashlib.sha256((templates / "theme.css").read_bytes()).hexdigest(),
        "theme_js_sha256": hashlib.sha256((templates / "theme.js").read_bytes()).hexdigest(),
        "settings_theme_language_keyboard_and_escape_390_1440": "PASS",
        "unrelated_requests_stubbed": sorted(requests_stubbed),
        "page_errors": sorted(set(errors)), "results": results,
    }
    (out / "browser-proof.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"out": str(out), "case_count": len(results),
                      "page_errors": sorted(set(errors)),
                      "min_contrast": min(t["contrast"] for r in results for t in r["text"]),
                      "page_overflow_cases": sum(r["pageScrollWidth"] > r["viewport"] + 1 for r in results)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
