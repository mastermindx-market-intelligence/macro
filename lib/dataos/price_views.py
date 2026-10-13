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

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Mapping

from lib.dataos.price import (
    AdjustmentBasis,
    PriceError,
    PriceField,
    is_ambiguous,
    parse_column,
)

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


def split_factor(t: date, revisions: ActionRevisionSet, as_at: datetime) -> Fraction:
    """``S(t)`` — the exact cumulative split divisor at row date ``t`` (D00.D3).

    Product of ``r_e`` over CONFIRMED split events active at ``as_at`` with
    ``t < ex_date <= as_at`` (UTC date).  The boundary is half-open on the left:
    a row dated ``ex_date - 1 day`` is divided by ``r``; a row dated ``ex_date``
    is not (the exchange already printed the new unit that session).  Events
    with ``ex_date > as_at`` are not yet effective — the view's share basis is
    the one at ``as_at``, so a future split never rescales the past.

    Cash dividends contribute nothing.  Any eligible in-window event that is
    unsupported, unconfirmed, or carries an invalid/unknown/mismatched value
    raises :class:`ViewRefusal` — never a silent skip.
    """
    _require_date(t, what="t")
    _require_aware(as_at, what="as_at")
    if not isinstance(revisions, ActionRevisionSet):
        raise TypeError(
            f"revisions must be an ActionRevisionSet, got {type(revisions).__name__}"
        )
    as_at_day = as_at.astimezone(timezone.utc).date()
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
    executed; an adjusted level is a level nobody ever traded at).
    """

    basis: str
    rows: tuple[Mapping, ...]
    reference: AdjustmentReference
    executable: bool

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


def raw_view(rows) -> PriceView:
    """The printed tape, validated as all-``<field>_raw`` and executable (D00.D3).

    RAW is never adjusted, but it is EXACT: every price column and
    ``volume_raw`` is coerced to a ``Fraction`` (float / bool / unparseable ->
    NON_EXACT_INPUT, like every other view) in a COPY of each row; every other
    key passes through unchanged and input rows are never mutated.  The column
    law above still applies, so a vendor-adjusted series can never be labelled
    RAW — the exact DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT failure mode.
    """
    materialized = tuple(rows)
    for row in materialized:
        if not isinstance(row, Mapping):
            raise TypeError(f"rows must be mappings, got {type(row).__name__}")
    per_row = _validate_price_columns(materialized)
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
    )


def sadj_view(rows, revisions: ActionRevisionSet, as_at: datetime, *, quantity_convention: str = "shares") -> PriceView:
    """The split-adjusted view: ``P_raw(t) / S(t)`` per row, never twice (D00.D3).

    Every input price column must be ``<field>_raw`` (see the column law above);
    every price and ``volume_raw`` value is coerced to an exact ``Fraction``.
    Output rows carry only ``date``, ``<field>_sadj`` and ``volume_sadj``;
    input rows are never mutated.  The view is never executable and its
    reference names the action revision set and the ``as_at`` instant, so the
    number is reproducible against the recorded revisions.  A row dated after
    the UTC date of ``as_at`` refuses ROW_AFTER_AS_AT.
    """
    if quantity_convention != "shares":
        raise ViewRefusal(
            f"quantity convention {quantity_convention!r} is unsupported (only 'shares')",
            reason=RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION,
        )
    _require_aware(as_at, what="as_at")
    as_at_day = as_at.astimezone(timezone.utc).date()
    if not isinstance(revisions, ActionRevisionSet):
        raise TypeError(
            f"revisions must be an ActionRevisionSet, got {type(revisions).__name__}"
        )
    materialized = tuple(rows)
    for row in materialized:
        if not isinstance(row, Mapping):
            raise TypeError(f"rows must be mappings, got {type(row).__name__}")
    per_row = _validate_price_columns(materialized)
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
        factor = split_factor(day, revisions, as_at)
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
    q0=1,
) -> TotalReturnView:
    """The house TOTAL_RETURN oracle over a raw close series (D00.D3, O2-P04).

    ``rows`` are date-ordered mappings each carrying ``date`` and an exact
    ``close_raw``; ``t0``/``t1`` are the first/last row dates and ``p0``/``p1``
    their closes.  The column law above applies verbatim: any non-raw price
    column refuses (``*_tradj`` -> NON_RAW_INPUT, ``*_sadj`` ->
    DOUBLE_ADJUST_RISK) — a vendor TRADJ series is never an input to this view.

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

    ``q0`` (default 1) is the starting share count and must be exact and
    positive.  Every output is an exact ``Fraction``.
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
        raise ValueError(f"q0 must be a positive share count, got {q_start}")
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
    close_by_day: dict[date, Fraction] = {}
    previous_day: date | None = None
    for row in materialized:
        if "date" not in row:
            raise TypeError(f"row is missing its 'date' member: {dict(row)!r}")
        day = _require_date(row["date"], what="row date")
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
        raise ValueError(f"close_raw at t0 must be positive, got {p0}")

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
    for event in in_window:  # resolve() already (ex_date, sequence)-ordered
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
        if event.currency is None or _norm_currency(event.currency) != policy.currency:
            raise ViewRefusal(
                f"cash dividend {event.event_id!r} is in "
                f"{event.currency!r}, not the policy's {policy.currency!r} — no "
                f"FX is applied in any view (D00.D3)",
                reason=RefusalReason.UNKNOWN_FX,
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
            q += amount / ex_close

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
