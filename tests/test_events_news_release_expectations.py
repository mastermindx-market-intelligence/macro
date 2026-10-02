"""Events & News release expectation/benchmark projection — no fake street survey."""
from copy import deepcopy

import pytest

from engine import events_news_release_evidence as view

ASOF = "2026-10-01T21:00:00Z"
FORECAST_ASOF = "2026-10-01T20:21:25Z"


def forecast_payload():
    return {
        "schema": "release_forecast.v2",
        "asof": FORECAST_ASOF,
        "display_only": True,
        "authority": {"can_score": False, "can_size": False, "can_trade": False},
        "methodology_status": {
            "forecast_epoch": "legacy_cross_vintage_training_target_experimental",
            "accuracy_claim": "withheld_until_clean_aligned_forward_evidence",
            "street_consensus": "unavailable",
        },
        "upcoming": [
            {
                "release": "cpi",
                "release_type": "cpi_headline",
                "period": "2026-09",
                "release_date": "2026-10-14",
                "target": "mom_sa_pct",
                "projection": {"point": 0.36, "p10": 0.14, "p90": 0.60},
                "primary_forecast_basis": "combined_v1_benchmark_augmented",
                "combined": {
                    "combined_point": 0.48,
                    "p10": 0.18,
                    "p90": 0.70,
                    "n_scored_basis": 0,
                    "combined_components": {"cold_start": True},
                    "display_only": True,
                    "authority": False,
                },
                "benchmark_set": {
                    "naive_prior": 0.39,
                    "trailing_3m": 0.02,
                    "ar_model": -0.42,
                    "cleveland_nowcast": 0.53,
                    "market_implied": {
                        "source": "kalshi",
                        "implied_median": 0.52,
                        "asof": "2026-10-01",
                    },
                },
                "model_epoch": "champion_legacy_target_v1",
                "target_epoch": "legacy_cross_vintage_initial_levels_v0",
                "cutoff_label": "T-1",
                "input_completeness": 1.0,
                "basis_warning": "Benchmark-augmented model context; not a street survey comparison.",
            },
            {
                "release": "cpi",
                "release_type": "cpi_core",
                "period": "2026-09",
                "release_date": "2026-10-14",
                "target": "mom_sa_pct",
                "projection": {"point": 0.27, "p10": 0.10, "p90": 0.42},
                "benchmark_set": {"naive_prior": 0.29, "trailing_3m": 0.16},
                "model_epoch": "champion_legacy_target_v1",
                "target_epoch": "legacy_cross_vintage_initial_levels_v0",
                "cutoff_label": "T-1",
                "input_completeness": 1.0,
            },
        ],
        "last_scored_all_forward": [],
    }


def cpi_event():
    return {
        "type": "CPI",
        "date": "2026-10-14",
        "reference_period": "2026-09",
    }


def pce_event():
    return {
        "type": "PCE",
        "date": "2026-09-30",
        "reference_period": "2026-08",
    }


def official_pce():
    event = pce_event()
    binding = {name: event.get(name) for name in view.official._EXPLICIT_REFERENCE_FIELDS}
    return {
        "schema": view.SCHEMA,
        "display_only": True,
        "authority": False,
        "event_type": "PCE",
        "release_date": "2026-09-30",
        "reference_binding": binding,
        "as_of_input": ASOF,
        "metrics": [
            {
                "release": "pce_headline",
                "metric_id": "pce_headline_mom",
                "unit": "percent",
                "period": "2026-08",
                "status": "available",
                "receipt_id": "official_actual:headline",
                "actual": 0.30,
            },
            {
                "release": "pce_core",
                "metric_id": "pce_core_mom",
                "unit": "percent",
                "period": "2026-08",
                "status": "available",
                "receipt_id": "official_actual:core",
                "actual": 0.20,
            },
        ],
    }


def scored_pce(eligible=True):
    return [
        {
            "schema": 2,
            "row_type": "scored",
            "model": None,
            "release": "pce_headline",
            "period": "2026-08",
            "release_date": "2026-09-30",
            "actual_receipt_id": "official_actual:headline",
            "frozen_projection_point": 0.31,
            "frozen_projection_p10": 0.17,
            "frozen_projection_p90": 0.42,
            "frozen_asof_night": "2026-09-29",
            "model_epoch": "champion_legacy_target_v1",
            "target_epoch": "legacy_cross_vintage_initial_levels_v0",
            "cutoff_label": "T-1",
            "evaluation": {
                "eligible": eligible,
                "excluded_defect_ids": [] if eligible else ["DN-004"],
                "basis": "structured_defect_notices_v1",
            },
        },
        {
            "schema": 2,
            "row_type": "scored",
            "model": None,
            "release": "pce_core",
            "period": "2026-08",
            "release_date": "2026-09-30",
            "actual_receipt_id": "official_actual:core",
            "frozen_projection_point": 0.23,
            "frozen_projection_p10": 0.10,
            "frozen_projection_p90": 0.36,
            "frozen_asof_night": "2026-09-29",
            "model_epoch": "champion_legacy_target_v1",
            "target_epoch": "legacy_cross_vintage_initial_levels_v0",
            "cutoff_label": "T-1",
            "evaluation": {
                "eligible": eligible,
                "excluded_defect_ids": [] if eligible else ["DN-004"],
                "basis": "structured_defect_notices_v1",
            },
        },
    ]


def test_future_context_uses_declared_primary_and_never_calls_it_survey_data():
    out = view.event_expectation_context(cpi_event(), forecast_payload(), as_of=ASOF)
    assert out["status"] == "available"
    assert out["street_survey_status"] == "unavailable"
    assert "consensus" not in str({k: v for k, v in out.items() if k != "methodology"}).lower()
    headline, core = out["metrics"]
    assert headline["status"] == "experimental_model_context"
    assert headline["point"] == 0.48
    assert headline["basis"] == "combined_v1_benchmark_augmented"
    assert headline["cold_start"] is True
    assert headline["n_scored_basis"] == 0
    assert headline["benchmarks"]["market_implied"]["implied_median"] == 0.52
    assert core["point"] == 0.27
    assert core["basis"] == "champion_model"


def test_combined_block_never_silently_wins_without_owner_declaration():
    payload = forecast_payload()
    payload["upcoming"][0].pop("primary_forecast_basis")
    out = view.event_expectation_context(cpi_event(), payload, as_of=ASOF)
    assert out["metrics"][0]["point"] == 0.36
    assert out["metrics"][0]["basis"] == "champion_model"


def test_declared_combined_primary_fails_closed_when_contract_is_invalid():
    payload = forecast_payload()
    payload["upcoming"][0]["combined"]["authority"] = True
    out = view.event_expectation_context(cpi_event(), payload, as_of=ASOF)
    metric = out["metrics"][0]
    assert metric["status"] == "model_point_unavailable"
    assert metric["reason"] == "primary_model_context_invalid"
    assert metric["point"] is None


def test_future_context_requires_exact_period_and_release_date():
    payload = forecast_payload()
    event = cpi_event()
    event["reference_period"] = "2026-08"
    out = view.event_expectation_context(event, payload, as_of=ASOF)
    assert all(m["reason"] == "no_matching_forecast_context" for m in out["metrics"])

    payload = forecast_payload()
    payload["upcoming"][0]["release_date"] = "2026-10-15"
    out = view.event_expectation_context(cpi_event(), payload, as_of=ASOF)
    assert out["metrics"][0]["reason"] == "no_matching_forecast_context"


def test_future_artifact_cannot_arrive_after_the_component_snapshot():
    payload = forecast_payload()
    payload["asof"] = "2026-10-02T00:00:00Z"
    out = view.event_expectation_context(cpi_event(), payload, as_of=ASOF)
    assert out["reason"] == "forecast_after_snapshot"
    assert out["metrics"] == []


def test_authority_or_methodology_drift_withholds_context():
    payload = forecast_payload()
    payload["authority"]["can_trade"] = True
    assert view.event_expectation_context(cpi_event(), payload, as_of=ASOF)["reason"] == "forecast_authority_contract_mismatch"

    payload = forecast_payload()
    payload["methodology_status"]["street_consensus"] = "connected"
    assert view.event_expectation_context(cpi_event(), payload, as_of=ASOF)["reason"] == "forecast_methodology_contract_mismatch"


def test_benchmark_only_mode_stays_benchmark_only_without_point():
    payload = forecast_payload()
    payload["upcoming"] = [{
        "release": "claims",
        "release_type": "claims",
        "period": "2026-10-08",
        "release_date": "2026-10-08",
        "projection": {"mode": "benchmark_only", "reason": "model failed kill rule"},
        "benchmark_set": {"naive_prior": 197, "trailing_4w": 201.25, "ar_model": 195.66},
        "model_epoch": "champion_legacy_target_v1",
        "target_epoch": "official_initial_level_v1",
        "cutoff_label": "T-1",
    }]
    out = view.event_expectation_context(
        {"type": "CLAIMS", "date": "2026-10-08"}, payload, as_of=ASOF)
    metric = out["metrics"][0]
    assert metric["status"] == "benchmark_only"
    assert metric["point"] is None
    assert metric["benchmarks"]["trailing_4w"] == 201.25


def test_historical_comparison_requires_exact_official_receipt_and_eligible_evaluation():
    payload = forecast_payload()
    payload["upcoming"] = []
    payload["last_scored_all_forward"] = scored_pce(True)
    out = view.event_expectation_context(
        pce_event(), payload, as_of=ASOF, official_evidence=official_pce())
    assert out["status"] == "available"
    headline, core = out["metrics"]
    assert headline["status"] == "historical_model_comparison"
    assert headline["point"] == 0.31
    assert headline["difference"] == pytest.approx(-0.01)
    assert headline["frozen_asof_night"] == "2026-09-29"
    assert core["difference"] == pytest.approx(-0.03)


def test_ineligible_historical_evaluation_withholds_point_and_difference():
    payload = forecast_payload()
    payload["upcoming"] = []
    payload["last_scored_all_forward"] = scored_pce(False)
    out = view.event_expectation_context(
        pce_event(), payload, as_of=ASOF, official_evidence=official_pce())
    assert all(m["status"] == "comparison_withheld" for m in out["metrics"])
    assert all(m["reason"] == "evaluation_ineligible" for m in out["metrics"])
    assert all(m["point"] is None for m in out["metrics"])
    assert out["metrics"][0]["excluded_defect_ids"] == ["DN-004"]


def test_historical_receipt_mismatch_cannot_compare_model_to_another_actual():
    payload = forecast_payload()
    payload["upcoming"] = []
    rows = scored_pce(True)
    rows[0]["actual_receipt_id"] = "official_actual:other"
    payload["last_scored_all_forward"] = rows
    out = view.event_expectation_context(
        pce_event(), payload, as_of=ASOF, official_evidence=official_pce())
    assert out["metrics"][0]["reason"] == "no_matching_frozen_model_context"
    assert out["metrics"][0]["point"] is None


def test_past_event_without_bound_official_result_does_not_show_model_comparison():
    payload = forecast_payload()
    payload["upcoming"] = []
    payload["last_scored_all_forward"] = scored_pce(True)
    out = view.event_expectation_context(pce_event(), payload, as_of=ASOF)
    assert out["status"] == "unavailable"
    assert all(m["reason"] == "official_result_required_for_historical_comparison" for m in out["metrics"])


def test_market_implied_string_is_not_reparsed_into_a_number():
    payload = forecast_payload()
    payload["upcoming"][0]["benchmark_set"]["market_implied"] = {
        "source": "polymarket", "implied": "0.2%", "asof": "2026-10-01"
    }
    out = view.event_expectation_context(cpi_event(), payload, as_of=ASOF)
    assert "market_implied" not in out["metrics"][0]["benchmarks"]


def test_attach_expectation_context_returns_copies_and_keeps_malformed_members():
    events = [cpi_event(), None]
    before = deepcopy(events)
    out = view.attach_event_expectation_context(events, forecast_payload(), as_of=ASOF)
    assert events == before
    assert out[0] is not events[0]
    assert out[0]["expectation_context"]["status"] == "available"
    assert out[1] is None
    assert view.attach_event_expectation_context(None, forecast_payload(), as_of=ASOF) is None
