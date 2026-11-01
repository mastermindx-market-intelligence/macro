from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED. Microstructure-noise-aware realized variance (Q15).

Verdict (research/quant_assessment_2026_10/Q15_noise_robust_realized_variance/VERDICT.md):
REJECT the noise-aware label upgrade at the only admitted intraday resolution
(Coinbase BTC-USD hourly candles). On that tape the Parzen realized kernel gives no
practically meaningful reliability gain over fixed-interval hourly RV; the
falsifier applies, so the simple fixed-interval proxy is retained with its stated
limitation and no high-frequency precision is manufactured. This module stays a
research reference for the day tick/quote data is admitted by its owner
(TP1 #8660). Nothing imports it; it registers, schedules, gates and forecasts
nothing (RESEARCH_ONLY = True, ACTIVATION all False).

Quadratic-variation convention (frozen)
---------------------------------------
Target = integrated variance IV = int sigma_t^2 dt of the efficient LOG price over a
declared window, in log-return-squared units (not annualised, not percent). The
observed log price is Y_j = X(t_j) + u_j with u_j i.i.d. noise of variance omega^2
(bid/ask bounce, rounding). Under that model fixed-interval RV on n returns has
bias 2*n*omega^2 and is NOT economic variance.

Estimators (pure functions on numpy arrays; no I/O, no wall clock)
-------------------------------------------------------------------
* ``realized_variance``       fixed-interval / tick RV (simple control).
* ``realized_kernel``         non-flat-top Parzen realized kernel (BNHLS 2008/2009),
                              the ONE primary noise-aware estimator.
* ``bnhls_bandwidth``         H* = c* xi^(4/5) n^(3/5), c* = 3.5134 (Parzen),
                              xi^2 = omega^2 / IV.
* ``preaveraged_variance``    Jacod-Li-Mykland-Podolskij-Vetter pre-averaging,
                              g(x) = min(x, 1-x), cross-check only.
* ``bipower_variation`` / ``jump_decomposition``  QUALIFIED jump-robust split:
                              BPV is itself biased upward by noise at high
                              frequency, so the jump share is reported only with
                              ``noise_qualified`` = whether the noise flag fired.
* ``noise_diagnostics``       omega^2 estimate, noise share of RV, lag-1 return
                              autocorrelation, ``noise_dominated`` flag.

Declared treatment of sampling irregularities (requirement 3)
-------------------------------------------------------------
* Irregular times: ``previous_tick_sample`` maps ticks to a calendar grid using the
  last observation at or before each grid point. Grid points before the first tick
  are dropped (no back-fill); stale points produce genuine zero returns and are
  counted (``stale_share``). Estimators may also run in tick time.
* Gaps and halts: any return whose two endpoints are more than ``max_gap`` apart is
  NEVER interpolated and NEVER enters an intraday estimator. It is moved to the
  gap bucket and reported separately (count and squared-return sum).
* Overnight / session breaks: identical rule. The close-to-open squared log return
  is reported as ``overnight_variance``; ``total_variance`` = intraday + overnight
  and both components are always returned separately.

As-of semantics (requirement 5)
-------------------------------
Every observation carries an event time and a knowledge time. ``asof_tape`` keeps
only records known at or before the cutoff and, per event time, the latest such
revision. ``build_versioned_label`` hashes exactly the inputs it used, so a later
correction cannot change an earlier label: recomputing as of the old cutoff
reproduces the old value and version id, while a later cutoff yields a NEW version
id. Labels carry ``accepted_label=False`` and ``research_only=True``.

Literature: L14 Barndorff-Nielsen, Hansen, Lunde & Shephard (2008, Econometrica 76)
realized kernels; L13 Corsi (2009) HAR is context only (no forecast here).
"""

import hashlib
import json
import math
from typing import Callable, Iterable, Sequence

import numpy as np

RESEARCH_ONLY = True
ACTIVATION = {
    "raw_data_capture": False,
    "variance_forecast": False,
    "gate": False,
    "accepted_outcome_label": False,
    "registry": False,
    "schedule": False,
}
QV_CONVENTION = (
    "integrated variance of the efficient log price over the declared window; "
    "log-return-squared units; not annualised"
)
GAP_POLICY = (
    "no interpolation; a return spanning more than max_gap is excluded from every "
    "intraday estimator and reported in the gap/overnight bucket"
)
PARZEN_CSTAR = 3.5134
MAX_OBSERVATIONS = 5_000_000
NOISE_SHARE_FLAG = 0.10
LABEL_SCHEMA = "q15.noise_robust_rv.label.v1"


# --------------------------------------------------------------------------- utils
def _as_1d(x: Iterable[float], name: str) -> np.ndarray:
    a = np.asarray(x, dtype=float).reshape(-1)
    if a.size > MAX_OBSERVATIONS:
        raise ValueError(f"{name}: {a.size} observations exceeds bound {MAX_OBSERVATIONS}")
    return a


def _finite(a: np.ndarray, name: str) -> np.ndarray:
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name}: non-finite values are not admitted (declare them as gaps)")
    return a


def log_returns(log_prices: Sequence[float]) -> np.ndarray:
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    return np.diff(p)


# ---------------------------------------------------------------- simple controls
def realized_variance(returns: Sequence[float]) -> float:
    """Fixed-interval (or tick) RV: sum of squared returns. Biased by 2*n*omega^2."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    return float(np.dot(r, r))


def sparse_realized_variance(log_prices: Sequence[float], step: int, average: bool = True) -> float:
    """RV on every ``step``-th price. ``average`` = mean over all ``step`` offsets
    (subsampled RV), each offset rescaled to the full span by n_full/n_offset."""
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    step = int(step)
    if step < 1:
        raise ValueError("step must be >= 1")
    if p.size < 2:
        return float("nan")
    if step == 1:
        return realized_variance(np.diff(p))
    offsets = range(step) if average else range(1)
    vals = []
    for o in offsets:
        sub = p[o::step]
        if sub.size < 2:
            continue
        span = (sub.size - 1) * step
        full = p.size - 1
        vals.append(realized_variance(np.diff(sub)) * full / span)
    return float(np.mean(vals)) if vals else float("nan")


# -------------------------------------------------------------- realized kernel
def parzen_weight(x: float | np.ndarray) -> np.ndarray:
    x = np.abs(np.asarray(x, dtype=float))
    out = np.zeros_like(x)
    a = x <= 0.5
    b = (x > 0.5) & (x <= 1.0)
    out[a] = 1.0 - 6.0 * x[a] ** 2 + 6.0 * x[a] ** 3
    out[b] = 2.0 * (1.0 - x[b]) ** 3
    return out


def realized_autocovariances(returns: Sequence[float], max_lag: int) -> np.ndarray:
    """gamma_h = sum_{j>h} r_j r_{j-h} for h = 0..max_lag (not mean-adjusted)."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    max_lag = int(max(0, min(max_lag, max(r.size - 1, 0))))
    return np.array([float(np.dot(r[h:], r[: r.size - h])) for h in range(max_lag + 1)])


def bnhls_bandwidth(n: int, noise_var: float, iv_proxy: float, cstar: float = PARZEN_CSTAR,
                    min_h: int = 1) -> int:
    """BNHLS bandwidth H* = c* xi^(4/5) n^(3/5) with xi^2 = omega^2 / IV (IQ^(1/2)~IV)."""
    n = int(n)
    if n < 2 or not (iv_proxy > 0) or not math.isfinite(iv_proxy):
        return int(min_h)
    xi2 = max(float(noise_var), 0.0) / float(iv_proxy)
    h = cstar * xi2 ** 0.4 * n ** 0.6
    return int(min(max(int(math.ceil(h)), int(min_h)), max(n - 1, int(min_h))))


def realized_kernel(returns: Sequence[float], bandwidth: int) -> float:
    """Non-flat-top Parzen realized kernel: gamma_0 + 2 sum_h k(h/(H+1)) gamma_h.

    Parzen weights make the estimator non-negative. End-point jittering is not
    applied (end-effect noise bias is O(omega^2), stated as a limitation)."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    if r.size == 0:
        return float("nan")
    h = int(max(0, bandwidth))
    g = realized_autocovariances(r, h)
    if g.size == 1:
        return float(g[0])
    w = parzen_weight(np.arange(1, g.size) / (h + 1.0))
    return float(max(g[0] + 2.0 * np.dot(w, g[1:]), 0.0))


def noise_variance_estimate(log_prices: Sequence[float], sparse_step: int) -> float:
    """omega^2 ~ max(RV_all - RV_sparse, 0) / (2 n); RV_sparse is the subsampled
    low-frequency pilot for IV, so the difference isolates the noise bias."""
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    n = p.size - 1
    if n < 2:
        return float("nan")
    rv_all = realized_variance(np.diff(p))
    rv_sp = sparse_realized_variance(p, max(1, int(sparse_step)))
    return float(max(rv_all - rv_sp, 0.0) / (2.0 * n))


def noise_aware_variance(log_prices: Sequence[float], sparse_step: int,
                         bandwidth: int | None = None) -> dict:
    """Primary noise-aware estimate (Parzen RK) with its diagnostics."""
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    r = np.diff(p)
    n = r.size
    iv_pilot = sparse_realized_variance(p, max(1, int(sparse_step)))
    omega2 = noise_variance_estimate(p, sparse_step)
    h = int(bandwidth) if bandwidth is not None else bnhls_bandwidth(n, omega2, iv_pilot)
    rk = realized_kernel(r, h)
    diag = noise_diagnostics(r, omega2)
    return {
        "estimator": "parzen_realized_kernel",
        "value": rk,
        "bandwidth": h,
        "n_returns": int(n),
        "iv_pilot_sparse_rv": iv_pilot,
        "raw_rv_includes_noise": diag["rv"],
        **{k: v for k, v in diag.items() if k != "rv"},
    }


# ----------------------------------------------------------------- pre-averaging
def preaveraged_variance(returns: Sequence[float], theta: float = 0.5,
                         noise_var: float | None = None) -> float:
    """Pre-averaged RV with g(x)=min(x,1-x), k_n = ceil(theta*sqrt(n)).

    PAV = n/(n-k+2) * sum(Ybar_i^2)/(k psi2) - n * omega^2 * psi1 / (k^2 psi2),
    with discrete psi1 = k sum (dg)^2, psi2 = (1/k) sum g^2 and omega^2 = RV/(2n)
    unless supplied."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    n = r.size
    if n < 4:
        return float("nan")
    k = int(max(2, math.ceil(theta * math.sqrt(n))))
    k = min(k, n)
    j = np.arange(1, k) / k
    g = np.minimum(j, 1.0 - j)
    gfull = np.concatenate([[0.0], g, [0.0]])
    psi1 = k * float(np.sum(np.diff(gfull) ** 2))
    psi2 = float(np.sum(g ** 2)) / k
    ybar = np.convolve(r, g[::-1], mode="valid")  # windows of k-1 returns
    m = ybar.size
    om2 = realized_variance(r) / (2.0 * n) if noise_var is None else float(noise_var)
    est = (n / max(m, 1)) * float(np.dot(ybar, ybar)) / (k * psi2) - n * om2 * psi1 / (k * k * psi2)
    return float(est)


# ---------------------------------------------------------- jump decomposition
def bipower_variation(returns: Sequence[float]) -> float:
    r = _finite(_as_1d(returns, "returns"), "returns")
    n = r.size
    if n < 2:
        return float("nan")
    a = np.abs(r)
    return float((math.pi / 2.0) * np.dot(a[1:], a[:-1]) * n / (n - 1))


def tripower_quarticity(returns: Sequence[float]) -> float:
    r = _finite(_as_1d(returns, "returns"), "returns")
    n = r.size
    if n < 3:
        return float("nan")
    a = np.abs(r) ** (4.0 / 3.0)
    mu43 = 2 ** (2.0 / 3.0) * math.gamma(7.0 / 6.0) / math.gamma(0.5)
    return float(n * mu43 ** -3 * n / (n - 2) * np.sum(a[2:] * a[1:-1] * a[:-2]))


def jump_decomposition(returns: Sequence[float], noise_dominated: bool | None = None) -> dict:
    """QUALIFIED split RV = continuous + jump using BPV and the Huang-Tauchen ratio z.

    Not decision-bearing: BPV is noise-biased at high frequency, so the output
    carries ``noise_qualified`` (True when a noise flag was raised) and must then be
    read as unreliable."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    n = r.size
    rv = realized_variance(r)
    bpv = bipower_variation(r)
    tq = tripower_quarticity(r)
    jump = max(rv - bpv, 0.0) if math.isfinite(bpv) else float("nan")
    z = float("nan")
    if n >= 3 and rv > 0 and bpv > 0 and tq > 0:
        theta = (math.pi / 2.0) ** 2 + math.pi - 5.0
        z = ((rv - bpv) / rv) / math.sqrt(theta / n * max(1.0, tq / bpv ** 2))
    if noise_dominated is None:
        noise_dominated = bool(noise_diagnostics(r)["noise_dominated"])
    return {
        "rv": rv,
        "bpv": bpv,
        "jump_variation": jump,
        "jump_share": (jump / rv) if rv > 0 else float("nan"),
        "ratio_z": z,
        "noise_qualified": bool(noise_dominated),
    }


# --------------------------------------------------------------- diagnostics
def noise_diagnostics(returns: Sequence[float], noise_var: float | None = None,
                      share_flag: float = NOISE_SHARE_FLAG) -> dict:
    """Noise share of RV and lag-1 autocorrelation.

    ``noise_dominated`` fires when the implied noise bias 2*n*omega^2 exceeds
    ``share_flag`` of RV AND lag-1 return autocorrelation is negative beyond
    2/sqrt(n) (the Roll bounce signature). When it fires, raw RV must not be read
    as economic variance."""
    r = _finite(_as_1d(returns, "returns"), "returns")
    n = r.size
    rv = realized_variance(r) if n else float("nan")
    if n < 3 or not rv > 0:
        return {"rv": rv, "omega2": float("nan"), "noise_share": float("nan"),
                "lag1_autocorr": float("nan"), "noise_dominated": False, "n": int(n)}
    g1 = float(np.dot(r[1:], r[:-1]))
    rho1 = g1 / rv
    om2 = max(-g1 / (n - 1), 0.0) if noise_var is None else max(float(noise_var), 0.0)
    share = min(2.0 * n * om2 / rv, 1.0)
    flag = bool(share > share_flag and rho1 < -2.0 / math.sqrt(n))
    return {"rv": rv, "omega2": om2, "noise_share": share, "lag1_autocorr": rho1,
            "noise_dominated": flag, "n": int(n)}


# ----------------------------------------------------- sampling and sessions
def previous_tick_sample(times: Sequence[float], log_prices: Sequence[float],
                         grid: Sequence[float]) -> dict:
    """Previous-tick sampling. Returns grid points at/after the first tick only."""
    t = _finite(_as_1d(times, "times"), "times")
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    gr = _finite(_as_1d(grid, "grid"), "grid")
    if t.size != p.size:
        raise ValueError("times and log_prices differ in length")
    if t.size and np.any(np.diff(t) < 0):
        raise ValueError("times must be non-decreasing")
    idx = np.searchsorted(t, gr, side="right") - 1
    ok = idx >= 0
    sampled = p[idx[ok]]
    src = idx[ok]
    stale = int(np.sum(np.diff(src) == 0)) if src.size > 1 else 0
    return {
        "grid": gr[ok],
        "log_prices": sampled,
        "dropped_before_first_tick": int(np.sum(~ok)),
        "stale_returns": stale,
        "stale_share": stale / max(src.size - 1, 1),
    }


def split_sessions(times: Sequence[float], max_gap: float) -> list[tuple[int, int]]:
    """Index ranges [start, end] (inclusive) of runs whose consecutive gaps <= max_gap."""
    t = _finite(_as_1d(times, "times"), "times")
    if t.size == 0:
        return []
    if np.any(np.diff(t) < 0):
        raise ValueError("times must be non-decreasing")
    breaks = np.flatnonzero(np.diff(t) > float(max_gap))
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [t.size - 1]])
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


def session_variance_decomposition(times: Sequence[float], log_prices: Sequence[float],
                                   max_gap: float,
                                   estimator: Callable[[np.ndarray], float] | None = None) -> dict:
    """Intraday variance (per session, estimator on within-session returns) plus the
    separately reported gap/overnight bucket. No interpolation anywhere."""
    t = _finite(_as_1d(times, "times"), "times")
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    if t.size != p.size:
        raise ValueError("times and log_prices differ in length")
    est = estimator if estimator is not None else (lambda r: realized_variance(r))
    sessions = split_sessions(t, max_gap)
    intraday = []
    for s, e in sessions:
        r = np.diff(p[s : e + 1])
        intraday.append(float(est(r)) if r.size else 0.0)
    gap_returns = [p[sessions[i + 1][0]] - p[sessions[i][1]] for i in range(len(sessions) - 1)]
    gap_var = float(np.sum(np.square(gap_returns))) if gap_returns else 0.0
    intra = float(np.sum(intraday)) if intraday else 0.0
    return {
        "intraday_variance": intra,
        "overnight_variance": gap_var,
        "total_variance": intra + gap_var,
        "n_sessions": len(sessions),
        "n_gap_returns": len(gap_returns),
        "per_session_intraday": intraday,
        "gap_policy": GAP_POLICY,
    }


# ----------------------------------------------------------- as-of / versioning
def asof_tape(event_times: Sequence[float], knowledge_times: Sequence[float],
              values: Sequence[float], cutoff: float) -> tuple[np.ndarray, np.ndarray]:
    """Records known at or before ``cutoff``; per event time the latest such revision."""
    et = _finite(_as_1d(event_times, "event_times"), "event_times")
    kt = _finite(_as_1d(knowledge_times, "knowledge_times"), "knowledge_times")
    v = _finite(_as_1d(values, "values"), "values")
    if not (et.size == kt.size == v.size):
        raise ValueError("event_times, knowledge_times and values differ in length")
    keep = kt <= float(cutoff)
    et, kt, v = et[keep], kt[keep], v[keep]
    order = np.lexsort((kt, et))  # by event time, then knowledge time
    et, kt, v = et[order], kt[order], v[order]
    if et.size:
        last = np.concatenate([et[1:] != et[:-1], [True]])
        et, v = et[last], v[last]
    return et, v


def build_versioned_label(event_times: Sequence[float], knowledge_times: Sequence[float],
                          log_prices: Sequence[float], window_start: float, window_end: float,
                          asof: float, max_gap: float, sparse_step: int = 1,
                          source_id: str = "synthetic") -> dict:
    """Window label from the tape as known at ``asof``. Research-only, never accepted."""
    if asof < window_end:
        raise ValueError("asof precedes the window end: label would use an incomplete window")
    et, v = asof_tape(event_times, knowledge_times, log_prices, asof)
    m = (et >= float(window_start)) & (et <= float(window_end))
    et, v = et[m], v[m]
    parts = session_variance_decomposition(et, v, max_gap) if et.size else {
        "intraday_variance": float("nan"), "overnight_variance": float("nan"),
        "total_variance": float("nan"), "n_sessions": 0, "n_gap_returns": 0}
    rk = float("nan")
    if et.size >= 3:
        sessions = split_sessions(et, max_gap)
        vals = []
        for s, e in sessions:
            seg = v[s : e + 1]
            vals.append(noise_aware_variance(seg, sparse_step)["value"] if seg.size >= 3
                        else realized_variance(np.diff(seg)))
        rk = float(np.sum(vals))
    payload = {
        "schema": LABEL_SCHEMA,
        "source_id": str(source_id),
        "window": [float(window_start), float(window_end)],
        "asof": float(asof),
        "max_gap": float(max_gap),
        "sparse_step": int(sparse_step),
        "event_times": [float(x) for x in et],
        "log_prices": [repr(float(x)) for x in v],
    }
    vid = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {
        "schema": LABEL_SCHEMA,
        "version_id": vid,
        "asof": float(asof),
        "window": payload["window"],
        "n_obs": int(et.size),
        "fixed_interval_rv_intraday": parts["intraday_variance"],
        "noise_aware_rk_intraday": rk,
        "overnight_variance": parts["overnight_variance"],
        "n_gap_returns": parts["n_gap_returns"],
        "qv_convention": QV_CONVENTION,
        "research_only": True,
        "accepted_label": False,
        "is_forecast": False,
    }


def label_unchanged(old: dict, recomputed: dict) -> bool:
    """True iff a recomputation as of the same cutoff reproduces the old label."""
    keys = ("version_id", "fixed_interval_rv_intraday", "noise_aware_rk_intraday",
            "overnight_variance", "n_obs")
    return all(old.get(k) == recomputed.get(k) for k in keys)


# ------------------------------------------------------------ synthetic controls
def simulate_efficient_path(n: int, iv: float, seed: int, stochastic_vol: bool = False,
                            vol_of_vol: float = 0.5) -> tuple[np.ndarray, float]:
    """Efficient log-price path with KNOWN integrated variance over [0, 1].

    The per-step variance is U-shaped (stochastic_vol=False) or an OU log-vol path
    (stochastic_vol=True), and in both cases is rescaled so it sums to ``iv``
    exactly; the returned IV is that known sum."""
    n = int(n)
    if n < 2 or n > MAX_OBSERVATIONS:
        raise ValueError("n out of bounds")
    rng = np.random.default_rng(int(seed))
    if stochastic_vol:
        z = rng.standard_normal(n)
        lv = np.empty(n)
        lv[0] = 0.0
        a = math.exp(-5.0 / n)
        for i in range(1, n):
            lv[i] = a * lv[i - 1] + vol_of_vol * math.sqrt(1 - a * a) * z[i]
        var = np.exp(2 * lv)
    else:
        u = (np.arange(n) + 0.5) / n
        var = 1.0 + 0.8 * (2 * u - 1) ** 2  # intraday U shape
    var = var / var.sum() * float(iv)
    r = rng.standard_normal(n) * np.sqrt(var)
    x = np.concatenate([[0.0], np.cumsum(r)])
    return x, float(var.sum())


def add_noise(log_prices: Sequence[float], omega: float, seed: int, kind: str = "roll") -> np.ndarray:
    """``roll``: bid/ask bounce +/- omega with random trade sign; ``gaussian``: N(0, omega^2)."""
    x = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    rng = np.random.default_rng(int(seed))
    if kind == "roll":
        u = omega * np.where(rng.random(x.size) < 0.5, -1.0, 1.0)
    elif kind == "gaussian":
        u = omega * rng.standard_normal(x.size)
    else:
        raise ValueError("kind must be 'roll' or 'gaussian'")
    return x + u


NOISE_REGIMES = {"none": 0.0, "low": 1e-5, "medium": 1e-4, "high": 1e-3}  # xi^2 = omega^2/IV


def monte_carlo_bias_table(n: int = 4680, iv: float = 1e-4, reps: int = 200, seed: int = 15,
                           regimes: dict | None = None, sparse_step: int = 60,
                           stochastic_vol: bool = False) -> list[dict]:
    """Bias / variance / RMSE of each estimator vs known IV across fixed noise regimes."""
    regimes = dict(NOISE_REGIMES if regimes is None else regimes)
    reps = int(reps)
    if reps < 2 or reps > 100_000:
        raise ValueError("reps out of bounds")
    rows = []
    for ri, (name, xi2) in enumerate(sorted(regimes.items(), key=lambda kv: kv[1])):
        omega = math.sqrt(xi2 * iv)
        est: dict[str, list[float]] = {"tick_rv": [], "sparse_rv": [], "realized_kernel": [],
                                       "preaveraged": []}
        ivs = []
        for k in range(reps):
            x, ivk = simulate_efficient_path(n, iv, seed + 7919 * k + 104729 * ri, stochastic_vol)
            y = add_noise(x, omega, seed + 31 * k + 1_000_003 * (ri + 1)) if omega > 0 else x
            r = np.diff(y)
            est["tick_rv"].append(realized_variance(r))
            est["sparse_rv"].append(sparse_realized_variance(y, sparse_step))
            est["realized_kernel"].append(noise_aware_variance(y, sparse_step)["value"])
            est["preaveraged"].append(preaveraged_variance(r))
            ivs.append(ivk)
        ivs_a = np.asarray(ivs)
        for e, vals in est.items():
            err = np.asarray(vals) - ivs_a
            rows.append({
                "regime": name, "xi2": xi2, "estimator": e, "n": int(n), "reps": reps,
                "rel_bias": float(err.mean() / iv),
                "rel_sd": float(err.std(ddof=1) / iv),
                "rel_rmse": float(math.sqrt(np.mean(err ** 2)) / iv),
                "theory_rv_bias_rel": float(2 * n * xi2) if e == "tick_rv" else None,
            })
    return rows


def signature_curve(log_prices: Sequence[float], steps: Sequence[int]) -> dict:
    """Subsampled RV at each sampling step (the signature plot), relative to the coarsest."""
    p = _finite(_as_1d(log_prices, "log_prices"), "log_prices")
    vals = {int(s): sparse_realized_variance(p, int(s)) for s in steps}
    ref = vals[max(vals)]
    return {s: {"rv": v, "ratio_to_coarsest": (v / ref) if ref > 0 else float("nan")}
            for s, v in sorted(vals.items())}
