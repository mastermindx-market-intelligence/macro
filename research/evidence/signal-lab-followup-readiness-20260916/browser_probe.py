"""Local full-admin browser proof using synthetic data and real source assets.

No production session, credentials, remote API, grading job or notification is used.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    allowed = (ROOT / '.pytest_cache').resolve()
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        parser.error('output must be a new child of this worktree pytest cache')
    output.mkdir(parents=True)
    sys.path.insert(0, str(ROOT))
    from engine import experiments_registry as registry
    from admin import experiments as admin
    from playwright.sync_api import sync_playwright
    today = datetime.now(timezone.utc).date()
    due = (today - timedelta(days=1)).isoformat()
    fixture = output / 'fixture'
    data = fixture / 'data/experiments'
    data.mkdir(parents=True)
    base = {'kind': 'track_record', 'status': 'accruing', 'come_back_on': due,
            'what': 'Synthetic acceptance fixture; not a trading recommendation.',
            'next_step': 'Review the existing dependency. Do not infer validation.'}
    seed = {'audited': today.isoformat(), 'experiments': [
        dict(base, id='due-fixture', name='Review needed', hook='static'),
        dict(base, id='result-fixture', name='Measured null result', hook='track_record',
             storage='data/experiments/calls.jsonl', track_json='data/experiments/result.json'),
        dict(base, id='closed-fixture', name='Concluded research', status='closed', hook='static'),
        dict(base, id='scheduled-fixture', name='Future review', hook='static',
             come_back_on=(today + timedelta(days=7)).isoformat())]}
    (data / 'registry_seed.json').write_text(json.dumps(seed))
    (data / 'calls.jsonl').write_text(json.dumps({'date': due}) + '\n')
    (data / 'result.json').write_text(json.dumps({'verdict': 'null', 'as_of': today.isoformat(),
                                                'horizons': {'21': {'n_matured': 25}}}))
    registry._root = lambda: fixture
    registry._load_machine_registry_entries = lambda: []
    payload = registry.compute()
    manifest = output / 'experiments.json'
    manifest.write_text(json.dumps(payload))
    admin._REGISTRY = manifest
    panel, summary = admin.panel(), admin.alert_summary()
    assets = ROOT / 'admin/static'
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass
        def do_GET(self):
            path = urlparse(self.path).path
            requests.append(('GET', path))
            if path == '/api/experiments':
                body, kind = json.dumps(panel).encode(), 'application/json'
            elif path == '/api/session':
                body, kind = b'{"auth_enabled":false,"authenticated":true,"deployed":false}', 'application/json'
            elif path == '/api/summary':
                body = json.dumps({'meta': {'repo': 'isolated fixture'},
                                   'health': {'healthy': True}, 'services': {'available': False},
                                   'experiments': summary}).encode()
                kind = 'application/json'
            elif path.startswith('/api/'):
                body, kind = b'{"ok":true,"n_pending":0,"open_count":0}', 'application/json'
            elif path in ('/', '/index.html', '/app.js', '/styles.css'):
                name = 'index.html' if path == '/' else path[1:]
                body = (assets / name).read_bytes()
                kind = {'index.html':'text/html', 'app.js':'text/javascript', 'styles.css':'text/css'}[name]
            else:
                self.send_response(204); self.end_headers(); return
            self.send_response(200); self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            requests.append(('POST', self.path))
            self.send_response(405); self.end_headers()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/#experiments'
    rows = []
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True,
                executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
            version = browser.version
            for width in (1440, 390):
                context = browser.new_context(viewport={'width':width, 'height':1000}, color_scheme='dark')
                def restrict(route):
                    target = urlparse(route.request.url)
                    if target.hostname != '127.0.0.1' or route.request.method != 'GET':
                        errors.append('blocked nonfixture request: ' + route.request.method)
                        route.abort()
                    else:
                        route.continue_()
                context.route('**/*', restrict)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url, wait_until='networkidle', timeout=20000)
                page.locator('[data-tab="experiments"]').click()
                page.locator('[data-followup-kind="review_due"]').wait_for(timeout=10000)
                assert page.locator('[data-followup-kind="review_due"]').count() == 1
                assert page.locator('[data-followup-kind="result_ready"]').count() == 1
                assert 'No new result reported' in page.locator('[data-followup-kind="review_due"]').inner_text()
                assert 'No live reader' in page.locator('[data-followup-kind="review_due"]').inner_text()
                assert '2 experiment follow-ups' in page.locator('#hmeta').inner_text()
                assert page.locator('.exp-act-btn').count() == 16
                assert page.locator('.table-wrap .exp-table').count() == 1
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                shot = output / f'admin-experiments-{width}.png'
                page.screenshot(path=str(shot), full_page=True)
                geometry = page.evaluate("""() => {
                    const topbar = document.querySelector('#topbar').getBoundingClientRect();
                    const meta = document.querySelector('#hmeta').getBoundingClientRect();
                    const content = document.querySelector('#view').getBoundingClientRect();
                    return {topbar_bottom:topbar.bottom, meta_bottom:meta.bottom,
                            meta_top:meta.top, topbar_top:topbar.top, content_top:content.top};
                }""")
                assert geometry['meta_bottom'] <= geometry['topbar_bottom'] + 1, geometry
                assert geometry['meta_top'] >= geometry['topbar_top'] - 1, geometry
                rows.append({'width':width, 'result_cards':1, 'due_only_cards':1,
                             'global_horizontal_overflow':overflow, 'header_geometry':geometry, 'screenshot':shot.name,
                             'screenshot_sha256':hashlib.sha256(shot.read_bytes()).hexdigest()})
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    assert not errors, errors
    assert not any(method != 'GET' for method, path in requests)
    assert not any(row['global_horizontal_overflow'] for row in rows)
    proof = {'scope':'isolated full admin app, real assets, synthetic reader fixtures',
             'production_proven':False, 'authenticated_production_access':False,
             'browser':version, 'as_of':today.isoformat(), 'rows':rows,
             'counts':{key:panel[key] for key in ('result_ready_count','review_due_count','attention_count')},
             'errors':errors, 'write_requests':0,
             'inherited_ui_limits':'Admin currently exposes English and dark styles only; no light/ZH capability is claimed.',
             'source_sha256':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                              for path in ('engine/experiment_followup.py','engine/experiments_registry.py',
                                           'admin/experiments.py','admin/static/app.js','admin/static/styles.css')}}
    (output / 'browser-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
