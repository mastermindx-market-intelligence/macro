"""Browser proof of the actual built China page, not a component replacement.

A process-owned localhost server is closed before return. External requests are
blocked; local built assets and their normal client code are used unchanged.
No production request, publishing, fixture masquerade or background daemon.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading

from playwright.sync_api import sync_playwright

from lib.china_pullback_view import snapshot


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    observed = snapshot()
    assert observed['available'], observed['quality']
    page_path = root / 'site/china.html'
    page_sha = sha256(page_path.read_bytes()).hexdigest()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root / 'site')))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks = []
    images = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for width in (1440, 390):
                    for theme in ('dark', 'light'):
                        for lang in ('en', 'zh'):
                            page = browser.new_page(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                            errors = []
                            page.on('pageerror', lambda e: errors.append(str(e)))
                            page.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
                            response = page.goto(f'http://127.0.0.1:{server.server_port}/china.html', wait_until='networkidle')
                            assert response.status == 200
                            page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;document.documentElement.lang=l;document.dispatchEvent(new Event('langchange'));}", [theme, lang])
                            suffix = f'{theme}-{lang}-{width}'
                            hero = out / f'page-hero-{suffix}.png'
                            page.screenshot(path=str(hero))
                            images.append(hero)
                            assert page.locator('.pbx-card').count() == 1
                            card = page.locator('.pbx-card')
                            assert card.get_attribute('data-pb-digest') == observed['source_digest']
                            assert card.get_attribute('data-pb-asof') == observed['asof']
                            value = f"{observed['drawdown_pct']:.1f}%"
                            assert card.locator('.pbx-number').inner_text() == value
                            assert page.locator('[data-pb-trigger-value]').inner_text() == value
                            assert card.get_attribute('data-pb-phase') == observed['phase']
                            # Hero popover uses the same observation; Escape closes it.
                            trigger = page.locator('[data-pb-trigger]')
                            trigger.click()
                            assert page.locator('#cnx-pop-risk .pbx-compact').is_visible()
                            page.keyboard.press('Escape')
                            page.wait_for_function("!document.querySelector('#cnx-pop-risk').classList.contains('open')")
                            metrics = card.evaluate("e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,overflow:e.scrollWidth>e.clientWidth,padding:parseFloat(getComputedStyle(e).paddingLeft),buttonHeight:e.querySelector('button').getBoundingClientRect().height})")
                            assert not metrics['overflow'] and metrics['padding'] >= 16
                            assert metrics['buttonHeight'] >= 44
                            card_image = out / f'page-card-{suffix}.png'
                            card.screenshot(path=str(card_image))
                            images.append(card_image)
                            button = card.locator('.pbx-open')
                            button.focus()
                            page.keyboard.press('Enter')
                            page.wait_for_function("document.activeElement===document.querySelector('#cnx-dlg-risk .cnx-dlg-close')")
                            detail = page.locator('#cnx-dlg-risk .pbx-detail')
                            assert detail.is_visible()
                            assert detail.get_attribute('data-pb-digest') == observed['source_digest']
                            assert not detail.evaluate('e=>e.scrollWidth>e.clientWidth')
                            assert page.locator('#cnx-dlg-risk .cnx-dlg-panel').evaluate('e=>e.scrollWidth<=e.clientWidth')
                            ids = page.locator('.pbx [id]').evaluate_all('els=>els.map(e=>e.id)')
                            assert len(ids) == len(set(ids))
                            assert not page.locator('.pbx svg path').evaluate_all("els=>els.some(e=>/NaN|Infinity/.test(e.getAttribute('d')||''))")
                            page.keyboard.press('Shift+Tab')
                            shifted = page.evaluate("({tag:document.activeElement.tagName,cls:document.activeElement.className,text:document.activeElement.textContent.slice(0,90)})")
                            assert page.evaluate("document.querySelector('#cnx-dlg-risk').contains(document.activeElement)")
                            page.keyboard.press('Tab')
                            assert page.evaluate("document.activeElement===document.querySelector('#cnx-dlg-risk .cnx-dlg-close')"), {'shifted':shifted,'after':page.evaluate("({tag:document.activeElement.tagName,cls:document.activeElement.className,text:document.activeElement.textContent.slice(0,90)})")}
                            method = detail.locator('summary')
                            method.focus()
                            page.keyboard.press('Enter')
                            assert detail.locator('details').get_attribute('open') is not None
                            page.keyboard.press('Enter')
                            method.evaluate('e=>e.blur()')
                            page.locator('#cnx-dlg-risk').evaluate("e=>{e.scrollTop=0;e.querySelectorAll('.cnx-dlg-panel,.cnx-dlg-body').forEach(n=>n.scrollTop=0)}")
                            page.wait_for_timeout(400)
                            modal = out / f'page-dialog-{suffix}.png'
                            page.screenshot(path=str(modal))
                            images.append(modal)
                            label = detail.locator('.ilx[role="img"]').get_attribute('aria-label')
                            assert ('上证综指' in label) if lang == 'zh' else ('Shanghai' in label)
                            page.keyboard.press('Escape')
                            page.wait_for_function("!document.querySelector('#cnx-dlg-risk').classList.contains('open')")
                            assert button.evaluate('e=>e===document.activeElement')
                            assert page.evaluate("document.body.style.overflow") == ''
                            # Same client code, expired source clock; no substitution data.
                            page.locator('[data-pb-valid-until]').evaluate_all("els=>els.forEach(e=>e.setAttribute('data-pb-valid-until','2000-01-01T00:00:00Z'))")
                            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                            assert card.get_attribute('data-pb-phase') == 'unavailable'
                            assert not card.locator('.pbx-current').is_visible()
                            assert not page.locator('[data-pb-trigger-value]').is_visible()
                            assert not errors, errors
                            checks.append({'width':width,'theme':theme,'language':lang,'card':metrics,'aria':label,
                                           'errors':errors,'keyboard_return':True,'expiry_demoted':True,
                                           'source_digest':observed['source_digest']})
                            page.close()
                # Normal-motion path actually reveals; no-script path remains static.
                for js_enabled, motion in ((True, 'no-preference'), (False, 'reduce')):
                    page = browser.new_page(viewport={'width':1440,'height':1000}, java_script_enabled=js_enabled, reduced_motion=motion)
                    page.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
                    page.goto(f'http://127.0.0.1:{server.server_port}/china.html', wait_until='networkidle')
                    card = page.locator('.pbx-card')
                    card.scroll_into_view_if_needed()
                    if js_enabled:
                        page.wait_for_timeout(2000)
                    paths = card.locator('.ilx-path').evaluate_all('els=>els.map(e=>getComputedStyle(e).strokeDashoffset)')
                    assert paths and all(float(value.replace('px','')) == 0 for value in paths), paths
                    page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    report = {'kind':'actual_built_page_browser_evidence','not_production_deployment':True,
              'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'source_uncommitted_diff':subprocess.check_output(['git','diff','HEAD','--stat','--','templates','scripts','lib'],text=True),
              'html_sha256':page_sha,'page':'site/china.html','observed_asof':observed['asof'],
              'generated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
              'normal_motion_and_no_script':True,
              'images':[{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest()} for p in images]}
    (out/'actual-page-browser-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({'variants_passed':len(checks),'normal_motion_and_no_script':True,
                      'source_digest':observed['source_digest'],'html_sha256':page_sha,'output':str(out)}))


if __name__ == '__main__':
    main()
