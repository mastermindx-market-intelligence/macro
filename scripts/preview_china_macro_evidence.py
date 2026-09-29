"""Build an offline review preview, NOT a production replacement or a data backfill.

Real mode uses public NBS releases plus latest values verified in the source audit.
It deliberately does not invent unavailable historical samples or percentile ranks.
Synthetic mode exists only for browser interaction/regression tests, visibly labeled.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.china_macro_evidence import build_snapshot, STATUS
from engine.china_macro_evidence_view import prepare_view
from engine.china_connect_leaderboard import normalize

ASOF = date(2026,9,29)
SOURCE_PIN = '650e2ebbe08046bedf10e7eec39def3f62073103'


def real_snapshot():
    # Official reference-month series. Percentages are published YTD YoY, not
    # derived monthly growth. These copied public facts are REVIEW input only.
    months = ['2026-03-01','2026-04-01','2026-05-01','2026-06-01','2026-07-01','2026-08-01']
    source_urls = [
        'https://www.stats.gov.cn/sj/zxfb/202604/t20260416_1963327.html',
        'https://www.stats.gov.cn/sj/zxfb/202605/t20260518_1963729.html',
        'https://www.stats.gov.cn/sj/zxfb/202606/t20260616_1963950.html',
        'https://www.stats.gov.cn/sj/zxfbhjd/202607/t20260715_1964126.html',
        'https://www.stats.gov.cn/zwfwck/sjfb/202608/t20260817_1965053.html',
        'https://www.stats.gov.cn/sj/zxfb/202609/t20260915_1965310.html']
    activity=pd.DataFrame({
        'investment_ytd_yoy':[-11.2,-13.7,-16.2,-18.0,-19.2,-19.9],
        'starts_ytd_yoy':[-20.3,-22.0,-22.6,-23.4,-24.0,-24.8],
        'completions_ytd_yoy':[-25.0,-24.0,-23.4,-23.7,-23.2,-23.7],
        'sales_area_ytd_yoy':[-10.4,-10.2,-10.8,-11.6,-11.8,-12.1],
        'sales_value_ytd_yoy':[-16.7,-14.6,-13.5,-13.6,-13.1,-13.0],
        'resale_area_ytd_yoy':[None,None,None,None,None,10.6],
        'funds_ytd_yoy':[None,None,-19.0,-20.2,None,-21.0],
        'domestic_loans_ytd_yoy':[None,None,-28.7,-31.7,None,-33.3],
        'mortgages_ytd_yoy':[None,None,-28.0,-24.9,None,-22.4],
        'deposits_ytd_yoy':[None,None,-16.1,-15.8,None,-14.8],
        'inventory_stock_yoy':[None,None,-.4,-.9,-.8,-1.1],
        'source_url':source_urls,
        # Reference dates and publication dates are separate. Earlier observed
        # article timestamps are supplied by the official pages, not by a model.
        'publication_time':['2026-04-16T10:00:00+08:00','2026-05-18T10:00:00+08:00','2026-06-16T10:00:00+08:00','2026-07-15T10:00:00+08:00','2026-08-17T15:00:00+08:00','2026-09-15T10:00:00+08:00'],
        'observed_at':[None]*6,
        'source_sha256':[None]*6,
        'period_start':['2026-01-01']*6,
        'period_end':['2026-03-31','2026-04-30','2026-05-31','2026-06-30','2026-07-31','2026-08-31'],
        'vintage_status':['public_release_review_copy_not_canonical_store']*6,
    },index=pd.to_datetime(months))
    activity.loc['2026-08-01','observed_at']='2026-09-29T09:27:59.292912+00:00'
    activity.loc['2026-08-01','source_sha256']='0345aa69391d4b0bb8beebf23d29915bbc41eb95fc070eaf9e760ded96548127'
    # Latest raw source observations, verified against the immutable Macro pin.
    data={'china_property/activity':activity,
        'china_property/home_price':pd.DataFrame({'new_rising':[15.],'new_falling':[49.],'new_flat':[6.],'cities':[70.],'second_breadth':[-59.]},index=pd.to_datetime(['2026-08-01'])),
        'china_property/climate':pd.DataFrame({'climate':[91.45]},index=pd.to_datetime(['2025-12-01'])),
        'china_property/cgb':pd.DataFrame({'cgb_2y':[1.2716],'cgb_5y':[1.4102],'cgb_10y':[1.679],'cgb_30y':[2.097]},index=pd.to_datetime(['2026-09-28'])),
        'china_macro/rrr':pd.DataFrame({'rrr_big':[9.0],'rrr_change':[-.5]},index=pd.to_datetime(['2025-05-07'])),
        'china_macro/money_supply':pd.DataFrame({'m1_yoy':[4.1],'m2_yoy':[7.5]},index=pd.to_datetime(['2026-08-01'])),
        'china_credit/tsf':pd.DataFrame({'tsf_total':[16577.],'rmb_loans':[552.],'fx_loans':[409.],'entrust':[229.],'trust':[-233.],'accept_bills':[382.],'corp_bonds':[2712.],'govt_bonds':[10097.],'equity':[639.]},index=pd.to_datetime(['2026-08-01'])),
        'china_connect/southbound':pd.DataFrame({'net':[-6553.87],'hold_mktcap':[119180.19093242301]},index=pd.to_datetime(['2026-09-28'])),
        'china_margin/balance':pd.DataFrame({'fin_pct_float':[2.678974]},index=pd.to_datetime(['2026-09-28'])),
        'china_margin/daily_trade':pd.DataFrame({'margin_trade_amt':[1383.37888496],'trade_amt_ratio':[8.0583],'maint_ratio':[267.7541]},index=pd.to_datetime(['2026-09-28'])),
        'china_flows/limit_breadth':pd.DataFrame({'zt':[33.],'dt':[56.],'seal_rate':[75.]},index=pd.to_datetime(['2026-09-28']))}
    x=build_snapshot(lambda g,n:data.get(g+'/'+n),ASOF)
    metrics={m['id']:m for p in x['panels'].values() for m in p['metrics']}
    # Audit-derived values are a single observed endpoint, not synthesized histories.
    audited={'financing_growth':(-10.7,'-10.7','2026-08-01'), 'tsf_12m':(32.96,'32.96','2026-08-01'),
             'southbound_5':(16.56,'+16.56','2026-09-28'), 'southbound_20':(56.04,'+56.04','2026-09-28'),
             'southbound_buy_days':(18,'18','2026-09-28'), 'margin_net20':(-49.16,'-49.16','2026-09-28'),
             'construction_return':(-2.5,'-2.5','2026-09-28'), 'maintenance':(267.8,'267.8','2026-09-28'),
             'northbound_turnover':(260.50,'260.50','2026-09-28')}
    for ident,(value,display,ref) in audited.items():
        m=metrics[ident];m.update(value=value,display=display,reference_date=ref,last_valid_date=ref,n=1,
            chart={'dates':[ref],'vals':[value]},status='recent',status_en=STATUS['recent'][0],status_zh=STATUS['recent'][1],
            delta=None,delta_display=None,previous_date=None,percentile=None)
        end=pd.Timestamp(ref)+pd.offsets.MonthEnd(0) if m['frequency']=='monthly' else pd.Timestamp(ref)
        m['age_days']=(pd.Timestamp(ASOF)-end).days
        m['note_en']+=' Review preview contains the verified latest endpoint only; full historical data was not copied into this artifact.'
        m['note_zh']+=' 审阅预览仅包含已核验最新读数，未复制完整历史。'
    metrics['property_drawdown'].update(value=None,display='—',status='quality_hold',status_en=STATUS['quality_hold'][0],status_zh=STATUS['quality_hold'][1],
        reference_date='2026-09-29',note_en='Three unverified >50% price discontinuities in August 2024. The audited series is held for basis verification.',note_zh='2024年8月存在三次未经核验的单日超过50%价格突变，等待口径核验。',discontinuities=['2024-08-05','2024-08-09','2024-08-12'])
    x['panels']['policy'].update(headline_en='Rolling-year financing is below last year.',headline_zh='过去一年新增融资低于去年同期。')
    x['panels']['flows'].update(headline_en='Selling in the latest session; 20-session buying remains positive.',headline_zh='最新交易日净卖出，20日累计仍净买入。')
    for p in x['panels'].values():p['recent']=sum(m['status']=='recent' for m in p['metrics'])
    x['preview_scope']='audited_latest_points_plus_six_public_property_releases_not_production_backfill'
    x['audit_source_pin']=SOURCE_PIN
    x['public_source_urls']=source_urls
    return x


def synthetic_snapshot():
    # Deterministic fixtures ONLY: no feature labels suggest real market history.
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('fixture_tests',ROOT/'tests/test_china_macro_evidence.py');mod=module_from_spec(spec);spec.loader.exec_module(mod)
    x=real_snapshot()
    for p in x['panels'].values():
        for m in p['metrics']:
            if m['status']=='quality_hold':continue
            dates=pd.bdate_range(end='2026-09-28',periods=300) if m['frequency']=='daily' else pd.date_range(end='2026-08-01',periods=60,freq='MS')
            base=m['value'] if m['value'] is not None else 1
            vals=(base+np.sin(np.arange(len(dates))*.12)*max(abs(base)*.12,1)+np.arange(len(dates))*.001).tolist()
            vals[-10]=None
            m['chart']={'dates':[d.date().isoformat() for d in dates],'vals':vals}
            m['preview_synthetic']=True
    x['preview_scope']='SYNTHETIC_TEST_FIXTURE_NOT_MARKET_DATA'
    return x


def render(snapshot:dict, destination:Path, synthetic:bool=False):
    destination.mkdir(parents=True,exist_ok=True)
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=True,undefined=StrictUndefined)
    template=env.from_string('''<!doctype html><html lang="en" data-lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>China macro · implementation review</title><style>{{ shell_css|safe }}{{ feature_css|safe }}</style></head><body class="page-china">
    <div class="preview-header"><strong>MASTERMIND <span>CHINA / REVIEW BUILD</span></strong><div><button type="button" onclick="document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark'">Light / dark</button><button type="button" onclick="document.documentElement.dataset.lang=document.documentElement.dataset.lang==='en'?'zh':'en'">EN / 中文</button></div></div>
    <main class="preview-home"><p class="preview-label">{{ disclaimer }}</p><h1>From scattered readings<br>to a clear China brief.</h1><p>Four perspectives. Dated evidence. Definitions and limitations one click away.</p><nav>{% for key in ['policy','property','flows','sentiment'] %}<button type="button" data-open="{{ key }}" onclick="cnxOpenDlg('cnx-dlg-{{ key }}')">{{ snapshot.panels[key].title_en }} ↗</button>{% endfor %}</nav><p>Review artifact only. The live China dashboard has not been changed by opening this file.</p></main>
    {% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}
    {% import '_china_macro_evidence.html.j2' as evidence with context %}
    {% for key in ['policy','property','flows','sentiment'] %}{{ evidence.panel(snapshot,key,leaderboard_data=lb) }}{% endfor %}
    <script>function cnxOpenDlg(id){document.querySelectorAll('.cnx-dlg.open').forEach(e=>e.classList.remove('open'));const el=document.getElementById(id);if(el){el.classList.add('open');document.body.style.overflow='hidden';history.replaceState(null,'','#'+id);}}function cnxCloseDlg(){document.querySelectorAll('.cnx-dlg.open').forEach(e=>e.classList.remove('open'));document.body.style.overflow='';history.replaceState(null,'',location.pathname);}if(location.hash.startsWith('#cnx-dlg-'))cnxOpenDlg(location.hash.slice(1));</script>
    <script>{{ feature_js|safe }}</script></body></html>''')
    shell_css='''*{box-sizing:border-box}html{font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;--bg:#0c1017;--panel:#121720;--panel2:#1a202b;--text:#e3e9f3;--muted:#93a1b5;--line:#283244;--info:#79adfa;--up:#54bb94;--down:#ea817e;--warn:#e5b767;color-scheme:dark}html[data-theme=light]{--bg:#eef1f5;--panel:#f9fafc;--panel2:#edf0f5;--text:#263244;--muted:#5b687c;--line:#cfd6e0;--info:#2b63b7;--up:#197353;--down:#b13839;--warn:#926313;color-scheme:light}body{margin:0;background:var(--bg);color:var(--text)}button{font-family:inherit;cursor:pointer}html[data-lang=en] .l-zh,html[data-lang=zh] .l-en{display:none}.cnx-dlg{display:none;position:fixed;inset:0;z-index:100;overflow:auto}.cnx-dlg.open{display:block}.cnx-dlg-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.66);backdrop-filter:blur(7px)}.cnx-dlg-panel{position:relative}.cnx-dlg-head{display:flex;justify-content:space-between;align-items:center}.preview-header{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:24px 4vw;border-bottom:1px solid var(--line);font-size:12px}.preview-header strong{letter-spacing:.12em}.preview-header strong span{color:var(--muted);font-weight:400;margin-left:12px;letter-spacing:.05em}.preview-header button{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-left:7px}.preview-home{max-width:980px;margin:10vh auto;padding:0 25px}.preview-home h1{font-size:clamp(32px,4.6vw,58px);font-weight:600;letter-spacing:-.04em;line-height:1.12}.preview-home p{line-height:1.8;color:var(--muted);font-size:14px}.preview-home nav{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:40px 0}.preview-home nav button{background:var(--panel);color:var(--text);border:1px solid var(--line);padding:25px;text-align:left;font-size:16px;border-radius:12px}.preview-label{font-size:11px!important;line-height:1.65!important;border-left:2px solid var(--warn);padding-left:12px}@media(max-width:560px){.preview-header{align-items:start}.preview-header strong span{display:block;margin:5px 0}.preview-header button{font-size:9px;padding:8px}.preview-home nav{grid-template-columns:1fr}.preview-home{margin-top:5vh}}'''
    # Latest provider examples read during the audit. No missing route invented.
    lb=normalize({'001':[{'TRADE_DATE':'2026-09-28','SECURITY_CODE':'688498','SECURITY_NAME':'源杰科技','DEAL_AMT':1239039719,'NET_BUY_AMT':None}],
                  '003':[{'TRADE_DATE':'2026-09-28','SECURITY_CODE':'000725','SECURITY_NAME':'京东方A','DEAL_AMT':1106352741,'NET_BUY_AMT':None}],
                  '002':[{'TRADE_DATE':'2026-09-28','SECURITY_CODE':'00700','SECURITY_NAME':'腾讯控股','NET_BUY_AMT':-420840488.6000061,'DEAL_AMT':4428124231.84}],
                  '004':[{'TRADE_DATE':'2026-09-28','SECURITY_CODE':'02800','SECURITY_NAME':'盈富基金','NET_BUY_AMT':-1927305000.0,'DEAL_AMT':5126691500.0}]},ASOF)
    lb['warnings'].append('Review includes one verified example per venue, not the full top-ten snapshot')
    disclaimer=('SYNTHETIC INTERACTION TEST — generated fixture histories, NOT market observations.' if synthetic else 'REVIEW PREVIEW — latest audited values and public property releases. Missing histories and percentile ranks are not fabricated. Not a production feed.')
    html=template.render(snapshot=prepare_view(snapshot),lb=lb,shell_css=shell_css,
        feature_css=(ROOT/'templates/china-macro-evidence.css').read_text(),feature_js=(ROOT/'templates/china-macro-evidence.js').read_text(),disclaimer=disclaimer)
    (destination/'index.html').write_text(html)
    (destination/'china_macro_evidence.json').write_text(json.dumps(snapshot,ensure_ascii=False,allow_nan=False,indent=2))
    return destination/'index.html'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--synthetic',action='store_true');args=parser.parse_args()
    print(render(synthetic_snapshot() if args.synthetic else real_snapshot(),args.output,args.synthetic))
