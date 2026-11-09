#!/usr/bin/env python3
"""Exercise native retry-to-reload focus using the saved Confluence page/payload.

Auth and HTTP responses are controlled local fixtures, not live entitlement.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.server
import json
import socketserver
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_confluence_screener_browser import AUTH


def meta(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}


SNAPSHOT = """() => {
  const status=document.querySelector('#confluence-access-status');
  const retry=document.querySelector('#confluence-check-access');
  const reload=document.querySelector('#confluence-reload-access');
  const active=document.activeElement;
  const box=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right}};
  return {state:status.dataset.state,statusHidden:status.hidden,
    message:document.querySelector('#confluence-access-message').textContent,
    messageVisible:document.querySelector('#confluence-access-message').innerText,
    retryHidden:retry.hidden,retryDisabled:retry.getAttribute('aria-disabled'),reloadHidden:reload.hidden,
    activeId:active.id,activeTag:active.tagName,activeHref:active.getAttribute('href'),
    activePublicMethod:active.matches('.lc-method summary'),
    activeHidden:!!active.closest('[hidden]'),focusVisible:active.matches(':focus-visible'),
    reloadBox:box(reload),statusBox:box(status),documentWidth:document.documentElement.scrollWidth,
    publicMarkup:[...document.querySelectorAll('.lc-top,.lc-method,.lc.free .lc-foot')].map(n=>n.outerHTML),
    locked:document.querySelectorAll('.locked[data-confluence-combo]').length,
    hydrated:document.querySelectorAll('[data-confluence-hydrated]').length,
    paidLinks:[...document.querySelectorAll('.lc.gated a.tkr')].map(n=>n.getAttribute('href')),
    busy:[...document.querySelectorAll('[data-confluence-combo]')].map(n=>n.getAttribute('aria-busy')),
    focusEvents:window.__recoveryFocusEvents||[],url:location.href};
}"""


def brief(snapshot):
    value = {k: v for k, v in snapshot.items() if k != 'publicMarkup'}
    data = json.dumps(snapshot['publicMarkup'], ensure_ascii=False, separators=(',', ':')).encode()
    value['public_markup_sha256'] = hashlib.sha256(data).hexdigest()
    value['public_regions'] = len(snapshot['publicMarkup'])
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--page', type=Path, default=ROOT/'site/confluence_screener.html')
    parser.add_argument('--browser-executable')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    page_path = args.page.resolve(); page_body = page_path.read_bytes()
    payload_path = ROOT/'site/premiumdata/confluence_screener.json'
    payload = json.loads(payload_path.read_text())
    mismatch = copy.deepcopy(payload)
    mismatch['source_generation']['sha256'] = '0'*64
    assert mismatch['source_generation']['sha256'] != payload['source_generation']['sha256']
    assert mismatch['schema'] == payload['schema'] == 'tier_payload.v2'
    assert mismatch['built'] == payload['built']
    expected_links = ['stocks/'+quote(t['ticker'], safe='')+'.html'
                      for c in payload['combos'] for t in c['active_tickers']]
    current = {'ctl': None}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT/'site'), **kw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            ctl = current['ctl']
            if parsed.path == '/premiumdata/confluence_screener.json':
                ctl['requests'].append({'path': self.path, 'method': 'GET'})
                index = len(ctl['requests'])
                if index == 1:
                    status, body = 503, b'{}'
                elif index == 2:
                    ctl['pending'].set()
                    if not ctl['release'].wait(5):
                        ctl['server_errors'].append('Controlled second response was not released within five seconds')
                    status, body = 200, json.dumps(mismatch).encode()
                else:
                    status, body = 200, json.dumps(payload).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    ctl['aborted_responses'] += 1
                return
            if parsed.path == '/confluence_screener.html':
                ctl['page_hits'].append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(page_body)))
                self.end_headers(); self.wfile.write(page_body); return
            if parsed.path.startswith('/premiumdata/'):
                self.send_response(403); self.end_headers(); return
            super().do_GET()

        def log_message(self, *_):
            pass

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

    server = Server(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = 'http://127.0.0.1:'+str(server.server_address[1])
    cases, captures, errors = [], [], []
    plan = [(width, lang, theme, mode)
            for width, lang, theme in ((1440, 'en', 'dark'), (320, 'zh', 'light'))
            for mode in ('retry_to_reload', 'preserve_moved_focus', 'focus_signout_reentry',
                         'focus_returns_to_retry', 'focus_moves_to_public')]
    try:
        with sync_playwright() as pw:
            options = {'headless': True}
            if args.browser_executable:
                options['executable_path'] = args.browser_executable
            browser = pw.chromium.launch(**options); version = browser.version
            for width, lang, theme, mode in plan:
                name = mode+'-'+str(width)+'-'+lang
                case = {'name': name, 'mode': mode, 'width': width, 'lang': lang, 'observations': []}
                ctl = {'pending': threading.Event(), 'release': threading.Event(), 'requests': [],
                       'page_hits': [], 'server_errors': [], 'aborted_responses': 0}
                current['ctl'] = ctl
                context = browser.new_context(viewport={'width': width, 'height': 900},
                    device_scale_factor=1, reduced_motion='reduce', is_mobile=width <= 500, has_touch=width <= 500)
                context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' else route.abort())
                context.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                page = context.new_page(); page.set_default_timeout(6000)
                local_errors = []
                page.on('pageerror', lambda error: (local_errors.append(str(error)), errors.append(str(error))))
                def observe(phase):
                    value = page.evaluate(SNAPSHOT)
                    case['observations'].append({'phase': phase, **brief(value)})
                    return value
                try:
                    page.goto(origin+'/confluence_screener.html?keep=a&keep=b#return-point', wait_until='load')
                    page.evaluate(AUTH)
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    status = page.locator('#confluence-access-status')
                    expect(status).to_have_attribute('data-state', 'unavailable')
                    retry = page.locator('#confluence-check-access')
                    reload = page.locator('#confluence-reload-access')
                    initial = observe('initial_unavailable')
                    assert initial['locked'] == 2 and initial['hydrated'] == 0 and initial['paidLinks'] == []
                    assert len(ctl['requests']) == 1
                    # Seed a known preceding position, then use native Tab and Enter.
                    page.locator('.locked a').last.focus()
                    page.keyboard.press('Tab'); expect(retry).to_be_focused()
                    page.evaluate("""mode => {
                      window.__recoveryFocusEvents=[];
                      const reload=document.querySelector('#confluence-reload-access');
                      reload.addEventListener('focus',()=>{
                        window.__recoveryFocusEvents.push({retryHidden:document.querySelector('#confluence-check-access').hidden,
                          reloadHidden:reload.hidden,state:document.querySelector('#confluence-access-status').dataset.state,
                          message:document.querySelector('#confluence-access-message').innerText,
                          activeId:document.activeElement.id});
                        if(mode==='focus_signout_reentry')window.__d04Auth(null,'SIGNED_OUT');
                        if(mode==='focus_returns_to_retry')document.querySelector('#confluence-check-access').focus({preventScroll:true});
                        if(mode==='focus_moves_to_public'){
                          window.__recoveryMovedFocus=document.querySelector('.lc-method summary');
                          window.__recoveryMovedFocus.focus({preventScroll:true});
                        }
                      },{once:true});
                    }""", mode)
                    retry.press('Enter')
                    expect(status).to_have_attribute('data-state', 'checking')
                    expect(retry).to_be_focused()
                    assert ctl['pending'].wait(3), 'Second request did not reach the controlled server'
                    assert len(ctl['requests']) == 2
                    pending = observe('pending_keyboard_retry')
                    assert not pending['retryHidden'] and pending['retryDisabled'] == 'true'
                    if mode == 'preserve_moved_focus':
                        for _ in range(12):
                            page.keyboard.press('Shift+Tab')
                            if page.evaluate("document.activeElement.matches('.lc-method summary')"):
                                break
                        assert page.evaluate("document.activeElement.matches('.lc-method summary')")
                        page.evaluate('window.__recoveryMovedFocus=document.activeElement')
                    ctl['release'].set()
                    expect(status).not_to_have_attribute('data-state', 'checking')
                    page.evaluate('() => new Promise(resolve => requestAnimationFrame(resolve))')
                    final = observe('mismatch_response_settled')
                    assert final['publicMarkup'] == initial['publicMarkup']
                    assert final['locked'] == 2 and final['hydrated'] == 0 and final['paidLinks'] == []
                    assert final['busy'] == ['false', 'false']
                    assert len(ctl['requests']) == 2
                    if mode == 'focus_signout_reentry':
                        assert len(final['focusEvents']) == 1, brief(final)
                        assert final['focusEvents'][0]['retryHidden'] is False
                        assert final['state'] == 'locked' and final['statusHidden']
                        assert final['retryHidden'] and final['reloadHidden'] and final['message'] == ''
                        assert final['retryDisabled'] == 'false'
                        assert page.evaluate('window.MDXAuth.user()') is None
                        assert not final['activeHidden']
                    else:
                        assert final['state'] == 'mismatch' and not final['statusHidden']
                        assert final['retryHidden'] == (mode != 'focus_returns_to_retry') and not final['reloadHidden']
                        expected_message = 'This page and the stock list are from different updates. Reload the latest page.' if lang == 'en' else '此页面与股票名单来自不同更新，请重新加载最新页面。'
                        assert final['messageVisible'] == expected_message
                        assert final['reloadBox']['height'] >= 44
                        assert final['reloadBox']['x'] >= 0 and final['reloadBox']['right'] <= width+1
                        assert final['documentWidth'] <= width
                        if mode in ('preserve_moved_focus', 'focus_moves_to_public'):
                            assert page.evaluate('document.activeElement===window.__recoveryMovedFocus')
                            assert final['activePublicMethod']
                            if mode == 'preserve_moved_focus':
                                assert not final['focusEvents']
                            else:
                                assert len(final['focusEvents']) == 1 and not final['focusEvents'][0]['retryHidden']
                        elif mode == 'focus_returns_to_retry':
                            assert final['activeId'] == 'confluence-check-access' and not final['activeHidden']
                            assert len(final['focusEvents']) == 1 and not final['focusEvents'][0]['retryHidden']
                        else:
                            filename = 'mismatch-focus-'+str(width)+'-'+lang+'.png'
                            status.screenshot(path=str(out/filename))
                            captures.append({'file': filename, 'width': width, 'lang': lang})
                            assert final['activeId'] == 'confluence-reload-access' and final['focusVisible'], brief(final)
                            assert len(final['focusEvents']) == 1
                            event = final['focusEvents'][0]
                            assert not event['retryHidden'] and not event['reloadHidden'] and event['state'] == 'mismatch'
                            assert event['message'] == expected_message
                            url = page.url; hits = len(ctl['page_hits'])
                            with page.expect_navigation(wait_until='load'):
                                reload.press('Enter')
                            assert page.url == url and len(ctl['page_hits']) == hits+1
                            page.evaluate(AUTH)
                            page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                            expect(status).to_have_attribute('data-state', 'loaded')
                            recovered = observe('native_reload_valid_pair')
                            assert recovered['hydrated'] == 2 and recovered['paidLinks'] == expected_links
                            assert recovered['publicMarkup'] == initial['publicMarkup']
                            assert len(ctl['requests']) == 3
                            page.evaluate("window.__d04Auth(null,'SIGNED_OUT')")
                            signed_out = observe('signout_after_recovery')
                            assert signed_out['locked'] == 2 and signed_out['hydrated'] == 0 and not signed_out['paidLinks']
                    assert not local_errors and not ctl['server_errors'], (local_errors, ctl['server_errors'])
                    case['status'] = 'PASS'
                except Exception as error:
                    case.update(status='FAIL', error=str(error), trace=traceback.format_exc(limit=3))
                finally:
                    ctl['release'].set()
                    case['requests'] = ctl['requests']
                    case['page_hits'] = ctl['page_hits']
                    case['server_errors'] = ctl['server_errors']
                    case['aborted_responses'] = ctl['aborted_responses']
                    context.close()
                cases.append(case)
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    assert len(cases) == len(plan) == 10
    for capture in captures:
        capture.update(meta(out/capture['file']))
    report = {'schema': 'confluence_recovery_browser/v1', 'observed_at': datetime.now(timezone.utc).isoformat(),
        'browser': version, 'contexts': len(cases), 'passed': sum(c['status']=='PASS' for c in cases),
        'failed': sum(c['status']=='FAIL' for c in cases), 'page_errors': errors, 'cases': cases, 'captures': captures,
        'sources': {'page': meta(page_path), 'protected_payload': meta(payload_path), 'harness': meta(Path(__file__)),
                    'existing_auth_fixture_owner': meta(ROOT/'scripts/verify_confluence_screener_browser.py')},
        'fixture': {'page': 'actual saved HTML', 'payload': 'actual saved protected JSON',
                    'mismatch': 'only full-source hash replaced with an intentionally different hash; same schema and clock',
                    'sequence': '503 unavailable -> held mismatching v2 -> valid pair after native reload',
                    'auth': 'existing controlled AUTH fixture; no live entitlement'},
        'scope': 'Native Tab/Enter retry, pending response, focus-before-hide handoff, newer user focus, synchronous sign-out reentry, URL-preserving reload, matching-pair hydration and sign-out. No deployment/live-account/production-auth or spoken AT claim.'}
    (out/'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': report['passed'], 'failed': report['failed'], 'contexts': len(cases),
        'page_errors': len(errors), 'report': str(out/'browser-report.json'),
        'failures': [{'name': c['name'], 'error': c['error'][:240]} for c in cases if c['status']=='FAIL']}, ensure_ascii=False))
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
