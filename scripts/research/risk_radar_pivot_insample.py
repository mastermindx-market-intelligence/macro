"""In-sample pivot scorecard for the shipped Radar and the fixed baselines, 2020-01-02 onward.

Research-only, IN-SAMPLE (the v2 constants were chosen on this window; 2024+ is the Radar's own
seen history, not the desk's sealed confirmation). Usage:
    python3 scripts/research/risk_radar_pivot_insample.py [--states /tmp/rr_insample_states.parquet]
Writes research/risk_radar/walkforward/PIVOT_INSAMPLE_v2_2020-2026.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.risk_radar_eval import inputs as I, labels as L, pivots as P  # noqa: E402

START = pd.Timestamp("2020-01-02")
OUT = Path("research/risk_radar/walkforward/PIVOT_INSAMPLE_v2_2020-2026.json")
LOUD = {"elevated", "risk-off"}


def _states(path: str | None) -> pd.Series:
    if path and Path(path).exists():
        return pd.read_parquet(path)["state"]
    from engine import risk_radar_backtest as bt
    return bt.state_series()["state"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--states")
    ap.add_argument("--pre", type=int, default=P.DEFAULT_PRE)
    args = ap.parse_args()
    px = L.spy_total_return()
    st = _states(args.states)
    cut = min(px.index.max(), st.index.max())
    idx = px.index[(px.index >= START) & (px.index <= cut)]
    st = st.reindex(idx).ffill()
    flags = I.baseline_flags(I.baseline_scores()).reindex(idx).fillna(False)
    series = {
        "radar_loud": st.isin(LOUD),
        "radar_riskoff": st.eq("risk-off"),
        "radar_caution_plus": st.isin(LOUD | {"caution"}),
        **{f"base_{c}": flags[c].astype(bool) for c in flags.columns},
    }
    # era regimes (dated, not fitted): pandemic/liquidity, inflation/rate shock, AI-led (seen history)
    regime = pd.Series(pd.cut(idx, [pd.Timestamp("2019-12-31"), pd.Timestamp("2021-12-31"),
                                     pd.Timestamp("2023-12-31"), pd.Timestamp("2100-01-01")],
                              labels=["2020-21", "2022-23", "2024+ seen"]).astype(str), index=idx)
    out = {"label": "IN-SAMPLE; 2024+ is seen history", "window": [idx[0].date().isoformat(),
           idx[-1].date().isoformat()], "results": {}}
    for depth in L.DEFAULT_DEPTHS:
        eps = L.drawdown_episodes(px.loc[:cut], depth, outcomes_through=cut)
        eps = [e for e in eps if e.peak >= START]
        turns = P.turns_from_episodes(eps)
        for post in (5, 10, 21):
            for name, a in series.items():
                r = P.score_pivots(a, turns=turns, episodes=eps, outcomes_through=cut,
                                   pre=args.pre, post=post, regime=regime,
                                   seen_history_ok=True, name=name)
                out["results"][f"dd{int(depth*100)}|post{post}|{name}"] = r
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(OUT)


if __name__ == "__main__":
    main()
