#!/usr/bin/env python3
"""Characterize exact pinned helpers without importing either application.

Run with Python + pandas, supplying source snapshots at the pinned SHAs:
  python verify_government_revenue_source_contract.py --source-root source_inputs

The snapshots are deliberately not bundled as a new source owner. The script
loads only listed AST definitions; no module initialization, collector, API,
alert run, lifecycle mutation, publication or notification occurs.
"""
from __future__ import annotations
import argparse
import ast
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import re
from typing import Any, Sequence
import pandas as pd

SOURCES = {
    "macro/engine/government_revenue/point_in_time.py": {
        "repository": "mastermindx-market-intelligence/macro",
        "sha": "aec7f387badcdf69c9a947fafbc73b4c68470c7d",
        "sha256": "bb747d91fcdcf2a7b7773dcc14c80a40f7d5aab344b41953ea5225b9af981a3a",
    },
    "macro/engine/government_revenue/metrics.py": {
        "repository": "mastermindx-market-intelligence/macro",
        "sha": "aec7f387badcdf69c9a947fafbc73b4c68470c7d",
        "sha256": "2ab30708459613c958b0a923ee6597ab2206795d027b31582551ef77cc85a787",
    },
    "terminal/ingest/alerts_engine.py": {
        "repository": "mastermindx-market-intelligence/mastermind-terminal",
        "sha": "5107f4d84e26aefc540c8c99e0ea3803770f1bb3",
        "sha256": "d08569144973ac96cfcb9561533c77b5552219a9abbbf251ead1ea031f355d0a",
    },
}

def definition_name(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None

def isolated_definitions(tree, names, filename, namespace):
    selected = [n for n in tree.body if definition_name(n) in names]
    assert {definition_name(n) for n in selected} == set(names), filename
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), filename, "exec"), namespace)
    return namespace

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path(__file__).with_name("source_inputs"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("GOV_REVENUE_SOURCE_CHARACTERIZATION.json"))
    args = parser.parse_args()
    fixtures = json.loads(Path(__file__).with_name("GOV_REVENUE_SOURCE_FIXTURES.json").read_text())
    trees = {}
    for path, source in SOURCES.items():
        raw = (args.source_root / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"], f"Source hash mismatch: {path}"
        trees[path] = ast.parse(raw.decode(), filename=path)

    ns = {"pd": pd, "math": math, "date": date, "datetime": datetime, "re": re, "Any": Any, "Sequence": Sequence}
    strict_path = "macro/engine/government_revenue/point_in_time.py"
    strict = isolated_definitions(
        trees[strict_path],
        {"KNOWLEDGE_CLOCK_COLUMNS", "EFFECTIVE_CLOCK_COLUMNS", "_DATE_ONLY",
         "timestamp", "analysis_clock", "_series_timestamps", "_coalesced_timestamps", "filter_dual_clock"},
        strict_path, dict(ns),
    )
    metrics_path = "macro/engine/government_revenue/metrics.py"
    legacy = isolated_definitions(trees[metrics_path], {"_timestamp", "_analysis_clock"}, metrics_path, dict(ns))
    frame = pd.DataFrame(fixtures["rows"])
    strict_cutoff = strict["analysis_clock"](fixtures["request"])[1]
    legacy_cutoff = legacy["_analysis_clock"](fixtures["request"])[1]
    def visible(cutoff, effective=True):
        kwargs = {"knowledge_cutoff": cutoff}
        if effective:
            kwargs["effective_cutoff"] = cutoff
        return strict["filter_dual_clock"](frame, **kwargs)["id"].tolist()
    strict_ids, legacy_ids = visible(strict_cutoff), visible(legacy_cutoff)
    assert strict_ids == fixtures["expected"]["strict_intraday_ids"]
    assert legacy_ids == fixtures["expected"]["metrics_intraday_ids"]
    knowledge_only_ids = visible(strict_cutoff, effective=False)
    assert knowledge_only_ids == fixtures["expected"]["strict_knowledge_only_ids"]
    strict_day = strict["analysis_clock"](fixtures["date_control"])[1]
    legacy_day = legacy["_analysis_clock"](fixtures["date_control"])[1]
    assert visible(strict_day) == visible(legacy_day) == fixtures["expected"]["date_control_ids"]
    assert strict_day != legacy_day  # ns versus us endpoints, not an assertion of identical precision.

    alerts_path = "terminal/ingest/alerts_engine.py"
    alert_tree = trees[alerts_path]
    data_class = next(n for n in alert_tree.body if isinstance(n, ast.ClassDef) and n.name == "Data")
    last_method = next(n for n in data_class.body if isinstance(n, ast.FunctionDef) and n.name == "last")
    method_module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), last_method],
        type_ignores=[],
    )
    alert_ns = {"_OPT_EVALUATORS": {}}
    # Options dispatch is deliberately outside this characterization. All test
    # conditions are legacy "price"; no stateful or suite evaluator is invoked.
    exec(compile(ast.fix_missing_locations(method_module), alerts_path, "exec"), alert_ns)
    isolated_definitions(alert_tree, {"evaluate"}, alerts_path, alert_ns)
    FixtureData = type("FixtureData", (), {"last": alert_ns["last"]})
    price_results = []
    for case in fixtures["price_cases"]:
        data = FixtureData()
        data.quotes = {"AVAV": {"last": case["quote_last"]}} if "quote_last" in case else {}
        data.symbols = {"AVAV": {"last": case["manifest_last"], "asof": "2026-11-09"}} if "manifest_last" in case else {}
        data.used_eod_fallback = False
        data.eod_fallback_asof = None
        observed_last, basis = data.last("AVAV")
        result = alert_ns["evaluate"]({"symbol": "AVAV", "condition": fixtures["price_condition"]}, data)
        fired, value, note, next_state = result
        assert fired is case["expected_fired"], case["name"]
        assert basis == case["expected_basis"], case["name"]
        assert next_state is None, case["name"]
        price_results.append({
            "name": case["name"], "last": observed_last, "basis": basis,
            "fired": fired, "value": value, "note": note, "next_state": next_state,
            "transition_proven": False,
        })

    output = {
        "schema": "paper.government_revenue_source_characterization.v1",
        "status": "CURRENT_HELPER_BEHAVIOR_REPRODUCED_NOT_FIX_ACCEPTANCE",
        "environment": {"python": platform.python_version(), "pandas": pd.__version__},
        "sources": SOURCES,
        "clock_characterization": {
            "request": fixtures["request"],
            "strict_cutoff": strict_cutoff.isoformat(),
            "metrics_cutoff": legacy_cutoff.isoformat(),
            "strict_visible_ids": strict_ids,
            "metrics_visible_ids": legacy_ids,
            "strict_knowledge_only_visible_ids": knowledge_only_ids,
            "date_control": {
                "request": fixtures["date_control"],
                "strict_cutoff": strict_day.isoformat(),
                "metrics_cutoff": legacy_day.isoformat(),
                "visible_ids": visible(strict_day),
                "endpoint_precision_identical": False,
            },
        },
        "legacy_price_characterization": price_results,
        "r5_crossing_requirements": fixtures["r5_acceptance_examples"],
        "limits": [
            "Controlled fixtures; no claim that a current live R5 view leaks future data.",
            "Effective cutoff was intentionally supplied for historical state. A calendar may show future effective events known by its knowledge cutoff.",
            "Only Data.last and legacy price evaluation were executed. Quote acquisition, evaluation vintage, disarming, suite dispatch, API admission, persistence, fire receipts, outbox and delivery were not executed.",
            "A helper return of fired=true is not evidence that an alert fired or delivered in the installed system.",
            "The R5 crossing examples remain build acceptance requirements; this script does not implement an alert condition.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": output["status"], "source_hashes_verified": len(SOURCES),
                      "clock_cases": 4, "price_cases": len(price_results), "output": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
