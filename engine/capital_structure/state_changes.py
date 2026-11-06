"""The typed change desk between two published state generations (SPEC_U2 §1.1).

One published ``state_bundle.json`` generation is answered once; the change desk
answers the W3 journey "what changed since the answer I gave you, and why" as a
DERIVED artifact over two published generations — never a second compilation
path.  :func:`diff_state_generations` reads the two bundles the nightly already
published (plus the two capacity-inputs bundles when both are retained) and
returns one closed-vocabulary :class:`StateChangeSet`:

* observations are matched on a stable logical identity and compared by their
  correction version, so a new filing, a corrected observation and a withdrawn
  observation are three distinct, named kinds;
* a per-family support transition between the two inputs bundles is its own
  kind, so "this family was available and now is not" is stated, never averaged
  away;
* a rule-pack edition change and a moved horizon are issuer-less changes every
  issuer's desk must see.

This module is deterministic and offline: no I/O, no HTTP, no wall clock (the
caller stamps ``generated_at``), no float anywhere.  Every identity goes through
the frozen contract helpers (:func:`stable_id`); every refusal is a
:class:`ContractViolation`.  Authority is inherited unchanged: a change set is
context about published facts and carries no rank, sizing, entry, score,
probability or recommendation.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from engine.capital_structure.issuer_state_contracts import (
    STATE_CONTRACT_VERSION,
    ContractViolation,
    stable_id,
)
from engine.capital_structure.scenario_inputs import ISSUER_FAMILIES
from engine.capital_structure.state_bundle import (
    STATE_BUNDLE_SCHEMA,
    STATE_BUNDLE_SCHEMA_PATH,
)

STATE_CHANGES_SCHEMA = "capital_structure.state_changes.v1"
#: The published artifact this module's producer writes (SPEC_U2 §1.1).
STATE_CHANGES_FILENAME = "state_changes.json"

#: Closed change vocabulary.  Anything outside it is a :class:`ContractViolation`,
#: never a guessed member.
CHANGE_KINDS = (
    "new_event",
    "corrected_observation",
    "withdrawn_observation",
    "input_support_changed",
    "rule_pack_changed",
    "horizon_moved",
)
CHANGE_REASONS = (
    "new_accession",
    "correction_version_incremented",
    "observation_absent_in_current",
    "family_support_transition",
    "rule_pack_digest_changed",
    "source_observation_horizon_moved",
    "material_filing_horizon_moved",
)

#: The reason each named horizon carries when it moved (SPEC_U2 §1.1: one record
#: per horizon).
_HORIZON_REASONS = (
    ("source_observation_horizon", "source_observation_horizon_moved"),
    ("material_filing_horizon", "material_filing_horizon_moved"),
)

#: Every ``evidence`` key is present on every change; a kind with no document
#: carries ``None`` values rather than absent keys.
EVIDENCE_KEYS = (
    "accession",
    "form",
    "source_manifest_id",
    "available_at",
    "correction_version",
)

_SUBJECT_KEYS = ("event_id", "logical_observation_id", "family", "rule_pack_id", "horizon")

_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _plain(obj: Any) -> Any:
    """Recursive JSON-able form of a frozen record or plain value."""
    if hasattr(obj, "as_record"):
        return obj.as_record()
    if isinstance(obj, Mapping):
        return {str(key): _plain(item) for key, item in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(item) for item in obj]
    return obj


def _evidence(
    *,
    accession: Any = None,
    form: Any = None,
    source_manifest_id: Any = None,
    available_at: Any = None,
    correction_version: Any = None,
) -> dict[str, Any]:
    """The closed five-key evidence block; every key present, ``None`` when the
    kind has no document."""
    return {
        "accession": None if accession is None else str(accession),
        "form": None if form is None else str(form),
        "source_manifest_id": None if source_manifest_id is None else str(source_manifest_id),
        "available_at": None if available_at is None else str(available_at),
        "correction_version": None if correction_version is None else int(correction_version),
    }


@dataclass(frozen=True)
class StateChange:
    """One typed change between two published generations.

    ``change_id`` digests kind, issuer and subject, so the same logical change
    recomputed from the same pair of bundles is the same row, and the set is
    sortable by identity alone.  ``before``/``after`` carry the exact published
    records (or ``None``); nothing here re-derives a component answer.
    """

    kind: str
    reason: str
    issuer_id: str | None
    subject: Mapping[str, Any]
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None
    evidence: Mapping[str, Any]
    from_generation_id: str | None
    to_generation_id: str

    def __post_init__(self) -> None:
        _require(self.kind in CHANGE_KINDS, f"state_change.kind: {self.kind!r} is not a change kind")
        _require(self.reason in CHANGE_REASONS, f"state_change.reason: {self.reason!r} is not a change reason")
        if self.issuer_id is not None:
            _require(isinstance(self.issuer_id, str) and bool(self.issuer_id), "state_change.issuer_id required")
        _require(isinstance(self.subject, Mapping), "state_change.subject: mapping required")
        unexpected = sorted(str(key) for key in self.subject if str(key) not in _SUBJECT_KEYS)
        _require(not unexpected, f"state_change.subject: unexpected keys {unexpected}")
        _require(len(self.subject) >= 1, "state_change.subject: at least one key is required")
        for key in self.subject:
            _require(isinstance(self.subject[key], (str, int)) and self.subject[key] is not None,
                     f"state_change.subject[{key}]: non-null scalar required")
        for name in ("before", "after"):
            value = getattr(self, name)
            if value is not None:
                _require(isinstance(value, Mapping), f"state_change.{name}: mapping or null required")
        _require(isinstance(self.evidence, Mapping), "state_change.evidence: mapping required")
        _require(
            sorted(str(key) for key in self.evidence) == sorted(EVIDENCE_KEYS),
            "state_change.evidence: exactly the closed evidence keys are required",
        )
        _require(isinstance(self.to_generation_id, str) and bool(self.to_generation_id),
                 "state_change.to_generation_id required")
        if self.from_generation_id is not None:
            _require(isinstance(self.from_generation_id, str), "state_change.from_generation_id must be a string")

    @property
    def change_id(self) -> str:
        return stable_id(
            "state_change",
            {"kind": self.kind, "issuer_id": self.issuer_id, "subject": _plain(self.subject)},
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "kind": self.kind,
            "reason": self.reason,
            "issuer_id": self.issuer_id,
            "subject": _plain(self.subject),
            "before": _plain(self.before) if self.before is not None else None,
            "after": _plain(self.after) if self.after is not None else None,
            "evidence": _plain(self.evidence),
            "from_generation_id": self.from_generation_id,
            "to_generation_id": self.to_generation_id,
        }


@dataclass(frozen=True)
class StateChangeSet:
    """One derived change ledger between two published state generations.

    ``baseline=True`` names the first retained generation: there is no previous
    bundle, the change list is empty and that is stated rather than padded.
    """

    to_generation_id: str
    to_as_of: str
    changes: tuple[StateChange, ...]
    generated_at: str
    schema: str = STATE_CHANGES_SCHEMA
    contract_version: str = STATE_CONTRACT_VERSION
    from_generation_id: str | None = None
    from_as_of: str | None = None
    baseline: bool = False

    def __post_init__(self) -> None:
        _require(self.schema == STATE_CHANGES_SCHEMA, "state_changes.schema is frozen")
        _require(
            self.contract_version == STATE_CONTRACT_VERSION,
            "state_changes.contract_version must be the served state contract version",
        )
        _require(isinstance(self.to_generation_id, str) and bool(self.to_generation_id),
                 "state_changes.to_generation_id required")
        _require(isinstance(self.to_as_of, str) and bool(self.to_as_of), "state_changes.to_as_of required")
        _require(isinstance(self.generated_at, str) and bool(self.generated_at),
                 "state_changes.generated_at required")
        if self.baseline:
            _require(self.from_generation_id is None, "state_changes: a baseline names no from generation")
            _require(self.from_as_of is None, "state_changes: a baseline names no from as_of")
            _require(len(self.changes) == 0, "state_changes: a baseline carries no changes")
        else:
            _require(self.from_generation_id is not None, "state_changes.from_generation_id required")
        object.__setattr__(self, "changes", tuple(self.changes))
        for change in self.changes:
            _require(isinstance(change, StateChange), "state_changes.changes: StateChange required")
            _require(change.to_generation_id == self.to_generation_id,
                     "state_changes: a change binds another to_generation_id")
            _require(change.from_generation_id == self.from_generation_id,
                     "state_changes: a change binds another from_generation_id")
        ids = [change.change_id for change in self.changes]
        _require(ids == sorted(ids), "state_changes.changes: sorted by change_id required")
        _require(len(set(ids)) == len(ids), "state_changes.changes: duplicate change_id")
        counted = {kind: 0 for kind in CHANGE_KINDS}
        for change in self.changes:
            counted[change.kind] += 1
        _require(self.counts == counted, "state_changes.counts must count the actual changes")

    @property
    def counts(self) -> dict[str, int]:
        counted = {kind: 0 for kind in CHANGE_KINDS}
        for change in self.changes:
            counted[change.kind] += 1
        return counted

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract_version": self.contract_version,
            "from_generation_id": self.from_generation_id,
            "to_generation_id": self.to_generation_id,
            "from_as_of": self.from_as_of,
            "to_as_of": self.to_as_of,
            "baseline": self.baseline,
            "changes": [change.as_record() for change in self.changes],
            "counts": self.counts,
            "generated_at": self.generated_at,
        }


def changes_for_issuer(changeset: StateChangeSet | None, issuer_id: str) -> tuple[StateChange, ...]:
    """The issuer's own changes plus the issuer-less ones (rule pack, horizons).

    A horizon or rule-pack change binds no issuer, so it is included for every
    issuer's desk: it moved the answer for everybody, not for nobody.
    """
    if changeset is None:
        return ()
    _require(isinstance(issuer_id, str) and bool(issuer_id), "changes_for_issuer: issuer_id required")
    return tuple(
        change
        for change in changeset.changes
        if change.issuer_id is None or change.issuer_id == issuer_id
    )


# ---------------------------------------------------------------------------
# Published-bundle reading (the merged observation key)
# ---------------------------------------------------------------------------


def _validate_bundle_envelope(bundle: Any, label: str) -> None:
    """Require the bundle to pass the published state-bundle JSON schema.

    The schema layer is the published envelope contract (schema constants,
    generation identity, horizons, rule pack, per-issuer records with safe
    property names).  The publisher's own deeper gate — per-issuer contract
    re-construction — stays in ``state_bundle.validate_state_bundle``; the
    change desk consumes what the publisher published.
    """
    from jsonschema import Draft202012Validator, FormatChecker  # noqa: PLC0415 — lazy, like every reader

    if not isinstance(bundle, Mapping):
        raise ContractViolation(f"state_changes: {label} bundle must be an object")
    schema = json.loads(STATE_BUNDLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dict(bundle)),
        key=lambda error: list(error.path),
    )
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:10]
        ]
        raise ContractViolation(f"state_changes: {label} bundle fails the state-bundle schema: " + "; ".join(messages))


def _observations(bundle: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    """The merged observation key of a published bundle.

    The bundle carries no ``issuers[].events[]``: an observation is one published
    registration-path family record, keyed by its ``lifecycle_id`` — the stable
    logical registration identity across generations.  Its correction version is
    the newest ``correction_version`` exposed on the record's amendment chain
    (``1`` when the chain is empty) and its document is the path's ``origin``.
    """
    out: dict[str, dict[str, Mapping[str, Any]]] = {}
    for issuer_record in bundle.get("issuers") or ():
        request = issuer_record.get("request") or {}
        issuer_id = str(request.get("issuer_id") or "")
        if not issuer_id:
            continue
        for family in issuer_record.get("families") or ():
            for record in family.get("records") or ():
                if not isinstance(record, Mapping) or not record.get("lifecycle_id"):
                    continue
                logical = str(record["lifecycle_id"])
                chain = [item for item in record.get("amendment_chain") or () if isinstance(item, Mapping)]
                version = max((int(item.get("correction_version") or 1) for item in chain), default=1)
                origin = record.get("origin") if isinstance(record.get("origin"), Mapping) else {}
                out.setdefault(issuer_id, {})[logical] = {
                    "issuer_id": issuer_id,
                    "logical_observation_id": logical,
                    "correction_version": version,
                    "origin": origin,
                    "record": record,
                }
    return out


def _observation_evidence(observation: Mapping[str, Any], correction_version: int) -> dict[str, Any]:
    origin = observation.get("origin") or {}
    return _evidence(
        accession=origin.get("accession"),
        form=origin.get("form"),
        source_manifest_id=None,
        available_at=origin.get("mastermind_available_at"),
        correction_version=correction_version,
    )


def _observation_changes(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    from_generation_id: str | None,
    to_generation_id: str,
) -> list[StateChange]:
    changes: list[StateChange] = []
    before_all = {} if previous is None else _observations(previous)
    after_all = _observations(current)
    for issuer_id in sorted(set(before_all) | set(after_all)):
        before = before_all.get(issuer_id) or {}
        after = after_all.get(issuer_id) or {}
        for logical in sorted(set(before) - set(after)):
            changes.append(
                StateChange(
                    kind="withdrawn_observation",
                    reason="observation_absent_in_current",
                    issuer_id=issuer_id,
                    subject={"logical_observation_id": logical},
                    before=dict(before[logical]["record"]),
                    after=None,
                    evidence=_observation_evidence(before[logical], int(before[logical]["correction_version"])),
                    from_generation_id=from_generation_id,
                    to_generation_id=to_generation_id,
                )
            )
        for logical in sorted(set(after) - set(before)):
            changes.append(
                StateChange(
                    kind="new_event",
                    reason="new_accession",
                    issuer_id=issuer_id,
                    subject={"logical_observation_id": logical},
                    before=None,
                    after=dict(after[logical]["record"]),
                    evidence=_observation_evidence(after[logical], int(after[logical]["correction_version"])),
                    from_generation_id=from_generation_id,
                    to_generation_id=to_generation_id,
                )
            )
        for logical in sorted(set(before) & set(after)):
            before_version = int(before[logical]["correction_version"])
            after_version = int(after[logical]["correction_version"])
            if after_version > before_version:
                changes.append(
                    StateChange(
                        kind="corrected_observation",
                        reason="correction_version_incremented",
                        issuer_id=issuer_id,
                        subject={"logical_observation_id": logical},
                        before=dict(before[logical]["record"]),
                        after=dict(after[logical]["record"]),
                        evidence=_observation_evidence(after[logical], after_version),
                        from_generation_id=from_generation_id,
                        to_generation_id=to_generation_id,
                    )
                )
    return changes


def _support_changes(
    inputs_previous: Mapping[str, Any] | None,
    inputs_current: Mapping[str, Any] | None,
    *,
    from_generation_id: str | None,
    to_generation_id: str,
) -> list[StateChange]:
    if inputs_previous is None or inputs_current is None:
        return []
    changes: list[StateChange] = []
    before_issuers = inputs_previous.get("issuers") or {}
    after_issuers = inputs_current.get("issuers") or {}
    for issuer_id in sorted(set(before_issuers) & set(after_issuers)):
        before_entries = before_issuers[issuer_id] or {}
        after_entries = after_issuers[issuer_id] or {}
        for family in ISSUER_FAMILIES:
            before_row = before_entries.get(family) if isinstance(before_entries.get(family), Mapping) else None
            after_row = after_entries.get(family) if isinstance(after_entries.get(family), Mapping) else None
            if before_row is None or after_row is None:
                continue
            before_support = before_row.get("support")
            after_support = after_row.get("support")
            if before_support == after_support:
                continue
            changes.append(
                StateChange(
                    kind="input_support_changed",
                    reason="family_support_transition",
                    issuer_id=issuer_id,
                    subject={"family": family},
                    before={"support": str(before_support)},
                    after={"support": str(after_support)},
                    evidence=_evidence(),
                    from_generation_id=from_generation_id,
                    to_generation_id=to_generation_id,
                )
            )
    return changes


def _rule_pack_change(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    from_generation_id: str | None,
    to_generation_id: str,
) -> list[StateChange]:
    if previous is None:
        return []
    before_pack = previous.get("rule_pack") or {}
    after_pack = current.get("rule_pack") or {}
    if before_pack.get("rule_pack_digest") == after_pack.get("rule_pack_digest"):
        return []
    return [
        StateChange(
            kind="rule_pack_changed",
            reason="rule_pack_digest_changed",
            issuer_id=None,
            subject={"rule_pack_id": str(after_pack.get("rule_pack_id") or "")},
            before={"rule_pack_digest": str(before_pack.get("rule_pack_digest") or "")},
            after={"rule_pack_digest": str(after_pack.get("rule_pack_digest") or "")},
            evidence=_evidence(),
            from_generation_id=from_generation_id,
            to_generation_id=to_generation_id,
        )
    ]


def _horizon_changes(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    from_generation_id: str | None,
    to_generation_id: str,
) -> list[StateChange]:
    after_horizons = current.get("horizons") or {}
    if previous is None:
        return []
    before_horizons = previous.get("horizons") or {}
    changes: list[StateChange] = []
    for name, reason in _HORIZON_REASONS:
        before_value = before_horizons.get(name)
        after_value = after_horizons.get(name)
        if before_value == after_value:
            continue
        changes.append(
            StateChange(
                kind="horizon_moved",
                reason=reason,
                issuer_id=None,
                subject={"horizon": name},
                before={} if before_value is None else {name: str(before_value)},
                after={} if after_value is None else {name: str(after_value)},
                evidence=_evidence(),
                from_generation_id=from_generation_id,
                to_generation_id=to_generation_id,
            )
        )
    return changes


def diff_state_generations(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    inputs_previous: Mapping[str, Any] | None = None,
    inputs_current: Mapping[str, Any] | None = None,
    generated_at: str,
) -> StateChangeSet:
    """Derive one closed change set from two published state generations.

    Pure: the caller stamps ``generated_at``.  ``previous is None`` is the
    baseline generation.  Both bundles must pass the state-bundle schema and
    carry the same ``contract_version``, else
    :class:`ContractViolation` — a change set is never computed across contract
    versions, and an unclassifiable difference is never guessed into a kind.
    """
    _require(isinstance(generated_at, str) and bool(generated_at), "state_changes: generated_at required")
    _validate_bundle_envelope(current, "current")
    if previous is not None:
        _validate_bundle_envelope(previous, "previous")
        _require(
            previous.get("contract_version") == current.get("contract_version"),
            "state_changes:contract_version_mismatch",
        )

    from_generation_id = None if previous is None else str(previous.get("generation_id"))
    to_generation_id = str(current.get("generation_id"))
    if previous is None:
        # The baseline states the first retained generation; it never
        # synthesizes changes from a generation it cannot diff against.
        changes: list[StateChange] = []
    else:
        changes = [
            *_observation_changes(
                previous, current,
                from_generation_id=from_generation_id, to_generation_id=to_generation_id,
            ),
            *_support_changes(
                inputs_previous, inputs_current,
                from_generation_id=from_generation_id, to_generation_id=to_generation_id,
            ),
            *_rule_pack_change(
                previous, current,
                from_generation_id=from_generation_id, to_generation_id=to_generation_id,
            ),
            *_horizon_changes(
                previous, current,
                from_generation_id=from_generation_id, to_generation_id=to_generation_id,
            ),
        ]
    changes.sort(key=lambda change: change.change_id)
    return StateChangeSet(
        from_generation_id=from_generation_id,
        to_generation_id=to_generation_id,
        from_as_of=None if previous is None else str(previous.get("as_of")),
        to_as_of=str(current.get("as_of")),
        baseline=previous is None,
        changes=tuple(changes),
        generated_at=generated_at,
    )
