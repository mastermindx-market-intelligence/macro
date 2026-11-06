"""Actual five-route builder; all inputs synthetic, all outputs private research.

Baseline mode restores the original two consumers and complete outer template.
No ledger, live feed, production data, deployed file or authenticated browser is used.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
import RRU_INTL_JOURNEY_TESTS_2026_09_09 as j
from lib import config, pages

HERE = Path(__file__).resolve().parent
TEMPLATES = ('international_macro.html.j2', '_risk_radar_card.html.j2',
             '_risk_radar_card.css.j2', '_seo_head.html.j2',
             '_site_nav.html.j2', '_navlinks.html.j2')
ASSETS = ('theme.css', 'product-nav-icons.css', 'navigation-refresh.css',
          'theme.js', 'data_base.js')
CASES = ('complete', 'partial', 'unavailable', 'legacy', 'absent',
         'old_odds', 'metadata_null', 'metadata_empty', 'claimed_reviewed')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def bind(baseline=False):
    j.a.apply_bundle(j.candidate.bundle)
    for module in (j.a.radar, j.a.market_state, j.a.recovery,
                   j.a.radar_audit, j.a.radar_tune, j.dashboard, j.builder):
        path = ('scripts/' if module is j.builder else 'engine/') + module.__name__.rsplit('.',1)[-1]+'.py'
        raw = j.candidate.edited.get(path) or j.pinned(path)
        if baseline and module in (j.dashboard, j.builder):
            raw = j.pinned(path)
        exec(compile(raw, path, 'exec'), module.__dict__)
    if baseline:
        j.a.RENDER_SOURCES[j.TEMPLATE] = j.pinned(j.TEMPLATE)
    assert j.builder.build_country_view is j.dashboard.build_country_view

def payload(cc, case):
    if case == 'absent':
        return j.record(cc, {})
    if case == 'legacy':
        return j.record(cc, dict(market=cc.lower(), state='caution',
            drawdown_prob=dict(h21=.42), dominant_label_en='Legacy fixture'))
    snap = j.snapshot(j.a.radar.PROFILES[cc.lower()], case)
    if case in ('old_odds','metadata_null','metadata_empty','claimed_reviewed'):
        snap['drawdown_prob'] = dict(h21=.42, measure='Synthetic older record')
        snap['state'] = 'calm'
    if case == 'metadata_null': snap['composition'] = None
    if case == 'metadata_empty': snap['composition'] = {}
    if case == 'claimed_reviewed': snap['composition']['calibration_status'] = 'reviewed'
    return j.record(cc, snap)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-consumers',action='store_true')
    parser.add_argument('--label',default='candidate-v1')
    args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        raise ValueError('label must be a simple fixture name')
    out=HERE/('rru_intl_build_20260910_'+args.label)
    out.mkdir(exist_ok=False)
    def state(p):
        f=j.a.ROOT/p
        return sha(f.read_bytes()) if f.exists() else None
    before={p:state(p) for p in set(j.candidate.bundle)|{j.BUILDER,j.VIEW}}
    bind(args.baseline_consumers)
    sources={name:j.a.RENDER_SOURCES.get('templates/'+name) or j.pinned('templates/'+name)
             for name in (*TEMPLATES,*ASSETS)}
    result=[]
    for case in CASES:
        root=out/case; site=root/'site'; data=root/'data'; templates=root/'templates'
        for folder in (site,data,templates): folder.mkdir(parents=True)
        for name,raw in sources.items(): (templates/name).write_text(raw)
        records=[payload(cc,case) for cc in j.dashboard.REGIONS]
        saved=deepcopy(records)
        settings={'storage':{'site_dir':str(site),'data_dir':str(data)},'watchlist':{}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(config,'ROOT',root))
            stack.enter_context(patch.object(config,'load',return_value=settings))
            stack.enter_context(patch.object(j.builder,'load_history',return_value=None))
            stack.enter_context(patch.object(j.a.market_state,'_rr_scorecard_track',return_value=None))
            stack.enter_context(patch.object(pages,'_shim_checked',False))
            paths=j.builder.build_all({'records':records})
        assert len(paths)==5 and records==saved
        for rec,path in zip(records,paths):
            cc=rec['cc']; modern=case not in ('legacy','absent')
            html=path.read_text(); soup=BeautifulSoup(html,'html.parser')
            view=json.loads((data/'international_macro'/f'{cc}_latest.json').read_text())
            cards=soup.select('.rrx'); card_text=cards[0].get_text(' ',strip=True) if cards else ''
            checks=dict(five_routes=len(paths)==5, shim='data-dbase' in html,
                        input_unchanged=records==saved, json_schema=view['schema']=='international_macro_dashboard.v1')
            if modern:
                checks.update(card_present=len(cards)==1, odds_withheld=view['risk']['h21'] is None,
                    not_calibrated=view['risk']['calibrated'] is False,
                    composition_preserved='composition' in view['risk'] and view['risk']['composition']==rec['risk_radar']['composition'],
                    no_score_adjustment=view['decision']['parts']['risk_state']==0,
                    no_false_calm='CALM' not in card_text and 'Normal exposure' not in card_text,
                    forecast_unavailable='Forecast not available' in soup.select_one('#dlg-risk').get_text(' ',strip=True),
                    no_old_probability='42.0%' not in soup.select_one('#dlg-risk').get_text(' ',strip=True))
            else:
                checks.update(legacy_card_count=len(cards)==(1 if case=='legacy' else 0),
                    legacy_odds=view['risk']['h21']==(.42 if case=='legacy' else None),
                    legacy_adjustment=view['decision']['parts']['risk_state']==(-4. if case=='legacy' else 0.),
                    no_new_legacy_field='composition' not in view['risk'])
            result.append(dict(cc=cc,case=case,route=path.name,checks=checks,
                html_sha256=sha(path.read_bytes()),view_sha256=sha((data/'international_macro'/f'{cc}_latest.json').read_bytes())))
    unchanged=all(state(p)==v for p,v in before.items())
    failures=[dict(cc=r['cc'],case=r['case'],failed=[k for k,v in r['checks'].items() if not v])
              for r in result if not all(r['checks'].values())]
    receipt=dict(kind='actual_builder_synthetic_inputs_private_outputs',
        source_pin=j.a.PIN, original_consumers=args.baseline_consumers,
        routes=len(result), cases=result, failures=failures, source_unchanged=unchanged,
        candidate_source_hashes={p:sha(raw.encode()) for p,raw in j.candidate.edited.items() if p in j.candidate.bundle},
        actual_template_hashes={n:sha(raw.encode()) for n,raw in sources.items()},
        renderer='scripts.build_international_macro.build_all -> lib.pages.write_page',
        replaced_seams=['config output roots; no auth config','history=None','read-only scorecard=None'],
        full_builder=True, authenticated=False, synthetic_only=True, production=False)
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(routes=len(result),failures=failures,source_unchanged=unchanged,
                         full_builder=True,production=False,receipt=str(out/'receipt.json'))))
    return 0 if not failures and unchanged else 1

if __name__=='__main__':
    raise SystemExit(main())
