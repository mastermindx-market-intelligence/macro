"""Render an offline synthetic quote-block fixture from the actual source files.

No provider data, site fetch, credentials or remote assets. The real controller's
single fetch is replaced by an in-memory response; CSP denies all connections.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(sys.argv[1]).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
template = (ROOT / 'templates/ticker.html.j2').read_text()
start = template.index('<div class="px-block hi hi2">')
depth = 0
for match in re.finditer(r'</?div\b[^>]*>', template[start:]):
    depth += -1 if match.group().startswith('</') else 1
    if depth == 0:
        block = template[start:start + match.end()]
        break
macro = template[:template.index('{% set nav_prefix')]
markup = Environment(autoescape=True).from_string(macro + block).render(
    ticker='NVDA', hero={'price':'100.00','chg':{'pos':True,'abs':'+$10.00','pct':'+11.11%'}})
css = re.search(r'<style>(.*?)</style>', template, re.S).group(1)
theme = (ROOT / 'templates/theme.css').read_text()
theme = re.sub(r'@import[^;]+;', '', theme)
theme = re.sub(r'@font-face\{[^}]+\}', '', theme)
controller = (ROOT / 'site/assets/js/dossier-live-quote.js').read_text()
now = 1792756800000
payload = {'ticker':'NVDA','price':100,'change_abs':10,'change_pct':100/9,
    'session':'pre','freshness':'delayed','regular_session_date':'2026-10-22',
    'extended_quote':{'price':99,'currency':'USD','change_abs':-1,'change_pct':-1,
        'completed_regular_reference':{'price':100,'session_date':'2026-10-22'},
        'print_session':'pre','market_session':'pre','freshness':'live',
        'as_of_ms':now-1000.25,'valid_until_ms':now+118000}}
setup = f'''var fixtureNow={now}; Date.now=function(){{return fixtureNow;}};
var fixturePacket={json.dumps(payload)};
var fixtureState=new URLSearchParams(location.search).get('state');
if(fixtureState==='unavailable') fixturePacket.extended_quote=null;
if(fixtureState==='expired') {{ fixturePacket.extended_quote.valid_until_ms=fixtureNow+300;
setTimeout(function(){{fixtureNow={now}+300;}},100); }}
window.fetch=function(){{return Promise.resolve({{ok:true,json:function(){{return Promise.resolve(fixturePacket);}}}});}};
'''
html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; img-src data:; font-src 'none'">
<title>Dossier quote — offline synthetic source fixture</title><style>''' + theme + css + '''</style></head><body>
<main class="page-wrap"><section class="hero"><div class="hero-grid"><div><div class="eyebrow">OFFLINE SYNTHETIC FIXTURE</div>
<h1>NVDA</h1><p class="hero-desc"><span class="l-en">Regular close and a separately dated pre-market reading.</span><span class="l-zh">常规时段收盘与独立标注时间的盘前报价。</span></p></div>''' + markup + '''</div></section></main>
<script>''' + setup + controller + '''</script></body></html>'''
(OUTPUT / 'quote.html').write_text(html)
inputs = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
    ['templates/ticker.html.j2','templates/theme.css','site/assets/js/dossier-live-quote.js']}
(OUTPUT/'fixture-source.json').write_text(json.dumps({'synthetic':True,'network':'CSP denies connect-src; in-memory fetch only','clock':'frozen synthetic observation, not real market time','inputs':inputs,'html_sha256':hashlib.sha256(html.encode()).hexdigest()},indent=2)+'\n')
print(OUTPUT / 'quote.html')
