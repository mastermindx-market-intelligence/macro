#!/usr/bin/env python3
"""Validate W1 source receipts and passport source/rights bindings."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PASSPORTS = ROOT / "research/technical_opportunity/w1_method_passports.jsonl"
SOURCES = ROOT / "research/technical_opportunity/w1_source_receipts.json"
RIGHTS = {"public_formula", "open_source_parity_only", "licensed", "opaque", "blocked"}
SOURCE_TYPES = {
    "official_open_source_documentation", "creator_official_documentation",
    "official_platform_formula_documentation", "primary_academic",
    "primary_academic_official", "public_practitioner_methodology",
    "internal_rights_record",
}
PRIMARY_OR_OFFICIAL_SOURCE_TYPES = {
    "official_open_source_documentation", "creator_official_documentation",
    "official_platform_formula_documentation", "primary_academic",
    "primary_academic_official",
}


def validate_sources(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if payload.get("schema_version") != "toi.source_receipts.v1":
        raise ValueError("wrong source-receipt schema")
    receipts = payload.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("source receipts empty")
    out: dict[str, dict[str, Any]] = {}
    for row in receipts:
        if not isinstance(row, dict):
            raise ValueError("source receipt must be object")
        ref = row.get("source_ref")
        if not isinstance(ref, str) or not ref or ref in out:
            raise ValueError(f"invalid/duplicate source_ref {ref!r}")
        if row.get("source_type") not in SOURCE_TYPES:
            raise ValueError(f"{ref}: invalid source_type")
        if row.get("rights_class") not in RIGHTS:
            raise ValueError(f"{ref}: invalid rights_class")
        if not isinstance(row.get("url"), str) or not row["url"]:
            raise ValueError(f"{ref}: missing URL/path")
        if not isinstance(row.get("rights_ref"), str) or not row["rights_ref"]:
            raise ValueError(f"{ref}: missing rights_ref")
        if not isinstance(row.get("covers"), list) or not row["covers"]:
            raise ValueError(f"{ref}: empty covers")
        out[ref] = row
    return out


def validate_passport_bindings(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    count = 0
    p0p1 = 0
    for n, line in enumerate(PASSPORTS.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        count += 1
        mid = row["method_id"]
        refs = row.get("source_refs") or []
        missing = sorted(ref for ref in refs if ref not in sources)
        if missing:
            raise ValueError(f"{mid}: unresolved source_refs {missing}")
        if row.get("research_priority") in {"P0", "P1"}:
            p0p1 += 1
            if not refs:
                raise ValueError(f"{mid}: P0/P1 requires a source")
            acceptable = [sources[ref] for ref in refs if sources[ref]["source_type"] in PRIMARY_OR_OFFICIAL_SOURCE_TYPES]
            if not acceptable:
                raise ValueError(f"{mid}: P0/P1 lacks primary/official source")
        rights_class = row.get("rights_class")
        rights_ref = row.get("rights_ref")
        if rights_class in {"licensed", "open_source_parity_only"} and not rights_ref:
            raise ValueError(f"{mid}: rights receipt required")
        if rights_class == "licensed" and rights_ref not in sources and not str(rights_ref).startswith("research/"):
            raise ValueError(f"{mid}: licensed rights_ref is not receipted")
        if rights_class in {"opaque", "blocked"} and row.get("owner_disposition") != "blocked":
            raise ValueError(f"{mid}: opaque/blocked source must be blocked from active ownership")
    return {"status": "valid", "passport_count": count, "p0_p1_count": p0p1, "source_count": len(sources)}


def main() -> int:
    sources = validate_sources(json.loads(SOURCES.read_text(encoding="utf-8")))
    print(json.dumps(validate_passport_bindings(sources), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
