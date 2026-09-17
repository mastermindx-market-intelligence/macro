"""Local browser proof; fixture live ticks are not production or natural-event proof."""
import copy, functools, hashlib, http.server, json, pickle, subprocess, sys, threading
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT = Path.cwd(); sys.path.insert(0, str(ROOT))
from lib.risk_presentation import market_read
OUT = ROOT / ('mockups/refs/us-risk-integrity/' + (sys.argv[1] if len(sys.argv)>1 else 'r7')); OUT.mkdir(parents=True, exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
base = 'http://127.0.0.1:' + str(server.server_port)
with (ROOT / 'data/_dev_macro_vm.pkl').open('rb') as f:
    vm = pickle.load(f)['vm']
ms = vm['market_state']; projection = ms['presentation']; rows = []; failures = []
source = (ROOT / 'templates/risk_state_live.js').read_text()
source = source[:source.index('  if (document.readyState')] + '\nwindow.__riskProof = {patch:patchMacro};})();'
def route(request):
    u = urlsplit(request.request.url)
    if u.hostname not in ('127.0.0.1', 'localhost') or '/live/' in u.path:
        request.abort()
    else:
        request.continue_()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width in (1440, 390):
            for theme in ('dark', 'light'):
                for lang in ('en', 'zh'):
                    key = f'{width}-{theme}-{lang}'
                    context = browser.new_context(viewport={'width': width, 'height': 1100}, device_scale_factor=1)
                    context.route('**/*', route)
                    context.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.removeItem("themeAuto");localStorage.setItem("lang",'+json.dumps(lang)+');')
                    page = context.new_page(); page.goto(base + '/macro.html', wait_until='load')
                    page.wait_for_timeout(500)
                    row = {'case': key, 'kind': 'canonical_local_render', 'errors': []}
                    word = page.locator('.mx5-verdict-word'); score = page.locator('.mx5-big-score')
                    row.update(label=word.inner_text(), score=score.inner_text(), headline=page.locator('.mx5-thesis').inner_text(), old_panel_count=page.locator('#risk-envelope-band').count())
                    row['geometry'] = word.bounding_box()
                    panel = page.locator('.mx5-sc-left').bounding_box()
                    row['panel_geometry'] = panel
                    if row['geometry'] and panel and row['geometry']['x'] + row['geometry']['width'] > panel['x'] + panel['width'] + 1: row['errors'].append('qualified label escapes its own score panel')
                    row['settled_aria'] = page.locator('.mx5-gauge-svg').get_attribute('aria-label')
                    if projection['label_'+lang] not in (row['settled_aria'] or ''): row['errors'].append('settled accessible label loses qualification')
                    row['label_color'] = word.evaluate('(e)=>getComputedStyle(e).color')
                    row['score_color'] = score.evaluate('(e)=>getComputedStyle(e).color')
                    if projection['label_'+lang] not in row['label']: row['errors'].append('wrong translated label')
                    if row['score'] != str(ms['score']): row['errors'].append('changed numeric score')
                    if row['geometry'] and row['geometry']['x'] + row['geometry']['width'] > width + 2: row['errors'].append('qualified label overflows viewport')
                    if projection['qualified'] and row['label_color'] == row['score_color']: row['errors'].append('qualification inherits supportive score colour')
                    page.locator('.mx5-sc-left').screenshot(path=str(OUT / (key+'.png')))
                    page.add_script_tag(content=source)
                    feed = {'schema':'risk_state.v1','built':ms['asof']+' 23:59:00 UTC','nightly_asof':ms['asof'],'live_active':False,'stale':False,'display':dict(ms),'nightly':dict(ms)}
                    flip = page.locator('.mx5-flip'); before = flip.first.evaluate('(e)=>e.style.display') if flip.count() else None
                    page.evaluate('(d)=>window.__riskProof.patch(d)', feed)
                    after = flip.first.evaluate('(e)=>e.style.display') if flip.count() else None
                    row['same_verdict_flip'] = {'before':before, 'after':after}
                    if before != after: row['errors'].append('same measured verdict hides existing flip explanation')
                    capped = copy.deepcopy(ms)
                    capped.update(verdict='MIXED', label_en='Mixed', label_zh='混合', score=50, raw_score=61, capped=True, score_source='radar_ceiling')
                    capped['presentation'] = market_read(capped)
                    feed.update(display=capped, nightly=capped)
                    page.evaluate('(d)=>window.__riskProof.patch(d)', feed)
                    row['fixture_capped_subline'] = page.locator('.mx5-sub-line').inner_text()
                    row['fixture_capped_aria'] = page.locator('.mx5-gauge-svg').get_attribute('aria-label')
                    if 'Measured blend 50' in (row['fixture_capped_aria'] or ''): row['errors'].append('accessibility calls cap the measured blend')
                    if '61' not in row['fixture_capped_subline']: row['errors'].append('cap loses original blend provenance')
                    if page.locator('.mx5-big-score').inner_text() != '50': row['errors'].append('live score not updated')
                    rows.append(row)
                    failures.extend(key+': '+e for e in row['errors'])
                    context.close()
        browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=3)
receipt = {'status':'PASS' if not failures else 'FAIL', 'utc':datetime.now(timezone.utc).isoformat(), 'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'page_sha256':hashlib.sha256((ROOT/'site/macro.html').read_bytes()).hexdigest(), 'production_proof':False, 'full_program_acceptance':False, 'external_requests_blocked':True, 'fixture_live_ticks':True, 'body_character_keystrokes':0, 'tab_discovery':0, 'cases':rows, 'failures':failures}
receipt['source_sha256'] = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['lib/risk_presentation.py','templates/dashboard.html.j2','templates/_market_read.html.j2','templates/risk_state_live.js','site/risk_state_live.js']}
receipt['render_basis'] = 'unchanged real VM; canonical renderer/writer; byte-equivalence to full builder established before frontend-only repair'
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':receipt['status'],'cases':len(rows),'failures':failures,'receipt':str(OUT/'receipt.json')},ensure_ascii=False),flush=True)
sys.exit(bool(failures))
