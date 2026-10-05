"""Build a self-contained OFFLINE research preview; never deploy or collect data."""
from __future__ import annotations
import argparse,json,sys,hashlib
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,StrictUndefined
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.china_economy import build_economy,extend_snapshot
from engine.china_economy_view import prepare_economy_view
from engine.china_macro_evidence_view import prepare_view
from scripts.preview_china_macro_evidence import evidence_theme_tokens

SHELL='''*{box-sizing:border-box}html{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;--bg:#0f1115;--panel:#181b21;--panel2:#1e222a;--text:#d7dce3;--muted:#8b93a1;--line:#3a4150;--info:#79adfa;--up:#45b873;--down:#e06464;--warn:#e0a030;color-scheme:dark}html[data-theme=light]{--bg:#f7f8fa;--panel:#ffffff;--panel2:#edf0f5;--text:#263244;--muted:#5b687c;--line:#cfd6e0;--info:#2b63b7;--up:#197353;--down:#b13839;--warn:#926313;color-scheme:light}body{margin:0;background:var(--bg);color:var(--text)}button{font-family:inherit;cursor:pointer}html[data-lang=en] .l-zh,html[data-lang=zh] .l-en{display:none}.cnx-dlg{display:none;position:fixed;inset:0;z-index:100;overflow:auto}.cnx-dlg.open{display:block}.cnx-dlg-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.66);backdrop-filter:blur(7px)}.cnx-dlg-panel{position:relative}.cnx-dlg-head{display:flex;justify-content:space-between;align-items:center}.review-header{border-bottom:1px solid var(--line);background:var(--panel);padding:15px max(24px,calc((100vw - 1184px)/2));display:flex;align-items:center;justify-content:space-between;gap:18px}.review-brand{font-size:12px;letter-spacing:.14em;font-weight:700}.review-brand small{font-size:10px;color:var(--muted);letter-spacing:.03em;font-weight:450;margin-left:13px}.review-actions{display:flex;gap:7px;align-items:center}.review-actions button{background:var(--panel2);color:var(--text);font-size:10px;min-height:36px;border:1px solid var(--line);border-radius:6px;padding:6px 10px}.review-banner{margin:0 auto;max-width:1184px;padding:13px 0 0;color:var(--muted);font-size:10px;line-height:1.6}.review-banner strong{color:var(--warn);font-weight:600}.review-existing{max-width:1184px;margin:0 auto 38px;border-top:1px solid var(--line);padding:24px 0}.review-existing p{font-size:12px;color:var(--muted)}.review-existing nav{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.review-existing nav button{border:1px solid var(--line);padding:16px;border-radius:8px;text-align:left;background:var(--panel);color:var(--text);font-size:12px}.review-footer{max-width:1184px;margin:0 auto;padding:0 0 25px;font-size:10px;color:var(--muted);line-height:1.8}@media(max-width:1240px){.review-banner,.review-existing,.review-footer{margin-left:24px;margin-right:24px}}@media(max-width:650px){.review-header{padding:14px 15px}.review-brand small{display:block;margin:4px 0}.review-actions{gap:4px}.review-actions button{font-size:9px;padding:6px}.review-existing nav{grid-template-columns:1fr 1fr}.review-banner,.review-existing,.review-footer{margin-left:15px;margin-right:15px}}'''
HTML='''<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><title>China economy — state, direction and pace</title><style>{{ shell|safe }}{{ old_css|safe }}{{ css|safe }}</style></head><body class="page-china">
{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}
<header class="review-header"><div class="review-brand">MASTERMIND <small>{{ t('ECONOMIC INTELLIGENCE','经济情报') }}</small></div><div class="review-actions"><button type="button" onclick="document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark'">{{ t('Light / dark','明亮 / 深色') }}</button><button type="button" onclick="EconomyLens.setLanguage(document.documentElement.dataset.lang==='en'?'zh':'en')">EN / 中文</button><button type="button" id="eco-export-json">JSON ↓</button></div></header>
<p class="review-banner"><strong>{{ t('RESEARCH BUILD','研究预览') }}</strong> · {{ t('Source-checked public observations; not a live feed or a production release. No invented history.','公开来源核验观测；不是实时数据或生产版本。不虚构历史。') }}</p>
<main>{% import '_china_economy_lens.html.j2' as economy with context %}{{ economy.lens(E, title_level=1) }}
<section class="review-existing"><p>{{ t('Your four detailed macro panels are preserved.','保留原有四个宏观详细面板。') }}</p><nav>{% for key in ['policy','property','flows','sentiment'] %}<button type="button" onclick="cnxOpenDlg('cnx-dlg-{{ key }}')">{{ t(base.panels[key].title_en,base.panels[key].title_zh) }} ↗</button>{% endfor %}</nav></section></main>
{% import '_china_macro_evidence.html.j2' as evidence with context %}{% for key in ['policy','property','flows','sentiment'] %}{{ evidence.panel(base,key,leaderboard_data=none) }}{% endfor %}
<footer class="review-footer">{{ t('Method: fixed-domain descriptive breadth; explicit level, direction and rate-of-change units. No GDP nowcast, causal guarantee or new trading authority.','方法：固定领域描述性广度；明确区分水平、方向与变化速度。不提供GDP预测、因果保证或新增交易权限。') }}<br>{{ t('Charts and interface behavior need production-browser review before release.','发布前须完成生产浏览器图表及交互审查。') }}</footer>
<noscript><p class="review-banner">JavaScript is disabled. The overview and default chart remain visible; interactive selection and exports are unavailable.</p></noscript>
<script type="application/json" id="eco-json">{{ publication_json|safe }}</script>
<script>function cnxOpenDlg(id){document.querySelectorAll('.cnx-dlg.open').forEach(e=>e.classList.remove('open'));const e=document.getElementById(id);if(e){e.classList.add('open');document.body.style.overflow='hidden';history.replaceState(null,'','#'+id);}}function cnxCloseDlg(){document.querySelectorAll('.cnx-dlg.open').forEach(e=>e.classList.remove('open'));document.body.style.overflow='';history.replaceState(null,'',location.pathname);}</script><script>{{ old_js|safe }}</script><script>{{ js|safe }}</script></body></html>'''


def render(document:dict,base:dict,destination:Path)->Path:
 destination.mkdir(parents=True,exist_ok=True)
 economy=build_economy(document);publication=extend_snapshot(base,economy)
 safe_json=json.dumps(publication,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
 env=Environment(loader=FileSystemLoader(ROOT/'templates'),undefined=StrictUndefined,autoescape=True)
 from engine.i18n import t_pctile
 env.globals["t_pctile"]=t_pctile
 html=env.from_string(HTML).render(E=prepare_economy_view(economy),base=prepare_view(base),shell=SHELL+evidence_theme_tokens(),
  old_css=(ROOT/'templates/china-macro-evidence.css').read_text(),css=(ROOT/'templates/china-economy.css').read_text(),
  old_js=(ROOT/'templates/china-macro-evidence.js').read_text(),js=(ROOT/'templates/china-economy.js').read_text(),publication_json=safe_json)
 (destination/'index.html').write_text(html)
 (destination/'china_economy_evidence.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2,allow_nan=False))
 return destination/'index.html'

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 print(render(json.loads(args.inputs.read_text()),json.loads(args.base.read_text()),args.output))
