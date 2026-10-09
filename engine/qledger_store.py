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

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Callable, Iterator, NoReturn

ROOT_PATH = "data/qledger/claims.parts.root.json"
BASE_PATH = "data/qledger/claims.jsonl"
INDEX_PREFIX = "data/qledger/claims.parts/index/"
DATA_PREFIX = "data/qledger/claims.parts/parts/"
SCHEMA = "mastermind.qledger.segmentation-read.v0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TX_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_PATH_CHARS = re.compile(r"[A-Za-z0-9_./-]+\Z")
_LINE_BREAK = re.compile(r"\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]")


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
    # Aggregate read budgets are separate from physical file-format limits.
    # Exhaustion is an explicit integrity failure, never a successful prefix.
    max_pages: int = 8_192
    max_total_bytes: int = 256 * 1024 * 1024
    max_lines: int = 2_000_000

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field.name} must be a positive integer")


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
        return list(_legacy_objects(self.raw_lines))


def _legacy_objects(rows: tuple[str, ...]) -> Iterator[object]:
    """Preserve native parsing, including non-dict JSON and duplicate rows."""
    for line in rows:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:  # noqa: BLE001 -- native legacy policy
            continue


def _fail(reason: str) -> NoReturn:
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
    except (UnicodeError, ValueError, RecursionError) as exc:
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


def _read_optional(read_blob: Callable[[str], bytes | None], path: str) -> bytes | None:
    # A provider failure is not an authoritative missing-object response.
    try:
        return read_blob(path)
    except (OSError, KeyError) as exc:
        raise StoreIntegrityError("snapshot member unavailable") from exc


def _read_member(read_blob: Callable[[str], bytes | None], path: str,
                 expected_sha: str, size: int) -> bytes:
    raw = _read_optional(read_blob, path)
    if not isinstance(raw, bytes):
        _fail("catalog member missing or nonbytes")
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("catalog member digest/length mismatch")
    return raw


def _lines(data: bytes, maximum_lines: int | None = None) -> tuple[str, ...]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise StoreIntegrityError("invalid UTF-8 in claims member") from exc
    if maximum_lines is None:
        return tuple(text.splitlines())
    # splitlines() would allocate every tiny/empty row before we could check a
    # budget. Match its Unicode boundaries lazily, including CRLF as one break.
    rows: list[str] = []
    start = 0
    for match in _LINE_BREAK.finditer(text):
        if len(rows) >= maximum_lines:
            _fail("logical line capacity exceeded")
        rows.append(text[start:match.start()])
        start = match.end()
    if start < len(text):
        if len(rows) >= maximum_lines:
            _fail("logical line capacity exceeded")
        rows.append(text[start:])
    return tuple(rows)


def _result(mode: str, present: bool, member_count: int,
            rows: tuple[str, ...], generation: str | None) -> ReadResult:
    # Framing preserves logical occurrence order. This is not a claim ID or
    # financial evidence vote. Parse one row at a time to avoid a second corpus.
    h = hashlib.sha256()
    for line in rows:
        raw = line.encode("utf-8")
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    receipt = ReadReceipt(mode, present, member_count, len(rows),
                          sum(1 for _ in _legacy_objects(rows)),
                          h.hexdigest(), generation)
    return ReadResult(rows, receipt)


def read_claims_snapshot(read_blob: Callable[[str], bytes | None],
                         *, limits: ReadLimits = ReadLimits()) -> ReadResult:
    """Read exact legacy bytes or a complete unactivated segmented tree.

    Absent catalog preserves incumbent legacy behavior, including its existing
    unbounded whole-file read. A present catalog never falls back after failure.
    Segmented reads enforce aggregate page/byte/line budgets before returning
    any history; byte budgets apply before fetching each referenced member.
    The callback must itself bound physical reads and pin every object to one
    immutable tree/coherent snapshot. A callback's allocation cannot be bounded
    by a reader that receives its result only after the callback returns.
    """
    if not isinstance(limits, ReadLimits):
        raise TypeError("limits must be ReadLimits")
    root_raw = _read_optional(read_blob, ROOT_PATH)
    if root_raw is None:
        legacy = _read_optional(read_blob, BASE_PATH)
        if legacy is None:
            return _result("legacy", False, 0, (), None)
        if not isinstance(legacy, bytes):
            _fail("legacy member is nonbytes")
        return _result("legacy", True, 1, _lines(legacy), None)
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
    index_ref = _ref(root["index_root"], INDEX_PREFIX, limits.max_index_bytes)
    consumed_bytes = len(root_raw)
    member_count = 1
    if consumed_bytes > limits.max_total_bytes:
        _fail("aggregate byte capacity exceeded")

    def read_member(path: str, sha: str, size: int) -> bytes:
        nonlocal consumed_bytes, member_count
        if size > limits.max_total_bytes - consumed_bytes:
            _fail("aggregate byte capacity exceeded")
        raw = _read_member(read_blob, path, sha, size)
        consumed_bytes += size
        member_count += 1
        return raw

    # Decode one member at a time; retain the logical lines, not a second copy
    # of every raw data part and metadata page. No prefix escapes on failure.
    rows = list(_lines(read_member(base_path, base_sha, base_size), limits.max_lines))
    seen_pages: set[str] = set()
    seen_parts: set[str] = set()
    seen_txs: set[str] = set()
    stack = [(*index_ref, 1)]
    while stack:
        path, sha, byte_count, depth = stack.pop()
        if depth > limits.max_depth:
            _fail("index depth exceeded")
        if path in seen_pages:
            _fail("repeated/cyclic index page")
        if len(seen_pages) >= limits.max_pages:
            _fail("index page capacity exceeded")
        seen_pages.add(path)
        page = _json_object(read_member(path, sha, byte_count), "index page")
        kind = page.get("kind")
        if not isinstance(kind, str) or kind not in {"leaf", "branch"}:
            _fail("unsupported index page")
        _shape(page, {"schema", "kind", "children" if kind == "branch" else "entries"},
               "index page")
        if page["schema"] != SCHEMA:
            _fail("unsupported index page")
        items = page["entries"] if kind == "leaf" else page["children"]
        if not isinstance(items, list) or len(items) > limits.max_fanout:
            _fail("index fanout exceeded")
        if kind == "branch":
            if not items:
                _fail("empty branch")
            children = [_ref(child, INDEX_PREFIX, limits.max_index_bytes)
                        for child in items]
            # LIFO traversal visits declared children left-to-right. Iteration
            # avoids Python recursion limits becoming an implicit format rule.
            stack.extend((*child, depth + 1) for child in reversed(children))
            continue
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
            if len(seen_parts) >= limits.max_parts:
                _fail("part capacity exceeded")
            seen_parts.add(part_path)
            n = _int(entry["bytes"], minimum=1, maximum=limits.max_part_bytes)
            num_lines = _int(entry["lines"], minimum=1)
            remaining_lines = limits.max_lines - len(rows)
            if num_lines > remaining_lines:
                _fail("logical line capacity exceeded")
            part_rows = _lines(read_member(part_path, _digest(entry["sha256"]), n),
                               remaining_lines)
            if len(part_rows) != num_lines:
                _fail("data part line count mismatch")
            rows.extend(part_rows)
    return _result("segmented_v0", True, member_count, tuple(rows), root["generation"])
