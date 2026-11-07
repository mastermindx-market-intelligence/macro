#!/usr/bin/env python3
"""Verify the delivered research bytes and basic document/data integrity; no writes."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


def reject_constant(value):
    raise ValueError(f"Non-finite JSON constant: {value}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / "ARTIFACTS_SHA256.json").read_text())
    errors = []
    counts = {"files": 0, "json": 0, "python": 0, "markdown": 0}
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve()
        if root not in path.parents:
            errors.append(f"Unsafe manifest path: {relative}")
            continue
        if not path.is_file():
            errors.append(f"Missing: {relative}")
            continue
        data = path.read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            errors.append(f"Digest/size mismatch: {relative}")
        counts["files"] += 1
        try:
            if path.suffix == ".json":
                json.loads(data, parse_constant=reject_constant)
                counts["json"] += 1
            elif path.suffix == ".py":
                ast.parse(data.decode(), filename=relative)
                counts["python"] += 1
            elif path.suffix == ".md":
                counts["markdown"] += 1
        except (ValueError, SyntaxError, UnicodeError) as exc:
            errors.append(f"Parse error {relative}: {exc}")
    required = ["README.md", "PRO_RESEARCH_SYNTHESIS_2026-10-06.md",
                "EVIDENCE_FAMILY_PIT_READINESS_2026-10-06.md",
                "EMERGENCE_MATCHED_STUDY_2026-10-06.md",
                "IGNITION_INTERACTION_STUDY_2026-10-06.md",
                "OPERATIONAL_LEAD_TIME_CENSUS_2026-10-06.md",
                "R6_IMPLEMENTATION_DECISION_2026-10-06.md"]
    for relative in required:
        if relative not in manifest["files"]:
            errors.append(f"Required report absent from manifest: {relative}")
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "verified": counts,
                      "errors": errors, "scope": "research package integrity; not production or predictive validation"}, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
