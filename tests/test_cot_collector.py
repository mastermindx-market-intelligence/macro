"""Collector changes are exercised without reaching external services."""
from pathlib import Path
import json

import pandas as pd
import pytest

from collectors.cot import CotAdapter
from lib.cot_contracts import DATASETS
from lib.cot_data import normalize_row


def test_actual_cftc_fixture_reconciles_all_cohorts():
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'cot_source_20261006.json').read_text())
    out = {record['family']: normalize_row(record['row'], record['family'], observed_at=record['observed_at']) for record in fixture['records']}
    assert out['legacy']['open_interest'] == 283586
    assert out['legacy']['net_spec'] == 58123
    assert out['tff']['asset_manager_net'] == 73798
    assert out['tff']['leveraged_funds_net'] == -19212
    assert out['legacy']['nonreportable_net'] == out['tff']['nonreportable_net']
    assert out['disaggregated']['open_interest'] == 396109


def test_initial_bootstrap_requests_deep_history_without_name_matching(monkeypatch, tmp_path):
    from collectors import cot
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'cot_source_20261006.json').read_text())
    queries = []
    adapter = CotAdapter()
    monkeypatch.setattr(cot.store, 'read', lambda *_: None)
    monkeypatch.setattr(cot.config, 'data_dir', lambda: tmp_path)

    class Response:
        def __init__(self, rows): self.rows = rows
        def json(self): return self.rows

    def get(url, **kwargs):
        queries.append(kwargs['params'])
        family = next(k for k,v in DATASETS.items() if v in url)
        return Response([r['row'] for r in fixture['records'] if r['family'] == family])

    monkeypatch.setattr(adapter, 'http_get', get)
    frames = adapter.fetch_positioning()
    assert len(frames) == 3
    assert len(queries) == 3
    assert all('1995-01-01' in q['$where'] for q in queries)
    assert all('starts_with' not in q['$where'] and 'cftc_contract_market_code in' in q['$where'] for q in queries)
    assert all(q['$limit'] == 5000 for q in queries)
    assert len(list((tmp_path/'cot'/'raw').rglob('*.json.gz'))) == 3


def test_family_failure_keeps_cache_and_returns_other_families(monkeypatch,tmp_path):
    from collectors import cot
    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'cot_source_20261006.json').read_text())
    adapter = CotAdapter()
    monkeypatch.setattr(cot.store,'read',lambda *_:None)
    monkeypatch.setattr(cot.config,'data_dir',lambda:tmp_path)
    class Response:
        def json(self): return [r['row'] for r in fixture['records'] if r['family']=='legacy']
    def get(url,**kwargs):
        if DATASETS['legacy'] not in url: raise OSError('source unavailable')
        return Response()
    monkeypatch.setattr(adapter,'http_get',get)
    result=adapter.fetch_positioning()
    assert list(result)==['cot_legacy_209742']


def test_legacy_strategy_cannot_see_shutdown_report_early(monkeypatch):
    from engine import commodity_strategies
    frame=pd.DataFrame({'net_spec_pct_oi':[-4.]},index=pd.to_datetime(['2025-09-30']))
    monkeypatch.setattr(commodity_strategies,'read_legacy_frame',lambda *_:frame)
    result=commodity_strategies._col('cot','cot_gold','net_spec_pct_oi')
    assert result.index[0] == pd.Timestamp('2025-11-20')


def test_invalid_source_snapshot_never_becomes_neutral():
    from engine.cot_positioning import build_snapshot
    result=build_snapshot(now='2026-10-09T20:00:00Z',reader=lambda *_:pd.DataFrame({'net_spec_pct_oi':[0.]},index=pd.to_datetime(['2026-10-06'])))
    assert result['coverage']['unavailable']==21
    assert result['coverage']['current']==0
    assert all(not m['families']['legacy']['cohorts'] for m in result['markets'])


def test_existing_alias_keeps_its_three_column_schema_and_first_column(monkeypatch):
    from tests.test_cot_positioning import history
    adapter=CotAdapter()
    adapter.cfg={'markets':{'nasdaq':['NASDAQ MINI']},'retries':1}
    canonical=history(64)
    monkeypatch.setattr(adapter,'fetch_positioning',lambda *_:{'cot_legacy_209742':canonical})
    frames=adapter.fetch()
    assert list(frames['cot_nasdaq'].columns)==['net_spec','open_interest','net_spec_pct_oi']
    assert frames['cot_nasdaq'].iloc[-1,0]==canonical['net_spec'].iloc[-1]
    assert 'source_record_sha256' in frames['cot_legacy_209742']
