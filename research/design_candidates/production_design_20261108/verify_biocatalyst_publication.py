#!/usr/bin/env python3
"""Characterize pinned Bio metadata; no app imports, I/O owners or production calls."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

p = argparse.ArgumentParser()
p.add_argument("--source", required=True, help="Exact source file or supplied exact-source snippets")
p.add_argument("--fixtures", default="BIOCATALYST_PUBLICATION_FIXTURES.json")
p.add_argument("--output", default="BIOCATALYST_PUBLICATION_CHARACTERIZATION.json")
a = p.parse_args()
source = Path(a.source).read_text()
fixtures = json.loads(Path(a.fixtures).read_text())
tree = ast.parse(source)
selected = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {"_meta", "_opaque_digest"}:
        selected.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_AUTHORITY" for t in node.targets):
        selected.append(node)
assert len(selected) == 3, "Expected exact two functions and authority assignment"
extracted = "\n\n".join(ast.get_source_segment(source, n) for n in selected)
module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + selected, type_ignores=[])
namespace = {"json": json, "sha256": hashlib.sha256}
exec(compile(ast.fix_missing_locations(module), "<pinned-biocat-extract>", "exec"), namespace)
meta, opaque = namespace["_meta"], namespace["_opaque_digest"]
base = fixtures["generation_base"]
g1 = SimpleNamespace(**base, generation_id=fixtures["generation_ids"][0])
g2 = SimpleNamespace(**base, generation_id=fixtures["generation_ids"][1])
m1 = meta(SimpleNamespace(generation=g1), fixtures["health"])
m2 = meta(SimpleNamespace(generation=g2), fixtures["health"])
d1 = opaque({"generation_id": g1.generation_id})
d2 = opaque({"generation_id": g2.generation_id})
assert m1 == m2 and d1 != d2
assert not any(k in m1 for k in ["publication_ref", "generation_id", "snapshot_id"])
m3 = meta(SimpleNamespace(generation=g1), fixtures["later_health"])
assert m3 != m1
assert opaque({"generation_id": g1.generation_id}) == d1
result = {
    "status": "CURRENT_PUBLICATION_BINDING_GAP_REPRODUCED_NOT_FIX_ACCEPTANCE",
    "source": fixtures["source"],
    "extraction": {"functions": ["_meta", "_opaque_digest"], "constant": "_AUTHORITY", "sha256": hashlib.sha256(extracted.encode()).hexdigest(), "input_sha256": hashlib.sha256(source.encode()).hexdigest()},
    "cases": [
        {"id": "different_generations_identical_public_metadata", "current_metadata_equal": m1 == m2, "existing_generation_digests_differ": d1 != d2, "digests": [d1,d2], "required_future": "Project the existing generation binding consistently into queue/dossier/screen responses."},
        {"id": "same_generation_different_operational_health", "current_metadata_equal": m1 == m3, "generation_digest_equal": True, "required_future": "Keep generation identity separate from operational clocks; neither is issuer identity or authorization."}
    ],
    "execution": {"app_imported": False, "network_calls": 0, "storage_calls": 0, "browser_playback": False, "generation_inputs": "controlled fictional fixtures"},
    "limits": ["The opaque digest already exists for cursor binding; this does not add it to public API metadata.", "No live source mismatch or current source generation was observed.", "Publication equality does not prove exact historical retrieval, security identity or research authority.", "The fixture never invokes publication, auth, alerts, prices or trading."],
}
Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "cases_passed": len(result["cases"]), "output": a.output}))
