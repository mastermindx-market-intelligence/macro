#!/usr/bin/env python3
"""Validate W1 alias/equivalence normalization without reading outcomes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PASSPORTS = ROOT / "research/technical_opportunity/w1_method_passports.jsonl"
EQUIV = ROOT / "research/technical_opportunity/w1_alias_equivalence.json"
REL = {"first_class", "parameter_variant", "alias", "algebraic_duplicate", "behavioral_duplicate", "subtype"}


def _methods() -> tuple[set[str], dict[str, str]]:
    ids: set[str] = set()
    aliases: dict[str, str] = {}
    for n, line in enumerate(PASSPORTS.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        mid = row["method_id"]
        if mid in ids:
            raise ValueError(f"duplicate method_id at line {n}: {mid}")
        ids.add(mid)
        for alias in row["aliases"]:
            key = alias.casefold().strip()
            prior = aliases.get(key)
            if prior is not None and prior != mid:
                raise ValueError(f"alias collision {alias!r}: {prior} vs {mid}")
            aliases[key] = mid
    return ids, aliases


def validate(payload: dict[str, Any], ids: set[str], passport_aliases: dict[str, str]) -> dict[str, Any]:
    if payload.get("schema_version") != "toi.alias_equivalence.v1":
        raise ValueError("wrong equivalence schema")
    classes = payload.get("classes")
    index = payload.get("alias_index")
    unresolved = payload.get("unresolved")
    if not isinstance(classes, list) or not isinstance(index, dict) or not isinstance(unresolved, list):
        raise ValueError("classes/alias_index/unresolved shape invalid")
    seen_class: set[str] = set()
    memberships: dict[str, int] = {}
    for cls in classes:
        cid = cls.get("class_id")
        canonical = cls.get("canonical_method_id")
        members = cls.get("members")
        if not isinstance(cid, str) or not cid or cid in seen_class:
            raise ValueError(f"invalid/duplicate class_id {cid!r}")
        seen_class.add(cid)
        if canonical not in ids or not isinstance(members, list) or not members:
            raise ValueError(f"{cid}: invalid canonical or empty members")
        member_ids: list[str] = []
        first = 0
        for member in members:
            mid = member.get("method_id")
            relationship = member.get("relationship")
            if mid not in ids or relationship not in REL:
                raise ValueError(f"{cid}: invalid member {member!r}")
            if mid in member_ids:
                raise ValueError(f"{cid}: duplicate member {mid}")
            member_ids.append(mid)
            memberships[mid] = memberships.get(mid, 0) + 1
            first += int(relationship == "first_class")
        if canonical not in member_ids or first != 1:
            raise ValueError(f"{cid}: canonical must be a member and exactly one first_class is required")
    duplicated = sorted(mid for mid, count in memberships.items() if count != 1)
    missing = sorted(ids - memberships.keys())
    if duplicated or missing:
        raise ValueError(f"equivalence membership mismatch duplicated={duplicated} missing={missing}")
    normalized_index: dict[str, str] = {}
    for alias, mid in index.items():
        if not isinstance(alias, str) or mid not in ids:
            raise ValueError(f"bad alias index row {alias!r} -> {mid!r}")
        key = alias.casefold().strip()
        if key in normalized_index and normalized_index[key] != mid:
            raise ValueError(f"case-insensitive alias collision {alias!r}")
        normalized_index[key] = mid
    for alias, mid in passport_aliases.items():
        if normalized_index.get(alias) != mid:
            raise ValueError(f"passport alias missing/misresolved: {alias!r} -> {mid}")
    return {"status": "valid", "method_count": len(ids), "class_count": len(classes), "alias_count": len(index), "unresolved_count": len(unresolved)}


def main() -> int:
    ids, aliases = _methods()
    payload = json.loads(EQUIV.read_text(encoding="utf-8"))
    print(json.dumps(validate(payload, ids, aliases), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
