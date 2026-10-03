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

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from engine.entry_radar.contracts import AUTHORITY_BLOCK, SOURCE_STATUSES, _TICKER_RE

if TYPE_CHECKING:
    from engine.entry_radar.live_ledger import LiveEpisode

SCHEMA = "mastermind.entry_radar.catalyst_context.v1"
RADAR_EPISODE_SCHEMA = "mastermind.live_entry_episode.v1"
OWNER_DISPOSITIONS = frozenset({"blocking", "soft", "nonblocking", "unknown"})
CONTEXT_STATES = frozenset({
    "blocking_event_observed",
    "event_classification_unknown",
    "coverage_unknown",
    "soft_event_observed",
    "no_blocking_event_observed",
})

MAX_ID_CHARS = 256
MAX_DETAIL_CHARS = 512
MAX_REQUIRED_SOURCES = 32
MAX_SOURCE_READS = 32
MAX_EVIDENCE = 256
EVIDENCE_TIMINGS = frozenset({"active", "late", "expired"})


class CatalystContextError(ValueError):
    """Malformed catalyst context input; callers must fail closed."""


# Local boundary/serialization validation, not a replacement for Radar's clock owner.
_AWARE_INSTANT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)


def _require_ts(name: str, value: Any) -> datetime:
    if isinstance(value, datetime):
        got = value
    elif isinstance(value, str) and _AWARE_INSTANT.fullmatch(value):
        if value.endswith("-00:00"):
            raise CatalystContextError(f"{name} has an unknown timezone offset")
        try:
            got = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CatalystContextError(f"{name} must be a valid aware timestamp") from exc
    else:
        raise CatalystContextError(f"{name} requires an explicit timezone and time")
    if got.tzinfo is None or got.utcoffset() is None:
        raise CatalystContextError(f"{name} requires an explicit timezone")
    return got.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    """Keep subsecond decision boundaries; never truncate evidence into the past."""
    return _require_ts("timestamp", value).isoformat().replace("+00:00", "Z")


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalystContextError(f"{name} must be a nonempty string")
    return value.strip()


def _bounded_id(name: str, value: Any) -> str:
    text = _require_text(name, value)
    if len(text) > MAX_ID_CHARS:
        raise CatalystContextError(f"{name} exceeds {MAX_ID_CHARS} characters")
    return text


def _require_detail(value: Any) -> str:
    if not isinstance(value, str):
        raise CatalystContextError("detail must be a string")
    if len(value) > MAX_DETAIL_CHARS:
        raise CatalystContextError(f"detail exceeds {MAX_DETAIL_CHARS} characters")
    return value


def _episode_id(value: Any) -> str:
    value = _require_text("radar_episode_id", value)
    if not re.fullmatch(r"[0-9a-f]{16}", value):
        raise CatalystContextError(
            "radar_episode_id must be the owner-issued 16-hex Live Entry Radar episode_id"
        )
    return value


def _required_sources(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise CatalystContextError("required_sources must be an explicit sequence")
    if len(values) > MAX_REQUIRED_SOURCES:
        raise CatalystContextError(
            f"required_sources exceeds {MAX_REQUIRED_SOURCES} entries"
        )
    required = tuple(sorted({_bounded_id("required_source", s) for s in values}))
    if not required:
        raise CatalystContextError("required_sources must declare at least one source owner")
    return required


def _coverage(required, reads, decision) -> bool:
    by_source = {}
    for row in reads:
        if not isinstance(row, CatalystSourceRead):
            raise CatalystContextError("source_reads must contain CatalystSourceRead records")
        if row.source_id in by_source:
            raise CatalystContextError(f"duplicate source read for {row.source_id!r}")
        by_source[row.source_id] = row
    return all(s in by_source and by_source[s].usable_at(decision) for s in required)


def _state(blocking, unknown, coverage_complete, soft) -> str:
    if blocking:
        return "blocking_event_observed"
    if unknown:
        return "event_classification_unknown"
    if not coverage_complete:
        return "coverage_unknown"
    if soft:
        return "soft_event_observed"
    return "no_blocking_event_observed"


def _evidence_timing(
    known_at: datetime,
    relevant_until: datetime,
    decision_at: datetime,
) -> str:
    if known_at > decision_at:
        return "late"
    if relevant_until < decision_at:
        return "expired"
    return "active"


@dataclass(frozen=True, slots=True)
class CatalystSourceRead:
    """One source owner's coverage read, using Radar's existing availability vocabulary."""

    source_id: str
    status: str
    source_asof: datetime
    observed_at: datetime
    fresh_until: datetime
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _bounded_id("source_id", self.source_id))
        if self.status not in SOURCE_STATUSES:
            raise CatalystContextError(
                f"source status {self.status!r} not in {sorted(SOURCE_STATUSES)}"
            )
        source_asof = _require_ts("source_asof", self.source_asof)
        observed_at = _require_ts("observed_at", self.observed_at)
        fresh_until = _require_ts("fresh_until", self.fresh_until)
        if source_asof > observed_at:
            raise CatalystContextError(
                f"{self.source_id}: source_asof {_iso(source_asof)} is after observed_at "
                f"{_iso(observed_at)}"
            )
        if fresh_until < source_asof:
            raise CatalystContextError(
                f"{self.source_id}: fresh_until {_iso(fresh_until)} is before source_asof "
                f"{_iso(source_asof)}"
            )
        object.__setattr__(self, "source_asof", source_asof)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "fresh_until", fresh_until)
        object.__setattr__(self, "detail", _require_detail(self.detail))

    def usable_at(self, decision_at: datetime) -> bool:
        decision = _require_ts("decision_at", decision_at)
        return (
            self.status == "ok"
            and self.source_asof <= self.observed_at <= decision <= self.fresh_until
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "source_asof": _iso(self.source_asof),
            "observed_at": _iso(self.observed_at),
            "fresh_until": _iso(self.fresh_until),
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
    relevant_until: datetime
    owner_disposition: str
    evidence_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner", _bounded_id("owner", self.owner))
        object.__setattr__(self, "native_id", _bounded_id("native_id", self.native_id))
        ticker = _require_text("ticker", self.ticker).upper()
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "event_kind", _bounded_id("event_kind", self.event_kind))
        object.__setattr__(
            self, "evidence_ref", _bounded_id("evidence_ref", self.evidence_ref)
        )
        if self.owner_disposition not in OWNER_DISPOSITIONS:
            raise CatalystContextError(
                f"owner_disposition {self.owner_disposition!r} not in "
                f"{sorted(OWNER_DISPOSITIONS)}"
            )
        source_available_at = _require_ts("source_available_at", self.source_available_at)
        known_at = _require_ts("known_at", self.known_at)
        relevant_until = _require_ts("relevant_until", self.relevant_until)
        if source_available_at > known_at:
            raise CatalystContextError(
                f"{self.owner}:{self.native_id}: source_available_at "
                f"{_iso(source_available_at)} is after known_at {_iso(known_at)}"
            )
        if relevant_until < source_available_at:
            raise CatalystContextError(
                f"{self.owner}:{self.native_id}: relevant_until "
                f"{_iso(relevant_until)} is before source_available_at "
                f"{_iso(source_available_at)}"
            )
        object.__setattr__(self, "source_available_at", source_available_at)
        object.__setattr__(self, "known_at", known_at)
        object.__setattr__(self, "relevant_until", relevant_until)

    @property
    def identity(self) -> tuple[str, str]:
        return (self.owner, self.native_id)

    def canonical_tuple(self) -> tuple[str, ...]:
        return (
            self.owner,
            self.native_id,
            self.ticker,
            self.event_kind,
            _iso(self.source_available_at) or "",
            _iso(self.known_at) or "",
            _iso(self.relevant_until) or "",
            self.owner_disposition,
            self.evidence_ref,
        )


@dataclass(frozen=True, slots=True)
class CatalystEvidenceClock:
    """Wire-auditable timing for one deduped evidence reference at a decision clock."""

    evidence_ref: str
    source_available_at: datetime
    known_at: datetime
    relevant_until: datetime
    timing: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "evidence_ref", _bounded_id("evidence_ref", self.evidence_ref)
        )
        object.__setattr__(
            self, "source_available_at", _require_ts("source_available_at", self.source_available_at)
        )
        object.__setattr__(self, "known_at", _require_ts("known_at", self.known_at))
        object.__setattr__(
            self, "relevant_until", _require_ts("relevant_until", self.relevant_until)
        )
        if self.timing not in EVIDENCE_TIMINGS:
            raise CatalystContextError(
                f"timing {self.timing!r} not in {sorted(EVIDENCE_TIMINGS)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_ref": self.evidence_ref,
            "source_available_at": _iso(self.source_available_at),
            "known_at": _iso(self.known_at),
            "relevant_until": _iso(self.relevant_until),
            "timing": self.timing,
        }


@dataclass(frozen=True, slots=True)
class CatalystContext:
    """Point-in-time catalyst context attached to an owner-issued Radar episode id."""

    ticker: str
    radar_episode_id: str
    decision_at: datetime
    generated_at: datetime
    context_state: str
    coverage_complete: bool
    required_sources: tuple[str, ...]
    source_reads: tuple[CatalystSourceRead, ...]
    blocking_evidence_refs: tuple[str, ...] = ()
    soft_evidence_refs: tuple[str, ...] = ()
    unknown_evidence_refs: tuple[str, ...] = ()
    nonblocking_evidence_refs: tuple[str, ...] = ()
    late_evidence_refs: tuple[str, ...] = ()
    expired_evidence_refs: tuple[str, ...] = ()
    evidence_clocks: tuple[CatalystEvidenceClock, ...] = ()
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise CatalystContextError("invalid catalyst context schema")
        symbol = _require_text("ticker", self.ticker).upper()
        if not _TICKER_RE.fullmatch(symbol):
            raise CatalystContextError("invalid ticker shape")
        object.__setattr__(self, "ticker", symbol)
        object.__setattr__(self, "radar_episode_id", _episode_id(self.radar_episode_id))
        decision = _require_ts("decision_at", self.decision_at)
        generated = _require_ts("generated_at", self.generated_at)
        object.__setattr__(self, "decision_at", decision)
        object.__setattr__(self, "generated_at", generated)
        if decision > generated:
            raise CatalystContextError("decision_at is after generated_at")
        object.__setattr__(self, "required_sources", _required_sources(self.required_sources))
        if len(self.source_reads) > MAX_SOURCE_READS:
            raise CatalystContextError(f"source_reads exceeds {MAX_SOURCE_READS} entries")
        object.__setattr__(self, "source_reads", tuple(self.source_reads))
        for row in self.source_reads:
            if row.observed_at > generated:
                raise CatalystContextError(
                    f"{row.source_id}: observed_at is after generated_at"
                )
        complete = _coverage(self.required_sources, self.source_reads, self.decision_at)
        if type(self.coverage_complete) is not bool or self.coverage_complete != complete:
            raise CatalystContextError("coverage_complete contradicts source reads")
        ref_names = (
            "blocking_evidence_refs", "soft_evidence_refs", "unknown_evidence_refs",
            "nonblocking_evidence_refs", "late_evidence_refs", "expired_evidence_refs",
        )
        ref_tuples: dict[str, tuple[str, ...]] = {}
        seen_refs: set[str] = set()
        for name in ref_names:
            values = getattr(self, name)
            if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
                raise CatalystContextError(f"{name} must be a sequence")
            if len(values) > MAX_EVIDENCE:
                raise CatalystContextError(f"{name} exceeds {MAX_EVIDENCE} entries")
            refs = tuple(sorted(_bounded_id(name, ref) for ref in values))
            if len(refs) != len(set(refs)):
                raise CatalystContextError(f"{name} contains duplicate references")
            overlap = seen_refs.intersection(refs)
            if overlap:
                raise CatalystContextError(
                    "evidence reference appears in more than one disposition group"
                )
            seen_refs.update(refs)
            object.__setattr__(self, name, refs)
            ref_tuples[name] = refs
        clocks = tuple(self.evidence_clocks)
        if len(clocks) > MAX_EVIDENCE:
            raise CatalystContextError(f"evidence_clocks exceeds {MAX_EVIDENCE} entries")
        clock_refs = [c.evidence_ref for c in clocks]
        if len(clock_refs) != len(set(clock_refs)):
            raise CatalystContextError("evidence_clocks contains duplicate evidence_ref")
        if tuple(sorted(clock_refs)) != tuple(sorted(seen_refs)):
            raise CatalystContextError("evidence_clocks must cover every evidence reference")
        if clocks != tuple(sorted(clocks, key=lambda c: c.evidence_ref)):
            raise CatalystContextError("evidence_clocks must be sorted by evidence_ref")
        for clock in clocks:
            if clock.known_at > generated:
                raise CatalystContextError(
                    f"{clock.evidence_ref}: known_at is after generated_at"
                )
            expected_timing = _evidence_timing(
                clock.known_at, clock.relevant_until, decision
            )
            if clock.timing != expected_timing:
                raise CatalystContextError(
                    f"{clock.evidence_ref}: timing contradicts decision clocks"
                )
            if clock.timing == "late" and clock.evidence_ref not in ref_tuples["late_evidence_refs"]:
                raise CatalystContextError(
                    f"{clock.evidence_ref}: late timing not in late_evidence_refs"
                )
            if clock.timing == "expired" and clock.evidence_ref not in ref_tuples["expired_evidence_refs"]:
                raise CatalystContextError(
                    f"{clock.evidence_ref}: expired timing not in expired_evidence_refs"
                )
            if clock.timing == "active":
                active_home = (
                    ref_tuples["blocking_evidence_refs"]
                    + ref_tuples["soft_evidence_refs"]
                    + ref_tuples["unknown_evidence_refs"]
                    + ref_tuples["nonblocking_evidence_refs"]
                )
                if clock.evidence_ref not in active_home:
                    raise CatalystContextError(
                        f"{clock.evidence_ref}: active timing not in disposition refs"
                    )
        expected = _state(
            ref_tuples["blocking_evidence_refs"],
            ref_tuples["unknown_evidence_refs"],
            complete,
            ref_tuples["soft_evidence_refs"],
        )
        if self.context_state != expected:
            raise CatalystContextError("context_state contradicts evidence/coverage")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "ticker": self.ticker,
            "radar_episode_schema": RADAR_EPISODE_SCHEMA,
            "radar_episode_id": self.radar_episode_id,
            "decision_at": _iso(self.decision_at),
            "generated_at": _iso(self.generated_at),
            "context_state": self.context_state,
            "coverage_complete": self.coverage_complete,
            "required_sources": list(self.required_sources),
            "source_reads": [r.to_dict() for r in self.source_reads],
            "blocking_evidence_refs": list(self.blocking_evidence_refs),
            "soft_evidence_refs": list(self.soft_evidence_refs),
            "unknown_evidence_refs": list(self.unknown_evidence_refs),
            "nonblocking_evidence_refs": list(self.nonblocking_evidence_refs),
            "late_evidence_refs": list(self.late_evidence_refs),
            "expired_evidence_refs": list(self.expired_evidence_refs),
            "evidence_clocks": [c.to_dict() for c in self.evidence_clocks],
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


def _validate_generation_clocks(
    *,
    generated_at: datetime,
    decision_at: datetime,
    source_reads: Sequence[CatalystSourceRead],
    evidence: Sequence[CatalystEvidence],
) -> None:
    generated = _require_ts("generated_at", generated_at)
    decision = _require_ts("decision_at", decision_at)
    if decision > generated:
        raise CatalystContextError("decision_at is after generated_at")
    for row in source_reads:
        if row.observed_at > generated:
            raise CatalystContextError(
                f"{row.source_id}: observed_at is after generated_at"
            )
    for row in evidence:
        if row.known_at > generated:
            raise CatalystContextError(
                f"{row.evidence_ref}: known_at is after generated_at"
            )


def assess_catalyst_context(
    *,
    ticker: str,
    radar_episode_id: str,
    decision_at: datetime,
    generated_at: datetime,
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
    episode_id = _episode_id(radar_episode_id)
    decision = _require_ts("decision_at", decision_at)
    generated = _require_ts("generated_at", generated_at)
    _validate_generation_clocks(
        generated_at=generated,
        decision_at=decision,
        source_reads=source_reads,
        evidence=evidence,
    )
    required = _required_sources(required_sources)
    if len(source_reads) > MAX_SOURCE_READS:
        raise CatalystContextError(f"source_reads exceeds {MAX_SOURCE_READS} entries")
    coverage_complete = _coverage(required, source_reads, decision)

    deduped = _dedupe_evidence(evidence)
    if len(deduped) > MAX_EVIDENCE:
        raise CatalystContextError(f"evidence exceeds {MAX_EVIDENCE} rows after dedupe")
    ref_to_identity: dict[str, tuple[str, str]] = {}
    for row in deduped:
        if row.ticker != symbol:
            raise CatalystContextError(
                f"catalyst evidence ticker {row.ticker!r} does not match {symbol!r}"
            )
        prior = ref_to_identity.get(row.evidence_ref)
        if prior is not None and prior != row.identity:
            raise CatalystContextError(
                "evidence_ref maps to more than one evidence identity"
            )
        ref_to_identity[row.evidence_ref] = row.identity

    groups: dict[str, list[str]] = {
        "blocking": [], "soft": [], "unknown": [], "nonblocking": [],
    }
    late: list[str] = []
    expired: list[str] = []
    clocks: list[CatalystEvidenceClock] = []
    for row in deduped:
        timing = _evidence_timing(row.known_at, row.relevant_until, decision)
        clocks.append(
            CatalystEvidenceClock(
                evidence_ref=row.evidence_ref,
                source_available_at=row.source_available_at,
                known_at=row.known_at,
                relevant_until=row.relevant_until,
                timing=timing,
            )
        )
        if timing == "late":
            late.append(row.evidence_ref)
        elif timing == "expired":
            expired.append(row.evidence_ref)
        else:
            groups[row.owner_disposition].append(row.evidence_ref)
    for refs in groups.values():
        refs.sort()
    late.sort()
    expired.sort()

    state = _state(groups["blocking"], groups["unknown"], coverage_complete, groups["soft"])

    ordered_reads = tuple(sorted(source_reads, key=lambda r: r.source_id))
    ordered_clocks = tuple(sorted(clocks, key=lambda c: c.evidence_ref))
    return CatalystContext(
        ticker=symbol,
        radar_episode_id=episode_id,
        decision_at=decision,
        generated_at=generated,
        context_state=state,
        coverage_complete=coverage_complete,
        required_sources=required,
        source_reads=ordered_reads,
        blocking_evidence_refs=tuple(groups["blocking"]),
        soft_evidence_refs=tuple(groups["soft"]),
        unknown_evidence_refs=tuple(groups["unknown"]),
        nonblocking_evidence_refs=tuple(groups["nonblocking"]),
        late_evidence_refs=tuple(late),
        expired_evidence_refs=tuple(expired),
        evidence_clocks=ordered_clocks,
    )


def assess_catalyst_context_for_live_episode(
    *,
    episode: "LiveEpisode | Mapping[str, Any]",
    decision_at: datetime,
    generated_at: datetime,
    required_sources: Sequence[str],
    source_reads: Sequence[CatalystSourceRead],
    evidence: Sequence[CatalystEvidence],
) -> CatalystContext:
    """Bind catalyst context to one validated owner-issued Radar live episode.

    This is a read-only composition seam. It does not mutate the episode, append catalyst
    references to ``LiveEpisode.evidence_refs``, or mint an alternate episode address.
    """
    from engine.entry_radar.live_ledger import (  # noqa: PLC0415
        LedgerError,
        LiveEpisode,
        compute_episode_id,
    )

    if isinstance(episode, LiveEpisode):
        record = episode
    elif isinstance(episode, Mapping):
        try:
            record = LiveEpisode.from_dict(episode)
        except (LedgerError, KeyError, TypeError, ValueError) as exc:
            raise CatalystContextError(f"invalid Live Entry Radar episode: {exc}") from exc
    else:
        raise CatalystContextError("episode must be a LiveEpisode or its exact mapping")

    expected_id = compute_episode_id(
        ticker=record.ticker,
        detector_id=record.detector_id,
        variant=record.variant,
        first_armed_at=record.first_armed_at,
    )
    if record.episode_id != expected_id:
        raise CatalystContextError(
            f"Radar episode_id {record.episode_id!r} does not match owner identity "
            f"tuple (expected {expected_id!r})"
        )

    decision = _require_ts("decision_at", decision_at)
    clocks = {
        "first_armed_at": _require_ts("first_armed_at", record.first_armed_at),
        "last_observed_at": _require_ts("last_observed_at", record.last_observed_at),
    }
    if record.candidate_at is not None:
        clocks["candidate_at"] = _require_ts("candidate_at", record.candidate_at)
    for name, when in clocks.items():
        if when > decision:
            raise CatalystContextError(f"Radar {name} is after decision_at")
    if clocks["first_armed_at"] > clocks["last_observed_at"]:
        raise CatalystContextError("Radar snapshot precedes its arm clock")
    if "candidate_at" in clocks and not (
        clocks["first_armed_at"] <= clocks["candidate_at"] <= clocks["last_observed_at"]
    ):
        raise CatalystContextError("Radar candidate clock is outside its snapshot interval")

    return assess_catalyst_context(
        ticker=record.ticker,
        radar_episode_id=record.episode_id,
        decision_at=decision_at,
        generated_at=generated_at,
        required_sources=required_sources,
        source_reads=source_reads,
        evidence=evidence,
    )
