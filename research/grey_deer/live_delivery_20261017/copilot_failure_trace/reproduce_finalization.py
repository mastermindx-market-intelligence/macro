"""Read-only diagnostic: execute selected pure nodes from the pinned gateway.

No first-party module import, provider call, or source mutation. This is a
counterexample to the finalization contract, not a replay of the live request.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SOURCE_REF = "15bdaec7351dbe2f1bf1a227b6e7498a8b3c0ac7"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repository", type=Path, default=ROOT.parents[3])
parser.add_argument("--source-root", type=Path, help="Optional already-captured exact source tree; never imports it")
parser.add_argument("--record", type=Path, default=ROOT.parent / "runtime_response_record.json")
parser.add_argument("--output", type=Path, help="Write a new result only to this explicit destination")
args = parser.parse_args()

def read_pinned(path: str, expected: str) -> bytes:
    if args.source_root is not None:
        content = (args.source_root / path).read_bytes()
    else:
        content = subprocess.run(
            ["git", "-C", str(args.repository), "show", SOURCE_REF + ":" + path],
            check=True, capture_output=True,
        ).stdout
    assert hashlib.sha256(content).hexdigest() == expected
    return content

SOURCE = "engine/neuralweb/brain_gateway.py"
EXPECTED = "78f4d3b320d25ff1b6b86c933fbac725fb0fe1784fe3ec7c4874564a08e926bf"
raw = read_pinned(SOURCE, EXPECTED)
tree = ast.parse(raw, filename=str(SOURCE))
names = {
    "_EVIDENCE_FAMILY_LABELS", "_EVIDENCE_FAMILY_CONTRADICTION_READS",
    "_evidence_probe_has_positive_marker", "_evidence_result_conditions",
    "_evidence_result_state", "_evidence_coverage_receipt",
    "_evidence_coverage_fallback_answer", "_evidence_coverage_disclosure",
    "_append_evidence_coverage_disclosure", "_split_suggestions",
}
nodes = []
for node in tree.body:
    name = getattr(node, "name", None)
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        name = node.target.id
    if name in names:
        nodes.append(node)
ns = {"Any": Any, "re": re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), ns)

# Execute the actual two finalization statements, preserving their source lines.
final_nodes = sorted(
    [n for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.If))
     and n.lineno in (8308, 8309)], key=lambda n: n.lineno)
assert len(final_nodes) == 2
final_code = compile(ast.Module(body=final_nodes, type_ignores=[]), str(SOURCE), "exec")
required = {"portfolio_current": ("get_portfolio_brief",)}
observations = [
    ("read_world_state", {"ok": True, "as_of": "2026-10-16"}),
    # Deliberately macro-scoped: the existing mapping never reads this scope.
    ("read_contradictions", {"contradictions": [{"scope": "macro_rates", "kind": "growth_vs_credit"}]}),
    ("read_factor_state", {"ok": True}),
    ("get_market_events", {"ok": True}),
]

def finalize(text: str, gate: bool, obs: list, req: dict | None = required) -> dict:
    env = dict(ns, full_answer=text, evidence_gate_issued=gate,
               evidence_observations=obs, evidence_required=req, turn_lang="en")
    exec(final_code, env)
    clean, suggestions = ns["_split_suggestions"](env["full_answer"])
    return {"before": text, "gate_issued": gate, "receipt": env["receipt"],
            "after_coverage": env["full_answer"], "after_suggestion_split": clean,
            "empty_after_coverage": not bool(clean.strip()), "suggestions": suggestions}

cases = {
    "blank_without_repair": finalize("", False, observations),
    "blank_with_repair": finalize("", True, observations),
    "supported_prose_without_repair": finalize("Supported market answer.", False, observations),
    "blank_without_adverse_coverage": finalize("", False, [], {}),
    "portfolio_witness_no_contradiction": finalize("Supported market answer.", False,
                                                   [("get_portfolio_brief", {"ok": True})]),
}
expected_caveat = "Evidence caveat — portfolio: not covered (contradiction present)."
assert cases["blank_without_repair"]["after_coverage"] == expected_caveat
assert cases["blank_without_repair"]["empty_after_coverage"] is False
assert cases["blank_with_repair"]["after_coverage"].startswith("I couldn't produce a supported answer")
assert cases["supported_prose_without_repair"]["after_coverage"].startswith("Supported market answer.\n\n")
assert cases["blank_without_adverse_coverage"]["empty_after_coverage"] is True
assert cases["portfolio_witness_no_contradiction"]["after_coverage"] == "Supported market answer."
record = json.loads(args.record.read_text())
assert record["answer"] == expected_caveat

# Exact-question profile plus bounded semantic controls, again executing only
# the original pure classifier AST and its own local regex/constant dependencies.
ASK = "engine/neuralweb/ask_brain.py"
ASK_EXPECTED = "a982ab591c3d1a4f940d69bf95e7b499f61af505e35c1f40e3ff50070c758a9d"
ask_raw = read_pinned(ASK, ASK_EXPECTED)
assert hashlib.sha256(ask_raw).hexdigest() == ASK_EXPECTED
ask_tree = ast.parse(ask_raw, filename=str(ASK))
index = {}
for node in ask_tree.body:
    node_names = []
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        node_names = [node.name]
    elif isinstance(node, ast.Assign):
        node_names = [x.id for x in node.targets if isinstance(x, ast.Name)]
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        node_names = [node.target.id]
    for name in node_names:
        index[name] = node
wanted = {"_question_profile", "_fast_required_evidence_families", "_fast_visible_tool_names"}
while True:
    dependencies = {x.id for name in wanted for x in ast.walk(index[name])
                    if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)
                    and x.id in index}
    if dependencies <= wanted:
        break
    wanted |= dependencies
ask_nodes = sorted({index[name] for name in wanted}, key=lambda x: x.lineno)
ask_ns = {"__name__": __name__, "re": re, "dataclass": dataclass}
exec(compile(ast.Module(body=ask_nodes, type_ignores=[]), str(ASK), "exec"), ask_ns)
question = record["question"]
suffix = " No portfolio percentages or trades."
assert question.endswith(suffix)
base = question[:-len(suffix)]
questions = {
    "exact_live_question": question,
    "same_question_without_final_constraint": base,
    "same_constraint_without_portfolio_token": base + " No numerical allocations or trades.",
    "explicit_portfolio_exclusion": base + " Do not analyze my portfolio.",
    "affirmative_private_portfolio": "What risks are building in my portfolio?",
    "affirmative_portfolio_with_allocation_constraint": "What risks are building in my portfolio? No portfolio percentages or trades.",
}
classification = {}
for label, q in questions.items():
    profile = ask_ns["_question_profile"](q, None)
    trigger = ask_ns["_PORTFOLIO_TRIGGER_TERMS"].search(q)
    classification[label] = {
        "question": q, "context_ticker": None, "profile": asdict(profile),
        "required": ask_ns["_fast_required_evidence_families"](profile),
        "visible_tools": ask_ns["_fast_visible_tool_names"](profile),
        "portfolio_trigger": {"text": trigger.group(), "span": list(trigger.span())} if trigger else None,
    }
assert classification["exact_live_question"]["profile"]["name"] == "portfolio_current"
assert classification["exact_live_question"]["required"] == {
    "portfolio_current": ("get_portfolio_brief", "get_watchlist")}
assert classification["same_question_without_final_constraint"]["profile"]["name"] == "ambiguous"
assert classification["same_constraint_without_portfolio_token"]["required"] is None
assert classification["explicit_portfolio_exclusion"]["profile"]["name"] == "portfolio_current"
assert classification["affirmative_private_portfolio"]["profile"]["name"] == "portfolio_current"
assert classification["affirmative_portfolio_with_allocation_constraint"]["profile"]["name"] == "portfolio_current"
classified_finalization = finalize("", False, observations,
                                   classification["exact_live_question"]["required"])
assert classified_finalization["after_coverage"] == expected_caveat
result = {
    "source_sha256": EXPECTED, "source_ref": "15bdaec7351dbe2f1bf1a227b6e7498a8b3c0ac7",
    "source_lines_executed": [8308, 8309], "mode": "pure AST counterexample; no runtime imports",
    "live_record_id": record["id"], "live_answer_matches_counterexample": True,
    "live_flags": record["flags"], "cases": cases,
    "classifier_source_sha256": ASK_EXPECTED,
    "classification_cases": classification,
    "exact_classification_to_finalization": classified_finalization,
    "limitations": [
        "Exact source classifier requires portfolio_current; live model-visible authorized schemas were not replayed.",
        "Tool payloads are synthetic; live contradiction payload scope was not retrieved.",
        "Provider stop reason/repair flag are not contained in the sanitized runtime record.",
        "Post-filter function belongs to ask_brain.py and is not substituted or claimed executed here.",
    ],
}
if args.output is not None:
    args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"source_sha256": EXPECTED, "cases": len(cases),
                  "exact_caveat_reproduced": True, "live_answer_matches": True,
                  "classification_cases": len(classification),
                  "exact_profile": classification["exact_live_question"]["profile"]["name"],
                  "artifact": str(args.output) if args.output else None}))
