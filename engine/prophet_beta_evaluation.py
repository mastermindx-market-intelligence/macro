"""Prophet beta-first evaluation — pure, deterministic, seeded harness.

Answers, under the FROZEN protocol header
``research/prophet_v4/beta_first_evaluation/protocol_header_v1.json`` (sha256 pinned in
``FROZEN_HEADER_SHA256``): does the incumbent Prophet plan book participate in the US market
(beta capture), and does sector context, member selection, or both add anything on top?

Everything here is pure: callers pass already-loaded frames (closes, membership, plans,
ledger) and receive plain dicts. No I/O except :func:`verify_header`, which reads the header
bytes so a run can refuse a header that is not the frozen one.

Conventions (all from the header — do not change without a new header version):

* daily close-to-close returns on the SPY session calendar, adjusted (total-return) closes;
* a rule decision at close ``t`` uses data dated ``<= t`` and executes at the close of
  ``t+1``; Prophet entries never precede the plan's publication session;
* costs are charged on traded notional at the trade close; uninvested weight earns BIL;
* the attribution bridge is a daily arithmetic ACCOUNTING identity (sector ETFs as
  benchmark segments), never a regression decomposition.

Authority: research/display only. Nothing here ranks, gates, sizes or trades.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

SCHEMA = "prophet.beta_evaluation/v1"
HEADER_REL_PATH = "research/prophet_v4/beta_first_evaluation/protocol_header_v1.json"
FROZEN_HEADER_SHA256 = "3be32166c7be5170c5153f7c6e66af02e988e88dda52167140e7ac12f30b2ada"
HEADER_COMMIT = "07f1c9cd8c0779934ae89e4da25ea97a5413e700"

SECTOR_ETFS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
BENCH = "SPY"
CASH = "BIL"
INCUMBENT_ERA = "anticipation-v1-2026-08-08"
HORIZONS = (10, 21, 42, 63)
TRADING_DAYS = 252
AUTHORITY = {"may_rank": False, "may_gate": False, "may_size": False,
             "may_trade": False, "may_escalate": False}
COMPARATOR_IDS = ("C1_passive_market", "C2_simple_participation", "C3_sector_allocation_only",
                  "C4_member_selection_only", "C5_joint_sector_and_name",
                  "C6_exact_incumbent_prophet", "C7_independent_emergence")
# Key-name substrings the lane-8 StrategyEvaluationResult validator forbids.
FORBIDDEN_KEY_SUBSTRINGS = ("alpha", "skill", "edge", "remaining_upside")


class HeaderMismatch(RuntimeError):
    """The protocol header on disk is not the frozen one; the run must refuse."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_header(path: str | Path, expected_sha256: str = FROZEN_HEADER_SHA256) -> dict:
    """Load the header and refuse unless its exact bytes hash to the frozen value."""
    raw = Path(path).read_bytes()
    got = sha256_bytes(raw)
    if got != expected_sha256:
        raise HeaderMismatch(f"protocol header sha256 {got} != frozen {expected_sha256}")
    return json.loads(raw)


# ─────────────────────────────── calendar helpers ────────────────────────────────

def session_on_or_after(cal: pd.DatetimeIndex, date) -> pd.Timestamp | None:
    i = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(date)), side="left"))
    return cal[i] if i < len(cal) else None


def session_after(cal: pd.DatetimeIndex, date) -> pd.Timestamp | None:
    i = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(date)), side="right"))
    return cal[i] if i < len(cal) else None


def session_on_or_before(cal: pd.DatetimeIndex, date) -> pd.Timestamp | None:
    i = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(date)), side="right")) - 1
    return cal[i] if i >= 0 else None


def publication_session(cal: pd.DatetimeIndex, price_basis_date, recorded_at) -> pd.Timestamp | None:
    """First session strictly after the price basis AND on/after the recorded (run) date."""
    a = session_after(cal, price_basis_date)
    b = session_on_or_after(cal, recorded_at)
    if a is None or b is None:
        return None
    return max(a, b)


# ─────────────────────────────── signals (no look-ahead) ─────────────────────────

def trailing_return(closes: pd.DataFrame, t: pd.Timestamp, n: int) -> pd.Series:
    """Total return over the last ``n`` sessions ending at close ``t`` using rows <= t only."""
    hist = closes.loc[:t]
    if len(hist) <= n:
        return pd.Series(np.nan, index=closes.columns)
    return hist.iloc[-1] / hist.iloc[-1 - n] - 1.0


def sector_rs(closes: pd.DataFrame, t: pd.Timestamp, n: int = 63) -> pd.Series:
    tr = trailing_return(closes[list(SECTOR_ETFS) + [BENCH]], t, n)
    return (tr[list(SECTOR_ETFS)] - tr[BENCH]).dropna()


def top_sectors(closes: pd.DataFrame, t: pd.Timestamp, k: int = 3, n: int = 63) -> list[str]:
    rs = sector_rs(closes, t, n)
    # deterministic tie-break: score desc, then ticker asc
    order = sorted(rs.items(), key=lambda kv: (-kv[1], kv[0]))
    return [s for s, _ in order[:k]]


def sma_signal(closes: pd.Series, t: pd.Timestamp, n: int = 200) -> bool | None:
    hist = closes.loc[:t].dropna()
    if len(hist) < n:
        return None
    return bool(hist.iloc[-1] > hist.iloc[-n:].mean())


def style_weights(spy_r: pd.Series, etf_r: pd.DataFrame) -> pd.Series:
    """Non-negative least squares style weights of SPY on the sector ETFs, normalised to 1."""
    from scipy.optimize import nnls
    df = pd.concat([spy_r.rename("_y"), etf_r], axis=1).dropna()
    w, _ = nnls(df[etf_r.columns].to_numpy(), df["_y"].to_numpy())
    s = w.sum()
    if s <= 0:
        raise ValueError("style weights degenerate")
    return pd.Series(w / s, index=etf_r.columns)


# ─────────────────────────────── portfolio simulator ─────────────────────────────

@dataclass
class BookResult:
    net: pd.Series                 # daily net returns, dates[1:]
    gross: pd.Series
    cost: pd.Series                # cost leg (net - gross), <= 0
    weights: pd.DataFrame          # holdings at the PRIOR close, applied to each day's return
    traded: pd.Series              # sum |dw| traded at each close (dates[0:])
    no_fill: int = 0
    stale_asset_days: int = 0
    invested: pd.Series = field(default_factory=pd.Series)


def simulate_book(dates: Sequence[pd.Timestamp], rets: pd.DataFrame, cash_r: pd.Series,
                  targets: Mapping[pd.Timestamp, Mapping[str, float]],
                  tradable: pd.DataFrame, cost_bps: Callable[[str], float]) -> BookResult:
    """Long-only book over ``dates`` (closes). Holdings set at close d_k earn d_{k+1}'s return.

    ``targets[d]`` = target weights after trading at close ``d``; dates without a target
    keep drifted holdings. A target asset not tradable at ``d`` is a no-fill: its weight
    stays in cash. Missing asset returns while held are treated as 0 (stale) and counted.
    """
    dates = list(dates)
    h: dict[str, float] = {}
    pending_cost = 0.0
    net, gross, cost, traded, wrows, inv = [], [], [], [], [], []
    no_fill = stale = 0
    for k, d in enumerate(dates):
        if k > 0:
            wrows.append(dict(h))
            g = 0.0
            for a, w in h.items():
                r = rets.at[d, a] if a in rets.columns else np.nan
                if not np.isfinite(r):
                    r = 0.0
                    stale += 1
                g += w * r
            c_w = 1.0 - sum(h.values())
            rc = cash_r.get(d, 0.0)
            rc = 0.0 if not np.isfinite(rc) else rc
            g += c_w * rc
            # drift
            if 1.0 + g > 0:
                nh = {}
                for a, w in h.items():
                    r = rets.at[d, a] if a in rets.columns else np.nan
                    r = 0.0 if not np.isfinite(r) else r
                    nh[a] = w * (1.0 + r) / (1.0 + g)
                h = nh
            n_ret = (1.0 + g) * (1.0 - pending_cost) - 1.0
            net.append(n_ret)
            gross.append(g)
            cost.append(n_ret - g)
            inv.append(sum(wrows[-1].values()))
            pending_cost = 0.0
        tgt = targets.get(d)
        if tgt is not None:
            clean: dict[str, float] = {}
            for a, w in tgt.items():
                if w <= 0:
                    continue
                ok = a in tradable.columns and bool(tradable.at[d, a])
                if ok:
                    clean[a] = float(w)
                elif a not in h:
                    no_fill += 1
                else:   # held but untradable today: keep current weight
                    clean[a] = h[a]
            tot = sum(clean.values())
            if tot > 1.0 + 1e-12:
                clean = {a: w / tot for a, w in clean.items()}
            names = set(h) | set(clean)
            dw = {a: clean.get(a, 0.0) - h.get(a, 0.0) for a in names}
            t_c = sum(abs(v) * cost_bps(a) / 1e4 for a, v in dw.items())
            traded.append(sum(abs(v) for v in dw.values()))
            # a cost incurred at close d reduces the value carried into d+1
            pending_cost = 1.0 - (1.0 - pending_cost) * (1.0 - t_c)
            h = {a: w for a, w in clean.items() if w > 0}
        else:
            traded.append(0.0)
    idx = pd.DatetimeIndex(dates[1:])
    wdf = pd.DataFrame(wrows, index=idx).fillna(0.0) if wrows else pd.DataFrame(index=idx)
    return BookResult(net=pd.Series(net, index=idx), gross=pd.Series(gross, index=idx),
                      cost=pd.Series(cost, index=idx), weights=wdf,
                      traded=pd.Series(traded, index=pd.DatetimeIndex(dates)),
                      no_fill=no_fill, stale_asset_days=stale,
                      invested=pd.Series(inv, index=idx))


# ─────────────────────────────── rule comparators ────────────────────────────────

def rule_schedule(cal: pd.DatetimeIndex, first_decision, last_exec, every: int) -> list[tuple]:
    """[(decision_close, execution_close)] every ``every`` sessions, executing at t+1."""
    i0 = cal.get_loc(pd.Timestamp(first_decision))
    out = []
    i = i0
    while i + 1 < len(cal) and cal[i + 1] <= pd.Timestamp(last_exec):
        out.append((cal[i], cal[i + 1]))
        i += every
    return out


def targets_c1(sched) -> dict:
    return {sched[0][1]: {BENCH: 1.0}}


def targets_c2(closes: pd.DataFrame, cal, first_decision, last_exec) -> dict:
    out = {}
    for t, x in rule_schedule(cal, first_decision, last_exec, 1):
        sig = sma_signal(closes[BENCH], t)
        out[x] = {BENCH: 1.0} if sig else {}
    return out


def targets_c3(closes, cal, first_decision, last_exec, every=21) -> tuple[dict, dict]:
    out, picks = {}, {}
    for t, x in rule_schedule(cal, first_decision, last_exec, every):
        top = top_sectors(closes, t)
        picks[x] = top
        out[x] = {s: 1.0 / len(top) for s in top}
    return out, picks


def member_universe(t: pd.Timestamp, pit: pd.DataFrame, sector_of: Mapping[str, str],
                    closes: pd.DataFrame, raw: pd.DataFrame, min_hist: int = 126,
                    min_price: float = 5.0) -> tuple[dict[str, str], dict[str, int]]:
    """{ticker: sector_etf} eligible at close t, plus counts by exclusion reason."""
    act = pit[(pit["start_date"] <= t) & (pit["end_date"].isna() | (pit["end_date"] > t))]
    counts = {"pit_active": 0, "no_price_file": 0, "no_sector": 0,
              "short_history": 0, "price_below_min": 0, "eligible": 0}
    elig: dict[str, str] = {}
    hist = closes.loc[:t]
    for tk in sorted(set(act["ticker"])):
        counts["pit_active"] += 1
        if tk not in closes.columns:
            counts["no_price_file"] += 1
            continue
        etf = sector_of.get(tk)
        if not etf:
            counts["no_sector"] += 1
            continue
        if hist[tk].notna().sum() < min_hist or not np.isfinite(hist[tk].iloc[-1]):
            counts["short_history"] += 1
            continue
        rp = raw.at[t, tk] if tk in raw.columns else np.nan
        if not np.isfinite(rp) or rp < min_price:
            counts["price_below_min"] += 1
            continue
        elig[tk] = etf
        counts["eligible"] += 1
    return elig, counts


def member_picks(t, elig: Mapping[str, str], closes: pd.DataFrame, n: int = 63,
                 frac: float = 0.10, k_min: int = 3) -> dict[str, list[str]]:
    cols = sorted(set(elig) | set(SECTOR_ETFS))
    tr = trailing_return(closes[cols], t, n)
    by_sector: dict[str, list[tuple[float, str]]] = {}
    for tk, etf in elig.items():
        s = tr.get(tk, np.nan) - tr.get(etf, np.nan)
        if np.isfinite(s):
            by_sector.setdefault(etf, []).append((s, tk))
    out = {}
    for etf, lst in by_sector.items():
        lst.sort(key=lambda v: (-v[0], v[1]))
        k = max(k_min, math.ceil(frac * len(lst)))
        out[etf] = [tk for _, tk in lst[:k]]
    return out


def targets_c4_c5(closes, raw, cal, first_decision, last_exec, pit, sector_of,
                  sector_w: pd.Series, every=21) -> tuple[dict, dict, list]:
    c4, c5, audit = {}, {}, []
    for t, x in rule_schedule(cal, first_decision, last_exec, every):
        elig, counts = member_universe(t, pit, sector_of, closes, raw)
        picks = member_picks(t, elig, closes)
        w4: dict[str, float] = {}
        live = {e: sector_w.get(e, 0.0) for e in picks if sector_w.get(e, 0.0) > 0}
        z = sum(live.values())
        for e, ws in live.items():
            for tk in picks[e]:
                w4[tk] = w4.get(tk, 0.0) + ws / z / len(picks[e])
        top = top_sectors(closes, t)
        w5: dict[str, float] = {}
        tops = [e for e in top if picks.get(e)]
        for e in tops:
            for tk in picks[e]:
                w5[tk] = w5.get(tk, 0.0) + 1.0 / len(tops) / len(picks[e])
        c4[x], c5[x] = w4, w5
        audit.append({"decision": str(t.date()), "execution": str(x.date()), **counts,
                      "c4_names": len(w4), "c5_names": len(w5), "c5_sectors": tops})
    return c4, c5, audit


# ─────────────────────────────── Prophet positions ───────────────────────────────

@dataclass
class Position:
    plan_id: str
    asset: str
    sector_etf: str | None
    entry: pd.Timestamp
    exit: pd.Timestamp
    censored: bool
    exit_basis: str
    admission_class: str | None
    aligned: bool | None           # sector in C3 top-3 at the price-basis close


def _ledger_close(ledger: Mapping[str, Mapping], pid: str) -> str | None:
    r = ledger.get(pid)
    return r.get("close_date") if r else None


def build_positions(plans: Iterable[Mapping], ledger: Mapping[str, Mapping], cal: pd.DatetimeIndex,
                    closes: pd.DataFrame, raw: pd.DataFrame, sector_of_plan: Mapping[str, str | None],
                    window_start, window_end, excluded_ids: frozenset = frozenset(),
                    era: str = INCUMBENT_ERA) -> tuple[list[Position], dict[str, int], dict]:
    """Prophet-as-built positions (C6 definition in the header) + exclusion counts."""
    ws, we = pd.Timestamp(window_start), pd.Timestamp(window_end)
    reasons: dict[str, int] = {}
    pos: list[Position] = []
    extra = {"era_plans": 0, "entry_shifted_to_publication": 0, "censored": 0,
             "exit_ledger": 0, "exit_mechanical": 0, "pub_sessions": {}}

    def bump(r):
        reasons[r] = reasons.get(r, 0) + 1

    for p in plans:
        if p.get("selection_era") != era:
            continue
        extra["era_plans"] += 1
        pid, asset = p["id"], p["asset"]
        if pid in excluded_ids:
            bump("excluded_by_sensitivity")
            continue
        if p.get("direction") != "BULL":
            bump("not_long")
            continue
        if not p.get("recorded_at") or not p.get("price_basis_date"):
            bump("no_publication_clock")
            continue
        P = publication_session(cal, p["price_basis_date"], p["recorded_at"])
        if P is None or P > we:
            bump("published_after_window")
            continue
        extra["pub_sessions"][pid] = P
        zs = p.get("entry_zone_state") or {}
        state = zs.get("state")
        led = ledger.get(pid)
        if led is not None and led.get("outcome") == "NO_ENTRY":
            bump("recorded_no_entry")
            continue
        if state not in ("filled", "converted"):
            bump(f"not_entered_zone_{state or 'none'}")
            continue
        fd = zs.get("filled_date")
        E = P
        if fd:
            fe = session_on_or_after(cal, fd)
            if fe is not None and fe > P:
                E = fe
            elif fe is not None and fe < P:
                extra["entry_shifted_to_publication"] += 1
        if E > we:
            bump("fill_after_window")
            continue
        if asset not in closes.columns or not np.isfinite(closes.at[E, asset]):
            bump("no_fill_no_close_at_entry")
            continue
        etf = sector_of_plan.get(pid)
        # exit
        cd = _ledger_close(ledger, pid)
        if cd:
            X = session_on_or_before(cal, cd)
            basis = "recorded_close_date"
        else:
            X, basis = _mechanical_exit(p, E, cal, raw, we)
        censored = False
        if X is None or X > we:
            X, censored = we, True
        if X <= E:
            bump("resolved_at_or_before_follower_fill")
            continue
        if censored:
            extra["censored"] += 1
        elif basis == "recorded_close_date":
            extra["exit_ledger"] += 1
        else:
            extra["exit_mechanical"] += 1
        aligned = None
        if etf:
            t0 = session_on_or_before(cal, p["price_basis_date"])
            aligned = etf in top_sectors(closes, t0) if t0 is not None else None
        pos.append(Position(pid, asset, etf, E, X, censored, basis if not censored else "censored_window_end",
                            p.get("admission_class"), aligned))
    return pos, reasons, extra


def _mechanical_exit(p, E, cal, raw, we):
    """Published geometry: first close <= invalidation or >= T1, or the horizon date."""
    asset = p["asset"]
    inv = p.get("invalidation")
    tg = (p.get("targets") or [None])[0]
    hz = p.get("horizon_days")
    hz_date = (pd.Timestamp(p["price_basis_date"]) + pd.Timedelta(days=int(hz))) if hz else None
    if asset not in raw.columns:
        return None, "mechanical_no_raw"
    for d in cal[(cal > E) & (cal <= we)]:
        c = raw.at[d, asset]
        if np.isfinite(c):
            if inv is not None and c <= inv:
                return d, "mechanical_invalidation"
            if tg is not None and c >= tg:
                return d, "mechanical_t1"
        if hz_date is not None and d >= hz_date:
            return d, "mechanical_horizon"
    return None, "open"


def prophet_targets(positions: Sequence[Position], dates: Sequence[pd.Timestamp]) -> dict:
    out = {}
    for d in dates:
        live = sorted({p.asset for p in positions if p.entry <= d < p.exit})
        out[d] = {a: 1.0 / len(live) for a in live} if live else {}
    return out


def asset_sector_map(positions: Sequence[Position]) -> dict[str, str | None]:
    m: dict[str, str | None] = {}
    for p in positions:
        m.setdefault(p.asset, p.sector_etf)
    return m


# ─────────────────────────────── metrics ─────────────────────────────────────────

def compound(r: np.ndarray) -> float:
    return float(np.prod(1.0 + np.asarray(r)) - 1.0)


def beta_ols(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x); y = np.asarray(y)
    vx = np.var(x)
    if vx <= 0:
        return float("nan"), float("nan")
    b = float(np.mean((x - x.mean()) * (y - y.mean())) / vx)
    return b, float(y.mean() - b * x.mean())


def capture(rp: np.ndarray, rm: np.ndarray, up: bool) -> float | None:
    m = rm > 0 if up else rm < 0
    n = int(m.sum())
    if n == 0:
        return None
    gm_m = (np.prod(1 + rm[m])) ** (1.0 / n) - 1
    gm_p = (np.prod(1 + rp[m])) ** (1.0 / n) - 1
    if abs(gm_m * n) < 0.01:
        return None
    return float(gm_p / gm_m)


def max_drawdown(r: np.ndarray) -> float:
    v = np.cumprod(1 + np.asarray(r))
    peak = np.maximum.accumulate(np.concatenate([[1.0], v]))[1:]
    return float(np.min(v / peak - 1.0)) if len(v) else 0.0


def point_metrics(rp: np.ndarray, rm: np.ndarray, rc: np.ndarray) -> dict:
    n = len(rp)
    b, a = beta_ols(rp - rc, rm - rc)
    tot, totm = compound(rp), compound(rm)
    return {
        "total_net_return": tot,
        "ann_return": (1 + tot) ** (TRADING_DAYS / n) - 1 if n else None,
        "excess_total_vs_spy": tot - totm,
        "ann_excess_vs_spy": float(np.mean(rp - rm) * TRADING_DAYS),
        "beta_vs_market": b,
        "intercept_ann": a * TRADING_DAYS if np.isfinite(a) else None,
        "tracking_error": float(np.std(rp - rm, ddof=1) * math.sqrt(TRADING_DAYS)) if n > 1 else None,
        "upside_capture": capture(rp, rm, True),
        "downside_capture": capture(rp, rm, False),
        "max_drawdown": max_drawdown(rp),
        "ann_excess_over_cash": float(np.mean(rp - rc) * TRADING_DAYS),
    }


def stationary_bootstrap_indices(n: int, B: int, mean_block: float, seed: int) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (B x n), deterministic for a seed."""
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=B)
    jumps = rng.random((B, n)) < p
    fresh = rng.integers(0, n, size=(B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jumps[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _ci(a: np.ndarray, level=0.95) -> list[float] | None:
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return None
    lo, hi = np.quantile(a, [(1 - level) / 2, 1 - (1 - level) / 2])
    return [float(lo), float(hi)]


def bootstrap_vs(rp: np.ndarray, rref: np.ndarray, rm: np.ndarray, rc: np.ndarray,
                 idx: np.ndarray) -> dict:
    """CIs for strategy-vs-reference differentials plus strategy beta/capture (paired rows)."""
    d = rp - rref
    obs = float(d.mean())
    P, R, M, C = rp[idx], rref[idx], rm[idx], rc[idx]
    D = P - R
    means = D.mean(axis=1)
    tot = np.prod(1 + P, axis=1) - np.prod(1 + R, axis=1)
    y, x = P - C, M - C
    xm, ym = x.mean(axis=1, keepdims=True), y.mean(axis=1, keepdims=True)
    vx = ((x - xm) ** 2).mean(axis=1)
    betas = np.where(vx > 0, ((x - xm) * (y - ym)).mean(axis=1) / np.where(vx > 0, vx, 1), np.nan)
    ups, downs = [], []
    for b in range(idx.shape[0]):
        u = capture(P[b], M[b], True)
        dn = capture(P[b], M[b], False)
        ups.append(np.nan if u is None else u)
        downs.append(np.nan if dn is None else dn)
    p = float(np.mean((means - obs) >= obs))
    return {
        "mean_daily_diff": obs,
        "ann_diff": obs * TRADING_DAYS,
        "ann_diff_ci95": [v * TRADING_DAYS for v in _ci(means)],
        "total_diff": compound(rp) - compound(rref),
        "total_diff_ci95": _ci(tot),
        "p_one_sided": p,
        "beta_ci95": _ci(betas),
        "upside_capture_ci95": _ci(np.array(ups)),
        "downside_capture_ci95": _ci(np.array(downs)),
    }


def holm(pvals: Mapping[str, float], alpha: float = 0.05) -> dict[str, dict]:
    items = sorted(pvals.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    out, running, stop = {}, 0.0, False
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        rej = (not stop) and p <= alpha / (m - i)
        if not rej:
            stop = True
        out[k] = {"p_raw": p, "p_holm": adj, "reject_h0": rej}
    return out


def wilson(k: int, n: int, z: float = 1.959964) -> list[float] | None:
    if n == 0:
        return None
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return [c - h, c + h]


def position_hits(positions: Sequence[Position], closes: pd.DataFrame) -> dict:
    k = n = 0
    for p in positions:
        a0, a1 = closes.at[p.entry, p.asset], closes.at[p.exit, p.asset]
        if not np.isfinite(a1):
            a1 = closes.loc[:p.exit, p.asset].dropna().iloc[-1]
        s0, s1 = closes.at[p.entry, BENCH], closes.at[p.exit, BENCH]
        if not all(np.isfinite([a0, a1, s0, s1])):
            continue
        n += 1
        k += int(a1 / a0 > s1 / s0)
    return {"n": n, "beat_spy": k, "rate": (k / n) if n else None, "ci95_wilson": wilson(k, n)}


# ─────────────────────────────── attribution bridge ──────────────────────────────

def attribution_bridge(book: BookResult, rets: pd.DataFrame, cash_r: pd.Series,
                       sector_of_asset: Mapping[str, str | None]) -> dict:
    """Daily arithmetic accounting identity; legs sum exactly to sum of daily net returns."""
    W = book.weights
    idx = W.index
    rm = rets.loc[idx, BENCH].fillna(0.0)
    mk = sec = sel = 0.0
    unmapped_w = 0.0
    for a in W.columns:
        w = W[a]
        ra = rets.loc[idx, a].fillna(0.0) if a in rets.columns else pd.Series(0.0, index=idx)
        e = sector_of_asset.get(a)
        if e and e in rets.columns:
            re_ = rets.loc[idx, e].fillna(0.0)
        else:
            re_ = rm   # unmapped: whole active return lands in selection, disclosed
            unmapped_w += float(w.sum())
        mk += float((w * rm).sum())
        sec += float((w * (re_ - rm)).sum())
        sel += float((w * (ra - re_)).sum())
    cw = 1.0 - W.sum(axis=1) if len(W.columns) else pd.Series(1.0, index=idx)
    cash = float((cw * cash_r.reindex(idx).fillna(0.0)).sum())
    costs = float(book.cost.sum())
    s = float(book.net.sum())
    gross_check = mk + sec + sel + cash + costs
    bench_sum = float(rm.sum())
    return {
        "method": "daily_arithmetic_accounting_identity_sector_etf_segments",
        "linking": "unlinked arithmetic sum of daily contributions; compounding residual shown",
        "legs": {
            "market_participation": mk,
            "sector_allocation": sec,
            "selection_within_sector": sel,
            "cash": cash,
            "costs": costs,
        },
        "sum_of_daily_net_returns": s,
        "identity_error": gross_check - s,
        "compounded_total_net_return": compound(book.net.to_numpy()),
        "compounding_residual": compound(book.net.to_numpy()) - s,
        "benchmark_sum_of_daily_returns": bench_sum,
        "gap_vs_benchmark_bridge": {
            "benchmark": bench_sum,
            "uninvested_market_shortfall": mk - bench_sum,
            "sector_allocation": sec,
            "selection_within_sector": sel,
            "cash": cash,
            "costs": costs,
            "strategy": s,
        },
        "unmapped_sector_weight_days": unmapped_w,
    }


def asset_contributions(book: BookResult, rets: pd.DataFrame) -> pd.Series:
    """Sum over days of weight x asset return per asset (gross, before costs), sorted asc."""
    W = book.weights
    if W.empty:
        return pd.Series(dtype=float)
    R = rets.reindex(index=W.index, columns=W.columns).fillna(0.0)
    return (W * R).sum().sort_values()


def concurrency(positions: Sequence[Position], dates: Sequence[pd.Timestamp]) -> dict:
    c = np.array([sum(p.entry <= d < p.exit for p in positions) for d in list(dates)[:-1]])
    if len(c) == 0:
        return {}
    return {"min": int(c.min()), "median": float(np.median(c)), "max": int(c.max()),
            "first_5_sessions": [int(v) for v in c[:5]]}


# ─────────────────────────────── event study ─────────────────────────────────────

def event_study(pub: Mapping[str, pd.Timestamp], plan_asset: Mapping[str, str],
                plan_etf: Mapping[str, str | None], closes: pd.DataFrame, cal: pd.DatetimeIndex,
                last_close, B: int, seed: int, horizons=HORIZONS) -> dict:
    """Policy-free fixed-horizon marks with the existing next-bar ruler (engine.grading)."""
    from engine.grading import forward_metrics
    last_close = pd.Timestamp(last_close)
    cl = closes.loc[:last_close]
    rows = []
    for pid, P in pub.items():
        sig = session_on_or_before(cal, P - pd.Timedelta(days=1))
        a, e = plan_asset[pid], plan_etf.get(pid)
        if a not in cl.columns or sig is None:
            continue
        fa = forward_metrics(cl[a].dropna(), sig, horizons)
        fm = forward_metrics(cl[BENCH].dropna(), sig, horizons)
        fe = forward_metrics(cl[e].dropna(), sig, horizons) if e in cl.columns else {}
        for h in horizons:
            ra, rm = fa.get(f"fwd_ret_{h}"), fm.get(f"fwd_ret_{h}")
            if ra is None or rm is None:
                continue
            re_ = fe.get(f"fwd_ret_{h}") if fe else None
            rows.append({"plan": pid, "date": P, "h": h, "x": ra - rm,
                         "sec": (re_ - rm) if re_ is not None else np.nan,
                         "sel": (ra - re_) if re_ is not None else np.nan})
    df = pd.DataFrame(rows)
    out = {}
    rng = np.random.default_rng(seed)
    for h in horizons:
        sub = df[df["h"] == h] if len(df) else df
        if len(sub) == 0:
            out[str(h)] = {"n": 0, "status": "unmatured"}
            continue
        dates = np.array(sorted(sub["date"].unique()))
        groups = {d: sub[sub["date"] == d] for d in dates}
        res = {"n": int(len(sub)), "n_dates": int(len(dates)), "status": "matured_subset"}
        for col, name in (("x", "excess_vs_spy"), ("sec", "sector_etf_minus_spy"),
                          ("sel", "stock_minus_sector_etf")):
            v = sub[col].dropna()
            boots = np.empty(B)
            draws = rng.integers(0, len(dates), size=(B, len(dates)))
            sums = np.array([groups[d][col].sum(skipna=True) for d in dates])
            cnts = np.array([groups[d][col].notna().sum() for d in dates])
            boots = sums[draws].sum(axis=1) / np.maximum(cnts[draws].sum(axis=1), 1)
            res[name] = {"mean": float(v.mean()) if len(v) else None,
                         "median": float(v.median()) if len(v) else None,
                         "n": int(len(v)), "ci95_date_cluster": _ci(boots)}
        hit = int((sub["x"] > 0).sum())
        res["share_beating_spy"] = {"k": hit, "n": int(len(sub)), "rate": hit / len(sub),
                                    "ci95_wilson_naive": wilson(hit, len(sub))}
        out[str(h)] = res
    return out


# ─────────────────────────────── release level ───────────────────────────────────

def _crit(name, required, observed, met):
    return {"criterion": name, "required": required, "observed": observed, "met": bool(met)}


def release_assessment(header: Mapping, *, window_sessions: int, spy_mdd: float,
                       resolved_positions: int, c6: Mapping, c6_vs_c1: Mapping,
                       c6_stress: Mapping, contrasts: Mapping[str, Mapping],
                       stress_contrasts: Mapping[str, Mapping], k3_vs_exposure: Mapping,
                       l0_checks: Mapping[str, Any]) -> dict:
    g = header["acceptance"]["global_minimum_for_L1"]
    glob = [
        _crit("window_sessions", f">= {g['window_sessions_min']}", window_sessions,
              window_sessions >= g["window_sessions_min"]),
        _crit("spy_drawdown_present", f"<= -{g['spy_peak_to_trough_drawdown_present_min']}", spy_mdd,
              spy_mdd <= -g["spy_peak_to_trough_drawdown_present_min"]),
        _crit("resolved_positions", f">= {g['resolved_positions_min']}", resolved_positions,
              resolved_positions >= g["resolved_positions_min"]),
    ]
    glob_ok = all(c["met"] for c in glob)
    l0 = [_crit("era_plans_classified_share", ">= 0.90", l0_checks["classified_share"],
                l0_checks["classified_share"] >= 0.90),
          _crit("entered_positions_priced_share", ">= 0.95", l0_checks["priced_share"],
                l0_checks["priced_share"] >= 0.95)]
    l0_ok = all(c["met"] for c in l0)
    bci = c6_vs_c1.get("beta_ci95") or [float("nan")] * 2
    uci = c6_vs_c1.get("upside_capture_ci95") or [float("nan")] * 2
    up = c6.get("upside_capture")
    jobA = [
        _crit("beta_point_in", "[0.8, 1.3]", c6["beta_vs_market"], 0.8 <= c6["beta_vs_market"] <= 1.3),
        _crit("beta_ci_lower", ">= 0.6", bci[0], bci[0] >= 0.6),
        _crit("upside_capture_point", ">= 0.90", up, up is not None and up >= 0.90),
        _crit("upside_capture_ci_lower", ">= 0.75", uci[0], uci[0] >= 0.75),
        _crit("mean_invested", ">= 0.80", c6["mean_invested"], c6["mean_invested"] >= 0.80),
        _crit("ann_excess_ci_lower_noninferior", "> -0.03", c6_vs_c1["ann_diff_ci95"][0],
              c6_vs_c1["ann_diff_ci95"][0] > -0.03),
        _crit("noninferior_at_2x_costs_point", "> -0.03", c6_stress["ann_diff"], c6_stress["ann_diff"] > -0.03),
    ]

    def job(keys, extra=None):
        crits = []
        for k in keys:
            c, s = contrasts[k], stress_contrasts[k]
            crits += [_crit(f"{k}_holm_p", "< 0.05", c["p_holm"], c["p_holm"] < 0.05),
                      _crit(f"{k}_ann_diff_point", ">= 0.02", c["ann_diff"], c["ann_diff"] >= 0.02),
                      _crit(f"{k}_holds_at_2x_costs", "> 0", s["ann_diff"], s["ann_diff"] > 0)]
        if extra:
            crits += extra
        return crits

    jobB = job(["K3", "K5", "K7"], [_crit("K3_vs_exposure_matched_ci_lower", "> 0",
                                         k3_vs_exposure["ann_diff_ci95"][0],
                                         k3_vs_exposure["ann_diff_ci95"][0] > 0)])
    jobC = job(["K2", "K4", "K6"])

    def level(crits, per_contrast=False):
        if not l0_ok:
            return "NOT_EVALUATED_SOURCE_INCOMPLETE"
        if not glob_ok:
            return "L0_descriptive"
        return "L1_accepted_historical" if all(c["met"] for c in crits) else "L0_descriptive"

    return {
        "levels_defined": ["L0_descriptive", "L1_accepted_historical", "L2_prospective_shadow",
                           "L3_approved_product_prediction"],
        "l0_source_checks": l0, "l0_met": l0_ok,
        "global_minimum_for_L1": glob, "global_minimum_met": glob_ok,
        "jobs": {
            "A_market_participation": {"level": level(jobA), "criteria": jobA},
            "B_sector_context": {"level": level(jobB), "criteria": jobB},
            "C_member_selection": {"level": level(jobC), "criteria": jobC},
        },
        "cap_rule": "below the global minimum every performance job is capped at L0_descriptive regardless of point estimates (header section 6)",
        "l2_l3_note": "L2 needs L1 plus >= 126 post-2026-11-11 sessions under this header hash; L3 is never assignable by this harness",
    }


def assert_no_forbidden_keys(obj, path="") -> list[str]:
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(s in str(k).lower() for s in FORBIDDEN_KEY_SUBSTRINGS):
                bad.append(f"{path}/{k}")
            bad += assert_no_forbidden_keys(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += assert_no_forbidden_keys(v, f"{path}[{i}]")
    return bad


def json_safe(o):
    if isinstance(o, dict):
        return {str(k): json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if not math.isfinite(f) else round(f, 8)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return str(o.date())
    return o
