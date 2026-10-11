"""RESEARCH REFERENCE — NOT WIRED. Fitted, leakage-controlled log-HAR forward-variance challenger (Q07).

Verdict of the pre-registered study
(research/quant_assessment_2026_10/Q07_fitted_har_volatility/VERDICT.md): see that file;
the verdict recorded there is the only authority, and whatever it says, this module changes
nothing in production. It is a pure-function reference implementation of the challenger and
its simple controls, kept so an auditor can re-derive every number in the study.

What it is
----------
A point forecast of the forward mean squared daily close-to-close log return over the next
``h`` sessions (label ``DAILY_CC_MSR``), produced by a log-HAR regression (Corsi 2009 form,
components 1/5/22 sessions) fitted per asset on an expanding window whose training targets
have fully matured by the fit cutoff, back-transformed with a training-residual smearing
factor (Duan 1983). Simple controls: the incumbent equal-weight blend of
``engine.vol_forecast.har_vol`` (re-implemented here byte-for-byte in behaviour, never
imported), a 22-session trailing mean square, a RiskMetrics EWMA (lambda 0.94), and the
incumbent blend rescaled by one training-only level factor.

What it is NOT
--------------
* Not wired: nothing imports it; it registers nothing, schedules nothing, gates nothing.
* Not a cone, probability, sizing, budget or default change (requirement 6):
  ``production_effects`` returns all-False for every verdict, including KEEP.
* Not a high-frequency integrated-variance study: the target is a DAILY close-to-close
  proxy and every target carries its label; mixing labels raises (requirement 3).

Information discipline
----------------------
A forecast stamped at session ``s`` uses returns through ``s`` and coefficients fitted at the
latest refit cutoff ``c <= s``. A fit at cutoff ``c`` uses only rows ``t`` with ``t + h <= c``,
i.e. whose forward window has closed by the cutoff (requirements 1 and 2). All functions are
pure: no I/O, no clock reads, no global state; inputs are bounded by ``MAX_ROWS``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

RESEARCH_ONLY = True

LABEL_DAILY_CC = "DAILY_CC_MSR"
INCUMBENT_LAGS = (2, 5, 22, 66)
HAR_COMPONENTS = (1, 5, 22)
EWMA_LAMBDA = 0.94
PERSISTENCE_WINDOW = 22
DEFAULT_FLOOR = 1e-8
FLOOR_SENSITIVITY = (1e-10, 1e-8, 1e-6)
DEFAULT_REFIT_EVERY = 21
DEFAULT_MIN_TRAIN = 504
MAX_ROWS = 50_000
VERDICTS = ("KEEP", "REJECT", "INSUFFICIENT_DATA")


class LabelMismatchError(ValueError):
    """Raised when variance labels of different measurement families would be mixed."""


# --------------------------------------------------------------------------- validation
def _validate_series(x: pd.Series, name: str) -> pd.Series:
    if not isinstance(x, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    if len(x) > MAX_ROWS:
        raise ValueError(f"{name} has {len(x)} rows > MAX_ROWS={MAX_ROWS}")
    if not x.index.is_unique:
        raise ValueError(f"{name} index must be unique")
    if not x.index.is_monotonic_increasing:
        raise ValueError(f"{name} index must be increasing (chronological)")
    return x.astype(float)


def log_returns(close: pd.Series) -> pd.Series:
    """Daily close-to-close log returns; first row NaN."""
    c = _validate_series(close, "close")
    if (c.dropna() <= 0).any():
        raise ValueError("close must be strictly positive")
    return np.log(c).diff()


# --------------------------------------------------------------------------- incumbent
def incumbent_blend_vol(close: pd.Series, lags: tuple[int, ...] = INCUMBENT_LAGS) -> pd.Series:
    """Re-implementation of ``engine.vol_forecast.har_vol`` (daily sd, simple returns, ddof=0)."""
    c = _validate_series(close, "close")
    ret = c.pct_change(fill_method=None)
    comps = []
    for lag in lags:
        win = max(2, int(lag))
        comps.append(ret.rolling(win, min_periods=min(win, max(2, win // 2))).std(ddof=0))
    return pd.concat(comps, axis=1).mean(axis=1)


# --------------------------------------------------------------------------- controls
def trailing_msr(r: pd.Series, window: int) -> pd.Series:
    """Trailing mean of squared returns over ``window`` sessions ending at t (inclusive)."""
    r = _validate_series(r, "r")
    window = int(window)
    if window < 1:
        raise ValueError("window must be >= 1")
    return r.pow(2).rolling(window, min_periods=window).mean()


def ewma_variance(r: pd.Series, lam: float = EWMA_LAMBDA, seed_window: int = PERSISTENCE_WINDOW) -> pd.Series:
    """RiskMetrics EWMA of squared returns; value at t uses returns through t only."""
    r = _validate_series(r, "r")
    if not 0.0 < lam < 1.0:
        raise ValueError("lam must be in (0, 1)")
    x = r.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    seen: list[float] = []
    state = math.nan
    for i, v in enumerate(x):
        if math.isnan(state):
            if not math.isnan(v):
                seen.append(v * v)
                if len(seen) >= seed_window:
                    state = float(np.mean(seen[-seed_window:]))
                    out[i] = state
            continue
        if not math.isnan(v):
            state = lam * state + (1.0 - lam) * v * v
        out[i] = state
    return pd.Series(out, index=r.index)


# --------------------------------------------------------------------------- target
@dataclass(frozen=True)
class LabeledTarget:
    values: pd.Series
    label: str
    horizon: int


def forward_target(r: pd.Series, h: int, label: str = LABEL_DAILY_CC) -> LabeledTarget:
    """y_t = mean(r_{t+1}^2 .. r_{t+h}^2); NaN unless all h forward returns exist."""
    if label != LABEL_DAILY_CC:
        raise LabelMismatchError(f"this module only builds {LABEL_DAILY_CC!r} targets, got {label!r}")
    r = _validate_series(r, "r")
    h = int(h)
    if h < 1:
        raise ValueError("h must be >= 1")
    fwd = r.pow(2).rolling(h, min_periods=h).mean().shift(-h)
    return LabeledTarget(values=fwd, label=label, horizon=h)


def require_label(target: LabeledTarget, expected: str = LABEL_DAILY_CC) -> pd.Series:
    if not isinstance(target, LabeledTarget):
        raise LabelMismatchError("unlabelled target: variance labels must be explicit")
    if target.label != expected:
        raise LabelMismatchError(f"target label {target.label!r} != expected {expected!r}")
    return target.values


def assert_single_label(targets: list[LabeledTarget]) -> str:
    labels = {t.label for t in targets}
    if len(labels) != 1:
        raise LabelMismatchError(f"mixed variance labels {sorted(labels)}")
    return labels.pop()


# --------------------------------------------------------------------------- HAR
def har_features(r: pd.Series, components: tuple[int, ...] = HAR_COMPONENTS,
                 floor: float = DEFAULT_FLOOR) -> pd.DataFrame:
    """log(max(trailing mean square over k sessions, floor)) for each component k."""
    if floor <= 0:
        raise ValueError("floor must be positive")
    cols = {}
    for k in components:
        m = trailing_msr(r, k)
        cols[f"logrv_{k}"] = np.log(np.maximum(m, floor)).where(m.notna())
    return pd.DataFrame(cols, index=r.index)


@dataclass(frozen=True)
class HarFit:
    coef: tuple[float, ...]
    smear: float
    n_train: int
    cutoff_pos: int


def training_mask(n: int, cutoff_pos: int, h: int, valid: np.ndarray) -> np.ndarray:
    """Rows usable for a fit at ``cutoff_pos``: forward window closed (t + h <= cutoff) and valid."""
    idx = np.arange(n)
    return (idx + int(h) <= int(cutoff_pos)) & np.asarray(valid, dtype=bool)


def fit_log_har(features: np.ndarray, target: np.ndarray, cutoff_pos: int, h: int,
                floor: float = DEFAULT_FLOOR, window: int | None = None,
                min_train: int = DEFAULT_MIN_TRAIN) -> HarFit | None:
    """OLS of log(max(y, floor)) on [1, features] over matured rows; Duan smearing on residuals."""
    X = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    if X.ndim != 2 or len(X) != len(y):
        raise ValueError("features must be 2-D with len(target) rows")
    valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
    m = training_mask(len(y), cutoff_pos, h, valid)
    rows = np.flatnonzero(m)
    if window is not None:
        rows = rows[-int(window):]
    if len(rows) < max(int(min_train), X.shape[1] + 2):
        return None
    A = np.column_stack([np.ones(len(rows)), X[rows]])
    z = np.log(np.maximum(y[rows], floor))
    beta, *_ = np.linalg.lstsq(A, z, rcond=None)
    resid = z - A @ beta
    smear = float(np.mean(np.exp(resid)))
    return HarFit(coef=tuple(float(b) for b in beta), smear=smear, n_train=int(len(rows)),
                  cutoff_pos=int(cutoff_pos))


def predict_log_har(fit: HarFit, features_row: np.ndarray) -> float:
    x = np.asarray(features_row, dtype=float)
    if not np.isfinite(x).all():
        return math.nan
    return float(math.exp(fit.coef[0] + float(np.dot(fit.coef[1:], x))) * fit.smear)


def cutoff_grid(n: int, refit_every: int = DEFAULT_REFIT_EVERY) -> np.ndarray:
    return np.arange(0, int(n), int(refit_every))


def har_forecast_path(r: pd.Series, h: int, refit_every: int = DEFAULT_REFIT_EVERY,
                      components: tuple[int, ...] = HAR_COMPONENTS, floor: float = DEFAULT_FLOOR,
                      window: int | None = None, min_train: int = DEFAULT_MIN_TRAIN) -> pd.DataFrame:
    """Walk-forward forecasts: at each cutoff c refit, then forecast sessions c..c+refit_every-1."""
    r = _validate_series(r, "r")
    feats = har_features(r, components, floor)
    y = require_label(forward_target(r, h)).to_numpy()
    X = feats.to_numpy()
    n = len(r)
    fc = np.full(n, np.nan)
    cpos = np.full(n, -1, dtype=int)
    ntr = np.zeros(n, dtype=int)
    for c in cutoff_grid(n, refit_every):
        fit = fit_log_har(X, y, c, h, floor=floor, window=window, min_train=min_train)
        if fit is None:
            continue
        for s in range(c, min(n, c + refit_every)):
            fc[s] = predict_log_har(fit, X[s])
            cpos[s] = c
            ntr[s] = fit.n_train
    return pd.DataFrame({"forecast": fc, "cutoff_pos": cpos, "n_train": ntr}, index=r.index)


def scaled_forecast_path(f: pd.Series, target: LabeledTarget, h: int,
                         refit_every: int = DEFAULT_REFIT_EVERY,
                         min_train: int = DEFAULT_MIN_TRAIN) -> pd.Series:
    """One-parameter level recalibration k = sum(y)/sum(f) over matured rows at each cutoff."""
    y = require_label(target).to_numpy()
    fv = np.asarray(f, dtype=float)
    n = len(fv)
    out = np.full(n, np.nan)
    valid = np.isfinite(fv) & np.isfinite(y) & (fv > 0)
    for c in cutoff_grid(n, refit_every):
        rows = np.flatnonzero(training_mask(n, c, h, valid))
        if len(rows) < min_train:
            continue
        k = float(np.sum(y[rows]) / np.sum(fv[rows]))
        seg = slice(c, min(n, c + refit_every))
        out[seg] = fv[seg] * k
    return pd.Series(out, index=f.index)


def empirical_interval_path(f: pd.Series, target: LabeledTarget, h: int, q: tuple[float, float] = (0.1, 0.9),
                            refit_every: int = DEFAULT_REFIT_EVERY, min_train: int = DEFAULT_MIN_TRAIN,
                            floor: float = DEFAULT_FLOOR) -> pd.DataFrame:
    """Variance-scale interval f*exp(quantiles of training log(y/f)), matured rows only."""
    y = require_label(target).to_numpy()
    fv = np.asarray(f, dtype=float)
    n = len(fv)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    valid = np.isfinite(fv) & np.isfinite(y)
    lr = np.log(np.maximum(y, floor)) - np.log(np.maximum(fv, floor))
    for c in cutoff_grid(n, refit_every):
        rows = np.flatnonzero(training_mask(n, c, h, valid))
        if len(rows) < min_train:
            continue
        ql, qh = np.quantile(lr[rows], q)
        seg = slice(c, min(n, c + refit_every))
        lo[seg] = fv[seg] * math.exp(ql)
        hi[seg] = fv[seg] * math.exp(qh)
    return pd.DataFrame({"lo": lo, "hi": hi}, index=f.index)


# --------------------------------------------------------------------------- losses
def qlike(y, f, floor: float = DEFAULT_FLOOR):
    """QLIKE = y/f - log(y/f) - 1 on floored positive variances; 0 iff y == f."""
    if floor <= 0:
        raise ValueError("floor must be positive")
    yy = np.maximum(np.asarray(y, dtype=float), floor)
    ff = np.maximum(np.asarray(f, dtype=float), floor)
    ratio = yy / ff
    return ratio - np.log(ratio) - 1.0


def log_loss(y, f, floor: float = DEFAULT_FLOOR):
    yy = np.maximum(np.asarray(y, dtype=float), floor)
    ff = np.maximum(np.asarray(f, dtype=float), floor)
    return (np.log(yy) - np.log(ff)) ** 2


def abs_vol_loss(y, f):
    return np.abs(np.sqrt(np.maximum(np.asarray(y, dtype=float), 0.0))
                  - np.sqrt(np.maximum(np.asarray(f, dtype=float), 0.0)))


def floor_sensitivity(y, forecasts: dict[str, np.ndarray], floors: tuple[float, ...] = FLOOR_SENSITIVITY) -> dict:
    out: dict = {}
    for fl in floors:
        out[repr(fl)] = {name: float(np.nanmean(qlike(y, f, fl))) for name, f in forecasts.items()}
    return out


# --------------------------------------------------------------------------- uncertainty
def circular_block_indices(n: int, block_len: int, n_boot: int, seed: int) -> np.ndarray:
    if n < 1 or block_len < 1:
        raise ValueError("n and block_len must be >= 1")
    rng = np.random.default_rng(int(seed))
    n_blocks = -(-n // block_len)
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offs = np.arange(block_len)
    idx = (starts[:, :, None] + offs[None, None, :]) % n
    return idx.reshape(n_boot, -1)[:, :n]


def paired_block_bootstrap(loss_ctrl: np.ndarray, loss_chal: np.ndarray, block_len: int,
                           n_boot: int = 2000, seed: int = 20261008, alpha: float = 0.05) -> dict:
    """Paired CBB over a date-ordered series of per-date losses (dates resampled jointly)."""
    a = np.asarray(loss_ctrl, dtype=float)
    b = np.asarray(loss_chal, dtype=float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("paired 1-D arrays required")
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    n = len(a)
    idx = circular_block_indices(n, block_len, n_boot, seed)
    ma, mb = a[idx].mean(axis=1), b[idx].mean(axis=1)
    d = ma - mb
    rel = 1.0 - mb / ma
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    return {
        "n_dates": int(n),
        "block_len": int(block_len),
        "honest_n_blocks": int(n // block_len),
        "mean_ctrl": float(a.mean()),
        "mean_chal": float(b.mean()),
        "mean_diff": float(a.mean() - b.mean()),
        "diff_ci": [float(np.quantile(d, lo_q)), float(np.quantile(d, hi_q))],
        "rel_improvement": float(1.0 - b.mean() / a.mean()),
        "rel_ci": [float(np.quantile(rel, lo_q)), float(np.quantile(rel, hi_q))],
        "p_boot_le0": float(np.mean(d <= 0)),
    }


def newey_west_tstat(d: np.ndarray, lag: int) -> float:
    """Diebold-Mariano style t-stat of mean(d) with Bartlett-kernel HAC variance."""
    x = np.asarray(d, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return math.nan
    e = x - x.mean()
    lrv = float(e @ e) / n
    for k in range(1, min(int(lag), n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        lrv += 2.0 * w * float(e[k:] @ e[:-k]) / n
    if lrv <= 0:
        return math.nan
    return float(x.mean() / math.sqrt(lrv / n))


# --------------------------------------------------------------------------- decision
def decide(comparisons: dict[str, dict], bar: float, n_blocks: int, min_blocks: int,
           n_assets: int, min_assets: int, floor_flip: bool) -> str:
    """KEEP only if the challenger beats EVERY control by >= bar with diff CI lower bound > 0."""
    if n_blocks < min_blocks or n_assets < min_assets or not comparisons:
        return "INSUFFICIENT_DATA"
    for res in comparisons.values():
        if not (res["rel_improvement"] >= bar and res["diff_ci"][0] > 0):
            return "REJECT"
    if floor_flip:
        return "REJECT"
    return "KEEP"


def production_effects(verdict: str) -> dict[str, bool]:
    """Research success alone changes nothing (requirement 6); every effect is False."""
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}")
    return {
        "cone_probability_changed": False,
        "model_promoted": False,
        "portfolio_budget_changed": False,
        "live_forecast_default_changed": False,
    }
