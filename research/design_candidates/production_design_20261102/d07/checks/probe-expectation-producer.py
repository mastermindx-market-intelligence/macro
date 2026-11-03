from __future__ import annotations
import ast
import builtins
import sys
import hashlib
import json
import logging
import tempfile
from pathlib import Path

import pandas as pd

if len(sys.argv) != 2:
    raise SystemExit("Pass the pinned scripts/build_expectation_surface.py source file")
SOURCE = Path(sys.argv[1])
raw = SOURCE.read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
assert blob == "1b39e3a519a548d2187130498dd05b58a256ccdd", blob
module = ast.parse(raw)
allowed_constants = {
    "SCHEMA", "OBSERVATIONS_PATH", "ATTEMPTS_PATH", "ALIASES_PATH",
    "_POINT_FIELDS", "_KEY_COLS", "_OBS_REQUIRED", "_TOP_N_MOVERS",
    "_OFFLINE_MOVERS_METRICS",
}
selected = []
for node in module.body:
    if isinstance(node, ast.FunctionDef):
        selected.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in allowed_constants for t in node.targets):
        selected.append(node)
namespace = {
    "pd": pd, "Path": Path, "json": json,
    "log": logging.getLogger("d07-review"),
    "write_page": lambda path, text: path.write_text(text, encoding="utf-8"),
}
exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), str(SOURCE), "exec"), namespace)
results = []
def emit(case, observed, contract):
    results.append({"case": case, "observed": observed, "required_contract": contract})

def row(session, value, kind="average", missing=None, period="2026-12-31", ticker="AAA", at=None):
    return dict(collection_session_id=session, ticker_compat=ticker, metric="EPS", horizon_label_raw="0q",
                period_end=period, observation_type=kind, value=value, missingness_reason=missing,
                system_observed_at=at or {"s1":"2026-10-20T00:00:00Z", "s2":"2026-11-02T00:00:00Z"}[session])

def clocks(obs, attempts=None):
    reasons = []
    result = namespace["_session_clocks"](obs, attempts, reasons)
    return result, reasons

# Explicitly ineligible observations are excluded by averages but reappear in the explorer.
obs = pd.DataFrame([
    row("s1", 10.0), row("s2", 999.0, missing="UNESTIMABLE"),
    row("s2", 9999.0, "high", missing="UNESTIMABLE"),
    row("s2", 30.0, "covering_analyst_count", missing="UNESTIMABLE"),
])
clk, _ = clocks(obs)
pairs = namespace["_comparable_pairs"](obs, clk, {})
point = namespace["_ticker_points"](obs, clk)["AAA"]["EPS"]["0q"][-1]
assert len(pairs) == 0
assert point["average"] == 999.0 and point["high"] == 9999.0 and point["analysts"] == 30.0
emit("flagged-numeric-observations", {"comparable_pairs":len(pairs),"explorer_point":point}, "Suppress ineligible numeric values consistently while retaining reason and independent eligible fields.")

# Schema-boundary fixture. Current SRC-A1 emits null unit/currency/basis.
# Same fiscal key but known incompatible currency still enters arithmetic.
obs = pd.DataFrame([
    {**row("s1", 10.0), "unit":"millions", "currency":"USD", "basis":"GAAP"},
    {**row("s2", 20.0), "unit":"millions", "currency":"EUR", "basis":"GAAP"},
])
clk, _ = clocks(obs)
pairs = namespace["_comparable_pairs"](obs, clk, {})
assert len(pairs) == 1
emit("known-noncomparable-currency", {"input_class":"schema-boundary synthetic data","current_src_a1_metadata":"unit/currency/basis are null","pair_count":len(pairs),"prior_currency":"USD","latest_currency":"EUR","naive_change":float((pairs.iloc[0]["value"]-pairs.iloc[0]["prior_value"])/abs(pairs.iloc[0]["prior_value"]))}, "The source owner already keeps basis changes noncomparable. Preserve unit/currency/basis and their absence through the descriptive consumer.")

# Some valid observations can be omitted when the attempts ledger is only partially present.
obs = pd.DataFrame([row("s1", 10.0), row("s2", 12.0)])
attempts = pd.DataFrame([{"collection_session_id":"s1","attempted_at":"2026-10-20T00:00:00Z"}])
clk, reasons = clocks(obs, attempts)
assert list(clk.session_id) == ["s1"] and reasons == []
emit("partial-attempt-clocks", {"observed_sessions":list(obs.collection_session_id),"emitted_sessions":list(clk.session_id),"reasons":reasons}, "Account for every observed session with fallback or typed omission. A silent drop cannot be represented as complete coverage.")

# Storage order can create two movements at one timestamp.
obs = pd.DataFrame([row("s1", 10.0), row("s2", 11.0), row("s2", 12.0)])
clk, _ = clocks(obs)
pairs = namespace["_comparable_pairs"](obs, clk, {})
breadth = namespace["_breadth"](pairs, clk)
latest = namespace["_ticker_points"](obs, clk)["AAA"]["EPS"]["0q"][-1]
assert len(pairs) == 2 and breadth[-1]["up"] == 2 and latest["average"] == 12.0
emit("duplicate-observation-key", {"pair_count":len(pairs),"breadth":breadth,"explorer_latest":latest}, "Require an owner-selected eligible observation revision shared across views, with original raw observations and lineage preserved.")

# One point can combine statistics for incompatible end dates.
obs = pd.DataFrame([
    row("s1", 10.0, period="2026-09-30"),
    row("s1", 20.0, "high", period="2026-09-30"),
    row("s1", 12.0, period="2026-12-31"),
    row("s1", 24.0, "high", period="2026-12-31"),
])
clk, _ = clocks(obs)
point = namespace["_ticker_points"](obs, clk)["AAA"]["EPS"]["0q"][0]
assert point["period_end"] == "2026-09-30" and point["average"] == 12.0 and point["high"] == 24.0
emit("conflicting-period-within-point", point, "Only combine mean/range/count for the same resolved fiscal period. Otherwise suppress range and show source conflict.")

# Mixed offset clock strings are minimized before timestamp normalization.
obs = pd.DataFrame([row("s1", 10.0)])
attempts = pd.DataFrame([
    {"collection_session_id":"s1","attempted_at":"2026-11-02T01:00:00+02:00"},
    {"collection_session_id":"s1","attempted_at":"2026-11-02T00:30:00Z"},
])
clk, _ = clocks(obs, attempts)
assert clk.iloc[0]["at"] == "2026-11-02T00:30:00Z"
emit("offset-aware-session-order", {"emitted":clk.iloc[0]["at"],"chronological_min":"2026-11-01T23:00:00Z"}, "Require normalized UTC producer timestamps or normalize before selecting the chronological minimum.")

# Last-write-wins point selection differs from pair arithmetic when source order reverses.
obs = pd.DataFrame([row("s1", 10.0), row("s2", 12.0), row("s2", 11.0)])
clk, _ = clocks(obs)
pairs = namespace["_comparable_pairs"](obs, clk, {})
breadth = namespace["_breadth"](pairs, clk)
latest = namespace["_ticker_points"](obs, clk)["AAA"]["EPS"]["0q"][-1]
assert breadth[-1]["up"] == 1 and breadth[-1]["down"] == 1 and latest["average"] == 11.0
emit("duplicate-order-reversal", {"breadth":breadth,"latest":latest["average"]}, "Input row order must not manufacture a new revision or change source eligibility.")

# Aggregate census is not a count of issuer-level analysts.
obs = pd.DataFrame([
    row("s1", 10.0, "covering_analyst_count"),
    {**row("s1", 30.0, "covering_analyst_count"),"horizon_label_raw":"0y"},
])
clk, _ = clocks(obs)
median = namespace["_analysts_median"](obs, clk)
assert median == 20.0
emit("analyst-denominator", {"median":median,"population":"two ticker/metric/horizon keys; one issuer"}, "Label this as median coverage per metric/horizon at each key's latest count. Do not imply a common-session issuer consensus.")

# Per-file writes are visible before HTML rendering finishes.
with tempfile.TemporaryDirectory(prefix="d07-expectation-review-") as temp:
    root = Path(temp)
    directory = root / "site" / "expectation_surface" / "tickers"
    directory.mkdir(parents=True)
    (root / "templates").mkdir()
    (root / "site" / "expectation_surface.html").write_text("old-html-generation", encoding="utf-8")
    (directory / "OLD.json").write_text('{"series":{"old":true}}', encoding="utf-8")
    error = None
    original_import = builtins.__import__
    def fail_render_import(name, *args, **kwargs):
        if name == "jinja2":
            raise RuntimeError("injected render initialization failure")
        return original_import(name, *args, **kwargs)
    builtins.__import__ = fail_render_import
    try:
        namespace["_write_outputs"](root, {"state":"OFFLINE"}, [], [])
    except Exception as exc:
        error = type(exc).__name__
    finally:
        builtins.__import__ = original_import
    assert error == "RuntimeError"
    assert (root / "site" / "expectation_surface" / "summary.json").read_text() == '{"state": "OFFLINE"}'
    assert (directory / "index.json").read_text() == "[]"
    assert (root / "site" / "expectation_surface.html").read_text() == "old-html-generation"
    assert (directory / "OLD.json").exists()
    emit("publication-interrupted", {"exception":error,"summary":"new","index":"new","html":"old","old_ticker_file":"still present"}, "The existing publisher must stage and promote one coherent generation or declare mismatch. Verify original files on failed render and keep orphan histories labeled.")

print(json.dumps({"kind":"D07 advisory source diagnostics", "status":"BASELINE_REPRODUCED", "scope":"Source functions and controlled synthetic fixtures. These passing probes reproduce existing defects or limits and do not establish product acceptance.", "source_blob":blob, "executed":len(results), "results":results}, ensure_ascii=False, indent=2))
