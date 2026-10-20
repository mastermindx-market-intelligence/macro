"""BEA GVC byte-only staging, subordinate to the existing Data OS owner.

No source fetching, registry edits, native clock rewriting, admission, user
serving, trading, or historical PIT.  The existing candidate producer alone
validates original BEA bytes/lineage.  A caller-supplied digest is NOT trusted
authentication; a stage receipt is not a Data OS installation receipt.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib import import_module
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Mapping

STAGE_SCHEMA = "mastermind.bea_gvc_bytes_staged_unadmitted/v1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}\Z")


class BEAGVCStageRefused(ValueError):
    """Unqualified or incomplete candidate cannot be staged."""


@dataclass(frozen=True, slots=True)
class BEAGVCStageReceipt:
    source_generation_id: str
    candidate_manifest_sha256: str
    candidate_index_sha256: str
    relative_directory: str
    source_response_count: int
    source_file_count: int
    capture_receipt_count: int
    industry_count: int
    total_industry_rows: int
    state: str = "STAGED_NOT_INSTALLED"
    dataos_native_admitted: bool = False
    may_publish: bool = False
    may_rank: bool = False
    may_trade: bool = False
    historical_pit_eligible: bool = False
    schema: str = STAGE_SCHEMA

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _digest(value: object) -> str:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise BEAGVCStageRefused("exact lowercase SHA-256 required")
    return value


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _checked_root(root: Path) -> Path:
    if not isinstance(root, Path) or not root.is_absolute():
        raise BEAGVCStageRefused("absolute Path staging root required")
    if root.is_symlink() or not root.is_dir():
        raise BEAGVCStageRefused("staging root is not a real directory")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise BEAGVCStageRefused("staging root unavailable") from exc
    if resolved != root:
        raise BEAGVCStageRefused("staging root traverses a symlink")
    return resolved


def _relative(name: object) -> PurePosixPath:
    if type(name) is not str or not name or "\\" in name or "\x00" in name:
        raise BEAGVCStageRefused("unsafe staging path")
    rel = PurePosixPath(name)
    if (rel.is_absolute() or rel.as_posix() != name
            or any(part in (".", "..", "") for part in rel.parts)):
        raise BEAGVCStageRefused("noncanonical staging path")
    return rel


def _write_exact(base: Path, name: str, value: bytes) -> None:
    rel = _relative(name)
    if type(value) is not bytes:
        raise BEAGVCStageRefused("immutable stage bytes required")
    target = base.joinpath(*rel.parts)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exact 0600 at creation: a permissive umask must never make candidate
    # originals or receipts world-readable even for a moment.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(value)
        out.flush()
        os.fsync(out.fileno())
    if _sha(target.read_bytes()) != _sha(value):
        raise BEAGVCStageRefused("stage readback mismatch")


def _fsync_directory(path: Path) -> None:
    """Durability barrier on stage directory entries; refuse an unproven sync."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _stage_verified_bytes(
    root: Path, *, generation: str, files: Mapping[str, bytes],
    receipt: BEAGVCStageReceipt,
) -> BEAGVCStageReceipt:
    """Private filesystem component; verified source admission is NOT implied.

    Only the incumbent Data OS owner may invoke this with real sources under
    its external writer/lease fence. No new lease, store selector or publication
    plane is created. The complete stage is made visible after all writes.
    """
    root = _checked_root(root)
    generation = _digest(generation)
    if (receipt.source_generation_id != generation
            or receipt.relative_directory != f"candidate-{generation}"
            or receipt.state != "STAGED_NOT_INSTALLED"):
        raise BEAGVCStageRefused("wrong candidate stage receipt")
    if any((receipt.dataos_native_admitted, receipt.may_publish, receipt.may_rank,
            receipt.may_trade, receipt.historical_pit_eligible)):
        raise BEAGVCStageRefused("stage cannot grant native authority")
    if not isinstance(files, dict) or not files or "stage_receipt.json" in files:
        raise BEAGVCStageRefused("complete byte map and owner receipt required")
    if any(type(blob) is not bytes for blob in files.values()):
        raise BEAGVCStageRefused("malformed stage bytes")
    for name in files:
        _relative(name)
    final = root / f"candidate-{generation}"
    if final.exists() or final.is_symlink():
        raise BEAGVCStageRefused("candidate generation already staged")
    temp = Path(tempfile.mkdtemp(dir=root, prefix=f".pending-bea-{generation[:12]}-"))
    try:
        for name, blob in sorted(files.items()):
            _write_exact(temp, name, blob)
        _write_exact(temp, "stage_receipt.json", _canonical(receipt.as_dict()))
        if final.exists() or final.is_symlink():
            raise BEAGVCStageRefused("candidate stage collision")
        # File content fsync is insufficient for nested path metadata.
        # Flush all newly-created directories before atomically exposing it.
        for folder in sorted((p for p in temp.rglob("*") if p.is_dir()),
                             key=lambda p: len(p.parts), reverse=True):
            _fsync_directory(folder)
        _fsync_directory(temp)
        os.rename(temp, final)
        # If this final durability barrier fails, the stage may already be
        # visible. Do not silently undo or retry an uncertain effect; the
        # original owner must reconcile its generation directory first.
        _fsync_directory(root)
        return receipt
    except BaseException:
        if temp.exists():
            shutil.rmtree(temp)
        raise


def stage_native_bea_gvc_candidate(
    candidate: object, *, root: Path, expected_manifest_sha256: str,
    expected_index_sha256: str,
) -> BEAGVCStageReceipt:
    """Pre-stage the full candidate only; never install or publish.

    The native source producer is imported lazily so accepted current Macro
    remains importable before the held BEA producer is installed. No fallback
    parses original source bytes or bypasses denied read authority.
    """
    root = _checked_root(root)
    manifest_pin = _digest(expected_manifest_sha256)
    index_pin = _digest(expected_index_sha256)
    # This source module lives in held #9444, so it is deliberately absent
    # from main. A first-party 'from collectors import ...' is an invalid
    # import on main and is correctly rejected by the import-name CI guard.
    # Resolve the optional installed producer only at explicit stage time.
    # Never swallow a missing transitive dependency as 'source unavailable'.
    try:
        bea = import_module("collectors.bea_gvc_native")
    except ModuleNotFoundError as exc:
        if exc.name != "collectors.bea_gvc_native":
            raise
        raise BEAGVCStageRefused("native BEA source producer unavailable") from exc
    if not isinstance(candidate, bea.BEAGVCCandidate):
        raise BEAGVCStageRefused("native candidate object required")
    if _sha(candidate.manifest_bytes) != manifest_pin:
        raise BEAGVCStageRefused("candidate manifest differs from external pin")
    manifest = candidate.manifest
    if (manifest.get("candidate_state") != "BYTE_VERIFIED_NOT_INSTALLED"
            or manifest.get("accounting_years") != list(bea.YEARS)
            or manifest.get("source_response_count") != 72
            or manifest.get("expected_l1_rows") != 138 * 139 * 8
            or manifest.get("complete_2017_2024_panel") is not True
            or manifest.get("dataos_native_admitted") is not False
            or manifest.get("may_publish") is not False
            or manifest.get("native_ingested_at", "MISSING") is not None
            or manifest.get("native_revision_seq", "MISSING") is not None):
        raise BEAGVCStageRefused("not a full unadmitted May-2026 panel")
    # These are the incumbent producer's validations, not a second parser.
    index = bea.build_candidate_industry_index(candidate)
    if index.sha256 != index_pin or _sha(index.manifest_bytes) != index_pin:
        raise BEAGVCStageRefused("industry index differs from external pin")
    views = tuple(bea.iter_candidate_industry_views(candidate))
    view_bytes = {v.industry_code_exact: v.jsonl_bytes for v in views}
    if len(views) != 138 or len(view_bytes) != len(views):
        raise BEAGVCStageRefused("incomplete/duplicate industry views")
    bound = bea.compare_candidate_staged_view_bytes(
        index, view_bytes, expected_index_sha256=index_pin)
    if (bound.industry_files_checked != 138
            or bound.rows_checked != 138 * 139 * 8
            or bound.dataos_native_admitted or bound.may_publish):
        raise BEAGVCStageRefused("candidate byte population is not eligible")
    files: dict[str, bytes] = {
        "candidate_manifest.json": candidate.manifest_bytes,
        "candidate_index.json": index.manifest_bytes,
        "source_lineage.json": candidate.lineage_bytes,
    }
    identities: set[tuple[int, str]] = set()
    original_paths: set[str] = set()
    for src in candidate.sources:
        identity = (src.year, src.table_id)
        if (identity in identities or src.year not in bea.YEARS
                or src.table_id not in bea.TABLES):
            raise BEAGVCStageRefused("invalid original response identity")
        identities.add(identity)
        path = f"original_responses/{src.table_id}/{_digest(src.sha256)}.json"
        if path in files and files[path] != src.original_bytes:
            raise BEAGVCStageRefused("one source path claims different bytes")
        original_paths.add(path)
        files[path] = src.original_bytes
    if len(identities) != 72:
        raise BEAGVCStageRefused("incomplete L0 originals")
    capture: set[str] = set()
    for sha, data in candidate.capture_receipts:
        sha = _digest(sha)
        if sha in capture or _sha(data) != sha:
            raise BEAGVCStageRefused("invalid retained receipt bytes")
        capture.add(sha)
        files[f"capture_receipts/{sha}.json"] = data
    for view in views:
        code = view.industry_code_exact
        if type(code) is not str or not _CODE.fullmatch(code):
            raise BEAGVCStageRefused("unsafe industry exact code")
        files[f"industry_inputs/industry_{code}.jsonl"] = view.jsonl_bytes
    receipt = BEAGVCStageReceipt(
        source_generation_id=candidate.generation_id,
        candidate_manifest_sha256=manifest_pin,
        candidate_index_sha256=index_pin,
        relative_directory=f"candidate-{candidate.generation_id}",
        source_response_count=72,
        source_file_count=len(original_paths),
        capture_receipt_count=len(capture),
        industry_count=138,
        total_industry_rows=bound.rows_checked)
    return _stage_verified_bytes(root, generation=candidate.generation_id,
                                 files=files, receipt=receipt)


# -------------------------- Unadmitted byte readback --------------------------
# This is a post-stage integrity check for the SAME existing Data OS owner.  It
# cannot authenticate source custody, publisher axes, real ingestion clocks,
# licences or an admission decision.  Only the incumbent source/lease holder may
# use it on real source storage after separate resource permission is granted.
import stat as _stage_stat

_STAGE_META_LIMIT = 256 * 1024
_STAGE_RECEIPT_LIMIT = 16 * 1024
_STAGE_SOURCE_LIMIT = 4 * 1024 * 1024
_STAGE_INDUSTRY_LIMIT = 16 * 1024 * 1024
_STAGE_YEARS = tuple(range(2017, 2025))
_STAGE_TABLES = frozenset((
    "Use", "ImMatAll", "ImMatCan", "ImMatChi", "ImMatEur",
    "ImMatJap", "ImMatMex", "ImMatRoa", "ImMatRow",
))


def _stage_json_exact(blob: bytes, *, kind: str) -> dict[str, object]:
    """Reject ambiguous/noncanonical JSON before interpreting source metadata."""
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise BEAGVCStageRefused("duplicate staged metadata JSON key")
            result[key] = value
        return result

    def bad_constant(_: str) -> None:
        raise BEAGVCStageRefused("nonfinite staged metadata")

    try:
        value = json.loads(blob, object_pairs_hook=unique,
                           parse_constant=bad_constant)
        if type(value) is not dict or _canonical(value) != blob:
            raise BEAGVCStageRefused("noncanonical staged metadata")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, BEAGVCStageRefused):
            raise
        raise BEAGVCStageRefused("invalid staged metadata") from exc
    return value


from contextlib import contextmanager as _stage_contextmanager

@_stage_contextmanager
def _stage_pinned_dir(stage: Path):
    """Hold one no-follow generation inode throughout one readback pass."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(stage, flags)
    except OSError as exc:
        raise BEAGVCStageRefused("staged generation is unavailable") from exc
    try:
        attr = os.fstat(fd)
        if (not _stage_stat.S_ISDIR(attr.st_mode)
                or _stage_stat.S_IMODE(attr.st_mode) != 0o700):
            raise BEAGVCStageRefused("staged generation directory is not private")
        yield fd
    finally:
        os.close(fd)


def _stage_file_bytes(stage_fd: int, name: str, limit: int) -> bytes:
    """Open a leaf relative to a pinned stage inode, refusing all symlinks."""
    rel = _relative(name)
    dfd = os.dup(stage_fd)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    dir_flags = flags | getattr(os, "O_DIRECTORY", 0)
    try:
        for part in rel.parts[:-1]:
            child = os.open(part, dir_flags, dir_fd=dfd)
            os.close(dfd)
            dfd = child
            attr = os.fstat(dfd)
            if (not _stage_stat.S_ISDIR(attr.st_mode)
                    or _stage_stat.S_IMODE(attr.st_mode) != 0o700):
                raise BEAGVCStageRefused("staged directory permissions invalid")
        ffd = os.open(rel.name, flags, dir_fd=dfd)
    except OSError as exc:
        raise BEAGVCStageRefused("staged file cannot be read") from exc
    finally:
        os.close(dfd)
    with os.fdopen(ffd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (not _stage_stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or _stage_stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size <= 0 or before.st_size > limit):
            raise BEAGVCStageRefused("staged file has unsafe shape or access")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if (len(data) != before.st_size or len(data) > limit
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns):
            raise BEAGVCStageRefused("staged file changed during read")
        return data


def _stage_exact_inventory(stage_fd: int, files: set[str]) -> None:
    """Read-only full census bound to the same pinned directory inode."""
    got_files: set[str] = set()
    got_dirs: set[str] = set()
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)

    def visit(dir_fd: int, prefix: str) -> None:
        for name in os.listdir(dir_fd):
            path = f"{prefix}/{name}" if prefix else name
            _relative(path)
            attr = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            if _stage_stat.S_ISDIR(attr.st_mode):
                if _stage_stat.S_IMODE(attr.st_mode) != 0o700:
                    raise BEAGVCStageRefused("unsafe staged directory permissions")
                next_fd = os.open(name, flags, dir_fd=dir_fd)
                try:
                    got_dirs.add(path)
                    visit(next_fd, path)
                finally:
                    os.close(next_fd)
            elif _stage_stat.S_ISREG(attr.st_mode):
                if (_stage_stat.S_IMODE(attr.st_mode) != 0o600 or attr.st_nlink != 1):
                    raise BEAGVCStageRefused("unsafe staged file permissions")
                got_files.add(path)
            else:
                raise BEAGVCStageRefused("unsupported staged filesystem node")

    try:
        visit(stage_fd, "")
    except OSError as exc:
        raise BEAGVCStageRefused("staged directory inventory unavailable") from exc
    expected_dirs: set[str] = set()
    for name in files:
        rel = _relative(name)
        parent = rel.parent
        while parent.as_posix() != ".":
            expected_dirs.add(parent.as_posix())
            parent = parent.parent
    if got_files != files or got_dirs != expected_dirs:
        raise BEAGVCStageRefused("incomplete or extraneous staged generation")


def verify_unadmitted_bea_gvc_stage(
    *, root: Path, source_generation_id: str,
    expected_manifest_sha256: str, expected_index_sha256: str,
) -> BEAGVCStageReceipt:
    """Re-read *complete staged bytes*; NEVER promote them to native Data OS.

    All supplied pins are integrity expectations, NOT authentication. The owner
    must validate original source custody, rights and its external exclusive
    writer lease before calling this on a real staging root. This read does
    not produce an admitted reader, mutable registry status, current native
    clock, historical PIT claim, trade input or public API response. Receipt
    state remains STAGED_NOT_INSTALLED even when every byte matches.
    """
    root = _checked_root(root)
    generation = _digest(source_generation_id)
    manifest_pin = _digest(expected_manifest_sha256)
    index_pin = _digest(expected_index_sha256)
    if generation != manifest_pin:
        raise BEAGVCStageRefused("generation does not bind manifest digest")
    stage = root / f"candidate-{generation}"
    with _stage_pinned_dir(stage) as stage_fd:
        return _stage_verify_anchored_bytes(
            stage_fd=stage_fd, stage=stage, generation=generation,
            manifest_pin=manifest_pin, index_pin=index_pin)


def _stage_verify_anchored_bytes(
    *, stage_fd: int, stage: Path, generation: str,
    manifest_pin: str, index_pin: str,
) -> BEAGVCStageReceipt:
    """Byte-only check under one anchored stage inode and external writer fence."""
    receipt_raw = _stage_file_bytes(stage_fd, "stage_receipt.json", _STAGE_RECEIPT_LIMIT)
    receipt_value = _stage_json_exact(receipt_raw, kind="receipt")
    if set(receipt_value) != set(BEAGVCStageReceipt.__dataclass_fields__):
        raise BEAGVCStageRefused("stage receipt fields differ from owner schema")
    try:
        receipt = BEAGVCStageReceipt(**receipt_value)
    except TypeError as exc:
        raise BEAGVCStageRefused("stage receipt has invalid shape") from exc
    if (type(receipt.source_generation_id) is not str
            or receipt.source_generation_id != generation
            or receipt.relative_directory != stage.name
            or receipt.candidate_manifest_sha256 != manifest_pin
            or receipt.candidate_index_sha256 != index_pin
            or receipt.schema != STAGE_SCHEMA
            or receipt.state != "STAGED_NOT_INSTALLED"
            or any(value is not False for value in (
                receipt.dataos_native_admitted, receipt.may_publish,
                receipt.may_rank, receipt.may_trade,
                receipt.historical_pit_eligible))
            or any(type(value) is not int for value in (
                receipt.source_response_count, receipt.source_file_count,
                receipt.capture_receipt_count, receipt.industry_count,
                receipt.total_industry_rows))
            or receipt.source_response_count != 72
            or not 1 <= receipt.source_file_count <= 72
            or not 1 <= receipt.capture_receipt_count <= 72
            or receipt.industry_count != 138
            or receipt.total_industry_rows != 138 * 139 * 8):
        raise BEAGVCStageRefused("stage receipt does not bind an unadmitted full panel")

    manifest_bytes = _stage_file_bytes(stage_fd, "candidate_manifest.json",
                                       _STAGE_META_LIMIT)
    index_bytes = _stage_file_bytes(stage_fd, "candidate_index.json",
                                    _STAGE_META_LIMIT)
    if _sha(manifest_bytes) != manifest_pin or _sha(index_bytes) != index_pin:
        raise BEAGVCStageRefused("staged generation metadata digest mismatch")
    manifest = _stage_json_exact(manifest_bytes, kind="source candidate")
    index = _stage_json_exact(index_bytes, kind="candidate index")
    if (manifest.get("schema") != "mastermind.bea_gvc_source_candidate/v1"
            or manifest.get("candidate_state") != "BYTE_VERIFIED_NOT_INSTALLED"
            or manifest.get("l0_dataset_id") != "bea.gvc.may2026.original_responses"
            or manifest.get("l1_dataset_id") != "bea.gvc.may2026.industry_import_inputs"
            or manifest.get("accounting_years") != list(_STAGE_YEARS)
            or manifest.get("source_response_count") != 72
            or manifest.get("expected_l1_rows") != 138 * 139 * 8
            or manifest.get("complete_2017_2024_panel") is not True
            or manifest.get("publisher_edition_date") != "2026-05-21"
            or manifest.get("publication_precision") != "DAY"
            or manifest.get("dataos_native_admitted") is not False
            or manifest.get("may_publish") is not False
            or manifest.get("may_rank") is not False
            or manifest.get("may_trade") is not False
            or manifest.get("may_train") is not False
            or manifest.get("historical_pit_eligible") is not False
            or manifest.get("named_company_relationship") is not False
            or manifest.get("published_at", "MISSING") is not None
            or manifest.get("original_historical_available_at", "MISSING") is not None
            or manifest.get("native_known_at", "MISSING") is not None
            or manifest.get("native_ingested_at", "MISSING") is not None
            or manifest.get("native_revision_seq", "MISSING") is not None):
        raise BEAGVCStageRefused("candidate manifest does not describe an unadmitted full panel")
    revision = manifest.get("candidate_revision_seq")
    predecessor = manifest.get("supersedes_candidate_generation")
    if (type(revision) is not int or revision < 0
            or (revision == 0 and predecessor is not None)
            or (revision > 0 and (type(predecessor) is not str
                                  or not _SHA.fullmatch(predecessor)
                                  or predecessor == generation))):
        raise BEAGVCStageRefused("candidate correction linkage is malformed")
    lineage_sha = _digest(manifest.get("source_lineage_sha256"))
    producer_sha = _digest(manifest.get("producer_code_sha256"))
    if (index.get("schema") != "mastermind.bea_gvc_l1_candidate_index/v1"
            or index.get("candidate_state") != "BYTE_VERIFIED_NOT_INSTALLED"
            or index.get("dataset_id") != "bea.gvc.may2026.industry_import_inputs"
            or index.get("source_generation_id") != generation
            or index.get("source_lineage_sha256") != lineage_sha
            or index.get("producer_code_sha256") != producer_sha
            or index.get("accounting_years") != list(_STAGE_YEARS)
            or index.get("source_response_count") != 72
            or index.get("industry_count") != 138
            or index.get("row_count") != 138 * 139 * 8
            or index.get("publisher_edition_date") != "2026-05-21"
            or index.get("publication_precision") != "DAY"
            or index.get("dataos_native_admitted") is not False
            or index.get("may_publish") is not False
            or index.get("native_ingested_at", "MISSING") is not None
            or index.get("native_revision_seq", "MISSING") is not None):
        raise BEAGVCStageRefused("candidate index differs from full unadmitted source")

    sources = manifest.get("sources")
    views = index.get("views")
    if type(sources) is not list or len(sources) != 72:
        raise BEAGVCStageRefused("staged manifest lacks 72 source identities")
    if type(views) is not list or len(views) != 138:
        raise BEAGVCStageRefused("staged index lacks 138 views")
    expected_files: dict[str, tuple[str, int | None, int]] = {
        "candidate_manifest.json": (manifest_pin, len(manifest_bytes), _STAGE_META_LIMIT),
        "candidate_index.json": (index_pin, len(index_bytes), _STAGE_META_LIMIT),
        "source_lineage.json": (lineage_sha, None, _STAGE_META_LIMIT),
    }
    source_identities: set[tuple[int, str]] = set()
    receipt_shas: set[str] = set()
    for entry in sources:
        if type(entry) is not dict:
            raise BEAGVCStageRefused("invalid staged source identity")
        year = entry.get("accounting_year")
        table = entry.get("source_table_id")
        if (type(year) is not int or year not in _STAGE_YEARS
                or type(table) is not str or table not in _STAGE_TABLES):
            raise BEAGVCStageRefused("unknown source table or accounting year")
        if (year, table) in source_identities:
            raise BEAGVCStageRefused("duplicate staged source identity")
        source_identities.add((year, table))
        source_sha = _digest(entry.get("original_response_sha256"))
        captured_sha = _digest(entry.get("capture_receipt_sha256"))
        byte_count = entry.get("original_response_bytes")
        if type(byte_count) is not int or not 0 < byte_count <= _STAGE_SOURCE_LIMIT:
            raise BEAGVCStageRefused("invalid original source byte count")
        name = f"original_responses/{table}/{source_sha}.json"
        if name in expected_files and expected_files[name][1] != byte_count:
            raise BEAGVCStageRefused("one original digest claims different byte lengths")
        expected_files[name] = (source_sha, byte_count, _STAGE_SOURCE_LIMIT)
        receipt_shas.add(captured_sha)
    if len(source_identities) != 72:
        raise BEAGVCStageRefused("incomplete source year/table population")

    codes: set[str] = set()
    for entry in views:
        if type(entry) is not dict:
            raise BEAGVCStageRefused("invalid candidate index view")
        code = entry.get("industry_code_exact")
        if type(code) is not str or not _CODE.fullmatch(code) or code in codes:
            raise BEAGVCStageRefused("invalid or repeated exact industry code")
        codes.add(code)
        name = f"industry_inputs/industry_{code}.jsonl"
        proposed = f"data/bea/gvc/may2026/{name}"
        if entry.get("relative_storage_path_proposed_only") != proposed:
            raise BEAGVCStageRefused("index path is not the expected unadmitted candidate")
        byte_count = entry.get("jsonl_bytes")
        row_count = entry.get("row_count")
        if (type(byte_count) is not int or not 0 < byte_count <= _STAGE_INDUSTRY_LIMIT
                or type(row_count) is not int or row_count != 139 * 8):
            raise BEAGVCStageRefused("index view population is incomplete")
        expected_files[name] = (_digest(entry.get("jsonl_sha256")),
                                byte_count, _STAGE_INDUSTRY_LIMIT)
    for receipt_sha in receipt_shas:
        expected_files[f"capture_receipts/{receipt_sha}.json"] = (
            receipt_sha, None, _STAGE_META_LIMIT)
    if (receipt.source_file_count != len(expected_files) - 3 - 138 - len(receipt_shas)
            or receipt.capture_receipt_count != len(receipt_shas)):
        raise BEAGVCStageRefused("stage receipt file census differs from source")

    expected_names = set(expected_files) | {"stage_receipt.json"}
    _stage_exact_inventory(stage_fd, expected_names)
    for name, (digest, length, limit) in expected_files.items():
        value = _stage_file_bytes(stage_fd, name, limit)
        if _sha(value) != digest or (length is not None and len(value) != length):
            raise BEAGVCStageRefused("staged source/index bytes do not match pinned generation")
        if (name.startswith("industry_inputs/")
                and (value.count(b"\n") != 139 * 8 or not value.endswith(b"\n"))):
            raise BEAGVCStageRefused("candidate view row count is not byte-observed")
    # Refuse a late extra/missing file even if it arrived during the scan;
    # the existing Data OS owner must independently fence concurrent writers.
    _stage_exact_inventory(stage_fd, expected_names)
    # Complete byte integrity is a prerequisite, NEVER an installation/rights
    # proof. The receipt's identical state and disabled authority flags remain.
    return receipt
