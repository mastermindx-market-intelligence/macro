"""Source-inert, strict as-of 252-session relative-strength high reference.

The current session compares with the PREVIOUS 252 complete sessions: 253
paired daily closes are required, and a future outcome is never read.
No source admission, ranking, trades, notification, or predictive efficacy.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import math

import pytest

from engine.entry_radar.replay.rs_onset_features import (
    RS_252_DEFINITION_ID, RS_252_SCHEMA, describe_onset_features,
    describe_rs_252_reference,
)
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest
from tests.test_entry_radar_rs_onset_features import fixture, iso, lookup


def assert_sealed(result):
    assert result["schema"] == RS_252_SCHEMA
    assert result["definition_id"] == RS_252_DEFINITION_ID
    assert result["source_admitted"] is False
    assert result["ranking_authority"] is False
    assert result["detector_registered"] is False
    assert result["actual_issuance_proven"] is False
    assert result["outcomes_computed"] is False
    assert result["issued_at"] is None
    assert all(value is False for value in result["authority"].values())
    assert result["descriptor_sha256"] == digest({
        key: value for key, value in result.items() if key != "descriptor_sha256"
    })


def measurement(bundle):
    return describe_rs_252_reference(bundle)["reference"]


def test_genuinely_new_rs_high_requires_252_prior_completed_days():
    bundle = fixture(253)
    result = describe_rs_252_reference(bundle)
    assert_sealed(result)
    assert result["state"] == "RESEARCH_REFERENCE_AVAILABLE"
    ref = result["reference"]
    assert ref["status"] == "measured"
    assert ref["at_new_high"] is True
    assert ref["observations"] == 253
    assert ref["prior_high_session"] == bundle["calendar"]["sessions"][-2]
    assert ref["log_gap_to_prior_high"] > 0.0
    assert ref["known_at"] <= bundle["decision_at"]


def test_equal_retest_is_not_a_strict_new_high():
    bundle = fixture(253)
    target, prior = bundle["calendar"]["sessions"][-1], bundle["calendar"]["sessions"][-2]
    # Identical price ratios across the last two completed sessions exactly tie.
    lookup(bundle, "stock", target)["close"] = lookup(bundle, "stock", prior)["close"]
    lookup(bundle, "benchmark", target)["close"] = lookup(bundle, "benchmark", prior)["close"]
    ref = measurement(bundle)
    assert ref["status"] == "measured"
    assert ref["at_new_high"] is False
    assert ref["log_gap_to_prior_high"] == pytest.approx(0.0, abs=1e-12)


def test_weakening_relative_strength_is_not_a_high():
    bundle = fixture(253)
    lookup(bundle, "stock", bundle["asof_session"])["close"] = 90.0
    ref = measurement(bundle)
    assert ref["at_new_high"] is False
    assert ref["log_gap_to_prior_high"] < 0.0


@pytest.mark.parametrize("count", [1, 20, 252])
def test_short_history_explicitly_unmeasured_not_low_rank(count):
    bundle = fixture(count)
    result = describe_rs_252_reference(bundle)
    assert_sealed(result)
    assert result["state"] == "UNAVAILABLE"
    assert result["reference"] == {
        "status": "unmeasured", "reason": "insufficient_completed_sessions"
    }


def test_missing_one_historical_stock_bar_invalidates_entire_reference():
    bundle = fixture(253)
    day = bundle["calendar"]["sessions"][17]
    bundle["rows"].remove(lookup(bundle, "stock", day))
    ref = measurement(bundle)
    assert ref["status"] == "unmeasured"
    assert ref["reason"] == "missing_or_future_known_daily_observation"


def test_future_known_historical_revision_cannot_change_original_reference():
    bundle = fixture(253)
    original = describe_rs_252_reference(bundle)
    day = bundle["calendar"]["sessions"][-2]
    row = copy.deepcopy(lookup(bundle, "stock", day))
    row.update({"revision_id": "late-rewrite", "close": 0.001,
                "known_at": iso(datetime.fromisoformat(bundle["asof_session"]).replace(
                    tzinfo=timezone.utc, hour=21))})
    bundle["rows"].append(row)
    assert describe_rs_252_reference(bundle) == original
    bundle["decision_at"] = row["known_at"]
    corrected = describe_rs_252_reference(bundle)
    assert corrected["visible_input_sha256"] != original["visible_input_sha256"]
    assert corrected["reference"]["input_sha256"] != original["reference"]["input_sha256"]


def test_unobserved_target_is_not_an_imputed_new_high():
    bundle = fixture(253)
    lookup(bundle, "stock", bundle["asof_session"])["known_at"] = "2029-01-01T00:00:00Z"
    result = describe_rs_252_reference(bundle)
    assert result["state"] == "UNAVAILABLE"
    assert result["reference"]["status"] == "unmeasured"


def test_source_input_permutation_has_identical_asof_reference_and_digest():
    bundle = fixture(253)
    original = describe_rs_252_reference(bundle)
    bundle["rows"].reverse()
    assert describe_rs_252_reference(bundle) == original


def test_wrong_daily_close_clock_refuses_not_known_at_predates_end():
    bundle = fixture(253)
    row = lookup(bundle, "stock", bundle["asof_session"])
    row["period_end"] = bundle["calendar"]["session_ends"][bundle["calendar"]["sessions"][-2]]
    with pytest.raises(InputContractError, match="period-end mismatches"):
        describe_rs_252_reference(bundle)


def test_mixed_adjustment_basis_never_claims_high():
    bundle = fixture(253)
    bundle["streams"]["benchmark"]["basis_kind"] = "unadjusted_close"
    result = describe_rs_252_reference(bundle)
    assert result["state"] == "UNAVAILABLE"
    assert "MIXED_RETURN_BASIS" in result["refusals"]


def test_nonfinite_nominal_ratio_is_handled_in_log_domain():
    bundle = fixture(253)
    target = bundle["asof_session"]
    lookup(bundle, "stock", target)["close"] = 1e308
    lookup(bundle, "benchmark", target)["close"] = 1e-308
    result = describe_rs_252_reference(bundle)
    ref = result["reference"]
    assert_sealed(result)
    assert ref["status"] == "measured"
    assert ref["at_new_high"] is True
    assert math.isfinite(ref["log_gap_to_prior_high"])


def test_new_reference_preserves_legacy_descriptor_bit_for_bit():
    bundle = fixture(253)
    original = describe_onset_features(bundle)
    result = describe_rs_252_reference(bundle)
    assert_sealed(result)
    assert describe_onset_features(bundle) == original


def test_unknown_market_kind_cannot_promote_authority():
    bundle = fixture(253)
    bundle["input_kind"] = "OBSERVED_MARKET"
    bundle["ranking_authority"] = True
    result = describe_rs_252_reference(bundle)
    assert result["evidence_status"] == "DESCRIPTOR_BUILT_NOT_ADMITTED"
    assert_sealed(result)


def test_calendar_knowledge_revision_changes_reference_identity_not_value():
    b = fixture(253)
    original = describe_rs_252_reference(b)
    b["calendar"]["known_at"] = "2026-05-29T00:00:00Z"
    updated = describe_rs_252_reference(b)
    assert updated["reference"]["at_new_high"] == original["reference"]["at_new_high"]
    assert updated["reference"]["log_gap_to_prior_high"] == original["reference"]["log_gap_to_prior_high"]
    assert updated["visible_input_sha256"] != original["visible_input_sha256"]
    assert updated["descriptor_sha256"] != original["descriptor_sha256"]


def test_older_outside_reference_revision_cannot_change_frozen_result():
    b = fixture(260)
    original = describe_rs_252_reference(b)
    old_day = b["calendar"]["sessions"][0]
    correction = copy.deepcopy(lookup(b, "stock", old_day))
    correction.update(
        close=0.001, revision_id="old-outside-window-correction",
        known_at=iso(datetime.fromisoformat(b["asof_session"]).replace(
            tzinfo=timezone.utc, hour=20, minute=3)),
    )
    b["rows"].append(correction)
    assert describe_rs_252_reference(b) == original


def test_future_calendar_session_and_source_row_are_not_part_of_prior_reference():
    b = fixture(253)
    original = describe_rs_252_reference(b)
    new_day = "2028-01-03"
    b["calendar"]["sessions"].append(new_day)
    b["calendar"]["session_ends"][new_day] = "2028-01-03T21:00:00Z"
    b["rows"].append({
        "stream": "stock", "session": new_day, "security_id": "SYNTH:security",
        "basis_id": "fixture-total-return", "revision_id": "futurerow",
        "period_end": "2028-01-03T21:00:00Z",
        "known_at": "2028-01-03T21:01:00Z", "close": 999999.0,
    })
    assert describe_rs_252_reference(b) == original
