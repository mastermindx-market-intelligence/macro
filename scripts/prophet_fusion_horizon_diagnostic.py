"""Post-hoc, pre-2020 attribution of the already-executed mechanism pilot.

This is not another strategy trial, grey-dot study, clean holdout or exit optimizer.
It consumes the frozen pilot's previously graded rows, verifies their digest and
filters BOTH decision dates and outcome-end dates before decoding any returns.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts.prophet_fusion_cohort_diagnostics import DiagnosticRefusal, same_entry_horizon_attribution
from scripts.prophet_fusion_mechanism_study import safe_cache, write_json

FROZEN_EVENTS_SHA256 = "1c7b9cb4027641fc88bbc88338543619257b46d0dced9964364e8535381b5ddd"
CUTOFF = "2019-12-31"
COLUMNS = ["ticker", "date", "trigger", "horizon", "fill_date", "exit_date", "status",
           "gross_return", "benchmark_return", "net_return", "net_excess", "forward_mdd_close", "forward_mfe_close"]


def read_frozen_development_rows(path: Path, expected_sha256: str) -> tuple[pd.DataFrame, dict]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise DiagnosticRefusal("FROZEN_EVENT_DIGEST_REQUIRED")
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise DiagnosticRefusal("FROZEN_EVENT_DIGEST_MISMATCH")
    frame = pq.read_table(io.BytesIO(raw), columns=COLUMNS,
        filters=[("date", "<=", pd.Timestamp(CUTOFF)), ("exit_date", "<=", CUTOFF)],
        use_threads=False, pre_buffer=False).to_pandas()
    if (frame.empty or not frame["horizon"].isin([21,63]).all()
            or frame[COLUMNS[:4]].isna().any().any()):
        raise DiagnosticRefusal("EMPTY_OR_MALFORMED_FROZEN_EVENT_FRAME")
    dates, exits = pd.to_datetime(frame["date"]), pd.to_datetime(frame["exit_date"], errors="raise")
    if ((dates > pd.Timestamp(CUTOFF)).any() or (exits > pd.Timestamp(CUTOFF)).any()
            or (exits <= dates).any()):
        raise DiagnosticRefusal("POST_CUTOFF_OR_INCONSISTENT_OUTCOME_DATE")
    # This is a local row-join key, not a newly minted native EntryEvent or signal.
    frame["event_id"] = [json.dumps(["frozen_pilot_row", str(t), str(k), str(pd.Timestamp(day).date())],separators=(",",":"))
                         for t,k,day in zip(frame.ticker, frame.trigger, frame.date)]
    frame["price_basis"] = "frozen_pilot_reconstructed_vendor_basis_unverified"
    return frame, {"event_rows_sha256": expected_sha256, "decoded_columns": COLUMNS,
        "decoded_rows": len(frame), "decision_range": [str(dates.min().date()),str(dates.max().date())],
        "latest_decoded_outcome_end": str(exits.max().date()),
        "cutoff_on_decisions_and_outcome_end": CUTOFF,
        "no_post2019_outcomes_decoded": True}


def _date_mean(frame: pd.DataFrame, column: str) -> float | None:
    return float(frame.groupby("date")[column].mean().mean()) if len(frame) else None


def summarize(frame: pd.DataFrame, receipt: dict) -> dict:
    short, long = frame.loc[frame.horizon.eq(21)], frame.loc[frame.horizon.eq(63)]
    attribution = same_entry_horizon_attribution(short, long)
    paired = attribution.loc[attribution.status.eq("PAIRED_GROSS_SEGMENTS")]
    meta = short[["event_id","date","ticker","trigger","net_return","net_excess","forward_mdd_close","forward_mfe_close"]].rename(
        columns={"net_return":"net21","net_excess":"excess21","forward_mdd_close":"adverse_close21","forward_mfe_close":"favorable_close21"})
    terminal = long[["event_id","net_return","net_excess","forward_mdd_close","forward_mfe_close"]].rename(
        columns={"net_return":"net63","net_excess":"excess63","forward_mdd_close":"adverse_close63","forward_mfe_close":"favorable_close63"})
    data = paired.merge(meta,on="event_id",validate="one_to_one").merge(terminal,on="event_id",validate="one_to_one")
    numeric=["net21","net63","excess21","excess63","adverse_close21","adverse_close63","favorable_close21","favorable_close63"]
    if not np.isfinite(data[numeric].to_numpy(dtype=float)).all():
        raise DiagnosticRefusal("FROZEN_NET_OUTCOME_UNAVAILABLE")
    if (data.adverse_close63.gt(data.adverse_close21+1e-12).any()
            or data.favorable_close63.lt(data.favorable_close21-1e-12).any()
            or data[["adverse_close21","adverse_close63"]].gt(0).any().any()
            or data[["adverse_close21","adverse_close63"]].lt(-1).any().any()
            or data[["favorable_close21","favorable_close63"]].lt(0).any().any()):
        raise DiagnosticRefusal("SAME_ENTRY_PATH_EXTREMA_MUST_NEST")
    data["positive21"] = data.net21.gt(0).astype(float)
    data["positive63"] = data.net63.gt(0).astype(float)
    data["negative21_positive63"] = (data.net21.le(0) & data.net63.gt(0)).astype(float)
    data["positive21_negative63"] = (data.net21.gt(0) & data.net63.le(0)).astype(float)
    data["late_gain_without_market_outperformance"] = (data.continuation_return.gt(0) & data.continuation_excess.le(0)).astype(float)
    summaries=[]
    for trigger, group in data.groupby("trigger",sort=True):
        result={"trigger":str(trigger),"same_entry_pairs":len(group),
                "decision_dates":int(group.date.nunique()),"names":int(group.ticker.nunique())}
        for field in numeric+["positive21","positive63","negative21_positive63","positive21_negative63",
                             "continuation_return","benchmark_continuation_return","continuation_excess",
                             "late_gain_without_market_outperformance"]:
            result[field]=_date_mean(group,field)
        result["rate_change_identity_error"]=(result["positive63"]-result["positive21"])-(
            result["negative21_positive63"]-result["positive21_negative63"])
        if abs(result["rate_change_identity_error"])>1e-12:
            raise DiagnosticRefusal("POSITIVE_RATE_TRANSITION_ACCOUNTING_FAILED")
        summaries.append(result)
    return {"schema":"prophet.frozen_pilot_horizon_diagnostic/v1",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "status":"POST_HOC_DESCRIPTIVE_PRE2020_ONLY","input_receipt":receipt,
        "population":"ORIGINAL_ELEVEN_NAME_SURVIVOR_PANEL_NOT_GREY_DOT_OR_LIVE_BOARD",
        "weighting":"equal decision date within each identical-entry paired sample",
        "net_outcomes":"original frozen 25-bps round-trip outcome, no costs recomputed",
        "segments":"gross 21-to-63 return = (1+gross63)/(1+gross21)-1",
        "pair_status_counts":{str(k):int(v) for k,v in attribution.status.value_counts().items()},
        "summaries":summaries,"primary_protocol_unchanged":True,"promotion_eligible":False,
        "statistical_inference":None,"new_prices_or_strategy_outcomes_generated":False,
        "limitations":["Already-seen development outcomes; not a held-out or causal result.",
          "Fixed surviving names and unaudited price-adjustment vintage remain disqualifiers for promotion.",
          "No sector return series or economic catalyst information was joined, so cohort versus stock attribution is unresolved.",
          "An improved terminal positive-return rate is not improved no-undercut survival or a better executable exit policy.",
          "Adverse/favorable excursions are close-to-entry path measures, not intraday losses, portfolio drawdown or modeled stop fills.",
          "Short-horizon-only entries near the cutoff are counted as unmatched, never compared against a different long-horizon population."]}


def render(report: dict) -> str:
    def pct(x):return "unavailable" if x is None else f"{x*100:+.3f}%"
    lines=["# Frozen-pilot horizon attribution (pre-2020 only)","",
        "**Post-hoc description of previously seen survivor-panel entries. Not grey-dot performance or a new winning strategy.**","",
        "Only outcomes ending on or before December 31, 2019 were decoded. The same entries are compared at both horizons.",
        "Net figures reuse the original 25-basis-point round-trip outcomes. The intervening 42-session segment is gross; no second trade or cost is inserted.","",
        "| Mechanism | Same entries | Positive net at 21 | Positive net at 63 | 21-to-63 gross return | Same-window SPY | Segment excess |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for r in report["summaries"]:
        lines.append(f"| {r['trigger']} | {r['same_entry_pairs']} | {pct(r['positive21'])} | {pct(r['positive63'])} | {pct(r['continuation_return'])} | {pct(r['benchmark_continuation_return'])} | {pct(r['continuation_excess'])} |")
    lines += ["","## What this can and cannot explain","",
        "The rate change is exactly the share moving from nonpositive at 21 to positive at 63, minus the reverse, with identical date weights. See JSON for both transition shares and the accounting residual.",
        "Comparing the later segment with SPY separates a broad-market continuation from simple absolute recovery. It does not identify sector leadership or causal entry skill. Those need the existing dated cohort source and a registered incremental test.",
        "Unmatched and incomplete rows remain explicit: `"+json.dumps(report["pair_status_counts"],sort_keys=True)+"`.","",
        "No result here changes the original primary horizon, significance finding, source population or live authority."]
    return "\n".join(lines)+"\n"


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        frame,receipt=read_frozen_development_rows(args.events,FROZEN_EVENTS_SHA256)
        report=summarize(frame,receipt)
        report["consumer_code_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        out=safe_cache(args.out)
        write_json(out/"pre2020_horizon_diagnostic.json",report)
        (out/"pre2020_horizon_diagnostic.md").write_text(render(report))
        print(json.dumps({"status":report["status"],"pairs":report["pair_status_counts"],"promotion_eligible":False}))
        return 0
    except DiagnosticRefusal as exc:
        print(f"REFUSED: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
