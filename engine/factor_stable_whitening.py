from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q17 (quant assessment 2026-10): stable symmetric factor whitening under
collinearity and missing observations.

VERDICT: see research/quant_assessment_2026_10/Q17_stable_factor_whitening/VERDICT.md
(recorded verdict: REJECT).

What this module is
-------------------
A pure-function challenger to the incumbent additive Löwdin whitening in
``engine/factor_orthogonal.py`` (``orthogonalize``: complete-case sample
correlation, eigenvalue floor 1e-6, zero-fill of missing legs in z-space, and a
silent ``factors.copy()`` fallback when support is thin).  The challenger keeps
the *symmetric* (Löwdin) form, so it stays permutation-equivariant, and changes
four numerics:

1. correlation is estimated from all jointly observed pairs (available-case),
   repaired to positive semi-definite, then shrunk toward the identity with a
   frozen Ledoit-Wolf-type intensity (elementwise generalisation for missing
   cells; Ledoit & Wolf, doi 10.1214/12-AOS989 is the literature anchor);
2. the eigenvalues used by the inverse square root are floored at
   ``EIG_FLOOR`` = 0.05, so the largest coordinate amplification is bounded by
   ``MAX_AMPLIFICATION`` (about 4.47 instead of 1000), and the raw estimate is
   flagged ``unstable`` whenever its smallest eigenvalue sits below that floor;
3. a missing leg is filled with its conditional expectation given the row's
   measured legs (not with 0), and every output row carries ``measured``
   indicators, ``n_measured`` and a ``row_status`` of full / partial /
   unmeasured, so a partially measured row is never presented as fully measured;
4. a thin-support input returns the raw input with status
   ``untransformed_fallback`` and ``whitened=False``.

What it is not
--------------
Not wired, imported, scheduled or registered anywhere.  It does not change live
factor ranks, Factor Atlas ownership, the composite, the IC scorecard or the
trial budget (``TRIAL_BUDGET_CHARGE = 0``).  It is not a covariance-of-returns
estimator (a separate estimand), not a new composite, and whitened coordinates
are statistical rotations, not independent economic bets.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

RESEARCH_ONLY = True
CONSUMERS: tuple[str, ...] = ()
TRIAL_BUDGET_CHARGE = 0

STATUS_WHITENED = "whitened"
STATUS_REGULARIZED = "regularized"
STATUS_FALLBACK = "untransformed_fallback"

ROW_FULL = "full"
ROW_PARTIAL = "partial"
ROW_UNMEASURED = "unmeasured"

INCUMBENT_EIG_FLOOR = 1e-6
EIG_FLOOR = 0.05
MAX_AMPLIFICATION = 1.0 / math.sqrt(EIG_FLOOR)
SHRINKAGE_REGULARIZED_AT = 0.10
MIN_SUPPORT_ABS = 30
MIN_SUPPORT_PER_FACTOR = 3
OUTPUT_INSTABILITY_BAR = 0.25

MAX_FACTORS = 64
MAX_ROWS = 200_000
MAX_BOOT = 2_000


# ----------------------------------------------------------------------------
# input bounds and standardisation
# ----------------------------------------------------------------------------
def _check_frame(factors: pd.DataFrame) -> np.ndarray:
    if not isinstance(factors, pd.DataFrame):
        raise TypeError("factors must be a pandas DataFrame")
    n, p = factors.shape
    if p > MAX_FACTORS:
        raise ValueError(f"too many factors: {p} > {MAX_FACTORS}")
    if n > MAX_ROWS:
        raise ValueError(f"too many rows: {n} > {MAX_ROWS}")
    if len(set(map(str, factors.columns))) != p:
        raise ValueError("factor column names must be unique")
    X = factors.to_numpy(dtype=float, copy=True)
    if np.isinf(X).any():
        raise ValueError("factors contain +/-inf; pass NaN for missing values")
    return X


def support_rule(p: int) -> int:
    """Frozen minimum pairwise support (same constants as the incumbent)."""
    return max(MIN_SUPPORT_ABS, MIN_SUPPORT_PER_FACTOR * int(p))


def standardize(factors: pd.DataFrame) -> pd.DataFrame:
    """Available-case z-score per column (ddof=0); zero-variance columns -> NaN."""
    X = _check_frame(factors)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.nanmean(X, axis=0) if X.size else np.zeros(X.shape[1])
        sd = np.nanstd(X, axis=0) if X.size else np.zeros(X.shape[1])
    sd = np.where(sd > 0, sd, np.nan)
    Z = (X - mu) / sd
    return pd.DataFrame(Z, index=factors.index, columns=factors.columns)


# ----------------------------------------------------------------------------
# incumbent reference (reproduces engine.factor_orthogonal.orthogonalize)
# ----------------------------------------------------------------------------
def _inv_sqrt(C: np.ndarray, floor: float) -> tuple[np.ndarray, np.ndarray]:
    w, V = np.linalg.eigh((C + C.T) / 2.0)
    wf = np.clip(w, floor, None)
    return V @ np.diag(1.0 / np.sqrt(wf)) @ V.T, w


def incumbent_reference_transform(factors: pd.DataFrame) -> pd.DataFrame:
    """Re-statement of the incumbent formula, for side-by-side diagnostics only."""
    _check_frame(factors)
    cols = list(factors.columns)
    if len(cols) < 2:
        return factors.copy()
    Z = standardize(factors)
    complete = Z.dropna()
    if len(complete) < support_rule(len(cols)):
        return factors.copy()
    C = np.corrcoef(complete.to_numpy(), rowvar=False)
    W, _ = _inv_sqrt(C, INCUMBENT_EIG_FLOOR)
    out = pd.DataFrame(Z.fillna(0.0).to_numpy() @ W, index=Z.index, columns=cols)
    out = standardize(out)
    out[Z.isna().all(axis=1)] = np.nan
    return out


def incumbent_weights(Zc: np.ndarray) -> np.ndarray:
    """Incumbent W from complete-case standardized rows."""
    C = np.corrcoef(Zc, rowvar=False)
    return _inv_sqrt(C, INCUMBENT_EIG_FLOOR)[0]


# ----------------------------------------------------------------------------
# challenger estimator
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class CorrelationEstimate:
    corr_raw: np.ndarray          # available-case correlation (may be indefinite)
    corr_used: np.ndarray         # PSD-repaired, shrunk, eigen-floored
    shrinkage: float
    pair_counts: np.ndarray
    diagnostics: dict


def _pairwise_moments(Z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    M = ~np.isnan(Z)
    X0 = np.where(M, Z, 0.0)
    Mf = M.astype(float)
    counts = Mf.T @ Mf
    with np.errstate(invalid="ignore", divide="ignore"):
        S = (X0.T @ X0) / counts
        Q = ((X0 ** 2).T @ (X0 ** 2))
    return S, counts, Q


def estimate_correlation(Z: pd.DataFrame | np.ndarray) -> CorrelationEstimate:
    """Available-case correlation -> PSD repair -> frozen shrinkage -> floor.

    Shrinkage intensity (frozen rule): s = clip(sum_{i!=j} B_ij / sum_{i!=j} S_ij^2, 0, 1)
    with B_ij = sum_k (z_ki z_kj - S_ij)^2 / n_ij^2 over jointly observed rows,
    the elementwise form of the Ledoit-Wolf identity-target intensity.
    """
    Zn = Z.to_numpy(dtype=float) if isinstance(Z, pd.DataFrame) else np.asarray(Z, float)
    p = Zn.shape[1]
    S, counts, Q = _pairwise_moments(Zn)
    if np.any(counts < 2) or np.isnan(S).any():
        raise ValueError("insufficient joint observations for a pairwise correlation")
    S = (S + S.T) / 2.0
    np.fill_diagonal(S, 1.0)
    off = ~np.eye(p, dtype=bool)
    B = (Q - counts * S ** 2) / counts ** 2
    delta = float(np.sum(S[off] ** 2))
    beta = float(np.sum(np.clip(B[off], 0.0, None)))
    s = 0.0 if delta <= 1e-15 else float(min(max(beta / delta, 0.0), 1.0))

    w_raw, V = np.linalg.eigh(S)
    C_psd = V @ np.diag(np.clip(w_raw, 0.0, None)) @ V.T
    d = np.sqrt(np.clip(np.diag(C_psd), 1e-12, None))
    C_psd = C_psd / np.outer(d, d)
    C_shr = (1.0 - s) * C_psd + s * np.eye(p)
    w_shr, V2 = np.linalg.eigh((C_shr + C_shr.T) / 2.0)
    w_used = np.clip(w_shr, EIG_FLOOR, None)
    C_used = V2 @ np.diag(w_used) @ V2.T

    raw_min = float(w_raw.min())
    raw_max = float(w_raw.max())
    diag = {
        "p": int(p),
        "min_pair_count": int(counts.min()),
        "raw_min_eig": raw_min,
        "raw_max_eig": raw_max,
        "raw_condition_number": float(raw_max / max(raw_min, 1e-12)),
        "incumbent_floor_amplification": float(1.0 / math.sqrt(max(raw_min, INCUMBENT_EIG_FLOOR))),
        "raw_indefinite": bool(raw_min < -1e-10),
        "shrinkage": s,
        "shrunk_min_eig": float(w_shr.min()),
        "floor_binding": int(np.sum(w_shr < EIG_FLOOR)),
        "used_condition_number": float(w_used.max() / w_used.min()),
        "applied_max_amplification": float(1.0 / math.sqrt(w_used.min())),
        "unstable": bool(raw_min < EIG_FLOOR),
    }
    return CorrelationEstimate(S, C_used, s, counts, diag)


def whitening_matrix(C_used: np.ndarray) -> np.ndarray:
    """Symmetric inverse square root (Löwdin); C_used is already floored."""
    w, V = np.linalg.eigh((C_used + C_used.T) / 2.0)
    w = np.clip(w, EIG_FLOOR, None)
    return V @ np.diag(1.0 / np.sqrt(w)) @ V.T


def conditional_fill(Z: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Replace each missing z by E[z_m | z_o] = C_mo C_oo^{-1} z_o (0 if nothing observed)."""
    out = Z.copy()
    M = ~np.isnan(Z)
    if M.all():
        return out
    patterns: dict[bytes, list[int]] = {}
    for r in range(Z.shape[0]):
        patterns.setdefault(M[r].tobytes(), []).append(r)
    for key, rows in patterns.items():
        obs = np.frombuffer(key, dtype=bool)
        if obs.all():
            continue
        mis = ~obs
        idx = np.asarray(rows)
        if not obs.any():
            out[np.ix_(idx, np.flatnonzero(mis))] = 0.0
            continue
        Coo = C[np.ix_(obs, obs)]
        Cmo = C[np.ix_(mis, obs)]
        beta = np.linalg.solve(Coo, Cmo.T)          # |o| x |m|
        out[np.ix_(idx, np.flatnonzero(mis))] = Z[np.ix_(idx, np.flatnonzero(obs))] @ beta
    return out


@dataclass(frozen=True)
class WhiteningResult:
    values: pd.DataFrame
    status: str
    whitened: bool
    measured: pd.DataFrame
    n_measured: pd.Series
    row_status: pd.Series
    raw_z: pd.DataFrame
    W: np.ndarray | None
    corr_used: np.ndarray | None
    diagnostics: dict = field(default_factory=dict)


def _row_bookkeeping(factors: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    measured = factors.notna()
    n_meas = measured.sum(axis=1).astype(int)
    p = factors.shape[1]
    rs = np.where(n_meas == p, ROW_FULL, np.where(n_meas == 0, ROW_UNMEASURED, ROW_PARTIAL))
    return measured, n_meas, pd.Series(rs, index=factors.index, name="row_status")


def stable_whiten(factors: pd.DataFrame) -> WhiteningResult:
    """Challenger transform. Pure; never mutates ``factors``."""
    _check_frame(factors)
    measured, n_meas, row_status = _row_bookkeeping(factors)
    cols = list(factors.columns)
    p = len(cols)
    Z = standardize(factors)
    base = dict(p=p, n_rows=int(len(factors)), support_required=support_rule(p))

    def _fallback(reason: str) -> WhiteningResult:
        d = dict(base, fallback_reason=reason)
        return WhiteningResult(factors.copy(), STATUS_FALLBACK, False, measured, n_meas,
                               row_status, Z, None, None, d)

    if p < 2:
        return _fallback("fewer than two factors")
    Zn = Z.to_numpy()
    Mf = (~np.isnan(Zn)).astype(float)
    counts = Mf.T @ Mf
    if counts.min() < support_rule(p):
        return _fallback(f"min pairwise support {int(counts.min())} < {support_rule(p)}")
    est = estimate_correlation(Zn)
    W = whitening_matrix(est.corr_used)
    filled = conditional_fill(Zn, est.corr_used)
    Y = filled @ W
    Y[n_meas.to_numpy() == 0] = np.nan
    vals = standardize(pd.DataFrame(Y, index=factors.index, columns=cols))
    regularized = est.diagnostics["floor_binding"] > 0 or est.shrinkage > SHRINKAGE_REGULARIZED_AT
    status = STATUS_REGULARIZED if regularized else STATUS_WHITENED
    d = dict(base, **est.diagnostics,
             n_full_rows=int((row_status == ROW_FULL).sum()),
             n_partial_rows=int((row_status == ROW_PARTIAL).sum()),
             n_unmeasured_rows=int((row_status == ROW_UNMEASURED).sum()))
    return WhiteningResult(vals, status, True, measured, n_meas, row_status, Z, W,
                           est.corr_used, d)


# ----------------------------------------------------------------------------
# diagnostics: off-diagonal residual, bootstrap instability
# ----------------------------------------------------------------------------
def mean_abs_offdiag(Y: np.ndarray) -> float:
    Y = np.asarray(Y, float)
    Y = Y[~np.isnan(Y).any(axis=1)]
    if Y.shape[0] < 3 or Y.shape[1] < 2:
        return float("nan")
    C = np.corrcoef(Y, rowvar=False)
    off = ~np.eye(C.shape[0], dtype=bool)
    return float(np.mean(np.abs(C[off])))


def independent_noise_floor(n: int, p: int) -> float:
    """E|r| for independent columns with n rows: sqrt(2/(pi (n-1))) (within-window null)."""
    if n < 3:
        return float("nan")
    return float(math.sqrt(2.0 / (math.pi * (n - 1))))


def _fit_w(Zn: np.ndarray, method: str) -> np.ndarray:
    if method == "incumbent":
        Zc = Zn[~np.isnan(Zn).any(axis=1)]
        return incumbent_weights(Zc)
    if method == "stable":
        return whitening_matrix(estimate_correlation(Zn).corr_used)
    raise ValueError("method must be 'incumbent' or 'stable'")


DEGENERACY_RTOL = 1e-8
MIN_OUTPUT_ROWS = 3


def amplified_subspace(W: np.ndarray, rtol: float = DEGENERACY_RTOL) -> np.ndarray:
    """Orthonormal basis (p x k) of the most-amplified subspace of W = C^{-1/2}.

    The smallest eigenvalue of C is the largest eigenvalue of W.  When the floor
    binds two or more eigenvalues, that top eigenvalue is degenerate and any single
    eigenvector inside the block is arbitrary, so the whole block (eigenvalues
    within ``rtol`` of the maximum, relative) is returned, with k >= 1.
    """
    w, V = np.linalg.eigh((W + W.T) / 2.0)
    top = float(w[-1])
    keep = w >= top - rtol * max(abs(top), 1.0)
    return V[:, keep]


def subspace_sine(U_a: np.ndarray, U_b: np.ndarray) -> float:
    """Sine of the largest principal angle between the smaller and the larger of
    two orthonormal bases (0 when the smaller subspace lies inside the larger).

    For two one-dimensional subspaces it equals sqrt(1 - (u_a . u_b)^2)."""
    small, large = (U_a, U_b) if U_a.shape[1] <= U_b.shape[1] else (U_b, U_a)
    resid = small - large @ (large.T @ small)
    return float(min(1.0, np.linalg.norm(resid, 2)))


def _has_support(Zn: np.ndarray, method: str) -> bool:
    """The method's own support rule: complete cases for the incumbent, pairwise
    available cases (the rule ``stable_whiten`` applies) for the challenger."""
    p = Zn.shape[1]
    if p < 2:
        return False
    if method == "stable":
        Mf = (~np.isnan(Zn)).astype(float)
        return bool((Mf.T @ Mf).min() >= support_rule(p))
    return int((~np.isnan(Zn).any(axis=1)).sum()) >= support_rule(p)


def bootstrap_instability(factors: pd.DataFrame, *, method: str = "stable",
                          n_boot: int = 50, seed: int = 0) -> dict:
    """Row (name) bootstrap of the fitted transform.

    Support follows each method's own rule (``_has_support``): complete cases for
    the incumbent, pairwise available cases for the challenger, so a cross-section
    the challenger can whiten is not reported as a fallback.

    Reports transform and output relative change, the sine of the largest
    principal angle between the most-amplified subspace of the base and the
    resampled fits (``amplified_subspace``; a degenerate floored block is compared
    as a subspace, never as an arbitrary vector), and the in-sample fitted
    off-diagonal correlation (which stays near zero even when the transform is
    unstable — the reason it is not reported alone).  Output change is measured on
    the complete-case rows of the input so both methods are compared on the same
    rows; with fewer than ``MIN_OUTPUT_ROWS`` such rows those fields are NaN and
    ``output_unstable`` is None.
    """
    _check_frame(factors)
    if not 1 <= int(n_boot) <= MAX_BOOT:
        raise ValueError(f"n_boot must be in [1, {MAX_BOOT}]")
    if method not in ("incumbent", "stable"):
        raise ValueError("method must be 'incumbent' or 'stable'")
    Zn = standardize(factors).to_numpy()
    complete = Zn[~np.isnan(Zn).any(axis=1)]
    if not _has_support(Zn, method):
        return {"method": method, "status": STATUS_FALLBACK, "n_boot": 0}
    W0 = _fit_w(Zn, method)
    U0 = amplified_subspace(W0)
    out_ok = len(complete) >= MIN_OUTPUT_ROWS
    Y0 = complete @ W0
    y0n = float(np.linalg.norm(Y0)) if out_ok else 0.0
    out_ok = out_ok and y0n > 0.0
    rng = np.random.default_rng(seed)
    n = Zn.shape[0]
    t_chg, o_chg, sines, fitted, dims = [], [], [], [], []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        Zb = standardize(pd.DataFrame(Zn[idx])).to_numpy()
        try:
            Wb = _fit_w(Zb, method)
        except (ValueError, np.linalg.LinAlgError):
            continue
        t_chg.append(np.linalg.norm(Wb - W0) / np.linalg.norm(W0))
        if out_ok:
            o_chg.append(np.linalg.norm(complete @ Wb - Y0) / y0n)
        Ub = amplified_subspace(Wb)
        dims.append(Ub.shape[1])
        sines.append(subspace_sine(U0, Ub))
        Zbc = Zb[~np.isnan(Zb).any(axis=1)]
        fitted.append(mean_abs_offdiag(Zbc @ Wb))
    if not t_chg:
        return {"method": method, "status": "bootstrap_failed", "n_boot": 0}
    q = lambda a, x: float(np.quantile(np.asarray(a), x)) if len(a) else float("nan")  # noqa: E731
    out_med = q(o_chg, 0.5)
    return {
        "method": method,
        "status": "ok",
        "n_boot": len(t_chg),
        "transform_rel_change_median": q(t_chg, 0.5),
        "transform_rel_change_p90": q(t_chg, 0.9),
        "output_rel_change_median": out_med,
        "output_rel_change_p90": q(o_chg, 0.9),
        "output_rows": int(len(complete)),
        "max_amplified_direction_sine_median": q(sines, 0.5),
        "amplified_subspace_dim_base": int(U0.shape[1]),
        "amplified_subspace_dim_median": q(dims, 0.5),
        "amplified_subspace_degenerate": bool(U0.shape[1] > 1),
        "fitted_offdiag_median": q(fitted, 0.5),
        "output_unstable": bool(out_med > OUTPUT_INSTABILITY_BAR) if out_ok else None,
    }


def transform_drift(W_a: np.ndarray, W_b: np.ndarray) -> float:
    """Relative Frobenius change between two fitted transforms on the same legs."""
    return float(np.linalg.norm(W_b - W_a) / np.linalg.norm(W_a))
