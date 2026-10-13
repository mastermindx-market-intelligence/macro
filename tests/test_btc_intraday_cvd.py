"""Intraday aggressor-CVD collector parsing + engine (display-only).

Run: .venv/bin/python -m tests.test_btc_intraday_cvd
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from collectors.okx import OkxAdapter  # noqa: E402
from engine import btc_intraday_cvd as CVD  # noqa: E402


class _Resp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return {"code": "0", "data": self._d}


def test_collector_parses_hourly_buy_sell():
    a = OkxAdapter()
    # rubik returns NEWEST-FIRST rows [ts_ms, sellVol, buyVol]
    rows = [[str(1_700_000_000_000 + i * 3_600_000), str(100 + i), str(200 + i)] for i in range(6)]
    rows = rows[::-1]
    a.http_get = lambda *args, **kw: _Resp(rows)
    df = a._taker_volume_hourly()
    assert list(df.columns) == ["taker_buy_vol", "taker_sell_vol"]
    assert df.index.is_monotonic_increasing
    # buy (200+) must exceed sell (100+) — confirms column order not flipped
    assert (df["taker_buy_vol"] > df["taker_sell_vol"]).all()
    # hourly cadence preserved (not normalized to dates)
    assert (df.index.to_series().diff().dropna() == pd.Timedelta(hours=1)).all()


def test_collector_empty_returns_none():
    a = OkxAdapter()
    a.http_get = lambda *args, **kw: _Resp([])
    assert a._taker_volume_hourly() is None


def test_validate_preserves_hourly_normalizes_daily():
    """THE accrual-killer guard: run_adapter calls adapter.validate() BEFORE
    upsert, and the BASE validate normalizes every index to dates. The OKX
    override MUST exempt taker_volume_hourly (else 24 rows/day collapse to 1 and
    the sub-daily CVD silently dies), while still normalizing daily series."""
    a = OkxAdapter()
    idx = pd.date_range("2026-06-01", periods=48, freq="h")
    hourly = pd.DataFrame({"taker_buy_vol": [1.0] * 48, "taker_sell_vol": [1.0] * 48}, index=idx)
    vh = a.validate("taker_volume_hourly", hourly)
    assert len(vh) == 48                                   # NOT collapsed to 2 days
    assert (vh.index.minute == 0).all()                    # intraday timestamps kept
    daily = pd.DataFrame({"x": [1.0] * 48}, index=idx)
    assert len(a.validate("funding_rate", daily)) == 2     # daily series still normalized


def _store_patch(frames):
    orig = CVD.store.read
    CVD.store.read = lambda ns, nm: frames.get((ns, nm))
    return orig


def _hourly(n, buy, sell, start="2026-01-01"):
    idx = pd.date_range(start, periods=n, freq="h")
    return pd.DataFrame({"taker_buy_vol": np.asarray(buy, dtype=float),
                         "taker_sell_vol": np.asarray(sell, dtype=float)}, index=idx)


def test_engine_accruing_and_distribution_state():
    n = 800                                          # < MIN_HOURS_DIV -> accruing
    buy = np.full(n, 1e7)                            # realistic ~1e7 hourly volume
    sell = np.full(n, 1e7); sell[-24:] = 3e7         # heavy net selling last 24h
    df = _hourly(n, buy, sell)
    orig = _store_patch({("okx", "taker_volume_hourly"): df})
    try:
        o = CVD.compute(as_of=df.index[-1].tz_localize("UTC"))
    finally:
        CVD.store.read = orig
    assert o["ok"] and o["accruing"] is True
    assert o["flow_state"] == "sell_dominant"         # net aggressor selling
    assert o["net_flow_24h_native"] < 0
    assert o["net_flow_24h_mn"] is None
    assert o["divergence"] is None                   # not enough history


def test_engine_divergence_when_history_sufficient():
    n = 1600                                          # > MIN_HOURS_DIV
    rng = np.random.default_rng(0)
    buy = 1e7 + rng.normal(0, 5e5, n)
    sell = 1e7 + rng.normal(0, 5e5, n)
    # price firm/up while flow turns net-negative -> "hidden distribution" lean
    sell[-200:] += 4e6
    cvd_df = _hourly(n, buy, sell)
    rets = 0.0002 + rng.normal(0, 0.003, n)          # noisy uptrend (nonzero return variance)
    price = pd.DataFrame({"close": 60000 * np.cumprod(1 + rets)}, index=cvd_df.index)
    orig = _store_patch({("okx", "taker_volume_hourly"): cvd_df, ("coinbase", "btc_hourly"): price})
    try:
        o = CVD.compute(as_of=cvd_df.index[-1].tz_localize("UTC"))
    finally:
        CVD.store.read = orig
    assert o["ok"] and o["accruing"] is False
    assert o["divergence"] is not None
    assert 0.0 <= o["divergence"]["pctile"] <= 1.0
    assert o["divergence"]["state"] in ("price_flow_high", "price_flow_low", "none")


def test_engine_stale_when_hourly_lags_reference():
    """Audit HIGH: a silently-frozen okx hourly feed must be FLAGGED stale by
    comparing it to the live coinbase intraday reference."""
    n = 800
    cvd_df = _hourly(n, np.full(n, 1e7), np.full(n, 1e7))
    ref_idx = pd.date_range(cvd_df.index[-1] + pd.Timedelta(days=5), periods=10, freq="h")
    ref = pd.DataFrame({"close": [60000.0] * 10}, index=ref_idx)        # reference 5d ahead
    orig = _store_patch({("okx", "taker_volume_hourly"): cvd_df, ("coinbase", "btc_hourly"): ref})
    try:
        o = CVD.compute()
    finally:
        CVD.store.read = orig
    assert o["stale"] is True and o["hours_behind_ref"] > 48


def test_engine_gap_detection_restarts_cumsum():
    """Audit MEDIUM: a gap wider than the rubik window can't be backfilled, so the
    cumsum must restart after it (not silently span a permanent hole)."""
    a = pd.date_range("2026-01-01", periods=100, freq="h")
    b = pd.date_range(a[-1] + pd.Timedelta(hours=800), periods=200, freq="h")   # 800h > 720h gap
    idx = a.append(b)
    cvd_df = pd.DataFrame({"taker_buy_vol": np.full(300, 1e7),
                           "taker_sell_vol": np.full(300, 1.2e7)}, index=idx)
    orig = _store_patch({("okx", "taker_volume_hourly"): cvd_df})
    try:
        o = CVD.compute()
    finally:
        CVD.store.read = orig
    assert o["gap_detected"] is True
    assert o["n_hours"] == 200            # only the post-gap contiguous segment counts


def test_engine_no_store_degrades():
    orig = _store_patch({})
    try:
        o = CVD.compute()
    finally:
        CVD.store.read = orig
    assert o["ok"] is False and o["accruing"] is True


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")


# R11: precise elapsed support and descriptive-only source semantics.
def test_r11_short_gap_cannot_be_called_a_complete_24_hour_window(monkeypatch):
    h=_hourly(25,np.ones(25),np.full(25,2.)).drop(pd.Timestamp('2026-01-01 20:00'))
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    out=CVD.compute(as_of='2026-01-02T02:00:00Z')
    assert out['gap_detected'] and not out['ok'] and out['n_hours']==4
    assert out['net_flow_24h_native'] is None and out['net_flow_72h_native'] is None
    assert out['flow_state']=='unavailable'


def test_r11_future_data_never_changes_a_historical_flow_view(monkeypatch):
    h=_hourly(800,np.full(800,3.),np.ones(800));cut=h.index[-1]
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    a=CVD.compute(as_of=cut.tz_localize('UTC'))
    extra=_hourly(20,np.full(20,1e15),np.ones(20),start=cut+pd.Timedelta(hours=1))
    future=pd.concat([h,extra]);monkeypatch.setattr(CVD.store,'read',lambda ns,nm:future if ns=='okx' else None)
    assert CVD.compute(as_of=cut.tz_localize('UTC'))==a


def test_r11_zero_activity_and_balanced_activity_are_not_missing(monkeypatch):
    zero=_hourly(800,np.zeros(800),np.zeros(800))
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:zero if ns=='okx' else None)
    out=CVD.compute(as_of=zero.index[-1].tz_localize('UTC'))
    assert out['ok'] and out['net_flow_24h_native']==0 and out['buy_share_24h'] is None
    assert out['flow_state']=='no_activity'
    balanced=zero+2;monkeypatch.setattr(CVD.store,'read',lambda ns,nm:balanced if ns=='okx' else None)
    out=CVD.compute(as_of=zero.index[-1].tz_localize('UTC'))
    assert out['buy_share_24h']==.5 and out['flow_state']=='balanced'


def test_r11_invalid_or_duplicate_flow_is_not_sanitized_to_neutral(monkeypatch):
    h=_hourly(800,np.ones(800),np.ones(800));h.iloc[-1,0]=-1
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    out=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert not out['ok'] and out['net_flow_24h_native'] is None
    dup=pd.concat([h,h.tail(1)]);monkeypatch.setattr(CVD.store,'read',lambda ns,nm:dup if ns=='okx' else None)
    assert not CVD.compute(as_of=h.index[-1].tz_localize('UTC'))['ok']


def test_r11_equal_old_sources_are_stale_against_wall_clock(monkeypatch):
    h=_hourly(800,np.full(800,3.),np.ones(800));px=pd.DataFrame({'close':10.},index=h.index)
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else px)
    out=CVD.compute(as_of=(h.index[-1]+pd.Timedelta(days=4)).tz_localize('UTC'))
    assert out['stale'] and out['hours_behind_ref']==0 and out['hours_behind_clock']==96
    assert out['flow_state']=='unavailable'


def test_r11_unknown_volume_units_never_turn_into_dollars(monkeypatch):
    h=_hourly(800,np.full(800,1e9),np.full(800,2e9))
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    out=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert out['scope']=='OKX/BTC/CONTRACTS' and out['volume_unit'] is None
    assert out['net_flow_24h_native']==-24e9 and out['net_flow_24h_mn'] is None and out['cvd_last_bn'] is None
    assert out['display_only'] is True and out['causally_qualified'] is False
    assert 'leading' not in out['note'].lower()


def test_r11_missing_price_hour_blocks_divergence_instead_of_forward_fill(monkeypatch):
    n=1600;rng=np.random.default_rng(4);h=_hourly(n,10+rng.random(n),10+rng.random(n))
    px=pd.DataFrame({'close':60000*np.exp(np.cumsum(rng.normal(0,.003,n)))},index=h.index).drop(h.index[-10])
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else px)
    out=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert out['ok'] and out['divergence'] is None and out['price_alignment_complete'] is False


def test_r11_legacy_diagnostic_is_pinned_while_current_gap_guard_is_fixed(monkeypatch):
    from research.crypto_science.r10_source_qualification import legacy_gap_example
    legacy=legacy_gap_example()
    assert legacy['reference_commit']=='d636e9c405c0283209eb75b09d477d32003ff827'
    assert legacy['incumbent_gap_detected'] is False
    h=_hourly(25,np.full(25,2.),np.ones(25)).drop(pd.Timestamp('2026-01-01 12:00'))
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    current=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert current['gap_detected'] is True and current['window_24h_complete'] is False


def test_r11_undated_flow_cannot_be_dropped_as_though_outside_the_cutoff(monkeypatch):
    h=_hourly(200,np.full(200,2.),np.ones(200))
    h=pd.concat([h,pd.DataFrame({'taker_buy_vol':[2.],'taker_sell_vol':[1.]},index=[pd.NaT])])
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    out=CVD.compute(as_of='2026-02-01T00:00:00Z')
    assert not out['ok'] and out['causally_qualified'] is False


def test_r11_boolean_flow_is_not_a_measured_unit(monkeypatch):
    h=_hourly(200,np.full(200,2.),np.ones(200)).astype(object)
    h.iloc[-1,0]=True
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    out=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert not out['ok'] and out['window_24h_complete'] is False


def test_r11_asof_is_timezone_normalized_without_using_future_rows(monkeypatch):
    h=_hourly(200,np.full(200,2.),np.ones(200))
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:h if ns=='okx' else None)
    t=h.index[-3].tz_localize('UTC')
    a=CVD.compute(as_of=t);b=CVD.compute(as_of=t.tz_convert('America/New_York'))
    assert a==b and a['stored_rows']==198
    assert a['causally_qualified'] is False and a['net_flow_24h_mn'] is None


def test_r11_builder_warnings_do_not_mislabel_short_gaps_or_stale_snapshots():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'scripts/build_vector.py').read_text()
    section=source.split('_cvd = legs.get("intraday_cvd")',1)[1].split('try:',1)[0]
    assert 'hours_behind_clock' in section
    assert 'unbackfillable >30d' not in section
    assert 'STOPPED accruing' not in section
    assert 'if _cvd.get("gap_detected"):' in section
    assert 'missing or invalid hourly observations' in section


# R12 integrates the previously sandbox-only review into the existing test owner.
def _r12_reference_case(monkeypatch):
    t = np.arange(1800)
    ix = pd.date_range('2026-01-01', periods=len(t), freq='h')
    h = pd.DataFrame({'taker_buy_vol':100+10*np.sin(t/19),
                      'taker_sell_vol':100+7*np.cos(t/31)}, index=ix)
    p = pd.DataFrame({'close':60000+20*t+1000*np.sin(t/27)}, index=ix)
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:p if ns=='coinbase' else h)
    before=CVD.compute(as_of=ix[-1].tz_localize('UTC'))
    assert before['price_alignment_complete'] and before['divergence'] is not None
    return h,p,before


def test_r12_boolean_reference_price_withholds_divergence_only(monkeypatch):
    h,p,before=_r12_reference_case(monkeypatch)
    for bad in (True,np.bool_(True),False,np.bool_(False)):
        for offset in (0,12,24):
            broken=p.astype(object).copy();broken.iloc[-1-offset,0]=bad
            monkeypatch.setattr(CVD.store,'read',lambda ns,nm:broken if ns=='coinbase' else h)
            after=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
            assert after['ok'] and after['causally_qualified'] is False
            assert after['price_alignment_complete'] is False
            assert after['divergence'] is None
            for key in ['net_flow_24h_native','net_flow_72h_native','buy_share_24h']:
                assert after[key]==before[key]


def test_r12_numeric_reference_prices_are_not_confused_with_boolean(monkeypatch):
    h,p,before=_r12_reference_case(monkeypatch)
    for valid in (1,1.0,np.float64(1),str(p.close.iloc[-1])):
        changed=p.astype(object).copy();changed.iloc[-1,0]=valid
        monkeypatch.setattr(CVD.store,'read',lambda ns,nm:changed if ns=='coinbase' else h)
        after=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
        assert after['price_alignment_complete'] is True
        assert after['net_flow_24h_native']==before['net_flow_24h_native']


import pytest


def test_r12_future_and_outside_dependency_boolean_does_not_poison_current_view(monkeypatch):
    h,p,before=_r12_reference_case(monkeypatch)
    cutoff=h.index[-2].tz_localize('UTC')
    prior=CVD.compute(as_of=cutoff)
    bad=p.astype(object);bad.iloc[-1,0]=True
    monkeypatch.setattr(CVD.store,'read',lambda ns,nm:bad if ns=='coinbase' else h)
    assert CVD.compute(as_of=cutoff)==prior
    bad=p.astype(object);bad.iloc[0,0]=True
    out=CVD.compute(as_of=h.index[-1].tz_localize('UTC'))
    assert out['price_alignment_complete'] is True and out['divergence'] is not None


@pytest.mark.parametrize('n',[23,24,72,1512,1800])
@pytest.mark.parametrize('seed',[13,29])
@pytest.mark.parametrize('shape',['numeric','string_price','flow_gap','null_volume','no_price','stale_clock'])
def test_r12_unchanged_numeric_coverage_and_freshness(monkeypatch,n,seed,shape):
    import hashlib
    from types import ModuleType,SimpleNamespace
    reference=Path(__file__).resolve().parents[1]/'research/crypto_science/r12/reference_cvd_before_price_guard.py.txt'
    raw=reference.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='12117869d18239cdffd4d70b0c6906ba8a51bf140894c860e07321db2a8420a9'
    old=ModuleType('r12_original_cvd');exec(compile(raw,str(reference),'exec'),old.__dict__)
    rng=np.random.default_rng(seed);ix=pd.date_range('2026-01-01',periods=n,freq='h')
    h=pd.DataFrame({'taker_buy_vol':rng.uniform(0,10,n),'taker_sell_vol':rng.uniform(0,10,n)},index=ix)
    p=pd.DataFrame({'close':60000+np.cumsum(rng.normal(0,20,n))},index=ix);clock=ix[-1].tz_localize('UTC')
    if shape=='string_price':p['close']=p.close.astype(str)
    elif shape=='flow_gap':h=h.drop(ix[n//2])
    elif shape=='null_volume':h.iloc[-1,0]=np.nan
    elif shape=='no_price':p=pd.DataFrame()
    elif shape=='stale_clock':clock+=pd.Timedelta(hours=72)
    reader=lambda ns,nm:p.copy() if ns=='coinbase' else h.copy()
    old.store=SimpleNamespace(read=reader);monkeypatch.setattr(CVD.store,'read',reader)
    assert CVD.compute(as_of=clock)==old.compute(as_of=clock)
