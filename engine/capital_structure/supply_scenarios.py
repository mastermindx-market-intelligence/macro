"""Capital-structure V2 task I1a: share supply and cash consequences (SPEC_I1 §5).

``evaluate_supply`` is the owner-declared interface of this module
(``issuer_state_contracts.INTERFACE_OWNERSHIP``) and the only place where a
retained-byte warrant or convertible term becomes a share-supply or cash
consequence.  ``supply_trace`` is the same computation before projection: it
keeps the per-action rows, the claim remainders and the resale facts the frozen
``SupplyEnvelope`` has no field for.

Laws enforced here (gates A19, A20, A23, A24, A25, A48; lines L78, L100, L122):

* The four components — ``existing_outstanding``, ``incremental_issuance``,
  ``as_converted_claims`` and ``resalable_existing`` — are four different
  questions and are NEVER summed, in code, in the trace, in a note or in a
  record.  There is no total and no fully-diluted figure (L78).
* A resale of already outstanding shares mints no new share and no issuer cash
  (A23): it lands in ``resalable_existing`` and in a ``no_cash`` effect only.
* The four settlement kinds have distinct consequences (A24): cash pays the
  strike, cashless and net-share net the spread against the scenario price and
  pay nothing, a pre-funded warrant pays ONLY its residual (the prepaid part is
  never counted again, L100), and a conversion issues the contractual shares and
  pays nothing.
* A holder cap or a notice period limits the SCENARIO, never the claim: the
  instrument's full as-converted claim stays in ``as_converted_claims`` (A25).
* No universal split factor (A19).  ``basis.corporate_action`` is read for its
  kind and effective date only; a term that predates the split is stale and
  therefore unknown, and nothing is ever multiplied by the split factor.
* Unknown is never 0 and never unbounded: a missing, unreadable, contradicted,
  formula-only or stale term, an unselected share basis, an unresolved holder
  position, an unpriced horizon or a missing fee rate each produce a named
  ``Unknown`` and an ``unknown``-status Quantity.

Exact arithmetic only.  Share counts are :class:`~fractions.Fraction` floored to
whole shares with the remainder recorded in the trace; money is
:class:`~decimal.Decimal`.  No float is accepted or produced, and no score,
rank, sizing, probability or total is emitted.

``expiry`` terms are attached by
:mod:`engine.capital_structure.instrument_economics` but are NOT evaluated here:
I1a applies no expiry cut-off to a scenario horizon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Mapping, Sequence

from engine.capital_structure import variable_terms
from engine.capital_structure.issuer_state_contracts import (
    ECONOMIC_TERM_STRUCTURE_NAMES,
    ECONOMIC_TERM_UNITS,
    STRUCTURE_KINDS,
    ActionSelection,
    CalculationReceipt,
    CashEffect,
    ContractViolation,
    EconomicTerm,
    FinancingScenario,
    Instrument,
    InstrumentSet,
    PriceFormula,
    Quantity,
    ShareBasisResult,
    SupplyEnvelope,
    Unknown,
    sha256_of,
    stable_id,
)

#: Every ``kind`` a structured term writes, including the nested ones that carry
#: exact integers (SPEC_I2 §1.5).  Used to let an integer through the no-float
#: gate inside a structure and nowhere else.
_STRUCTURE_KIND_KEYS = frozenset(STRUCTURE_KINDS) | {"price_component", "reset_event", "rounding"}

IMPLEMENTATION = "capital_structure.supply_scenarios.v1"
TRACE_SCHEMA = "capital_structure.supply_trace.v1"

#: The §5.4 settlement table, transcribed verbatim as data.  The receipt's
#: ``rule_digest`` is the digest of THIS table, so changing a rule changes every
#: receipt instead of silently changing an answer.
SETTLEMENT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "warrant_exercise|cash",
        "incremental shares = n (the underlying shares selected, capped at the claim)",
        "proceeds: gross = n*K, net = gross*(1-fee_rate)",
    ),
    (
        "warrant_exercise|cashless",
        "incremental shares = n*(P-K)/P when P > K, else 0",
        "no_cash: gross = 0, net = 0",
    ),
    (
        "warrant_exercise|net_share",
        "incremental shares = n*(P-K)/P when P > K, else 0",
        "no_cash: gross = 0, net = 0",
    ),
    (
        "warrant_exercise|pre_funded",
        "incremental shares = n (pre_funded_warrant only)",
        "proceeds: gross = n*R only, the prepaid part is never counted again",
    ),
    (
        "conversion|cashless",
        "incremental shares = principal/C, or n when given, capped at principal/C",
        "no_cash: gross = 0, net = 0",
    ),
    (
        "conversion|net_share",
        "incremental shares = principal/C, or n when given, capped at principal/C",
        "no_cash: gross = 0, net = 0",
    ),
    (
        "resalable_existing|fact_not_an_action",
        "incremental shares = 0: already outstanding shares change hands",
        "no_cash: gross = 0, net = 0 (a resale is never issuer funding)",
    ),
)

#: Actions this module owns.  Every other route kind is a capacity route (C1/C2)
#: and contributes an Unknown here, never a share count (§5.3).
SUPPLY_ACTIONS = ("warrant_exercise", "conversion")
WARRANT_KINDS = ("warrant", "pre_funded_warrant")
CONVERTIBLE_KINDS = ("convertible_note", "convertible_preferred")
CLAIMED_KINDS = WARRANT_KINDS + CONVERTIBLE_KINDS
ELIGIBLE_STATUSES = ("outstanding", "amended")

ACTION_INSTRUMENT_KINDS: Mapping[str, tuple[str, ...]] = {
    "warrant_exercise": WARRANT_KINDS,
    "conversion": CONVERTIBLE_KINDS,
}
#: Which settlement each instrument kind may actually use (§5.4, D2).  A
#: cash-settled conversion is I2's, not a liberty this module may take.
PERMITTED_SETTLEMENTS: Mapping[str, tuple[str, ...]] = {
    "warrant": ("cash", "cashless", "net_share"),
    "pre_funded_warrant": ("pre_funded",),
    "convertible_note": ("cashless", "net_share"),
    "convertible_preferred": ("cashless", "net_share"),
}
NO_CASH_SETTLEMENTS = ("cashless", "net_share")

#: Terms whose value a split makes stale (A19, D9).
SPLIT_SENSITIVE_NAMES = (
    "exercise_price",
    "conversion_price",
    "prefunded_residual_price",
    "shares_per_instrument",
    "instruments_outstanding",
)
#: Terms an instrument's claim is built from (§5.8, D4).
CLAIM_TERMS: Mapping[str, tuple[str, ...]] = {
    "warrant": ("instruments_outstanding", "shares_per_instrument"),
    "pre_funded_warrant": ("instruments_outstanding", "shares_per_instrument"),
    "convertible_note": ("principal_outstanding", "conversion_price"),
    "convertible_preferred": ("principal_outstanding", "conversion_price"),
}
#: Extra terms one row needs on top of its claim terms (D6).
ROW_TERMS: Mapping[tuple[str, str], tuple[str, ...]] = {
    ("warrant_exercise", "cash"): ("exercise_price",),
    ("warrant_exercise", "cashless"): ("exercise_price",),
    ("warrant_exercise", "net_share"): ("exercise_price",),
    ("warrant_exercise", "pre_funded"): ("prefunded_residual_price",),
    ("conversion", "cashless"): (),
    ("conversion", "net_share"): (),
    # I2 (SPEC_I2 §1.2, §3.4): reachable only through a settlement_branches term.
    ("conversion", "physical"): (),
    ("conversion", "cash"): (),
}
#: Price terms a row needs from the scenario rather than from a term record (D8).
PRICE_SETTLEMENTS = ("cashless", "net_share")
CASH_PRICE_TERMS: Mapping[str, str] = {"cash": "exercise_price", "pre_funded": "prefunded_residual_price"}
LIMITER_NAMES = ("beneficial_ownership_cap", "notice_days")
RESALE_NAME = "resale_registered_shares"
CAP_NAME = "beneficial_ownership_cap"
NOTICE_NAME = "notice_days"

GUARD_COMPONENTS_NEVER_SUMMED = "components_never_summed"
GUARD_RESALE_MINTS_NOTHING = "resale_mints_no_shares_or_issuer_cash"
GUARD_PREFUNDED_NOT_RECOUNTED = "prefunded_paid_economics_not_recounted"
GUARD_ONE_DECREMENT = "one_decrement_per_action"
GUARD_CLAIM_SURVIVES = "claim_survives_execution_limit"
GUARD_NOTICE_LIMITS = "notice_period_limits_execution"
GUARD_CAP_LIMITS = "holder_cap_limits_execution"
GUARD_CAPPED_AT_CLAIM = "selection_capped_at_claim"
#: I2 guards (SPEC_I2 §3).
GUARD_EXCLUSIVE_BRANCHES = "exclusive_branches_never_summed"
GUARD_EXCHANGE_CAP_LIMITS_DELIVERY = "exchange_cap_limits_delivery_not_claim"
GUARD_NO_PRICE_AFTER_PRICING_DATE = "no_price_after_pricing_date"
GUARD_NO_ASSUMED_FLOOR = "no_assumed_floor"
GUARD_CONDITION_NOT_MET = "conversion_condition_not_met"

#: Blockers and trace facts an I2 row raises (SPEC_I2 §2, §3).
BLOCKER_CONDITION_ASSUMED_MET = "conversion_condition_assumed_met"
TRACE_BLOCKED_BY_EXCHANGE_CAP = "blocked_by_exchange_cap"

#: The fixed §3 order, recorded on every I2 row as ``evaluation_order``.
EVALUATION_ORDER = (
    "amount",
    "price",
    "condition",
    "branch",
    "exchange_cap",
    "holder_cap_and_notice",
)

#: I2 term names.  An instrument carrying any of them, or any structured term,
#: is evaluated through the §3 order.
I2_VALUE_NAMES = ("exchange_cap_shares", "shares_issued_under_instrument", "accrued_amount_outstanding")
I2_FLAG_NAMES = ("shareholder_approval_obtained",)
I2_TERM_NAMES = tuple(ECONOMIC_TERM_STRUCTURE_NAMES) + I2_VALUE_NAMES + I2_FLAG_NAMES
#: Names that LIMIT what a cap leaves deliverable, for ``maximum_issuable``.
#: ``shares_issued_under_instrument`` is that cap's USAGE, not a second limit, so
#: it stays in the trace and is never listed here; authorized-share headroom is
#: joined later by the joint capacity model and the issuer state, not by I2
#: (audit S2).
MAXIMUM_ISSUABLE_LIMITS = ("exchange_cap_shares",)
#: The flag term that lifts the exchange cap entirely.
SHAREHOLDER_APPROVAL_NAME = "shareholder_approval_obtained"
#: M3: the action I2 evaluates settlement branches for, and only that one.
BRANCH_EVALUATED_ACTION = "conversion"

#: The I2 rule rows (SPEC_I2 §3).  These are a SEPARATE table from
#: ``SETTLEMENT_RULES``: the I1 table is pinned verbatim by
#: ``tests/test_capital_structure_supply_scenarios.py``, and a receipt states
#: the rules it ran under, so the extended digest is used only for a scenario
#: that actually runs an I2 rule.
VARIABLE_TERM_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "i2|price_formula",
        "price = combine(components) at the horizon end, then ceiling, then a STATED floor only, then rounding",
        "no_assumed_floor: a formula with no stated floor is priced with none, and is never given a finite maximum",
    ),
    (
        "i2|maximum_issuable",
        "a stated floor bounds amount/floor; none_in_complete_agreement is unbounded_by_contract",
        "not_established is a named Unknown: never a finite maximum and never infinity",
    ),
    (
        "i2|price_reset",
        "a past reset is a fact only if an admitted price term is dated on or after it; a horizon reset is priced at its own date",
        "a reset beyond the horizon is never applied, and no price point after the pricing date is ever read",
    ),
    (
        "i2|anti_dilution",
        "full_ratchet, weighted_average_narrow or none; a broad base comes only from an UnknownResolution",
        "the issuance is a scenario assumption, never a fact, and is never computed here",
    ),
    (
        "i2|accrual_terms",
        "amount = principal + accrual to the horizon end; simple accrual is on principal only",
        "an evidenced accrued_amount_outstanding continues from its own date; converts_with_principal false converts principal only",
    ),
    (
        "i2|conversion_condition",
        "a condition met in the trading-day window delivers; not met delivers 0 and the claim survives",
        "an unevaluable window is Unknown unless the action lists it in conditions_assumed_met",
    ),
    (
        "i2|settlement_branches",
        "conversion|branch: physical pays no cash, cash repays the conversion value, net_share repays min(amount, CV) and issues the surplus",
        "exclusive_branches_never_summed: every branch is priced separately and only the elected one reaches the envelope",
    ),
    (
        "i2|exchange_cap_shares",
        "delivered shares are limited to cap - issued, or unlimited once shareholder approval is admitted true",
        "exchange_cap_limits_delivery_not_claim: the as-converted claim is never reduced by the cap",
    ),
    (
        "i2|floor_cash_make_whole",
        "a floor that binds with floor_applies_with_cash_make_whole owes a repayment",
        "the make-whole amount is an unknown repayment, never 0 and never a guess",
    ),
)

AFFECTS_INCREMENTAL = ("incremental_issuance",)
AFFECTS_CLAIMS = ("as_converted_claims",)
AFFECTS_ROW_AND_CLAIMS = ("as_converted_claims", "incremental_issuance")
AFFECTS_EXISTING = ("existing_outstanding",)
AFFECTS_RESALE = ("resalable_existing",)
AFFECTS_CASH = ("cash_effects",)

#: Sentinel for a name an instrument carries twice: two terms for one name is a
#: contradiction this module reports, never a choice it makes.
_UNUSABLE = object()
_UNSET = object()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _parsed(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"{label}: {value!r} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{label}: timestamp must carry a timezone")
    return parsed


def _decimal_string(value: Decimal) -> str:
    """Plain, exponent-free decimal text: never a float, never a rounding."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _exact_string(value: Fraction) -> str:
    """Exact text for a rational: whole shares, a terminating decimal, or num/den.

    A share count that does not terminate in base 10 is written as an exact
    reduced fraction instead of being rounded, because rounding a contractual
    ratio would be a guess.
    """
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
            return _decimal_string(Decimal(value.numerator) / Decimal(value.denominator))
    return f"{value.numerator}/{value.denominator}"


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _remainder_string(value: Fraction) -> str:
    whole = _floor(value)
    remainder = value - whole
    if remainder == 0:
        return "0"
    return f"{remainder.numerator}/{remainder.denominator}"


def _refuse_numbers(value: Any, path: str = "<root>", in_structure: bool = False) -> None:
    """No float and no non-string number anywhere on the I1/I2 path (§0 item 3).

    One narrow exception: a structured term's day counts, rounding places and
    period lengths are exact integers BY CONTRACT (SPEC_I2 §1.5), so an ``int``
    is admitted inside a structure subtree and nowhere else.  Every money and
    rate figure inside a structure is still a ``Quantity`` carrying an exact
    decimal string, and a float is refused at every depth either way.
    """
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (float, Decimal, complex, Fraction)):
        raise ContractViolation(f"{path}: exact decimal strings only, a {type(value).__name__} is refused ({value!r})")
    if isinstance(value, int):
        if in_structure:
            return
        raise ContractViolation(f"{path}: exact decimal strings only, a {type(value).__name__} is refused ({value!r})")
    if isinstance(value, Mapping):
        nested = in_structure or value.get("kind") in _STRUCTURE_KIND_KEYS
        for key, item in value.items():
            _require(isinstance(key, str), f"{path}: non-string key {key!r}")
            _refuse_numbers(item, f"{path}.{key}", nested)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_numbers(item, f"{path}[{index}]", in_structure)
        return
    raise ContractViolation(f"{path}: unsupported type {type(value).__name__}")


def _money(value: Fraction) -> Decimal | None:
    """Exact :class:`Decimal` money, or ``None`` when it does not terminate.

    Money is never rounded: an amount that does not terminate in base 10 is an
    unknown cash amount, not a guessed one.
    """
    reduced = value.denominator
    while reduced % 2 == 0:
        reduced //= 2
    while reduced % 5 == 0:
        reduced //= 5
    if reduced != 1:
        return None
    with localcontext() as context:
        context.prec = 60
        return Decimal(value.numerator) / Decimal(value.denominator)


# ---------------------------------------------------------------------------
# Unknowns: named, described and de-duplicated (§5, D16)
# ---------------------------------------------------------------------------


def _unknown(unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str]) -> Unknown:
    return Unknown(
        unknown_id=unknown_id,
        description=description,
        resolving_fact=resolving_fact,
        affects=tuple(sorted(set(affects))),
    )


def _retarget(unknown: Unknown, affects: Sequence[str]) -> Unknown:
    merged = tuple(sorted(set(unknown.affects) | set(affects)))
    if merged == tuple(unknown.affects):
        return unknown
    return Unknown(unknown.unknown_id, unknown.description, unknown.resolving_fact, merged)


def _share_basis_unknown(status: str) -> Unknown:
    return _unknown(
        f"share_basis_{status}",
        f"the issued-and-outstanding share basis is {status}, so no comparable existing share count is selected",
        "a share basis selection: one admitted issued_and_outstanding observation with nothing contradicting it",
        AFFECTS_EXISTING,
    )


def _instrument_unknown(route_id: str) -> Unknown:
    return _unknown(
        f"instrument_{route_id}",
        f"the scenario selects route {route_id}, but no outstanding or amended instrument of that identity is in the set",
        "an adjudicated identity decision for that instrument, or a scenario that does not select it",
        AFFECTS_INCREMENTAL,
    )


def _route_not_supply_unknown(route_id: str) -> Unknown:
    return _unknown(
        f"route_not_supply_{route_id}",
        f"route {route_id} is not a warrant exercise or a conversion, so its issuance is not a supply fact of this module",
        "the capacity evaluation of that route kind (C1/C2), which owns shelf, ATM, equity-line and draw routes",
        AFFECTS_INCREMENTAL,
    )


def _settlement_not_permitted_unknown(route_id: str, detail: str) -> Unknown:
    return _unknown(
        f"settlement_not_permitted_{route_id}",
        f"the settlement selected for route {route_id} is not permitted: {detail}",
        "a scenario selecting a settlement this instrument's terms permit, or the I2 amendment that changes them",
        AFFECTS_INCREMENTAL,
    )


def _settlement_unknown(route_id: str) -> Unknown:
    return _unknown(
        f"settlement_unknown_{route_id}",
        f"the settlement selected for route {route_id} is unknown, so neither its share nor its cash consequence is knowable",
        "a scenario naming one settlement for that route",
        AFFECTS_INCREMENTAL,
    )


def _quantity_unknown(route_id: str) -> Unknown:
    return _unknown(
        f"quantity_{route_id}",
        f"the quantity selected for route {route_id} carries no known underlying-share count",
        "a scenario selecting a known underlying-share quantity, or the whole claim by selecting none",
        AFFECTS_INCREMENTAL,
    )


def _term_unknown(instrument_id: str, name: str) -> Unknown:
    unit = ECONOMIC_TERM_UNITS.get(name, (None, None))[0]
    return _unknown(
        f"term_{instrument_id}_{name}",
        f"the {name} of instrument {instrument_id} is missing, deferred, contradicted or stated only as a formula"
        + (f" (unit {unit})" if unit else ""),
        f"a retained-byte term occurrence stating {name} for this instrument, bound by an adjudicated identity decision",
        AFFECTS_INCREMENTAL,
    )


def _stale_unknown(instrument_id: str, name: str) -> Unknown:
    return _unknown(
        f"stale_presplit_{instrument_id}_{name}",
        f"the {name} of instrument {instrument_id} predates the split's effective date or is undated, "
        "so it is a pre-split term and no universal factor may be applied to it",
        f"a contract-adjustment term restating {name} as of or after the split's effective date",
        AFFECTS_ROW_AND_CLAIMS,
    )


def _holder_position_unknown(instrument_id: str) -> Unknown:
    return _unknown(
        f"holder_position_{instrument_id}",
        f"a beneficial-ownership cap applies to instrument {instrument_id}, but the holder's current position is not supplied",
        f"an UnknownResolution for holder_position_{instrument_id} carrying the holder's known share position",
        AFFECTS_INCREMENTAL,
    )


def _price_at_horizon_unknown() -> Unknown:
    return _unknown(
        "price_at_horizon",
        "the scenario price path has no point dated on or before the horizon end, so no cashless or net-share spread exists",
        "a price path point dated on or before the horizon end, or a fixed price assumption",
        AFFECTS_INCREMENTAL,
    )


def _price_currency_unknown(currency: str) -> Unknown:
    return _unknown(
        "price_currency",
        f"the scenario price is in {currency}, not USD, so it cannot value a USD-denominated exercise spread",
        "a USD price assumption, or a disclosed conversion this scenario states explicitly",
        AFFECTS_INCREMENTAL,
    )


def _conversion_condition_unknown(instrument_id: str) -> Unknown:
    return _unknown(
        f"conversion_condition_{instrument_id}",
        f"the conversion condition of instrument {instrument_id} cannot be evaluated on this scenario's price path, "
        "so neither meeting nor failing it is a fact",
        f"a price path covering the condition's trading-day window, or an action listing "
        f"conversion_condition_{instrument_id} in conditions_assumed_met",
        AFFECTS_INCREMENTAL,
    )


def _settlement_branches_not_evaluated_unknown(instrument_id: str) -> Unknown:
    """M3: a branches term on an action I2 does not price branches for.

    The term is VALID — the contracts layer admits ``settlement_branches`` on any
    instrument — it is simply not evaluated here, so the row names the fact that
    would resolve it instead of going unknown anonymously (§0 item 4).
    """
    return _unknown(
        f"settlement_branches_not_evaluated_{instrument_id}",
        f"instrument {instrument_id} carries an admitted settlement_branches term, and I2 evaluates settlement "
        f"branches for a {BRANCH_EVALUATED_ACTION} action only, so this action's branch is not evaluated here",
        f"a {BRANCH_EVALUATED_ACTION} action for instrument {instrument_id}, or an evaluator that prices "
        "settlement branches for this action",
        AFFECTS_INCREMENTAL,
    )


def _floor_not_established_unknown(instrument_id: str) -> Unknown:
    return _unknown(
        f"floor_not_established_{instrument_id}",
        f"the conversion price of instrument {instrument_id} floats and no floor is established, so the maximum "
        "share count the contract itself bounds is unknown; it is never a finite maximum and never infinity",
        f"a retained-byte floor price for instrument {instrument_id}, or the complete agreement's statement that there is none",
        ("maximum_issuable",),
    )


def _inexact_cash_unknown(route_id: str) -> Unknown:
    return _unknown(
        f"cash_amount_not_exact_{route_id}",
        f"the cash consequence of route {route_id} does not terminate in base 10, so it is reported as an unknown "
        "amount rather than rounded",
        "an exact stated cash amount for that route",
        AFFECTS_CASH,
    )


def _fee_rate_unknown() -> Unknown:
    return _unknown(
        "fee_rate",
        "the scenario states no fee rate, so net proceeds are unknown; a zero fee is never assumed",
        "a scenario fee_rate, or the underwriting agreement's disclosed fee",
        AFFECTS_CASH,
    )


class _Unknowns:
    """De-duplicated by ``unknown_id``; the same id always means the same fact."""

    def __init__(self) -> None:
        self._by_id: dict[str, Unknown] = {}

    def add(self, unknown: Unknown) -> str:
        prior = self._by_id.get(unknown.unknown_id)
        if prior is None:
            self._by_id[unknown.unknown_id] = unknown
            return unknown.unknown_id
        _require(
            prior.description == unknown.description and prior.resolving_fact == unknown.resolving_fact,
            f"unknown {unknown.unknown_id!r} is described two different ways",
        )
        merged = _retarget(prior, unknown.affects)
        self._by_id[unknown.unknown_id] = merged
        return unknown.unknown_id

    def sorted(self) -> tuple[Unknown, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def ids(self) -> list[str]:
        return sorted(self._by_id)


@dataclass(frozen=True)
class _Row:
    """One action row: the unit the envelope has no field for (§5, D18)."""

    route_id: str
    instrument_id: str | None
    action: str
    settlement: str
    underlying_shares: str
    incremental_shares: str
    gross_cash: str
    net_cash: str
    guards: tuple[str, ...]
    unknowns: tuple[str, ...]
    fraction: str
    incremental: int | None
    cash_effect: CashEffect | None
    #: I2 (SPEC_I2 §3).  Empty for a pre-I2 row, whose trace record therefore
    #: keeps exactly its I1 keys.
    evaluation_order: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    variable_terms: tuple[tuple[str, str], ...] = ()

    def as_trace_record(self) -> dict[str, Any]:
        record = {
            "route_id": self.route_id,
            "instrument_id": self.instrument_id,
            "action": self.action,
            "settlement": self.settlement,
            "underlying_shares": self.underlying_shares,
            "incremental_shares": self.incremental_shares,
            "gross_cash": self.gross_cash,
            "net_cash": self.net_cash,
            "guards": list(self.guards),
            "unknowns": list(self.unknowns),
            "fraction": self.fraction,
        }
        if self.evaluation_order:
            record["evaluation_order"] = list(self.evaluation_order)
        if self.blockers:
            record["blockers"] = list(self.blockers)
        if self.variable_terms:
            record["variable_terms"] = dict(self.variable_terms)
        return record


@dataclass(frozen=True)
class _AmountOutcome:
    """The §3 step 1 dollar amount of a conversion, before any limit."""

    amount: Fraction | None
    unknowns: tuple[Unknown, ...]
    trace_items: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _PriceOutcome:
    """The §3 step 2 price after the formula, the resets and the anti-dilution."""

    price: Fraction | None
    count: Fraction | None
    unknowns: tuple[Unknown, ...]
    trace_items: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]
    formula: Any
    #: Unknowns the envelope must NAME but that do not make the price unknown —
    #: a make-whole whose amount no term states still leaves the price known.
    extra_unknowns: tuple[Unknown, ...] = ()


def _terms_by_name(instrument: Instrument) -> dict[str, Any]:
    """One term per name; a name carried twice is unusable, never a choice."""
    by_name: dict[str, Any] = {}
    for term in instrument.economic_terms:
        by_name[term.name] = _UNUSABLE if term.name in by_name else term
    return by_name


def _split_instant(basis: ShareBasisResult) -> datetime | None:
    """The split's effective instant at 00:00:00Z, or None when there is no split.

    Only the KIND and the EFFECTIVE DATE are read.  The split factor itself is
    never read, because applying one universal factor to contractual terms is
    exactly what A19 forbids: a pre-split term is stale, not convertible.
    """
    action = basis.corporate_action
    if action.kind not in ("reverse_split", "forward_split"):
        return None
    _require(action.effective_date is not None, "supply: a split basis carries its effective date")
    day = date.fromisoformat(action.effective_date)
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _horizon_days(scenario: FinancingScenario) -> int:
    """Days from the later of the scenario's ``as_of`` date and its horizon start."""
    as_of = _parsed(scenario.as_of, "scenario.as_of").date()
    start = date.fromisoformat(scenario.horizon_start)
    end = date.fromisoformat(scenario.horizon_end)
    return (end - max(as_of, start)).days


class _Evaluation:
    """One deterministic pass over ``(instruments, basis, scenario)``.

    Both public entry points run this and project it: ``supply_trace`` keeps the
    rows, ``evaluate_supply`` returns the frozen envelope.  Nothing is summed
    across the four components anywhere in here.
    """

    def __init__(self, instruments: InstrumentSet, basis: ShareBasisResult, scenario: FinancingScenario) -> None:
        _require(isinstance(instruments, InstrumentSet), "supply.instruments: an InstrumentSet is required")
        _require(isinstance(basis, ShareBasisResult), "supply.basis: a ShareBasisResult is required")
        _require(isinstance(scenario, FinancingScenario), "supply.scenario: a FinancingScenario is required")
        _refuse_numbers(instruments.as_record(), "instrument_set")
        _refuse_numbers(basis.as_record(), "share_basis")
        _refuse_numbers(scenario.as_record(), "financing_scenario")
        _require(
            instruments.issuer_id == basis.issuer_id,
            f"supply: the instrument set issuer {instruments.issuer_id!r} differs from the share basis issuer {basis.issuer_id!r}",
        )
        self.instruments = instruments
        self.basis = basis
        self.scenario = scenario
        self.unknowns = _Unknowns()
        self.guards: set[str] = {GUARD_COMPONENTS_NEVER_SUMMED, GUARD_RESALE_MINTS_NOTHING, GUARD_ONE_DECREMENT}
        self.by_id = {item.instrument_id: item for item in instruments.instruments}
        self.terms = {item.instrument_id: _terms_by_name(item) for item in instruments.instruments}
        self.split_instant = _split_instant(basis)
        self.horizon_days = _horizon_days(scenario)
        self.selected: set[str] = set()
        self.basis_unknown_id: str | None = None
        self._price_cache: Any = _UNSET
        self.existing, self.existing_value = self._existing_outstanding()
        # I2 state (SPEC_I2 §2, §3): the path measure the scenario declares, the
        # single pricing date every evaluator reads, and the memoised outcomes
        # that keep one pass deterministic and one instrument priced once.
        self.path_measure = variable_terms.path_measure_of(scenario.other_assumptions)
        self.pricing_date = scenario.horizon_end
        self.i2_active = any(self._carries_i2_term(item) for item in instruments.instruments)
        self._assumptions = dict(scenario.other_assumptions)
        self._base_cache: dict[str, Any] = {}
        self._amount_cache: dict[str, Any] = {}
        self._price_cache2: dict[Any, Any] = {}
        self._maximum_issuable: dict[str, dict[str, Any]] = {}
        self._alternatives: list[dict[str, Any]] = []
        self._variable_trace: dict[str, dict[str, str]] = {}

    # -- share basis (§5.2) -------------------------------------------------

    def _existing_outstanding(self) -> tuple[Quantity, Fraction | None]:
        selected = self.basis.selected
        if self.basis.status == "selected" and selected is not None and selected.status == "known" and selected.value is not None:
            return selected, Fraction(Decimal(selected.value))
        self.basis_unknown_id = self.unknowns.add(_share_basis_unknown(self.basis.status))
        quantity = Quantity.unknown(
            "shares",
            share_basis="issued_and_outstanding",
            security_class_id=self.basis.security_class_id,
        )
        return quantity, None

    # -- scenario price (§5.5, D8) -----------------------------------------

    def _resolve_price(self) -> tuple[Fraction | None, str | None, tuple[Unknown, ...]]:
        """The scenario price as an exact value plus its verbatim stated text."""
        price = self.scenario.price
        unknowns: list[Unknown] = []
        value: Fraction | None = None
        stated: str | None = None
        if price.kind == "fixed":
            if price.fixed_price is not None:
                value = Fraction(Decimal(price.fixed_price))
                stated = price.fixed_price
        else:
            horizon_end = self.scenario.horizon_end
            dated = [point for point in price.path if point[0] <= horizon_end]
            if dated:
                value = Fraction(Decimal(dated[-1][1]))
                stated = dated[-1][1]
            else:
                unknowns.append(_price_at_horizon_unknown())
        if price.currency != "USD":
            value = None
            stated = None
            unknowns.append(_price_currency_unknown(price.currency))
        return value, stated, tuple(unknowns)

    def _price(self) -> tuple[Fraction | None, tuple[str, ...]]:
        """Resolve the price because a row needs it, naming what is missing."""
        if self._price_cache is not _UNSET:
            return self._price_cache
        value, _stated, unknowns = self._resolve_price()
        ids = tuple(sorted(self.unknowns.add(unknown) for unknown in unknowns))
        self._price_cache = (value, ids)
        return self._price_cache

    def _price_record(self) -> dict[str, Any]:
        _value, stated, _unknowns = self._resolve_price()
        required = self._price_cache is not _UNSET
        return {
            "kind": self.scenario.price.kind,
            "currency": self.scenario.price.currency,
            "value": stated if stated is not None else "unknown",
            "required": bool(required),
            "horizon_end": self.scenario.horizon_end,
            "unknowns": sorted(self._price_cache[1]) if required else [],
        }

    # -- terms --------------------------------------------------------------

    def _term(self, instrument_id: str, name: str) -> Any:
        return self.terms.get(instrument_id, {}).get(name)

    def _is_stale(self, name: str, term: EconomicTerm) -> bool:
        """A19: a term the split predates, or one with no effective instant at all."""
        if self.split_instant is None or name not in SPLIT_SENSITIVE_NAMES:
            return False
        if term.effective_at is None:
            return True
        return _parsed(term.effective_at, f"economic_term[{term.term_id}].effective_at") < self.split_instant

    def _quantity(self, instrument_id: str, name: str) -> tuple[Decimal | None, Unknown | None]:
        """The exact stated value of one quantity term, or the Unknown that replaces it."""
        term = self._term(instrument_id, name)
        if term is None or term is _UNUSABLE:
            return None, _term_unknown(instrument_id, name)
        if term.status != "admitted" or term.expression is not None:
            return None, _term_unknown(instrument_id, name)
        value = term.value
        if value is None or value.status != "known" or value.value is None:
            return None, _term_unknown(instrument_id, name)
        if self._is_stale(name, term):
            return None, _stale_unknown(instrument_id, name)
        return Decimal(value.value), None

    def _limiter(self, instrument: Instrument, name: str) -> tuple[Decimal | None, Unknown | None, bool]:
        """A limiter term: absent means no such limit exists, unreadable means unknown."""
        if self._term(instrument.instrument_id, name) is None:
            return None, None, False
        value, unknown = self._quantity(instrument.instrument_id, name)
        return value, unknown, True

    def _permission(self, instrument: Instrument, settlement: str, route_id: str) -> Unknown | None:
        """D3: what the instrument's permission terms say about this settlement."""
        if settlement in ("cash", "pre_funded"):
            name = "cash_exercise_permitted"
            term = self._term(instrument.instrument_id, name)
            if term is None:
                return None
            if term is _UNUSABLE or term.status == "contradicted":
                return _term_unknown(instrument.instrument_id, name)
            if term.status == "admitted" and term.flag is False:
                return _settlement_not_permitted_unknown(route_id, f"{name} is admitted false")
            return None
        if settlement in NO_CASH_SETTLEMENTS:
            name = "cashless_exercise_permitted"
            term = self._term(instrument.instrument_id, name)
            if term is not None and term is not _UNUSABLE and term.status == "admitted":
                if term.flag is True:
                    return None
                if term.flag is False:
                    return _settlement_not_permitted_unknown(route_id, f"{name} is admitted false")
            return _term_unknown(instrument.instrument_id, name)
        return None

    def _holder_position(self, instrument_id: str) -> Fraction | None:
        target = f"holder_position_{instrument_id}"
        for resolution in self.scenario.unknown_resolutions:
            if resolution.unknown_id != target:
                continue
            assumed = resolution.assumed
            _require(
                assumed.unit == "shares",
                f"supply: {target} must be resolved with a shares quantity, got unit {assumed.unit!r}",
            )
            _require(
                assumed.status == "known" and assumed.value is not None,
                f"supply: {target} must be resolved with a known share count",
            )
            return Fraction(Decimal(assumed.value))
        return None

    # -- I2 terms (SPEC_I2 §2, §3) -----------------------------------------

    def _carries_i2_term(self, instrument: Instrument) -> bool:
        """Whether any term of this instrument puts the row on the §3 order."""
        return any(term.structure is not None or term.name in I2_TERM_NAMES for term in instrument.economic_terms)

    def _admitted_term(self, instrument_id: str, name: str) -> tuple[Any, Unknown | None]:
        """The admitted term of one name, or the Unknown that replaces it.

        An absent term is ``(None, None)``: no such contractual fact exists.  A
        term carried twice, contradicted, deferred or formula-only is
        ``(None, Unknown)``: the fact exists but is not knowable, which is never
        the same thing.
        """
        term = self._term(instrument_id, name)
        if term is None:
            return None, None
        if not isinstance(term, EconomicTerm) or term.status != "admitted":
            return None, _term_unknown(instrument_id, name)
        return term, None

    def _structure(self, instrument_id: str, name: str) -> Any:
        term, _unknown = self._admitted_term(instrument_id, name)
        return None if term is None else term.structure

    def _structure_unknown(self, instrument_id: str, name: str) -> Unknown | None:
        _term, unknown = self._admitted_term(instrument_id, name)
        return unknown

    def _register(self, unknowns: Sequence[Unknown], affects: Sequence[str]) -> list[str]:
        return [self.unknowns.add(_retarget(item, affects)) for item in unknowns]

    def _name_only(self, unknowns: Sequence[Unknown], affects: Sequence[str]) -> None:
        """Register unknowns the envelope must name without blocking the row."""
        for item in unknowns:
            self.unknowns.add(_retarget(item, affects))

    def _dilutive_issuance(self) -> dict[str, Fraction | None]:
        """The anti-dilution issuance, read ONLY from scenario assumptions (§2.5).

        Both figures are validated with the contracts module's exact-decimal rule
        (audit S4): ``NaN``, an infinity, an exponent form, garbage text and a
        negative are each refused with :class:`ContractViolation` and never with
        another exception type.  An assumption is exact text or it is nothing.
        """
        shares_text = self._assumptions.get(variable_terms.DILUTIVE_ISSUANCE_SHARES)
        shares = (
            None
            if shares_text is None
            else variable_terms.exact_decimal(
                shares_text, f"scenario.other_assumptions[{variable_terms.DILUTIVE_ISSUANCE_SHARES}]"
            )
        )
        price_text = self._assumptions.get(variable_terms.DILUTIVE_ISSUANCE_PRICE)
        if price_text is not None:
            issued_price: Fraction | None = variable_terms.exact_decimal(
                price_text, f"scenario.other_assumptions[{variable_terms.DILUTIVE_ISSUANCE_PRICE}]"
            )
        else:
            horizon_price, _unknowns = self._price()
            if horizon_price is not None and self.scenario.discount_rate is not None:
                issued_price = horizon_price * (Fraction(1) - Fraction(Decimal(self.scenario.discount_rate)))
            else:
                issued_price = None
        return {variable_terms.DILUTIVE_ISSUANCE_SHARES: shares, variable_terms.DILUTIVE_ISSUANCE_PRICE: issued_price}

    def _broad_base(self, instrument_id: str) -> Fraction | None:
        """The fully-diluted base a BROAD weighted average needs, if resolved."""
        target = f"{variable_terms.BROAD_BASE_PREFIX}{instrument_id}"
        for resolution in self.scenario.unknown_resolutions:
            if resolution.unknown_id != target:
                continue
            assumed = resolution.assumed
            _require(
                assumed.unit == "shares" and assumed.status == "known" and assumed.value is not None,
                f"supply: {target} must be resolved with a known share count",
            )
            return Fraction(Decimal(assumed.value))
        return None

    def _warrant_base(self, instrument: Instrument) -> tuple[Fraction | None, tuple[Unknown, ...]]:
        """The unadjusted underlying-share count of a warrant (I1 §5.8)."""
        cached = self._base_cache.get(instrument.instrument_id)
        if cached is not None:
            return cached
        values: dict[str, Decimal] = {}
        unknowns: list[Unknown] = []
        for name in CLAIM_TERMS[instrument.kind]:
            value, unknown = self._quantity(instrument.instrument_id, name)
            if unknown is not None:
                unknowns.append(unknown)
            else:
                assert value is not None
                values[name] = value
        outcome: tuple[Fraction | None, tuple[Unknown, ...]] = (
            (None, tuple(unknowns))
            if unknowns
            else (Fraction(values["instruments_outstanding"]) * Fraction(values["shares_per_instrument"]), ())
        )
        self._base_cache[instrument.instrument_id] = outcome
        return outcome

    def _amount_outcome(self, instrument: Instrument) -> "_AmountOutcome":
        """The dollar amount a conversion carries at the horizon end (§3 step 1)."""
        instrument_id = instrument.instrument_id
        cached = self._amount_cache.get(instrument_id)
        if cached is not None:
            return cached
        value, unknown = self._quantity(instrument_id, "principal_outstanding")
        if unknown is not None:
            outcome = _AmountOutcome(None, (unknown,), ())
        else:
            assert value is not None
            principal = Fraction(value)
            trace_items: list[tuple[str, str]] = [("amount", _exact_string(principal))]
            accrual = self._structure(instrument_id, "accrual_terms")
            accrual_unknown = self._structure_unknown(instrument_id, "accrual_terms")
            if accrual_unknown is not None:
                outcome = _AmountOutcome(None, (accrual_unknown,), ())
            elif accrual is None:
                outcome = _AmountOutcome(principal, (), tuple(trace_items))
            else:
                accrued_term, accrued_unknown = self._admitted_term(instrument_id, "accrued_amount_outstanding")
                if accrued_unknown is not None:
                    outcome = _AmountOutcome(None, (accrued_unknown,), ())
                else:
                    result = variable_terms.accreted_amount(
                        principal, accrual, accrued_term, self.scenario.horizon_end, instrument_id
                    )
                    trace_items.extend(result.trace_items)
                    outcome = (
                        _AmountOutcome(None, (result.unknown,), tuple(trace_items))
                        if result.unknown is not None
                        else _AmountOutcome(result.value, (), tuple(trace_items))
                    )
        self._amount_cache[instrument_id] = outcome
        return outcome

    def _price_outcome(
        self, instrument: Instrument, name: str, base_count: Fraction | None, require_price: bool
    ) -> "_PriceOutcome":
        """§3 step 2: the I1 fixed term, or the formula, then resets, then anti-dilution."""
        instrument_id = instrument.instrument_id
        key = (instrument_id, name, bool(require_price))
        cached = self._price_cache2.get(key)
        if cached is not None:
            return cached
        outcome = self._compute_price_outcome(instrument, name, base_count, require_price)
        self._price_cache2[key] = outcome
        return outcome

    def _compute_price_outcome(
        self, instrument: Instrument, name: str, base_count: Fraction | None, require_price: bool
    ) -> "_PriceOutcome":
        instrument_id = instrument.instrument_id
        unknowns: list[Unknown] = []
        extra_unknowns: list[Unknown] = []
        trace_items: list[tuple[str, str]] = []
        blockers: list[str] = []
        term, term_unknown = self._admitted_term(instrument_id, name)
        formula = term.structure if isinstance(term, EconomicTerm) else None
        formula = formula if isinstance(formula, PriceFormula) else None
        price: Fraction | None = None
        price_unknown: Unknown | None = None
        stale = isinstance(term, EconomicTerm) and self._is_stale(name, term)
        stated_value: str | None = None
        if (
            term is not None
            and term.expression is None
            and term.value is not None
            and term.value.status == "known"
            and term.value.value is not None
        ):
            stated_value = str(term.value.value)
        if stale:
            price_unknown = _stale_unknown(instrument_id, name)
        elif formula is not None:
            # S3: a formula is the contract's price rule even when every one of
            # its components is fixed and the term also states a known value, so
            # the §2.2 order — ceiling, then floor, then rounding — always runs.
            # A fixed value never bypasses its own formula.
            result = variable_terms.formula_price(
                formula, self.scenario.price.path, self.pricing_date, self.path_measure, instrument_id
            )
            trace_items.extend(result.trace_items)
            blockers.extend(result.blockers)
            extra_unknowns.extend(result.extra_unknowns)
            # A path is only ever read up to the pricing date, and a floor is
            # only ever the one the contract states (SPEC_I2 §0 items 4 and 7).
            self.guards.add(GUARD_NO_PRICE_AFTER_PRICING_DATE)
            self.guards.add(GUARD_NO_ASSUMED_FLOOR)
            if stated_value is not None:
                trace_items.append(("price_term_also_states_a_value", stated_value))
            if result.unknown is not None:
                price_unknown = result.unknown
            else:
                price = result.value
                trace_items.append(("price_source", "price_formula"))
        elif stated_value is not None:
            assert term is not None and term.value is not None and term.value.value is not None
            price = Fraction(Decimal(term.value.value))
            trace_items.append(("price_source", "fixed_term"))
        elif term_unknown is not None:
            price_unknown = term_unknown
        else:
            value, unknown = self._quantity(instrument_id, name)
            if unknown is not None:
                price_unknown = unknown
            else:
                assert value is not None
                price = Fraction(value)
                trace_items.append(("price_source", "fixed_term"))
        if price_unknown is not None:
            unknowns.append(price_unknown)
        if price is not None:
            trace_items.append(("price_term_name", name))
            trace_items.append(("contract_price", _exact_string(price)))

        count = base_count
        schedule = self._structure(instrument_id, "price_reset")
        if schedule is not None and schedule.applies_to == name:
            schedule_unknown = self._structure_unknown(instrument_id, "price_reset")
            if schedule_unknown is not None:
                unknowns.append(schedule_unknown)
            else:
                result = variable_terms.apply_resets(
                    schedule, price, count, self.terms.get(instrument_id, {}), self.scenario, instrument_id
                )
                trace_items.extend(result.trace_items)
                if result.unknown is not None:
                    unknowns.append(result.unknown)
                    price = None
                else:
                    price = result.value
                    count = result.count
        elif self._structure_unknown(instrument_id, "price_reset") is not None:
            unknowns.append(self._structure_unknown(instrument_id, "price_reset"))
        anti_dilution = self._structure(instrument_id, "anti_dilution")
        if anti_dilution is not None and anti_dilution.applies_to == name:
            result = variable_terms.anti_dilution_price(
                anti_dilution,
                price,
                self._dilutive_issuance(),
                self.existing_value,
                instrument_id,
                broad_base=self._broad_base(instrument_id),
                count=count,
            )
            trace_items.extend(result.trace_items)
            blockers.extend(result.blockers)
            if result.unknown is not None:
                unknowns.append(result.unknown)
                price = None
            else:
                price = result.value
                count = result.count
        elif self._structure_unknown(instrument_id, "anti_dilution") is not None:
            unknowns.append(self._structure_unknown(instrument_id, "anti_dilution"))
        if price is None and not require_price:
            # The row does not need this price, so its absence is not a fact
            # about the row: drop the price Unknowns and keep only the rest.
            unknowns = [item for item in unknowns if item is not price_unknown]
        if price is not None:
            trace_items.append(("adjusted_price", _exact_string(price)))
        if count is not None and base_count is not None and count != base_count:
            trace_items.append(("adjusted_count", _exact_string(count)))
        return _PriceOutcome(
            price=price,
            count=count,
            unknowns=tuple(unknowns),
            trace_items=tuple(trace_items),
            blockers=tuple(sorted(set(blockers))),
            formula=formula,
            extra_unknowns=tuple(extra_unknowns),
        )

    def _record_maximum_issuable(
        self, instrument: Instrument, amount: Fraction | None, formula: Any, price_name: str = "conversion_price"
    ) -> None:
        """§3: ``trace.maximum_issuable`` per instrument, a trace row and never a Quantity."""
        if formula is None or amount is None:
            return
        instrument_id = instrument.instrument_id
        # S2: a limit is listed only when it actually binds.  Shareholder
        # approval lifts the exchange cap entirely, and the shares already issued
        # under the instrument are that cap's usage — they stay in the trace.
        approval_term, _approval_unknown = self._admitted_term(instrument_id, SHAREHOLDER_APPROVAL_NAME)
        approval_obtained = (
            isinstance(approval_term, EconomicTerm)
            and approval_term.status == "admitted"
            and approval_term.flag is True
        )
        limits = () if approval_obtained else tuple(
            name for name in MAXIMUM_ISSUABLE_LIMITS if self._admitted_term(instrument_id, name)[0] is not None
        )
        # M4: the reported maximum must bound every delivered count, so it takes
        # its bound from the LOWEST price any stated term can reach — the reset
        # schedule applies the EVENT floor, and §2.5 anti-dilution applies none.
        anti_dilution = self._structure(instrument_id, "anti_dilution")
        if anti_dilution is not None and anti_dilution.applies_to != price_name:
            anti_dilution = None
        schedule = self._structure(instrument_id, "price_reset")
        if schedule is not None and schedule.applies_to != price_name:
            schedule = None
        entry = variable_terms.maximum_issuable(
            formula, amount, instrument_id, limits, anti_dilution=anti_dilution, schedule=schedule
        )
        self._maximum_issuable[instrument_id] = entry
        if entry.get("state") == "unknown":
            # §0 item 4: an unestablished floor is a NAMED Unknown, never a
            # finite maximum and never infinity.
            self.unknowns.add(_floor_not_established_unknown(instrument_id))

    # -- claims (§5.8, D4) --------------------------------------------------

    def _claim(self, instrument: Instrument, affects: Sequence[str]) -> tuple[Fraction | None, list[str]]:
        """The instrument's full underlying-share claim, exact and unfloored."""
        if self._carries_i2_term(instrument):
            return self._claim_i2(instrument, affects)
        values: dict[str, Decimal] = {}
        ids: list[str] = []
        for name in CLAIM_TERMS[instrument.kind]:
            value, unknown = self._quantity(instrument.instrument_id, name)
            if unknown is not None:
                assert unknown is not None
                ids.append(self.unknowns.add(_retarget(unknown, affects)))
            else:
                assert value is not None
                values[name] = value
        if ids:
            return None, ids
        if instrument.kind in WARRANT_KINDS:
            return Fraction(values["instruments_outstanding"]) * Fraction(values["shares_per_instrument"]), []
        denominator = Fraction(values["conversion_price"])
        if denominator == 0:
            # A zero conversion price is not a price: it is neither zero shares
            # nor infinitely many, so the claim stays unknown.
            unknown = _term_unknown(instrument.instrument_id, "conversion_price")
            return None, [self.unknowns.add(_retarget(unknown, affects))]
        return Fraction(values["principal_outstanding"]) / denominator, []

    def _claim_i2(self, instrument: Instrument, affects: Sequence[str]) -> tuple[Fraction | None, list[str]]:
        """The claim of an instrument on the §3 order, at the horizon price.

        A25: this is the claim BEFORE the conversion condition, the exchange cap
        and the holder cap or notice period are applied.  None of those limits
        reaches it.
        """
        instrument_id = instrument.instrument_id
        ids: list[str] = []
        if instrument.kind in WARRANT_KINDS:
            base, base_unknowns = self._warrant_base(instrument)
            ids.extend(self._register(base_unknowns, affects))
            schedule = self._structure(instrument_id, "price_reset")
            anti_dilution = self._structure(instrument_id, "anti_dilution")
            needs_price = (schedule is not None and schedule.applies_to == "exercise_price") or (
                anti_dilution is not None and anti_dilution.applies_to == "exercise_price"
            )
            outcome = self._price_outcome(instrument, "exercise_price", base, needs_price)
            ids.extend(self._register(outcome.unknowns, affects))
            self._name_only(outcome.extra_unknowns, affects)
            self._merge_variable_trace(instrument_id, outcome.trace_items)
            if ids or base is None:
                return None, ids
            return (base if outcome.count is None else outcome.count), []
        amount_outcome = self._amount_outcome(instrument)
        ids.extend(self._register(amount_outcome.unknowns, affects))
        self._merge_variable_trace(instrument_id, amount_outcome.trace_items)
        outcome = self._price_outcome(instrument, "conversion_price", None, True)
        ids.extend(self._register(outcome.unknowns, affects))
        self._name_only(outcome.extra_unknowns, affects)
        self._merge_variable_trace(instrument_id, outcome.trace_items)
        self._record_maximum_issuable(instrument, amount_outcome.amount, outcome.formula, "conversion_price")
        if outcome.price is not None and outcome.price == 0:
            # A zero conversion price is not a price: neither zero shares nor
            # infinitely many, so the claim stays unknown.
            ids.append(self.unknowns.add(_retarget(_term_unknown(instrument_id, "conversion_price"), affects)))
            outcome = _PriceOutcome(
                None, None, outcome.unknowns, outcome.trace_items, outcome.blockers, outcome.formula,
                outcome.extra_unknowns,
            )
        if ids or amount_outcome.amount is None or outcome.price is None:
            return None, ids
        return amount_outcome.amount / outcome.price, []

    def _merge_variable_trace(self, instrument_id: str, items: Sequence[tuple[str, str]]) -> None:
        """Keep the per-instrument I2 trace; a later key wins only if it differs."""
        merged = dict(self._variable_trace.get(instrument_id, {}))
        for key, value in items:
            merged[key] = value
        self._variable_trace[instrument_id] = merged

    # -- rows (§5.3, §5.4, §5.7) -------------------------------------------

    def _cash_effect(self, route_id: str, settlement: str, gross: Decimal | None, net: Decimal | None) -> CashEffect:
        if settlement in NO_CASH_SETTLEMENTS:
            # Structurally no issuer cash: true whatever the share count is.
            return CashEffect(route_id, "no_cash", Quantity.known("0", "usd"), Quantity.known("0", "usd"))
        gross_quantity = Quantity.known(_decimal_string(gross), "usd") if gross is not None else Quantity.unknown("usd")
        net_quantity = Quantity.known(_decimal_string(net), "usd") if net is not None else Quantity.unknown("usd")
        return CashEffect(route_id, "proceeds", gross_quantity, net_quantity)

    def _unknown_row(
        self,
        instrument_id: str | None,
        selection: ActionSelection,
        unknown_ids: Sequence[str],
        guards: Sequence[str] = (),
        cash_effect: Any = _UNSET,
        evaluation_order: Sequence[str] = (),
        blockers: Sequence[str] = (),
        variable_terms: Sequence[tuple[str, str]] = (),
    ) -> _Row:
        """An all-unknown row.

        ``cash_effect`` left unset derives the row's own cash shape with unknown
        amounts (a supply row whose terms are missing still has a settlement, so
        its cash is unknown, never absent).  An explicit ``None`` means the row
        carries NO cash effect at all, which is what §5.3 requires of a route
        this module cannot identify and of a capacity route it does not own.
        """
        if cash_effect is _UNSET:
            cash_effect = self._cash_effect(selection.route_id, selection.settlement, None, None)
        return _Row(
            route_id=selection.route_id,
            instrument_id=instrument_id,
            action=selection.action,
            settlement=selection.settlement,
            underlying_shares="unknown",
            incremental_shares="unknown",
            gross_cash="unknown",
            net_cash="unknown",
            guards=tuple(sorted(set(guards))),
            unknowns=tuple(sorted(set(unknown_ids))),
            fraction="0",
            incremental=None,
            cash_effect=cash_effect,
            evaluation_order=tuple(evaluation_order),
            blockers=tuple(sorted(set(blockers))),
            variable_terms=tuple(variable_terms),
        )

    def _row(self, selection: ActionSelection) -> _Row:
        route_id = selection.route_id
        action = selection.action
        settlement = selection.settlement
        if action not in SUPPLY_ACTIONS:
            # §5.3: a capacity route contributes its Unknown and nothing else.
            # Because its issuance is unknown, the component is unknown too —
            # never 0 (D13).
            unknown_id = self.unknowns.add(_route_not_supply_unknown(route_id))
            return self._unknown_row(None, selection, [unknown_id], cash_effect=None)
        instrument = self.by_id.get(route_id)
        if instrument is None or instrument.status not in ELIGIBLE_STATUSES:
            unknown_id = self.unknowns.add(_instrument_unknown(route_id))
            # §5.3: no shares and no cash for a row this set cannot identify.
            return self._unknown_row(route_id, selection, [unknown_id], cash_effect=None)
        _require(
            instrument.instrument_id not in self.selected,
            f"supply: instrument {instrument.instrument_id} is selected twice; one action decrements one claim",
        )
        self.selected.add(instrument.instrument_id)
        if instrument.kind not in ACTION_INSTRUMENT_KINDS[action]:
            return self._refused(
                instrument,
                selection,
                _settlement_not_permitted_unknown(
                    route_id,
                    f"action {action} does not apply to a {instrument.kind} instrument",
                ),
            )
        branches_unknown = (
            self._structure_unknown(instrument.instrument_id, "settlement_branches") if action == "conversion" else None
        )
        if branches_unknown is not None:
            return self._refused(instrument, selection, _retarget(branches_unknown, AFFECTS_INCREMENTAL))
        branches = (
            self._structure(instrument.instrument_id, "settlement_branches") if action == "conversion" else None
        )
        if branches is not None:
            # SPEC_I2 §1.2, §3.4: an admitted settlement_branches term names the
            # ONLY settlements this conversion may use, `physical` included.  An
            # `automatic` term has exactly one branch (§1.5), so the contract
            # elects it and no party does: whatever settlement the action names,
            # that single branch is what applies (SPEC_I2 §3 step 4).
            if branches.elected_by == "automatic":
                _require(len(branches.branches) == 1,
                         "supply: an automatic settlement_branches term names exactly one branch")
            elif settlement not in branches.branches:
                return self._refused(
                    instrument,
                    selection,
                    _settlement_not_permitted_unknown(
                        route_id,
                        f"the settlement_branches term admits {list(branches.branches)} "
                        f"and {settlement!r} is not one of them",
                    ),
                )
        elif settlement not in PERMITTED_SETTLEMENTS[instrument.kind]:
            if settlement == "unknown":
                return self._refused(instrument, selection, _settlement_unknown(route_id))
            return self._refused(
                instrument,
                selection,
                _settlement_not_permitted_unknown(route_id, f"a {instrument.kind} may not settle {settlement}"),
            )
        permission = self._permission(instrument, settlement, route_id)
        if permission is not None:
            return self._refused(instrument, selection, permission)
        guards: set[str] = set()
        ids: list[str] = []
        # An unreadable limiter means the row cannot be bounded: unknown, never
        # unlimited (a cap or notice period that exists but cannot be read is
        # not the same as no cap at all).
        for name in LIMITER_NAMES:
            _value, unknown, present = self._limiter(instrument, name)
            if present and unknown is not None:
                return self._refused(instrument, selection, _retarget(unknown, AFFECTS_INCREMENTAL), guards)

        if self._carries_i2_term(instrument):
            return self._row_i2(instrument, selection, guards, ids)

        n_exact: Fraction | None = None
        quantity = selection.quantity
        if quantity is not None:
            _require(
                quantity.unit == "shares",
                f"supply: the quantity selected for route {route_id} is an underlying share count, got unit {quantity.unit!r}",
            )
            if quantity.status != "known" or quantity.value is None:
                ids.append(self.unknowns.add(_quantity_unknown(route_id)))
            else:
                n_exact = Fraction(Decimal(quantity.value))
        claim_exact, claim_ids = self._claim(instrument, AFFECTS_ROW_AND_CLAIMS)
        ids.extend(claim_ids)
        values: dict[str, Decimal] = {}
        for name in ROW_TERMS[(action, settlement)]:
            if name in CLAIM_TERMS[instrument.kind]:
                continue
            value, unknown = self._quantity(instrument.instrument_id, name)
            if unknown is not None:
                ids.append(self.unknowns.add(_retarget(unknown, AFFECTS_INCREMENTAL)))
            else:
                assert value is not None
                values[name] = value
        price_value: Fraction | None = None
        needs_price = action == "warrant_exercise" and settlement in PRICE_SETTLEMENTS
        if needs_price:
            price_value, price_ids = self._price()
            ids.extend(price_ids)
        if quantity is None:
            # §5.3: selecting no quantity selects the whole remaining claim.
            n_exact = claim_exact
        elif n_exact is not None and claim_exact is not None and n_exact > claim_exact:
            # D5: the selection is capped at the claim; the claim itself survives.
            n_exact = claim_exact
            guards.add(GUARD_CAPPED_AT_CLAIM)
            guards.add(GUARD_CLAIM_SURVIVES)
        if ids or claim_exact is None or n_exact is None:
            return self._unknown_row(instrument.instrument_id, selection, ids, guards)

        incremental_exact = self._incremental(action, settlement, n_exact, values, price_value)
        whole = _floor(incremental_exact)
        fraction = _remainder_string(incremental_exact)

        notice_limited = False
        notice_value, _notice_unknown, has_notice = self._limiter(instrument, NOTICE_NAME)
        if has_notice and notice_value is not None and Fraction(self.horizon_days) < Fraction(notice_value):
            # A25: the notice period limits THIS scenario; the claim stays whole.
            whole = 0
            notice_limited = True
            guards.add(GUARD_NOTICE_LIMITS)
            guards.add(GUARD_CLAIM_SURVIVES)
        cap_value, _cap_unknown, has_cap = self._limiter(instrument, CAP_NAME)
        if has_cap and cap_value is not None:
            cap = Fraction(cap_value) / 100
            if cap < 1:
                position = self._holder_position(instrument.instrument_id)
                if position is None:
                    ids.append(self.unknowns.add(_holder_position_unknown(instrument.instrument_id)))
                    return self._unknown_row(instrument.instrument_id, selection, ids, guards)
                if self.existing_value is None:
                    unknown_ids = list(ids)
                    if self.basis_unknown_id is not None:
                        unknown_ids.append(self.basis_unknown_id)
                    return self._unknown_row(instrument.instrument_id, selection, unknown_ids, guards)
                ceiling = max(0, _floor((cap * self.existing_value - position) / (1 - cap)))
                if ceiling < whole:
                    whole = ceiling
                    guards.add(GUARD_CAP_LIMITS)
                    guards.add(GUARD_CLAIM_SURVIVES)

        gross: Decimal | None = None
        net: Decimal | None = None
        if settlement in NO_CASH_SETTLEMENTS:
            gross = Decimal(0)
            net = Decimal(0)
        else:
            unit_price = values[CASH_PRICE_TERMS[settlement]]
            gross = Decimal(whole) * unit_price
            if notice_limited or gross == 0:
                # Zero issued is zero proceeds: no fee assumption is needed.
                net = Decimal(0)
            elif self.scenario.fee_rate is None:
                self.unknowns.add(_fee_rate_unknown())
            else:
                net = gross * (Decimal(1) - Decimal(self.scenario.fee_rate))
        self.guards.update(guards)
        cash_effect = self._cash_effect(route_id, settlement, gross, net)
        return _Row(
            route_id=route_id,
            instrument_id=instrument.instrument_id,
            action=action,
            settlement=settlement,
            underlying_shares=_exact_string(n_exact),
            incremental_shares=str(whole),
            gross_cash="unknown" if gross is None else _decimal_string(gross),
            net_cash="unknown" if net is None else _decimal_string(net),
            guards=tuple(sorted(guards)),
            unknowns=tuple(sorted(set(ids))),
            fraction=fraction,
            incremental=whole,
            cash_effect=cash_effect,
        )

    def _row_i2(self, instrument: Instrument, selection: ActionSelection, guards: set[str], ids: list[str]) -> _Row:
        """One row on the fixed SPEC_I2 §3 order: amount, price, condition, branch, cap, notice.

        Every limit below — a failed condition, an exchange cap, a holder cap, a
        notice period — limits what THIS SCENARIO delivers.  None of them is
        allowed to touch ``as_converted_claims`` (A25), which ``_claim_i2``
        computed before any of them ran.
        """
        route_id = selection.route_id
        action = selection.action
        settlement = selection.settlement
        instrument_id = instrument.instrument_id
        is_warrant = instrument.kind in WARRANT_KINDS
        trace_items: list[tuple[str, str]] = []
        blockers: list[str] = []

        def unfinished(cash_effect: Any = _UNSET) -> _Row:
            self.guards.update(guards)
            self._merge_variable_trace(instrument_id, trace_items)
            return self._unknown_row(
                instrument_id,
                selection,
                ids,
                guards,
                cash_effect=cash_effect,
                evaluation_order=EVALUATION_ORDER,
                blockers=blockers,
                variable_terms=trace_items,
            )

        # -- step 1: amount -------------------------------------------------
        claim_exact, claim_ids = self._claim(instrument, AFFECTS_ROW_AND_CLAIMS)
        ids.extend(claim_ids)
        amount: Fraction | None = None
        if not is_warrant:
            amount_outcome = self._amount_outcome(instrument)
            ids.extend(self._register(amount_outcome.unknowns, AFFECTS_ROW_AND_CLAIMS))
            trace_items.extend(amount_outcome.trace_items)
            amount = amount_outcome.amount
        n_exact: Fraction | None = None
        quantity = selection.quantity
        if quantity is not None:
            _require(
                quantity.unit == "shares",
                f"supply: the quantity selected for route {route_id} is an underlying share count, got unit {quantity.unit!r}",
            )
            if quantity.status != "known" or quantity.value is None:
                ids.append(self.unknowns.add(_quantity_unknown(route_id)))
            else:
                n_exact = Fraction(Decimal(quantity.value))
        if quantity is None:
            # §5.3: selecting no quantity selects the whole remaining claim.
            n_exact = claim_exact
        elif n_exact is not None and claim_exact is not None and n_exact > claim_exact:
            n_exact = claim_exact
            guards.add(GUARD_CAPPED_AT_CLAIM)
            guards.add(GUARD_CLAIM_SURVIVES)

        # -- step 2: price --------------------------------------------------
        price_name = "exercise_price" if is_warrant else "conversion_price"
        base_count = self._warrant_base(instrument)[0] if is_warrant else None
        branches = self._structure(instrument_id, "settlement_branches")
        outcome = self._price_outcome(
            instrument, price_name, base_count, True if not is_warrant else settlement != "pre_funded"
        )
        ids.extend(self._register(outcome.unknowns, AFFECTS_ROW_AND_CLAIMS))
        self._name_only(outcome.extra_unknowns, AFFECTS_ROW_AND_CLAIMS)
        trace_items.extend(outcome.trace_items)
        blockers.extend(outcome.blockers)
        contract_price = outcome.price
        scenario_price: Fraction | None = None
        if (action == "warrant_exercise" and settlement in PRICE_SETTLEMENTS) or branches is not None:
            scenario_price, price_ids = self._price()
            ids.extend(price_ids)
        if ids or n_exact is None:
            return unfinished()

        # -- step 3: condition ----------------------------------------------
        condition_state = "absent"
        condition = self._structure(instrument_id, "conversion_condition")
        if condition is not None:
            met = variable_terms.condition_met(
                condition, self.scenario.price.path, self.pricing_date, self.path_measure, contract_price, instrument_id
            )
            if met is None and f"conversion_condition_{instrument_id}" in selection.conditions_assumed_met:
                # A scenario may assume a condition it cannot read, but it must
                # say so, and the trace must carry it as an assumption.
                met = True
                condition_state = "assumed_met"
                blockers.append(BLOCKER_CONDITION_ASSUMED_MET)
                trace_items.append(("conversion_condition_assumed_met", "true"))
                trace_items.append(("conversion_condition_is_a_scenario_assumption", "true"))
            elif met is None:
                condition_state = "not_evaluable"
                trace_items.append(("conversion_condition", condition_state))
                ids.append(
                    self.unknowns.add(_retarget(_conversion_condition_unknown(instrument_id), AFFECTS_INCREMENTAL))
                )
                return unfinished()
            elif met:
                condition_state = "met"
            else:
                condition_state = "not_met"
            trace_items.append(("conversion_condition", condition_state))
        condition_failed = condition_state == "not_met"
        if condition_failed:
            guards.add(GUARD_CONDITION_NOT_MET)
            guards.add(GUARD_CLAIM_SURVIVES)
        # S5: a cash make-whole is owed only when the floor ACTUALLY bound and
        # this scenario converts.  A row that delivers nothing books no repayment,
        # and when the make-whole does apply it is named in the ROW's unknowns as
        # well as the envelope's, so the two never disagree.
        make_whole_ids = [
            item.unknown_id
            for item in outcome.extra_unknowns
            if item.unknown_id == f"make_whole_amount_{instrument_id}"
        ]
        make_whole_applies = (
            bool(make_whole_ids)
            and variable_terms.BLOCKER_FLOOR_MAKE_WHOLE in blockers
            and not condition_failed
            and dict(trace_items).get("floor_reached") == "true"
        )

        # -- step 4: branch -------------------------------------------------
        cash_kind: str | None = None
        repayment: Fraction | None = None
        delivered_exact: Fraction
        if branches is not None:
            if action != BRANCH_EVALUATED_ACTION:
                # M3: I2 evaluates settlement branches for a conversion only
                # (SPEC_I2 §3 step 4).  The term itself is valid, so nothing is
                # raised — the row is unknown and NAMES the unknown, which is
                # what tells a reader what would resolve it (§0 item 4).
                ids.append(
                    self.unknowns.add(
                        _retarget(_settlement_branches_not_evaluated_unknown(instrument_id), AFFECTS_INCREMENTAL)
                    )
                )
                return unfinished()
            # A24 / §0 item 5: every admitted branch is priced on its own and
            # recorded as an alternative; only the elected one is delivered.
            guards.add(GUARD_EXCLUSIVE_BRANCHES)
            self.guards.add(GUARD_EXCLUSIVE_BRANCHES)
            if amount is None or contract_price is None or contract_price == 0 or scenario_price is None:
                return unfinished()
            elected_branch = branches.branches[0] if branches.elected_by == "automatic" else settlement
            elected = None
            for branch in branches.branches:
                settled = variable_terms.settle_branch(branch, amount, contract_price, scenario_price)
                self._alternatives.append(
                    {
                        "instrument_id": instrument_id,
                        "route_id": route_id,
                        "branch": branch,
                        "elected": branch == elected_branch,
                        "shares": str(settled.shares),
                        "cash_kind": settled.cash_kind,
                        "cash_amount": _exact_string(settled.cash_amount),
                        "guard": GUARD_EXCLUSIVE_BRANCHES,
                    }
                )
                if branch == elected_branch:
                    elected = settled
            assert elected is not None
            delivered_exact = Fraction(0) if condition_failed else Fraction(elected.shares)
            cash_kind = "no_cash" if condition_failed else elected.cash_kind
            repayment = Fraction(0) if condition_failed else elected.cash_amount
            trace_items.append(("settlement_branch_elected", elected_branch))
            trace_items.append(("settlement_branch_alternatives", ",".join(branches.branches)))
            trace_items.append(("settlement_branch_elected_by", branches.elected_by))
            if elected_branch != settlement:
                trace_items.append(("settlement_branch_named_by_the_action", settlement))
        elif condition_failed:
            delivered_exact = Fraction(0)
            cash_kind = "no_cash"
            repayment = Fraction(0)
        elif action == "conversion" or settlement in ("cash", "pre_funded"):
            delivered_exact = n_exact
        elif scenario_price is not None and contract_price is not None and scenario_price > contract_price:
            delivered_exact = n_exact * (scenario_price - contract_price) / scenario_price
        else:
            delivered_exact = Fraction(0)

        # -- step 5: exchange cap -------------------------------------------
        cap_term, cap_unknown = self._admitted_term(instrument_id, "exchange_cap_shares")
        if cap_unknown is not None:
            ids.append(self.unknowns.add(_retarget(cap_unknown, AFFECTS_INCREMENTAL)))
            return unfinished()
        if cap_term is not None:
            issued_term, issued_unknown = self._admitted_term(instrument_id, "shares_issued_under_instrument")
            approval_term, approval_unknown = self._admitted_term(instrument_id, "shareholder_approval_obtained")
            if issued_unknown is not None:
                ids.append(self.unknowns.add(_retarget(issued_unknown, AFFECTS_INCREMENTAL)))
                return unfinished()
            if approval_unknown is not None:
                ids.append(self.unknowns.add(_retarget(approval_unknown, AFFECTS_INCREMENTAL)))
                return unfinished()
            remaining = variable_terms.exchange_cap_remaining(cap_term, issued_term, approval_term, instrument_id)
            trace_items.extend(remaining.trace_items)
            if remaining.unknown is not None:
                ids.append(self.unknowns.add(_retarget(remaining.unknown, AFFECTS_INCREMENTAL)))
                return unfinished()
            blockers.extend(remaining.blockers)
            if remaining.value is not None:
                ceiling = Fraction(_floor(remaining.value))
                if ceiling < delivered_exact:
                    # A25: the cap limits delivery, never the claim.
                    blocked = Fraction(_floor(delivered_exact)) - ceiling
                    delivered_exact = ceiling
                    guards.add(GUARD_EXCHANGE_CAP_LIMITS_DELIVERY)
                    guards.add(GUARD_CLAIM_SURVIVES)
                    self.guards.add(GUARD_EXCHANGE_CAP_LIMITS_DELIVERY)
                    trace_items.append((TRACE_BLOCKED_BY_EXCHANGE_CAP, str(_floor(blocked))))

        # -- step 6: I1 holder cap and notice period (§5.7), unchanged -------
        whole = _floor(delivered_exact)
        fraction = _remainder_string(delivered_exact)
        notice_limited = False
        notice_value, _notice_unknown, has_notice = self._limiter(instrument, NOTICE_NAME)
        if has_notice and notice_value is not None and Fraction(self.horizon_days) < Fraction(notice_value):
            whole = 0
            notice_limited = True
            guards.add(GUARD_NOTICE_LIMITS)
            guards.add(GUARD_CLAIM_SURVIVES)
        cap_value, _cap_unknown, has_cap = self._limiter(instrument, CAP_NAME)
        if has_cap and cap_value is not None:
            cap = Fraction(cap_value) / 100
            if cap < 1:
                position = self._holder_position(instrument_id)
                if position is None:
                    ids.append(self.unknowns.add(_holder_position_unknown(instrument_id)))
                    return unfinished()
                if self.existing_value is None:
                    unknown_ids = list(ids)
                    if self.basis_unknown_id is not None:
                        unknown_ids.append(self.basis_unknown_id)
                    ids[:] = unknown_ids
                    return unfinished()
                ceiling = max(0, _floor((cap * self.existing_value - position) / (1 - cap)))
                if ceiling < whole:
                    whole = ceiling
                    guards.add(GUARD_CAP_LIMITS)
                    guards.add(GUARD_CLAIM_SURVIVES)

        # -- cash ------------------------------------------------------------
        zero = Quantity.known("0", "usd")
        if make_whole_applies:
            # A make-whole is a repayment whose amount no admitted term states:
            # unknown, never 0 and never a guess.
            ids.extend(make_whole_ids)
            cash_effect = CashEffect(route_id, "repayment", Quantity.unknown("usd"), Quantity.unknown("usd"))
        elif cash_kind == "no_cash":
            cash_effect = CashEffect(route_id, "no_cash", zero, Quantity.known("0", "usd"))
        elif cash_kind == "repayment":
            assert repayment is not None
            money = _money(repayment)
            if money is None:
                ids.append(self.unknowns.add(_inexact_cash_unknown(route_id)))
                cash_effect = CashEffect(route_id, "repayment", Quantity.unknown("usd"), Quantity.unknown("usd"))
            else:
                text = _decimal_string(money)
                cash_effect = CashEffect(route_id, "repayment", Quantity.known(text, "usd"), Quantity.known(text, "usd"))
        elif settlement in NO_CASH_SETTLEMENTS:
            cash_effect = self._cash_effect(route_id, settlement, Decimal(0), Decimal(0))
        else:
            if settlement == "pre_funded":
                residual, residual_unknown = self._quantity(instrument_id, "prefunded_residual_price")
                if residual_unknown is not None:
                    ids.append(self.unknowns.add(_retarget(residual_unknown, AFFECTS_INCREMENTAL)))
                    return unfinished()
                assert residual is not None
                unit_price = Fraction(residual)
            else:
                unit_price = contract_price
            if unit_price is None:
                return unfinished()
            gross = _money(Fraction(whole) * unit_price)
            if gross is None:
                ids.append(self.unknowns.add(_inexact_cash_unknown(route_id)))
                cash_effect = CashEffect(route_id, "proceeds", Quantity.unknown("usd"), Quantity.unknown("usd"))
            else:
                net: Decimal | None
                if notice_limited or gross == 0:
                    # Zero issued is zero proceeds: no fee assumption is needed.
                    net = Decimal(0)
                elif self.scenario.fee_rate is None:
                    self.unknowns.add(_fee_rate_unknown())
                    net = None
                else:
                    net = gross * (Decimal(1) - Decimal(self.scenario.fee_rate))
                cash_effect = self._cash_effect(route_id, settlement, gross, net)

        self.guards.update(guards)
        self._merge_variable_trace(instrument_id, trace_items)
        return _Row(
            route_id=route_id,
            instrument_id=instrument_id,
            action=action,
            settlement=settlement,
            underlying_shares=_exact_string(n_exact),
            incremental_shares=str(whole),
            gross_cash=cash_effect.gross.value if cash_effect.gross.status == "known" else "unknown",
            net_cash=cash_effect.net.value if cash_effect.net.status == "known" else "unknown",
            guards=tuple(sorted(guards)),
            unknowns=tuple(sorted(set(ids))),
            fraction=fraction,
            incremental=whole,
            cash_effect=cash_effect,
            evaluation_order=EVALUATION_ORDER,
            blockers=tuple(sorted(set(blockers))),
            variable_terms=tuple(trace_items),
        )

    def _refused(
        self,
        instrument: Instrument,
        selection: ActionSelection,
        unknown: Unknown,
        guards: Sequence[str] = (),
    ) -> _Row:
        unknown_id = self.unknowns.add(unknown)
        self.guards.update(guards)
        return self._unknown_row(instrument.instrument_id, selection, [unknown_id], guards)

    def _incremental(
        self,
        action: str,
        settlement: str,
        n_exact: Fraction,
        values: Mapping[str, Decimal],
        price_value: Fraction | None,
    ) -> Fraction:
        """The §5.4 incremental-share rule for one row, exactly."""
        if action == "conversion" or settlement in ("cash", "pre_funded"):
            return n_exact
        strike = Fraction(values["exercise_price"])
        if price_value is not None and price_value > strike:
            return n_exact * (price_value - strike) / price_value
        return Fraction(0)

    # -- components (§5.8): four questions, never a sum ---------------------

    def _incremental_component(self, rows: Sequence[_Row]) -> Quantity:
        if not rows:
            return Quantity.known("0", "shares", share_basis="scenario_incremental_issuance")
        if any(row.incremental is None for row in rows):
            return Quantity.unknown("shares", share_basis="scenario_incremental_issuance")
        return Quantity.known(str(sum(row.incremental or 0 for row in rows)), "shares", share_basis="scenario_incremental_issuance")

    def _claims_component(self) -> tuple[Quantity, list[dict[str, Any]]]:
        entries: list[dict[str, Any]] = []
        total = 0
        any_unknown = False
        eligible = [
            item
            for item in self.instruments.instruments
            if item.status in ELIGIBLE_STATUSES and item.kind in CLAIMED_KINDS
        ]
        for instrument in sorted(eligible, key=lambda item: item.instrument_id):
            claim, _ids = self._claim(instrument, AFFECTS_CLAIMS)
            if claim is None:
                any_unknown = True
                entries.append(
                    {
                        "instrument_id": instrument.instrument_id,
                        "kind": instrument.kind,
                        "claim": "unknown",
                        "remainder": "0",
                    }
                )
                continue
            whole = _floor(claim)
            total += whole
            entries.append(
                {
                    "instrument_id": instrument.instrument_id,
                    "kind": instrument.kind,
                    "claim": str(whole),
                    "remainder": _remainder_string(claim),
                }
            )
        if not eligible:
            return Quantity(unit="shares", status="not_applicable", share_basis="assumed_as_converted"), entries
        if any_unknown:
            return Quantity.unknown("shares", share_basis="assumed_as_converted"), entries
        return Quantity.known(str(total), "shares", share_basis="assumed_as_converted"), entries

    def _resale_component(self) -> tuple[Quantity, list[dict[str, Any]], list[CashEffect]]:
        entries: list[dict[str, Any]] = []
        effects: list[CashEffect] = []
        total = 0
        any_unknown = False
        common = [
            item
            for item in self.instruments.instruments
            if item.status in ELIGIBLE_STATUSES and item.kind == "common"
        ]
        for instrument in sorted(common, key=lambda item: item.instrument_id):
            if self._term(instrument.instrument_id, RESALE_NAME) is None:
                continue
            value, unknown = self._quantity(instrument.instrument_id, RESALE_NAME)
            route_id = f"resale_{instrument.instrument_id}"
            if value is None:
                any_unknown = True
                assert unknown is not None
                self.unknowns.add(_retarget(unknown, AFFECTS_RESALE))
                registered = "unknown"
                whole_text = "unknown"
            else:
                whole = _floor(Fraction(value))
                total += whole
                registered = _decimal_string(value)
                whole_text = str(whole)
            entries.append(
                {
                    "instrument_id": instrument.instrument_id,
                    "kind": instrument.kind,
                    "registered_shares": registered,
                    "whole_shares": whole_text,
                    "cash_route_id": route_id,
                }
            )
            # A23: a resale of already outstanding shares mints no new share and
            # pays the issuer nothing, whatever the registered count turns out to be.
            effects.append(
                CashEffect(route_id, "no_cash", Quantity.known("0", "usd"), Quantity.known("0", "usd"))
            )
        if not entries:
            quantity = Quantity(unit="shares", status="not_applicable", share_basis="potentially_resalable_existing")
            return quantity, entries, effects
        if any_unknown:
            return Quantity.unknown("shares", share_basis="potentially_resalable_existing"), entries, effects
        return Quantity.known(str(total), "shares", share_basis="potentially_resalable_existing"), entries, effects

    # -- projection ---------------------------------------------------------

    def run(self) -> tuple[dict[str, Any], SupplyEnvelope]:
        rows = [
            self._row(selection)
            for selection in sorted(self.scenario.actions, key=lambda item: item.route_id)
        ]
        if any(row.settlement == "pre_funded" for row in rows):
            self.guards.add(GUARD_PREFUNDED_NOT_RECOUNTED)
        incremental = self._incremental_component(rows)
        claims, claim_entries = self._claims_component()
        resalable, resale_entries, resale_effects = self._resale_component()
        cash_effects = sorted(
            [row.cash_effect for row in rows if row.cash_effect is not None] + resale_effects,
            key=lambda item: item.route_id,
        )
        route_ids = [item.route_id for item in cash_effects]
        _require(len(set(route_ids)) == len(route_ids), f"supply: duplicate cash effect route ids {sorted(route_ids)}")

        inputs = {
            "supply_inputs": {
                "instruments": self.instruments.as_record(),
                "basis": self.basis.as_record(),
            },
            "scenario_id": self.scenario.scenario_id,
        }
        state_id = stable_id("state", inputs)
        # A receipt states the rules it ran under.  A scenario with no I2 term
        # ran only the I1 table, so its digest is unchanged (SPEC_I2 §0 item 2).
        rules = SETTLEMENT_RULES + VARIABLE_TERM_RULES if self.i2_active else SETTLEMENT_RULES
        receipt = CalculationReceipt.build(
            inputs=inputs,
            rule_digest=sha256_of(rules),
            implementation=IMPLEMENTATION,
            computed_at=self.scenario.as_of,
            scenario_id=self.scenario.scenario_id,
        )
        unknowns = self.unknowns.sorted()
        guards = tuple(sorted(self.guards))
        envelope = SupplyEnvelope(
            state_id=state_id,
            scenario_id=self.scenario.scenario_id,
            existing_outstanding=self.existing,
            incremental_issuance=incremental,
            as_converted_claims=claims,
            resalable_existing=resalable,
            receipt=receipt,
            cash_effects=tuple(cash_effects),
            double_count_guards=guards,
            unknowns=unknowns,
        )
        trace = {
            "schema": TRACE_SCHEMA,
            "implementation": IMPLEMENTATION,
            "state_id": state_id,
            "scenario_id": self.scenario.scenario_id,
            "price": self._price_record(),
            "horizon_days": str(self.horizon_days),
            "rows": [row.as_trace_record() for row in rows],
            "claims": claim_entries,
            "resale": resale_entries,
            "unknowns": [item.unknown_id for item in unknowns],
            "guards": list(guards),
        }
        if self.i2_active:
            # I2 keys are added only when an instrument carries an I2 term, so a
            # pre-I2 trace keeps exactly its I1 keys and digest.
            trace["alternatives"] = list(self._alternatives)
            trace["maximum_issuable"] = {key: self._maximum_issuable[key] for key in sorted(self._maximum_issuable)}
            trace["variable_terms"] = {key: dict(self._variable_trace[key]) for key in sorted(self._variable_trace)}
        return trace, envelope


def supply_trace(instruments: InstrumentSet, basis: ShareBasisResult, scenario: FinancingScenario) -> dict[str, Any]:
    """The per-action rows behind :func:`evaluate_supply`, as a plain dict.

    Every number is an exact decimal string, an exact reduced ``num/den`` for a
    rational that does not terminate in base 10, or the literal ``"unknown"``.
    There is no float and no total: the four components are never added.
    """
    trace, _envelope = _Evaluation(instruments, basis, scenario).run()
    return trace


def evaluate_supply(instruments: InstrumentSet, basis: ShareBasisResult, scenario: FinancingScenario) -> SupplyEnvelope:
    """Project the supply computation onto the frozen C0 ``SupplyEnvelope``."""
    _trace, envelope = _Evaluation(instruments, basis, scenario).run()
    return envelope


__all__ = [
    "CLAIM_TERMS",
    "EVALUATION_ORDER",
    "GUARD_CONDITION_NOT_MET",
    "GUARD_EXCHANGE_CAP_LIMITS_DELIVERY",
    "GUARD_EXCLUSIVE_BRANCHES",
    "GUARD_NO_ASSUMED_FLOOR",
    "GUARD_NO_PRICE_AFTER_PRICING_DATE",
    "I2_TERM_NAMES",
    "VARIABLE_TERM_RULES",
    "CONVERTIBLE_KINDS",
    "ELIGIBLE_STATUSES",
    "IMPLEMENTATION",
    "PERMITTED_SETTLEMENTS",
    "ROW_TERMS",
    "SETTLEMENT_RULES",
    "SUPPLY_ACTIONS",
    "TRACE_SCHEMA",
    "WARRANT_KINDS",
    "evaluate_supply",
    "supply_trace",
]
