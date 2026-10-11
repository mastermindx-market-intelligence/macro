"""Factor Atlas: pure, display-only options aggregation over owner-qualified inputs.

Options Hub owns observations/publication, MSC owns dealer signs, and the factor
owner supplies definitions. This leaf performs no I/O, pricing, covariance fitting,
portfolio persistence, scheduling, entitlement decisions, or Prophet promotion.
Freshness deadlines are supplied by the source owner, never a built-in wall TTL.
DTOs are a trusted in-process interface, not a public authorization validator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import fsum, isfinite, sqrt
from numbers import Real
import re
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class Definition:
    factor_ref: str
    source_ref: str
    source_sha256: str
    known_at: datetime


@dataclass(frozen=True)
class Member:
    root: str
    weight: float
    iv: float | None
    observed_at: datetime | None
    known_at: datetime | None
    qualified: bool
    premium: float | None = None
    source_ref: str = ""
    source_sha256: str = ""
    valid_until: datetime | None = None
    method: str | None = None
    tenor_calendar_days: float = 30
    year_basis: str = "ACT/365F"


@dataclass(frozen=True)
class Correlation:
    roots: tuple[str, ...]
    values: object
    source_ref: str
    source_sha256: str
    observed_at: datetime | None
    known_at: datetime | None
    valid_until: datetime | None
    method: str


@dataclass(frozen=True)
class Policy:
    min_weight: float = .8
    min_count_fraction: float = .8
    max_missing_name_weight: float = .1
    min_names: int = 3
    premium_dominance: float = .7
    version: str = "factor_options_coverage/v1"


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_IV_METHODS = {"iv30_total_variance_act365f", "iv30_exact_act365f"}


def _number(value: object, label: str, minimum: float | None = None) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{label}: numeric scalar required; coercion refused")
    out = float(value)
    if not isfinite(out) or (minimum is not None and out < minimum):
        raise ValueError(f"{label}: nonfinite or below minimum")
    return out


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value.strip() == value


def _digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _source_reasons(source, asof: datetime) -> list[str]:
    reasons = []
    if not _text(source.source_ref): reasons.append("SOURCE_REF_MISSING")
    if not _digest(source.source_sha256): reasons.append("SOURCE_DIGEST_MISSING")
    if not all(_aware(v) for v in (source.observed_at, source.known_at, source.valid_until)):
        reasons.append("SOURCE_CLOCKS_MISSING")
    else:
        if source.observed_at > source.known_at or source.known_at > asof:
            reasons.append("NOT_KNOWN_ASOF")
        if source.valid_until <= source.observed_at:
            reasons.append("SOURCE_CLOCK_ORDER_INVALID")
        if asof >= source.valid_until:
            reasons.append("OBSERVATION_STALE")
    return reasons


def standardized_iv(points: Sequence[tuple[float, float]], target_days: float = 30) -> float | None:
    """Owner-qualified annual-decimal ATM nodes; total variance, no extrapolation.

    This conservative monotonic-total-variance check is not a surface arbitrage
    certificate. Quote convention, exercise model and marks remain source duties.
    """
    target = _number(target_days, "target_days")
    if target <= 0: raise ValueError("target must be positive")
    clean = []
    for days, iv in points:
        d, s = _number(days, "tenor_days"), _number(iv, "iv", 0)
        if d <= 0: raise ValueError("tenor must be positive")
        clean.append((d, s))
    clean.sort()
    if len({d for d, _ in clean}) != len(clean): raise ValueError("duplicate tenors")
    for (d1, s1), (d2, s2) in zip(clean, clean[1:]):
        if s2*s2*d2 < s1*s1*d1 - 1e-12:
            raise ValueError("declining total variance")
    for d, s in clean:
        if d == target: return s
    for (d1, s1), (d2, s2) in zip(clean, clean[1:]):
        if d1 < target < d2:
            a = (d2-target)/(d2-d1)
            result = sqrt((a*s1*s1*d1+(1-a)*s2*s2*d2)/target)
            if not isfinite(result): raise ValueError("nonfinite interpolated variance")
            return result
    return None


def _correlation(values: object, n: int) -> np.ndarray:
    raw = np.asarray(values, dtype=object)
    if raw.shape != (n, n): raise ValueError("correlation dimensions mismatch")
    matrix = np.array([_number(v, "correlation") for v in raw.flat]).reshape(n, n)
    if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
        raise ValueError("correlation must be symmetric")
    if not np.allclose(np.diag(matrix), 1, rtol=0, atol=1e-12) or np.any(np.abs(matrix)>1+1e-12):
        raise ValueError("correlation requires unit diagonal and bounded elements")
    eigenvalues = np.linalg.eigvalsh(matrix)
    if eigenvalues.min() < -1e-12*max(1, float(np.max(np.abs(eigenvalues)))):
        raise ValueError("correlation is not positive semidefinite")
    return matrix


def _receipt(source) -> dict:
    return {"source_ref": source.source_ref if _text(source.source_ref) else None,
            "sha256": source.source_sha256 if _digest(source.source_sha256) else None,
            "observed_at": source.observed_at.isoformat() if _aware(source.observed_at) else None,
            "known_at": source.known_at.isoformat() if _aware(source.known_at) else None,
            "valid_until": source.valid_until.isoformat() if _aware(source.valid_until) else None}


def aggregate(members: Sequence[Member], *, definition: Definition, asof: datetime,
              correlation: Correlation | None = None, policy: Policy = Policy()) -> dict:
    """Covered-constituent statistics and a separate full-basket hybrid risk model.

    Positive-weight membership must be complete for full-risk output. The model
    uses annual-decimal IV with supplied historical/scenario correlation for
    30 calendar days; it is neither a traded basket IV nor a calibrated probability.
    """
    if not _aware(asof): raise ValueError("asof must be timezone-aware")
    if not isinstance(definition, Definition) or not _text(definition.factor_ref) or not _text(definition.source_ref) or not _digest(definition.source_sha256):
        raise ValueError("qualified definition reference and digest required")
    if not _aware(definition.known_at) or definition.known_at > asof:
        raise ValueError("definition not known at requested time")
    if not isinstance(policy, Policy): raise ValueError("typed policy required")
    for value in (policy.min_weight, policy.min_count_fraction, policy.max_missing_name_weight, policy.premium_dominance):
        if not 0 <= _number(value, "policy fraction") <= 1: raise ValueError("invalid policy fraction")
    if type(policy.min_names) is not int or policy.min_names < 1 or not _text(policy.version):
        raise ValueError("invalid policy")
    if not members or not all(isinstance(r, Member) for r in members):
        raise ValueError("nonempty typed membership required")
    roots = [r.root for r in members]
    if any(not _text(r) for r in roots) or len(set(roots)) != len(roots):
        raise ValueError("invalid or duplicate roots")
    for row in members:
        _number(row.weight, "weight", 0)
        if row.iv is not None: _number(row.iv, "iv", 0)
        if row.premium is not None: _number(row.premium, "premium", 0)
        if type(row.qualified) is not bool: raise ValueError("qualification must be boolean")
    if abs(fsum(r.weight for r in members)-1) > 1e-12:
        raise ValueError("house weights must sum to one without renormalization")
    active = sorted((r for r in members if r.weight>0), key=lambda r: r.root)
    eligible, excluded = [], []
    for row in active:
        reasons = _source_reasons(row, asof)
        if row.iv is None: reasons.append("IV_MISSING")
        if not row.qualified: reasons.append("IV_QUALITY_UNQUALIFIED")
        if not isinstance(row.method, str) or row.method not in _IV_METHODS: reasons.append("IV_METHOD_UNQUALIFIED")
        if _number(row.tenor_calendar_days, "IV tenor") != 30: reasons.append("IV_TENOR_UNQUALIFIED")
        if row.year_basis != "ACT/365F": reasons.append("IV_YEAR_BASIS_UNQUALIFIED")
        if reasons: excluded.append({"root":row.root,"weight":float(row.weight),"reasons":reasons})
        else: eligible.append(row)
    covered_weight = fsum(r.weight for r in eligible)
    n, total = len(eligible), len(active)
    normalized = [r.weight/covered_weight for r in eligible] if n else []
    mean = fsum(a*r.iv for a,r in zip(normalized,eligible)) if n else None
    rms = sqrt(fsum(a*r.iv*r.iv for a,r in zip(normalized,eligible))) if n else None
    median, accumulated = None, 0
    for row in sorted(eligible, key=lambda r:(r.iv,r.root)):
        accumulated += row.weight/covered_weight
        if accumulated >= .5-1e-12:
            median = float(row.iv); break
    concentration = fsum(a*a for a in normalized) if n else None
    missing_max = max((r["weight"] for r in excluded), default=0)
    headline_ok = (n>=policy.min_names and covered_weight+1e-12>=policy.min_weight
                   and n/total+1e-12>=policy.min_count_fraction
                   and missing_max<=policy.max_missing_name_weight+1e-12)
    # Activity has its own population, but never escapes source-time admission.
    # IV-quality refusal alone does not erase a timely reported activity proxy.
    eligible_roots = {r.root for r in eligible}
    premiums = [r for r in active if r.premium is not None and not _source_reasons(r, asof)]
    premium_total = fsum(r.premium for r in premiums)
    top_share = max((r.premium/premium_total for r in premiums),default=0) if premium_total>0 else None
    warnings = ["REPORTED_PREMIUM_SINGLE_NAME_DOMINATED"] if top_share is not None and top_share>policy.premium_dominance else []
    reasons = ["INCOMPLETE_IV_COVERAGE"] if n!=total else []
    model = None
    if correlation is None:
        reasons.append("CORRELATION_UNAVAILABLE")
    else:
        if not isinstance(correlation, Correlation): raise ValueError("typed correlation required")
        cr = correlation.roots
        if not all(_text(r) for r in cr) or len(cr)!=total or len(set(cr))!=total or set(cr)!={r.root for r in active}:
            raise ValueError("correlation identity mismatch")
        matrix = _correlation(correlation.values, total)
        indexes = [cr.index(r.root) for r in active]
        matrix = matrix[np.ix_(indexes,indexes)]
        model_reasons = _source_reasons(correlation, asof)
        if correlation.method not in ("historical_correlation", "scenario_assumption"):
            model_reasons.append("CORRELATION_METHOD_UNQUALIFIED")
        reasons.extend("CORRELATION_"+r if not r.startswith("CORRELATION_") else r for r in model_reasons)
        if n==total and not model_reasons:
            weighted_iv = np.array([r.weight*r.iv for r in active])
            variance = float(weighted_iv @ matrix @ weighted_iv)*30/365
            if not isfinite(variance): raise ValueError("nonfinite modeled variance")
            model = sqrt(max(variance,0))
    for value in (mean,rms,median,premium_total,top_share,model):
        if value is not None and not isfinite(value): raise ValueError("nonfinite aggregation")
    return {
        "schema":"options_hub.factor_options/v1", "policy":policy.version,
        "policy_parameters":{"min_weight":float(policy.min_weight),
                             "min_count_fraction":float(policy.min_count_fraction),
                             "min_names":policy.min_names,
                             "max_missing_name_weight":float(policy.max_missing_name_weight),
                             "premium_dominance":float(policy.premium_dominance),
                             "full_risk_requires_complete_coverage":True},
        "factor_ref":definition.factor_ref, "asof":asof.isoformat(),
        "horizon":{"days":30,"basis":"ACT/365F","unit":"calendar_day"},
        "coverage":{"count":n,"total_count":total,"count_fraction":n/total,
                    "weight":covered_weight,"missing_weight":max(0,1-covered_weight),
                    "largest_missing_weight":missing_max,"excluded":excluded},
        "covered":{"mean_iv":mean,"rms_iv":rms,"weighted_median_iv":median,
                   "effective_names":1/concentration if concentration else None,
                   "normalization":"eligible subset weights sum to one; not whole-basket risk"},
        "headline_mean_iv":mean if headline_ok else None,
        "headline_label":"covered-constituent annual IV statistic",
        "hybrid_expected_move":model,
        "hybrid_label":"modeled: constituent IV with supplied correlation",
        "premium":{"complete":len(premiums)==total,"root_count":len(premiums),
                   "total_reported":premium_total if premiums else None,"top_share_reported":top_share,
                   "denominator":"reported constituent activity proxy; not whole-market coverage"},
        "definition":{"source_ref":definition.source_ref,"sha256":definition.source_sha256,"known_at":definition.known_at.isoformat()},
        "inputs":[{"root":r.root,"weight":float(r.weight),
                   "iv":float(r.iv) if r.root in eligible_roots else None,
                   "qualified":r.root in eligible_roots,
                   "method":r.method if isinstance(r.method,str) else None,
                   "tenor_calendar_days":float(r.tenor_calendar_days),
                   "year_basis":r.year_basis if isinstance(r.year_basis,str) else None,
                   **_receipt(r)} for r in active],
        "correlation":None if correlation is None else {
            "method":correlation.method if isinstance(correlation.method,str) else None,
            "roots":list(correlation.roots),**_receipt(correlation)},
        "warnings":warnings,"reasons":reasons,
        "authority":{"display_only":True,"publication":False,"prophet":False,"position_sizing":False},
    }
