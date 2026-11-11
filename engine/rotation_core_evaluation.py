"""Rotation Core historical rotation evaluation — pure functions bound to the frozen header.

Header: research/rotation_core/protocol_header_v1.json (sha256 FROZEN_HEADER_SHA256). The JSON governs; this
module implements it. Research-only and paper-only: nothing here ranks, gates, sizes, alerts or trades.

Conventions (header `global_conventions`):
  * a decision at the close of session t uses data dated <= t (macro series only from their availability date);
  * targets are executed at the close of t+1; the day-(t+1) return is earned on the pre-execution holdings and the
    execution cost is charged on day t+1;
  * daily rules trade only when their target changes; monthly rules decide on the last session of a month;
  * long only, no leverage, remainder in cash earning the lagged 3-month T-bill rate.

Statistics helpers (stationary bootstrap, Holm, capture, max drawdown, OLS beta) are ported from
engine/prophet_beta_evaluation.py on branch fable/prophet-beta-evaluation-20261110 (unmerged), with attribution.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd

FROZEN_HEADER_SHA256 = "af2a09886132bb784535e21134b63c2c86c579e186c248b20bb617fc77580f32"
TRADING_DAYS = 252
D_END = pd.Timestamp("2019-12-31")
H_START = pd.Timestamp("2020-01-02")
ERA_SPLIT = pd.Timestamp("2009-12-31")

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"]
SLEEVES = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC"]
DEFENSIVE_TRIO = ["XLP", "XLU", "XLV"]


class HeaderMismatch(RuntimeError):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_header(path: str | Path, expected: str = FROZEN_HEADER_SHA256) -> dict:
    raw = Path(path).read_bytes()
    got = sha256_bytes(raw)
    if got != expected:
        raise HeaderMismatch(f"protocol header sha256 {got} != frozen {expected}")
    return json.loads(raw)


# --------------------------------------------------------------------------- #
# cash and macro availability
# --------------------------------------------------------------------------- #
def cash_returns(dtb3: pd.Series, sessions: pd.DatetimeIndex, fallback: pd.Series | None = None) -> pd.Series:
    """Daily T-bill accrual on each session t from the yield dated t-1 (forward-filled <= 5 sessions)."""
    y = dtb3.astype(float).dropna()
    if fallback is not None:
        fb = fallback.astype(float).dropna()
        y = y.combine_first(fb)
    on = y.reindex(y.index.union(sessions)).ffill(limit=5).reindex(sessions)
    lagged = on.shift(1)
    out = (1.0 + lagged / 100.0) ** (1.0 / TRADING_DAYS) - 1.0
    if len(out):
        out.iloc[0] = 0.0 if not np.isfinite(out.iloc[0]) else out.iloc[0]   # first session: no prior yield needed
    return out   # NaN = unresolved rate (counted by simulate; never silently zero)


def lagged_flag_on_sessions(flag_raw: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """Map a flag computed on its own observation dates to sessions using observations dated <= t-1.

    The flag value at session t is the last observation dated on or before the previous session."""
    f = flag_raw.dropna().astype(float)
    on = f.reindex(f.index.union(sessions)).ffill().reindex(sessions)
    return on.shift(1)


def credit_flag(spread: pd.Series, sessions: pd.DatetimeIndex, window: int = 252) -> pd.Series:
    """C: spread(t-1) > SMA of the `window` spread observations ending t-1 (NaN until `window` observations)."""
    s = spread.astype(float).dropna()
    sma = s.rolling(window, min_periods=window).mean()
    raw = (s > sma).astype(float).where(sma.notna())
    return lagged_flag_on_sessions(raw, sessions)


def sahm_available(sahm: pd.Series, sessions: pd.DatetimeIndex, threshold: float = 0.50) -> pd.Series:
    """M: latest SAHMREALTIME >= threshold; month m is usable from the first session after the 10th business day of
    month m+1."""
    s = sahm.astype(float).dropna()
    avail = []
    for d in s.index:
        nxt = (pd.Timestamp(d) + pd.offsets.MonthBegin(1)).normalize()
        bd10 = pd.bdate_range(nxt, nxt + pd.Timedelta(days=31))[9]
        avail.append(bd10)
    av = pd.Series((s.values >= threshold).astype(float), index=pd.DatetimeIndex(avail))
    av = av[~av.index.duplicated(keep="last")].sort_index()
    vals = np.full(len(sessions), np.nan)
    pos = np.searchsorted(av.index.values, sessions.values, side="left") - 1   # avail date strictly < t
    ok = pos >= 0
    vals[ok] = av.values[pos[ok]]
    return pd.Series(vals, index=sessions)


# --------------------------------------------------------------------------- #
# price signals (all causal: values at t use closes <= t)
# --------------------------------------------------------------------------- #
def sma(x: pd.Series | pd.DataFrame, n: int):
    return x.rolling(n, min_periods=n).mean()


def trend_broken(level: pd.Series, n: int = 200) -> pd.Series:
    m = sma(level, n)
    return (level < m).astype(float).where(m.notna())


def mtf(level: pd.Series | pd.DataFrame, ns: Sequence[int] = (50, 100, 200)):
    parts = []
    for n in ns:
        m = sma(level, n)
        parts.append((level > m).astype(float).where(m.notna()))
    out = sum(parts) / len(parts)
    return out


def total_return(px: pd.DataFrame | pd.Series, start_lag: int, end_lag: int = 0):
    """Return from session t-start_lag to t-end_lag."""
    return px.shift(end_lag) / px.shift(start_lag) - 1.0


def rel_wealth(ra, rb):
    return (1.0 + ra) / (1.0 + rb) - 1.0


def cum_cash(cash_r: pd.Series, start_lag: int, end_lag: int = 0) -> pd.Series:
    w = (1.0 + cash_r).cumprod()
    return w.shift(end_lag) / w.shift(start_lag) - 1.0


def eligible(px: pd.DataFrame, min_sessions: int = 253) -> pd.DataFrame:
    """True from an instrument's `min_sessions`-th priced session onward."""
    return px.notna().cumsum() >= min_sessions


def month_end_sessions(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(sessions, index=sessions)
    return pd.DatetimeIndex(s.groupby([sessions.year, sessions.month]).max().values)


# --------------------------------------------------------------------------- #
# book simulation
# --------------------------------------------------------------------------- #
@dataclass
class Book:
    name: str
    returns: pd.Series            # daily net returns (NAV_t / NAV_{t-1} - 1)
    risky_weight: pd.Series       # risky weight held during each day (start-of-day holdings)
    equity_weight: pd.Series      # weight in the job's equity asset(s), same timing
    holdings: pd.DataFrame        # start-of-day holdings (weights of start-of-day NAV)
    traded: pd.Series             # traded notional per day as a fraction of pre-trade NAV
    costs: pd.Series              # fees paid per day as a fraction of start-of-day NAV
    meta: dict = field(default_factory=dict)
    post_holdings: pd.DataFrame | None = None   # holdings after each close (after any execution)

    @property
    def post_equity_weight(self) -> pd.Series:
        cols = self.meta.get("equity_cols", [])
        return self.post_holdings[[c for c in cols if c in self.post_holdings]].sum(axis=1)


def _validate_target(t: np.ndarray, name: str, when) -> np.ndarray:
    if not np.all(np.isfinite(t)):
        raise ValueError(f"{name}: non-finite target component at {when}")
    if np.any(t < -1e-12):
        raise ValueError(f"{name}: negative target weight (long-only violated) at {when}")
    if t.sum() > 1 + 1e-9:
        raise ValueError(f"{name}: target weights sum {t.sum()} > 1 at {when}")
    return np.clip(t, 0.0, None)


def _fee_funded_nav(v: np.ndarray, cash: float, tgt: np.ndarray, fee: np.ndarray) -> tuple[float, float]:
    """Self-financing rebalance: find post-fee NAV N with N + sum_j fee_j |tgt_j N - v_j| = NAV_pre."""
    pre = float(v.sum() + cash)
    N = pre
    for _ in range(100):
        f = float(fee @ np.abs(tgt * N - v))
        N_new = pre - f
        if abs(N_new - N) < 1e-15 * max(1.0, pre):
            N = N_new
            break
        N = N_new
    paid = float(fee @ np.abs(tgt * N - v))
    assert abs(N + paid - pre) < 1e-10 * max(1.0, pre), "dollar conservation violated"
    return N, paid


def simulate(targets: pd.DataFrame, rets: pd.DataFrame, cash_r: pd.Series, cost_bps: float | Mapping[str, float],
             name: str, decision_mask: pd.Series | None = None, threshold: float | None = None,
             equity_cols: Sequence[str] = ("SPY",), start: pd.Timestamp | None = None,
             end: pd.Timestamp | None = None, always_rebalance: bool = False,
             avail: pd.DataFrame | None = None) -> Book:
    """Simulate a long-only book in dollars (positions + cash), self-financing, fees funded at execution.

    rets: daily returns from VALUATION marks (forward-filled within an instrument's life: a missing close earns 0 and
      the next observed close carries the full move). avail: RAW observed-close mask; an order may execute only at a
      close where every instrument whose position changes has an observed close; otherwise it stays pending (counted)
      and executes at the next such close, at that close's marks.
    Execution: a decision at session t executes at the close of the next executable session (>= t+1). Day returns
      accrue on the holdings carried into the day; fees are paid out of NAV at the execution close so that
      post-fee NAV + fees = pre-trade NAV (asserted) and target weights apply to post-fee NAV.
    Daily rules trade only when the target changes; with `threshold`, only if max |target - drifted weight| >=
      threshold; monthly rules (always_rebalance=True) execute every decision.
    """
    sess = rets.index
    if start is not None:
        sess = sess[sess >= start]
    if end is not None:
        sess = sess[sess <= end]
    assets = list(targets.columns)
    R = rets.reindex(index=sess, columns=assets).fillna(0.0).to_numpy()
    Craw = cash_r.reindex(sess).to_numpy()
    C = np.nan_to_num(Craw, nan=0.0)
    A = (avail.reindex(index=sess, columns=assets).fillna(False).to_numpy().astype(bool)
         if avail is not None else np.ones(R.shape, dtype=bool))
    T = targets.reindex(sess).to_numpy()
    if decision_mask is not None:
        dm = decision_mask.reindex(sess).fillna(False).to_numpy()
        T = np.where(dm[:, None], T, np.nan)
    if isinstance(cost_bps, Mapping):
        fee = np.array([cost_bps.get(a, 5.0) for a in assets]) / 1e4
    else:
        fee = np.full(len(assets), float(cost_bps) / 1e4)
    n, k = R.shape
    v = np.zeros(k); cash = 1.0
    last_target = None
    pending = None
    deferrals = 0; cash_rate_missing = 0
    out_r = np.zeros(n); out_w = np.zeros(n); out_eq = np.zeros(n); out_tr = np.zeros(n); out_c = np.zeros(n)
    H = np.zeros((n, k)); HP = np.zeros((n, k))
    eq_idx = [assets.index(a) for a in equity_cols if a in assets]
    for i in range(n):
        nav0 = float(v.sum() + cash)
        w0 = v / nav0
        H[i] = w0
        out_w[i] = w0.sum()
        out_eq[i] = w0[eq_idx].sum() if eq_idx else 0.0
        if cash > 1e-12 and not np.isfinite(Craw[i]):
            cash_rate_missing += 1
        v = v * (1 + R[i])
        cash = cash * (1 + C[i])
        nav_pre = float(v.sum() + cash)
        if pending is not None:
            tgt = pending
            changed = np.abs(tgt * nav_pre - v) > 1e-12 * nav_pre
            if np.all(A[i][changed]):
                N, paid = _fee_funded_nav(v, cash, tgt, fee)
                out_tr[i] = float(np.abs(tgt * N - v).sum() / nav_pre)
                out_c[i] = paid / nav0
                v = tgt * N
                cash = N * (1.0 - tgt.sum())
                pending = None
            else:
                deferrals += 1
        nav1 = float(v.sum() + cash)
        out_r[i] = nav1 / nav0 - 1.0
        HP[i] = v / nav1
        t = T[i]
        if not np.all(np.isnan(t)):
            t = _validate_target(np.nan_to_num(t, nan=0.0), name, sess[i])
            new = None
            if always_rebalance:
                new = t
            elif threshold is not None:
                if np.max(np.abs(t - HP[i])) >= threshold:
                    new = t
            elif last_target is None or np.max(np.abs(t - last_target)) > 1e-12:
                new = t
            if new is not None:
                pending = new
                last_target = new
    idx = sess
    return Book(name, pd.Series(out_r, idx), pd.Series(out_w, idx), pd.Series(out_eq, idx),
                pd.DataFrame(H, idx, assets), pd.Series(out_tr, idx), pd.Series(out_c, idx),
                meta={"deferred_executions": deferrals, "cash_rate_missing_days_with_cash": cash_rate_missing,
                      "equity_cols": list(equity_cols)},
                post_holdings=pd.DataFrame(HP, idx, assets))


# --------------------------------------------------------------------------- #
# metrics (ported helpers)
# --------------------------------------------------------------------------- #
def compound(r) -> float:
    return float(np.prod(1.0 + np.asarray(r)) - 1.0)


def beta_ols(y, x) -> tuple[float, float]:
    x = np.asarray(x); y = np.asarray(y)
    vx = np.var(x)
    if vx <= 0:
        return float("nan"), float("nan")
    b = float(np.mean((x - x.mean()) * (y - y.mean())) / vx)
    return b, float(y.mean() - b * x.mean())


def max_drawdown(r) -> float:
    v = np.cumprod(1 + np.asarray(r))
    if not len(v):
        return 0.0
    peak = np.maximum.accumulate(np.concatenate([[1.0], v]))[1:]
    return float(np.min(v / peak - 1.0))


def monthly(r: pd.Series) -> pd.Series:
    return (1 + r).groupby([r.index.year, r.index.month]).prod() - 1


def capture_monthly(rp: pd.Series, rm: pd.Series, up: bool, min_abs: float = 0.005) -> tuple[float | None, int]:
    mp, mm = monthly(rp), monthly(rm)
    keep = mm.abs() >= min_abs
    excluded = int((~keep).sum())
    mp, mm = mp[keep], mm[keep]
    m = mm > 0 if up else mm < 0
    n = int(m.sum())
    if n == 0:
        return None, excluded
    gm = np.prod(1 + mm[m]) ** (1 / n) - 1
    gp = np.prod(1 + mp[m]) ** (1 / n) - 1
    return (float(gp / gm) if gm != 0 else None), excluded


def sharpe(r, c) -> float:
    e = np.asarray(r) - np.asarray(c)
    sd = e.std(ddof=1)
    return float(e.mean() / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def sortino(r, c) -> float:
    e = np.asarray(r) - np.asarray(c)
    dn = np.sqrt(np.mean(np.minimum(e, 0) ** 2))
    return float(e.mean() / dn * math.sqrt(TRADING_DAYS)) if dn > 0 else float("nan")


def ann_return(r) -> float:
    n = len(r)
    return float((1 + compound(r)) ** (TRADING_DAYS / n) - 1) if n else float("nan")


def book_metrics(b: Book, spy: pd.Series, cash: pd.Series, mask: pd.Series | None = None) -> dict:
    r = b.returns if mask is None else b.returns[mask.reindex(b.returns.index).fillna(False).astype(bool)]
    m = spy.reindex(r.index).fillna(0.0)
    c = cash.reindex(r.index).fillna(0.0)
    years = len(r) / TRADING_DAYS
    beta, a = beta_ols((r - c).values, (m - c).values)
    up, ex_u = capture_monthly(r, m, True)
    dn, _ = capture_monthly(r, m, False)
    mdd = max_drawdown(r.values)
    ar = ann_return(r.values)
    w = b.risky_weight.reindex(r.index)
    return {
        "first": str(r.index[0].date()), "last": str(r.index[-1].date()), "sessions": int(len(r)),
        "total_return": compound(r.values), "ann_return": ar,
        "ann_vol": float(r.std(ddof=1) * math.sqrt(TRADING_DAYS)),
        "sharpe": sharpe(r.values, c.values), "sortino": sortino(r.values, c.values),
        "max_drawdown": mdd, "calmar": (ar / abs(mdd)) if mdd < 0 else None,
        "beta_vs_spy": beta, "residual_intercept_ann": a * TRADING_DAYS if np.isfinite(a) else None,
        "up_capture_monthly": up, "down_capture_monthly": dn, "capture_months_excluded_small_spy": ex_u,
        "traded_notional_per_year": float(b.traded.reindex(r.index).sum() / years) if years else None,
        "turnover_one_way_per_year": float(b.traded.reindex(r.index).sum() / years / 2) if years else None,
        "costs_paid_per_year": float(b.costs.reindex(r.index).sum() / years) if years else None,
        "mean_risky_weight": float(w.mean()), "time_in_market": float((w > 1e-9).mean()),
    }


# --------------------------------------------------------------------------- #
# bootstrap, Holm, power
# --------------------------------------------------------------------------- #
def stationary_bootstrap_indices(n: int, B: int, mean_block: float, seed: int) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (B x n), deterministic for a seed (ported)."""
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=B)
    jumps = rng.random((B, n)) < p
    fresh = rng.integers(0, n, size=(B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jumps[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_stat(cols: Sequence[np.ndarray], stat: Callable[..., np.ndarray], B: int, mean_block: float,
                   seed: int, chunk: int = 1000) -> np.ndarray:
    """Bootstrap distribution of a vectorised statistic of paired columns; stat(*cols_resampled) -> (b,) array."""
    n = len(cols[0])
    out = []
    done = 0
    k = 0
    while done < B:
        b = min(chunk, B - done)
        idx = stationary_bootstrap_indices(n, b, mean_block, seed + k)
        out.append(stat(*[c[idx] for c in cols]))
        done += b
        k += 1
    return np.concatenate(out)


def stat_mean_diff(a, b):
    return (a - b).mean(axis=1) * TRADING_DAYS


def stat_sharpe_diff(a, ref, c):
    def sh(x):
        e = x - c
        sd = e.std(axis=1, ddof=1)
        return np.where(sd > 0, e.mean(axis=1) / sd * math.sqrt(TRADING_DAYS), np.nan)
    return sh(a) - sh(ref)


def centred_p(dist: np.ndarray, obs: float) -> float:
    """One-sided centred p with the literal B+1 denominator; non-finite draws never count as exceedances
    (conservative); their number is reported by finite_draws()."""
    d = np.asarray(dist, dtype=float)
    if not np.isfinite(obs):
        return float("nan")
    exceed = np.sum(np.isfinite(d) & ((d - obs) >= obs))
    return float((1 + exceed) / (len(d) + 1))


def finite_draws(dist: np.ndarray) -> int:
    return int(np.isfinite(np.asarray(dist, dtype=float)).sum())


def ci95(dist: np.ndarray) -> list[float] | None:
    d = dist[np.isfinite(dist)]
    if not len(d):
        return None
    lo, hi = np.quantile(d, [0.025, 0.975])
    return [float(lo), float(hi)]


def norm_ppf(p: float) -> float:
    # Acklam-free: use math.erf inverse via bisection (adequate precision for reporting)
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power_line(se: float, m: int, effect: float, unit: str, alpha: float = 0.05) -> dict:
    z80 = norm_ppf(0.80)
    mde_holm = (norm_ppf(1 - alpha / m) + z80) * se
    mde_raw = (norm_ppf(1 - alpha) + z80) * se
    could = mde_holm <= effect
    return {"se": se, "mde80_holm": mde_holm, "mde80_unadjusted": mde_raw, "holm_m": m,
            "reference_effect": effect,
            "sentence": (f"this test {'could' if could else 'could not'} have detected an effect of "
                         f"{effect:g} {unit} (80% power at the Holm threshold alpha/{m}; minimum detectable "
                         f"{mde_holm:.3g} {unit})")}


def holm(pvals: Mapping[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm step-down (ported)."""
    items = sorted(pvals.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    out, running, stop = {}, 0.0, False
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        rej = (not stop) and p < alpha / (m - i)
        if not rej:
            stop = True
        out[k] = {"p_raw": p, "p_holm": adj, "reject_h0": rej}
    return out


class SummedLedger:
    """Duck-typed ledger: effective_n is the sum over named families of a real TrialLedger's effective_n."""

    def __init__(self, ledger, families: Sequence[str]):
        self.ledger = ledger
        self.families = list(families)
        self.parts = {f: int(ledger.effective_n(f)) for f in self.families}

    def effective_n(self, family=None) -> int:
        return int(sum(self.parts.values()))


def dsr(r: np.ndarray, c: np.ndarray, ledger) -> dict | None:
    from engine.validation import deflated_sharpe
    e = np.asarray(r) - np.asarray(c)
    sd = e.std(ddof=1)
    if sd <= 0 or len(e) < 3:
        return None
    z = (e - e.mean()) / e.std(ddof=0)
    skew = float(np.mean(z ** 3)); kurt = float(np.mean(z ** 4))
    return deflated_sharpe(float(e.mean() / sd), skew, kurt, len(e), ledger=ledger, family="rotation_core_v1")


# --------------------------------------------------------------------------- #
# pivots / episodes
# --------------------------------------------------------------------------- #
def find_episode(level: pd.Series, peak_from, peak_to, trough_by) -> dict | None:
    lv = level.dropna()
    w = lv[(lv.index >= pd.Timestamp(peak_from)) & (lv.index <= pd.Timestamp(peak_to))]
    if w.empty:
        return None
    peak = w.idxmax()
    after = lv[(lv.index > peak) & (lv.index <= pd.Timestamp(trough_by))]
    if after.empty:
        return None
    trough = after.idxmin()
    return {"peak": peak, "trough": trough, "drawdown": float(lv[trough] / lv[peak] - 1)}


def algorithmic_drawdowns(level: pd.Series, thresh: float = 0.15) -> list[dict]:
    lv = level.dropna()
    out, peak_v, peak_d, trough_v, trough_d, in_dd = [], lv.iloc[0], lv.index[0], None, None, False
    for d, v in lv.items():
        if v >= peak_v:
            if in_dd and trough_v / peak_v - 1 <= -thresh:
                out.append({"peak": peak_d, "trough": trough_d, "drawdown": float(trough_v / peak_v - 1),
                            "recovered": str(d.date())})
            peak_v, peak_d, in_dd, trough_v, trough_d = v, d, False, None, None
        else:
            in_dd = True
            if trough_v is None or v < trough_v:
                trough_v, trough_d = v, d
    if in_dd and trough_v is not None and trough_v / peak_v - 1 <= -thresh:
        out.append({"peak": peak_d, "trough": trough_d, "drawdown": float(trough_v / peak_v - 1),
                    "recovered": None})
    return out


def _spells(w: pd.Series, thr: float = 0.5) -> list[tuple[pd.Timestamp, pd.Timestamp | None]]:
    off = (w <= thr + 1e-12)
    spells, start = [], None
    for d, o in off.items():
        if o and start is None:
            start = d
        elif not o and start is not None:
            spells.append((start, d))
            start = None
    if start is not None:
        spells.append((start, None))
    return spells


def pivot_table(weight: pd.Series, strat_r: pd.Series, mkt_r: pd.Series, mkt_level: pd.Series,
                episodes: Mapping[str, dict], thr: float = 0.5, first_exec: pd.Timestamp | None = None,
                sealed_tail: int = 0) -> dict:
    """Per-episode exit/re-entry timing and the calm-period false-pivot record.

    weight: risky (equity) weight in force AFTER the close of each session (i.e. after any execution at that close);
    an exit date is therefore the execution close at which the weight first fell to <= thr. Exit: from > thr to <= thr;
    re-entry: first later session with weight >= thr.
    first_exec: sessions before the book's first execution are a start-up artefact and excluded from spell counts.
    sealed_tail: spells starting in the last `sealed_tail` sessions are 'undetermined_sealed' (they may belong to an
    episode window that lies in the sealed hold-out); they and those sessions are excluded from false-pivot counts."""
    sess = weight.index
    pos = {d: i for i, d in enumerate(sess)}
    rows = {}
    windows = []
    for name, ep in episodes.items():
        pk, tr = ep["peak"], ep["trough"]
        if pk not in pos or tr not in pos:
            rows[name] = {"status": "outside_window"}
            continue
        ip, it = pos[pk], pos[tr]
        w0 = max(0, ip - 63)
        windows.append((sess[w0], sess[min(len(sess) - 1, it + 21)]))
        exit_d, already = None, False
        if weight.iloc[w0] <= thr + 1e-12:
            already = True
            j = w0
            while j > 0 and weight.iloc[j - 1] <= thr + 1e-12:
                j -= 1
            exit_d = sess[j]
        else:
            for j in range(w0 + 1, it + 1):
                if weight.iloc[j] <= thr + 1e-12 and weight.iloc[j - 1] > thr + 1e-12:
                    exit_d = sess[j]
                    break
        row = {"peak": str(pk.date()), "trough": str(tr.date()),
               "market_drawdown": float(mkt_level[tr] / mkt_level[pk] - 1)}
        r_pt = strat_r.iloc[ip + 1: it + 1]
        row["strategy_return_peak_to_trough"] = compound(r_pt.values)
        row["strategy_maxdd_peak_to_trough"] = max_drawdown(r_pt.values)
        row["drawdown_captured"] = (row["strategy_maxdd_peak_to_trough"] / row["market_drawdown"]
                                    if row["market_drawdown"] < 0 else None)
        if exit_d is None:
            row.update({"exit": "missed", "exit_lead_sessions": None})
            reentry = None
        else:
            ie = pos[exit_d]
            row["exit"] = "already_out" if already else str(exit_d.date())
            row["exit_date"] = str(exit_d.date())
            row["exit_lead_sessions"] = ip - ie            # positive = before the peak
            row["lost_before_exit"] = compound(strat_r.iloc[ip + 1: ie + 1].values) if ie > ip else 0.0
            reentry = None
            for j in range(ie + 1, len(sess)):
                if weight.iloc[j] >= thr:
                    reentry = sess[j]
                    break
            if reentry is not None:
                ir = pos[reentry]
                row["reentry"] = str(reentry.date())
                row["reentry_lag_sessions"] = ir - it      # negative = before the trough
                row["missed_after_trough"] = (compound(mkt_r.iloc[it + 1: ir + 1].values) if ir > it else 0.0)
            else:
                row["reentry"] = None
        end = min(len(sess) - 1, it + 126)
        mk = compound(mkt_r.iloc[it + 1: end + 1].values)
        sr = compound(strat_r.iloc[it + 1: end + 1].values)
        row["recovery_126_strategy"] = sr
        row["recovery_126_market"] = mk
        row["recovery_participation"] = sr / mk if abs(mk) > 1e-9 else None
        row["recovery_window_complete"] = bool(it + 126 <= len(sess) - 1)
        rows[name] = row
    # calm-period false pivots
    in_ep = pd.Series(False, index=sess)
    for a, b in windows:
        in_ep[(sess >= a) & (sess <= b)] = True
    valid = pd.Series(True, index=sess)
    if first_exec is not None:
        valid &= sess >= first_exec
    tail_start = sess[max(0, len(sess) - sealed_tail)] if sealed_tail else None
    if tail_start is not None:
        valid &= sess < tail_start
    calm_years = float(((~in_ep) & valid).sum()) / TRADING_DAYS
    false_n, whip_false, whip_all, cost, sealed_n = 0, 0, 0, 0.0, 0
    for a, b in _spells(weight, thr):
        if first_exec is not None and a < first_exec:
            continue                                   # start-up artefact (no position before first execution)
        # weight is the post-close weight, so the spell is out of the market for returns dated (a, b]
        held = (sess > a) & ((sess <= b) if b is not None else True)
        dur = int(held.sum())
        if tail_start is not None and (b is None or b > tail_start):
            sealed_n += 1                              # overlaps the sealed tail: unresolved, not a false pivot
            continue
        if dur < 21:
            whip_all += 1
        if in_ep[held].any():
            continue
        false_n += 1
        if dur < 21:
            whip_false += 1
        cost += compound(mkt_r[held].values) - compound(strat_r[held].values)
    return {"episodes": rows, "calm_years": calm_years, "false_pivots": false_n,
            "false_pivots_per_calm_year": false_n / calm_years if calm_years else None,
            "false_pivot_whipsaws_lt21": whip_false, "whipsaws_lt21_all_spells": whip_all,
            "spells_undetermined_sealed": sealed_n,
            "false_pivot_cost_per_calm_year": cost / calm_years if calm_years else None}
