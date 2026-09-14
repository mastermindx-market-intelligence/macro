"""Actual-module call/binding witness and deliberately broken-output control.
Runs only the owning synthetic-input tests; never edits production source.
The mutant is a zero composite, not a positive rescaling (ranks ignore scaling).
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "engine/risk_radar_intl.py"
EXPECTED = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mutant-zero", action="store_true")
    args = parser.parse_args()
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    old = "        col = ser.fillna(0.5) * w"
    new = "        col = ser.fillna(0.0) * w"
    assert raw.decode().count(old) == 1
    candidate_text = raw.decode().replace(old, new)
    from engine import risk_radar_intl as radar
    import pytest
    node = next(n for n in ast.parse(candidate_text).body
                if isinstance(n, ast.FunctionDef) and n.name == "composite_series")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    tree = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
    exec(compile(tree, "candidate_composite", "exec"), radar.__dict__)
    injected = radar.composite_series
    seen = []

    def witnessed(*a, **kw):
        seen.append(getattr(a[0], "key", "unknown"))
        bench, sub, comp, gate = injected(*a, **kw)
        if args.mutant_zero and comp is not None:
            comp = comp * 0.0
        return bench, sub, comp, gate

    radar.composite_series = witnessed
    result = int(pytest.main([str(ROOT / "tests/test_risk_radar_intl_profiles.py"), "-q", "--tb=short"]))
    evidence = {"mode": "mutant_zero" if args.mutant_zero else "candidate",
        "pytest_exit": result, "calls": len(seen), "profiles_reached": sorted(set(seen)),
        "binding_preserved": radar.composite_series is witnessed,
        "source_unchanged": SOURCE.read_bytes() == raw,
        "candidate_sha256": hashlib.sha256(candidate_text.encode()).hexdigest()}
    print("DISCRIMINATION_RECEIPT " + json.dumps(evidence, sort_keys=True))
    assert seen and evidence["binding_preserved"] and evidence["source_unchanged"]
    assert result == (1 if args.mutant_zero else 0), "Owning suite did not discriminate as expected"


if __name__ == "__main__":
    main()
