"""Independent arithmetic/provenance readback for the existing mechanism pilot.

This does not call the study's grader, return formula, summary builder or bootstrap.
It is a principal self-check, not a distinct reviewer or independent market dataset.
No strategy promotion, new trial, live-data write or automatic repair is performed.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

# Direct file-path execution must resolve this repository, not the caller cwd.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from scripts.prophet_fusion_mechanisms import MechanismRefusal

ROOT = Path(__file__).resolve().parents[1]
NATIVE_PATHS = ("engine", "lib", "scripts/prophet_fusion_arena.py", "research/prophet_fusion/families.yml")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, code: str) -> None:
    if not condition:
        raise MechanismRefusal(code)


def number_equal(actual: Any, expected: Any, label: str, *, tolerance: float = 1e-11) -> None:
    if expected is None or pd.isna(expected):
        require(actual is None or pd.isna(actual), f"{label}:EXPECTED_UNKNOWN")
        return
    require(actual is not None and np.isfinite(actual), f"{label}:NONFINITE")
    require(bool(np.isclose(float(actual), float(expected), atol=tolerance, rtol=tolerance)),
            f"{label}:ARITHMETIC_MISMATCH")


def assert_native_source(source: str) -> dict:
    """The spec's native engine/base cannot silently become today's different engine."""
    import re
    require(bool(re.fullmatch(r"[0-9a-f]{40}", source)), "NATIVE_SOURCE_PIN_REQUIRED")
    changed = subprocess.run(["git", "diff", "--name-only", source, "--", *NATIVE_PATHS],
                             cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", *NATIVE_PATHS],
                               cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    require(not changed.stdout.strip(), "NATIVE_SOURCE_DRIFT")
    require(not untracked.stdout.strip(), "UNTRACKED_NATIVE_SOURCE")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, timeout=10, check=True).stdout.strip()
    return {"source_base": source, "checked_worktree_head": head,
            "native_paths_checked": list(NATIVE_PATHS), "native_source_matches_spec": True}


def verify_rows(events: pd.DataFrame, prices: dict[str, pd.Series], benchmark: pd.Series, spec: dict) -> dict:
    """Recompute every realized price ratio directly from the captured prices."""
    require(not events.empty, "EMPTY_GRADED_EVENTS")
    require(not events.duplicated(["ticker", "date", "trigger", "horizon"]).any(), "DUPLICATE_EVENTS")
    require(set(events["ticker"]) <= set(spec["universe"]), "EVENT_UNIVERSE_MISMATCH")
    require(set(events["trigger"]) <= set(spec["triggers"]), "UNREGISTERED_EVENT_TRIGGER")
    require(set(events["horizon"]) == {21, 63}, "EVENT_HORIZONS_MISMATCH")
    require(events["date"].between(pd.Timestamp(spec["start"]), pd.Timestamp(spec["end"])).all(),
            "EVENT_OUTSIDE_REGISTERED_WINDOW")
    # Independent contemporaneous context computation; no original study helper is used.
    ma200 = benchmark.rolling(200, min_periods=200).mean()
    ret = benchmark / benchmark.shift(1) - 1
    up = (benchmark > ma200) & (ma200 > ma200.shift(20))
    calm = ret.rolling(21, min_periods=21).std() <= 1.5 * ret.rolling(252, min_periods=252).std()
    max_error = 0.0
    for row in events.to_dict("records"):
        symbol, date, horizon = row["ticker"], pd.Timestamp(row["date"]), int(row["horizon"])
        close = prices[symbol]
        require(date in close.index and date in benchmark.index, "UNOBSERVED_EVENT_DATE")
        i, j = int(close.index.get_loc(date)), int(benchmark.index.get_loc(date))
        require(i + horizon + 1 < len(close) and j + horizon + 1 < len(benchmark), "IMMATURE_EVENT")
        require(close.index[i:i + horizon + 2].equals(benchmark.index[j:j + horizon + 2]),
                "EVENT_CALENDAR_MISMATCH")
        gross = float(close.iloc[i + horizon + 1] / close.iloc[i + 1] - 1)
        market = float(benchmark.iloc[j + horizon + 1] / benchmark.iloc[j + 1] - 1)
        window = close.iloc[i + 2:i + horizon + 2] / close.iloc[i + 1] - 1
        require(row["fill_date"] == str(close.index[i + 1].date()), "FILL_DATE_MISMATCH")
        require(row["exit_date"] == str(close.index[i + horizon + 1].date()), "EXIT_DATE_MISMATCH")
        number_equal(row["gross_return"], gross, "GROSS_RETURN")
        number_equal(row["benchmark_return"], market, "BENCHMARK_RETURN")
        number_equal(row["forward_mdd_close"], min(0.0, float(window.min())), "ADVERSE_EXCURSION")
        number_equal(row["forward_mfe_close"], max(0.0, float(window.max())), "FAVORABLE_EXCURSION")
        require(isinstance(row["market_uptrend"], (bool, np.bool_))
                and isinstance(row["no_volatility_stress"], (bool, np.bool_)), "CONTEXT_NOT_BOOLEAN")
        require(bool(row["market_uptrend"]) == bool(up.loc[date]), "MARKET_TREND_MISMATCH")
        require(bool(row["no_volatility_stress"]) == bool(calm.loc[date]), "VOLATILITY_CONTEXT_MISMATCH")
        for cost in spec["cost_sensitivity_bps"]:
            half = cost / 20000
            # Explicit acquisition cost and liquidation proceeds, independent of original helper.
            paid = float(close.iloc[i + 1]) * (1 + half)
            received = float(close.iloc[i + horizon + 1]) * (1 - half)
            net = received / paid - 1
            number_equal(row[f"net_{cost}bps"], net, f"COST_{cost}")
            if cost == spec["primary_round_trip_cost_bps"]:
                number_equal(row["net_return"], net, "PRIMARY_NET_RETURN")
                number_equal(row["net_excess"], net - market, "NET_EXCESS")
                number_equal(row["net_positive"], float(net > 0), "POSITIVE_NET_LABEL")
                max_error = max(max_error, abs(row["net_return"] - net))
    return {"events_verified": len(events), "all_price_fill_cost_and_context_checks": True,
            "maximum_net_return_absolute_error": max_error}


def verify_summaries(events: pd.DataFrame, report: dict, spec: dict) -> dict:
    summaries = report["arm_summaries"]
    expected_arms = {f"{trigger}__{context}" for trigger in spec["triggers"] for context in spec["contexts"]}
    keys = {(x["arm"], x["horizon"]) for x in summaries}
    require(len(summaries) == 24 and keys == {(arm, h) for arm in expected_arms for h in (21, 63)},
            "REPORT_ARM_CENSUS_MISMATCH")
    indexed = {}
    for summary in summaries:
        trigger, context = summary["arm"].split("__")
        base = events.loc[events.trigger.eq(trigger) & events.horizon.eq(summary["horizon"])]
        selected = base if context == "unfiltered" else base.loc[base[context].eq(True)]
        require(summary["events"] == len(selected), "SUMMARY_EVENT_COUNT")
        require(summary["decision_dates"] == selected["date"].nunique(), "SUMMARY_DATE_COUNT")
        for column, output in (("net_return", "net_return"), ("net_excess", "net_excess"),
                               ("net_positive", "net_positive_rate_date_weighted")):
            # Group first; never weight a date more heavily because more names fire.
            groups = selected.groupby("date")[column]
            means = [float(group.sum() / len(group)) for _, group in groups]
            expected = sum(means) / len(means) if means else None
            number_equal(summary[output], expected, f"SUMMARY_{output}")
        number_equal(summary["signal_retention"], len(selected) / len(base) if len(base) else None,
                     "RETENTION")
        wins = float(base["net_positive"].sum())
        number_equal(summary["winner_retention"], float(selected["net_positive"].sum()) / wins if wins else None,
                     "WINNER_RETENTION")
        require(summary["promotion_eligible"] is False, "SUMMARY_AUTHORITY_ESCALATION")
        indexed[(summary["arm"], summary["horizon"])] = summary
    contrasts = report["primary_comparisons"]
    require(len(contrasts) == spec["integer_primary_comparison_count"], "CONTRAST_COUNT_MISMATCH")
    require({(c['left'], c['right']) for c in contrasts} == {tuple(c) for c in spec['primary_comparisons']},
            "CONTRAST_IDENTITY_MISMATCH")
    for contrast in contrasts:
        a = indexed[(contrast["left"], 21)]["net_excess"]
        b = indexed[(contrast["right"], 21)]["net_excess"]
        number_equal(contrast["delta"], a - b if a is not None and b is not None else None,
                     "CONTRAST_POINT_ESTIMATE")
        require(contrast["promotion_eligible"] is False, "CONTRAST_AUTHORITY_ESCALATION")
    return {"arm_summaries_verified": len(summaries), "contrast_point_estimates_verified": len(contrasts),
            "bootstrap_intervals_recomputed_here": False}


def verify(directory: Path, spec_path: Path) -> dict:
    directory = directory.resolve(strict=True)
    spec = json.loads(spec_path.read_text())
    report_path = directory / "report.json"
    report = json.loads(report_path.read_text())
    require(report["spec_sha256"] == sha256(spec_path), "REPORT_SPEC_DIGEST_MISMATCH")
    require(report["source_base"] == spec["source_base"], "REPORT_SOURCE_MISMATCH")
    require(report["promotion_eligible"] is False and report["survivorship_biased"] is True,
            "REPORT_AUTHORITY_OR_POPULATION_MISMATCH")
    require(report["adapter_sha256"] == sha256(ROOT / "scripts/prophet_fusion_mechanisms.py"),
            "ADAPTER_CHANGED_SINCE_REPORT")
    require(report["study_code_sha256"] == sha256(ROOT / "scripts/prophet_fusion_mechanism_study.py"),
            "STUDY_CHANGED_SINCE_REPORT")
    native = assert_native_source(spec["source_base"])
    prices = {}
    for item in report["input_manifest"]["inputs"]:
        path = (directory / item["cache_name"]).resolve(strict=True)
        require(path.is_relative_to(directory), "INPUT_CACHE_PATH_ESCAPE")
        require(sha256(path) == item["sha256"], "INPUT_DIGEST_MISMATCH")
        expected_path = (spec["benchmark_path"] if item["name"] == "SPY_BENCHMARK"
                         else spec["price_path_template"].format(ticker=item["name"]))
        require(item["source_path"] == expected_path, "UNREGISTERED_PRICE_SOURCE")
        blob = subprocess.run(["git", "rev-parse", f"{spec['source_base']}:{expected_path}"],
                              cwd=ROOT, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        raw = path.read_bytes()
        actual_blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        require(blob == item["git_blob_sha"] == actual_blob, "SOURCE_GIT_BLOB_MISMATCH")
        prices[item["name"]] = pd.read_parquet(path, columns=[item["column"]])[item["column"]]
    require(set(prices) == set(spec["universe"]) | {"SPY_BENCHMARK"}, "INPUT_UNIVERSE_MISMATCH")
    for symbol in spec["universe"]:
        receipt = json.loads((directory / "observations" / f"{symbol}.json").read_text())
        require(receipt["spec_sha256"] == report["spec_sha256"]
                and receipt["source_base"] == spec["source_base"]
                and receipt["adapter_sha256"] == report["adapter_sha256"],
                "OBSERVATION_IDENTITY_MISMATCH")
        require(receipt["data_sha256"] == sha256(directory / "observations" / f"{symbol}.parquet"),
                "OBSERVATION_DIGEST_MISMATCH")
    event_path = directory / "graded_research_events.parquet"
    events = pd.read_parquet(event_path)
    rows = verify_rows(events, prices, prices["SPY_BENCHMARK"], spec)
    summaries = verify_summaries(events, report, spec)
    return {"schema": "prophet.entry_regime_arithmetic_verification/v1",
            "verified_at": datetime.now(timezone.utc).isoformat(), "status": "PASS_WITH_DECLARED_SCOPE",
            "report_sha256": sha256(report_path), "event_rows_sha256": sha256(event_path),
            "spec_sha256": sha256(spec_path), "verifier_code_sha256": sha256(Path(__file__)),
            "native_source": native, "row_verification": rows, "summary_verification": summaries,
            "environment": {"python": platform.python_version(),
                            **{name: importlib.metadata.version(name) for name in ("numpy", "pandas", "pyarrow")}},
            "scope": "Independent arithmetic implementation and source readback by the assigned principal; not a distinct reviewer.",
            "does_not_prove": ["original historical availability", "unbiased universe", "execution feasibility",
                               "bootstrap asymptotic coverage", "future edge", "portfolio returns", "production promotion"],
            "promotion_eligible": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=ROOT / "research/prophet_fusion/entry_regime_v1_spec.json")
    args = parser.parse_args(argv)
    # Enforce the existing output boundary before any read or write.
    from scripts.prophet_fusion_arena import _safe_out_dir
    out = _safe_out_dir(args.input)
    receipt = verify(args.input, args.spec)
    target = out / "verification.json"
    temporary = target.with_suffix(".writing")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(target)
    print(json.dumps({"status": receipt["status"], **receipt["row_verification"],
                      **receipt["summary_verification"], "promotion_eligible": False}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
