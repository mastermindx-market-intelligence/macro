"""Mode-bound basket composition read over the Data OS read contract (U04).

One ``ReadRequest`` decides EVERYTHING a basket read touches: the membership
snapshot, the identity resolution and the price read all answer under the SAME
mode and the SAME view contract (D00.D1).  A ``pit=False`` membership answer is
the engine's current-membership fallback applied backward — context and
evidence, never a substitute for a snapshot (D00.D4), and it can never fund a
RECONSTRUCT.  Members are accounted by LISTING id, never by the ticker string a
membership store carries as a storage key (D00.D2), through the C02 coverage
owner: one member, one disposition, the population is the frozen denominator,
and the curated capped population and the raw vendor concept universe are
distinct populations, never accounted or differenced as one.

No production caller yet; names are not re-exported by lib/dataos/__init__.py
(a seat act).
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Callable, Iterable, Mapping
from datetime import date, timedelta
from enum import StrEnum
from types import MappingProxyType

from lib.dataos.read_contract import (
    CoverageResult,
    Disposition,
    MemberDisposition,
    ReadContractError,
    ReadMode,
    ReadRequest,
    ReadResult,
    SourceSegment,
    account_coverage,
)
from lib.dataos.nulls import MissingReason
from lib.dataos.identity import (
    IdentityError,
    listing_id,
    parse_listing_key,
    venue_timezone,
)

__all__ = [
    "PopulationKind", "EvidenceMode", "BasketRefusalCode", "BasketReadRefusal",
    "BasketRead", "read_basket", "population_delta",
]


class PopulationKind(StrEnum):
    """WHICH population a membership answer carries; ``value == name``."""

    CURATED_CAPPED = "CURATED_CAPPED"    # the seeded, capped subset the engine tracks
    VENDOR_UNIVERSE = "VENDOR_UNIVERSE"  # the raw vendor concept dump


class EvidenceMode(StrEnum):
    """How the membership answer was actually sourced; ``value == name``."""

    PIT_SNAPSHOT = "PIT_SNAPSHOT"              # members_asof pit=True, basis "pit_snapshot"
    CURRENT_MEMBERSHIP = "CURRENT_MEMBERSHIP"  # pit=False, current applied backward


class BasketRefusalCode(StrEnum):
    """Closed refusal vocabulary of the composition read; ``value == name``."""

    MODE_UNSUPPORTED = "MODE_UNSUPPORTED"
    MODE_MISMATCH = "MODE_MISMATCH"
    CONTRACT_MISMATCH = "CONTRACT_MISMATCH"
    CUTOFF_MISMATCH = "CUTOFF_MISMATCH"
    ALREADY_ACCOUNTED = "ALREADY_ACCOUNTED"
    PRICES_UNBOUND = "PRICES_UNBOUND"
    DAY_CONFLICT = "DAY_CONFLICT"
    UNKNOWN_SUITE = "UNKNOWN_SUITE"
    MEMBERSHIP_ECHO_MISMATCH = "MEMBERSHIP_ECHO_MISMATCH"
    MALFORMED_MEMBERSHIP = "MALFORMED_MEMBERSHIP"
    UNKNOWN_BASKET = "UNKNOWN_BASKET"
    MEMBERSHIP_UNREADABLE = "MEMBERSHIP_UNREADABLE"
    EMPTY_MEMBERSHIP = "EMPTY_MEMBERSHIP"
    LOOKAHEAD_MEMBERSHIP = "LOOKAHEAD_MEMBERSHIP"
    SNAPSHOT_AFTER_DAY = "SNAPSHOT_AFTER_DAY"
    UNKNOWN_POPULATION = "UNKNOWN_POPULATION"
    POPULATION_KIND_MISMATCH = "POPULATION_KIND_MISMATCH"
    EVIDENCE_MODE_MISMATCH = "EVIDENCE_MODE_MISMATCH"
    BASKET_MISMATCH = "BASKET_MISMATCH"
    MALFORMED_IDENTITY = "MALFORMED_IDENTITY"
    MALFORMED_PRICE_ROW = "MALFORMED_PRICE_ROW"


class BasketReadRefusal(ReadContractError):
    """A lawful-shaped composition the read refuses; ``str()`` leads with the code."""

    def __init__(self, code: BasketRefusalCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


# Pinned to the engine's own literals by tests/test_dataos_basket_read.py.
_BASIS_PIT = "pit_snapshot"
_BASIS_CURRENT = "current_membership"
_BASIS_UNKNOWN = "unknown_basket"
_BASIS_UNREADABLE = "membership_unreadable"
_SHAPE_MEMBERSHIP = "membership"
_SHAPE_CONCEPT_DUMP = "ths_concept_dump"
# A venue-TIMEZONE anchor used only to turn a cutoff instant into a local
# calendar day via identity.venue_timezone; it is not a listing venue and says
# nothing about where a member trades.
_SUITE_TZ_MIC = {"baskets": "XNYS", "baskets_china": "XSHG", "baskets_china_ths": "XSHG"}

_LAWFUL_MEMBERSHIP = {(True, _BASIS_PIT), (False, _BASIS_CURRENT), (False, _BASIS_UNKNOWN),
                      (False, _BASIS_UNREADABLE)}


def _require_text(value: object, what: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReadContractError(f"{what} must be a non-empty string, got {value!r}")


def _names(segments: Iterable[SourceSegment]) -> str:
    return ", ".join(sorted({segment.source for segment in segments}))


def read_basket(
    request: ReadRequest, *, basket_id: str, suite: str, price_read: ReadResult,
    resolve: Callable[[str, date], str | None], expected_population: PopulationKind,
    session_day: date | None = None,
    membership_reader: Callable[..., Mapping[str, object]] | None = None,
    fallback_sources: Iterable[str] = (), prices_dependency: str = "prices",
) -> BasketRead:
    """Compose ONE basket read: membership + identity + prices under ONE request.

    Check order is law: each step refuses before the next runs, so a refused
    read never touches the rows.  Identity/basis drift and undeclared-fallback
    demotion are C02's ``account_coverage`` decisions, never re-implemented here.
    """
    _require_text(basket_id, "basket_id")
    _require_text(suite, "suite")
    if not isinstance(request, ReadRequest):
        raise ReadContractError(
            f"request must be a ReadRequest, got {type(request).__name__}")
    if not isinstance(expected_population, PopulationKind):
        raise ReadContractError(
            f"expected_population must be a PopulationKind, got {expected_population!r}")
    # 1. Mode (D00.D1): a retained output is replayed whole by read_contract.replay;
    # it is never re-composed here.
    if request.mode is ReadMode.REPLAY:
        raise BasketReadRefusal(
            BasketRefusalCode.MODE_UNSUPPORTED,
            "a REPLAY output is replayed whole, never re-composed from parts")
    # 2. The price read must be the ONE made under this very request.
    if not isinstance(price_read, ReadResult):
        raise ReadContractError(
            f"price_read must be a ReadResult, got {type(price_read).__name__}")
    if price_read.mode is not request.mode:
        raise BasketReadRefusal(
            BasketRefusalCode.MODE_MISMATCH,
            f"the price read answered {price_read.mode.value} while the request asks "
            f"{request.mode.value}")
    if price_read.contract != request.contract:
        raise BasketReadRefusal(
            BasketRefusalCode.CONTRACT_MISMATCH,
            "the price read was made under a different view contract")
    if request.mode is ReadMode.RECONSTRUCT:
        if (price_read.evidence.get("cutoff") != request.cutoff.isoformat()
                or price_read.evidence.get("clock") != request.clock.value):
            raise BasketReadRefusal(
                BasketRefusalCode.CUTOFF_MISMATCH,
                "the price read was not made at this request's cutoff and clock")
    if price_read.coverage is not None:
        raise BasketReadRefusal(
            BasketRefusalCode.ALREADY_ACCOUNTED,
            "the price read already carries a coverage account")
    if prices_dependency not in price_read.values:
        raise BasketReadRefusal(
            BasketRefusalCode.PRICES_UNBOUND,
            f"dependency {prices_dependency!r} is not bound in the price read")
    # 3. Day: the one calendar day the membership and identity answers share.
    if suite not in _SUITE_TZ_MIC:
        raise BasketReadRefusal(
            BasketRefusalCode.UNKNOWN_SUITE,
            f"suite {suite!r} has no venue-day anchor; known: {sorted(_SUITE_TZ_MIC)}")
    if request.mode is ReadMode.RECONSTRUCT:
        if session_day is not None:
            raise BasketReadRefusal(
                BasketRefusalCode.DAY_CONFLICT,
                "RECONSTRUCT derives the day from the cutoff; a caller session_day "
                "would let one request answer for two days")
        # The membership store carries no knowledge clock, so a snapshot dated on
        # the cutoff's own local day is not provably known BY the cutoff; the day
        # is therefore the venue-local day BEFORE the cutoff's — a declared
        # conservative convention, not a proof.
        day = (request.cutoff.astimezone(venue_timezone(_SUITE_TZ_MIC[suite])).date()
               - timedelta(days=1))
    else:
        if type(session_day) is not date:
            raise BasketReadRefusal(
                BasketRefusalCode.DAY_CONFLICT,
                "CURRENT needs the session day as a calendar date, got "
                f"{type(session_day).__name__}")
        day = session_day
    # 4. Membership: the store answers FOR this day, and must say so (echo).
    reader = membership_reader if membership_reader is not None else _default_membership_reader
    m = reader(basket_id, day.isoformat(), suite=suite)
    if not isinstance(m, Mapping):
        raise BasketReadRefusal(
            BasketRefusalCode.MALFORMED_MEMBERSHIP,
            f"the membership reader returned {type(m).__name__}, not a mapping")
    if (str(m.get("basket_id")) != basket_id or m.get("suite") != suite
            or m.get("asof") != day.isoformat()):
        raise BasketReadRefusal(
            BasketRefusalCode.MEMBERSHIP_ECHO_MISMATCH,
            "the membership answer does not echo this read's basket, suite and day")
    # 5. Validity: which basis the answer is ON, and which population it carries.
    pit = m.get("pit")
    basis = m.get("basis")
    if not ((pit is True or pit is False) and (pit, basis) in _LAWFUL_MEMBERSHIP):
        raise BasketReadRefusal(
            BasketRefusalCode.MALFORMED_MEMBERSHIP,
            "the (pit, basis) pair is not a lawful membership basis pair")
    if basis == _BASIS_UNREADABLE:
        raise BasketReadRefusal(
            BasketRefusalCode.MEMBERSHIP_UNREADABLE,
            f"the membership store for suite {suite!r} exists but is unreadable; "
            "corruption is refused, never measured as absence or as a current membership")
    if basis == _BASIS_UNKNOWN:
        raise BasketReadRefusal(
            BasketRefusalCode.UNKNOWN_BASKET,
            f"basket {basket_id!r} is unknown to suite {suite!r}")
    members = m.get("members")
    if not isinstance(members, (list, tuple)) or not all(
            isinstance(ticker, str) and ticker.strip() for ticker in members):
        raise BasketReadRefusal(
            BasketRefusalCode.MALFORMED_MEMBERSHIP,
            "members must be a list/tuple of non-empty ticker strings")
    if not members:
        raise BasketReadRefusal(
            BasketRefusalCode.EMPTY_MEMBERSHIP,
            f"basket {basket_id!r} carries no members on {day.isoformat()}")
    if len(set(members)) != len(members):
        raise BasketReadRefusal(
            BasketRefusalCode.MALFORMED_MEMBERSHIP,
            "the membership answer lists a ticker more than once")
    if request.mode is ReadMode.RECONSTRUCT and pit is False:
        raise BasketReadRefusal(
            BasketRefusalCode.LOOKAHEAD_MEMBERSHIP,
            "current membership applied backward is a look-ahead basis (D00.D4); "
            "it can never fund a RECONSTRUCT")
    snapshot_date = m.get("snapshot_date")
    if snapshot_date is not None and str(snapshot_date) > day.isoformat():
        raise BasketReadRefusal(
            BasketRefusalCode.SNAPSHOT_AFTER_DAY,
            f"snapshot {snapshot_date!r} is dated after the membership day "
            f"{day.isoformat()}")
    evidence_mode = (EvidenceMode.PIT_SNAPSHOT if pit is True
                     else EvidenceMode.CURRENT_MEMBERSHIP)
    shape = m.get("source_shape")
    if shape == _SHAPE_MEMBERSHIP:
        kind = PopulationKind.CURATED_CAPPED
    elif shape == _SHAPE_CONCEPT_DUMP:
        kind = PopulationKind.VENDOR_UNIVERSE
    elif shape is None and basis == _BASIS_CURRENT:
        # membership.json is the curated document: a shapeless current answer is it.
        kind = PopulationKind.CURATED_CAPPED
    else:
        raise BasketReadRefusal(
            BasketRefusalCode.UNKNOWN_POPULATION,
            f"source_shape {shape!r} does not name a known population")
    if kind != expected_population:
        raise BasketReadRefusal(
            BasketRefusalCode.POPULATION_KIND_MISMATCH,
            f"the answer carries {kind.value} while this read asked for "
            f"{expected_population.value}")
    # 6. Identity (D00.D2): one listing id per ticker, resolved FOR this day.
    ordered = sorted(members)
    identity: dict[str, str | None] = {}
    for ticker in ordered:
        try:
            resolved = resolve(ticker, day)
        except IdentityError as exc:
            # D00.D2: a resolver that cannot even parse the ticker is a malformed
            # identity, never a quietly unresolved member (U04 repair r1).
            raise BasketReadRefusal(
                BasketRefusalCode.MALFORMED_IDENTITY,
                f"ticker {ticker!r} raised an identity error while resolving on "
                f"{day.isoformat()}: {exc}") from exc
        if resolved is not None:
            try:
                lawful = (isinstance(resolved, str)
                          and listing_id(parse_listing_key(resolved)) == resolved)
            except IdentityError:
                lawful = False
            if not lawful:
                raise BasketReadRefusal(
                    BasketRefusalCode.MALFORMED_IDENTITY,
                    f"ticker {ticker!r} does not resolve to a lawful listing id on "
                    f"{day.isoformat()}")
        identity[ticker] = resolved
    member_keys = tuple(
        identity[ticker] if identity[ticker] is not None else f"unresolved:{ticker}"
        for ticker in ordered)
    # 7. Dispositions: C02's one-member-one-disposition account over the rows.
    declared = frozenset(fallback_sources)
    price_rows = price_read.values[prices_dependency]
    groups: dict[str, list[Mapping[str, object]]] = {}
    for row in price_rows:
        listing = row.get("listing_id")
        if not isinstance(listing, str) or not listing.strip():
            raise BasketReadRefusal(
                BasketRefusalCode.MALFORMED_PRICE_ROW,
                "every price row must carry a non-empty string listing_id")
        groups.setdefault(listing, []).append(row)
    member_key_set = set(member_keys)
    outside = sum(len(group) for key, group in groups.items()
                  if key not in member_key_set)
    dispositions: list[MemberDisposition] = []
    for ticker, key in zip(ordered, member_keys):
        if identity[ticker] is None:
            dispositions.append(MemberDisposition(
                key, Disposition.NEVER_INSPECTED,
                detail=f"ticker {ticker!r} has no listing on {day.isoformat()}"))
            continue
        group = groups.get(key)
        if not group:
            dispositions.append(MemberDisposition(
                key, Disposition.MISSING, missing_reason=MissingReason.NO_COVERAGE,
                detail="no price rows in the bound read"))
            continue
        segments: list[SourceSegment] = []
        seen: set[tuple[str, str]] = set()
        for row in group:
            source = row.get("source")
            row_basis = row.get("basis")
            if (not isinstance(source, str) or not source.strip()
                    or not isinstance(row_basis, str) or not row_basis.strip()):
                raise BasketReadRefusal(
                    BasketRefusalCode.MALFORMED_PRICE_ROW,
                    "a price row must carry non-empty string 'source' and 'basis'")
            if (source, row_basis) not in seen:
                seen.add((source, row_basis))
                segments.append(SourceSegment(
                    source=source, basis=row_basis, listing_id=key))
        fb = [s for s in segments if s.source in declared]
        prim = [s for s in segments if s.source not in declared]
        if not fb:
            dispositions.append(MemberDisposition(
                key, Disposition.SERVED, segments=tuple(prim)))
        elif not prim:
            dispositions.append(MemberDisposition(
                key, Disposition.FALLBACK, segments=tuple(fb),
                detail=(f"declared fallback source(s): {_names(fb)} "
                        "(context only, D00.D4)")))
        else:
            # Only the fallback segments ride a FALLBACK entry: C02 demotes a
            # FALLBACK naming any undeclared source to REFUSED, which would
            # misreport the primary rows as an undeclared fallback.
            dispositions.append(MemberDisposition(
                key, Disposition.FALLBACK, segments=tuple(fb),
                detail=(f"declared fallback source(s): {_names(fb)} spliced with "
                        f"primary source(s): {_names(prim)} (context only, D00.D4)")))
    # 8. Account: the C02 owner builds it and owns every demotion inside it.
    coverage = account_coverage(
        request.contract, member_keys, dispositions, fallback_sources=fallback_sources)
    # 9. Result: the SAME price read, accounted — the input is never mutated.
    note = m.get("note")
    tickers = tuple(ordered)
    block = MappingProxyType({
        "basket_id": basket_id,
        "suite": suite,
        "membership_day": day.isoformat(),
        "snapshot_date": snapshot_date,
        "basis": basis,
        "pit": pit,
        "source_shape": shape,
        "population_kind": kind.value,
        "evidence_mode": evidence_mode.value,
        "note": note if isinstance(note, str) else "",
        "collection_state": m.get("collection_state"),
        "members_sha256": hashlib.sha256("\n".join(tickers).encode("utf-8")).hexdigest(),
        "identity": MappingProxyType(identity),
        "rows_outside_population": outside,
        # The vendor dump's members are point-in-time, but its concept -> basket
        # mapping is today's document — never claim more PIT than that.
        "concept_mapping": ("current" if kind is PopulationKind.VENDOR_UNIVERSE
                            else None),
    })
    result = dataclasses.replace(
        price_read, coverage=coverage,
        evidence={**price_read.evidence, "basket": block})
    return BasketRead(
        result=result, basket_id=basket_id, suite=suite, membership_day=day,
        evidence_mode=evidence_mode, population_kind=kind, tickers=tickers,
        member_keys=member_keys)


@dataclasses.dataclass(frozen=True, slots=True)
class BasketRead:
    """One composed basket read: the accounted price result plus its provenance."""

    result: ReadResult
    basket_id: str
    suite: str
    membership_day: date
    evidence_mode: EvidenceMode
    population_kind: PopulationKind
    tickers: tuple[str, ...]          # sorted
    member_keys: tuple[str, ...]      # same order as tickers

    @property
    def coverage(self) -> CoverageResult:
        return self.result.coverage

    def summary(self) -> dict:
        return {
            **self.coverage.summary(),
            "basket_id": self.basket_id,
            "suite": self.suite,
            "membership_day": self.membership_day.isoformat(),
            "evidence_mode": self.evidence_mode.value,
            "population_kind": self.population_kind.value,
            "label": self.result.label,
        }


def population_delta(a: BasketRead, b: BasketRead) -> dict:
    """Membership churn between two reads of the SAME basket, mode and population.

    A curated read and a vendor-universe read are never differenced: the
    seeding cap is not churn.
    """
    if (a.basket_id, a.suite) != (b.basket_id, b.suite):
        raise BasketReadRefusal(
            BasketRefusalCode.BASKET_MISMATCH,
            "population delta compares two reads of the same basket and suite")
    if a.result.mode is not b.result.mode:
        raise BasketReadRefusal(
            BasketRefusalCode.MODE_MISMATCH,
            "population delta compares two reads made under the same mode")
    if a.population_kind != b.population_kind:
        raise BasketReadRefusal(
            BasketRefusalCode.POPULATION_KIND_MISMATCH,
            "a curated population and a vendor universe are never differenced")
    if a.evidence_mode != b.evidence_mode:
        raise BasketReadRefusal(
            BasketRefusalCode.EVIDENCE_MODE_MISMATCH,
            "population delta compares two reads on the same membership basis")
    return {
        "from_day": a.membership_day.isoformat(),
        "to_day": b.membership_day.isoformat(),
        "added": tuple(sorted(set(b.tickers) - set(a.tickers))),
        "removed": tuple(sorted(set(a.tickers) - set(b.tickers))),
    }


def _default_membership_reader(basket_id: str, day_iso: str, *,
                               suite: str) -> Mapping[str, object]:
    # Lazy import: pandas (and the whole engine graph) never loads at lib.dataos
    # import time.
    from engine import basket_membership_pit
    return basket_membership_pit.members_asof(basket_id, day_iso, suite=suite)
