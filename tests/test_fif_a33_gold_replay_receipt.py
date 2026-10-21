"""A33 receipt guard: the recorded G-pack gold replay covers every committed pack.

Z0 closure-matrix row A33 owes a ``ci_proof`` that the kernel-vs-gold replays in
``tests/test_fif_g_pack_kernel.py`` and ``tests/test_fif_g_pack_gold.py`` execute
(not skip) over the four committed G-packs when ``FIF_GSRC_STAGE_ROOT`` names a
stage root. The staged SEC bytes never enter git, so the proof is the receipt
committed at ``research/financial_intelligence_fabric/``
``FIF_A33_GOLD_REPLAY_RECEIPT_2026-10-20.json`` plus this guard, which pins the
receipt to the committed packs. Hermetic: no marker, no env, no network, no
stage access — the module must pass with ``FIF_GSRC_STAGE_ROOT`` unset.

Every kernel group is either executed (PASSED) or an XFAIL the pack's own
``defects[]`` ledger turned into an expected failure; a group that appears in
neither list is a coverage hole in the recorded run.
"""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    REPO_ROOT
    / "research/financial_intelligence_fabric/FIF_A33_GOLD_REPLAY_RECEIPT_2026-10-20.json"
)
PACK_ROOT = REPO_ROOT / "tests" / "fixtures" / "fundamental_forensics" / "g_pack"
KERNEL_TEST_PATH = REPO_ROOT / "tests" / "test_fif_g_pack_kernel.py"
KERNEL_NODE_PREFIX = "tests/test_fif_g_pack_kernel.py::test_kernel_cells_match_gold_cells["
GOLD_NODE_ID = (
    "tests/test_fif_g_pack_gold.py::test_staged_bytes_match_gold_cells_and_pins"
)
FORBIDDEN_TICKERS = ("SNOW", "CAT", "BAC", "GOOGL", "AAPL")


def _load_receipt() -> dict:
    return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def _load_manifests() -> dict[str, dict]:
    manifests = {}
    for pack_dir in sorted(PACK_ROOT.iterdir()):
        manifest_path = pack_dir / "pack_manifest.json"
        if manifest_path.is_file():
            manifests[pack_dir.name] = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
    return manifests


def _kernel_group_params() -> list[str]:
    spec = importlib.util.spec_from_file_location(
        "fif_g_pack_kernel_for_a33_receipt", KERNEL_TEST_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [str(param.id) for param in module._group_params()]


def test_a33_receipt_schema_and_counts() -> None:
    receipt = _load_receipt()
    assert receipt["schema"] == "fif.a33_gold_replay_receipt.v1"
    assert receipt["matrix_row"] == "A33"
    assert re.fullmatch(r"[0-9a-f]{40}", receipt["base_commit"])
    recorded_at = datetime.fromisoformat(
        receipt["recorded_at"].replace("Z", "+00:00")
    )
    assert recorded_at.tzinfo is not None
    assert recorded_at.utcoffset() == timezone.utc.utcoffset(None)
    counts = receipt["counts"]
    assert counts["failed"] == 0
    assert counts["skipped"] == 0
    assert counts["errors"] == 0
    assert counts["passed"] == len(receipt["executed"]) > 0
    assert receipt["summary_line"].startswith(f"{counts['passed']} passed")
    assert all(entry["outcome"] == "PASSED" for entry in receipt["executed"])
    assert receipt["stage"]["network"] is False


def test_a33_receipt_covers_every_committed_pack() -> None:
    receipt = _load_receipt()
    manifests = _load_manifests()
    receipt_packs = {pack["cik10"]: pack for pack in receipt["packs"]}
    assert set(receipt_packs) == set(manifests)
    for cik10, manifest in manifests.items():
        pack = receipt_packs[cik10]
        assert pack["admitted_accessions"] == [
            str(accession) for accession in manifest["admitted_accessions"]
        ]
        assert pack["defects"] == len(manifest.get("defects", []))


def test_a33_receipt_executed_every_kernel_group() -> None:
    receipt = _load_receipt()
    executed_ids = {entry["node_id"] for entry in receipt["executed"]}
    recorded_ids = executed_ids | {entry["node_id"] for entry in receipt["xfailed"]}
    for group_id in _kernel_group_params():
        assert KERNEL_NODE_PREFIX + group_id + "]" in recorded_ids, group_id
    assert GOLD_NODE_ID in executed_ids
    for pack in receipt["packs"]:
        expected = sorted(
            node_id
            for node_id in executed_ids
            if node_id.startswith(KERNEL_NODE_PREFIX + pack["cik10"])
        )
        assert pack["kernel_node_ids"] == expected


def test_a33_receipt_carries_no_path_or_identity() -> None:
    text = RECEIPT_PATH.read_text(encoding="utf-8")
    for forbidden in ("/home/", "/Users/", "~/", "lanes/stage"):
        assert forbidden not in text, forbidden
    for ticker in FORBIDDEN_TICKERS:
        assert not re.search(rf"\b{ticker}\b", text), ticker
    for manifest in _load_manifests().values():
        legal_name = str(manifest.get("legal_name", "")).strip()
        if legal_name:
            assert legal_name not in text, legal_name
