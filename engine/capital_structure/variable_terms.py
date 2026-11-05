"""Capital-structure V2 task I2a: variable, reset and contingent term evaluators.

Every function here is pure: no I/O, no clock, no module state and no network.
Each one reads an already-admitted structured term
(:mod:`engine.capital_structure.issuer_state_contracts`, SPEC_I2 §1.5) plus the
exact inputs a scenario supplies, and returns an exact
:class:`~fractions.Fraction` or a NAMED :class:`Unknown` — never both, never a
guess, and never ``0`` in place of an unknown.

The three harms this module exists to keep out of a supply answer are structural,
not stylistic:

* **No assumed floor and no universal finite maximum** (masterplan L231, A26).
  A floating conversion price with no floor in the complete agreement is
  reported as ``unbounded_by_contract`` by :func:`maximum_issuable`; it is never
  turned into a finite "maximum dilution" figure and never into infinity.  An
  unestablished floor is ``floor_not_established_<instrument>``, an Unknown.
* **Exclusive branches are alternatives, never a sum** (A24).
  :func:`settle_branch` prices ONE branch; the caller evaluates every admitted
  branch separately and only the elected one reaches an envelope.
* **A limit on delivery never shrinks the claim** (A25).
  :func:`exchange_cap_remaining` reports what a cap leaves deliverable; it says
  nothing about the claim, which the caller keeps whole.

No evaluator looks ahead: every price read uses only path points dated on or
before the date being priced, and a path point is one TRADING day, never one
calendar day.  Exact arithmetic only — a float is refused by the contracts
module before it can reach here, and nothing here produces one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal, localcontext
from fractions import Fraction
from typing import Any, Mapping, NamedTuple, Sequence

from engine.capital_structure.issuer_state_contracts import (
    PRICE_MEASURES,
    SETTLEMENT_BRANCH_NAMES,
    AntiDilution,
    Accrual,
    ContractViolation,
    ConversionCondition,
    EconomicTerm,
    PriceComponent,
    PriceFormula,
    Quantity,
    ResetSchedule,
    Unknown,
)
# The contracts module's ONE exact-decimal validator (regex, finiteness and
# non-negativity, refusing with ContractViolation).  It is imported rather than
# re-spelled so a scenario assumption can never drift from the rule a Quantity
# value obeys (SPEC_I2 §0 item 3, audit S4).
from engine.capital_structure.issuer_state_contracts import _decimal as _exact_decimal_text

IMPLEMENTATION = "capital_structure.variable_terms.v1"

#: The scenario assumption that declares what a path point MEASURES.  A
#: ``daily_vwap`` declaration is a scenario assumption and is never a fact.
PATH_MEASURE_ASSUMPTION = "price_path_measure"
DEFAULT_PATH_MEASURE = "closing_price"
#: The scenario assumptions an anti-dilution issuance is read from (SPEC_I2 §2.5).
DILUTIVE_ISSUANCE_SHARES = "dilutive_issuance_shares"
DILUTIVE_ISSUANCE_PRICE = "dilutive_issuance_price"
#: The UnknownResolution a broad weighted-average base must come from.
BROAD_BASE_PREFIX = "broad_base_"

#: Blocker names this module raises; the caller carries them into its trace.
BLOCKER_FLOOR_MAKE_WHOLE = "floor_reached_cash_make_whole"
#: The ``below_floor`` rule that owes the holder a cash make-whole.
BELOW_FLOOR_MAKE_WHOLE = "floor_applies_with_cash_make_whole"
BLOCKER_ANTI_DILUTION_NOT_TRIGGERED = "anti_dilution_not_triggered"
BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED = "shareholder_approval_required"
BLOCKER_EXCHANGE_CAP_REACHED = "exchange_cap_reached"
TRACE_ACCRUED_NOT_CONVERTED = "accrued_not_converted"
#: S6: a sparse ``including_pricing_date`` window is visible, never silent.
TRACE_WINDOW_LAST_POINT_BEFORE_PRICING_DATE = "window_last_point_before_pricing_date"
#: M4: the §2.5 methods that apply NO floor, so a later step can carry the price
#: below any floor the formula states and the contract itself bounds nothing.
FLOOR_BYPASSING_ANTI_DILUTION = (
    "full_ratchet",
    "weighted_average_narrow",
    "weighted_average_broad",
)
TRACE_ANTI_DILUTION_BYPASSES_FLOOR = "anti_dilution_bypasses_floor"
TRACE_STATED_FLOOR_IS_ZERO = "stated_floor_is_zero"
TRACE_RESET_EVENT_FLOOR_NOT_STATED = "reset_event_floor_not_stated"
#: S2: authorized-share headroom is joined later, by the joint capacity model and
#: the issuer state — never here, and the trace says so out loud.
TRACE_AUTHORIZED_SHARES_NOT_EVALUATED = "authorized_shares_not_evaluated_here"
#: M2: the count terms a PAST reset that adjusts shares must have evidenced.
COUNT_TERM_NAMES = ("instruments_outstanding", "shares_per_instrument")

AFFECTS_PRICE = ("as_converted_claims", "incremental_issuance")
AFFECTS_DELIVERY = ("incremental_issuance",)
AFFECTS_CASH = ("cash_effects",)

_ROUNDING_MODES = {"half_up": ROUND_HALF_UP, "down": ROUND_DOWN, "up": ROUND_UP}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _unknown(unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str]) -> Unknown:
    return Unknown(
        unknown_id=unknown_id,
        description=description,
        resolving_fact=resolving_fact,
        affects=tuple(sorted(set(affects))),
    )


def _exact(value: Fraction) -> str:
    """Exact text for a rational: an integer, a terminating decimal, or ``num/den``."""
    if value.denominator == 1:
        return str(value.numerator)
    reduced = value.denominator
    while reduced % 2 == 0:
        reduced //= 2
    while reduced % 5 == 0:
        reduced //= 5
    if reduced == 1:
        with localcontext() as context:
            context.prec = 60
            text = format(Decimal(value.numerator) / Decimal(value.denominator), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
    return f"{value.numerator}/{value.denominator}"


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def exact_decimal(value: Any, field_name: str) -> Fraction:
    """One exact decimal string as a :class:`~fractions.Fraction`.

    This is the contracts module's own validation, so ``NaN``, an infinity, an
    exponent form, garbage text, a float and a negative are each refused with
    :class:`ContractViolation` and never with another exception type.  A
    scenario assumption is exact text or it is nothing (audit S4).
    """
    return Fraction(Decimal(_exact_decimal_text(value, field_name)))


def _quantity_value(quantity: Quantity | None, field_name: str) -> Fraction | None:
    """The exact value of a known quantity; ``None`` when it states no number."""
    if quantity is None:
        return None
    _require(isinstance(quantity, Quantity), f"{field_name}: a Quantity is required")
    if quantity.status != "known" or quantity.value is None:
        return None
    return Fraction(Decimal(quantity.value))


def _known(quantity: Quantity | None, field_name: str) -> Fraction:
    value = _quantity_value(quantity, field_name)
    _require(value is not None, f"{field_name}: a known quantity is required")
    assert value is not None
    return value


def _is_admitted_value(term: Any) -> bool:
    return (
        isinstance(term, EconomicTerm)
        and term.status == "admitted"
        and term.value is not None
        and term.value.status == "known"
        and term.value.value is not None
    )


def _round(value: Fraction, rounding: Any) -> Fraction:
    """Round an exact rational to the contract's stated places and mode."""
    quantum = Decimal(1).scaleb(-int(rounding.places))
    with localcontext() as context:
        context.prec = 60
        exact = Decimal(value.numerator) / Decimal(value.denominator)
        rounded = exact.quantize(quantum, rounding=_ROUNDING_MODES[rounding.mode])
    return Fraction(rounded)


def _add_months(day: date, months: int) -> date:
    """The same day-of-month ``months`` later, clamped to the target month's end."""
    total = (day.year * 12 + (day.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last = (following - timedelta(days=1)).day
    return date(year, month, min(day.day, last))


def _thirty_360_days(start: date, end: date) -> int:
    """The 30/360 bond basis day count (ISDA 2006 §4.16(f))."""
    first = 30 if start.day == 31 else start.day
    second = end.day
    if second == 31 and first in (30, 31):
        second = 30
    return 360 * (end.year - start.year) + 30 * (end.month - start.month) + (second - first)


def _year_fraction(start: date, end: date, day_count: str) -> Fraction:
    """The accrual fraction of ``[start, end]``; never negative."""
    if end <= start:
        return Fraction(0)
    if day_count == "actual_365":
        return Fraction((end - start).days, 365)
    if day_count == "actual_360":
        return Fraction((end - start).days, 360)
    return Fraction(_thirty_360_days(start, end), 360)


def _as_date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    _require(isinstance(value, str) and bool(value), f"{field_name}: an ISO date is required")
    return date.fromisoformat(str(value)[:10])


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermResult:
    """One evaluator's exact outcome.

    Exactly one of ``value`` and ``unknown`` is set, except where a function
    documents a third state: :func:`formula_price` can return a known price AND
    a make-whole unknown, and :func:`apply_resets` / :func:`anti_dilution_price`
    also carry an adjusted ``count``.
    """

    value: Fraction | None = None
    unknown: Unknown | None = None
    trace_items: tuple[tuple[str, str], ...] = ()
    blockers: tuple[str, ...] = ()
    count: Fraction | None = None
    extra_unknowns: tuple[Unknown, ...] = ()

    @property
    def trace(self) -> dict[str, str]:
        """The trace as a dict of strings."""
        return dict(self.trace_items)


class BranchSettlement(NamedTuple):
    """One settlement branch priced on its own: shares, cash kind, cash amount."""

    shares: int
    cash_kind: str
    cash_amount: Fraction


# ---------------------------------------------------------------------------
# Path conventions (SPEC_I2 §2)
# ---------------------------------------------------------------------------


def path_measure_of(other_assumptions: Any) -> str:
    """What the scenario's path points measure: ``closing_price`` unless declared."""
    for entry in other_assumptions or ():
        key, value = entry
        if key == PATH_MEASURE_ASSUMPTION:
            _require(
                value in PRICE_MEASURES,
                f"scenario.other_assumptions[{PATH_MEASURE_ASSUMPTION}]: {value!r} is not a price measure",
            )
            return str(value)
    return DEFAULT_PATH_MEASURE


def _window(
    path: Sequence[Sequence[str]], pricing_date: str, points: int, window_end: str
) -> tuple[tuple[str, str], ...] | None:
    """The last ``points`` path points in the window; ``None`` when it is short.

    No point dated after ``pricing_date`` is ever read: that is the no-look-ahead
    law (SPEC_I2 §0 item 7), and it is why the window is filtered before it is
    counted.  ``points`` counts PATH points, never calendar days.
    """
    inclusive = window_end == "including_pricing_date"
    dated = [
        (str(point[0]), str(point[1]))
        for point in (path or ())
        if (point[0] <= pricing_date if inclusive else point[0] < pricing_date)
    ]
    if len(dated) < points:
        return None
    return tuple(dated[-points:])


def _window_values(points: Sequence[Sequence[str]]) -> list[Fraction]:
    return [Fraction(Decimal(str(point[1]))) for point in points]


# ---------------------------------------------------------------------------
# 2.1 component_price
# ---------------------------------------------------------------------------


def component_price(
    component: PriceComponent,
    path: Sequence[Sequence[str]],
    pricing_date: str,
    path_measure: str,
    inst: str,
) -> TermResult:
    """One price component at ``pricing_date``: a fixed price, or a window aggregate.

    ``period_vwap`` is Unknown: a price path carries no volume, so a
    volume-weighted average over a period is not computable from it and is never
    approximated by an unweighted one.
    """
    _require(isinstance(component, PriceComponent), "component_price.component: a PriceComponent is required")
    if component.source == "fixed":
        value = _quantity_value(component.fixed_price, "price_component.fixed_price")
        if value is None:
            return TermResult(unknown=_not_established(inst, "fixed_price_not_established", "the fixed price component states no known amount"))
        return TermResult(
            value=value,
            trace_items=(("path_points_are_trading_days", "true"), ("component_source", "fixed")),
        )
    if component.measure != path_measure:
        return TermResult(
            unknown=_unknown(
                f"price_measure_mismatch_{inst}",
                f"the price formula reads {component.measure} but the scenario path declares {path_measure}",
                f"a scenario other_assumptions entry ({PATH_MEASURE_ASSUMPTION!r}, {component.measure!r}), "
                "or a path of the measure the formula reads",
                AFFECTS_PRICE,
            ),
            trace_items=(("path_points_are_trading_days", "true"),),
        )
    if component.aggregation == "period_vwap":
        return TermResult(
            unknown=_unknown(
                f"period_vwap_needs_volume_{inst}",
                "the price formula is a period VWAP, and a price path carries no volume",
                "a retained volume-weighted average price for the period, admitted as a term",
                AFFECTS_PRICE,
            ),
            trace_items=(("path_points_are_trading_days", "true"),),
        )
    assert component.lookback_days is not None and component.window_end is not None
    points = _window(path, pricing_date, component.lookback_days, component.window_end)
    if points is None:
        return TermResult(
            unknown=_unknown(
                f"price_window_not_covered_{inst}",
                f"the scenario price path does not cover the {component.lookback_days} trading days "
                f"the formula reads before {pricing_date}",
                f"a price path with at least {component.lookback_days} points dated in the window",
                AFFECTS_PRICE,
            ),
            trace_items=(("path_points_are_trading_days", "true"),),
        )
    values = _window_values(points)
    aggregation = component.aggregation
    if aggregation == "single_day":
        measure = values[-1]
    elif aggregation == "lowest_daily":
        measure = min(values)
    elif aggregation == "average_daily":
        measure = sum(values, Fraction(0)) / Fraction(len(values))
    else:
        assert component.lowest_count is not None
        lowest = sorted(values)[: component.lowest_count]
        measure = sum(lowest, Fraction(0)) / Fraction(len(lowest))
    percent = _quantity_value(component.percent_of_measure, "price_component.percent_of_measure")
    if percent is None:
        return TermResult(
            unknown=_not_established(inst, "percent_of_measure_not_established", "the price formula states no known percentage of the measure"),
            trace_items=(("path_points_are_trading_days", "true"),),
        )
    trace: list[tuple[str, str]] = [
        ("path_points_are_trading_days", "true"),
        ("component_source", "market"),
        ("component_measure", str(component.measure)),
        ("component_aggregation", str(aggregation)),
        ("component_window_end", str(component.window_end)),
        ("component_window_start", points[0][0]),
        ("component_window_end_date", points[-1][0]),
        ("component_measure_value", _exact(measure)),
        ("component_percent_of_measure", _exact(percent)),
    ]
    if component.window_end == "including_pricing_date" and points[-1][0] < str(pricing_date):
        # S6: the window is SPARSE at the pricing date — no point is dated on D,
        # so the last point read is an earlier trading day.  The price is still
        # the contract's price (a path point is one trading day, never one
        # calendar day), but the gap is visible instead of silent.
        trace.append((TRACE_WINDOW_LAST_POINT_BEFORE_PRICING_DATE, "true"))
    return TermResult(value=measure * percent / 100, trace_items=tuple(trace))


def _not_established(inst: str, what: str, description: str) -> Unknown:
    return _unknown(
        f"{what}_{inst}",
        description,
        "a retained-byte term stating the amount, bound by an adjudicated identity decision",
        AFFECTS_PRICE,
    )


# ---------------------------------------------------------------------------
# 2.2 formula_price
# ---------------------------------------------------------------------------


def formula_price(
    formula: PriceFormula,
    path: Sequence[Sequence[str]],
    pricing_date: str,
    path_measure: str,
    inst: str,
) -> TermResult:
    """The formula's price at ``pricing_date``: components, ceiling, floor, rounding.

    Any Unknown component makes the whole result Unknown — a ``lesser`` of one
    known and one unknown price is never the known price alone, because that
    would silently pick the branch the contract might not have picked.

    The floor is applied ONLY when ``floor_basis == "stated"``.  A formula with
    ``none_in_complete_agreement`` or ``not_established`` is priced with no floor
    at all and the trace says so: no floor is ever assumed (masterplan L231).
    """
    _require(isinstance(formula, PriceFormula), "formula_price.formula: a PriceFormula is required")
    trace: list[tuple[str, str]] = [
        ("path_points_are_trading_days", "true"),
        ("pricing_date", str(pricing_date)),
        ("path_measure", str(path_measure)),
        ("combine", formula.combine),
        ("floor_basis", formula.floor_basis),
    ]
    priced: list[Fraction] = []
    blockers: list[str] = []
    for index, component in enumerate(formula.components):
        result = component_price(component, path, pricing_date, path_measure, inst)
        trace.extend((f"component_{index}_{key}", value) for key, value in result.trace_items)
        blockers.extend(result.blockers)
        if result.unknown is not None:
            return TermResult(
                unknown=result.unknown,
                trace_items=tuple(trace),
                blockers=tuple(blockers),
                extra_unknowns=result.extra_unknowns,
            )
        assert result.value is not None
        priced.append(result.value)
    if formula.combine == "single":
        value = priced[0]
    elif formula.combine == "lesser":
        value = min(priced)
    else:
        value = max(priced)
    trace.append(("combined_price", _exact(value)))
    if formula.ceiling is not None:
        ceiling = _quantity_value(formula.ceiling, "price_formula.ceiling")
        if ceiling is None:
            return TermResult(
                unknown=_not_established(inst, "ceiling_not_established", "the price formula states a ceiling with no known amount"),
                trace_items=tuple(trace),
            )
        if value > ceiling:
            trace.append(("ceiling_reached", "true"))
            value = ceiling
        else:
            trace.append(("ceiling_reached", "false"))
    floor_reached = False
    if formula.floor_basis == "stated":
        floor = _quantity_value(formula.floor, "price_formula.floor")
        if floor is None:
            return TermResult(
                unknown=_not_established(inst, "floor_not_established", "the price formula states a floor with no known amount"),
                trace_items=tuple(trace),
            )
        if value < floor:
            floor_reached = True
            value = floor
        trace.append(("floor", _exact(floor)))
    trace.append(("floor_reached", "true" if floor_reached else "false"))
    if formula.rounding is not None:
        value = _round(value, formula.rounding)
        trace.append(("rounded_price", _exact(value)))
    extra: tuple[Unknown, ...] = ()
    if floor_reached and formula.below_floor == BELOW_FLOOR_MAKE_WHOLE:
        blockers.append(BLOCKER_FLOOR_MAKE_WHOLE)
        extra = (
            _unknown(
                f"make_whole_amount_{inst}",
                "the floor bound the conversion price, and the contract requires a cash make-whole "
                "whose amount is not stated by any admitted term",
                f"a retained-byte make-whole amount for instrument {inst}, or the holder's election",
                AFFECTS_CASH,
            ),
        )
    return TermResult(value=value, trace_items=tuple(trace), blockers=tuple(blockers), extra_unknowns=extra)


# ---------------------------------------------------------------------------
# 2.3 maximum_issuable
# ---------------------------------------------------------------------------


def _unbounded(body: dict[str, Any], limits: Sequence[str], **flags: str) -> dict[str, Any]:
    """The one shape a floating price may report: unbounded, and saying why."""
    body.update(
        {
            "state": "unbounded_by_contract",
            "binding_limits": [str(item) for item in limits],
            # S2: authorized-share headroom is joined later, by the joint
            # capacity model and the issuer state.  I2 never joins it, and the
            # trace says so rather than letting a reader assume it was checked.
            TRACE_AUTHORIZED_SHARES_NOT_EVALUATED: "true",
        }
    )
    body.update(flags)
    return body


def maximum_issuable(
    formula: PriceFormula | None,
    amount: Fraction,
    inst: str,
    limits: Sequence[str] = (),
    anti_dilution: AntiDilution | None = None,
    schedule: ResetSchedule | None = None,
) -> dict[str, Any]:
    """What the contract itself bounds, as a trace row — never a Quantity.

    A floating price with no floor in the complete agreement is
    ``unbounded_by_contract``: this is the one place the module says so out
    loud, and it never converts that into a finite maximum or into infinity
    (A26, masterplan L231).  ``binding_limits`` names the OTHER limits that do
    bind — an exchange cap that shareholder approval has not lifted — because
    they bound delivery without bounding the claim.

    The bound is taken from the LOWEST price any stated term can reach, not
    from the formula floor alone (audit M4):

    * §2.5 anti-dilution applies NO floor, so a ``full_ratchet`` or a weighted
      average can carry the price below the formula's floor and the contract
      bounds nothing — ``anti_dilution_bypasses_floor`` says so;
    * §2.4 resets DO apply the EVENT floor, so every event floor lowers the
      bound, and an event with no stated floor (or a floor of exactly zero)
      leaves the price unbounded;
    * a stated floor of exactly ``0`` bounds nothing either.  It is not a
      division by zero and it is not ``floor_not_established`` (audit N2);
    * ``not_established`` stays the Unknown it always was.
    """
    _require(isinstance(amount, Fraction), "maximum_issuable.amount: an exact Fraction is required")
    if anti_dilution is not None:
        _require(isinstance(anti_dilution, AntiDilution), "maximum_issuable.anti_dilution: an AntiDilution is required")
    if schedule is not None:
        _require(isinstance(schedule, ResetSchedule), "maximum_issuable.schedule: a ResetSchedule is required")
    body: dict[str, Any] = {"amount": _exact(amount)}
    if formula is None:
        body.update({"state": "no_price_formula"})
        return body
    body["floor_basis"] = formula.floor_basis
    stated: Fraction | None = None
    if formula.floor_basis == "stated":
        stated = _quantity_value(formula.floor, "price_formula.floor")
        if stated is None:
            body.update({"state": "unknown", "unknown_id": f"floor_not_established_{inst}"})
            return body
    elif formula.floor_basis != "none_in_complete_agreement":
        body.update({"state": "unknown", "unknown_id": f"floor_not_established_{inst}"})
        return body
    if anti_dilution is not None and anti_dilution.method in FLOOR_BYPASSING_ANTI_DILUTION:
        return _unbounded(body, limits, **{TRACE_ANTI_DILUTION_BYPASSES_FLOOR: anti_dilution.method})
    if stated == 0:
        return _unbounded(body, limits, **{TRACE_STATED_FLOOR_IS_ZERO: "true"})
    floors: list[Fraction] = [] if stated is None else [stated]
    if schedule is not None and floors:
        for event in schedule.events:
            event_floor = _quantity_value(event.floor, "reset_event.floor")
            if event_floor is None or event_floor == 0:
                return _unbounded(
                    body, limits, **{TRACE_RESET_EVENT_FLOOR_NOT_STATED: str(event.reset_date)}
                )
            floors.append(event_floor)
    if not floors:
        return _unbounded(body, limits)
    bound = min(floors)
    body.update({"state": "bounded_by_floor", "floor": _exact(bound), "shares": str(_floor(amount / bound))})
    return body


# ---------------------------------------------------------------------------
# 2.4 apply_resets
# ---------------------------------------------------------------------------


def _reset_evidenced(applies_to: str, reset_date: date, terms: Any) -> bool:
    """Whether an admitted price term dated on or after the reset evidences it."""
    term = terms.get(applies_to) if isinstance(terms, Mapping) else None
    if not isinstance(term, EconomicTerm) or term.status != "admitted" or term.effective_at is None:
        return False
    return _as_date(term.effective_at, "economic_term.effective_at") >= reset_date


def _count_evidence(reset_date: date, terms: Any) -> tuple[str, ...]:
    """The admitted COUNT terms dated on or after a past reset (audit M2).

    A reset that adjusts the share count states two facts, not one: the new
    price AND the new count.  Only an admitted ``shares_per_instrument`` or
    ``instruments_outstanding`` term dated on or after the reset date evidences
    the second one; the pre-reset count is never carried across a reset that
    changed it, because that would report the pre-reset supply as a fact.
    """
    if not isinstance(terms, Mapping):
        return ()
    evidenced: list[str] = []
    for name in COUNT_TERM_NAMES:
        term = terms.get(name)
        if not _is_admitted_value(term) or term.effective_at is None:
            continue
        if _as_date(term.effective_at, "economic_term.effective_at") >= reset_date:
            evidenced.append(name)
    return tuple(evidenced)


def _evidenced_count(terms: Any) -> Fraction | None:
    """The share count the admitted count terms state, or ``None`` if incomplete."""
    if not isinstance(terms, Mapping):
        return None
    count = Fraction(1)
    for name in COUNT_TERM_NAMES:
        term = terms.get(name)
        if not _is_admitted_value(term):
            return None
        count *= _known(term.value, f"economic_term[{name}].value")
    return count


def apply_resets(
    schedule: ResetSchedule,
    base_price: Fraction | None,
    base_count: Fraction | None,
    terms: Any,
    scenario: Any,
    inst: str,
) -> TermResult:
    """Apply the schedule's events in date order to ``base_price``/``base_count``.

    Three date classes, three different treatments:

    * **past** (``reset_date <= scenario.as_of``): the outcome is a FACT, and a
      fact is only what an admitted price term dated on or after the reset date
      states.  With no such term the outcome is Unknown — the formula is never
      re-run backwards to invent one.
    * **inside the horizon** (``as_of < reset_date <= horizon_end``): price the
      event's market component AT the reset date, apply the rule, then the
      event's floor.
    * **beyond the horizon**: not applied, and listed in the trace as
      ``future_reset`` — a scenario never books a reset it does not reach.
    """
    _require(isinstance(schedule, ResetSchedule), "apply_resets.schedule: a ResetSchedule is required")
    path = scenario.price.path
    path_measure = path_measure_of(scenario.other_assumptions)
    as_of = _as_date(scenario.as_of, "scenario.as_of")
    horizon_end = _as_date(scenario.horizon_end, "scenario.horizon_end")
    price = base_price
    count = base_count
    trace: list[tuple[str, str]] = [
        ("path_points_are_trading_days", "true"),
        ("reset_applies_to", schedule.applies_to),
        ("reset_as_of", as_of.isoformat()),
        ("reset_horizon_end", horizon_end.isoformat()),
    ]
    future: list[str] = []
    past: list[str] = []
    for event in schedule.events:
        reset_date = _as_date(event.reset_date, "reset_event.reset_date")
        if reset_date <= as_of:
            if not _reset_evidenced(schedule.applies_to, reset_date, terms):
                return TermResult(
                    value=None,
                    count=count,
                    unknown=_unknown(
                        f"reset_outcome_not_evidenced_{inst}_{event.reset_date}",
                        f"the {event.reset_date} reset of instrument {inst} is already past, and no admitted "
                        f"{schedule.applies_to} term dated on or after it states the outcome",
                        f"an admitted {schedule.applies_to} term with an effective_at on or after {event.reset_date}",
                        AFFECTS_PRICE,
                    ),
                    trace_items=tuple(trace),
                )
            past.append(event.reset_date)
            trace.append((f"past_reset_{event.reset_date}", "evidenced_by_admitted_term"))
            if event.share_adjustment != "none" and count is not None:
                # M2: the reset changed the count, so the count is a second fact
                # that needs its own evidence.  Without it the row is Unknown and
                # never the pre-reset count.
                evidenced_names = _count_evidence(reset_date, terms)
                if not evidenced_names:
                    return TermResult(
                        value=None,
                        count=count,
                        unknown=_unknown(
                            f"reset_share_adjustment_not_evidenced_{inst}_{reset_date.isoformat()}",
                            f"the {event.reset_date} reset of instrument {inst} is already past and adjusts the "
                            f"share count ({event.share_adjustment}), but no admitted count term dated on or after "
                            "it states the adjusted count",
                            f"an admitted shares_per_instrument or instruments_outstanding term for instrument "
                            f"{inst} with an effective_at on or after {reset_date.isoformat()}",
                            AFFECTS_PRICE,
                        ),
                        trace_items=tuple(trace),
                    )
                adjusted = _evidenced_count(terms)
                if adjusted is not None:
                    count = adjusted
                trace.append((f"past_reset_count_{event.reset_date}", ",".join(evidenced_names)))
            continue
        if reset_date > horizon_end:
            future.append(event.reset_date)
            continue
        market = component_price(event.market, path, event.reset_date, path_measure, inst)
        if market.unknown is not None:
            return TermResult(value=None, count=count, unknown=market.unknown, trace_items=tuple(trace))
        assert market.value is not None
        if price is None:
            return TermResult(
                value=None,
                count=count,
                unknown=_unknown(
                    f"reset_base_price_{inst}",
                    f"the {event.reset_date} reset of instrument {inst} is inside the horizon, but the price "
                    "it resets from is not known, so the reset outcome is not computable",
                    f"a known {schedule.applies_to} for instrument {inst}, or a scenario that does not reach the reset",
                    AFFECTS_PRICE,
                ),
                trace_items=tuple(trace),
            )
        new_price = market.value
        if event.rule == "set_to_lesser_of_current_and_market":
            new_price = min(price, new_price)
        event_floor = _quantity_value(event.floor, "reset_event.floor")
        if event_floor is not None and new_price < event_floor:
            new_price = event_floor
            trace.append((f"reset_floor_applied_{event.reset_date}", _exact(event_floor)))
        old_price = price
        price = new_price
        trace.append((f"reset_applied_{event.reset_date}", _exact(price)))
        if event.share_adjustment == "preserve_aggregate_exercise_price":
            if count is not None and old_price not in (None, Fraction(0)) and price != 0:
                adjusted = count * old_price / price
                trace.append(
                    (
                        f"reset_share_adjustment_{event.reset_date}",
                        f"{_exact(count)}*{_exact(old_price)}/{_exact(price)}={_exact(adjusted)}",
                    )
                )
                count = Fraction(_floor(adjusted))
            else:
                trace.append((f"reset_share_adjustment_{event.reset_date}", "not_applicable_without_a_count"))
    if past:
        trace.append(("past_reset", ",".join(past)))
    if future:
        trace.append(("future_reset", ",".join(future)))
    return TermResult(value=price, count=count, trace_items=tuple(trace))


# ---------------------------------------------------------------------------
# 2.5 anti_dilution_price
# ---------------------------------------------------------------------------


def anti_dilution_price(
    ad: AntiDilution,
    price: Fraction | None,
    issuance: Mapping[str, Fraction | None],
    existing: Fraction | None,
    inst: str,
    broad_base: Fraction | None = None,
    count: Fraction | None = None,
) -> TermResult:
    """The price-protection adjustment of one price, on scenario-stated issuance.

    The issuance is a SCENARIO ASSUMPTION, never a fact: it is read only from
    ``dilutive_issuance_shares`` and ``dilutive_issuance_price`` (SPEC_I2 §2.5).
    A broad weighted average needs a fully-diluted base, and contracts define
    "fully diluted" differently, so that base is NEVER computed here: it comes
    from an ``UnknownResolution`` for ``broad_base_<instrument>`` or the result
    is Unknown.
    """
    _require(isinstance(ad, AntiDilution), "anti_dilution_price.ad: an AntiDilution is required")
    trace: list[tuple[str, str]] = [
        ("anti_dilution_applies_to", ad.applies_to),
        ("anti_dilution_method", ad.method),
        ("anti_dilution_issuance_is_a_scenario_assumption", "true"),
    ]
    if ad.method == "none_in_complete_agreement":
        return TermResult(value=price, count=count, trace_items=tuple(trace))
    shares = issuance.get(DILUTIVE_ISSUANCE_SHARES) if issuance else None
    if shares is None:
        return TermResult(
            value=None,
            count=count,
            unknown=_unknown(
                f"dilutive_issuance_{inst}",
                f"anti-dilution applies to instrument {inst}, but the scenario states no "
                f"{DILUTIVE_ISSUANCE_SHARES} assumption",
                f"a scenario other_assumptions entry ({DILUTIVE_ISSUANCE_SHARES!r}, <shares>)",
                AFFECTS_PRICE,
            ),
            trace_items=tuple(trace),
        )
    issued_price = issuance.get(DILUTIVE_ISSUANCE_PRICE) if issuance else None
    if issued_price is None:
        return TermResult(
            value=None,
            count=count,
            unknown=_unknown(
                f"dilutive_issuance_price_{inst}",
                f"anti-dilution applies to instrument {inst}, but neither the scenario nor the horizon price "
                f"supplies a {DILUTIVE_ISSUANCE_PRICE}",
                f"a scenario other_assumptions entry ({DILUTIVE_ISSUANCE_PRICE!r}, <price>), a horizon price and a discount_rate",
                AFFECTS_PRICE,
            ),
            trace_items=tuple(trace),
        )
    trace.append(("dilutive_issuance_shares", _exact(shares)))
    trace.append(("dilutive_issuance_price", _exact(issued_price)))
    if price is None:
        return TermResult(
            value=None,
            count=count,
            unknown=_unknown(
                f"anti_dilution_base_price_{inst}",
                f"anti-dilution applies to instrument {inst}, but the price it protects is not known",
                f"a known {ad.applies_to} for instrument {inst}",
                AFFECTS_PRICE,
            ),
            trace_items=tuple(trace),
        )
    if issued_price >= price:
        # A higher-priced issuance dilutes nothing: no adjustment, and the guard
        # is recorded rather than the price being silently left alone.
        trace.append(("anti_dilution_triggered", "false"))
        return TermResult(value=price, count=count, blockers=(BLOCKER_ANTI_DILUTION_NOT_TRIGGERED,), trace_items=tuple(trace))
    trace.append(("anti_dilution_triggered", "true"))
    if ad.method == "full_ratchet":
        new_price = issued_price
    else:
        base = broad_base if ad.method == "weighted_average_broad" else existing
        if base is None:
            what = "anti_dilution_broad_base" if ad.method == "weighted_average_broad" else "anti_dilution_existing_base"
            description = (
                f"a broad weighted-average adjustment applies to instrument {inst}, and contracts define "
                '"fully diluted" differently, so the base is never computed here'
                if ad.method == "weighted_average_broad"
                else f"a weighted-average adjustment applies to instrument {inst}, but no share basis is selected"
            )
            resolving = (
                f"an UnknownResolution for {BROAD_BASE_PREFIX}{inst} carrying the contract's fully-diluted base"
                if ad.method == "weighted_average_broad"
                else "a selected issued_and_outstanding share basis"
            )
            return TermResult(
                value=None,
                count=count,
                unknown=_unknown(f"{what}_{inst}", description, resolving, AFFECTS_PRICE),
                trace_items=tuple(trace),
            )
        # CP2 = CP1 * (A + B) / (A + C), B = C * issuance_price / CP1.
        equivalent = shares * issued_price / price
        new_price = price * (base + equivalent) / (base + shares)
        trace.append(("anti_dilution_base", _exact(base)))
        trace.append(("anti_dilution_equivalent_shares", _exact(equivalent)))
    trace.append(("anti_dilution_price", _exact(new_price)))
    if ad.price_rounding is not None:
        new_price = _round(new_price, ad.price_rounding)
        trace.append(("anti_dilution_rounded_price", _exact(new_price)))
    if ad.share_adjustment == "preserve_aggregate_exercise_price":
        if count is not None and price != 0 and new_price != 0:
            adjusted = count * price / new_price
            trace.append(
                (
                    "anti_dilution_share_adjustment",
                    f"{_exact(count)}*{_exact(price)}/{_exact(new_price)}={_exact(adjusted)}",
                )
            )
            count = Fraction(_floor(adjusted))
        else:
            trace.append(("anti_dilution_share_adjustment", "not_applicable_without_a_count"))
    return TermResult(value=new_price, count=count, trace_items=tuple(trace))


# ---------------------------------------------------------------------------
# 2.6 accreted_amount
# ---------------------------------------------------------------------------


def accreted_amount(
    principal: Fraction,
    accrual: Accrual,
    accrued_term: Any,
    end: Any,
    inst: str,
) -> TermResult:
    """The amount owed at ``end``, and the part of it that actually converts.

    ``simple`` accrues on PRINCIPAL ONLY, whatever has already accrued: adding
    accrued amounts to the base would compound a contract that does not.  With
    an admitted ``accrued_amount_outstanding`` term the accrual starts from that
    stated figure at its own date, because a stated accrued amount is a fact and
    re-deriving it from the start date would be a second, possibly different,
    reading of the same contract.

    ``periodic`` compounds on a grid that is ALWAYS anchored to
    ``accrual_start``: the boundaries are ``accrual_start + k × period_months``
    and an evidenced amount never moves them (audit M1).  A stated balance is a
    fact about the BALANCE, not about the contract's compounding dates, so it
    re-bases the balance inside its own anchored period:

    * ``B`` = principal + the evidenced amount, stated at ``s``;
    * ``[p0, p1)`` is the anchored period containing ``s``;
    * the period's opening balance is ``Pk = B / (1 + r × yf(p0, s))``, so the
      evidence is read as the opening balance plus simple interest to ``s``;
    * the balance at ``p1`` is ``B + Pk × r × yf(s, p1)`` — simple interest on
      that opening balance, from ``s`` to the period end;
    * from ``p1`` the balance compounds on the anchored grid.

    An ``s`` exactly on a boundary gives ``yf(p0, s) = 0``, so ``Pk = B`` and the
    period compounds normally.  A partial final period earns SIMPLE interest on
    the RUNNING balance, never on the original principal (audit M1b): interest
    already compounded into the balance keeps earning, which is what compounding
    means.
    """
    _require(isinstance(accrual, Accrual), "accreted_amount.accrual: an Accrual is required")
    _require(isinstance(principal, Fraction), "accreted_amount.principal: an exact Fraction is required")
    end_date = _as_date(end, "accreted_amount.end")
    rate = _quantity_value(accrual.annual_rate, "accrual.annual_rate")
    if rate is None:
        return TermResult(
            unknown=_unknown(
                f"accrual_rate_{inst}",
                f"the accrual terms of instrument {inst} state no known annual rate",
                f"a retained-byte annual rate for instrument {inst}, bound by an adjudicated identity decision",
                AFFECTS_PRICE,
            )
        )
    rate = rate / 100
    start = _as_date(accrual.accrual_start, "accrual.accrual_start")
    cursor = start
    evidenced = Fraction(0)
    evidenced_at: date | None = None
    trace: list[tuple[str, str]] = [
        ("accrual_day_count", accrual.day_count),
        ("accrual_compounding", accrual.compounding),
        ("accrual_annual_rate", _exact(rate * 100)),
        ("accrual_start", cursor.isoformat()),
        ("accrual_end", end_date.isoformat()),
        ("accrual_principal", _exact(principal)),
    ]
    if _is_admitted_value(accrued_term):
        evidenced = Fraction(Decimal(accrued_term.value.value))
        stated_at = None
        if accrued_term.effective_at is not None:
            stated_at = _as_date(accrued_term.effective_at, "economic_term.effective_at")
            evidenced_at = stated_at
        if stated_at is None:
            return TermResult(
                unknown=_unknown(
                    f"accrued_amount_outstanding_{inst}",
                    f"the accrued amount of instrument {inst} is admitted but undated, so the accrual cannot "
                    "be continued from it without guessing a start date",
                    f"an admitted accrued_amount_outstanding term for instrument {inst} with an effective_at",
                    AFFECTS_PRICE,
                )
            )
        cursor = stated_at
        trace.append(("accrued_amount_evidenced", _exact(evidenced)))
        trace.append(("accrued_amount_evidenced_at", cursor.isoformat()))
    if accrual.compounding == "simple":
        # Simple accrual is always on PRINCIPAL only: never on what already accrued.
        accrued = evidenced + principal * rate * _year_fraction(cursor, end_date, accrual.day_count)
    else:
        assert accrual.period_months is not None
        period_months = accrual.period_months
        amount = principal + evidenced
        # M1: the grid is anchored to accrual_start, never stepped from the
        # evidenced date.
        period_start = start
        if evidenced_at is not None:
            while _add_months(period_start, period_months) <= evidenced_at:
                period_start = _add_months(period_start, period_months)
            trace.append(("accrual_evidenced_period_start", period_start.isoformat()))
        trace.append(("accrual_period_grid_anchored_at", start.isoformat()))
        periods = 0
        while True:
            boundary = _add_months(period_start, period_months)
            # The opening balance of the anchored period that contains `cursor`.
            # With no evidence cursor == period_start, so this is the running
            # balance and the step is ordinary compounding.
            opening = amount / (
                Fraction(1) + rate * _year_fraction(period_start, cursor, accrual.day_count)
            )
            if evidenced_at is not None and periods == 0:
                trace.append(("accrual_evidenced_period_opening_balance", _exact(opening)))
            if boundary > end_date:
                # M1b: the partial final period is simple interest on the RUNNING
                # balance — the period's opening balance — never on principal.
                amount = amount + opening * rate * _year_fraction(cursor, end_date, accrual.day_count)
                break
            amount = amount + opening * rate * _year_fraction(cursor, boundary, accrual.day_count)
            periods += 1
            period_start = boundary
            cursor = boundary
        trace.append(("accrual_periods_compounded", str(periods)))
        accrued = amount - principal
    trace.append(("accrued_amount", _exact(accrued)))
    owed = principal + accrued
    trace.append(("amount_owed", _exact(owed)))
    if accrual.converts_with_principal:
        return TermResult(value=owed, trace_items=tuple(trace))
    # The accrued amount is owed but does NOT convert: the claim stays principal
    # only, and the accrued figure is reported rather than silently dropped.
    trace.append((TRACE_ACCRUED_NOT_CONVERTED, _exact(accrued)))
    return TermResult(value=principal, trace_items=tuple(trace))


# ---------------------------------------------------------------------------
# 2.7 condition_met
# ---------------------------------------------------------------------------


def condition_met(
    cond: ConversionCondition,
    path: Sequence[Sequence[str]],
    pricing_date: str,
    path_measure: str,
    conversion_price: Fraction | None,
    inst: str,
) -> bool | None:
    """``True``/``False`` when the trading-day condition is evaluable, else ``None``.

    ``None`` is NOT ``False``: a window the path does not cover means the
    condition cannot be read, and treating that as unmet would convert an
    unknown into a denial of the holder's claim.
    """
    _require(isinstance(cond, ConversionCondition), "condition_met.cond: a ConversionCondition is required")
    if cond.measure != path_measure:
        return None
    points = _window(path, pricing_date, cond.window_days, cond.window_end)
    if points is None:
        return None
    threshold = _quantity_value(cond.threshold, "conversion_condition.threshold")
    if threshold is None:
        return None
    if cond.threshold_kind == "percent_of_conversion_price":
        if conversion_price is None or conversion_price == 0:
            return None
        threshold = conversion_price * threshold / 100
    values = _window_values(points)
    if cond.comparison == "at_or_above":
        qualifying = sum(1 for value in values if value >= threshold)
    else:
        qualifying = sum(1 for value in values if value <= threshold)
    return qualifying >= cond.required_days


# ---------------------------------------------------------------------------
# 2.8 settle_branch
# ---------------------------------------------------------------------------


def settle_branch(
    branch: str,
    amount: Fraction,
    conversion_price: Fraction,
    price: Fraction,
) -> BranchSettlement:
    """Price ONE settlement branch: ``(shares, cash_kind, cash_amount)``.

    The branches are exclusive.  This function prices exactly one of them and
    knows nothing about the others, so there is no code path in which two
    branches could be added together (A24, SPEC_I2 §0 item 5).
    """
    _require(branch in SETTLEMENT_BRANCH_NAMES, f"settle_branch.branch: {branch!r} is not a settlement branch")
    for name, value in (("amount", amount), ("conversion_price", conversion_price), ("price", price)):
        _require(isinstance(value, Fraction), f"settle_branch.{name}: an exact Fraction is required")
    _require(conversion_price != 0, "settle_branch.conversion_price: a zero conversion price converts nothing")
    underlying = amount / conversion_price
    if branch == "physical":
        return BranchSettlement(_floor(underlying), "no_cash", Fraction(0))
    conversion_value = underlying * price
    if branch == "cash":
        return BranchSettlement(0, "repayment", conversion_value)
    cash = min(amount, conversion_value)
    surplus = conversion_value - amount
    shares = 0 if surplus <= 0 or price == 0 else _floor(surplus / price)
    return BranchSettlement(shares, "repayment", cash)


# ---------------------------------------------------------------------------
# 2.9 exchange_cap_remaining
# ---------------------------------------------------------------------------


def exchange_cap_remaining(cap_term: Any, issued_term: Any, approval_term: Any, inst: str) -> TermResult:
    """What an exchange cap leaves deliverable — never what it leaves claimable.

    A cap limits DELIVERY.  This function returns a remaining share count and
    blockers; it returns nothing about the claim, so a caller cannot shrink a
    claim with it (A25, SPEC_I2 §0 item 6).  Shareholder approval removes the
    limit entirely; without it the cap binds and says so.
    """
    if isinstance(approval_term, EconomicTerm) and approval_term.status == "admitted" and approval_term.flag is True:
        return TermResult(value=None, trace_items=(("shareholder_approval_obtained", "true"),))
    if cap_term is None:
        return TermResult(value=None, trace_items=(("exchange_cap", "absent"),))
    if not _is_admitted_value(cap_term):
        return TermResult(
            unknown=_unknown(
                f"exchange_cap_shares_{inst}",
                f"the exchange cap of instrument {inst} is missing, contradicted or unknown, so the "
                "deliverable share count cannot be bounded",
                f"a retained-byte exchange_cap_shares term for instrument {inst}",
                AFFECTS_DELIVERY,
            ),
            trace_items=(("shareholder_approval_obtained", "false"),),
        )
    cap = Fraction(Decimal(cap_term.value.value))
    blockers = [BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED]
    trace: list[tuple[str, str]] = [
        ("shareholder_approval_obtained", "false"),
        ("exchange_cap", _exact(cap)),
    ]
    if not _is_admitted_value(issued_term):
        return TermResult(
            unknown=_unknown(
                f"shares_issued_under_instrument_{inst}",
                f"the exchange cap of instrument {inst} applies, but the share count already issued under it "
                "is not stated, so the remaining deliverable count is unknown",
                f"a retained-byte shares_issued_under_instrument term for instrument {inst}",
                AFFECTS_DELIVERY,
            ),
            blockers=tuple(blockers),
            trace_items=tuple(trace),
        )
    issued = Fraction(Decimal(issued_term.value.value))
    remaining = cap - issued
    if remaining < 0:
        remaining = Fraction(0)
    trace.append(("shares_issued_under_instrument", _exact(issued)))
    trace.append(("exchange_cap_remaining", _exact(remaining)))
    if remaining == 0:
        blockers.append(BLOCKER_EXCHANGE_CAP_REACHED)
    return TermResult(value=remaining, blockers=tuple(blockers), trace_items=tuple(trace))


__all__ = [
    "AFFECTS_CASH",
    "AFFECTS_DELIVERY",
    "AFFECTS_PRICE",
    "BELOW_FLOOR_MAKE_WHOLE",
    "BLOCKER_ANTI_DILUTION_NOT_TRIGGERED",
    "BLOCKER_EXCHANGE_CAP_REACHED",
    "BLOCKER_FLOOR_MAKE_WHOLE",
    "BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED",
    "BROAD_BASE_PREFIX",
    "BranchSettlement",
    "DEFAULT_PATH_MEASURE",
    "DILUTIVE_ISSUANCE_PRICE",
    "DILUTIVE_ISSUANCE_SHARES",
    "IMPLEMENTATION",
    "PATH_MEASURE_ASSUMPTION",
    "TermResult",
    "TRACE_ACCRUED_NOT_CONVERTED",
    "accreted_amount",
    "anti_dilution_price",
    "apply_resets",
    "component_price",
    "condition_met",
    "exact_decimal",
    "exchange_cap_remaining",
    "formula_price",
    "maximum_issuable",
    "path_measure_of",
    "settle_branch",
]
