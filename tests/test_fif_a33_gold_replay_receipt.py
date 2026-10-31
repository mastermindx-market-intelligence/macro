"""A33 receipt guard: the recorded G-pack gold replay covers every committed pack.

Z0 closure-matrix row A33 owes a ``ci_proof`` that the kernel-vs-gold replays in
``tests/test_fif_g_pack_kernel.py`` and ``tests/test_fif_g_pack_gold.py`` execute
(not skip) over the four committed G-packs when ``FIF_GSRC_STAGE_ROOT`` names a
stage root. The staged SEC bytes never enter git, so the proof is the receipt
committed at ``research/financial_intelligence_fabric/``
``FIF_A33_GOLD_REPLAY_RECEIPT_2026-10-20.json`` plus this guard, which pins the
receipt to the committed packs. Hermetic: no marker, no env, no network, no
stage access — the module must pass with ``FIF_GSRC_STAGE_ROOT`` unset.

The executed set and the xfailed set are each pinned EXACTLY, not just their
union. The split is derivable from committed data alone:
``test_kernel_cells_match_gold_cells`` selects each group's defects with
``_defect_in_group`` over the pack manifest's ``defects[]`` ledger, the stale
check forces every selected defect to fire, and a non-empty fired set turns the
group into ``pytest.xfail("pack defects: " + ", ".join(sorted(fired)))``. So a
group is XFAIL exactly when its in-group defect list is non-empty (with the
reason naming exactly those ids), PASSED exactly when that list is empty —
moving a group between the lists cannot satisfy this guard.
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
FORBIDDEN_HOST_TOKENS = re.compile(
    r"ubuntu|debian|fedora|centos|alpine|darwin|macos|linux|windows|uname|hostname"
    r"|mmx-|\.local\b|lane host \(",
    re.IGNORECASE,
)
DISTRO_SUFFIX = re.compile(r"\d+\.\d+\.\d+-\d*[a-z]")


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


def _kernel_module():
    spec = importlib.util.spec_from_file_location(
        "fif_g_pack_kernel_for_a33_receipt", KERNEL_TEST_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _group_expectations() -> tuple[set[str], set[str], dict[str, str], dict[str, list[str]], dict[str, set[str]]]:
    """Derive the exact executed/xfailed split from committed data alone.

    Returns ``(expected_executed, expected_xfailed, expected_reason,
    expected_defect_ids, grouped_defect_ids)`` where the last maps each cik10 to
    the ids of its manifest defects that belong to at least one of its groups.
    """
    module = _kernel_module()
    manifests = _load_manifests()
    expected_executed = {GOLD_NODE_ID}
    expected_xfailed: set[str] = set()
    expected_reason: dict[str, str] = {}
    expected_defect_ids: dict[str, list[str]] = {}
    grouped_defect_ids: dict[str, set[str]] = {}
    for param in module._group_params():
        pack_name, cik10, view, accession = (str(v) for v in param.values)
        in_group = sorted(
            str(entry["id"])
            for entry in manifests[pack_name].get("defects", ())
            if module._defect_in_group(entry, view, accession)
        )
        grouped_defect_ids.setdefault(cik10, set()).update(in_group)
        node_id = KERNEL_NODE_PREFIX + str(param.id) + "]"
        if in_group:
            expected_xfailed.add(node_id)
            expected_reason[node_id] = "pack defects: " + ", ".join(in_group)
            expected_defect_ids[node_id] = in_group
        else:
            expected_executed.add(node_id)
    return (
        expected_executed,
        expected_xfailed,
        expected_reason,
        expected_defect_ids,
        grouped_defect_ids,
    )


def test_a33_receipt_schema_and_counts() -> None:
    receipt = _load_receipt()
    assert receipt["schema"] == "fif.a33_gold_replay_receipt.v2"
    assert receipt["host"] == "fabric lane host"
    assert re.fullmatch(r"\d+\.\d+\.\d+", receipt["python"])
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
    assert counts["xfailed"] == len(receipt["xfailed"])
    assert receipt["summary_line"].startswith(f"{counts['passed']} passed")
    assert all(entry["outcome"] == "PASSED" for entry in receipt["executed"])
    assert all(entry["outcome"] == "XFAIL" for entry in receipt["xfailed"])
    assert receipt["stage"]["network"] is False


def test_a33_receipt_covers_every_committed_pack() -> None:
    receipt = _load_receipt()
    manifests = _load_manifests()
    receipt_packs = {pack["cik10"]: pack for pack in receipt["packs"]}
    assert set(receipt_packs) == set(str(m["cik10"]) for m in manifests.values())
    for pack_dir_name, manifest in manifests.items():
        pack = receipt_packs[str(manifest["cik10"])]
        assert pack["admitted_accessions"] == [
            str(accession) for accession in manifest["admitted_accessions"]
        ]
        assert pack["defects"] == len(manifest.get("defects", []))


def test_a33_receipt_executed_every_kernel_group() -> None:
    receipt = _load_receipt()
    (
        expected_executed,
        expected_xfailed,
        expected_reason,
        expected_defect_ids,
        grouped_defect_ids,
    ) = _group_expectations()
    executed_ids = {entry["node_id"] for entry in receipt["executed"]}
    xfailed_entries = {entry["node_id"]: entry for entry in receipt["xfailed"]}
    assert executed_ids == expected_executed, (
        "executed set differs from the defect-ledger derivation "
        f"(symmetric difference): {sorted(executed_ids ^ expected_executed)}"
    )
    assert set(xfailed_entries) == expected_xfailed, (
        "xfailed set differs from the defect-ledger derivation "
        f"(symmetric difference): {sorted(set(xfailed_entries) ^ expected_xfailed)}"
    )
    for node_id, entry in xfailed_entries.items():
        assert entry["reason"] == expected_reason[node_id], node_id
        assert entry["defect_ids"] == expected_defect_ids[node_id], node_id
    for pack in receipt["packs"]:
        prefix = KERNEL_NODE_PREFIX + pack["cik10"]
        assert pack["kernel_node_ids"] == sorted(
            node_id for node_id in executed_ids if node_id.startswith(prefix)
        ), pack["cik10"]
        assert pack["xfailed_node_ids"] == sorted(
            node_id for node_id in xfailed_entries if node_id.startswith(prefix)
        ), pack["cik10"]
        assert pack["defect_ids_fired"] == sorted(
            {
                defect_id
                for node_id in pack["xfailed_node_ids"]
                for defect_id in xfailed_entries[node_id]["defect_ids"]
            }
        ), pack["cik10"]
        assert set(pack["defect_ids_fired"]) == grouped_defect_ids[pack["cik10"]], (
            pack["cik10"]
        )


def test_a33_receipt_every_ledger_defect_is_grouped() -> None:
    module = _kernel_module()
    manifests = _load_manifests()
    params_by_pack: dict[str, list] = {}
    for param in module._group_params():
        params_by_pack.setdefault(str(param.values[0]), []).append(param)
    ungrouped: dict[str, list[str]] = {}
    for pack_name, manifest in manifests.items():
        missing = sorted(
            str(entry["id"])
            for entry in manifest.get("defects", ())
            if not any(
                module._defect_in_group(entry, param.values[2], param.values[3])
                for param in params_by_pack.get(pack_name, ())
            )
        )
        if missing:
            ungrouped[pack_name] = missing
    assert not ungrouped, (
        "manifest defects no kernel group can ever name "
        f"(no recorded outcome could justify them): {json.dumps(ungrouped, sort_keys=True)}"
    )


def test_a33_receipt_carries_no_path_or_identity() -> None:
    text = RECEIPT_PATH.read_text(encoding="utf-8")
    for forbidden in ("/home/", "/Users/", "~/", "lanes/stage"):
        assert forbidden not in text, forbidden
    for ticker in FORBIDDEN_TICKERS:
        assert not re.search(rf"\b{ticker}\b", text), ticker
    host_token = FORBIDDEN_HOST_TOKENS.search(text)
    assert host_token is None, host_token.group(0) if host_token else None
    assert not DISTRO_SUFFIX.search(text)
    assert _load_receipt()["host"] == "fabric lane host"
    for manifest in _load_manifests().values():
        legal_name = str(manifest.get("legal_name", "")).strip()
        if legal_name:
            assert legal_name not in text, legal_name
