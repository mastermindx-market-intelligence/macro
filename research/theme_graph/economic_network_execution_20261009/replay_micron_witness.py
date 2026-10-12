#!/usr/bin/env python3
"""Replay the bounded real-source witness through the actual file-input CLI.

This research harness makes no network calls, registry changes, publication or
admission. It requires the original, lawfully held source bytes named by the case.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from engine.company_intelligence.relationship_candidates import MAX_SOURCE_BYTES
from engine.earnings_release.receipts import receipt_for_char_span, sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Exact held original UTF-8 HTML")
    args = parser.parse_args()
    case = json.loads(Path(__file__).with_name("MICRON_SOURCE_CASE.json").read_text())
    try:
        with Path(args.source).open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            raise ValueError("SOURCE_LIMIT")
        if sha256_bytes(raw) != case["raw_sha256"] or len(raw) != case["source_bytes"]:
            raise ValueError("SOURCE_CAPTURE_MISMATCH")
        source = raw.decode("utf-8")
        if source.encode("utf-8") != raw:
            raise ValueError("SOURCE_ENCODING")
        receipt = receipt_for_char_span(
            source=source, source_sha256=case["raw_sha256"],
            char_start=case["char_start"], char_end=case["char_end"],
        )
        if (
            receipt.span_sha256 != case["span_sha256"]
            or receipt.byte_start != case["byte_start"]
            or receipt.byte_end != case["byte_end"]
        ):
            raise ValueError("SOURCE_SPAN_MISMATCH")
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({
            "case_id": case["case_id"], "status": "REFUSED",
            "reason": "exact_held_source_capture_or_span_unavailable",
            "admission": "NOT_ADMITTED", "historical_system_replay": False,
        }, sort_keys=True))
        return 2

    candidate = {
        "schema": "company_intelligence.relationship_candidate/v1",
        "candidate_id": case["candidate_id"],
        "document": {
            "document_id": case["document_id"],
            "version": "sha256:" + case["raw_sha256"],
            "source_ref": case["source_url"], "published_date": case["published_date"],
        },
        "dataset_id": None, "temporal_row": None,
        "receipt": receipt.to_dict(), "assertion": case["assertion"],
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix="mmx-relationship-witness-") as directory:
        candidate_path = Path(directory) / "candidate.json"
        candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
        command = [
            sys.executable, "-m", "engine.company_intelligence.relationship_candidates",
            "--candidate", str(candidate_path), "--source", str(Path(args.source).resolve()),
        ]
        for name, extra in (
            ("current", []),
            ("historical", ["--as-of", case["historical_probe"]]),
        ):
            run = subprocess.run(command + extra, cwd=ROOT, capture_output=True,
                                 text=True, timeout=30, check=False)
            outcomes[name] = {
                "exit_code": run.returncode,
                "stderr_empty": not run.stderr,
                "result": json.loads(run.stdout),
            }

    current = outcomes["current"]["result"]
    historical = outcomes["historical"]["result"]
    passed = (
        outcomes["current"]["exit_code"] == 0
        and outcomes["historical"]["exit_code"] == 2
        and all(outcome["stderr_empty"] for outcome in outcomes.values())
        and current["inspection_status"] == "INSPECTABLE"
        and current["current_candidate_view"]["assertion"]["lifecycle"] == "planned"
        and current["current_candidate_view"]["economic_weight"] is None
        and historical["refusal"]["code"] == "AS_OF_REGISTRY_REQUIRED"
        and historical["current_candidate_view"] is None
        and historical["source_provenance"] is None
        and historical["support"] is None
        and all(result["admission"] == "NOT_ADMITTED"
                and result["graph1_projection"] is None
                and not any(result["authority"].values())
                and result["temporal"]["historical_system_replay"] is False
                for result in (current, historical))
    )
    print(json.dumps({
        "schema": "economic_relationship_execution_witness.v1",
        "case_id": case["case_id"], "status": "PASS" if passed else "FAIL",
        "proof_scope": "held_source_to_actual_candidate_inspection_cli",
        "source_sha256": case["raw_sha256"], "outcomes": outcomes,
        "production_admission": False, "served_product_proof": False,
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
