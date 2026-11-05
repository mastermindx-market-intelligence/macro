"""Native early sorting followed by a real deferred window.load, not a renderer call."""
from __future__ import annotations
import argparse, hashlib, json, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('--output-dir')
ap.add_argument('--site-dir')
a = ap.parse_args()
site = Path(a.site_dir) if a.site_dir else ROOT / 'site'
out = Path(a.output_dir) if a.output_dir else Path(__file__).parent / 'browser'
out.mkdir(parents=True, exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(site)))
threading.Thread(target=server.serve_forever, daemon=True).start()
rows = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for route in ['basket/ai_semiconductors.html', 'basket_china/cn_solar.html']:
            for device, width, height in [('desktop',1440,900), ('mobile',390,844)]:
                for lang in ['en', 'zh']:
                    for theme in ['dark', 'light']:
                        label = f'{route.replace("/","-")}-{device}-{lang}-{theme}'
                        page = browser.new_page(viewport={'width':width,'height':height}, has_touch=device=='mobile', is_mobile=device=='mobile', reduced_motion='reduce')
                        errors = []
                        page.on('pageerror', lambda error, errors=errors: errors.append(str(error)))
                        page.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');window.__loadCount=0;window.addEventListener('load',()=>window.__loadCount++);")
                        pending = []
                        page.route('**/__uiux_late_load.svg', lambda request, _source_request, pending=pending: pending.append(request))
                        original = (site / route).read_text()
                        # A single non-data image holds the native load event. All application code and data are the committed page.
                        fixture = original.replace('</body>', '<img src="/__uiux_late_load.svg" alt="" style="width:1px;height:1px;position:absolute;left:-10px">\n</body>')
                        page.route('**/' + route, lambda request, _source_request, fixture=fixture: request.fulfill(status=200, content_type='text/html', body=fixture))
                        response = page.goto(f'http://127.0.0.1:{server.server_port}/{route}', wait_until='domcontentloaded')
                        assert response.status == 200 and len(pending)==1 and page.evaluate('__loadCount')==0, label
                        details = page.locator('details.ftr-anatomy-disclosure')
                        details.locator('summary').click()
                        for _ in range(80):
                            page.keyboard.press('Tab')
                            if page.evaluate('document.activeElement?.dataset.holdSort==="recommend"'):
                                break
                        else:
                            raise AssertionError((label, 'sorting unreachable'))
                        key = 'recommend'
                        if device == 'desktop':
                            page.keyboard.press('Tab')
                            key = 'r20'
                        page.keyboard.press('Enter')
                        button = page.locator(f'#hold button[data-hold-sort="{key}"]')
                        assert button.evaluate('e=>e===document.activeElement'), label
                        old_control = button.element_handle()
                        order = page.locator('#hold tbody .hold-stock .tk').all_text_contents()
                        assert page.locator('#hold').evaluate('t=>t.parentElement.matches(".ts.tbl-scroll")'), label
                        assert page.evaluate('__loadCount') == 0
                        pending[0].fulfill(status=200, content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
                        page.wait_for_function('__loadCount===1')
                        page.wait_for_timeout(50)
                        assert old_control.evaluate('e=>e.isConnected && e===document.activeElement'), (label,'late load stole focus')
                        assert page.locator('#hold tbody .hold-stock .tk').all_text_contents() == order, label
                        assert details.evaluate('e=>e.open'), label
                        assert page.locator('#hold').evaluate('t=>t.closest(".tbl-scroll")===t.parentElement && !t.parentElement.parentElement.closest(".tbl-scroll")'), label
                        page.keyboard.press('Space')
                        assert button.evaluate('e=>e===document.activeElement'), label
                        if device == 'mobile':
                            button.tap()
                            assert button.evaluate('e=>e===document.activeElement'), label
                        before_lang = page.locator('#hold tbody .hold-stock .tk').all_text_contents()
                        page.evaluate('(lang)=>window.setLang(lang)', 'zh' if lang=='en' else 'en')
                        assert button.evaluate('e=>e===document.activeElement'), label
                        assert page.locator('#hold tbody .hold-stock .tk').all_text_contents() == before_lang, label
                        page.evaluate('(lang)=>window.setLang(lang)', lang)
                        overflow = page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
                        assert overflow <= 1 and not errors, (label,overflow,errors)
                        page.screenshot(path=str(out / (label+'.png')))
                        row = {'cell':label, 'fixture':'one delayed non-data image; genuine window.load', 'source_html_sha256':hashlib.sha256(original.encode()).hexdigest(), 'native_sort_key':key, 'same_focused_node_after_load':True, 'order_preserved':True, 'score_open_preserved':True, 'no_nested_scroll_wrapper':True, 'touch_checked':device=='mobile', 'language_focus_preserved':True, 'overflow':overflow, 'page_errors':errors, 'passed':True}
                        rows.append(row)
                        print(json.dumps(row), flush=True)
                        page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    (out/'results.json').write_text(json.dumps({'method':'Native Tab/Enter/Space/touch then real window.load released by a delayed non-data image. No private renderer or shared wrap function called.', 'cases':rows}, indent=2)+'\n')
