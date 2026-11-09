#!/usr/bin/env python3
"""Inspect the monthly-method figure, native disclosure/motion and narrow locked grouping."""
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

SNAPSHOT = r"""() => {
  const box=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
  const card=document.querySelector('.lc');const method=card.querySelector('.lc-method');
  return {documentOverflow:document.documentElement.scrollWidth>innerWidth+1,
    method:{box:box(method),summary:box(method.querySelector('summary')),open:method.open,
      firstParagraph:method.querySelector(':scope>p')?.innerText,
      firstParagraphHeight:method.querySelector(':scope>p')?.getBoundingClientRect().height,
      remainingParagraphs:[...method.querySelectorAll(':scope>p')].map(n=>n.innerText)},
    figure:method.querySelector('figure')?{box:box(method.querySelector('figure')),
      text:method.querySelector('figure').innerText,caption:method.querySelector('figcaption').innerText,
      steps:[...method.querySelectorAll('ol>li')].map(n=>({box:box(n),text:n.innerText,scroll:n.scrollWidth,client:n.clientWidth})),
      opacity:getComputedStyle(method.querySelector('figure')).opacity,
      animationName:getComputedStyle(method.querySelector('figure')).animationName,
      animationDuration:getComputedStyle(method.querySelector('figure')).animationDuration,
      captionLast:method.querySelector('figure').lastElementChild.matches('figcaption'),
      captionCount:method.querySelectorAll('figcaption').length,
      animations:method.querySelector('figure').getAnimations().map(a=>({name:a.animationName,timing:a.effect.getTiming()}))}:null,
    locked:[...document.querySelectorAll('.locked')].map(n=>({box:box(n),icon:box(n.querySelector('.ic')),
      text:box(n.querySelector('.lk-tx')),button:box(n.querySelector('a')),content:n.innerText,
      href:n.querySelector('a').getAttribute('href'),scroll:n.scrollWidth,client:n.clientWidth,
      textScroll:n.querySelector('.lk-tx').scrollWidth,textClient:n.querySelector('.lk-tx').clientWidth})),
    publicValues:[...document.querySelectorAll('.lc-wr')].map(n=>n.innerText),
    heroAnimations:document.querySelector('.hero-motif').getAnimations({subtree:true}).length};
}"""


def meta(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "blob": hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline-page', type=Path, required=True)
    parser.add_argument('--browser-executable')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline_page.resolve()
    pages = {'before': baseline.read_bytes(), 'after': (ROOT/'site/confluence_screener.html').read_bytes()}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT/'site'), **kw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path.startswith('/premiumdata/'):
                self.send_response(403); self.end_headers(); return
            version = parse_qs(parsed.query).get('method_version', [None])[0]
            if parsed.path == '/confluence_screener.html' and version in pages:
                data = pages[version]
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data); return
            super().do_GET()

        def log_message(self, *_):
            pass

    server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = 'http://127.0.0.1:'+str(server.server_address[1])
    plan = [(w, lang, 'reduce', True) for w in (320, 390, 400, 401, 1440) for lang in ('en', 'zh')]
    plan += [(320, 'en', 'no-preference', True), (1440, 'zh', 'no-preference', True), (320, 'en', 'reduce', False)]
    cases, captures, errors = [], [], []
    capture_keys = {(320, 'en'), (320, 'zh'), (1440, 'en'), (1440, 'zh')}
    try:
        with sync_playwright() as pw:
            options = {'headless': True}
            if args.browser_executable:
                options['executable_path'] = args.browser_executable
            browser = pw.chromium.launch(**options); version = browser.version
            for width, lang, motion, scripts in plan:
                name = str(width)+'-'+lang+'-'+motion+('' if scripts else '-no-page-js')
                case = {'name': name, 'width': width, 'lang': lang, 'reduced_motion': motion, 'page_javascript_enabled': scripts}
                context = browser.new_context(viewport={'width': width, 'height': 900}, device_scale_factor=1,
                    is_mobile=width <= 500, has_touch=width <= 500, reduced_motion=motion, java_script_enabled=scripts)
                context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' else route.abort())
                if scripts:
                    context.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps('dark' if lang == 'en' else 'light')+");")
                page = context.new_page(); page.set_default_timeout(6000)
                local_errors = []
                page.on('pageerror', lambda error: (local_errors.append(str(error)), errors.append(str(error))))
                try:
                    for state in ('before', 'after'):
                        page.goto(origin+'/confluence_screener.html?method_version='+state, wait_until='load')
                        summary = page.locator('.lc').first.locator('.lc-method summary')
                        summary.focus()
                        if state == 'after' and scripts:
                            page.evaluate("""() => {
                              window.__methodOpenMotion=[];
                              document.querySelector('.lc-method').addEventListener('toggle',event=>{
                                if(!event.target.open)return;
                                const figure=event.target.querySelector('.method-figure');
                                const animations=figure.getAnimations();
                                window.__methodOpenMotion.push({opacity:getComputedStyle(figure).opacity,
                                  animations:animations.map(a=>({name:a.animationName,timing:a.effect.getTiming(),frames:a.effect.getKeyframes().map(k=>({offset:k.offset,opacity:k.opacity,transform:k.transform}))}))});
                              });
                            }""")
                        summary.press('Enter')
                        expect(page.locator('.lc-method').first).to_have_attribute('open', '')
                        expect(summary).to_be_focused()
                        if state == 'after' and scripts:
                            page.wait_for_function('window.__methodOpenMotion.length>0')
                            case['open_motion'] = page.evaluate('window.__methodOpenMotion[0]')
                            page.evaluate("""() => Promise.all(document.querySelector('.method-figure').getAnimations().map(a=>a.finished)).then(()=>true)""")
                        case[state] = page.evaluate(SNAPSHOT)
                        if scripts and motion == 'reduce' and (width, lang) in capture_keys:
                            target = page.locator('.method-figure').first if state == 'after' else page.locator('.lc-method').first.locator(':scope>p').first
                            filename = state+'-method-'+str(width)+'-'+lang+'.png'
                            target.screenshot(path=str(out/filename)); captures.append({'file': filename, 'surface': 'method', 'state': state, 'width': width, 'lang': lang})
                            if width == 320:
                                filename = state+'-locked-'+str(width)+'-'+lang+'.png'
                                page.locator('.locked').first.screenshot(path=str(out/filename)); captures.append({'file': filename, 'surface': 'locked', 'state': state, 'width': width, 'lang': lang})
                    before, after = case['before'], case['after']
                    assert not after['documentOverflow']
                    assert before['figure'] is None and after['figure'] is not None
                    assert len(after['figure']['steps']) == 2
                    assert after['figure']['captionLast'] and after['figure']['captionCount'] == 1
                    assert after['method']['remainingParagraphs'] == before['method']['remainingParagraphs'][1:]
                    assert after['publicValues'] == before['publicValues']
                    assert after['method']['summary']['height'] >= before['method']['summary']['height'] >= 44
                    assert after['figure']['box']['right'] <= after['method']['box']['right']+1
                    assert after['figure']['box']['y'] >= after['method']['summary']['bottom']+7
                    for step in after['figure']['steps']:
                        assert step['scroll'] <= step['client']+1 and step['box']['width'] >= 100, step
                    figure_text = after['figure']['text']
                    expected = ('Within each month', 'Share of winning fires', 'Across months', 'Average shares equally',
                                'above the next-close entry price after 21 trading days', 'not the fraction of winning months or the pooled win rate') if lang == 'en' else (
                                '每个月内', '触发后上涨的占比', '汇总各月', '各月占比等权平均', '价格高于入场价', '这不是盈利月份占比，也不是所有触发次数合并后的胜率')
                    assert all(text in figure_text for text in expected), figure_text
                    assert ('触发后' not in figure_text) if lang == 'en' else ('Share of winning fires' not in figure_text)
                    assert after['heroAnimations'] == before['heroAnimations'] == 0
                    if motion == 'reduce':
                        assert after['figure']['animationName'] == 'none' and after['figure']['animationDuration'] == '0s', after['figure']
                        if scripts:
                            assert case['open_motion']['animations'] == [] and float(case['open_motion']['opacity']) == 1, case['open_motion']
                    else:
                        observed_animations = case['open_motion']['animations']
                        assert len(observed_animations) == 1, case['open_motion']
                        animation = observed_animations[0]
                        assert animation['name'] == 'method-reveal'
                        assert animation['timing']['duration'] == 120 and animation['timing']['delay'] == 0 and animation['timing']['iterations'] == 1
                        assert animation['frames'][0]['opacity'] == '0.85' and animation['frames'][-1]['opacity'] == '1'
                        assert all(not f.get('transform') for f in animation['frames'])
                    assert float(after['figure']['opacity']) == 1
                    case['method_height_delta'] = after['method']['box']['height']-before['method']['box']['height']
                    case['figure_height_vs_paragraph'] = {'figure': after['figure']['box']['height'], 'prior_paragraph': before['method']['firstParagraphHeight']}
                    assert len(before['locked']) == len(after['locked']) == 2
                    for old, new in zip(before['locked'], after['locked']):
                        assert new['content'] == old['content'] and new['href'] == old['href']
                        assert new['scroll'] <= new['client']+1 and new['textScroll'] <= new['textClient']+1
                        assert new['button']['height'] >= old['button']['height'] >= 44
                        if width <= 400:
                            assert abs(new['icon']['y']-new['text']['y']) < 1
                            assert new['text']['x'] >= new['icon']['right']+13
                            assert abs(new['button']['x']-new['icon']['x']) < 1
                            assert new['button']['y'] >= max(new['icon']['bottom'],new['text']['bottom'])+13
                        new['height_reduction'] = old['box']['height']-new['box']['height']
                        new['action_upward'] = (old['button']['y']-old['box']['y'])-(new['button']['y']-new['box']['y'])
                        assert new['height_reduction'] >= -1, new
                        if width > 400:
                            assert abs(new['height_reduction']) < 1 and abs(new['action_upward']) < 1, new
                        if width == 320:
                            assert new['height_reduction'] > 20 and new['action_upward'] > 20, new
                    summary = page.locator('.lc-method').first.locator('summary')
                    summary.focus(); summary.press('Space')
                    expect(page.locator('.lc-method').first).not_to_have_attribute('open', '')
                    expect(summary).to_be_focused()
                    summary.press('Enter')
                    expect(page.locator('.lc-method').first).to_have_attribute('open', '')
                    expect(summary).to_be_focused()
                    button = page.locator('.locked a').first
                    button.focus(); destination = button.get_attribute('href')
                    focus = button.evaluate("n=>({visible:n.matches(':focus-visible'),outline:getComputedStyle(n).outlineStyle,width:getComputedStyle(n).outlineWidth})")
                    assert focus['visible'] and focus['outline'] != 'none'
                    page.route(destination, lambda route: route.fulfill(content_type='text/html', body='<h1>Intercepted existing app destination</h1>'))
                    button.press('Enter'); page.wait_for_url(destination)
                    assert not local_errors, local_errors
                    case.update(status='PASS', destination=destination, action_focus=focus)
                except Exception as error:
                    case.update(status='FAIL', error=str(error), trace=traceback.format_exc(limit=3))
                finally:
                    context.close()
                cases.append(case)
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    assert len(cases) == len(plan) == 13
    for capture in captures:
        capture.update(meta(out/capture['file']))
    report = {'schema':'confluence_method_browser/v1','observed_at':datetime.now(timezone.utc).isoformat(),
        'browser':version,'contexts':len(cases),'page_observations':sum(int('before' in c)+int('after' in c) for c in cases),'cases':cases,'captures':captures,'page_errors':errors,
        'passed':sum(c['status']=='PASS' for c in cases),'failed':sum(c['status']=='FAIL' for c in cases),
        'sources':{p:meta(ROOT/p) for p in ('templates/confluence_screener.html.j2','site/confluence_screener.html','site/premiumdata/confluence_screener.json','scripts/verify_confluence_method_browser.py')},
        'baseline_page':meta(baseline),'scope':'Actual saved-page before/after pairs. Two no-preference motion cases and one page-JavaScript-disabled native-disclosure case supplement reduced-motion EN/ZH widths. Browser evaluation observes state; no product controller is introduced. Existing app navigation is intercepted locally. No live entitlement, deployment, spoken AT or full shared-shell/font claim.'}
    (out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'failed':report['failed'],'contexts':len(cases),'page_errors':len(errors),
        'report':str(out/'browser-report.json'),'failures':[{'name':c['name'],'error':c['error'][:450]} for c in cases if c['status']=='FAIL']},ensure_ascii=False))
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
