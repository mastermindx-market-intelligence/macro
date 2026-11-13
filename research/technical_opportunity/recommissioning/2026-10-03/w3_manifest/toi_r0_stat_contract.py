"""TOI R0 model/inference contract — research-only, outcome-blind.

This module freezes deterministic numerical mechanics for the Daily-first TOI R0
candidate. It is not a production engine, does not read market data, and does not
write the TrialLedger. All functions are pure numpy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

RIDGE_LAMBDA = 1.0
GRAD_TOL = 1e-8
MAX_ITER = 100
ARMIJO_C = 1e-4
MIN_STEP = 2.0 ** -20
PROB_EPS = 1e-8
ZERO_SD_EPS = 1e-12
BOOT_DRAWS = 5000
BOOT_SEED = 20261006
PRIMARY_BLOCK_SESSIONS = 22
SENSITIVITY_BLOCK_SESSIONS = (44, 66)
FAMILYWISE_ALPHA = 0.05


@dataclass(frozen=True)
class FitResult:
    coef: np.ndarray
    intercept: np.ndarray
    converged: bool
    iterations: int
    objective: float
    grad_inf: float
    reason: str | None = None


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(np.asarray(z, float), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def _softmax_reference(logits_nonref: np.ndarray) -> np.ndarray:
    a = np.asarray(logits_nonref, float)
    full = np.concatenate([a, np.zeros((len(a), 1), dtype=float)], axis=1)
    m = np.max(full, axis=1, keepdims=True)
    e = np.exp(full - m)
    return e / e.sum(axis=1, keepdims=True)


def standardize_train(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Train-only mean/std (ddof=0). Zero-variance columns become all-zero and are flagged."""
    X = np.asarray(X, float)
    if X.ndim != 2 or not np.isfinite(X).all():
        raise ValueError("X must be finite 2D")
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=0)
    zero = sd <= ZERO_SD_EPS
    safe = sd.copy()
    safe[zero] = 1.0
    Z = (X - mu) / safe
    Z[:, zero] = 0.0
    return Z, mu, safe, zero


def apply_standardization(X: np.ndarray, mu: np.ndarray, sd: np.ndarray, zero: np.ndarray) -> np.ndarray:
    X = np.asarray(X, float)
    if not np.isfinite(X).all():
        raise ValueError("X must be finite")
    Z = (X - mu) / sd
    Z[:, zero] = 0.0
    return Z


def _binary_terms(params: np.ndarray, X: np.ndarray, y: np.ndarray, l2: float):
    p_dim = X.shape[1]
    w = params[:p_dim]
    b = float(params[p_dim])
    z = X @ w + b
    prob = _sigmoid(z)
    n = len(y)
    nll = float(np.mean(np.logaddexp(0.0, z) - y * z))
    obj = nll + 0.5 * float(l2) * float(w @ w)
    g = prob - y
    grad = np.concatenate([X.T @ g / n + float(l2) * w, [float(g.mean())]])
    wt = prob * (1.0 - prob)
    Z = np.column_stack([X, np.ones(n)])
    H = (Z.T * wt) @ Z / n
    H[:p_dim, :p_dim] += float(l2) * np.eye(p_dim)
    return obj, grad, H


def _newton(opt_terms, init: np.ndarray, *, max_iter: int = MAX_ITER, tol: float = GRAD_TOL):
    x = np.asarray(init, float).copy()
    last_obj = math.inf
    for it in range(1, int(max_iter) + 1):
        obj, grad, H = opt_terms(x)
        ginf = float(np.max(np.abs(grad)))
        if not np.isfinite(obj) or not np.isfinite(grad).all() or not np.isfinite(H).all():
            return x, False, it, float(obj), ginf, "non_finite"
        if ginf <= tol:
            return x, True, it, float(obj), ginf, None
        try:
            direction = -np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            return x, False, it, float(obj), ginf, "singular_hessian"
        gd = float(grad @ direction)
        if not np.isfinite(gd) or gd >= 0:
            return x, False, it, float(obj), ginf, "non_descent_newton_step"
        step = 1.0
        accepted = False
        while step >= MIN_STEP:
            cand = x + step * direction
            cand_obj, _, _ = opt_terms(cand)
            if np.isfinite(cand_obj) and cand_obj <= obj + ARMIJO_C * step * gd:
                x = cand
                last_obj = float(cand_obj)
                accepted = True
                break
            step *= 0.5
        if not accepted:
            return x, False, it, float(obj), ginf, "line_search_failed"
    obj, grad, _ = opt_terms(x)
    return x, False, int(max_iter), float(obj), float(np.max(np.abs(grad))), "max_iter"


def fit_binary_ridge(X: np.ndarray, y: np.ndarray, *, l2: float = RIDGE_LAMBDA) -> FitResult:
    """Mean binary NLL + (lambda/2)||beta||^2. Intercept is unpenalized."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    if X.ndim != 2 or y.ndim != 1 or len(X) != len(y) or len(y) == 0:
        raise ValueError("shape mismatch")
    if not np.isfinite(X).all() or not np.isfinite(y).all() or not np.isin(y, [0.0, 1.0]).all():
        raise ValueError("binary fit requires finite X and y in {0,1}")
    params, ok, it, obj, ginf, reason = _newton(
        lambda q: _binary_terms(q, X, y, float(l2)),
        np.zeros(X.shape[1] + 1),
    )
    return FitResult(params[:-1], np.array([params[-1]]), ok, it, obj, ginf, reason)


def predict_binary(X: np.ndarray, fit: FitResult) -> np.ndarray:
    return _sigmoid(np.asarray(X, float) @ fit.coef + float(fit.intercept[0]))


def _multinomial_terms(params: np.ndarray, X: np.ndarray, y: np.ndarray, k: int, l2: float):
    n, p = X.shape
    q = k - 1
    d = p + 1
    theta = params.reshape((d, q), order="F")
    W, b = theta[:p, :], theta[p, :]
    P = _softmax_reference(X @ W + b)
    Y = np.eye(k, dtype=float)[y]
    obj = -float(np.mean(np.log(np.clip(P[np.arange(n), y], PROB_EPS, 1.0))))
    obj += 0.5 * float(l2) * float(np.sum(W * W))
    G = P[:, :q] - Y[:, :q]
    Z = np.column_stack([X, np.ones(n)])
    grad_m = Z.T @ G / n
    grad_m[:p, :] += float(l2) * W
    grad = grad_m.reshape(-1, order="F")
    H = np.zeros((d * q, d * q), dtype=float)
    for i in range(n):
        pn = P[i, :q]
        C = np.diag(pn) - np.outer(pn, pn)
        H += np.kron(C, np.outer(Z[i], Z[i]))
    H /= n
    pen = np.tile(np.concatenate([np.full(p, float(l2)), [0.0]]), q)
    H += np.diag(pen)
    return obj, grad, H


def fit_multinomial_ridge(
    X: np.ndarray,
    y: np.ndarray,
    *,
    classes: int = 3,
    l2: float = RIDGE_LAMBDA,
) -> FitResult:
    """Reference-class softmax; final class is fixed reference. Mean NLL + exact ridge."""
    X = np.asarray(X, float)
    y = np.asarray(y, int)
    k = int(classes)
    if X.ndim != 2 or y.ndim != 1 or len(X) != len(y) or len(y) == 0 or k < 2:
        raise ValueError("shape mismatch")
    if not np.isfinite(X).all() or np.any(y < 0) or np.any(y >= k):
        raise ValueError("invalid multinomial input")
    q = k - 1
    d = X.shape[1] + 1
    params, ok, it, obj, ginf, reason = _newton(
        lambda z: _multinomial_terms(z, X, y, k, float(l2)),
        np.zeros(d * q),
    )
    theta = params.reshape((d, q), order="F")
    return FitResult(theta[:-1, :], theta[-1, :], ok, it, obj, ginf, reason)


def predict_multinomial(X: np.ndarray, fit: FitResult) -> np.ndarray:
    return _softmax_reference(np.asarray(X, float) @ fit.coef + fit.intercept)


def fit_binary_platt(raw_p: np.ndarray, y: np.ndarray):
    """Unpenalized slope/intercept recalibration. Nonpositive slope is non-estimable for display."""
    p = np.clip(np.asarray(raw_p, float), PROB_EPS, 1.0 - PROB_EPS)
    y = np.asarray(y, float)
    if len(p) != len(y) or len(p) == 0 or len(np.unique(y)) < 2:
        return {"estimable": False, "reason": "class_absent"}
    z = np.log(p / (1.0 - p))[:, None]
    fit = fit_binary_ridge(z, y, l2=0.0)
    slope = float(fit.coef[0]) if fit.coef.size else math.nan
    if not fit.converged:
        return {"estimable": False, "reason": fit.reason}
    if not np.isfinite(slope) or slope <= 0:
        return {"estimable": False, "reason": "nonpositive_slope", "slope": slope}
    return {"estimable": True, "slope": slope, "intercept": float(fit.intercept[0])}


def apply_binary_platt(raw_p: np.ndarray, cal: dict) -> np.ndarray:
    if not cal.get("estimable"):
        raise ValueError("calibration unavailable")
    p = np.clip(np.asarray(raw_p, float), PROB_EPS, 1.0 - PROB_EPS)
    z = np.log(p / (1.0 - p))
    return _sigmoid(float(cal["slope"]) * z + float(cal["intercept"]))


def _multical_terms(params: np.ndarray, raw_p: np.ndarray, y: np.ndarray):
    n, k = raw_p.shape
    q = k - 1
    ref = np.clip(raw_p[:, [-1]], PROB_EPS, 1.0)
    z = np.log(np.clip(raw_p[:, :q], PROB_EPS, 1.0) / ref)
    a = float(params[0])
    b = params[1:]
    P = _softmax_reference(a * z + b)
    Y = np.eye(k, dtype=float)[y]
    G = P[:, :q] - Y[:, :q]
    obj = -float(np.mean(np.log(np.clip(P[np.arange(n), y], PROB_EPS, 1.0))))
    grad = np.concatenate([[float(np.mean(np.sum(G * z, axis=1)))], G.mean(axis=0)])
    H = np.zeros((1 + q, 1 + q), dtype=float)
    for i in range(n):
        pn = P[i, :q]
        C = np.diag(pn) - np.outer(pn, pn)
        J = np.zeros((q, 1 + q), dtype=float)
        J[:, 0] = z[i]
        J[:, 1:] = np.eye(q)
        H += J.T @ C @ J
    H /= n
    return obj, grad, H


def fit_multinomial_logistic_calibration(raw_p: np.ndarray, y: np.ndarray):
    """One shared positive log-odds slope plus K-1 intercept shifts; last class is reference."""
    raw_p = np.asarray(raw_p, float)
    y = np.asarray(y, int)
    if raw_p.ndim != 2 or len(raw_p) != len(y) or raw_p.shape[1] < 2:
        raise ValueError("shape mismatch")
    k = raw_p.shape[1]
    if set(np.unique(y)) != set(range(k)):
        return {"estimable": False, "reason": "class_absent"}
    init = np.zeros(k, dtype=float)
    init[0] = 1.0
    params, ok, it, obj, ginf, reason = _newton(
        lambda z: _multical_terms(z, raw_p, y),
        init,
    )
    slope = float(params[0])
    if not ok:
        return {"estimable": False, "reason": reason}
    if not np.isfinite(slope) or slope <= 0:
        return {"estimable": False, "reason": "nonpositive_slope", "slope": slope}
    return {
        "estimable": True,
        "slope": slope,
        "intercepts_nonref": params[1:].tolist(),
        "reference_intercept": 0.0,
        "objective": obj,
        "grad_inf": ginf,
        "iterations": it,
    }


def apply_multinomial_logistic_calibration(raw_p: np.ndarray, cal: dict) -> np.ndarray:
    if not cal.get("estimable"):
        raise ValueError("calibration unavailable")
    raw_p = np.asarray(raw_p, float)
    q = raw_p.shape[1] - 1
    ref = np.clip(raw_p[:, [-1]], PROB_EPS, 1.0)
    z = np.log(np.clip(raw_p[:, :q], PROB_EPS, 1.0) / ref)
    b = np.asarray(cal["intercepts_nonref"], float)
    return _softmax_reference(float(cal["slope"]) * z + b)


def holm_familywise(pvals: dict[str, float], alpha: float = FAMILYWISE_ALPHA):
    """Holm step-down FWER. Missing/invalid callers must supply p=1.0."""
    clean = {str(k): min(1.0, max(0.0, float(v))) for k, v in pvals.items()}
    ordered = sorted(clean.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(ordered)
    rejected = {k: False for k in clean}
    adjusted = {}
    running = 0.0
    active = True
    for rank, (key, p) in enumerate(ordered, start=1):
        mult = m - rank + 1
        running = max(running, min(1.0, mult * p))
        adjusted[key] = running
        threshold = float(alpha) / mult
        if active and p <= threshold:
            rejected[key] = True
        else:
            active = False
    return {"rejected": rejected, "adjusted_p": adjusted, "alpha": float(alpha), "m": m}


def circular_block_positions(n_dates: int, block: int, *, rng: np.random.Generator) -> np.ndarray:
    """Sample ordered date positions in circular contiguous blocks until n_dates are produced."""
    n = int(n_dates)
    b = int(block)
    if n < 1 or b < 1:
        raise ValueError("n_dates and block must be >=1")
    out = []
    while len(out) < n:
        start = int(rng.integers(0, n))
        out.extend((start + j) % n for j in range(b))
    return np.asarray(out[:n], dtype=int)


def basic_bootstrap_one_sided_p(
    observed: float,
    boot_stats: Iterable[float],
    *,
    null: float,
    alternative: str,
) -> float:
    """Recentred basic-bootstrap one-sided p with plus-one correction."""
    b = np.asarray(list(boot_stats), float)
    b = b[np.isfinite(b)]
    if len(b) < 2 or not np.isfinite(observed):
        return 1.0
    dev = b - float(observed)
    t = float(observed) - float(null)
    if alternative == "lower":
        extreme = int(np.sum(dev <= t))
    elif alternative == "greater":
        extreme = int(np.sum(dev >= t))
    else:
        raise ValueError("alternative must be lower or greater")
    return float((1 + extreme) / (len(b) + 1))


def intersection_union_p(component_p: Iterable[float]) -> float:
    vals = [min(1.0, max(0.0, float(x))) for x in component_p]
    return 1.0 if not vals else max(vals)


def synthetic_validation() -> dict:
    rng = np.random.default_rng(20261006)

    # Exact penalty-scaling witness: house cycle fit divides lambda*w by n; TOI does not.
    n = 100
    w = 0.5
    house_penalty_grad = RIDGE_LAMBDA * w / n
    toi_penalty_grad = RIDGE_LAMBDA * w
    assert toi_penalty_grad == 0.5 and house_penalty_grad == 0.005

    X = rng.normal(size=(600, 3))
    p_true = _sigmoid(0.9 * X[:, 0] - 0.5 * X[:, 1] + 0.25)
    y = (rng.random(len(X)) < p_true).astype(float)
    Xz, mu, sd, zero = standardize_train(X)
    bfit = fit_binary_ridge(Xz, y)
    assert bfit.converged and bfit.grad_inf <= GRAD_TOL * 1.01
    bp = predict_binary(Xz, bfit)
    assert np.all((bp > 0) & (bp < 1))

    Xm = rng.normal(size=(700, 4))
    l1 = 0.8 * Xm[:, 0] - 0.3 * Xm[:, 1]
    l2 = -0.4 * Xm[:, 0] + 0.6 * Xm[:, 2]
    Pm = _softmax_reference(np.column_stack([l1, l2]))
    u = rng.random(len(Xm))
    cum = np.cumsum(Pm, axis=1)
    ym = (u[:, None] > cum).sum(axis=1).astype(int)
    Xmz, _, _, _ = standardize_train(Xm)
    mfit = fit_multinomial_ridge(Xmz, ym, classes=3)
    assert mfit.converged and mfit.grad_inf <= GRAD_TOL * 1.01
    mp = predict_multinomial(Xmz, mfit)
    assert np.max(np.abs(mp.sum(axis=1) - 1.0)) < 1e-12

    raw = np.clip(_sigmoid(0.65 * X[:, 0] - 0.15), PROB_EPS, 1 - PROB_EPS)
    cal = fit_binary_platt(raw, y)
    assert cal.get("estimable") and cal["slope"] > 0
    cp = apply_binary_platt(raw, cal)
    assert np.all((cp > 0) & (cp < 1))

    mcal = fit_multinomial_logistic_calibration(np.clip(mp, PROB_EPS, 1.0), ym)
    assert mcal.get("estimable") and mcal["slope"] > 0
    mcp = apply_multinomial_logistic_calibration(mp, mcal)
    assert np.max(np.abs(mcp.sum(axis=1) - 1.0)) < 1e-12

    h = holm_familywise({"a": 0.001, "b": 0.01, "c": 0.04, "blocked": 1.0}, alpha=0.05)
    assert h["rejected"]["a"] and h["rejected"]["b"]
    assert not h["rejected"]["c"] and not h["rejected"]["blocked"]

    r1 = np.random.default_rng(BOOT_SEED)
    r2 = np.random.default_rng(BOOT_SEED)
    pos1 = circular_block_positions(30, PRIMARY_BLOCK_SESSIONS, rng=r1)
    pos2 = circular_block_positions(30, PRIMARY_BLOCK_SESSIONS, rng=r2)
    assert np.array_equal(pos1, pos2)
    assert len(pos1) == 30

    p_iut = intersection_union_p([0.01, 0.03, 0.02])
    assert p_iut == 0.03

    return {
        "schema": "toi.r0.stat_contract.synthetic_validation.v1",
        "penalty_scaling": {
            "n": n,
            "w": w,
            "house_cycle_penalty_gradient_term": house_penalty_grad,
            "toi_required_penalty_gradient_term": toi_penalty_grad,
            "different": house_penalty_grad != toi_penalty_grad,
        },
        "binary_fit": {
            "converged": bfit.converged,
            "iterations": bfit.iterations,
            "objective": bfit.objective,
            "grad_inf": bfit.grad_inf,
        },
        "multinomial_fit": {
            "converged": mfit.converged,
            "iterations": mfit.iterations,
            "objective": mfit.objective,
            "grad_inf": mfit.grad_inf,
            "max_probability_sum_error": float(np.max(np.abs(mp.sum(axis=1) - 1.0))),
        },
        "binary_calibration": cal,
        "multinomial_calibration": mcal,
        "holm": h,
        "block_bootstrap": {
            "seed": BOOT_SEED,
            "block_sessions": PRIMARY_BLOCK_SESSIONS,
            "deterministic": bool(np.array_equal(pos1, pos2)),
            "first_positions": pos1[:12].tolist(),
        },
        "intersection_union_example_p": p_iut,
        "market_data_or_outcomes_read": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(synthetic_validation(), indent=2, sort_keys=True))
