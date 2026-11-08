#!/usr/bin/env python3
"""Offline, source-bound news projection proof; no model or production mutation.

The gateway is not imported or started. Only its unchanged model-result and JSON
normalizer function bodies are evaluated for this tool name. This proves that
specific serialization boundary, not authentication, dispatch or model behavior.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded._VPS_LIVE_DIR = "/nonexistent/news-proof/public"
    loaded._VPS_STATE_DIR = "/nonexistent/news-proof/state"
    return loaded

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--baseline-module", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    for name in ("MACRO_LIVE_DIR", "MACRO_LIVE_STATE_DIR"):
        os.environ.pop(name, None)
    helper = root / "engine/neuralweb/brain_market_intel.py"
    gateway = root / "engine/neuralweb/brain_gateway.py"
    current = module(helper, "news_candidate")
    baseline = module(args.baseline_module, "news_baseline")
    # A fixed evaluation instant makes the exact pinned-data read reproducible.
    now = datetime(2026, 11, 8, 8, 44, 41, tzinfo=timezone.utc)
    before = baseline.get_market_events(root, window_h=48, limit=5, symbol="NVDA", now=now)
    after = current.get_market_events(root, window_h=48, limit=5, symbol="NVDA", now=now)
    assert before["events"], "real pinned data must contribute events"
    assert before["events"] == [
        {k: v for k, v in event.items() if k in baseline.EVENT_FIELDS}
        for event in after["events"]
    ], "existing event content, ordering and selection changed"
    assert {k: after[k] for k in ("asof", "window_h", "note")} == {
        k: before[k] for k in ("asof", "window_h", "note")
    }
    parsed = ast.parse(gateway.read_text())
    names = {"_model_visible_tool_result", "_json_safe"}
    functions = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in functions} == names
    body = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *functions]
    ns = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                 str(gateway), "exec"), ns)
    visible = ns["_model_visible_tool_result"]("get_market_events", after)
    transported = json.loads(json.dumps(ns["_json_safe"](visible), default=str))
    assert transported == after
    assert transported["asof_basis"] == "tool_read_time"
    assert transported["collection_health"]["state"] == "unknown"
    assert any(e["source_url"] for e in transported["events"])
    assert all(e["news_freshness"]["retained_from_previous_build"] is None
               for e in transported["events"]), "these artifacts carry no explicit retention boolean"
    receipt = {
        "schema": "mastermind.news_brain_projection_proof.v1",
        "artifact_source_commit": "4bf5db311721bb2ceffe66f694de08a52d9d168c",
        "evaluation_instant": now.isoformat(),
        "source_sha256": {"candidate_helper": digest(helper),
                          "baseline_helper": digest(args.baseline_module),
                          "gateway": digest(gateway)},
        "artifact_sha256": {name: digest(root / "site/news" / name)
                            for name in ("macro.json", "financial.json")},
        "checks": {"old_event_projection_and_order_preserved": True,
                   "unchanged_gateway_projection_and_json_normalizer_preserve_metadata": True,
                   "health_unknown_without_receipt": True,
                   "actual_upstream_links_preserved": True,
                   "retention_unknown_without_explicit_flag": True},
        "model_visible_result": transported,
        "limits": ["offline read of pinned artifacts whose hashes match the observed VPS files",
                   "wire ladder neutralized; this proof reads nightly artifacts only",
                   "gateway function bodies evaluated without gateway initialization",
                   "not the recovered raw response of the live model run",
                   "no authenticated dispatch, provider call, source release or production acceptance"]
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checks": receipt["checks"], "event_count": len(transported["events"]),
                      "source_sha256": receipt["source_sha256"],
                      "artifact_sha256": receipt["artifact_sha256"]}))

if __name__ == "__main__":
    main()
