"""Actual candle/MTF/texture parity and binding to one resolved thematic snapshot."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import basket_index, basket_score, basket_breadth_divergence as bd, cycles, theme_scoring as ts
from tests.fixtures import base_basket_index_7885 as original_index
from tests.fixtures import base_basket_signals_4eddd4 as original_signals
from tests.fixtures import base_basket_score_4eddd4 as original_score
from tests.fixtures import base_basket_breadth_divergence_4eddd4 as original_bd
from tests.test_member_index_explicit_inputs import inputs, wide, install_loaders, CASES, MODES

WEIGHTS = (.30, .25, .20, .15, .10)


def cycle_inputs(idx):
    return cycles.CycleCalculationInputs(evaluation_date=str(idx[-1].date()), fitted_bands={},
        risk_calibration={}, macro_overlay={}, vol_regime_overlay={}, vol_overlay_gate={},
        entry_gate={"stoch_oversold": 20, "stoch_overbought": 80, "daily_rsi_extension_cap": 75,
                    "stretch_block_pct": 20, "approach_days": 6, "overextended_osc_exempt_below_pct": 10},
        reference_sessions={"US": idx})


def prepared(count=365):
    members, idx, frames = inputs(count=count)
    reference = wide(frames, "close")
    level = (reference.pct_change(fill_method=None).mean(axis=1).fillna(0) + 1).cumprod() * 100
    row = {"bid": "basket-a", "skip": False, "members": members, "lvl": level,
           "mc_closes": reference.copy(), "fp": {"rs_pctile": .9, "accel_z": -.8},
           "fp5": {"accel_z": .2}, "crowd": None, "breadth_d": {"pct50": .3, "nh": 0, "nl": 2},
           "perf": {"5d": {"rel": -.02}}}
    return row, idx, frames, reference


def enrich(row, idx, frames, reference, **kwargs):
    return ts.basket_enrichments_from_inputs([row], region="us", member_frames=frames,
        reference_close=reference, source_session=str(idx[-1].date()), calculation_inputs=cycle_inputs(idx),
        rollover_weights=kwargs.pop("rollover_weights", WEIGHTS),
        breadth_divergence_fit=kwargs.pop("breadth_divergence_fit", {}), **kwargs)[row["bid"]]


def canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("mode,pit,alpha_pit", MODES)
def test_explicit_full_candle_is_exactly_the_literal_legacy_numerical_result(case, mode, pit, alpha_pit, monkeypatch):
    members, idx, frames = inputs(case)
    install_loaders(monkeypatch, frames)
    kwargs = dict(mode=mode, pit=pit, alpha_pit=alpha_pit, conv_map={"A": 90, "C": 25})
    before, before_meta = original_index.consolidated_candle(members, idx, **kwargs)
    after, meta = basket_index.consolidated_candle_from_inputs(
        members, idx, frames=frames, reference_close=wide(frames, "close"), **kwargs)
    pd.testing.assert_frame_equal(after, before, check_exact=True)
    assert {key: meta[key] for key in before_meta} == before_meta
    assert meta["reference_basis_qualified"] is True


@pytest.mark.parametrize("count", [60, 75, 365])
def test_actual_signal_and_texture_math_matches_original_with_captured_calibration(count, monkeypatch):
    row, idx, frames, reference = prepared(count)
    install_loaders(monkeypatch, frames)
    monkeypatch.setattr(original_score, "_rollover_weights", lambda: WEIGHTS)
    monkeypatch.setattr(bd, "_calibration", lambda: {})
    with cycles.bind_calculation_inputs(cycle_inputs(idx)):
        before_signal = original_signals._basket_signals(row["members"], row["lvl"], "us", use_cache=False)
        before_texture = original_score.theme_textures(row["lvl"], row["fp"], row["fp5"], row["crowd"],
            row["breadth_d"], row["perf"], mc_closes=row["mc_closes"])
    after = enrich(row, idx, frames, reference)
    assert canonical(after["signals"].get("mtf")) == canonical(before_signal.get("mtf"))
    assert canonical(after["signals"].get("tape")) == canonical(before_signal.get("tape"))
    assert canonical(after["textures"]) == canonical(before_texture)
    for key, value in before_signal.get("meta", {}).items():
        assert after["signals"]["meta"][key] == value
    if count == 75:
        assert after["signals"]["mtf"]["source"] == "member_ohlcv"
        assert after["signals"]["tape"] is not None


def test_deep_candle_keeps_more_than_ten_years_and_a_shallow_reference(monkeypatch):
    row, idx, frames, reference = prepared(2800)
    frames["C"].iloc[:1500] = np.nan
    row["mc_closes"] = reference.iloc[-100:].copy()
    reference = reference.iloc[-100:].copy()
    install_loaders(monkeypatch, frames)
    expected, _ = original_index.consolidated_candle(row["members"], idx, "equal", pit=False)
    seen = []
    actual_mtf = ts.basket_mtf.basket_mtf
    def observe(candle, market):
        seen.append(candle.copy(deep=True)); return actual_mtf(candle, market)
    monkeypatch.setattr(ts.basket_mtf, "basket_mtf", observe)
    result = enrich(row, idx, frames, reference)
    assert result["input_evidence"]["member_candle_qualified"] is True
    assert len(seen[0]) > 2600 and seen[0].index[0] < idx[-1] - pd.DateOffset(years=10)
    pd.testing.assert_frame_equal(seen[0], expected, check_exact=True)


def test_union_calendar_does_not_insert_an_unobserved_interior_session(monkeypatch):
    row, idx, frames, reference = prepared()
    missing = idx[100]
    frames = {ticker: frame.drop(index=missing) for ticker, frame in frames.items()}
    seen = []
    actual_mtf = ts.basket_mtf.basket_mtf
    def observe(candle, market):
        seen.append(candle.index.copy()); return actual_mtf(candle, market)
    monkeypatch.setattr(ts.basket_mtf, "basket_mtf", observe)
    result = enrich(row, idx, frames, reference)
    assert result["input_evidence"]["member_candle_qualified"] is True
    assert missing not in seen[0]


def test_all_null_physical_suffix_is_not_a_future_observation():
    members, idx, frames = inputs()
    for frame in frames.values(): frame.iloc[-1] = np.nan
    candle, meta = basket_index.consolidated_candle_from_inputs(
        members, idx[:-1], frames=frames, reference_close=wide(frames, "close"))
    assert candle.index[-1] == idx[-2] and meta["observed_endpoint"] == str(idx[-2].date())


def test_removed_members_later_quote_cannot_advance_actual_endpoint():
    members, idx, frames = inputs()
    members[2]["removed"] = str(idx[-2].date())
    for ticker, frame in frames.items():
        if ticker != "C": frame.iloc[-1] = np.nan
    candle, meta = basket_index.consolidated_candle_from_inputs(
        members, idx, frames=frames, reference_close=wide(frames, "close"))
    assert candle.index[-1] == idx[-2] and meta["observed_endpoint"] == str(idx[-2].date())


@pytest.mark.parametrize("case", ["missing_open", "missing_volume", "older", "mixed_volume_tip", "basis_mismatch"])
def test_unqualified_member_fields_publish_labelled_close_only_fallback(case):
    row, idx, frames, reference = prepared()
    for frame in frames.values():
        if case == "missing_open": frame.drop(columns="open", inplace=True)
        elif case == "missing_volume": frame.drop(columns="volume", inplace=True)
        elif case == "older": frame.iloc[-1] = np.nan
        elif case == "mixed_volume_tip": frame.loc[idx[-1], "volume"] = np.nan
        else: frame[["open", "high", "low", "close"]] *= .5
    result = enrich(row, idx, frames, reference)
    assert not result["input_evidence"]["member_candle_qualified"]
    assert result["signals"]["mtf"]["source"] == "equal_weight_close"
    assert result["signals"]["tape"] is None and result["signals"]["meta"]["flow_available"] is False
    if case == "older":
        assert result["input_evidence"]["member_candle_observed_at"] == str(idx[-2].date())
        assert result["input_evidence"]["member_candle_unavailable_reason"] == "member_candle_older_than_source"


def test_one_or_two_real_overlap_sessions_do_not_claim_full_basis_qualification():
    row, idx, frames, reference = prepared()
    for ticker in frames: frames[ticker] = frames[ticker].iloc[-2:]
    result = enrich(row, idx, frames, reference)
    assert not result["input_evidence"]["member_candle_qualified"]
    assert set(result["input_evidence"]["unavailable_members"].values()) == {"reference_basis_unqualified"}
    assert all(value["overlap_dates"] == 2 for value in result["input_evidence"]["member_price_basis_checks"].values())


def test_same_date_wrong_prepared_prices_are_rejected_before_calculation():
    row, idx, frames, reference = prepared()
    row["mc_closes"] = row["mc_closes"] * 1.01
    with pytest.raises(ValueError, match="resolved thematic panel"):
        enrich(row, idx, frames, reference)


def test_resolved_extra_prices_and_masked_omissions_bind_without_primary_substitution():
    row, idx, frames, reference = prepared()
    # A tied-date extras winner may differ from primary. The captured RESOLVED panel
    # is the row's actual source; it must not be replaced with a primary-only input.
    for field in ("open", "high", "low", "close"): frames["A"][field] *= 2
    reference["A"] *= 2
    row["mc_closes"] = reference.copy(); row["mc_closes"].iloc[:40, 0] = np.nan
    result = enrich(row, idx, frames, reference)
    assert result["input_evidence"]["member_candle_qualified"] is True
    wrong_primary = reference.copy(); wrong_primary["A"] /= 2
    with pytest.raises(ValueError, match="resolved thematic panel"):
        enrich(row, idx, frames, wrong_primary)


def test_positive_impossible_ohlc_is_rejected_before_aggregate_clamping():
    row, idx, frames, reference = prepared()
    frames["A"].loc[idx[-1], "high"] = frames["A"].loc[idx[-1], "open"] * .9
    with pytest.raises(ValueError, match="ohlcv_geometry"):
        enrich(row, idx, frames, reference)


@pytest.mark.parametrize("weights", [(-1, 0, 0, 0, 0), (np.inf, 0, 0, 0, 0), (True, 0, 0, 0, 0)])
def test_invalid_rollover_weights_are_refused(weights):
    row, idx, frames, reference = prepared()
    with pytest.raises(ValueError, match="nonnegative"):
        enrich(row, idx, frames, reference, rollover_weights=weights)


@pytest.mark.parametrize("weights", [[-1, 2, 0], [0, 0, 0], [True, 1, 0], [1, np.nan, 0], [1e308, 1e308, 1]])
def test_invalid_shipped_breadth_weights_cannot_retain_backtested_grade(weights):
    row, idx, frames, reference = prepared()
    with pytest.raises(ValueError, match="calibration"):
        enrich(row, idx, frames, reference,
               breadth_divergence_fit={"verdict": "ship_sizing_leg", "wired_weights": weights})


@pytest.mark.parametrize("fit", [{}, {"verdict": "display_only"},
    {"verdict": "ship_sizing_leg", "wired_weights": [.1, .7, .2]}])
def test_breadth_divergence_grade_and_available_leg_math_match_literal_original(fit, monkeypatch):
    row, idx, frames, reference = prepared()
    row["mc_closes"].iloc[-5:, 0] = np.nan
    monkeypatch.setattr(original_bd, "_calibration", lambda: deepcopy(fit))
    expected = original_bd.breadth_divergence(row["mc_closes"], row["lvl"])
    actual = bd.breadth_divergence(row["mc_closes"], row["lvl"], calibration=deepcopy(fit))
    assert canonical(actual) == canonical(expected)
    before = original_bd.series(row["mc_closes"], row["lvl"])
    after = bd.series(row["mc_closes"], row["lvl"], calibration=fit)
    for key in before:
        if isinstance(before[key], pd.Series): pd.testing.assert_series_equal(before[key], after[key], check_exact=True)
        else: pd.testing.assert_frame_equal(before[key], after[key], check_exact=True)


def test_single_calibration_acquisition_governs_grade_and_math(monkeypatch):
    row, idx, frames, reference = prepared()
    fit = {"verdict": "ship_sizing_leg", "wired_weights": [.7, .2, .1]}
    calls = []
    def acquire_fit():
        calls.append(True); return deepcopy(fit) if len(calls) == 1 else {}
    monkeypatch.setattr(bd, "_calibration", acquire_fit)
    result = bd.breadth_divergence(row["mc_closes"], row["lvl"])
    assert len(calls) == 1 and result == bd.breadth_divergence(row["mc_closes"], row["lvl"], calibration=fit)


def test_zero_rollover_weights_preserve_reason_order_and_fixed_breadth_legs(monkeypatch):
    row, idx, frames, reference = prepared()
    zero = (0, 0, 0, 0, 0)
    monkeypatch.setattr(original_score, "_rollover_weights", lambda: zero)
    expected = original_score.rollover_risk(row["lvl"], row["fp"], row["fp5"], row["breadth_d"], row["perf"])
    actual = basket_score.rollover_risk(row["lvl"], row["fp"], row["fp5"], row["breadth_d"], row["perf"], rollover_weights=zero)
    assert actual == expected and actual["risk"] >= .3
    assert actual["reasons"][0].startswith("extended")


def test_explicit_enrichments_use_no_store_config_cache_or_legacy_acquisition(monkeypatch):
    from lib import config, store
    row, idx, frames, reference = prepared()
    saved_row, saved_frames, saved_reference = deepcopy(row), deepcopy(frames), reference.copy(deep=True)
    saved_cache = dict(ts._SIG_CACHE)
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient acquisition reached")
    for owner, name in ((basket_index, "_load_member_ohlcv"), (basket_index, "deep_calendar"),
                        (basket_index, "consolidated_candle"), (ts, "_basket_signals"),
                        (basket_score, "_rollover_weights"), (bd, "_calibration"),
                        (config, "load"), (config, "data_dir"), (store, "read"),
                        (pd, "read_parquet"), (pd.DataFrame, "to_parquet")):
        monkeypatch.setattr(owner, name, forbidden)
    first = enrich(row, idx, frames, reference)
    assert first["signals"]["mtf"]["source"] == "member_ohlcv"
    assert first["signals"]["tape"] is not None
    assert ts._SIG_CACHE == saved_cache
    for ticker in frames: pd.testing.assert_frame_equal(frames[ticker], saved_frames[ticker])
    pd.testing.assert_frame_equal(reference, saved_reference)
    pd.testing.assert_frame_equal(row["mc_closes"], saved_row["mc_closes"])
    pd.testing.assert_series_equal(row["lvl"], saved_row["lvl"])
    first["textures"]["rollover_risk"]["reasons"].append("mutated return")
    assert "mutated return" not in enrich(row, idx, frames, reference)["textures"]["rollover_risk"]["reasons"]


def test_distinct_same_session_snapshots_cannot_reuse_cached_candles(monkeypatch):
    row, idx, frames, reference = prepared()
    monkeypatch.setattr(ts.basket_mtf, "basket_mtf", lambda candle, market: {"last": float(candle["close"].iloc[-1])})
    monkeypatch.setattr(ts.basket_tape, "basket_tape", lambda candle, meta: {"volume": float(candle["dollar_vol"].iloc[-1])})
    first = enrich(row, idx, frames, reference)
    for frame in frames.values(): frame.loc[idx[-1], ["open", "high", "low", "close"]] *= 1.1
    reference.loc[idx[-1]] *= 1.1; row["mc_closes"] = reference.copy()
    second = enrich(row, idx, frames, reference)
    assert first["signals"]["mtf"]["last"] != second["signals"]["mtf"]["last"]
    assert first["signals"]["tape"]["volume"] != second["signals"]["tape"]["volume"]


def test_literal_calibration_fixtures_are_the_published_source_bytes():
    root = Path(__file__).parent / "fixtures"
    assert hashlib.sha256((root / "base_basket_score_4eddd4.py").read_bytes()).hexdigest() == "313e9dfae08768d769c6604dcc0881315c848ce4b6ffa524430385723d7f5016"
    assert hashlib.sha256((root / "base_basket_breadth_divergence_4eddd4.py").read_bytes()).hexdigest() == "f073f778f43f9e040b5b3b76cfb66fe5085940ca00b92e7ae2fac359d1d68be6"


def test_real_prepared_rows_and_enrichments_feed_the_theme_intelligence_consumer(monkeypatch):
    from engine import group_flow
    from lib import config, store, market_session
    from lib.closes_panel import align_latest_common_observation
    from tests.test_theme_allocation_explicit_inputs import _make_universe, _make_membership, NAMES, CALIBRATION, EMPTY_MACRO
    closes, _, _, bench_close, _, _, _, populations = _make_universe()
    candidates = pd.bdate_range(end="2026-11-03", periods=450)
    idx = candidates[[market_session.is_session_date("US", date.date()) for date in candidates]][-len(closes):].as_unit("ns")
    closes.index = idx; bench_close.index = idx
    closes, bench_close, observation = align_latest_common_observation(closes, bench_close)
    rets = closes.pct_change(fill_method=None)
    bench_ret = bench_close.pct_change(fill_method=None)
    bench = pd.Series(np.nan, index=idx)
    first = bench_ret.first_valid_index()
    bench.loc[first:] = (1 + bench_ret.loc[first:].fillna(0)).cumprod()
    panel = {"mem": _make_membership(idx, populations), "closes": closes, "rets": rets,
        "idx": idx, "bench": bench, "region": "us", "observation": observation,
        "price_resolution": {"effective_as_of": str(idx[-1].date())}}
    cfg = deepcopy(group_flow._DEFAULTS)
    rows = ts.prepare_theme_basket_rows(panel, region="us", group_flow_cfg=cfg, names_sectors=NAMES)
    assert sum(not row["skip"] for row in rows) >= 3
    frames = {ticker: pd.DataFrame({"open": closes[ticker] * .998,
        "high": closes[ticker] * 1.01, "low": closes[ticker] * .99, "close": closes[ticker],
        "volume": pd.Series(10000.0 + np.arange(len(idx)), index=idx).where(closes[ticker].notna())})
        for ticker in closes}
    calculation = cycle_inputs(idx)
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient input reached from captured consumer path")
    for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"),
                        (store, "read"), (basket_index, "_load_member_ohlcv"),
                        (basket_index, "deep_calendar"), (basket_score, "_rollover_weights"),
                        (bd, "_calibration"), (ts, "_basket_signals")):
        monkeypatch.setattr(owner, name, forbidden)
    enrichments = ts.basket_enrichments_from_inputs(rows, region="us", member_frames=frames,
        reference_close=closes, source_session=str(idx[-1].date()), calculation_inputs=calculation,
        rollover_weights=WEIGHTS, breadth_divergence_fit={})
    bundle = ts.ThemeScoreInputs(region="us", panel=panel, basket_rows=rows, group_flow_cfg=cfg,
        names_sectors=NAMES, macro_context=deepcopy(EMPTY_MACRO), signal_calibration=deepcopy(CALIBRATION),
        regime_snapshot={}, regime_sizing={}, regime_caution_scored=False, prior_sector_text=None,
        evaluation_date=idx[-1].date(), earnings_calendar={}, market_concentration={"hhi": .11, "n": 21},
        basket_enrichments=enrichments, bench_label="S&P 500", bench_label_zh="标普500")
    result = ts.compute_theme_intel_core(bundle)
    themes = result.payload["themes"]
    assert len(themes) >= 3
    for theme in themes:
        source = enrichments[theme["id"]]
        assert theme["mtf"]["source"] == "member_ohlcv"
        assert canonical(theme["tape"]) == canonical(source["signals"]["tape"])
        assert canonical(theme["textures"]) == canonical(source["textures"])
        assert source["input_evidence"]["source_session"] == "2026-11-03"
    assert result.payload["as_of"] == "2026-11-03"


def test_direct_candle_bounds_full_input_history_before_projection(monkeypatch):
    from lib import adjusted_price_capture
    members, idx, frames = inputs()
    monkeypatch.setattr(adjusted_price_capture, "MAX_PANEL_CELLS", 1000)
    # The requested 100x4 projection fits, but the full 365x4x5 supplied archive
    # exceeds the fixed-five allocation budget. Refuse before detaching it.
    with pytest.raises(ValueError, match="member-frame allocation bound"):
        basket_index.consolidated_candle_from_inputs(members, idx[-100:], frames=frames)
