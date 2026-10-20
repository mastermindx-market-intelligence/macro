"""Dated provider approximations never acquire instantaneous capabilities."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from engine.options_exposure_projection import (build_exposure_projection, compose_native_exposure_context,
    exposure_input_digest, expand_projection_cells, DATED_KIND, DATED_TENOR,
    DATED_CAPABILITIES, THETA_METHODOLOGY)
from lib.options_source_receipts import (ACQUISITION_COLUMN, THETA_ENDPOINTS, theta_acquisition,
    massive_reference_terms, ordinary_spy_terms, BoundedRequestBudget)
from tests.test_options_source_receipts import book, reference, RECEIVED, ASOF, EXPIRY


def dated_book():
    g, oi, ctx = book()
    for frame, kind in ((g, 'greeks'), (oi, 'oi')):
        params = dict(symbol='SPY', expiration=EXPIRY.replace('-', ''), start_date=20261015,
                      end_date=20261015, right='both', strike_range=5, format='csv')
        if kind == 'greeks':
            params['version'] = '1'
        frame[ACQUISITION_COLUMN] = theta_acquisition(THETA_ENDPOINTS[kind], params,
            b'synthetic', origin='http://theta-test:25503', received_at=RECEIVED)
    ctx.update(kind=DATED_KIND, rights_decision_ref='synthetic:rights',
        valuation=dict(basis='provider_eod_approximation', source_session=ASOF,
            observation_clock='session_only', methodology_ref=THETA_METHODOLOGY,
            endpoint=THETA_ENDPOINTS['greeks'], requested_version='1', serving_build=None,
            tenor_policy=DATED_TENOR))
    for k in ('option_observed_at', 'underlying_observed_at'):
        ctx['clocks'][k] = None
    ctx['clocks']['available_at'] = '2026-10-15T21:00:00Z'
    for t in ctx['contract_terms']:
        t.pop('economic_expiry_at')
    for p in ctx['greek_provenance'].values():
        p['tenor_policy'] = DATED_TENOR
        p['model_ref'] = THETA_METHODOLOGY + '#eod-version-1'
    ctx['input_sha256'] = exposure_input_digest(g, oi, ASOF, 'SPY')
    return g, oi, ctx


def project(g, oi, ctx):
    p = build_exposure_projection(g, oi, ASOF, 'SPY', context=ctx)
    return {**p, 'cells': expand_projection_cells(p)}


def test_dated_gamma_uses_existing_math_and_keeps_all_other_capabilities_off():
    g, oi, ctx = dated_book()
    p = project(g, oi, ctx)
    assert p['kind'] == DATED_KIND and p['capabilities'] == DATED_CAPABILITIES
    assert p['cells'][0]['gamma']['gross'] == 20000
    assert p['cells'][0]['economic_expiry_at'] is None
    assert p['clocks']['option_observed_at'] is None
    for metric in ('vanna', 'charm'):
        assert p['metrics'][metric]['qualified'] == 0
        assert p['metrics'][metric]['known_net'] is None
        assert p['metrics'][metric]['exclusions'] == {'dated_metric_unavailable': 2}
    assert p['cells'][0]['joint']['qualified'] == 0 and not p['cells'][0]['joint']['complete']
    oi['open_interest'] = 0
    ctx['input_sha256'] = exposure_input_digest(g, oi, ASOF, 'SPY')
    p = project(g, oi, ctx)
    assert p['metrics']['gamma']['gross'] == 0
    assert p['metrics']['vanna']['qualified'] == 0 and not p['cells'][0]['joint']['complete']


@pytest.mark.parametrize('mutation', [
    lambda g, o, c: c['valuation'].update(requested_version='latest'),
    lambda g, o, c: c['valuation'].update(serving_build='invented'),
    lambda g, o, c: c['valuation'].update(methodology_ref='unknown'),
    lambda g, o, c: g.drop(columns=[ACQUISITION_COLUMN], inplace=True),
    lambda g, o, c: o.drop(columns=[ACQUISITION_COLUMN], inplace=True),
    lambda g, o, c: c['clocks'].update(available_at='2026-10-15T19:00:00Z'),
])
def test_dated_profile_cannot_forge_parameters_clocks_or_rights(mutation):
    g, oi, ctx = dated_book(); mutation(g, oi, ctx)
    ctx['input_sha256'] = exposure_input_digest(g, oi, ASOF, 'SPY')
    assert project(g, oi, ctx)['metrics']['gamma']['qualified'] == 0


def test_strict_modeled_class_keeps_existing_clocks_expiry_and_nofloor_guards():
    g, oi, ctx = dated_book(); ctx['kind'] = 'modeled_exposure'
    assert project(g, oi, ctx)['metrics']['gamma']['qualified'] == 0
    g, oi, ctx = book(); ctx['greek_provenance']['gamma']['tenor_policy'] = DATED_TENOR
    assert project(g, oi, ctx)['metrics']['gamma']['qualified'] == 0


def test_oi_missing_preserves_denominator_without_zero_or_partial_total():
    g, oi, ctx = dated_book(); oi = oi.iloc[:1]
    ctx['input_sha256'] = exposure_input_digest(g, oi, ASOF, 'SPY')
    p = project(g, oi, ctx)
    assert p['metrics']['gamma']['qualified'] == 1 and p['metrics']['gamma']['missing'] == 1
    assert p['metrics']['gamma']['gross'] is None and p['metrics']['gamma']['known_gross'] == 10000


def test_documented_omission_is_interpreted_with_citations_without_changing_raw():
    obs = reference(); original = deepcopy(obs)
    term = ordinary_spy_terms(massive_reference_terms(obs, 'SPY', 'SEC:SPY'))
    assert term['currency'] == 'USD' and term['multiplier'] == 100
    assert term['deliverable'] == '100_underlying_shares'
    assert not term['term_interpretation']['additional_underlyings_field_present']
    assert 'additional_underlyings' not in term and 'correction' not in term
    assert obs == original
    for change in ({'shares_per_contract': 150}, {'root': 'QQQ'},
                   {'additional_underlyings': [{'amount': 1, 'type': 'currency', 'underlying': 'USD'}]}):
        bad = {**term, **change}
        for k in ('currency', 'multiplier', 'deliverable', 'deliverable_ref', 'term_interpretation'):
            bad.pop(k, None)
        assert 'deliverable' not in ordinary_spy_terms(bad)


def test_list_reference_keeps_actual_route_and_selected_contract_identity():
    obs = reference(); c = obs.pop('contract'); obs.pop('field_presence')
    obs.update(path='/v3/reference/options/contracts', contracts=[c],
               params=dict(underlying_ticker='SPY', expiration_date=EXPIRY))
    term = massive_reference_terms(obs, 'SPY', 'SEC:SPY', contract=c)
    assert term['series_id'] == c['ticker'] and '/contracts#sha256=' in term['terms_ref']
    obs['params']['underlying_ticker'] = 'QQQ'
    with pytest.raises(ValueError):
        massive_reference_terms(obs, 'SPY', contract=c)


class FakeSession:
    def __init__(self, raw, status=200):
        self.calls = []; self.headers = {}; self.raw = raw; self.status = status
    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(status_code=self.status, iter_content=lambda **kw: iter([self.raw]), close=lambda: None)


def test_bounded_theta_skips_health_get_and_records_explicit_request_profile(monkeypatch):
    from collectors import thetadata as td
    s = FakeSession(b'symbol,expiration,strike,right,timestamp,gamma,underlying_price\nSPY,2026-10-23,100,C,2026-10-15T16:00:00,0.01,100\n')
    monkeypatch.setattr(td, '_session', lambda: s)
    monkeypatch.setattr(td, 'reachable', lambda: pytest.fail('extra health GET'))
    budget = BoundedRequestBudget()
    frame = td.bulk_greeks('SPY', EXPIRY, ASOF, ASOF, order=3, request_budget=budget,
                          strike_range=5, version='1', max_bytes=131072, max_rows=64)
    assert budget.attempts == 1 and len(s.calls) == 1 and not s.calls[0][1]['allow_redirects']
    rec = json.loads(frame.iloc[0][ACQUISITION_COLUMN])
    assert rec['parameters']['version'] == '1' and rec['parameters']['strike_range'] == 5
    s.raw = b'symbol,expiration,strike,right,timestamp,open_interest\nSPY,2026-10-23,100,C,2026-10-15T06:30:00,100\n'
    oi = td.bulk_open_interest('SPY', EXPIRY, ASOF, ASOF, request_budget=budget,
                               strike_range=5, max_bytes=131072, max_rows=64)
    assert budget.attempts == 2 and oi['open_interest'].tolist() == [100]


def test_native_observed_root_capture_retains_realistic_book_without_canary_limits(monkeypatch):
    from collectors import thetadata as td
    raw = ('symbol,expiration,strike,right,timestamp,gamma,underlying_price\n' + ''.join(
        f'SPY,2026-10-{23 + i % 2},{100 + i / 1000},C,2026-10-15T16:00:00,0.01,100\n'
        for i in range(14000))).encode()
    s=FakeSession(raw);monkeypatch.setattr(td,'_session',lambda:s)
    monkeypatch.setattr(td,'reachable',lambda:pytest.fail('extra health GET'))
    monkeypatch.setattr(td,'_concurrent_windows',lambda *a,**k:pytest.fail('unbounded retry/window path'))
    budget=BoundedRequestBudget(max_gets=2)
    frame=td.bounded_observed_root_history('SPY',ASOF,'greeks',request_budget=budget,
        version='1',max_bytes=2*1024*1024,max_rows=20000)
    assert len(frame)==14000 and budget.attempts==1 and len(s.calls)==1
    rec=json.loads(frame.iloc[0][ACQUISITION_COLUMN])
    assert rec['parameters']['expiration']=='*' and 'strike_range' not in rec['parameters']
    assert rec['parameters']['version']=='1' and frame.expiration.nunique()==2
    assert not s.calls[0][1]['allow_redirects'] and not rec['historical_first_availability_established']
    # The independently bounded original selected-expiry profile remains narrow.
    with pytest.raises(ValueError):
        td.bulk_greeks('SPY',EXPIRY,ASOF,ASOF,request_budget=BoundedRequestBudget(),
            strike_range=5,max_bytes=2*1024*1024,max_rows=20000)
    assert len(s.calls)==1


@pytest.mark.parametrize('kind,status,byte_cap,row_cap',[
    ('oi',403,10000,10),('greeks',500,10000,10),
    ('oi',200,1,10),('greeks',200,10000,1)])
def test_observed_root_failure_closes_same_budget(monkeypatch,kind,status,byte_cap,row_cap):
    from collectors import thetadata as td
    s=FakeSession(b'symbol,expiration,strike,right,timestamp,gamma,open_interest\nQQQ,2026-10-23,100,C,2026-10-15,0.01,1\nQQQ,2026-10-23,101,C,2026-10-15,0.01,1\n',status)
    monkeypatch.setattr(td,'_session',lambda:s);budget=BoundedRequestBudget(max_gets=2)
    assert td.bounded_observed_root_history('QQQ',ASOF,kind,request_budget=budget,
        version='1' if kind=='greeks' else None,max_bytes=byte_cap,max_rows=row_cap) is None
    assert budget.stopped and budget.attempts==1 and len(s.calls)==1
    with pytest.raises(RuntimeError):budget.begin(s,'http://theta-test')


@pytest.mark.parametrize('root,kind,version',[('IWM','greeks','1'),('SPY','eod','1'),
    ('SPY','greeks',None),('QQQ','oi','1')])
def test_observed_root_profile_is_explicit_before_effect(root,kind,version):
    from collectors import thetadata as td
    budget=BoundedRequestBudget()
    with pytest.raises(ValueError):td.bounded_observed_root_history(root,ASOF,kind,
        request_budget=budget,version=version,max_bytes=1000,max_rows=10)
    assert budget.attempts==0


@pytest.mark.parametrize('raw,status,max_bytes,max_rows', [
    (b'x\n1\n', 403, 100, 10), (b'x\n1\n', 500, 100, 10),
    (b'x\n1\n', 200, 1, 10), (b'x\n1\n2\n', 200, 100, 1)])
def test_bounded_theta_failure_closes_budget_without_retry(raw, status, max_bytes, max_rows):
    from collectors import thetadata as td
    s = FakeSession(raw, status); budget = BoundedRequestBudget()
    try:
        assert td._get_csv(s, THETA_ENDPOINTS['greeks'], {}, request_budget=budget,
                           max_bytes=max_bytes, max_rows=max_rows) is None
    except td._StreamTruncated:
        pass
    assert budget.stopped and budget.attempts == 1 and len(s.calls) == 1
    with pytest.raises(RuntimeError): budget.begin(s, 'http://theta-test')


def test_optional_evidence_failure_preserves_valid_legacy_csv():
    from collectors import thetadata as td
    s = FakeSession(b'gamma\n0.01\n')
    frame = td._get_csv(s, THETA_ENDPOINTS['greeks'], {'future_provider_parameter': True})
    assert frame['gamma'].tolist() == [.01] and ACQUISITION_COLUMN not in frame


def test_massive_bounded_read_preserves_digest_no_retry_and_no_next_page():
    from scripts.massive_entitlement_probe import RestProber
    for payload, status, successful in [({'results': []}, 200, True),
        ({'results': [], 'next_url': 'https://api.massive.com/next'}, 200, False), ({}, 403, False), ({}, 500, False)]:
        s = FakeSession(json.dumps(payload).encode(), status); b = BoundedRequestBudget()
        p = RestProber(None, session=s, request_budget=b)
        result = p.probe('selected', '/v3/reference/options/contracts', {'limit': 100})
        assert b.attempts == 1 and len(s.calls) == 1 and not s.calls[0][1]['allow_redirects']
        assert (result is not None) == successful
        if successful: assert len(p.results['selected']['evidence']['response_sha256']) == 64
        else: assert b.stopped


def test_shared_budget_enforces_three_gets_and_rejects_retry_carrier_before_effect():
    b = BoundedRequestBudget(); s = FakeSession(b'')
    for _ in range(3): b.begin(s, 'http://theta-test')
    with pytest.raises(RuntimeError): b.begin(s, 'http://theta-test')
    actual = requests.Session()
    actual.mount('https://', requests.adapters.HTTPAdapter(max_retries=1))
    b = BoundedRequestBudget()
    with pytest.raises(ValueError): b.begin(actual, 'https://api.massive.com')
    assert b.attempts == 0


def test_numerical_projection_does_not_mint_or_require_an_invented_rights_decision():
    g, oi, ctx = dated_book(); ctx.pop('rights_decision_ref')
    p = project(g, oi, ctx)
    assert p['rights_decision_ref'] is None and p['metrics']['gamma']['qualified'] == 2
    assert not p['capabilities']['historical_pit']


def test_native_receipt_wrong_expiry_cannot_qualify_other_selected_rows():
    g, oi, ctx = dated_book()
    rec=json.loads(g.iloc[0][ACQUISITION_COLUMN]);rec['parameters']['expiration']='20261030'
    g[ACQUISITION_COLUMN]=json.dumps(rec)
    ctx['input_sha256']=exposure_input_digest(g, oi, ASOF, 'SPY')
    assert project(g, oi, ctx)['metrics']['gamma']['qualified'] == 0


def test_native_normalized_datetime_expiry_remains_bound_after_parquet(tmp_path):
    g, oi, ctx=dated_book()
    for frame in (g, oi):frame['expiration']=pd.to_datetime(frame['expiration'])
    g.to_parquet(tmp_path/'g.parquet',index=False);oi.to_parquet(tmp_path/'oi.parquet',index=False)
    g=pd.read_parquet(tmp_path/'g.parquet');oi=pd.read_parquet(tmp_path/'oi.parquet')
    ctx['input_sha256']=exposure_input_digest(g,oi,ASOF,'SPY')
    assert project(g,oi,ctx)['metrics']['gamma']['qualified']==2


def test_context_cannot_promote_dated_capabilities():
    g, oi, ctx = dated_book()
    ctx['capabilities'] = {k: True for k in DATED_CAPABILITIES}
    assert project(g, oi, ctx)['capabilities'] == DATED_CAPABILITIES


def test_dated_underlying_reference_requires_uniform_observed_prices():
    g,oi,ctx=dated_book()
    p=project(g,oi,ctx)
    assert p['underlying_reference']==dict(value=100.0,currency='USD',basis='uniform_selected_contract_underlying_price',source_session=ASOF,instantaneous=False)
    g.loc[1,'underlying_price']=101
    ctx['input_sha256']=exposure_input_digest(g,oi,ASOF,'SPY')
    assert project(g,oi,ctx)['underlying_reference']['value'] is None
