"""FIF Z0 A47: the committed recovery-drill receipts replay hermetically.

Loads the research driver via importlib (research/ is not a package), replays
``run_drill()`` into pytest's ``tmp_path``, and pins the committed receipt's
deterministic fields: the schema/matrix literals, the seven scenario laws, and
equality of every field except ``recorded_at`` (the single wall-clock field,
written by ``main()`` alone). Local-directory stores only; no marker, no env,
no network, nothing outside the tree.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = (
    ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "fif_a47_recovery_drill_receipts.py"
)
RECEIPT_PATH = (
    ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "FIF_A47_RECOVERY_DRILL_RECEIPTS_2026-10-20.json"
)
SCENARIO_ORDER = [
    "publish_g1",
    "restart",
    "backup",
    "lost_publication",
    "restore",
    "rollback_refused",
    "corrupted_target",
]
REWIND_REFUSAL_MESSAGE = "stale production dataset cannot rewind independent latest pointer"


def _load_driver():
    spec = importlib.util.spec_from_file_location(
        "fif_a47_recovery_drill_receipts", DRIVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _receipt() -> dict:
    return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def _steps(scenario: dict) -> dict:
    return {step["step"]: step for step in scenario["steps"]}


def test_a47_receipt_schema() -> None:
    doc = _receipt()
    text = RECEIPT_PATH.read_text(encoding="utf-8")

    assert doc["schema"] == "fif.a47_recovery_drill_receipts.v1"
    assert doc["matrix_row"] == "A47"
    assert doc["store_kind"] == "local_directory"
    assert doc["production_touched"] is False
    assert doc["network"] is False
    assert doc["issuer_id"] == "mmx.issuer.fip1"
    assert re.fullmatch(r"[0-9a-f]{40}", doc["base_commit"])

    stamp = datetime.fromisoformat(doc["recorded_at"])
    assert stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0)

    assert [s["scenario"] for s in doc["scenarios"]] == SCENARIO_ORDER
    for banned in ("/home/", "/Users/", "~/", "lanes/tmp"):
        assert banned not in text


def test_a47_replay_matches_committed_receipt(tmp_path: Path) -> None:
    driver = _load_driver()
    fresh = driver.run_drill(tmp_path)
    committed = driver._strip_run_local(_receipt())
    committed.pop("recorded_at", None)  # the single wall-clock field (main() only)
    assert fresh == committed


def test_a47_every_scenario_asserts_its_law() -> None:
    doc = _receipt()
    g1 = doc["generations"]["g1"]
    g2 = doc["generations"]["g2"]
    by_name = {s["scenario"]: s for s in doc["scenarios"]}

    # publish_g1: one admitted generation in the source local store.
    publish = _steps(by_name["publish_g1"])["publish_g1"]
    assert publish["assert"]["generation_id"] == g1

    # restart: a NEW store object over the same directory serves the same
    # generation; the CLI audit admits it.
    restart = _steps(by_name["restart"])
    summary = restart["reopen_store_object"]["assert"]["summary"]
    assert summary["dataset_generation_id"] == g1
    assert summary["admitted_at"].startswith("2026-10-01T00:00:00")
    audit = restart["audit"]
    assert audit["exit_code"] == 0
    assert audit["stdout"]["state"] == "admitted"
    assert audit["assert"]["generation_id"] == g1

    # backup: the CLI captured exactly the admitted G1.
    backup = _steps(by_name["backup"])["backup"]
    assert backup["exit_code"] == 0
    assert backup["assert"]["generation_id"] == g1
    assert backup["assert"]["entries"] == backup["stdout"]["entries"] > 0
    assert backup["assert"]["manifest_path"] == "backup/manifest.json"
    assert re.fullmatch(r"[0-9a-f]{64}", backup["assert"]["manifest_sha256"])
    assert backup["assert"]["objects"] == backup["assert"]["entries"]

    # lost publication: the audit demands a publisher repoint and writes none.
    lost = _steps(by_name["lost_publication"])
    assert lost["publish_skip_pointer"]["assert"] == {
        "generation_id": g1,
        "skip_pointer": True,
        "pointer_key_absent": True,
    }
    lost_audit = lost["audit"]
    assert lost_audit["exit_code"] == 1
    assert lost_audit["stdout"]["state"] == "pointer_absent_generation_present"
    assert lost_audit["stdout"]["recovery"] == "publisher_repoint_required"
    assert lost_audit["stdout"]["generation_id"] is None
    assert lost_audit["stdout"]["manifest_generation_ids"] == [g1]
    assert lost_audit["assert"]["pointer_key_absent_after_audit"] is True

    # restore: verified into a fresh target, then idempotent — the second
    # restore writes nothing and finds every immutable entry already present.
    restore_steps = _steps(by_name["restore"])
    first = restore_steps["restore"]
    assert first["exit_code"] == 0
    assert first["stdout"]["verified"] is True
    assert first["stdout"]["pointer"] == "restored"
    assert first["stdout"]["already_present"] == []
    assert (
        first["assert"]["entries_written_by_restore"]
        == first["assert"]["immutable_entry_count"]
        > 0
    )
    target_audit = restore_steps["audit_restored_target"]
    assert target_audit["exit_code"] == 0
    assert target_audit["stdout"]["state"] == "admitted"
    assert target_audit["stdout"]["generation_id"] == g1
    again = restore_steps["restore_again"]
    assert again["exit_code"] == 0
    assert again["stdout"]["verified"] is True
    assert again["stdout"]["pointer"] == "kept_existing"
    assert again["stdout"]["written"] == []
    assert again["stdout"]["restored"] == []
    assert (
        again["assert"]["already_present_count"]
        == again["assert"]["immutable_entry_count"]
        > 0
    )
    assert again["assert"]["entries_written_by_restore"] == 0

    # rollback: the owner refuses the rewind; the correction is admitted; the
    # originals stay loadable; reconciliation names the other generation; the
    # drill exposes no rewind surface at all.
    rollback = _steps(by_name["rollback_refused"])
    assert rollback["publish_g2"]["assert"] == {"generation_id": g2, "supersedes": g1}
    refused = rollback["rewind_refused"]
    assert refused["exit_code"] == 1
    assert refused["assert"]["raised"] == "ProductionDatasetError"
    assert REWIND_REFUSAL_MESSAGE in refused["assert"]["message"]
    assert refused["assert"]["message"] == refused["stderr_first_line"]
    rollback_audit = rollback["audit_after_rollback"]
    assert rollback_audit["exit_code"] == 0
    assert rollback_audit["stdout"]["state"] == "admitted"
    assert rollback_audit["stdout"]["generation_id"] == g2
    assert rollback["originals_intact"]["assert"]["loadable_generation_ids"] == sorted(
        [g1, g2]
    )
    assert (
        rollback["reconcile_g1"]["assert"]["outcome"] == "pointer_names_other_generation"
    )
    assert rollback["rewind_surface_absent"]["assert"]["rewindish_names"] == []

    # corrupted target: one flipped object byte makes the pointer unverifiable.
    corrupted = _steps(by_name["corrupted_target"])
    corrupt_step = corrupted["corrupt_one_object"]
    assert corrupt_step["assert"]["byte_offset"] == 0
    assert corrupt_step["assert"]["corrupted_key"].startswith(
        "fundamental_forensics/production-datasets/v1/objects/"
    )
    corrupt_audit = corrupted["audit"]
    assert corrupt_audit["exit_code"] == 1
    assert corrupt_audit["stdout"]["state"] == "pointer_unverifiable"
