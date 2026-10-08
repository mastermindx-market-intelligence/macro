"""Isolated context math; no collection, pricing model, prediction or decision authority.

Every quantity is an externally qualified observation, including explicit zero.
Invalid contract values raise ValueError. Missing/unavailable information yields
NOT_COMPUTABLE or NOT_SCORED with a reason and null quantitative outputs.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from enum import Enum
from fractions import Fraction
from typing import Optional, Sequence, Union

Number = Union[int, float, Decimal]
METHOD_DV01 = "provided_duration.v1"
METHOD_CASH = "private_settlement_cash.v1"
METHOD_IMPORTANCE = "same_cohort_midrank.v1"


class SecurityClass(str, Enum):
    BILL = "BILL"
    CMB = "CMB"
    NOTE = "NOTE"
    BOND = "BOND"
    TIPS = "TIPS"
    FRN = "FRN"


class InputRole(str, Enum):
    QUALIFIED = "EXTERNALLY_QUALIFIED"
    SYNTHETIC = "SYNTHETIC_GOLDEN_FIXTURE"
    RESULT = "AUCTION_RESULT"


@dataclass(frozen=True)
class Observation:
    value: Optional[Number]
    unit: str
    currency: Optional[str]
    known_at: Optional[datetime]
    as_of: Optional[datetime]
    source_ref: str
    input_method: str
    role: InputRole


def _number(value: Number, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{name}: expected a finite int, float or Decimal (not bool)")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{name}: nonfinite number")
    return result


def _exact_decimal(value: Fraction) -> Decimal:
    """Exact for sums/products of finite decimal inputs and powers of ten.

    The denominator in these calculations contains only factors 2 and 5.
    Percentiles, which can repeat, use a separate explicit 40-digit context.
    """
    precision = max(40, len(str(abs(value.numerator))) + len(str(value.denominator)))
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        return Decimal(value.numerator) / Decimal(value.denominator)


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty string required")


def _clock(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name}: timezone-aware datetime required; date-only is ineligible")


def _enum(value, enum_type, name):
    if not isinstance(value, enum_type):
        raise ValueError(f"{name}: {enum_type.__name__} member required")


def _observation(obs: Optional[Observation], unit: str, currency: Optional[str],
                 decision_at: datetime, name: str) -> tuple[Optional[Decimal], Optional[str]]:
    if obs is None:
        return None, f"{name}: missing observation"
    if not isinstance(obs, Observation):
        raise ValueError(f"{name}: Observation required")
    if obs.unit != unit or obs.currency != currency:
        raise ValueError(f"{name}: expected unit={unit}, currency={currency}")
    _text(obs.source_ref, f"{name}.source_ref")
    _text(obs.input_method, f"{name}.input_method")
    _enum(obs.role, InputRole, f"{name}.role")
    value = None if obs.value is None else _number(obs.value, name)
    for key in ("known_at", "as_of"):
        clock = getattr(obs, key)
        if clock is not None:
            _clock(clock, f"{name}.{key}")
    if obs.known_at is not None and obs.as_of is not None and obs.as_of > obs.known_at:
        raise ValueError(f"{name}: observation as_of exceeds receipt known_at")
    if value is None:
        return None, f"{name}: missing value"
    if obs.known_at is None or obs.as_of is None:
        return None, f"{name}: missing known_at or as_of"
    if obs.known_at > decision_at or obs.as_of > decision_at:
        return None, f"{name}: not known/observed by decision_at"
    return value, None


def _provenance(obs):
    return None if obs is None else asdict(obs)


def calculate_dv01(*, security_class: SecurityClass, decision_at: datetime,
                   market_value: Optional[Observation],
                   duration: Optional[Observation],
                   currency: str,
                   measure_basis: Optional[str] = None) -> dict:
    """Positive sensitivity magnitude in USD/bp from supplied durations in years.

    Required basis: NOMINAL_YIELD_MODIFIED for nominal/Bill/CMB,
    REAL_YIELD_MODIFIED for TIPS, or an explicit supplier basis for FRN
    effective rate duration. TIPS market_value unit is INDEXED_USD.
    Result-role inputs are never eligible for this ex-ante capability.
    """
    _clock(decision_at, "decision_at")
    _enum(security_class, SecurityClass, "security_class")
    if currency != "USD":
        raise ValueError("DV01 capability requires explicit USD currency")
    is_tips = security_class == SecurityClass.TIPS
    is_frn = security_class == SecurityClass.FRN
    basis_required = "REAL_YIELD_MODIFIED" if is_tips else "NOMINAL_YIELD_MODIFIED"
    if measure_basis is not None:
        _text(measure_basis, "measure_basis")
        if not is_frn and measure_basis != basis_required:
            raise ValueError(f"measure_basis must be {basis_required}")
        if is_frn and measure_basis in ("LEGAL_MATURITY", "NOMINAL_YIELD_MODIFIED", "REAL_YIELD_MODIFIED"):
            raise ValueError("FRN requires supplied effective rate duration basis")
    value, value_reason = _observation(market_value, "INDEXED_USD" if is_tips else "USD",
                                       currency, decision_at, "market_value")
    years, duration_reason = _observation(duration, "EFFECTIVE_RATE_DURATION_YEARS" if is_frn
                                          else "MODIFIED_DURATION_YEARS", None,
                                          decision_at, "duration")
    # Validate signs even on otherwise ineligible future observations.
    for obs, name in ((market_value, "market_value"), (duration, "duration")):
        if obs is not None and obs.value is not None and _number(obs.value, name) < 0:
            raise ValueError(f"{name}: negative magnitude")
    result = {
        "status": "NOT_COMPUTABLE", "null_reason": None,
        "security_class": security_class.value, "currency": currency,
        "sensitivity_axis": "REAL_YIELD" if is_tips else "FRN_EFFECTIVE_RATE" if is_frn else "NOMINAL_YIELD",
        "dv01_usd_per_bp": None, "dv01_million_usd_per_bp": None,
        "measure_basis": measure_basis, "method_version": METHOD_DV01,
        "decision_at": decision_at, "is_context_only": True,
        "inputs": {"market_value": _provenance(market_value), "duration": _provenance(duration)},
    }
    reasons = [r for r in (value_reason, duration_reason) if r]
    if measure_basis is None:
        reasons.append("missing measure_basis")
    if any(obs is not None and obs.role == InputRole.RESULT for obs in (market_value, duration)):
        reasons.append("auction result is not an eligible ex-ante market input")
    if reasons:
        result["null_reason"] = "; ".join(reasons)
        return result
    sensitivity = Fraction(value) * Fraction(years) / 10000
    dv01 = _exact_decimal(sensitivity)
    million = _exact_decimal(sensitivity / 1000000)
    result.update(status="COMPUTABLE", dv01_usd_per_bp=dv01,
                  dv01_million_usd_per_bp=million)
    return result


class CashKind(str, Enum):
    PRIVATE_PROCEEDS_EX_SOMA = "PRIVATE_PROCEEDS_EX_SOMA"
    PRIVATE_MARKETABLE_REDEMPTION = "PRIVATE_MARKETABLE_REDEMPTION"
    FUNDED_BUYBACK_OUTLAY = "FUNDED_BUYBACK_OUTLAY"


@dataclass(frozen=True)
class CashComponent:
    component_id: str
    kind: CashKind
    cohort_id: str
    settlement_date: date
    amount: Optional[Observation]  # Nonnegative cash magnitude; kind supplies the sign.


def settlement_cash(*, cohort_id: str, settlement_date: date, currency: str,
                    decision_at: datetime,
                    proceeds: Optional[Sequence[CashComponent]],
                    redemptions: Optional[Sequence[CashComponent]],
                    buybacks: Optional[Sequence[CashComponent]],
                    completeness_certified: bool = False,
                    gross_offered_face: Optional[Observation] = None,
                    soma_context: Optional[Observation] = None) -> dict:
    """Private cash only. Missing/empty category needs a sourced explicit zero.

    completeness_certified asserts the supplying owner has enumerated every
    necessary component for this scope/cohort; the math leaf cannot prove it.
    Optional gross face/SOMA are explanatory observations and never deducted.
    """
    _text(cohort_id, "cohort_id")
    if type(settlement_date) is not date:
        raise ValueError("settlement_date: date required")
    if currency != "USD":
        raise ValueError("settlement capability requires explicit USD currency")
    _clock(decision_at, "decision_at")
    if type(completeness_certified) is not bool:
        raise ValueError("completeness_certified: bool required")
    reasons = [] if completeness_certified else ["component inventory not certified complete"]
    totals, drivers, seen = {}, [], set()
    groups = ((CashKind.PRIVATE_PROCEEDS_EX_SOMA, proceeds, 1),
              (CashKind.PRIVATE_MARKETABLE_REDEMPTION, redemptions, -1),
              (CashKind.FUNDED_BUYBACK_OUTLAY, buybacks, -1))
    with localcontext() as ctx:
        ctx.prec = 40
        for kind, components, sign in groups:
            total = Fraction(0)
            missing = not components
            if missing:
                reasons.append(f"{kind.value}: missing components or observed zero")
            for component in components or ():
                if not isinstance(component, CashComponent):
                    raise ValueError("CashComponent required")
                _enum(component.kind, CashKind, "cash kind")
                _text(component.component_id, "component_id")
                if component.component_id in seen:
                    raise ValueError("duplicate cash component_id")
                seen.add(component.component_id)
                if component.kind != kind or component.cohort_id != cohort_id or component.settlement_date != settlement_date:
                    raise ValueError("cash component kind/cohort/settlement mismatch")
                if type(component.settlement_date) is not date:
                    raise ValueError("cash component settlement_date: date required")
                amount, reason = _observation(component.amount, "USD", currency,
                                               decision_at, component.component_id)
                if component.amount is not None and component.amount.value is not None and _number(component.amount.value, "cash amount") < 0:
                    raise ValueError("cash input must be nonnegative; kind supplies sign")
                if reason:
                    missing = True
                    reasons.append(reason)
                else:
                    total += Fraction(amount)
                drivers.append({"component_id": component.component_id, "kind": kind.value,
                                "sign": sign, "signed_cash_usd": None if amount is None else amount if sign == 1 else amount.copy_negate(),
                                "input": _provenance(component.amount)})
            totals[kind.value] = None if missing else _exact_decimal(total)
        net = None if reasons else _exact_decimal(Fraction(totals[CashKind.PRIVATE_PROCEEDS_EX_SOMA.value])
                                    - Fraction(totals[CashKind.PRIVATE_MARKETABLE_REDEMPTION.value])
                                    - Fraction(totals[CashKind.FUNDED_BUYBACK_OUTLAY.value]))
    context = {}
    for key, obs in (("gross_offered_face", gross_offered_face), ("soma_context", soma_context)):
        value, reason = _observation(obs, "USD", currency, decision_at, key)
        if obs is not None and obs.value is not None and _number(obs.value, key) < 0:
            raise ValueError(f"{key}: negative magnitude")
        context[key] = {"value_usd": value, "null_reason": reason, "input": _provenance(obs)}
    return {
        "status": "NOT_COMPUTABLE" if reasons else "COMPUTABLE",
        "null_reason": "; ".join(reasons) if reasons else None,
        "net_private_cash_usd": net, "currency": currency,
        "cohort_id": cohort_id, "settlement_date": settlement_date,
        "decision_at": decision_at, "method_version": METHOD_CASH,
        "component_totals_usd": totals, "components": drivers, "context": context,
        "reserve_pressure": None, "is_context_only": True,
        "accounting_scope": "certified private marketable cash settlement cohort; proceeds already exclude SOMA",
        "limits": "not TGA change, reserve drain, purchaser funding source or debt reduction; supplied cash only",
    }


class MetricAxis(str, Enum):
    NOMINAL_DV01 = "NOMINAL_DV01"
    REAL_DV01 = "REAL_DV01"
    FRN_EFFECTIVE_DV01 = "FRN_EFFECTIVE_DV01"
    ABS_NET_PRIVATE_CASH = "ABS_NET_PRIVATE_CASH"


@dataclass(frozen=True)
class MagnitudeEvent:
    event_id: str
    event_at: datetime
    security_class: SecurityClass
    tenor_cohort: str  # Explicit canonical original-tenor cohort supplied by owner.
    metric_axis: MetricAxis
    measure_basis: str
    magnitude: Optional[Observation]


def _magnitude_event(event: MagnitudeEvent, decision_at: datetime):
    if not isinstance(event, MagnitudeEvent):
        raise ValueError("MagnitudeEvent required")
    _text(event.event_id, "event_id")
    _clock(event.event_at, "event_at")
    _enum(event.security_class, SecurityClass, "security_class")
    _enum(event.metric_axis, MetricAxis, "metric_axis")
    _text(event.tenor_cohort, "tenor_cohort")
    _text(event.measure_basis, "measure_basis")
    required = (MetricAxis.REAL_DV01 if event.security_class == SecurityClass.TIPS else
                MetricAxis.FRN_EFFECTIVE_DV01 if event.security_class == SecurityClass.FRN else
                MetricAxis.NOMINAL_DV01)
    if event.metric_axis not in (required, MetricAxis.ABS_NET_PRIVATE_CASH):
        raise ValueError("metric axis incompatible with security class")
    unit = "USD" if event.metric_axis == MetricAxis.ABS_NET_PRIVATE_CASH else "USD_PER_BP"
    value, reason = _observation(event.magnitude, unit, "USD", decision_at, event.event_id)
    if event.magnitude is not None and event.magnitude.value is not None and _number(event.magnitude.value, "magnitude") < 0:
        raise ValueError("magnitude must be nonnegative; funding axis is absolute net cash")
    return value, reason


def importance_percentile(*, current: MagnitudeEvent,
                          history: Sequence[MagnitudeEvent], decision_at: datetime) -> dict:
    """Midrank 100*(strictly-less + 0.5*ties)/n; minimum 20 distinct events.

    Only same class, tenor, axis, unit and measure basis can enter. Baseline
    events must precede both current event and decision time, with observation
    known/as_of no later than decision. Thresholds 75/90 are product choices.
    """
    _clock(decision_at, "decision_at")
    value, reason = _magnitude_event(current, decision_at)
    baseline, ids, baseline_inputs, seen = [], [], [], set()
    for event in history:
        candidate, missing = _magnitude_event(event, decision_at)
        if event.event_id in seen:
            raise ValueError("history requires one vintage per distinct event_id")
        seen.add(event.event_id)
        if (event.event_id != current.event_id and event.event_at < current.event_at
                and event.event_at < decision_at and not missing
                and event.security_class == current.security_class
                and event.tenor_cohort == current.tenor_cohort
                and event.metric_axis == current.metric_axis
                and event.measure_basis == current.measure_basis
                and event.magnitude.role != InputRole.RESULT):
            baseline.append(candidate)
            ids.append(event.event_id)
            baseline_inputs.append(asdict(event))
    if current.magnitude is not None and current.magnitude.role == InputRole.RESULT:
        reason = "auction result is not eligible for ex-ante importance"
    if not reason and len(baseline) < 20:
        reason = "insufficient comparable past-only history: minimum n=20"
    less = equal = percentile = label = None
    if not reason:
        less = sum(item < value for item in baseline)
        equal = sum(item == value for item in baseline)
        with localcontext(Context(prec=40, rounding=ROUND_HALF_EVEN)):
            percentile = Decimal(100) * (Decimal(less) + Decimal(equal) / 2) / len(baseline)
        label = "HIGH" if percentile >= 90 else "WATCH" if percentile >= 75 else "ROUTINE"
    return {
        "status": "NOT_SCORED" if reason else "SCORED", "null_reason": reason,
        "percentile": percentile, "importance_label": label,
        "is_context_only": True, "method_version": METHOD_IMPORTANCE,
        "threshold_policy": {"minimum_n": 20, "watch_gte": 75, "high_gte": 90,
                             "basis": "versioned product choice; not fitted or validated"},
        "drivers": {"magnitude": value, "unit": "USD" if current.metric_axis == MetricAxis.ABS_NET_PRIVATE_CASH else "USD_PER_BP",
                    "metric_axis": current.metric_axis.value, "measure_basis": current.measure_basis,
                    "security_class": current.security_class.value, "tenor_cohort": current.tenor_cohort,
                    "n": len(baseline), "strictly_less": less, "ties": equal,
                    "baseline_event_ids": ids},
        "decision_at": decision_at, "current_input": asdict(current),
        "baseline_inputs": baseline_inputs,
    }
