"""Research-only catalyst context attachment for Live Entry Radar episodes.

This module does not detect tactical entries, mint event identities, rank names, score
setups, size positions, or originate trading authority. It consumes caller-supplied
source-owner evidence and answers one narrow point-in-time question: what catalyst
coverage and owner-classified event evidence was actually knowable at a Radar decision
clock?

Missing/stale coverage is never equivalent to "no event". Event materiality is never
inferred here from price, residual returns, headline prose, or an LLM. If a source owner
has not supplied a governed disposition, the event remains ``unknown``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from engine.entry_radar.contracts import AUTHORITY_BLOCK, SOURCE_STATUSES, iso, parse_ts

SCHEMA = "mastermind.entry_radar.catalyst_context.v1"
OWNER_DISPOSITIONS = frozenset({"blocking", "soft", "nonblocking", "unknown"})
CONTEXT_STATES = frozenset({
    "blocking_event_observed",
    "event_classification_unknown",
    "coverage_unknown",
    "soft_event_observed",
    "no_blocking_event_observed",
})


class CatalystContextError(ValueError):
    """Malformed catalyst context input; callers must fail closed."""


def _require_ts(name: str, value: Any) -> datetime:
    got = parse_ts(value)
    if got is None:
        raise CatalystContextError(f"{name} must be an ISO timestamp (got {value!r})")
    return got.astimezone(timezone.utc)


def _require_text(name: str, value: Any) -> str:
    got = str(value or "").strip()
    if not got:
        raise CatalystContextError(f"{name} is required")
    return got


@dataclass(frozen=True, slots=True)
class CatalystSourceRead:
    """One source owner's coverage read, using Radar's existing availability vocabulary."""

    source_id: str
    status: str
    source_asof: datetime
    observed_at: datetime
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _require_text("source_id", self.source_id))
        if self.status not in SOURCE_STATUSES:
            raise CatalystContextError(
                f"source status {self.status!r} not in {sorted(SOURCE_STATUSES)}"
            )
        source_asof = _require_ts("source_asof", self.source_asof)
        observed_at = _require_ts("observed_at", self.observed_at)
        if source_asof > observed_at:
            raise CatalystContextError(
                f"{self.source_id}: source_asof {iso(source_asof)} is after observed_at "
                f"{iso(observed_at)}"
            )
        object.__setattr__(self, "source_asof", source_asof)
        object.__setattr__(self, "observed_at", observed_at)

    def usable_at(self, decision_at: datetime) -> bool:
        return (
            self.status == "ok"
            and self.source_asof <= decision_at
            and self.observed_at <= decision_at
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "source_asof": iso(self.source_asof),
            "observed_at": iso(self.observed_at),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class CatalystEvidence:
    """A compact reference to source-owner event truth; no event body is copied here."""

    owner: str
    native_id: str
    ticker: str
    event_kind: str
    source_available_at: datetime
    known_at: datetime
    owner_disposition: str
    evidence_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner", _require_text("owner", self.owner))
        object.__setattr__(self, "native_id", _require_text("native_id", self.native_id))
        ticker = _require_text("ticker", self.ticker).upper()
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "event_kind", _require_text("event_kind", self.event_kind))
        object.__setattr__(self, "evidence_ref", _require_text("evidence_ref", self.evidence_ref))
        if self.owner_disposition not in OWNER_DISPOSITIONS:
            raise CatalystContextError(
                f"owner_disposition {self.owner_disposition!r} not in "
                f"{sorted(OWNER_DISPOSITIONS)}"
            )
        source_available_at = _require_ts("source_available_at", self.source_available_at)
        known_at = _require_ts("known_at", self.known_at)
        if source_available_at > known_at:
            raise CatalystContextError(
                f"{self.owner}:{self.native_id}: source_available_at "
                f"{iso(source_available_at)} is after known_at {iso(known_at)}"
            )
        object.__setattr__(self, "source_available_at", source_available_at)
        object.__setattr__(self, "known_at", known_at)

    @property
    def identity(self) -> tuple[str, str]:
        return (self.owner, self.native_id)

    def canonical_tuple(self) -> tuple[str, ...]:
        return (
            self.owner,
            self.native_id,
            self.ticker,
            self.event_kind,
            iso(self.source_available_at) or "",
            iso(self.known_at) or "",
            self.owner_disposition,
            self.evidence_ref,
        )


@dataclass(frozen=True, slots=True)
class CatalystContext:
    """Point-in-time catalyst context attached to an existing Radar episode reference."""

    ticker: str
    tactical_episode_ref: str
    decision_at: datetime
    context_state: str
    coverage_complete: bool
    required_sources: tuple[str, ...]
    source_reads: tuple[CatalystSourceRead, ...]
    blocking_evidence_refs: tuple[str, ...] = ()
    soft_evidence_refs: tuple[str, ...] = ()
    unknown_evidence_refs: tuple[str, ...] = ()
    nonblocking_evidence_refs: tuple[str, ...] = ()
    late_evidence_refs: tuple[str, ...] = ()
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.context_state not in CONTEXT_STATES:
            raise CatalystContextError(
                f"context_state {self.context_state!r} not in {sorted(CONTEXT_STATES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "ticker": self.ticker,
            "tactical_episode_ref": self.tactical_episode_ref,
            "decision_at": iso(self.decision_at),
            "context_state": self.context_state,
            "coverage_complete": self.coverage_complete,
            "required_sources": list(self.required_sources),
            "source_reads": [r.to_dict() for r in self.source_reads],
            "blocking_evidence_refs": list(self.blocking_evidence_refs),
            "soft_evidence_refs": list(self.soft_evidence_refs),
            "unknown_evidence_refs": list(self.unknown_evidence_refs),
            "nonblocking_evidence_refs": list(self.nonblocking_evidence_refs),
            "late_evidence_refs": list(self.late_evidence_refs),
            "authority": dict(AUTHORITY_BLOCK),
            "research_only": True,
        }


def _dedupe_evidence(evidence: Iterable[CatalystEvidence]) -> tuple[CatalystEvidence, ...]:
    by_id: dict[tuple[str, str], CatalystEvidence] = {}
    for row in evidence:
        prior = by_id.get(row.identity)
        if prior is None:
            by_id[row.identity] = row
            continue
        if prior.canonical_tuple() != row.canonical_tuple():
            raise CatalystContextError(
                f"conflicting payloads for catalyst evidence identity {row.identity!r}"
            )
    return tuple(sorted(by_id.values(), key=lambda r: r.canonical_tuple()))


def assess_catalyst_context(
    *,
    ticker: str,
    tactical_episode_ref: str,
    decision_at: datetime,
    required_sources: Sequence[str],
    source_reads: Sequence[CatalystSourceRead],
    evidence: Sequence[CatalystEvidence],
) -> CatalystContext:
    """Attach fail-closed catalyst context without changing the Radar episode identity.

    ``required_sources`` is an explicit caller contract: the function never pretends an
    omitted source is covered. A healthy empty read means only "nothing blocking was
    observed in the declared covered sources by decision_at".
    """
    symbol = _require_text("ticker", ticker).upper()
    episode_ref = _require_text("tactical_episode_ref", tactical_episode_ref)
    decision = _require_ts("decision_at", decision_at)

    required = tuple(sorted({_require_text("required_source", s) for s in required_sources}))
    if not required:
        raise CatalystContextError("required_sources must declare at least one source owner")

    read_by_source: dict[str, CatalystSourceRead] = {}
    for row in source_reads:
        if row.source_id in read_by_source:
            raise CatalystContextError(f"duplicate source read for {row.source_id!r}")
        read_by_source[row.source_id] = row

    coverage_complete = all(
        source in read_by_source and read_by_source[source].usable_at(decision)
        for source in required
    )

    deduped = _dedupe_evidence(evidence)
    for row in deduped:
        if row.ticker != symbol:
            raise CatalystContextError(
                f"catalyst evidence ticker {row.ticker!r} does not match {symbol!r}"
            )

    on_time = tuple(row for row in deduped if row.known_at <= decision)
    late = tuple(row for row in deduped if row.known_at > decision)

    groups: dict[str, list[str]] = {
        "blocking": [], "soft": [], "unknown": [], "nonblocking": [],
    }
    for row in on_time:
        groups[row.owner_disposition].append(row.evidence_ref)
    for refs in groups.values():
        refs.sort()

    if groups["blocking"]:
        state = "blocking_event_observed"
    elif groups["unknown"]:
        state = "event_classification_unknown"
    elif not coverage_complete:
        state = "coverage_unknown"
    elif groups["soft"]:
        state = "soft_event_observed"
    else:
        state = "no_blocking_event_observed"

    ordered_reads = tuple(sorted(source_reads, key=lambda r: r.source_id))
    return CatalystContext(
        ticker=symbol,
        tactical_episode_ref=episode_ref,
        decision_at=decision,
        context_state=state,
        coverage_complete=coverage_complete,
        required_sources=required,
        source_reads=ordered_reads,
        blocking_evidence_refs=tuple(groups["blocking"]),
        soft_evidence_refs=tuple(groups["soft"]),
        unknown_evidence_refs=tuple(groups["unknown"]),
        nonblocking_evidence_refs=tuple(groups["nonblocking"]),
        late_evidence_refs=tuple(sorted(row.evidence_ref for row in late)),
    )
