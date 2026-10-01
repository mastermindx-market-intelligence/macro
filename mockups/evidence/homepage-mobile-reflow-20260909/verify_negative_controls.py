"""Reproduce both H1 width defects without modifying source or production."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
from verify_mobile import ROOT, OUT, QuietHandler, ThreadingHTTPServer

BASELINE = 'a4d33f32dad140acdfa081b21f55ad6d8dcb94d4'
FOOTER_PROBE = ('\n@media(max-width:680px){.f-cols{display:grid;'
    'grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gutter);'
    'width:100%;min-width:0}.f-col{min-width:0}.f-col a{overflow-wrap:anywhere}}')

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default=BASELINE)
    args = parser.parse_args()
    baseline = subprocess.check_output(['git', 'show', f'{args.baseline_ref}:site/landing.css'], cwd=ROOT, text=True)
    patched = (ROOT / 'site/landing.css').read_text()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'site')))
    Thread(target=server.serve_forever, daemon=True).start()
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for name, css in [('baseline', baseline), ('footer-only', baseline + FOOTER_PROBE), ('complete-fix', patched)]:
                    context = browser.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce')
                    try:
                        context.add_init_script("localStorage.setItem('lang','en');localStorage.setItem('theme','light')")
                        page = context.new_page()
                        # One-argument callback: the optional request argument must not replace CSS.
                        def inject(route):
                            route.fulfill(status=200, content_type='text/css', body=css)
                        page.route('**/landing.css*', inject)
                        page.goto(f'http://127.0.0.1:{server.server_port}/index.html?still', wait_until='domcontentloaded')
                        page.wait_for_timeout(900)
                        for width in (390, 320):
                            page.set_viewport_size({'width':width,'height':844})
                            page.wait_for_timeout(100)
                            row = page.evaluate('() => ({viewport:innerWidth, document:document.documentElement.scrollWidth})')
                            row.update(case=name, css_sha256=hashlib.sha256(css.encode()).hexdigest())
                            rows.append(row)
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    widths = {(r['case'],r['viewport']):r['document'] for r in rows}
    checks = {
        'baseline_reproduces_390_overflow': widths['baseline',390] > 390,
        'footer_only_fixes_390': widths['footer-only',390] <= 390,
        'footer_only_still_fails_320': widths['footer-only',320] > 320,
        'complete_fix_fits_both': all(widths['complete-fix',w] <= w for w in (390,320)),
    }
    report = {'observed_at':datetime.now(timezone.utc).isoformat(),
        'baseline_ref':args.baseline_ref, 'passed':all(checks.values()),
        'scope':'Local browser CSS substitution only; no source or production mutation.',
        'checks':checks, 'cases':rows}
    (OUT / 'negative-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
