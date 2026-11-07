"""Original, synthetic mathematical conformance oracle for a research appendix.

This is NOT a native Factor Atlas pilot, a market-data reader, a portfolio engine,
or an owner-admission implementation. It imports no Mastermind code, reads no
owner store, contacts no network and creates no identity, membership or state.
The PIT predicate checks necessary conditions on synthetic inputs; it cannot
verify a receipt's authenticity, entitlement or historical completeness.
Statistical formulas here are mathematical checks; publishability thresholds
are separately proposed in contracts/metrics_policy.v0.json.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any

TOLERANCE = 1e-12


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('FINITE_NUMBER_REQUIRED')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('FINITE_NUMBER_REQUIRED')
    return number


def _weights(values: Sequence[float]) -> tuple[float, ...]:
    result = tuple(_number(x) for x in values)
    if not result or any(x < 0 for x in result):
        raise ValueError('NONEMPTY_LONG_ONLY_WEIGHTS_REQUIRED')
    if abs(math.fsum(result) - 1) > TOLERANCE:
        raise ValueError('WEIGHTS_MUST_SUM_TO_ONE')
    return result


def _returns(values: Sequence[float | None]) -> tuple[float | None, ...]:
    result = tuple(None if x is None else _number(x) for x in values)
    if any(x is not None and x < -1 for x in result):
        raise ValueError('RETURN_BELOW_MINUS_ONE')
    return result


def _paired(weights: Sequence[float], returns: Sequence[float | None]):
    w, r = _weights(weights), _returns(returns)
    if len(w) != len(r):
        raise ValueError('LENGTH_MISMATCH')
    return w, r


def normalize_positive(values: Sequence[float]) -> tuple[float, ...]:
    """Normalize nonnegative *weighting inputs*, not erroneous supplied weights."""
    v = tuple(_number(x) for x in values)
    if not v or any(x < 0 for x in v) or math.fsum(v) <= 0:
        raise ValueError('POSITIVE_TOTAL_REQUIRED')
    total = math.fsum(v)
    return tuple(x / total for x in v)


def capped_weights(values: Sequence[float], cap: float) -> tuple[float, ...]:
    """Proportional redistribution with fixed cap; no infeasible EW fallback."""
    v = tuple(_number(x) for x in values)
    c = _number(cap)
    if not v or any(x <= 0 for x in v) or not 0 < c <= 1:
        raise ValueError('POSITIVE_INPUTS_AND_VALID_CAP_REQUIRED')
    if len(v) * c < 1 - TOLERANCE:
        raise ValueError('INFEASIBLE_WEIGHT_CONSTRAINT')
    result = [0.0] * len(v)
    active = list(range(len(v)))
    remaining = 1.0
    while active:
        total = math.fsum(v[i] for i in active)
        proposed = {i: remaining * v[i] / total for i in active}
        over = [i for i in active if proposed[i] > c + TOLERANCE]
        if not over:
            for i in active:
                result[i] = proposed[i]
            break
        for i in over:
            result[i] = c
        active = [i for i in active if i not in over]
        remaining = 1.0 - math.fsum(result)
    if abs(math.fsum(result) - 1) > TOLERANCE or max(result) > c + TOLERANCE:
        raise ValueError('WEIGHT_CONSTRAINT_NOT_SATISFIED')
    return tuple(result)


def weight_coverage(weights: Sequence[float], returns: Sequence[float | None]) -> float:
    w, r = _paired(weights, returns)
    return math.fsum(x for x, y in zip(w, r) if y is not None)


def strict_return(weights: Sequence[float], returns: Sequence[float | None]) -> float | None:
    w, r = _paired(weights, returns)
    # Do not turn a missing positive position into zero through a tolerance.
    if any(x > 0 and y is None for x, y in zip(w, r)):
        return None
    return math.fsum(x * y for x, y in zip(w, r) if y is not None)


def claims_return(start_price: float, end_claim_values: Sequence[float | None],
                  cash: float | None = 0.0) -> float | None:
    """End values already supplied in the same currency per beginning share."""
    start = _number(start_price)
    if start <= 0:
        raise ValueError('POSITIVE_START_PRICE_REQUIRED')
    if cash is None or any(x is None for x in end_claim_values):
        return None
    values = tuple(_number(x) for x in end_claim_values)
    if any(x < 0 for x in values):
        raise ValueError('NEGATIVE_CLAIM_VALUE')
    end = math.fsum(values) + _number(cash)
    if end < 0:
        raise ValueError('NEGATIVE_END_VALUE')
    return end / start - 1


def drift_weights(weights: Sequence[float], returns: Sequence[float | None]) -> tuple[float, ...] | None:
    w, r = _paired(weights, returns)
    result = strict_return(w, r)
    if result is None:
        return None
    if result <= -1:
        raise ValueError('INSOLVENT_PORTFOLIO')
    return tuple(0.0 if x == 0 else x * (1 + y) / (1 + result)
                 for x, y in zip(w, r))


def link_returns(returns: Sequence[float | None], base: float = 100.0) -> list[float | None]:
    r = _returns(returns)
    level = _number(base)
    if level <= 0:
        raise ValueError('POSITIVE_BASE_REQUIRED')
    output: list[float | None] = [level]
    broken = False
    for value in r:
        if broken or value is None:
            broken = True
            output.append(None)
            continue
        level *= 1 + value
        output.append(level)
        if level == 0:
            broken = True
    return output


def horizon_return(returns: Sequence[float | None], sessions: int) -> float | None:
    if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions <= 0:
        raise ValueError('POSITIVE_SESSION_COUNT_REQUIRED')
    if len(returns) < sessions:
        return None
    r = _returns(returns[-sessions:])
    if any(x is None for x in r):
        return None
    return math.prod(1 + x for x in r) - 1


def relative_return(a: float, b: float) -> float:
    ra, rb = _returns([a, b])
    if ra is None or rb is None or rb == -1:
        raise ValueError('VALID_NONZERO_BENCHMARK_WEALTH_REQUIRED')
    return (1 + ra) / (1 + rb) - 1


def concentration(weights: Sequence[float]) -> dict[str, float]:
    w = _weights(weights)
    hhi = math.fsum(x*x for x in w)
    ordered = sorted(w, reverse=True)
    return {'hhi': hhi, 'effective_n': 1/hhi, 'top1': ordered[0],
            'top5': math.fsum(ordered[:5]), 'top10': math.fsum(ordered[:10])}


def advance_breadth(returns: Sequence[float | None], weights: Sequence[float]) -> dict[str, Any]:
    w, r = _paired(weights, returns)
    valid = [x for x in r if x is not None]
    n, observed = len(r), len(valid)
    count_fraction = observed/n
    weight_fraction = weight_coverage(w, r)
    qualifies = (n >= 3 and count_fraction >= .8 - TOLERANCE
                 and weight_fraction >= .8 - TOLERANCE)
    advancing, unchanged = sum(x > 0 for x in valid), sum(x == 0 for x in valid)
    return {'value': advancing/observed if qualifies else None,
            'status': ('READY' if observed == n else 'PARTIAL') if qualifies else 'UNAVAILABLE',
            'eligible': n, 'observed': observed, 'advancing': advancing, 'unchanged': unchanged,
            'declining': sum(x < 0 for x in valid), 'missing': n-observed,
            'count_coverage': count_fraction, 'weight_coverage': weight_fraction,
            'small_n': n < 10}


def linked_contributions(rows: Sequence[Mapping[str, float]]) -> dict[str, float]:
    if not rows:
        raise ValueError('NONEMPTY_ATTRIBUTION_REQUIRED')
    normalized = [{k: _number(v) for k, v in sorted(row.items())} for row in rows]
    totals = [math.fsum(row.values()) for row in normalized]
    if any(x < -1 for x in totals):
        raise ValueError('RETURN_BELOW_MINUS_ONE')
    keys = sorted({k for row in normalized for k in row})
    components: dict[str, list[float]] = {k: [] for k in keys}
    suffix = 1.0
    for row, total in zip(reversed(normalized), reversed(totals)):
        for key in keys:
            components[key].append(row.get(key, 0.0) * suffix)
        suffix *= 1 + total
    return {key: math.fsum(components[key]) for key in keys}


def downside_deviation(returns: Sequence[float], *, annualization: float = 252) -> float:
    r = tuple(_number(x) for x in returns)
    scale = _number(annualization)
    if not r or scale <= 0:
        raise ValueError('NONEMPTY_RETURNS_AND_POSITIVE_ANNUALIZATION_REQUIRED')
    return math.sqrt(scale * math.fsum(min(x, 0)**2 for x in r)/len(r))


def sample_volatility(returns: Sequence[float], *, annualization: float = 252) -> float:
    r = tuple(_number(x) for x in returns)
    scale = _number(annualization)
    if len(r) < 2 or scale <= 0:
        raise ValueError('TWO_RETURNS_AND_POSITIVE_ANNUALIZATION_REQUIRED')
    mean = math.fsum(r)/len(r)
    return math.sqrt(scale * math.fsum((x-mean)**2 for x in r)/(len(r)-1))


def prior_z(value: float, prior: Sequence[float]) -> float | None:
    current = _number(value)
    r = tuple(_number(x) for x in prior)
    if len(r) < 2:
        return None
    sd = sample_volatility(r, annualization=1)
    if sd == 0:
        return None
    return (current-math.fsum(r)/len(r))/sd


def tail_loss(returns: Sequence[float], p: float) -> dict[str, float]:
    r = sorted(_number(x) for x in returns)
    level = _number(p)
    if not r or not 0 < level < 1:
        raise ValueError('NONEMPTY_RETURNS_AND_VALID_TAIL_REQUIRED')
    location = (len(r)-1)*level
    low, high = math.floor(location), math.ceil(location)
    quantile = r[low] + (location-low)*(r[high]-r[low])
    mass = len(r)*level
    full = math.floor(mass)
    fraction = mass-full
    lower_sum = math.fsum(r[:full]) + (fraction*r[full] if fraction else 0.0)
    return {'var': -quantile, 'es': -lower_sum/mass, 'tail_mass': mass}


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith('Z') or 'T' not in value:
        raise ValueError('PRECISE_UTC_REQUIRED')
    parsed = datetime.fromisoformat(value[:-1]+'+00:00')
    if parsed.tzinfo != timezone.utc:
        raise ValueError('UTC_REQUIRED')
    return parsed


def pit_eligible(receipt: Mapping[str, Any], *, basket_id: str,
                 selection_cutoff: str, holding_at: str) -> bool:
    """Necessary synthetic AS_KNOWN conditions; NEVER authenticates a receipt."""
    try:
        if receipt.get('pit') is not True or receipt.get('basket_id') != basket_id:
            return False
        if receipt.get('collection_state') != 'COMPLETE':
            return False
        required = receipt.get('public_availability_required')
        if not isinstance(required, bool):
            return False
        decision, holding = _utc(selection_cutoff), _utc(holding_at)
        start, known, observed = (_utc(receipt[k]) for k in ['effective_from', 'known_at', 'observed_at'])
        end = _utc(receipt['effective_to']) if receipt.get('effective_to') is not None else None
        if not decision < holding or observed > known or known > decision or holding < start:
            return False
        if end is not None and (end <= start or holding >= end):
            return False
        if required and _utc(receipt.get('source_published_at')) > decision:
            return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
