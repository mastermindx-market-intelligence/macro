"""Observe actual China-builder risk writes without permitting their effects.

This is a diagnostic, not a replacement publisher or a repaired implementation.
All file-output seams are intercepted; HTML is retained in memory only.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import requests
from scripts import build_china as bc
from engine import china_run, market_state, risk_radar_intl_audit as audit
from engine import risk_radar_intl_tune as tuner, risk_radar_scorecard as scorecard
from lib import pages

ROOT = Path.cwd()
PROTECTED = ['data/china_regime/latest.json', 'data/china_regime/regime_history.parquet',
    'data/china_market_state/latest.json', 'data/china_market_state/score_log.parquet',
    'data/risk_radar_intl/cn_forward_log.jsonl', 'data/risk_radar_intl/cn_calibration.json',
    'data/risk_radar/scorecard.json', 'site/riskdata/scorecard.json',
    'data/risk_radar/recovery_log.jsonl', 'data/neuralweb/governance.jsonl',
    'data/china_regime/china_alloc_latest.json', 'data/china_stocks/latest.json',
    'site/china.html']

def digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def observe(flag, lane):
    risk_calls, page_outputs, other_outputs, network_calls = [], {}, [], []
    def effect(name):
        def call(*args, **kwargs):
            risk_calls.append(name)
            return audit.scorecard('cn', log_governance=False) if name=='grade' else {}
        return call
    def page_write(path, text, *args, **kwargs):
        page_outputs[str(path)] = str(text)
    def text_write(path, text, *args, **kwargs):
        other_outputs.append(str(path)); return len(text)
    def table_write(frame, path=None, *args, **kwargs):
        other_outputs.append(str(path)); return None
    def forbidden_network(*args, **kwargs):
        network_calls.append('request')
        raise RuntimeError('network disabled by read-only diagnostic')
    def forbidden_engine(*args, **kwargs):
        raise AssertionError('page-only path must not call analytical engine')
    env = {'RENDER_NO_DRIP':'', 'CHINA_FAST_RENDER':'', 'COLLECT_LANE':lane,
           'US_LANE':'', 'CHINA_VM_DUMP':''}
    env[flag] = '1'
    before = {p:digest(p) for p in PROTECTED}
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, env))
        for obj, name, replacement in [
            (audit,'snapshot_and_grade',effect('grade')),
            (tuner,'tune',effect('tune')), (scorecard,'write',effect('scorecard_write')),
            (market_state,'persist',effect('state_write')), (china_run,'run',forbidden_engine),
            (bc,'write_page',page_write), (pages,'write_page',page_write),
            (Path,'write_text',text_write), (Path,'write_bytes',text_write),
            (pd.DataFrame,'to_parquet',table_write), (pd.Series,'to_csv',table_write),
            (pd.DataFrame,'to_csv',table_write), (requests.sessions.Session,'request',forbidden_network),
        ]:
            stack.enter_context(patch.object(obj, name, replacement))
        code = bc.main()
    assert code == 0, code
    assert {p:digest(p) for p in PROTECTED} == before, 'unexpected persistent change'
    assert not network_calls, network_calls
    outputs = [v for k,v in page_outputs.items() if Path(k).name=='china.html']
    assert len(outputs)==1 and 'cnx-participation' in outputs[0]
    assert 'Read the backdrop' in outputs[0] and 'Historical stress' in outputs[0]
    return {'render_flag':flag, 'collect_lane':lane or 'unset', 'builder_exit':code,
        'risk_effect_calls_intercepted':risk_calls, 'generated_pages_intercepted':len(page_outputs),
        'other_output_calls_intercepted':len(other_outputs), 'network_calls':len(network_calls),
        'protected_sha256':before, 'html_sha256':hashlib.sha256(outputs[0].encode()).hexdigest(),
        'complete_main_to_template':True, 'risk_publication_is_read_only':not risk_calls}


def main():
    results = [observe(flag,lane) for flag,lane in
               [('RENDER_NO_DRIP',''), ('RENDER_NO_DRIP','nightly'), ('CHINA_FAST_RENDER','nightly')]]
    receipt = {'scope':'actual main with intercepted effect sinks; no source repair',
        'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'source_sha256':digest('scripts/build_china.py'), 'cases':results,
        'production':False, 'fresh_collection':False, 'browser_proof':False,
        'risk_source_modified':False, 'all_risk_writes_intercepted':True}
    target = Path(os.environ['CHINA_RENDER_EFFECT_PROOF'])
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cases':[{k:v for k,v in r.items() if k not in ('protected_sha256',)}
                             for r in results], 'receipt':str(target)},indent=2))


if __name__=='__main__':
    main()
