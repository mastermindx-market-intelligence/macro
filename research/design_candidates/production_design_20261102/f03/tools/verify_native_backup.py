#!/usr/bin/env python3
"""Read-only, fail-closed Paper full-file clone comparison for F03.

This verifier does not create, open, modify, restore, or delete Paper files.
It cannot certify native backup fidelity from metadata or synthetic receipts.
Actual original-carrier, vendor, canary, history and restore acceptance remain
separate gates after structural preflight.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FILE_ID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}\Z")
PAGE_ID = re.compile(r"p-[A-Za-z0-9-]{1,30}\Z")
REQUIRED_NATIVE_PROPERTIES = (
    "full_native_tree", "vector_geometry", "styles_and_fonts",
    "embedded_assets", "prototype_links", "comments_and_annotations",
    "sharing_and_permissions", "revision_history", "visual_readback",
    "reopen_and_restore",
)


class EvidenceInvalid(ValueError):
    """Malformed or internally contradictory native readback."""


def _file_record(record: object, label: str) -> tuple[list[tuple], dict]:
    if not isinstance(record, dict):
        raise EvidenceInvalid(f"{label}: record must be an object")
    file_id = record.get("file_id")
    if not isinstance(file_id, str) or not FILE_ID.fullmatch(file_id):
        raise EvidenceInvalid(f"{label}: invalid exact file ID")
    if not isinstance(record.get("file_name"), str) or not record["file_name"].strip():
        raise EvidenceInvalid(f"{label}: file name missing")
    pages = record.get("pages")
    if not isinstance(pages, list) or not pages:
        raise EvidenceInvalid(f"{label}: complete page array required")
    if type(record.get("page_count")) is not int or record["page_count"] != len(pages):
        raise EvidenceInvalid(f"{label}: page count conflicts with array")
    tuples = []
    for row in pages:
        if (not isinstance(row, dict) or row.get("type") != "page"
                or not isinstance(row.get("id"), str)
                or not PAGE_ID.fullmatch(row["id"])
                or not isinstance(row.get("name"), str)
                or not row["name"].strip()
                or (row.get("icon") is not None and not isinstance(row["icon"], str))):
            raise EvidenceInvalid(f"{label}: unsupported page or divider schema")
        tuples.append((row["id"], row["name"], row.get("icon")))
    if len({x[0] for x in tuples}) != len(tuples):
        raise EvidenceInvalid(f"{label}: duplicate page IDs")
    tokens = record.get("tokens_hash")
    if not isinstance(tokens, str) or not re.fullmatch(r"[0-9a-fA-F]{8,64}", tokens):
        raise EvidenceInvalid(f"{label}: token digest missing")
    warnings = record.get("warnings")
    if not isinstance(warnings, list) or any(not isinstance(x, str) for x in warnings):
        raise EvidenceInvalid(f"{label}: warnings must be retained verbatim")
    return tuples, record


def evaluate_pair(pair: object) -> dict:
    """Compare native metadata and report explicit unmet fidelity gates.

    A good metadata comparison is NEVER interpreted as restore acceptance.
    """
    if not isinstance(pair, dict) or pair.get("kind") != "F03_native_file_pair_readback_v1":
        raise EvidenceInvalid("unrecognized readback kind")
    source_pages, src = _file_record(pair.get("source"), "source")
    clone_pages, dst = _file_record(pair.get("candidate"), "candidate")
    if src["file_id"] == dst["file_id"]:
        raise EvidenceInvalid("candidate is the original file")
    source_ids = [p[0] for p in source_pages]
    candidate_ids = [p[0] for p in clone_pages]
    missing = [p for p in source_ids if p not in set(candidate_ids)]
    extras = [p for p in candidate_ids if p not in set(source_ids)]
    tokens_match = src["tokens_hash"] == dst["tokens_hash"]
    same_page_ids_in_order = source_ids == candidate_ids
    exact_page_metadata_match = source_pages == clone_pages
    oversize_warning = any("file is too large" in w.lower() or "data loss" in w.lower()
                           for w in src["warnings"])
    blockers = []
    if missing:
        blockers.append("MISSING_SOURCE_PAGES")
    if extras:
        blockers.append("CANDIDATE_HAS_UNKNOWN_PAGES")
    if not same_page_ids_in_order:
        blockers.append("PAGE_IDS_OR_ORDER_DIFFER")
    if not exact_page_metadata_match:
        blockers.append("PAGE_NAMES_ICONS_OR_ORDER_DIFFER")
    if not tokens_match:
        blockers.append("TOKEN_HASH_DIFFERS")
    if oversize_warning:
        blockers.append("ORIGINAL_OVERSIZE_DATA_LOSS_WARNING")
    # Metadata, even when equal, contains none of these property-level checks.
    blockers.extend("UNVERIFIED_" + key.upper() for key in REQUIRED_NATIVE_PROPERTIES)
    blockers.extend(("VENDOR_OVERSIZED_CLONE_SAFETY_NOT_ATTESTED",
                     "NATIVE_RESOURCE_WRITE_CARRIER_NOT_AUTHORIZED",
                     "HARMLESS_SCRATCH_CANARY_NOT_PROVEN"))
    return {
        "kind": "F03_native_backup_fail_closed_assessment_v1",
        "decision": "HOLD_NOT_A_NATIVE_BACKUP",
        "original_file_id": src["file_id"],
        "candidate_file_id": dst["file_id"],
        "source_page_count": len(source_pages),
        "candidate_page_count": len(clone_pages),
        "missing_source_page_ids": missing,
        "unexpected_candidate_page_ids": extras,
        "ordered_page_ids_equal": same_page_ids_in_order,
        "page_metadata_equal": exact_page_metadata_match,
        "token_hash_equal_not_sufficient": tokens_match,
        "original_oversize_warning": oversize_warning,
        "unverified_native_properties": list(REQUIRED_NATIVE_PROPERTIES),
        "blockers": blockers,
        "paper_mutations": 0,
        "restore_test_executed": False,
        "physical_reorganization_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("readback", type=Path, help="Immutable normalized native read-only pair")
    parser.add_argument("--require-restored", action="store_true",
                        help="Exit nonzero unless an independently certified restore exists")
    args = parser.parse_args()
    try:
        if args.readback.stat().st_size > 4_000_000:
            raise EvidenceInvalid("readback file exceeds bounded size")
        result = evaluate_pair(json.loads(args.readback.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"decision": "INVALID_EVIDENCE", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 3 if args.require_restored else 0


if __name__ == "__main__":
    raise SystemExit(main())
