"""Run the actual owning pytest suite with the candidate function in memory only.
No engine source is written. Tests keep their existing synthetic-store/data guards.
This is module regression proof, not historical replay or production acceptance.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "engine/risk_radar_intl.py"
raw = SOURCE.read_bytes()
expected = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"
if hashlib.sha256(raw).hexdigest() != expected:
    raise SystemExit("Source pin changed; do not transfer the old receipt.")
patch_path = Path(__file__).with_name("RRU1A_MISSINGNESS_CANDIDATE.patch")
lines = patch_path.read_text().splitlines()
removed = [s[1:] for s in lines if s.startswith("-") and not s.startswith("---")]
added = [s[1:] for s in lines if s.startswith("+") and not s.startswith("+++")]
if len(removed) != 1 or len(added) != 1 or raw.decode().count(removed[0]) != 1:
    raise SystemExit("Candidate is not one unique line replacement.")
text = raw.decode().replace(removed[0], added[0])

from engine import risk_radar_intl as radar
import pytest

node = next(n for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef) and n.name == "composite_series")
future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
module = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
exec(compile(module, str(SOURCE), "exec"), radar.__dict__)
print("SOURCE_SHA256", expected, flush=True)
print("CANDIDATE_SHA256", hashlib.sha256(text.encode()).hexdigest(), flush=True)
print("PATCH_SHA256", hashlib.sha256(patch_path.read_bytes()).hexdigest(), flush=True)
print("MODE in-memory candidate; actual module, percentile and owning tests", flush=True)
result = pytest.main([str(ROOT / "tests/test_risk_radar_intl_profiles.py"), "-q"])
if SOURCE.read_bytes() != raw:
    raise SystemExit("Unexpected source mutation during test execution.")
print("SOURCE_UNCHANGED", True, flush=True)
raise SystemExit(int(result))
