#!/usr/bin/env python3
"""Compare the saved Confluence card layout with its exact parent in real Chromium."""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import socketserver
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

MEASURE = r"""() => {
  const rect=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
  const outside=[...document.querySelectorAll('body *')].filter(n=>{const r=rect(n);return r.width>0&&r.height>0&&(r.right>innerWidth+1||r.x< -1)&&getComputedStyle(n).position!=='fixed'}).map(n=>{
    const r=rect(n);return {tag:n.tagName,id:n.id,class:n.className,x:r.x,right:r.right,width:r.width,
      sharedNav:!!n.closest('.site-nav'),card:!!n.closest('.lc'),visibility:getComputedStyle(n).visibility};
  });
  return {overflow:document.documentElement.scrollWidth>innerWidth+1,scrollWidth:document.documentElement.scrollWidth,outside,cards:[...document.querySelectorAll('.lc')].map(c=>{
    const one=s=>c.querySelector(s), box=s=>rect(one(s));
    const font=s=>getComputedStyle(one(s)).fontSize;
    return {box:rect(c),top:box('.lc-top'),title:box('.lc-title-wrap'),legs:box('.legs'),wr:box('.lc-wr'),
      method:box('.lc-method'),summary:box('.lc-method summary'),action:rect(c.querySelector('a')),
      titleGap:box('.legs').y-box('.lc-title-wrap').bottom,
      directChildren:[...one('.lc-top').children].map(n=>n.className),
      legsCount:c.querySelectorAll('.legs').length,legCount:c.querySelectorAll('.leg').length,
      descendantOverflow:[...c.querySelectorAll('*')].filter(n=>{const r=rect(n);return r.width>0&&r.height>0&&(r.x<rect(c).x-1||r.right>rect(c).right+1)}).map(n=>({tag:n.tagName,class:n.className,box:rect(n)})),
      legRows:[...c.querySelectorAll('.leg')].map(n=>({box:rect(n),badge:rect(n.querySelector('.leg-tf')),
        text:rect(n.querySelector('.leg-txt')),client:n.querySelector('.leg-txt').clientWidth,
        scroll:n.querySelector('.leg-txt').scrollWidth,content:n.innerText})),
      rates:[...c.querySelectorAll('.lc-wr-big,.lc-wr-old')].map(rect),samples:[...c.querySelectorAll('.lc-sample')].map(rect),
      values:[...c.querySelectorAll('.lc-baseline-value')].map(n=>({box:rect(n),text:n.innerText,state:n.dataset.state})),
      fonts:{title:font('.lc-title'),leg:font('.leg-txt'),rate:font('.lc-wr-big'),sample:font('.lc-sample'),action:getComputedStyle(c.querySelector('a')).fontSize},
      hrefs:[...c.querySelectorAll('a')].map(n=>n.getAttribute('href')),
      publicText:[...c.querySelectorAll('.lc-title-wrap,.legs,.lc-wr,.lc-method,.lc-foot')].map(n=>n.textContent.trim()).sort()
    };
  })};
}"""


def meta(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "blob": hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-page", required=True, type=Path)
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline_page.resolve()
    pages = {"before": baseline.read_bytes(), "after": (ROOT/"site/confluence_screener.html").read_bytes()}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT/"site"), **kw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/premiumdata/"):
                self.send_response(403); self.end_headers(); return
            version = parse_qs(parsed.query).get("layout_version", [None])[0]
            if parsed.path == "/confluence_screener.html" and version in pages:
                data = pages[version]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers(); self.wfile.write(data); return
            super().do_GET()

        def log_message(self, *_):
            pass

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:"+str(server.server_address[1])
    plan = [(width, lang, False) for width in (320, 390, 640, 641, 767, 768, 960, 1440) for lang in ("en", "zh")]
    plan += [(width, lang, True) for width in (320, 768) for lang in ("en", "zh")]
    captures, cases, errors = [], [], []
    capture_keys = {(320, "en", False), (320, "zh", False), (641, "en", False),
                    (768, "zh", False), (1440, "en", False), (1440, "zh", False), (768, "en", True)}
    try:
        with sync_playwright() as pw:
            options = {"headless": True}
            if args.browser_executable:
                options["executable_path"] = args.browser_executable
            browser = pw.chromium.launch(**options)
            version = browser.version
            for width, lang, stress in plan:
                name = ("stress" if stress else "served")+"-"+str(width)+"-"+lang
                theme = "dark" if lang == "en" else "light"
                case = {"name": name, "width": width, "lang": lang, "theme": theme, "synthetic_label_stress": stress}
                context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1,
                    is_mobile=width <= 500, has_touch=width <= 500, reduced_motion="reduce")
                context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1" else route.abort())
                context.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                page = context.new_page()
                page.set_default_timeout(6000)
                local_errors = []
                page.on("pageerror", lambda error: (local_errors.append(str(error)), errors.append(str(error))))
                try:
                    for state in ("before", "after"):
                        page.goto(origin+"/confluence_screener.html?layout_version="+state, wait_until="load")
                        if stress:
                            page.evaluate("""() => {
                              document.querySelector('.leg-txt .l-en').textContent='LongUnbrokenCriterionIdentifierForResponsiveContainment'.repeat(3);
                              document.querySelector('.leg-txt .l-zh').textContent='较长期均线趋势与周线确认条件同时成立且必须完整显示'.repeat(3);
                            }""")
                        case[state] = page.evaluate(MEASURE)
                        if (width, lang, stress) in capture_keys and (state == "after" or width == 1440):
                            filename = state+"-"+name+".png"
                            page.locator('.lc').first.screenshot(path=str(out/filename))
                            captures.append({"file": filename, "state": state, "width": width, "lang": lang, "stress": stress})
                    before, after = case["before"], case["after"]
                    if after["overflow"]:
                        assert width == 960 and not stress, "Unexpected document overflow"
                        assert before["overflow"] and after["scrollWidth"] == before["scrollWidth"], "Document overflow changed"
                        assert after["outside"] == before["outside"] and after["outside"], "Overflow ownership or geometry changed"
                        assert all(n["sharedNav"] and not n["card"] and n["visibility"] == "hidden" for n in after["outside"]), after["outside"]
                        case["known_baseline_navigation_overflow"] = {"unchanged": True, "scrollWidth": after["scrollWidth"], "viewport": width, "owner": "hidden shared .site-nav menus"}
                    assert len(before["cards"]) == len(after["cards"]) == 3
                    assert max(c["legCount"] for c in after["cards"]) == 4, "Expected actual four-leg combination"
                    for index, (old, new) in enumerate(zip(before["cards"], after["cards"])):
                        assert new["directChildren"] == ["lc-rank cs-tipped", "lc-title-wrap", "legs", "lc-wr"], new["directChildren"]
                        assert new["legsCount"] == 1 and new["legCount"] == old["legCount"]
                        assert not new["descendantOverflow"], new["descendantOverflow"]
                        assert new["fonts"] == old["fonts"] and new["hrefs"] == old["hrefs"]
                        assert new["publicText"] == old["publicText"]
                        assert new["summary"]["height"] >= old["summary"]["height"] >= 44
                        assert new["action"]["height"] >= old["action"]["height"]-1
                        assert 15 <= new["titleGap"] <= 17, {"card": index, "titleGap": new["titleGap"]}
                        for row in new["legRows"]:
                            assert row["scroll"] <= row["client"]+1, row
                            assert row["text"]["right"] <= new["legs"]["right"]+1, row
                            assert row["badge"]["width"] >= 25 and row["badge"]["height"] > 10, row
                        assert new["wr"]["right"] <= new["top"]["right"]+1
                        assert new["legs"]["bottom"] <= new["method"]["y"]+1
                        assert new["wr"]["bottom"] <= new["method"]["y"]+1
                        for key in ("rates", "samples"):
                            assert abs(new[key][0]["y"]-new[key][1]["y"]) < 1
                        assert [v["text"] for v in new["values"]] == [v["text"] for v in old["values"]]
                        assert abs(new["values"][0]["box"]["y"]-new["values"][1]["box"]["y"]) < 1
                        if width < 768:
                            assert abs(new["legs"]["width"]-new["top"]["width"]) < 1
                            assert abs(new["wr"]["width"]-new["top"]["width"]) < 1
                            assert new["wr"]["y"] >= new["legs"]["bottom"]+15
                        else:
                            assert abs(new["legs"]["x"]-new["title"]["x"]) < 1
                            assert new["legs"]["right"]+15 <= new["wr"]["x"]
                            assert abs(new["wr"]["width"]-310) < 1
                        new["card_height_reduction"] = old["box"]["height"]-new["box"]["height"]
                        new["action_upward"] = (old["action"]["y"]-old["box"]["y"])-(new["action"]["y"]-new["box"]["y"])
                        if width >= 960 and not stress:
                            assert new["card_height_reduction"] > 60 and new["action_upward"] > 60, new
                    card = page.locator('.lc').first
                    sequence = [card.locator('.lc-since')]+[card.locator('.leg-tf').nth(i) for i in range(card.locator('.leg-tf').count())]+[card.locator('.lc-method summary')]
                    card.locator('.lc-rank').focus()
                    focus = []
                    for target in sequence:
                        page.keyboard.press('Tab')
                        expect(target).to_be_focused()
                        details = target.evaluate("""n=>({class:n.className,text:n.innerText,visible:n.matches(':focus-visible'),outline:getComputedStyle(n).outlineStyle,outlineWidth:getComputedStyle(n).outlineWidth})""")
                        assert details["visible"] and details["outline"] != "none" and float(details["outlineWidth"].replace('px','')) > 0, details
                        focus.append(details)
                    summary = card.locator('.lc-method summary')
                    summary.press('Enter')
                    expect(card.locator('.lc-method')).to_have_attribute('open', '')
                    opened = page.evaluate("""()=>{const cards=[...document.querySelectorAll('.lc')];const c=cards[0];return {methodBottom:c.querySelector('.lc-method').getBoundingClientRect().bottom,footerTop:c.querySelector('.lc-foot').getBoundingClientRect().top,cardBottom:c.getBoundingClientRect().bottom,nextTop:cards[1].getBoundingClientRect().top}}""")
                    assert opened["methodBottom"] <= opened["footerTop"] and opened["cardBottom"] < opened["nextTop"]
                    if width in (767, 768) and not stress:
                        badge = card.locator('.leg-tf').last
                        badge.focus()
                        badge.evaluate("n=>window.__layoutFocusedNode=n")
                        page.set_viewport_size({"width": 768 if width == 767 else 767, "height": 900})
                        assert badge.evaluate("n=>n===window.__layoutFocusedNode && n===document.activeElement")
                        expect(card.locator('.lc-method')).to_have_attribute('open', '')
                        page.set_viewport_size({"width": width, "height": 900})
                        summary.focus()
                        case["resize"] = {"same_focused_node": True, "open_disclosure_preserved": True, "crossed": [767, 768]}
                    summary.press('Enter')
                    expect(card.locator('.lc-method')).not_to_have_attribute('open', '')
                    page.keyboard.press('Tab')
                    company = card.locator('a.tkr').first
                    expect(company).to_be_focused()
                    destination = company.get_attribute('href')
                    page.route('**/stocks/*', lambda route: route.fulfill(content_type='text/html', body='<h1>Local company navigation proof</h1>'))
                    company.press('Enter')
                    page.wait_for_url('**/'+destination)
                    assert not local_errors, local_errors
                    case.update(status='PASS', focus_order=focus, opened_method=opened, company_destination=destination)
                except Exception as error:
                    case.update(status='FAIL', error=str(error), trace=traceback.format_exc(limit=3))
                finally:
                    context.close()
                cases.append(case)
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    assert len(cases) == len(plan) == 20
    for capture in captures:
        capture.update(meta(out/capture['file']))
    report = {"schema": "confluence_responsive_layout_browser/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
        "browser": version, "contexts": len(cases), "page_observations": len(cases)*2, "cases": cases, "captures": captures,
        "page_errors": errors, "passed": sum(c['status']=='PASS' for c in cases), "failed": sum(c['status']=='FAIL' for c in cases),
        "sources": {p: meta(ROOT/p) for p in ('templates/confluence_screener.html.j2','site/confluence_screener.html','site/premiumdata/confluence_screener.json','scripts/verify_confluence_layout_browser.py')},
        "baseline_page": meta(baseline), "scope": "Sixteen actual saved-page before/after comparisons and four explicitly synthetic long-label stress cases. Local HTTP, blocked external requests, no auth changes; company navigation intercepted locally. Shared shell/font completeness, live entitlement, spoken AT and deployment are not claimed."}
    (out/'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({"passed": report['passed'], "failed": report['failed'], "contexts": len(cases), "page_errors": len(errors),
        "report": str(out/'browser-report.json'), "failures": [{"name": c['name'], "error": c['error'][:500]} for c in cases if c['status']=='FAIL']}, ensure_ascii=False))
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
