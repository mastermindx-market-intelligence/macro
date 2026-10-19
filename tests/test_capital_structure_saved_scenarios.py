"""SPEC_U2 §2 gates 8-14: the saved-scenario contract, restore classifier and store.

The fixture is the U1B-2 evaluate lane's own, reused BY IMPORT: the scenario,
the inputs bundle and the composed result all come from
``tests.test_capital_structure_state_api`` helpers over the real U1a bundle
builder and S0's composer, so a saved scenario is always built from a result
the route actually owes — never a hand-written record.  The store gates inject
a fake PostgREST transport; no test opens a socket.

No digest, id or generation is hard-coded; no float literal anywhere.
"""
from __future__ import annotations

import json
from typing import Any, NamedTuple

import pytest

from engine.capital_structure.issuer_state_contracts import (
    ContractViolation,
    FinancingScenario,
    PriceAssumption,
    stable_id,
)
from engine.capital_structure.scenario_composition import compose_scenario
from engine.capital_structure.scenario_inputs import (
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
)
from engine.capital_structure.saved_scenarios import (
    RESTORE_NOTES,
    RESTORE_OUTCOMES,
    SavedScenario,
    classify_restore,
    financing_scenario_from_record,
    result_digest_of,
)
from engine.capital_structure.state_bundle import (
    state_from_record,
)
from engine.capital_structure.state_changes import StateChange, StateChangeSet
import tests.test_capital_structure_state_api as evaluate_suite
from tests.test_capital_structure_state_api import built  # noqa: F401 — requested as a fixture below
from tests.test_capital_structure_state_api import pack  # noqa: F401 — ``built`` resolves it by name here
from tests.test_capital_structure_state_bundle import _state_record

SAVED_AT = "2026-10-19T07:00:00Z"
CHANGES_GENERATED_AT = "2026-10-19T06:00:00Z"
USER_ALPHA = "user:alpha"
USER_BETA = "user:beta"

_EVIDENCE_EMPTY = {
    "accession": None,
    "form": None,
    "source_manifest_id": None,
    "available_at": None,
    "correction_version": None,
}


class _Composed(NamedTuple):
    """One composed evaluate answer plus the exact objects behind it."""

    envelope: dict[str, Any]
    scenario: FinancingScenario
    state_generation_id: str
    inputs_generation_id: str
    other_result: dict[str, Any]


@pytest.fixture(scope="module")
def composed(built: evaluate_suite._Built) -> _Composed:
    """The U1B-2 lane's own evaluate answer, composed once per module."""
    from engine.capital_structure.rule_applicability import load_rule_applicability_pack

    pack = load_rule_applicability_pack()
    scenario = evaluate_suite._test_scenario()
    inputs_record = evaluate_suite._inputs_bundle_record(built)
    state = state_from_record(_state_record(built.bundle, evaluate_suite.ISSUER_ONE))
    assembled = assemble_scenario_inputs(
        inputs_record,
        evaluate_suite.ISSUER_ONE,
        scenario.as_of,
        served_state_generation_id=built.bundle["generation_id"],
    )
    assert not isinstance(assembled, ScenarioInputsUnavailable)
    result = compose_scenario(
        state,
        assembled.instruments,
        assembled.basis,
        assembled.financials,
        assembled.commitments,
        scenario,
        assembled.rules,
        pack=pack,
    )
    # A second, different answer on the SAME generations (another price), for
    # the identity-drift gate.
    other_scenario = evaluate_suite._test_scenario(
        price=PriceAssumption("fixed", "USD", fixed_price="2.50")
    )
    other_result = compose_scenario(
        state,
        assembled.instruments,
        assembled.basis,
        assembled.financials,
        assembled.commitments,
        other_scenario,
        assembled.rules,
        pack=pack,
    )
    envelope = {
        "view": {
            "mode": "scenario",
            "as_of": scenario.as_of,
            "clock": "system",
            "state_id": state.state_id,
            "generation_id": built.bundle["generation_id"],
            "scenario_id": scenario.scenario_id,
        },
        "inputs_generation_id": inputs_record["generation_id"],
        "result": result.as_record(),
        "facts_unchanged": True,
        "scenario": scenario.as_record(),
    }
    return _Composed(
        envelope=envelope,
        scenario=scenario,
        state_generation_id=built.bundle["generation_id"],
        inputs_generation_id=inputs_record["generation_id"],
        other_result=other_result.as_record(),
    )


def _make_saved(composed: _Composed, **over: Any) -> SavedScenario:
    kwargs: dict[str, Any] = dict(
        user_id=USER_ALPHA,
        issuer_id=evaluate_suite.ISSUER_ONE,
        label="u2 saved fixture",
        view={"mode": "scenario", "cutoff": None},
        scenario=composed.envelope["scenario"],
        state_generation_id=composed.state_generation_id,
        inputs_generation_id=composed.inputs_generation_id,
        result_id=composed.envelope["result"]["result_id"],
        result_digest=result_digest_of(composed.envelope["result"]),
        rule_pack_digest=composed.envelope["result"]["capacity_envelope"]["rule_pack_digest"],
        saved_at=SAVED_AT,
    )
    kwargs.update(over)
    return SavedScenario(**kwargs)


def _check_saved(record: dict[str, Any], original: FinancingScenario) -> None:
    """The ONE shared helper every saved record in this file asserts through."""
    assert "user_id" not in record
    rebuilt = financing_scenario_from_record(record["scenario"])
    assert rebuilt.as_record() == record["scenario"]
    body = {
        key: value
        for key, value in record["scenario"].items()
        if key not in ("schema", "scenario_id")
    }
    body["price"] = PriceAssumption(**body["price"])
    assert FinancingScenario(**body) == original


def _moved_generation(name: str) -> str:
    """A derived, well-formed generation id distinct from every fixture one."""
    return stable_id("state_bundle", {"probe": name})


def _changeset(*changes: StateChange, from_generation_id: str, to_generation_id: str) -> StateChangeSet:
    return StateChangeSet(
        from_generation_id=from_generation_id,
        to_generation_id=to_generation_id,
        from_as_of="2026-10-14T00:00:00Z",
        to_as_of="2026-10-15T00:00:00Z",
        baseline=False,
        changes=changes,
        generated_at=CHANGES_GENERATED_AT,
    )


def _change(
    kind: str,
    reason: str,
    *,
    issuer_id: str | None,
    subject: dict[str, Any],
    from_generation_id: str,
    to_generation_id: str,
) -> StateChange:
    return StateChange(
        kind=kind,
        reason=reason,
        issuer_id=issuer_id,
        subject=subject,
        before=None,
        after=None,
        evidence=dict(_EVIDENCE_EMPTY),
        from_generation_id=from_generation_id,
        to_generation_id=to_generation_id,
    )


# ---------------------------------------------------------------------------
# Gate 8 — identity is idempotent over user, issuer, scenario and view
# ---------------------------------------------------------------------------


def test_u2_saved_scenario_id_is_idempotent_over_user_issuer_scenario_view(
    composed: _Composed,
) -> None:
    first = _make_saved(composed)
    again = _make_saved(composed)
    assert first.saved_id == again.saved_id
    assert first.saved_id.startswith("saved_scenario:cs:")

    relabelled = _make_saved(composed, label="u2 saved fixture, renamed")
    assert relabelled.saved_id == first.saved_id

    other_user = _make_saved(composed, user_id=USER_BETA)
    assert other_user.saved_id != first.saved_id

    other_view = _make_saved(composed, view={"mode": "scenario", "cutoff": "2026-10-14T00:00:00Z"})
    assert other_view.saved_id != first.saved_id

    other_price = evaluate_suite._test_scenario(
        price=PriceAssumption("fixed", "USD", fixed_price="3.00")
    )
    other_scenario = _make_saved(composed, scenario=other_price.as_record())
    assert other_scenario.saved_id != first.saved_id


# ---------------------------------------------------------------------------
# Gate 9 — the public record omits the user and reconstructs the scenario
# ---------------------------------------------------------------------------


def test_u2_saved_scenario_public_record_omits_user_id_and_reconstructs_scenario(
    composed: _Composed,
) -> None:
    saved = _make_saved(composed)
    record = saved.public_record()
    _check_saved(record, composed.scenario)
    full = saved.as_record()
    assert full["user_id"] == USER_ALPHA
    assert full["saved_id"] == record["saved_id"]
    assert record["label"] == "u2 saved fixture"
    assert record["view"] == {"mode": "scenario", "cutoff": None}
    assert record["last_outcome"] is None


# ---------------------------------------------------------------------------
# Gate 10 — the seven precedence rows
# ---------------------------------------------------------------------------


def _unavailable() -> ScenarioInputsUnavailable:
    return ScenarioInputsUnavailable(
        {
            "financials": {"support": "unavailable", "reason_codes": ["companyfacts_snapshot_unavailable"]},
            "share_basis": {"support": "unavailable", "reason_codes": ["share_observations_not_admitted"]},
        },
        ("commitments", "instruments", "rules"),
    )


@pytest.mark.parametrize(
    "row",
    (
        "scenario_rejected",
        "source_outage",
        "inputs_unavailable",
        "no_change_same_generations",
        "new_events",
        "correction",
        "no_change_generation_moved",
    ),
)
def test_u2_restore_precedence_rejected_outage_unavailable_then_generations(
    composed: _Composed, row: str
) -> None:
    saved = _make_saved(composed)
    moved_state = _moved_generation(row)
    moved_inputs = _moved_generation(row + "-inputs")

    if row == "scenario_rejected":
        outcome = classify_restore(
            saved,
            state_generation_id=moved_state,
            inputs_generation_id=moved_inputs,
            current_result=None,
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=True,
            changes=None,
        )
        assert outcome.outcome == "scenario_rejected"
        assert outcome.result_id_after is None and outcome.result_identical is None
    elif row == "source_outage":
        outcome = classify_restore(
            saved,
            state_generation_id=None,
            inputs_generation_id=None,
            current_result=None,
            unavailable=None,
            state_unavailable=True,
            scenario_rejected=False,
            changes=None,
        )
        assert outcome.outcome == "source_outage"
        assert outcome.to_generation_id is None
    elif row == "inputs_unavailable":
        outcome = classify_restore(
            saved,
            state_generation_id=moved_state,
            inputs_generation_id=moved_inputs,
            current_result=None,
            unavailable=_unavailable(),
            state_unavailable=False,
            scenario_rejected=False,
            changes=None,
        )
        assert outcome.outcome == "inputs_unavailable"
        assert outcome.unavailable_components == ("financials", "share_basis")
    elif row == "no_change_same_generations":
        outcome = classify_restore(
            saved,
            state_generation_id=saved.state_generation_id,
            inputs_generation_id=saved.inputs_generation_id,
            current_result=composed.envelope["result"],
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=False,
            changes=None,
        )
        assert outcome.outcome == "no_change"
        assert outcome.result_identical is True
        assert outcome.result_id_after == saved.result_id
        assert outcome.note == RESTORE_NOTES["no_change"]
    else:
        moved = _moved_generation("state-from")
        if row == "new_events":
            changes = _changeset(
                _change(
                    "new_event",
                    "new_accession",
                    issuer_id=evaluate_suite.ISSUER_ONE,
                    subject={"logical_observation_id": stable_id("lifecycle", {"probe": row})},
                    from_generation_id=moved,
                    to_generation_id=moved_state,
                ),
                from_generation_id=moved,
                to_generation_id=moved_state,
            )
        elif row == "correction":
            changes = _changeset(
                _change(
                    "corrected_observation",
                    "correction_version_incremented",
                    issuer_id=evaluate_suite.ISSUER_ONE,
                    subject={"logical_observation_id": stable_id("lifecycle", {"probe": row})},
                    from_generation_id=moved,
                    to_generation_id=moved_state,
                ),
                from_generation_id=moved,
                to_generation_id=moved_state,
            )
        else:
            changes = None
        outcome = classify_restore(
            saved,
            state_generation_id=moved_state,
            inputs_generation_id=moved_inputs,
            current_result=composed.envelope["result"],
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=False,
            changes=changes,
        )
        if row == "new_events":
            assert outcome.outcome == "new_events"
            assert outcome.change_kinds == ("new_event",)
        elif row == "correction":
            assert outcome.outcome == "correction"
            assert outcome.change_kinds == ("corrected_observation",)
        else:
            assert outcome.outcome == "no_change"
            assert outcome.note == RESTORE_NOTES["no_change_moved"]
            assert outcome.result_identical is True
            assert outcome.changes_n == 0
    assert outcome.outcome in RESTORE_OUTCOMES
    assert outcome.note in set(RESTORE_NOTES.values())
    assert outcome.from_generation_id == saved.state_generation_id
    assert outcome.result_id_before == saved.result_id


# ---------------------------------------------------------------------------
# Gate 11 — a different result on the same generations is identity drift
# ---------------------------------------------------------------------------


def test_u2_restore_same_generations_different_result_is_identity_drift(
    composed: _Composed,
) -> None:
    saved = _make_saved(composed)
    assert composed.other_result["result_id"] != saved.result_id
    with pytest.raises(ContractViolation) as raised:
        classify_restore(
            saved,
            state_generation_id=saved.state_generation_id,
            inputs_generation_id=saved.inputs_generation_id,
            current_result=composed.other_result,
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=False,
            changes=None,
        )
    assert "saved_scenario:identity_drift" in str(raised.value)


# ---------------------------------------------------------------------------
# Gate 12 — identity is the byte digest, never a numeric comparison
# ---------------------------------------------------------------------------


def _reverse_keys(value: Any) -> Any:
    """Rebuild every mapping with its keys in reverse insertion order."""
    if isinstance(value, dict):
        return {key: _reverse_keys(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [_reverse_keys(item) for item in value]
    return value


def test_u2_restore_result_identity_uses_digest_not_floats(composed: _Composed) -> None:
    saved = _make_saved(composed)
    reordered = _reverse_keys(composed.envelope["result"])
    # The wire bytes genuinely differ in key order; dict equality cannot see
    # that, the digest must not care.
    assert json.dumps(reordered, separators=(",", ":")) != json.dumps(
        composed.envelope["result"], separators=(",", ":")
    )
    assert result_digest_of(reordered) == saved.result_digest
    assert result_digest_of(composed.envelope["result"]) == saved.result_digest
    outcome = classify_restore(
        saved,
        state_generation_id=_moved_generation("digest"),
        inputs_generation_id=_moved_generation("digest-inputs"),
        current_result=reordered,
        unavailable=None,
        state_unavailable=False,
        scenario_rejected=False,
        changes=None,
    )
    assert outcome.result_identical is True
