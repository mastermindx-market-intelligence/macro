"""Synthetic market calendars and outcomes; no historical performance claims."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from engine.release_surprise_confirmation import EvidenceError, authority, instant, iso
from engine.release_surprise_study import (
    evaluate_matrix, forward_outcomes, join_regime_features, walk_forward,
)

SESSIONS = [f"2026-11-{d:02d}T21:00:00Z" for d in (9, 10, 11, 12, 13, 16, 17, 18)]


def event(known="2026-11-10T13:31:00Z", **overrides):
    row = {"event_id": "pair:fixture", "pair_id": "cpi_headline_ppi_headline",
           "period": "2026-10", "known_at": known, "quadrant": "cpi_hot_ppi_cold",
           "agreement": False, "cpi_surprise": 0.1, "ppi_surprise": -0.1,
           "display_derived_allowed": True}
    row.update(overrides)
    return row


def bars():
    return [{"symbol": "SPY", "close_at": stamp, "known_at": stamp,
             "close": 100.0 + i, "basis": "total_return_adjusted_close",
             "source_ref": "synthetic-test"} for i, stamp in enumerate(SESSIONS)]


def outcomes(events=None, prices=None, **kwargs):
    return forward_outcomes(events if events is not None else [event()], prices if prices is not None else bars(),
                            SESSIONS, symbols=["SPY"], horizons=[1], asof="2026-11-19T00:00:00Z", **kwargs)


def study_rows(n=80):
    rng = np.random.default_rng(31)
    rows = []
    quadrants = ("cpi_cold_ppi_cold", "cpi_hot_ppi_hot", "cpi_hot_ppi_cold", "cpi_cold_ppi_hot")
    for i in range(n):
        year, month = 2010 + i // 12, i % 12 + 1
        start = datetime(year, month, 5, 13, 31, tzinfo=timezone.utc)
        quadrant = quadrants[i % 4]
        cpi = -0.1 if "cpi_cold" in quadrant else 0.1
        ppi = -0.1 if "ppi_cold" in quadrant else 0.1
        agreement = (cpi == ppi)
        rows.append({"event_id": f"synthetic:{i}", "pair_id": "cpi_headline_ppi_headline",
                     "period": f"{year}-{month:02d}", "symbol": "SPY", "horizon": 20,
                     "signal_known_at": iso(start), "entry_at": iso(start + timedelta(hours=7)),
                     "exit_at": iso(start + timedelta(days=20)),
                     "outcome_known_at": iso(start + timedelta(days=20, hours=1)),
                     "quadrant": quadrant, "agreement": agreement,
                     "cpi_surprise": cpi, "ppi_surprise": ppi,
                     "net_return_pct": float(0.5 + 1.5 * agreement + rng.normal(0, 0.5)),
                     "max_drawdown_pct": -1.0, "round_trip_cost_bps": 0.0,
                     "display_derived_allowed": True})
    return rows


def test_entry_same_day_when_preclose_but_strictly_after_signal():
    result = outcomes()["rows"][0]
    assert result["entry_at"] == "2026-11-10T21:00:00Z"
    assert result["exit_at"] == "2026-11-11T21:00:00Z"
    assert result["return_pct"] == pytest.approx((102 / 101 - 1) * 100)
    result = outcomes([event("2026-11-10T21:00:00Z")])["rows"][0]
    assert result["entry_at"] == "2026-11-11T21:00:00Z"


def test_second_report_clock_is_not_reset_to_first_report():
    individual = outcomes([event("2026-11-10T13:31:00Z")])["rows"][0]
    pair = outcomes([event("2026-11-13T13:31:00Z")])["rows"][0]
    assert individual["entry_at"] != pair["entry_at"]
    assert pair["entry_at"] == "2026-11-13T21:00:00Z"
    assert pair["exit_at"] == "2026-11-16T21:00:00Z"


def test_missing_bar_never_shortens_session_horizon():
    result = outcomes(prices=[bar for bar in bars() if bar["close_at"] != "2026-11-11T21:00:00Z"])
    assert not result["rows"]
    assert result["exclusions"] == {"missing_session_price": 1}


def test_immature_and_late_available_outcomes_are_distinct():
    result = forward_outcomes([event()], bars(), SESSIONS, symbols=["SPY"], horizons=[5], asof="2026-11-13T22:00:00Z")
    assert result["exclusions"] == {"outcome_not_matured": 1}
    data = bars()
    data[2]["known_at"] = "2026-12-01T00:00:00Z"
    assert outcomes(prices=data)["exclusions"] == {"outcome_not_known_at_evaluation_cut": 1}


def test_calendar_coverage_and_missing_asset_are_explicit():
    assert outcomes([event("2026-11-01T00:00:00Z")])["exclusions"] == {"calendar_left_coverage_unknown": 1}
    assert outcomes([event("2026-11-18T20:00:00Z")])["exclusions"] == {"calendar_right_coverage_missing": 1}
    assert outcomes(prices=[])["exclusions"] == {"missing_session_price": 1}


@pytest.mark.parametrize("change", [{"close": 0}, {"close": True}, {"close": float("nan")},
                                    {"basis": "unadjusted_close"}, {"source_ref": None},
                                    {"known_at": "2020-01-01T00:00:00Z"}])
def test_price_contract_refuses_bad_rows(change):
    data = bars()
    data[1].update(change)
    with pytest.raises(EvidenceError):
        outcomes(prices=data)


def test_duplicate_prices_and_events_refused():
    with pytest.raises(EvidenceError, match="duplicate_price_bar"):
        outcomes(prices=bars() + bars()[:1])
    with pytest.raises(EvidenceError, match="event_identity_missing_or_duplicate"):
        outcomes([event(), event()])


def test_cost_and_close_tail_risk_are_separate_from_gross_return():
    data = bars()
    data[2]["close"] = 90
    result = outcomes(prices=data, round_trip_cost_bps=10)["rows"][0]
    assert result["net_return_pct"] == pytest.approx(result["return_pct"] - 0.1)
    assert result["max_drawdown_pct"] == pytest.approx((90 / 101 - 1) * 100)
    assert result["risk_basis"] == "session_closes_only_not_intraday"


def test_whole_family_report_preserves_empty_cells_and_baseline_gap():
    rows = study_rows()
    result = evaluate_matrix(rows, symbols=["SPY"], horizons=[20], draws=100, min_cell_n=10)
    assert result["declared_hypotheses"] == 14
    assert result["authority"] == authority()
    agreement = next(r for r in result["cells"] if r["pair_id"] == "cpi_headline_ppi_headline" and r["condition"] == "agreement")
    assert agreement["gap_pct"] == pytest.approx(agreement["conditional"]["mean_pct"] - agreement["baseline"]["mean_pct"])
    assert agreement["p_holm"] >= agreement["p_bootstrap_approx"]
    missing = [r for r in result["cells"] if r["pair_id"] == "cpi_core_ppi_headline"]
    assert all(r["status"] == "insufficient_evidence" and r["p_holm"] is None for r in missing)
    assert result == evaluate_matrix(rows, symbols=["SPY"], horizons=[20], draws=100, min_cell_n=10)


def test_constant_positive_returns_do_not_become_alpha():
    rows = study_rows()
    for row in rows:
        row["net_return_pct"] = 1.0
    result = evaluate_matrix(rows, symbols=["SPY"], horizons=[20], draws=100, min_cell_n=10)
    cells = [r for r in result["cells"] if r["pair_id"] == "cpi_headline_ppi_headline"]
    assert all(r["gap_pct"] == 0 and r["p_bootstrap_approx"] is None for r in cells)


def test_duplicate_macro_observations_do_not_inflate_sample_size():
    rows = study_rows()
    with pytest.raises(EvidenceError, match="duplicate_macro_period"):
        evaluate_matrix(rows + rows[:1], symbols=["SPY"], horizons=[20], draws=100)


def test_walk_forward_purges_labels_and_fits_train_only():
    rows = study_rows(30)
    baseline = walk_forward(rows, min_train=8)
    assert baseline["predictions"]
    first = baseline["predictions"][0]
    changed = copy.deepcopy(rows)
    for row in changed:
        if row["signal_known_at"] >= first["decision_at"]:
            row["net_return_pct"] += 1_000_000
    modified = walk_forward(changed, min_train=8)["predictions"][0]
    assert modified["forecast_pct"] == first["forecast_pct"]
    assert modified["unconditional_forecast_pct"] == first["unconditional_forecast_pct"]
    assert all(instant(p["latest_training_outcome_known_at"]) + timedelta(hours=24) < instant(p["decision_at"]) for p in baseline["predictions"])
    assert baseline["validation_class"] == "retrospective_walk_forward_not_prospective"


def test_late_outcome_labels_cannot_train_the_challenger():
    rows = study_rows(30)
    for row in rows[:20]:
        row["outcome_known_at"] = "2099-01-01T00:00:00Z"
    result = walk_forward(rows, min_train=8)
    assert result["predictions"][0]["event_id"] == "synthetic:28"
    assert result["predictions"][0]["n_train"] == 8


def test_missing_features_abstain_instead_of_zero_imputing():
    rows = study_rows(30)
    for row in rows:
        row["cpi_surprise"] = None
    result = walk_forward(rows, min_train=8)
    assert not result["predictions"]
    assert result["exclusions"]["missing_feature"] == 30


def test_regime_context_is_asof_source_bound_and_unknown_is_not_zero():
    obs = [{"name": "two_year_yield", "value": 4.1, "observed_at": "2026-11-09T21:00:00Z",
            "known_at": "2026-11-09T21:01:00Z", "source_ref": "synthetic-rates"},
           {"name": "two_year_yield", "value": 9.9, "observed_at": "2026-11-10T14:00:00Z",
            "known_at": "2026-11-10T14:01:00Z", "source_ref": "future-unavailable"}]
    result = join_regime_features([event()], obs, names=["two_year_yield", "breadth"])[0]
    assert result["regime_features"] == {"two_year_yield": 4.1}
    assert result["regime_missing"] == ["breadth"]
    assert result["regime_source_refs"] == {"two_year_yield": "synthetic-rates"}


def test_resampling_preserves_calendar_gaps_and_counts_distinct_events():
    rows = [r for i, r in enumerate(study_rows(80)) if i % 5 != 0]
    result = evaluate_matrix(rows, symbols=["SPY"], horizons=[20], draws=100, min_cell_n=10)
    assert result["resampling_clock"] == "shared_complete_reference_month_calendar"
    assert result["calendar_months"] == 79
    populated = [r for r in result["cells"] if r["pair_id"] == "cpi_headline_ppi_headline"]
    assert all(r["distinct_macro_periods"] == 64 for r in populated)
    assert all("independent_macro_periods" not in r for r in populated)


def _strong_injected_effect_rows():
    """Deterministic synthetic effect, not historical market observations."""
    from engine.release_surprise_study import QUADRANTS
    rng = np.random.default_rng(47)
    rows = []
    for i in range(240):
        year, month = 2000 + i // 12, i % 12 + 1
        agreement = i % 4 < 2
        rows.append({"pair_id": "cpi_headline_ppi_headline", "symbol": "SPY", "horizon": 20,
                     "period": f"{year:04d}-{month:02d}",
                     "signal_known_at": f"{year:04d}-{month:02d}-13T13:31:00Z",
                     "quadrant": QUADRANTS[i % 4], "agreement": agreement,
                     "net_return_pct": (4.0 if agreement else -2.0) + float(rng.normal(0, 0.5)),
                     "max_drawdown_pct": -2.0})
    return rows


def test_default_bootstrap_can_resolve_the_complete_declared_family():
    from engine.release_surprise_study import DEFAULT_BOOTSTRAP_DRAWS
    result = evaluate_matrix(_strong_injected_effect_rows())
    assert result["declared_hypotheses"] == 168  # unavailable assets/variants retain slots
    assert result["bootstrap_draws"] == DEFAULT_BOOTSTRAP_DRAWS == 9999
    resolution = result["monte_carlo_resolution"]
    assert resolution["best_possible_first_holm_p"] == pytest.approx(0.0168)
    assert resolution["minimum_draws_for_first_holm_p_below_005"] == 3360
    assert resolution["supports_005_first_rejection"] is True
    gap = next(row for row in result["cells"] if row["pair_id"] == "cpi_headline_ppi_headline"
               and row["symbol"] == "SPY" and row["horizon"] == 20
               and row["condition"] == "agreement_vs_disagreement")
    assert gap["gap_pct"] > 5.0
    assert gap["p_holm"] < 0.05
    assert gap["raw_p_resolution_floor"] == pytest.approx(1 / (gap["valid_bootstrap_draws"] + 1))
    assert result["authority"] == authority()
    assert result["inference"] == "exploratory_time_block_bootstrap_not_prospective_validation"


def test_low_draw_budget_is_explicitly_resolution_limited_not_no_edge():
    result = evaluate_matrix(_strong_injected_effect_rows(), draws=800)
    resolution = result["monte_carlo_resolution"]
    assert resolution["status"] == "resolution_limited"
    assert resolution["supports_005_first_rejection"] is False
    assert resolution["best_possible_first_holm_p"] == pytest.approx(168 / 801)
    assert all(row["p_holm"] is None or row["p_holm"] >= 168 / 801 - 1e-12
               for row in result["cells"])
    assert result["authority"] == authority()


def test_chunked_shared_bootstrap_equals_literal_masked_estimand():
    from engine.release_surprise_study import _bootstrap_mean_gaps
    rng = np.random.default_rng(8)
    values = np.array([1.2, np.nan, -0.7, 3.1, 0.2, np.nan, -1.0])
    selected = np.array([True, False, False, True, False, False, False])
    reference = np.isfinite(values)
    indices = rng.integers(0, len(values), size=(530, len(values)))
    indices[0] = 1  # no observed rows, not a zero-return month
    indices[260] = 6  # reference exists but selected group is absent
    literal = []
    for sample in indices:
        sm, rm = selected[sample], reference[sample]
        if sm.any() and rm.any():
            literal.append(float(np.mean(values[sample][sm]) - np.mean(values[sample][rm])))
    actual = _bootstrap_mean_gaps(values, selected, reference, indices)
    assert len(actual) < len(indices)
    np.testing.assert_allclose(actual, literal, rtol=1e-13, atol=1e-13)
    assert np.isfinite(actual).all()


def test_adequate_draw_resolution_does_not_make_missing_data_available():
    result = evaluate_matrix([])
    assert result["monte_carlo_resolution"]["status"] == "adequate_resolution_only"
    assert all(row["status"] == "insufficient_evidence" for row in result["cells"])
    assert all(row["p_bootstrap_approx"] is None for row in result["cells"])
    assert result["authority"] == authority()
