#!/usr/bin/env python3
"""Complete reviewed reporting gaps; no signal, parameter, or outcome changes.

Independent review requested top-side benchmark comparisons and a common
nonoverlap roster before oscillator partitioning. Original results are retained.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze


def contrast(a, b, field):
    if a.empty or b.empty:
        return [np.nan, np.nan, np.nan, 0.]
    labels = np.arange(min(a.halfyear.min(), b.halfyear.min()), max(a.halfyear.max(), b.halfyear.max())+1)
    def sums(x):
        g = x.groupby("halfyear")[field].agg(["sum", "count"]).reindex(labels, fill_value=0)
        return g["sum"].to_numpy(), g["count"].to_numpy()
    av, an = sums(a); bv, bn = sums(b)
    rng = np.random.default_rng(analyze.SEED)
    starts = rng.integers(0, len(labels), size=(2000, (len(labels)+1)//2))
    ix = np.stack([starts, (starts+1)%len(labels)], axis=2).reshape(2000, -1)[:, :len(labels)]
    with np.errstate(divide="ignore", invalid="ignore"):
        values = av[ix].sum(axis=1)/an[ix].sum(axis=1)-bv[ix].sum(axis=1)/bn[ix].sum(axis=1)
    good = np.isfinite(values)
    interval = np.quantile(values[good], [.025, .975]) if good.any() else [np.nan, np.nan]
    return [a[field].mean()-b[field].mean(), *interval, float(good.mean())]


def main():
    out = Path(__file__).parent/"results"
    original_hashes = json.loads((out/"run_summary.json").read_text())["results"]
    panel = pd.read_parquet(out/"ordinary_panel.parquet")
    panel["avoid"] = -panel.gross-.002
    panel["avoid_win"] = (panel.avoid > 0).astype(float)
    keys = ["ticker", "horizon", "period", "halfyear", "own_regime", "market_regime"]
    g = panel.groupby(keys)
    n = g.avoid.transform("count")-1
    panel["ordinary_avoid"] = ((g.avoid.transform("sum")-panel.avoid)/n).where(n >= 10)
    panel["ordinary_avoid_win"] = ((g.avoid_win.transform("sum")-panel.avoid_win)/n).where(n >= 10)
    pg = panel.groupby(["date", "asset_class", "horizon"])
    pn = pg.avoid.transform("count")-1
    panel["peer_avoid"] = ((pg.avoid.transform("sum")-panel.avoid)/pn).where(pn >= np.where(panel.asset_class.eq("crypto"), 1, 2))
    spy = panel[panel.ticker.eq("SPY")].set_index(["date", "horizon"]).avoid
    panel["spy_avoid"] = spy.reindex(pd.MultiIndex.from_frame(panel[["date", "horizon"]])).to_numpy()
    ev = pd.read_parquet(out/"audit_events.parquet")
    ev = ev[ev.side.eq("top")].merge(panel[["ticker", "date", "horizon", "avoid", "avoid_win", "ordinary_avoid", "ordinary_avoid_win", "peer_avoid", "spy_avoid"]], on=["ticker", "date", "horizon"], validate="many_to_one")
    top_rows = []
    for (rule, period, horizon), q in ev.groupby(["rule_id", "period", "horizon"]):
        for pool in ("primary", "stocks", "crypto"):
            mask = q.asset_class.eq("crypto") if pool == "crypto" else q.asset_class.eq("us_stock") if pool == "stocks" else ~q.asset_class.eq("crypto")
            cell = q[mask].copy()
            if cell.empty:
                continue
            row = {"rule_id": rule, "period": period, "horizon": horizon, "pool": pool, "n": len(cell), "avoid_mean": cell.avoid.mean(), "avoid_positive": cell.avoid_win.mean()}
            for name in ("ordinary", "peer", "spy"):
                cell["delta"] = cell.avoid-cell[f"{name}_avoid"]
                row[f"{name}_matches"] = int(cell.delta.notna().sum())
                row[f"{name}_avoid_mean"] = cell[f"{name}_avoid"].mean()
                row[f"{name}_delta"] = cell.delta.mean()
                row[f"{name}_delta_ci_lo"], row[f"{name}_delta_ci_hi"] = analyze.boot(cell, "delta")
            row["ordinary_positive"] = cell.ordinary_avoid_win.mean()
            top_rows.append(row)
    analyze.save_csv(out/"top_exit_comparators.csv", top_rows)
    entries = pd.read_parquet(out/"mechanism_events.parquet")
    shared_rows, contrast_rows = [], []
    for (period, horizon), q in entries.groupby(["period", "horizon"]):
        common = analyze.nonoverlap(q, horizon)
        arms = {
            "reset_reclaim_all": common,
            "leader_reset_reclaim": common[common.leader],
            "nonleader_reset_reclaim": common[~common.leader],
            "leader_weekly_stoch_yes": common[common.leader & common.weekly_stoch],
            "leader_weekly_stoch_no": common[common.leader & ~common.weekly_stoch],
            "leader_daily_stoch_yes": common[common.leader & common.daily_stoch],
            "leader_daily_stoch_no": common[common.leader & ~common.daily_stoch],
        }
        for arm, cell in arms.items():
            shared_rows.append({"arm": arm, "period": period, "horizon": horizon, "roster": "common_price_events_nonoverlap", **analyze.metrics(cell)})
        for roster, full in [("original", q), ("common_nonoverlap", common)]:
            leaders = full[full.leader]
            pairs = {
                "leader_minus_nonleader": (leaders, full[~full.leader]),
                "weekly_gate_yes_minus_no": (leaders[leaders.weekly_stoch], leaders[~leaders.weekly_stoch]),
                "daily_gate_yes_minus_no": (leaders[leaders.daily_stoch], leaders[~leaders.daily_stoch]),
            }
            for label, (a, b) in pairs.items():
                for field in ("net20", "win", "stop_net20", "stop_win"):
                    delta, lo, hi, usable = contrast(a, b, field)
                    contrast_rows.append({"contrast": label, "period": period, "horizon": horizon, "roster": roster, "field": field, "n_a": len(a), "n_b": len(b), "delta": delta, "ci_lo": lo, "ci_hi": hi, "usable_bootstrap_fraction": usable})
    analyze.save_csv(out/"shared_nonoverlap.csv", shared_rows)
    analyze.save_csv(out/"gate_contrasts.csv", contrast_rows)
    unchanged = all(analyze.sha(out/name) == digest for name, digest in original_hashes.items())
    assert unchanged, "Original result file changed"
    result = {"completed_utc": pd.Timestamp.now(tz="UTC").isoformat(), "purpose": "complete fixed comparator and common-roster diagnostics after independent review", "signal_or_parameter_changes": 0, "original_csv_files_unchanged": unchanged, "code_sha256": analyze.sha(__file__), "outputs": {name: analyze.sha(out/name) for name in ("top_exit_comparators.csv", "shared_nonoverlap.csv", "gate_contrasts.csv")}}
    analyze.dump(out/"review_supplement.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
