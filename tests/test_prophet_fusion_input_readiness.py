"""The readiness consumer must not acquire outcome authority or manufacture history."""
from __future__ import annotations

import json
import pandas as pd
import pytest

from scripts import prophet_fusion_input_readiness as r
from scripts.prophet_fusion_arena import load_registry
from scripts.prophet_fusion_mechanisms import MechanismRefusal
from scripts.prophet_fusion_mechanism_study import write_json


@pytest.fixture
def registry():
    return load_registry()


@pytest.fixture
def frame():
    return pd.DataFrame({
        "stamp_date": ["2026-01-20", "2026-01-21", "2026-01-22"],
        "ticker": ["AAPL", "AAPL", "MSFT"],
        "board_definition": ["vA", "vA", "vB"],
        "selection_era": ["same", "same", "same"],
        "alpha": [0.0, 0.2, 0.1], "alpha_percentile": [0.0, 0.7, 0.6],
        "regime__quad": ["Q1", "Q2", "Q1"],
        "regime__as_of": ["2026-01-16", "2026-01-21", "2026-01-22"],
        "forensics__action": ["clear", "clear", "caution"],
        "forensics__as_of": ["2026-01-20", "2026-01-21", "2026-01-22"],
    })


def member(report, key):
    return next(x for x in report["members"] if x["member"] == key)


def test_zero_and_false_are_not_missing():
    cleaned = r.clean_observations(pd.Series([0.0, False, "unknown", "", None, "Q1", float("inf")], dtype=object))
    assert cleaned.notna().tolist() == [True, True, False, False, False, True, False]


def test_loader_chooses_only_registry_inputs_and_identity(registry):
    names = ["stamp_date", "ticker", "alpha", "regime__quad", "regime__as_of", "outcome_graded",
             "graded_at", "fwd_ret_21", "net_return", "some_unknown_feature", "prophet_score"]
    chosen = r.selected_columns(names, registry)
    assert chosen == ["alpha", "regime__as_of", "regime__quad", "stamp_date", "ticker"]


def test_without_observation_date_refuse_before_reading_values(registry):
    with pytest.raises(MechanismRefusal, match="STAMP_DATE"):
        r.selected_columns(["ticker", "alpha"], registry)


def test_native_status_blocks_snapshot_fundamentals(frame, registry):
    report = r.audit_frame(frame, registry)
    row = member(report, "F7_QUALITY_FUNDAMENTAL.forensics_scalars")
    assert row["raw_known_fraction"] > 0
    assert row["native_backtest_status_allowed"] is False
    assert row["date_checked_known_fraction"] == 0
    assert "PITRefusal" in row["native_refusal"]


def test_market_holiday_does_not_make_prior_session_stale(frame, registry):
    # January 19, 2026 is the NYSE MLK holiday: Friday -> Tuesday is one session.
    report = r.audit_frame(frame, registry)
    row = member(report, "F6_MACRO_REGIME.regime_dim")
    assert row["stale_source_date_rows"] == 0
    assert row["source_date_after_row_rows"] == 0
    assert row["intraday_availability_proven"] is False
    assert row["same_day_source_rows"] == 2


def test_future_and_stale_sources_are_measured_not_imputed(frame, registry):
    frame.loc[0, "regime__as_of"] = "2026-01-23"
    frame.loc[1, "regime__as_of"] = "2026-01-02"
    report = r.audit_frame(frame, registry)
    row = member(report, "F6_MACRO_REGIME.regime_dim")
    assert row["source_date_after_row_rows"] == 1
    assert row["stale_source_date_rows"] == 1
    assert row["date_checked_known_fraction"] < row["raw_known_fraction"]


def test_absent_source_clock_stays_unknown(frame, registry):
    report = r.audit_frame(frame.drop(columns=["regime__as_of"]), registry)
    row = member(report, "F6_MACRO_REGIME.regime_dim")
    assert row["source_clock_unknown_rows"] == 3
    assert row["date_checked_known_fraction"] == 0


def test_row_count_does_not_overcome_missing_independent_months(frame, registry):
    repeated = pd.concat([frame] * 1000, ignore_index=True)
    report = r.audit_frame(repeated, registry)
    axis = next(x for x in report["native_regime_estimability"] if x["axis"] == "regime__quad")
    assert report["rows"] == 3000
    assert report["distinct_months"] == 1
    assert axis["n_states"] == 2
    assert axis["estimable"] is False
    assert axis["verdict"] == "insufficient_contrast"


def test_placeholder_regime_is_not_a_new_state(frame, registry):
    frame["regime__quad"] = ["Q1", "unknown", None]
    report = r.audit_frame(frame, registry)
    axis = next(x for x in report["native_regime_estimability"] if x["axis"] == "regime__quad")
    assert axis["n_states"] == 1
    assert axis["estimable"] is False


def test_invalid_session_does_not_get_admissible_by_fresh_clock(frame, registry):
    frame.loc[0, "stamp_date"] = "2026-01-18"
    frame.loc[0, "regime__as_of"] = "2026-01-18"
    report = r.audit_frame(frame, registry)
    assert report["invalid_session_or_date_rows"] == 1
    assert member(report, "F6_MACRO_REGIME.regime_dim")["source_clock_unknown_rows"] == 1


def test_distinct_board_definitions_and_ambiguity_are_retained(frame, registry):
    report = r.audit_frame(frame, registry)
    assert report["identity_populations"]["board_definition"] == {"vA": 2, "vB": 1}
    assert report["promotion_eligible"] is False
    assert report["date_checks_are_admission"] is False
    assert report["outcomes_read"] is False
    assert report["original_receipt_proof"] == "NOT_ESTABLISHED_BY_THIS_AUDIT"


def test_empty_registered_members_are_not_complete_coverage(frame, registry):
    row = member(r.audit_frame(frame, registry), "F6_MACRO_REGIME.factor_dispersion_state")
    assert row["date_checked_known_fraction"] == 0
    assert row["native_backtest_status_allowed"] is False


def test_report_consumer_keeps_constraints_and_serializes_without_nan(frame, registry, tmp_path):
    report = r.audit_frame(frame, registry)
    report["source_base"] = "a" * 40
    text = r.render(report)
    assert "Outcome-blind" in text
    assert "twelve distinct months" in text
    assert "No W3 or W2 outcomes were read" in text
    path = tmp_path / "readiness.json"
    write_json(path, report)
    assert json.loads(path.read_text())["outcomes_read"] is False


def test_nonimmutable_source_is_refused_before_git(registry):
    with pytest.raises(MechanismRefusal, match="IMMUTABLE"):
        r.collect_source("main", registry)


def test_native_chronological_floors_cannot_be_satisfied_by_many_names(frame, registry):
    report = r.audit_frame(pd.concat([frame] * 1000, ignore_index=True), registry)
    for row in report["native_fold_readiness"].values():
        assert row["folds"] == []
        assert row["refusals"]
