"""Qualify one China registry correction through the existing Signal Lab builder.

Writes only operation-owned evidence outputs. No China rebuild, data refresh,
model retune or production publication. Browser captures follow all gestures.
"""
from pathlib import Path
import ast, copy, functools, hashlib, http.server, json, os, subprocess, threading
from datetime import datetime, timezone
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright, expect
from engine import signal_lab, i18n
from scripts import build_site

ROOT = Path.cwd()
OUT = Path(os.environ['CHINA_SIGNAL_LAB_PROOF'])
BASE = '6c8786bc9fe29a58448a05a9aebca03e448f9fe3'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
TARGET = 'China external-driver radar'
PROTECTED = ['site/china.html', 'site/signal_lab.html', 'site/factordata/signal_lab.json',
    'data/china_regime/latest.json', 'data/china_market_state/latest.json',
    'data/risk_radar_intl/cn_forward_log.jsonl', 'data/risk_radar_intl/hk_forward_log.jsonl',
    'data/risk_radar_intl/ca_forward_log.jsonl', 'data/risk_radar/scorecard.json',
    'engine/risk_radar_intl.py', 'engine/risk_radar_intl_audit.py',
    'engine/risk_radar_intl_evidence.py', 'engine/neuralweb/constitution.py']

def digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def target(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == '_row' and node.args and isinstance(node.args[0], ast.Constant)
            and str(node.args[0].value).startswith(TARGET))

old = ast.parse(subprocess.check_output(['git', 'show', BASE + ':engine/signal_lab.py'], text=True))
new = ast.parse((ROOT / 'engine/signal_lab.py').read_text())
old_row = next(n for n in ast.walk(old) if target(n))
new_row = next(n for n in ast.walk(new) if target(n))
assert ast.dump(ast.Tuple(elts=old_row.args), include_attributes=False) == ast.dump(ast.Tuple(elts=new_row.args), include_attributes=False)
old_kw = {k.arg: ast.dump(k.value, include_attributes=False) for k in old_row.keywords}
new_kw = {k.arg: ast.dump(k.value, include_attributes=False) for k in new_row.keywords}
changed = sorted(k for k in set(old_kw) | set(new_kw) if old_kw.get(k) != new_kw.get(k))
assert changed == ['extra', 'horizon', 'source', 'why', 'why_zh', 'wired']
class RestoreOnlyTheNote(ast.NodeTransformer):
    def visit_Call(self, node):
        return copy.deepcopy(old_row) if target(node) else self.generic_visit(node)
assert ast.dump(RestoreOnlyTheNote().visit(new), include_attributes=False) == ast.dump(old, include_attributes=False)

assert not (OUT / 'build/signal_lab.html').exists(), 'prior build exists; reconcile before rerunning'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'build').mkdir(exist_ok=True)
before = {p: digest(ROOT / p) for p in PROTECTED}
registry_before = copy.deepcopy(signal_lab.REGISTRY)
env = Environment(loader=FileSystemLoader(ROOT / 'templates'))
env.filters['min'] = lambda seq: min(seq)
env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
build_site.build_signal_lab_page(env, OUT / 'build', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))
assert signal_lab.REGISTRY == registry_before
payload = json.loads((OUT / 'build/factordata/signal_lab.json').read_text())
rows = [r for tier in payload['tiers'] for r in tier['rows']]
row = next(r for r in rows if r['name'].startswith(TARGET))
assert row['tier'] == 'display' and row['n'] is None and row['hit'] is None
assert '1.63×' in row['why'] and '2.64×' in row['why']
assert 'CSI300-confirmed' not in str(row) and '2.07×' not in str(row)
assert before == {p: digest(ROOT / p) for p in PROTECTED}
receipt = {'source_base': BASE, 'source_sha256': digest(ROOT / 'engine/signal_lab.py'),
    'changed_literal_fields': changed, 'other_code_and_rows_unchanged': True,
    'builder': 'scripts.build_site.build_signal_lab_page', 'builder_succeeded': True,
    'html_sha256': digest(OUT / 'build/signal_lab.html'), 'registry_count': len(rows),
    'machine_row': row, 'protected_sha256': before, 'browser': [],
    'production': False, 'fresh_collection': False, 'new_calibration': False}
(OUT / 'qualification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def translate_path(self, path):
        route = urlsplit(path).path
        if route in ('/signal_lab.html', '/factordata/signal_lab.json'):
            return str(OUT / 'build' / route.lstrip('/'))
        return super().translate_path(path)

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(Handler, directory=str(ROOT / 'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f'http://127.0.0.1:{server.server_address[1]}'
row_id = 'sig-' + row['slug']
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for width in (1440, 390):
                for theme in ('dark', 'light'):
                    for lang in ('en', 'zh'):
                        context = browser.new_context(viewport={'width': width, 'height': 1000},
                            is_mobile=width == 390, has_touch=width == 390, device_scale_factor=1)
                        page = context.new_page(); page.set_default_timeout(10000)
                        errors, responses = [], []
                        page.on('pageerror', lambda err: errors.append(str(err)))
                        page.on('response', lambda res: responses.append(res.url) if res.status >= 400 else None)
                        page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                        page.goto(base_url+'/signal_lab.html', wait_until='networkidle')
                        page.locator('#slq').fill(TARGET)
                        selected = page.locator('#'+row_id)
                        expect(selected).to_be_visible()
                        button = selected.locator('.row-expand-btn')
                        detail = page.locator('#'+row_id+'-detail')
                        button.click(); expect(detail).to_be_visible()
                        visible = detail.locator('.why-full.l-'+lang)
                        expect(visible).to_be_visible()
                        expect(detail.locator('.why-full.l-'+('zh' if lang=='en' else 'en'))).not_to_be_visible()
                        text = visible.inner_text()
                        for item in ('1.63×', '2.64×', '18', '50%'): assert item in text
                        assert ('not independent confirmations' if lang=='en' else '不是独立的多重确认') in text
                        assert ('cash-index replication is unavailable' if lang=='en' else '现货指数复核暂不可用') in text
                        button.click(); expect(detail).not_to_be_visible()
                        button.click(); expect(detail).to_be_visible()
                        detail.scroll_into_view_if_needed()
                        overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                        touch = page.evaluate('navigator.maxTouchPoints > 0')
                        assert touch == (width == 390)
                        result = {'width': width, 'theme': theme, 'lang': lang,
                            'open_close_reopen': True, 'visible_claims': text,
                            'document_overflow': overflow, 'page_errors': errors,
                            'bad_responses': responses, 'touch_preserved_before_capture': touch}
                        screenshot = OUT / f'{width}-{theme}-{lang}.png'
                        page.screenshot(path=str(screenshot))  # observation only, after all gestures
                        result.update(screenshot=screenshot.name, screenshot_sha256=digest(screenshot))
                        receipt['browser'].append(result)
                        context.close()
                        assert not errors and not responses and not overflow, result
        finally:
            browser.close()
    receipt['browser_accepted'] = len(receipt['browser']) == 8
except BaseException as exc:
    receipt['browser_failure'] = f'{type(exc).__name__}: {exc}'
    raise
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
    receipt['protected_preserved'] = before == {p: digest(ROOT / p) for p in PROTECTED}
    receipt['build_unchanged'] = receipt['html_sha256'] == digest(OUT / 'build/signal_lab.html')
    (OUT / 'qualification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
assert receipt['protected_preserved'] and receipt['build_unchanged']
print(json.dumps({'builder': True, 'journeys': len(receipt['browser']),
    'protected_paths': len(before), 'browser_accepted': receipt['browser_accepted'],
    'other_registry_code_unchanged': True, 'production': False}))
