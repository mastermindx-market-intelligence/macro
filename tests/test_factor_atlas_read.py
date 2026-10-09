"""Session 1 native measurement contract; all inputs are explicit synthetic owner projections.

These tests do not grant source rights, attest live receipts, or modify any data store.
The product adapter must reuse Data OS identifiers, clocks and price-basis vocabulary.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import importlib
import importlib.util
import json

import pytest

from engine.price_ladder import PriceEvidence
from lib.dataos.identity import ListingKey, security_id
from lib.dataos.price import AdjustmentBasis, Session, VenueScope


IDS = [security_id(ListingKey("US", "XNYS", code)) for code in ("AAA", "BBB", "CCC", "DDD")]
SHA = "a" * 64


def case(dates=None, names=None):
    dates = dates or ["2026-01-28", "2026-01-29", "2026-01-30"]
    names = names or IDS[:3]
    sessions = [{"date": day, "close_at": day + "T21:00:00Z"} for day in dates]
    rebalances = [dates[0]] + [a for a, b in zip(dates, dates[1:]) if a[:7] != b[:7]]
    current = {
        "basket_id": "mag7", "members": list(names), "pit": False,
        "basis": "current_membership", "source_shape": "membership",
        "collection_state": "COMPLETE", "known_at": "2026-01-27T20:00:00Z",
        "snapshot_ref": "fixture:current-roster/v1", "source_sha256": SHA,
        "asof": dates[-1], "snapshot_date": "2026-01-27",
        "effective_from": "2026-01-27", "effective_to": None,
    }
    prices = {}
    for sid in IDS:
        evidence = asdict(PriceEvidence(
            ticker=sid.rsplit("-", 1)[-1], source="baskets_ohlcv",
            source_path="fixture:prices/" + sid, column="close",
            basis=AdjustmentBasis.TRADJ.value, receipt_state="EXACT_ENCODED_OBJECT",
            content_sha256=SHA, content_bytes=100,
            adjustment_asof="2026-02-11T22:00:00Z", session=Session.REGULAR.value,
            venue_scope=VenueScope.CONSOLIDATED.value, observed_at="2026-02-11T22:00:00Z",
        ))
        prices[sid] = {"evidence": evidence, "corporate_action_ref": "fixture:actions/v1",
                       "currency": "USD", "values": {day: 100.0 for day in dates}}
    inputs = {
        "evidence_kind": "SYNTHETIC_FIXTURE", "code_ref": "fixture:native-code/v1",
        "input_revision": "fixture:inputs/v1", "correction_of": None,
        "calendar": {"ref": "fixture:XNYS-calendar/v1", "sessions": sessions,
                     "rebalance_dates": rebalances},
        "current_roster": current,
        "pit_rosters": {day: {**deepcopy(current), "pit": True, "basis": "pit_snapshot",
                              "snapshot_ref": "fixture:pit/" + day, "asof": day} for day in rebalances},
        "decision_cutoffs": {day: day + "T20:59:00Z" for day in rebalances},
        "identity": {sid: {"owner_ref": "fixture:alias/" + sid,
                           "known_at": "2026-01-01T00:00:00Z",
                           "valid_from": "2026-01-01", "valid_to": None} for sid in IDS},
        "prices": prices,
        "rights": {"status": "QUALIFIED", "purpose": "internal_research",
                   "owner_ref": "fixture:rights/v1"},
    }
    request = {"basket_id": "mag7", "history_mode": "CURRENT_ROSTER", "start": dates[0],
               "end": dates[-1], "measurement_cutoff": "2026-02-12T00:00:00Z",
               "purpose": "internal_research", "weighting": "equal", "rebalance": "monthly"}
    return request, inputs


def run(request, inputs):
    assert importlib.util.find_spec("engine.factor_atlas_read") is not None, (
        "native factor read adapter is not implemented")
    return importlib.import_module("engine.factor_atlas_read").build_factor_read(
        request, owner_inputs=inputs)


def set_path(inputs, sid, values):
    for day, value in zip(inputs["prices"][sid]["values"], values, strict=True):
        inputs["prices"][sid]["values"][day] = value


def returns(result):
    return [point["return"] for point in result["points"]]


def test_monthly_drift_round_trip_is_not_daily_equal_reset():
    request, inputs = case()
    set_path(inputs, IDS[0], [100, 200, 100])
    result = run(request, inputs)
    assert returns(result) == pytest.approx([1 / 3, -1 / 4])
    assert result["points"][-1]["index_level"] == pytest.approx(100)
    assert result["method"]["between_rebalances"] == "drift"


def test_actual_month_boundary_resets_target_weights():
    request, inputs = case(["2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"])
    set_path(inputs, IDS[0], [100, 200, 200, 100])
    result = run(request, inputs)
    assert returns(result) == pytest.approx([1 / 3, 0, -1 / 6])
    assert result["points"][-1]["index_level"] == pytest.approx(100 * 10 / 9)


def test_current_roster_and_pit_return_different_results():
    request, inputs = case()
    set_path(inputs, IDS[0], [100, 110, 121])
    current = run(request, inputs)
    inputs["pit_rosters"][request["start"]]["members"] = IDS[1:]
    request["history_mode"] = "PIT_AS_KNOWN"
    pit = run(request, inputs)
    assert current["analytics"]["window_return"] == pytest.approx(0.07)
    assert pit["analytics"]["window_return"] == 0
    assert current["cohort_digest"] != pit["cohort_digest"]


@pytest.mark.parametrize("change,reason", [
    ({"pit": False}, "CURRENT_ROSTER_FALLBACK"),
    ({"collection_state": "PARTIAL"}, "COLLECTION_NOT_COMPLETE"),
    ({"known_at": None}, "MEMBERSHIP_CLOCK_UNAVAILABLE"),
    ({"known_at": "2026-01-28T21:01:00Z"}, "MEMBERSHIP_NOT_KNOWN_AT_DECISION"),
    ({"source_shape": "ths_concept_dump"}, "MEMBERSHIP_POPULATION_MISMATCH"),
    ({"source_sha256": None}, "MEMBERSHIP_RECEIPT_UNAVAILABLE"),
])
def test_strict_pit_refusals_do_not_fall_back(change, reason):
    request, inputs = case()
    request["history_mode"] = "PIT_AS_KNOWN"
    inputs["pit_rosters"][request["start"]].update(change)
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert reason in result["reasons"]


def test_current_roster_may_be_known_after_historical_selection_but_before_measurement():
    request, inputs = case()
    inputs["current_roster"]["known_at"] = "2026-02-11T20:00:00Z"
    assert returns(run(request, inputs)) == [0, 0]


def test_late_outcome_price_is_qualified_at_measurement_not_selection_cutoff():
    request, inputs = case()
    assert returns(run(request, inputs)) == [0, 0]
    inputs["prices"][IDS[0]]["evidence"]["observed_at"] = "2026-02-13T00:00:00Z"
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert "PRICE_NOT_KNOWN_AT_MEASUREMENT" in result["reasons"]


def test_future_identity_cannot_enter_pit_selection():
    request, inputs = case()
    request["history_mode"] = "PIT_AS_KNOWN"
    inputs["identity"][IDS[0]]["known_at"] = "2026-01-28T21:00:00Z"
    assert "IDENTITY_NOT_KNOWN_AT_DECISION" in run(request, inputs)["reasons"]


def test_missing_held_price_withholds_return_and_breaks_chain():
    request, inputs = case()
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = None
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert all(point["index_level"] is None for point in result["points"])
    assert result["points"][0]["coverage"]["weight"] == pytest.approx(2 / 3)
    assert result["points"][0]["breadth"]["advance_fraction"] is None
    assert result["analytics"]["window_return"] is None


def test_all_missing_is_not_zero_return():
    request, inputs = case()
    for sid in IDS[:3]:
        inputs["prices"][sid]["values"]["2026-01-29"] = None
    first = run(request, inputs)["points"][0]
    assert first["return"] is None
    assert first["coverage"]["weight"] == 0
    assert first["breadth"]["advance_fraction"] is None


def test_flat_is_observed_not_missing():
    request, inputs = case()
    first = run(request, inputs)["points"][0]
    assert first["return"] == 0
    assert first["breadth"]["advance_fraction"] == 0
    assert first["breadth"]["valid_count"] == 3
    assert first["concentration"]["hhi"] == pytest.approx(1 / 3)


def test_concentration_uses_drifted_end_weights_and_contributions_reconcile():
    request, inputs = case()
    set_path(inputs, IDS[0], [100, 200, 100])
    result = run(request, inputs)
    first = result["points"][0]
    assert first["concentration"]["hhi"] == pytest.approx(0.375)
    assert first["concentration"]["effective_n"] == pytest.approx(8 / 3)
    for point in result["points"]:
        assert sum(point["contributions"].values()) == pytest.approx(point["return"])


@pytest.mark.parametrize("field,value,reason", [
    ("basis", "raw", "PRICE_BASIS_UNQUALIFIED"),
    ("basis", "sadj", "PRICE_BASIS_UNQUALIFIED"),
    ("adjustment_asof", None, "ADJUSTMENT_VINTAGE_UNAVAILABLE"),
    ("session", None, "SESSION_UNAVAILABLE_OR_MISMATCHED"),
    ("venue_scope", None, "VENUE_UNAVAILABLE_OR_MISMATCHED"),
    ("content_sha256", None, "PRICE_RECEIPT_UNAVAILABLE"),
    ("receipt_state", "SOURCE_OBJECT_UNATTESTED", "PRICE_RECEIPT_UNAVAILABLE"),
])
def test_price_evidence_gate(field, value, reason):
    request, inputs = case()
    inputs["prices"][IDS[0]]["evidence"][field] = value
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert reason in result["reasons"]


def test_mixed_adjustment_vintages_are_not_spliced():
    request, inputs = case()
    inputs["prices"][IDS[0]]["evidence"]["adjustment_asof"] = "2026-02-10T22:00:00Z"
    assert "MIXED_ADJUSTMENT_VINTAGES" in run(request, inputs)["reasons"]


def test_corporate_action_basis_requires_owner_reference():
    request, inputs = case()
    inputs["prices"][IDS[0]]["corporate_action_ref"] = None
    assert "CORPORATE_ACTION_BASIS_UNAVAILABLE" in run(request, inputs)["reasons"]


def test_rights_are_not_inferred_from_a_price_hash():
    request, inputs = case()
    inputs["rights"]["status"] = "UNAVAILABLE"
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert "RIGHTS_UNAVAILABLE" in result["reasons"]


def test_no_duplicate_security_identity_or_silent_deduplication():
    request, inputs = case()
    inputs["current_roster"]["members"].append(IDS[0])
    with pytest.raises(ValueError, match="duplicate"):
        run(request, inputs)


def test_empty_complete_and_unknown_cohort_are_distinct():
    request, inputs = case()
    inputs["current_roster"]["members"] = []
    empty = run(request, inputs)
    assert "COHORT_EMPTY" in empty["reasons"]
    request["history_mode"] = "PIT_AS_KNOWN"
    inputs["pit_rosters"] = {}
    unknown = run(request, inputs)
    assert "PIT_COVERAGE_UNAVAILABLE" in unknown["reasons"]


@pytest.mark.parametrize("key,value", [
    ("weighting", "market_cap"), ("rebalance", "daily"),
    ("history_mode", "PIT_LATEST_CORRECTED"), ("purpose", "public_display"),
])
def test_unsupported_modes_are_explicit_not_fallback(key, value):
    request, inputs = case()
    request[key] = value
    with pytest.raises(ValueError, match="unsupported"):
        run(request, inputs)


def test_exactly_five_daily_returns_are_enough_for_five_session_result():
    request, inputs = case(["2026-02-03", "2026-02-04", "2026-02-05", "2026-02-06", "2026-02-09", "2026-02-10"])
    result = run(request, inputs)
    assert result["analytics"]["return_5"] == 0
    assert result["analytics"]["return_10"] is None


def test_calendar_does_not_silently_drop_a_missing_price_date():
    request, inputs = case()
    for sid in IDS[:3]:
        del inputs["prices"][sid]["values"]["2026-01-29"]
    result = run(request, inputs)
    assert [p["date"] for p in result["points"]] == ["2026-01-29", "2026-01-30"]
    assert returns(result) == [None, None]


def test_rebalance_decision_cannot_follow_its_execution_close():
    request, inputs = case()
    inputs["decision_cutoffs"][request["start"]] = "2026-01-28T21:01:00Z"
    with pytest.raises(ValueError, match="decision"):
        run(request, inputs)


def test_deterministic_permutation_and_input_immutability():
    request, inputs = case()
    before = deepcopy(inputs)
    first = run(request, inputs)
    assert inputs == before
    permuted = deepcopy(inputs)
    permuted["prices"] = dict(reversed(list(permuted["prices"].items())))
    permuted["current_roster"]["members"].reverse()
    second = run(request, permuted)
    assert first == second
    assert len(first["result_digest"]) == 64
    json.dumps(first, allow_nan=False)


def test_source_revision_changes_identity_even_when_numbers_are_equal():
    request, inputs = case()
    first = run(request, inputs)
    inputs["input_revision"] = "fixture:inputs/v2"
    inputs["correction_of"] = first["result_digest"]
    second = run(request, inputs)
    assert second["input_digest"] != first["input_digest"]
    assert second["result_digest"] != first["result_digest"]
    assert second["correction_of"] == first["result_digest"]
    assert returns(first) == returns(second)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_input_is_not_json(bad):
    request, inputs = case()
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = bad
    with pytest.raises(ValueError):
        run(request, inputs)


def test_candidate_does_not_claim_production_or_authority():
    request, inputs = case()
    result = run(request, inputs)
    assert result["release_state"] == "CANDIDATE_NOT_ADMITTED"
    assert result["evidence_kind"] == "SYNTHETIC_FIXTURE"
    assert not any(result["authority"].values())


@pytest.mark.parametrize("changes,reason", [
    ({"asof": "2026-01-29"}, "MEMBERSHIP_QUERY_MISMATCH"),
    ({"snapshot_date": "2026-01-29"}, "MEMBERSHIP_FUTURE_SNAPSHOT"),
    ({"effective_from": "2026-01-29"}, "MEMBERSHIP_NOT_EFFECTIVE"),
    ({"effective_to": "2026-01-28"}, "MEMBERSHIP_NOT_EFFECTIVE"),
    ({"asof": None}, "MEMBERSHIP_QUERY_MISMATCH"),
])
def test_pit_effective_time_and_exact_query_are_checked(changes, reason):
    request, inputs = case()
    request["history_mode"] = "PIT_AS_KNOWN"
    inputs["pit_rosters"][request["start"]].update(changes)
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert reason in result["reasons"]


def test_current_roster_effective_date_does_not_claim_historical_selection():
    request, inputs = case()
    inputs["current_roster"].update(effective_from="2026-01-30", snapshot_date="2026-01-30",
                                   known_at="2026-01-30T20:00:00Z")
    assert returns(run(request, inputs)) == [0, 0]


@pytest.mark.parametrize("changes", [
    {"valid_from": "2026-01-29"}, {"valid_to": "2026-01-28"},
    {"valid_from": "invalid"},
])
def test_native_identity_interval_is_half_open(changes):
    request, inputs = case()
    request["history_mode"] = "PIT_AS_KNOWN"
    inputs["identity"][IDS[0]].update(changes)
    result = run(request, inputs)
    assert returns(result) == [None, None]
    assert "IDENTITY_NOT_EFFECTIVE" in result["reasons"]


def test_missing_identity_interval_is_not_an_open_historical_grant():
    request, inputs = case()
    del inputs["identity"][IDS[0]]["valid_from"]
    assert "IDENTITY_INTERVAL_UNAVAILABLE" in run(request, inputs)["reasons"]


@pytest.mark.parametrize("path,value", [
    (("pit_rosters",), []), (("prices",), []), (("calendar",), []),
    (("current_roster", "members"), "AAA"), (("prices", IDS[0], "evidence"), []),
    (("prices", IDS[0], "values"), []), (("identity", IDS[0]), []),
    (("rights",), []),
])
def test_malformed_owner_shapes_are_typed_errors(path, value):
    request, inputs = case()
    target = inputs
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        run(request, inputs)


def test_extreme_positive_price_cannot_overflow_a_qualified_return():
    request, inputs = case()
    inputs["prices"][IDS[0]]["values"]["2026-01-28"] = 1e-300
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = 1e300
    result = run(request, inputs)
    assert result["points"][0]["return"] is None
    assert "NONFINITE_CONSTITUENT_RETURN" in result["reasons"]


def test_huge_integer_price_is_unavailable_not_an_uncaught_overflow():
    request, inputs = case()
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = 10 ** 400
    result = run(request, inputs)
    assert result["points"][0]["return"] is None
    assert "MISSING_OR_INVALID_HELD_PRICE" in result["reasons"]


def test_broken_full_history_never_reconnects_at_later_rebalance():
    request, inputs = case(["2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"])
    inputs["prices"][IDS[0]]["values"]["2026-01-29"] = None
    result = run(request, inputs)
    assert returns(result) == [None, 0, 0]
    assert [point["index_level"] for point in result["points"]] == [None, None, None]
    assert result["analytics"]["window_return"] is None
    assert result["analytics"]["return_1"] == 0


def test_pure_compute_does_not_open_files_or_network(monkeypatch):
    import builtins
    import socket
    module = importlib.import_module("engine.factor_atlas_read")
    request, inputs = case()
    def refused(*args, **kwargs):
        raise AssertionError("pure calculation attempted I/O")
    monkeypatch.setattr(builtins, "open", refused)
    monkeypatch.setattr(socket, "socket", refused)
    assert module.build_factor_read(request, owner_inputs=inputs)["status"] == "READY"


def test_request_start_on_weekend_is_not_an_invented_regular_session():
    request, inputs = case(["2026-01-24", "2026-01-26"])
    with pytest.raises(ValueError, match="calendar"):
        run(request, inputs)


def test_missing_calendar_session_cannot_compress_a_daily_return():
    request, inputs = case(["2026-01-28", "2026-01-30"])
    with pytest.raises(ValueError, match="calendar"):
        run(request, inputs)


def test_non_session_holiday_is_not_an_observed_zero_return():
    request, inputs = case(["2026-01-19", "2026-01-20"])
    with pytest.raises(ValueError, match="calendar"):
        run(request, inputs)


def test_incorrect_close_clock_is_not_canonicalized_into_success():
    request, inputs = case()
    inputs["calendar"]["sessions"][1]["close_at"] = "2026-01-29T20:00:00Z"
    with pytest.raises(ValueError, match="calendar"):
        run(request, inputs)


def test_identity_uses_each_decision_observation_not_one_old_alias():
    request, inputs = case(["2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"])
    request["history_mode"] = "PIT_AS_KNOWN"
    early, later = deepcopy(inputs["identity"]), deepcopy(inputs["identity"])
    early[IDS[0]]["valid_to"] = "2026-01-30"
    later[IDS[0]].update(valid_from="2026-01-30", known_at="2026-01-30T08:00:00Z")
    inputs["identity"] = early
    inputs["identity_by_date"] = {"2026-01-29": early, "2026-01-30": later}
    assert returns(run(request, inputs)) == [0, 0, 0]


def test_qualified_looking_identity_clock_still_has_no_source_authentication():
    request, inputs = case()
    result = run(request, inputs)
    assert result["input_admission"] == "REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION"
    assert result["source_refs"]["identity"][IDS[0]]["owner_ref"] == inputs["identity"][IDS[0]]["owner_ref"]
