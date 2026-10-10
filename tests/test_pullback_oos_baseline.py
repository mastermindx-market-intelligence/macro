"""Research-only OOS baseline: no future train leakage or publication authority."""
from __future__ import annotations

import pytest

from research.grey_deer.pullback_oos_baseline import (
    predict_research_quantiles, evaluate_research_predictions, pinball,
)

BASIS = "split_adjusted_dividend_unadjusted_close"


def row(i: int, *, phase="underway", market="us", basis=BASIS,
        origin_year=2015, label_end_year=2016, episode=None, loss=None):
    origin = f"{origin_year}-{1 + (i // 27):02d}-{1 + (i % 27):02d}"
    target = f"{label_end_year}-{1 + (i // 27):02d}-{1 + (i % 27):02d}"
    return {"market": market, "price_basis": basis, "phase": phase,
            "episode_proxy": episode if episode is not None else f"episode-{i}",
            "label": {"matured": True, "origin": origin,
                      "target_end": target, "horizon_sessions": 21,
                      "additional_loss_fraction": (i / 100 if loss is None else loss)}}


def forecast(rows, phase=None):
    return predict_research_quantiles(
        rows, forecast_origin="2019-02-01", training_end_exclusive="2018-01-01",
        market="us", price_basis=BASIS, phase=phase,
        horizon_sessions=21, min_origins=30, min_episodes=20)


def test_empirical_quantiles_are_sorted_interpolated_and_explicitly_not_promoted():
    out = forecast([row(i) for i in range(40)])
    assert out["state"] == "research_only"
    assert out["publication_authorized"] is False
    assert out["training_origins"] == 40
    assert out["distinct_episode_proxies"] == 40
    assert out["q25"] == pytest.approx(0.0975)
    assert out["q75"] == pytest.approx(0.2925)
    assert out["q90"] == pytest.approx(0.351)
    assert out["q25"] <= out["q75"] <= out["q90"]


def test_phase_requires_own_population_not_fallback_to_other_phases():
    all_rows = [row(i, phase=("underway" if i < 25 else "monitoring")) for i in range(45)]
    assert forecast(all_rows)["state"] == "research_only"
    phased = forecast(all_rows, phase="underway")
    assert phased["state"] == "unavailable"
    assert phased["reason"] == "insufficient_training_origins"
    assert phased["q25"] is None


def test_few_episode_proxies_prevent_precise_tail_appearance():
    sample = [row(i, episode="one-episode") for i in range(45)]
    out = forecast(sample, phase="underway")
    assert out["state"] == "unavailable"
    assert out["reason"] == "insufficient_episode_proxies"
    assert out["distinct_episode_proxies"] == 1


def test_different_market_basis_and_horizon_cannot_train_target():
    matches = [row(i) for i in range(35)]
    others = [row(i+35, market="cn", basis=BASIS) for i in range(5)]
    others += [row(i+40, basis="total_return_close") for i in range(5)]
    others.append({**row(55), "label": {**row(55)["label"], "horizon_sessions": 5}})
    out = forecast(matches + others)
    assert out["training_origins"] == 35


def test_training_requires_label_maturity_before_both_test_and_frozen_train_cutoff():
    accepted = [row(i) for i in range(32)]
    leaked = row(90, origin_year=2017, label_end_year=2018, loss=0.99)
    late = row(91, origin_year=2019, label_end_year=2020, loss=0.99)
    future = row(92, origin_year=2020, label_end_year=2021, loss=0.99)
    same_day = row(93, origin_year=2019, label_end_year=2019, loss=0.99)
    out = forecast(accepted + [leaked, late, future, same_day])
    assert out["training_origins"] == 32
    assert out["q90"] < 0.5


def test_immature_labels_are_excluded_not_zero_loss():
    x = row(43)
    x["label"]["matured"] = False
    x["label"]["additional_loss_fraction"] = None
    out = forecast([row(i) for i in range(35)] + [x])
    assert out["training_origins"] == 35


@pytest.mark.parametrize("loss", [True, float("nan"), -0.01, 1.1])
def test_malformed_mature_label_fails_closed(loss):
    samples = [row(i) for i in range(32)]
    samples[0]["label"]["additional_loss_fraction"] = loss
    with pytest.raises(ValueError):
        forecast(samples)


def test_partial_train_below_minimum_returns_explicit_unavailable():
    out = forecast([row(i) for i in range(5)])
    assert out["state"] == "unavailable"
    assert out["publication_authorized"] is False
    assert out["q90"] is None


def test_pinball_returns_correct_directional_quantile_loss():
    assert pinball(0.25, y=0.2, qhat=0.1) == pytest.approx(0.025)
    assert pinball(0.25, y=0.05, qhat=0.1) == pytest.approx(0.0375)


def test_study_metrics_track_coverage_and_exceedance_without_publication():
    forecast_candidate = {
        "state": "research_only", "publication_authorized": False,
        "q25": 0.05, "q75": 0.15, "q90": 0.2
    }
    outcomes = [
        {"estimate": forecast_candidate, "observed_loss": x}
        for x in (0.10, 0.02, 0.25)
    ]
    result = evaluate_research_predictions(outcomes)
    assert result["evaluated_origins"] == 3
    assert result["interval_coverage"] == pytest.approx(1/3)
    assert result["interval_width"] == pytest.approx(0.1)
    assert result["q90_exceedance"] == pytest.approx(1/3)
    assert result["publication_authorized"] is False


def test_unavailable_predictions_are_counted_not_scored_as_zero():
    valid = {"state": "research_only", "q25": 0.01, "q75": 0.05, "q90": 0.1}
    rows = [{"estimate": valid, "observed_loss": 0.04},
            {"estimate": {"state": "unavailable"}, "observed_loss": 0.22}]
    result = evaluate_research_predictions(rows)
    assert result["evaluated_origins"] == 1
    assert result["unavailable_origins"] == 1


def test_invalid_publication_or_outcome_cannot_make_evaluation_pass():
    with pytest.raises(ValueError):
        evaluate_research_predictions([
            {"estimate": {"state": "research_only", "publication_authorized": True,
                          "q25":0.01,"q75":0.05,"q90":0.1}, "observed_loss": 0.03}
        ])
