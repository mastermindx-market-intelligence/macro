"""Explicit-evidence instrument resolution (I0).

Capital Structure Intelligence V2, masterplan task I0 (gates A04, A08, A09).
Input is the closed T0 candidate boundary (a C0 ``CandidateBundle``) plus owner
adjudication records (a C0 ``ResolutionInputs``).  Output is the C0
``InstrumentSet``.  No network, collector, LLM or clock is read: the result is a
pure function of its three arguments and the pinned E0 reference pack.

Identity law
------------
* An instrument exists only because an owner decision says so.  A
  ``supported_identity`` decision founds one series/tranche; an
  ``amendment_join`` decision supersedes named terms of that series with named
  later terms; a ``retirement`` decision retires it.  Candidate names, titles,
  strikes, amounts and repeated exhibit text never join anything (A08): the
  resolver does not read candidate values at all, and two byte-identical
  exhibits filed twice remain two unresolved candidates until a decision binds
  or supersedes them explicitly.
* ``instrument_id`` is ``stable_id("instrument", {issuer_id, series_key})`` --
  owner-assigned, clock-independent and immutable across re-observation,
  amendment, correction and retirement (A04).  Instruments cite *occurrence*
  identities (``logical_candidate_term_id``), so a later correction of a
  candidate term never re-mints the instrument.
* Only an adjudicated decision mints identity (A09).  A decision must carry the
  E0 fact origin ``adjudicated_gold`` and the reference pack must let it mint.
  LLM spans and interpretations, issuer assertions, model prose, unknown
  origins and even ``canonical_extraction`` (a parser reads terms; it does not
  adjudicate identity) are refused with an explicit reason and have no effect.
* Ambiguity is first-class.  A conflicting founding, a candidate claimed by two
  series, a repeated term left live twice, an unsupported supersession, a
  non-observed or not-yet-visible candidate -- each leaves the whole series
  unresolved with reasons; there is no partial or "best guess" identity.  An
  unresolved candidate is never emitted as an instrument and never carries a
  quantity: it is listed in ``InstrumentSet.unresolved_candidate_ids`` and its
  reasons are in :class:`ResolutionTrace`.
* Point in time.  A candidate is visible when its ``point_in_time.available_at``
  is at or before ``as_of`` (latest visible correction per occurrence).  A
  decision is visible when ``decided_at <= as_of`` and applies when its
  ``effective_at <= as_of`` too; a visible decision not yet effective is
  pending, never retroactive.

Every visible candidate ends in exactly one partition: bound to a resolved
instrument, superseded by an explicit amendment, or unresolved.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from engine.capital_structure.instrument_candidates import INSTRUMENT_CANDIDATE_TERM_SCHEMA, MAPPING_VERSION
from engine.capital_structure.issuer_state_contracts import (
    INSTRUMENT_KINDS,
    CalculationReceipt,
    CandidateBundle,
    ContractViolation,
    EvidenceRef,
    FamilyProvenance,
    Instrument,
    InstrumentSet,
    Provenance,
    Resolution,
    ResolutionInputs,
    sha256_of,
    stable_id,
)
from engine.capital_structure.reference_qualification import (
    CANONICAL_FACT_ORIGINS,
    NON_CANONICAL_FACT_ORIGINS,
    ReferencePack,
    load_reference_pack,
)
from engine.capital_structure.term_integration import assert_closed_candidate_term

__all__ = [
    "CANDIDATE_REASONS",
    "DECISION_METHODS",
    "IDENTITY_FACT_ORIGIN",
    "INSTRUMENT_RESOLUTION_VERSION",
    "REFUSAL_REASONS",
    "RESOLUTION_DECISION_SCHEMA",
    "RESOLUTION_TRACE_SCHEMA",
    "SERIES_REASONS",
    "DecisionRefusal",
    "ResolutionRefusal",
    "ResolutionTrace",
    "SeriesOutcome",
    "SupersededTerm",
    "UnresolvedCandidate",
    "build_decision",
    "decision_id_for",
    "instrument_id_for",
    "resolve_instrument_trace",
    "resolve_instruments",
]

INSTRUMENT_RESOLUTION_VERSION = "capital-structure-instrument-resolution/1.0.0"
RESOLUTION_DECISION_SCHEMA = "capital_structure.instrument_resolution_decision.v1"
RESOLUTION_TRACE_SCHEMA = "capital_structure.instrument_resolution_trace.v1"
CANDIDATE_FAMILY = "instrument_candidate_terms"

FOUNDING = "supported_identity"
AMENDMENT = "amendment_join"
RETIREMENT = "retirement"
DECISION_METHODS = (FOUNDING, AMENDMENT, RETIREMENT)

#: The only E0 fact origin that may mint an instrument identity.
IDENTITY_FACT_ORIGIN = "adjudicated_gold"

_DECISION_KEYS = frozenset({
    "schema",
    "decision_id",
    "method",
    "issuer_id",
    "series_key",
    "security_class_id",
    "kind",
    "candidate_term_ids",
    "supersedes",
    "evidence",
    "fact_origin",
    "decided_at",
    "effective_at",
})
_SUPERSESSION_KEYS = frozenset({"superseded", "by"})
_EVIDENCE_KEYS = frozenset({"manifest_id", "span_id", "text_sha256"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}$")

#: Why a visible decision had no effect at all (A09), closed.
REFUSAL_REASONS = (
    "fact_origin_not_canonical",
    "fact_origin_unknown",
    "identity_requires_adjudication",
)

#: Why a whole series stays unresolved, closed.
SERIES_REASONS = (
    "missing_founding_decision",
    "conflicting_identity_decisions",
    "inconsistent_series_identity",
    "conflicting_retirement_decisions",
    "amendment_after_retirement",
    "decision_precedes_founding",
    "candidate_not_visible",
    "candidate_not_observed",
    "candidate_claimed_by_multiple_series",
    "candidate_already_bound",
    "superseded_term_not_bound",
    "duplicate_current_term",
)

#: Why one visible candidate is unresolved, closed (plus any SERIES_REASONS of
#: the unresolved series that claimed it).
CANDIDATE_REASONS = (
    "no_identity_decision",
    "identity_decision_refused",
    "identity_decision_not_yet_effective",
    "candidate_not_observed",
    "series_unresolved",
)


class ResolutionRefusal(ValueError):
    """The inputs are malformed or cannot be resolved point-in-time; nothing is produced."""


# ---------------------------------------------------------------------------
# Trace records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionRefusal:
    """A visible decision that may not mint identity; it had no effect."""

    decision_id: str
    fact_origin: str
    reason: str

    def as_record(self) -> dict[str, Any]:
        return {"decision_id": self.decision_id, "fact_origin": self.fact_origin, "reason": self.reason}


@dataclass(frozen=True)
class SupersededTerm:
    """A candidate term an explicit amendment replaced inside one instrument."""

    logical_candidate_term_id: str
    candidate_term_id: str
    instrument_id: str
    superseded_by: str
    decision_id: str

    def as_record(self) -> dict[str, Any]:
        return {
            "logical_candidate_term_id": self.logical_candidate_term_id,
            "candidate_term_id": self.candidate_term_id,
            "instrument_id": self.instrument_id,
            "superseded_by": self.superseded_by,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class UnresolvedCandidate:
    """A visible candidate no admitted decision resolved, with its reasons."""

    logical_candidate_term_id: str
    candidate_term_id: str
    reasons: tuple[str, ...]
    decision_ids: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "logical_candidate_term_id": self.logical_candidate_term_id,
            "candidate_term_id": self.candidate_term_id,
            "reasons": list(self.reasons),
            "decision_ids": list(self.decision_ids),
        }


@dataclass(frozen=True)
class SeriesOutcome:
    """One owner series: resolved to an instrument, or unresolved with reasons."""

    series_key: str
    instrument_id: str
    resolved: bool
    reasons: tuple[str, ...]
    decision_ids: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "series_key": self.series_key,
            "instrument_id": self.instrument_id,
            "resolved": self.resolved,
            "reasons": list(self.reasons),
            "decision_ids": list(self.decision_ids),
        }


@dataclass(frozen=True)
class ResolutionTrace:
    """The ``InstrumentSet`` plus every reason behind it."""

    instrument_set: InstrumentSet
    decided_by: str
    series: tuple[SeriesOutcome, ...]
    unresolved: tuple[UnresolvedCandidate, ...]
    superseded: tuple[SupersededTerm, ...]
    refusals: tuple[DecisionRefusal, ...]
    pending_decision_ids: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": RESOLUTION_TRACE_SCHEMA,
            "version": INSTRUMENT_RESOLUTION_VERSION,
            "decided_by": self.decided_by,
            "instrument_set": self.instrument_set.as_record(),
            "series": [item.as_record() for item in self.series],
            "unresolved": [item.as_record() for item in self.unresolved],
            "superseded": [item.as_record() for item in self.superseded],
            "refusals": [item.as_record() for item in self.refusals],
            "pending_decision_ids": list(self.pending_decision_ids),
        }


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


def _instant(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ResolutionRefusal(f"{label}: timestamp string required")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ResolutionRefusal(f"{label}: {value!r} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ResolutionRefusal(f"{label}: {value!r} has no timezone")
    return parsed


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise ResolutionRefusal(f"{label}: identifier required, got {value!r}")
    return value


def decision_id_for(record: Mapping[str, Any]) -> str:
    """Content address of one decision: every field except ``decision_id`` itself."""
    return stable_id("instrument-decision", {key: value for key, value in record.items() if key != "decision_id"})


def instrument_id_for(issuer_id: str, series_key: str) -> str:
    """Immutable instrument identity: the issuer plus the owner-assigned series key, nothing else."""
    return stable_id("instrument", {"issuer_id": issuer_id, "series_key": series_key})


@dataclass(frozen=True)
class _Decision:
    decision_id: str
    method: str
    issuer_id: str
    series_key: str
    security_class_id: str
    kind: str
    candidate_term_ids: tuple[str, ...]
    supersedes: tuple[tuple[str, str], ...]
    evidence: tuple[EvidenceRef, ...]
    fact_origin: str
    decided_at: str
    effective_at: str
    decided: datetime
    effective: datetime

    @property
    def order(self) -> tuple[datetime, datetime, str]:
        return (self.effective, self.decided, self.decision_id)


def _parse_decision(record: Any) -> _Decision:
    if not isinstance(record, Mapping):
        raise ResolutionRefusal("decision: mapping required")
    label = f"decision[{record.get('decision_id')!r}]"
    keys = set(record)
    if keys != _DECISION_KEYS:
        raise ResolutionRefusal(
            f"{label}: keys must be exactly {sorted(_DECISION_KEYS)}; "
            f"missing {sorted(_DECISION_KEYS - keys)}, unexpected {sorted(keys - _DECISION_KEYS)}"
        )
    if record["schema"] != RESOLUTION_DECISION_SCHEMA:
        raise ResolutionRefusal(f"{label}: schema {record['schema']!r} is not {RESOLUTION_DECISION_SCHEMA!r}")
    decision_id = _identifier(record["decision_id"], f"{label}.decision_id")
    if decision_id != decision_id_for(record):
        raise ResolutionRefusal(f"{label}: decision_id is not the content address of the decision")
    method = record["method"]
    if method not in DECISION_METHODS:
        raise ResolutionRefusal(f"{label}: method {method!r} is not one of {list(DECISION_METHODS)}")
    kind = record["kind"]
    if kind not in INSTRUMENT_KINDS:
        raise ResolutionRefusal(f"{label}: kind {kind!r} is not an instrument kind")
    candidate_ids = record["candidate_term_ids"]
    if not isinstance(candidate_ids, (list, tuple)):
        raise ResolutionRefusal(f"{label}: candidate_term_ids must be a list")
    candidate_term_ids = tuple(_identifier(item, f"{label}.candidate_term_ids") for item in candidate_ids)
    if len(set(candidate_term_ids)) != len(candidate_term_ids):
        raise ResolutionRefusal(f"{label}: candidate_term_ids repeat")
    if method == RETIREMENT and candidate_term_ids:
        raise ResolutionRefusal(f"{label}: a retirement binds no candidate terms; its proof is its evidence")
    if method != RETIREMENT and not candidate_term_ids:
        raise ResolutionRefusal(f"{label}: a {method} decision names the candidate terms it binds")
    raw_supersedes = record["supersedes"]
    if not isinstance(raw_supersedes, (list, tuple)):
        raise ResolutionRefusal(f"{label}: supersedes must be a list")
    supersedes: list[tuple[str, str]] = []
    for item in raw_supersedes:
        if not isinstance(item, Mapping) or set(item) != _SUPERSESSION_KEYS:
            raise ResolutionRefusal(f"{label}: supersedes entries are exactly {sorted(_SUPERSESSION_KEYS)}")
        old = _identifier(item["superseded"], f"{label}.supersedes.superseded")
        new = _identifier(item["by"], f"{label}.supersedes.by")
        if new not in candidate_term_ids:
            raise ResolutionRefusal(f"{label}: a superseding term must be one of the decision's candidate terms")
        if old in candidate_term_ids:
            raise ResolutionRefusal(f"{label}: a term cannot supersede itself or be re-bound by its own amendment")
        supersedes.append((old, new))
    if supersedes and method != AMENDMENT:
        raise ResolutionRefusal(f"{label}: only an amendment_join supersedes terms")
    if len({old for old, _ in supersedes}) != len(supersedes):
        raise ResolutionRefusal(f"{label}: a term is superseded twice")
    raw_evidence = record["evidence"]
    if not isinstance(raw_evidence, (list, tuple)) or not raw_evidence:
        raise ResolutionRefusal(f"{label}: an identity decision carries at least one evidence reference")
    evidence: list[EvidenceRef] = []
    for item in raw_evidence:
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise ResolutionRefusal(f"{label}: evidence entries are exactly {sorted(_EVIDENCE_KEYS)}")
        try:
            evidence.append(EvidenceRef(item["manifest_id"], item["span_id"], item["text_sha256"]))
        except ContractViolation as exc:
            raise ResolutionRefusal(f"{label}: {exc}") from exc
    fact_origin = record["fact_origin"]
    if not isinstance(fact_origin, str):
        raise ResolutionRefusal(f"{label}: fact_origin must be a string")
    return _Decision(
        decision_id=decision_id,
        method=method,
        issuer_id=_identifier(record["issuer_id"], f"{label}.issuer_id"),
        series_key=_identifier(record["series_key"], f"{label}.series_key"),
        security_class_id=_identifier(record["security_class_id"], f"{label}.security_class_id"),
        kind=kind,
        candidate_term_ids=candidate_term_ids,
        supersedes=tuple(supersedes),
        evidence=tuple(evidence),
        fact_origin=fact_origin,
        decided_at=record["decided_at"],
        effective_at=record["effective_at"],
        decided=_instant(record["decided_at"], f"{label}.decided_at"),
        effective=_instant(record["effective_at"], f"{label}.effective_at"),
    )


def build_decision(
    *,
    method: str,
    issuer_id: str,
    series_key: str,
    security_class_id: str,
    kind: str,
    evidence: Sequence[EvidenceRef | Mapping[str, Any]],
    decided_at: str,
    candidate_term_ids: Sequence[str] = (),
    supersedes: Sequence[Mapping[str, str]] = (),
    fact_origin: str = IDENTITY_FACT_ORIGIN,
    effective_at: str | None = None,
) -> dict[str, Any]:
    """One well-formed decision record with its content-addressed ``decision_id``.

    Building a record grants nothing: the resolver still checks its fact origin,
    its series and every candidate it names.
    """
    record: dict[str, Any] = {
        "schema": RESOLUTION_DECISION_SCHEMA,
        "method": method,
        "issuer_id": issuer_id,
        "series_key": series_key,
        "security_class_id": security_class_id,
        "kind": kind,
        "candidate_term_ids": list(candidate_term_ids),
        "supersedes": [{"superseded": item["superseded"], "by": item["by"]} for item in supersedes],
        "evidence": [item.as_record() if isinstance(item, EvidenceRef) else dict(item) for item in evidence],
        "fact_origin": fact_origin,
        "decided_at": decided_at,
        "effective_at": effective_at if effective_at is not None else decided_at,
    }
    record["decision_id"] = decision_id_for(record)
    _parse_decision(record)
    return record


def _origin_refusal(origin: str, pack: ReferencePack) -> str | None:
    if origin == IDENTITY_FACT_ORIGIN and pack.fact_origins.get(origin) is True:
        return None
    if origin not in CANONICAL_FACT_ORIGINS | NON_CANONICAL_FACT_ORIGINS or origin not in pack.fact_origins:
        return "fact_origin_unknown"
    if origin in NON_CANONICAL_FACT_ORIGINS or pack.fact_origins.get(origin) is not True:
        return "fact_origin_not_canonical"
    return "identity_requires_adjudication"


def _assert_pack_law(pack: ReferencePack) -> None:
    for origin in CANONICAL_FACT_ORIGINS:
        if pack.fact_origins.get(origin) is not True:
            raise ResolutionRefusal(f"reference pack does not let canonical origin {origin!r} mint")
    for origin in NON_CANONICAL_FACT_ORIGINS:
        if pack.fact_origins.get(origin) is not False:
            raise ResolutionRefusal(f"reference pack lets non-canonical origin {origin!r} mint")


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Candidate:
    logical_id: str
    candidate_term_id: str
    issuer_id: str
    observed: bool
    slot: tuple[str, str, str]
    available_at: str
    available: datetime


def _visible_candidates(bundle: CandidateBundle, as_of: datetime) -> dict[str, _Candidate]:
    """The latest correction of each occurrence visible at ``as_of``; refuses an incomplete history."""
    versions: dict[str, dict[int, _Candidate]] = {}
    for row in bundle.candidate_terms:
        assert_closed_candidate_term(row)
        logical_id = _identifier(row.get("logical_candidate_term_id"), "candidate.logical_candidate_term_id")
        version = (row.get("version") or {}).get("correction_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ResolutionRefusal(f"{logical_id}: correction_version must be a positive integer")
        available_at = (row.get("point_in_time") or {}).get("available_at")
        security = row.get("security") or {}
        state = (row.get("candidate") or {}).get("state") or {}
        candidate = _Candidate(
            logical_id=logical_id,
            candidate_term_id=row["candidate_term_id"],
            issuer_id=_identifier(row.get("issuer_id"), f"{logical_id}.issuer_id"),
            observed=state.get("disposition") == "observed",
            slot=(
                str((row.get("term") or {}).get("name") or ""),
                str(security.get("title_normalized") or ""),
                str(security.get("classification") or ""),
            ),
            available_at=available_at,
            available=_instant(available_at, f"{logical_id}.point_in_time.available_at"),
        )
        slot = versions.setdefault(logical_id, {})
        if version in slot and slot[version].candidate_term_id != candidate.candidate_term_id:
            raise ResolutionRefusal(f"{logical_id}: two different records claim correction_version {version}")
        slot[version] = candidate
    visible: dict[str, _Candidate] = {}
    for logical_id, by_version in versions.items():
        seen = [version for version, item in by_version.items() if item.available <= as_of]
        if not seen:
            if min(by_version) > 1:
                raise ResolutionRefusal(
                    f"{logical_id}: the bundle lacks the version visible at as_of (earliest present is v{min(by_version)})"
                )
            continue
        latest = max(seen)
        if any(version > latest for version in by_version) and latest + 1 not in by_version:
            raise ResolutionRefusal(f"{logical_id}: correction history has a gap after v{latest}")
        visible[logical_id] = by_version[latest]
    return visible


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Series:
    outcome: SeriesOutcome
    instrument: Instrument | None
    superseded: tuple[SupersededTerm, ...]


def _resolve_series(
    issuer_id: str,
    series_key: str,
    decisions: Sequence[_Decision],
    candidates: Mapping[str, _Candidate],
    contested: set[str],
    binding_generation_id: str | None,
) -> _Series:
    instrument_id = instrument_id_for(issuer_id, series_key)
    ordered = sorted(decisions, key=lambda item: item.order)
    decision_ids = tuple(item.decision_id for item in ordered)
    foundings = [item for item in ordered if item.method == FOUNDING]
    amendments = [item for item in ordered if item.method == AMENDMENT]
    retirements = [item for item in ordered if item.method == RETIREMENT]
    reasons: set[str] = set()
    if not foundings:
        reasons.add("missing_founding_decision")
    elif len(foundings) > 1:
        reasons.add("conflicting_identity_decisions")
    if len({(item.security_class_id, item.kind) for item in ordered}) > 1:
        reasons.add("inconsistent_series_identity")
    if len(retirements) > 1:
        reasons.add("conflicting_retirement_decisions")
    if retirements and any(item.effective > retirements[0].effective for item in amendments):
        reasons.add("amendment_after_retirement")
    if len(foundings) == 1 and any(item.effective < foundings[0].effective for item in amendments + retirements):
        reasons.add("decision_precedes_founding")
    for item in ordered:
        for logical_id in item.candidate_term_ids:
            candidate = candidates.get(logical_id)
            if candidate is None:
                reasons.add("candidate_not_visible")
            elif not candidate.observed:
                reasons.add("candidate_not_observed")
            if logical_id in contested:
                reasons.add("candidate_claimed_by_multiple_series")

    bound: list[str] = []
    superseded: list[SupersededTerm] = []
    if not reasons:
        bound = list(foundings[0].candidate_term_ids)
        retired_ids: set[str] = set()
        for amendment in amendments:
            if any(logical_id in bound or logical_id in retired_ids for logical_id in amendment.candidate_term_ids):
                reasons.add("candidate_already_bound")
            if any(old not in bound for old, _ in amendment.supersedes):
                reasons.add("superseded_term_not_bound")
            if reasons:
                break
            olds = {old for old, _ in amendment.supersedes}
            bound = [logical_id for logical_id in bound if logical_id not in olds] + list(amendment.candidate_term_ids)
            retired_ids |= olds
            for old, new in amendment.supersedes:
                superseded.append(SupersededTerm(
                    logical_candidate_term_id=old,
                    candidate_term_id=candidates[old].candidate_term_id,
                    instrument_id=instrument_id,
                    superseded_by=new,
                    decision_id=amendment.decision_id,
                ))
    if not reasons:
        slots = [candidates[logical_id].slot for logical_id in bound]
        if len(set(slots)) != len(slots):
            reasons.add("duplicate_current_term")
    if reasons:
        outcome = SeriesOutcome(series_key, instrument_id, False, tuple(sorted(reasons)), decision_ids)
        return _Series(outcome, None, ())

    founding = foundings[0]
    if retirements:
        status, governing = "retired", retirements[0]
    elif amendments:
        status, governing = "amended", amendments[-1]
    else:
        status, governing = "outstanding", founding
    evidence: list[EvidenceRef] = []
    for item in ordered:
        for ref in item.evidence:
            if ref not in evidence:
                evidence.append(ref)
    instants = [(item.decided, item.decided_at) for item in ordered]
    instants += [(item.effective, item.effective_at) for item in ordered]
    instants += [(candidates[logical_id].available, candidates[logical_id].available_at) for logical_id in bound]
    knowable_at = max(instants)[1]
    try:
        instrument = Instrument(
            instrument_id=instrument_id,
            security_class_id=founding.security_class_id,
            kind=founding.kind,
            status=status,
            candidate_term_ids=tuple(bound),
            resolution=Resolution(governing.method, governing.decision_id, governing.evidence, governing.decided_at),
            amendments=tuple(item.decision_id for item in amendments),
            outstanding=None,
            provenance=Provenance(CANDIDATE_FAMILY, binding_generation_id, tuple(evidence), knowable_at),
        )
    except ContractViolation as exc:
        raise ResolutionRefusal(f"series {series_key!r}: {exc}") from exc
    outcome = SeriesOutcome(series_key, instrument_id, True, (), decision_ids)
    return _Series(outcome, instrument, tuple(superseded))


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def _rule_digest(pack: ReferencePack) -> str:
    return sha256_of({
        "instrument_resolution": INSTRUMENT_RESOLUTION_VERSION,
        "decision_schema": RESOLUTION_DECISION_SCHEMA,
        "decision_methods": list(DECISION_METHODS),
        "identity_fact_origin": IDENTITY_FACT_ORIGIN,
        "candidate_schema": INSTRUMENT_CANDIDATE_TERM_SCHEMA,
        "mapping_version": MAPPING_VERSION,
        "fact_origins": dict(pack.fact_origins),
    })


def _receipt_inputs(
    bundle: CandidateBundle, decisions: ResolutionInputs, parsed: Mapping[str, _Decision], as_of: str
) -> dict[str, Any]:
    """Order-independent receipt inputs: permuting rows or decisions cannot move the receipt."""
    records = {decision_id_for(record): record for record in decisions.decisions}
    return {
        "candidate_binding": bundle.as_record()["binding"],
        "candidate_as_of": bundle.as_of,
        "candidate_terms": sorted(bundle.as_record()["candidate_terms"], key=lambda row: row["candidate_term_id"]),
        "decisions": [records[decision_id] for decision_id in sorted(parsed)],
        "decided_by": decisions.decided_by,
        "decisions_as_of": decisions.as_of,
        "as_of": as_of,
    }


def resolve_instrument_trace(
    candidate_bundle: CandidateBundle,
    decisions: ResolutionInputs,
    as_of: str,
    *,
    reference_pack: ReferencePack | None = None,
) -> ResolutionTrace:
    """Resolve instruments at ``as_of`` and keep every reason (see module docstring)."""
    if not isinstance(candidate_bundle, CandidateBundle):
        raise ResolutionRefusal("candidate_bundle: CandidateBundle required")
    if not isinstance(decisions, ResolutionInputs):
        raise ResolutionRefusal("decisions: ResolutionInputs required")
    point = _instant(as_of, "as_of")
    if point > _instant(candidate_bundle.as_of, "candidate_bundle.as_of"):
        raise ResolutionRefusal("as_of is later than the candidate bundle: later candidates are not known")
    if point > _instant(decisions.as_of, "decisions.as_of"):
        raise ResolutionRefusal("as_of is later than the decision inputs: later decisions are not known")
    pack = reference_pack if reference_pack is not None else load_reference_pack()
    _assert_pack_law(pack)

    candidates = _visible_candidates(candidate_bundle, point)
    parsed: dict[str, _Decision] = {}
    for record in decisions.decisions:
        item = _parse_decision(record)
        parsed.setdefault(item.decision_id, item)
    visible_decisions = sorted((item for item in parsed.values() if item.decided <= point), key=lambda item: item.order)

    issuers = {item.issuer_id for item in candidates.values()} | {item.issuer_id for item in visible_decisions}
    if len(issuers) != 1:
        raise ResolutionRefusal(
            "one issuer per resolution required" if issuers else "no visible candidate or decision names the issuer"
        )
    issuer_id = issuers.pop()

    refusals: list[DecisionRefusal] = []
    pending: list[_Decision] = []
    admitted: list[_Decision] = []
    for item in visible_decisions:
        reason = _origin_refusal(item.fact_origin, pack)
        if reason is not None:
            refusals.append(DecisionRefusal(item.decision_id, item.fact_origin, reason))
        elif item.effective > point:
            pending.append(item)
        else:
            admitted.append(item)

    claims: dict[str, set[str]] = {}
    by_series: dict[str, list[_Decision]] = {}
    for item in admitted:
        by_series.setdefault(item.series_key, []).append(item)
        for logical_id in item.candidate_term_ids:
            claims.setdefault(logical_id, set()).add(item.series_key)
    contested = {logical_id for logical_id, keys in claims.items() if len(keys) > 1}

    binding = candidate_bundle.binding
    series = [
        _resolve_series(issuer_id, key, by_series[key], candidates, contested, binding.generation_id)
        for key in sorted(by_series)
    ]
    instruments = sorted((item.instrument for item in series if item.instrument is not None), key=lambda item: item.instrument_id)
    superseded = sorted((term for item in series for term in item.superseded), key=lambda item: item.logical_candidate_term_id)
    bound_ids = {logical_id for item in instruments for logical_id in item.candidate_term_ids}
    superseded_ids = {term.logical_candidate_term_id for term in superseded}
    if bound_ids & superseded_ids or not (bound_ids | superseded_ids) <= set(candidates):
        raise ResolutionRefusal("internal partition violated: bound, superseded and unresolved must be disjoint")

    series_reasons = {item.outcome.series_key: item.outcome.reasons for item in series if not item.outcome.resolved}
    referencing: dict[str, list[_Decision]] = {}
    for item in visible_decisions:
        for logical_id in item.candidate_term_ids:
            referencing.setdefault(logical_id, []).append(item)
    refused_ids = {item.decision_id for item in refusals}
    pending_ids = {item.decision_id for item in pending}
    unresolved: list[UnresolvedCandidate] = []
    for logical_id in sorted(candidates):
        if logical_id in bound_ids or logical_id in superseded_ids:
            continue
        candidate = candidates[logical_id]
        cited = referencing.get(logical_id, [])
        reasons: set[str] = set()
        if not candidate.observed:
            reasons.add("candidate_not_observed")
        admitted_series = [item.series_key for item in cited if item.decision_id not in refused_ids | pending_ids]
        for key in admitted_series:
            if key not in series_reasons:
                raise ResolutionRefusal(f"internal partition violated: {logical_id} is cited by resolved series {key!r}")
            reasons.add("series_unresolved")
            reasons.update(series_reasons[key])
        if not admitted_series:
            if any(item.decision_id in pending_ids for item in cited):
                reasons.add("identity_decision_not_yet_effective")
            elif any(item.decision_id in refused_ids for item in cited):
                reasons.add("identity_decision_refused")
            else:
                reasons.add("no_identity_decision")
        unresolved.append(UnresolvedCandidate(
            logical_candidate_term_id=logical_id,
            candidate_term_id=candidate.candidate_term_id,
            reasons=tuple(sorted(reasons)),
            decision_ids=tuple(sorted({item.decision_id for item in cited})),
        ))

    limits: list[str] = []
    if binding.support == "partial":
        limits.append("candidate input generation is bound as partial")
    if unresolved:
        limits.append(f"{len(unresolved)} candidate term(s) remain unresolved and are not instruments")
    if binding.support in ("supported", "partial"):
        support = "partial" if limits else "supported"
    else:
        support = binding.support
    try:
        provenance = FamilyProvenance(
            family="instruments",
            input_family=CANDIDATE_FAMILY,
            input_schema=binding.schema,
            support=support,
            compiler_version=INSTRUMENT_RESOLUTION_VERSION,
            generation_id=binding.generation_id,
            artifact_sha256=binding.artifact_sha256,
            support_limits=tuple(limits),
            as_of=as_of,
        )
        receipt = CalculationReceipt.build(
            inputs=_receipt_inputs(candidate_bundle, decisions, parsed, as_of),
            rule_digest=_rule_digest(pack),
            implementation=INSTRUMENT_RESOLUTION_VERSION,
            computed_at=as_of,
        )
        instrument_set = InstrumentSet(
            issuer_id=issuer_id,
            as_of=as_of,
            instruments=tuple(instruments),
            provenance=provenance,
            receipt=receipt,
            unresolved_candidate_ids=tuple(item.logical_candidate_term_id for item in unresolved),
        )
    except ContractViolation as exc:
        raise ResolutionRefusal(str(exc)) from exc
    return ResolutionTrace(
        instrument_set=instrument_set,
        decided_by=decisions.decided_by,
        series=tuple(item.outcome for item in series),
        unresolved=tuple(unresolved),
        superseded=tuple(superseded),
        refusals=tuple(refusals),
        pending_decision_ids=tuple(item.decision_id for item in pending),
    )


def resolve_instruments(candidate_bundle: CandidateBundle, decisions: ResolutionInputs, as_of: str) -> InstrumentSet:
    """Canonical supported series/tranche identity, amendments and retirement at ``as_of``.

    Interface owned by capital-structure-intelligence (C0 ``INTERFACE_OWNERSHIP``).
    Unresolved candidates are listed, never guessed; reasons are in
    :func:`resolve_instrument_trace`.
    """
    return resolve_instrument_trace(candidate_bundle, decisions, as_of).instrument_set
