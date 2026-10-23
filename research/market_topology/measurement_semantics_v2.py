"""Research reference semantics, not a production reader, classifier or trade gate.
Inputs are supplied by existing owners. This module owns no persistence or identity.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import fsum, isclose, isfinite
from typing import Mapping, Sequence

Flag = bool | None


def _validate_flags(flags: Mapping[str, Flag]) -> None:
    for key, value in flags.items():
        if not isinstance(key, str) or not key:
            raise ValueError('A stable, nonempty supplied identity is required')
        if value is not None and type(value) is not bool:
            raise ValueError('A flag must be true, false or unknown; never a truthy number')


def participation(flags: Mapping[str, Flag], weights: Mapping[str, float] | None = None) -> dict:
    """Sharp missingness bounds, NOT sampling confidence intervals.
    Weights must be known for the full supplied census; unweighted does not imply
    issuer deduplication, economic comparability or predicate validation.
    """
    _validate_flags(flags)
    n = len(flags)
    if not n:
        if weights:
            raise ValueError('Weights cannot refer to absent identities')
        return {'n': 0, 'known': 0, 'positive': 0, 'unknown': 0,
                'lower': None, 'upper': None, 'known_only': None,
                'reason': 'EMPTY_UNIVERSE'}
    w = {k: 1.0 for k in flags} if weights is None else dict(weights)
    if set(w) != set(flags):
        raise ValueError('Complete, exactly matching weight identities required')
    if any(not isfinite(v) or v < 0 for v in w.values()) or max(w.values()) <= 0:
        raise ValueError('Finite nonnegative weights with positive total required')
    scale = max(w.values())
    w = {k: v / scale for k, v in w.items()}
    positive = fsum(w[k] for k, f in flags.items() if f is True)
    unknown = fsum(w[k] for k, f in flags.items() if f is None)
    total = fsum(w.values())
    known_weight = fsum(w[k] for k, f in flags.items() if f is not None)
    return {'n': n, 'known': sum(f is not None for f in flags.values()),
            'positive': sum(f is True for f in flags.values()),
            'unknown': sum(f is None for f in flags.values()),
            'lower': positive / total, 'upper': (positive + unknown) / total,
            'known_only': positive / known_weight if known_weight > 0 else None,
            'unknown_weight_share': unknown / total,
            'reason': None}


def state_count_bridge(before: Mapping[str, Flag], after: Mapping[str, Flag]) -> dict:
    """Decompose OBSERVED positive counts, never impute an unknown true state."""
    _validate_flags(before); _validate_flags(after)
    old, new = set(before), set(after)
    common, entries, exits = old & new, new - old, old - new
    economic = coverage = 0
    for k in common:
        a, b = before[k], after[k]
        change = int(b is True) - int(a is True)
        if a is not None and b is not None:
            economic += change
        else:
            coverage += change
    membership = sum(after[k] is True for k in entries) - sum(before[k] is True for k in exits)
    observed = sum(x is True for x in after.values()) - sum(x is True for x in before.values())
    residual = observed - economic - coverage - membership
    assert residual == 0
    return {'observed_positive_count_change': observed,
            'common_known_state_change': economic,
            'common_coverage_change': coverage,
            'membership_positive_count_change': membership,
            'n_entering': len(entries), 'n_exiting': len(exits), 'residual': residual}


def common_weighted_bridge(before: Mapping[str, bool], after: Mapping[str, bool],
                           old_weights: Mapping[str, float], new_weights: Mapping[str, float]) -> dict:
    """Exact symmetric state/weight attribution on a common fully known population.
    Entry/exit effects are separate. Inputs must be full normalized weights here.
    This is arithmetic attribution, not a causal or investment-return claim.
    """
    _validate_flags(before); _validate_flags(after)
    ids = set(before)
    if not ids or any(set(x) != ids for x in [after, old_weights, new_weights]):
        raise ValueError('The same nonempty known population is required')
    if any(v is None for x in [before, after] for v in x.values()):
        raise ValueError('Unknown states cannot enter a point decomposition')
    for w in [old_weights, new_weights]:
        if any(not isfinite(v) or v < 0 for v in w.values()) or not isclose(fsum(w.values()), 1, rel_tol=0, abs_tol=1e-12):
            raise ValueError('Finite nonnegative normalized weights required')
    state = sum((old_weights[k]+new_weights[k])/2 * (int(after[k])-int(before[k])) for k in ids)
    reweight = sum((int(before[k])+int(after[k]))/2 * (new_weights[k]-old_weights[k]) for k in ids)
    observed = sum(new_weights[k]*after[k]-old_weights[k]*before[k] for k in ids)
    return {'observed_share_change': observed, 'state_component': state,
            'weight_component': reweight, 'residual': observed-state-reweight}


def cohort_overlap(a: set[str], b: set[str], universe: set[str]) -> dict:
    """Uniform fixed-size independent-set reference, not an empirical market null.
    Does NOT correct overlapping return windows or correlated securities.
    """
    if not universe or not a <= universe or not b <= universe:
        raise ValueError('One declared, nonempty common universe is required')
    n, ka, kb, observed = len(universe), len(a), len(b), len(a & b)
    expected = ka * kb / n
    denom = min(ka, kb) - expected
    return {'intersection': observed, 'independent_set_expected': expected,
            'centered_overlap': (observed-expected)/denom if denom > 0 else None,
            'raw_retention': observed/ka if ka else None,
            'not_corrected_for': ['rolling_window_overlap', 'cross_security_dependence']}


def _aware(t: datetime) -> bool:
    return t.tzinfo is not None and t.utcoffset() is not None


@dataclass(frozen=True)
class Observation:
    record_id: str
    effective_at: datetime
    source_available_at: datetime
    system_ready_at: datetime
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id:
            raise ValueError('An observed source record identity is required')
        if not all(_aware(t) for t in [self.effective_at,self.source_available_at,self.system_ready_at]):
            raise ValueError('Timezone-aware clocks required')
        if self.system_ready_at < self.source_available_at or not isfinite(self.value):
            raise ValueError('Invalid readiness clock or value')


def latest_available(rows: Sequence[Observation], decision_at: datetime, *, mode: str) -> Observation | None:
    """Caller supplies versions of ONE series/observation family, not merged domains."""
    if not _aware(decision_at) or mode not in {'source_asof', 'served_replay'}:
        raise ValueError('Explicit aware decision clock and replay mode required')
    ready = [r for r in rows if r.effective_at <= decision_at and r.source_available_at <= decision_at
             and (mode != 'served_replay' or r.system_ready_at <= decision_at)]
    if not ready:
        return None
    source_key = lambda r: (r.effective_at, r.source_available_at)
    top_key = max(source_key(r) for r in ready)
    tied = [r for r in ready if source_key(r) == top_key]
    if len({r.value for r in tied}) > 1:
        raise ValueError('Conflicting equal-source-clock values require owner reconciliation')
    # Ingestion order cannot resolve an economic conflict. Identical-value copies
    # have deterministic selection, without claiming they are different releases.
    return max(tied, key=lambda r: (r.system_ready_at, r.record_id))


def earnings_multiple_bridge(eps0: float, eps1: float, pe0: float, pe1: float) -> dict:
    """Positive EPS/multiple identity only; not a causal valuation model."""
    if not all(isfinite(v) and v > 0 for v in [eps0,eps1,pe0,pe1]):
        raise ValueError('This identity requires strictly positive comparable EPS and P/E')
    growth, rerating = eps1/eps0, pe1/pe0
    return {'eps_growth': growth-1, 'multiple_change': rerating-1,
            'price_change': growth*rerating-1,
            'causal_explanation': None}
