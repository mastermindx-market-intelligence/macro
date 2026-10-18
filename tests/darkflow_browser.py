"""Exercise the real Dark Flow component with source-backed and typed fault inputs.

This anonymous component harness stays outside site/. It is not an authenticated
production-page proof. Production navigation is verified separately after delivery.
No remote requests, model calls, credential reads, or production writes.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def render(output: Path, source: Path) -> dict:
    from jinja2 import Environment, FileSystemLoader
    if output.resolve() == ROOT or ROOT in output.resolve().parents:
        raise ValueError('Browser fixtures must stay outside the source repository')
    output.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for name in ['darkflow_latest.json', 'darkflow_history.json']:
        raw = (source / name).read_bytes()
        inputs[name] = hashlib.sha256(raw).hexdigest()
        (output / name).write_bytes(raw)
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    for compact, name in [(False, 'darkflow-component.html'), (True, 'darkflow-compact.html')]:
        fragment = env.get_template('_darkflow_panel.html.j2').render(df_compact=compact)
        html = ('<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head>'
                '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Dark Flow anonymous component verification</title><link rel="stylesheet" href="darkflow.css">'
                '<style>body{margin:0;padding:16px;background:#0f1115}main{max-width:1360px;margin:auto}'
                '.l-zh{display:none}html[data-lang="zh"] .l-en{display:none}'
                'html[data-lang="zh"] .l-zh{display:inline}'
                'html[data-theme="light"] body{background:#f7f8fa}</style>'
                '<script defer src="darkflow.js"></script></head><body><main>' + fragment + '</main></body></html>')
        (output / name).write_text(html)
    for name in ['darkflow.js', 'darkflow.css']:
        shutil.copy2(ROOT / 'templates' / name, output / name)
        inputs['templates/' + name] = hashlib.sha256((ROOT / 'templates' / name).read_bytes()).hexdigest()
    vol = subprocess.check_output(['git', 'show', 'HEAD:site/basketdata/vol_weather.json'], cwd=ROOT)
    (output / 'basketdata').mkdir(exist_ok=True)
    (output / 'basketdata/vol_weather.json').write_bytes(vol)
    inputs['vol_weather.json'] = hashlib.sha256(vol).hexdigest()
    inputs['templates/_darkflow_panel.html.j2'] = hashlib.sha256((ROOT / 'templates/_darkflow_panel.html.j2').read_bytes()).hexdigest()
    return inputs


def check(output: Path) -> dict:
    from playwright.sync_api import sync_playwright
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(output)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    checks, errors, shots = [], [], []
    payload = json.loads((output / 'darkflow_latest.json').read_text())
    expected = f"{payload['display']['reading']['value']:.2f}"
    def record(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            for width in [390, 1440]:
                for theme in ['dark', 'light']:
                    for lang in ['en', 'zh']:
                        context = browser.new_context(viewport={'width':width, 'height':900})
                        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(origin + '/darkflow-component.html')
                        page.locator('[data-df="value"]').filter(has_text=expected).wait_for()
                        page.evaluate('([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang}', [theme,lang])
                        page.locator('[data-df="history-chart"] svg').wait_for()
                        page.locator('[data-df="volatility"] > div').first.wait_for()
                        record(f'{width}-{theme}-{lang}: no page overflow', page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                        record(f'{width}-{theme}-{lang}: correct dated ratio', page.locator('[data-df="asof"]').inner_text()==payload['display']['asof'])
                        page.locator('[data-df="sector"]').select_option('Information Technology')
                        page.locator('[data-df="range"]').select_option('63')
                        chart = page.locator('[data-df="history-chart"] svg')
                        before = chart.get_attribute('aria-label')
                        chart.focus(); page.keyboard.press('ArrowLeft')
                        record(f'{width}-{theme}-{lang}: keyboard chart inspection', chart.get_attribute('aria-label')!=before)
                        page.locator('.df-names > summary').click()
                        page.locator('[data-df="search"]').fill('NVDA')
                        record(f'{width}-{theme}-{lang}: constituent drilldown', page.locator('[data-df="names"] a').first.get_attribute('href')=='stock.html?t=NVDA')
                        record(f'{width}-{theme}-{lang}: independent volatility dates', payload['display']['asof'] in page.locator('[data-df="volatility-status"]').inner_text())
                        page.locator('[data-df="sector"]').select_option('__market__')
                        name=f'darkflow-{width}-{theme}-{lang}.png'
                        page.locator('#dark-flow').screenshot(path=str(output/name), animations='disabled')
                        shots.append(name)
                        context.close()
            # The compact Macro consumer must not pull history/volatility until opened.
            context=browser.new_context(viewport={'width':390,'height':844})
            page=context.new_page(); requests=[]
            page.on('request',lambda request: requests.append(request.url))
            page.goto(origin+'/darkflow-compact.html')
            page.locator('[data-df="value"]').filter(has_text=expected).wait_for()
            record('compact: history deferred',not any('darkflow_history' in u for u in requests))
            record('compact: volatility deferred',not any('vol_weather' in u for u in requests))
            page.locator('[data-df="explore"] > summary').click()
            page.locator('[data-df="history-chart"] svg').wait_for()
            record('compact: expanded history loads',any('darkflow_history' in u for u in requests))
            context.close()
            # Synthetic fault checks, not market observations or screenshot evidence.
            for case in ['http_failure','generation_mismatch','future_clock','authority_escalation','string_number','observed_zero']:
                context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page()
                changed=copy.deepcopy(payload)
                if case=='future_clock': changed['known_at']='2099-01-01T00:00:00Z'
                if case=='authority_escalation': changed['trade_authority']=True
                if case=='string_number': changed['display']['reading']['value']='42'
                if case=='observed_zero': changed['display']['reading']['value']=0
                if case=='http_failure':
                    context.route('**/darkflow_latest.json',lambda route:route.fulfill(status=503,body='unavailable'))
                else:
                    context.route('**/darkflow_latest.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(changed)))
                if case=='generation_mismatch':
                    h=json.loads((output/'darkflow_history.json').read_text());h['generation']='0'*64
                    context.route('**/darkflow_history.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(h)))
                page.goto(origin+'/darkflow-component.html')
                if case=='observed_zero':
                    page.locator('[data-df="value"]').filter(has_text='0.00').wait_for()
                    record(case+': zero not missing',page.locator('[data-df="body"]').is_visible())
                elif case=='generation_mismatch':
                    page.locator('[data-df="history-retry"]').wait_for(state='visible')
                    record(case+': dated summary retained',page.locator('[data-df="value"]').inner_text()==expected)
                else:
                    page.locator('[data-df="retry"]').wait_for(state='visible')
                    record(case+': no fabricated reading',page.locator('#dark-flow').get_attribute('data-state')=='error')
                context.close()
            browser.close()
        record('no component JavaScript exceptions',not errors)
        return {'state':'PASS','checks':checks,'page_errors':errors,'screenshots':shots,
                'source_backed_visuals':True,'synthetic_fault_checks':True,'production_acceptance':False}
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    inputs=render(args.output,args.source)
    result=check(args.output)
    result['inputs']=inputs
    (args.output/'browser-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'state':result['state'],'checks':len(result['checks']),'page_errors':result['page_errors'],'receipt':str(args.output/'browser-result.json')}))


if __name__=='__main__':
    main()
