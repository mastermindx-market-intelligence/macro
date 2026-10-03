#!/usr/bin/env python3
"""Install and read back the canonical MarketDesk extractor source bytes.

The installer owns source files only. It never touches credentials, virtual
environments, browser profiles, databases, research artifacts, or logs, and it
never starts or stops launchd jobs. Runtime activation remains a later reviewed
operator step after an accepted Git commit exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_PAYLOAD_COUNT = 58
EXPECTED_MANIFEST_SHA256 = (
    "6209be070fbdfe8b8269bb62c0b6f466dac9b425ba1e9244b9b1bf7d983ba602"
)
MANIFEST_NAME = "SHA256SUMS"
IMPORT_RECEIPT_NAME = "IMPORT_RECEIPT.json"
ROLLBACK_RECEIPT = "ROLLBACK_RECEIPT.json"
APPROVED_RUNTIME_PAYLOADS = frozenset(
    {
        "runtime/feed.sh",
        "runtime/com.mastermindx.research-feed.plist",
        "runtime/com.mastermindx.research-trickle.plist",
    }
)
MANAGED_RUNTIME_DIRS = ("src", "tests", "docs", "deploy")
MANAGED_RUNTIME_FILES = (".env.example", "README.md", "pyproject.toml")
DEFAULT_SOURCE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = Path.home() / "mastermind-research" / "marketdesk_paper_extractor"
DEFAULT_FEED_SCRIPT = Path.home() / "mastermind-research" / "feed.sh"
DEFAULT_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _absolute_without_resolving(path: Path) -> Path:
    """Return an absolute path without erasing a symlink at the destination."""
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))


def _refuse_symlink_components(path: Path, label: str) -> None:
    """Reject a symlink at the path or in any existing ancestor component."""
    absolute = _absolute_without_resolving(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RuntimeError(f"{label} traverses a symlink: {current}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_manifest_path(raw: str) -> str:
    value = raw.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe manifest path: {raw!r}")
    return path.as_posix()


def _parse_manifest(source_root: Path) -> dict[str, str]:
    manifest_path = source_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing source manifest: {manifest_path}")

    entries: dict[str, str] = {}
    for line_number, line in enumerate(manifest_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        digest, separator, raw_path = line.partition("  ")
        if not separator or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"invalid manifest line {line_number}: {line!r}")
        relative_path = _normalise_manifest_path(raw_path)
        if relative_path in entries:
            raise ValueError(f"duplicate manifest path: {relative_path}")
        entries[relative_path] = digest
    return entries


def verify_source(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    entries = _parse_manifest(source_root)
    payload_paths = [
        path
        for top_level in ("extractor", "runtime")
        for path in (source_root / top_level).rglob("*")
    ]
    symlinks = sorted(
        path.relative_to(source_root).as_posix()
        for path in payload_paths
        if path.is_symlink()
    )
    actual_files = {
        path.relative_to(source_root).as_posix()
        for path in payload_paths
        if path.is_file() and not path.is_symlink()
    }

    missing: list[str] = []
    mismatched: list[str] = []
    for relative_path, expected_hash in entries.items():
        path = source_root / relative_path
        if not path.is_file() or path.is_symlink():
            missing.append(relative_path)
        elif _sha256(path) != expected_hash:
            mismatched.append(relative_path)

    unexpected = sorted(actual_files - set(entries))
    receipt_error: str | None = None
    receipt_manifest_sha256: str | None = None
    manifest_sha256 = _sha256(source_root / MANIFEST_NAME)
    try:
        receipt_path = source_root / IMPORT_RECEIPT_NAME
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise ValueError(f"missing regular import receipt: {receipt_path}")
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("schema") != "mastermind.marketdesk_extractor.import.v1":
            raise ValueError(f"unsupported import receipt: {receipt.get('schema')!r}")
        packet = receipt.get("source_packet")
        if not isinstance(packet, dict):
            raise ValueError("import receipt source_packet must be an object")
        if packet.get("manifest") != MANIFEST_NAME:
            raise ValueError("import receipt names a different source manifest")
        if packet.get("payload_count") != EXPECTED_PAYLOAD_COUNT:
            raise ValueError("import receipt payload count does not match the frozen packet")
        candidate_hash = packet.get("manifest_sha256")
        if (
            not isinstance(candidate_hash, str)
            or len(candidate_hash) != 64
            or any(character not in "0123456789abcdef" for character in candidate_hash)
        ):
            raise ValueError("import receipt manifest hash is invalid")
        receipt_manifest_sha256 = candidate_hash
        if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
            raise ValueError("source manifest does not match the frozen manifest hash")
        if receipt_manifest_sha256 != EXPECTED_MANIFEST_SHA256:
            raise ValueError("import receipt does not match the frozen manifest hash")
        if manifest_sha256 != receipt_manifest_sha256:
            raise ValueError("source manifest does not match the frozen import receipt")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        receipt_error = str(exc)

    result = {
        "ok": not missing
        and not mismatched
        and not unexpected
        and not symlinks
        and len(entries) == EXPECTED_PAYLOAD_COUNT
        and receipt_error is None,
        "source_root": str(source_root),
        "payload_count": len(entries),
        "manifest_sha256": manifest_sha256,
        "receipt_manifest_sha256": receipt_manifest_sha256,
        "receipt_error": receipt_error,
        "missing": sorted(missing),
        "mismatched": sorted(mismatched),
        "unexpected": unexpected,
        "symlinks": symlinks,
    }
    return result


def _destination_mappings(
    source_root: Path,
    runtime_root: Path,
    feed_script: Path,
    launch_agents_dir: Path,
) -> list[tuple[str, Path, Path, str]]:
    mappings: list[tuple[str, Path, Path, str]] = []
    for relative_path, expected_hash in _parse_manifest(source_root).items():
        source_path = source_root / relative_path
        packet_path = PurePosixPath(relative_path)
        if packet_path.parts[0] == "extractor":
            destination = runtime_root.joinpath(*packet_path.parts[1:])
        elif relative_path == "runtime/feed.sh":
            destination = feed_script
        elif relative_path in APPROVED_RUNTIME_PAYLOADS:
            destination = launch_agents_dir / packet_path.name
        elif packet_path.parts[0] == "runtime":
            raise ValueError(f"unapproved runtime payload: {relative_path}")
        else:
            raise ValueError(f"unmapped source payload: {relative_path}")
        mappings.append((relative_path, source_path, destination, expected_hash))
    return mappings


def _atomic_copy(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise RuntimeError(f"refusing to copy symlink source: {source}")
    if not source.is_file():
        raise FileNotFoundError(f"copy source is not a regular file: {source}")
    if destination.is_symlink():
        raise RuntimeError(f"refusing to replace symlink: {destination}")
    if destination.exists() and not destination.is_file():
        raise RuntimeError(f"destination is not a regular file: {destination}")
    _refuse_symlink_components(destination.parent, "destination parent")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing to replace symlinked JSON file: {path}")
    _refuse_symlink_components(path.parent, "JSON parent")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _existing_managed_files(runtime_root: Path) -> set[Path]:
    managed: set[Path] = set()
    for name in MANAGED_RUNTIME_FILES:
        path = runtime_root / name
        if path.is_file() or path.is_symlink():
            managed.add(path)
    for name in MANAGED_RUNTIME_DIRS:
        directory = runtime_root / name
        if directory.is_symlink():
            raise RuntimeError(f"managed source directory is a symlink: {directory}")
        if directory.is_dir():
            managed.update(path for path in directory.rglob("*") if path.is_file() or path.is_symlink())
        elif directory.exists():
            raise RuntimeError(f"managed source path is not a directory: {directory}")
    return managed


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_managed_runtime_destination(destination: Path, runtime_root: Path) -> bool:
    """Return whether rollback may alter this source-owned runtime path."""
    if destination in {runtime_root / name for name in MANAGED_RUNTIME_FILES}:
        return True
    return any(
        destination != managed_root and _is_relative_to(destination, managed_root)
        for managed_root in (runtime_root / name for name in MANAGED_RUNTIME_DIRS)
    )


def _create_backup(
    backup_dir: Path,
    managed_destinations: set[Path],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if backup_dir.exists():
        raise FileExistsError(f"backup directory already exists: {backup_dir}")

    destinations = sorted(managed_destinations, key=str)
    for destination in destinations:
        if destination.is_symlink():
            raise RuntimeError(f"refusing to back up symlink: {destination}")
        if destination.exists() and not destination.is_file():
            raise RuntimeError(f"managed destination is not a regular file: {destination}")

    backup_dir.mkdir(parents=True)
    files_dir = backup_dir / "files"
    files_dir.mkdir()

    entries: list[dict[str, Any]] = []
    try:
        for index, destination in enumerate(destinations):
            existed = destination.is_file()
            backup_relative: str | None = None
            backup_sha256: str | None = None
            backup_mode: int | None = None
            if existed:
                backup_relative = f"files/{index:04d}.bin"
                backup_path = backup_dir / backup_relative
                _atomic_copy(destination, backup_path)
                backup_sha256 = _sha256(backup_path)
                backup_mode = stat.S_IMODE(backup_path.stat().st_mode)
            entries.append(
                {
                    "destination": str(destination),
                    "existed": existed,
                    "backup": backup_relative,
                    "backup_sha256": backup_sha256,
                    "backup_mode": backup_mode,
                }
            )
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise

    receipt = {
        "schema": "mastermind.marketdesk_extractor.rollback.v1",
        "created_at": _utc_now(),
        "phase": "backed_up",
        "entries": entries,
        **metadata,
    }
    _atomic_write_json(backup_dir / ROLLBACK_RECEIPT, receipt)
    return receipt


def verify_installed(
    source_root: Path = DEFAULT_SOURCE_ROOT,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    feed_script: Path = DEFAULT_FEED_SCRIPT,
    launch_agents_dir: Path = DEFAULT_LAUNCH_AGENTS_DIR,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    runtime_root = _absolute_without_resolving(runtime_root)
    feed_script = _absolute_without_resolving(feed_script)
    launch_agents_dir = _absolute_without_resolving(launch_agents_dir)

    source_result = verify_source(source_root)
    missing: list[str] = []
    mismatched: list[str] = []
    mode_mismatched: list[str] = []
    symlinks: list[str] = []
    matched = 0
    for _, source_path, destination, expected_hash in _destination_mappings(
        source_root, runtime_root, feed_script, launch_agents_dir
    ):
        if destination.is_symlink():
            symlinks.append(str(destination))
        elif not destination.is_file():
            missing.append(str(destination))
        elif _sha256(destination) != expected_hash:
            mismatched.append(str(destination))
        else:
            source_mode = stat.S_IMODE(source_path.stat().st_mode)
            destination_mode = stat.S_IMODE(destination.stat().st_mode)
            if source_mode != destination_mode:
                mode_mismatched.append(str(destination))
            else:
                matched += 1
    return {
        "ok": source_result["ok"]
        and not missing
        and not mismatched
        and not mode_mismatched
        and not symlinks,
        "source_ok": source_result["ok"],
        "matched": matched,
        "missing": sorted(missing),
        "mismatched": sorted(mismatched),
        "mode_mismatched": sorted(mode_mismatched),
        "symlinks": sorted(symlinks),
        "runtime_root": str(runtime_root),
        "feed_script": str(feed_script),
        "launch_agents_dir": str(launch_agents_dir),
    }


def _remove_managed_runtime_source(runtime_root: Path) -> None:
    for name in MANAGED_RUNTIME_DIRS:
        directory = runtime_root / name
        if directory.is_symlink():
            raise RuntimeError(f"refusing to remove symlinked managed directory: {directory}")
        if directory.exists():
            if not directory.is_dir():
                raise RuntimeError(f"managed source path is not a directory: {directory}")
            shutil.rmtree(directory)


def _receipt_absolute_path(receipt: dict[str, Any], field: str) -> Path:
    raw = receipt.get(field)
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise ValueError(f"rollback receipt field {field!r} is not an absolute path")
    path = _absolute_without_resolving(Path(raw))
    _refuse_symlink_components(path, f"rollback {field}")
    return path


def rollback(
    backup_dir: Path,
    *,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    feed_script: Path = DEFAULT_FEED_SCRIPT,
    launch_agents_dir: Path = DEFAULT_LAUNCH_AGENTS_DIR,
) -> dict[str, Any]:
    backup_dir = _absolute_without_resolving(backup_dir)
    runtime_root = _absolute_without_resolving(runtime_root)
    feed_script = _absolute_without_resolving(feed_script)
    launch_agents_dir = _absolute_without_resolving(launch_agents_dir)
    _refuse_symlink_components(backup_dir, "backup directory")
    _refuse_symlink_components(runtime_root, "requested runtime root")
    _refuse_symlink_components(feed_script, "requested feed script")
    _refuse_symlink_components(launch_agents_dir, "requested launch-agents directory")
    receipt_path = backup_dir / ROLLBACK_RECEIPT
    _refuse_symlink_components(receipt_path, "rollback receipt")
    if not receipt_path.is_file():
        raise FileNotFoundError(f"missing rollback receipt: {receipt_path}")
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("schema") != "mastermind.marketdesk_extractor.rollback.v1":
        raise ValueError(f"unsupported rollback receipt: {receipt.get('schema')!r}")

    receipt_destinations = {
        "runtime_root": _receipt_absolute_path(receipt, "runtime_root"),
        "feed_script": _receipt_absolute_path(receipt, "feed_script"),
        "launch_agents_dir": _receipt_absolute_path(receipt, "launch_agents_dir"),
    }
    requested_destinations = {
        "runtime_root": runtime_root,
        "feed_script": feed_script,
        "launch_agents_dir": launch_agents_dir,
    }
    for field, requested in requested_destinations.items():
        recorded = receipt_destinations[field]
        if recorded != requested:
            raise ValueError(
                f"rollback receipt {field} does not match requested destination: "
                f"recorded={recorded} requested={requested}"
            )
    allowed_launch_agents = {
        launch_agents_dir / "com.mastermindx.research-feed.plist",
        launch_agents_dir / "com.mastermindx.research-trickle.plist",
    }

    raw_entries = receipt.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("rollback receipt entries must be a list")
    prepared: list[tuple[Path, bool, Path | None, str | None, int | None]] = []
    seen_destinations: set[Path] = set()
    for entry in raw_entries:
        if not isinstance(entry, dict):
            raise ValueError("rollback receipt entry must be an object")
        raw_destination = entry.get("destination")
        if not isinstance(raw_destination, str) or not Path(raw_destination).is_absolute():
            raise ValueError("rollback destination is not an absolute path")
        destination = _absolute_without_resolving(Path(raw_destination))
        if destination in seen_destinations:
            raise ValueError(f"duplicate rollback destination: {destination}")
        seen_destinations.add(destination)
        if not (
            _is_managed_runtime_destination(destination, runtime_root)
            or destination == feed_script
            or destination in allowed_launch_agents
        ):
            raise ValueError(
                f"rollback destination is outside managed source-owned destinations: {destination}"
            )
        _refuse_symlink_components(destination, "rollback destination")
        if destination.exists() and not destination.is_file():
            raise RuntimeError(f"refusing to alter non-file during rollback: {destination}")

        existed = entry.get("existed")
        if not isinstance(existed, bool):
            raise ValueError(f"rollback existed flag is invalid for {destination}")
        backup_path: Path | None = None
        backup_sha256: str | None = None
        backup_mode: int | None = None
        if existed:
            raw_backup = entry.get("backup")
            if not isinstance(raw_backup, str):
                raise ValueError(f"missing backup path for {destination}")
            backup_relative = _normalise_manifest_path(raw_backup)
            parts = PurePosixPath(backup_relative).parts
            if len(parts) != 2 or parts[0] != "files":
                raise ValueError(f"backup path is outside the backup payload directory: {raw_backup}")
            backup_path = backup_dir / backup_relative
            _refuse_symlink_components(backup_path, "backup payload")
            if not backup_path.is_file():
                raise FileNotFoundError(f"missing backup payload: {backup_path}")
            backup_sha256 = entry.get("backup_sha256")
            if (
                not isinstance(backup_sha256, str)
                or len(backup_sha256) != 64
                or any(character not in "0123456789abcdef" for character in backup_sha256)
            ):
                raise ValueError(f"invalid backup hash for {destination}")
            if _sha256(backup_path) != backup_sha256:
                raise RuntimeError(f"backup hash mismatch for {destination}")
            backup_mode = entry.get("backup_mode")
            if not isinstance(backup_mode, int) or not 0 <= backup_mode <= 0o7777:
                raise ValueError(f"invalid backup mode for {destination}")
            if stat.S_IMODE(backup_path.stat().st_mode) != backup_mode:
                raise RuntimeError(f"backup mode mismatch for {destination}")
        elif any(entry.get(key) is not None for key in ("backup", "backup_sha256", "backup_mode")):
            raise ValueError(f"unexpected backup metadata for absent destination: {destination}")
        prepared.append((destination, existed, backup_path, backup_sha256, backup_mode))

    restored = 0
    removed = 0
    for destination, existed, backup_path, backup_sha256, backup_mode in prepared:
        if existed:
            assert backup_path is not None and backup_sha256 is not None and backup_mode is not None
            _atomic_copy(backup_path, destination)
            if _sha256(destination) != backup_sha256:
                raise RuntimeError(f"restored hash mismatch for {destination}")
            if stat.S_IMODE(destination.stat().st_mode) != backup_mode:
                raise RuntimeError(f"restored mode mismatch for {destination}")
            restored += 1
        elif destination.exists():
            destination.unlink()
            removed += 1

    receipt["phase"] = "rolled_back"
    receipt["rolled_back_at"] = _utc_now()
    _atomic_write_json(receipt_path, receipt)
    return {
        "ok": True,
        "backup_dir": str(backup_dir),
        "restored": restored,
        "removed": removed,
    }


def install(
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    feed_script: Path = DEFAULT_FEED_SCRIPT,
    launch_agents_dir: Path = DEFAULT_LAUNCH_AGENTS_DIR,
    backup_dir: Path,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    runtime_root = _absolute_without_resolving(runtime_root)
    feed_script = _absolute_without_resolving(feed_script)
    launch_agents_dir = _absolute_without_resolving(launch_agents_dir)
    backup_dir = _absolute_without_resolving(backup_dir)

    _refuse_symlink_components(runtime_root, "runtime root")
    _refuse_symlink_components(feed_script, "feed script")
    _refuse_symlink_components(launch_agents_dir, "launch-agents directory")
    _refuse_symlink_components(backup_dir, "backup directory")

    source_result = verify_source(source_root)
    if not source_result["ok"]:
        raise RuntimeError(f"source verification failed: {json.dumps(source_result, sort_keys=True)}")
    if _is_relative_to(backup_dir, runtime_root):
        raise ValueError("backup directory must be outside the managed runtime root")

    mappings = _destination_mappings(source_root, runtime_root, feed_script, launch_agents_dir)
    managed_destinations = _existing_managed_files(runtime_root)
    managed_destinations.update(destination for _, _, destination, _ in mappings)
    receipt = _create_backup(
        backup_dir,
        managed_destinations,
        {
            "source_root": str(source_root),
            "runtime_root": str(runtime_root),
            "feed_script": str(feed_script),
            "launch_agents_dir": str(launch_agents_dir),
            "source_manifest_sha256": _sha256(source_root / MANIFEST_NAME),
            "payload_count": len(mappings),
        },
    )

    try:
        _remove_managed_runtime_source(runtime_root)
        for _, source_path, destination, _ in mappings:
            _atomic_copy(source_path, destination)

        readback = verify_installed(
            source_root=source_root,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents_dir,
        )
        if not readback["ok"]:
            raise RuntimeError(f"installed-byte verification failed: {json.dumps(readback, sort_keys=True)}")

        receipt["phase"] = "installed"
        receipt["installed_at"] = _utc_now()
        receipt["readback"] = readback
        _atomic_write_json(backup_dir / ROLLBACK_RECEIPT, receipt)
        return {
            "ok": True,
            "installed_files": len(mappings),
            "backup_dir": str(backup_dir),
            "readback": readback,
        }
    except Exception:
        rollback(
            backup_dir,
            runtime_root=runtime_root,
            feed_script=feed_script,
            launch_agents_dir=launch_agents_dir,
        )
        raise


def _add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)


def _add_destination_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=DEFAULT_RUNTIME_ROOT,
        help="non-production test/rehearsal override for the extractor root",
    )
    parser.add_argument(
        "--feed-script",
        type=Path,
        default=DEFAULT_FEED_SCRIPT,
        help="non-production test/rehearsal override for the feed script",
    )
    parser.add_argument(
        "--launch-agents-dir",
        type=Path,
        default=DEFAULT_LAUNCH_AGENTS_DIR,
        help="non-production test/rehearsal override for the launch-agent directory",
    )


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    _add_source_argument(parser)
    _add_destination_arguments(parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    verify_source_parser = commands.add_parser(
        "verify-source", help="verify the immutable packet payload"
    )
    _add_source_argument(verify_source_parser)

    verify_installed_parser = commands.add_parser(
        "verify-installed", help="compare runtime bytes with canonical source"
    )
    _add_runtime_arguments(verify_installed_parser)

    install_parser = commands.add_parser(
        "install", help="back up and atomically install source-owned bytes"
    )
    _add_runtime_arguments(install_parser)
    install_parser.add_argument("--backup-dir", type=Path, required=True)

    rollback_parser = commands.add_parser(
        "rollback", help="restore the exact pre-install source-owned bytes"
    )
    _add_destination_arguments(rollback_parser)
    rollback_parser.add_argument("--backup-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "verify-source":
            result = verify_source(args.source_root)
        elif args.command == "verify-installed":
            result = verify_installed(
                source_root=args.source_root,
                runtime_root=args.runtime_root,
                feed_script=args.feed_script,
                launch_agents_dir=args.launch_agents_dir,
            )
        elif args.command == "install":
            result = install(
                source_root=args.source_root,
                runtime_root=args.runtime_root,
                feed_script=args.feed_script,
                launch_agents_dir=args.launch_agents_dir,
                backup_dir=args.backup_dir,
            )
        elif args.command == "rollback":
            result = rollback(
                args.backup_dir,
                runtime_root=args.runtime_root,
                feed_script=args.feed_script,
                launch_agents_dir=args.launch_agents_dir,
            )
        else:  # pragma: no cover - argparse prevents this branch
            raise AssertionError(f"unhandled command: {args.command}")
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": type(exc).__name__, "message": str(exc)},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
