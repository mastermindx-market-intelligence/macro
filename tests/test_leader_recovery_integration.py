"""Recovery additions must preserve incumbent Leader Radar state and data ownership."""
from pathlib import Path
import json
import os
from unittest.mock import patch
import pytest
from tests.test_build_leader_radar import _build_fixture_root
from scripts.build_leader_radar import build
import re

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from engine.leader_recovery import LABELS, RecoverySpec, describe_recovery, recovery_roster


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


# ---------------------------------------------------------------------------
# WP2: the recovery panel on leader_radar.html consumes leader_recovery.v1 /
# leader_recovery_roster.v1 as a descriptive observation tier. These tests pin
# that the page renders plain words with paired dates for every episode state,
# discloses empty / stale / partial / behind-clock honestly, disappears without
# the roster schema, and that its order is navigation rather than authority.
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[1]
_SPEC = RecoverySpec(high_window=60, fast_window=10, slow_window=40, rs_window=5, confirm_sessions=3)
_CFG = {
    "storage": {"data_dir": "data", "site_dir": "site"},
    "leader_radar": {"enabled": True, "basket_keys": ["mag7"], "dow30": []},
}
_PANEL_START = 'aria-label="Deep corrections and recovery"'
_ZH = {
    "UNAVAILABLE": "修复证据不可用",
    "NO_PRIOR_LEADER": "未观察到先前领导地位",
    "ACTIVE_LEADER": "观察到领导地位",
    "CORRECTING": "领导股回调中",
    "DAMAGED": "领导地位受损",
    "REBUILDING": "修复尝试中",
    "REIGNITING": "趋势与相对强度修复中",
    "REPAIR_PAUSED": "修复暂停，领导地位未确认",
    "PRICE_RECOVERED_RS_LAGGING": "价格已恢复，相对领导地位未恢复",
    "LEADERSHIP_REESTABLISHED": "价格与相对领导地位已恢复",
    "FAILED_REPAIR": "修复尝试失败",
}
_TAILS = {
    "DAMAGED": (np.r_[np.linspace(99, 55, 25), np.full(100, 55.0)], None),
    "FAILED_REPAIR": (np.r_[np.linspace(99, 55, 30), np.linspace(56, 85, 20), 54], None),
    "PRICE_RECOVERED_RS_LAGGING": (
        np.r_[np.linspace(99, 55, 30), np.linspace(56, 115, 40)],
        np.linspace(100, 145, 40),
    ),
    "RESTORED": (np.r_[np.linspace(99, 55, 30), np.linspace(56, 110, 40)], None),
}
_EXPECTATIONS = {
    "schema": "leader_recovery_expectations.v1",
    "availability": "SOURCE_DATED_OBSERVATIONS",
    "reason": None,
    "source": "revisions_snapshot",
    "source_date": "2026-09-30",
    "source_age_sessions": 7,
    "readings": {"rev_fy1_30d": 0.03},
    "quality_flags": [],
    "revision_direction": "POSITIVE_OBSERVATIONS",
    "thesis_state": "UNKNOWN",
    "basis": "fixture",
    "disclosure": "Snapshot observations, not actual reported revenue growth or a thesis verdict.",
}


def _render(payload):
    env = Environment(loader=FileSystemLoader(str(_REPO / "templates")), autoescape=False)
    return env.get_template("leader_radar.html.j2").render(leader_radar=payload)


def _panel(html):
    start = html.find(_PANEL_START)
    if start < 0:
        return ""
    return html[start : html.find("</section>", start)]


def _artifact(tmp_path):
    root = _build_fixture_root(tmp_path, ["AAPL", "MSFT"])
    with (
        patch("lib.config.ROOT", root),
        patch("lib.config.data_dir", lambda: root / "data"),
        patch("lib.config.load", lambda: _CFG),
        patch.dict(os.environ, {"COLLECT_LANE": "express"}),
    ):
        build(data_root=root / "data", site_root=root / "site")
    return json.loads((root / "site" / "leaderradar" / "radar.json").read_text())


def _synthetic(tail, bench_tail=None, end="2026-10-09"):
    values = np.r_[np.linspace(50, 100, 90), np.asarray(tail)]
    idx = pd.bdate_range(end=end, periods=len(values))
    close = pd.Series(values, index=idx)
    bench = pd.Series(100.0, index=idx)
    if bench_tail is not None:
        bench.iloc[-len(bench_tail) :] = np.asarray(bench_tail)
    return describe_recovery(close, bench, as_of=close.index[-1].date(), sessions=list(close.index.date), spec=_SPEC)


def _payload(recs, *, stale=False, clock=None):
    rows = [{"ticker": ticker, "display_chips": {"leader_recovery": rec}} for ticker, rec in recs]
    roster = recovery_roster(rows, as_of="2026-10-09", stale=stale)
    if clock is not None:
        roster["additive_clock"] = clock
    return {"as_of": "2026-10-09", "rows": rows, "recovery_roster": roster}


def test_recovery_panel_renders_from_builder_artifact(tmp_path):
    disk = _artifact(tmp_path)
    roster = disk["recovery_roster"]
    assert roster["schema"] == "leader_recovery_roster.v1"
    panel = _panel(_render(disk))
    assert panel, "recovery panel missing from the rendered page"
    assert f'<span class="section-count">{len(roster["rows"])}</span>' in panel
    assert ('class="lr-rec-row"' in panel) or ("mx-empty-line" in panel)
    assert "Reconstructed from today's data, not first-seen." in panel
    assert "It sets no rank, size, alert or entry." in panel
    # the page never promotes the descriptive tier: no authority flag is rendered true
    assert "authority" not in panel.lower() or "true" not in panel.lower()


@pytest.mark.parametrize("name", ["DAMAGED", "FAILED_REPAIR", "PRICE_RECOVERED_RS_LAGGING", "RESTORED"])
def test_recovery_panel_states_render_plain_words_and_paired_dates(name):
    tail, bench_tail = _TAILS[name]
    rec = _synthetic(tail, bench_tail)
    rec["expectations"] = dict(_EXPECTATIONS)
    expected = {"ACTIVE_LEADER", "LEADERSHIP_REESTABLISHED"} if name == "RESTORED" else {name}
    assert rec["state"] in expected
    episode = rec["episode"]
    panel = _panel(_render(_payload([("TEST", rec)])))
    start = panel.find('data-ticker="TEST"')
    assert start >= 0
    row = panel[start:]
    assert f'data-state="{rec["state"]}"' in row
    assert 'class="rs-highs-ticker" href="us_stocks.html#TEST"' in row
    assert LABELS[rec["state"]] in row
    assert _ZH[rec["state"]] in row
    # the raw state key appears only in the data attribute, never as visible copy
    assert row.replace(f'data-state="{rec["state"]}"', "").count(rec["state"]) == 0
    # paired dates: the leadership peak and the trough it fell to
    assert episode["peak_on"] in row and episode["trough_on"] in row
    assert "Failed attempts" in row
    assert f'<b>{episode["failed_repairs"]}' in row
    if name in {"DAMAGED", "FAILED_REPAIR"}:
        assert "Stand aside" in row
    else:
        assert "Watch, don't chase" in row
    # dated estimate evidence is shown as observations with its source date, never as a thesis verdict
    assert "Source dated 2026-09-30" in row
    assert "rising" in row
    assert "Snapshot observations, not actual reported revenue growth or a thesis verdict." in row
    assert "Fundamental read not sourced." in row


def test_recovery_panel_discloses_empty_stale_clock_and_partial():
    clock = {
        "as_of": "2026-10-09",
        "incumbent_as_of": "2026-10-08",
        "lag_sessions": 1,
        "basis": "fixture",
        "universe_rows": 1,
        "rows_at_or_after_clock": 1,
        "rows_behind_clock": 0,
    }
    unavailable = {"schema": "leader_recovery.v1", "state": "UNAVAILABLE"}
    panel = _panel(_render(_payload([("UNAV", unavailable)], stale=True, clock=clock)))
    assert panel
    assert 'class="lr-rec-row"' not in panel
    assert "No deep corrections on record" in panel
    assert "mx-empty-why" in panel
    assert "Source stale" in panel
    assert "session behind" in panel
    assert "Recovery evidence unavailable for 1 name(s)." in panel


def test_recovery_panel_absent_without_roster_schema():
    assert _panel(_render({})) == ""
    assert _panel(_render(None)) == ""
    foreign = {"as_of": "2026-10-09", "rows": [], "recovery_roster": {"schema": "something_else.v9", "rows": []}}
    assert _panel(_render(foreign)) == ""


def test_recovery_panel_order_is_navigation_not_authority():
    recs = []
    for name in ("DAMAGED", "FAILED_REPAIR", "PRICE_RECOVERED_RS_LAGGING"):
        tail, bench_tail = _TAILS[name]
        recs.append((name[:4], _synthetic(tail, bench_tail)))
    panel = _panel(_render(_payload(recs)))
    found = re.findall(r'data-ticker="([A-Z]+)"[^>]*data-depth="([0-9.]+)"', panel)
    assert len(found) == 3
    depths = [float(depth) for _, depth in found]
    assert depths == sorted(depths, reverse=True), "default order is deepest correction first"
    assert "Order by" in panel
    assert "Order is navigation, not a ranking." in panel
    visible = re.sub(r"<[^>]+>", " ", panel)
    for banned in ("validated", "falsifier", "refuted", "z-score", "percentile", "score", "buy", "sell"):
        assert not re.search(rf"\b{re.escape(banned)}\b", visible), banned
    assert "证伪" not in visible
