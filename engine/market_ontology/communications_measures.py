"""Bounded deterministic arithmetic for the Communications A1 comparison.

These frozen objects are IN-MEMORY adapters, not native records or a source store.
Callers must first validate immutable owner inputs and the actual reviewed rule
receipt. A nonempty ref is necessary binding metadata, NEVER proof of admission.
This module does not read files/network, mint identities, validate source rights,
load research fixtures, publish, rank, forecast, or obtain trading authority.

Different definitions need an exact owner-reviewed relation and input binding.
Different accounting bases are conservatively refused: this adapter cannot infer
an accounting bridge from a relation label. Unknown precision is never expanded
into invented support. Guidance uses the entire finite support, not its midpoint.
Any numeric distance outside guidance is explicitly from its original bound, not
consensus. Non-point arithmetic is qualified documentary arithmetic; Result does
not purport to carry a derived underlying interval.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from typing import Literal

@dataclass(frozen=True)
class Interval:
    lower: Decimal
    upper: Decimal
    lower_inclusive: bool
    upper_inclusive: bool

@dataclass(frozen=True)
class Measure:
    ref: str
    metric: str
    population: str
    period: tuple[str, str]
    currency: str | None
    scale: Decimal
    basis: str
    value: Decimal | None
    domain: str
    definition_ref: str
    unit: str
    support: Interval | None
    support_basis: Literal['exact', 'source_interval', 'reviewed_nearest', 'unknown']
    support_ref: str | None

@dataclass(frozen=True)
class Guidance:
    ref: str
    metric: str
    population: str
    period: tuple[str, str]
    currency: str | None
    scale: Decimal
    basis: str
    lower: Decimal | None
    upper: Decimal | None
    lower_inclusive: bool | None
    upper_inclusive: bool | None
    published: str
    vintage: str
    definition_ref: str
    unit: str
    bounds_basis: Literal['stated_threshold', 'approximate', 'unknown']

@dataclass(frozen=True)
class InputBinding:
    role: str
    ref: str
    definition_ref: str
    population: str
    period: tuple[str, str]
    unit: str
    currency: str | None
    scale: Decimal
    domain: str

@dataclass(frozen=True)
class CashRole:
    component_key: str
    binding_role: str
    orientation: Literal['signed_flow', 'positive_magnitude']
    coefficient: Literal[-1, 1]

@dataclass(frozen=True)
class ComparisonRule:
    revision: str
    operation: Literal['period_absolute', 'period_pct', 'guidance', 'cash']
    bindings: tuple[InputBinding, ...]
    relation_ref: str
    review_ref: str
    interpretation_basis: Literal['underlying_interval', 'published_figures']
    cash_roles: tuple[CashRole, ...]

@dataclass(frozen=True)
class CashComponent:
    component_key: str
    measure_ref: str
    orientation: Literal['signed_flow', 'positive_magnitude']
    coefficient: Literal[-1, 1]

@dataclass(frozen=True)
class Result:
    status: Literal['COMPARABLE', 'QUALIFIED', 'INCOMPATIBLE', 'UNAVAILABLE']
    value: Decimal | None
    label: str
    refs: tuple[str, ...]
    reason: str | None
    rule_revision: str
    formula: str
    interpretation_basis: str


# Finite in-memory limits apply BEFORE arithmetic, including scale conversion.
# 48 coefficient digits and exponents +/-32 bound exact sums/products below
# 256 significant digits. Division is deterministically rounded, not advertised
# as an exact finite decimal. Caller context and flags are never modified.
_CONTEXT = Context(prec=256, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999)
_MAX_INPUTS = 16
_DOMAINS = frozenset(('signed_amount', 'nonnegative_amount', 'nonnegative_count',
                      'percent', 'fraction'))
_BIND_FIELDS = ('ref', 'definition_ref', 'population', 'period', 'unit', 'currency', 'scale')


def _text(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= 240 and bool(value.strip())


def _decimal(value: object) -> bool:
    if type(value) is not Decimal or not value.is_finite():
        return False
    parts = value.as_tuple()
    return len(parts.digits) <= 48 and abs(parts.exponent) <= 32


def _date(value: object) -> bool:
    if type(value) is not str or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _period(value: object) -> bool:
    return (type(value) is tuple and len(value) == 2
            and all(_date(x) for x in value) and value[0] <= value[1])


def _common(value: Measure | Guidance) -> bool:
    return (all(_text(getattr(value, field)) for field in
                ('ref', 'metric', 'population', 'basis', 'definition_ref', 'unit'))
            and _period(value.period) and _decimal(value.scale) and value.scale > 0
            and (value.currency is None or _text(value.currency)))


def _domain_value(value: Decimal, domain: str) -> bool:
    if domain == 'signed_amount':
        return True
    if value < 0:
        return False
    if domain == 'fraction':
        return value <= 1
    if domain == 'percent':
        return value <= 100
    if domain == 'nonnegative_count':
        return value == value.to_integral_value()
    return domain == 'nonnegative_amount'


def _interval(value: object) -> bool:
    return (type(value) is Interval and _decimal(value.lower) and _decimal(value.upper)
            and type(value.lower_inclusive) is bool and type(value.upper_inclusive) is bool
            and (value.lower < value.upper or
                 (value.lower == value.upper and value.lower_inclusive and value.upper_inclusive)))


def _contains(interval: Interval, value: Decimal) -> bool:
    return ((value > interval.lower or (value == interval.lower and interval.lower_inclusive))
            and (value < interval.upper or (value == interval.upper and interval.upper_inclusive)))


def _measure(value: object) -> bool:
    if (type(value) is not Measure or not _common(value)
            or type(value.domain) is not str or value.domain not in _DOMAINS):
        return False
    expected_unit = {'signed_amount': 'currency', 'nonnegative_amount': 'currency',
                     'nonnegative_count': 'count', 'percent': 'percent', 'fraction': 'fraction'}[value.domain]
    if value.unit != expected_unit or (value.currency is not None) != (expected_unit == 'currency'):
        return False
    if expected_unit in ('percent', 'fraction', 'count') and value.scale != 1:
        return False
    if value.value is not None and (not _decimal(value.value) or not _domain_value(value.value, value.domain)):
        return False
    if value.support_ref is not None and not _text(value.support_ref):
        return False
    if value.support_basis == 'unknown':
        return value.support is None
    if value.support_basis not in ('exact', 'source_interval', 'reviewed_nearest') or not _interval(value.support):
        return False
    support = value.support
    if not all(_domain_value(x, value.domain) for x in (support.lower, support.upper)):
        return False
    if value.value is not None and not _contains(support, value.value):
        return False
    if value.support_basis == 'exact':
        return value.value is not None and support.lower == support.upper == value.value
    if not _text(value.support_ref):
        return False
    return value.support_basis != 'reviewed_nearest' or value.value is not None


def _guidance(value: object) -> bool:
    if type(value) is not Guidance or not _common(value) or not _date(value.published):
        return False
    if value.bounds_basis not in ('stated_threshold', 'approximate', 'unknown') or not _text(value.vintage):
        return False
    for bound, inclusive in ((value.lower, value.lower_inclusive), (value.upper, value.upper_inclusive)):
        if bound is None:
            if inclusive is not None:
                return False
        elif not _decimal(bound) or type(inclusive) is not bool:
            return False
    if value.lower is None and value.upper is None:
        return value.bounds_basis != 'stated_threshold'
    return (value.lower is None or value.upper is None or value.lower < value.upper
            or (value.lower == value.upper and value.lower_inclusive and value.upper_inclusive))


def _result(rule, inputs, *, status='INCOMPATIBLE', reason=None,
            value=None, label='COMPARISON_UNAVAILABLE', formula='') -> Result:
    refs = tuple(x.ref for x in inputs[:_MAX_INPUTS]
                 if type(x) in (Measure, Guidance) and _text(x.ref))
    revision = rule.revision if type(rule) is ComparisonRule and _text(rule.revision) else ''
    basis = rule.interpretation_basis if type(rule) is ComparisonRule and _text(rule.interpretation_basis) else ''
    return Result(status, value, label, refs, reason, revision, formula, basis)


def _rule_problem(rule: object, operation: str) -> str | None:
    if rule is None:
        return 'RULE_REQUIRED'
    if type(rule) is not ComparisonRule:
        return 'INVALID_RULE'
    if not all(_text(x) for x in (rule.revision, rule.relation_ref, rule.review_ref)):
        return 'RULE_NOT_REVIEWED'
    if rule.operation != operation:
        return 'RULE_OPERATION_MISMATCH'
    if (rule.interpretation_basis not in ('underlying_interval', 'published_figures')
            or type(rule.bindings) is not tuple or not 1 <= len(rule.bindings) <= _MAX_INPUTS
            or type(rule.cash_roles) is not tuple):
        return 'INVALID_RULE'
    if operation != 'cash' and rule.cash_roles:
        return 'INVALID_RULE'
    if any(type(b) is not InputBinding or not _text(b.role) for b in rule.bindings):
        return 'INVALID_RULE'
    if (len({b.role for b in rule.bindings}) != len(rule.bindings)
            or any(not _text(b.ref) for b in rule.bindings)):
        return 'INPUT_BINDING_MISMATCH'
    return None


def _bound(rule: ComparisonRule, inputs: tuple[tuple[str, Measure | Guidance], ...]) -> bool:
    by_role = {b.role: b for b in rule.bindings}
    if len(inputs) != len(by_role) or set(by_role) != {role for role, _ in inputs}:
        return False
    for role, value in inputs:
        binding = by_role[role]
        if (not _decimal(binding.scale) or type(binding.domain) is not str
                or binding.domain not in _DOMAINS):
            return False
        if any(getattr(binding, key) != getattr(value, key) for key in _BIND_FIELDS):
            return False
        if type(value) is Measure and binding.domain != value.domain:
            return False
        if type(value) is Guidance:
            if any(x is not None and not _domain_value(x, binding.domain) for x in (value.lower, value.upper)):
                return False
    return True


def _same_scope(a: Measure, b: Measure | Guidance, *, same_period=False, cash=False) -> bool:
    fields = ['population', 'unit', 'currency', 'basis']
    if not cash:
        fields.append('metric')
    if same_period:
        fields.append('period')
    return all(getattr(a, key) == getattr(b, key) for key in fields)


def _point_exact(value: Measure) -> bool:
    return value.support is not None and value.support.lower == value.support.upper


def compare_period(current: Measure, prior: Measure, *, rule: ComparisonRule, mode='pct') -> Result:
    """Compare the rule's exact two fiscal intervals; never match by duration.

    Rates support explicit absolute-unit changes only. Accounting-basis changes
    require an upstream accepted bridge, not a guessed local normalization.
    """
    inputs = (current, prior)
    if mode not in ('pct', 'absolute'):
        return _result(rule, inputs, reason='UNSUPPORTED_MODE')
    problem = _rule_problem(rule, 'period_pct' if mode == 'pct' else 'period_absolute')
    if problem:
        return _result(rule, inputs, reason=problem, status='UNAVAILABLE' if rule is None else 'INCOMPATIBLE')
    if not all(_measure(m) for m in inputs):
        return _result(rule, inputs, reason='INVALID_MEASURE')
    if not _bound(rule, (('current', current), ('prior', prior))):
        return _result(rule, inputs, reason='INPUT_BINDING_MISMATCH')
    if not _same_scope(current, prior) or current.domain != prior.domain:
        return _result(rule, inputs, reason='COMPARISON_SCOPE_MISMATCH')
    if prior.period[1] >= current.period[0]:
        return _result(rule, inputs, reason='PERIOD_ORDER_INCOMPATIBLE')
    if mode == 'pct' and current.unit in ('percent', 'fraction'):
        return _result(rule, inputs, reason='RATE_PERCENT_CHANGE_UNSUPPORTED')
    if current.value is None or prior.value is None:
        return _result(rule, inputs, status='UNAVAILABLE', reason='POINT_VALUE_UNAVAILABLE')
    if mode == 'pct' and prior.value <= 0:
        return _result(rule, inputs, status='UNAVAILABLE', reason='NONPOSITIVE_PRIOR')
    if (mode == 'pct' and rule.interpretation_basis == 'underlying_interval'
            and prior.support is not None and prior.support.lower <= 0):
        return _result(rule, inputs, status='UNAVAILABLE', reason='PRIOR_SUPPORT_NONPOSITIVE')
    with localcontext(_CONTEXT):
        a, b = current.value * current.scale, prior.value * prior.scale
        value = Decimal(100) * (a - b) / b if mode == 'pct' else a - b
    label = 'PERCENT_CHANGE' if mode == 'pct' else {
        'percent': 'PERCENTAGE_POINT_CHANGE', 'fraction': 'FRACTIONAL_RATE_CHANGE',
    }.get(current.unit, 'ABSOLUTE_CHANGE')
    qualified = rule.interpretation_basis == 'published_figures' or not all(_point_exact(m) for m in inputs)
    return _result(rule, inputs, status='QUALIFIED' if qualified else 'COMPARABLE', value=value,
                   label=label, reason='PUBLISHED_FIGURES_ONLY' if qualified else None,
                   formula='100 * (current_scaled - prior_scaled) / prior_scaled' if mode == 'pct'
                   else 'current_scaled - prior_scaled')


def _guide_label(value: Decimal, lower, upper, li, ui) -> str:
    if lower is not None:
        if value < lower:
            return 'BELOW_ORIGINAL_FLOOR'
        if value == lower and not li:
            return 'AT_EXCLUDED_BOUNDARY'
    if upper is not None:
        if value > upper:
            return 'ABOVE_ORIGINAL_CEILING'
        if value == upper and not ui:
            return 'AT_EXCLUDED_BOUNDARY'
    if lower is not None and upper is not None:
        return 'WITHIN_ORIGINAL_RANGE'
    return 'MEETS_ORIGINAL_FLOOR' if lower is not None else 'WITHIN_ORIGINAL_CEILING'


def _support_labels(support: Interval, lower, upper, li, ui) -> set[str]:
    """Finite partition of every possible category, including isolated equality.

    Endpoints alone are insufficient: an actual interval may span an entire
    guidance interval. Sample each discontinuity and each nonempty open cell.
    There are at most four cuts and seven samples, independent of magnitudes.
    """
    cuts = sorted({support.lower, support.upper} | {
        b for b in (lower, upper) if b is not None and support.lower <= b <= support.upper})
    samples = [x for x in cuts if _contains(support, x)]
    samples.extend((a + b) / 2 for a, b in zip(cuts, cuts[1:]) if a < b)
    return {_guide_label(x, lower, upper, li, ui) for x in samples}


def compare_guidance(actual: Measure, guide: Guidance, *, rule: ComparisonRule) -> Result:
    """Compare original-company guidance only; do not invent final/consensus history."""
    inputs = (actual, guide)
    problem = _rule_problem(rule, 'guidance')
    if problem:
        return _result(rule, inputs, reason=problem, status='UNAVAILABLE' if rule is None else 'INCOMPATIBLE')
    if not _measure(actual):
        return _result(rule, inputs, reason='INVALID_MEASURE')
    if not _guidance(guide):
        return _result(rule, inputs, reason='INVALID_GUIDANCE')
    if not _bound(rule, (('actual', actual), ('guide', guide))):
        return _result(rule, inputs, reason='INPUT_BINDING_MISMATCH')
    if (not _same_scope(actual, guide, same_period=True)
            or rule.bindings[0].domain != rule.bindings[1].domain):
        return _result(rule, inputs, reason='COMPARISON_SCOPE_MISMATCH')
    if guide.vintage != 'original_company_guidance':
        return _result(rule, inputs, status='QUALIFIED', label='GUIDANCE_VINTAGE_UNQUALIFIED',
                       reason='GUIDANCE_VINTAGE_UNQUALIFIED')
    if guide.bounds_basis != 'stated_threshold':
        return _result(rule, inputs, status='QUALIFIED', label='GUIDANCE_BOUNDS_UNQUALIFIED',
                       reason='GUIDANCE_BOUNDS_UNQUALIFIED')
    printed = rule.interpretation_basis == 'published_figures'
    if not printed and actual.support is None:
        return _result(rule, inputs, status='QUALIFIED', label='SOURCE_PRECISION_UNKNOWN',
                       reason='SOURCE_PRECISION_UNKNOWN')
    if printed and actual.value is None:
        return _result(rule, inputs, status='UNAVAILABLE', reason='POINT_VALUE_UNAVAILABLE')
    with localcontext(_CONTEXT):
        lower = None if guide.lower is None else guide.lower * guide.scale
        upper = None if guide.upper is None else guide.upper * guide.scale
        if printed:
            point = actual.value * actual.scale
            support = Interval(point, point, True, True)
        else:
            s = actual.support
            support = Interval(s.lower * actual.scale, s.upper * actual.scale,
                               s.lower_inclusive, s.upper_inclusive)
        labels = _support_labels(support, lower, upper, guide.lower_inclusive, guide.upper_inclusive)
        if len(labels) != 1:
            return _result(rule, inputs, status='QUALIFIED', label='ROUNDING_INDETERMINATE',
                           reason='SUPPORT_SPANS_VERDICTS', formula='actual_support versus original_guidance_bounds')
        label = next(iter(labels))
        value = None
        formula = 'actual_support versus original_guidance_bounds'
        bound = lower if label == 'BELOW_ORIGINAL_FLOOR' else upper if label == 'ABOVE_ORIGINAL_CEILING' else None
        if bound is not None and bound > 0 and actual.value is not None:
            value = Decimal(100) * (actual.value * actual.scale - bound) / bound
            formula = '100 * (actual_scaled - original_' + ('floor' if label == 'BELOW_ORIGINAL_FLOOR' else 'ceiling') + '_scaled) / original_bound_scaled'
    qualified = printed or (value is not None and not _point_exact(actual))
    return _result(rule, inputs, status='QUALIFIED' if qualified else 'COMPARABLE',
                   label=label, value=value, reason='PUBLISHED_FIGURES_ONLY' if qualified else None, formula=formula)


def _signed_role(value: CashRole | CashComponent) -> bool:
    return (value.orientation in ('signed_flow', 'positive_magnitude')
            and type(value.coefficient) is int and value.coefficient in (-1, 1))


def cash_bridge(*, measures: tuple[Measure, ...], components: tuple[CashComponent, ...], rule: ComparisonRule) -> Result:
    """Evaluate exactly the reviewed component partition, with signed orientation.

    The owner must reject overlapping economic components when admitting a rule.
    This adapter enforces that exact recipe; it does not infer partitions from
    names. One uncertain receipt may cancel algebraically under two explicit
    opposing roles, but cannot count twice as independent economic evidence.
    """
    safe_inputs = measures if type(measures) is tuple else ()
    problem = _rule_problem(rule, 'cash')
    if problem:
        return _result(rule, safe_inputs, reason=problem, status='UNAVAILABLE' if rule is None else 'INCOMPATIBLE')
    if (type(measures) is not tuple or not 1 <= len(measures) <= _MAX_INPUTS
            or type(components) is not tuple or not 1 <= len(components) <= _MAX_INPUTS
            or not 1 <= len(rule.cash_roles) <= _MAX_INPUTS):
        return _result(rule, safe_inputs, reason='CASH_RECIPE_MISMATCH')
    if not all(_measure(m) for m in measures):
        return _result(rule, measures, reason='INVALID_MEASURE')
    if len({m.ref for m in measures}) != len(measures):
        return _result(rule, measures, reason='CASH_RECIPE_MISMATCH')
    if any(type(x) is not CashRole or not _signed_role(x) or not _text(x.component_key)
           or not _text(x.binding_role) for x in rule.cash_roles):
        return _result(rule, measures, reason='CASH_RECIPE_MISMATCH')
    if any(type(x) is not CashComponent or not _signed_role(x) or not _text(x.component_key)
           or not _text(x.measure_ref) for x in components):
        return _result(rule, measures, reason='CASH_RECIPE_MISMATCH')
    roles = {x.component_key: x for x in rule.cash_roles}
    parts = {x.component_key: x for x in components}
    by_role = {x.role: x for x in rule.bindings}
    by_ref = {m.ref: m for m in measures}
    if (len(roles) != len(rule.cash_roles) or len(parts) != len(components)
            or set(roles) != set(parts)
            or {x.binding_role for x in rule.cash_roles} != set(by_role)
            or len(rule.cash_roles) != len(by_role)
            or {x.ref for x in rule.bindings} != set(by_ref)):
        return _result(rule, measures, reason='CASH_RECIPE_MISMATCH')
    bound_inputs = tuple((b.role, by_ref[b.ref]) for b in rule.bindings)
    if not _bound(rule, bound_inputs):
        return _result(rule, measures, reason='INPUT_BINDING_MISMATCH')
    if not all(m.unit == 'currency' and _same_scope(measures[0], m, same_period=True, cash=True) for m in measures):
        return _result(rule, measures, reason='COMPARISON_SCOPE_MISMATCH')
    coefficients: dict[str, list[int]] = {}
    for key, role in roles.items():
        component, binding = parts[key], by_role[role.binding_role]
        if (component.measure_ref != binding.ref or component.orientation != role.orientation
                or component.coefficient != role.coefficient):
            return _result(rule, measures, reason='CASH_RECIPE_MISMATCH')
        m = by_ref[component.measure_ref]
        if component.orientation == 'positive_magnitude' and (
                (m.value is not None and m.value < 0) or (m.support is not None and m.support.lower < 0)):
            return _result(rule, measures, reason='CASH_SIGN_MISMATCH')
        coefficients.setdefault(m.ref, []).append(component.coefficient)
    if any(len(cs) > 1 and sum(cs) != 0 for cs in coefficients.values()):
        return _result(rule, measures, reason='REPEATED_ECONOMIC_RECEIPT')
    active = [(by_ref[ref], sum(cs)) for ref, cs in coefficients.items() if sum(cs)]
    if any(m.value is None for m, _ in active):
        return _result(rule, measures, status='UNAVAILABLE', reason='POINT_VALUE_UNAVAILABLE')
    with localcontext(_CONTEXT):
        value = sum((m.value * m.scale * coefficient for m, coefficient in active), Decimal(0))
    qualified = bool(active) and (rule.interpretation_basis == 'published_figures'
                                 or not all(_point_exact(m) for m, _ in active))
    return _result(rule, measures, status='QUALIFIED' if qualified else 'COMPARABLE', value=value,
                   label='CASH_BRIDGE', reason='PUBLISHED_FIGURES_ONLY' if qualified else None,
                   formula='sum(reviewed_signed_components)')
