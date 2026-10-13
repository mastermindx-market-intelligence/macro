"""Canada zero-authority discovery challenger.

This broadens research recall from the existing scored Canada candidate pool
without changing the canonical Branch-B board, rank, entry owner, or publication.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

DEFINITION = "ca_discovery_v1"

ENTRY_OPEN = "ENTRY_OPEN"
WAIT_PULLBACK = "WAIT_PULLBACK"
WAIT_CONFLUENCE = "WAIT_CONFLUENCE"
RAN_DONT_CHASE = "RAN_DONT_CHASE"
BLOCKED = "BLOCKED"
UNAVAILABLE_DATA = "UNAVAILABLE_DATA"

_OPEN = frozenset({"buy_now", "partial"})
_PULLBACK = frozenset({"wait_pullback", "hold"})
_RAN = frozenset({"extended", "topping"})
_BLOCKED = frozenset({"blocked", "avoid", "exit"})
_WAIT = frozenset({"buy_soon", "await_confluence", "watch", "bounce_wait"})


class PopulationStatus(str, Enum):
    """Whether a producer supplied an observation, an honest zero, or no read."""

    OBSERVED = "OBSERVED"
    OBSERVED_ZERO = "OBSERVED_ZERO"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class OfficialScreenMember:
    """One owner-visible Branch-B member, preserving raw listing identity/order."""

    ticker: str
    lane: str
    owner_group: str | None


@dataclass(frozen=True, slots=True)
class OfficialScreenPopulation:
    status: PopulationStatus
    members: tuple[OfficialScreenMember, ...]


@dataclass(frozen=True, slots=True)
class ResearchCandidateEvidence:
    """Primitive pre-alignment evidence only; never rank/publication authority."""

    ticker: str
    aligned: bool
    near: bool
    entry_status: str | None


@dataclass(frozen=True, slots=True)
class ResearchPopulation:
    status: PopulationStatus
    members: tuple[ResearchCandidateEvidence, ...]


@dataclass(frozen=True, slots=True)
class CanadaPopulationContract:
    official_screen: OfficialScreenPopulation
    prealignment_research: ResearchPopulation


class ResearchPopulationUnavailable(RuntimeError):
    """Raised so the shadow receipt records unavailable input, not a valid zero."""


def _raw_ticker(row: Mapping[str, Any], *, population: str) -> str:
    raw = row.get("ticker")
    if raw in (None, ""):
        raise ValueError(f"{population} row is missing raw listing ticker identity")
    return str(raw)


def freeze_official_screen(
    official_board: Mapping[str, Any] | None,
) -> OfficialScreenPopulation:
    """Freeze the producer-owned ``buy`` + ``watch`` roster without research rows."""
    if official_board is None:
        return OfficialScreenPopulation(PopulationStatus.UNAVAILABLE, ())
    if not isinstance(official_board, Mapping):
        raise TypeError("official Canada screen must be a mapping")
    # A valid zero requires both producer lanes to be explicitly computed as empty.
    # A missing/null lane is unavailable evidence, not proof that the lane had zero rows.
    if any(lane not in official_board or official_board.get(lane) is None
           for lane in ("buy", "watch")):
        return OfficialScreenPopulation(PopulationStatus.UNAVAILABLE, ())

    members: list[OfficialScreenMember] = []
    seen: set[str] = set()
    for lane in ("buy", "watch"):
        lane_rows = official_board.get(lane)
        if lane_rows is None:
            lane_rows = ()
        if isinstance(lane_rows, (str, bytes)) or not isinstance(lane_rows, Iterable):
            raise TypeError(f"official Canada {lane} population must be iterable")
        for row in lane_rows:
            if not isinstance(row, Mapping):
                raise ValueError(f"official Canada {lane} row must be a mapping")
            ticker = _raw_ticker(row, population=f"official Canada {lane}")
            if ticker in seen:
                raise ValueError(f"duplicate official Canada identity: {ticker}")
            seen.add(ticker)
            raw_group = row.get("group")
            owner_group = (
                str(raw_group) if raw_group not in (None, "")
                else ("watch" if lane == "watch" else None)
            )
            members.append(OfficialScreenMember(ticker, lane, owner_group))

    status = PopulationStatus.OBSERVED if members else PopulationStatus.OBSERVED_ZERO
    return OfficialScreenPopulation(status, tuple(members))


def freeze_research_population(
    candidates: Iterable[Any] | None,
    align_map: Mapping[str, Mapping[str, Any]] | None,
    entry_signals: Mapping[str, Mapping[str, Any]] | None,
) -> ResearchPopulation:
    """Freeze the complete scored pool while distinguishing missing from valid zero."""
    if candidates is None:
        return ResearchPopulation(PopulationStatus.UNAVAILABLE, ())

    align = align_map or {}
    entries = entry_signals or {}
    members: list[ResearchCandidateEvidence] = []
    seen: set[str] = set()
    for item in candidates:
        row = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else item
        if not isinstance(row, Mapping):
            raise ValueError("pre-alignment research row must be a mapping")
        ticker = _raw_ticker(row, population="pre-alignment research")
        if ticker in seen:
            raise ValueError(f"duplicate pre-alignment research identity: {ticker}")
        seen.add(ticker)
        a = align.get(ticker) or {}
        es = entries.get(ticker) or {}
        status = es.get("status")
        members.append(ResearchCandidateEvidence(
            ticker=ticker,
            aligned=bool(a.get("aligned")),
            near=bool(a.get("near")),
            entry_status=str(status) if status not in (None, "") else None,
        ))

    status = PopulationStatus.OBSERVED if members else PopulationStatus.OBSERVED_ZERO
    return ResearchPopulation(status, tuple(members))


def freeze_population_contract(
    *,
    official_board: Mapping[str, Any] | None,
    candidates: Iterable[Any] | None,
    align_map: Mapping[str, Mapping[str, Any]] | None,
    entry_signals: Mapping[str, Mapping[str, Any]] | None,
) -> CanadaPopulationContract:
    """Keep the public owner roster and broader research pool explicitly separate."""
    official = freeze_official_screen(official_board)
    research = freeze_research_population(candidates, align_map, entry_signals)
    if official.members:
        research_ids = {member.ticker for member in research.members}
        missing = [member.ticker for member in official.members
                   if member.ticker not in research_ids]
        if missing:
            raise ValueError(
                "official Canada identities absent from pre-alignment research: "
                + ", ".join(missing)
            )
    return CanadaPopulationContract(official, research)


def freeze_evidence(
    candidates: Iterable[Any] | None,
    align_map: Mapping[str, Mapping[str, Any]] | None,
    entry_signals: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[tuple[str, bool, bool, str | None], ...]:
    """Backward-compatible primitive tuple projection for older callers."""
    population = freeze_research_population(candidates, align_map, entry_signals)
    return tuple(
        (member.ticker, member.aligned, member.near, member.entry_status)
        for member in population.members
    )


def _availability(
    status: str | None, *, aligned: bool, near: bool,
) -> tuple[str, str]:
    source = f"entry_signal:{status or 'missing'}"
    if status in _OPEN:
        if not aligned and not near:
            return WAIT_CONFLUENCE, f"alignment_blocked+{source}"
        return ENTRY_OPEN, source
    if status in _PULLBACK:
        return WAIT_PULLBACK, source
    if status in _RAN:
        return RAN_DONT_CHASE, source
    if status in _BLOCKED:
        return BLOCKED, source
    if status in _WAIT:
        return WAIT_CONFLUENCE, source
    return UNAVAILABLE_DATA, source


def _source_session(asof: Any) -> str:
    raw = "" if asof is None else str(asof).strip()
    try:
        parsed = date.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "source session must be an explicit YYYY-MM-DD owner date"
        ) from exc
    if parsed.isoformat() != raw:
        raise ValueError("source session must be an explicit YYYY-MM-DD owner date")
    return raw


def build_candidates(
    frozen: ResearchPopulation | Iterable[tuple[str, bool, bool, str | None]],
    asof: str,
) -> list[dict[str, Any]]:
    """Emit the full valid research observation with deterministic availability."""
    session_date = _source_session(asof)
    if isinstance(frozen, ResearchPopulation):
        if frozen.status is PopulationStatus.UNAVAILABLE:
            raise ResearchPopulationUnavailable(
                "pre-alignment research population was not computed"
            )
        members: Iterable[Any] = frozen.members
    else:
        members = frozen

    rows: list[dict[str, Any]] = []
    for member in members:
        if isinstance(member, ResearchCandidateEvidence):
            ticker = member.ticker
            aligned = member.aligned
            near = member.near
            entry_status = member.entry_status
        else:
            ticker, aligned, near, entry_status = member
        origins = ["scored_screen"]
        if aligned:
            origins.append("alignment_aligned")
        elif near:
            origins.append("alignment_near")
        availability, source = _availability(
            entry_status, aligned=aligned, near=near,
        )
        rows.append({
            "session_date": session_date,
            "security_ref_raw": str(ticker),
            "candidate_origin": "+".join(origins),
            "availability_status": availability,
            "availability_source": source,
        })
    return rows
