"""Literal builder parity and explicit stock/sector calculation without page effects."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from markupsafe import Markup

from engine import cycles, sector_action_board as board, sector_signals
from scripts import build_site
from tests.fixtures import base_sector_timing_c18e840 as original
from tests.test_basket_enrichments_explicit_inputs import cycle_inputs


@pytest.fixture
def captured():
    idx = pd.bdate_range(end="2026-11-03", periods=365).as_unit("ns")
    def prices(marker, count=365, high=True):
        selected = idx[-count:]
        close = pd.Series(marker + np.arange(count) / 10, index=selected)
        return pd.DataFrame({"close": close, **({"high": close + 2} if high else {})})
    funds = ("XLK", "XLF", "MISSING", "NOLADDER")
    etfs = {"XLK": prices(101), "XLF": prices(201), "MISSING": None, "NOLADDER": prices(777)}
    stocks = {"A-B": prices(51), "SECOND": prices(71, high=False),
              "SHORT": prices(81, 299), "NONE": prices(777), "OLDER": prices(91).iloc[:-3]}
    top = pd.DataFrame({"ticker": ["A.B", "SECOND", "SHORT", "NONE", "OLDER", "ABSENT"],
        "name": ["ALPHA CO", "second company", "short", "none", "older co", "absent"],
        "weight_pct": [10.0, 9.0, 8.0, 7.0, 6.0, 5.0]})
    alpha = {"A-B": {"alpha": 2.3, "sector_rank": 1, "sector_n": 20, "entry": "pullback"}}
    insiders = {"A-B": {"buyers": 2, "net_mn": 1.5, "bps": 4}, "SECOND": {"buyers": 1, "net_mn": 10}}
    return board.SectorTimingInputs(source_session="2026-11-03", funds=funds,
        etf_frames=etfs, top_holdings={"XLK": top, "XLF": top.iloc[:2].copy()}, stock_frames=stocks,
        liquidity="expanding", macro_drag=.2, macro_beta={"XLK": 1.0, "XLF": -1.0, "NOLADDER": 0.0},
        alpha_per_ticker=alpha, insider_map=insiders, factor_z={"A-B": 2.8, "SECOND": 1.2},
        sue_z={"A-B": 1.7, "SECOND": .4}, calculation_inputs=cycle_inputs(idx),
        auxiliary_evidence={"holdings": {"XLK": "2026-10-30"}, "alpha": "2026-11-02",
                            "macro": "2026-11-03", "insider": "2026-11-01"})


def fake_analyze(close, high=None, *, liquidity=None, macro_drag=None, macro_beta=0):
    marker = int(close.iloc[0])
    if marker == 777:
        return {"cycle": {}}
    urgency = "exit" if macro_beta < 0 else "imminent" if marker == 71 else "now" if marker == 51 else "soon"
    state = "DECLINE" if macro_beta < 0 else "FRESH BUY"
    return {"ladder": {"state": state, "label": state, "action": "reduce" if macro_beta < 0 else "buy",
        "entry": {"urgency": urgency, "tag": "EXIT" if urgency == "exit" else "BUY", "days_hi": 3},
        "dir": "down" if macro_beta < 0 else "up", "eq_dir": "up", "eq_score": 7.0,
        "eq_grade": "A", "eq_grade_zh": "甲", "score": 70.0,
        "signal_date": str(close.dropna().index[-1].date()), "age_days": 1, "age_short": "1d",
        "age_short_zh": "1天", "eq_badge": "badge", "eq_tip": "tip"},
        "cycle": {"dc_day": 4}, "mtf": {"controlled": marker},
        "context": {"liquidity": liquidity, "macro_drag": macro_drag, "beta": macro_beta,
                    "high_supplied": high is not None}}


class Template:
    def __init__(self, calls): self.calls = calls
    def render(self, **kwargs):
        self.calls.append(deepcopy(kwargs)); return "controlled rendered page"


class Environment:
    def __init__(self, calls): self.calls = calls
    def get_template(self, name):
        assert name == "sector.html.j2"; return Template(self.calls)


def install_legacy_acquisitions(monkeypatch, captured, tmp_path):
    from collectors import sector_holdings
    from engine import conditions, holdings_signals, ticker_alerts, technicals
    from scripts import build_stock_library
    from lib import config, store
    site, data = tmp_path / "site", tmp_path / "data"
    (site / "factordata").mkdir(parents=True)
    (data / "yahoo").mkdir(parents=True)
    (site / "factordata/insider_signals.json").write_text(json.dumps(captured.insider_map))
    (site / "factordata/factors.json").write_text(json.dumps({"table": [
        {"ticker": "A-B", "composite_rank": 2.8, "composite": -5, "sue": 1.7},
        {"ticker": "SECOND", "composite": 1.2, "sue": .4}]}))
    cfg = {"sponsors": {"sector_funds": list(captured.funds)},
           "yahoo": {"tickers": {"sectors": ["XLE"]}}, "alerts": {}}
    monkeypatch.setattr(config, "load", lambda: deepcopy(cfg))
    monkeypatch.setattr(config, "data_dir", lambda: data)
    monkeypatch.setattr(store, "read", lambda group, ticker: deepcopy(
        captured.stock_frames.get(ticker) if group == "stocks" else
        captured.etf_frames.get("XLK" if ticker == "SPY" else ticker)))
    monkeypatch.setattr(sector_holdings, "latest_top10", lambda fund: deepcopy(captured.top_holdings.get(fund)))
    monkeypatch.setattr(sector_holdings, "latest_fundamentals", lambda ticker: {"ticker": ticker, "pe": 20})
    monkeypatch.setattr(conditions, "sector_macro_beta", lambda fund: captured.macro_beta[fund])
    monkeypatch.setattr(build_stock_library, "current_liquidity", lambda: captured.liquidity)
    monkeypatch.setattr(build_stock_library, "current_macro", lambda: captured.macro_drag)
    monkeypatch.setattr(holdings_signals, "accumulation_signals", lambda *a, **k: {"controlled": True})
    monkeypatch.setattr(ticker_alerts, "build_feed", lambda *a, **k: {"events": []})
    monkeypatch.setattr(technicals, "snapshot", lambda close: {"price": float(close.iloc[-1])})
    monkeypatch.setattr(sector_signals, "sector_signal", lambda *a, **k: {"ok": False})
    for owner in (original, build_site):
        monkeypatch.setattr(owner, "_dollar_context", lambda *a: None)
        monkeypatch.setattr(owner, "write_page", lambda *a: None)
    return site, data


def test_literal_source_and_display_helper_types_remain_exact():
    p = Path(__file__).parent / "fixtures/base_sector_timing_c18e840.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "e7d4bf0dde7e1653b11d2a8fdeaa8b3679edf00b6d6fbe5a75d4540bf92698cb"
    values = [10, 12, 11, 14]
    for kwargs in ({}, {"baseline": 0, "dot": False}, {"zone_lo": 11, "zone_hi": 13, "zone_state": "active"}):
        assert board._mini_svg(values, **kwargs) == original._mini_svg(values, **kwargs) == build_site._mini_svg(values, **kwargs)
    seasons = {1: {"avg_pct": 2.1, "hit_pct": 60, "n": 25}, 11: {"avg_pct": -.8, "hit_pct": 45, "n": 25}}
    expected = original._season_tooltip(seasons, 11)
    assert isinstance(expected, Markup)
    assert board._season_tooltip(seasons, 11) == build_site._season_tooltip(seasons, 11) == expected
    assert isinstance(build_site._season_tooltip(seasons, 11), Markup)
    assert board.STATE_STYLES == original.STATE_STYLES == build_site.STATE_STYLES
    assert all(isinstance(value, tuple) and len(value) == 2 for value in board.STATE_STYLES.values())


def test_legacy_page_adapters_and_explicit_timing_match_original(captured, monkeypatch, tmp_path):
    site, _ = install_legacy_acquisitions(monkeypatch, captured, tmp_path)
    calls = []
    def analyze(close, high=None, **kwargs):
        calls.append((int(close.iloc[0]), high is not None, kwargs["macro_beta"]))
        return fake_analyze(close, high, **kwargs)
    monkeypatch.setattr(cycles, "analyze", analyze)
    alpha = {"per_ticker": captured.alpha_per_ticker}
    original_pages, updated_pages = [], []
    before = original.build_sector_pages(Environment(original_pages), site, "frozen", alpha=alpha)
    original_calls = calls[:]; calls.clear()
    after = build_site.build_sector_pages(Environment(updated_pages), site, "frozen", alpha=alpha)
    assert calls == original_calls
    assert after == before and updated_pages == original_pages
    calls.clear(); explicit = board.sector_timing_and_notable_from_inputs(captured)
    assert calls == original_calls
    assert (explicit.timing, explicit.notable) == before
    assert list(explicit.timing) == ["XLK", "XLF"]
    assert explicit.timing["XLK"]["n_holdings"] == 3 and explicit.timing["XLK"]["buy_zone"] == 3
    assert explicit.timing["XLF"]["n_holdings"] == 2 and explicit.timing["XLF"]["buy_zone"] == 0
    assert [(row["ticker"], row["urgency"]) for row in explicit.notable] == [
        ("A-B", "now"), ("SECOND", "imminent"), ("A-B", "exit"), ("SECOND", "exit")]
    assert (51, True, 1.0) in calls and (51, True, -1.0) in calls
    assert all(not high for marker, high, beta in calls if marker in (101, 201, 777) and marker != 777)
    assert (71, False, 1.0) in calls
    assert explicit.notable[0]["factor_z"] == 2.8 and explicit.notable[0]["sue_z"] == 1.7
    assert explicit.notable[1]["sue_z"] is None and explicit.notable[1]["insider_buyers"] is None
    assert explicit.input_evidence["auxiliary"] == captured.auxiliary_evidence
    older = next(row for row in explicit.input_evidence["funds"]["XLK"]["holdings"] if row["ticker"] == "OLDER")
    assert older["included"] and not older["price"]["current"]
    assert older["price"]["observed_at"] == str(captured.stock_frames["OLDER"].index[-1].date())


def setup_row(state="buy_now", side="buy", base=None):
    return {"ticker": "XLE", "state": state, "side": side, "label": "BUY", "label_zh": "买入",
        "action": "enter", "action_zh": "入场", "conviction": 2, "conviction_label": "medium",
        "conviction_label_zh": "中", "above200": True, "above50": False, "rsi_3d": 51,
        "stoch_3d": 30, "rs_60d": 2.2, "base_rate": base}


@pytest.mark.parametrize("urgency,tag,lane_hint,chip", [("exit", "EXIT", None, True),
    ("caution", "TAKE PROFITS", None, True), ("caution", "DON'T CHASE", None, False),
    ("caution", "UNCONFIRMED — HIGH RISK", None, False),
    ("now", "BUY", "take_profits", False)])
@pytest.mark.parametrize("calibration", ["measured", "fallback", "unavailable"])
def test_production_setup_projection_matches_original_and_preserves_two_reads(
        captured, monkeypatch, tmp_path, urgency, tag, lane_hint, chip, calibration):
    site, data = install_legacy_acquisitions(monkeypatch, captured, tmp_path)
    closes = pd.DataFrame({"XLE": captured.etf_frames["XLK"]["close"],
                           "SPY": captured.etf_frames["XLF"]["close"]})
    for ticker in closes:
        pd.DataFrame({"close": closes[ticker]}).to_parquet(data / "yahoo" / f"{ticker}.parquet")
    base = {"exc63": 1.1, "hit": 58, "n": 40}
    row = setup_row(base=None if calibration == "unavailable" else base)
    calls = []
    def signal_board(panel, names, sectors, *, spy, put_absent):
        calls.append((list(sectors), put_absent)); return {"sectors": [deepcopy(row)]}
    monkeypatch.setattr(sector_signals, "board", signal_board)
    monkeypatch.setattr(sector_signals, "signal_line", lambda row, zh=False: "信号" if zh else "signal")
    def calibrate(*args):
        if calibration == "fallback": raise ValueError("controlled calibration shortfall")
        return {"buy_now": {"exc63": 2.0, "hit": 61, "n": 42}} if calibration == "measured" else {}
    monkeypatch.setattr(sector_signals, "calibrate", calibrate)
    latest = {"date": "2026-11-03", "dislocation": {"put_state": "put-absent"}, "playbook": {
        "stages": [{"ticker": "XLE", "season_this": "Nov: +1.2% avg, up 55% of years (n=25)",
                    "season_month": 10, "season_all": {10: {"avg_pct": 1.2, "hit_pct": 55, "n": 25}}}]}}
    timing = {"XLE": {"state": "ROLLING OVER", "label": "Reduce", "entry": {
        "urgency": urgency, "tag": tag, "lane_hint": lane_hint}}}
    before = original.sector_setup_view(latest, timing)
    after = build_site.sector_setup_view(latest, timing)
    explicit = board.sector_setup_from_inputs(latest=latest, timing=timing, closes=closes, sectors=["XLE"])
    assert explicit == before == after
    assert all(sectors == ["XLE"] and absent for sectors, absent in calls)
    record = explicit["sectors"][0]
    assert bool(record["two_reads_chip"]) is chip
    assert isinstance(record["season_tip"], Markup)
    assert record["rate_exc"] == (2.0 if calibration == "measured" else 1.1 if calibration == "fallback" else None)


def test_timing_execution_has_no_ambient_acquisition_or_page_effects(captured, monkeypatch):
    from collectors import sector_holdings
    from engine import conditions
    from lib import config, store
    before_etfs = deepcopy(captured.etf_frames); before_stocks = deepcopy(captured.stock_frames)
    monkeypatch.setattr(cycles, "analyze", fake_analyze)
    def forbidden(*args, **kwargs): raise AssertionError("ambient acquisition or page effect reached")
    for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"), (store, "read"),
                        (sector_holdings, "latest_top10"), (sector_holdings, "latest_fundamentals"),
                        (conditions, "sector_macro_beta"), (pd, "read_parquet"), (build_site, "write_page")):
        monkeypatch.setattr(owner, name, forbidden)
    first = board.sector_timing_and_notable_from_inputs(captured)
    assert first.notable and first.timing
    for ticker, frame in captured.etf_frames.items():
        if frame is not None: pd.testing.assert_frame_equal(frame, before_etfs[ticker])
    for ticker, frame in captured.stock_frames.items(): pd.testing.assert_frame_equal(frame, before_stocks[ticker])
    first.notable[0]["alpha_entry"] = "changed return"
    first.input_evidence["auxiliary"]["holdings"]["XLK"] = "changed return"
    assert captured.alpha_per_ticker["A-B"]["entry"] == "pullback"
    assert captured.auxiliary_evidence["holdings"]["XLK"] == "2026-10-30"
    again = board.sector_timing_and_notable_from_inputs(captured)
    assert again.notable[0]["alpha_entry"] == "pullback"
    assert again.input_evidence["auxiliary"]["holdings"]["XLK"] == "2026-10-30"


def test_real_cycle_analysis_runs_with_only_captured_context(captured, monkeypatch):
    from lib import config, store
    idx = captured.etf_frames["XLK"].index
    t = np.arange(len(idx), dtype=float)
    close = pd.Series(100 + .04 * t + 12 * np.sin(t / 13) + 5 * np.sin(t / 41), index=idx)
    frame = pd.DataFrame({"close": close, "high": close * 1.01})
    minimal = replace(captured, funds=("XLK",), etf_frames={"XLK": frame},
        top_holdings={"XLK": captured.top_holdings["XLK"].iloc[:1]},
        stock_frames={"A-B": frame * .5}, macro_beta={"XLK": 1.0})
    def forbidden(*args, **kwargs): raise AssertionError("ambient read reached in real cycle analysis")
    for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"), (store, "read")):
        monkeypatch.setattr(owner, name, forbidden)
    result = board.sector_timing_and_notable_from_inputs(minimal)
    assert result.timing["XLK"]["n_holdings"] == 1
    assert result.input_evidence["funds"]["XLK"]["etf"]["observed_at"] == captured.source_session


@pytest.mark.parametrize("change", ["future", "missing_beta", "infinite_drag", "infinite_sue", "foreign_reference"])
def test_unadmitted_inputs_are_rejected_before_analysis(captured, monkeypatch, change):
    def forbidden(*args, **kwargs): raise AssertionError("analysis must not begin")
    monkeypatch.setattr(cycles, "analyze", forbidden)
    if change == "future":
        frames = deepcopy(captured.stock_frames)
        extra = frames["A-B"].iloc[-1:].copy(); extra.index = pd.to_datetime(["2026-11-04"])
        frames["A-B"] = pd.concat([frames["A-B"], extra]); captured = replace(captured, stock_frames=frames)
    elif change == "missing_beta": captured = replace(captured, macro_beta={})
    elif change == "infinite_drag": captured = replace(captured, macro_drag=np.inf)
    elif change == "infinite_sue": captured = replace(captured, sue_z={"A-B": np.inf})
    else:
        context = captured.calculation_inputs
        captured = replace(captured, calculation_inputs=replace(context,
            reference_sessions={"HK": context.reference_sessions["US"]}))
    with pytest.raises((ValueError, TypeError)):
        board.sector_timing_and_notable_from_inputs(captured)


def test_real_setup_calculation_reads_only_explicit_prices(captured, monkeypatch):
    from lib import config, store
    closes = pd.DataFrame({"XLE": captured.etf_frames["XLK"]["close"],
                           "SPY": captured.etf_frames["XLF"]["close"]})
    before = closes.copy(deep=True)
    def forbidden(*args, **kwargs): raise AssertionError("ambient setup acquisition reached")
    for owner, name in ((config, "load"), (config, "data_dir"), (store, "read"), (pd, "read_parquet")):
        monkeypatch.setattr(owner, name, forbidden)
    result = board.sector_setup_from_inputs(latest={"date": captured.source_session},
        timing={}, closes=closes, sectors=["XLE"])
    assert result and [row["ticker"] for row in result["sectors"]] == ["XLE"]
    pd.testing.assert_frame_equal(closes, before)
    assert board.sector_setup_from_inputs(latest={}, timing={}, closes=closes[["XLE"]], sectors=["XLE"]) is None


def test_frame_row_floor_and_partial_high_dates_preserve_incumbent_calculation(captured, monkeypatch, tmp_path):
    stocks = deepcopy(captured.stock_frames)
    stocks["A-B"] = stocks["A-B"].iloc[-300:].copy()
    stocks["A-B"].iloc[1:25, 0] = np.nan
    stocks["A-B"].iloc[-4:, 1] = np.nan
    captured = replace(captured, funds=("XLK",), etf_frames={"XLK": captured.etf_frames["XLK"]},
        top_holdings={"XLK": captured.top_holdings["XLK"].iloc[[0, 2]]},
        stock_frames=stocks, macro_beta={"XLK": 1.0})
    site, _ = install_legacy_acquisitions(monkeypatch, captured, tmp_path)
    calls = []
    def analyze(close, high=None, **kwargs):
        calls.append((len(close), int(close.notna().sum()), high is not None))
        return fake_analyze(close, high, **kwargs)
    monkeypatch.setattr(cycles, "analyze", analyze)
    before = original.build_sector_pages(Environment([]), site, "frozen", alpha={"per_ticker": captured.alpha_per_ticker})
    expected_calls = calls[:]; calls.clear()
    result = board.sector_timing_and_notable_from_inputs(captured)
    assert (result.timing, result.notable) == before
    assert calls == expected_calls == [(365, 365, False), (300, 276, True)]
    assert result.timing["XLK"]["n_holdings"] == 1
    holding = result.input_evidence["funds"]["XLK"]["holdings"][0]
    assert holding["included"] and holding["price"]["close_current"]
    assert holding["price"]["current"] is False
    assert holding["price"]["field_observed_at"] == {
        "close": captured.source_session, "high": str(stocks["A-B"].index[-5].date())}


def test_tactical_base_rate_display_remains_literal_original(captured, monkeypatch, tmp_path):
    _, data = install_legacy_acquisitions(monkeypatch, captured, tmp_path)
    closes = pd.DataFrame({"XLE": captured.etf_frames["XLK"]["close"], "SPY": captured.etf_frames["XLF"]["close"]})
    for ticker in closes:
        pd.DataFrame({"close": closes[ticker]}).to_parquet(data / "yahoo" / f"{ticker}.parquet")
    base = {"abs63": 5.5, "abs_hit": 70, "exc63": -1.2, "hit": 48, "n": 41}
    row = setup_row(state="partial", side="tactical", base=base)
    monkeypatch.setattr(sector_signals, "board", lambda *a, **k: {"sectors": [deepcopy(row)]})
    monkeypatch.setattr(sector_signals, "calibrate", lambda *a, **k: {})
    monkeypatch.setattr(sector_signals, "signal_line", lambda row, zh=False: "信号" if zh else "signal")
    latest = {"date": captured.source_session}
    expected = original.sector_setup_view(latest, {})
    result = board.sector_setup_from_inputs(latest=latest, closes=closes, sectors=["XLE"], timing={})
    assert result == expected == build_site.sector_setup_view(latest, {})
    assert "+5.5% abs" in result["sectors"][0]["rate_str"]
    assert "-1.2% vs SPY" in result["sectors"][0]["rate_str"]
    assert result["sectors"][0]["rate_pos"] is None
