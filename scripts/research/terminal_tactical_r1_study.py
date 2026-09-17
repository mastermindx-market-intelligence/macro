#!/usr/bin/env python3
"""Run the frozen Terminal Tactical R1-A corrected-history study offline.

This is a research consumer: no network, provider fetch, live signal, registry fork,
or order/execution path. Raw input bars remain outside committed outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.entry_radar import tactical_research as tr  # noqa: E402

CONFIG_PATH = ROOT / "research/species/tti_r1/config.json"
PREREG_PATH = ROOT / "research/species/TTI_R1A_PREREG.md"
LEDGER_PATH = ROOT / "data/trial_ledger.jsonl"
UTC = timezone.utc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_config() -> dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text())
    if cfg.get("study_id") != "tti-r1-extended-session-v1" or cfg.get("may_rank") is not False or cfg.get("may_alert") is not False or cfg.get("may_size") is not False:
        raise ValueError("invalid_frozen_config")
    if len(grid_cells(cfg)) != cfg.get("full_grid_size"):
        raise ValueError("grid_size_mismatch")
    return cfg


def grid_cells(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"study_id": cfg["study_id"], "selector": selector, "horizon": horizon,
         "round_trip_cost_bps": int(cost)}
        for selector in cfg["selectors"]
        for horizon in cfg["horizons"]
        for cost in cfg["round_trip_cost_bps"]
    ]


def verify_registered_grid(ledger_path: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    wanted = {json.dumps(x, sort_keys=True, separators=(",", ":")) for x in grid_cells(cfg)}
    found: set[str] = set(); family_rows = 0
    with ledger_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("family") != cfg["trial_family"]:
                continue
            family_rows += 1
            value = row.get("config")
            if isinstance(value, dict) and value.get("study_id") == cfg["study_id"]:
                found.add(json.dumps(value, sort_keys=True, separators=(",", ":")))
    if found != wanted:
        raise ValueError(f"registered_grid_mismatch:{len(found)}/{len(wanted)}")
    return {"study_cells": len(wanted), "family_rows": family_rows,
            "ledger_sha256": _sha(ledger_path)}


def segment_eligible(features: Mapping[str, Any], kind: str, cfg: Mapping[str, Any]) -> bool:
    if kind not in {"ah", "pre"}:
        raise ValueError("unknown_segment_kind")
    observations = features.get("observations"); span = features.get("span_minutes")
    gap = features.get("max_gap_minutes"); last_end = features.get("last_end_minute")
    if not isinstance(observations, int) or observations < int(cfg["min_observations"]):
        return False
    if span is None or float(span) < float(cfg["minimum_span_minutes"]):
        return False
    if gap is None or float(gap) > float(cfg["max_gap_minutes"]):
        return False
    if kind == "pre":
        return last_end == int(cfg["pre_cutoff_minute"])
    return last_end is not None and int(last_end) >= int(cfg["ah_last_end_floor"])


def date_matched_deltas(rows: pd.DataFrame, selected_arm: str, baseline_arm: str) -> pd.DataFrame:
    selected = rows.loc[(rows["arm"] == selected_arm) & rows["net_beta_residual"].notna()]
    baseline = rows.loc[(rows["arm"] == baseline_arm) & rows["net_beta_residual"].notna()]
    if selected.empty or baseline.empty:
        return pd.DataFrame(columns=["date", "delta"])
    a = selected.groupby("date", sort=True)["net_beta_residual"].mean()
    b = baseline.groupby("date", sort=True)["net_beta_residual"].mean()
    joined = pd.concat([a.rename("selected"), b.rename("baseline")], axis=1, join="inner").dropna()
    out = (joined["selected"] - joined["baseline"]).rename("delta").reset_index()
    return out.loc[:, ["date", "delta"]]


def week_block_interval(dated: pd.DataFrame, *, repetitions: int, seed: int) -> dict[str, Any]:
    if dated.empty:
        return {"mean": None, "low": None, "high": None, "blocks": 0, "dates": 0,
                "repetitions": repetitions}
    work = dated.copy(); parsed = pd.to_datetime(work["date"])
    iso = parsed.dt.isocalendar(); work["week"] = iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    groups = [g["delta"].astype(float).to_numpy() for _, g in work.groupby("week", sort=True)]
    rng = np.random.default_rng(seed); draws = np.empty(repetitions, dtype=float)
    for i in range(repetitions):
        sampled = rng.integers(0, len(groups), size=len(groups))
        values = np.concatenate([groups[j] for j in sampled])
        draws[i] = float(np.mean(values))
    return {"mean": float(work["delta"].astype(float).mean()),
            "low": float(np.percentile(draws, 2.5)), "high": float(np.percentile(draws, 97.5)),
            "blocks": len(groups), "dates": int(work["date"].nunique()), "repetitions": repetitions}


def _load_terminal_module(root: Path):
    path = root / "ingest/intraday_qualification.py"
    if not path.is_file():
        raise ValueError("terminal_qualification_module_missing")
    spec = importlib.util.spec_from_file_location("tti_terminal_intraday_qualification", path)
    if spec is None or spec.loader is None:
        raise ValueError("terminal_qualification_module_unloadable")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    for name in ("CalendarProjection", "decode_display_epoch", "qualify_store"):
        if not hasattr(module, name):
            raise ValueError(f"terminal_dependency_missing:{name}")
    return module


def _git_head(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _manifest_map(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    data = json.loads(path.read_text()); out = {}
    for row in data.get("results", []):
        if isinstance(row, dict) and isinstance(row.get("symbol"), str) and isinstance(row.get("timeframe"), str):
            out[(row["symbol"], row["timeframe"])] = row
    return out


def _load_symbol(path: Path, symbol: str, expected_sha: str, d0) -> pd.DataFrame:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"input_digest_mismatch:{symbol}")
    doc = json.loads(raw)
    if doc.get("t") != symbol or doc.get("tf") != "5m" or doc.get("src") not in {"polygon", "massive"} or not isinstance(doc.get("bars"), list):
        raise ValueError(f"input_identity_mismatch:{symbol}")
    rows = []
    for bar in doc["bars"]:
        if not isinstance(bar, list) or len(bar) != 6:
            raise ValueError(f"invalid_bar_shape:{symbol}")
        display = int(bar[0]); true_utc = int(d0.decode_display_epoch(display))
        wall = datetime.fromtimestamp(display, UTC)
        rows.append((true_utc, display, wall.date().isoformat(), wall.hour * 60 + wall.minute,
                     float(bar[1]), float(bar[2]), float(bar[3]), float(bar[4]), float(bar[5])))
    frame = pd.DataFrame(rows, columns=["event_start_utc", "display_epoch", "date", "minute", "o", "h", "l", "c", "v"]).set_index("event_start_utc")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"input_clock_order:{symbol}")
    return frame


def _scheduled_days(calendar, start: str, end: str) -> list[str]:
    first = date.fromisoformat(start); last = date.fromisoformat(end); out=[]
    for n in range((last-first).days+1):
        day=(first+timedelta(days=n)).isoformat()
        if calendar.window(day) is not None: out.append(day)
    return out


def _day_rows(frame: pd.DataFrame, day: str) -> pd.DataFrame:
    return frame.loc[frame["date"] == day]


def _regular(frame: pd.DataFrame, day: str, calendar) -> pd.DataFrame | None:
    window = calendar.window(day)
    if window is None: return None
    opening, closing = window; expected = list(range(opening, closing, 5))
    rows = _day_rows(frame, day); rows = rows.loc[rows["minute"].isin(expected)]
    if rows["minute"].tolist() != expected: return None
    raw = rows.loc[:, ["o","h","l","c","v"]].copy()
    try:
        tr.segment_features(raw)
    except ValueError:
        return None
    return raw


def _segment(frame: pd.DataFrame, day: str, start_minute: int, end_minute: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = _day_rows(frame, day); rows = rows.loc[(rows["minute"] >= start_minute) & ((rows["minute"] + 5) <= end_minute)]
    raw = rows.loc[:, ["o","h","l","c","v"]].copy()
    try:
        features = tr.segment_features(raw)
    except ValueError:
        return raw, {"invalid": True, "input_rows": int(len(raw)), "observations": 0,
                     "return": None, "efficiency": None, "above_bar_vwap_fraction": None,
                     "bar_vwap_proxy": None, "last_close": None, "low": None,
                     "span_minutes": None, "max_gap_minutes": None,
                     "first_start_minute": None, "last_end_minute": None}
    features["invalid"] = False
    evidence_rows = rows.loc[rows["v"].astype(float) > 0]
    if not evidence_rows.empty:
        features["first_start_minute"] = int(evidence_rows.iloc[0]["minute"])
        features["last_end_minute"] = int(evidence_rows.iloc[-1]["minute"]) + 5
    else:
        features["first_start_minute"] = None; features["last_end_minute"] = None
    return raw, features


def _daily_tables(frames: Mapping[str, pd.DataFrame], days: Sequence[str], calendar) -> dict[str, pd.DataFrame]:
    result={}
    for symbol, frame in frames.items():
        rows=[]
        for day in days:
            r=_regular(frame, day, calendar)
            if r is None: continue
            rows.append({"date":day,"o":float(r.iloc[0].o),"h":float(r.h.max()),"l":float(r.l.min()),"c":float(r.iloc[-1].c),"v":float(r.v.sum())})
        if rows:
            d=pd.DataFrame(rows).set_index("date").reindex(days)
        else:
            d=pd.DataFrame(index=pd.Index(days,name="date"),columns=["o","h","l","c","v"],dtype=float)
        if len(d):
            prev=d["c"].shift(1); d["tr"]=np.maximum(d["h"]-d["l"], np.maximum((d["h"]-prev).abs(),(d["l"]-prev).abs()))
            d["atr20"]=d["tr"].rolling(20,min_periods=20).mean(); d["return"]=d["c"].pct_change(fill_method=None)
        result[symbol]=d
    return result


def _beta_for(symbol: str, prior_day: str, days: Sequence[str], daily: Mapping[str, pd.DataFrame], cfg: Mapping[str, Any]) -> float | None:
    position=days.index(prior_day); window=days[max(0,position-int(cfg["beta_lookback"])+1):position+1]
    pairs=[]
    for day in window:
        if day in daily[symbol].index and day in daily[cfg["benchmark"]].index:
            a=daily[symbol].at[day,"return"]; b=daily[cfg["benchmark"]].at[day,"return"]
            if pd.notna(a) and pd.notna(b): pairs.append((float(a),float(b)))
    if len(pairs) < int(cfg["beta_minimum"]): return None
    x=np.asarray([p[0] for p in pairs]); y=np.asarray([p[1] for p in pairs]); var=float(np.var(y,ddof=1))
    if not math.isfinite(var) or var <= 0: return None
    beta=float(np.cov(x,y,ddof=1)[0,1]/var)
    return float(np.clip(beta,0.0,3.0)) if math.isfinite(beta) else None


def _display_epoch(day: str, minute: int) -> int:
    midnight=int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp())
    return midnight + minute * 60


def _true_epoch(day: str, minute: int, d0) -> int:
    return int(d0.decode_display_epoch(_display_epoch(day, minute)))


def _expected_path(days: Sequence[str], day_index: int, entry_minute: int, horizon: str, calendar, d0) -> list[int] | None:
    current=days[day_index]; window=calendar.window(current)
    if window is None or entry_minute < window[0] or entry_minute >= window[1]: return None
    if horizon == "60m":
        end=min(entry_minute+60, window[1]); minutes=list(range(entry_minute,end,5))
        return [_true_epoch(current,m,d0) for m in minutes] if end-entry_minute==60 else None
    future_count={"close":0,"1d":1,"3d":3}.get(horizon)
    if future_count is None or day_index+future_count >= len(days): return None
    path=[]
    for offset in range(future_count+1):
        d=days[day_index+offset]; ow,cw=calendar.window(d)
        start=entry_minute if offset==0 else ow
        path.extend(_true_epoch(d,m,d0) for m in range(start,cw,5))
    return path


def _feature_panel(frames: Mapping[str,pd.DataFrame], daily: Mapping[str,pd.DataFrame], days: Sequence[str], calendar, d0, cfg: Mapping[str,Any]) -> tuple[pd.DataFrame, Counter]:
    records=[]; reasons=Counter()
    benchmark=cfg["benchmark"]
    for i, day in enumerate(days):
        if i < 4: continue
        prior=days[i-1]
        for symbol in cfg["symbols"]:
            rth=_regular(frames[symbol], prior, calendar)
            if rth is None:
                reasons["prior_rth_incomplete"] += 1; records.append({"date":day,"ticker":symbol,"comparable":False,"arms":()}); continue
            if calendar.window(prior)[1] != 960:
                reasons["early_close_ah_unqualified"] += 1; records.append({"date":day,"ticker":symbol,"comparable":False,"arms":()}); continue
            _,ah=_segment(frames[symbol],prior,960,1200); _,pre=_segment(frames[symbol],day,240,int(cfg["pre_cutoff_minute"])); opening_frame,opening_features=_segment(frames[symbol],day,570,int(cfg["open_cutoff_minute"])); opening_features["complete"] = opening_frame.index.size==3 and opening_features["observations"]==3
            if not segment_eligible(ah,"ah",cfg): reasons["ah_ineligible"] += 1
            if not segment_eligible(pre,"pre",cfg): reasons["pre_ineligible"] += 1
            atr=float(daily[symbol].at[prior,"atr20"]) if prior in daily[symbol].index and pd.notna(daily[symbol].at[prior,"atr20"]) else None
            beta=_beta_for(symbol,prior,days,daily,cfg)
            prior_ret=float(daily[symbol].at[prior,"return"]) if prior in daily[symbol].index and pd.notna(daily[symbol].at[prior,"return"]) else None
            prior_close=float(daily[symbol].at[prior,"c"]) if prior in daily[symbol].index else None
            three=None
            required=days[i-4:i]
            if all(d in daily[symbol].index and pd.notna(daily[symbol].at[d,"c"]) for d in required):
                three=float(daily[symbol].at[prior,"c"]-daily[symbol].at[days[i-4],"c"])
            comparable=segment_eligible(ah,"ah",cfg) and segment_eligible(pre,"pre",cfg) and atr is not None and beta is not None and prior_ret is not None
            row={"date":day,"ticker":symbol,"comparable":comparable,"ah":ah,"pre":pre,"opening":opening_features,
                 "prior_close":prior_close,"prior_return":prior_ret,"three_day_change":three,"atr20":atr,"beta":beta}
            row["arms"]=tr.select_arms(row,cfg)
            if not comparable: reasons["not_comparable"] += 1
            records.append(row)
    return pd.DataFrame(records), reasons


def _outcome_rows(panel: pd.DataFrame, frames: Mapping[str,pd.DataFrame], days: Sequence[str], calendar, d0, cfg: Mapping[str,Any]) -> pd.DataFrame:
    rows=[]; early={"ALL_EARLY","GAP_UP","PERSISTENT","WEAKNESS_PERSISTENT","WEAKNESS_RECLAIM"}
    day_pos={d:i for i,d in enumerate(days)}
    for record in panel.to_dict("records"):
        if not record.get("comparable"): continue
        day=record["date"]; symbol=record["ticker"]; i=day_pos[day]
        for arm in record["arms"]:
            entry_minute=int(cfg["early_entry_minute"] if arm in early else cfg["late_entry_minute"])
            entry_epoch=_true_epoch(day,entry_minute,d0)
            for horizon in cfg["horizons"]:
                expected=_expected_path(days,i,entry_minute,horizon,calendar,d0)
                if expected is None:
                    outcome={"status":"censored","raw_return":None,"benchmark_return":None,"beta_residual":None,"mfe":None,"mae":None,"touch":None,"execution_proven":False}
                else:
                    outcome=tr.fixed_outcome(frames[symbol].loc[:,["o","h","l","c","v"]], frames[cfg["benchmark"]].loc[:,["o","h","l","c","v"]], entry_epoch, expected[-1]+300, record.get("beta"), record.get("atr20"), expected)
                for cost in cfg["round_trip_cost_bps"]:
                    raw=outcome.get("raw_return"); residual=outcome.get("beta_residual")
                    rows.append({"date":day,"ticker":symbol,"arm":arm,"entry_minute":entry_minute,"horizon":horizon,"cost_bps":int(cost),"partition":"development" if day<=cfg["development_end"] else "assessment","status":outcome["status"],"raw_return":raw,"net_return":None if raw is None else raw-int(cost)/10000.0,"beta_residual":residual,"net_beta_residual":None if residual is None else residual-int(cost)/10000.0,"mfe":outcome.get("mfe"),"mae":outcome.get("mae"),"touch":outcome.get("touch") if horizon=="60m" else None})
    return pd.DataFrame(rows)


def _aggregates(outcomes: pd.DataFrame, cfg: Mapping[str,Any]) -> list[dict[str,Any]]:
    result=[]
    for cell in grid_cells(cfg):
        g=outcomes.loc[(outcomes["arm"]==cell["selector"])&(outcomes["horizon"]==cell["horizon"])&(outcomes["cost_bps"]==cell["round_trip_cost_bps"])] if not outcomes.empty else outcomes
        available=g.loc[g["status"]=="available"] if not g.empty else g
        residual=available.loc[available["net_beta_residual"].notna()] if not available.empty else available
        result.append({**cell,"fires":int(len(g)),"available":int(len(available)),"residual_available":int(len(residual)),"censored":int((g["status"]!="available").sum()) if not g.empty else 0,"distinct_dates":int(g["date"].nunique()) if not g.empty else 0,"tickers":sorted(g["ticker"].unique().tolist()) if not g.empty else [],"mean_net_return":float(available["net_return"].mean()) if not available.empty else None,"mean_net_beta_residual":float(residual["net_beta_residual"].mean()) if not residual.empty else None,"mean_mfe":float(available["mfe"].mean()) if not available.empty else None,"mean_mae":float(available["mae"].mean()) if not available.empty else None})
    return result


def _primary(outcomes: pd.DataFrame, cfg: Mapping[str,Any]) -> list[dict[str,Any]]:
    primary=outcomes.loc[(outcomes["horizon"]==cfg["primary_horizon"])&(outcomes["cost_bps"]==cfg["primary_cost_bps"])]
    early={"ALL_EARLY","GAP_UP","PERSISTENT","WEAKNESS_PERSISTENT","WEAKNESS_RECLAIM"}; rows=[]
    for arm in cfg["selectors"]:
        baseline="ALL_EARLY" if arm in early else "ALL_LATE"
        deltas=date_matched_deltas(primary,arm,baseline); interval=week_block_interval(deltas,repetitions=int(cfg["bootstrap_repetitions"]),seed=int(cfg["seed"]))
        selected=primary.loc[(primary["arm"]==arm)&primary["net_beta_residual"].notna()]
        per_stock={str(k):float(v) for k,v in selected.groupby("ticker")["net_beta_residual"].mean().items()}
        partition={str(k):float(v) for k,v in selected.groupby("partition")["net_beta_residual"].mean().items()}
        rows.append({"arm":arm,"baseline":baseline,"selected_rows":int(len(selected)),"selected_dates":int(selected["date"].nunique()),"ticker_coverage":sorted(selected["ticker"].unique().tolist()),"selected_mean_net_beta_residual":float(selected["net_beta_residual"].mean()) if not selected.empty else None,"date_matched_delta":interval,"per_stock_mean":per_stock,"partition_mean":partition})
    for arm in ("PERSISTENT","WEAKNESS_PERSISTENT"):
        deltas=date_matched_deltas(primary,arm,"GAP_UP")
        rows.append({"arm":arm,"baseline":"GAP_UP","comparison":"direct_gap_control","date_matched_delta":week_block_interval(deltas,repetitions=int(cfg["bootstrap_repetitions"]),seed=int(cfg["seed"]))})
    return rows


def _markdown(report: Mapping[str,Any]) -> str:
    lines=["# Terminal Tactical R1-A result","","**Retrospective corrected-history research only. Not a live signal, fill proof, or promotion.**","",f"Study: `{report['study_id']}`; generated from frozen prereg/config and {report['registered_grid']['study_cells']} registered cells.",f"Candidate rows: **{report['counts']['candidate_rows']}**; comparable rows: **{report['counts']['comparable_rows']}**; outcome rows: **{report['counts']['outcome_rows']}**.","","## Primary 60-minute / 25 bp comparisons","","| Arm | Rows | Dates | Mean net beta residual | Same-date delta | 95% week-block interval |","|---|---:|---:|---:|---:|---:|"]
    for row in report["primary_comparisons"]:
        if row.get("comparison"): continue
        interval=row["date_matched_delta"]
        fmt=lambda x: "n/a" if x is None else f"{100*x:.3f}%"
        lines.append(f"| {row['arm']} | {row['selected_rows']} | {row['selected_dates']} | {fmt(row['selected_mean_net_beta_residual'])} | {fmt(interval['mean'])} | {fmt(interval['low'])} .. {fmt(interval['high'])} |")
    lines += ["","## Boundaries","","- Corrected archive only: historical knowledge-time and fills are not proven.","- Week-block intervals are descriptive uncertainty, not promotion-grade p-values.","- Empty/negative/censored cells remain in the machine report; no threshold was tuned after outcomes.","- Options, news, regime and sector witnesses were not added retrospectively.",""]
    return "\n".join(lines)


def run_study(input_dir: Path, manifest: Path, terminal_root: Path, output_dir: Path) -> dict[str,Any]:
    cfg=_load_config(); registration=verify_registered_grid(LEDGER_PATH,cfg); d0=_load_terminal_module(terminal_root)
    terminal_head=_git_head(terminal_root)
    if terminal_head != cfg["terminal_dependency_sha"]:
        raise ValueError(f"terminal_dependency_head_mismatch:{terminal_head}")
    calendar=d0.CalendarProjection.load(terminal_root/"terminal/lib/usEquitySessionProjection.json")
    manifest_rows=_manifest_map(manifest); needed=list(cfg["symbols"])+[cfg["benchmark"]]; frames={}; input_receipts={}
    for symbol in needed:
        meta=manifest_rows.get((symbol,"5m"));
        if not meta or meta.get("status") not in {"captured","previously_captured"} or not meta.get("sha256"):
            raise ValueError(f"manifest_5m_missing:{symbol}")
        path=input_dir/f"{symbol}.5m.json"
        qualification=d0.qualify_store(path,symbol,"5m",calendar,cfg["start"],cfg["end"],None,"corrected_history")
        qerrors=qualification.get("errors") or {}
        hard_errors=set(qerrors)-{"invalid_bar"}
        if qualification.get("status") in {"missing","unreadable","malformed","empty"} or hard_errors:
            raise ValueError(f"input_qualification_failed:{symbol}:{qerrors}")
        frames[symbol]=_load_symbol(path,symbol,meta["sha256"],d0)
        input_receipts[symbol]={"sha256":meta["sha256"],"rows":int(len(frames[symbol])),
                                "whole_file_diagnostics":qerrors}
    days=_scheduled_days(calendar,cfg["start"],cfg["end"]); daily=_daily_tables(frames,days,calendar)
    panel,reasons=_feature_panel(frames,daily,days,calendar,d0,cfg); outcomes=_outcome_rows(panel,frames,days,calendar,d0,cfg)
    aggregates=_aggregates(outcomes,cfg); primary=_primary(outcomes,cfg)
    report={"schema":"mastermind.terminal_tactical_r1_result.v1","study_id":cfg["study_id"],"research_admission":cfg["research_admission"],"may_rank":False,"may_alert":False,"may_size":False,"prereg_sha256":_sha(PREREG_PATH),"config_sha256":_sha(CONFIG_PATH),"terminal_dependency":{"head":terminal_head,"qualification_module_sha256":_sha(terminal_root/"ingest/intraday_qualification.py"),"calendar_sha256":calendar.sha256},"manifest_sha256":_sha(manifest),"input_receipts":input_receipts,"registered_grid":registration,"window":{"start":cfg["start"],"development_end":cfg["development_end"],"assessment_start":cfg["assessment_start"],"end":cfg["end"]},"counts":{"scheduled_dates":len(days),"candidate_rows":int(len(panel)),"comparable_rows":int(panel["comparable"].sum()) if not panel.empty else 0,"outcome_rows":int(len(outcomes)),"ineligibility":dict(sorted(reasons.items()))},"cells":aggregates,"primary_comparisons":primary}
    if output_dir.exists(): raise ValueError("output_directory_exists")
    output_dir.mkdir(parents=True)
    (output_dir/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    (output_dir/"report.md").write_text(_markdown(report))
    panel_private=panel.copy(); panel_private["arms"]=panel_private["arms"].apply(list)
    panel_private.to_json(output_dir/"feature_panel.jsonl",orient="records",lines=True)
    outcomes.to_json(output_dir/"outcomes.jsonl",orient="records",lines=True)
    return report


def main(argv: Sequence[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--register-only",action="store_true"); parser.add_argument("--input-dir",type=Path); parser.add_argument("--manifest",type=Path); parser.add_argument("--terminal-root",type=Path); parser.add_argument("--output-dir",type=Path)
    args=parser.parse_args(argv)
    try:
        cfg=_load_config(); registration=verify_registered_grid(LEDGER_PATH,cfg)
        if args.register_only:
            print(json.dumps({"study_id":cfg["study_id"],"registered_grid":registration},sort_keys=True)); return 0
        if None in (args.input_dir,args.manifest,args.terminal_root,args.output_dir): raise ValueError("full_run_requires_input_manifest_terminal_output")
        report=run_study(args.input_dir.resolve(),args.manifest.resolve(),args.terminal_root.resolve(),args.output_dir.resolve())
        print(json.dumps({"study_id":report["study_id"],"output_dir":str(args.output_dir.resolve()),"counts":report["counts"]},sort_keys=True)); return 0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 2


if __name__=="__main__":
    raise SystemExit(main())
