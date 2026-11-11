#!/usr/bin/env python3
"""Characterize exact account helpers without account, doctrine, quote or FX I/O."""
from pathlib import Path
from typing import Any
from datetime import date, timedelta
import ast
import copy
import hashlib
import json
import logging
import math
import sys
import types

BASE = Path(__file__).resolve().parent
fixture = json.loads((BASE / "BOT_VALUATION_FIXTURES.json").read_text())
source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "source_inputs/bot_paper_account.py"
output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE / "BOT_VALUATION_CHARACTERIZATION.json"
source = source_path.read_text()
digest = hashlib.sha256(source.encode()).hexdigest()
assert digest == fixture["source_sha256"], "Pinned source bytes must match"
names = {"NavWithheld", "_valuation_day", "valuation", "nav", "positions_pnl"}
tree = ast.parse(source)
definitions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
assert {n.name for n in definitions} == names
module = ast.fix_missing_locations(ast.Module(body=definitions, type_ignores=[]))
assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in module.body)
logger = logging.getLogger("controlled_bot_account_helpers")
logger.handlers = [logging.NullHandler()]
logger.propagate = False

portfolio_stub = types.ModuleType("portfolio")
portfolio_stub.__path__ = []
marks_stub = types.ModuleType("portfolio.marks")
marks_stub._stale_max_days = lambda: fixture["stale_max_days"]
portfolio_stub.marks = marks_stub
saved = {key: sys.modules.get(key) for key in ("portfolio", "portfolio.marks")}
sys.modules["portfolio"] = portfolio_stub
sys.modules["portfolio.marks"] = marks_stub
results = []
account_reads = 0
try:
    for case in fixture["cases"]:
        def controlled_account(_portfolio_id=None):
            global account_reads
            account_reads += 1
            return copy.deepcopy(case["state"])
        namespace = {
            "__name__": "controlled_bot_account_helpers",
            "Any": Any, "date": date, "timedelta": timedelta,
            "math": math, "logging": logging, "_load_account": controlled_account,
        }
        exec(compile(module, str(source_path) + "#selected-pure-helpers", "exec"), namespace)
        prices = copy.deepcopy(case["prices"])
        evidence = copy.deepcopy(case["evidence"])
        legacy = namespace["nav"](prices, portfolio_id="controlled_fixture", asof=fixture["asof"])
        pnl = namespace["positions_pnl"](prices, portfolio_id="controlled_fixture")
        value = namespace["valuation"](prices, fixture["asof"], portfolio_id="controlled_fixture",
                                       state=copy.deepcopy(case["state"]), price_evidence=evidence)
        strict_error = None
        strict_value = None
        try:
            strict_value = namespace["nav"](prices, portfolio_id="controlled_fixture", strict=True,
                                            asof=fixture["asof"], price_evidence=evidence)
        except namespace["NavWithheld"]:
            strict_error = "NavWithheld"
        observed = {
            "legacy_nav": legacy, "nav_status": value["nav_status"], "nav": value["nav"],
            "nav_qualified": value["nav_qualified"],
            "classes": {ticker: row["class"] for ticker, row in value["lines"].items()},
            "priced_count": sum(row["current_price"] is not None for row in pnl.values()),
            "held_count": len(case["state"]["positions"]),
            "strict_nav": strict_value, "strict_error": strict_error,
        }
        observed["numeric_price_coverage_complete"] = observed["priced_count"] == observed["held_count"]
        for key, expected in case["expect"].items():
            assert observed[key] == expected, (case["id"], key, observed[key], expected)
        if case["id"] == "missing_mark_cost_fallback":
            assert all(pnl["B"][key] is None for key in ("current_price", "market_value", "unrealized_pnl"))
        results.append({"id": case["id"], "observed": observed, "positions_pnl": pnl, "valuation": value})
finally:
    for key, prior in saved.items():
        if prior is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = prior

report = {
    "status": "CURRENT_VALUATION_AND_LEGACY_PREVIEW_BEHAVIOR_REPRODUCED_NOT_INTEGRATION_ACCEPTANCE",
    "source": {"repository": fixture["source_repo"], "commit": fixture["source_commit"],
               "path": fixture["source_path"], "sha256": digest},
    "extracted_definitions": [{"name": n.name, "first_line": n.lineno, "last_line": n.end_lineno} for n in definitions],
    "execution": {"python": sys.version.split()[0], "real_account_reads": 0,
                  "controlled_account_stub_calls": account_reads, "fixed_stale_max_days": fixture["stale_max_days"],
                  "quote_calls": 0, "fx_calls": 0, "doctrine_reads": 0, "endpoint_calls": 0,
                  "module_initialization_executed": False, "browser_playback": False},
    "cases": results,
    "limits": [
        "Explicit synthetic account and mark fixtures in one stipulated monetary unit.",
        "No live defect occurrence, real balances, endpoint acceptance or deployed repair is established.",
        "Strict nav rejects withheld totals but can still return a provisional numeric total; consumers need the full valuation status.",
        "Current valuation treats empty evidence dictionaries as FRESH under optional legacy fields; QUALIFIED alone is not explicit close attestation.",
        "Numeric price coverage is a helper-derived analogue of the inspected API completeness formula, not endpoint execution.",
        "Currency, FX provenance, S0 snapshot integration and source attestation remain separate build requirements."
    ],
}
output_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "cases": len(results), "source_sha256": digest,
                  "output": str(output_path)}))
