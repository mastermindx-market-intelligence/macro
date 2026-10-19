"""Adversarial metadata chains; these fixtures never activate a study."""
import copy
import pytest

from engine.research_factory import market_memory_e0_access_history as history
from engine.research_factory.market_memory_contextual_registration import E0ControlError
from tests.test_market_memory_e0_control_records import records, canonical, record_ref

NOW = "2026-10-14T01:00:00.000000Z"


def next_state(previous, **changes):
    state = copy.deepcopy(previous)
    state.update(sequence=previous["sequence"] + 1,
                 previous_state_ref=record_ref(previous, "access_state_id"),
                 recorded_at="2026-10-14T00:05:00.000000Z")
    state.update(changes)
    return state


def check(records, states, now=NOW):
    return history.validate_access_history(installation=records["installation"],
                                          history=[canonical(x) for x in states], as_of=now)


def test_reserved_to_consumed_preserves_look_and_has_no_grant(records):
    first = records["access"]
    second = next_state(first, budget={"maximum_looks": 3, "consumed_looks": 0, "reserved_looks": 1})
    third = next_state(second, budget={"maximum_looks": 3, "consumed_looks": 1, "reserved_looks": 0})
    result = check(records, [first, second, third])
    assert result["records"] == 3
    assert result["selected_state_ref"] == record_ref(third, "access_state_id")
    assert result["declared_budget"]["consumed_looks"] == 1
    assert result["metadata_consistent"] is True
    assert result["operational_admission"] is False
    assert result["current_selection_authenticated"] is False
    assert result["actual_reservation_accounting_verified"] is False
    assert "permitted_actions" not in result


@pytest.mark.parametrize("field,value,reason", [
    ("sequence", 2, "access_sequence_gap"),
    ("installation_epoch", "other-epoch", "access_installation_binding_mismatch"),
    ("study_id", "other-study", "access_installation_binding_mismatch"),
    ("recorded_at", "2026-10-14T00:03:30.000000Z", "access_clock_order"),
    ("recorded_at", "2026-10-14T02:00:00.000000Z", "access_clock_order"),
])
def test_chain_gaps_identity_and_clocks_refuse(records, field, value, reason):
    first = records["access"]
    second = next_state(first, **{field: value})
    with pytest.raises(history.E0AccessHistoryError, match=reason):
        check(records, [first, second])


def test_tampered_predecessor_and_scope_refuse(records):
    first = records["access"]
    second = next_state(first)
    second["previous_state_ref"]["sha256"] = "a" * 64
    with pytest.raises(history.E0AccessHistoryError, match="access_predecessor_mismatch"):
        check(records, [first, second])
    second = next_state(first)
    second["scope_ref"]["object_id"] = "expanded-scope"
    with pytest.raises(history.E0AccessHistoryError, match="access_epoch_binding_changed"):
        check(records, [first, second])


@pytest.mark.parametrize("terminal", ["revoked", "exhausted"])
def test_terminal_state_cannot_reactivate(records, terminal):
    first = records["access"]
    second = next_state(first, status=terminal)
    assert check(records, [first, second])["status"] == terminal
    third = next_state(second, status="active")
    with pytest.raises(history.E0AccessHistoryError, match="terminal_access_state_changed"):
        check(records, [first, second, third])


def test_contamination_sticky_even_if_later_record_claims_clean(records):
    first = records["access"]
    second = next_state(first, contamination_state="contaminated")
    third = next_state(second, contamination_state="clean")
    with pytest.raises(history.E0AccessHistoryError, match="contamination_state_reversed"):
        check(records, [first, second, third])


def test_exhausted_epoch_may_be_revoked_without_reactivation(records):
    first = records["access"]
    second = next_state(first, status="exhausted")
    third = next_state(second, status="revoked")
    assert check(records, [first, second, third])["status"] == "revoked"


@pytest.mark.parametrize("budget,reason", [
    ({"maximum_looks": 4, "consumed_looks": 0, "reserved_looks": 1}, "access_budget_limit_changed"),
    ({"maximum_looks": 3, "consumed_looks": 0, "reserved_looks": 0}, "access_look_refund"),
])
def test_budget_expansion_or_refund_refuses(records, budget, reason):
    first = records["access"]
    second = next_state(first, budget={"maximum_looks": 3, "consumed_looks": 0, "reserved_looks": 1})
    third = next_state(second, budget=budget)
    with pytest.raises(history.E0AccessHistoryError, match=reason):
        check(records, [first, second, third])


def test_consumed_to_reserved_is_not_permitted_even_with_same_total(records):
    first = records["access"]
    second = next_state(first, budget={"maximum_looks": 3, "consumed_looks": 1, "reserved_looks": 0})
    third = next_state(second, budget={"maximum_looks": 3, "consumed_looks": 0, "reserved_looks": 1})
    with pytest.raises(history.E0AccessHistoryError, match="access_look_refund"):
        check(records, [first, second, third])


@pytest.mark.parametrize("now", ["2026-10-13T00:00:00.000000Z", "2026-10-15T00:00:00.000000Z"])
def test_owner_clock_required_before_expiry(records, now):
    with pytest.raises(history.E0AccessHistoryError, match="installation_clock_or_expiry"):
        check(records, [records["access"]], now=now)


def test_initial_budget_and_supported_bound(records):
    first = records["access"]
    first["budget"]["reserved_looks"] = 1
    with pytest.raises(history.E0AccessHistoryError, match="initial_access_budget_not_empty"):
        check(records, [first])
    first["budget"].update(reserved_looks=0, maximum_looks=1025)
    with pytest.raises(history.E0AccessHistoryError, match="unsupported_owner_look_budget"):
        check(records, [first])


def test_exact_wire_count_and_total_byte_bounds(records, monkeypatch):
    body = canonical(records["access"])
    for values in ([], (), [body] * 1026, [bytearray(body)], [body + b"\n"]):
        with pytest.raises((history.E0AccessHistoryError, E0ControlError)):
            history.validate_access_history(installation=records["installation"], history=values, as_of=NOW)
    monkeypatch.setattr(history, "MAX_ACCESS_HISTORY_BYTES", len(body) - 1)
    with pytest.raises(history.E0AccessHistoryError, match="access_history_byte_limit"):
        check(records, [records["access"]])


def test_output_cannot_mutate_retained_input(records):
    result = check(records, [records["access"]])
    result["declared_budget"]["maximum_looks"] = 99
    assert records["access"]["budget"]["maximum_looks"] == 3
