"""Validate design-document invariants, not Mastermind product behavior.

Run from a checkout: python research/mining/check_mining_design.py
Or beside the portable spec: python check_mining_design.py
Standard library only; no network, native data, application imports or trading.
Writes one adjacent receipt. Source interpretations require human/principal review.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
SPEC_NAME = "2026-09-24-mining-shared-foundation-economic-dossier-design.md"
REPO_SPEC = ROOT.parent.parent / "docs" / "superpowers" / "specs" / SPEC_NAME
SPEC = REPO_SPEC if REPO_SPEC.is_file() else ROOT / SPEC_NAME
RECEIPT = ROOT / "MINING_SHARED_FOUNDATION_DESIGN_CHECKS_2026-09-24.json"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def inspect(text: str) -> dict[str, bool]:
    ids = re.findall(r"^\| (MGD-\d{2}) \|", text, re.M)
    refs = re.findall(r"^\| (N\d{2}) \|", text, re.M)
    return {
        "forty_unique_release_obligations": ids == [f"MGD-{i:02}" for i in range(1, 41)],
        "sixteen_ordered_source_records": refs == [f"N{i:02}" for i in range(1, 17)],
        "source_reference_ids_resolve": set(re.findall(r"\bN\d{2}\b", text)) == set(refs),
        "proposed_not_implemented": "**Status:** DESIGN_PROPOSED / IMPLEMENTATION_HELD. Mission complete: false." in text,
        "same_mining_operation_and_carrier": all(x in text for x in ("gmi-mining-principal-research-20260923-sol-001", "#7795", "sol/mining-principal-research-20260923")),
        "immutable_source_pins_present": all(x in text for x in ("0497e28864752e3ab70fa5aa2f1567bc3c9c6aca", "14587e506d3e03c6064086abd417a87d2cafc0da", "45eb37bbf832e007e67ce2594674d6bfeeb3b880")),
        "two_named_positive_witnesses": "### W-C:" in text and "### W-R:" in text,
        "actual_enrollment_gap_visible": "not Freeport or MP Materials" in text and "Not in the inspected production registry" in text,
        "no_financial_sign_workaround": "Never take the absolute value" in text,
        "same_horizon_distinction_visible": "same-horizon guidance revisions" in text and "must not be relabeled as next-quarter guidance" in text,
        "copper_proxy_distinction_visible": "opening a reshoring basket alone is not acceptance" in text,
        "future_handoff_not_issued": "Final Fable implementation packet: not issued." in text and "This amendment is design guidance, not a worker assignment" in text,
    }


def main() -> None:
    raw = SPEC.read_bytes()
    text = raw.decode("utf-8")
    checks = inspect(text)
    mutations = {
        "missing_release_obligation": (text.replace("| MGD-40 |", "| OMITTED-40 |", 1), "forty_unique_release_obligations"),
        "false_implementation_status": (text.replace("DESIGN_PROPOSED / IMPLEMENTATION_HELD", "DESIGN_ACCEPTED / IMPLEMENTATION_READY", 1), "proposed_not_implemented"),
        "missing_native_admission_gap": (text.replace("not Freeport or MP Materials", "witness admission not specified", 1), "actual_enrollment_gap_visible"),
    }
    traps = {name: not inspect(candidate)[expected] for name, (candidate, expected) in mutations.items()}
    receipt = {
        "operation": "gmi-mining-principal-research-20260923-sol-001",
        "classification": "DESIGN_DOCUMENT_INVARIANTS_AND_SELF_REVIEW_ONLY",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python research/mining/check_mining_design.py" if SPEC == REPO_SPEC else "python check_mining_design.py",
        "layout": "repository" if SPEC == REPO_SPEC else "portable",
        "document": SPEC.name,
        "document_words": len(text.split()),
        "document_bytes": len(raw),
        "document_sha256": hashlib.sha256(raw).hexdigest(),
        "document_git_blob_sha1": git_blob(raw),
        "checker_git_blob_sha1": git_blob(Path(__file__).read_bytes()),
        "checks": checks,
        "passed": sum(checks.values()),
        "failed": sum(not x for x in checks.values()),
        "mutated_documents_rejected": traps,
        "self_review": [
            {"finding": "Initial checker assumed the spec was beside it, unlike the committed repository layout.", "resolution": "Repository-layout FileNotFoundError reproduced after initial checker publication; lookup now prefers the canonical docs/superpowers/specs path and supports the flat portable package. Both layouts are checked before final publication.", "source": "local verification utility only"},
            {"finding": "Shared implementation is not only an old research packet.", "resolution": "#7870 source pinned separately from #7780 plan and main; no runtime or production acceptance inferred.", "source": "N01,N06,N09"},
            {"finding": "Generic physical-quantity observation rejects signed financial values.", "resolution": "Retain shared guard and use native financial objects; schema support does not imply issuer/metric coverage.", "source": "N02,N03,N07"},
            {"finding": "Annual outlook revision does not fit the later-period history call.", "resolution": "Keep same-horizon native-owner qualification explicit; do not falsify period or add a local history engine.", "source": "N04"},
            {"finding": "Two null optional bases do not independently prove comparable economics.", "resolution": "Require upstream native input qualification; recorded as a consumer precondition, not an unproven global helper defect.", "source": "N04"},
            {"finding": "Copper theme lacks a primary basket.", "resolution": "Require theme-level shared entry; do not relabel the reshoring proxy or mint theme:mining.", "source": "N10"},
            {"finding": "Chosen Company witnesses are absent from the inspected production registry.", "resolution": "Added concrete witness-admission inventory; no global financial-data absence claimed.", "source": "N15,N16"},
            {"finding": "Economic-right clauses and actual stream thresholds are not typed ready inputs.", "resolution": "Keep source-attributed descriptive case; hold settlement computation until accepted owner extension and actual inputs.", "source": "N02,N03,N14"},
            {"finding": "Private-path classification is not live private admission or rights acceptance.", "resolution": "Retain #7870 R4 and incumbent binding/rights gates; no fallback store or public payload.", "source": "N01,N05,N06"},
            {"finding": "#7669 body and metadata disagree about the candidate head.", "resolution": "Preserve the mismatch and its source-owner gate; do not choose a head or displace custody.", "source": "N12"},
            {"finding": "Two first-release witnesses could be mistaken for full mission completion.", "resolution": "Preserve eight-pass corpus and broader research/coverage obligations; M1 is explicitly bounded.", "source": "N14"},
        ],
        "unverified": ["upstream module execution", "application tests", "current CI", "independent review", "private-source admission", "witness data availability outside inspected registry", "native derivation receipts", "browser proof", "design acceptance", "Fable dispatch", "implementation or investment validation"],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": receipt["passed"], "failed": receipt["failed"], "mutation_traps": traps, "document_words": receipt["document_words"], "document_bytes": len(raw), "document_sha256": receipt["document_sha256"], "document_git_blob_sha1": receipt["document_git_blob_sha1"], "checker_git_blob_sha1": receipt["checker_git_blob_sha1"], "receipt_git_blob_sha1": git_blob(RECEIPT.read_bytes())}, indent=2))
    if not all(checks.values()) or not all(traps.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
