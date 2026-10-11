"""Projection semantics: weekly samples, no recommendations, explicit coverage."""
import json
import numpy as np
import pandas as pd
import pytest

from engine.cot_positioning import build_snapshot, family_view, percentile, tier
from lib.cot_contracts import BY_KEY, MARKETS
from lib.cot_data import normalize_frame
from lib.cot_publication import align_released, legacy_series
from tests.test_cot_data import row, NOW


def history(n=156):
    dates = pd.date_range(end="2026-10-06", periods=n, freq="W-TUE")
    raws = []
    for i, d in enumerate(dates):
        r = row(); r['report_date_as_yyyy_mm_dd'] = d.isoformat()
        r['noncomm_positions_long_all'] = str(10 + i % 40)
        r['comm_positions_long_all'] = str(60 - i % 40)
        raws.append(r)
    return normalize_frame(raws, 'legacy', code='209742', observed_at=NOW)


def test_weekly_ranks_and_ties():
    assert percentile(pd.Series(range(156))) == (100.0, 156)
    assert percentile(pd.Series(range(155, -1, -1))) == (0.0, 156)
    assert percentile(pd.Series([10.0] * 156)) == (50.0, 156)
    assert percentile(pd.Series(range(51))) == (None, 51)
    assert percentile(pd.Series([1.0] * 155 + [np.nan]))[0] is None


@pytest.mark.parametrize('score,level,side', [(0,'extreme','low'),(5,'extreme','low'),(6,'setup','low'),(10,'setup','low'),(12,'watch','low'),(15,'watch','low'),(50,'neutral',None),(85,'watch','high'),(90,'setup','high'),(95,'extreme','high'),(None,'unavailable',None)])
def test_tier_is_relative_positioning_not_trade_direction(score,level,side):
    assert tier(score) == {'level':level,'relative_side':side}


def test_all_21_rows_survive_missing_data():
    p = build_snapshot(now=NOW, reader=lambda *_: None)
    assert len(p['markets']) == 21
    assert p['coverage']['unavailable'] == 21
    assert not any(p['authority'].values())
    assert not p['method']['is_trade_recommendation']
    assert 'NaN' not in json.dumps(p, allow_nan=False)


def test_history_counts_weekly_reports_and_keeps_absolute_direction():
    f = history(64)
    v = family_view(f, BY_KEY['nasdaq'], 'legacy', pd.Timestamp(NOW))
    assert v['state'] == 'current'
    assert v['cohorts']['noncommercial']['history_observations'] == 64
    assert len(v['history']) == 64
    assert not v['original_vintage_certified']
    assert v['history_basis'].startswith('latest_revised')


def test_unobserved_snapshot_cannot_see_a_later_fetch():
    v = family_view(history(), BY_KEY['nasdaq'], 'legacy', pd.Timestamp('2026-10-09T19:31:00Z'))
    assert v['state'] == 'unavailable'
    assert v['null_reason'] == 'no_observed_version_available'


def test_late_report_is_not_freshened_by_a_new_page_build():
    v = family_view(history(), BY_KEY['nasdaq'], 'legacy', pd.Timestamp('2026-10-16T20:00:00Z'))
    assert v['state'] == 'awaiting_update'
    assert v['report_asof_date'] == '2026-10-06'
    v = family_view(history(), BY_KEY['nasdaq'], 'legacy', pd.Timestamp('2026-11-01T20:00:00Z'))
    assert v['state'] == 'stale'


def test_wrong_contract_and_missing_columns_fail_closed():
    f = history(); f['cftc_contract_market_code'] = '13874A'
    assert family_view(f, BY_KEY['nasdaq'], 'legacy', pd.Timestamp(NOW))['null_reason'] == 'source_identity_conflict'
    assert family_view(f[['net_spec_pct_oi']], BY_KEY['nasdaq'], 'legacy', pd.Timestamp(NOW))['state'] == 'unavailable'


def test_native_commodity_and_fx_loaders_observe_shutdown_lag(monkeypatch):
    from engine import commodity_inputs, forex_inputs
    f = pd.DataFrame({'net_spec_pct_oi': [-10.0]}, index=pd.to_datetime(['2025-09-30']))
    for module in [commodity_inputs, forex_inputs]:
        monkeypatch.setattr(module, 'read_legacy_frame', lambda *_: f)
        s = module.load_cot_positioning('cot_gold')
        assert s.index[0] == pd.Timestamp('2025-11-20')
        assert align_released(s, pd.to_datetime(['2025-10-03'])).isna().all()


def test_native_btc_loader_does_not_shift_other_sources(monkeypatch):
    from engine import btc_inputs
    f = pd.DataFrame({'net_spec_pct_oi': [-10.0]}, index=pd.to_datetime(['2025-09-30']))
    monkeypatch.setattr(btc_inputs, 'read_legacy_frame', lambda *_: f)
    assert btc_inputs._col('cot', 'cot_bitcoin', 'net_spec_pct_oi').index[0] == pd.Timestamp('2025-11-20')
    monkeypatch.setattr(btc_inputs.store, 'read', lambda *_: f)
    assert btc_inputs._col('yahoo', 'TEST', 'net_spec_pct_oi').index[0] == pd.Timestamp('2025-09-30')


def test_native_positioning_accepts_weekend_publication():
    from engine.commodity_signals import positioning
    s = pd.Series(range(170), index=pd.date_range('2023-01-07',periods=170,freq='W-SAT'),dtype=float)
    idx = pd.bdate_range(s.index[0],s.index[-1]+pd.Timedelta(days=2))
    p = positioning(s,idx,{'pctile_lookback_d':52,'crowded_long_pctile':.85,'crowded_short_pctile':.15})
    assert p['pos_net_pct_oi'].iloc[-1] == 169
    assert not p['pos_pctile'].isna().all()
