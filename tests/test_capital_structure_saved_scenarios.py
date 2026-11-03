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


# ---------------------------------------------------------------------------
# Gates 13-14 — the store adapter (SPEC_U2 §1.3); the transport is faked
# ---------------------------------------------------------------------------

import io  # noqa: E402
import pathlib  # noqa: E402
import json as _json  # noqa: E402
import re as _re  # noqa: E402
import urllib.error as _urlerror  # noqa: E402

from engine.alert_delivery_drain import (  # noqa: E402
    READ_OK,
    READ_OK_ZERO,
    READ_UNAVAILABLE,
)
from engine.capital_structure import saved_scenario_store as store  # noqa: E402

SOURCE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "engine" / "capital_structure" / "saved_scenario_store.py"
)

_TABLE_ROW_FIELDS = (
    "saved_id",
    "user_id",
    "issuer_id",
    "record",
    "saved_at",
    "updated_at",
    "last_outcome",
    "last_outcome_generation_id",
)


def _row_for(saved: SavedScenario, *, user_id: str | None = None) -> dict[str, Any]:
    return {
        "saved_id": saved.saved_id,
        "user_id": user_id if user_id is not None else saved.user_id,
        "issuer_id": saved.issuer_id,
        "record": _json.dumps(saved.as_record(), sort_keys=True),
        "saved_at": saved.saved_at,
        "updated_at": saved.saved_at,
        "last_outcome": None,
        "last_outcome_generation_id": None,
    }


class _FakePostgREST:
    """A canned transport: records every (method, path) and answers by path."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, failure: str | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.rows = rows or []
        self.failure = failure

    def __call__(self, method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6) -> Any:
        self.calls.append((method, path))
        if self.failure == "http404":
            raise _urlerror.HTTPError(path, 404, "Not Found", {}, io.BytesIO(b"not found"))
        if self.failure == "pg42P01":
            raise _urlerror.HTTPError(
                path,
                400,
                "Bad Request",
                {},
                io.BytesIO(_json.dumps({"code": "42P01", "message": "relation does not exist"}).encode()),
            )
        if self.failure == "timeout":
            raise TimeoutError("timed out")
        return list(self.rows)


def test_u2_store_partition_is_enforced_by_the_module(
    composed: _Composed, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = _make_saved(composed)
    own_row = _row_for(saved)
    foreign_row = _row_for(_make_saved(composed, user_id=USER_BETA))
    fake = _FakePostgREST(rows=[own_row, foreign_row])
    monkeypatch.setattr(store, "_transport", fake)

    result = store.read_for_user(USER_ALPHA)
    assert result.state == READ_OK
    assert [row["saved_id"] for row in (result.rows or [])] == [saved.saved_id]
    assert all(row["user_id"] == USER_ALPHA for row in result.rows or [])
    assert result.error_class == "partition_violation"
    assert len(fake.calls) == 1, "no retry loop: one read, one transport call"
    for _method, path in fake.calls:
        assert "user_id=eq." in path

    # read_one is scoped to the owner too, and a foreign id is indistinguishable
    # from an absent one.
    fake_one = _FakePostgREST(rows=[own_row])
    monkeypatch.setattr(store, "_transport", fake_one)
    found = store.read_one(USER_ALPHA, saved.saved_id)
    assert found.state == READ_OK
    assert found.error_class is None
    assert "user_id=eq." in fake_one.calls[0][1]
    assert "saved_id=eq." in fake_one.calls[0][1]

    fake_absent = _FakePostgREST(rows=[own_row])
    monkeypatch.setattr(store, "_transport", fake_absent)
    zero = store.read_one(USER_BETA, saved.saved_id)
    assert zero.state == READ_OK_ZERO
    assert zero.rows == []

    # A foreign row on a single-row read is dropped as the same typed violation.
    fake_foreign = _FakePostgREST(rows=[foreign_row])
    monkeypatch.setattr(store, "_transport", fake_foreign)
    dropped = store.read_one(USER_ALPHA, saved.saved_id)
    assert dropped.state == READ_OK_ZERO
    assert dropped.error_class == "partition_violation"


@pytest.mark.parametrize("failure", ("http404", "pg42P01", "timeout"))
def test_u2_store_missing_table_is_typed_unavailable_without_fallback(
    composed: _Composed, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    saved = _make_saved(composed)
    fake = _FakePostgREST(failure=failure)
    monkeypatch.setattr(store, "_transport", fake)

    for read in (
        lambda: store.read_for_user(USER_ALPHA),
        lambda: store.read_one(USER_ALPHA, saved.saved_id),
        lambda: store.read_all_service_side(),
    ):
        result = read()
        assert result.state == READ_UNAVAILABLE, (failure, result)
        assert result.rows is None
    writes = [
        store.upsert(saved),
        store.delete(USER_ALPHA, saved.saved_id),
        store.write_outcome(saved.saved_id, "correction", saved.state_generation_id),
    ]
    for write in writes:
        assert write.state == "unavailable", (failure, write)
        assert isinstance(write.error_class, str) and write.error_class
    expected_calls = 6
    assert len(fake.calls) == expected_calls, "one call per operation, never a retry loop"

    # The module never grows a local fallback: no file/sqlite/cache write shape.
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert not _re.search(
        r"open\(|Path\(.*write|pickle|shelve|sqlite|lru_cache", source, _re.I
    ), "the store adapter persists nothing locally"
    for forbidden in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        assert source.count(forbidden) >= 1
    assert "print(" not in source, "the adapter never prints credentials or rows"
