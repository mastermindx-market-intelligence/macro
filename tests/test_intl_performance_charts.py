"""Real-owner chart windows, source gaps, identity and request boundaries."""
import json
from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from engine.intl_performance_charts import build_chart_records
from engine.intl_performance_records import build_return_records
from engine import intl_performance as owner, intl_inputs
from lib import store


def test_real_owner_windows_levels_gaps_and_context(monkeypatch):
    checks=0
    def check(condition, name):
        nonlocal checks
        assert condition,name
        checks+=1

    def blocked(*args,**kwargs): raise AssertionError('unexpected store/collector/spark/benchmark call')
    monkeypatch.setattr(store, 'read', blocked)
    monkeypatch.setattr(intl_inputs, '_intl_closes', blocked)
    monkeypatch.setattr(owner, '_spark', blocked)
    monkeypatch.setattr(owner, '_bench_series_fresh', blocked)

    def chart(f,**kw):
        before=f.copy(deep=True)
        r=build_chart_records(f,**kw)
        pd.testing.assert_frame_equal(f,before)
        json.dumps(r,allow_nan=False)
        return r

    def first(r):return r['records'][0]

    idx=pd.date_range('2025-12-01',periods=22)
    f=pd.DataFrame({'^N225':np.arange(100.,122.),'USDJPY=X':[100.]*22,'^FTSE':np.arange(200.,222.),'GBPUSD=X':[1.25]*22},index=idx)
    r=first(chart(f,market_ids=['JP'],basis='usd',source_reference='fixture:v1'))
    check(len(r['points'])==22,'all supplied timestamps')
    check(r['points'][0]['value']==1 and r['points'][-1]['value']==1.21,'actual inverse quote levels')
    check(r['qualification']=='not_evaluated' and r['normalization']['status']=='unavailable','no qualified normalization')
    check(r['window']==build_return_records(f,market_ids=['JP'])['records'][0]['usd']['window'],'exact accepted USD window')
    gb=first(chart(f,market_ids=['GB'],basis='usd'))
    check(gb['points'][0]['value']==250 and gb['points'][-1]['value']==276.25,'actual direct quote levels')
    gap=f.copy();gap.iloc[5,gap.columns.get_loc('USDJPY=X')]=np.nan;gap.iloc[9,gap.columns.get_loc('^N225')]=np.nan;gap.iloc[13,gap.columns.get_indexer(['^N225','USDJPY=X'])]=np.nan
    # Both-missing row is absent from the real owner union, so add one real
    # earlier observation to retain a full 21-step window while preserving that gap.
    prior_gap=pd.DataFrame({'^N225':[99.],'USDJPY=X':[100.],'^FTSE':[199.],'GBPUSD=X':[1.25]},index=[idx[0]-pd.Timedelta(days=1)])
    gap=pd.concat([prior_gap,gap]);g=first(chart(gap,market_ids=['JP'],basis='usd'))
    gpoints={v['timestamp']:v for v in g['points']}
    check([gpoints[idx[i].isoformat()]['reason'] for i in [5,9,13]]==['missing_fx','missing_price','missing_price_and_fx'],'three explicit gaps')
    check(gpoints[idx[5].isoformat()]['source_observations']['fx']==idx[4].isoformat(),'actual previous FX contributor')
    check(gpoints[idx[6].isoformat()]['value']==1.06 and g['numerical_status']=='partial','resume after gap')
    glocal=first(chart(gap,market_ids=['JP'],basis='local'))
    lp={v['timestamp']:v for v in glocal['points']}
    check(lp[idx[5].isoformat()]['value']==105 and lp[idx[5].isoformat()]['source_observations']['fx'] is None,'local does not depend on FX cell')
    end=f.copy();end.loc[idx[-1],'^N225']=np.nan
    e=first(chart(end,market_ids=['JP'],basis='usd'))
    check(e['points'][-1]['timestamp']==idx[-1].isoformat() and e['points'][-1]['value'] is None,'masked endpoint not silently moved')
    check(e['window']['endpoint_observations']['price_end']==idx[-2].isoformat(),'endpoint contributor remains earlier observation')
    only=f[['^N225']].copy();only.loc[idx[8],'^N225']=np.nan
    l=first(chart(only,market_ids=['JP'],basis='local'))
    # A missing local observation shrinks the owner horizon; add one real prior row.
    check(l['numerical_status']=='unavailable','observed local n+1 insufficiency')
    prior=pd.DataFrame({'^N225':[99.]},index=[idx[0]-pd.Timedelta(days=1)])
    only=pd.concat([prior,only]);l=first(chart(only,market_ids=['JP'],basis='local'))
    check(l['window']['calendar_policy']=='observed_local_prices' and len(l['points'])==23,'local observed horizon includes explicit interior gap')
    check(first(chart(only,market_ids=['JP'],basis='usd'))['points']==[],'missing FX withholds USD')
    y=f.copy();y.index=pd.date_range('2025-12-20 23:30:00.000000001',periods=22,tz='Pacific/Kiritimati')
    yr=first(chart(y,market_ids=['JP'],basis='usd',horizon='ytd'))
    check(yr['points'][0]['timestamp']=='2025-12-31T23:30:00.000000001+14:00','YTD keeps actual local-year/ns start')
    check(yr['window']==[v for v in build_return_records(y,market_ids=['JP'])['records'] if v['horizon']=='ytd'][0]['usd']['window'],'timezone window equality')
    check(chart(f,market_ids=[])['records']==[],'empty selected markets')
    for kwargs in [dict(horizon='nope'),dict(basis='hedged'),dict(market_ids=['JP','JP']),dict(source_reference=' ')]:
        try:chart(f,**kwargs)
        except ValueError:check(True,'closed request rejected')
        else:raise AssertionError(('accepted invalid request',kwargs))
    for bad in [f.iloc[::-1],f.set_axis([idx[0]]*22)]:
        check(chart(bad)['reason']=='invalid_geometry','bad chronology closed')
    for v in [0.,-1.,float('inf')]:
        bad=f.copy();bad.loc[idx[10],'^N225']=v
        check(first(chart(bad,market_ids=['JP']))['points']==[],'bad raw source withheld')
    assert checks == 26


@pytest.fixture
def closes():
    return pd.DataFrame({'^N225':np.arange(100.,400.),'USDJPY=X':[100.]*300},
                        index=pd.date_range('2025-09-01',periods=300))


@pytest.mark.parametrize('basis',[None,True,0,[],{},set(),('usd',),'USD','usd_unhedged',''])
def test_bad_basis_is_request_error(closes,basis):
    with pytest.raises(ValueError,match='invalid_request:basis'):
        build_chart_records(closes,basis=basis)


@pytest.mark.parametrize('horizon',['1m','3m','6m','12m','ytd'])
@pytest.mark.parametrize('basis',['local','usd'])
def test_each_configured_window_keeps_exact_endpoints(closes,horizon,basis):
    record=next(r for r in build_return_records(closes,market_ids=['JP'])['records'] if r['horizon']==horizon)
    result=build_chart_records(closes,market_ids=['JP'],horizon=horizon,basis=basis)['records'][0]
    assert result['window']==record[basis]['window']
    assert result['points'][0]['timestamp']==result['window']['start']
    assert result['points'][-1]['timestamp']==result['window']['end']
    assert result['points'][0]['value'] > 0
    assert result['sampling_policy']=='all_supplied_timestamps_no_downsampling'
    assert result['qualification']=='not_evaluated'
    assert result['normalization']['status']=='unavailable'
    assert 'benchmark' not in result and 'normalized_100' not in result
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('zone',['Pacific/Kiritimati','America/Adak'])
def test_local_year_boundary_and_nanoseconds(closes,zone):
    closes.index=pd.date_range('2025-12-20 23:30:00.000000001',periods=300,tz=zone)
    expected=next(r for r in build_return_records(closes,market_ids=['JP'])['records'] if r['horizon']=='ytd')['usd']['window']
    r=build_chart_records(closes,market_ids=['JP'],horizon='ytd')['records'][0]
    assert r['window']==expected
    assert r['points'][0]['timestamp']==expected['start']
    assert '.000000001' in r['points'][0]['timestamp']
    assert r['points'][-1]['timestamp']==expected['end']


@pytest.mark.parametrize('value',[True,'100',0,-1,float('inf')])
def test_invalid_observed_values_conservatively_withhold(closes,value):
    closes['^N225']=closes['^N225'].astype(object)
    closes.iloc[17,0]=value
    r=build_chart_records(closes,market_ids=['JP'])['records'][0]
    assert r['numerical_status']=='unavailable' and r['points']==[]
    assert r['reason']=='invalid_observation'
    json.dumps(r,allow_nan=False)


def test_duplicate_columns_are_invalid_geometry(closes):
    closes.columns=['^N225','^N225']
    r=build_chart_records(closes)
    assert r['reason']=='invalid_geometry' and r['records']==[]


def test_custom_order_empty_horizons_and_configuration_not_mutated(monkeypatch,closes):
    cfg={'horizons_d':{}}
    original=deepcopy(cfg)
    monkeypatch.setattr(owner,'_pcfg',lambda:cfg)
    with pytest.raises(ValueError,match='invalid_request:horizon'):
        build_chart_records(closes,horizon='1m',market_ids=[])
    r=build_chart_records(closes,market_ids=['JP'],horizon='ytd')
    assert len(r['records'])==1 and r['records'][0]['horizon']=='ytd'
    assert cfg==original


def test_source_and_input_identity_nonmutating(closes):
    before=closes.copy(deep=True)
    countries_before=deepcopy(intl_inputs.countries())
    legacy_before=build_return_records(closes)
    r=build_chart_records(closes,market_ids=['GB','JP'],source_reference='supplied:fixture')
    assert [x['market_id'] for x in r['records']]==['GB','JP']
    assert r['source_reference']=='supplied:fixture'
    assert r['records'][0]['numerical_status']=='unavailable'
    assert r['records'][1]['numerical_status']=='available'
    assert r['numerical_status']=='partial'
    pd.testing.assert_frame_equal(closes,before)
    assert intl_inputs.countries()==countries_before
    assert build_return_records(closes)==legacy_before


def _binding_inputs(closes):
    bases = {series_id: "fixture-only" for country in intl_inputs.countries().values()
             for series_id in (country["index"], country["fx"])}
    snap = intl_inputs.source_snapshot(closes, source_reference="fixture:bound", adjustment_bases=bases)
    return bases, snap


def test_snapshot_binding_preserves_raw_owner_points_and_no_admission(closes, monkeypatch):
    from engine.intl_performance_charts import build_snapshot_bound_charts
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected source acquisition")
    monkeypatch.setattr(store, 'read', forbidden)
    monkeypatch.setattr(intl_inputs, '_intl_closes', forbidden)
    monkeypatch.setattr(owner, '_bench_series_fresh', forbidden)
    closes.loc[closes.index[-8], 'USDJPY=X'] = np.nan
    before = closes.copy(deep=True)
    bases, snap = _binding_inputs(closes); original = deepcopy(snap)
    raw = build_chart_records(closes, market_ids=['JP'], basis='usd', source_reference=snap['source_reference'])
    bound = build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'], basis='usd')
    assert bound['source_content_sha256'] == snap['content_sha256']
    assert {k: v for k, v in bound.items() if k != 'source_content_sha256'} == raw
    assert bound['records'][0]['qualification'] == 'not_evaluated'
    assert bound['records'][0]['normalization']['status'] == 'unavailable'
    assert any(p['reason'] == 'missing_fx' for p in bound['records'][0]['points'])
    assert 'benchmark' not in bound
    bound['records'][0]['points'][0]['value'] = -100
    assert snap == original
    pd.testing.assert_frame_equal(closes, before)


@pytest.mark.parametrize('change', ['value', 'digest', 'timestamp', 'basis', 'extra', 'number_type'])
def test_snapshot_binding_rejects_tampered_snapshot(closes, change):
    from engine.intl_performance_charts import build_snapshot_bound_charts
    bases, snap = _binding_inputs(closes)
    if change == 'value': snap['series'][0]['observations'][0]['value'] += 1
    if change == 'digest': snap['content_sha256'] = '0' * 64
    if change == 'timestamp': snap['series'][0]['observations'][0]['timestamp'] += 'Z'
    if change == 'basis': snap['series'][0]['adjustment_basis'] = 'different'
    if change == 'extra': snap['permission'] = 'allowed'
    if change == 'number_type': snap['series'][0]['observations'][0]['value'] = int(snap['series'][0]['observations'][0]['value'])
    reason = 'invalid_chart_snapshot' if change == 'extra' else 'chart_snapshot_mismatch'
    with pytest.raises(ValueError, match=reason):
        build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'])


def test_snapshot_binding_rejects_changed_frame_and_preserves_nanosecond_clock(closes):
    from engine.intl_performance_charts import build_snapshot_bound_charts
    closes.index = pd.date_range('2025-09-01 23:30:00.000000123', periods=len(closes), tz='Pacific/Kiritimati')
    bases, snap = _binding_inputs(closes)
    result = build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'])
    assert result['records'][0]['points'][-1]['timestamp'] == closes.index[-1].isoformat()
    closes.iloc[-5, 0] += 1
    with pytest.raises(ValueError, match='chart_snapshot_mismatch'):
        build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'])


def test_snapshot_binding_rejects_container_hooks_before_access(closes):
    from engine.intl_performance_charts import build_snapshot_bound_charts
    bases, snap = _binding_inputs(closes)
    class Poison(dict):
        def get(self, *args): raise AssertionError('hook invoked')
        def __getitem__(self, key): raise AssertionError('hook invoked')
        def items(self): raise AssertionError('hook invoked')
    with pytest.raises(ValueError, match='invalid_chart_snapshot'):
        build_snapshot_bound_charts(closes, snapshot=Poison(snap), adjustment_bases=bases)
    snap['series'][0]['observations'] = Poison()
    with pytest.raises(ValueError, match='invalid_chart_snapshot'):
        build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases)


def test_snapshot_binding_keeps_local_absence_and_source_label_untrusted(closes):
    from engine.intl_performance_charts import build_snapshot_bound_charts
    closes = closes[['^N225']]
    bases, snap = _binding_inputs(closes)
    local = build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'], basis='local')
    usd = build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'], basis='usd')
    assert local['records'][0]['points'] and usd['records'][0]['points'] == []
    assert local['source_content_sha256'] == usd['source_content_sha256']
    snap['source_reference'] = 'caller-label-not-issuer-authentication'
    relabelled = build_snapshot_bound_charts(closes, snapshot=snap, adjustment_bases=bases, market_ids=['JP'], basis='local')
    assert relabelled['source_content_sha256'] == local['source_content_sha256']
    assert relabelled['records'][0]['qualification'] == 'not_evaluated'
