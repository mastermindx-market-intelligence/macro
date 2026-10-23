"""The saved-scenario contract and the restore classifier (SPEC_U2 §1.2).

A saved scenario is the exact answer the evaluate route gave one entitled user
for one exact assumption set on one exact generation: the user's posted
``FinancingScenario`` record, the echoed view identity, both generation ids, the
result identity and the result's byte digest, and the rule-pack edition it was
composed under.  Saving the same answer twice is the same row by construction
(:attr:`SavedScenario.saved_id` digests user, issuer, scenario and view alone).

:func:`classify_restore` answers the W3 journey "come back to that exact answer
later and learn precisely why it moved" as a closed-vocabulary outcome.  A
correction, a new event, a source outage, an unavailable input family and a
saved body that no longer reconstructs are five DIFFERENT outcomes (A39); the
one thing that is never an outcome is a different result on the same
generations — that is a bug, raised as identity drift.

Deterministic and offline: no I/O, no HTTP, no wall clock, no float anywhere.
Every refusal is a :class:`ContractViolation`.  A saved scenario is context
about one published answer: no rank, sizing, entry, score, probability or
recommendation authority, and the user's label never enters any derived record.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, Mapping

from engine.capital_structure.issuer_state_contracts import (
    RECORD_SCHEMAS,
    STATE_CONTRACT_VERSION,
    VIEW_MODES,
    ActionSelection,
    ContractViolation,
    FinancingScenario,
    PriceAssumption,
    Quantity,
    UnknownResolution,
    stable_id,
)
from engine.capital_structure.scenario_inputs import ScenarioInputsUnavailable
from engine.capital_structure.state_changes import (
    StateChangeSet,
    changes_for_issuer,
)

SAVED_SCENARIO_SCHEMA = "capital_structure.saved_scenario.v1"

#: Closed restore vocabulary (A39: corrections, new events, no-change and
#: source outage differ).  An outcome that cannot be classified is never a
#: guessed member of this tuple.
RESTORE_OUTCOMES = (
    "no_change",
    "correction",
    "new_events",
    "source_outage",
    "inputs_unavailable",
    "scenario_rejected",
    "changed_unattributed",
)

#: The closed note sentences a restore outcome may carry, keyed by outcome
#: (three no-change sentences: same generations, a ledgered generation move
#: that did not touch this issuer, and a move no retained ledger spans).
RESTORE_NOTES: dict[str, str] = {
    "no_change": "no change: same state and inputs generations",
    "no_change_moved": "generation moved without change to this issuer",
    "no_change_unledgered": "the answer is unchanged; the change ledger does not span this generation move",
    "correction": "a correction changed this issuer's prior answer",
    "new_events": "new events were observed for this issuer",
    "source_outage": "no bindable state generation is served",
    "inputs_unavailable": "input families are unavailable for this issuer",
    "scenario_rejected": "the saved scenario does not reconstruct under the served contract version",
    "scenario_refused": "the served engine refuses the saved assumptions at the restore anchor",
    "changed_unattributed": "the answer changed and the change ledger does not attribute the cause",
}

_MAX_LABEL_CHARS = 120
_VIEW_KEYS = ("cutoff", "mode")


def result_digest_of(result: Mapping[str, Any]) -> str:
    """The exact byte identity of one result record (SPEC_U2 §1.2).

    Canonical-JSON text over sorted keys and no float anywhere in the record —
    two records differing only in key order carry the same digest, which is why
    identity is never computed from a numeric comparison.
    """
    return hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


#: The closed identity-key set a substance digest removes at EVERY depth.  The
#: top-level ``as_of`` is removed separately (one level deep only): nested
#: ``as_of`` values are data vintages and stay substance.
_SUBSTANCE_IDENTITY_KEYS = frozenset({"result_id", "scenario_id", "state_id", "receipt"})


def result_substance_digest_of(result: Mapping[str, Any]) -> str:
    """The answer's substance identity: canonical JSON with identity removed.

    ``result_id``, ``scenario_id``, ``state_id`` and ``receipt`` are identity at
    every depth (dicts nested in dicts and in lists); ``as_of`` is identity at
    the TOP level only, because a re-run at a served generation's as_of is the
    same answer re-anchored, while a nested vintage is a fact about the data.
    The input is never mutated.
    """
    def strip(node: Any, top: bool) -> Any:
        if isinstance(node, Mapping):
            stripped: dict[str, Any] = {}
            for key, value in node.items():
                name = str(key)
                if name in _SUBSTANCE_IDENTITY_KEYS or (top and name == "as_of"):
                    continue
                stripped[name] = strip(value, False)
            return stripped
        if isinstance(node, list):
            return [strip(item, False) for item in node]
        return node

    payload = json.dumps(
        strip(result, True), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def restore_anchor(saved: SavedScenario, served_as_of: str) -> FinancingScenario:
    """The assumption set one restore re-runs (DEC:CS-V2-U2-RESTORE-REBASES-AS-OF).

    A ``current`` or ``scenario`` anchor re-runs the SAVED assumptions at the
    served generation's as_of (S′): every other assumption, the horizon
    included, is kept verbatim, and S′.scenario_id is whatever the contract
    recomputes — never edited by hand.  A ``then_known`` anchor is returned
    unchanged: it re-runs at its own cutoff, and a mismatch stays a refusal
    downstream.  The saved body must reconstruct under the served contract
    version (:class:`ContractViolation` otherwise — the caller maps that to the
    rejected-restore answer, never to a guessed outcome).  Pure: no I/O, no
    clock, no globals.
    """
    scenario = financing_scenario_from_record(saved.scenario)
    if str(saved.view.get("mode") or "") == "then_known":
        return scenario
    return replace(scenario, as_of=served_as_of)


def _recommendation_words() -> tuple[str, ...]:
    """The recommendation vocabulary, by import from its only owner.

    The API module owns the frozen tuple; it is imported lazily (function
    level) so this engine module stays importable without the API's transport
    dependencies and no vocabulary is ever copied.
    """
    from app.capital_structure import _RECOMMENDATION_WORDS  # noqa: PLC0415 — lazy, single owner

    return tuple(_RECOMMENDATION_WORDS)


def financing_scenario_from_record(record: Mapping[str, Any]) -> FinancingScenario:
    """Rebuild the posted scenario through the contract constructors.

    The published form of a ``FinancingScenario`` carries its schema name and
    server-minted identity plus serialized nested records; a supported or
    partial answer restores EXACT assumptions, so the rebuilt record must equal
    the saved one byte for byte.
    """
    if not isinstance(record, Mapping):
        raise ContractViolation("saved_scenario.scenario: a financing scenario record is required")
    body = {key: value for key, value in record.items() if key not in ("schema", "scenario_id")}
    try:
        price = PriceAssumption(**dict(body.pop("price")))
        actions = tuple(
            ActionSelection(
                route_id=str(row["route_id"]),
                action=str(row["action"]),
                settlement=str(row["settlement"]),
                quantity=None if row.get("quantity") is None else Quantity(**dict(row["quantity"])),
                conditions_assumed_met=tuple(row.get("conditions_assumed_met") or ()),
            )
            for row in body.pop("actions") or ()
        )
        resolutions = tuple(
            UnknownResolution(
                unknown_id=str(row["unknown_id"]),
                assumed=Quantity(**dict(row["assumed"])),
                rationale=str(row["rationale"]),
            )
            for row in body.pop("unknown_resolutions") or ()
        )
        scenario = FinancingScenario(
            price=price,
            actions=actions,
            unknown_resolutions=resolutions,
            **body,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"saved_scenario.scenario: does not reconstruct ({exc})") from exc
    if "scenario_id" in record and scenario.scenario_id != record["scenario_id"]:
        raise ContractViolation("saved_scenario.scenario: scenario_id does not bind its assumptions")
    if record.get("schema") not in (None, RECORD_SCHEMAS["financing_scenario"]):
        raise ContractViolation("saved_scenario.scenario: schema is not the frozen financing scenario")
    if scenario.as_record() != _json_normal(record):
        raise ContractViolation("saved_scenario.scenario: the saved record does not round-trip byte-identically")
    return scenario


def _json_normal(value: Any) -> Any:
    """Tuples to lists so an in-memory record compares like parsed JSON."""
    if isinstance(value, Mapping):
        return {str(key): _json_normal(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_normal(item) for item in value]
    return value


@dataclass(frozen=True)
class SavedScenario:
    """One entitled user's saved exact answer, restorable against the served
    generation.

    ``saved_id`` digests user, issuer, scenario and view alone — the label is
    display text and never part of the identity, so re-saving the same answer
    under another label is the same row (an idempotent upsert).  ``last_outcome``
    is written only by the monitor; saving never sets it.
    """

    user_id: str
    issuer_id: str
    label: str
    view: Mapping[str, Any]
    scenario: Mapping[str, Any]
    state_generation_id: str
    inputs_generation_id: str
    result_id: str
    result_digest: str
    result_substance_digest: str
    rule_pack_digest: str
    saved_at: str
    contract_version: str = STATE_CONTRACT_VERSION
    last_outcome: str | None = None
    last_outcome_generation_id: str | None = None

    def __post_init__(self) -> None:
        _require(bool(self.user_id) and isinstance(self.user_id, str), "saved_scenario.user_id required")
        _require(bool(self.issuer_id) and isinstance(self.issuer_id, str), "saved_scenario.issuer_id required")
        _require(isinstance(self.label, str), "saved_scenario.label: text required")
        _require(len(self.label) <= _MAX_LABEL_CHARS, "saved_scenario.label: too long")
        lowered = self.label.lower()
        for word in _recommendation_words():
            _require(word.lower() not in lowered, f"saved_scenario.label: carries advisory vocabulary {word!r}")
        _require(isinstance(self.view, Mapping), "saved_scenario.view: mapping required")
        _require(sorted(str(key) for key in self.view) == sorted(_VIEW_KEYS), "saved_scenario.view: exactly mode and cutoff")
        _require(self.view["mode"] in VIEW_MODES, f"saved_scenario.view.mode: {self.view['mode']!r} is not a view mode")
        if self.view["cutoff"] is not None:
            _require(isinstance(self.view["cutoff"], str) and bool(self.view["cutoff"]),
                     "saved_scenario.view.cutoff: text or null required")
        financing_scenario_from_record(self.scenario)
        for name in (
            "state_generation_id",
            "inputs_generation_id",
            "result_id",
            "result_digest",
            "result_substance_digest",
            "rule_pack_digest",
            "saved_at",
        ):
            value = getattr(self, name)
            _require(isinstance(value, str) and bool(value), f"saved_scenario.{name} required")
        _require(
            self.contract_version == STATE_CONTRACT_VERSION,
            "saved_scenario.contract_version must be the served state contract version",
        )
        if self.last_outcome is not None:
            _require(self.last_outcome in RESTORE_OUTCOMES,
                     f"saved_scenario.last_outcome: {self.last_outcome!r} is not a restore outcome")
        if self.last_outcome_generation_id is not None:
            _require(isinstance(self.last_outcome_generation_id, str) and bool(self.last_outcome_generation_id),
                     "saved_scenario.last_outcome_generation_id must be text or null")

    @property
    def scenario_id(self) -> str:
        return str(self.scenario.get("scenario_id") or "")

    @property
    def saved_id(self) -> str:
        """``stable_id("saved_scenario", {user, issuer, scenario, view})`` —
        saving the same scenario twice is the same row."""
        return stable_id(
            "saved_scenario",
            {
                "user_id": self.user_id,
                "issuer_id": self.issuer_id,
                "scenario_id": self.scenario_id,
                "view": _json_normal(self.view),
            },
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": SAVED_SCENARIO_SCHEMA,
            "saved_id": self.saved_id,
            "user_id": self.user_id,
            "issuer_id": self.issuer_id,
            "label": self.label,
            "view": _json_normal(self.view),
            "scenario": _json_normal(self.scenario),
            "state_generation_id": self.state_generation_id,
            "inputs_generation_id": self.inputs_generation_id,
            "result_id": self.result_id,
            "result_digest": self.result_digest,
            "result_substance_digest": self.result_substance_digest,
            "rule_pack_digest": self.rule_pack_digest,
            "saved_at": self.saved_at,
            "contract_version": self.contract_version,
            "last_outcome": self.last_outcome,
            "last_outcome_generation_id": self.last_outcome_generation_id,
        }

    def public_record(self) -> dict[str, Any]:
        """The record a response may carry: no ``user_id``, ever (A40)."""
        record = self.as_record()
        record.pop("user_id")
        return record


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


@dataclass(frozen=True)
class RestoreOutcome:
    """One typed restore answer (A39): what changed, or precisely which outage
    or refusal stands in front of the saved answer.

    ``result_identical`` compares SUBSTANCE digests (identity keys removed), so
    a re-anchored re-run of the same assumptions stays the same answer; it is
    ``None`` exactly when no current result exists to compare.  ``from_as_of``
    is the saved scenario's as_of (always set); ``to_as_of``,
    ``scenario_id_after`` and ``result_id_after`` are the evaluated S′'s
    identity, and all three are null together or non-null together.
    """

    outcome: str
    from_generation_id: str | None
    to_generation_id: str | None
    from_inputs_generation_id: str | None
    to_inputs_generation_id: str | None
    from_as_of: str
    to_as_of: str | None
    result_id_before: str
    result_id_after: str | None
    scenario_id_before: str
    scenario_id_after: str | None
    result_identical: bool | None
    changes_n: int
    change_kinds: tuple[str, ...]
    unavailable_components: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        _require(self.outcome in RESTORE_OUTCOMES, f"restore.outcome: {self.outcome!r} is not a restore outcome")
        _require(isinstance(self.from_as_of, str) and bool(self.from_as_of), "restore.from_as_of required")
        _require(isinstance(self.result_id_before, str) and bool(self.result_id_before),
                 "restore.result_id_before required")
        _require(isinstance(self.scenario_id_before, str) and bool(self.scenario_id_before),
                 "restore.scenario_id_before required")
        after = (self.to_as_of, self.result_id_after, self.scenario_id_after)
        if any(entry is not None for entry in after) and not all(entry is not None for entry in after):
            raise ContractViolation("restore: to_as_of, result_id_after and scenario_id_after are null together")
        for entry in after:
            if entry is not None:
                _require(isinstance(entry, str) and bool(entry), "restore: the evaluated identity must be text or null")
        if self.result_identical is not None:
            _require(isinstance(self.result_identical, bool), "restore.result_identical must be boolean or null")
        _require(isinstance(self.changes_n, int) and self.changes_n >= 0, "restore.changes_n must be a count")
        object.__setattr__(self, "change_kinds", tuple(self.change_kinds))
        for kind in self.change_kinds:
            _require(isinstance(kind, str) and bool(kind), "restore.change_kinds: text required")
        object.__setattr__(self, "unavailable_components", tuple(self.unavailable_components))
        for component in self.unavailable_components:
            _require(isinstance(component, str) and bool(component), "restore.unavailable_components: text required")
        _require(self.note in set(RESTORE_NOTES.values()), f"restore.note: {self.note!r} is not a closed sentence")

    def as_record(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "from_generation_id": self.from_generation_id,
            "to_generation_id": self.to_generation_id,
            "from_inputs_generation_id": self.from_inputs_generation_id,
            "to_inputs_generation_id": self.to_inputs_generation_id,
            "from_as_of": self.from_as_of,
            "to_as_of": self.to_as_of,
            "result_id_before": self.result_id_before,
            "result_id_after": self.result_id_after,
            "scenario_id_before": self.scenario_id_before,
            "scenario_id_after": self.scenario_id_after,
            "result_identical": self.result_identical,
            "changes_n": self.changes_n,
            "change_kinds": list(self.change_kinds),
            "unavailable_components": list(self.unavailable_components),
            "note": self.note,
        }


def classify_restore(
    saved: SavedScenario,
    *,
    state_generation_id: str | None,
    inputs_generation_id: str | None,
    current_result: Mapping[str, Any] | None,
    unavailable: ScenarioInputsUnavailable | None,
    state_unavailable: bool,
    scenario_rejected: bool,
    changes: StateChangeSet | None,
    scenario_refused: bool = False,
    current_scenario_id: str | None = None,
    current_as_of: str | None = None,
) -> RestoreOutcome:
    """Classify one restore attempt in a closed precedence (SPEC_U2 §1.2).

    1. the saved body no longer reconstructs under the served contract version
       → ``scenario_rejected``; the served engine refusing the rebased anchor
       (``scenario_refused``) → the same outcome, with its own note;
    2. no bindable state generation → ``source_outage``;
    3. any input family unavailable → ``inputs_unavailable`` with its components;
    4. same state and inputs generations → ``no_change``, and a different
       identity on the same generations is NEVER an outcome: it is drift;
    5. a new event for this issuer on the spanning ledger → ``new_events``;
    6. a correction or withdrawal for this issuer, or a rule-pack edition
       change, on the spanning ledger → ``correction``;
    7. substance identical → ``no_change`` — ``no_change_moved`` when the
       spanning ledger is retained, ``no_change_unledgered`` when it is not;
    8. substance differs and nothing above attributed it →
       ``changed_unattributed``.

    The ledger counts ONLY when it spans exactly saved→served and is not a
    baseline; any other ledger classifies nothing and is treated as absent.
    """
    _require(isinstance(saved, SavedScenario), "classify_restore: a SavedScenario is required")
    if current_result is not None:
        _require(
            isinstance(current_scenario_id, str) and bool(current_scenario_id),
            "classify_restore: current_scenario_id is required with a current result",
        )
        _require(
            isinstance(current_as_of, str) and bool(current_as_of),
            "classify_restore: current_as_of is required with a current result",
        )
    spanning = (
        changes is not None
        and not changes.baseline
        and changes.from_generation_id == saved.state_generation_id
        and changes.to_generation_id == state_generation_id
    )
    ledger = changes if spanning else None
    issuer_changes = changes_for_issuer(ledger, saved.issuer_id)
    kinds = tuple(sorted({change.kind for change in issuer_changes}))
    same_state = state_generation_id is not None and state_generation_id == saved.state_generation_id
    same_inputs = inputs_generation_id is not None and inputs_generation_id == saved.inputs_generation_id
    from_as_of = str(saved.scenario.get("as_of") or "")
    _require(bool(from_as_of), "classify_restore: the saved scenario names no as_of")

    def identity(current: Mapping[str, Any]) -> tuple[str, bool]:
        result_id = str(current.get("result_id") or "")
        if not result_id:
            raise ContractViolation("classify_restore: the current result names no result_id")
        return result_id, result_substance_digest_of(current) == saved.result_substance_digest

    if scenario_rejected or scenario_refused:
        return RestoreOutcome(
            outcome="scenario_rejected",
            from_generation_id=saved.state_generation_id,
            to_generation_id=state_generation_id,
            from_inputs_generation_id=saved.inputs_generation_id,
            to_inputs_generation_id=inputs_generation_id,
            from_as_of=from_as_of,
            to_as_of=None,
            result_id_before=saved.result_id,
            result_id_after=None,
            scenario_id_before=saved.scenario_id,
            scenario_id_after=None,
            result_identical=None,
            changes_n=len(issuer_changes),
            change_kinds=kinds,
            unavailable_components=(),
            note=(
                RESTORE_NOTES["scenario_rejected"]
                if scenario_rejected
                else RESTORE_NOTES["scenario_refused"]
            ),
        )
    if state_unavailable:
        return RestoreOutcome(
            outcome="source_outage",
            from_generation_id=saved.state_generation_id,
            to_generation_id=state_generation_id,
            from_inputs_generation_id=saved.inputs_generation_id,
            to_inputs_generation_id=inputs_generation_id,
            from_as_of=from_as_of,
            to_as_of=None,
            result_id_before=saved.result_id,
            result_id_after=None,
            scenario_id_before=saved.scenario_id,
            scenario_id_after=None,
            result_identical=None,
            changes_n=len(issuer_changes),
            change_kinds=kinds,
            unavailable_components=(),
            note=RESTORE_NOTES["source_outage"],
        )
    if unavailable is not None:
        return RestoreOutcome(
            outcome="inputs_unavailable",
            from_generation_id=saved.state_generation_id,
            to_generation_id=state_generation_id,
            from_inputs_generation_id=saved.inputs_generation_id,
            to_inputs_generation_id=inputs_generation_id,
            from_as_of=from_as_of,
            to_as_of=None,
            result_id_before=saved.result_id,
            result_id_after=None,
            scenario_id_before=saved.scenario_id,
            scenario_id_after=None,
            result_identical=None,
            changes_n=len(issuer_changes),
            change_kinds=kinds,
            unavailable_components=tuple(sorted(unavailable.components)),
            note=RESTORE_NOTES["inputs_unavailable"],
        )
    if same_state and same_inputs:
        if current_result is None:
            raise ContractViolation("classify_restore: the same generations name no current result")
        result_id, identical = identity(current_result)
        if result_id != saved.result_id or not identical:
            raise ContractViolation("saved_scenario:identity_drift")
        return RestoreOutcome(
            outcome="no_change",
            from_generation_id=saved.state_generation_id,
            to_generation_id=state_generation_id,
            from_inputs_generation_id=saved.inputs_generation_id,
            to_inputs_generation_id=inputs_generation_id,
            from_as_of=from_as_of,
            to_as_of=current_as_of,
            result_id_before=saved.result_id,
            result_id_after=result_id,
            scenario_id_before=saved.scenario_id,
            scenario_id_after=current_scenario_id,
            result_identical=identical,
            changes_n=len(issuer_changes),
            change_kinds=kinds,
            unavailable_components=(),
            note=RESTORE_NOTES["no_change"],
        )
    if current_result is None:
        raise ContractViolation("classify_restore: a moved generation names no current result")
    result_id, identical = identity(current_result)
    if "new_event" in kinds:
        outcome, note = "new_events", RESTORE_NOTES["new_events"]
    elif (
        {"corrected_observation", "withdrawn_observation"} & set(kinds)
        or "rule_pack_changed" in kinds
    ):
        outcome, note = "correction", RESTORE_NOTES["correction"]
    elif identical:
        outcome = "no_change"
        note = (
            RESTORE_NOTES["no_change_moved"]
            if ledger is not None
            else RESTORE_NOTES["no_change_unledgered"]
        )
    else:
        outcome, note = "changed_unattributed", RESTORE_NOTES["changed_unattributed"]
    return RestoreOutcome(
        outcome=outcome,
        from_generation_id=saved.state_generation_id,
        to_generation_id=state_generation_id,
        from_inputs_generation_id=saved.inputs_generation_id,
        to_inputs_generation_id=inputs_generation_id,
        from_as_of=from_as_of,
        to_as_of=current_as_of,
        result_id_before=saved.result_id,
        result_id_after=result_id,
        scenario_id_before=saved.scenario_id,
        scenario_id_after=current_scenario_id,
        result_identical=identical,
        changes_n=len(issuer_changes),
        change_kinds=kinds,
        unavailable_components=(),
        note=note,
    )


__all__ = [
    "RESTORE_NOTES",
    "RESTORE_OUTCOMES",
    "SAVED_SCENARIO_SCHEMA",
    "RestoreOutcome",
    "SavedScenario",
    "classify_restore",
    "financing_scenario_from_record",
    "result_digest_of",
    "result_substance_digest_of",
    "restore_anchor",
]
