"""Split-adjusted price views over exact action revisions (Data OS §D4, D00.D3).

THE CONTRACT (D00.D3, frozen).  For a raw printed price series and a *qualified*
corporate-action revision set::

    P_sadj(t) = P_raw(t) / S(t)
    S(t)      = prod r_e   over CONFIRMED split events e with ex_date > t
               in the eligible revision set, capped at the share basis of `as_at`

``r_e`` is an EXACT rational: a 2:1 forward split is ``Fraction(2, 1)``; a 1:10
reverse split is ``Fraction(1, 10)``.  A split changes the price/share unit, not
holding wealth, which is why volume transforms the OTHER way,
``vol_sadj = vol_raw * S(t)`` (V01/V02/V03), and why a common scalar on both
endpoints of a return cancels (V04) while differing scalars do not (V05).

WHY REVISIONS ARE FIRST-CLASS (D00.D1, D00.D5).  An adjusted price is a
point-in-time quantity: the same event, corrected next week, rescales history
differently.  A view therefore never sees "the events"; it sees an
:class:`ActionRevisionSet` *resolved at an `as_at` instant*, so a later
correction can never rewrite what an earlier as-of view saw (P02.01/P02.02).
The original observations stay recorded untouched (:meth:`ActionRevisionSet.history`)
— an event is always recordable intact; the *value* refusals (unconfirmed,
unsupported family, unknown/invalid ratio, cash-basis mismatch) fire only when
the event is eligible AND inside the view window, never at recording time.

WHAT THIS MODULE NEVER DOES.  It never adjusts twice: an ``*_sadj``/``*_tradj``
or ambiguous column in the input is a typed refusal, not a silent division
(``DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`` is the standing precedent that an adjusted
tape quietly answering a raw-price question is a stop-ship event).  It never
invents an event: rights issues, spin-offs, mergers, return-of-capital
specials, stock dividends and scrip are ``UNSUPPORTED_ACTION``, never coerced
into a phantom split ratio.  Cash dividends are CARRIED (O2-P04 builds the
total-return view on this same event model) but contribute nothing to SADJ
prices or volume (P03.03).  TRADJ is a vendor proxy and never an input here.

EXACTNESS.  No ``float`` arithmetic exists anywhere in this module: inputs are
coerced once (int / ``Fraction`` / ``Decimal`` / rational string -> ``Fraction``;
float or bool -> ``NON_EXACT_INPUT``) and every numeric output is a
``Fraction``.  STDLIB ONLY.

Lane O2-P02, programme DATA-OS-COMPLETION, base D00 (2026-10-13).
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Mapping

from lib.dataos import read_contract
from lib.dataos.price import (
    AdjustmentBasis,
    PriceError,
    PriceField,
    is_ambiguous,
    parse_column,
)
from lib.dataos.read_contract import (
    Dependency,
    ReadMode,
    ReadRequest,
    ReadResult,
    RetainedOutput,
)
from lib.dataos.registry import ActionInputStatus, Registry, qualify_action_input
from lib.dataos.temporal import utc
from lib.dataos.identity import IdentityError, parse_listing_key, venue_currency, venue_timezone

__all__ = [
    "ActionFamily",
    "RefusalReason",
    "ViewRefusal",
    "CONFIRMED",
    "SUPPORTED_FAMILIES",
    "UNSUPPORTED_FAMILIES",
    "CASH_BASES",
    "ActionEvent",
    "ActionRevisionSet",
    "AdjustmentReference",
    "PriceView",
    "split_factor",
    "adjust_quantity",
    "return_vector",
    "qualified_return",
    "raw_view",
    "sadj_view",
    # ── house TOTAL_RETURN (lane O2-P04, D00.D3) ──
    "ReinvestPolicy",
    "TotalReturnPolicy",
    "TotalReturnView",
    "total_return_view",
    # ── correction-aware retained views + the qualify-first gate (O3-P05) ──
    "ViewVintage",
    "RetainedView",
    "ReopenedView",
    "ComposedView",
    "admit_action_input",
    "admit_revision_set",
    "retain_view",
    "reopen_view",
    "reconstruct_price_view",
    "simple_returns",
    "view_label",
    "view_receipt_sha256",
]

#: The only P01 qualification string that may enter a split factor (D00.D3).
CONFIRMED = "CONFIRMED"

#: Allowed values of :attr:`ActionEvent.cash_basis` (D00.D3: original cash,
#: current-share adjusted cash and a price factor are three distinct facts).
CASH_BASES: frozenset[str] = frozenset({"as_declared", "current_share_adjusted"})


class ActionFamily(StrEnum):
    """Corporate-action families (D00.D3 v1).  Any other string -> ValueError.

    SUPPORTED (may enter a SADJ factor): ``forward_split`` (ratio > 1),
    ``reverse_split`` (0 < ratio < 1), ``cash_dividend`` (carried for O2-P04's
    total-return view; never touches SADJ prices or volume).

    KNOWN-UNSUPPORTED (typed refusal ``UNSUPPORTED_ACTION``, never coerced):
    everything else below.  An action inferred solely from a price
    discontinuity is never admitted here at all (P01.02) — the only admitted
    source of events is a qualified original observation with its receipt.
    """

    FORWARD_SPLIT = "forward_split"
    REVERSE_SPLIT = "reverse_split"
    CASH_DIVIDEND = "cash_dividend"

    RIGHTS_ISSUE = "rights_issue"
    SPIN_OFF = "spin_off"
    MERGER = "merger"
    RETURN_OF_CAPITAL = "return_of_capital"
    STOCK_DIVIDEND = "stock_dividend"
    SCRIP = "scrip"

    @property
    def supported(self) -> bool:
        return self in SUPPORTED_FAMILIES


SUPPORTED_FAMILIES: frozenset[ActionFamily] = frozenset(
    {
        ActionFamily.FORWARD_SPLIT,
        ActionFamily.REVERSE_SPLIT,
        ActionFamily.CASH_DIVIDEND,
    }
)
UNSUPPORTED_FAMILIES: frozenset[ActionFamily] = frozenset(
    {
        ActionFamily.RIGHTS_ISSUE,
        ActionFamily.SPIN_OFF,
        ActionFamily.MERGER,
        ActionFamily.RETURN_OF_CAPITAL,
        ActionFamily.STOCK_DIVIDEND,
        ActionFamily.SCRIP,
    }
)


class RefusalReason(StrEnum):
    """The typed reasons a price view refuses instead of answering (D00.D3/D4).

    A refusal names the exact defect; it never silently drops a member or
    substitutes a fallback (D00.D4).  ``UNKNOWN_WITHHOLDING`` / ``UNKNOWN_FX`` /
    ``UNKNOWN_REINVESTMENT`` are added by lane O2-P04's total-return view.
    ``DUPLICATE_EVENT_ID`` / ``ROW_AFTER_AS_AT`` / ``NON_POSITIVE_VALUE`` were
    added by the R02 heal.
    ``DUPLICATE_ROW_DATE`` was added by the R02 heal of the total-return view.
    ``VENUE_CLOCK_UNKNOWN`` (D00.A1.1: the as_at day is the listing venue's
    calendar day, so an unmapped or contradictory MIC is never fallen back to
    UTC), ``CURRENCY_MISMATCH`` (D00.A1.2: a known-and-different currency
    refuses rather than assuming FX) and ``SCHEMA_MISMATCH`` (a retained
    payload that does not declare the current retained-view schema) were added
    by lane P06.
    """

    UNSUPPORTED_ACTION = "unsupported_action"
    INVALID_RATIO = "invalid_ratio"
    UNKNOWN_RATIO = "unknown_ratio"
    NOT_CONFIRMED = "not_confirmed"
    AMBIGUOUS_BASIS = "ambiguous_basis"
    MIXED_OHLC_BASIS = "mixed_ohlc_basis"
    DOUBLE_ADJUST_RISK = "double_adjust_risk"
    RETURN_ACROSS_UNADJUSTED_SPLIT = "return_across_unadjusted_split"
    NON_EXACT_INPUT = "non_exact_input"
    NON_RAW_INPUT = "non_raw_input"
    UNSUPPORTED_QUANTITY_CONVENTION = "unsupported_quantity_convention"
    NO_ELIGIBLE_REVISION = "no_eligible_revision"
    AMBIGUOUS_REVISION = "ambiguous_revision"
    DUPLICATE_EVENT_ID = "duplicate_event_id"
    ROW_AFTER_AS_AT = "row_after_as_at"
    NON_POSITIVE_VALUE = "non_positive_value"
    NAIVE_TIMESTAMP = "naive_timestamp"
    CASH_BASIS_MISMATCH = "cash_basis_mismatch"
    UNKNOWN_ORDERING = "unknown_ordering"
    NOT_EXECUTABLE_BASIS = "not_executable_basis"
    # ── added by lane O2-P04's total-return view (D00.D3 house TOTAL_RETURN row) ──
    UNKNOWN_WITHHOLDING = "unknown_withholding"
    UNKNOWN_FX = "unknown_fx"
    UNKNOWN_REINVESTMENT = "unknown_reinvestment"
    MISSING_PRICE = "missing_price"
    # ── added by the R02 heal of the total-return view (m5) ──
    DUPLICATE_ROW_DATE = "duplicate_row_date"
    # ── added by lane O3-P05's retained views (D00.D5: one generation, one receipt) ──
    MIXED_GENERATION = "mixed_generation"
    RECEIPT_MISMATCH = "receipt_mismatch"
    UNBOUND_GENERATION = "unbound_generation"
    # ── added by lane P06: venue-local as_at day + declared listing currency (D00.A1) ──
    VENUE_CLOCK_UNKNOWN = "venue_clock_unknown"
    CURRENCY_MISMATCH = "currency_mismatch"
    SCHEMA_MISMATCH = "schema_mismatch"


class ViewRefusal(PriceError):
    """A typed refusal from a price view: `.reason` plus the offending id/column.

    Subclasses :class:`lib.dataos.price.PriceError` so every existing consumer
    that already catches a bad price column catches these too.
    """

    def __init__(
        self,
        message: str,
        *,
        reason: RefusalReason,
        event_id: str | None = None,
        column: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.event_id = event_id
        self.column = column


# ── exact input coercion ─────────────────────────────────────────────────────

def _exact_fraction(value, *, what: str, column: str | None = None) -> Fraction:
    """int | Fraction | Decimal | rational str -> Fraction; anything else refuses.

    ``bool`` is refused before ``int`` (bool subclasses int) and a float is
    refused by falling through to the final branch — no float is ever converted,
    so no inexact value can enter a factor (NON_EXACT_INPUT).
    """
    if isinstance(value, bool):
        raise ViewRefusal(
            f"{what} must be an exact rational, got bool {value!r}",
            reason=RefusalReason.NON_EXACT_INPUT,
            column=column,
        )
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        return Fraction(value)
    if isinstance(value, str):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise ViewRefusal(
                f"{what} {value!r} is not an exact rational string",
                reason=RefusalReason.NON_EXACT_INPUT,
                column=column,
            ) from exc
    raise ViewRefusal(
        f"{what} must be int/Fraction/Decimal/rational string, "
        f"got {type(value).__name__} {value!r}",
        reason=RefusalReason.NON_EXACT_INPUT,
        column=column,
    )


def _require_aware(value: datetime, *, what: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{what} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ViewRefusal(
            f"{what} must be timezone-aware (a naive timestamp cannot order "
            f"revisions); got {value!r}",
            reason=RefusalReason.NAIVE_TIMESTAMP,
        )
    return value


def _require_date(value, *, what: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{what} must be a datetime.date, got {type(value).__name__}")
    return value


# ── the event model ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ActionEvent:
    """One recorded corporate-action observation, never mutated after the fact.

    Construction validates TYPES (and coerces exact rationals) only, so an
    original observation can always be recorded intact — a ``SUSPECTED``
    qualification, an unknown ratio (``None``) or an unsupported family records
    fine.  The VALUE refusals (NOT_CONFIRMED / UNSUPPORTED_ACTION /
    UNKNOWN_RATIO / INVALID_RATIO / CASH_BASIS_MISMATCH) are raised by the
    views, and only when this event is eligible and inside the window.

    ``source_receipt`` is the original observation receipt (P01/D00.D5): the
    event is source-linked forever, whatever later revisions say about it.
    """

    event_id: str
    family: ActionFamily
    ex_date: date
    known_at: datetime
    source_receipt: str
    qualification: str
    ratio: Fraction | None = None
    cash_per_share: Fraction | None = None
    cash_basis: str | None = None
    currency: str | None = None
    supersedes: str | None = None
    cancelled: bool = False
    sequence: int | None = None

    def __post_init__(self) -> None:
        for name, value in (("event_id", self.event_id), ("source_receipt", self.source_receipt)):
            if not isinstance(value, str) or not value:
                raise TypeError(f"{name} must be a non-empty string, got {value!r}")
        if not isinstance(self.family, ActionFamily):
            if not isinstance(self.family, str):
                raise TypeError(
                    f"family must be an ActionFamily, got {type(self.family).__name__}"
                )
            # Unknown family strings ValueError here, at construction (D00.D3).
            object.__setattr__(self, "family", ActionFamily(self.family))
        _require_date(self.ex_date, what=f"{self.event_id}.ex_date")
        _require_aware(self.known_at, what=f"{self.event_id}.known_at")
        if not isinstance(self.qualification, str):
            raise TypeError(
                f"qualification must be the P01 status string, got {type(self.qualification).__name__}"
            )
        for name in ("ratio", "cash_per_share"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _exact_fraction(value, what=f"{self.event_id}.{name}"),
                )
        if self.cash_basis is not None:
            if not isinstance(self.cash_basis, str) or self.cash_basis not in CASH_BASES:
                raise ValueError(
                    f"cash_basis must be one of {sorted(CASH_BASES)} or None, got {self.cash_basis!r}"
                )
        if self.currency is not None and not isinstance(self.currency, str):
            raise TypeError(
                f"currency must be a str or None, got {type(self.currency).__name__}"
            )
        if self.supersedes is not None and (
            not isinstance(self.supersedes, str) or not self.supersedes
        ):
            raise TypeError(f"supersedes must be a non-empty str or None, got {self.supersedes!r}")
        if not isinstance(self.cancelled, bool):
            raise TypeError(f"cancelled must be a bool, got {self.cancelled!r}")
        if self.sequence is not None and (
            isinstance(self.sequence, bool) or not isinstance(self.sequence, int)
        ):
            raise TypeError(f"sequence must be an int or None, got {self.sequence!r}")


@dataclass(frozen=True)
class ActionRevisionSet:
    """An immutable set of action records with as-of resolution (D00.D1/D00.D5).

    ``resolve(as_at)`` answers "which events does a view at `as_at` see":
    records known by `as_at`, supersede chains resolved, ordered by
    ``(ex_date, sequence)``.  ``history(event_id)`` returns the full untouched
    chain — the set never rewrites a recorded observation (P02.01).
    """

    revision_set_id: str
    events: tuple[ActionEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.revision_set_id, str) or not self.revision_set_id:
            raise TypeError(
                f"revision_set_id must be a non-empty string, got {self.revision_set_id!r}"
            )
        if not isinstance(self.events, tuple):
            object.__setattr__(self, "events", tuple(self.events))
        for event in self.events:
            if not isinstance(event, ActionEvent):
                raise TypeError(
                    f"events must be ActionEvent records, got {type(event).__name__}"
                )

    def resolve(self, as_at: datetime) -> tuple[ActionEvent, ...]:
        """The active events a view at ``as_at`` sees, (ex_date, sequence)-ordered.

        A record with ``supersedes=X`` replaces X; ``cancelled=True`` removes X
        (and the tombstone itself never acts as an event).  Two eligible
        records superseding the same id -> AMBIGUOUS_REVISION; ``supersedes``
        naming an id absent from the set -> NO_ELIGIBLE_REVISION.  Two visible
        records sharing one ``event_id`` -> DUPLICATE_EVENT_ID.  Records with
        ``known_at > as_at`` are invisible to this resolution (a later
        correction can never rewrite an earlier as-of view).
        """
        _require_aware(as_at, what="as_at")
        all_ids = {event.event_id for event in self.events}
        eligible = [event for event in self.events if event.known_at <= as_at]
        seen_ids: set[str] = set()
        for event in eligible:
            if event.event_id in seen_ids:
                raise ViewRefusal(
                    f"event_id {event.event_id!r} appears more than once among the "
                    f"revisions visible at {as_at.isoformat()} in revision set "
                    f"{self.revision_set_id!r}; an event id names exactly one record — "
                    f"a correction is a NEW record with supersedes=<old id> (D00.D5)",
                    reason=RefusalReason.DUPLICATE_EVENT_ID,
                    event_id=event.event_id,
                )
            seen_ids.add(event.event_id)
        superseding: dict[str, list[ActionEvent]] = {}
        for event in eligible:
            if event.supersedes is None:
                continue
            if event.supersedes not in all_ids:
                raise ViewRefusal(
                    f"revision {event.event_id!r} supersedes {event.supersedes!r}, "
                    f"which is absent from revision set {self.revision_set_id!r}",
                    reason=RefusalReason.NO_ELIGIBLE_REVISION,
                    event_id=event.event_id,
                )
            superseding.setdefault(event.supersedes, []).append(event)
        for target, records in superseding.items():
            if len(records) > 1:
                raise ViewRefusal(
                    f"two eligible revisions ({records[0].event_id!r}, "
                    f"{records[1].event_id!r}) supersede {target!r} in revision "
                    f"set {self.revision_set_id!r}",
                    reason=RefusalReason.AMBIGUOUS_REVISION,
                    event_id=target,
                )
        replaced = set(superseding)
        active = [
            event
            for event in eligible
            if event.event_id not in replaced and not event.cancelled
        ]
        # (ex_date, sequence); an unset sequence sorts before set ones so the
        # key is total even on same-day events recorded without sequences.
        active.sort(
            key=lambda e: (
                e.ex_date,
                e.sequence is not None,
                e.sequence if e.sequence is not None else 0,
            )
        )
        return tuple(active)

    def history(self, event_id: str) -> tuple[ActionEvent, ...]:
        """The full untouched supersede chain of ``event_id``, earliest-known first."""
        chain = {event_id}
        current = event_id
        by_id = {event.event_id: event for event in self.events}
        while True:
            record = by_id.get(current)
            if record is None or record.supersedes is None:
                break
            if record.supersedes in chain:
                break
            chain.add(record.supersedes)
            current = record.supersedes
        changed = True
        while changed:
            changed = False
            for event in self.events:
                if event.supersedes in chain and event.event_id not in chain:
                    chain.add(event.event_id)
                    changed = True
        return tuple(
            sorted(
                (event for event in self.events if event.event_id in chain),
                key=lambda e: e.known_at,
            )
        )


# ── the factor and quantity math ─────────────────────────────────────────────

def _check_window_event(event: ActionEvent) -> Fraction | None:
    """Value refusals for an eligible in-window event; its factor, or None.

    Only called for events already resolved as active at `as_at` and inside the
    view window.  Order: family -> qualification -> split ratio validity ->
    cash-basis mismatch (the order the D00.D3 refusal rows are written in).
    """
    if not event.family.supported:
        raise ViewRefusal(
            f"event {event.event_id!r} family {event.family.value!r} is "
            f"UNSUPPORTED and is never coerced into a split factor",
            reason=RefusalReason.UNSUPPORTED_ACTION,
            event_id=event.event_id,
        )
    if event.qualification != CONFIRMED:
        raise ViewRefusal(
            f"event {event.event_id!r} qualification {event.qualification!r} may "
            f"not enter a factor (only {CONFIRMED!r} may)",
            reason=RefusalReason.NOT_CONFIRMED,
            event_id=event.event_id,
        )
    if event.family is ActionFamily.CASH_DIVIDEND:
        if event.ratio is not None:
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} carries a split ratio — a "
                f"cash event and a share-count event are distinct facts",
                reason=RefusalReason.CASH_BASIS_MISMATCH,
                event_id=event.event_id,
            )
        return None  # carried for O2-P04; contributes nothing to SADJ (P03.03)
    if event.ratio is None:
        raise ViewRefusal(
            f"split event {event.event_id!r} has no ratio (unknown ratio is "
            f"never guessed from a price discontinuity)",
            reason=RefusalReason.UNKNOWN_RATIO,
            event_id=event.event_id,
        )
    if event.ratio <= 0:
        raise ViewRefusal(
            f"split event {event.event_id!r} ratio {event.ratio} must be positive",
            reason=RefusalReason.INVALID_RATIO,
            event_id=event.event_id,
        )
    if event.family is ActionFamily.FORWARD_SPLIT and event.ratio <= 1:
        raise ViewRefusal(
            f"forward split {event.event_id!r} ratio {event.ratio} must exceed 1",
            reason=RefusalReason.INVALID_RATIO,
            event_id=event.event_id,
        )
    if event.family is ActionFamily.REVERSE_SPLIT and event.ratio >= 1:
        raise ViewRefusal(
            f"reverse split {event.event_id!r} ratio {event.ratio} must be below 1",
            reason=RefusalReason.INVALID_RATIO,
            event_id=event.event_id,
        )
    if event.cash_per_share is not None:
        raise ViewRefusal(
            f"split event {event.event_id!r} carries cash_per_share — a split "
            f"and a cash distribution are distinct facts",
            reason=RefusalReason.CASH_BASIS_MISMATCH,
            event_id=event.event_id,
        )
    return event.ratio


# ── the venue clock and the declared currency (D00.A1.1 / D00.A1.2, P06) ──────

def _venue_zone(mic):
    try:
        return venue_timezone(mic)
    except IdentityError as exc:
        raise ViewRefusal(f"no venue clock for MIC {mic!r} — the as_at day is never taken from UTC (D00.A1.1)",
                          reason=RefusalReason.VENUE_CLOCK_UNKNOWN) from exc

def _venue_day(as_at: datetime, mic) -> date:
    return as_at.astimezone(_venue_zone(mic)).date()

def _venue_currency(mic) -> str:
    try:
        return venue_currency(mic)
    except IdentityError as exc:
        raise ViewRefusal(f"no declared currency for MIC {mic!r} (D00.A1.2)",
                          reason=RefusalReason.VENUE_CLOCK_UNKNOWN) from exc

def _check_row_currency(rows, expected: str) -> None:
    # A1.2: an optional `currency` column, when present, must equal the declared currency row by row.
    for row in rows:
        if "currency" not in row:
            continue
        value = row["currency"]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ViewRefusal("row currency is empty — the view never assumes a currency",
                              reason=RefusalReason.UNKNOWN_FX, column="currency")
        if not isinstance(value, str):
            raise TypeError(f"row currency must be a str, got {type(value).__name__}")
        if _norm_currency(value) != expected:
            raise ViewRefusal(f"row currency {value!r} is not the listing's {expected!r} — no FX is applied",
                              reason=RefusalReason.CURRENCY_MISMATCH, column="currency")


def split_factor(t: date, revisions: ActionRevisionSet, as_at: datetime, *, mic: str) -> Fraction:
    """``S(t)`` — the exact cumulative split divisor at row date ``t`` (D00.D3).

    Product of ``r_e`` over CONFIRMED split events active at ``as_at`` with
    ``t < ex_date <= as_at_day`` (the listing venue's calendar day of ``as_at``,
    D00.A1.1 — never the UTC date).  The boundary is half-open on the left:
    a row dated ``ex_date - 1 day`` is divided by ``r``; a row dated ``ex_date``
    is not (the exchange already printed the new unit that session).  Events
    with ``ex_date > as_at_day`` are not yet effective — the view's share basis is
    the one at ``as_at``, so a future split never rescales the past.

    Cash dividends contribute nothing.  Any eligible in-window event that is
    unsupported, unconfirmed, or carries an invalid/unknown/mismatched value
    raises :class:`ViewRefusal` — never a silent skip.  ``mic`` (keyword-only,
    required) names the listing venue: a MIC with no venue clock refuses
    ``VENUE_CLOCK_UNKNOWN`` rather than falling back to UTC.
    """
    _require_date(t, what="t")
    _require_aware(as_at, what="as_at")
    if not isinstance(revisions, ActionRevisionSet):
        raise TypeError(
            f"revisions must be an ActionRevisionSet, got {type(revisions).__name__}"
        )
    as_at_day = _venue_day(as_at, mic)
    factor = Fraction(1)
    for event in revisions.resolve(as_at):
        if not (t < event.ex_date <= as_at_day):
            continue
        contribution = _check_window_event(event)
        if contribution is not None:
            factor *= contribution
    return factor


def adjust_quantity(q, factor, convention: str = "shares") -> Fraction:
    """``q * factor`` under the declared volume convention (``vol_sadj``, V03).

    Any convention other than ``"shares"`` is refused
    (UNSUPPORTED_QUANTITY_CONVENTION) rather than guessed.
    """
    if convention != "shares":
        raise ViewRefusal(
            f"quantity convention {convention!r} is unsupported (only 'shares'); "
            f"guessing a lot/round-lot multiplier would misstate volume",
            reason=RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION,
        )
    q = _exact_fraction(q, what="quantity q")
    factor = _exact_fraction(factor, what="factor")
    return q * factor


def return_vector(p0, p1, k0, k1) -> dict:
    """The pure oracle: the same return with and without rebasing (V04/V05).

    ``original = p1/p0 - 1`` (both endpoints in one unit) and
    ``rebased = p1*k1/(p0*k0) - 1`` (each endpoint in its own share unit).
    ``equal`` states whether the two agree — a scalar common to both endpoints
    cancels; a scalar on one endpoint does not.  It refuses non-exact inputs
    and a non-positive p0 / k0 / k1 (a return from a zero or negative price or
    share unit is undefined); p1 = 0 is a total loss, not a refusal.
    """
    p0 = _exact_fraction(p0, what="p0")
    p1 = _exact_fraction(p1, what="p1")
    k0 = _exact_fraction(k0, what="k0")
    k1 = _exact_fraction(k1, what="k1")
    if p0 <= 0 or k0 <= 0 or k1 <= 0:
        raise ViewRefusal(
            f"p0, k0 and k1 must be positive (p0={p0}, k0={k0}, k1={k1})",
            reason=RefusalReason.NON_POSITIVE_VALUE,
        )
    original = p1 / p0 - 1
    rebased = p1 * k1 / (p0 * k0) - 1
    return {"original": original, "rebased": rebased, "equal": original == rebased}


def qualified_return(p0, p1, k0, k1) -> Fraction:
    """The executable claim: a return only when no split crosses the interval.

    Returns ``p1/p0 - 1`` only when ``k0 == k1``; otherwise the two endpoints
    are in different share units and the printed-price return is not a return
    at all (RETURN_ACROSS_UNADJUSTED_SPLIT, V05).
    """
    k0 = _exact_fraction(k0, what="k0")
    k1 = _exact_fraction(k1, what="k1")
    if k0 <= 0 or k1 <= 0:
        raise ViewRefusal(
            f"share unit must be positive (k0={k0}, k1={k1})",
            reason=RefusalReason.NON_POSITIVE_VALUE,
        )
    if k0 != k1:
        raise ViewRefusal(
            f"a split crosses the return interval (k0={k0} != k1={k1}); the "
            f"raw-price return is not a return — rebase first or refuse",
            reason=RefusalReason.RETURN_ACROSS_UNADJUSTED_SPLIT,
        )
    p0 = _exact_fraction(p0, what="p0")
    p1 = _exact_fraction(p1, what="p1")
    if p0 <= 0:
        raise ViewRefusal(
            f"start price must be positive (p0={p0}); a return from a zero or "
            f"negative price is undefined",
            reason=RefusalReason.NON_POSITIVE_VALUE,
        )
    return p1 / p0 - 1


# ── views ────────────────────────────────────────────────────────────────────

def _normalize_basis(basis) -> str:
    """Uppercase D00 basis vocabulary (``"raw"``/``AdjustmentBasis.RAW`` -> ``"RAW"``)."""
    if isinstance(basis, AdjustmentBasis):
        return basis.value.upper()
    if isinstance(basis, str):
        return basis.strip().upper()
    raise TypeError(f"basis must be a str or AdjustmentBasis, got {type(basis).__name__}")


@dataclass(frozen=True)
class AdjustmentReference:
    """What a view's numbers are relative to (D00.01 ``adjustment_reference``)."""

    basis: str
    action_revision_set_id: str | None
    as_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "basis", _normalize_basis(self.basis))
        for name in ("action_revision_set_id", "as_at"):
            value = getattr(self, name)
            if value is not None and not isinstance(
                value, str if name == "action_revision_set_id" else datetime
            ):
                raise TypeError(f"{name} must be {'a str' if name == 'action_revision_set_id' else 'a datetime'} or None")


@dataclass(frozen=True)
class PriceView:
    """A labelled, source-linked price view (D00.D1/D00.01).

    ``executable`` is True only for RAW (D00.D3: only a printed price may be
    executed; an adjusted level is a level nobody ever traded at).  ``currency``
    (P06, D00.A1.2) is the listing's declared currency when the view resolved
    it from the venue, and ``None`` when no venue was consulted (a mic-less
    RAW view) — never a guessed or FX-converted code.
    """

    basis: str
    rows: tuple[Mapping, ...]
    reference: AdjustmentReference
    executable: bool
    currency: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "basis", _normalize_basis(self.basis))
        if not isinstance(self.rows, tuple):
            object.__setattr__(self, "rows", tuple(self.rows))
        if not isinstance(self.reference, AdjustmentReference):
            raise TypeError(
                f"reference must be an AdjustmentReference, got {type(self.reference).__name__}"
            )
        if self.executable and self.basis != "RAW":
            raise ViewRefusal(
                f"basis {self.basis!r} is not executable — only RAW is a printed "
                f"price; an adjusted level is a level nobody traded",
                reason=RefusalReason.NOT_EXECUTABLE_BASIS,
            )
        if self.currency is not None and not isinstance(self.currency, str):
            raise TypeError(
                f"currency must be a str or None, got {type(self.currency).__name__}"
            )
        if isinstance(self.currency, str):
            object.__setattr__(self, "currency", _norm_currency(self.currency))


def _price_columns(row: Mapping) -> list[tuple[str, PriceField, AdjustmentBasis]]:
    """Canonical price columns of one row, checking the naming law as we go.

    A price column is a key that parses as ``{field}_{basis}``, OR a key the
    naming law already condemns (``is_ambiguous``, and — extended here on the
    same principle — a bare ``PriceField`` name like ``"open"``): a name that
    names a price without naming its basis is an unlabelled unit and refuses
    AMBIGUOUS_BASIS.  Everything else (``date``, ``volume_raw``, ...) is not a
    price column and passes through.  An unparseable key that still looks like
    a price (``adjusted_close``, ``Adj Close``) refuses AMBIGUOUS_BASIS; an
    unparseable key carrying a non-price token (``volume``, ``time``, ``date``,
    ``interest`` …) is not a price column and passes through.
    """
    columns: list[tuple[str, PriceField, AdjustmentBasis]] = []
    for key in row:
        if not isinstance(key, str):
            continue
        if is_ambiguous(key) or key.strip().lower() in _BARE_FIELD_NAMES:
            raise ViewRefusal(
                f"price column {key!r} does not declare its adjustment basis — "
                f"an unlabelled unit (§D4 naming law)",
                reason=RefusalReason.AMBIGUOUS_BASIS,
                column=key,
            )
        try:
            field, basis = parse_column(key)
        except PriceError:
            if _looks_price_like(key):
                raise ViewRefusal(
                    f"unrecognised price-like column {key!r} — a price that does not "
                    f"parse as {{field}}_{{raw|sadj|tradj}} is an unlabelled unit "
                    f"(the D00.D4 naming law)",
                    reason=RefusalReason.AMBIGUOUS_BASIS,
                    column=key,
                ) from None
            continue  # not a price column (e.g. volume_raw, close_time)
        columns.append((key, field, basis))
    return columns


#: Bare price-field names ("open", "high", ...) are unlabelled units exactly like
#: the AMBIGUOUS_NAMES set; refused as AMBIGUOUS_BASIS rather than passed through.
_BARE_FIELD_NAMES: frozenset[str] = frozenset(member.value for member in PriceField)

#: Tokens that make an unparseable column name LOOK like a price (refuse it)
#: and tokens that mark it as plainly not a price (let it pass through).
_PRICE_LIKE_TOKENS: frozenset[str] = frozenset(m.value for m in PriceField) | frozenset(
    {"adj", "adjusted", "adjclose", "price", "px"}
)
_NON_PRICE_TOKENS: frozenset[str] = frozenset(
    {"volume", "size", "interest", "count", "qty", "quantity", "shares",
     "time", "timestamp", "date", "datetime", "updated", "ts"}
)


def _looks_price_like(key: str) -> bool:
    """True when an unparseable column name still names a price (m1)."""
    if not isinstance(key, str):
        return False
    tokens = [t for t in re.split(r"[^a-z0-9]+", key.strip().lower()) if t]
    if not tokens or any(t in _NON_PRICE_TOKENS for t in tokens):
        return False
    compact = "".join(tokens)
    return any(t in _PRICE_LIKE_TOKENS for t in tokens) or "close" in compact or "price" in compact


def _validate_price_columns(rows: tuple[Mapping, ...]) -> list[list[tuple[str, PriceField, AdjustmentBasis]]]:
    """The shared column law for every view, in the frozen order:

    1. an unsuffixed/ambiguous price column -> AMBIGUOUS_BASIS;
    2. more than one basis among price columns (within a row or across rows)
       -> MIXED_OHLC_BASIS;
    3. any ``*_sadj`` -> DOUBLE_ADJUST_RISK (adjusting an adjusted input);
    4. any ``*_tradj`` -> NON_RAW_INPUT (a vendor proxy, never an input here).
    """
    per_row = [_price_columns(row) for row in rows]
    bases: set[AdjustmentBasis] = set()
    for columns in per_row:
        bases.update(basis for _, _, basis in columns)
    if len(bases) > 1:
        raise ViewRefusal(
            f"price columns mix adjustment bases ({', '.join(sorted(b.value for b in bases))})",
            reason=RefusalReason.MIXED_OHLC_BASIS,
        )
    for columns in per_row:
        for key, _, basis in columns:
            if basis is AdjustmentBasis.SADJ:
                raise ViewRefusal(
                    f"price column {key!r} is already split-adjusted (*_sadj); "
                    f"adjusting it again would double-count every split",
                    reason=RefusalReason.DOUBLE_ADJUST_RISK,
                    column=key,
                )
            if basis is AdjustmentBasis.TRADJ:
                raise ViewRefusal(
                    f"price column {key!r} is a vendor total-return proxy "
                    f"(*_tradj), never an input to a house view",
                    reason=RefusalReason.NON_RAW_INPUT,
                    column=key,
                )
    return per_row


def raw_view(rows, *, mic: str | None = None) -> PriceView:
    """The printed tape, validated as all-``<field>_raw`` and executable (D00.D3).

    RAW is never adjusted, but it is EXACT: every price column and
    ``volume_raw`` is coerced to a ``Fraction`` (float / bool / unparseable ->
    NON_EXACT_INPUT, like every other view) in a COPY of each row; every other
    key passes through unchanged and input rows are never mutated.  The column
    law above still applies, so a vendor-adjusted series can never be labelled
    RAW — the exact DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT failure mode.

    ``mic`` is OPTIONAL here: without it the view is identical to a mic-less
    past (``currency`` is ``None`` and no row-currency check runs); with it the
    listing's declared currency (D00.A1.2) is carried on the view and an
    optional ``currency`` column on the rows must equal it row by row.
    """
    materialized = tuple(rows)
    for row in materialized:
        if not isinstance(row, Mapping):
            raise TypeError(f"rows must be mappings, got {type(row).__name__}")
    expected = _venue_currency(mic) if mic is not None else None
    per_row = _validate_price_columns(materialized)
    if expected is not None:
        _check_row_currency(materialized, expected)
    out_rows: list[dict] = []
    for row, columns in zip(materialized, per_row):
        out = dict(row)
        for key, _, _ in columns:
            out[key] = _exact_fraction(row[key], what=f"price column {key!r}", column=key)
        if "volume_raw" in row:
            out["volume_raw"] = _exact_fraction(
                row["volume_raw"], what="volume_raw", column="volume_raw"
            )
        out_rows.append(out)
    return PriceView(
        basis="RAW",
        rows=tuple(out_rows),
        reference=AdjustmentReference("RAW", None, None),
        executable=True,
        currency=expected,
    )


def sadj_view(rows, revisions: ActionRevisionSet, as_at: datetime, *, mic: str, quantity_convention: str = "shares") -> PriceView:
    """The split-adjusted view: ``P_raw(t) / S(t)`` per row, never twice (D00.D3).

    Every input price column must be ``<field>_raw`` (see the column law above);
    every price and ``volume_raw`` value is coerced to an exact ``Fraction``.
    Output rows carry only ``date``, ``<field>_sadj`` and ``volume_sadj``;
    input rows are never mutated.  The view is never executable and its
    reference names the action revision set and the ``as_at`` instant, so the
    number is reproducible against the recorded revisions.  A row dated after
    the listing venue's calendar day of ``as_at`` (D00.A1.1) refuses
    ROW_AFTER_AS_AT.  ``mic`` (keyword-only, required) resolves both the venue
    clock and the declared currency (D00.A1.2): the view carries the listing's
    currency and an optional ``currency`` column on the rows must equal it.
    """
    if quantity_convention != "shares":
        raise ViewRefusal(
            f"quantity convention {quantity_convention!r} is unsupported (only 'shares')",
            reason=RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION,
        )
    _require_aware(as_at, what="as_at")
    as_at_day = _venue_day(as_at, mic)
    if not isinstance(revisions, ActionRevisionSet):
        raise TypeError(
            f"revisions must be an ActionRevisionSet, got {type(revisions).__name__}"
        )
    materialized = tuple(rows)
    for row in materialized:
        if not isinstance(row, Mapping):
            raise TypeError(f"rows must be mappings, got {type(row).__name__}")
    per_row = _validate_price_columns(materialized)
    _check_row_currency(materialized, _venue_currency(mic))
    out_rows: list[dict] = []
    for row, columns in zip(materialized, per_row):
        if "date" not in row:
            raise TypeError(f"row is missing its 'date' member: {dict(row)!r}")
        day = _require_date(row["date"], what="row date")
        if day > as_at_day:
            raise ViewRefusal(
                f"row date {day.isoformat()} is after the view's as_at "
                f"{as_at.isoformat()} — an as-of view cannot carry a price printed "
                f"later (point-in-time law)",
                reason=RefusalReason.ROW_AFTER_AS_AT,
                column="date",
            )
        factor = split_factor(day, revisions, as_at, mic=mic)
        out: dict = {"date": day}
        for key, field, _ in columns:
            raw = _exact_fraction(row[key], what=f"price column {key!r}", column=key)
            out[f"{field.value}_sadj"] = raw / factor
        if "volume_raw" in row:
            volume = _exact_fraction(row["volume_raw"], what="volume_raw", column="volume_raw")
            out["volume_sadj"] = adjust_quantity(volume, factor, quantity_convention)
        out_rows.append(out)
    return PriceView(
        basis="SADJ",
        rows=tuple(out_rows),
        reference=AdjustmentReference("SADJ", revisions.revision_set_id, as_at),
        executable=False,
        currency=_venue_currency(mic),
    )


# ── house TOTAL_RETURN: holding plus cash under a declared policy (O2-P04) ────
#
# D00.D3, the house TOTAL_RETURN row, verbatim in substance: "a separately
# computed holding-plus-cash oracle under a *declared* policy: reinvest=NONE
# (cash held) or reinvest=EX_DATE_CLOSE; withholding = none unless declared".
# It refuses when "any event in the window is unsupported, or withholding/FX/
# reinvestment/ordering the request needs is unknown (P04.03)".  Three facts
# are DISTINCT and never substitute for one another (P04.02): original cash,
# current-share-adjusted cash, and a price factor.  Cash is carried AS CASH
# (or reinvested at the ex-date's own printed close per the declared policy) —
# never folded into the price.  A vendor TRADJ series is a proxy for this
# number, never the number (P04.04), which is why the view is never
# executable: nobody ever traded at a total-return index level.


class ReinvestPolicy(StrEnum):
    """What the declared policy does with cash the holding receives (D00.D3).

    ``NONE``: cash accumulates as cash (``view.cash``), never a price factor.
    ``EX_DATE_CLOSE``: cash buys fractional shares at ``close_raw`` printed on
    the ex-date — a declared accounting convenience, not an execution claim.
    """

    NONE = "none"
    EX_DATE_CLOSE = "ex_date_close"


def _norm_currency(code: str) -> str:
    """One comparison form for currency codes (ISO 4217 is case-insensitive)."""
    return code.strip().upper()


@dataclass(frozen=True)
class TotalReturnPolicy:
    """The declared policy a total-return question must carry (D00.D3, P04.03).

    Nothing is assumed.  A missing reinvestment, withholding or currency is a
    typed refusal — UNKNOWN_REINVESTMENT / UNKNOWN_WITHHOLDING / UNKNOWN_FX —
    never a silent default: "withholding = none unless declared" means *no*
    withholding is ``Fraction(0)``, declared.  A rate outside ``[0, 1)`` is as
    unknown as ``None``.  A non-exact rate (float/bool) refuses NON_EXACT_INPUT
    like every other number in this module.
    """

    reinvest: ReinvestPolicy | None
    withholding_rate: Fraction | None
    currency: str | None

    def __post_init__(self) -> None:
        if self.reinvest is None:
            raise ViewRefusal(
                "reinvest is None — a total-return view never assumes a "
                "reinvestment convention; declare ReinvestPolicy.NONE or "
                "ReinvestPolicy.EX_DATE_CLOSE",
                reason=RefusalReason.UNKNOWN_REINVESTMENT,
            )
        if isinstance(self.reinvest, ReinvestPolicy):
            pass
        elif isinstance(self.reinvest, str):
            try:
                object.__setattr__(
                    self, "reinvest", ReinvestPolicy(self.reinvest.strip().lower())
                )
            except ValueError as exc:
                raise ViewRefusal(
                    f"reinvest {self.reinvest!r} names no known policy "
                    f"({', '.join(p.value for p in ReinvestPolicy)}) — what the "
                    f"request wants is unknown",
                    reason=RefusalReason.UNKNOWN_REINVESTMENT,
                ) from exc
        else:
            raise TypeError(
                f"reinvest must be a ReinvestPolicy or None, "
                f"got {type(self.reinvest).__name__}"
            )
        if self.withholding_rate is None:
            raise ViewRefusal(
                "withholding_rate is None — withholding is none only when "
                "DECLARED as Fraction(0), never assumed",
                reason=RefusalReason.UNKNOWN_WITHHOLDING,
            )
        rate = _exact_fraction(self.withholding_rate, what="withholding_rate")
        object.__setattr__(self, "withholding_rate", rate)
        if not (Fraction(0) <= rate < Fraction(1)):
            raise ViewRefusal(
                f"withholding_rate {rate} is outside [0, 1) — the request's "
                f"withholding is unknown, not 'none'",
                reason=RefusalReason.UNKNOWN_WITHHOLDING,
            )
        if self.currency is None:
            raise ViewRefusal(
                "currency is None — the view never assumes a currency",
                reason=RefusalReason.UNKNOWN_FX,
            )
        if not isinstance(self.currency, str):
            raise TypeError(
                f"currency must be a str or None, got {type(self.currency).__name__}"
            )
        if not _norm_currency(self.currency):
            raise ViewRefusal(
                "currency is empty — the view never assumes a currency",
                reason=RefusalReason.UNKNOWN_FX,
            )
        object.__setattr__(self, "currency", _norm_currency(self.currency))


@dataclass(frozen=True)
class TotalReturnView:
    """One house TOTAL_RETURN answer: a holding plus its cash (D00.D3).

    ``wealth0 = q0 * p0`` at ``t0``; ``wealth1 = q1 * p1 + cash`` at ``t1``.
    ``events_applied`` records, in application order, each event's id, family
    and the share basis it acted on — so a same-day split-then-cash states the
    cash used the NEW share count (V07) instead of leaving it implicit.
    ``executable`` is always False and its constructor refuses True: this is an
    accounting oracle, and a vendor TRADJ series mistaken for it (P04.04) is
    exactly the confusion the refusal prevents.
    """

    wealth0: Fraction
    q1: Fraction
    cash: Fraction
    wealth1: Fraction
    holding_return: Fraction
    raw_price_return: Fraction
    policy: TotalReturnPolicy
    reference: AdjustmentReference
    events_applied: tuple[tuple[str, ActionFamily, Fraction], ...] = ()
    executable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.policy, TotalReturnPolicy):
            raise TypeError(
                f"policy must be a TotalReturnPolicy, got {type(self.policy).__name__}"
            )
        if not isinstance(self.reference, AdjustmentReference):
            raise TypeError(
                f"reference must be an AdjustmentReference, "
                f"got {type(self.reference).__name__}"
            )
        if not isinstance(self.events_applied, tuple):
            object.__setattr__(self, "events_applied", tuple(self.events_applied))
        for record in self.events_applied:
            if not isinstance(record, tuple) or len(record) != 3:
                raise TypeError(
                    f"events_applied entries must be (event_id, family, "
                    f"share_basis) tuples, got {record!r}"
                )
            event_id, family, basis = record
            if not isinstance(event_id, str) or not event_id:
                raise TypeError(f"event_id must be a non-empty string, got {event_id!r}")
            if not isinstance(family, ActionFamily):
                raise TypeError(f"family must be an ActionFamily, got {family!r}")
            if not isinstance(basis, Fraction):
                raise TypeError(
                    f"share_basis must be a Fraction, got {type(basis).__name__}"
                )
        if self.executable:
            raise ViewRefusal(
                "a TOTAL_RETURN view is never executable — it is a "
                "holding-plus-cash accounting number, not a price anyone traded",
                reason=RefusalReason.NOT_EXECUTABLE_BASIS,
            )


def total_return_view(
    rows,
    revisions: ActionRevisionSet,
    as_at: datetime,
    policy: TotalReturnPolicy,
    *,
    mic: str,
    q0=1,
) -> TotalReturnView:
    """The house TOTAL_RETURN oracle over a raw close series (D00.D3, O2-P04).

    ``rows`` are date-ordered mappings each carrying ``date`` and an exact
    ``close_raw``; ``t0``/``t1`` are the first/last row dates and ``p0``/``p1``
    their closes.  The column law above applies verbatim: any non-raw price
    column refuses (``*_tradj`` -> NON_RAW_INPUT, ``*_sadj`` ->
    DOUBLE_ADJUST_RISK) — a vendor TRADJ series is never an input to this view.

    ``mic`` (keyword-only, required) resolves the listing venue's clock
    (D00.A1.1) and its declared currency (D00.A1.2): the policy's currency must
    equal the declared one (else CURRENCY_MISMATCH) and an optional
    ``currency`` column on the rows must equal it row by row.

    Events are ``revisions.resolve(as_at)`` (P02) kept while ``t0 < ex_date <=
    t1`` and applied in ``(ex_date, sequence)`` order; two same-ex-date events
    whose sequence is None or equal refuse UNKNOWN_ORDERING — never a guess.
    Each event then faces P02's value law unchanged (unsupported family /
    not CONFIRMED / unknown or invalid ratio / cash-basis mismatch), plus the
    cash law this view adds:

    - a split multiplies the holding: ``q = q * r``;
    - a cash dividend must be declared ``as_declared`` (else
      CASH_BASIS_MISMATCH — original cash and current-share-adjusted cash are
      distinct facts, P04.02) in the policy's currency (else, or None,
      UNKNOWN_FX); ``amount = q * cash_per_share * (1 - withholding_rate)``
      with ``q`` the share count in force at the ex_date AFTER any same-day
      earlier-sequence split; the policy then holds it as cash (NONE) or buys
      fractional shares at ``close_raw(ex_date)`` (EX_DATE_CLOSE; a missing or
      non-positive close on the ex-date refuses MISSING_PRICE — no proxy price
      is ever substituted).

    - EX_DATE_CLOSE purchases settle at the ex-date's close, i.e. after EVERY
      event of that ex-date has been applied: cash paid before a same-day split
      buys post-split shares at the post-split close, and shares bought at the
      close carry no later same-day dividend (R02 M2).

    ``q0`` (default 1) is the starting share count and must be exact and
    positive.  Every output is an exact ``Fraction``.
    A non-positive ``q0`` or ``close_raw(t0)`` refuses NON_POSITIVE_VALUE; two
    rows on one date refuse DUPLICATE_ROW_DATE and a row dated after the
    listing venue's calendar day of ``as_at`` (D00.A1.1) refuses
    ROW_AFTER_AS_AT (column ``date`` for both).
    """
    if not isinstance(policy, TotalReturnPolicy):
        raise TypeError(
            f"policy must be a TotalReturnPolicy, got {type(policy).__name__}"
        )
    _require_aware(as_at, what="as_at")
    if not isinstance(revisions, ActionRevisionSet):
        raise TypeError(
            f"revisions must be an ActionRevisionSet, got {type(revisions).__name__}"
        )
    q_start = _exact_fraction(q0, what="q0")
    if q_start <= 0:
        raise ViewRefusal(
            f"q0 must be a positive share count, got {q_start}",
            reason=RefusalReason.NON_POSITIVE_VALUE,
        )
    materialized = tuple(rows)
    for row in materialized:
        if not isinstance(row, Mapping):
            raise TypeError(f"rows must be mappings, got {type(row).__name__}")
    _validate_price_columns(materialized)
    if not materialized:
        raise ValueError(
            "total_return_view needs at least one row (t0/t1 are the first "
            "and last row dates)"
        )
    as_at_day = _venue_day(as_at, mic)
    expected = _venue_currency(mic)
    if policy.currency != expected:
        raise ViewRefusal(
            f"the policy's currency {policy.currency!r} is not the listing's "
            f"declared {expected!r} — no FX is applied in any view (D00.A1.2)",
            reason=RefusalReason.CURRENCY_MISMATCH,
        )
    _check_row_currency(materialized, expected)
    close_by_day: dict[date, Fraction] = {}
    previous_day: date | None = None
    for row in materialized:
        if "date" not in row:
            raise TypeError(f"row is missing its 'date' member: {dict(row)!r}")
        day = _require_date(row["date"], what="row date")
        if day > as_at_day:
            raise ViewRefusal(
                f"row date {day.isoformat()} is after the view's as_at "
                f"{as_at.isoformat()} — an as-of view cannot carry a price printed "
                f"later (point-in-time law)",
                reason=RefusalReason.ROW_AFTER_AS_AT,
                column="date",
            )
        if previous_day is not None and day == previous_day:
            raise ViewRefusal(
                f"two rows carry the date {day.isoformat()} — one session has "
                f"exactly one close and which print is real is never guessed",
                reason=RefusalReason.DUPLICATE_ROW_DATE,
                column="date",
            )
        if previous_day is not None and day < previous_day:
            raise ValueError(
                f"rows must be date-ordered: {day:%Y-%m-%d} follows "
                f"{previous_day:%Y-%m-%d}"
            )
        previous_day = day
        if "close_raw" not in row:
            raise ViewRefusal(
                f"row {day:%Y-%m-%d} carries no close_raw — the view has no "
                f"price for that session",
                reason=RefusalReason.MISSING_PRICE,
                column="close_raw",
            )
        close_by_day[day] = _exact_fraction(
            row["close_raw"], what="close_raw", column="close_raw"
        )
    t0: date = materialized[0]["date"]
    t1: date = materialized[-1]["date"]
    p0 = close_by_day[t0]
    p1 = close_by_day[t1]
    if p0 <= 0:
        raise ViewRefusal(
            f"close_raw at t0 must be positive, got {p0} — a return from a zero "
            f"or negative starting price is undefined",
            reason=RefusalReason.NON_POSITIVE_VALUE,
            column="close_raw",
        )

    in_window = [
        event for event in revisions.resolve(as_at) if t0 < event.ex_date <= t1
    ]
    # Never guess a same-day order (D00.D3/P04.03): sequences present and
    # pairwise distinct, or the view refuses.
    by_day: dict[date, list[ActionEvent]] = {}
    for event in in_window:
        by_day.setdefault(event.ex_date, []).append(event)
    for day, group in sorted(by_day.items()):
        if len(group) > 1:
            sequences = [event.sequence for event in group]
            if any(s is None for s in sequences) or len(set(sequences)) < len(sequences):
                names = ", ".join(repr(event.event_id) for event in group)
                raise ViewRefusal(
                    f"same-ex-date events ({names}) on {day:%Y-%m-%d} have a "
                    f"None or equal sequence — which applied first is unknown "
                    f"and is never guessed",
                    reason=RefusalReason.UNKNOWN_ORDERING,
                    event_id=group[-1].event_id,
                )

    q = q_start
    cash = Fraction(0)
    applied: list[tuple[str, ActionFamily, Fraction]] = []
    # EX_DATE_CLOSE buys at the ex-date's CLOSE, which prints after EVERY event
    # of that ex-date took effect at the open: a day's purchases settle once
    # the whole day has been applied, in post-event shares at the printed close
    # (R02 M2 — cash paid before a same-day split is never reinvested at the
    # post-split close on the pre-split share count, and shares bought at the
    # close carry no later same-day dividend).
    to_buy = Fraction(0)
    buy_day: date | None = None
    for event in in_window:  # resolve() already (ex_date, sequence)-ordered
        if buy_day is not None and event.ex_date != buy_day:
            q += to_buy / close_by_day[buy_day]
            to_buy, buy_day = Fraction(0), None
        contribution = _check_window_event(event)  # P02's value law, verbatim
        if contribution is not None:  # a split: the unit changes, wealth does not
            applied.append((event.event_id, event.family, q))
            q = q * contribution
            continue
        # A cash dividend — carried by P02 for exactly this view.
        if event.cash_basis != "as_declared":
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} is declared "
                f"{event.cash_basis!r}, not 'as_declared' — original cash and "
                f"current-share-adjusted cash are distinct facts (P04.02)",
                reason=RefusalReason.CASH_BASIS_MISMATCH,
                event_id=event.event_id,
            )
        if event.currency is None or not event.currency.strip():
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} declares no currency — the "
                f"view never assumes one and no FX is applied in any view "
                f"(D00.D3)",
                reason=RefusalReason.UNKNOWN_FX,
                event_id=event.event_id,
            )
        if _norm_currency(event.currency) != policy.currency:
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} is in "
                f"{event.currency!r}, not the policy's {policy.currency!r} — no "
                f"FX is applied in any view (D00.D3)",
                reason=RefusalReason.CURRENCY_MISMATCH,
                event_id=event.event_id,
            )
        if event.cash_per_share is None:
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} has no cash_per_share — an "
                f"unknown amount is never guessed",
                reason=RefusalReason.UNKNOWN_RATIO,
                event_id=event.event_id,
            )
        if event.cash_per_share < 0:
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} cash_per_share "
                f"{event.cash_per_share} must not be negative",
                reason=RefusalReason.INVALID_RATIO,
                event_id=event.event_id,
            )
        applied.append((event.event_id, event.family, q))
        amount = q * event.cash_per_share * (1 - policy.withholding_rate)
        if policy.reinvest is ReinvestPolicy.NONE:
            cash += amount
        else:  # ReinvestPolicy.EX_DATE_CLOSE
            if event.ex_date not in close_by_day:
                raise ViewRefusal(
                    f"ex_date {event.ex_date:%Y-%m-%d} has no row — "
                    f"EX_DATE_CLOSE reinvestment needs that session's printed "
                    f"close and never substitutes a proxy",
                    reason=RefusalReason.MISSING_PRICE,
                    event_id=event.event_id,
                )
            ex_close = close_by_day[event.ex_date]
            if ex_close <= 0:
                raise ViewRefusal(
                    f"close_raw on ex_date {event.ex_date:%Y-%m-%d} is "
                    f"{ex_close} — not a usable reinvestment price",
                    reason=RefusalReason.MISSING_PRICE,
                    event_id=event.event_id,
                )
            to_buy += amount
            buy_day = event.ex_date

    if buy_day is not None:
        q += to_buy / close_by_day[buy_day]
    wealth0 = q_start * p0
    wealth1 = q * p1 + cash
    return TotalReturnView(
        wealth0=wealth0,
        q1=q,
        cash=cash,
        wealth1=wealth1,
        holding_return=wealth1 / wealth0 - 1,
        raw_price_return=p1 / p0 - 1,
        policy=policy,
        reference=AdjustmentReference(
            "total_return", revisions.revision_set_id, as_at
        ),
        events_applied=tuple(applied),
        executable=False,
    )


# ── correction-aware retained views + the qualify-first gate (O3-P05) ─────────
#
# D00.D5 closes the loop this section implements: a view is a point-in-time
# quantity over (rows, action revision set, identity generation, code), and a
# CORRECTION is a new generation — never a rewrite of the old one.  So a view
# that answered a question must be RETAINABLE exactly as it answered it, and
# reopenable byte-exactly later, while a recomputation over a corrected source
# is a different vintage that can never wear the old one's receipt.
#
# Three pieces, each a composition of accepted modules (never a re-implementation):
#
# * the QUALIFY-FIRST gate — :func:`admit_action_input` runs P01's
#   ``registry.qualify_action_input`` BEFORE any event enters a composed view;
#   the caller's qualification string is always discarded and replaced by the
#   verdict, so a SUSPECTED inference can never arrive pre-labelled CONFIRMED;
# * the VINTAGE — :class:`ViewVintage` + :func:`retain_view`/:func:`reopen_view`
#   bind a view to its source generation, revision set, identity generation and
#   code version through one canonical payload, one digest and one receipt
#   (T01's ``read_contract.replay`` does the byte-exactness);
# * the COMPOSITION — :func:`reconstruct_price_view` builds a view from a
#   read_contract RECONSTRUCT result, so mode/cutoff/clock/generation refusals
#   stay read_contract's own and are never re-implemented here.

#: Schema tags written into every canonical payload / receipt, so a retained
#: artifact declares what it is instead of relying on its file name.  The view
#: payload moved to v2 in P06 (it gained the declared ``currency`` member);
#: the receipt schema is unchanged (it never carried view fields).
_RETAINED_VIEW_SCHEMA = "dataos.retained_price_view.v2"
_RETAINED_RECEIPT_SCHEMA = "dataos.retained_price_view_receipt.v1"

_HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


def _dumps_canonical(doc: Mapping) -> bytes:
    """The one canonical JSON encoding: sorted keys, tight separators, no NaN."""
    return json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


# ── P05.05 — the qualify-first action-input gate ─────────────────────────────

def admit_action_input(
    event: ActionEvent, observation: Mapping, *, registry: Registry
) -> ActionEvent:
    """Stamp one action event with P01's verdict BEFORE it may enter a view.

    The FIRST statement qualifies the observation (P01's
    ``lib.dataos.registry.qualify_action_input``, imported — never copied); a
    structurally impossible observation raises that function's ``ValueError``
    unchanged, because a malformed input has no honest status to stamp.

    The gate then refuses, typed, exactly the two shapes that cannot become an
    event at all:

    * a QUALIFIED EMPTY response — authoritative absence is not an event, so
      there is nothing to stamp (NOT_CONFIRMED; P01.03);
    * a receipt naming a DIFFERENT observation than the one the event claims
      (RECEIPT_MISMATCH) — a verdict may not authenticate a substituted event.

    Every other verdict is STAMPED onto the event as its qualification string:
    the caller's own qualification is always discarded (``replace``), so a
    SUSPECTED / UNQUALIFIED / UNCAPTURED event is recorded — never dropped —
    and ``_check_window_event`` refuses it NOT_CONFIRMED in every view whose
    window it enters, while outside any window it stays inert.
    """
    verdict = qualify_action_input(observation, registry=registry)
    if verdict.status is ActionInputStatus.NO_ACTION_IN_QUALIFIED_RESPONSE:
        raise ViewRefusal(
            f"event {event.event_id!r} was offered against a qualified response "
            f"that authoritatively held no action — absence is not an event "
            f"(P01.03)",
            reason=RefusalReason.NOT_CONFIRMED,
            event_id=event.event_id,
        )
    if verdict.receipt is not None and verdict.receipt != event.source_receipt:
        raise ViewRefusal(
            f"event {event.event_id!r} carries source_receipt "
            f"{event.source_receipt!r} but its observation was qualified under "
            f"receipt {verdict.receipt!r} — a verdict may not authenticate a "
            f"substituted event (D00.D5)",
            reason=RefusalReason.RECEIPT_MISMATCH,
            event_id=event.event_id,
        )
    return replace(event, qualification=verdict.status.value)


def admit_revision_set(
    revision_set_id: str,
    inputs: Iterable[tuple[ActionEvent, Mapping]],
    *,
    registry: Registry,
) -> ActionRevisionSet:
    """An :class:`ActionRevisionSet` every event of which passed the gate.

    Composes :func:`admit_action_input` over ``(event, observation)`` pairs;
    the set itself is P02's, unchanged.  Direct ``ActionRevisionSet(...)``
    construction stays legal for legacy callers and tests (see GAPS).
    """
    return ActionRevisionSet(
        revision_set_id,
        tuple(admit_action_input(event, obs, registry=registry) for event, obs in inputs),
    )


# ── P05.03 — the vintage, the canonical payload, the receipt, the label ───────

@dataclass(frozen=True)
class ViewVintage:
    """What a view's numbers were computed FROM (D00.D1/D00.D5).

    Four names, one vintage: the source generation of the rows, the action
    revision set the factors resolved against, the identity generation the
    request bound, and the code version that produced the view.  Two views with
    equal vintages and equal digests are the same answer; anything else is a
    different answer even when the rows happen to coincide.  ``revision_set_id``
    is ``None`` ONLY for a RAW view (no action revisions were consulted).
    """

    source_generation_id: str
    revision_set_id: str | None
    identity_generation_id: str
    code_version: str

    def __post_init__(self) -> None:
        for name in ("source_generation_id", "identity_generation_id"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a str, got {type(value).__name__}")
            if not value:
                raise ValueError(f"{name} must be a non-empty str, got {value!r}")
        if self.revision_set_id is not None:
            if not isinstance(self.revision_set_id, str):
                raise TypeError(
                    f"revision_set_id must be a str or None, "
                    f"got {type(self.revision_set_id).__name__}"
                )
            if not self.revision_set_id:
                raise ValueError(
                    f"revision_set_id must be a non-empty str or None, "
                    f"got {self.revision_set_id!r}"
                )
        if not isinstance(self.code_version, str):
            raise TypeError(
                f"code_version must be a str, got {type(self.code_version).__name__}"
            )
        if not _HEX40.match(self.code_version):
            raise ValueError(
                f"code_version must be a 40-char lowercase-hex code version "
                f"(the read_contract rule), got {self.code_version!r}"
            )


def _encode_view_value(value, *, key: str):
    """One row value -> its exact, reversible canonical form.

    ``bool`` is checked before ``int`` (bool subclasses int) and ``datetime``
    before ``date`` (likewise), exactly as the frozen table orders them.
    Anything else — a float, a Decimal, a naive datetime, a nested container —
    refuses NON_EXACT_INPUT: a value that cannot round-trip byte-exactly
    cannot be retained, and converting it would silently restate history.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, Fraction):
        return {"q": f"{value.numerator}/{value.denominator}"}
    if isinstance(value, int):
        return value
    if isinstance(value, datetime):
        return {"t": utc(value).isoformat()}
    if isinstance(value, date):
        return {"d": value.isoformat()}
    if value is None or isinstance(value, str):
        return value
    raise ViewRefusal(
        f"retained row column {key!r} carries {type(value).__name__} {value!r} — "
        f"only exact reversible values (Fraction, date, aware datetime, str, "
        f"int, bool, None) may be retained byte-exactly",
        reason=RefusalReason.NON_EXACT_INPUT,
        column=key,
    )


def _decode_view_value(value):
    """Invert :func:`_encode_view_value` exactly (single-key ``q``/``d``/``t``)."""
    if isinstance(value, dict) and len(value) == 1:
        if "q" in value:
            return Fraction(value["q"])
        if "d" in value:
            return date.fromisoformat(value["d"])
        if "t" in value:
            return datetime.fromisoformat(value["t"])
    return value


def _encode_view_row(row: Mapping) -> dict:
    if not isinstance(row, Mapping):
        raise TypeError(f"a view row must be a Mapping, got {type(row).__name__}")
    encoded: dict = {}
    for key, value in row.items():
        if not isinstance(key, str):
            raise ViewRefusal(
                f"a retained row carries the non-string column {key!r} — a "
                f"column that cannot be named cannot be retained",
                reason=RefusalReason.NON_EXACT_INPUT,
            )
        encoded[key] = _encode_view_value(value, key=key)
    return encoded


def _decode_view_row(row: Mapping) -> dict:
    return {key: _decode_view_value(value) for key, value in row.items()}


def _vintage_doc(vintage: ViewVintage) -> dict:
    return {
        "source_generation_id": vintage.source_generation_id,
        "revision_set_id": vintage.revision_set_id,
        "identity_generation_id": vintage.identity_generation_id,
        "code_version": vintage.code_version,
    }


def _canonical_view_payload(view: PriceView, vintage: ViewVintage) -> bytes:
    """The canonical payload of (view, vintage) — the bytes a replay must serve.

    One JSON document under the frozen dumps settings; every row value passes
    through the exact/reversible encoder first, so the payload carries no float
    anywhere and decodes back to the very objects it was built from.
    """
    reference = view.reference
    return _dumps_canonical(
        {
            "schema": _RETAINED_VIEW_SCHEMA,
            "basis": view.basis,
            "executable": view.executable,
            "currency": view.currency,
            "reference": {
                "basis": reference.basis,
                "action_revision_set_id": reference.action_revision_set_id,
                "as_at": (
                    None if reference.as_at is None else utc(reference.as_at).isoformat()
                ),
            },
            "vintage": _vintage_doc(vintage),
            "rows": [_encode_view_row(row) for row in view.rows],
        }
    )


def view_receipt_sha256(output_id: str, vintage: ViewVintage, view_digest: str) -> str:
    """The receipt that PUBLISHED one retained view under ``output_id``.

    Hashes the canonical JSON of the receipt schema — output id, the four
    vintage names, the view digest — so an old receipt can never cover a new
    source generation, factor set, identity generation or view: any one of them
    moves the digest (D00.D5.3).
    """
    return hashlib.sha256(
        _dumps_canonical(
            {
                "schema": _RETAINED_RECEIPT_SCHEMA,
                "output_id": output_id,
                "vintage": _vintage_doc(vintage),
                "view_digest": view_digest,
            }
        )
    ).hexdigest()


def view_label(view: PriceView, vintage: ViewVintage) -> str:
    """The one-line human label of (view, vintage): basis, currency, as_at, ids, code."""
    reference = view.reference
    as_at = "-" if reference.as_at is None else utc(reference.as_at).isoformat()
    revision_set = reference.action_revision_set_id or "-"
    return (
        f"{view.basis}|currency={view.currency or '-'}|as_at={as_at}"
        f"|revision_set={revision_set}"
        f"|source_generation={vintage.source_generation_id}"
        f"|identity_generation={vintage.identity_generation_id}"
        f"|code_version={vintage.code_version}"
    )


# ── P05.01/P05.03 — retain and reopen ────────────────────────────────────────

@dataclass(frozen=True)
class RetainedView:
    """A view frozen as it answered: vintage, payload, digest, receipt.

    ``key`` is the vintage triple plus the digest — the identity two retained
    views must share to be the same answer.  ``payload`` is the canonical bytes
    (``None`` only on a destructured/tampered holder, which ``reopen_view``
    routes to read_contract's NO_RETAINED_OUTPUT).
    """

    vintage: ViewVintage
    view_digest: str
    label: str
    payload: bytes | None
    output_id: str
    publishing_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.vintage, ViewVintage):
            raise TypeError(
                f"vintage must be a ViewVintage, got {type(self.vintage).__name__}"
            )
        for name in ("view_digest", "publishing_receipt_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _HEX64.match(value):
                raise ValueError(
                    f"{name} must be a 64-char lowercase-hex sha256, got {value!r}"
                )

    @property
    def key(self) -> tuple:
        return (
            self.vintage.source_generation_id,
            self.vintage.revision_set_id,
            self.vintage.code_version,
            self.view_digest,
        )


def retain_view(
    view: PriceView,
    vintage: ViewVintage,
    *,
    output_id: str,
    publishing_receipt_sha256: str | None = None,
) -> RetainedView:
    """Freeze one view as it answered, under one output id and one receipt.

    Refuses MIXED_GENERATION — a vintage that does not belong to this view —
    before anything is serialised, in each of its three shapes: a revision set
    the view's own reference does not name; a RAW view (which consulted no
    action revisions) carrying a revision set id; an adjusted view carrying
    none.  After the digest is computed, a SUPPLIED receipt that does not equal
    the receipt this (output_id, vintage, view) actually hashes to refuses the
    same way: an old receipt can never cover a new generation, factor set,
    identity generation or view.  With no receipt supplied, the computed one is
    used.  A row value that cannot round-trip refuses NON_EXACT_INPUT.
    """
    if not isinstance(view, PriceView):
        raise TypeError(f"view must be a PriceView, got {type(view).__name__}")
    if not isinstance(vintage, ViewVintage):
        raise TypeError(f"vintage must be a ViewVintage, got {type(vintage).__name__}")
    if not isinstance(output_id, str) or not output_id:
        raise TypeError(f"output_id must be a non-empty string, got {output_id!r}")
    reference = view.reference
    if vintage.revision_set_id != reference.action_revision_set_id:
        raise ViewRefusal(
            f"vintage names revision set {vintage.revision_set_id!r} but the view "
            f"was computed against {reference.action_revision_set_id!r} — one "
            f"vintage, one revision set (D00.D5.1)",
            reason=RefusalReason.MIXED_GENERATION,
        )
    if view.basis == "RAW" and vintage.revision_set_id is not None:
        raise ViewRefusal(
            "a RAW view consulted no action revisions, so its vintage carries "
            f"no revision set id (got {vintage.revision_set_id!r})",
            reason=RefusalReason.MIXED_GENERATION,
        )
    if view.basis != "RAW" and vintage.revision_set_id is None:
        raise ViewRefusal(
            f"a {view.basis!r} view resolves factors against an action revision "
            f"set, so its vintage must name it (got None)",
            reason=RefusalReason.MIXED_GENERATION,
        )
    payload = _canonical_view_payload(view, vintage)
    view_digest = hashlib.sha256(payload).hexdigest()
    receipt = view_receipt_sha256(output_id, vintage, view_digest)
    if publishing_receipt_sha256 is not None and publishing_receipt_sha256 != receipt:
        raise ViewRefusal(
            f"the supplied publishing receipt does not cover output "
            f"{output_id!r} at this vintage and view digest — an old receipt "
            f"can never publish a new generation, factor set, identity "
            f"generation or view (D00.D5.3)",
            reason=RefusalReason.MIXED_GENERATION,
        )
    return RetainedView(
        vintage=vintage,
        view_digest=view_digest,
        label=view_label(view, vintage),
        payload=payload,
        output_id=output_id,
        publishing_receipt_sha256=(
            receipt if publishing_receipt_sha256 is None else publishing_receipt_sha256
        ),
    )


@dataclass(frozen=True)
class ReopenedView:
    """A retained view reopened byte-exactly: the view, its label, its vintage
    and the read_contract REPLAY result that served the bytes."""

    view: PriceView
    label: str
    vintage: ViewVintage
    result: ReadResult


def reopen_view(retained: RetainedView, request: ReadRequest) -> ReopenedView:
    """Reopen a retained view through ``read_contract.replay`` — byte-exactly.

    The retained material (payload, digest, receipt) goes to T01's ``replay``
    untouched: tampered bytes surface as read_contract's ``ReadRefusal`` with
    ``RETAINED_DIGEST_MISMATCH``, and missing material (a ``None`` payload, a
    wrong ``output_id``) as ``NO_RETAINED_OUTPUT`` — both propagate unchanged.
    The decoded document must declare the current ``_RETAINED_VIEW_SCHEMA`` or
    refuse ``SCHEMA_MISMATCH`` (P06): a payload of another schema is never
    reopened as this view shape.  Only then is the payload decoded back into a
    :class:`PriceView` and its
    :class:`ViewVintage`, and the decoded vintage must equal the retained one
    and re-hash to the retained receipt, else MIXED_GENERATION: bytes that
    decode to a different vintage than the one they were retained under are a
    mixed generation no matter what their digest says.
    """
    if not isinstance(retained, RetainedView):
        raise TypeError(
            f"retained must be a RetainedView, got {type(retained).__name__}"
        )
    if not isinstance(request, ReadRequest):
        raise TypeError(f"request must be a ReadRequest, got {type(request).__name__}")
    result = read_contract.replay(
        request,
        RetainedOutput(
            retained.output_id,
            retained.payload,
            retained.view_digest,
            retained.publishing_receipt_sha256,
        ),
    )
    doc = json.loads(result.payload.decode("utf-8"))
    if doc.get("schema") != _RETAINED_VIEW_SCHEMA:
        raise ViewRefusal(
            f"the retained bytes for output {retained.output_id!r} declare schema "
            f"{doc.get('schema')!r}, not {_RETAINED_VIEW_SCHEMA!r} — an artifact "
            f"of another schema is never reopened as this one (D00.D5)",
            reason=RefusalReason.SCHEMA_MISMATCH,
        )
    reference_doc = doc["reference"]
    as_at = (
        None
        if reference_doc["as_at"] is None
        else datetime.fromisoformat(reference_doc["as_at"])
    )
    view = PriceView(
        doc["basis"],
        tuple(_decode_view_row(row) for row in doc["rows"]),
        AdjustmentReference(
            reference_doc["basis"], reference_doc["action_revision_set_id"], as_at
        ),
        doc["executable"],
        currency=doc["currency"],
    )
    vintage = ViewVintage(**doc["vintage"])
    if vintage != retained.vintage:
        raise ViewRefusal(
            f"the retained bytes for output {retained.output_id!r} decode to "
            f"vintage {_vintage_doc(vintage)} but were retained under "
            f"{_vintage_doc(retained.vintage)} — one artifact, one generation "
            f"(D00.D5.1)",
            reason=RefusalReason.MIXED_GENERATION,
        )
    if (
        view_receipt_sha256(retained.output_id, vintage, retained.view_digest)
        != retained.publishing_receipt_sha256
    ):
        raise ViewRefusal(
            f"the retained bytes for output {retained.output_id!r} do not "
            f"re-hash to the receipt that published them — the receipt and the "
            f"artifact belong to different generations (D00.D5.3)",
            reason=RefusalReason.MIXED_GENERATION,
        )
    label = view_label(view, vintage)
    if label != retained.label:
        raise ViewRefusal(
            f"the retained bytes for output {retained.output_id!r} decode to "
            f"label {label!r}, not the retained {retained.label!r}",
            reason=RefusalReason.MIXED_GENERATION,
        )
    return ReopenedView(view, label, vintage, result)


# ── P05.02 — the composition over read_contract.reconstruct ──────────────────

@dataclass(frozen=True)
class ComposedView:
    """A view composed from a read_contract reconstruction: the view, its
    vintage, the underlying ``ReadResult`` (evidence intact) and the label."""

    view: PriceView
    vintage: ViewVintage
    result: ReadResult
    label: str


def _action_event_from_row(row: Mapping, *, clock_column: str) -> ActionEvent:
    """One selected action row -> an ActionEvent stamped ``UNQUALIFIED``.

    The placeholder qualification is exactly that: the qualify-first gate
    overwrites it with the verdict before any view sees the event.
    """
    return ActionEvent(
        event_id=row["event_id"],
        family=ActionFamily(row["family"]),
        ex_date=date.fromisoformat(row["ex_date"]),
        known_at=utc(row[clock_column]),
        source_receipt=row["source_receipt"],
        qualification="UNQUALIFIED",
        ratio=Fraction(row["ratio"]) if row.get("ratio") is not None else None,
        cash_per_share=(
            Fraction(row["cash_per_share"])
            if row.get("cash_per_share") is not None
            else None
        ),
        cash_basis=row.get("cash_basis"),
        currency=row.get("currency"),
        supersedes=row.get("supersedes"),
        cancelled=bool(row.get("cancelled", False)),
        sequence=row.get("sequence"),
    )


def reconstruct_price_view(
    request: ReadRequest,
    *,
    bars: Dependency,
    actions: Dependency,
    observations: Mapping[str, Mapping],
    registry: Registry,
    code_version: str,
    identity_generation_id: str,
    basis: str = "SADJ",
) -> ComposedView:
    """Compose a correction-aware view over ``read_contract.reconstruct``.

    Step 1 is the reconstruction itself, so every mode/cutoff/clock/generation
    refusal is read_contract's own and is never re-implemented here.  Step 2
    (P06, D00.A1) resolves the listing's MIC from the contract identity: the
    listing key's MIC and an explicit ``identity["mic"]`` must agree, either
    alone binds the venue, and neither refuses ``VENUE_CLOCK_UNKNOWN`` —
    an ``IdentityError`` never escapes the view layer.  A
    ``field_units["currency"]`` that differs from the venue's declared currency
    refuses ``CURRENCY_MISMATCH`` (D00.A1.2: it IS the listing currency).
    Each
    selected action row becomes an ``ActionEvent`` whose ``known_at`` is the
    REQUESTED clock's value on that row; every event must carry an observation,
    which the qualify-first gate stamps (or refuses on).  The revision set id is
    ``"actions:" + <read_contract's digest of exactly the selected action
    rows>``, so a correction that changes what was selected changes the vintage
    even when the rows happen to compose the same view.  Bars rows are
    projected to ``date`` plus their ``*_raw`` columns only — generation and
    clock columns never enter a view.  The source generation is the bars
    dependency's bound generation: a bars dependency that declared no
    generations refuses UNBOUND_GENERATION, because a view with no source
    generation can never be retained or superseded (D00.D5).
    """
    result = read_contract.reconstruct(
        request,
        {"bars": bars, "actions": actions},
        required=("bars", "actions"),
        code_version=code_version,
    )
    identity = request.contract.identity
    key_mic: str | None = None
    try:
        key_mic = parse_listing_key(identity["listing_id"]).mic
    except IdentityError:
        key_mic = None
    id_value = identity.get("mic")
    if id_value is not None and not isinstance(id_value, str):
        raise ViewRefusal(
            f"identity['mic'] must be a str or absent, got "
            f"{type(id_value).__name__} {id_value!r} — the listing's venue is "
            f"never guessed (D00.A1.1)",
            reason=RefusalReason.VENUE_CLOCK_UNKNOWN,
        )
    id_mic: str | None = (
        id_value.strip().upper()
        if isinstance(id_value, str) and id_value.strip()
        else None
    )
    if key_mic is not None and id_mic is not None and key_mic != id_mic:
        raise ViewRefusal(
            f"the listing key names venue {key_mic!r} but identity['mic'] names "
            f"{id_mic!r} — one listing, one venue (D00.A1.1)",
            reason=RefusalReason.VENUE_CLOCK_UNKNOWN,
        )
    mic = key_mic if key_mic is not None else id_mic
    if mic is None:
        raise ViewRefusal(
            "the contract identity names no listing venue (neither a parseable "
            "listing key MIC nor identity['mic']) — the as_at day is never taken "
            "from UTC (D00.A1.1)",
            reason=RefusalReason.VENUE_CLOCK_UNKNOWN,
        )
    expected_currency = _venue_currency(mic)
    declared_unit = request.contract.field_units.get("currency")
    if declared_unit is not None and (
        not isinstance(declared_unit, str) or _norm_currency(declared_unit) != expected_currency
    ):
        raise ViewRefusal(
            f"field_units['currency'] is {declared_unit!r}, not the listing's "
            f"declared {expected_currency!r} — field_units.currency IS the "
            f"listing currency and no FX is applied (D00.A1.2)",
            reason=RefusalReason.CURRENCY_MISMATCH,
        )
    clock_column = result.evidence["clock"]
    events = [
        _action_event_from_row(row, clock_column=clock_column)
        for row in result.values["actions"]
    ]
    for event in events:
        if event.event_id not in observations:
            raise ViewRefusal(
                f"action event {event.event_id!r} has no observation — an event "
                f"may enter a composed view only through P01's qualify-first "
                f"gate (D00.D3)",
                reason=RefusalReason.NOT_CONFIRMED,
                event_id=event.event_id,
            )
    revisions = admit_revision_set(
        "actions:" + read_contract.selected_input_sha256s(result)["actions"],
        ((event, observations[event.event_id]) for event in events),
        registry=registry,
    )
    projected = [
        {
            "date": date.fromisoformat(row["date"]),
            **{k: v for k, v in row.items() if k.endswith("_raw")},
        }
        for row in result.values["bars"]
    ]
    normalized_basis = _normalize_basis(basis)
    if normalized_basis == "SADJ":
        view = sadj_view(projected, revisions, request.cutoff, mic=mic)
    elif normalized_basis == "RAW":
        view = raw_view(projected, mic=mic)
    else:
        raise ViewRefusal(
            f"basis {basis!r} names no composable view (only SADJ and RAW)",
            reason=RefusalReason.AMBIGUOUS_BASIS,
        )
    source_generation_id = result.evidence["dependency_generation_ids"]["bars"]
    if source_generation_id is None:
        raise ViewRefusal(
            "the bars dependency declared no generations, so the view has no "
            "source generation to be retained or superseded under (D00.D5)",
            reason=RefusalReason.UNBOUND_GENERATION,
        )
    vintage = ViewVintage(
        source_generation_id,
        view.reference.action_revision_set_id,
        identity_generation_id,
        code_version,
    )
    return ComposedView(view, vintage, result, view_label(view, vintage))


def simple_returns(view: PriceView, field: str = "close") -> tuple[Fraction, ...]:
    """``p1 / p0 - 1`` over consecutive rows of ``<field>_<basis>`` — exact.

    A common split factor on every endpoint cancels in these returns (V04) and
    a single-bar correction does not (V05) — which is exactly why the retained
    view, not the recomputation, is the artifact a return claim must cite.
    """
    column = f"{field}_{view.basis.lower()}"
    prices = [
        _exact_fraction(row[column], what=f"return column {column!r}", column=column)
        for row in view.rows
    ]
    return tuple(prices[i + 1] / prices[i] - 1 for i in range(len(prices) - 1))
