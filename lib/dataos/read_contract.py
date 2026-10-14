"""Explicit read modes over the temporal model — decision D00.D1 (Data OS).

THE LAW (D00.D1, frozen): "A canonical read carries an explicit mode.  One
as_of switch never promises all three."  CURRENT = what the house holds now,
binding source receipts, identity generation id, action revision set id and
producing code version — never a historical claim.  RECONSTRUCT(cutoff, clock)
= what qualified information was available by cutoff, binding the clock used
(published_at = publisher availability, ingested_at = first system observation),
the known-by-cutoff filter on EVERY dependency, and the code version; labelled
"reconstruction", never "replay", and a DERIVED profile RAISES
``PointInTimeError`` instead of ever returning latest.  REPLAY(output_id) = what
the system actually emitted, binding the retained artifact's identity, its
exact-byte sha256 and publishing receipt; with no retained output ->
``NO_RETAINED_OUTPUT``, never a generated label.

temporal.py is UNTOUCHED here: ``as_of_filter`` stays a coalescing row filter
for its existing callers, while this module reads the REQUESTED clock column
directly through ``utc()`` (validated against ``KNOWN_AT_CLOCKS``) and never
delegates to ``known_at``, which coalesces published_at first and so cannot
express clock=ingested_at (V08).  Revision/generation eligibility is the
higher-level contract layered on top (ORCH-1 route proof G01), and every view
declares its D00.01 contract before any implementation result is seen.

STDLIB ONLY plus ``.temporal`` (thin CI lanes: pytest alone).  No wall clock
anywhere: a read without an explicit cutoff is refused, never defaulted.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType

from .temporal import (
    KNOWN_AT_CLOCKS, Clock, TemporalError, TemporalProfile, assert_pit_readable, utc,
)

__all__ = [
    "READ_CONTRACT_VERSION", "ReadMode", "RefusalCode", "ReadContractError",
    "ReadRefusal", "ViewContract", "ReadRequest", "GenerationRef", "Dependency",
    "CurrentEvidence", "RetainedOutput", "ReadResult", "eligible_rows",
    "resolve_revisions", "select_generation", "reconstruct", "current", "replay",
    "selected_input_sha256s",
]

READ_CONTRACT_VERSION = "mastermind.read_contract.v1"

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
_SHA1 = re.compile(r"\A[0-9a-f]{40}\Z")

#: What each knowledge clock SAYS about the reader's position: the publisher
#: had released it, the house had first observed it, or the house had served it.
_KNOWLEDGE_TERMS: dict[Clock, str] = {
    Clock.PUBLISHED_AT: "publisher_availability",
    Clock.INGESTED_AT: "system_observation",
    Clock.SERVED_AT: "served_output",
}

#: A dependency GENERATION binds on the two producer-controlled knowledge
#: clocks; every other named time says "when was this true", not "when known".
_GENERATION_CLOCKS = (Clock.PUBLISHED_AT, Clock.INGESTED_AT)


class ReadMode(StrEnum):
    """The three explicit read modes of D00.D1."""

    CURRENT = "CURRENT"
    RECONSTRUCT = "RECONSTRUCT"
    REPLAY = "REPLAY"


class RefusalCode(StrEnum):
    """Closed vocabulary of typed refusals; ``value == name``."""

    NO_VIEW_CONTRACT = "NO_VIEW_CONTRACT"
    UNKNOWN_CLOCK = "UNKNOWN_CLOCK"
    CLOCK_NOT_DECLARED = "CLOCK_NOT_DECLARED"
    MISSING_CLOCK_VALUE = "MISSING_CLOCK_VALUE"
    MISSING_REVISION_SEQ = "MISSING_REVISION_SEQ"
    AMBIGUOUS_REVISION = "AMBIGUOUS_REVISION"
    UNBOUND_DEPENDENCY = "UNBOUND_DEPENDENCY"
    STALE_GENERATION = "STALE_GENERATION"
    MISSING_CURRENT_EVIDENCE = "MISSING_CURRENT_EVIDENCE"
    NO_RETAINED_OUTPUT = "NO_RETAINED_OUTPUT"
    RETAINED_DIGEST_MISMATCH = "RETAINED_DIGEST_MISMATCH"
    KEY_TYPE_MISMATCH = "KEY_TYPE_MISMATCH"
    DUPLICATE_KEY = "DUPLICATE_KEY"


class ReadContractError(TemporalError):
    """A malformed request or contract OBJECT — not a data condition."""


class ReadRefusal(ReadContractError):
    """A lawful-shaped request the contract refuses; ``str()`` leads with the code."""

    def __init__(self, code: RefusalCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


def _require_str(value: object, what: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReadContractError(f"{what} must be a non-empty string, got {value!r}")


def _coerce_clock(clock: Clock | str | None) -> Clock:
    """A clock arrives as a ``Clock`` or its column name; nothing else is one."""
    if isinstance(clock, Clock):
        return clock
    if isinstance(clock, str):
        try:
            return Clock(clock)
        except ValueError:
            raise ReadRefusal(
                RefusalCode.UNKNOWN_CLOCK,
                f"{clock!r} is not one of the named times of the temporal vocabulary",
            ) from None
    raise ReadContractError(f"clock must be a Clock or its column name, got {clock!r}")


@dataclass(frozen=True, slots=True)
class ViewContract:
    """The D00.01 view contract — declared before any implementation result.

    ``identity`` must bind ``security_id`` and ``listing_id`` (a symbol is never
    an identity); mappings are copied into read-only proxies, because a contract
    editable after the fact is not one.
    """

    purpose: str
    identity: Mapping[str, str]
    field_units: Mapping[str, str]
    adjustment_reference: Mapping[str, str]
    coverage: str
    refusal_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_str(self.purpose, "purpose")
        _require_str(self.coverage, "coverage")
        for name in ("identity", "field_units", "adjustment_reference"):
            mapping = getattr(self, name)
            if not isinstance(mapping, Mapping):
                raise ReadContractError(
                    f"{name} must be a mapping, got {type(mapping).__name__}")
            object.__setattr__(self, name, MappingProxyType(dict(mapping)))
        for key in ("security_id", "listing_id"):
            value = self.identity.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ReadContractError(f"identity must declare a non-empty {key!r}")
        object.__setattr__(self, "refusal_reasons", tuple(self.refusal_reasons))


@dataclass(frozen=True, slots=True)
class ReadRequest:
    """One canonical read: explicit mode, complete mode parameters.

    Nothing is defaulted — there is NO default cutoff, because a silently-now()
    cutoff is how a "reconstruction" becomes a current read wearing a historical
    label.  Cutoff and clock normalize at construction so a malformed request
    dies at its author, not at read time.
    """

    mode: ReadMode
    contract: ViewContract | None
    cutoff: datetime | str | None = None
    clock: Clock | str | None = None
    output_id: str | None = None

    def __post_init__(self) -> None:
        if self.contract is None or not isinstance(self.contract, ViewContract):
            raise ReadRefusal(
                RefusalCode.NO_VIEW_CONTRACT,
                "a canonical read declares its view contract before any result exists")
        mode = self.mode
        if isinstance(mode, str):
            try:
                mode = ReadMode(mode)
            except ValueError:
                raise ReadContractError(f"unknown read mode {self.mode!r}") from None
        if not isinstance(mode, ReadMode):
            raise ReadContractError(f"read mode must be a ReadMode, got {self.mode!r}")
        object.__setattr__(self, "mode", mode)
        if mode is ReadMode.CURRENT:
            for name in ("cutoff", "clock", "output_id"):
                if getattr(self, name) is not None:
                    raise ReadContractError(
                        f"CURRENT takes no {name} — it is what the house holds now")
        elif mode is ReadMode.RECONSTRUCT:
            if self.output_id is not None:
                raise ReadContractError(
                    "RECONSTRUCT takes no output_id — that is REPLAY's parameter")
            if self.cutoff is None:
                raise TemporalError(
                    "RECONSTRUCT requires an explicit cutoff — there is no default now")
            object.__setattr__(self, "cutoff", utc(self.cutoff))
            object.__setattr__(self, "clock", _coerce_clock(self.clock))
        else:  # ReadMode.REPLAY
            if self.cutoff is not None or self.clock is not None:
                raise ReadContractError(
                    "REPLAY binds a retained output, not a cutoff or a clock")
            _require_str(self.output_id, "output_id")


@dataclass(frozen=True, slots=True)
class GenerationRef:
    """One atomic generation of a dependency's identity/metadata (D00.D1)."""

    generation_id: str
    published_at: datetime | str | None = None
    ingested_at: datetime | str | None = None
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class Dependency:
    """A named input to a read: its profile, its rows, its generation ledger."""

    name: str
    profile: TemporalProfile
    rows: Iterable[Mapping[str, object]] = ()
    key_fields: tuple[str, ...] = ()
    generations: tuple[GenerationRef, ...] = ()
    pinned_generation_id: str | None = None


def _validate_current_evidence(evidence: object) -> None:
    """CURRENT must bind WHERE the rows came from and WHICH code produced them."""
    if not isinstance(evidence, CurrentEvidence):
        raise ReadRefusal(
            RefusalCode.MISSING_CURRENT_EVIDENCE,
            "a CURRENT read binds CurrentEvidence — receipts, generation ids, code "
            "version")
    receipts = tuple(evidence.receipt_sha256s)
    if not receipts or not all(
        isinstance(receipt, str) and _HEX64.match(receipt) for receipt in receipts
    ):
        raise ReadRefusal(
            RefusalCode.MISSING_CURRENT_EVIDENCE,
            "receipt_sha256s must be a non-empty tuple of 64-char lowercase-hex receipts")
    for name in ("identity_generation_id", "action_revision_set_id"):
        value = getattr(evidence, name)
        if not isinstance(value, str) or not value.strip():
            raise ReadRefusal(RefusalCode.MISSING_CURRENT_EVIDENCE,
                              f"{name} must be a non-empty id")
    if not isinstance(evidence.code_version, str) or not _SHA1.match(evidence.code_version):
        raise ReadRefusal(
            RefusalCode.MISSING_CURRENT_EVIDENCE,
            "code_version must be a 40-char lowercase-hex producing code version")


@dataclass(frozen=True, slots=True)
class CurrentEvidence:
    """What a CURRENT read binds — validated at construction, before any rows."""

    receipt_sha256s: tuple[str, ...]
    identity_generation_id: str
    action_revision_set_id: str
    code_version: str

    def __post_init__(self) -> None:
        _validate_current_evidence(self)


@dataclass(frozen=True, slots=True)
class RetainedOutput:
    """A served artifact actually retained, with its exact-byte digest."""

    output_id: str
    payload: bytes | None
    sha256: str
    publishing_receipt_sha256: str | None


@dataclass(frozen=True, slots=True)
class ReadResult:
    """A contract-first result: evidence and values are read-only mappings."""

    mode: ReadMode
    label: str
    contract: ViewContract
    evidence: Mapping[str, object]
    values: Mapping[str, tuple[Mapping[str, object], ...]]
    payload: bytes | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))
        # Served rows are read-only too (R01 m7): a caller mutating one served row
        # would rewrite the very inputs the evidence just bound.
        object.__setattr__(
            self, "values",
            MappingProxyType({n: tuple(MappingProxyType(dict(row)) for row in rows)
                              for n, rows in self.values.items()}))


def _result(mode: ReadMode, label: str, contract: ViewContract, evidence: dict,
            values: Mapping[str, Iterable[Mapping[str, object]]],
            payload: bytes | None = None) -> ReadResult:
    return ReadResult(
        mode=mode, label=label, contract=contract, payload=payload,
        evidence={"read_contract_version": READ_CONTRACT_VERSION, "mode": mode.value,
                  **evidence},
        values=values)


def _declared_knowledge_clock(profile: TemporalProfile,
                              clock: Clock | str) -> Clock:
    """The ONE explicit knowledge clock, checked against the profile BEFORE rows.

    The clock must be one the profile declares (so period_end/event_at/
    effective_at/computed_at can never bound knowledge); checked before any row
    is touched, because a read that must refuse must refuse before it iterates.
    """
    knowledge_clock = _coerce_clock(clock)
    declared = KNOWN_AT_CLOCKS[profile]
    if knowledge_clock not in declared:
        names = ", ".join(clock_.value for clock_ in declared) or "none"
        raise ReadRefusal(
            RefusalCode.CLOCK_NOT_DECLARED,
            f"{getattr(profile, 'name', profile)} declares knowledge clocks [{names}] — "
            f"{knowledge_clock.value} can never bound what was known")
    return knowledge_clock


def eligible_rows(rows: Iterable[Mapping[str, object]], profile: TemporalProfile, *,
                  cutoff: datetime | str, clock: Clock | str) -> list[dict]:
    """Rows KNOWN by cutoff under ONE explicit clock — the V08 filter.

    Fail-closed order: PIT-readable profile before any row is touched; the clock
    must be one the profile declares (so period_end/event_at/effective_at/
    computed_at can never bound knowledge); a row missing the chosen column is
    a refusal, never a fallback that would silently switch the knowledge claim.
    """
    assert_pit_readable(profile)
    knowledge_clock = _declared_knowledge_clock(profile, clock)
    cutoff_at = utc(cutoff)
    eligible: list[dict] = []
    for row in rows:
        value = row.get(knowledge_clock.value)
        if value is None:
            raise ReadRefusal(
                RefusalCode.MISSING_CLOCK_VALUE,
                f"row carries no {knowledge_clock.value} — falling back to another clock "
                "would change the knowledge claim (V08), so it is refused")
        if utc(value) <= cutoff_at:
            eligible.append(dict(row))
    return eligible


def _key_part(value: object, field: str) -> tuple[str, object]:
    """One key field's canonical ``(kind, value)`` — R01 M2.

    One instant is ONE key however it is spelled: a tz-aware datetime, an
    offset-bearing ISO string and a ``Z``-suffixed string all canonicalize to the
    same UTC instant.  Nothing naive is guessed into an instant: a naive
    ``datetime`` makes ``utc()`` raise and that refusal propagates, while a
    string that is not an offset-bearing ISO instant stays an opaque ``str`` —
    so a key position mixing it with instants refuses ``KEY_TYPE_MISMATCH``.
    Kinds keep ``bool``/``int`` and ``datetime``/``date`` apart so one key
    position has one comparable type.
    """
    if value is None:
        raise ReadContractError(f"every row must carry key field {field!r}")
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, datetime):
        return ("instant", utc(value))
    if isinstance(value, date):
        return ("date", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value)
    if isinstance(value, str):
        try:
            return ("instant", utc(value))
        except TemporalError:
            return ("str", value)
    raise ReadRefusal(
        RefusalCode.KEY_TYPE_MISMATCH,
        f"key field {field!r} carries unsupported type {type(value).__name__}")


def _keyed_rows(rows: Iterable[Mapping[str, object]],
                keys: tuple[str, ...]) -> list[tuple[tuple, dict]]:
    """Canonical-key every row once, and refuse a key position of mixed kinds.

    Canonical keys first (M2), so the resolution that follows never depends on
    how an instant was spelled.  The kind seen at each key position is tracked
    over ALL rows; one position carrying two kinds could never sort (M1's
    ``TypeError`` path), so it is refused typed before any ordering is attempted.
    """
    keyed: list[tuple[tuple, dict]] = []
    kinds: list[set[str]] = [set() for _ in keys]
    for row in rows:
        if not isinstance(row, Mapping):
            raise ReadContractError(f"rows must be mappings, got {type(row).__name__}")
        key = []
        for position, field in enumerate(keys):
            kind, canonical = _key_part(row.get(field), field)
            kinds[position].add(kind)
            key.append(canonical)
        keyed.append((tuple(key), dict(row)))
    for position, field in enumerate(keys):
        if len(kinds[position]) > 1:
            raise ReadRefusal(
                RefusalCode.KEY_TYPE_MISMATCH,
                f"key field {field!r} mixes {sorted(kinds[position])} across rows - "
                "one key position has one type")
    return keyed


def resolve_revisions(rows: Iterable[Mapping[str, object]], *,
                      key_fields: tuple[str, ...]) -> list[dict]:
    """Per key, the single max-``revision_seq`` row — the V09/V10 resolution.

    The winner is returned WHATEVER its status: a max-revision row marked REFUSED
    is the answer, and a later eligible revision fully replaces the earlier one.
    Two different rows claiming one revision of a key is an ambiguity, not a tie
    to break silently; identical duplicates collapse.  The answer depends on the
    SET of rows, never on the order they were supplied in (R01 M1): the best
    sequence is found over ALL of a key's rows first, and only then are the rows
    at that sequence collected — so every permutation of the same supply picks
    the same winner or refuses the same way.
    """
    keys = tuple(key_fields)
    if not keys:
        raise ReadContractError("key_fields must name at least one key column")
    keyed = _keyed_rows(rows, keys)
    for key, row in keyed:
        seq = row.get("revision_seq")
        if isinstance(seq, bool) or not isinstance(seq, int):
            raise ReadRefusal(
                RefusalCode.MISSING_REVISION_SEQ,
                f"row {key!r} carries no int revision_seq (a bool is not a revision "
                "number); revision eligibility is this contract, not the row filter")
    best: dict[tuple, int] = {}
    for key, row in keyed:
        seq = row["revision_seq"]
        if key not in best or seq > best[key]:
            best[key] = seq
    winners: dict[tuple, list[dict]] = {}
    for key, row in keyed:
        if row["revision_seq"] == best[key] and row not in winners.setdefault(key, []):
            winners[key].append(row)
    for key in sorted(winners):
        if len(winners[key]) > 1:
            raise ReadRefusal(
                RefusalCode.AMBIGUOUS_REVISION,
                f"two different rows of key {key!r} both claim "
                f"revision_seq={best[key]}")
    return [winners[key][0] for key in sorted(winners)]


def _resolve_unique_keys(rows: Iterable[Mapping[str, object]], *,
                         key_fields: tuple[str, ...]) -> list[dict]:
    """Serve unique keys as supplied; two DIFFERENT rows of one key refuse (R01 M3).

    A dataset whose profile declares no revision ordering has nothing that ranks
    one row over another, so a second, different row of a key is a contradiction
    to refuse (``DUPLICATE_KEY``), never a silent pick.  Identical duplicates
    collapse; the kept rows come back in SUPPLY order — selection, not sorting.
    """
    keys = tuple(key_fields)
    if not keys:
        raise ReadContractError("key_fields must name at least one key column")
    keyed = _keyed_rows(rows, keys)
    first: dict[tuple, dict] = {}
    distinct: dict[tuple, list[dict]] = {}
    for key, row in keyed:
        if key not in first:
            first[key] = row
        bucket = distinct.setdefault(key, [])
        if row not in bucket:
            bucket.append(row)
    for key in sorted(distinct):
        if len(distinct[key]) > 1:
            raise ReadRefusal(
                RefusalCode.DUPLICATE_KEY,
                f"different rows share key {key!r} and the dataset declares no "
                "revision ordering - refusing to pick one")
    return list(first.values())


def _bind_rows(name: str, dependency: Dependency, supplied: tuple,
               eligible: list[dict],
               generation_id: str | None) -> tuple[tuple[dict, ...], str]:
    """The shared per-dependency binding: generation filter, then resolution.

    M4 (D00.D5.1, EXCLUDE): when the dependency declares generations, a
    generation is complete and immutable, so ONLY the rows of the selected
    generation are candidates — rows tagged with any other generation are
    excluded, not refused, and a row carrying no ``generation_id`` is never
    served under one.  Whether the rows are revision-ordered is decided on ALL
    supplied rows, so the label cannot flip with the cutoff (R01 M3).
    """
    filtered = eligible
    if dependency.generations:
        for row in eligible:
            if row.get("generation_id") is None:
                raise ReadRefusal(
                    RefusalCode.UNBOUND_DEPENDENCY,
                    f"dependency {name!r} declares generations but a row carries no "
                    "generation_id - a row bound to no generation is never served "
                    "under one (D00.D5.1)")
        filtered = [row for row in eligible
                    if row.get("generation_id") == generation_id]
    ordered = "revision_seq" in dependency.profile.required_fields or any(
        isinstance(row, Mapping) and "revision_seq" in row for row in supplied)
    if ordered:
        rows = resolve_revisions(filtered, key_fields=dependency.key_fields)
        resolution = "max_revision_seq_per_key"
    elif dependency.key_fields:
        rows = _resolve_unique_keys(filtered, key_fields=dependency.key_fields)
        resolution = "unique_key"
    else:
        rows = filtered
        resolution = "none"
    return tuple(rows), resolution


def select_generation(generations: Iterable[GenerationRef], *, cutoff: datetime | str,
                      clock: Clock | str,
                      pinned_generation_id: str | None = None) -> GenerationRef:
    """The dependency generation a RECONSTRUCT binds — per clock, per cutoff.

    Chooses the latest generation KNOWN by the cutoff under the requested clock
    (published_at or ingested_at only).  A generation that cannot state its
    chosen-clock instant is refused, not fallback-bound; none eligible leaves the
    dependency UNBOUND; a pinned id older than the newest eligible one is STALE.
    """
    knowledge_clock = _coerce_clock(clock)
    if knowledge_clock not in _GENERATION_CLOCKS:
        raise ReadRefusal(
            RefusalCode.CLOCK_NOT_DECLARED,
            f"generations bind on published_at/ingested_at only, not "
            f"{knowledge_clock.value}")
    cutoff_at = utc(cutoff)
    ledger = tuple(generations)
    eligible: list[tuple[datetime, GenerationRef]] = []
    for generation in ledger:
        value = getattr(generation, knowledge_clock.value)
        if value is None:
            raise ReadRefusal(
                RefusalCode.MISSING_CLOCK_VALUE,
                f"generation {generation.generation_id!r} carries no "
                f"{knowledge_clock.value} — no fallback to its other clock")
        known_at_instant = utc(value)
        if known_at_instant <= cutoff_at:
            eligible.append((known_at_instant, generation))
    if not eligible:
        raise ReadRefusal(
            RefusalCode.UNBOUND_DEPENDENCY,
            f"no generation of {len(ledger)} was known by {cutoff_at.isoformat()} "
            f"under {knowledge_clock.value}")
    newest = max(instant for instant, _ in eligible)
    chosen = [generation for instant, generation in eligible if instant == newest]
    if len({generation.generation_id for generation in chosen}) > 1:
        ids = ", ".join(sorted(generation.generation_id for generation in chosen))
        raise ReadRefusal(
            RefusalCode.AMBIGUOUS_REVISION,
            f"distinct generations tie on the newest {knowledge_clock.value}: {ids}")
    winner = chosen[0]
    if pinned_generation_id is not None:
        eligible_ids = {generation.generation_id for _, generation in eligible}
        if pinned_generation_id not in eligible_ids:
            raise ReadRefusal(
                RefusalCode.STALE_GENERATION,
                f"pinned generation {pinned_generation_id!r} is not eligible under "
                f"{knowledge_clock.value} by {cutoff_at.isoformat()}")
        if winner.generation_id != pinned_generation_id:
            raise ReadRefusal(
                RefusalCode.STALE_GENERATION,
                f"a newer generation ({winner.generation_id!r}) is eligible — a newer "
                f"generation is never returned under the older requested identity "
                f"{pinned_generation_id!r}")
    return winner


def _mode_request(request: object, mode: ReadMode, verb: str) -> ReadRequest:
    if not isinstance(request, ReadRequest) or request.mode is not mode:
        actual = getattr(request, "mode", request)
        raise ReadContractError(f"{verb}() serves {mode.value} requests, got {actual!r}")
    return request


def _dependency_map(dependencies: Mapping[str, object]) -> None:
    for name, dependency in dependencies.items():
        if not isinstance(dependency, Dependency):
            raise ReadContractError(f"dependency {name!r} is not a Dependency")


def reconstruct(request: ReadRequest, dependencies: Mapping[str, Dependency], *,
                required: Collection[str], code_version: str) -> ReadResult:
    """What qualified information was available by cutoff — labelled
    "reconstruction", never "replay".

    Order is law: mode checked; every REQUIRED dependency bound before any row
    is iterated; each profile PIT-readable before ITS rows are touched; then per
    dependency — explicit-clock eligibility, max-revision resolution when
    revisable, generation binding when a ledger exists.  Every binding lands in
    the evidence, declared before the values are read.
    """
    _mode_request(request, ReadMode.RECONSTRUCT, "reconstruct")
    missing = sorted(name for name in required if name not in dependencies)
    if missing:
        raise ReadRefusal(
            RefusalCode.UNBOUND_DEPENDENCY,
            f"required dependencies are unbound (not supplied): {', '.join(missing)}")
    cutoff_at = utc(request.cutoff)
    knowledge_clock = _coerce_clock(request.clock)
    values: dict[str, tuple[dict, ...]] = {}
    generation_ids: dict[str, str | None] = {}
    revision_resolutions: dict[str, str] = {}
    for name, dependency in dependencies.items():
        if not isinstance(dependency, Dependency):
            raise ReadContractError(f"dependency {name!r} is not a Dependency")
        # Fail closed on the profile AND its clock BEFORE any of this
        # dependency's rows — then materialize once (rows may be one-shot).
        assert_pit_readable(dependency.profile)
        _declared_knowledge_clock(dependency.profile, knowledge_clock)
        supplied = tuple(dependency.rows)
        eligible = eligible_rows(
            supplied, dependency.profile, cutoff=cutoff_at, clock=knowledge_clock)
        generation_id: str | None = None
        if dependency.generations:
            generation_id = select_generation(
                dependency.generations, cutoff=cutoff_at, clock=knowledge_clock,
                pinned_generation_id=dependency.pinned_generation_id).generation_id
        elif dependency.pinned_generation_id is not None:
            raise ReadRefusal(
                RefusalCode.UNBOUND_DEPENDENCY,
                f"dependency {name!r} pins generation "
                f"{dependency.pinned_generation_id!r} but declares no generations")
        values[name], revision_resolutions[name] = _bind_rows(
            name, dependency, supplied, eligible, generation_id)
        generation_ids[name] = generation_id
    if not isinstance(code_version, str) or not _SHA1.match(code_version):
        raise ReadContractError(
            f"code_version must be a 40-char lowercase-hex code version, "
            f"got {code_version!r}")
    return _result(
        request.mode, "reconstruction", request.contract,
        {
            "cutoff": cutoff_at.isoformat(),
            "clock": knowledge_clock.value,
            "knowledge": _KNOWLEDGE_TERMS.get(knowledge_clock, knowledge_clock.value),
            "dependency_generation_ids": MappingProxyType(generation_ids),
            "revision_resolution": MappingProxyType(revision_resolutions),
            "code_version": code_version,
        },
        values)


def _current_generation(name: str, dependency: Dependency) -> GenerationRef:
    """The dependency's CURRENT generation — its newest non-superseded one.

    Per D00.D5.2 the ledger's ``supersedes`` edges decide what "now" is: a
    generation another generation supersedes is history, readable by id only for
    RECONSTRUCT/REPLAY.  Live generations order on ``coalesce(published_at,
    ingested_at)``; a live generation stating neither instant cannot be ordered
    and is refused, not fallback-bound.
    """
    ledger = tuple(dependency.generations)
    superseded = {g.supersedes for g in ledger if g.supersedes}
    live = [g for g in ledger if g.generation_id not in superseded]
    if not live:
        raise ReadRefusal(
            RefusalCode.UNBOUND_DEPENDENCY,
            f"every generation of {name!r} is superseded - no current generation")
    stamped: list[tuple[datetime, GenerationRef]] = []
    for generation in live:
        instant = (generation.published_at if generation.published_at is not None
                   else generation.ingested_at)
        if instant is None:
            raise ReadRefusal(
                RefusalCode.MISSING_CLOCK_VALUE,
                f"generation {generation.generation_id!r} states neither published_at "
                "nor ingested_at - CURRENT cannot order it")
        stamped.append((utc(instant), generation))
    newest = max(instant for instant, _ in stamped)
    chosen = [generation for instant, generation in stamped if instant == newest]
    if len({generation.generation_id for generation in chosen}) > 1:
        ids = ", ".join(sorted(generation.generation_id for generation in chosen))
        raise ReadRefusal(
            RefusalCode.AMBIGUOUS_REVISION,
            f"distinct generations of {name!r} tie as the current newest: {ids}")
    winner = chosen[0]
    pinned = dependency.pinned_generation_id
    if pinned is not None and pinned != winner.generation_id:
        raise ReadRefusal(
            RefusalCode.STALE_GENERATION,
            f"dependency {name!r} pins generation {pinned!r} but its newest "
            f"non-superseded generation is {winner.generation_id!r}")
    return winner


def current(request: ReadRequest, dependencies: Mapping[str, Dependency], *,
            evidence: CurrentEvidence) -> ReadResult:
    """What the house holds now — labelled "current", never a historical claim.

    Evidence is validated BEFORE any row is iterated, and ``cutoff``/``clock``
    deliberately never appear in its evidence.  The generation ledger is read
    before any row either: each dependency binds its newest non-superseded
    generation (D00.D5.2), and evidence naming a ledger id that has since been
    superseded is STALE, because CURRENT never serves a superseded generation.
    Rows resolve exactly as a RECONSTRUCT binds them (max revision per key, or
    the unique-key law), so CURRENT and the historical reads answer with the
    same row for the same state (R01 M5).
    """
    _mode_request(request, ReadMode.CURRENT, "current")
    _validate_current_evidence(evidence)
    _dependency_map(dependencies)
    # FIRST LOOP — generations only; no row is touched yet.
    generation_ids: dict[str, str | None] = {}
    for name, dependency in dependencies.items():
        if dependency.generations:
            generation_ids[name] = _current_generation(name, dependency).generation_id
        elif dependency.pinned_generation_id is not None:
            raise ReadRefusal(
                RefusalCode.UNBOUND_DEPENDENCY,
                f"dependency {name!r} pins generation "
                f"{dependency.pinned_generation_id!r} but declares no generations")
        else:
            generation_ids[name] = None
    # Identity coherence: an id the ledger actually contains must be its CURRENT
    # one; an id found in no ledger is another dependency's vocabulary, unchecked.
    for name, dependency in dependencies.items():
        if not dependency.generations:
            continue
        ledger_ids = {g.generation_id for g in dependency.generations}
        if (evidence.identity_generation_id in ledger_ids
                and generation_ids[name] != evidence.identity_generation_id):
            raise ReadRefusal(
                RefusalCode.STALE_GENERATION,
                f"CURRENT evidence names generation "
                f"{evidence.identity_generation_id!r} of {name!r} but "
                f"{generation_ids[name]!r} is its newest non-superseded generation - "
                "a superseded generation is readable by id only for "
                "RECONSTRUCT/REPLAY (D00.D5.2)")
    # SECOND LOOP — the rows, bound through the same shared binder as a read.
    values: dict[str, tuple[dict, ...]] = {}
    resolutions: dict[str, str] = {}
    for name, dependency in dependencies.items():
        supplied = tuple(dependency.rows)
        values[name], resolutions[name] = _bind_rows(
            name, dependency, supplied, [dict(row) for row in supplied],
            generation_ids[name])
    return _result(
        request.mode, "current", request.contract,
        {
            "receipt_sha256s": tuple(evidence.receipt_sha256s),
            "identity_generation_id": evidence.identity_generation_id,
            "action_revision_set_id": evidence.action_revision_set_id,
            "code_version": evidence.code_version,
            "dependency_generation_ids": MappingProxyType(generation_ids),
            "revision_resolution": MappingProxyType(resolutions),
        },
        values)


def replay(request: ReadRequest, retained: RetainedOutput | None, *,
           max_bytes: int = 64 * 1024 * 1024) -> ReadResult:
    """What the system ACTUALLY emitted — the retained bytes or a typed refusal.

    A checksum alone is not retained material; a wrong artifact id, a missing
    publishing receipt or absent bytes all refuse NO_RETAINED_OUTPUT rather than
    regenerate (recomputing is a current-rule recomputation, not a replay).
    Tampered bytes refuse RETAINED_DIGEST_MISMATCH instead of serving altered
    history.
    """
    _mode_request(request, ReadMode.REPLAY, "replay")
    if (
        retained is None
        or not isinstance(retained, RetainedOutput)
        or retained.output_id != request.output_id
        or retained.payload is None
        or not isinstance(retained.publishing_receipt_sha256, str)
        or not _HEX64.match(retained.publishing_receipt_sha256)
    ):
        raise ReadRefusal(
            RefusalCode.NO_RETAINED_OUTPUT,
            f"no retained material proves output {request.output_id!r} — a checksum or "
            "a generated label is never substituted for retained bytes")
    if len(retained.payload) > max_bytes:
        raise ReadContractError(
            f"retained payload for {request.output_id!r} is {len(retained.payload)} "
            f"bytes, above the {max_bytes}-byte replay budget")
    digest = hashlib.sha256(retained.payload).hexdigest()
    if digest != retained.sha256:
        raise ReadRefusal(
            RefusalCode.RETAINED_DIGEST_MISMATCH,
            f"retained bytes for {request.output_id!r} hash to {digest}, not the bound "
            f"{retained.sha256!r}")
    return _result(
        request.mode, "replay", request.contract,
        {
            "output_id": retained.output_id,
            "sha256": digest,
            "publishing_receipt_sha256": retained.publishing_receipt_sha256,
        },
        {}, payload=retained.payload)


def _canonical_value(value: object) -> object:
    """JSON-able form of one row value; datetimes bind through ``utc().isoformat()``."""
    if isinstance(value, datetime):
        return utc(value).isoformat()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    raise ReadContractError(
        f"row value {value!r} of type {type(value).__name__} is neither JSON nor a "
        "datetime — it cannot bind as a selected input")


def _canonical_row_text(row: Mapping[str, object]) -> str:
    normalized = {str(key): _canonical_value(value) for key, value in row.items()}
    try:
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReadContractError(f"row is not canonical JSON: {exc}") from exc


def selected_input_sha256s(result: ReadResult) -> Mapping[str, str]:
    """Per dependency, a digest of EXACTLY the rows this result selected.

    Binds a reconstruction to its inputs: two reads that selected the same rows
    digest equal whatever order the rows were supplied in, and a read that
    selected different rows can never present itself as the same input state.
    Each row becomes one canonical JSON text (sort_keys, tight separators,
    datetimes through ``utc().isoformat()``), the texts are SORTED, and the
    sorted texts are hashed together — so selection, not supply order, decides.
    The SELECTED GENERATION is bound too (R01 M6): a dependency whose ledger
    named a generation hashes ``{"generation_id": ..., "rows": [...]}``, so two
    reads selecting the same (empty) rows under different generations can never
    present themselves as the same input state.  A dependency with no ledger
    hashes exactly as before, byte for byte.  A REPLAY result selected no
    inputs: it binds the retained ``sha256`` instead, so asking it for input
    digests is a contract error, not a digest.
    """
    if result.mode is ReadMode.REPLAY:
        raise ReadContractError(
            "a REPLAY result binds the retained output sha256, not selected inputs")
    gids = result.evidence.get("dependency_generation_ids") or {}
    digests: dict[str, str] = {}
    for name, rows in result.values.items():
        texts = sorted(_canonical_row_text(row) for row in rows)
        gid = gids.get(name)
        if gid is None:
            blob = json.dumps(texts, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False)
        else:
            blob = json.dumps({"generation_id": gid, "rows": texts}, sort_keys=True,
                              separators=(",", ":"), ensure_ascii=False)
        digests[name] = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return MappingProxyType(digests)
