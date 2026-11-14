"""Adversarial contracts for the research adapter; synthetic fixtures are not alpha evidence."""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import pytest

from scripts import prophet_fusion_mechanisms as m
from scripts import prophet_fusion_mechanism_study as study


@pytest.fixture
def prices():
    dates = pd.bdate_range("2014-01-02", periods=3400)
    rng = np.random.default_rng(42)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.00025, 0.012, len(dates)))), index=dates, name="close")


@pytest.fixture
def spec():
    return m.load_spec(study.DEFAULT_SPEC)


def _gate(ticker, prefix, **kwargs):
    flag = len(prefix) % 13 in (0, 1)
    date = str(prefix.index[-1].date())
    return {"eligible": flag, "tier_cascade": "T2" if flag else None, "result": {},
            "provisional": False, "tier_event_date": date if flag else None,
            "tier_observed_date": date if flag else None, "reason": "fixture"}


@pytest.mark.parametrize("mutation,code", [
    (lambda x: x.update(schema="other"), "SPEC_SCHEMA"),
    (lambda x: x.update(source_base="main"), "SOURCE_PIN"),
    (lambda x: x.update(universe=["AAPL", "AAPL"]), "UNIVERSE"),
    (lambda x: x.update(promotion_eligible=True), "AUTHORITY"),
    (lambda x: x.update(integer_primary_comparison_count=1), "COMPARISON"),
    (lambda x: x.update(primary_horizon=5), "HORIZON"),
    (lambda x: x.update(entry_gap_sessions=1), "OBSERVATION"),
])
def test_spec_rejects_semantic_drift(tmp_path, spec, mutation, code):
    mutation(spec)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(spec))
    with pytest.raises(m.MechanismRefusal, match=code):
        m.load_spec(path)


def test_frozen_spec_has_exact_primary_budget(spec):
    assert len(spec["primary_comparisons"]) == 11
    assert len(spec["triggers"]) * len(spec["contexts"]) == 12
    assert spec["survivorship_biased"] is True
    assert spec["promotion_eligible"] is False


@pytest.mark.parametrize("bad", [0.0, -1.0, np.nan, np.inf])
def test_bad_prices_do_not_become_market_states(prices, bad):
    prices.iloc[30] = bad
    with pytest.raises(m.MechanismRefusal, match="PRICE"):
        m.momentum_triggers(prices)


def test_unsorted_or_duplicate_sessions_refused(prices):
    with pytest.raises(m.MechanismRefusal, match="UNSORTED"):
        m.validate_close(prices.iloc[::-1])
    with pytest.raises(m.MechanismRefusal, match="DUPLICATE"):
        m.validate_close(pd.concat([prices, prices.iloc[-1:]]))


def test_timezone_and_intraday_clock_refused(prices):
    prices.index = prices.index.tz_localize("UTC")
    with pytest.raises(m.MechanismRefusal, match="CLOCK"):
        m.validate_close(prices)


def test_feature_prefix_invariance_against_future_mutation(prices):
    cut = 900
    changed = prices.copy()
    changed.iloc[cut:] *= np.linspace(0.01, 100, len(changed) - cut)
    for fn in (m.momentum_triggers, m.market_context):
        base = fn(prices)
        pd.testing.assert_frame_equal(base.iloc[:cut], fn(changed).iloc[:cut])
        pd.testing.assert_frame_equal(base.iloc[:cut], fn(prices.iloc[:cut]))


def test_beta_prefix_invariance(prices):
    benchmark = prices * np.exp(np.linspace(0, 0.2, len(prices)))
    cut = 700
    changed = benchmark.copy()
    changed.iloc[cut:] *= 20
    pd.testing.assert_series_equal(m.ex_ante_beta(prices, benchmark).iloc[:cut],
                                   m.ex_ante_beta(prices, changed).iloc[:cut])


def test_unknown_regime_is_not_bearish_or_calm(prices):
    state = m.market_context(prices.iloc[:200])
    assert state["market_uptrend"].isna().all()
    assert state["no_volatility_stress"].isna().all()
    assert not state["market_context_known"].any()
    constant = prices * 0 + 100
    assert m.market_context(constant)["no_volatility_stress"].isna().all()


def test_breakout_excludes_current_bar_from_prior_high():
    prices = pd.Series(np.arange(1.0, 401), index=pd.bdate_range("2020-01-01", periods=400))
    flags = m.momentum_triggers(prices)
    assert bool(flags["breakout_63"].iloc[-1])
    assert flags.iloc[:251].isna().all().all()


def test_prefix_adapter_never_passes_future_or_context_state(prices):
    dates = prices.index[[400, 500, 600]]
    seen = []
    def gate(ticker, prefix, **kwargs):
        seen.append(prefix.index[-1])
        assert kwargs == {"reclaim_veto": True, "washout_waiver": False, "event_latch": None}
        pd.testing.assert_series_equal(prefix, prices.loc[:prefix.index[-1]])
        return _gate(ticker, prefix, **kwargs)
    result = m.technical_core_observations("AAPL", prices, dates, gate_fn=gate)
    assert seen == list(dates)
    assert result["status"].eq("EVALUATED").all()


@pytest.mark.parametrize("mode", ["raise", "missing_result", "future", "missing_provenance", "waiver"])
def test_broken_gate_is_unknown_not_a_false_signal(prices, mode):
    date = prices.index[519]  # length 520, fixture signal is true
    def gate(ticker, prefix, **kwargs):
        value = _gate(ticker, prefix, **kwargs)
        if mode == "raise":
            raise RuntimeError("deliberate fixture failure")
        if mode == "missing_result": value["result"] = None
        if mode == "future": value["tier_observed_date"] = "2099-01-01"
        if mode == "missing_provenance": value["tier_event_date"] = None
        if mode == "waiver": value["waiver"] = {"active": True}
        return value
    row = m.technical_core_observations("AAPL", prices, pd.DatetimeIndex([date]), gate_fn=gate).iloc[0]
    assert row["status"] == "UNAVAILABLE"
    assert pd.isna(row["signal"])


def test_pending_observation_stays_provisional(prices):
    def gate(ticker, prefix, **kwargs):
        value = _gate(ticker, prefix, **kwargs)
        value["sub"] = "pending"
        return value
    row = m.technical_core_observations("AAPL", prices, prices.index[519:520], gate_fn=gate).iloc[0]
    assert bool(row["provisional"])
    assert row.name == prices.index[519]


def test_onset_requires_known_false_gap_and_is_not_refired_by_context():
    signal = pd.Series([False, False, False, True, True, True, False, False, False, True], dtype="boolean")
    assert m.onset_mask(signal).tolist() == [False, False, False, True, False, False, False, False, False, True]
    signal.iloc[1] = pd.NA
    assert not m.onset_mask(signal).iloc[3]
    context = pd.Series([False] * 5 + [True] * 5)
    assert not (m.onset_mask(signal) & context).iloc[5]


def test_missing_price_session_is_not_compressed(prices):
    broken = prices.drop(prices.index[410])
    with pytest.raises(m.MechanismRefusal, match="CALENDAR"):
        m.align_calendar(broken, prices)
    with pytest.raises(m.MechanismRefusal, match="CALENDAR"):
        m.canonical_outcome(broken, prices, prices.index[400], 21)


def test_canonical_outcome_exact_next_close_and_horizon(prices):
    date = prices.index[400]
    got = m.canonical_outcome(prices, prices * 2, date, 21)
    assert got["fill_date"] == str(prices.index[401].date())
    assert got["exit_date"] == str(prices.index[422].date())
    assert got["gross_return"] == pytest.approx(prices.iloc[422] / prices.iloc[401] - 1)
    assert got["gross_return"] == pytest.approx(got["benchmark_return"])
    assert m.canonical_outcome(prices.iloc[:420], (prices * 2).iloc[:420], date, 21) == {"status": "UNMATURED"}


def test_costs_are_applied_on_both_sides_and_never_improve_gross():
    r = np.array([-0.4, 0, 0.5])
    assert np.all(m.net_return(r, 25) < r)
    assert m.net_return(0.0, 25) == pytest.approx((1 - .00125) / (1 + .00125) - 1)
    assert m.net_return(0.1, 0) == pytest.approx(0.1)


def test_date_weighting_does_not_count_correlated_names_as_independent_votes():
    frame = pd.DataFrame({"date": [pd.Timestamp("2020-01-01")] * 100 + [pd.Timestamp("2020-01-02")],
                          "metric": [0.1] * 100 + [-0.1]})
    assert study._date_mean(frame, "metric") == pytest.approx(0.0)
    assert frame["metric"].mean() > 0.09


def test_bootstrap_is_paired_on_calendar_not_ticker_rows():
    rng = np.random.default_rng(9)
    common = rng.normal(0, 0.1, 1600)
    got = study.moving_block_contrast(common + 0.01, common, block=126,
                                      replications=2500, seed=5, alpha=.05, comparisons=11)
    assert got["delta"] == pytest.approx(.01)
    assert got["familywise_ci"] == pytest.approx([.01, .01])
    assert got["nonoverlapping_calendar_blocks"] == 12


def test_empty_arm_never_has_a_zero_return_estimate():
    got = study.moving_block_contrast(np.full(1600, np.nan), np.zeros(1600), block=126,
                                      replications=2000, seed=5, alpha=.05, comparisons=11)
    assert got["status"] == "EMPTY_ARM"
    assert got["delta"] is None


def test_name_episodes_exclude_overlapping_holding_windows():
    frame = pd.DataFrame({"ticker": ["A", "A", "A", "B"],
                          "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-03-01", "2020-01-01"]),
                          "exit_date": ["2020-02-01", "2020-02-02", "2020-04-01", "2020-02-01"]})
    assert study.independent_episode_count(frame) == 3


def test_strict_json_converts_nonfinite_to_null_without_invalid_json(tmp_path):
    path = tmp_path / "result.json"
    study.write_json(path, {"a": np.nan, "b": np.int64(2), "c": pd.NA})
    assert json.loads(path.read_text()) == {"a": None, "b": 2, "c": None}


def test_runtime_data_and_site_are_not_output_locations():
    for top in ("data", "site"):
        with pytest.raises(study.OutputPathRefusal):
            study.safe_cache(study.ROOT / top / "must-not-be-created-mechanism-test")


def test_input_capture_uses_pinned_bytes_and_detects_tampering(tmp_path, prices, spec, monkeypatch):
    raw = io.BytesIO()
    prices.to_frame().to_parquet(raw)
    calls = []
    def git_bytes(source, path):
        calls.append((source, path))
        return raw.getvalue()
    monkeypatch.setattr(study, "_git_bytes", git_bytes)
    out = study.safe_cache(tmp_path / "cache")
    manifest = study.qualify(spec, out)
    assert len(calls) == 12
    assert {x[0] for x in calls} == {spec["source_base"]}
    assert all("w3" not in x[1] and "grades" not in x[1] for x in calls)
    assert manifest["outcome_blind"] is True
    assert manifest["promotion_eligible"] is False
    study.qualify(spec, out)
    assert len(calls) == 12  # no duplicate materialization
    (out / manifest["inputs"][0]["cache_name"]).write_bytes(b"tampered")
    with pytest.raises(m.MechanismRefusal, match="DIGEST"):
        study.qualify(spec, out)


def test_registered_window_cannot_be_silently_truncated(tmp_path, prices, spec, monkeypatch):
    raw = io.BytesIO()
    prices.iloc[:700].to_frame().to_parquet(raw)
    monkeypatch.setattr(study, "_git_bytes", lambda *args: raw.getvalue())
    with pytest.raises(m.MechanismRefusal, match="WINDOW_NOT_COVERED"):
        study.qualify(spec, study.safe_cache(tmp_path / "cache"))


def test_native_gate_prefix_parity_on_synthetic_prices(prices):
    from engine.signal_gate import gate
    dates = prices.index[[300, 400, 519, 620, 711, 802]]
    result = m.technical_core_observations("AAPL", prices, dates)
    for date in dates:
        native = gate("AAPL", prices.loc[:date], reclaim_veto=True,
                      washout_waiver=False, event_latch=None)
        assert native["result"] is not None
        assert result.at[date, "status"] == "EVALUATED"
        assert bool(result.at[date, "signal"]) == bool(
            native["eligible"] and native["tier_cascade"] in ("T1", "T2"))


def test_complete_synthetic_consumer_and_equal_asset_benchmark_negative_control(
    tmp_path, prices, spec, monkeypatch
):
    # One synthetic name is a fixture, not the registered real-data study.
    spec = dict(spec, universe=["AAPL"], _sha256="fixture-not-a-research-result")
    raw = io.BytesIO()
    prices.to_frame().to_parquet(raw)
    monkeypatch.setattr(study, "_git_bytes", lambda *args: raw.getvalue())
    out = study.safe_cache(tmp_path / "fixture")
    manifest = study.qualify(spec, out)
    def fixture_observations(ticker, close, dates, **kwargs):
        signal = pd.Series(np.arange(len(dates)) % 17 == 0, index=dates, dtype="boolean")
        return pd.DataFrame({"ticker": ticker, "signal": signal,
                             "tier": np.where(signal, "T2", None), "provisional": False,
                             "status": "EVALUATED", "reason": "SYNTHETIC_FIXTURE"}, index=dates)
    monkeypatch.setattr(m, "technical_core_observations", fixture_observations)
    receipt = study._collect_one("AAPL", spec, str(out), manifest)
    study.write_json(out / "collection_receipt.json", {
        "complete": True, "spec_sha256": spec["_sha256"], "assets": [receipt]})
    report = study.evaluate(spec, out, manifest)
    from scripts import prophet_fusion_mechanism_verify as verifier
    rows = pd.read_parquet(out / "graded_research_events.parquet")
    verified_rows = verifier.verify_rows(rows, {"AAPL": prices}, prices, spec)
    verified_summaries = verifier.verify_summaries(rows, report, spec)
    assert verified_rows["events_verified"] == len(rows)
    assert verified_summaries["arm_summaries_verified"] == 24
    assert len(report["arm_summaries"]) == 24
    assert len(report["primary_comparisons"]) == 11
    assert report["promotion_eligible"] is False
    assert all(row["net_excess"] is None or row["net_excess"] < 0
               for row in report["arm_summaries"])
    assert len(report["chronological_fold_qualification"]["folds"]) > 0
    assert json.loads((out / "report.json").read_text())["spec_sha256"] == spec["_sha256"]
    markdown = (out / "report.md").read_text()
    assert "NOT_PROMOTION_BEARING" in markdown
    assert "Familywise" in markdown
    assert "survivor" in markdown.lower()
