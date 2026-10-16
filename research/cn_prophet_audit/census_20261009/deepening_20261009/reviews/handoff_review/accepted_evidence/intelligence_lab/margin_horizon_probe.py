"""Read-only frozen-source margin horizon census; never import/run the collector."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import subprocess
import sys

import pandas as pd

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def run(repo: Path) -> dict:
    receipts = []

    def read(path: str) -> bytes:
        data = subprocess.check_output(["git", "-C", str(repo), "show", f"{PIN}:{path}"])
        git_sha = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", f"{PIN}:{path}"], text=True
        ).strip()
        receipts.append({"path": path, "git_blob": git_sha, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
        return data

    source = read("collectors/china_margin_detail.py").decode()
    module = ast.parse(source)
    selected = [node for node in module.body if
                isinstance(node, ast.FunctionDef) and node.name == "_first_populated"]
    refresh = next(node for node in module.body if isinstance(node, ast.FunctionDef)
                   and node.name == "refresh")
    prior = next(node for node in ast.walk(refresh) if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "prior_slice" for t in node.targets))
    lookback = next(node.value.value for node in module.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "LOOKBACK_TD" for t in node.targets))
    namespace = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "pinned_first_populated", "exec"), namespace)
    slice_code = compile(ast.Expression(prior.value), "pinned_prior_slice", "eval")

    def scenario(name, length, current_index, available_indices, expected_index, initial_indices=None):
        days = [(date(2026, 1, 1) + timedelta(days=i)).strftime("%Y%m%d") for i in range(length)]
        available = {days[i]: {"000001.SZ": {"fin_balance": 1.0}} for i in available_indices}
        initial = available if initial_indices is None else {days[i]: {"000001.SZ": {"fin_balance": 1.0}} for i in initial_indices}
        namespace["_detail_for"] = lambda d: initial.get(d, {})
        current, _ = namespace["_first_populated"](days[-3:])
        assert current == days[current_index], (name, current, current_index)
        namespace["_detail_for"] = lambda d: available.get(d, {})
        window = eval(slice_code, {"dates": days, "ci": current_index, "LOOKBACK_TD": lookback})
        chosen, _ = namespace["_first_populated"](window)
        index = days.index(chosen) if chosen else None
        assert index == expected_index, (name, index, expected_index)
        # Proposed bounded slice preserves the incumbent 20..22 source-index window.
        # It returns no prior when the selected current has fewer than 20 preceding rows.
        target = current_index - lookback
        bounded_window = days[max(0, target-2):target+1] if target >= 0 else []
        repaired, _ = namespace["_first_populated"](bounded_window)
        repaired_index = days.index(repaired) if repaired else None
        if target < 0:
            assert repaired_index is None
        else:
            assert repaired_index == index
        return {"name": name, "history_length": length, "current_index": current_index,
                "native_current_lookup_verified": True,
                "availability_changes_between_current_and_prior_lookup": initial_indices is not None,
                "candidate_indices": [days.index(d) for d in window], "chosen_index": index,
                "source_index_gap": current_index - index if index is not None else None,
                "bounded_repair_chosen_index": repaired_index,
                "passed": True, "mode": "synthetic index positions, not an exchange calendar"}

    cases = [
        scenario("full_history_target_20", 40, 39, [17, 18, 19, 39], 19),
        scenario("full_history_fallback_21", 40, 39, [17, 18, 39], 18),
        scenario("full_history_fallback_22", 40, 39, [17, 39], 17),
        scenario("full_history_missing_prior", 40, 39, [39], None),
        scenario("short_history_21_current_oldest_recent_selects_itself", 21, 18, [18], 18),
        scenario("short_history_21_newly_available_future_can_be_selected", 21, 18, [18, 19], 19, initial_indices=[18]),
        scenario("short_history_21_current_middle_uses_19_gap", 21, 19, [0, 19], 0),
        scenario("short_history_21_current_latest_uses_20_gap", 21, 20, [0, 20], 0),
    ]

    detail = pd.read_parquet(io.BytesIO(read("data/china_margin_detail/detail.parquet")))
    index = pd.read_parquet(io.BytesIO(read("data/china/000001.SS.parquet")))
    calendar_dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in index.index]
    positions = {d: i for i, d in enumerate(calendar_dates)}
    observations = detail["date"].astype(str)
    previous = detail["prior_date"].where(detail["prior_date"].notna(), None)
    latest_date = observations.max()
    pairs = []
    weighted = Counter()
    unbound = 0
    for (current, prior_date), part in detail.groupby(["date", "prior_date"], dropna=False):
        current = str(current)
        prior_date = None if pd.isna(prior_date) else str(prior_date)
        gap = positions[current] - positions[prior_date] if current in positions and prior_date in positions else None
        if gap is None:
            unbound += len(part)
        else:
            weighted[str(gap)] += len(part)
        pairs.append({"date": current, "prior_date": prior_date, "rows": len(part),
                      "source_index_gap": gap,
                      "nonmissing_prior_balance": int(part["fin_balance_prior"].notna().sum())})
    latest = detail[observations == latest_date]
    return {
        "schema": "research.margin_horizon_trace.v1", "pin": PIN,
        "method": "git show immutable source/data; AST-execute only pure slice and lookup with synthetic inputs; no collector/network calls",
        "python": sys.version, "pandas": pd.__version__, "receipts": receipts,
        "source_contract": {"LOOKBACK_TD": lookback, "prior_slice": ast.get_source_segment(source, prior),
                            "lookup_order": "newest populated whole-source date first; not per-issuer fallback"},
        "synthetic_cases": cases,
        "data": {"rows": len(detail), "tickers": int(detail["ticker"].nunique()),
                 "observation_dates": int(observations.nunique()), "latest_date": latest_date,
                 "missing_prior_date_rows": int(previous.isna().sum()),
                 "missing_prior_balance_rows": int(detail["fin_balance_prior"].isna().sum()),
                 "latest_rows": len(latest), "latest_missing_prior_date": int(latest["prior_date"].isna().sum()),
                 "latest_missing_prior_balance": int(latest["fin_balance_prior"].isna().sum()),
                 "index_rows": len(index), "index_start": min(calendar_dates), "index_end": max(calendar_dates),
                 "index_duplicate_dates": len(calendar_dates)-len(positions),
                 "known_source_index_gap_weighted_rows": dict(sorted(weighted.items())),
                 "rows_without_both_dates_in_index": unbound, "date_pairs": pairs},
        "limits": ["Stored pairs and current index coverage do not prove historical exchange-calendar completeness, source publication or first-seen time.",
                   "Actual data receipts describe the frozen snapshot. Synthetic underfilled-history behavior is not asserted to have occurred in these rows.",
                   "No score, board, rank, gate, weight or investment-return recalculation is performed."]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.repo), ensure_ascii=False, indent=2, allow_nan=False))
