"""Frozen multi-cycle proxy comparison of existing entry/recommendation gates.

Research only: no ranking, allocation, order, live output or calibration promotion.
Reuses the native calibration/entry/extension/statistics owners. See preregistration.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import basket_score, theme_extension, theme_scoring, validation
from engine.trial_ledger import TrialLedger
from lib import nyse_calendar
from scripts import calibrate_baskets as calibration
from scripts.thematic_rotation_phase0 import REGION_SECTORS, COST

FAMILY = "theme_entry_two_gate_ablation_20260922"
SOURCE_REF = "1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee"
ARMS = ("incumbent", "entry_veto_only", "recommendation_veto_only",
        "both_rs_vetoes", "both_with_price_bound")
CORE = tuple(REGION_SECTORS["us"]["core"])
BENCH = REGION_SECTORS["us"]["bench"]
WARMUP = 504
STEP = 5
HORIZONS = (5, 21, 63)
SPLIT = "2018-01-01"
RS_ENTRY = 0.75
RS_RECO = 0.85
QUALITY = 0.60
ROUND_TRIP_COST = 2 * COST
PREREG = Path(__file__).with_name("ENTRY_GATE_COMPARISON_PREREG.md")
NATIVE_PATHS = ("engine/basket_score.py", "engine/theme_extension.py",
                "engine/group_flow.py", "engine/indicators.py", "engine/validation.py",
                "lib/nyse_calendar.py", "scripts/calibrate_baskets.py",
                "scripts/thematic_rotation_phase0.py")


def read_blob(ref: str, path: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", ref) is None:
        raise ValueError("an immutable full source commit is required")
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)


def fixed_config(arm: str, source_ref: str) -> dict:
    if arm not in ARMS:
        raise ValueError("unknown preregistered arm")
    return {"arm": arm, "source_ref": source_ref, "core": list(CORE), "benchmark": BENCH,
            "warmup": WARMUP, "step": STEP, "horizons": list(HORIZONS), "split": SPLIT,
            "entry_rs": RS_ENTRY, "recommendation_rs": RS_RECO, "quality": QUALITY,
            "extra_entry_extension_lt": theme_extension.STRETCHED,
            "round_trip_cost": ROUND_TRIP_COST, "fill": "next_expected_session_close",
            "feature_scope": "native_sector_proxy_neutral_macro_no_mtf"}


def arm_decisions(level: pd.Series, fp: dict, breadth: dict, label: str,
                  crowd: float, rsi: float, extension: float | None) -> dict:
    """One immutable decision prefix, five research reads; no input mutation.

    The entry-veto ablation retains ORIGINAL quality, not the .20 bonus earned
    by changing the counterfactual RS input. Labels/crowding remain frozen.
    """
    values = (fp.get("rs_pctile"), fp.get("accel_z"), crowd, rsi)
    if any(v is None or isinstance(v, bool) or not math.isfinite(float(v)) for v in values):
        raise ValueError("finite native inputs required")
    original = basket_score.clean_entry(level, fp, breadth, rsi)
    cf = basket_score.clean_entry(level, {**fp, "rs_pctile": math.nextafter(RS_ENTRY, 0.0)}, breadth, rsi)
    entry_relaxed = bool(original["flag"] or
                         (original["quality"] >= QUALITY and cf["flag"]
                          and fp["rs_pctile"] >= RS_ENTRY))
    reco = theme_scoring._reco(label, 0.0, crowd, fp)
    cf_reco = theme_scoring._reco(label, 0.0, crowd,
                                 {**fp, "rs_pctile": math.nextafter(RS_RECO, 0.0)})
    if label != "dominant":
        cf_reco = reco
    positive = reco in ("enter", "accumulate")
    relaxed_positive = cf_reco in ("enter", "accumulate")
    control = bool(positive and original["flag"])
    both = bool(relaxed_positive and entry_relaxed)
    known_extension = (extension is not None and not isinstance(extension, bool)
                       and math.isfinite(float(extension)))
    flags = {
        "incumbent": control,
        "entry_veto_only": bool(positive and entry_relaxed),
        "recommendation_veto_only": bool(relaxed_positive and original["flag"]),
        "both_rs_vetoes": both,
        "both_with_price_bound": bool(control or (both and known_extension
                                                   and extension < theme_extension.STRETCHED)),
    }
    assert not control or all(flags.values()), "no arm may remove incumbent selections"
    return {**flags, "native_reco": reco, "native_entry": bool(original["flag"]),
            "native_quality": float(original["quality"]),
            "counterfactual_quality": float(cf["quality"])}


def prepare_panel(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    """Validate the fixed universe and retain missing expected sessions as holes."""
    symbols = (*CORE, BENCH)
    if set(frames) != set(symbols):
        raise ValueError("all nine native core proxies and SPY are required, no substitutions")
    columns, reports = {}, {}
    ends = set()
    for symbol in symbols:
        frame = frames[symbol]
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.empty or "close" not in frame:
            raise ValueError(f"invalid native close frame: {symbol}")
        index = frame.index
        if index.tz is not None or not index.is_monotonic_increasing or index.has_duplicates:
            raise ValueError(f"unordered, duplicate or timezone-ambiguous dates: {symbol}")
        if not (index == index.normalize()).all():
            raise ValueError(f"daily closes require date-only rows: {symbol}")
        close = pd.to_numeric(frame["close"], errors="raise").astype(float)
        if not np.isfinite(close.to_numpy()).all() or (close <= 0).any():
            raise ValueError(f"invalid close values: {symbol}")
        mask = [nyse_calendar.is_session(d.date()) for d in index]
        retained = close.loc[mask]
        if retained.empty:
            raise ValueError(f"no valid sessions: {symbol}")
        columns[symbol] = retained
        ends.add(retained.index[-1])
        reports[symbol] = {"rows": len(frame), "non_session_rows_excluded": int(len(frame)-sum(mask)),
                           "first_session": str(retained.index[0].date()),
                           "last_session": str(retained.index[-1].date())}
    if len(ends) != 1:
        raise ValueError("mixed last-session inputs cannot be presented as one cohort")
    start = max(v.index[0] for v in columns.values())
    end = next(iter(ends))
    sessions = pd.DatetimeIndex(nyse_calendar.sessions_between(start.date(), end.date()))
    panel = pd.DataFrame(columns).reindex(sessions)
    for symbol in symbols:
        reports[symbol]["missing_expected_sessions"] = int(panel[symbol].isna().sum())
    return panel, reports


def decision_frame(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Causal vectorized owners plus native scalar functions on each prefix.

    The rolling native feature arrays are computed once; prefix invariance is
    tested independently. No future outcome or adjusted cohort feeds selection.
    """
    prices, bench = panel[list(CORE)], panel[BENCH]
    breadth_frame = calibration._panel_breadth(prices)
    features = {c: calibration._rs_features(prices[c], bench) for c in CORE}
    ma200 = prices.rolling(200, min_periods=100).mean()
    good_prefix = panel.notna().all(axis=1).rolling(WARMUP, min_periods=WARMUP).sum() == WARMUP
    rows, refusals = [], Counter()
    for i in range(WARMUP, len(panel), STEP):
        if not good_prefix.iloc[i]:
            refusals["incomplete_trailing_native_input_window"] += len(CORE)
            continue
        observed = str(panel.index[i].date())
        bd = {"pct50": float(breadth_frame["pct50"].iloc[i]),
              "nh": int(breadth_frame["nh"].iloc[i]), "nl": int(breadth_frame["nl"].iloc[i])}
        for symbol in CORE:
            f = features[symbol]
            vals = {k: float(f[k].iloc[i]) for k in ("accel_z", "rs_pctile", "r5", "r20", "r60", "delta_5d")}
            if not all(math.isfinite(x) for x in vals.values()):
                refusals["native_feature_unavailable"] += 1
                continue
            prefix = prices[symbol].iloc[:i+1]
            rsi = basket_score._rsi(prefix)
            if rsi is None or not math.isfinite(float(rsi)):
                refusals["native_rsi_unavailable"] += 1
                continue
            above = prefix.iloc[-1] > ma200[symbol].iloc[i]
            slope = ma200[symbol].iloc[i] - ma200[symbol].iloc[i-21]
            sign = 1 if above and slope > 0 else (-1 if not above and slope <= 0 else 0)
            fp = {"accel_z": vals["accel_z"], "rs_pctile": vals["rs_pctile"], "long_sign": sign}
            crowd = calibration._crowd_pen(fp["rs_pctile"])
            trend = calibration._trend_leg(vals["r5"], vals["r20"], vals["r60"], vals["accel_z"])
            bl = calibration._breadth_leg(bd["pct50"], breadth_frame["pct200"].iloc[i],
                                          breadth_frame["net_nh"].iloc[i])
            score = calibration._proxy_score(trend, bl, crowd)
            perf = {f"{h}d": {"rel": vals[f"r{h}"]} for h in (5, 20, 60)}
            label = theme_scoring._label(score, fp, perf, bd, vals["delta_5d"])
            extension = theme_extension._atr_ext(prefix)
            flags = arm_decisions(prefix, fp, bd, label, crowd, float(rsi), extension)
            rows.append({"decision_date": observed, "asset": symbol, "bar": i,
                         "label": label, "proxy_score": score, "rs_pctile": fp["rs_pctile"],
                         "close_atr_extension": extension, **flags})
    return pd.DataFrame(rows), dict(refusals)


def forward_outcome(panel: pd.DataFrame, symbol: str, bar: int, horizon: int) -> dict:
    """Strictly delayed entry and complete close paths. Future gaps remain null."""
    if horizon not in HORIZONS or symbol not in CORE or bar < 0 or bar >= len(panel):
        raise ValueError("invalid outcome request")
    observed = panel.index[bar].date()
    enter = nyse_calendar.session_n_forward(observed, 1)
    leave = nyse_calendar.session_n_forward(enter, horizon) if enter else None
    if enter is None or leave is None or pd.Timestamp(leave) > panel.index[-1]:
        return {"status": "tail_unavailable", "entry_date": str(enter) if enter else None,
                "exit_date": str(leave) if leave else None}
    idx = pd.DatetimeIndex(nyse_calendar.sessions_between(enter, leave))
    sub = panel[[symbol, BENCH]].reindex(idx)
    if len(sub) != horizon+1 or sub.isna().any().any():
        return {"status": "missing_future_session", "entry_date": str(enter), "exit_date": str(leave)}
    x, b = sub[symbol], sub[BENCH]
    gross = float(x.iloc[-1]/x.iloc[0]-1)
    benchmark = float(b.iloc[-1]/b.iloc[0]-1)
    return {"status": "observed", "entry_date": str(enter), "exit_date": str(leave),
            "net_return": gross-ROUND_TRIP_COST, "net_relative": gross-benchmark-ROUND_TRIP_COST,
            "mae": float(x.min()/x.iloc[0]-1), "mfe": float(x.max()/x.iloc[0]-1)}


def add_outcomes(panel: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in decisions.to_dict("records"):
        for horizon in HORIZONS:
            outcome = forward_outcome(panel, row["asset"], int(row["bar"]), horizon)
            split = ("assessment" if row["decision_date"] >= SPLIT else
                     "development" if outcome.get("exit_date") and outcome["exit_date"] < SPLIT
                     else "partition_boundary_purged")
            rows.append({**row, "horizon": horizon, "partition": split, **outcome})
    return pd.DataFrame(rows)


def group_metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"n_events": 0, "n_dates": 0, "net_mean": None, "relative_mean": None,
                "negative_net_share": None, "mae_below_minus8_share": None}
    return {"n_events": len(frame), "n_dates": int(frame["decision_date"].nunique()),
            "net_mean": float(frame["net_return"].mean()),
            "relative_mean": float(frame["net_relative"].mean()),
            "net_median": float(frame["net_return"].median()),
            "negative_net_share": float((frame["net_return"] < 0).mean()),
            "mae_mean": float(frame["mae"].mean()),
            "mae_below_minus8_share": float((frame["mae"] < calibration.DD_RISK).mean())}


def summarize(outcomes: pd.DataFrame) -> dict:
    """Same fully observed date/asset population for all arms and paired inference."""
    if outcomes.empty:
        return {"partitions": {}, "dispositions": {}, "promotion_authorized": False}
    report, pvalues = {}, {}
    for partition in ("development", "assessment"):
        partition_result = {}
        for horizon in HORIZONS:
            raw = outcomes[(outcomes["partition"] == partition) & (outcomes["horizon"] == horizon)]
            known = raw[raw["status"] == "observed"]
            sizes = known.groupby("decision_date")["asset"].nunique()
            full_dates = sizes[sizes == len(CORE)].index
            known = known[known["decision_date"].isin(full_dates)]
            if known.duplicated(["decision_date", "asset"]).any():
                raise ValueError("duplicate event identities cannot inflate inference")
            base_budget = (known["net_relative"] * known["incumbent"].astype(float)).groupby(known["decision_date"]).sum()/len(CORE)
            arms = {}
            for arm in ARMS:
                selected = known[known[arm]]
                extra = selected[~selected["incumbent"]]
                budget = (known["net_relative"]*known[arm].astype(float)).groupby(known["decision_date"]).sum()/len(CORE)
                delta = budget-base_budget
                inference = validation.newey_west_tstat(delta, lags=math.ceil(horizon/STEP))
                arms[arm] = {"selected": group_metrics(selected), "additional": group_metrics(extra),
                             "fixed_slot_event_budget_relative_mean": float(budget.mean()) if len(budget) else None,
                             "paired_vs_incumbent": inference,
                             "selected_slot_share": float(len(selected)/(len(full_dates)*len(CORE))) if len(full_dates) else None,
                             "additional_by_asset": {str(k): group_metrics(v) for k,v in extra.groupby("asset")},
                             "additional_by_era": {
                                 era: group_metrics(extra[(extra["decision_date"] >= lo) & (extra["decision_date"] < hi)])
                                 for era, lo, hi in (("2000s", "2000-01-01", "2010-01-01"),
                                                     ("2010s", "2010-01-01", "2020-01-01"),
                                                     ("2020s", "2020-01-01", "2030-01-01"))
                             }}
                if arm != "incumbent" and horizon == 21 and partition == "assessment" and inference["p"] is not None:
                    pvalues[arm] = inference["p"]
            partition_result[str(horizon)] = {"full_observation_dates": len(full_dates),
                                               "incomplete_date_events_excluded": int(len(raw)-len(known)),
                                               "arms": arms}
        report[partition] = partition_result
    bh = validation.benjamini_hochberg(pvalues, alpha=0.10) if pvalues else {}
    return {"partitions": report, "assessment_primary_bh": bh,
            "dispositions": {str(k): int(v) for k,v in outcomes["status"].value_counts().items()},
            "purged_partition_events": int((outcomes["partition"] == "partition_boundary_purged").sum()),
            "promotion_authorized": False,
            "estimand": "non_compounded_fixed_nine_slot_overlapping_event_budget_not_portfolio"}


def run(source_ref: str, output: Path, prereg_commit: str) -> dict:
    if source_ref != SOURCE_REF:
        raise ValueError("source vintage differs from the preregistered comparison")
    frozen = read_blob(prereg_commit, str(PREREG.relative_to(ROOT)))
    if frozen != PREREG.read_bytes():
        raise ValueError("preregistration differs from its pre-outcome frozen commit")
    # Refuse a changed native dependency rather than silently reinterpret the study.
    native_hashes = {}
    for path in NATIVE_PATHS:
        raw = read_blob(source_ref, path)
        if raw != (ROOT/path).read_bytes():
            raise ValueError(f"native dependency moved: {path}")
        native_hashes[path] = hashlib.sha256(raw).hexdigest()
    from prove import policy_parity
    policy_proof = policy_parity(source_ref)
    native_hashes["engine/theme_scoring.py"] = hashlib.sha256((ROOT/"engine/theme_scoring.py").read_bytes()).hexdigest()
    ledger_path = ROOT/"data/trial_ledger.jsonl"
    if not ledger_path.exists():
        raise ValueError("materialize the existing canonical trial ledger before running")
    ledger = TrialLedger(ledger_path, family=FAMILY)
    ledger.log_grid([fixed_config(a,source_ref) for a in ARMS], info_cutoff="2026-09-22")
    if ledger.effective_n(FAMILY) != len(ARMS):
        raise ValueError("unexpected prior variants in the fixed study family")
    raw_inputs = {f"data/yahoo/{s}.parquet": read_blob(source_ref,f"data/yahoo/{s}.parquet") for s in (*CORE,BENCH)}
    frames = {s:pd.read_parquet(io.BytesIO(raw_inputs[f"data/yahoo/{s}.parquet"])) for s in (*CORE,BENCH)}
    panel, metadata = prepare_panel(frames)
    decisions, refusals = decision_frame(panel)
    if decisions.empty:
        raise ValueError("no complete decision-time proxy inputs after warm-up")
    outcomes = add_outcomes(panel,decisions)
    result = {"schema":"theme_entry_gate_proxy_comparison.v1", "source_ref":source_ref,
              "prereg_commit":prereg_commit,"prereg_sha256":hashlib.sha256(frozen).hexdigest(),
              "study_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "source_sha256":{p:hashlib.sha256(b).hexdigest() for p,b in raw_inputs.items()},
              "native_sha256":native_hashes,"input_metadata":metadata,"incumbent_policy_parity":policy_proof,
              "trial_family":FAMILY,"registered_arms":ledger.effective_n(FAMILY),
              "universe":list(CORE),"price_start":str(panel.index[0].date()),"price_end":str(panel.index[-1].date()),
              "decision_rows":len(decisions),"decision_refusals":refusals,
              "selection_counts":{a:int(decisions[a].sum()) for a in ARMS},
              "config":[fixed_config(a,source_ref) for a in ARMS], **summarize(outcomes),
              "limitations":["Causal reconstruction on current-vintage close archive, not logged-at historical replay.",
                             "Sector panel breadth and neutral macro are proxies, not the full Prophet or constituent engine.",
                             "Retrospective partition, not prospective validation; no threshold fitting.",
                             "Overlapping event outcomes are not portfolio CAGR, Sharpe or actual fills.",
                             "No individual CPU stock, current market, rank, entry, sizing or live policy claim."]}
    output.mkdir(parents=True,exist_ok=True)
    csv=outcomes.to_csv(index=False,float_format="%.12g").encode()
    compressed=gzip.compress(csv,mtime=0)
    (output/"events.csv.gz").write_bytes(compressed)
    result["event_file_sha256"]=hashlib.sha256(compressed).hexdigest()
    (output/"comparison.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--prereg-commit",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    result=run(args.source_ref,args.output,args.prereg_commit)
    print(json.dumps({k:result[k] for k in ("price_start","price_end","decision_rows","decision_refusals","selection_counts","assessment_primary_bh")},indent=2))


if __name__=="__main__":
    main()
