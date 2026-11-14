import ast
import datetime
import hashlib
import json
from pathlib import Path

directory = Path(__file__).resolve().parent
manifest = json.loads((directory / "sources.json").read_text())
entry = next(item for item in manifest["files"] if item["source_path"] == "ingest/gen_fund_cn.py")
source_path = directory / entry["local_path"]
source_bytes = source_path.read_bytes()
assert hashlib.sha1(f"blob {len(source_bytes)}\0".encode() + source_bytes).hexdigest() == entry["git_blob"]
assert hashlib.sha256(source_bytes).hexdigest() == entry["sha256"]
assert len(source_bytes) == entry["bytes"]
tree = ast.parse(source_bytes.decode())
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"_f", "build_estimates"}]
assert {node.name for node in functions} == {"_f", "build_estimates"}
namespace = {"dt": datetime}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_path), "exec"), namespace)
build = namespace["build_estimates"]
results = []
assertions = 0


def equal(actual, expected):
    global assertions
    assertions += 1
    assert actual == expected, (actual, expected)


def run(identifier, label, operation):
    before = assertions
    observed = operation()
    results.append({"id": identifier, "label": label, "status": "BASELINE_REPRODUCED", "assertions": assertions - before, "observed": observed})


def fixture(years):
    return {"600519.SH": {year: {"EPS": year - 2020, "TOTAL_OPERATE_INCOME": (year - 2020) * 1_000_000} for year in years}}


def annual_targets(years):
    output = build("600519.SH", fixture(years), {}, {"income": {}}, "600519.SS")
    equal(output["eps_fy"]["periods"], [str(year) for year in sorted(years)])
    equal(output["eps_q"], None)
    equal(output["rev_fy"]["n"], [None] * len(years))
    return output


run("FP01", "Three annual targets and null quarters", lambda: annual_targets([2026, 2027, 2028]))
run("FP02", "Sparse targets preserve the absent year", lambda: annual_targets([2026, 2028]))
run("FP03", "A single later target retains its fiscal identity", lambda: annual_targets([2028]))


def no_consensus():
    output = build("600519.SH", {}, {"600519.SH": [{"publishDate": "2026-03-01", "predictThisYearEps": 8}]}, {"income": {}}, "600519.SS")
    equal(output, None)
    return output


run("FP04", "Reports alone do not manufacture consensus coverage", no_consensus)


def populations():
    reports = {"600519.SH": [
        {"publishDate": "2026-02-01", "predictThisYearEps": 8, "orgSName": "Same firm"},
        {"publishDate": "2025-10-01", "predictNextYearEps": 9, "orgSName": "Same firm"},
        {"publishDate": "2024-10-01", "predictNextYearEps": 99, "orgSName": "Excluded year"},
    ]}
    output = build("600519.SH", fixture([2026]), reports, {"income": {}}, "600519.SS")
    equal(output["eps_fy"], {"periods": ["2026"], "avg": [6.0], "high": [9.0], "low": [8.0], "n": [2]})
    equal(output["rev_fy"]["high"], [None])
    equal(output["rev_fy"]["low"], [None])
    return output


run("FP05", "Consensus mean and per-report range/count retain distinct populations", populations)


def zero_and_missing():
    consensus = {"600519.SH": {2026: {"EPS": 0, "TOTAL_OPERATE_INCOME": None}, 2027: {"EPS": -2, "TOTAL_OPERATE_INCOME": 0}, 2028: {"EPS": None, "TOTAL_OPERATE_INCOME": None}}}
    output = build("600519.SH", consensus, {}, {"income": {}}, "600519.SS")
    equal(output["eps_fy"]["avg"], [0.0, -2.0, None])
    equal(output["rev_fy"]["avg"], [None, 0.0, None])
    equal(output["eps_fy"]["n"], [None, None, None])
    return output


run("FP06", "Zero, negative and absent estimate values remain distinct", zero_and_missing)
print(json.dumps({"status": "SOURCE_BEHAVIOR_REPRODUCED", "source_commit": manifest["commit"], "method": "AST-selected unchanged _f and build_estimates definitions; no producer top-level execution", "cases": len(results), "assertions": assertions, "integrity_checks": 3, "component_render_assertions": 0, "browser_assertions": 0, "results": results}, indent=2))
