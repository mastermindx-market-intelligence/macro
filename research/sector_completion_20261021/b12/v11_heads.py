"""B12 v1.1 — run the PREDECLARED four-head + seven-comparator protocol.

Protocol: research/sector_completion_20261021/B12_V11_HEADS_PROTOCOL.md (committed before this
script existed). Research only: off the render path, no ledger write, no payload mutation.
Nothing here ranks, gates, sizes or trades.

    python3 research/sector_completion_20261021/b12/v11_heads.py --tape-dir <dir with data/yahoo> \
        --out research/sector_completion_20261021/b12/v11_heads_result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine.cycle_ontology import TurnParams, detect_turns  # noqa: E402

SECTORS = ["XLK", "XLE", "XLF", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC"]
PARAMS = TurnParams(pct=14.0, basis="close_price")
STEP = 20            # decision cadence and horizon (completed sessions)
WARMUP = 504         # first decision at the 505th session (index 504)
TEST_FROM = pd.Timestamp("2008-01-01")
MIN_CELL = 30
QS = (0.10, 0.25, 0.50, 0.75, 0.90)
COST_RT = 0.0010     # H1 round trip
COST_SIDE = 0.0005   # comparators, per side
N_BOOT, SEED, BH_Q = 2000, 11, 0.10
HEADS = ("H1_remaining_return_distribution", "H2_adverse_tail",
         "H3_target_before_invalidation", "H4_transition_time")


def load(tape_dir: Path, t: str) -> pd.DataFrame:
    d = pd.read_parquet(tape_dir / "data" / "yahoo" / f"{t}.parquet")
    d.index = pd.to_datetime(d.index)
    return d.sort_index()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── turns + PIT check ────────────────────────────────────────────────────────
def confirmed_turns(close: pd.Series, sid: str) -> list[dict]:
    return [t for t in detect_turns(close, series_id=sid, params=PARAMS) if not t["provisional"]]


def pit_check(close: pd.Series, sid: str, full: list[dict], dates) -> int:
    """Truncated detection at every decision date must equal the full-tape set filtered by
    confirmed_at <= t. Returns the number of dates checked; raises on any mismatch."""
    key = [(t["date"], t["k"], t["confirmed_at"]) for t in full]
    for t in dates:
        trunc = confirmed_turns(close.loc[:t], sid)
        want = [k for k in key if k[2] <= str(t.date())]
        got = [(x["date"], x["k"], x["confirmed_at"]) for x in trunc]
        if got != want:
            raise SystemExit(f"PIT check failed: {sid} at {t.date()}: {got[-3:]} vs {want[-3:]}")
    return len(dates)


# ── windows ─────────────────────────────────────────────────────────────────
def age_bucket(a: int) -> str:
    return "A1" if a < 63 else ("A2" if a < 189 else "A3")


def build_windows(sid: str, df: pd.DataFrame, spy: pd.Series):
    px = df["close_price"].dropna()
    tr = df["close"].reindex(px.index)
    spy_tr = spy.reindex(px.index)
    full = confirmed_turns(px, sid)
    idx = px.index
    dates = [idx[i] for i in range(WARMUP, len(idx), STEP)]
    n_pit = pit_check(px, sid, full, dates)
    logr = np.log(tr).diff()
    rows = []
    for i in range(WARMUP, len(idx), STEP):
        t = idx[i]
        mature = i + 21 < len(idx)
        known = [x for x in full if x["confirmed_at"] <= str(t.date())]
        last = known[-1] if known else None
        direction = None if last is None else ("up" if last["k"] == "trough" else "down")
        age = None
        if last is not None:
            age = int(i - idx.get_loc(pd.Timestamp(last["date"])))
        sig = float(logr.iloc[max(1, i - 251):i + 1].std() * np.sqrt(20))
        row = {"sid": sid, "t": t, "i": i, "direction": direction, "age": age,
               "cell": None if direction is None else f"{direction}:{age_bucket(age)}",
               "sigma20": sig, "mature": mature}
        if mature and np.isfinite(spy_tr.iloc[i + 1]) and np.isfinite(spy_tr.iloc[i + 21]):
            e, x = i + 1, i + 21
            r_etf = tr.iloc[x] / tr.iloc[e] - 1.0
            r_spy = spy_tr.iloc[x] / spy_tr.iloc[e] - 1.0
            path = tr.iloc[e:x + 1].to_numpy() / tr.iloc[e] - 1.0
            row["y1"] = float(r_etf - r_spy - COST_RT)
            row["y2"] = int(path.min() <= -1.5 * sig)
            hit_t = np.where(path >= sig)[0]
            hit_i = np.where(path <= -sig)[0]
            ft = hit_t[0] if len(hit_t) else 10**9
            fi = hit_i[0] if len(hit_i) else 10**9
            row["y3"] = int(ft < fi)
            row["y3_outcome"] = "target" if ft < fi else ("invalidation" if fi < ft else
                                                           ("same_close" if ft < 10**9 else "neither"))
            nxt = [x2 for x2 in full if x2["confirmed_at"] > str(t.date())]
            end = str(idx[i + 20].date())
            row["y4"] = int(bool(nxt) and nxt[0]["confirmed_at"] <= end)
        rows.append(row)
    return rows, full, n_pit


# ── scoring ─────────────────────────────────────────────────────────────────
def pinball(y: float, q: np.ndarray) -> float:
    qs = np.array(QS)
    d = y - q
    return float(np.mean(np.maximum(qs * d, (qs - 1) * d)))


def forecasts(W: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-sector-out, time-respecting forecasts for every test window."""
    M = W[W.mature & W.y1.notna()].copy()
    out = []
    test = W[(W.t >= TEST_FROM) & W.mature & W.y1.notna()]
    for w in test.itertuples():
        pool = M[(M.sid != w.sid) & (M.exit_t <= w.t)]
        rec = {"sid": w.sid, "t": w.t, "cell": w.cell, "y1": w.y1, "y2": w.y2, "y3": w.y3,
               "y4": w.y4}
        if w.cell is None or len(pool) == 0:
            rec["abstain"] = True
            out.append(rec)
            continue
        cellp = pool[pool.cell == w.cell]
        rec["n_cell"] = len(cellp)
        if len(cellp) < MIN_CELL:
            rec["abstain"] = True
            out.append(rec)
            continue
        rec["abstain"] = False
        qm = np.quantile(cellp.y1, QS)
        qb = np.quantile(pool.y1, QS)
        rec["pl_m"], rec["pl_b"] = pinball(w.y1, qm), pinball(w.y1, qb)
        rec["in_band"] = int(qm[0] <= w.y1 <= qm[-1])
        for h in ("y2", "y3", "y4"):
            fm = (cellp[h].sum() + 1) / (len(cellp) + 2)
            fb = (pool[h].sum() + 1) / (len(pool) + 2)
            rec[f"f_{h}"], rec[f"b_{h}"] = fm, fb
            rec[f"bs_m_{h}"], rec[f"bs_b_{h}"] = (fm - getattr(w, h)) ** 2, (fb - getattr(w, h)) ** 2
        out.append(rec)
    return pd.DataFrame(out)


def skill(F: pd.DataFrame, head: str) -> float:
    if head == HEADS[0]:
        return 1 - F.pl_m.sum() / F.pl_b.sum()
    h = {HEADS[1]: "y2", HEADS[2]: "y3", HEADS[3]: "y4"}[head]
    return 1 - F[f"bs_m_{h}"].sum() / F[f"bs_b_{h}"].sum()


def boot(F: pd.DataFrame, head: str, rng) -> tuple[float, float, float]:
    years = F.t.dt.year
    uy = np.array(sorted(years.unique()))
    groups = {y: F[years == y] for y in uy}
    vals = []
    for _ in range(N_BOOT):
        pick = rng.choice(uy, size=len(uy), replace=True)
        vals.append(skill(pd.concat([groups[y] for y in pick]), head))
    vals = np.array(vals)
    return float(np.quantile(vals, 0.05)), float(np.quantile(vals, 0.95)), float(np.mean(vals <= 0))


def judge(Fall: pd.DataFrame, rng) -> dict:
    F = Fall[~Fall.abstain]
    cov = len(F) / len(Fall) if len(Fall) else 0.0
    res = {}
    for head in HEADS:
        r = {"n_test_windows": int(len(Fall)), "n_scored": int(len(F)), "coverage": round(cov, 4),
             "n_dates": int(F.t.nunique()), "n_years": int(F.t.dt.year.nunique())}
        if len(F) == 0:
            res[head] = r
            continue
        r["skill"] = round(float(skill(F, head)), 5)
        lo, hi, p = boot(F, head, rng)
        r["ci90"], r["p_one_sided"] = [round(lo, 5), round(hi, 5)], round(p, 4)
        if head == HEADS[0]:
            r["band_coverage_q10_q90"] = round(float(F.in_band.mean()), 4)
            r["calibration_ok"] = 0.72 <= r["band_coverage_q10_q90"] <= 0.88
            r["pinball_model"], r["pinball_baseline"] = round(F.pl_m.mean(), 6), round(F.pl_b.mean(), 6)
        else:
            h = {HEADS[1]: "y2", HEADS[2]: "y3", HEADS[3]: "y4"}[head]
            f, y = F[f"f_{h}"].to_numpy(), F[h].to_numpy().astype(float)
            r["observed_rate"], r["mean_forecast"] = round(float(y.mean()), 4), round(float(f.mean()), 4)
            r["mean_baseline"] = round(float(F[f"b_{h}"].mean()), 4)
            # Protocol §4 rule 6: forecast-DECILE reliability slope (OLS of decile mean outcome
            # on decile mean forecast). The raw-window OLS slope is kept as a diagnostic only.
            raw = float(np.polyfit(f, y, 1)[0]) if np.var(f) > 1e-12 else float("nan")
            r["reliability_slope_raw_windows"] = None if not np.isfinite(raw) else round(raw, 3)
            bins = pd.qcut(pd.Series(f).rank(method="first"), 10, labels=False)
            bf = pd.Series(f).groupby(bins).mean().to_numpy()
            by = pd.Series(y).groupby(bins).mean().to_numpy()
            slope = float(np.polyfit(bf, by, 1)[0]) if np.var(bf) > 1e-12 else float("nan")
            r["n_reliability_bins"] = int(len(bf))
            r["reliability_slope"] = None if not np.isfinite(slope) else round(slope, 3)
            r["calibration_ok"] = bool(abs(f.mean() - y.mean()) <= 0.03 and np.isfinite(slope)
                                       and 0.5 <= slope <= 1.5)
            r["brier_model"], r["brier_baseline"] = (round(F[f"bs_m_{h}"].mean(), 6),
                                                     round(F[f"bs_b_{h}"].mean(), 6))
        yrs = []
        for y_, g in F.groupby(F.t.dt.year):
            if len(g) >= 10:
                yrs.append(skill(g, head) > 0)
        r["years_positive"] = f"{sum(yrs)}/{len(yrs)}"
        r["years_ok"] = bool(yrs) and sum(yrs) / len(yrs) >= 0.60
        res[head] = r
    # BH over the four primary p-values
    ps = [(h, res[h].get("p_one_sided", 1.0)) for h in HEADS]
    order = sorted(ps, key=lambda x: x[1])
    m, k_max = len(order), 0
    for k, (_, p) in enumerate(order, 1):
        if p <= k / m * BH_Q:
            k_max = k
    survivors = {h for h, _ in order[:k_max]}
    for h in HEADS:
        r = res[h]
        r["bh_survives"] = h in survivors
        reasons = []
        if r["coverage"] < 0.80:
            reasons.append("coverage_below_0.80")
        if r["n_scored"] < 200:
            reasons.append("n_scored_below_200")
        under = bool(reasons)
        if "ci90" not in r or r["ci90"][0] <= 0:
            reasons.append("skill_ci90_includes_or_below_zero")
        if not r["bh_survives"]:
            reasons.append("fails_bh_fdr_q0.10")
        if not r.get("calibration_ok"):
            reasons.append("calibration_out_of_band")
        if not r.get("years_ok"):
            reasons.append("skill_positive_in_under_60pct_of_years")
        r["reasons"] = reasons
        r["disposition"] = ("QUALIFIED_RESEARCH" if not reasons else
                            "WITHHELD_UNDERPOWERED" if under else "WITHHELD_FAILED")
    return res


# ── comparators ─────────────────────────────────────────────────────────────
def stats(rets: pd.Series, bench: pd.Series, cash: pd.Series) -> dict:
    per = 252 / STEP
    eq = (1 + rets).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    ex = rets - cash
    cov = np.cov(rets, bench)
    beta = float(cov[0, 1] / cov[1, 1])
    up, dn = bench >= 0.005, bench <= -0.005
    def cap(mask):
        den = bench[mask].sum()
        return None if abs(den) < 0.01 else round(float(rets[mask].sum() / den), 3)
    return {"ann_return": round(float(eq.iloc[-1] ** (per / len(rets)) - 1), 4),
            "ann_vol": round(float(rets.std() * np.sqrt(per)), 4),
            "ann_excess_over_cash": round(float(ex.mean() * per), 4),
            "max_drawdown_period_level": round(dd, 4),
            "beta_vs_C1": round(beta, 3),
            "tracking_error_vs_C1": round(float((rets - bench).std() * np.sqrt(per)), 4),
            "upside_capture": cap(up), "downside_capture": cap(dn)}


def comparators(data: dict, spy: pd.DataFrame, cash_tr: pd.Series, turns: dict, rng) -> dict:
    idx = spy.index
    spy_tr = spy["close"]
    sma200 = spy["close_price"].rolling(200, min_periods=200).mean()
    first_ok = {s: data[s].index[WARMUP] if len(data[s]) > WARMUP else None for s in SECTORS}
    rows, prev = [], {}
    no_entry = no_fill = immature = 0
    emerg = {"emergers": 0, "emergers_held": 0, "nontop": 0, "nontop_held": 0}
    failed = {"failed_leaders": 0, "failed_held": 0}
    rebounds = []
    in_dd = False            # rebound episodes: first decision date per >=10% drawdown episode
    for i in range(WARMUP, len(idx), STEP):
        t = idx[i]
        if i + 1 >= len(idx):          # signal on the last session: no t+1 close to fill at
            no_fill += 1
            continue
        if i + 21 >= len(idx):         # filled but horizon not complete: immature, not scored
            immature += 1
            continue
        e, x = idx[i + 1], idx[i + 21]
        elig = [s for s in SECTORS if first_ok[s] is not None and first_ok[s] <= t
                and e in data[s].index and x in data[s].index]
        def R(s):
            c = data[s]["close"]
            return float(c.loc[x] / c.loc[e] - 1)
        rs = {s: R(s) for s in elig}
        r_spy = float(spy_tr.loc[x] / spy_tr.loc[e] - 1)
        r_cash = float(cash_tr.loc[x] / cash_tr.loc[e] - 1) if (e in cash_tr.index and x in cash_tr.index
                                                                and e >= cash_tr.index[0]) else 0.0
        up_secs = []
        for s in elig:
            known = [z for z in turns[s] if z["confirmed_at"] <= str(t.date())]
            if known and known[-1]["k"] == "trough":
                up_secs.append(s)
        w = {"C1": {"SPY": 1.0},
             "C2": {"SPY": 1.0} if spy["close_price"].loc[t] > sma200.loc[t] else {},
             "C3": {s: 1 / len(up_secs) for s in up_secs},
             "C3_EW": {s: 1 / len(elig) for s in elig} if elig else {}}
        if not up_secs and t >= TEST_FROM:
            no_entry += 1
        row = {"t": t, "cash": r_cash, "spy": r_spy}
        for k, wk in w.items():
            ra = {a: (r_spy if a == "SPY" else rs[a]) for a in wk}
            gross = sum(v * ra[a] for a, v in wk.items())
            inv = sum(wk.values())
            old = prev.get(k, {})          # weights as DRIFTED to this execution close
            turn = sum(abs(wk.get(a, 0) - old.get(a, 0)) for a in set(wk) | set(old))
            row[k] = gross + (1 - inv) * r_cash - turn * COST_SIDE
            row[f"{k}_inv"], row[f"{k}_turn"], row[f"{k}_cost"] = inv, turn, turn * COST_SIDE
            port = gross + (1 - inv) * r_cash
            prev[k] = {a: v * (1 + ra[a]) / (1 + port) for a, v in wk.items()}
        rows.append(row)
        # failed leaders + emergence (trailing 63 vs SPY)
        if i >= 63 and t >= TEST_FROM:
            t63 = idx[i - 63]
            trail = {s: float(data[s]["close"].loc[t] / data[s]["close"].loc[t63] - 1)
                     - float(spy_tr.loc[t] / spy_tr.loc[t63] - 1)
                     for s in elig if t63 in data[s].index}
            if len(trail) >= 6:
                top3 = set(sorted(trail, key=trail.get, reverse=True)[:3])
                fwd = sorted(rs, key=rs.get)
                bottom = set(fwd[:len(fwd) // 2])
                fl = top3 & bottom
                failed["failed_leaders"] += len(fl)
                failed["failed_held"] += len(fl & set(up_secs))
                if i + 64 < len(idx):
                    x63 = idx[i + 64]
                    f63 = {s: float(data[s]["close"].loc[x63] / data[s]["close"].loc[e] - 1)
                           for s in trail if x63 in data[s].index}
                    ftop = set(sorted(f63, key=f63.get, reverse=True)[:3])
                    non = set(trail) - top3
                    em = non & ftop
                    emerg["emergers"] += len(em)
                    emerg["emergers_held"] += len(em & set(up_secs))
                    emerg["nontop"] += len(non)
                    emerg["nontop_held"] += len(non & set(up_secs))
        # rebounds (protocol §5): the next 20 sessions after EACH >= 10% C1 drawdown — one
        # period per episode (the first decision date at or past -10%); an episode ends when
        # SPY makes a new total-return high above the episode's peak.
        peak = float(spy_tr.loc[:t].max())
        if in_dd and peak > dd_peak:
            in_dd = False
        if not in_dd and float(spy_tr.loc[t]) / peak - 1 <= -0.10:
            in_dd, dd_peak = True, peak
            rebounds.append(row)
    P = pd.DataFrame(rows).set_index("t")
    P = P[P.index >= TEST_FROM]
    w_match = P["C3_inv"].mean()
    P["C3_EXPO"] = w_match * P["C3_EW"] + (1 - w_match) * P["cash"]
    out = {"n_periods": int(len(P)), "test_from": str(TEST_FROM.date()),
           "test_to": str(P.index[-1].date()), "no_entry_periods_C3": no_entry,
           "no_fill_signals": no_fill, "immature_signals_not_scored": immature,
           "exposure_match_w": round(float(w_match), 4)}
    for k in ("C1", "C2", "C3", "C3_EW", "C3_EXPO"):
        s = stats(P[k], P["C1"], P["cash"])
        if f"{k}_inv" in P:
            s["mean_invested"] = round(float(P[f"{k}_inv"].mean()), 4)
            s["annual_turnover"] = round(float(P[f"{k}_turn"].mean() * 252 / STEP), 3)
            s["costs_paid_total"] = round(float(P[f"{k}_cost"].sum()), 4)
        out[k] = s
    years = P.index.year
    uy = np.array(sorted(set(years)))
    def ci(diff):
        g = {y: diff[years == y] for y in uy}
        v = [pd.concat([g[y] for y in rng.choice(uy, len(uy))]).mean() * 252 / STEP
             for _ in range(N_BOOT)]
        return [round(float(np.quantile(v, .05)), 4), round(float(np.quantile(v, .95)), 4)]
    for a, b in (("C3", "C1"), ("C3", "C3_EXPO"), ("C3", "C3_EW"), ("C2", "C1")):
        d = P[a] - P[b]
        out[f"{a}_minus_{b}"] = {"ann_mean": round(float(d.mean() * 252 / STEP), 4), "ci90": ci(d)}
    out["C4"] = {"status": "unavailable", "reason": "no_pit_constituent_membership"}
    out["C5"] = {"status": "unavailable", "reason": "no_pit_constituent_membership"}
    out["C6"] = {"status": "unavailable", "reason": "incumbent_record_not_in_lane_scope"}
    out["C7"] = {**emerg,
                 "recall_emergers_held": round(emerg["emergers_held"] / emerg["emergers"], 4)
                 if emerg["emergers"] else None,
                 "base_rate_nontop_held": round(emerg["nontop_held"] / emerg["nontop"], 4)
                 if emerg["nontop"] else None}
    out["failed_leaders"] = {**failed, "share_held_by_C3": round(failed["failed_held"]
                             / failed["failed_leaders"], 4) if failed["failed_leaders"] else None}
    RB = pd.DataFrame(rebounds)
    RB = RB[RB.t >= TEST_FROM] if len(RB) else RB
    ok = RB[RB.spy.abs() >= 0.005] if len(RB) else RB
    out["rebounds"] = {"n_drawdown_episodes": int(len(RB)),
                       "n_with_usable_denominator": int(len(ok)),
                       "C3_over_C1_median": round(float((ok.C3 / ok.spy).median()), 3) if len(ok) else None,
                       "C2_over_C1_median": round(float((ok.C2 / ok.spy).median()), 3) if len(ok) else None,
                       "C1_mean": round(float(RB.spy.mean()), 4) if len(RB) else None,
                       "C3_mean": round(float(RB.C3.mean()), 4) if len(RB) else None,
                       "C2_mean": round(float(RB.C2.mean()), 4) if len(RB) else None}
    return out


def simpler_state_sensitivity(W: pd.DataFrame, F_full: pd.DataFrame) -> dict:
    """Adjudication diagnostic added after the independent review (NOT a protocol rule and
    never a verdict input): how much of each head's skill a direction-only or age-only state
    already earns, on the full model's scored windows."""
    full = F_full[~F_full.abstain].set_index(["sid", "t"])
    out = {}
    for name, fn in {"direction_only": lambda c: None if c is None else c.split(":")[0],
                     "age_only": lambda c: None if c is None else c.split(":")[1]}.items():
        W2 = W.copy()
        W2["cell"] = W2.cell.map(fn)
        A = forecasts(W2)
        A = A[~A.abstain].set_index(["sid", "t"]).reindex(full.index)
        for h, head in (("y2", HEADS[1]), ("y3", HEADS[2]), ("y4", HEADS[3])):
            d = out.setdefault(head, {})
            d[f"{name}_skill_vs_climatology"] = round(float(
                1 - A[f"bs_m_{h}"].sum() / A[f"bs_b_{h}"].sum()), 5)
            d[f"full_skill_vs_{name}"] = round(float(
                1 - full[f"bs_m_{h}"].sum() / A[f"bs_m_{h}"].sum()), 5)
        a1 = A.dropna(subset=["pl_m"])
        f1 = full.loc[a1.index]
        out.setdefault(HEADS[0], {})[f"full_skill_vs_{name}"] = round(float(
            1 - f1.pl_m.sum() / a1.pl_m.sum()), 5)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    spy = load(a.tape_dir, "SPY")
    cash = load(a.tape_dir, "BIL")["close"]
    data, turns, W, pit = {}, {}, [], {}
    for s in SECTORS:
        data[s] = load(a.tape_dir, s).dropna(subset=["close_price"])
        rows, full, n = build_windows(s, data[s], spy["close"])
        turns[s], pit[s] = full, n
        W += rows
    W = pd.DataFrame(W)
    W["exit_t"] = [data[r.sid].index[min(r.i + 21, len(data[r.sid]) - 1)] for r in W.itertuples()]
    F = forecasts(W)
    heads = judge(F, rng)
    cells = (F[~F.abstain].groupby("cell").size().to_dict())
    comp = comparators(data, spy, cash, turns, rng)
    sens = simpler_state_sensitivity(W, F)
    tapes = {t: sha(a.tape_dir / "data" / "yahoo" / f"{t}.parquet") for t in SECTORS + ["SPY", "BIL"]}
    result = {"schema": "b12.v11_heads_result.v1",
              "protocol": "research/sector_completion_20261021/B12_V11_HEADS_PROTOCOL.md",
              "pit_check": {"passed": True, "dates_checked": pit},
              "windows": {"total": int(len(W)), "mature": int(W.mature.sum()),
                          "test_cells_scored": {k: int(v) for k, v in cells.items()}},
              "heads": heads, "comparators": comp, "tape_sha256": tapes,
              "sensitivity_not_verdict": sens,
              "authority": {k: False for k in ("may_rank", "may_gate", "may_size",
                                               "may_trade", "may_escalate")}}
    a.out.write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps({h: {k: heads[h].get(k) for k in ("disposition", "skill", "ci90", "p_one_sided",
                                                         "n_scored", "coverage", "reasons")}
                      for h in HEADS}, indent=1, default=str))


if __name__ == "__main__":
    main()
