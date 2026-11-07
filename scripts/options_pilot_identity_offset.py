"""Offline identity-link B1-RI arithmetic from PILOT_STUDY_SPEC_V1 Appendix A.

Consumes prepared, eligible eight-column covariates and causal B0 offsets. This
uses the frozen order (score_center, stage_live, stage_setting_up, stage_ran,
stage_basing, stage_unknown, score_missing, publication_age_days).
This
module checks numerical inputs and supplied clock ordering, not historical receipt
authenticity, population eligibility, date balancing or cross-fit provenance.
It does not read data, construct covariates, activate an empirical trial or change
the production ranker. P3/P5's positive-link adapter is a separate algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from typing import Sequence

import numpy as np


PILOTS = frozenset({"P1", "P2", "P4", "P6"})
RIDGE = 0.01
RESIDUAL_TOLERANCE = 1e-10


class OffsetRefusal(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class IdentityOffsetFit:
    pilot: str
    coefficients: tuple[float, ...]
    fit_cutoff: datetime
    training_rows: int
    constant_columns: tuple[int, ...]
    relative_residual: float


def _clock(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise OffsetRefusal("CLOCK_UNQUALIFIED")
    return value.astimezone(timezone.utc)


def _number(value: Real) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise OffsetRefusal("NUMERIC_DOMAIN")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise OffsetRefusal("NUMERIC_DOMAIN") from None
    if not np.isfinite(result):
        raise OffsetRefusal("NUMERIC_DOMAIN")
    return result


def _vector(values: Sequence[Real], length: int) -> np.ndarray:
    try:
        if len(values) != length:
            raise OffsetRefusal("SHAPE_MISMATCH")
        return np.array([_number(x) for x in values], dtype=np.float64)
    except TypeError:
        raise OffsetRefusal("SHAPE_MISMATCH") from None


def _pilot(pilot: str) -> None:
    if not isinstance(pilot, str) or pilot not in PILOTS:
        raise OffsetRefusal("PILOT_UNSUPPORTED")


def fit_identity_offset(
    *,
    pilot: str,
    covariates: Sequence[Sequence[Real]],
    targets: Sequence[Real],
    baselines: Sequence[Real],
    weights: Sequence[Real],
    target_matured_at: Sequence[datetime],
    fit_cutoff: datetime,
) -> IdentityOffsetFit:
    """Fixed .01 ridge, no intercept; caller supplies date-balanced row weights.

    All supplied rows are retained. Invalid rows refuse the fit, never disappear.
    Weights are normalized to sum one before the fixed ridge is added. Numerical
    solvability does not establish sample sufficiency or empirical admissibility.
    """
    _pilot(pilot)
    cutoff = _clock(fit_cutoff)
    try:
        n = len(covariates)
        if n == 0 or len(target_matured_at) != n:
            raise OffsetRefusal("SHAPE_MISMATCH")
        c = np.stack([_vector(row, 8) for row in covariates])
    except TypeError:
        raise OffsetRefusal("SHAPE_MISMATCH") from None
    for matured in target_matured_at:
        if _clock(matured) >= cutoff:
            raise OffsetRefusal("TARGET_NOT_MATURE")
    y, b0, w = (_vector(v, n) for v in (targets, baselines, weights))
    if np.any(w <= 0):
        raise OffsetRefusal("WEIGHT_DOMAIN")
    if pilot == "P1" and (np.any(y < 0) or np.any(b0 < 0)):
        raise OffsetRefusal("RANGE_DOMAIN")
    try:
        with np.errstate(all="raise"):
            w = w / w.sum()
            if np.any(w <= 0):
                raise OffsetRefusal("NUMERIC_FAILURE")
            a = c.T @ (w[:, None] * c) + RIDGE * np.eye(8)
            rhs = c.T @ (w * (y - b0))
            if not np.isfinite(a).all() or not np.isfinite(rhs).all():
                raise OffsetRefusal("NUMERIC_FAILURE")
            factor = np.linalg.cholesky(a)
            gamma = np.linalg.solve(factor.T, np.linalg.solve(factor, rhs))
            # Relative residual in the infinity norm. With exactly zero rhs,
            # the unique ridge solution must have an exactly zero residual.
            error = np.linalg.norm(a @ gamma - rhs, ord=np.inf)
            scale = np.linalg.norm(rhs, ord=np.inf)
            residual = float(error / scale) if scale else float(error)
            if (not np.isfinite(gamma).all() or not np.isfinite(residual)
                    or residual > RESIDUAL_TOLERANCE):
                raise OffsetRefusal("SOLVE_RESIDUAL")
    except (FloatingPointError, np.linalg.LinAlgError):
        raise OffsetRefusal("NUMERIC_FAILURE") from None
    constants = tuple(int(i) for i in np.flatnonzero(np.all(c == c[0], axis=0)))
    return IdentityOffsetFit(pilot, tuple(float(x) for x in gamma), cutoff,
                             n, constants, residual)


def predict_identity_offset(
    fit: IdentityOffsetFit,
    *,
    covariates: Sequence[Real],
    baseline: Real,
    decision_at: datetime,
    feature_available_at: datetime,
) -> float:
    """Frozen B0 + C gamma; only P1 projects the range onto [0, infinity)."""
    if not isinstance(fit, IdentityOffsetFit):
        raise OffsetRefusal("FIT_UNQUALIFIED")
    _pilot(fit.pilot)
    if (type(fit.training_rows) is not int or fit.training_rows < 1
            or not isinstance(fit.coefficients, tuple)
            or not 0 <= _number(fit.relative_residual) <= RESIDUAL_TOLERANCE):
        raise OffsetRefusal("FIT_UNQUALIFIED")
    decision = _clock(decision_at)
    if decision < _clock(fit.fit_cutoff):
        raise OffsetRefusal("FIT_NOT_AVAILABLE")
    if _clock(feature_available_at) > decision:
        raise OffsetRefusal("FEATURE_NOT_AVAILABLE")
    c, gamma = _vector(covariates, 8), _vector(fit.coefficients, 8)
    b0 = _number(baseline)
    if fit.pilot == "P1" and b0 < 0:
        raise OffsetRefusal("RANGE_DOMAIN")
    try:
        with np.errstate(all="raise"):
            result = float(np.float64(b0) + c @ gamma)
            if not np.isfinite(result):
                raise OffsetRefusal("NUMERIC_FAILURE")
    except FloatingPointError:
        raise OffsetRefusal("NUMERIC_FAILURE") from None
    return max(0.0, result) if fit.pilot == "P1" else result
