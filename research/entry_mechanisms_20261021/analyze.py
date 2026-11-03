#!/usr/bin/env python3
"""Frozen mechanism contrasts, not a strategy optimizer. See PROTOCOL.md."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261021
HORIZONS = (21, 63)
SECTORS = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "SOXX", "AMD": "SOXX",
    "INTC": "SOXX", "MU": "SOXX", "AMZN": "XLY", "GOOGL": "XLC",
    "META": "XLC", "TSLA": "XLY", "JPM": "XLF", "XOM": "XLE",
    "CVX": "XLE", "CAT": "XLI", "FCX": "XLB", "NEM": "XLB",
    "KO": "XLP", "PEP": "XLP", "WMT": "XLP", "WM": "XLI",
    "JNJ": "XLV", "PFE": "XLV",
}
PERIODS = {
    "1995_2013": ("1995-01-01", "2013-12-31"),
    "2014_2019": ("2014-01-01", "2019-12-31"),
    "2020_2026_exposed": ("2020-01-01", "2026-10-08"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=str, allow_nan=False))


def forward_outcomes(d, atr, horizon):
    """Every decision t uses next open; stop can fire on that entry day."""
    n = len(d)
    out = pd.DataFrame(index=d.index)
    if n <= horizon:
        return out
    k = n - horizon
    ix = np.arange(k)
    o, lo, hi, c = [d[x].to_numpy(float) for x in ("open", "low", "high", "close")]
    fac = (d.adjclose / d.close).to_numpy(float)
    if not np.isfinite(fac).all() or (fac <= 0).any():
        raise ValueError("Invalid return adjustment factor")
    entry = o[ix + 1]
    adjentry = entry * fac[ix + 1]
    ratio = c[ix + horizon] * fac[ix + horizon] / adjentry
    lwin = np.lib.stride_tricks.sliding_window_view(lo[1:], horizon)
    adjlwin = np.lib.stride_tricks.sliding_window_view((lo * fac)[1:], horizon)
    adjhwin = np.lib.stride_tricks.sliding_window_view((hi * fac)[1:], horizon)
    stop = entry - 3 * np.asarray(atr)[:k]
    stop_valid = np.isfinite(stop) & (stop > 0)
    hits = (lwin <= stop[:, None]) & stop_valid[:, None]
    stopped = hits.any(axis=1)
    first = hits.argmax(axis=1)
    stopix = ix + 1 + first
    exitix = np.where(stopped, stopix, ix + horizon)
    fill = np.where(stopped, np.minimum(stop, o[stopix]), c[ix + horizon])
    sratio = fill * fac[exitix] / adjentry
    out.loc[d.index[:k], "gross"] = ratio - 1
    out.loc[d.index[:k], "net20"] = ratio * (1 - .001) / (1 + .001) - 1
    out.loc[d.index[:k], "net50"] = ratio * (1 - .0025) / (1 + .0025) - 1
    out.loc[d.index[:k], "stop_net20"] = np.where(stop_valid, sratio * (1 - .001) / (1 + .001) - 1, np.nan)
    out.loc[d.index[:k], "stop_net50"] = np.where(stop_valid, sratio * (1 - .0025) / (1 + .0025) - 1, np.nan)
    out.loc[d.index[:k], "stop_hit"] = np.where(stop_valid, stopped.astype(float), np.nan)
    out.loc[d.index[:k], "stop_exit_t"] = np.where(stop_valid, exitix, np.nan)
    out.loc[d.index[:k], "mae"] = np.minimum(adjlwin.min(axis=1) / adjentry - 1, 0)
    out.loc[d.index[:k], "top_adverse"] = np.minimum(1 - adjhwin.max(axis=1) / adjentry, 0)
    out.loc[d.index[:k], "entry_open"] = entry
    out.loc[d.index[:k], "stop_price"] = np.where(stop_valid, stop, np.nan)
    out["exit_date"] = pd.Series(d.index, index=d.index).shift(-horizon)
    out["entry_date"] = pd.Series(d.index, index=d.index).shift(-1)
    return out


def reset_state(d, atr):
    """Strict peak -> trough -> decision chronology, fixed before outcomes."""
    hi, lo, close = [d[x].to_numpy(float) for x in ("high", "low", "close")]
    a = np.asarray(atr)
    reset = np.zeros(len(d), bool)
    peak, trough = np.full(len(d), -1), np.full(len(d), -1)
    for t in range(20, len(d)):
        p = t - 1 - np.argmax(hi[t-20:t][::-1])
        if p >= t - 1 or not np.isfinite(a[p]) or a[p] <= 0:
            continue
        q = t - 1 - np.argmin(lo[p+1:t][::-1])
        peak[t], trough[t] = p, q
        depth, distance = (hi[p] - lo[q]) / a[p], (hi[p] - close[t]) / a[p]
        reset[t] = q >= t - 10 and depth >= 2 and 0 <= distance <= 3
    return reset, peak, trough


def period_labels(dates, ends):
    out = np.full(len(dates), "excluded", object)
    for name, (start, end) in PERIODS.items():
        take = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end)) & (ends <= pd.Timestamp(end))
        out[np.asarray(take)] = name
    return out


def add_leave_one_out(df, keys, prefix):
    """Descriptive comparator; remove the focal date from its own cell."""
    grouped = df.groupby(keys, dropna=False)
    count = grouped.net20.transform("count") - 1
    for value in ("net20", "win", "stop_net20", "stop_win"):
        c = grouped[value].transform("count") - df[value].notna().astype(int)
        total = grouped[value].transform("sum") - df[value].fillna(0)
        df[f"{prefix}_{value}"] = (total / c).where(c >= 10)
    df[f"{prefix}_n"] = count


def nonoverlap(q, horizon):
    take = []
    for _, group in q.sort_values(["ticker", "date"]).groupby("ticker", sort=False):
        last = -100000
        for row in group.itertuples():
            if row.t >= last:
                take.append(row.Index)
                last = row.t + horizon
    return q.loc[take]


def boot(q, field, draws=2000):
    x = q[["halfyear", field]].dropna()
    if x.empty:
        return (np.nan, np.nan)
    # Include inactive calendar blocks so concentration is not hidden.
    labels = np.arange(int(q.halfyear.min()), int(q.halfyear.max()) + 1)
    g = x.groupby("halfyear")[field].agg(["sum", "count"]).reindex(labels, fill_value=0)
    if len(g) < 4 or (g["count"] > 0).sum() < 4:
        return (np.nan, np.nan)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, len(g), size=(draws, (len(g) + 1)//2))
    ix = np.stack([starts, (starts + 1) % len(g)], axis=2).reshape(draws, -1)[:, :len(g)]
    a, b = g["sum"].to_numpy()[ix].sum(axis=1), g["count"].to_numpy()[ix].sum(axis=1)
    vals = np.divide(a, b, out=np.full(draws, np.nan), where=b > 0)
    return tuple(np.nanquantile(vals, [.025, .975]))


def metrics(q, side="bottom", ci=True):
    if q.empty:
        return {"n": 0, "assets": 0, "dates": 0, "halfyears": 0}
    q = q.copy()
    r = q.net20 if side == "bottom" else -q.gross - .002
    rs = q.net50 if side == "bottom" else -q.gross - .005
    q["result"] = r
    q["positive"] = (r > 0).astype(float)
    winners, losers = r[r > 0], r[r <= 0]
    p05 = r.quantile(.05)
    out = {
        "n": len(q), "assets": q.ticker.nunique(), "dates": q.date.nunique(),
        "quarters": q.quarter.nunique(), "halfyears": q.halfyear.nunique(),
        "positive": float((r > 0).mean()), "mean": r.mean(), "median": r.median(),
        "mean_winner": winners.mean(), "mean_loser": losers.mean(),
        "p05": p05, "worst5_mean": r[r <= p05].mean(), "worst": r.min(),
        "positive_cost50": float((rs > 0).mean()), "mean_cost50": rs.mean(),
        "mean_mae": q.mae.mean() if side == "bottom" else q.top_adverse.mean(),
        "median_mae": q.mae.median() if side == "bottom" else q.top_adverse.median(),
        "worst_mae": q.mae.min() if side == "bottom" else q.top_adverse.min(),
        "largest_date_share": q.groupby("date").size().max()/len(q),
        "equal_date_mean": q.groupby("date").result.mean().mean(),
        "equal_asset_mean": q.groupby("ticker").result.mean().mean(),
        "positive_halfyear_fraction": float((q.groupby("halfyear").result.mean() > 0).mean()),
    }
    if "qualified" in q:
        out["original_qualified_fraction"] = q.qualified.mean()
        if q.horizon.eq(63).all():
            out["original_timely_durable63"] = q.primary63.mean()
    if side == "bottom":
        st = q.stop_net20
        out.update(stop_n=st.notna().sum(), stop_positive=float((st.dropna() > 0).mean()),
                   stop_mean=st.mean(), stop_median=st.median(), stop_p05=st.quantile(.05),
                   stop_hit=q.stop_hit.mean(), stop_worst=st.min(),
                   stop_positive_cost50=float((q.stop_net50.dropna() > 0).mean()),
                   positive_endpoint_stopped_loss=float(((r > 0) & (st <= 0)).mean()),
                   stopped_loss_given_positive=float((st[r > 0] <= 0).mean()))
        for prefix in ("ordinary", "state"):
            if f"{prefix}_net20" not in q:
                continue
            match = q[f"{prefix}_net20"].notna()
            q[f"delta_{prefix}"] = q.net20 - q[f"{prefix}_net20"]
            q[f"hitdelta_{prefix}"] = (q.net20 > 0).astype(float) - q[f"{prefix}_win"]
            out[f"{prefix}_matches"] = int(match.sum())
            out[f"{prefix}_coverage"] = match.mean()
            out[f"{prefix}_mean"] = q.loc[match, f"{prefix}_net20"].mean()
            out[f"{prefix}_positive"] = q.loc[match, f"{prefix}_win"].mean()
            out[f"{prefix}_delta_mean"] = q[f"delta_{prefix}"].mean()
            out[f"{prefix}_delta_positive"] = q[f"hitdelta_{prefix}"].mean()
            out[f"{prefix}_stop_delta"] = (q.stop_net20-q[f"{prefix}_stop_net20"]).mean()
            if ci:
                out[f"{prefix}_delta_ci_lo"], out[f"{prefix}_delta_ci_hi"] = boot(q, f"delta_{prefix}")
        for prefix in ("peer", "spy", "sector"):
            if f"{prefix}_net20" in q:
                q[f"delta_{prefix}"] = q.net20-q[f"{prefix}_net20"]
                out[f"{prefix}_matches"] = int(q[f"delta_{prefix}"].notna().sum())
                out[f"{prefix}_mean"] = q[f"{prefix}_net20"].mean()
                out[f"{prefix}_delta_mean"] = q[f"delta_{prefix}"].mean()
                if ci:
                    out[f"{prefix}_delta_ci_lo"], out[f"{prefix}_delta_ci_hi"] = boot(q, f"delta_{prefix}")
    if ci:
        out["mean_ci_lo"], out["mean_ci_hi"] = boot(q, "result")
        out["positive_ci_lo"], out["positive_ci_hi"] = boot(q, "positive")
    return out


def save_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, float_format="%.10g")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path(__file__).resolve().parents[1]/"durable_pivots_20261021")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent/"results")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.baseline))
    import study
    started = time.time()
    protocol = Path(__file__).with_name("PROTOCOL.md")
    registration = {
        "registered_before_outcomes_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "protocol_sha256": sha(protocol), "code_sha256": sha(__file__),
        "baseline_code_sha256": sha(args.baseline/"study.py"),
        "selection_sha256": sha(args.baseline/"results/selection_lock.json"),
        "manifest_sha256": sha(args.baseline/"data/input_manifest.json"),
        "sector_map": SECTORS, "seed": SEED, "horizons": HORIZONS,
        "sample_status": "already exposed; exploratory; no new independent holdout",
    }
    dump(args.out/"registration.json", registration)
    meta, data, items, eqcal, ccal = study.load_inputs(args.baseline/"data/input_manifest.json")
    spy_ind = study.basic_indicators(data["SPY"])
    mr = pd.Series(np.where((data["SPY"].close > spy_ind.sma200) & (spy_ind.sma200_slope > 0), "up",
                  np.where((data["SPY"].close < spy_ind.sma200) & (spy_ind.sma200_slope < 0), "down", "mixed")), index=data["SPY"].index)
    allrows, inputrows, eventrows = [], [], []
    for ticker, d in data.items():
        group = items[ticker]["asset_class"]
        f = study.features(d, ccal if group == "crypto" else eqcal, crypto=group == "crypto")
        daily = f["1D"]
        z = pd.DataFrame({"date": d.index, "ticker": ticker, "asset_class": group, "t": np.arange(len(d))}, index=d.index)
        z["valid"] = (f["1W"].valid.fillna(False) & f["2W"].valid.fillna(False) & daily.atr.notna())
        z["own_regime"] = np.where((d.close > daily.sma200) & (daily.sma200_slope > 0), "up",
                                   np.where((d.close < daily.sma200) & (daily.sma200_slope < 0), "down", "mixed"))
        z["market_regime"] = mr.reindex(d.index, method="ffill").fillna("unknown")
        z["halfyear"] = d.index.year*2 + (d.index.month > 6).astype(int)
        z["quarter"] = d.index.to_period("Q").astype(str)
        z["year"] = d.index.year
        z["daily_stoch"] = daily.bottom_curl.fillna(False).astype(bool)
        z["weekly_stoch"] = f["1W"].bottom_curl.fillna(False).astype(bool)
        z["leader"] = False
        z["leader_known"] = False
        z["reset"] = False
        z["sector_proxy"] = ""
        if ticker in SECTORS:
            sector = SECTORS[ticker]
            s = data[sector].adjclose.reindex(d.index)
            spy = data["SPY"].adjclose.reindex(d.index)
            mom = d.adjclose.shift(21)/d.adjclose.shift(252)-1
            sm = s.shift(21)/s.shift(252)-1
            mm = spy.shift(21)/spy.shift(252)-1
            known = pd.concat([mom, sm, mm, daily.sma200, daily.sma200_slope], axis=1).notna().all(axis=1)
            lead = ((d.close > daily.sma200) & (daily.sma200_slope > 0) & (mom > mm) & (mom > sm))
            z["leader_known"] = known.shift(21, fill_value=False)
            z["leader"] = lead.shift(21, fill_value=False)
            z["reset"], z["peak_t"], z["trough_t"] = reset_state(d, daily.atr)
            reclaim = (d.close > daily.ema10) & (d.close.shift(1) <= daily.ema10.shift(1))
            at = study.event_indices(reclaim & z.reset, z.valid & z.leader_known, 21)
            eventrows.append(z.iloc[at][["ticker", "date", "leader", "reset", "daily_stoch", "weekly_stoch"]].reset_index(drop=True))
            z["sector_proxy"] = sector
            inputrows.append({"ticker": ticker, "sector_proxy": sector, "valid_dates": int(z.valid.sum()),
                              "leadership_unknown_valid_dates": int((z.valid & ~z.leader_known).sum()),
                              "first_leadership_known": str(z.index[z.leader_known].min())})
        for horizon in HORIZONS:
            o = forward_outcomes(d, daily.atr.to_numpy(), horizon)
            b = z.join(o)
            b["horizon"] = horizon
            b["period"] = period_labels(d.index, b.exit_date)
            b = b[b.valid & b.period.ne("excluded") & b.net20.notna()].copy()
            b["win"] = (b.net20 > 0).astype(float)
            b["stop_win"] = (b.stop_net20 > 0).astype(float).where(b.stop_net20.notna())
            allrows.append(b.reset_index(drop=True))
        print("BUILT", ticker, len(d), flush=True)
    panel = pd.concat(allrows, ignore_index=True)
    add_leave_one_out(panel, ["ticker", "horizon", "period", "halfyear", "own_regime", "market_regime"], "ordinary")
    # Fixed same-date peer group, excluding the focal asset.
    pg = panel.groupby(["date", "asset_class", "horizon"])
    pc = pg.net20.transform("count")-1
    minimum = np.where(panel.asset_class.eq("crypto"), 1, 2)
    panel["peer_net20"] = ((pg.net20.transform("sum")-panel.net20)/pc).where(pc >= minimum)
    spyrows = panel[panel.ticker.eq("SPY")].set_index(["date", "horizon"]).net20
    keys = pd.MultiIndex.from_frame(panel[["date", "horizon"]])
    panel["spy_net20"] = spyrows.reindex(keys).to_numpy()
    bysymbol = panel.set_index(["ticker", "date", "horizon"]).net20
    skeys = pd.MultiIndex.from_arrays([panel.sector_proxy, panel.date, panel.horizon])
    panel["sector_net20"] = bysymbol.reindex(skeys).to_numpy()
    leaders = panel[panel.asset_class.eq("us_stock") & panel.leader_known].copy()
    add_leave_one_out(leaders, ["ticker", "horizon", "period", "halfyear", "leader", "reset", "market_regime"], "state")
    panel.to_parquet(args.out/"ordinary_panel.parquet", index=False)
    save_csv(args.out/"leadership_input_coverage.csv", inputrows)
    frozen = json.loads((args.baseline/"results/selection_lock.json").read_text())["selected"]
    old = pd.read_parquet(args.baseline/"results/base_events.parquet")
    audit, audit_sub, ledgers = [], [], []
    for spec in frozen:
        rule = spec["rule"]
        q = old[old.base.eq(rule["base"])]
        if rule["filter"] != "none":
            q = q[q[rule["filter"]].fillna(False).astype(bool)]
        keep = ["ticker", "date", "qualified", "primary63", "age", "distance"]
        joined = q[keep].merge(panel, on=["ticker", "date"], how="inner", validate="one_to_many")
        joined["rule_id"], joined["side"] = rule["rule_id"], rule["side"]
        ledgers.append(joined)
        for (period, horizon), part in joined.groupby(["period", "horizon"]):
            for pool in ("primary", "stocks", "crypto"):
                mask = part.asset_class.eq("crypto") if pool == "crypto" else part.asset_class.eq("us_stock") if pool == "stocks" else ~part.asset_class.eq("crypto")
                subset = part[mask]
                if subset.empty:
                    continue
                label = {"rule_id": rule["rule_id"], "side": rule["side"], "period": period, "horizon": horizon, "pool": pool}
                audit.append({**label, **metrics(subset, rule["side"])})
                if pool == "primary":
                    audit.append({**label, "pool": "primary_nonoverlap", **metrics(nonoverlap(subset, horizon), rule["side"])})
                    for field in ("market_regime", "asset_class", "year", "ticker"):
                        for value, cell in subset.groupby(field):
                            audit_sub.append({**label, "dimension": field, "value": value, **metrics(cell, rule["side"], ci=False)})
                    for name, cell in [("exclude2020", subset[subset.year.ne(2020)]), ("exclude_semis", subset[~subset.ticker.isin(["NVDA", "AMD", "MU", "INTC", "SOXX"])])]:
                        audit_sub.append({**label, "dimension": "concentration", "value": name, **metrics(cell, rule["side"], ci=False)})
    save_csv(args.out/"frozen_rule_audit.csv", audit)
    save_csv(args.out/"frozen_rule_subgroups.csv", audit_sub)
    audit_events = pd.concat(ledgers, ignore_index=True)
    audit_events.to_parquet(args.out/"audit_events.parquet", index=False)
    # Compact recent ledger permits inspection without publishing the whole price panel.
    lc = ["rule_id", "side", "ticker", "asset_class", "date", "horizon", "entry_date", "exit_date", "qualified", "primary63", "net20", "net50", "stop_net20", "stop_hit", "mae", "ordinary_net20", "ordinary_win", "peer_net20", "spy_net20"]
    audit_events[audit_events.period.eq("2020_2026_exposed")][lc].to_csv(args.out/"recent_audit_events.csv", index=False, float_format="%.8g")
    # Shared price-event timestamps: gating never moves the entry date.
    event_keys = pd.concat(eventrows, ignore_index=True)[["ticker", "date"]]
    entries = event_keys.merge(leaders, on=["ticker", "date"], how="inner", validate="one_to_many")
    entries.to_parquet(args.out/"mechanism_events.parquet", index=False)
    entries.to_csv(args.out/"mechanism_events.csv", index=False, float_format="%.8g")
    state_rows, mechanism_rows, mechanism_sub = [], [], []
    for (period, horizon, leader, reset), q in leaders.groupby(["period", "horizon", "leader", "reset"]):
        state_rows.append({"period": period, "horizon": horizon, "leader": leader, "reset": reset, **metrics(q, ci=False)})
    for (period, horizon), q in entries.groupby(["period", "horizon"]):
        arms = {
            "reset_reclaim_all": q,
            "leader_reset_reclaim": q[q.leader],
            "nonleader_reset_reclaim": q[~q.leader],
            "leader_weekly_stoch_yes": q[q.leader & q.weekly_stoch],
            "leader_weekly_stoch_no": q[q.leader & ~q.weekly_stoch],
            "leader_daily_stoch_yes": q[q.leader & q.daily_stoch],
            "leader_daily_stoch_no": q[q.leader & ~q.daily_stoch],
        }
        for arm, cell in arms.items():
            label = {"arm": arm, "period": period, "horizon": horizon}
            mechanism_rows.append({**label, "overlap": "original", **metrics(cell)})
            mechanism_rows.append({**label, "overlap": "nonoverlap", **metrics(nonoverlap(cell, horizon))})
            for field in ("market_regime", "sector_proxy", "ticker", "year"):
                for value, sub in cell.groupby(field):
                    mechanism_sub.append({**label, "dimension": field, "value": value, **metrics(sub, ci=False)})
            for name, sub in [("exclude2020", cell[cell.year.ne(2020)]), ("exclude_semis", cell[~cell.ticker.isin(["NVDA", "AMD", "MU", "INTC"])])]:
                mechanism_sub.append({**label, "dimension": "concentration", "value": name, **metrics(sub, ci=False)})
    save_csv(args.out/"state_census.csv", state_rows)
    save_csv(args.out/"mechanism_summary.csv", mechanism_rows)
    save_csv(args.out/"mechanism_subgroups.csv", mechanism_sub)
    summary = {**registration, "completed_utc": pd.Timestamp.now(tz="UTC").isoformat(),
               "elapsed_seconds": time.time()-started, "ordinary_rows": len(panel),
               "frozen_rules": len(frozen), "audit_event_horizon_rows": len(audit_events),
               "mechanism_event_horizon_rows": len(entries), "new_parameter_searches": 0,
               "protocol_unchanged": sha(protocol) == registration["protocol_sha256"],
               "code_unchanged": sha(__file__) == registration["code_sha256"],
               "results": {p.name: sha(p) for p in sorted(args.out.glob("*.csv"))}}
    dump(args.out/"run_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
