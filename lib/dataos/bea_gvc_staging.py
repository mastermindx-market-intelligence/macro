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
