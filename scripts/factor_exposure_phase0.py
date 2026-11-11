"""Factor-exposure engine — Phase 0 honest validation (engine/factor_exposure.py).

This feature is MEASUREMENT, not prediction, so the gate is NOT predictive IC/FDR/DSR
— you don't backtest a thermometer. The honest questions are:

  1. COLLINEARITY — are the raw factors so correlated that a univariate beta table
     (the ChatGPT version) double-counts? Quantify it: VIF, top pairs, and the
     variance-inflation factor between the naive "sum of univariate exposures" and the
     orthogonal model's true factor variance. Confirm orthogonalization removes it.

  2. BETA STABILITY (the core gate) — does a beta estimated on the trailing window
     persist out-of-sample? At monthly rebalances, estimate betas on [t-W, t] (causal)
     and correlate them cross-sectionally with realized betas on the next (t, t+H].
     A factor whose in-sample beta doesn't rank next-period exposure is noise.

  3. AGGREGATION DENOISING (the design justification) — the working assumption is
     "trust the portfolio aggregate, not a single stock's secondary beta." Form random
     K-name equal-weight books and measure whether out-of-sample stability rises with K.
     A flat or weaker result does not support an aggregation-denoising claim.

  4. EXPLANATORY POWER — market-only vs full-model R², and how much the secondary
     factors add at the single-stock level.

Run:
  .venv/bin/python -m scripts.factor_exposure_phase0
  .venv/bin/python -m scripts.factor_exposure_phase0 --win 252 --horizon 63

Writes reports/factor-exposure-phase0.md. No commit, no site build — pure harness.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")   # rolling-beta on truncated history emits benign numpy warnings

from engine import factor_exposure as fe          # noqa: E402
from engine.equity_factors import _closes         # noqa: E402
from engine.validation import top_correlated_pairs, vif  # noqa: E402
from lib import config                             # noqa: E402

RNG = np.random.default_rng(7)


def _beta_series(betas: dict, key: str) -> pd.Series:
    """Pull one factor's beta across stocks as a Series (drops missing)."""
    return pd.Series({t: r[key] for t, r in betas.items()
                      if r.get(key) is not None}).astype(float)


def _spearman(a: pd.Series, b: pd.Series) -> float:
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(j) < 10:
        return float("nan")
    return float(j["a"].rank().corr(j["b"].rank()))


def month_grid(index, warmup: int, horizon: int) -> list:
    out = []
    for me in pd.date_range(index.min(), index.max(), freq="ME"):
        d = index[index <= me]
        if not len(d):
            continue
        loc = index.get_loc(d[-1])
        if loc >= warmup and loc + horizon < len(index):
            out.append(d[-1])
    return out


# --------------------------------------------------------------------------- #
# 1. collinearity + double-count
# --------------------------------------------------------------------------- #
def collinearity(F: pd.DataFrame, closes: pd.DataFrame, win: int, minp: int,
                 max_abs: float) -> dict:
    raw_vif = vif(F)
    pairs = top_correlated_pairs(F, k=8, thresh=0.3)
    G = fe.orthogonalize_factors(F.tail(win))
    orth_vif = vif(G)

    # double-count: naive "sum of univariate exposures treating factors as independent"
    # variance vs the orthogonal model's true factor variance, per stock.
    rb = fe.raw_betas(closes, F, window=win, min_obs=minp, max_abs=max_abs)
    res = fe.stock_betas(closes, F, window=win, min_obs=minp, max_abs=max_abs)["betas"]
    keys = list(G.columns)
    raw_var = {k: float(F[k].tail(win).var()) for k in keys}
    orth_var = {k: float(G[k].var()) for k in keys}
    infl = []
    for t in res:
        if t not in rb:
            continue
        naive = sum((rb[t].get(k) or 0.0) ** 2 * raw_var[k] for k in keys)
        true = sum((res[t].get(k) or 0.0) ** 2 * orth_var[k] for k in keys)
        if true > 0:
            infl.append(naive / true)
    return {"raw_vif": raw_vif, "orth_vif": orth_vif, "pairs": pairs,
            "infl_median": float(np.median(infl)) if infl else None,
            "infl_p90": float(np.percentile(infl, 90)) if infl else None,
            "n_stocks": len(infl)}


# --------------------------------------------------------------------------- #
# 2+3. out-of-sample stability, per-stock and aggregated
# --------------------------------------------------------------------------- #
def stability(F: pd.DataFrame, closes: pd.DataFrame, *, win: int, horizon: int,
              minp: int, max_abs: float, basket_sizes: list, n_baskets: int) -> dict:
    F = fe._finite_factor_frame(F)
    idx = F.index.intersection(closes.index)
    # Preserve original return intervals before factor availability/window slicing.
    returns = closes.pct_change(fill_method=None)
    grid = month_grid(idx, warmup=win, horizon=horizon)
    keys = [k for k in fe.FACTOR_ORDER if k in F.columns]
    if len(grid) < 4:
        return {"error": f"grid too short ({len(grid)})", "rebalances": len(grid)}

    per_stock = {k: [] for k in keys}                     # cross-sectional persistence per date
    agg = {K: {k: [] for k in keys} for K in basket_sizes}
    fwd_minp = max(horizon // 2, 20)
    evaluated = []

    for d in grid:
        loc = F.index.get_loc(d)
        in_sl = F.index[max(0, loc - win + 1):loc + 1]
        # The anchor close is the predecessor of the first forward return; its own
        # return remains in-sample and must not enter forward estimates.
        fw_sl = F.index[loc + 1:min(len(F), loc + horizon + 1)]
        if len(fw_sl) < fwd_minp:
            continue
        bin_ = fe.stock_betas(closes, F.loc[in_sl], returns=returns,
                              window=win, min_obs=minp, max_abs=max_abs)["betas"]
        bfw = fe.stock_betas(closes, F.loc[fw_sl], returns=returns,
                             window=len(fw_sl), min_obs=fwd_minp, max_abs=max_abs)["betas"]
        if not bin_ or not bfw:
            continue
        evaluated.append(d)
        for k in keys:
            si, sf = _beta_series(bin_, k), _beta_series(bfw, k)
            per_stock[k].append(_spearman(si, sf))
            common = si.index.intersection(sf.index)
            if len(common) < max(basket_sizes) + 5:
                continue
            si, sf = si[common], sf[common]
            for K in basket_sizes:
                ins, fws = [], []
                for _ in range(n_baskets):
                    pick = RNG.choice(common.to_numpy(), size=K, replace=False)
                    ins.append(float(si[pick].mean()))
                    fws.append(float(sf[pick].mean()))
                agg[K][k].append(_spearman(pd.Series(ins), pd.Series(fws)))

    def mean_n(xs):
        s = pd.Series(xs).dropna()
        return (round(float(s.mean()), 3), len(s)) if len(s) else (None, 0)

    if len(evaluated) < 4:
        return {"error": f"too few fitted rebalances ({len(evaluated)})",
                "rebalances": len(evaluated)}
    ps = {k: dict(zip(("persist", "n"), mean_n(per_stock[k]))) for k in keys}
    ag = {K: {k: mean_n(agg[K][k])[0] for k in keys} for K in basket_sizes}
    return {"rebalances": len(evaluated), "span": f"{evaluated[0].date()}..{evaluated[-1].date()}",
            "horizon": horizon, "win": win, "per_stock": ps, "by_basket": ag,
            "basket_sizes": basket_sizes}


# --------------------------------------------------------------------------- #
# 4. explanatory power (market-only vs full model)
# --------------------------------------------------------------------------- #
def explanatory(F: pd.DataFrame, closes: pd.DataFrame, win: int, minp: int,
                max_abs: float) -> dict:
    """Nested R²: market-only → +style (growth, size) → full (+macro). Isolates how
    much the MACRO factors (rates/usd/oil/btc) actually add at the single-stock level."""
    style = [c for c in ("mkt", "growth", "size") if c in F.columns]

    def r2_of(cols):
        b = fe.stock_betas(closes, F[cols], window=win, min_obs=minp, max_abs=max_abs)["betas"]
        return pd.Series({t: r["r2"] for t, r in b.items() if r.get("r2") is not None})

    r2_mkt, r2_style, r2_full = r2_of(["mkt"]), r2_of(style), r2_of(list(F.columns))
    common = r2_mkt.index.intersection(r2_style.index).intersection(r2_full.index)
    macro_add = (r2_full[common] - r2_style[common]).dropna()
    style_add = (r2_style[common] - r2_mkt[common]).dropna()
    return {"r2_mkt_median": round(float(r2_mkt[common].median()), 3),
            "r2_style_median": round(float(r2_style[common].median()), 3),
            "r2_full_median": round(float(r2_full[common].median()), 3),
            "style_add_median": round(float(style_add.median()), 3),
            "macro_add_median": round(float(macro_add.median()), 3),
            "macro_add_p90": round(float(macro_add.quantile(0.9)), 3), "n": int(len(common))}


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", type=int, default=252, help="estimation window (finite factor observations)")
    ap.add_argument("--horizon", type=int, default=63, help="forward window (finite factor observations)")
    ap.add_argument("--min-obs", type=int, default=126)
    ap.add_argument("--max-abs", type=float, default=5.0)
    ap.add_argument("--n-baskets", type=int, default=200, help="random books per size per date")
    args = ap.parse_args()
    sizes = [1, 5, 10, 20, 40]

    F = fe.factor_frame()
    closes = _closes()
    if F.empty or closes.empty:
        print("missing factor or close data")
        return 1
    print(f"[factors] {list(F.columns)} · {len(F)} rows {F.index.min().date()}..{F.index.max().date()}")
    print(f"[stocks]  {closes.shape[1]} names · {len(closes)} rows")

    print("[1/4] collinearity + double-count …")
    col = collinearity(F, closes, args.win, args.min_obs, args.max_abs)
    print("[2-3/4] out-of-sample beta stability (per-stock + aggregated) …")
    stab = stability(F, closes, win=args.win, horizon=args.horizon, minp=args.min_obs,
                     max_abs=args.max_abs, basket_sizes=sizes, n_baskets=args.n_baskets)
    print("[4/4] explanatory power …")
    exp = explanatory(F, closes, args.win, args.min_obs, args.max_abs)

    report = render(F, col, stab, exp, args)
    out = config.ROOT / config.load()["storage"]["reports_dir"] / "factor-exposure-phase0.md"
    out.write_text(report)
    print(f"\n[report] {out}")
    return 0


def render(F, col, stab, exp, args) -> str:
    keys = [k for k in fe.FACTOR_ORDER if k in F.columns]
    lab = {f.key: f.label for f in fe.FACTORS}
    L = ["# Factor-exposure engine — Phase 0 validation", "",
         "*Generated by `scripts/factor_exposure_phase0.py`. This is a MEASUREMENT tool, "
         "not a predictive signal — the gate is collinearity control + out-of-sample beta "
         "STABILITY, not IC/FDR/DSR. Working assumption under test: trust the portfolio "
         "aggregate, not a single stock's secondary beta.*", "",
         f"Factor observations: {len(F)} rows, {F.index.min().date()}..{F.index.max().date()}. "
         f"Fit {args.win} returns; forward {args.horizon} returns; minimum fit support "
         f"{args.min_obs}; coefficient cap ±{args.max_abs:g}. Random baskets: "
         f"{args.n_baskets} per size/date, seed 7. The forward sample excludes the "
         "rebalance anchor's return.", ""]

    # 1. collinearity
    L += ["## 1. Collinearity — why a univariate beta table double-counts", "",
          "VIF per factor (>5 redundant, >10 severe) on the RAW factors vs after "
          "orthogonalization:", "",
          "| factor | raw VIF | orthogonalized VIF |", "|---|--:|--:|"]
    for k in keys:
        L.append(f"| {lab.get(k, k)} | {col['raw_vif'].get(k, '—')} | {col['orth_vif'].get(k, '—')} |")
    if col["pairs"]:
        L += ["", "Most-correlated raw factor pairs: "
              + ", ".join(f"{p['a']}–{p['b']} {p['corr']}" for p in col["pairs"]) + "."]
    if col["infl_median"] is not None:
        L += ["", f"**Variance ratio:** treating univariate exposures as independent gives "
              f"a median naive/model factor-variance ratio of **{col['infl_median']:.2f}×** "
              f"(p90 {col['infl_p90']:.2f}×) across {col['n_stocks']} stocks. A ratio above "
              "one indicates overstatement; below one indicates understatement."]

    # 2. per-stock stability
    L += ["", "## 2. Out-of-sample beta stability (single-stock)", ""]
    if stab.get("error"):
        L += [f"_skipped — {stab['error']}_", ""]
    else:
        L += [f"Span {stab['span']} · {stab['rebalances']} monthly rebalances · estimate on "
              f"{stab['win']} finite factor observations, realize on the next {stab['horizon']}. "
              f"Forward windows overlap; these are not independent trials. Cross-sectional rank "
              f"correlation between in-sample and next-period beta (1 = perfectly persistent, "
              f"0 = no rank association):", "",
              "| factor | persistence | n |", "|---|--:|--:|"]
        for k in keys:
            r = stab["per_stock"][k]
            L.append(f"| {lab.get(k, k)} | {r['persist']} | {r['n']} |")

        # 3. aggregation denoising
        L += ["", "## 3. Aggregation denoising — does the portfolio aggregate firm up?", "",
              "Same persistence, but for random equal-weight books of K names (mean beta). "
              "Compare each size with K=1; improvement must be measured, not assumed:", "",
              "| factor | " + " | ".join(f"K={K}" for K in stab["basket_sizes"]) + " |",
              "|---|" + "--:|" * len(stab["basket_sizes"])]
        for k in keys:
            row = " | ".join(str(stab["by_basket"][K].get(k, "—")) for K in stab["basket_sizes"])
            L.append(f"| {lab.get(k, k)} | {row} |")

    # 4. explanatory
    L += ["", "## 4. Explanatory power (nested R²)", "",
          f"Median single-stock R² over {exp['n']} names: market-only **{exp['r2_mkt_median']}** "
          f"→ +style (growth, size) **{exp['r2_style_median']}** → +remaining factors "
          f"**{exp['r2_full_median']}**. Style adds a median **{exp['style_add_median']}**; the "
          f"remaining factors add a median **{exp['macro_add_median']}** "
          f"(p90 {exp['macro_add_p90']}). These are in-sample explanatory changes, "
          f"not evidence of forward beta stability.", ""]

    L += ["---", "",
          "**How to read.** §1 measures collinearity and the variance difference between "
          "the two models. §2 reports single-stock beta persistence on the evaluated "
          "dates. §3 tests whether aggregation improves that persistence; a flat or "
          "weaker result does not support a denoising claim. Interpret each factor "
          "against its measured values and sample size. This historical measurement "
          "does not establish predictive performance or future stability.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
