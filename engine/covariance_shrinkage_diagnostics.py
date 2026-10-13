from __future__ import annotations

# The house rule puts the __future__ import on line 1, which makes a following
# string literal a no-op expression rather than the module docstring; binding
# __doc__ explicitly keeps the docstring visible to help() and to the tests.
__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q08 — regularized correlation estimators and uncertainty-aware independent-bet
counts for the factor block of ``engine/neuralweb/covariance_spine.py``.

VERDICT (Q08, research/quant_assessment_2026_10/Q08_regularized_covariance/VERDICT.md):
REJECT for the estimator contest. On 17 non-overlapping 21-day held-out blocks of
the 4 daily long-short factor legs, no regularized estimator beat the incumbent
sample correlation on Gaussian/Stein loss with a Bonferroni block-bootstrap
lower bound above zero (best: nonlinear shrinkage, +0.0084 nats/day,
interval [-0.0105, +0.0263]). Keep the incumbent sample estimator. What survives
as a research reference is the uncertainty diagnostic: the incumbent's point
participation ratio 2.4807 carries a 90% stationary-bootstrap interval of about
[2.22, 2.72], so it must not be read as a precise count of independent bets;
plus the basis/support guards.

What this module is
-------------------
A pure, bounded, side-effect-free reference implementation of:

* a basis/unit/clock compatibility guard, so long-short, long-only and excess
  return definitions can never silently share one matrix (the incumbent factor
  block falls back from ``chart_data.spread`` to ``chart_data.long`` per factor);
* a complete-case support check that returns an explicit ``unavailable`` status
  for constant columns or inadequate support instead of handing NaNs to an
  eigensolver;
* four correlation estimators fitted on training rows only — the incumbent
  sample correlation, Ledoit-Wolf (2004) linear shrinkage to the scaled
  identity, Ledoit-Wolf (2003) shrinkage to the constant-correlation
  ("equal") target, and Ledoit-Wolf (2022) quadratic-inverse nonlinear
  shrinkage;
* symmetry / PSD checks at a declared tolerance, with exact zero covariance
  retained by the zero-structure-preserving estimators;
* a participation ratio that refuses an invalid (non-PSD) matrix rather than
  clipping it, and is always inside ``[1, N]``;
* stationary block-bootstrap intervals for the participation ratio, and a
  circular moving-block bootstrap for a mean held-out loss difference;
* rolling-origin held-out correlation losses (Gaussian/Stein and Frobenius).

What it is not
--------------
No risk, gate, rank, sizing or allocation authority; nothing imports it; it
registers nothing, performs no I/O, reads no clock, and does not touch the
frozen PSS-CD1 crowding hazard (HOLD-PSS-CD1-CROWDING). The participation
ratio is a descriptive context number reported WITH an interval — never a
precise integer count of independent bets.
"""

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np

RESEARCH_ONLY = True
AUTHORITY = "context"
SCHEMA = "research.covariance_shrinkage_diagnostics.v1"
NOT_FOR = ("risk", "gate", "rank", "sizing", "allocation", "promotion")

# Declared numerical tolerances (relative to the matrix scale).
SYM_TOL = 1e-12
PSD_TOL = 1e-10
ZERO_SNAP_TOL = 1e-12
CONSTANT_REL_TOL = 1e-12

# Mirrors the incumbent factor block (covariance_spine._FACTOR_MIN_OBS / _MAX_OBS).
DEFAULT_MIN_OBS = 60
DEFAULT_MAX_OBS = 252

ALLOWED_BASES = ("long_short", "long_only", "excess_return", "total_return")


# ---------------------------------------------------------------------------
# Input contract — basis / unit / clock segregation (requirement 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeriesSpec:
    """Declared return definition of one input column."""

    name: str
    basis: str  # one of ALLOWED_BASES
    unit: str  # e.g. "decimal_return" or "percent_return"
    clock: str  # e.g. "daily_close" or "month_end"


def check_compatible(specs: Sequence[SeriesSpec]) -> dict:
    """Return ``{"ok": bool, "reason": str | None, ...}`` for a set of specs.

    Every column must share ONE basis, ONE unit and ONE clock. A mixture is
    refused with an explicit reason; it is never coerced.
    """
    specs = list(specs)
    if not specs:
        return {"ok": False, "reason": "no_columns"}
    bad = [s.name for s in specs if s.basis not in ALLOWED_BASES]
    if bad:
        return {"ok": False, "reason": "unknown_basis:" + ",".join(sorted(bad))}
    for field in ("basis", "unit", "clock"):
        values = sorted({getattr(s, field) for s in specs})
        if len(values) > 1:
            groups = {
                v: sorted(s.name for s in specs if getattr(s, field) == v) for v in values
            }
            detail = ";".join(f"{v}={'|'.join(names)}" for v, names in groups.items())
            return {"ok": False, "reason": f"incompatible_{field}:{detail}"}
    return {
        "ok": True,
        "reason": None,
        "basis": specs[0].basis,
        "unit": specs[0].unit,
        "clock": specs[0].clock,
    }


def _unavailable(reason: str, **extra) -> dict:
    out = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "research_only": RESEARCH_ONLY,
        "status": "unavailable",
        "reason": reason,
    }
    out.update(extra)
    return out


def _is_constant(col: np.ndarray) -> bool:
    scale = max(1.0, float(np.max(np.abs(col)))) if col.size else 1.0
    return float(np.std(col)) <= CONSTANT_REL_TOL * scale


def prepare_panel(
    values: Mapping[str, Sequence[float]],
    specs: Mapping[str, SeriesSpec],
    min_obs: int = DEFAULT_MIN_OBS,
    max_obs: int | None = DEFAULT_MAX_OBS,
) -> dict:
    """Complete-case, trailing-window panel with explicit support accounting.

    Returns ``status == "ok"`` with ``X`` (rows x columns, sorted names) or
    ``status == "unavailable"`` with a reason. Never raises on data problems.
    """
    names = sorted(values)
    if sorted(specs) != names:
        return _unavailable("spec_columns_mismatch")
    compat = check_compatible([specs[n] for n in names])
    if not compat["ok"]:
        return _unavailable(compat["reason"])
    if len(names) < 2:
        return _unavailable("need_at_least_2_columns", n_columns=len(names))
    lengths = {len(values[n]) for n in names}
    if len(lengths) != 1:
        return _unavailable("unequal_column_lengths")
    rows_total = lengths.pop()
    if rows_total == 0:
        return _unavailable("insufficient_support:0_rows", n_obs_used=0)
    mat = np.column_stack(
        [
            np.array([np.nan if v is None else float(v) for v in values[n]], dtype=float)
            for n in names
        ]
    )
    finite = np.isfinite(mat)
    complete = np.all(finite, axis=1)
    idx = np.flatnonzero(complete)
    if max_obs is not None and idx.size > max_obs:
        idx = idx[-max_obs:]
    attrition = {
        "rows_total": int(rows_total),
        "rows_complete": int(complete.sum()),
        "rows_used": int(idx.size),
        "missing_by_column": {n: int((~finite[:, j]).sum()) for j, n in enumerate(names)},
    }
    n_obs, p = int(idx.size), len(names)
    floor = max(int(min_obs), p + 2)
    if n_obs < floor:
        return _unavailable(
            f"insufficient_support:{n_obs}<{floor}", n_obs_used=n_obs, attrition=attrition
        )
    X = mat[idx, :]
    const = [n for j, n in enumerate(names) if _is_constant(X[:, j])]
    if const:
        return _unavailable(
            "constant_column:" + ",".join(const), n_obs_used=n_obs, attrition=attrition
        )
    return {
        "status": "ok",
        "X": X,
        "names": names,
        "basis": compat["basis"],
        "unit": compat["unit"],
        "clock": compat["clock"],
        "n_obs_used": n_obs,
        "attrition": attrition,
    }


# ---------------------------------------------------------------------------
# Matrix validity (requirement 2)
# ---------------------------------------------------------------------------


def matrix_validity(M: np.ndarray, tol: float = PSD_TOL) -> dict:
    """Symmetry and PSD at a declared relative tolerance."""
    M = np.asarray(M, dtype=float)
    if M.ndim != 2 or M.shape[0] != M.shape[1] or not np.all(np.isfinite(M)):
        return {"symmetric": False, "psd": False, "min_eig": None, "max_asym": None}
    scale = max(1.0, float(np.max(np.abs(M))))
    max_asym = float(np.max(np.abs(M - M.T)))
    symmetric = max_asym <= SYM_TOL * scale
    eig = np.linalg.eigvalsh((M + M.T) / 2.0)
    min_eig = float(eig[0])
    psd = symmetric and min_eig >= -tol * max(scale, float(np.max(np.abs(eig))))
    return {"symmetric": bool(symmetric), "psd": bool(psd), "min_eig": min_eig, "max_asym": max_asym}


def cov2corr(C: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.diag(C))
    R = C / np.outer(d, d)
    return R


def _finalize(R: np.ndarray, zero_mask: np.ndarray | None) -> np.ndarray:
    R = (R + R.T) / 2.0
    np.fill_diagonal(R, 1.0)
    if zero_mask is not None:
        snap = zero_mask & (np.abs(R) <= ZERO_SNAP_TOL)
        R = np.where(snap, 0.0, R)
    return R


def _standardize(X: np.ndarray) -> np.ndarray:
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=1)
    return (X - mu) / sd


def exact_zero_mask(X: np.ndarray) -> np.ndarray:
    """Pairs whose demeaned cross-product is exactly zero (valid zero covariance)."""
    D = X - X.mean(axis=0)
    G = D.T @ D
    mask = G == 0.0
    np.fill_diagonal(mask, False)
    return mask


# ---------------------------------------------------------------------------
# Estimators — each takes training rows only and returns (R, meta)
# ---------------------------------------------------------------------------


def sample_correlation(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """Incumbent estimator: Pearson sample correlation."""
    Z = _standardize(X)
    R = Z.T @ Z / (X.shape[0] - 1)
    return _finalize(R, exact_zero_mask(X)), {"intensity": 0.0, "preserves_zero_structure": True}


def linear_shrinkage_identity(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """Ledoit-Wolf (2004) linear shrinkage to the scaled identity, on standardized data."""
    Z = _standardize(X)
    Z = Z - Z.mean(axis=0)
    n, p = Z.shape
    S = Z.T @ Z / n
    Z2 = Z**2
    tr = Z2.sum(axis=0) / n
    mu = tr.sum() / p
    beta_ = float(np.sum(Z2.T @ Z2))
    delta_ = float(np.sum((Z.T @ Z) ** 2)) / n**2
    beta = (beta_ / n - delta_) / (p * n)
    delta = (delta_ - 2.0 * mu * tr.sum() + p * mu**2) / p
    beta = min(beta, delta)
    s = 0.0 if beta <= 0 or delta <= 0 else float(beta / delta)
    C = s * mu * np.eye(p) + (1.0 - s) * S
    return _finalize(cov2corr(C), exact_zero_mask(X)), {
        "intensity": s,
        "preserves_zero_structure": True,
    }


def constant_correlation_shrinkage(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """Ledoit-Wolf (2003) shrinkage to the constant-correlation ("equal") target.

    Does NOT preserve exact zero structure: the target fills every off-diagonal
    with the average correlation. That is declared in the meta, not hidden.
    """
    Z = _standardize(X)
    Y = Z - Z.mean(axis=0)
    n, p = Y.shape
    S = Y.T @ Y / n
    var = np.diag(S).copy()
    sd = np.sqrt(var)
    rbar = (float(np.sum(S / np.outer(sd, sd))) - p) / (p * (p - 1))
    F = rbar * np.outer(sd, sd)
    np.fill_diagonal(F, var)
    Y2 = Y**2
    pi_mat = Y2.T @ Y2 / n - S**2
    pihat = float(pi_mat.sum())
    gammahat = float(np.sum((S - F) ** 2))
    rho_diag = float(np.trace(pi_mat))
    theta = (Y**3).T @ Y / n - var[:, None] * S
    np.fill_diagonal(theta, 0.0)
    rho_off = rbar * float(np.sum(np.outer(1.0 / sd, sd) * theta))
    rhohat = rho_diag + rho_off
    if gammahat <= 0:
        s = 1.0
    else:
        kappa = (pihat - rhohat) / gammahat
        s = float(max(0.0, min(1.0, kappa / n)))
    C = s * F + (1.0 - s) * S
    return _finalize(cov2corr(C), None), {
        "intensity": s,
        "target_mean_corr": rbar,
        "preserves_zero_structure": False,
    }


def nonlinear_shrinkage(X: np.ndarray) -> tuple[np.ndarray, dict]:
    """Ledoit-Wolf (2022) quadratic-inverse shrinkage (QIS), p < n case, standardized data."""
    Z = _standardize(X)
    Y = Z - Z.mean(axis=0)
    N, p = Y.shape
    n = N - 1  # one degree of freedom spent on demeaning
    if p >= n:
        raise ValueError("nonlinear_shrinkage requires p < n - 1")
    c = p / n
    S = Y.T @ Y / n
    S = (S + S.T) / 2.0
    lam, U = np.linalg.eigh(S)
    if lam[0] <= 0:
        raise ValueError("sample matrix singular")
    h = (min(c**2, 1.0 / c**2) ** 0.35) / p**0.35
    inv = 1.0 / lam
    Li = inv[:, None]  # rows i
    Lj = inv[None, :]  # cols j
    diff = Li - Lj
    den = diff**2 + (Li**2) * h**2
    theta = np.mean(Li * diff / den, axis=0)
    htheta = np.mean(Li * (Li * h) / den, axis=0)
    a2 = theta**2 + htheta**2
    delta = 1.0 / ((1 - c) ** 2 * inv + 2 * c * (1 - c) * inv * theta + c**2 * inv * a2)
    delta = delta * (lam.sum() / delta.sum())
    C = U @ np.diag(delta) @ U.T
    return _finalize(cov2corr(C), exact_zero_mask(X)), {
        "intensity": None,
        "bandwidth": h,
        "preserves_zero_structure": True,
    }


ESTIMATORS: dict[str, Callable[[np.ndarray], tuple[np.ndarray, dict]]] = {
    "sample": sample_correlation,
    "lw_identity": linear_shrinkage_identity,
    "lw_constant_corr": constant_correlation_shrinkage,
    "lw_nonlinear": nonlinear_shrinkage,
}
BASELINE = "sample"


# ---------------------------------------------------------------------------
# Participation ratio (requirement 3)
# ---------------------------------------------------------------------------


def participation_ratio(M: np.ndarray) -> float | None:
    """(sum lambda)^2 / sum lambda^2 of a VALID symmetric PSD matrix, in [1, N].

    Returns None for a matrix that is not symmetric PSD at tolerance (e.g. an
    incoherent pairwise-assembled correlation matrix) — it is never clipped
    into a plausible-looking number.
    """
    M = np.asarray(M, dtype=float)
    v = matrix_validity(M)
    if not v["psd"]:
        return None
    eig = np.clip(np.linalg.eigvalsh((M + M.T) / 2.0), 0.0, None)
    s1, s2 = float(eig.sum()), float(np.sum(eig**2))
    if s1 <= 0 or s2 <= 0:
        return None
    pr = s1 * s1 / s2
    n = M.shape[0]
    return float(min(max(pr, 1.0), float(n)))


def dominant_share(M: np.ndarray) -> float | None:
    if not matrix_validity(M)["psd"]:
        return None
    eig = np.clip(np.linalg.eigvalsh((M + M.T) / 2.0), 0.0, None)
    tot = float(eig.sum())
    return None if tot <= 0 else float(eig[-1] / tot)


def incumbent_algorithm_pr(X: np.ndarray) -> dict:
    """Exact replica of the incumbent factor-block arithmetic (for reproduction only)."""
    corr = np.corrcoef(X, rowvar=False)
    eig = np.clip(np.linalg.eigvalsh(corr)[::-1], 0, None)
    share = round(float(eig[0] / eig.sum()), 4) if eig.sum() > 0 else None
    s2 = float(np.sum(eig**2))
    pr = (float(eig.sum()) ** 2 / s2) if s2 > 0 else None
    return {
        "dominant_factor_pc_share": share,
        "effective_factor_bets_pr": round(pr, 4) if pr is not None else None,
    }


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def stationary_bootstrap_indices(n: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap row indices (circular)."""
    p_new = 1.0 / float(mean_block)
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(0, n)
    starts = rng.random(n) < p_new
    fresh = rng.integers(0, n, size=n)
    for t in range(1, n):
        idx[t] = fresh[t] if starts[t] else (idx[t - 1] + 1) % n
    return idx


def moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Circular moving-block bootstrap indices."""
    nb = int(math.ceil(n / block))
    st = rng.integers(0, n, size=nb)
    return ((st[:, None] + np.arange(block)[None, :]).ravel()[:n]) % n


def bootstrap_pr_interval(
    X: np.ndarray,
    estimator: str = BASELINE,
    B: int = 500,
    mean_block: float = 10.0,
    seed: int = 0,
    level: float = 0.90,
) -> dict:
    """Stationary block-bootstrap interval for the participation ratio."""
    if B < 1 or B > 20000:
        raise ValueError("B out of bounds")
    fn = ESTIMATORS[estimator]
    R, _ = fn(X)
    point = participation_ratio(R)
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    vals: list[float] = []
    failed = 0
    for _ in range(B):
        Xb = X[stationary_bootstrap_indices(n, mean_block, rng)]
        if any(_is_constant(Xb[:, j]) for j in range(Xb.shape[1])):
            failed += 1
            continue
        try:
            Rb, _ = fn(Xb)
        except (ValueError, np.linalg.LinAlgError):
            failed += 1
            continue
        pr = participation_ratio(Rb)
        if pr is None:
            failed += 1
            continue
        vals.append(pr)
    if not vals:
        return {"point": point, "lo": None, "hi": None, "median": None, "width": None,
                "n_valid": 0, "n_failed": failed, "B": B, "level": level}
    a = np.asarray(vals)
    lo, hi = np.quantile(a, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {
        "point": point,
        "lo": float(lo),
        "hi": float(hi),
        "median": float(np.median(a)),
        "width": float(hi - lo),
        "n_valid": int(a.size),
        "n_failed": int(failed),
        "B": int(B),
        "level": float(level),
        "mean_block": float(mean_block),
    }


def block_bootstrap_mean_ci(
    d: Sequence[float], block_len: int = 3, B: int = 10000, seed: int = 0, level: float = 0.95
) -> dict:
    """Circular moving-block bootstrap CI for the mean of a dependent series."""
    a = np.asarray([x for x in d if x is not None and np.isfinite(x)], dtype=float)
    n = int(a.size)
    if n < 2 * block_len or n < 4:
        return {"mean": float(a.mean()) if n else None, "lo": None, "hi": None,
                "n_blocks_honest": n, "block_len": block_len, "B": B, "level": level,
                "status": "insufficient_support"}
    rng = np.random.default_rng(seed)
    means = np.empty(B)
    for b in range(B):
        means[b] = a[moving_block_indices(n, block_len, rng)].mean()
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {
        "mean": float(a.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "share_boot_le_0": float(np.mean(means <= 0)),
        "n_blocks_honest": n,
        "block_len": int(block_len),
        "B": int(B),
        "level": float(level),
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Held-out losses (requirement 5)
# ---------------------------------------------------------------------------


def realized_correlation(X_eval: np.ndarray) -> np.ndarray | None:
    if X_eval.shape[0] < X_eval.shape[1] + 2:
        return None
    if any(_is_constant(X_eval[:, j]) for j in range(X_eval.shape[1])):
        return None
    R, _ = sample_correlation(X_eval)
    return R


def gaussian_stein_loss(R_hat: np.ndarray, C_real: np.ndarray) -> float | None:
    """0.5*[tr(R_hat^-1 C_real) + log det R_hat]: mean Gaussian NLL (constant dropped)
    of evaluation rows self-standardized by the evaluation block (an evaluation-only
    transform shared by every estimator). Proper: minimized in expectation by the
    true correlation."""
    try:
        L = np.linalg.cholesky(R_hat)
    except np.linalg.LinAlgError:
        return None
    logdet = 2.0 * float(np.sum(np.log(np.diag(L))))
    inv = np.linalg.solve(R_hat, C_real)
    return 0.5 * (float(np.trace(inv)) + logdet)


def frobenius_offdiag_loss(R_hat: np.ndarray, C_real: np.ndarray) -> float:
    iu = np.triu_indices(R_hat.shape[0], k=1)
    return float(np.sum((R_hat[iu] - C_real[iu]) ** 2))


def rolling_origin_losses(
    X: np.ndarray,
    train: int,
    horizon: int,
    estimators: Sequence[str] = tuple(ESTIMATORS),
    first_origin: int | None = None,
) -> list[dict]:
    """Non-overlapping evaluation blocks; every estimator is fitted on the trailing
    ``train`` rows before the origin and nothing after it."""
    n = X.shape[0]
    t = int(train if first_origin is None else first_origin)
    if t < train:
        raise ValueError("first_origin earlier than the training window")
    out: list[dict] = []
    k = 0
    while t + horizon <= n:
        Xtr = X[t - train : t]
        Xev = X[t : t + horizon]
        row: dict = {"block": k, "train_rows": [t - train, t], "eval_rows": [t, t + horizon]}
        C = realized_correlation(Xev)
        const_tr = any(_is_constant(Xtr[:, j]) for j in range(X.shape[1]))
        for name in estimators:
            rec: dict = {"status": "ok"}
            if const_tr:
                rec = {"status": "unavailable", "reason": "constant_column_in_training"}
            elif C is None:
                rec = {"status": "unavailable", "reason": "eval_block_unsupported"}
            else:
                try:
                    R, meta = ESTIMATORS[name](Xtr)
                except (ValueError, np.linalg.LinAlgError) as exc:
                    rec = {"status": "unavailable", "reason": f"estimator_failed:{exc}"}
                else:
                    rec["stein"] = gaussian_stein_loss(R, C)
                    rec["frobenius"] = frobenius_offdiag_loss(R, C)
                    rec["pr"] = participation_ratio(R)
                    rec["intensity"] = meta.get("intensity")
                    rec["psd"] = matrix_validity(R)["psd"]
            row[name] = rec
        out.append(row)
        t += horizon
        k += 1
    return out


# ---------------------------------------------------------------------------
# Context-only top-level diagnostic (requirement 6)
# ---------------------------------------------------------------------------


def estimate(
    values: Mapping[str, Sequence[float]],
    specs: Mapping[str, SeriesSpec],
    estimator: str = BASELINE,
    min_obs: int = DEFAULT_MIN_OBS,
    max_obs: int | None = DEFAULT_MAX_OBS,
    bootstrap_B: int = 500,
    mean_block: float = 10.0,
    seed: int = 0,
) -> dict:
    """Context-only correlation + participation-ratio interval. Never raises on data."""
    if estimator not in ESTIMATORS:
        return _unavailable(f"unknown_estimator:{estimator}")
    panel = prepare_panel(values, specs, min_obs=min_obs, max_obs=max_obs)
    if panel["status"] != "ok":
        return panel
    X = panel["X"]
    try:
        R, meta = ESTIMATORS[estimator](X)
    except (ValueError, np.linalg.LinAlgError) as exc:
        return _unavailable(f"estimator_failed:{exc}", n_obs_used=panel["n_obs_used"])
    validity = matrix_validity(R)
    interval = bootstrap_pr_interval(X, estimator, B=bootstrap_B, mean_block=mean_block, seed=seed)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "research_only": RESEARCH_ONLY,
        "not_for": list(NOT_FOR),
        "status": "ok",
        "estimator": estimator,
        "estimator_meta": meta,
        "names": panel["names"],
        "basis": panel["basis"],
        "unit": panel["unit"],
        "clock": panel["clock"],
        "correlation": R.tolist(),
        "validity": validity,
        "participation_ratio": {
            "point": participation_ratio(R),
            "lo": interval["lo"],
            "hi": interval["hi"],
            "level": interval["level"],
            "n_valid_resamples": interval["n_valid"],
            "bounds": [1.0, float(len(panel["names"]))],
        },
        "dominant_share": dominant_share(R),
        "n_obs_used": panel["n_obs_used"],
        "attrition": panel["attrition"],
    }
