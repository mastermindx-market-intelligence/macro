"""Bounded real-browser regression; no account, mutation, or production claims."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
WIDTHS = (320, 360, 390, 430, 768, 1440)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='')
    parser.add_argument('--output', default=str(OUT / 'browser-regression.json'))
    args = parser.parse_args()
    server = None
    base = args.base_url.rstrip('/')
    if not base:
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'site')))
        Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
    rows, failures = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for locale in ('en', 'zh'):
                    for theme in ('light', 'dark'):
                        context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
                        context.add_init_script(f"localStorage.setItem('lang', {json.dumps(locale)});localStorage.setItem('theme', {json.dumps(theme)});localStorage.removeItem('themeAuto');")
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(base + '/index.html?still', wait_until='domcontentloaded', timeout=35000)
                        page.wait_for_timeout(1200)
                        for width in WIDTHS:
                            page.set_viewport_size({'width': width, 'height': 900 if width > 700 else 844})
                            page.wait_for_timeout(120)
                            row = page.evaluate('''() => ({width:innerWidth, document:document.documentElement.scrollWidth,
                              lang:document.documentElement.getAttribute('data-lang'),theme:document.documentElement.getAttribute('data-theme'),
                              links:[...document.querySelectorAll('footer a')].map(e=>({text:e.innerText,href:e.getAttribute('href'),x:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})),
                              labels:[...document.querySelectorAll('.sit .early')].map(e=>({text:e.innerText,width:e.getBoundingClientRect().width,scroll:e.scrollWidth,right:e.getBoundingClientRect().right}))})''')
                            row.update(locale_requested=locale, theme_requested=theme, errors=list(errors))
                            row['passed'] = row['document'] <= width and row['lang'] == locale and not errors and len(row['links']) >= 10 and all(link['x'] >= -1 and link['right'] <= width + 1 for link in row['links']) and all(label['right'] <= width + 1 and label['scroll'] <= label['width'] + 1 for label in row['labels'])
                            rows.append(row)
                            if not row['passed']:
                                failures.append({'locale': locale, 'theme': theme, 'width': width, 'document': row['document'], 'errors': errors})
                        if locale == 'en' and theme == 'light':
                            page.set_viewport_size({'width':320,'height':844})
                            for selector, name in (('footer','footer-320.png'),('#f-sits','situations-320.png')):
                                page.locator(selector).screenshot(path=str(OUT / name))
                        context.close()
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'base_url': base, 'scope': 'anonymous layout only; no account or revenue result', 'passed': not failures, 'cases': rows, 'failures': failures}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': report['passed'], 'cases': len(rows), 'failures': failures}, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == '__main__':
    raise SystemExit(main())
