#!/usr/bin/env python3
"""Reproduce the pinned FIF evidence-binding diagnostic without changing source.

Run only against a trusted isolated snapshot, never a live production checkout.
--hypothesis adds a process-local canonical-equality wrapper; it is NOT a repair.
The script writes JSON to stdout, disables bytecode writes and blocks socket
connections during the experiment. It does not acquire sources or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone

PIN = "44a45369617dbbd0afdcf161682679640352a554"
BLOBS = {
    "engine/fundamental_forensics/query.py": "529d9e7df8e6183848fea0a37280e938c0bd9238",
    "engine/fundamental_forensics/lineage_evidence.py": "2aaac83a73121e55e38f07c1a7b8228691875149",
}
ENTITY = "ISS:US-XNAS-AAPL"
MUTATIONS = {
    "parent_document_id": "assessment_invalid_parent",
    "child_document_id": "assessment_invalid_child",
    "parent_source_occurrence_keys": ["assessment_invalid_parent_key"],
    "child_source_occurrence_keys": ["assessment_invalid_child_key"],
    "dimensions_known": False,
    "parent_accepted_at": "2000-01-01T00:00:00Z",
    "child_accepted_at": "2000-01-01T00:00:00Z",
    "parent_recorded_at": "2000-01-01T00:00:00Z",
    "child_recorded_at": "2000-01-01T00:00:00Z",
    "concept_qname": "us-gaap:Liabilities",
    "parsed_value": "1",
    "decimals": 0,
    "parent_taxonomy_uri": "https://invalid.example/us-gaap",
    "parent_accession": "0000000000-00-000000",
}
EXPECTED_OMISSIONS = set(list(MUTATIONS)[:9])


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def verify_snapshot(root: Path) -> None:
    marker = root / "ASSESSMENT_PIN.txt"
    if marker.is_file():
        observed = marker.read_text().strip()
    else:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        observed = result.stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        if dirty.stdout.strip():
            raise ValueError("Use a clean isolated checkout or verified snapshot")
    if observed != PIN:
        raise ValueError(f"Snapshot pin differs from required {PIN}")
    for name, expected in BLOBS.items():
        if git_blob((root / name).read_bytes()) != expected:
            raise ValueError(f"Pinned source differs: {name}; do not reuse old expectations")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--hypothesis", action="store_true")
    args = parser.parse_args()
    root = args.repo.expanduser().resolve(strict=True)
    verify_snapshot(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))

    def deny_network(event, _args):
        if event in {"socket.connect", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("Diagnostic network access is forbidden")

    sys.addaudithook(deny_network)
    proof_owner = None
    original_proof = None
    try:
        from engine.fundamental_forensics.ixbrl_raw_ledger import GoldenAaplFinancialQueryProvider
        from engine.fundamental_forensics.query_service import execute_financial_query
        from engine.fundamental_forensics.query import BitemporalMetricQueryEngine
        from engine.fundamental_forensics.lineage_evidence import _positive_evidence_payload

        provider = GoldenAaplFinancialQueryProvider(
            root, lineage_evidence_available_at=datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
        )
        dataset = provider.resolve(ENTITY)
        target = next(r for r in dataset.lineage_evidence
                      if r.positive_evidence["concept_qname"] == "us-gaap:Assets")

        class InMemoryProvider:
            def __init__(self, data):
                self.data = data

            def resolve(self, entity_id: str):
                if entity_id != ENTITY:
                    raise ValueError("Unexpected diagnostic issuer")
                return self.data

        def query(current_provider, selection="latest_known_as_of",
                  source="2026-09-20T00:00:00Z", recorded="2026-09-20T00:00:00Z"):
            body = {
                "schema": "fundamental_forensics.financial_query_request/v1",
                "entity_id": ENTITY,
                "policy": {"selection": selection, "source_snapshot_at": source,
                           "recorded_at": recorded},
                "metric_ids": ["total_assets"],
                "periods": [{"kind": "instant", "start": None,
                             "end": "2025-09-27", "label": "2025-09-27"}],
            }
            try:
                result = execute_financial_query(body=json.dumps(body).encode(),
                                                 provider=current_provider)
                env = result.envelope
                roots = set(env["receipt"]["root_cell_ids"])
                cell = next(n for n in env["receipt"]["nodes"] if n["cell_id"] in roots)
                return {"state": cell.get("state"), "value": cell.get("value"),
                        "sha256": result.sha256, "lineage": env.get("lineage")}
            except Exception as exc:
                return {"error": type(exc).__name__}

        policies = {
            "latest": {}, "as_reported": {"selection": "as_reported"},
            "latest_restated": {"selection": "latest_restated"},
            "pre_lineage": {"source": "2026-08-01T00:00:00Z",
                            "recorded": "2026-08-23T12:00:00Z"},
        }
        compact = lambda d: {k: v for k, v in d.items() if k != "lineage"}
        before = {name: compact(query(provider, **kw)) for name, kw in policies.items()}
        if before["latest"].get("value") != "359241000000":
            raise ValueError("Golden baseline failed; do not interpret mutation trials")

        if args.hypothesis:
            proof_owner = BitemporalMetricQueryEngine
            original_proof = proof_owner._receipt_still_proves_confirmation

            def hypothesis(self, receipt, policy):
                if not original_proof(self, receipt, policy):
                    return False
                parent = self._event_by_occurrence_id[receipt.parent_occurrence_id]
                child = self._event_by_occurrence_id[receipt.child_occurrence_id]
                evidence = dict(receipt.positive_evidence or {})
                expected = _positive_evidence_payload(
                    self._visible_accession_group(parent, policy),
                    self._visible_accession_group(child, policy),
                    parent_taxonomy_uri=evidence["parent_taxonomy_uri"],
                    child_taxonomy_uri=evidence["child_taxonomy_uri"],
                )
                return evidence == expected

            proof_owner._receipt_still_proves_confirmation = hypothesis

        rows = []
        for name, value in MUTATIONS.items():
            evidence = dict(target.positive_evidence)
            if name not in evidence or evidence[name] == value:
                raise ValueError(f"Mutation is missing or not distinct: {name}")
            evidence[name] = value
            forged = replace(target, positive_evidence=evidence,
                             receipt_id="", evidence_digest="")
            changed = replace(dataset, lineage_evidence=tuple(
                forged if old.receipt_id == target.receipt_id else old
                for old in dataset.lineage_evidence
            ))
            observed = query(InMemoryProvider(changed))
            disclosed = forged.receipt_id in json.dumps(observed.get("lineage"), default=str)
            accepted = observed.get("state") == "value" and disclosed
            rows.append({"field": name, "rehash_changed": forged.receipt_id != target.receipt_id,
                         "accepted_and_disclosed": accepted, "observed": compact(observed)})
        after = {name: compact(query(provider, **kw)) for name, kw in policies.items()}
        accepted_fields = {r["field"] for r in rows if r["accepted_and_disclosed"]}
        valid = before == after and all(r["rehash_changed"] for r in rows)
        valid = valid and (not accepted_fields if args.hypothesis
                           else accepted_fields == EXPECTED_OMISSIONS)
        print(json.dumps({
            "source_pin": PIN, "mode": "hypothesis" if args.hypothesis else "diagnosis",
            "meaning": "Diagnostic reproduction, NOT product acceptance or source repair",
            "events": len(dataset.ledger.events), "genuine_receipts": len(dataset.lineage_evidence),
            "delivery": dict(dataset.delivery), "before": before, "after": after,
            "mutations": rows, "expected_diagnostic_behavior_observed": valid,
            "source_files_changed": False, "production_calls": False,
        }, indent=2))
        return 0 if valid else 1
    finally:
        if proof_owner is not None and original_proof is not None:
            proof_owner._receipt_still_proves_confirmation = original_proof


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"diagnostic_error": type(exc).__name__, "detail": str(exc)}),
              file=sys.stderr)
        raise SystemExit(2)
