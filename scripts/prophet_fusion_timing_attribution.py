"""Auxiliary timing attribution, not another primary test or strategy optimizer.

Compare each registered event with the same asset/calendar month's common-qualified
hypothetical decision dates. Future month observations are outcome controls only,
never predictor inputs. This diagnostic cannot rescue a failed primary contrast.
The native grader, registered horizons/costs and original event set are unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from engine.grading import forward_metrics
from scripts import prophet_fusion_mechanisms as core
from scripts.prophet_fusion_arena import _safe_out_dir
from scripts.prophet_fusion_mechanism_study import (
    DEFAULT_SPEC, _load_input, _verified_observations, select_arm, write_json,
)


def control_pool(close: pd.Series, benchmark: pd.Series, observations: pd.DataFrame,
                 spec: dict, ticker: str) -> pd.DataFrame:
    """Grade all common-qualified dates; never choose control days from their outcome."""
    close = core.align_calendar(close, benchmark)
    known = observations["signal"].reindex(close.index).notna()
    known_prior = known.shift(1, fill_value=False).rolling(3, min_periods=3).sum().eq(3)
    market_known = core.market_context(benchmark)["market_context_known"].reindex(close.index, fill_value=False)
    date_ok = (close.index >= pd.Timestamp(spec["start"])) & (close.index <= pd.Timestamp(spec["end"]))
    dates = close.index[known & known_prior & market_known & date_ok]
    rows = []
    cost = spec["primary_round_trip_cost_bps"]
    for date in dates:
        stock = forward_metrics(close, date, horizons=(21, 63))
        market = forward_metrics(benchmark, date, horizons=(21, 63))
        if stock["fill_date"] != market["fill_date"]:
            raise core.MechanismRefusal("ATTRIBUTION_FILL_CALENDAR_MISMATCH")
        for horizon in (21, 63):
            gross, reference = stock[f"fwd_ret_{horizon}"], market[f"fwd_ret_{horizon}"]
            if gross is None or reference is None:
                continue
            net = float(core.net_return(gross, cost))
            rows.append({"ticker": ticker, "date": date, "month": str(date.to_period("M")),
                         "horizon": horizon, "control_net_return": net,
                         "control_net_excess": net - float(reference)})
    if not rows:
        raise core.MechanismRefusal(f"NO_COMMON_QUALIFIED_CONTROLS:{ticker}")
    return pd.DataFrame(rows)


def attach_controls(events: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    if pool.duplicated(["ticker", "date", "horizon"]).any():
        raise core.MechanismRefusal("DUPLICATE_ATTRIBUTION_CONTROL")
    keys = ["ticker", "month", "horizon"]
    means = pool.groupby(keys, as_index=False).agg(
        control_net_excess=("control_net_excess", "mean"),
        control_net_return=("control_net_return", "mean"),
        control_dates=("date", "nunique"))
    frame = events.copy()
    frame["month"] = pd.to_datetime(frame["date"]).dt.to_period("M").astype(str)
    frame = frame.merge(means, on=keys, how="left", validate="many_to_one")
    if frame["control_dates"].isna().any():
        raise core.MechanismRefusal("EVENT_WITHOUT_SAME_ASSET_MONTH_CONTROL")
    frame["timing_residual_net_excess"] = frame["net_excess"] - frame["control_net_excess"]
    frame["timing_residual_net_return"] = frame["net_return"] - frame["control_net_return"]
    return frame


def summarize(frame: pd.DataFrame, spec: dict) -> list[dict]:
    result = []
    for horizon in (21, 63):
        for trigger in spec["triggers"]:
            for context in spec["contexts"]:
                arm = f"{trigger}__{context}"
                selected = select_arm(frame, arm, horizon)
                def mean(column: str):
                    return (float(selected.groupby("date")[column].mean().mean()) if len(selected) else None)
                result.append({
                    "arm": arm, "horizon": horizon, "events": len(selected),
                    "decision_dates": int(selected["date"].nunique()),
                    "asset_months": int(selected[["ticker", "month"]].drop_duplicates().shape[0]),
                    "event_net_excess": mean("net_excess"),
                    "same_asset_month_control_net_excess": mean("control_net_excess"),
                    "timing_residual_net_excess": mean("timing_residual_net_excess"),
                    "event_net_return": mean("net_return"),
                    "same_asset_month_control_net_return": mean("control_net_return"),
                    "timing_residual_net_return": mean("timing_residual_net_return"),
                    "minimum_control_dates_per_event_month": int(selected["control_dates"].min()) if len(selected) else None,
                    "median_control_dates_per_event_month": float(selected["control_dates"].median()) if len(selected) else None,
                    "promotion_eligible": False,
                })
    return result


def render(report: dict) -> str:
    def fmt(value):
        return "unknown" if value is None else f"{100 * value:.2f}%"
    lines = ["# Timing versus asset/period selection", "",
             "**Auxiliary descriptive attribution; not a new primary test or promotion.**", "",
             "An attractive event return may reflect owning a good asset in a good period. This control "
             "subtracts the same asset/calendar month's mean hypothetical net return (or excess versus SPY) "
             "over all common-qualified decision dates, using the same next-close fill, horizon and cost.", "",
             "Controls may include dates after the event and the event itself: they are retrospective outcome "
             "comparators, never a historical decision input or independent sample. No p-values, forecast, "
             "new threshold, primary-protocol substitution or live change follows from this table.", "",
             "| Arm | Horizon | Events | Event excess | Asset/month control excess | Timing residual | Min control dates |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["summaries"]:
        lines.append(f"| {row['arm']} | {row['horizon']} | {row['events']} | "
                     f"{fmt(row['event_net_excess'])} | {fmt(row['same_asset_month_control_net_excess'])} | "
                     f"{fmt(row['timing_residual_net_excess'])} | {row['minimum_control_dates_per_event_month']} |")
    lines += ["", "The original primary report and its eleven contrasts are unchanged. This is not a complete "
              "risk/exposure-matched portfolio test and does not repair survivor, vintage, price-basis or live-board "
              "parity limitations. Thin control months are disclosed rather than silently dropped.", ""]
    return "\n".join(lines)


def run(directory: Path, spec_path: Path) -> dict:
    directory = _safe_out_dir(directory)
    spec = core.load_spec(spec_path)
    report_path = directory / "report.json"
    original_digest = core.digest_bytes(report_path.read_bytes())
    report = json.loads(report_path.read_text())
    verification = json.loads((directory / "verification.json").read_text())
    if (verification.get("status") != "PASS_WITH_DECLARED_SCOPE"
            or verification["report_sha256"] != original_digest
            or verification["spec_sha256"] != spec["_sha256"]
            or verification["event_rows_sha256"] != core.digest_bytes((directory / "graded_research_events.parquet").read_bytes())):
        raise core.MechanismRefusal("ATTRIBUTION_REQUIRES_BOUND_VERIFIED_PRIMARY_REPORT")
    manifest = report["input_manifest"]
    benchmark = _load_input(directory, manifest, "SPY_BENCHMARK")
    controls = []
    for ticker in spec["universe"]:
        observations = _verified_observations(ticker, spec, directory)
        close = _load_input(directory, manifest, ticker)
        controls.append(control_pool(close, benchmark, observations, spec, ticker))
    pool = pd.concat(controls, ignore_index=True)
    events = pd.read_parquet(directory / "graded_research_events.parquet")
    frame = attach_controls(events, pool)
    artifact = {
        "schema": "prophet.entry_timing_attribution/v1", "status": "AUXILIARY_DESCRIPTIVE_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(), "source_base": spec["source_base"],
        "spec_sha256": spec["_sha256"], "primary_report_sha256": original_digest,
        "code_sha256": core.digest_bytes(Path(__file__).read_bytes()),
        "protocol": "ENTRY_REGIME_RESEARCH_PROGRAM_2026-11-14.md#independent-readback-and-attribution-frontier",
        "primary_protocol_unchanged": True, "promotion_eligible": False, "statistical_inference": None,
        "control_rows": len(pool), "control_dates": int(pool["date"].nunique()),
        "control_asset_months": int(pool[["ticker", "month"]].drop_duplicates().shape[0]),
        "summaries": summarize(frame, spec),
        "limitations": ["Controls are retrospective outcomes, not available features.",
                        "Event days are included in their monthly control mean; no independence claim.",
                        "No full portfolio risk or capital-allocation attribution.",
                        "All original population, vintage and execution limitations remain."],
    }
    write_json(directory / "timing_attribution.json", artifact)
    (directory / "timing_attribution.md").write_text(render(artifact))
    if core.digest_bytes(report_path.read_bytes()) != original_digest:
        raise core.MechanismRefusal("PRIMARY_REPORT_CHANGED_DURING_ATTRIBUTION")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    args = parser.parse_args(argv)
    report = run(args.input, args.spec)
    print(json.dumps({"status": report["status"], "control_rows": report["control_rows"],
                      "arms": len(report["summaries"]), "primary_protocol_unchanged": True,
                      "promotion_eligible": False}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
