"""Recovery additions must preserve incumbent Leader Radar state and data ownership."""
from pathlib import Path
import json
import os
from unittest.mock import patch
import pytest
from tests.test_build_leader_radar import _build_fixture_root
from scripts.build_leader_radar import build


def test_builder_emits_recovery_without_advancing_data_stores(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    before={str(p.relative_to(root)):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}):
        result=build(data_root=root/'data',site_root=root/'site')
    assert len(result['rows'])==2
    assert result['recovery_roster']['population_rows']==2
    assert sum(result['recovery_roster']['counts'].values())==2
    for row in result['rows']:
        r=row['display_chips']['leader_recovery']
        assert r['schema']=='leader_recovery.v1'
        assert r['as_of']==result['as_of']
        assert not any(r['authority'].values())
        assert r['fundamental_thesis']['state']=='UNKNOWN'
        assert r['expectations']['schema']=='leader_recovery_expectations.v1'
        assert r['expectations']['thesis_state']=='UNKNOWN'
    assert json.loads((root/'site/leaderradar/radar.json').read_text())['recovery_roster']==result['recovery_roster']
    after={str(p.relative_to(root)):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    assert before==after


def test_optional_recovery_failure_cannot_remove_incumbent_rows(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}),patch('engine.leader_recovery.describe_recovery',side_effect=ValueError('bad optional projection')):
        result=build(data_root=root/'data',site_root=root/'site')
    assert len(result['rows'])==2
    assert result['recovery_roster']['counts']['UNAVAILABLE']==2
    assert all(r['display_chips']['leader_recovery']['reason']=='projection_error' for r in result['rows'])


def test_expectation_failure_does_not_destroy_price_recovery(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}),patch('engine.leader_recovery_expectations.project_expectations',side_effect=ValueError('bad optional source')):
        result=build(data_root=root/'data',site_root=root/'site')
    assert len(result['rows'])==2
    for row in result['rows']:
        d=row['display_chips']['leader_recovery']
        assert d['reason']!='projection_error'
        assert d['expectations']['reason']=='projection_error'


def test_native_nightly_capture_is_opt_in_and_idempotent(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    cfg={'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[],'recovery_capture_enabled':True}}
    from engine.leader_recovery_observations import COLUMNS
    import pandas as pd
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:cfg),patch.dict(os.environ,{'COLLECT_LANE':'nightly'}):
        payload=build(data_root=root/'data',site_root=root/'site')
        p=root/'data/leader_radar/state_history.parquet';first=pd.read_parquet(p)
        assert len(first)==2 and first[COLUMNS[2]].notna().all()
        assert all(json.loads(x)['source_first_seen_proven'] is False for x in first[COLUMNS[1]])
        build(data_root=root/'data',site_root=root/'site')
        second=pd.read_parquet(p)
        assert second[COLUMNS[2]].tolist()==first[COLUMNS[2]].tolist()
        cfg['leader_radar']['recovery_capture_enabled']=False
        build(data_root=root/'data',site_root=root/'site')
        third=pd.read_parquet(p)
        assert third[COLUMNS[2]].tolist()==first[COLUMNS[2]].tolist()


def test_additive_layer_clock_follows_universe_when_spy_leads(tmp_path, capsys):
    """SPY's store can lead the issuer stores by one session (measured on main 2026-10-11: SPY
    2026-10-09, every issuer 2026-10-08). The incumbent as_of keeps following SPY, while the
    fail-closed additive layer observes at the latest session the universe actually completed
    and reports the lag — never a blanket UNAVAILABLE / unknown universe."""
    import hashlib
    import pandas as pd
    from datetime import timedelta
    from lib.nyse_calendar import sessions_between
    from tests.test_build_leader_radar import _make_ohlcv
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    spy=_make_ohlcv(401,seed=99)[['close']]
    spy.to_parquet(root/'data/yahoo/SPY.parquet')
    issuer_last=pd.to_datetime(pd.read_parquet(root/'data/baskets/ohlcv/AAPL.parquet').index).max().date()
    spy_last=pd.to_datetime(spy.index).max().date()
    assert spy_last>issuer_last
    expected_lag=len(sessions_between(issuer_last+timedelta(days=1),spy_last))
    assert expected_lag>=1
    files=sorted(p for p in (root/'data').rglob('*') if p.is_file())
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}):
        result=build(data_root=root/'data',site_root=root/'site')
    out=capsys.readouterr().out
    # incumbent clock untouched: still SPY's last completed session
    assert result['as_of']==spy_last.isoformat()
    assert len(result['rows'])==2
    for roster_key in ('recovery_roster','rs_high_roster'):
        clock=result[roster_key]['additive_clock']
        assert clock['as_of']==issuer_last.isoformat()
        assert clock['incumbent_as_of']==spy_last.isoformat()
        assert clock['lag_sessions']==expected_lag
        assert clock['basis']=='universe_majority_completed_session'
        assert clock['universe_rows']==clock['rows_at_or_after_clock']==2 and clock['rows_behind_clock']==0
        assert result[roster_key]['as_of']==spy_last.isoformat()  # roster header keeps the incumbent clock
    assert result['rs_high_roster']['clock_as_of']['daily']==issuer_last.isoformat()
    assert result['recovery_roster']['counts'].get('UNAVAILABLE',0)==0
    for r in result['rows']:
        rec=r['display_chips']['leader_recovery']
        assert rec['as_of']==issuer_last.isoformat()
        assert rec['state']!='UNAVAILABLE' and rec.get('reason')!='missing_or_invalid_completed_session'
        assert rec['expectations']['as_of']==issuer_last.isoformat()
        hi=r['display_chips']['rs_high_watch']
        assert hi['as_of']==issuer_last.isoformat()
        assert hi['daily']['new_high'] is not None and hi['weekly']['new_high'] is not None
    # the lag is announced as a GitHub annotation that STARTS the line (house law), via bare print
    assert any(line.startswith('::warning title=leader_radar_additive_clock::') for line in out.splitlines())
    disk=json.loads((root/'site/leaderradar/radar.json').read_text())
    assert disk['recovery_roster']==result['recovery_roster'] and disk['rs_high_roster']==result['rs_high_roster']
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert before==after


def test_additive_layer_clock_equals_incumbent_when_stores_align(tmp_path, capsys):
    """When every store ends on the same session the additive clock IS the incumbent clock, the lag is
    zero and no annotation is printed (the aligned fixture path stays byte-identical in behaviour)."""
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}):
        result=build(data_root=root/'data',site_root=root/'site')
    out=capsys.readouterr().out
    for roster_key in ('recovery_roster','rs_high_roster'):
        clock=result[roster_key]['additive_clock']
        assert clock['as_of']==result['as_of']==clock['incumbent_as_of']
        assert clock['lag_sessions']==0 and clock['rows_behind_clock']==0
    assert not any('leader_radar_additive_clock' in line for line in out.splitlines())


@pytest.mark.parametrize("ahead_tickers", [("AAPL",), ("AAPL", "MSFT")])
def test_additive_clock_ignores_issuer_rows_after_spy_cut(tmp_path, ahead_tickers):
    """Independently updated issuer stores may run AHEAD of the benchmark cut. Appending a
    later row to an issuer must not move the universe-majority clock backward or change an
    existing daily-high classification whose issuer+benchmark history at or before the cut
    is identical (counterexample from the late review on PR #8750). The core engine already
    ignores observations after ``as_of``; this pins the builder's clock to the same rule."""
    from datetime import date, timedelta
    import pandas as pd
    from engine.rs_leader_highs import observe_rs_highs
    from lib.nyse_calendar import sessions_between
    from scripts.build_leader_radar import _additive_layer_clock, _load_ohlcv, _load_spy
    cut = date(2026, 10, 8)
    index = pd.to_datetime(sessions_between(cut - timedelta(days=700), cut))
    close = pd.Series(100.0, index=index)
    close.iloc[-1] = 101.0  # a strict daily RS high against a flat benchmark
    bars = pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5,
                         "close": close, "volume": 1_000_000.0}, index=index)
    frames = {"AAPL": bars.copy(), "MSFT": bars.copy(), "GOOG": bars.iloc[:-1].copy()}
    data_root = tmp_path / "data"
    issuer_dir = data_root / "baskets" / "ohlcv"
    issuer_dir.mkdir(parents=True)
    spy_dir = data_root / "yahoo"
    spy_dir.mkdir(parents=True)
    for ticker, frame in frames.items():
        frame.to_parquet(issuer_dir / f"{ticker}.parquet")
    pd.DataFrame({"close": 100.0}, index=index).to_parquet(spy_dir / "SPY.parquet")

    def load_issuers():
        loaded = {t: _load_ohlcv(t, data_root) for t in frames}
        assert all(f is not None for f in loaded.values())
        return loaded

    spy = _load_spy(data_root)
    assert spy is not None
    today = spy.index[-1].date()
    assert today == cut
    before_frames = load_issuers()
    before_clock, before_meta = _additive_layer_clock(before_frames, today)
    assert before_clock == cut  # majority (AAPL, MSFT) completed the cut session
    assert before_meta["basis"] == "universe_majority_completed_session"
    before_watch = observe_rs_highs(before_frames["MSFT"]["close"], spy, as_of=before_clock)
    assert before_watch["daily"]["new_high"] is True
    # append ONE later row (past SPY's cut) to the ahead issuers; nothing at/before the cut changes
    for ticker in ahead_tickers:
        advanced = frames[ticker].copy()
        advanced.loc[pd.Timestamp("2026-10-09")] = [102.0, 102.5, 101.5, 102.0, 1_000_000.0]
        advanced.to_parquet(issuer_dir / f"{ticker}.parquet")
    after_frames = load_issuers()
    # the engine itself is cut-stable (fixed as_of): same classification from the advanced store
    assert observe_rs_highs(after_frames["MSFT"]["close"], spy, as_of=cut) == before_watch
    # the builder's additive clock must be cut-stable too — never moved backward by a store
    # that ran ahead, and never excluding that store from the universe census
    after_clock, after_meta = _additive_layer_clock(after_frames, today)
    assert after_clock == before_clock
    assert after_meta == before_meta
    assert observe_rs_highs(after_frames["MSFT"]["close"], spy, as_of=after_clock) == before_watch
