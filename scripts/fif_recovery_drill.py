#!/usr/bin/env python3
"""FIF V0-b recovery drill CLI: backup / restore / audit on LOCAL stores only.

Thin command surface over
``engine.fundamental_forensics/recovery_drill.py`` (the read-mostly drill;
see its module docstring for the A47/A18 laws and typed gaps). Every
subcommand operates on a local-directory store built from an explicit
``--local-store`` directory — this tool never builds a remote store and
never reads ``R2_*`` (or any other credential) environment.

* ``backup`` inventories an issuer's admitted latest generation and writes
  ``<out>/manifest.json`` plus the exact bytes under ``<out>/objects/<sha256>``.
* ``restore`` replays such a backup into a target local store, create-only.
  Exit code 1 when the restored generation cannot be loaded and verified.
* ``audit`` prints one issuer's recovery state as JSON. Exit code 0 for
  ``admitted``/``absent``, 1 for any state that needs operator attention
  (lost publication, unverifiable pointer, listing gap).

Failure shape mirrors the publication gate: one line-start ``::error`` on
STDERR and a non-zero exit — never a stack trace, never silence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.fundamental_forensics import production_datasets as PDS  # noqa: E402
from engine.fundamental_forensics import recovery_drill as RD  # noqa: E402


def _fail(message: str) -> int:
    print(f"::error title=fif-recovery-drill::{message}", file=sys.stderr, flush=True)
    return 1


def _build_local_store(local_dir: Path):
    """Local-directory store only; the explicit dir short-circuits every
    environment fallback inside build_production_dataset_store."""
    return PDS.build_production_dataset_store(local_dir=Path(local_dir))


def _run_backup(args: argparse.Namespace) -> int:
    store = _build_local_store(args.local_store)
    manifest = RD.backup_issuer(store, args.issuer)
    payloads = RD.backup_bytes(store, manifest)
    out_dir = Path(args.out)
    objects_dir = out_dir / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    for entry in sorted(manifest.entries, key=lambda e: e.key):
        (objects_dir / entry.sha256_hex).write_bytes(payloads[entry.key])
    # manifest.json lands last: its presence marks a complete backup.
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "backed_up": args.issuer,
                "generation_id": manifest.generation_id,
                "entries": len(manifest.entries),
                "out": str(out_dir),
            },
            sort_keys=True,
        )
    )
    return 0


def _run_restore(args: argparse.Namespace) -> int:
    backup_dir = Path(args.from_dir)
    document_path = backup_dir / "manifest.json"
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"backup manifest unreadable at {document_path}: {exc}")
    manifest = RD.BackupManifest.from_dict(document)
    if manifest.issuer_id != args.issuer:
        return _fail(
            f"backup issuer {manifest.issuer_id!r} does not match --issuer {args.issuer!r}"
        )
    payloads: dict[str, bytes] = {}
    for entry in manifest.entries:
        payload_path = backup_dir / "objects" / entry.sha256_hex
        if not payload_path.is_file():
            return _fail(f"backup object missing: {payload_path}")
        payloads[entry.key] = payload_path.read_bytes()
    target = _build_local_store(args.local_store)
    receipt = RD.restore_issuer(target, manifest, payloads)
    print(json.dumps(receipt.to_dict(), sort_keys=True))
    if not receipt.verified:
        return _fail(
            f"restore of {manifest.generation_id} is not complete: the generation "
            "cannot be loaded and verified from the target store"
        )
    return 0


def _run_audit(args: argparse.Namespace) -> int:
    store = _build_local_store(args.local_store)
    state = RD.audit_issuer(store, args.issuer)
    print(json.dumps(state.to_dict(), sort_keys=True))
    return 0 if state.state in ("admitted", "absent") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fif_recovery_drill.py",
        description="FIF production-dataset recovery drill (local-directory stores only).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser(
        "backup", help="Back up an issuer's admitted latest generation to a directory"
    )
    backup.add_argument("--local-store", type=Path, required=True, help="Source local store directory")
    backup.add_argument("--issuer", required=True, help="Issuer id (entity id)")
    backup.add_argument("--out", type=Path, required=True, help="Backup output directory")
    backup.set_defaults(func=_run_backup)

    restore = subparsers.add_parser(
        "restore", help="Restore a backup into a target local store (create-only)"
    )
    restore.add_argument("--from", dest="from_dir", type=Path, required=True, help="Backup directory")
    restore.add_argument("--local-store", type=Path, required=True, help="Target local store directory")
    restore.add_argument("--issuer", required=True, help="Issuer id (entity id)")
    restore.set_defaults(func=_run_restore)

    audit = subparsers.add_parser("audit", help="Print one issuer's recovery state as JSON")
    audit.add_argument("--local-store", type=Path, required=True, help="Local store directory")
    audit.add_argument("--issuer", required=True, help="Issuer id (entity id)")
    audit.set_defaults(func=_run_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except PDS.ProductionDatasetError as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
