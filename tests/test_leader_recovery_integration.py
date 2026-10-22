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


def test_nightly_capture_seals_at_the_additive_clock_when_spy_leads(tmp_path, capsys):
    """Production 2026-10-16/17: SPY led the issuer stores, the descriptors were cut at the
    additive clock but capture was keyed to the incumbent SPY date, so every lagged nightly
    raised descriptor_cut_mismatch and captured nothing. Capture follows the descriptor's own
    cut: it seals the existing native row of that session and leaves the SPY-dated row alone."""
    import pandas as pd
    from engine.leader_recovery_observations import COLUMNS
    from tests.test_build_leader_radar import _make_ohlcv
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    cfg={'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[],'recovery_capture_enabled':False}}
    p=root/'data/leader_radar/state_history.parquet'
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:cfg),patch.dict(os.environ,{'COLLECT_LANE':'nightly'}):
        aligned=build(data_root=root/'data',site_root=root/'site')  # native rows for the issuer session
        issuer_last=aligned['as_of']
        _make_ohlcv(401,seed=99)[['close']].to_parquet(root/'data/yahoo/SPY.parquet')
        cfg['leader_radar']['recovery_capture_enabled']=True
        capsys.readouterr()
        lagged=build(data_root=root/'data',site_root=root/'site')
    out=capsys.readouterr().out
    spy_last=lagged['as_of']
    assert spy_last>issuer_last
    assert lagged['recovery_roster']['additive_clock']['as_of']==issuer_last
    assert not any('recovery observation enrichment FAILED' in line for line in out.splitlines())
    h=pd.read_parquet(p);h['day']=pd.to_datetime(h['date']).dt.date.astype(str)
    sealed=h[h['day']==issuer_last]
    assert sorted(sealed.ticker)==['AAPL','MSFT'] and sealed[COLUMNS[2]].notna().all()
    assert all(json.loads(x)['as_of']==issuer_last for x in sealed[COLUMNS[1]])
    assert h[h['day']==spy_last][COLUMNS[2]].isna().all()


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


# ---------------------------------------------------------------------------
# LINEAGE-C (2026-10-17): CONSUMER_SPEC §2's chip + roster are wired into the
# builder behind `leader_radar.lineage_enabled` (default off), and the
# first-observed lineage seals ride the incumbent state_history rows beside the
# recovery seals. These tests pin the admission's invariants: flag-off is
# unchanged, flag-on is additive and display-only, seals follow the shipped
# recovery contract, and every lineage failure leaves the incumbent payload and
# state_history intact.
# ---------------------------------------------------------------------------

import hashlib
import logging
from contextlib import ExitStack
from copy import deepcopy

import yaml

from engine.leader_lineage import AUTHORITY, lineage_chip
from engine.leader_recovery_observations import COLUMNS, LINEAGE_COLUMNS, LINEAGE_SCHEMA
from tests.test_build_leader_radar import _make_ohlcv

_LIN_SEED = 20261017
_LIN_LOGGER = "scripts.build_leader_radar"
_LIN_STATE_HISTORY = "data/leader_radar/state_history.parquet"
# Enumerated explicitly (no directory walk): the incumbent data/ stores the
# Leader Radar builder owns, plus the price inputs it reads.
_LIN_DATA_FILES = (
    "data/leader_radar/state_history.parquet",
    "data/leader_radar/fire_log.parquet",
    "data/baskets/ohlcv/AAPL.parquet",
    "data/baskets/ohlcv/MSFT.parquet",
    "data/yahoo/SPY.parquet",
)
_LIN_ATTACH_WARNING = (
    "::warning title=leader_lineage::lineage layer FAILED — incumbent "
    "payload unchanged: "
)
_LIN_MERGE_WARNING = (
    "::warning title=leader_lineage::lineage observation enrichment FAILED — incumbent "
    "state_history written unchanged: "
)


def _lin_cfg(**extra):
    return {"storage": {"data_dir": "data", "site_dir": "site"},
            "leader_radar": {"enabled": True, "basket_keys": ["mag7"], "dow30": [], **extra}}


def _lin_root(base, name, tickers=("AAPL", "MSFT")):
    """A deterministic fixture root. `_build_fixture_root` draws breadth from the
    GLOBAL numpy RNG, so two unseeded roots differ and a cross-root byte
    comparison would measure the fixture rather than the flag. The RNG state is
    restored so no other test in this module is affected."""
    root = Path(base) / name
    root.mkdir(parents=True, exist_ok=True)
    state = np.random.get_state()
    try:
        np.random.seed(_LIN_SEED)
        _build_fixture_root(root, list(tickers))
    finally:
        np.random.set_state(state)
    return root


def _lin_build(root, cfg, *, lane="express", extra=()):
    with ExitStack() as stack:
        stack.enter_context(patch("lib.config.ROOT", root))
        stack.enter_context(patch("lib.config.data_dir", lambda: root / "data"))
        stack.enter_context(patch("lib.config.load", lambda: cfg))
        stack.enter_context(patch.dict(os.environ, {"COLLECT_LANE": lane}))
        for ctx in extra:
            stack.enter_context(ctx)
        return build(data_root=root / "data", site_root=root / "site")


def _stamps_out(payload):
    """A payload with its wall-clock stamps removed: `built_at`, `elapsed_s` and
    `freshness.built_at` are exactly the three keys the LR-EXP byte-stability
    carry treats as build-time dependent, and nothing else in the artifact is."""
    out = json.loads(json.dumps(payload, default=str))
    out.pop("built_at", None)
    out.pop("elapsed_s", None)
    fresh = out.get("freshness")
    if isinstance(fresh, dict):
        fresh.pop("built_at", None)
    return out


def _lin_disk(root):
    return json.loads((root / "site" / "leaderradar" / "radar.json").read_text())


def _lin_history(root):
    frame = pd.read_parquet(root / _LIN_STATE_HISTORY)
    frame["day"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    return frame


def _lin_col(frame, col):
    """NA-safe column snapshot (parquet 'string' columns hold pd.NA, whose
    equality is pd.NA rather than True, so a raw list compare would not work)."""
    if col not in frame.columns:
        return [None] * len(frame)
    return [None if pd.isna(value) else value for value in frame[col].tolist()]


def _lin_hashes(root):
    return {rel: (hashlib.sha256((root / rel).read_bytes()).hexdigest()
                  if (root / rel).exists() else None) for rel in _LIN_DATA_FILES}


def _lin_chips(payload):
    for key in ("rows", "early_entry"):
        for row in payload.get(key) or []:
            yield row.get("display_chips") or {}


def _strip_lineage(payload):
    """The flag-on artifact reduced to its flag-off shape (deep copy)."""
    out = deepcopy(payload)
    out.pop("lineage_roster")
    for chips in _lin_chips(out):
        chips.pop("leader_lineage", None)
    return out


def test_lc1_config_lineage_flag_exists_and_is_boolean():
    """The flag is shipped, and its TYPE is the contract: the activation PR flips
    the value, so this test must keep passing on both sides of that flip."""
    cfg = yaml.safe_load((_REPO / "config.yml").read_text())
    assert "lineage_enabled" in cfg["leader_radar"]
    assert type(cfg["leader_radar"]["lineage_enabled"]) is bool


def test_lc2_flag_off_leaves_the_express_payload_unchanged(tmp_path):
    """Absent, `False` and the STRING 'true' are all off: only the literal `true`
    activates, and the lineage engine is never even called."""
    calls = []

    def _never(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("lineage ran with the flag off")

    keys, stamps = [], []
    for i, variant in enumerate(("absent", False, "true")):
        extra = {} if variant == "absent" else {"lineage_enabled": variant}
        root = _lin_root(tmp_path, f"off{i}")
        payload = _lin_build(
            root, _lin_cfg(**extra),
            extra=[patch("engine.leader_lineage.describe_lineage_universe", side_effect=_never)])
        disk = _lin_disk(root)
        assert "lineage_roster" not in payload and "lineage_roster" not in disk
        for chips in list(_lin_chips(payload)) + list(_lin_chips(disk)):
            assert "leader_lineage" not in chips
        keys.append(list(disk.keys()))
        stamps.append(_stamps_out(disk))
    assert calls == []
    assert keys[0] == keys[1] == keys[2]
    assert stamps[0] == stamps[1] == stamps[2]


def test_lc3_flag_off_nightly_seals_no_lineage_columns(tmp_path):
    """Recovery capture alone keeps sealing exactly what it seals today."""
    root = _lin_root(tmp_path, "off-nightly")
    _lin_build(root, _lin_cfg(recovery_capture_enabled=True), lane="nightly")
    frame = _lin_history(root)
    assert len(frame) == 2
    for col in LINEAGE_COLUMNS:
        assert col not in frame.columns
    assert frame[list(COLUMNS)].notna().all().all()
    assert all(json.loads(raw)["schema"] == "leader_recovery_observation.v1"
               for raw in frame[COLUMNS[1]].tolist())


def test_lc4_flag_on_express_is_additive_and_display_only(tmp_path, caplog):
    off_root = _lin_root(tmp_path, "on-off")
    off = _lin_build(off_root, _lin_cfg())
    root = _lin_root(tmp_path, "on-on")
    before = _lin_hashes(root)
    with caplog.at_level(logging.INFO, logger=_LIN_LOGGER):
        res = _lin_build(root, _lin_cfg(lineage_enabled=True))
    disk = _lin_disk(root)
    rows = res["rows"]
    assert len(rows) == 2
    clock = res["recovery_roster"]["additive_clock"]["as_of"]
    for row in rows:
        chip = row["display_chips"]["leader_lineage"]
        assert chip["schema"] == "leader_lineage.v1"
        assert chip["as_of"] == clock
        assert chip["authority"] == {key: False for key in AUTHORITY}
        assert set(chip["authority"]) == set(AUTHORITY)
    # the artifact on disk is the returned payload (json round-trip)
    assert disk == json.loads(json.dumps(res, default=str))
    # additive key placement: right after recovery_roster, nothing else moves
    off_keys = list(off.keys())
    cut = off_keys.index("recovery_roster") + 1
    assert list(res.keys()) == off_keys[:cut] + ["lineage_roster"] + off_keys[cut:]
    assert list(disk.keys()) == list(res.keys())
    roster = res["lineage_roster"]
    assert not any(roster["authority"].values())
    assert set(roster["authority"]) == set(AUTHORITY)
    assert roster["additive_clock"] == res["recovery_roster"]["additive_clock"]
    assert roster["as_of"] == res["as_of"]
    coverage, counts = roster["coverage"], roster["counts"]
    assert coverage["issuers"] == len(rows) == 2
    states = [row["display_chips"]["leader_lineage"]["state"] for row in rows]
    # counts covers every lineage state, so it sums to the issuer census.
    assert sum(counts.values()) == len(rows) == coverage["issuers"]
    assert all(counts[state] >= 1 for state in states)
    # a fresh authority per chip: mutating one row cannot reach another
    rows[0]["display_chips"]["leader_lineage"]["authority"]["may_rank"] = True
    assert rows[1]["display_chips"]["leader_lineage"]["authority"]["may_rank"] is False
    assert not any(disk["rows"][0]["display_chips"]["leader_lineage"]["authority"].values())
    assert any("leader lineage: 2 issuers in" in record.getMessage() for record in caplog.records)
    # express writes no data/: every incumbent store and price input is untouched
    assert _lin_hashes(root) == before


def test_lc5_flag_on_nightly_seals_first_observed_lineage(tmp_path):
    root = _lin_root(tmp_path, "seal")
    res = _lin_build(root, _lin_cfg(recovery_capture_enabled=True, lineage_enabled=True),
                     lane="nightly")
    clock = res["recovery_roster"]["additive_clock"]["as_of"]
    frame = _lin_history(root)
    sealed = frame[frame["day"] == clock]
    assert len(frame) == len(sealed) == 2
    assert sealed[list(LINEAGE_COLUMNS)].notna().all().all()
    assert sealed[list(COLUMNS)].notna().all().all()
    for col in list(COLUMNS) + list(LINEAGE_COLUMNS):
        assert str(frame[col].dtype) == "string"
    for _, row in sealed.iterrows():
        raw = row[LINEAGE_COLUMNS[1]]
        payload = json.loads(raw)
        assert payload["schema"] == LINEAGE_SCHEMA
        assert payload["ticker"] == row["ticker"]
        assert payload["as_of"] == clock
        assert payload["source_first_seen_proven"] is False
        assert payload["observed_at"] == row[LINEAGE_COLUMNS[0]]
        assert row[LINEAGE_COLUMNS[2]] == hashlib.sha256(raw.encode()).hexdigest()


def test_lc6_late_lineage_activation_leaves_recovery_seals_untouched(tmp_path):
    root = _lin_root(tmp_path, "late")
    cfg = _lin_cfg(recovery_capture_enabled=True)
    first = _lin_build(root, cfg, lane="nightly")
    clock = first["recovery_roster"]["additive_clock"]["as_of"]
    frame1 = _lin_history(root)
    snap = {col: _lin_col(frame1, col) for col in COLUMNS}
    dtypes = {col: str(frame1[col].dtype) for col in COLUMNS}
    native_at_clock = len(frame1[frame1["day"] == clock])
    cfg["leader_radar"]["lineage_enabled"] = True
    second = _lin_build(root, cfg, lane="nightly")
    assert second["recovery_roster"]["additive_clock"]["as_of"] == clock
    frame2 = _lin_history(root)
    assert len(frame2) == len(frame1)                      # no row added for the session
    assert len(frame2[frame2["day"] == clock]) == native_at_clock
    for col in COLUMNS:
        assert _lin_col(frame2, col) == snap[col]          # recovery byte-identical
        assert str(frame2[col].dtype) == dtypes[col]
    sealed = frame2[frame2["day"] == clock]
    assert sealed[list(LINEAGE_COLUMNS)].notna().all().all()
    assert all(json.loads(raw)["schema"] == LINEAGE_SCHEMA
               for raw in sealed[LINEAGE_COLUMNS[1]].tolist())


def test_lc7_lineage_seals_never_overwrite_and_disarm_deletes_nothing(tmp_path):
    root = _lin_root(tmp_path, "rerun")
    cfg = _lin_cfg(recovery_capture_enabled=True, lineage_enabled=True)
    _lin_build(root, cfg, lane="nightly")
    first = {col: _lin_col(_lin_history(root), col) for col in LINEAGE_COLUMNS}
    assert all(value is not None for values in first.values() for value in values)
    _lin_build(root, cfg, lane="nightly")
    second = {col: _lin_col(_lin_history(root), col) for col in LINEAGE_COLUMNS}
    assert second == first
    cfg["leader_radar"]["lineage_enabled"] = False
    _lin_build(root, cfg, lane="nightly")
    third = {col: _lin_col(_lin_history(root), col) for col in LINEAGE_COLUMNS}
    assert third == first


def test_lc8_lagged_cut_seals_the_existing_native_row_and_mints_nothing(tmp_path, capsys):
    root = _lin_root(tmp_path, "lag")
    cfg = _lin_cfg(recovery_capture_enabled=False)
    aligned = _lin_build(root, cfg, lane="nightly")
    issuer_last = aligned["as_of"]
    native_before = len(_lin_history(root).query("day == @issuer_last"))
    assert native_before == 2
    _make_ohlcv(401, seed=99)[["close"]].to_parquet(root / "data/yahoo/SPY.parquet")
    cfg["leader_radar"]["recovery_capture_enabled"] = True
    cfg["leader_radar"]["lineage_enabled"] = True
    capsys.readouterr()
    lagged = _lin_build(root, cfg, lane="nightly")
    out = capsys.readouterr().out
    spy_last = lagged["as_of"]
    assert spy_last > issuer_last
    assert lagged["recovery_roster"]["additive_clock"]["as_of"] == issuer_last
    assert lagged["lineage_roster"]["additive_clock"]["as_of"] == issuer_last
    lines = out.splitlines()
    assert not any("lineage observation enrichment FAILED" in line for line in lines)
    assert not any("lineage layer FAILED" in line for line in lines)
    frame = _lin_history(root)
    sealed = frame[frame["day"] == issuer_last]
    assert len(sealed) == native_before                    # a lagged cut mints no row
    assert sorted(sealed["ticker"].tolist()) == ["AAPL", "MSFT"]
    assert sealed[list(LINEAGE_COLUMNS)].notna().all().all()
    assert all(json.loads(raw)["as_of"] == issuer_last
               for raw in sealed[LINEAGE_COLUMNS[1]].tolist())
    assert frame[frame["day"] == spy_last][list(LINEAGE_COLUMNS)].isna().all().all()


def test_lc9_lineage_attach_failure_leaves_the_incumbent_payload_intact(tmp_path, capsys):
    bad_root = _lin_root(tmp_path, "attach-fail")
    cfg = _lin_cfg(recovery_capture_enabled=True, lineage_enabled=True)
    capsys.readouterr()
    failed = _lin_build(bad_root, cfg, lane="nightly",
                        extra=[patch("engine.leader_lineage.describe_lineage_universe",
                                     side_effect=RuntimeError("boom"))])
    out = capsys.readouterr().out
    assert any(line.startswith(_LIN_ATTACH_WARNING + "RuntimeError: boom")
               for line in out.splitlines())
    assert "lineage_roster" not in failed
    for chips in list(_lin_chips(failed)) + list(_lin_chips(_lin_disk(bad_root))):
        assert "leader_lineage" not in chips
    frame = _lin_history(bad_root)
    for col in LINEAGE_COLUMNS:
        assert col not in frame.columns or frame[col].isna().all()
    assert frame[list(COLUMNS)].notna().all().all()        # recovery still sealed
    off_root = _lin_root(tmp_path, "attach-fail-off")
    off = _lin_build(off_root, _lin_cfg(recovery_capture_enabled=True), lane="nightly")
    assert list(failed.keys()) == list(off.keys())
    assert _stamps_out(failed) == _stamps_out(off)


def test_lc9b_partial_chip_failure_attaches_nothing(tmp_path):
    """The layer computes EVERY chip before it attaches any, so a chip that fails
    halfway leaves no partial attach behind."""
    root = _lin_root(tmp_path, "chip-fail")
    original = lineage_chip
    calls = {"n": 0}

    def _flaky(descriptor):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("chip boom")
        return original(descriptor)

    payload = _lin_build(root, _lin_cfg(lineage_enabled=True),
                         extra=[patch("engine.leader_lineage.lineage_chip", side_effect=_flaky)])
    assert calls["n"] == 2
    assert "lineage_roster" not in payload
    for chips in list(_lin_chips(payload)) + list(_lin_chips(_lin_disk(root))):
        assert "leader_lineage" not in chips


def test_lc10_lineage_seal_merge_failure_leaves_state_history_intact(tmp_path, capsys):
    root = _lin_root(tmp_path, "merge-fail")
    cfg = _lin_cfg(recovery_capture_enabled=True, lineage_enabled=True)
    capsys.readouterr()
    res = _lin_build(root, cfg, lane="nightly",
                     extra=[patch("engine.leader_recovery_observations.merge_lineage_observations",
                                  side_effect=RuntimeError("seal boom"))])
    out = capsys.readouterr().out
    assert any(line.startswith(_LIN_MERGE_WARNING + "RuntimeError: seal boom")
               for line in out.splitlines())
    frame = _lin_history(root)
    assert len(frame) == 2                                 # today's rows still written
    for col in LINEAGE_COLUMNS:
        assert col not in frame.columns
    assert frame[list(COLUMNS)].notna().all().all()        # recovery seals intact
    assert "lineage_roster" in res                         # the attach did succeed
    assert _lin_disk(root)["lineage_roster"] == json.loads(
        json.dumps(res["lineage_roster"], default=str))


def test_lc11_page_html_is_unchanged_by_the_lineage_layer(tmp_path):
    root = _lin_root(tmp_path, "html")
    _lin_build(root, _lin_cfg(lineage_enabled=True))
    on = _lin_disk(root)
    assert "lineage_roster" in on
    assert any("leader_lineage" in chips for chips in _lin_chips(on))
    stripped = _strip_lineage(on)
    assert _render(on) == _render(stripped)
    assert "leader_lineage" not in _render(on)
