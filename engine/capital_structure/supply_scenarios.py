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

from engine.capital_structure.issuer_state_contracts import (
    ECONOMIC_TERM_UNITS,
    ActionSelection,
    CalculationReceipt,
    CashEffect,
    ContractViolation,
    EconomicTerm,
    FinancingScenario,
    Instrument,
    InstrumentSet,
    Quantity,
    ShareBasisResult,
    SupplyEnvelope,
    Unknown,
    sha256_of,
    stable_id,
)

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


def _refuse_numbers(value: Any, path: str = "<root>") -> None:
    """No float and no non-string number anywhere on the I1 path (§0 item 3)."""
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (float, int, Decimal, complex, Fraction)):
        raise ContractViolation(f"{path}: exact decimal strings only, a {type(value).__name__} is refused ({value!r})")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(isinstance(key, str), f"{path}: non-string key {key!r}")
            _refuse_numbers(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_numbers(item, f"{path}[{index}]")
        return
    raise ContractViolation(f"{path}: unsupported type {type(value).__name__}")


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

    def as_trace_record(self) -> dict[str, Any]:
        return {
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

    # -- claims (§5.8, D4) --------------------------------------------------

    def _claim(self, instrument: Instrument, affects: Sequence[str]) -> tuple[Fraction | None, list[str]]:
        """The instrument's full underlying-share claim, exact and unfloored."""
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
        if settlement not in PERMITTED_SETTLEMENTS[instrument.kind]:
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
        receipt = CalculationReceipt.build(
            inputs=inputs,
            rule_digest=sha256_of(SETTLEMENT_RULES),
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
