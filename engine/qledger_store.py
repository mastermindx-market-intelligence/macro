"""Read-only, unactivated QLedger segmented-history compatibility seam.

Source-only Wave A candidate for research/QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md.
NOT wired into qledger.py, publishers or production readers; no registration,
rewrite, grading, evidence-clock, migration or publishing effect.

Callers MUST supply a read_blob(relative_path) bound to ONE immutable Git tree
or single coherent transaction snapshot. A live, changing filesystem is NOT
a qualified provider. All members are integrity-checked before returning rows.
The proposed v0 format is not approved for activation; physical names, limits,
revision semantics and multi-writer promotion require native owner acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Callable

ROOT_PATH = "data/qledger/claims.parts.root.json"
BASE_PATH = "data/qledger/claims.jsonl"
INDEX_PREFIX = "data/qledger/claims.parts/index/"
DATA_PREFIX = "data/qledger/claims.parts/parts/"
SCHEMA = "mastermind.qledger.segmentation-read.v0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TX_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_PATH_CHARS = re.compile(r"[A-Za-z0-9_./-]+\Z")


class StoreIntegrityError(ValueError):
    """No complete, trustworthy logical history can be returned."""


@dataclass(frozen=True)
class ReadLimits:
    max_root_bytes: int = 16 * 1024
    max_index_bytes: int = 1 * 1024 * 1024
    max_part_bytes: int = 64 * 1024 * 1024
    max_base_bytes: int = 100_000_000
    max_fanout: int = 128
    max_depth: int = 8
    max_parts: int = 100_000


@dataclass(frozen=True)
class ReadReceipt:
    mode: str
    source_present: bool
    member_count: int
    raw_line_count: int
    claim_count: int
    occurrence_digest: str
    generation: str | None


@dataclass(frozen=True)
class ReadResult:
    """Complete read; callers keep their own first/last/duplicate policies."""

    raw_lines: tuple[str, ...]
    receipt: ReadReceipt

    def load_claims(self) -> list[object]:
        """Match qledger._read_jsonl: skip malformed/empty, never globally dedupe."""
        result: list[object] = []
        for line in self.raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except Exception:  # noqa: BLE001 -- native legacy policy
                continue
        return result


def _fail(reason: str) -> None:
    raise StoreIntegrityError(reason)


def _object_no_dup(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON property")
        result[key] = value
    return result


def _json_object(data: bytes, where: str) -> dict:
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_object_no_dup)
    except StoreIntegrityError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise StoreIntegrityError(f"invalid {where} JSON") from exc
    if not isinstance(parsed, dict):
        _fail(f"{where} must be an object")
    return parsed


def _shape(obj: dict, keys: set[str], where: str) -> None:
    if set(obj) != keys:
        _fail(f"invalid {where} fields")


def _int(v: object, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(v) is not int or v < minimum or (maximum is not None and v > maximum):
        _fail("invalid bounded integer")
    return v


def _digest(d: object) -> str:
    if not isinstance(d, str) or not _SHA256.fullmatch(d):
        _fail("invalid sha256")
    return d


def _path(p: object, prefix: str) -> str:
    if (not isinstance(p, str) or not _PATH_CHARS.fullmatch(p)
            or ".." in p.split("/") or "." in p.split("/")
            or "//" in p or not p.startswith(prefix)
            or PurePosixPath(p).as_posix() != p or p.endswith("/")):
        _fail("invalid catalog member path")
    return p


def _ref(obj: object, prefix: str, maximum: int) -> tuple[str, str, int]:
    if not isinstance(obj, dict):
        _fail("reference must be an object")
    _shape(obj, {"path", "sha256", "bytes"}, "member reference")
    return (_path(obj["path"], prefix), _digest(obj["sha256"]),
            _int(obj["bytes"], maximum=maximum))


def _read_member(read_blob: Callable[[str], bytes | None], path: str,
                 expected_sha: str, size: int) -> bytes:
    try:
        raw = read_blob(path)
    except (OSError, KeyError) as exc:
        raise StoreIntegrityError("catalog member unavailable") from exc
    if not isinstance(raw, bytes):
        _fail("catalog member missing or nonbytes")
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("catalog member digest/length mismatch")
    return raw


def _lines(data: bytes) -> tuple[str, ...]:
    try:
        return tuple(data.decode("utf-8").splitlines())
    except UnicodeError as exc:
        raise StoreIntegrityError("invalid UTF-8 in claims member") from exc


def _receipt(mode: str, present: bool, members: list[bytes],
             rows: tuple[str, ...], generation: str | None,
             actual_claims: int) -> ReadReceipt:
    # Row-length framing preserves logical occurrence order, never assigns
    # a business claim ID or constitutes a new financial evidence score.
    h = hashlib.sha256()
    for line in rows:
        raw = line.encode("utf-8")
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return ReadReceipt(mode, present, len(members), len(rows), actual_claims,
                       h.hexdigest(), generation)


def read_claims_snapshot(read_blob: Callable[[str], bytes | None],
                         *, limits: ReadLimits = ReadLimits()) -> ReadResult:
    """Preflight exact legacy bytes or a complete unactivated segmented tree.

    Absent catalog => incumbent legacy behavior. Present but broken catalog =>
    integrity error, NOT fallback to old history or silent zero coverage.
    Source provider must pin every read to the same immutable generation.
    """
    root_raw = read_blob(ROOT_PATH)
    if root_raw is None:
        legacy = read_blob(BASE_PATH)
        if legacy is None:
            rows: tuple[str, ...] = ()
            members: list[bytes] = []
        elif isinstance(legacy, bytes):
            rows = _lines(legacy)
            members = [legacy]
        else:
            _fail("legacy member is nonbytes")
        parsed_count = len(ReadResult(rows, _receipt("legacy", legacy is not None,
                                                    members, rows, None, 0)).load_claims())
        return ReadResult(rows, _receipt("legacy", legacy is not None,
                                         members, rows, None, parsed_count))
    if not isinstance(root_raw, bytes) or len(root_raw) > limits.max_root_bytes:
        _fail("root is nonbytes/oversized")
    root = _json_object(root_raw, "root")
    _shape(root, {"schema", "generation", "base", "index_root"}, "root")
    if (root["schema"] != SCHEMA or not isinstance(root["generation"], str)
            or not _TX_ID.fullmatch(root["generation"])):
        _fail("unknown root schema/generation")
    base_path, base_sha, base_size = _ref(root["base"], BASE_PATH,
                                         limits.max_base_bytes)
    if base_path != BASE_PATH:
        _fail("noncanonical QLedger base")
    ix_path, ix_sha, ix_size = _ref(root["index_root"], INDEX_PREFIX,
                                   limits.max_index_bytes)

    # Preflight full membership; do not expose a prefix after later corruption.
    seen_pages: set[str] = set()
    seen_parts: set[str] = set()
    seen_txs: set[str] = set()
    parts: list[tuple[bytes, int]] = []
    metadata: list[bytes] = []

    def visit(path: str, sha: str, byte_count: int, depth: int) -> None:
        if depth > limits.max_depth:
            _fail("index depth exceeded")
        if path in seen_pages:
            _fail("repeated/cyclic index page")
        seen_pages.add(path)
        raw = _read_member(read_blob, path, sha, byte_count)
        metadata.append(raw)
        page = _json_object(raw, "index page")
        _shape(page, {"schema", "kind",
                      "children" if page.get("kind") == "branch" else "entries"},
               "index page")
        if page["schema"] != SCHEMA or page["kind"] not in {"leaf", "branch"}:
            _fail("unsupported index page")
        items = page["entries"] if page["kind"] == "leaf" else page["children"]
        if not isinstance(items, list) or len(items) > limits.max_fanout:
            _fail("index fanout exceeded")
        if page["kind"] == "branch":
            if not items:
                _fail("empty branch")
            for child in items:
                child_path, child_sha, child_size = _ref(child, INDEX_PREFIX,
                                                         limits.max_index_bytes)
                visit(child_path, child_sha, child_size, depth + 1)
            return
        for entry in items:
            if not isinstance(entry, dict):
                _fail("invalid data entry")
            _shape(entry, {"tx_id", "path", "sha256", "bytes", "lines"}, "data entry")
            tx = entry["tx_id"]
            if not isinstance(tx, str) or not _TX_ID.fullmatch(tx) or tx in seen_txs:
                _fail("invalid/reused storage transaction")
            seen_txs.add(tx)
            part_path = _path(entry["path"], DATA_PREFIX)
            if part_path in seen_parts:
                _fail("repeated data part")
            seen_parts.add(part_path)
            if len(parts) >= limits.max_parts:
                _fail("part capacity exceeded")
            n = _int(entry["bytes"], minimum=1,
                     maximum=limits.max_part_bytes)
            raw_part = _read_member(read_blob, part_path,
                                    _digest(entry["sha256"]), n)
            num_lines = _int(entry["lines"], minimum=1)
            if len(_lines(raw_part)) != num_lines:
                _fail("data part line count mismatch")
            parts.append((raw_part, num_lines))

    visit(ix_path, ix_sha, ix_size, 1)
    base_raw = _read_member(read_blob, base_path, base_sha, base_size)
    rows = _lines(base_raw) + tuple(line for raw, _ in parts for line in _lines(raw))
    verified = [root_raw, *metadata, base_raw, *(raw for raw, _ in parts)]
    parsed_count = len(ReadResult(rows, _receipt("segmented_v0", True, verified,
                                                 rows, root["generation"], 0)).load_claims())
    return ReadResult(rows, _receipt("segmented_v0", True, verified, rows,
                                     root["generation"], parsed_count))
