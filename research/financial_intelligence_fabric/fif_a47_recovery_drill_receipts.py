#!/usr/bin/env python3
"""FIF Z0 A47 research-only recovery-drill receipt driver (closure-matrix A47).

Replay tool. Not a runtime provider. Does not import into engine/. Builds the
committed FIP-1 fixture material in LOCAL-DIRECTORY stores under ``--work``
and drives the shipped drill through its CLI (``scripts/fif_recovery_drill.py``)
and public API (``engine.fundamental_forensics/recovery_drill.py``), recording
one receipt entry per scenario: publish, restart, backup, lost publication,
restore (+ idempotent second restore), refused rewind (rollback-as-correction),
and a corrupted restore target. Nothing here touches the production store, R2,
credentials or the network. Research JSON must never be loaded by a
production/query provider. Research scripts may name the fixture identity;
production code may not.

Determinism: generation ids are content-derived (A17) and the owner writes no
wall clock (every timestamp is caller-supplied,
engine/fundamental_forensics/production_datasets.py:33), so every recorded
field replays byte-for-byte on the same tree. ``recorded_at`` is the single
wall-clock field and is added by ``main()`` alone; ``RUN_LOCAL_FIELDS`` lists
any other field that had to be stripped before a replay comparison (none
today). Every path in the receipt is relative to ``--work`` or to the repo
root — the driver scrubs both prefixes out of recorded CLI output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics import recovery_drill as RD
from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    fip1_fixture_dataset,
)

SCHEMA = "fif.a47_recovery_drill_receipts.v1"
MATRIX_ROW = "A47"
BASE_COMMIT = "ec425df59e5141ee78cb6cedab0b6d5a6306f3ee"
ISSUER = "mmx.issuer.fip1"
CLI_SCRIPT = "scripts/fif_recovery_drill.py"
REWIND_REFUSAL_MESSAGE = "stale production dataset cannot rewind independent latest pointer"
# Fields stripped from BOTH documents before the hermetic replay comparison.
# Empty: every recorded field is deterministic on a fixed tree.
RUN_LOCAL_FIELDS: list[str] = []

T_ADMITTED = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
T_FLOOR = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
T_LATER = T_ADMITTED + timedelta(days=2)

# Copied from tests/test_fundamental_forensics_recovery_drill.py:34-47 (not
# imported — tests/ is not a library). Research code may name the fixture.
_FIP1_BINDING = CanonicalEntityBinding(
    entity_id="mmx.issuer.fip1",
    cik="0000999999",
    ticker="FIP1",
    source_entity_id="0000999999",
)
_FIP1_ENTITY = EntityInput(
    entity_id="mmx.issuer.fip1",
    cik="0000999999",
    ticker="FIP1",
    name="FIP1 Fixture",
    identity_basis="sec-cik",
    source_entity_id="0000999999",
)

# Scratch directory names this driver owns under --work; a reused --work is
# reset for exactly these before the drill starts.
_OWNED_WORKDIRS = ("source", "lost", "backup", "target", "corrupt")


def _material(
    *,
    admitted_at: datetime = T_ADMITTED,
    supersedes: str | None = None,
) -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
        binding=_FIP1_BINDING,
        entity=_FIP1_ENTITY,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=admitted_at,
        source_recorded_at_floor=T_FLOOR,
        supersedes_generation=supersedes,
    )


def _local_store(work: Path, name: str):
    directory = work / name
    directory.mkdir(parents=True, exist_ok=True)
    return PDS.build_production_dataset_store(local_dir=directory)


# ---------------------------------------------------------------------------
# Recording helpers: every recorded path is --work-relative or repo-relative.
# ---------------------------------------------------------------------------


def _recorded_arg(work: Path, arg: str) -> str:
    if arg == str(work):
        return "."
    for prefix in (str(work) + os.sep, str(ROOT) + os.sep):
        if arg.startswith(prefix):
            return arg[len(prefix):]
    return arg


def _scrub(work: Path, value: Any) -> Any:
    """Relativize any absolute path the CLI may print into its output."""
    if isinstance(value, str):
        out = value.replace(str(work) + os.sep, "").replace(str(work), ".")
        return out.replace(str(ROOT) + os.sep, "")
    if isinstance(value, list):
        return [_scrub(work, item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(work, item) for key, item in value.items()}
    return value


def _first_line(text: str) -> str | None:
    lines = text.splitlines()
    return lines[0] if lines else None


def _cli_step(work: Path, *, step: str, args: list[str], asserts: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / CLI_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        stdout: Any = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout = None
    return _scrub(
        work,
        {
            "step": step,
            "via": "cli",
            "argv": [CLI_SCRIPT, *(_recorded_arg(work, a) for a in args)],
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr_first_line": _first_line(proc.stderr),
            "assert": asserts,
        },
    )


def _api_step(
    work: Path,
    *,
    step: str,
    argv: list[str],
    asserts: dict,
    exit_code: int = 0,
    stderr_first_line: str | None = None,
) -> dict:
    return {
        "step": step,
        "via": "api",
        "argv": argv,
        "exit_code": exit_code,
        "stdout": None,
        "stderr_first_line": stderr_first_line,
        "assert": asserts,
    }


def _strip_run_local(document: dict) -> dict:
    """Drop RUN_LOCAL_FIELDS (top level) before a replay comparison."""
    return {k: v for k, v in document.items() if k not in RUN_LOCAL_FIELDS}


# ---------------------------------------------------------------------------
# The seven A47 scenarios, in order.
# ---------------------------------------------------------------------------


def run_drill(work: Path) -> dict:
    """Run the whole drill under ``work`` and return the receipt document.

    ``recorded_at`` is deliberately NOT set here — only ``main()`` adds the
    single wall-clock field, so a replay compares everything else exactly.
    """
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    for name in _OWNED_WORKDIRS:
        victim = work / name
        if victim.exists():
            shutil.rmtree(victim)

    scenarios: list[dict] = []

    # 1. publish_g1 — G1 admitted into the source local store.
    source = _local_store(work, "source")
    g1 = PDS.publish_production_dataset(source, _material()).generation_id
    scenarios.append(
        {
            "scenario": "publish_g1",
            "steps": [
                _api_step(
                    work,
                    step="publish_g1",
                    argv=["PDS.publish_production_dataset", "--local-store", "source"],
                    asserts={"generation_id": g1, "store": "source"},
                )
            ],
        }
    )

    # 2. restart — a NEW store object over the same directory serves G1.
    reopened = _local_store(work, "source")
    summary = PDS.latest_generation_summary(reopened, ISSUER)
    audit = _cli_step(
        work,
        step="audit",
        args=["audit", "--local-store", str(work / "source"), "--issuer", ISSUER],
        asserts={},
    )
    audit["assert"] = {
        "state": audit["stdout"]["state"],
        "generation_id": audit["stdout"]["generation_id"],
        "summary": summary,
    }
    scenarios.append(
        {
            "scenario": "restart",
            "steps": [
                _api_step(
                    work,
                    step="reopen_store_object",
                    argv=["PDS.build_production_dataset_store", "--local-store", "source"],
                    asserts={"store": "source", "summary": summary},
                ),
                audit,
            ],
        }
    )

    # 3. backup — CLI backup of the admitted G1.
    backup = _cli_step(
        work,
        step="backup",
        args=[
            "backup",
            "--local-store",
            str(work / "source"),
            "--issuer",
            ISSUER,
            "--out",
            str(work / "backup"),
        ],
        asserts={},
    )
    manifest_bytes = (work / "backup" / "manifest.json").read_bytes()
    manifest_document = json.loads(manifest_bytes)
    objects_count = len(list((work / "backup" / "objects").iterdir()))
    backup["assert"] = {
        "generation_id": backup["stdout"]["generation_id"],
        "entries": backup["stdout"]["entries"],
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_path": "backup/manifest.json",
        "objects": objects_count,
    }
    scenarios.append({"scenario": "backup", "steps": [backup]})
    entries_total = len(manifest_document["entries"])
    immutable_entries = entries_total - 1  # exactly one pointer-role entry

    # 4. lost_publication — manifest landed, pointer never wrote.
    lost = _local_store(work, "lost")
    lost_g1 = PDS.publish_production_dataset(lost, _material(), skip_pointer=True)
    pointer_absent = lost.get_bytes(PDS.production_latest_key(ISSUER)) is None
    lost_audit = _cli_step(
        work,
        step="audit",
        args=["audit", "--local-store", str(work / "lost"), "--issuer", ISSUER],
        asserts={},
    )
    lost_audit["assert"] = {
        "state": lost_audit["stdout"]["state"],
        "recovery": lost_audit["stdout"]["recovery"],
        "generation_id": lost_audit["stdout"]["generation_id"],
        "manifest_generation_ids": lost_audit["stdout"]["manifest_generation_ids"],
        "pointer_key_absent_after_audit": (
            lost.get_bytes(PDS.production_latest_key(ISSUER)) is None
        ),
    }
    scenarios.append(
        {
            "scenario": "lost_publication",
            "steps": [
                _api_step(
                    work,
                    step="publish_skip_pointer",
                    argv=[
                        "PDS.publish_production_dataset",
                        "--local-store",
                        "lost",
                        "--skip-pointer",
                    ],
                    asserts={
                        "generation_id": lost_g1.generation_id,
                        "skip_pointer": True,
                        "pointer_key_absent": pointer_absent,
                    },
                ),
                lost_audit,
            ],
        }
    )

    # 5. restore — CLI restore into a fresh target, then the same restore again.
    restore = _cli_step(
        work,
        step="restore",
        args=[
            "restore",
            "--from",
            str(work / "backup"),
            "--local-store",
            str(work / "target"),
            "--issuer",
            ISSUER,
        ],
        asserts={},
    )
    first = restore["stdout"]
    restore["assert"] = {
        "verified": first["verified"],
        "pointer": first["pointer"],
        "already_present_count": len(first["already_present"]),
        # The drill's own writes: clean conditional creates ("written") plus
        # ambiguous-signal writes a read-back confirmed ("restored").
        "entries_written_by_restore": len(first["written"]) + len(first["restored"]),
        "immutable_entry_count": immutable_entries,
    }
    target_audit = _cli_step(
        work,
        step="audit_restored_target",
        args=["audit", "--local-store", str(work / "target"), "--issuer", ISSUER],
        asserts={},
    )
    target_audit["assert"] = {
        "state": target_audit["stdout"]["state"],
        "generation_id": target_audit["stdout"]["generation_id"],
    }
    restore_again = _cli_step(
        work,
        step="restore_again",
        args=[
            "restore",
            "--from",
            str(work / "backup"),
            "--local-store",
            str(work / "target"),
            "--issuer",
            ISSUER,
        ],
        asserts={},
    )
    second = restore_again["stdout"]
    restore_again["assert"] = {
        "verified": second["verified"],
        "pointer": second["pointer"],
        "already_present_count": len(second["already_present"]),
        "entries_written_by_restore": len(second["written"]) + len(second["restored"]),
        "immutable_entry_count": immutable_entries,
    }
    scenarios.append(
        {"scenario": "restore", "steps": [restore, target_audit, restore_again]}
    )

    # 6. rollback_refused — rollback is a superseding correction, never a rewind.
    g2 = PDS.publish_production_dataset(
        source, _material(admitted_at=T_LATER, supersedes=g1)
    ).generation_id
    rewind_error: PDS.ProductionDatasetError | None = None
    try:
        PDS.publish_production_dataset(source, _material())
    except PDS.ProductionDatasetError as exc:
        rewind_error = exc
    if rewind_error is None or REWIND_REFUSAL_MESSAGE not in str(rewind_error):
        raise SystemExit(
            "rollback refusal did not occur or carried an unexpected message: "
            f"{rewind_error!r}"
        )
    rollback_audit = _cli_step(
        work,
        step="audit_after_rollback",
        args=["audit", "--local-store", str(work / "source"), "--issuer", ISSUER],
        asserts={},
    )
    rollback_audit["assert"] = {
        "state": rollback_audit["stdout"]["state"],
        "generation_id": rollback_audit["stdout"]["generation_id"],
    }
    loadable_ids = sorted(
        PDS.load_generation(source, ISSUER, generation_id).generation_id
        for generation_id in (g1, g2)
    )
    reconcile = RD.reconcile_effect_unknown(source, ISSUER, g1)
    rewindish = sorted(
        name
        for name in vars(RD)
        if "rewind" in name.lower() or "rollback" in name.lower()
    )
    scenarios.append(
        {
            "scenario": "rollback_refused",
            "steps": [
                _api_step(
                    work,
                    step="publish_g2",
                    argv=["PDS.publish_production_dataset", "--local-store", "source"],
                    asserts={"generation_id": g2, "supersedes": g1},
                ),
                _api_step(
                    work,
                    step="rewind_refused",
                    argv=["PDS.publish_production_dataset", "--local-store", "source"],
                    asserts={
                        "raised": type(rewind_error).__name__,
                        "message": str(rewind_error),
                        "message_contains": REWIND_REFUSAL_MESSAGE,
                    },
                    exit_code=1,
                    stderr_first_line=str(rewind_error),
                ),
                rollback_audit,
                _api_step(
                    work,
                    step="originals_intact",
                    argv=["PDS.load_generation", "--local-store", "source", "--issuer", ISSUER],
                    asserts={"loadable_generation_ids": loadable_ids},
                ),
                _api_step(
                    work,
                    step="reconcile_g1",
                    argv=[
                        "RD.reconcile_effect_unknown",
                        "--local-store",
                        "source",
                        "--expected",
                        g1,
                    ],
                    asserts={"outcome": reconcile},
                ),
                _api_step(
                    work,
                    step="rewind_surface_absent",
                    argv=["vars(engine.fundamental_forensics.recovery_drill)"],
                    asserts={"rewindish_names": rewindish},
                ),
            ],
        }
    )

    # 7. corrupted_target — one flipped object byte makes the pointer unverifiable.
    # LocalStore maps a store key to <store dir>/<key> (keys are relative
    # paths; engine/research_vault/r2_store.py:1029,1044-1049), so the file to
    # corrupt is derived from the public backup manifest, not guessed.
    corrupt_entry = min(
        (row for row in manifest_document["entries"] if row["role"] == "object"),
        key=lambda row: row["key"],
    )
    shutil.copytree(work / "target", work / "corrupt")
    object_path = work / "corrupt" / corrupt_entry["key"]
    payload = bytearray(object_path.read_bytes())
    payload[0] ^= 0x01
    object_path.write_bytes(bytes(payload))
    corrupt_audit = _cli_step(
        work,
        step="audit",
        args=["audit", "--local-store", str(work / "corrupt"), "--issuer", ISSUER],
        asserts={},
    )
    corrupt_audit["assert"] = {"state": corrupt_audit["stdout"]["state"]}
    scenarios.append(
        {
            "scenario": "corrupted_target",
            "steps": [
                _api_step(
                    work,
                    step="corrupt_one_object",
                    argv=["shutil.copytree", "--from", "target", "--to", "corrupt"],
                    asserts={
                        "corrupted_key": corrupt_entry["key"],
                        "corrupted_file": f"corrupt/{corrupt_entry['key']}",
                        "byte_offset": 0,
                        "first_byte_xor": 1,
                    },
                ),
                corrupt_audit,
            ],
        }
    )

    return {
        "schema": SCHEMA,
        "matrix_row": MATRIX_ROW,
        "base_commit": BASE_COMMIT,
        "store_kind": "local_directory",
        "production_touched": False,
        "network": False,
        "issuer_id": ISSUER,
        "generations": {"g1": g1, "g2": g2},
        "scenarios": scenarios,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fif_a47_recovery_drill_receipts.py",
        description="Record the FIF Z0 A47 recovery-drill receipts on local-directory stores.",
    )
    parser.add_argument("--work", type=Path, required=True, help="Scratch directory for the local stores")
    parser.add_argument("--out", type=Path, required=True, help="Receipt JSON output path")
    args = parser.parse_args(argv)

    document = run_drill(args.work)
    document["recorded_at"] = datetime.now(timezone.utc).isoformat()
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    generations = document["generations"]
    print(
        "wrote "
        f"{args.out} (g1={generations['g1']} g2={generations['g2']}, "
        f"{len(document['scenarios'])} scenarios)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
