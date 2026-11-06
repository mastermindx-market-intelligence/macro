#!/usr/bin/env python3
"""Deliver completed retained US OHLC generations through the existing VPS carrier.

The CLI has fixed production paths and a pinned SSH destination. Filesystem
parameters on the Python API exist for isolated synthetic tests.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from typing import BinaryIO, Mapping, Sequence

SCHEMA = "macro.ohlc.delivery.v1"
REPOSITORY = "mastermindx-market-intelligence/macro"
WORKFLOW = REPOSITORY + "/.github/workflows/daily.yml@refs/heads/main"
APP_ROOT = Path("/opt/macro")
LOCK_FILE = Path("/var/lock/macro-update.lock")
SSH_TARGET = "root@146.190.142.17"
HOST_PIN = Path(__file__).resolve().parents[1] / "app/deploy/ohlc_origin_known_hosts"
MAX_FILES = 25000
MAX_SYMBOLS = 50000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 3 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_BYTES = MAX_TOTAL_BYTES + MAX_MANIFEST_BYTES + MAX_FILES * 4096
GENERATION_RE = re.compile(r"daily-[1-9][0-9]{0,19}-[1-9][0-9]{0,9}")
OWNER = {"schema": SCHEMA, "purpose": "retained-us-ohlc-delivery"}


class DeliveryError(Exception):
    """A finite, non-secret diagnostic suitable for workflow output."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DeliveryError(code)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _object(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "duplicate_json_key")
        value[key] = item
    return value


def _decode(data: bytes):
    try:
        return json.loads(data, object_pairs_hook=_object)
    except (UnicodeError, ValueError):
        raise DeliveryError("invalid_json") from None


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _positive(value, maximum: int = 10**20 - 1) -> bool:
    return type(value) is int and 0 < value <= maximum


def _filename(symbol: str) -> str:
    _require(isinstance(symbol, str), "invalid_symbol")
    name = symbol.replace("^", "_").replace("=", "_") + ".json"
    _require(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,94}\.json", name) is not None,
             "unsafe_filename")
    return name


def _plain_dir(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise DeliveryError("missing_directory") from None
    _require(stat.S_ISDIR(mode) and not stat.S_ISLNK(mode), "foreign_directory")


def _read_regular(path: Path, limit: int) -> bytes:
    try:
        before = path.lstat()
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "nonregular_file")
        _require(0 < before.st_size <= limit, "file_size_limit")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            _require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
                     "file_changed")
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
        _require(len(data) == before.st_size <= limit, "file_changed")
        _require((after.st_size, after.st_mtime_ns, after.st_nlink)
                 == (before.st_size, before.st_mtime_ns, 1), "file_changed")
        return data
    except OSError:
        raise DeliveryError("file_unreadable") from None


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(fd)


def _write_json(path: Path, value: object, *, exclusive: bool = False) -> None:
    _plain_dir(path.parent)
    _require(not path.is_symlink(), "foreign_receipt")
    data = _json_bytes(value)
    if exclusive:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            raise DeliveryError("operation_already_started") from None
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    else:
        fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    _sync_directory(path.parent)


def validate_manifest(document: dict) -> dict:
    keys = {"schema", "repository", "workflow", "ref", "source_sha", "run_id",
            "run_number", "run_attempt", "index_sha256", "created_at_utc",
            "generation", "files", "expected_symbols", "unavailable_symbols", "total_bytes"}
    _require(isinstance(document, dict) and set(document) == keys, "manifest_schema")
    _require(document["schema"] == SCHEMA and document["repository"] == REPOSITORY
             and document["workflow"] == WORKFLOW and document["ref"] == "refs/heads/main",
             "untrusted_provenance")
    for key, length in (("source_sha", 40), ("index_sha256", 64)):
        _require(isinstance(document[key], str)
                 and re.fullmatch("[0-9a-f]{" + str(length) + "}", document[key]) is not None,
                 "invalid_digest")
    run_id = document["run_id"]
    _require(isinstance(run_id, str) and re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is not None,
             "invalid_run_identity")
    _require(_positive(document["run_number"]) and _positive(document["run_attempt"], 10**10-1),
             "invalid_run_identity")
    _require(document["generation"] == f"daily-{run_id}-{document['run_attempt']}",
             "invalid_generation")
    created = document["created_at_utc"]
    try:
        _require(isinstance(created, str) and created.endswith("Z"), "invalid_timestamp")
        datetime.fromisoformat(created[:-1] + "+00:00")
    except ValueError:
        raise DeliveryError("invalid_timestamp") from None
    symbols = document["expected_symbols"]
    _require(isinstance(symbols, list) and 0 < len(symbols) <= MAX_SYMBOLS, "symbol_census")
    names = [_filename(symbol) for symbol in symbols]
    symbol_set = set(symbols)
    _require(len(symbol_set) == len(symbols)
             and len({name.casefold() for name in names}) == len(names), "filename_collision")
    unavailable = document["unavailable_symbols"]
    _require(isinstance(unavailable, dict)
             and set(unavailable) <= symbol_set
             and all(reason == "no_retained_price" for reason in unavailable.values()),
             "unavailable_census")
    files = document["files"]
    _require(isinstance(files, list) and 0 < len(files) <= MAX_FILES, "file_census")
    seen = set()
    total = 0
    for entry in files:
        _require(isinstance(entry, dict) and set(entry) == {"symbol", "name", "size", "sha256"},
                 "file_schema")
        symbol = entry["symbol"]
        _require(isinstance(symbol, str) and symbol in symbol_set and symbol not in seen,
                 "file_census")
        seen.add(symbol)
        _require(entry["name"] == _filename(symbol), "unsafe_filename")
        _require(_positive(entry["size"], MAX_FILE_BYTES), "file_size_limit")
        _require(isinstance(entry["sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None, "invalid_digest")
        total += entry["size"]
    _require(not (seen & set(unavailable)) and seen | set(unavailable) == symbol_set,
             "incomplete_census")
    _require(type(document["total_bytes"]) is int
             and document["total_bytes"] == total <= MAX_TOTAL_BYTES, "total_size_limit")
    return document


def validate_payload(payload_dir: Path, document: dict) -> None:
    validate_manifest(document)
    _plain_dir(payload_dir)
    expected = {entry["name"]: entry for entry in document["files"]}
    _require({entry.name for entry in payload_dir.iterdir()} == set(expected), "payload_census")
    for name, entry in expected.items():
        data = _read_regular(payload_dir / name, MAX_FILE_BYTES)
        _require(len(data) == entry["size"] and _digest(data) == entry["sha256"],
                 "payload_digest")


def seal_generation(
    payload_dir: Path, manifest_path: Path, *, source_sha: str, run_id: str,
    run_number: int, run_attempt: int, index_sha256: str,
    expected_symbols: Sequence[str], unavailable_symbols: Mapping[str, str],
    created_at_utc: str | None = None,
) -> dict:
    _plain_dir(payload_dir)
    _require(manifest_path.parent.resolve() != payload_dir.resolve(), "manifest_inside_payload")
    symbols = list(expected_symbols)
    files = []
    for symbol in symbols:
        name = _filename(symbol)
        if symbol in unavailable_symbols:
            continue
        data = _read_regular(payload_dir / name, MAX_FILE_BYTES)
        files.append({"symbol": symbol, "name": name, "size": len(data), "sha256": _digest(data)})
    document = {
        "schema": SCHEMA, "repository": REPOSITORY, "workflow": WORKFLOW,
        "ref": "refs/heads/main", "source_sha": source_sha,
        "run_id": run_id, "run_number": run_number, "run_attempt": run_attempt,
        "index_sha256": index_sha256, "created_at_utc": created_at_utc or _utc_now(),
        "generation": f"daily-{run_id}-{run_attempt}",
        "expected_symbols": symbols, "unavailable_symbols": dict(unavailable_symbols),
        "files": files, "total_bytes": sum(entry["size"] for entry in files),
    }
    validate_payload(payload_dir, document)
    _require(len(_json_bytes(document)) <= MAX_MANIFEST_BYTES, "manifest_size_limit")
    _write_json(manifest_path, document)
    return document


def build_bundle(payload_dir: Path, manifest_path: Path, bundle_path: Path) -> dict:
    manifest_bytes = _read_regular(manifest_path, MAX_MANIFEST_BYTES)
    document = validate_manifest(_decode(manifest_bytes))
    validate_payload(payload_dir, document)
    # No directory entries or filesystem metadata are imported into the archive.
    with bundle_path.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            header = tarfile.TarInfo("manifest.json")
            header.size = len(manifest_bytes)
            header.mode = 0o644
            archive.addfile(header, io.BytesIO(manifest_bytes))
            for entry in document["files"]:
                data = _read_regular(payload_dir / entry["name"], MAX_FILE_BYTES)
                _require(len(data) == entry["size"] and _digest(data) == entry["sha256"],
                         "payload_changed")
                header = tarfile.TarInfo("payload/" + entry["name"])
                header.size = len(data)
                header.mode = 0o644
                archive.addfile(header, io.BytesIO(data))
        output.flush()
        os.fsync(output.fileno())
    _require(bundle_path.stat().st_size <= MAX_BUNDLE_BYTES, "bundle_size_limit")
    return {"generation": document["generation"], "manifest_sha256": _digest(manifest_bytes)}


@contextmanager
def _locked(lock_path: Path, *, inherited_fd: int | None = None, timeout: float = 5.0):
    """Borrow the updater's open description without ever unlocking it."""
    try:
        info = lock_path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "invalid_lock")
    except OSError:
        raise DeliveryError("lock_unavailable") from None
    if inherited_fd is not None:
        try:
            opened = os.fstat(inherited_fd)
            _require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino),
                     "invalid_lock_fd")
            fcntl.flock(inherited_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ValueError):
            raise DeliveryError("lock_unavailable") from None
        yield
        return
    try:
        fd = os.open(lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        raise DeliveryError("lock_unavailable") from None
    try:
        opened = os.fstat(fd)
        _require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "lock_changed")
        deadline = time.monotonic() + max(0.0, min(timeout, 30.0))
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise DeliveryError("lock_busy") from None
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        yield
    finally:
        os.close(fd)

def _store(app_dir: Path, *, create: bool = False) -> Path | None:
    _plain_dir(app_dir)
    root = app_dir / "ohlc.served"
    if not root.exists() and not root.is_symlink():
        if not create:
            return None
        temporary = Path(tempfile.mkdtemp(prefix=".ohlc-initialize-", dir=app_dir))
        try:
            (temporary / "generations").mkdir(mode=0o755)
            os.chmod(temporary / "generations", 0o755)
            (temporary / "operations").mkdir(mode=0o700)
            _write_json(temporary / "owner.json", OWNER)
            os.chmod(temporary, 0o755)
            os.rename(temporary, root)
            _sync_directory(app_dir)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    _plain_dir(root)
    _require(_decode(_read_regular(root / "owner.json", 4096)) == OWNER, "foreign_store")
    for name in ("generations", "operations"):
        _plain_dir(root / name)
    return root


def _generation(root: Path, generation: str) -> tuple[dict, str]:
    _require(isinstance(generation, str) and GENERATION_RE.fullmatch(generation) is not None,
             "invalid_generation")
    directory = root / "generations" / generation
    _plain_dir(directory)
    _require({item.name for item in directory.iterdir()} == {"manifest.json", "payload"},
             "generation_census")
    raw = _read_regular(directory / "manifest.json", MAX_MANIFEST_BYTES)
    document = validate_manifest(_decode(raw))
    _require(document["generation"] == generation, "generation_identity")
    validate_payload(directory / "payload", document)
    return document, _digest(raw)


def _current(root: Path) -> tuple[dict | None, str | None]:
    current = root / "current"
    if not current.is_symlink():
        _require(not current.exists(), "foreign_current")
        return None, None
    target = os.readlink(current)
    match = re.fullmatch(r"generations/(daily-[1-9][0-9]{0,19}-[1-9][0-9]{0,9})/payload", target)
    _require(match is not None, "foreign_current")
    document, digest = _generation(root, match.group(1))
    record = _operation(root, document["generation"])
    _require(record is not None and record["state"] in {"prepared", "published"}
             and record["manifest_sha256"] == digest, "current_receipt_conflict")
    return document, digest


def _links(app_dir: Path, *, repair: bool) -> None:
    links = []
    for name in ("site", "site.served"):
        directory = app_dir / name
        if directory.exists() or directory.is_symlink():
            _plain_dir(directory)
        links.append(directory / "ohlc")
    for link in links:
        if link.is_symlink():
            _require(os.readlink(link) == "../ohlc.served/current", "foreign_ohlc_path")
        else:
            _require(not link.exists(), "foreign_ohlc_path")
    if repair:
        for link in links:
            if not link.parent.exists():
                link.parent.mkdir(mode=0o755)
                link.parent.chmod(0o755)
            if not link.is_symlink():
                # The shared lock excludes all recognized delivery/updater writers.
                link.symlink_to("../ohlc.served/current", target_is_directory=True)
                _sync_directory(link.parent)


def _select(root: Path, generation: str) -> None:
    temporary = root / (".current-" + uuid.uuid4().hex)
    try:
        temporary.symlink_to(f"generations/{generation}/payload", target_is_directory=True)
        os.replace(temporary, root / "current")
        _sync_directory(root)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def _operation(root: Path, operation_id: str) -> dict | None:
    _require(GENERATION_RE.fullmatch(operation_id) is not None, "invalid_operation")
    path = root / "operations" / (operation_id + ".json")
    if not path.exists() and not path.is_symlink():
        return None
    record = _decode(_read_regular(path, 16384))
    _require(isinstance(record, dict) and record.get("schema") == SCHEMA
             and record.get("generation") == operation_id
             and record.get("state") in {"prepared", "published", "rolled_back"},
             "invalid_operation_receipt")
    _require(re.fullmatch(r"[0-9a-f]{64}", str(record.get("manifest_sha256", ""))) is not None,
             "invalid_operation_receipt")
    return record


def _watermark(root: Path) -> dict | None:
    path = root / "watermark.json"
    if not path.exists() and not path.is_symlink():
        return None
    value = _decode(_read_regular(path, 4096))
    _require(isinstance(value, dict)
             and set(value) == {"generation", "manifest_sha256", "run_id", "run_number", "run_attempt"}
             and _positive(value["run_number"]) and _positive(value["run_attempt"], 10**10-1)
             and isinstance(value["run_id"], str)
             and re.fullmatch(r"[1-9][0-9]{0,19}", value["run_id"]) is not None
             and value["generation"] == f"daily-{value['run_id']}-{value['run_attempt']}"
             and re.fullmatch(r"[0-9a-f]{64}", str(value["manifest_sha256"])) is not None,
             "invalid_watermark")
    return value


class _BoundedInput:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.count = 0

    def read(self, size: int = -1) -> bytes:
        amount = min(size if size >= 0 else 65536, MAX_BUNDLE_BYTES - self.count + 1)
        data = self.stream.read(amount)
        self.count += len(data)
        _require(self.count <= MAX_BUNDLE_BYTES, "bundle_size_limit")
        return data


def _extract(stream: BinaryIO, stage: Path, operation_id: str, manifest_sha256: str) -> dict:
    """Read strict USTAR regular members; inspect headers before any body read."""
    payload = stage / "payload"
    payload.mkdir(mode=0o755)
    bounded = _BoundedInput(stream)
    document = None
    seen = set()
    expected = {}

    def read_exact(size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = bounded.read(min(65536, size - len(data)))
            _require(bool(chunk), "truncated_archive")
            data.extend(chunk)
        return bytes(data)

    while True:
        header = read_exact(tarfile.BLOCKSIZE)
        if header == b"\0" * tarfile.BLOCKSIZE:
            _require(read_exact(tarfile.BLOCKSIZE) == header, "invalid_archive_end")
            while True:
                padding = bounded.read(65536)
                if not padding:
                    break
                _require(not padding.strip(b"\0"), "trailing_archive_data")
            break
        try:
            # Unlike TarFile iteration, frombuf does not consume extension bodies.
            member = tarfile.TarInfo.frombuf(header, encoding="ascii", errors="strict")
        except (tarfile.TarError, UnicodeError, ValueError):
            raise DeliveryError("invalid_archive_header") from None
        _require(header[257:263] == tarfile.POSIX_MAGIC[:6]
                 and member.type == tarfile.REGTYPE and not member.linkname,
                 "archive_member_type")
        _require(member.name not in seen, "duplicate_archive_member")
        seen.add(member.name)
        _require(len(seen) <= MAX_FILES + 1, "archive_member_limit")
        if document is None:
            _require(member.name == "manifest.json"
                     and 0 < member.size <= MAX_MANIFEST_BYTES, "archive_manifest")
            raw = read_exact(member.size)
            _require(_digest(raw) == manifest_sha256, "manifest_digest")
            document = validate_manifest(_decode(raw))
            _require(document["generation"] == operation_id, "operation_identity")
            _require(shutil.disk_usage(stage).free
                     >= document["total_bytes"] + 1024 * 1024 * 1024, "insufficient_disk")
            expected = {"payload/" + item["name"]: item for item in document["files"]}
            with (stage / "manifest.json").open("xb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
        else:
            _require(member.name in expected, "unexpected_archive_member")
            entry = expected[member.name]
            _require(member.size == entry["size"], "archive_member_size")
            digest = hashlib.sha256()
            remaining = member.size
            destination = payload / entry["name"]
            with destination.open("xb") as output:
                while remaining:
                    chunk = read_exact(min(1024 * 1024, remaining))
                    remaining -= len(chunk)
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            _require(digest.hexdigest() == entry["sha256"], "archive_payload_digest")
            destination.chmod(0o644)
        padding_size = (-member.size) % tarfile.BLOCKSIZE
        _require(read_exact(padding_size) == b"\0" * padding_size, "invalid_archive_padding")
    _require(document is not None and seen == {"manifest.json"} | set(expected),
             "incomplete_archive")
    validate_payload(payload, document)
    os.chmod(payload, 0o755)
    os.chmod(stage, 0o755)
    _sync_directory(payload)
    _sync_directory(stage)
    return document

def _enforce_order(root: Path, document: dict, digest: str) -> None:
    watermark = _watermark(root)
    if watermark is None:
        _require(not any((root / "generations").iterdir())
                 and not any((root / "operations").iterdir())
                 and not (root / "current").exists()
                 and not (root / "current").is_symlink(), "missing_watermark")
        return
    old_order = (watermark["run_number"], watermark["run_attempt"])
    new_order = (document["run_number"], document["run_attempt"])
    _require(new_order >= old_order, "older_generation")
    if document["run_number"] == watermark["run_number"]:
        _require(document["run_id"] == watermark["run_id"], "run_identity_conflict")
    if new_order == old_order:
        _require(document["generation"] == watermark["generation"]
                 and digest == watermark["manifest_sha256"], "generation_conflict")


def _prune_known_generations(root: Path, keep: set[str]) -> list[str]:
    """Only remove verified terminal generations; preserve unknown effects."""
    retained = []
    for directory in (root / "generations").iterdir():
        if directory.name in keep:
            continue
        try:
            record = _operation(root, directory.name)
            if record is None or record["state"] not in {"published", "rolled_back"}:
                retained.append(directory.name)
                continue
            _document, digest = _generation(root, directory.name)
            _require(digest == record["manifest_sha256"], "generation_conflict")
            shutil.rmtree(directory)
        except (DeliveryError, OSError):
            # Cleanup cannot erase the successful selection or justify deleting
            # a generation whose identity could not be verified.
            retained.append(directory.name)
    return retained


def _receive_result(
    root: Path, operation_id: str, manifest_sha256: str,
    current: dict | None, current_digest: str | None,
) -> dict | None:
    """Reconcile a durable operation before accepting a new selection."""
    current_id = current["generation"] if current else None
    existing = _operation(root, operation_id)
    if existing is not None:
        _require(existing["manifest_sha256"] == manifest_sha256, "generation_conflict")
        _require(existing["state"] != "rolled_back", "operation_rolled_back")
    if current_id == operation_id:
        _require(current_digest == manifest_sha256 and existing is not None,
                 "current_receipt_conflict")
        if existing["state"] == "prepared":
            existing = {**existing, "state": "published", "finished_at_utc": _utc_now()}
            _write_json(root / "operations" / (operation_id + ".json"), existing)
        return {**existing, "current": current_id}
    if existing is not None and existing["state"] == "published":
        return {**existing, "state": "published_superseded", "current": current_id}
    return None


def receive_bundle(
    stream: BinaryIO, app_dir: Path = APP_ROOT, *, expected_predecessor: str | None,
    operation_id: str, manifest_sha256: str, lock_path: Path = LOCK_FILE,
    lock_timeout: float = 5.0,
) -> dict:
    _require(GENERATION_RE.fullmatch(operation_id) is not None, "invalid_operation")
    _require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is not None, "invalid_digest")
    _require(expected_predecessor is None
             or GENERATION_RE.fullmatch(expected_predecessor) is not None, "invalid_predecessor")
    with _locked(lock_path, timeout=lock_timeout):
        root = _store(app_dir, create=True)
        _links(app_dir, repair=False)
        current, current_digest = _current(root)
        result = _receive_result(root, operation_id, manifest_sha256, current, current_digest)
        if result is not None:
            return result
        current_id = current["generation"] if current else None
        _require(current_id == expected_predecessor, "predecessor_changed")
        root_info = root.stat()
        root_identity = (root_info.st_dev, root_info.st_ino)
        stage = Path(tempfile.mkdtemp(prefix=".incoming-", dir=root))

    # A slow or broken upload must not occupy the ordinary updater's lock.
    # This private staging directory is never selected or pruned by another writer.
    try:
        document = _extract(stream, stage, operation_id, manifest_sha256)
        with _locked(lock_path, timeout=lock_timeout):
            root = _store(app_dir)
            _require(root is not None, "store_changed")
            root_info = root.stat()
            _require((root_info.st_dev, root_info.st_ino) == root_identity, "store_changed")
            _links(app_dir, repair=False)
            current, current_digest = _current(root)
            result = _receive_result(root, operation_id, manifest_sha256, current, current_digest)
            if result is not None:
                return result
            current_id = current["generation"] if current else None
            _require(current_id == expected_predecessor, "predecessor_changed")
            _plain_dir(stage)
            _require({item.name for item in stage.iterdir()} == {"manifest.json", "payload"},
                     "generation_census")
            _require(_digest(_read_regular(stage / "manifest.json", MAX_MANIFEST_BYTES))
                     == manifest_sha256, "manifest_digest")
            validate_payload(stage / "payload", document)
            _enforce_order(root, document, manifest_sha256)
            destination = root / "generations" / operation_id
            if destination.exists() or destination.is_symlink():
                _old, old_digest = _generation(root, operation_id)
                _require(old_digest == manifest_sha256, "generation_conflict")
            else:
                os.rename(stage, destination)
                _sync_directory(destination.parent)
            record = {
                "schema": SCHEMA, "state": "prepared", "generation": operation_id,
                "manifest_sha256": manifest_sha256, "predecessor": current_id,
                "source_sha": document["source_sha"], "run_id": document["run_id"],
                "run_number": document["run_number"], "run_attempt": document["run_attempt"],
                "file_count": len(document["files"]), "total_bytes": document["total_bytes"],
                "prepared_at_utc": _utc_now(),
            }
            _write_json(root / "operations" / (operation_id + ".json"), record)
            # Keep the ordering fence even if the pointer transition is interrupted
            # or an explicitly fenced rollback later selects the predecessor.
            _write_json(root / "watermark.json", {
                key: record[key] for key in
                ("generation", "manifest_sha256", "run_id", "run_number", "run_attempt")
            })
            _links(app_dir, repair=True)
            _select(root, operation_id)
            record.update(state="published", finished_at_utc=_utc_now())
            _write_json(root / "operations" / (operation_id + ".json"), record)
            keep = {operation_id}
            if current_id is not None:
                keep.add(current_id)
            retained = _prune_known_generations(root, keep)
            return {**record, "current": operation_id,
                    "unpruned_generation_count": len(retained)}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def receiver_status(
    app_dir: Path = APP_ROOT, *, operation_id: str | None = None,
    lock_path: Path = LOCK_FILE, lock_timeout: float = 5.0,
) -> dict:
    with _locked(lock_path, timeout=lock_timeout):
        root = _store(app_dir)
        if root is None:
            return {"schema": SCHEMA, "state": "not_installed", "current": None,
                    "manifest_sha256": None, "operation": None}
        current, digest = _current(root)
        result = {
            "schema": SCHEMA, "state": "ready" if current else "not_installed",
            "current": current["generation"] if current else None,
            "manifest_sha256": digest,
            "operation": _operation(root, operation_id) if operation_id else None,
        }
        if current is not None:
            result.update(run_number=current["run_number"], run_attempt=current["run_attempt"],
                          file_count=len(current["files"]), total_bytes=current["total_bytes"],
                          source_sha=current["source_sha"])
        return result


def reconcile(
    app_dir: Path = APP_ROOT, *, lock_fd: int | None = None,
    lock_path: Path = LOCK_FILE, lock_timeout: float = 5.0,
) -> dict:
    with _locked(lock_path, inherited_fd=lock_fd, timeout=lock_timeout):
        root = _store(app_dir)
        _links(app_dir, repair=False)
        if root is None:
            return {"schema": SCHEMA, "state": "not_installed", "current": None}
        current, digest = _current(root)
        if current is None:
            return {"schema": SCHEMA, "state": "not_installed", "current": None}
        _links(app_dir, repair=True)
        return {"schema": SCHEMA, "state": "reconciled", "current": current["generation"],
                "manifest_sha256": digest, "file_count": len(current["files"])}


def rollback_generation(
    app_dir: Path = APP_ROOT, *, expected_current: str, predecessor: str,
    lock_path: Path = LOCK_FILE, lock_timeout: float = 5.0,
) -> dict:
    with _locked(lock_path, timeout=lock_timeout):
        root = _store(app_dir)
        _require(root is not None, "not_installed")
        current, digest = _current(root)
        _require(current is not None and current["generation"] == expected_current,
                 "rollback_current_changed")
        record = _operation(root, expected_current)
        _require(record is not None and record["manifest_sha256"] == digest
                 and record.get("predecessor") == predecessor, "rollback_predecessor")
        _previous, previous_digest = _generation(root, predecessor)
        previous_record = _operation(root, predecessor)
        _require(previous_record is not None
                 and previous_record["state"] in {"prepared", "published"}
                 and previous_record["manifest_sha256"] == previous_digest,
                 "rollback_receipt_conflict")
        _links(app_dir, repair=False)
        _links(app_dir, repair=True)
        _select(root, predecessor)
        record.update(state="rolled_back", rolled_back_to=predecessor,
                      rolled_back_at_utc=_utc_now())
        _write_json(root / "operations" / (expected_current + ".json"), record)
        return {"schema": SCHEMA, "state": "rolled_back", "generation": expected_current,
                "current": predecessor, "manifest_sha256": digest}


def _trusted_publication(document: dict, environment: Mapping[str, str]) -> None:
    _require(environment.get("GITHUB_REPOSITORY") == REPOSITORY
             and environment.get("GITHUB_REF") == "refs/heads/main"
             and environment.get("GITHUB_WORKFLOW_REF") == WORKFLOW, "untrusted_workflow")
    for field, variable in (("run_id", "GITHUB_RUN_ID"), ("run_number", "GITHUB_RUN_NUMBER"),
                            ("run_attempt", "GITHUB_RUN_ATTEMPT")):
        _require(environment.get(variable) == str(document[field]), "receipt_from_another_run")


def _ssh(arguments: list[str], *, ssh_key: Path, stdin_path: Path | None = None) -> dict:
    """Fixed destination, pinned identity, bounded output, and no raw SSH diagnostics."""
    key_info = ssh_key.lstat()
    _require(stat.S_ISREG(key_info.st_mode) and key_info.st_nlink == 1
             and key_info.st_mode & 0o077 == 0, "unsafe_key_file")
    _read_regular(HOST_PIN, 4096)
    remote = shlex.join(["/usr/bin/python3", "/opt/macro/scripts/publish_ohlc.py", *arguments])
    command = [
        "ssh", "-F", "/dev/null", "-T", "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "GlobalKnownHostsFile=/dev/null", "-o", f"UserKnownHostsFile={HOST_PIN}",
        "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1",
        "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
        "-i", str(ssh_key), SSH_TARGET, remote,
    ]
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        incoming = stdin_path.open("rb") if stdin_path else subprocess.DEVNULL
        try:
            try:
                result = subprocess.run(
                    command, stdin=incoming, stdout=output, stderr=errors,
                    timeout=960 if stdin_path else 60, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                raise DeliveryError("transport_unknown") from None
        finally:
            if stdin_path:
                incoming.close()
        _require(output.tell() <= 65536, "remote_output_limit")
        output.seek(0)
        raw = output.read(65537)
    try:
        response = _decode(raw)
        _require(isinstance(response, dict) and response.get("schema") == SCHEMA,
                 "remote_protocol")
    except DeliveryError:
        raise DeliveryError("transport_unknown") from None
    if result.returncode != 0:
        code = response.get("code", "")
        _require(isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,64}", code) is not None,
                 "transport_unknown")
        raise DeliveryError(code)
    return response


def _sender_unknown(start: dict, code: str) -> dict:
    return {"schema": SCHEMA, "state": "unknown", "generation": start["generation"],
            "manifest_sha256": start["manifest_sha256"], "code": code}


def _reconcile_sender(start: dict, ssh_key: Path) -> dict:
    """Read the original operation; never resend after a lost acknowledgment."""
    try:
        status = _ssh(["status", "--operation", start["generation"]], ssh_key=ssh_key)
        record = status.get("operation")
        same = (isinstance(record, dict) and record.get("generation") == start["generation"]
                and record.get("manifest_sha256") == start["manifest_sha256"])
        if (same and record.get("state") in {"prepared", "published"}
                and status.get("current") == start["generation"]
                and status.get("manifest_sha256") == start["manifest_sha256"]):
            return {"schema": SCHEMA, "state": "published_reconciled",
                    "generation": start["generation"], "manifest_sha256": start["manifest_sha256"],
                    "current": status["current"], "reconciled_at_utc": _utc_now()}
        if (same and record.get("state") == "published"
                and status.get("current") not in (None, start["generation"])):
            return {"schema": SCHEMA, "state": "published_superseded",
                    "generation": start["generation"], "manifest_sha256": start["manifest_sha256"],
                    "current": status["current"], "reconciled_at_utc": _utc_now()}
        if same and record.get("state") == "rolled_back":
            return {"schema": SCHEMA, "state": "refused", "generation": start["generation"],
                    "manifest_sha256": start["manifest_sha256"], "code": "operation_rolled_back"}
        return _sender_unknown(start, "operation_not_confirmed")
    except DeliveryError as exc:
        return _sender_unknown(start, exc.code)
    except Exception:
        return _sender_unknown(start, "status_unavailable")


def _save_sender_result(path: Path, start: dict, result: dict) -> dict:
    try:
        _write_json(path, result)
    except Exception:
        # The remote selection may already be complete. A local receipt failure
        # cannot turn that uncertain/applied effect into a pre-effect refusal.
        return _sender_unknown(start, "result_receipt_unwritten")
    return result


def publish(
    manifest_path: Path, payload_dir: Path, evidence_dir: Path, ssh_key: Path,
    *, environment: Mapping[str, str] | None = None,
) -> dict:
    raw = _read_regular(manifest_path, MAX_MANIFEST_BYTES)
    document = validate_manifest(_decode(raw))
    _trusted_publication(document, os.environ if environment is None else environment)
    digest = _digest(raw)
    _require(not evidence_dir.is_symlink(), "foreign_evidence_directory")
    evidence_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    _plain_dir(evidence_dir)
    _require({path.name for path in evidence_dir.iterdir()} <= {"operation.json", "result.json"},
             "foreign_evidence_directory")
    intent_path = evidence_dir / "operation.json"
    result_path = evidence_dir / "result.json"
    if intent_path.exists() or intent_path.is_symlink():
        start = _decode(_read_regular(intent_path, 16384))
        _require(isinstance(start, dict) and start.get("schema") == SCHEMA
                 and start.get("state") == "started"
                 and start.get("generation") == document["generation"]
                 and start.get("manifest_sha256") == digest, "operation_identity_conflict")
        return _save_sender_result(result_path, start, _reconcile_sender(start, ssh_key))
    _require(not result_path.exists() and not result_path.is_symlink(), "orphan_result")
    validate_payload(payload_dir, document)
    start = None
    try:
        with tempfile.TemporaryDirectory(prefix="macro-ohlc-bundle-") as directory:
            _require(shutil.disk_usage(directory).free
                     >= document["total_bytes"] + 1024 * 1024 * 1024, "insufficient_disk")
            bundle = Path(directory) / "bundle.tar"
            build_bundle(payload_dir, manifest_path, bundle)
            status = _ssh(["status"], ssh_key=ssh_key)
            predecessor = status.get("current")
            _require(status.get("state") in {"ready", "not_installed"}
                     and (predecessor is None or isinstance(predecessor, str)
                          and GENERATION_RE.fullmatch(predecessor) is not None),
                     "remote_protocol")
            start = {
                "schema": SCHEMA, "state": "started", "generation": document["generation"],
                "manifest_sha256": digest, "expected_predecessor": predecessor,
                "source_sha": document["source_sha"], "started_at_utc": _utc_now(),
            }
            # Exclusive durable intent precedes the only mutating transport call.
            # Concurrent copies of the same workflow attempt cannot both send.
            _write_json(intent_path, start, exclusive=True)
            try:
                result = _ssh(
                    ["receive", "--operation", document["generation"],
                     "--manifest-sha256", digest,
                     "--expected-predecessor", predecessor or "none"],
                    ssh_key=ssh_key, stdin_path=bundle,
                )
                _require(result.get("generation") == document["generation"]
                         and result.get("manifest_sha256") == digest
                         and result.get("state") in {"published", "published_superseded"},
                         "publication_ack_unknown")
            except Exception as exc:
                code = exc.code if isinstance(exc, DeliveryError) else "publication_ack_unknown"
                _save_sender_result(result_path, start, _sender_unknown(start, code))
                result = _reconcile_sender(start, ssh_key)
            result = _save_sender_result(result_path, start, result)
        return result
    except Exception:
        if start is None:
            raise
        # Includes post-intent receipt and temporary-directory cleanup failures.
        # The only remaining transport is a read of the original operation.
        return _save_sender_result(result_path, start, _reconcile_sender(start, ssh_key))


def _receive_deadline(_signum, _frame):
    raise DeliveryError("receive_timeout")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sender = commands.add_parser("publish")
    for argument in ("manifest", "payload-dir", "evidence-dir", "ssh-key"):
        sender.add_argument("--" + argument, required=True, type=Path)
    receiver = commands.add_parser("receive")
    receiver.add_argument("--operation", required=True)
    receiver.add_argument("--manifest-sha256", required=True)
    receiver.add_argument("--expected-predecessor", required=True)
    status = commands.add_parser("status")
    status.add_argument("--operation")
    repair = commands.add_parser("reconcile")
    repair.add_argument("--lock-fd", type=int)
    rollback = commands.add_parser("rollback")
    rollback.add_argument("--expected-current", required=True)
    rollback.add_argument("--predecessor", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "publish":
            result = publish(args.manifest, args.payload_dir, args.evidence_dir, args.ssh_key)
        elif args.command == "receive":
            import signal

            previous_handler = signal.signal(signal.SIGALRM, _receive_deadline)
            signal.alarm(900)
            try:
                result = receive_bundle(
                    sys.stdin.buffer, expected_predecessor=(
                        None if args.expected_predecessor == "none" else args.expected_predecessor),
                    operation_id=args.operation, manifest_sha256=args.manifest_sha256,
                )
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous_handler)
        elif args.command == "status":
            result = receiver_status(operation_id=args.operation)
        elif args.command == "reconcile":
            result = reconcile(lock_fd=args.lock_fd)
        else:
            result = rollback_generation(
                expected_current=args.expected_current, predecessor=args.predecessor)
    except DeliveryError as exc:
        # A receiver can be interrupted after pointer selection. Treat an
        # unconfirmed command effect as unknown until its original receipt is read.
        result = {"schema": SCHEMA, "state": "unknown" if args.command in {"receive", "rollback"}
                  else "refused", "code": exc.code}
    except Exception:
        result = {"schema": SCHEMA, "state": "unknown" if args.command in {"receive", "rollback"}
                  else "refused", "code": "internal_error"}
    print(json.dumps(result, sort_keys=True))
    return 2 if result["state"] in {"unknown", "refused"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
