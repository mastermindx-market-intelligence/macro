"""RESEARCH REFERENCE — NOT WIRED. Q16 delayed-feedback interval calibration harness.

VERDICT: REJECT (Q16, see research/quant_assessment_2026_10/Q16_delayed_interval_calibration/
VERDICT.md). On the single frozen 2015-2026 holdout (5 ETFs, 22-day log returns, 80%
intervals around the incumbent vol_forecast scale, 134 honest blocks) delayed-feedback
ACI had a pooled normalized interval score 2.2% WORSE than honest fixed split
calibration (block-bootstrap 95% CI +1.1% to +3.3%) and 0.7% worse than plain rolling
recalibration, despite passing the synthetic shift controls. The adaptive layer is
rejected; honest fixed calibration is retained. Nothing in this module is wired,
registered, scheduled or imported by any production path.

What this module is
-------------------
A pure-function stress harness plus an optional calibration residual adapter for an
EXISTING scale forecast (for example the incumbent ``engine.vol_forecast`` cone). It is
not a second forecasting model and it does not build a CQR program (that remains the
planned ANTICIPATION_ENGINE §5.4 work), and it does not touch the frozen CN-HAR-2
conformal registration, MRI-R30 interval recalibration, or any trial ledger.

Clocks
------
Origins are integer positions ``i = 0..n-1`` on a trading-day axis. A forecast emitted
at origin ``i`` with horizon ``h`` has a label that matures at position ``i + h`` and
becomes usable after a further ``avail_lag`` positions. An update performed at origin
``i`` may therefore consume only labels of origins ``j`` with
``j + h + avail_lag <= i``. Every runner returns the largest consumed origin per step so
the maturity invariant is auditable (requirement 1).

Methods
-------
* ``fixed``   — split-conformal: one quantile of normalized scores whose labels matured
                inside the training window, frozen thereafter.
* ``rolling`` — conformal quantile of the last ``window`` matured scores at level 1-alpha.
* ``aci``     — Adaptive Conformal Inference (Gibbs & Candès 2021) with DELAYED
                feedback: alpha_t is updated only when the error of origin ``i-delay``
                matures; the quantile is taken over the same matured rolling buffer at
                level 1-alpha_t, with alpha_t projected onto ``alpha_clip``.
* ``run_leaky_aci_diagnostic`` — the same update consuming the previous origin's error
                immediately (delay 1); it uses IMMATURE labels by construction and exists
                only to measure the size of the look-ahead a naive implementation gains.

Pure functions, bounded inputs, no I/O, no wall-clock reads, no registration.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

RESEARCH_ONLY = True
Q16_VERDICT = "REJECT"

#: Registrations this harness must never alter (requirement 6). Listed so a reader can
#: see the boundary; the module holds no handle to any of them.
PROTECTED_REGISTRATIONS: tuple[str, ...] = (
    "CN-HAR-2 conformal layer (cycle_masterplan PREREGISTRATION §18)",
    "HAR-1 cycle_pattern analog cone",
    "MRI-R30 release interval recalibration V1",
    "ANTICIPATION_ENGINE §5.4 planned CQR",
    "trial_ledger / calibration_hub / OA-3 qledger",
)

METHODS: tuple[str, ...] = ("fixed", "rolling", "aci")
MAX_N = 2_000_000
MAX_WINDOW = 100_000
MAX_HORIZON = 10_000


# ─────────────────────────────────────────────────────────────────────────────
# Input guards
# ─────────────────────────────────────────────────────────────────────────────

def _as_1d(x: Any, name: str) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-D")
    if arr.size > MAX_N:
        raise ValueError(f"{name} exceeds MAX_N={MAX_N}")
    return arr


def _check_alpha(alpha: float) -> float:
    a = float(alpha)
    if not (0.0 < a < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    return a


def _check_horizon(horizon: int, avail_lag: int = 0) -> int:
    h = int(horizon)
    lag = int(avail_lag)
    if h < 1 or h > MAX_HORIZON:
        raise ValueError("horizon must be in [1, MAX_HORIZON]")
    if lag < 0 or lag > MAX_HORIZON:
        raise ValueError("avail_lag must be in [0, MAX_HORIZON]")
    return h + lag


# ─────────────────────────────────────────────────────────────────────────────
# Maturity / scoring primitives
# ─────────────────────────────────────────────────────────────────────────────

def label_available(origin: int, horizon: int, cutoff: int, avail_lag: int = 0) -> bool:
    """True iff the label of ``origin`` is usable at position ``cutoff``."""
    delay = _check_horizon(horizon, avail_lag)
    return int(origin) + delay <= int(cutoff)


def matured_mask(n: int, horizon: int, cutoff: int, avail_lag: int = 0) -> np.ndarray:
    """Boolean mask over origins ``0..n-1``: label usable at ``cutoff``."""
    if n < 0 or n > MAX_N:
        raise ValueError("n out of range")
    delay = _check_horizon(horizon, avail_lag)
    idx = np.arange(int(n))
    return idx + delay <= int(cutoff)


def normalized_scores(y: Any, scale: Any, center: Any = 0.0) -> np.ndarray:
    """Signed normalized residual ``(y - center) / scale``; NaN where scale <= 0/NaN."""
    yy = _as_1d(y, "y")
    ss = np.broadcast_to(np.asarray(scale, dtype=float), yy.shape)
    cc = np.broadcast_to(np.asarray(center, dtype=float), yy.shape)
    out = np.full(yy.shape, np.nan)
    ok = np.isfinite(yy) & np.isfinite(ss) & np.isfinite(cc) & (ss > 0)
    out[ok] = (yy[ok] - cc[ok]) / ss[ok]
    return out


def conformal_quantile(scores: Any, level: float) -> float:
    """Finite-sample split-conformal quantile: the ceil((n+1)*level)-th order statistic
    of the finite scores (capped at the maximum so the interval stays finite)."""
    s = _as_1d(scores, "scores")
    s = s[np.isfinite(s)]
    n = s.size
    if n == 0:
        return float("nan")
    lv = float(level)
    if not (0.0 < lv < 1.0):
        raise ValueError("level must be in (0, 1)")
    k = int(math.ceil((n + 1) * lv))
    k = min(max(k, 1), n)
    return float(np.partition(s, k - 1)[k - 1])


def interval_metrics(q: Any, s: Any, alpha: float, scale: Any = 1.0) -> dict[str, np.ndarray]:
    """Per-origin coverage, width and Winkler interval score for the symmetric interval
    ``[-q, q] * scale`` around the centre, evaluated at signed normalized score ``s``.

    The interval score ``width + (2/alpha) * miss_distance`` makes an arbitrarily wide
    interval pay for its width, so coverage alone can never win (requirement 3).
    """
    a = _check_alpha(alpha)
    qq = _as_1d(q, "q")
    ss = _as_1d(s, "s")
    if qq.shape != ss.shape:
        raise ValueError("q and s must align")
    sc = np.broadcast_to(np.asarray(scale, dtype=float), qq.shape)
    ok = np.isfinite(qq) & np.isfinite(ss) & np.isfinite(sc)
    covered = np.full(qq.shape, np.nan)
    width = np.full(qq.shape, np.nan)
    score = np.full(qq.shape, np.nan)
    absd = np.abs(ss[ok])
    qo = qq[ok]
    covered[ok] = (absd <= qo).astype(float)
    width[ok] = 2.0 * qo * sc[ok]
    score[ok] = (2.0 * qo + (2.0 / a) * np.maximum(absd - qo, 0.0)) * sc[ok]
    return {"covered": covered, "width": width, "interval_score": score}


def summarize_metrics(m: dict[str, np.ndarray], mask: Any = None) -> dict[str, float]:
    """Coverage, mean width, mean interval score and row count over ``mask``."""
    cov = m["covered"]
    sel = np.isfinite(cov)
    if mask is not None:
        sel &= np.asarray(mask, dtype=bool)
    n = int(sel.sum())
    if n == 0:
        return {"n_rows": 0, "coverage": float("nan"), "mean_width": float("nan"),
                "mean_interval_score": float("nan")}
    return {"n_rows": n, "coverage": float(np.mean(cov[sel])),
            "mean_width": float(np.mean(m["width"][sel])),
            "mean_interval_score": float(np.mean(m["interval_score"][sel]))}


# ─────────────────────────────────────────────────────────────────────────────
# Delayed-feedback runners
# ─────────────────────────────────────────────────────────────────────────────

def fixed_split_quantile(abs_scores: Any, alpha: float, train_end: int, horizon: int,
                         avail_lag: int = 0) -> float:
    """Split-conformal quantile from origins whose labels matured by ``train_end``."""
    a = _check_alpha(alpha)
    s = _as_1d(abs_scores, "abs_scores")
    mask = matured_mask(s.size, horizon, int(train_end), avail_lag)
    return conformal_quantile(np.abs(s[mask]), 1.0 - a)


def run_delayed_calibration(abs_scores: Any, *, horizon: int, alpha: float, method: str,
                            gamma: float = 0.0, window: int = 504, min_calib: int = 252,
                            avail_lag: int = 0, q_fixed: float | None = None,
                            alpha_clip: tuple[float, float] = (0.005, 0.995),
                            _delay_override: int | None = None) -> dict[str, np.ndarray]:
    """Run one calibration method online over origins with delayed label maturity.

    ``abs_scores[i]`` is the absolute normalized score of origin ``i`` (NaN if the
    forecast or label is unavailable). Returns per-origin issued quantile ``q``,
    the ACI state ``alpha_t``, the miss indicator ``err`` and ``consumed_max`` — the
    largest origin whose label any update at step ``i`` used (-1 if none).
    """
    a = _check_alpha(alpha)
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    s = np.abs(_as_1d(abs_scores, "abs_scores"))
    n = s.size
    delay = _check_horizon(horizon, avail_lag) if _delay_override is None else int(_delay_override)
    if delay < 1:
        raise ValueError("delay must be >= 1")
    w = int(window)
    if w < 2 or w > MAX_WINDOW:
        raise ValueError("window out of range")
    mc = max(1, min(int(min_calib), w))
    g = float(gamma)
    if not (0.0 <= g <= 1.0):
        raise ValueError("gamma must be in [0, 1]")
    lo_c, hi_c = float(alpha_clip[0]), float(alpha_clip[1])
    if not (0.0 < lo_c < hi_c < 1.0):
        raise ValueError("alpha_clip must satisfy 0 < lo < hi < 1")
    if method == "fixed" and (q_fixed is None or not np.isfinite(q_fixed)):
        raise ValueError("fixed method needs a finite q_fixed")

    q = np.full(n, np.nan)
    alpha_t_arr = np.full(n, np.nan)
    err = np.full(n, np.nan)
    consumed = np.full(n, -1, dtype=np.int64)
    ring = np.empty(w)
    count = 0
    head = 0
    alpha_t = a
    last_consumed = -1
    for i in range(n):
        j = i - delay
        if j >= 0:
            last_consumed = j
            sj = s[j]
            if np.isfinite(sj):
                ring[head] = sj
                head = (head + 1) % w
                count = min(count + 1, w)
            if method == "aci" and np.isfinite(err[j]):
                alpha_t = min(max(alpha_t + g * (a - err[j]), lo_c), hi_c)
        consumed[i] = last_consumed
        if method == "fixed":
            qi = float(q_fixed)
        elif count >= mc:
            level = 1.0 - (alpha_t if method == "aci" else a)
            qi = conformal_quantile(ring[:count], level)
        else:
            qi = float("nan")
        q[i] = qi
        alpha_t_arr[i] = alpha_t
        if np.isfinite(qi) and np.isfinite(s[i]):
            err[i] = 1.0 if s[i] > qi else 0.0
    return {"q": q, "alpha_t": alpha_t_arr, "err": err, "consumed_max": consumed,
            "delay": np.asarray(delay)}


def run_leaky_aci_diagnostic(abs_scores: Any, *, alpha: float, gamma: float,
                             window: int = 504, min_calib: int = 252) -> dict[str, Any]:
    """INVALID-BY-CONSTRUCTION diagnostic: ACI that consumes the previous origin's
    label immediately (delay 1) even though the true horizon has not elapsed. Used only
    to size the look-ahead advantage; flagged ``uses_immature_labels=True``."""
    out: dict[str, Any] = dict(run_delayed_calibration(
        abs_scores, horizon=1, alpha=alpha, method="aci", gamma=gamma, window=window,
        min_calib=min_calib, _delay_override=1))
    out["uses_immature_labels"] = True
    return out


def maturity_violations(consumed_max: Any, horizon: int, avail_lag: int = 0) -> int:
    """Count steps whose consumed label had not matured (requirement 1 audit)."""
    delay = _check_horizon(horizon, avail_lag)
    c = np.asarray(consumed_max, dtype=np.int64)
    idx = np.arange(c.size)
    used = c >= 0
    return int(np.sum(c[used] + delay > idx[used]))


def tune_gamma(abs_scores: Any, *, horizon: int, alpha: float, gammas: tuple[float, ...],
               train_end: int, tune_start: int, window: int = 504, min_calib: int = 252,
               avail_lag: int = 0) -> dict[str, Any]:
    """Pick the ACI step size inside the training window only.

    Scores of origins whose labels mature after ``train_end`` are masked before the
    run, so tuning cannot see any test label; the objective is the mean normalized
    interval score over matured training origins ``[tune_start, train_end - delay]``.
    Ties resolve to the smaller gamma.
    """
    a = _check_alpha(alpha)
    delay = _check_horizon(horizon, avail_lag)
    s = np.abs(_as_1d(abs_scores, "abs_scores")).copy()
    n = s.size
    te = int(train_end)
    mature = matured_mask(n, horizon, te, avail_lag)
    s[~mature] = np.nan
    s = s[: min(n, te + 1)]
    lo = int(tune_start)
    hi = te - delay
    if hi <= lo:
        raise ValueError("tuning window empty")
    table = []
    for g in sorted(float(x) for x in gammas):
        r = run_delayed_calibration(s, horizon=horizon, alpha=a, method="aci", gamma=g,
                                    window=window, min_calib=min_calib, avail_lag=avail_lag)
        m = interval_metrics(r["q"], s, a)
        sel = np.zeros(s.size, dtype=bool)
        sel[lo: hi + 1] = True
        summ = summarize_metrics(m, sel)
        table.append({"gamma": g, **summ})
    finite = [t for t in table if np.isfinite(t["mean_interval_score"])]
    if not finite:
        raise ValueError("no finite tuning score")
    best = min(finite, key=lambda t: (t["mean_interval_score"], t["gamma"]))
    return {"gamma": best["gamma"], "table": table}


# ─────────────────────────────────────────────────────────────────────────────
# Honest evidence accounting (requirement 2)
# ─────────────────────────────────────────────────────────────────────────────

def honest_block_count(origins: Any, horizon: int) -> int:
    """Number of non-overlapping outcome windows among ``origins`` (greedy, sorted).
    Overlapping daily h-step forecasts collapse to about n/h independent outcomes."""
    h = _check_horizon(horizon)
    o = np.unique(np.asarray(origins, dtype=np.int64))
    count = 0
    nxt = -(10 ** 18)
    for v in o:
        if v >= nxt:
            count += 1
            nxt = v + h
    return count


def collapse_repeated_forecasts(outcome_ids: Any, values: Any) -> dict[Any, float]:
    """Average repeated forecasts that target the same eventual outcome so each outcome
    contributes one unit of evidence."""
    ids = list(outcome_ids)
    vals = _as_1d(values, "values")
    if len(ids) != vals.size:
        raise ValueError("outcome_ids and values must align")
    acc: dict[Any, list[float]] = {}
    for k, v in zip(ids, vals):
        if np.isfinite(v):
            acc.setdefault(k, []).append(float(v))
    return {k: float(np.mean(v)) for k, v in acc.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Dependence-aware uncertainty
# ─────────────────────────────────────────────────────────────────────────────

def circular_block_bootstrap(num: Any, den: Any | None = None, *, block_len: int,
                             n_boot: int = 2000, seed: int = 0,
                             level: float = 0.95) -> dict[str, float]:
    """Circular moving-block bootstrap on a date-ordered series.

    Without ``den`` it bootstraps the mean of ``num``; with ``den`` it bootstraps the
    ratio ``mean(num) / mean(den)`` resampling identical blocks for both. NaN rows are
    dropped before resampling (the caller passes a contiguous date axis).
    """
    x = _as_1d(num, "num")
    d = None if den is None else _as_1d(den, "den")
    ok = np.isfinite(x) if d is None else (np.isfinite(x) & np.isfinite(d))
    x = x[ok]
    if d is not None:
        d = d[ok]
    n = x.size
    L = int(block_len)
    B = int(n_boot)
    if n < 2 or L < 1 or B < 1 or B > 100_000:
        raise ValueError("bad bootstrap inputs")
    L = min(L, n)
    rng = np.random.default_rng(int(seed))
    nb = int(math.ceil(n / L))
    stats = np.empty(B)
    offs = np.arange(L)
    for b in range(B):
        starts = rng.integers(0, n, size=nb)
        idx = ((starts[:, None] + offs[None, :]) % n).ravel()[:n]
        if d is None:
            stats[b] = x[idx].mean()
        else:
            stats[b] = x[idx].mean() / d[idx].mean()
    point = float(x.mean()) if d is None else float(x.mean() / d.mean())
    tail = (1.0 - float(level)) / 2.0
    return {"point": point, "lo": float(np.quantile(stats, tail)),
            "hi": float(np.quantile(stats, 1.0 - tail)), "n": int(n),
            "block_len": int(L), "n_blocks": int(nb), "n_boot": int(B)}


def newey_west_se(x: Any, lags: int) -> float:
    """Bartlett-kernel HAC standard error of the mean."""
    v = _as_1d(x, "x")
    v = v[np.isfinite(v)]
    n = v.size
    if n < 2:
        return float("nan")
    e = v - v.mean()
    L = max(0, min(int(lags), n - 1))
    s = float(e @ e) / n
    for k in range(1, L + 1):
        wk = 1.0 - k / (L + 1.0)
        s += 2.0 * wk * float(e[k:] @ e[:-k]) / n
    return float(math.sqrt(max(s, 0.0) / n))


# ─────────────────────────────────────────────────────────────────────────────
# Regime support disclosure (requirement 5)
# ─────────────────────────────────────────────────────────────────────────────

def regime_support(labels: Any, covered: Any, origins: Any, horizon: int,
                   min_blocks: int = 20) -> dict[str, dict[str, Any]]:
    """Per-regime row count, honest non-overlapping blocks and coverage.

    Never asserts conditional coverage: every row carries
    ``conditional_coverage_claim=False`` and cells under ``min_blocks`` are flagged
    ``support_ok=False``.
    """
    lab = np.asarray(list(labels), dtype=object)
    cov = _as_1d(covered, "covered")
    org = np.asarray(origins, dtype=np.int64)
    if not (lab.size == cov.size == org.size):
        raise ValueError("inputs must align")
    out: dict[str, dict[str, Any]] = {}
    for key in sorted({str(v) for v in lab}):
        sel = np.array([str(v) == key for v in lab]) & np.isfinite(cov)
        nb = honest_block_count(org[sel], horizon) if sel.any() else 0
        out[key] = {"n_rows": int(sel.sum()), "honest_blocks": int(nb),
                    "coverage": float(np.mean(cov[sel])) if sel.any() else float("nan"),
                    "support_ok": bool(nb >= int(min_blocks)),
                    "conditional_coverage_claim": False}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic controls (requirement 4)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_overlapping_scores(n: int, horizon: int, *, shift_at: int | None = None,
                                shift_factor: float = 1.0, df: float = 5.0,
                                seed: int = 0) -> np.ndarray:
    """Signed normalized scores for overlapping h-step sums of daily shocks.

    Daily shocks are unit-variance Student-t; after ``shift_at`` their scale is
    multiplied by ``shift_factor`` while the forecast scale stays at the pre-shift value
    (a stale predictor). The last ``horizon`` origins are NaN (never mature).
    """
    nn = int(n)
    h = _check_horizon(horizon)
    if nn < 2 * h or nn > MAX_N:
        raise ValueError("n out of range")
    rng = np.random.default_rng(int(seed))
    dfv = float(df)
    if dfv <= 2.0:
        raise ValueError("df must exceed 2")
    e = rng.standard_t(dfv, size=nn + h) / math.sqrt(dfv / (dfv - 2.0))
    scale = np.ones(nn + h)
    if shift_at is not None:
        scale[int(shift_at) + 1:] = float(shift_factor)
    e = e * scale
    c = np.concatenate([[0.0], np.cumsum(e)])
    y = c[np.arange(nn) + h + 1] - c[np.arange(nn) + 1]
    out = y / math.sqrt(h)
    out[nn - h:] = np.nan
    return out


def control_experiment(*, scenario: str, n: int = 6000, horizon: int = 22,
                       alpha: float = 0.2, n_train: int = 3000, window: int = 504,
                       gammas: tuple[float, ...] = (0.001, 0.005, 0.01, 0.02, 0.05),
                       seed: int = 0) -> dict[str, Any]:
    """One replication of a pre-registered control scenario.

    ``stationary``  — no shift; adaptation can only chase noise.
    ``shift_up``    — shock scale doubles at the middle of the test segment.
    ``shift_down``  — shock scale halves at the middle of the test segment.
    Returns test and post-shift summaries for fixed, rolling and delayed ACI, plus the
    leaky diagnostic.
    """
    factors = {"stationary": None, "shift_up": 2.0, "shift_down": 0.5}
    if scenario not in factors:
        raise ValueError("unknown scenario")
    h = _check_horizon(horizon)
    a = _check_alpha(alpha)
    shift_at = None if factors[scenario] is None else n_train + (n - n_train) // 2
    s = simulate_overlapping_scores(n, h, shift_at=shift_at,
                                    shift_factor=factors[scenario] or 1.0, seed=seed)
    abs_s = np.abs(s)
    train_end = n_train - 1
    qf = fixed_split_quantile(abs_s, a, train_end, h)
    tg = tune_gamma(abs_s, horizon=h, alpha=a, gammas=gammas, train_end=train_end,
                    tune_start=min(window, train_end // 2), window=window)
    runs = {
        "fixed": run_delayed_calibration(abs_s, horizon=h, alpha=a, method="fixed", q_fixed=qf,
                                         window=window),
        "rolling": run_delayed_calibration(abs_s, horizon=h, alpha=a, method="rolling",
                                           window=window),
        "aci": run_delayed_calibration(abs_s, horizon=h, alpha=a, method="aci",
                                       gamma=tg["gamma"], window=window),
        "aci_leaky": run_leaky_aci_diagnostic(abs_s, alpha=a, gamma=tg["gamma"], window=window),
    }
    idx = np.arange(n)
    test = idx > train_end
    post = test if shift_at is None else (idx > shift_at + h)
    res: dict[str, Any] = {"scenario": scenario, "gamma": tg["gamma"], "q_fixed": qf,
                           "shift_at": shift_at}
    for k, r in runs.items():
        m = interval_metrics(r["q"], s, a)
        res[k] = {"test": summarize_metrics(m, test), "post": summarize_metrics(m, post)}
    res["maturity_violations_aci"] = maturity_violations(runs["aci"]["consumed_max"], h)
    return res


def discrimination_verdict(reps: list[dict[str, Any]], *, alpha: float = 0.2,
                           noise_tol: float = 0.02, cov_gain: float = 0.05) -> dict[str, Any]:
    """Pre-registered control criteria over replications of the three scenarios.

    stationary: mean ACI interval score <= (1 + noise_tol) * fixed (no noise chasing).
    shift_up:   post-shift ACI coverage gap at least ``cov_gain`` smaller than fixed and
                ACI interval score lower.
    shift_down: post-shift ACI mean width lower than fixed and ACI interval score lower.
    """
    a = _check_alpha(alpha)
    by: dict[str, list[dict[str, Any]]] = {}
    for r in reps:
        by.setdefault(r["scenario"], []).append(r)

    def _mean(sc: str, meth: str, seg: str, key: str) -> float:
        v = [x[meth][seg][key] for x in by.get(sc, [])]
        return float(np.mean(v)) if v else float("nan")

    st_ratio = _mean("stationary", "aci", "test", "mean_interval_score") / \
        _mean("stationary", "fixed", "test", "mean_interval_score")
    up_gap_aci = abs(_mean("shift_up", "aci", "post", "coverage") - (1 - a))
    up_gap_fix = abs(_mean("shift_up", "fixed", "post", "coverage") - (1 - a))
    up_is = _mean("shift_up", "aci", "post", "mean_interval_score") < \
        _mean("shift_up", "fixed", "post", "mean_interval_score")
    dn_w = _mean("shift_down", "aci", "post", "mean_width") < \
        _mean("shift_down", "fixed", "post", "mean_width")
    dn_is = _mean("shift_down", "aci", "post", "mean_interval_score") < \
        _mean("shift_down", "fixed", "post", "mean_interval_score")
    crit = {
        "stationary_no_noise_chasing": bool(st_ratio <= 1.0 + noise_tol),
        "shift_up_coverage_recovers": bool(up_gap_aci <= up_gap_fix - cov_gain and up_is),
        "shift_down_sharpens": bool(dn_w and dn_is),
    }
    return {"stationary_is_ratio": st_ratio, "shift_up_gap_aci": up_gap_aci,
            "shift_up_gap_fixed": up_gap_fix, "criteria": crit,
            "controls_discriminate": bool(all(crit.values()))}


__all__ = [
    "RESEARCH_ONLY", "Q16_VERDICT", "PROTECTED_REGISTRATIONS", "METHODS",
    "label_available", "matured_mask", "normalized_scores", "conformal_quantile",
    "interval_metrics", "summarize_metrics", "fixed_split_quantile",
    "run_delayed_calibration", "run_leaky_aci_diagnostic", "maturity_violations",
    "tune_gamma", "honest_block_count", "collapse_repeated_forecasts",
    "circular_block_bootstrap", "newey_west_se", "regime_support",
    "simulate_overlapping_scores", "control_experiment", "discrimination_verdict",
]
