#!/usr/bin/env python3
"""Characterize the pinned heatmap helper before reuse by a historical calendar."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import platform
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = "macro/engine/sp500_heatmap.py"
SOURCE_SHA256 = "94607542cae6a31485bd7116a5af4cbe12a5d21d8fb36f33e8e86289f0853682"
PIN = "aec7f387badcdf69c9a947fafbc73b4c68470c7d"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT / "source_inputs")
    args = parser.parse_args()
    raw = (args.source_root / SOURCE_PATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, "Source hash mismatch"
    tree = ast.parse(raw.decode(), filename=SOURCE_PATH)
    names = {"_DATE_OFFSETS", "_pct", "_ref_close_on_or_before", "daily_returns"}
    def name(node):
        if isinstance(node, ast.FunctionDef):
            return node.name
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return node.target.id
        return None
    selected = [node for node in tree.body if name(node) in names]
    assert {name(node) for node in selected} == names
    module = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *selected], type_ignores=[])
    ns = {"np": np, "pd": pd}
    exec(compile(ast.fix_missing_locations(module), SOURCE_PATH, "exec"), ns)
    fixture = json.loads((ROOT / "RETURNS_SOURCE_FIXTURES.json").read_text())
    results = []
    for case in fixture["cases"]:
        frame = pd.DataFrame({"DEMO": case["closes"]}, index=pd.to_datetime(case["dates"]))
        observed = ns["daily_returns"](frame, asof=case["requested_session"]).get("DEMO", {}).get("1D")
        assert observed == case["expected_existing_helper_1d"], case["id"]
        results.append({
            "id": case["id"], "requested_session": case["requested_session"],
            "latest_available_session": case["dates"][-1], "helper_1d_pct": observed,
            "required_selected_session_return_pct": case["required_selected_session_return"],
            "acceptance_reason": case.get("required_reason"),
        })
    a = fixture["decomposition"]
    p, o, c = a["previous_close"], a["regular_open"], a["endpoint"]
    gap, regular, total = o/p-1, c/o-1, c/p-1
    compounded = (1+gap)*(1+regular)-1
    log_gap, log_regular, log_total = math.log(o/p), math.log(c/o), math.log(c/p)
    assert math.isclose(compounded, total, abs_tol=1e-12)
    assert math.isclose(log_gap+log_regular, log_total, abs_tol=1e-12)
    assert not math.isclose(gap+regular, total, abs_tol=1e-12)
    result = {
        "schema": "paper.returns_source_characterization.v1",
        "status": "CURRENT_HELPER_REUSE_HAZARD_REPRODUCED_NOT_PRODUCT_ACCEPTANCE",
        "source": {"repository": "mastermindx-market-intelligence/macro", "pin": PIN,
                   "path": "engine/sp500_heatmap.py", "sha256": SOURCE_SHA256},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "cases": results,
        "arithmetic_specification_example": {
            "inputs": a,
            "simple_gap_pct": gap*100, "simple_regular_pct": regular*100,
            "simple_total_pct": total*100, "incorrect_simple_sum_pct": (gap+regular)*100,
            "compounded_total_pct": compounded*100,
            "log_gap": log_gap, "log_regular": log_regular, "log_total": log_total,
            "scope": "Formula identity only; no claim of an installed Returns adapter."
        },
        "limits": [
            "The source helper's asof is an anchor date, not a historical-session selector. This is a reuse hazard, not a proven live Returns Calendar bug.",
            "Only exact AST definitions executed; no package initialization, collector, API, source build, route or publication.",
            "The pre-sliced case is a controlled input. A production adapter must also resolve the expected previous session through its existing calendar owner.",
            "No claim of adjustment, dividend treatment, finality, completeness, historical availability, or runtime acceptance."
        ]
    }
    target = ROOT / "RETURNS_SOURCE_CHARACTERIZATION.json"
    target.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": result["status"], "source_hash_verified": True,
                      "cases": len(results), "output": str(target)}, indent=2))

if __name__ == "__main__":
    main()
