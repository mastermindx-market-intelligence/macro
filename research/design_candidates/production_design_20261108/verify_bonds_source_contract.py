#!/usr/bin/env python3
"""Characterize pinned Bonds source with controlled inputs.

This is read-only design evidence, not a release test or an implementation of
the proposed adapter. Passing means the documented current behavior reproduced.
Only named pure functions and the exact health arithmetic block are executed.
No repository module is imported, no collector runs, and no browser is used.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

PIN = "aec7f387badcdf69c9a947fafbc73b4c68470c7d"
EXPECTED_HASHES = {
    "scripts/build_bonds.py": "6b23a5397d78fcc41da7187ff2d0dff1d5bcb341cbec5f274aff07638ddfe8eb",
    "engine/bonds.py": "983e60492c12ea89699e9b4e824f95c00344691d8b9f82552125add4ca76ce57",
}

def source(root: Path, rel: str):
    data = (root / rel).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_HASHES[rel]:
        raise ValueError(f"Source drift in {rel}; refresh the evidence before rerunning.")
    return ast.parse(data.decode("utf-8")), digest

def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)

def execute(nodes, namespace, label):
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, label, "exec"), namespace)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Checkout of the pinned source, or an exact read-only source snapshot.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    build, bhash = source(args.source_root, "scripts/build_bonds.py")
    engine, ehash = source(args.source_root, "engine/bonds.py")
    captured = {}
    def capture_multi(series, **options):
        return {"series": series, "options": options}
    namespace = {"math": math, "pd": pd, "_multi": capture_multi}
    execute([
        function(build, "_build_finra_vm"),
        function(build, "_build_corp_credit_bond_health"),
        function(build, "chart_curve_now"),
    ], namespace, "pinned_pure_bonds_functions")

    def finra(net):
        raw = {"finra": {"breadth": {"all securities": {
            "advance_share_latest": 0.5,
            "wk52_high_low_net_share": net,
            "latest_date": "2026-10-14",
        }}}}
        vm = namespace["_build_finra_vm"](raw)
        machine = namespace["_build_corp_credit_bond_health"]({"finra": vm})
        return {
            "net_input": net,
            "retained_vm_net": vm["wk52_net_share"],
            "current_lows_pct": vm["lows_pct"],
            "current_machine_lows_share": machine["breadth"]["finra_lows_share"],
        }

    opposite = [finra(-0.2), finra(0.2)]
    assert [x["retained_vm_net"] for x in opposite] == [-0.2, 0.2]
    assert [x["current_lows_pct"] for x in opposite] == [20.0, 20.0]
    assert [x["current_machine_lows_share"] for x in opposite] == [0.2, 0.2]
    zero, missing = finra(0.0), finra(None)
    assert zero["retained_vm_net"] == 0.0 and zero["current_lows_pct"] == 0.0
    assert missing["retained_vm_net"] is None and missing["current_lows_pct"] is None

    frame = function(engine, "bonds_frame")
    health_block = next(n for n in frame.body if isinstance(n, ast.If)
                        and isinstance(n.test, ast.Name) and n.test.id == "legs")
    weights = {"recession": .30, "drawdown": .30, "credit": .20,
               "rates_vol": .10, "plumbing": .10}
    stresses = {"recession": 20.0, "drawdown": 40.0, "credit": np.nan,
                "rates_vol": 0.0, "plumbing": np.nan}
    index = pd.DatetimeIndex(["2026-10-14"])
    legs = {k: (pd.Series([stresses[k]], index=index), w) for k, w in weights.items()}
    health_ns = {"np": np, "legs": legs, "out": pd.DataFrame(index=index)}
    execute([health_block], health_ns, "pinned_health_arithmetic_block")
    score = float(health_ns["out"]["health_score"].iloc[0])
    available_weight = float(health_ns["den"].iloc[0])
    assert math.isclose(score, 74.28571428571428)
    assert round(score) == 74
    assert math.isclose(available_weight, .70)
    active = [k for k, (s, _) in legs.items() if s.notna().iloc[0]]
    assert active == ["recession", "drawdown", "rates_vol"]
    assert "health_coverage" not in health_ns["out"].columns

    early = pd.date_range("2025-09-30", "2026-07-09", periods=188).normalize()
    late = pd.date_range("2026-07-10", "2026-10-14", periods=64).normalize()
    curve_index = early.append(late)
    assert len(curve_index) == 252 and curve_index.is_unique and curve_index.is_monotonic_increasing
    cols = ["us3m", "us6m", "us1y", "us2y", "us3y", "us5y", "us7y", "us10y", "us30y"]
    curve = pd.DataFrame(4.0, index=curve_index, columns=cols)
    curve.iloc[0, 3:] = np.nan
    curve.iloc[-64, 7:] = np.nan
    sampled = [
        {"role": role, "offset": off, "sampled_frame_date": str(curve.index[off].date()),
         "valid_tenors": int(curve.iloc[off].notna().sum())}
        for role, off in [("latest", -1), ("approx_3_months", -64), ("approx_1_year", -252)]
    ]
    assert [x["sampled_frame_date"] for x in sampled] == ["2026-10-14", "2026-07-10", "2025-09-30"]
    output = namespace["chart_curve_now"](curve)
    rendered = output["series"]
    assert [x["label_en"] for x in rendered] == ["Today", "3 mo ago"]
    assert len(rendered) == 2
    assert all("sampled_frame_date" not in x for x in rendered)
    assert [x["valid_tenors"] for x in sampled] == [9, 7, 3]

    result = {
        "schema": "paper.bonds_source_characterization.v1",
        "status": "CURRENT_BEHAVIOR_REPRODUCED_NOT_FIX_ACCEPTANCE",
        "source_pin": PIN,
        "source_sha256": {"scripts/build_bonds.py": bhash, "engine/bonds.py": ehash},
        "execution_scope": {
            "pure_functions": ["_build_finra_vm", "_build_corp_credit_bond_health", "chart_curve_now"],
            "exact_block": "bonds_frame / if legs health arithmetic",
            "collector_run": False, "repository_import": False, "browser_run": False,
            "curve_renderer": "_multi stub captures series; no rendered-product proof",
        },
        "finra_opposite_signs": opposite,
        "finra_zero_and_missing": {"zero": zero, "missing": missing},
        "health_fixture": {
            "weights": weights,
            "stress_values": {k: None if not math.isfinite(v) else v for k, v in stresses.items()},
            "current_exact_score": score, "current_rounded_score": round(score),
            "active_legs": active, "available_weight": available_weight,
            "expected_weight": sum(weights.values()),
            "proposed_coverage_state": "partial",
            "coverage_block_implemented_by_this_harness": False,
        },
        "curve_fixture": {
            "controlled_build_date": "2026-10-16", "sampled_rows": sampled,
            "current_rendered_labels": [x["label_en"] for x in rendered],
            "sampled_frame_dates_in_current_series": False,
            "suppressed_role": "approx_1_year",
            "source_observation_dates": "not supplied by the fixture",
        },
        "limits": [
            "Synthetic inputs; no live FINRA or Treasury data was queried.",
            "FINRA denominator universe meaning remains unverified.",
            "Raw-count missing/zero-denominator cases are proposed producer acceptance, not executed here.",
            "The additive adapter and its actual page/machine consumer integration remain unimplemented.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Reproduced sign loss in page/machine projections; valid zero versus missing;")
    print("incumbent partial-score arithmetic (74, 70% weight); and undated/suppressed curve roles.")
    print("This characterizes current source behavior; it does not pass the proposed rollout contract.")

if __name__ == "__main__":
    main()
