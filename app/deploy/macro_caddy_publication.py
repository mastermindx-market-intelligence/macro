"""Bounded publication transaction for the existing Macro updater's Caddy API writes.

Scope is deliberately narrow: one ``publish`` transaction that takes a captured
native Caddy config preimage, a captured candidate config, and captured
Caddyfile source bytes, then either

  1. refuses proven-no-effect (nothing was ever posted), or
  2. holds a durably recorded *pending* intent (effect unknown / diverged), or
  3. completes: one conditional API write verified against both the full API
     readback and the full autosave, followed by the caller's exact-baseline
     source install and a durably committed receipt.

Out of scope (parent-owned): route planning, daemon/scheduler behaviour, real
HTTP clients, host authentication, package installation, repository writes and
production root/path checks.  The updater that calls this already serialises
itself with ``flock``; this module adds no retry, loop, fallback or alternate
endpoint, and never clears recorded state on failure.

Adapter contract (all injected, fakes in tests):

``api.read()``
    Returns the full native config plus its ETag.  Accepted shapes: a
    ``(config, etag)`` pair, or a mapping/object exposing ``config`` and
    ``etag``.  The pair form is preferred.
``api.write(candidate, etag)``
    Performs exactly one conditional request (If-Match) and returns the HTTP
    status as an ``int``.  This module calls it at most once per intent and
    never again for that intent.
``read_autosave()``
    Returns the complete native autosave config as a JSON-compatible dict.
``install_source(old_bytes, new_bytes)``
    Caller-provided exact source-baseline installer.  Invoked only after the
    API readback and the autosave both equal the candidate, and only with the
    bytes captured for the pending intent -- never with bytes belonging to a
    different, later operation.

State lives in a minimal private intent/receipt journal under ``state_dir``:
one immutable ``intent-<op_id>.json`` per attempted write, plus one immutable
``receipt-<op_id>.json`` closure.  An intent without a receipt is *pending*
and blocks any further conditional write.  Nothing is ever deleted, rewritten
or repaired; tampering, symlink aliasing, ownership drift and fsync/readback
failures close the gate.

Judgement calls, for review:

* ``state_dir`` must be a directory owned by the current UID with no
  group/other access (created ``0700`` when absent).  The production root and
  the real fixed path remain the wrapper's responsibility.
* A ``412`` response is treated as a *server-proven* pre-effect refusal: it is
  retained durably as a ``refused_precondition`` receipt and does not block a
  later, different operation.  Every other non-200, every write exception and
  every unverifiable 200 leaves the intent pending and blocks all further
  conditional writes -- including when the API still equals the preimage,
  because an in-flight effect cannot be disproved.
* Reconciliation is read-only with respect to the API.  It may finish a
  pending intent only when BOTH the full API read and the full autosave equal
  the pending intent's OWN captured candidate, and it installs only that
  intent's OWN captured source bytes -- a caller arriving with newer bytes is
  never adopted in place of the pending operation.
* Successful ``install_source`` followed by a failed receipt persist leaves
  the intent pending, so a later reconciliation re-runs the installer; the
  caller-provided installer must therefore be idempotent over its exact
  baseline.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["publish", "journal_status", "JOURNAL_SCHEMA"]

JOURNAL_SCHEMA = "mm.macro_caddy_publication.journal.v1"

# Payload bounds.  Configuration documents and captured source bytes are
# rejected outright above these limits rather than truncated.
MAX_CONFIG_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_JOURNAL_BYTES = 16 * 1024 * 1024

# Native Caddy includes its resource path and an internal ASCII space, e.g.
# "/config/ 9a6898e094be700c". Preserve that opaque value for If-Match while
# refusing control bytes, embedded quotes and backslashes.
_ETAG_RE = re.compile(r'^(?:W/)?"[\x20-\x21\x23-\x5B\x5D-\x7E]{1,120}"$')

_DIR_MODE = 0o700
_FILE_MODE = 0o600

_INTENT_PREFIX = "intent-"
_RECEIPT_PREFIX = "receipt-"
_ENTRY_RE = re.compile(r"^(intent|receipt)-([0-9a-f]{64})\.json$")

# Result statuses.
S_PUBLISHED = "published"                    # fresh conditional write fully verified
S_RECONCILED = "reconciled"                  # pending intent for THIS op finished read-only
S_RECONCILED_PRIOR = "reconciled_prior"      # a DIFFERENT pending op finished with its own bytes
S_ALREADY = "already_published"              # durable receipt already existed for this op
S_REFUSED = "refused"                        # proven no-effect refusal
S_HELD = "held_pending"                      # effect uncertain or diverged; write gate closed

# Effect states (explicitly separates proven no-effect from unproven effect).
E_NONE_PROVEN = "none_proven"
E_APPLIED_VERIFIED = "applied_verified"
E_UNCERTAIN = "uncertain"


class _StructureError(Exception):
    """Internal: injected data did not have the required shape."""


# --------------------------------------------------------------------------
# small primitives
# --------------------------------------------------------------------------

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    """Deterministic native-JSON encoding; refuses NaN/Infinity/non-JSON."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _native_equal(left: Any, right: Any) -> bool:
    """Exact native-JSON equality.

    Deliberately stricter than ``==`` so that ``1`` vs ``1.0`` and ``True`` vs
    ``1`` count as drift rather than equality.
    """
    try:
        return _canonical_json_bytes(left) == _canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _error(code: str, detail: str = "") -> Dict[str, str]:
    out = {"code": code}
    if detail:
        out["detail"] = detail
    return out


def _result(status: str, op_id: Optional[str], errors: List[Dict[str, str]], **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "status": status,
        "published": status in (S_PUBLISHED, S_RECONCILED, S_RECONCILED_PRIOR, S_ALREADY),
        "op_id": op_id,
        "effect_state": extra.pop("effect_state", E_NONE_PROVEN),
        "write_attempted": extra.pop("write_attempted", False),
        "write_http_status": extra.pop("write_http_status", None),
        "installed_source": extra.pop("installed_source", False),
        "receipt_written": extra.pop("receipt_written", False),
        "pending": status == S_HELD,
        "errors": list(errors),
    }
    out.update(extra)
    return out


# --------------------------------------------------------------------------
# injected-surface coercion and validation
# --------------------------------------------------------------------------

def _coerce_api_read(value: Any) -> Tuple[Any, Any]:
    """Extract (full config, etag) from an ``api.read()`` return value."""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return value[0], value[1]
    if isinstance(value, dict) and "config" in value and "etag" in value:
        return value["config"], value["etag"]
    if value is not None and not isinstance(value, (dict, list, tuple, str, bytes)):
        config = getattr(value, "config", None)
        etag = getattr(value, "etag", None)
        if config is not None and etag is not None:
            return config, etag
    raise _StructureError("api.read() did not yield (config, etag)")


def _validate_etag(etag: Any) -> Optional[str]:
    """Return the etag if it is a bounded, safe, well-formed string, else None."""
    if not isinstance(etag, str):
        return None
    if len(etag) > 128 or not _ETAG_RE.fullmatch(etag):
        return None
    return etag


def _validate_doc(value: Any) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Validate a native config document; return (digest, error)."""
    if not isinstance(value, dict):
        return None, _error("invalid_structure", "config document must be a JSON object")
    try:
        canon = _canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        return None, _error("invalid_structure", "config is not native JSON: %s" % type(exc).__name__)
    if len(canon) > MAX_CONFIG_BYTES:
        return None, _error("config_oversized", "canonical config exceeds %d bytes" % MAX_CONFIG_BYTES)
    return _sha256_hex(canon), None


def _validate_source(value: Any, label: str) -> Tuple[Optional[bytes], Optional[Dict[str, str]]]:
    if not isinstance(value, bytes):
        return None, _error("invalid_source_bytes", "%s must be captured bytes" % label)
    if len(value) > MAX_SOURCE_BYTES:
        return None, _error("source_oversized", "%s exceeds %d bytes" % (label, MAX_SOURCE_BYTES))
    return value, None


def _op_id(preimage_digest: str, candidate_digest: str,
           before_digest: str, after_digest: str, predecessor=None) -> str:
    """Captured transition plus its fully closed predecessor, never a pending escape."""
    material = "\n".join((preimage_digest, candidate_digest, before_digest, after_digest))
    if predecessor is not None:
        material += "\nclosed-predecessor:" + predecessor
    return _sha256_hex(material.encode("ascii"))


# --------------------------------------------------------------------------
# journal custody
# --------------------------------------------------------------------------

def _record_integrity(record: Dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "integrity"}
    return _sha256_hex(_canonical_json_bytes(body))


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ensure_private_dir(state_dir: Path) -> Tuple[Optional[Tuple[int, int]], Optional[Dict[str, str]]]:
    """Create/validate the private journal directory.  Returns ((dev, ino), error)."""
    try:
        if os.path.islink(str(state_dir)):
            return None, _error("state_dir_symlink")
        if not state_dir.exists():
            os.mkdir(str(state_dir), _DIR_MODE)
        st = os.lstat(str(state_dir))
    except OSError as exc:
        return None, _error("state_dir_unavailable", type(exc).__name__)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        return None, _error("state_dir_not_directory")
    if st.st_uid != os.geteuid():
        return None, _error("state_dir_not_current_uid")
    if stat.S_IMODE(st.st_mode) & 0o077:
        return None, _error("state_dir_not_private")
    real = os.stat(str(state_dir))
    if (real.st_dev, real.st_ino) != (st.st_dev, st.st_ino):
        return None, _error("state_dir_aliased")
    try:
        _fsync_dir(state_dir)
    except OSError as exc:
        return None, _error("state_dir_fsync_failed", type(exc).__name__)
    return (st.st_dev, st.st_ino), None


def _write_journal_file(path: Path, payload: bytes) -> Tuple[Optional[Tuple[int, int]], Optional[Dict[str, str]]]:
    """Exclusive nofollow immutable write with fsync and full readback custody."""
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, _FILE_MODE)
    except OSError as exc:
        return None, _error("journal_create_failed", "%s: %s" % (type(exc).__name__, exc.errno))
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.geteuid():
            return None, _error("journal_custody_error", "written file failed custody checks")
        if stat.S_IMODE(st.st_mode) & 0o077:
            return None, _error("journal_custody_error", "written file is group/other accessible")
        # Readback through a fresh nofollow descriptor: same inode, same bytes.
        rfd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            rst = os.fstat(rfd)
            if (rst.st_dev, rst.st_ino) != (st.st_dev, st.st_ino):
                return None, _error("journal_custody_error", "readback inode mismatch")
            chunks: List[bytes] = []
            while True:
                chunk = os.read(rfd, 1 << 16)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(len(c) for c in chunks) > MAX_JOURNAL_BYTES:
                    return None, _error("journal_custody_error", "readback oversized")
        finally:
            os.close(rfd)
        if b"".join(chunks) != payload:
            return None, _error("journal_readback_mismatch")
    except OSError as exc:
        return None, _error("journal_write_failed", type(exc).__name__)
    finally:
        os.close(fd)
    try:
        _fsync_dir(path.parent)
    except OSError as exc:
        return (st.st_dev, st.st_ino), _error("journal_dir_fsync_failed", type(exc).__name__)
    return (st.st_dev, st.st_ino), None


def _load_journal_record(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
    """Custody-checked load of one journal record (symlink/uid/mode/integrity)."""
    try:
        st = os.lstat(str(path))
    except OSError as exc:
        return None, _error("journal_stat_failed", type(exc).__name__)
    if stat.S_ISLNK(st.st_mode):
        return None, _error("journal_symlink")
    if not stat.S_ISREG(st.st_mode):
        return None, _error("journal_not_regular")
    if st.st_nlink != 1:
        return None, _error("journal_nlink_not_one")
    if st.st_uid != os.geteuid():
        return None, _error("journal_not_current_uid")
    if stat.S_IMODE(st.st_mode) & 0o077:
        return None, _error("journal_not_private")
    if st.st_size > MAX_JOURNAL_BYTES:
        return None, _error("journal_oversized")
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        return None, _error("journal_open_failed", type(exc).__name__)
    try:
        fst = os.fstat(fd)
        if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
            return None, _error("journal_renamed_under_read")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 16)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(len(c) for c in chunks) > MAX_JOURNAL_BYTES:
                return None, _error("journal_oversized")
    except OSError as exc:
        return None, _error("journal_read_failed", type(exc).__name__)
    finally:
        os.close(fd)
    data = b"".join(chunks)
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, _error("journal_corrupt", "record is not valid JSON")
    if not isinstance(record, dict) or record.get("schema") != JOURNAL_SCHEMA:
        return None, _error("journal_corrupt", "unknown record schema")
    if record.get("kind") not in ("intent", "receipt"):
        return None, _error("journal_corrupt", "unknown record kind")
    stored = record.get("integrity")
    if not isinstance(stored, str) or stored != _record_integrity(record):
        return None, _error("journal_corrupt", "integrity digest mismatch")
    return record, None


def _intent_unchanged(state_dir, state_identity, path, intent_identity, expected):
    """Revalidate the captured pathname/inode without creating or repairing it."""
    try:
        directory = os.lstat(state_dir)
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid()
                or directory.st_mode & 0o077
                or (directory.st_dev, directory.st_ino) != state_identity):
            return _error("journal_directory_changed")
        current = os.lstat(path)
        if (current.st_dev, current.st_ino) != intent_identity:
            return _error("journal_intent_inode_changed")
        record, error = _load_journal_record(path)
        if error is not None:
            return error
        if not _native_equal(record, expected):
            return _error("journal_intent_bytes_changed")
    except OSError as exc:
        return _error("journal_intent_unavailable", type(exc).__name__)
    return None


class _Journal:
    """Scan result over the private journal directory."""

    def __init__(self, state_dir: Path) -> None:
        self.intents: Dict[str, Dict[str, Any]] = {}
        self.receipts: Dict[str, Dict[str, Any]] = {}
        self.intent_paths: Dict[str, Path] = {}
        self.custody_errors: List[Dict[str, str]] = []
        try:
            entries = sorted(os.listdir(str(state_dir)))
        except OSError as exc:
            self.custody_errors.append(_error("journal_list_failed", type(exc).__name__))
            return
        for name in entries:
            match = _ENTRY_RE.fullmatch(name)
            if match is None:
                continue  # foreign/unknown entries are not this owner's records
            kind, op_id = match.group(1), match.group(2)
            record, err = _load_journal_record(state_dir / name)
            if err is not None:
                self.custody_errors.append(dict(err, detail="%s: %s" % (err.get("detail", ""), op_id)))
                continue
            target = self.intents if kind == "intent" else self.receipts
            if op_id in target:
                self.custody_errors.append(_error("journal_duplicate_record", op_id))
                continue
            target[op_id] = record
            if kind == "intent":
                self.intent_paths[op_id] = state_dir / name
        for op_id in self.receipts:
            if op_id not in self.intents:
                self.custody_errors.append(_error("journal_orphan_receipt", op_id))

    def pending_ops(self) -> List[str]:
        """Recorded intents with no durable closure; more than one is ambiguous."""
        return sorted(op for op in self.intents if op not in self.receipts)


def _receipt_for(journal: _Journal, op_id: str) -> Optional[Dict[str, Any]]:
    receipt = journal.receipts.get(op_id)
    if receipt is None:
        return None
    intent = journal.intents.get(op_id)
    if intent is None:
        return None
    # Inode custody recorded by the receipt at closure time.
    try:
        st = os.lstat(str(journal.intent_paths[op_id]))
    except OSError:
        return None
    if (st.st_dev, st.st_ino) != (receipt.get("intent_dev"), receipt.get("intent_ino")):
        return None
    return receipt


def _closed_history_tip(journal):
    """Validate one immutable intent chain; clocks and ETags are not generations."""
    if not journal.intents:
        return None, None
    children = {}
    for op, intent in journal.intents.items():
        predecessor = intent.get("predecessor")
        if predecessor is not None and (not isinstance(predecessor, str)
                                        or not re.fullmatch(r"[0-9a-f]{64}", predecessor)):
            return None, _error("journal_predecessor_invalid")
        digests = [intent.get(key) for key in (
            "preimage_digest", "candidate_digest", "source_before_digest", "source_after_digest")]
        if (any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                for value in digests) or _op_id(*digests, predecessor) != op):
            return None, _error("journal_transition_identity_invalid")
        if ("predecessor" not in intent or intent.get("op_id") != op
                or intent.get("kind") != "intent"
                or predecessor == op or predecessor in children):
            return None, _error("journal_history_ambiguous")
        if predecessor is not None and (predecessor not in journal.intents
                                       or predecessor not in journal.receipts):
            return None, _error("journal_predecessor_not_closed")
        children[predecessor] = op
        if op in journal.receipts:
            receipt = _receipt_for(journal, op)
            if (receipt is None or receipt.get("op_id") != op
                    or receipt.get("kind") != "receipt"
                    or receipt.get("closure") not in {"committed", "refused_precondition"}
                    or any(receipt.get(key) != intent.get(key) for key in
                           ("preimage_digest", "candidate_digest", "source_before_digest", "source_after_digest"))):
                return None, _error("journal_receipt_unverified")
    current, seen = None, set()
    while current in children:
        current = children[current]
        if current in seen:
            return None, _error("journal_history_cycle")
        seen.add(current)
    if len(seen) != len(journal.intents):
        return None, _error("journal_history_disconnected")
    return current, None


def _build_intent(state_dir_identity: Tuple[int, int], op_id: str, etag: str,
                  expected_preimage_digest: str, candidate_digest: str,
                  candidate: Dict[str, Any], source_before: bytes,
                  source_after: bytes, predecessor=None) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "kind": "intent",
        "op_id": op_id,
        "predecessor": predecessor,
        "created_ns": time.time_ns(),
        "pid": os.getpid(),
        "uid": os.geteuid(),
        "journal_dev": state_dir_identity[0],
        "journal_ino": state_dir_identity[1],
        "etag": etag,
        "preimage_digest": expected_preimage_digest,
        "candidate_digest": candidate_digest,
        "candidate": candidate,
        "source_before_b64": base64.b64encode(source_before).decode("ascii"),
        "source_after_b64": base64.b64encode(source_after).decode("ascii"),
        "source_before_digest": _sha256_hex(source_before),
        "source_after_digest": _sha256_hex(source_after),
        "source_before_len": len(source_before),
        "source_after_len": len(source_after),
    }
    record["integrity"] = _record_integrity(record)
    return record


def _build_receipt(op_id: str, closure: str, intent_identity: Tuple[int, int],
                   write_http_status: Optional[int], reconciled: bool,
                   preimage_digest: str, candidate_digest: str,
                   before_digest: str, after_digest: str) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "kind": "receipt",
        "op_id": op_id,
        "created_ns": time.time_ns(),
        "pid": os.getpid(),
        "uid": os.geteuid(),
        "closure": closure,
        "intent_dev": intent_identity[0],
        "intent_ino": intent_identity[1],
        "write_http_status": write_http_status,
        "reconciled": bool(reconciled),
        "preimage_digest": preimage_digest,
        "candidate_digest": candidate_digest,
        "source_before_digest": before_digest,
        "source_after_digest": after_digest,
    }
    record["integrity"] = _record_integrity(record)
    return record


def _persist_closure(state_dir: Path, receipt: Dict[str, Any]) -> Tuple[Optional[Tuple[int, int]], Optional[Dict[str, str]]]:
    payload = _canonical_json_bytes(receipt)
    if len(payload) > MAX_JOURNAL_BYTES:
        return None, _error("journal_oversized")
    return _write_journal_file(state_dir / ("%s%s.json" % (_RECEIPT_PREFIX, receipt["op_id"])), payload)


# --------------------------------------------------------------------------
# reconciliation (read-only with respect to the API; may finish the install)
# --------------------------------------------------------------------------

def _captured_from_intent(record: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[bytes], Optional[bytes]]:
    candidate = record.get("candidate")
    if not isinstance(candidate, dict):
        return None, None, None
    try:
        before = base64.b64decode(record["source_before_b64"], validate=True)
        after = base64.b64decode(record["source_after_b64"], validate=True)
    except (KeyError, binascii.Error, TypeError, ValueError):
        return None, None, None
    if not isinstance(before, bytes) or not isinstance(after, bytes):
        return None, None, None
    if len(before) > MAX_SOURCE_BYTES or len(after) > MAX_SOURCE_BYTES:
        return None, None, None
    if (record.get("source_before_digest") != _sha256_hex(before)
            or record.get("source_after_digest") != _sha256_hex(after)
            or record.get("source_before_len") != len(before)
            or record.get("source_after_len") != len(after)):
        return None, None, None
    return candidate, before, after


def _reconcile_pending(state_dir: Path, journal: _Journal, pending_id: str,
                       state_identity: Tuple[int, int],
                       api: Any, read_autosave: Callable[[], Any],
                       install_source: Callable[[bytes, bytes], Any],
                       requested_op: Optional[str]) -> Dict[str, Any]:
    """Finish (or keep holding) a pending intent without any further API write.

    May complete only when BOTH the full API read and the full autosave equal
    the ORIGINAL captured candidate of the pending intent.  Never substitutes
    new candidate/source bytes for the pending ones.
    """
    hold_extra: Dict[str, Any] = {"pending_op_id": pending_id, "requested_op_id": requested_op}
    record = journal.intents[pending_id]

    # The intent must still belong to this journal directory.
    if (record.get("journal_dev"), record.get("journal_ino")) != state_identity:
        return _result(S_HELD, pending_id, [_error("journal_relocated")],
                       effect_state=E_UNCERTAIN, **hold_extra)
    try:
        ist = os.lstat(str(journal.intent_paths[pending_id]))
    except OSError as exc:
        return _result(S_HELD, pending_id, [_error("journal_intent_stat_failed", type(exc).__name__)],
                       effect_state=E_UNCERTAIN, **hold_extra)
    intent_identity = (ist.st_dev, ist.st_ino)
    err = _intent_unchanged(state_dir, state_identity, journal.intent_paths[pending_id],
                            intent_identity, record)
    if err is not None:
        return _result(S_HELD, pending_id, [err], effect_state=E_UNCERTAIN, **hold_extra)

    candidate, before, after = _captured_from_intent(record)
    if candidate is None or before is None or after is None:
        return _result(S_HELD, pending_id, [_error("journal_captured_bytes_invalid")],
                       effect_state=E_UNCERTAIN, **hold_extra)
    candidate_digest, err = _validate_doc(candidate)
    if err is not None or candidate_digest != record.get("candidate_digest"):
        return _result(S_HELD, pending_id, [_error("journal_captured_candidate_invalid")],
                       effect_state=E_UNCERTAIN, **hold_extra)
    try:
        config, _etag = _coerce_api_read(api.read())
    except Exception as exc:  # no API write occurs on this path
        return _result(S_HELD, pending_id, [_error("reconcile_read_failed", type(exc).__name__)],
                       effect_state=E_UNCERTAIN, **hold_extra)
    if not _native_equal(config, candidate):
        return _result(S_HELD, pending_id, [_error("reconcile_api_diverged")],
                       effect_state=E_UNCERTAIN, **hold_extra)
    try:
        autosave = read_autosave()
    except Exception as exc:
        return _result(S_HELD, pending_id, [_error("reconcile_autosave_failed", type(exc).__name__)],
                       effect_state=E_UNCERTAIN, **hold_extra)
    if not _native_equal(autosave, candidate):
        return _result(S_HELD, pending_id, [_error("reconcile_autosave_diverged")],
                       effect_state=E_UNCERTAIN, **hold_extra)
    err = _intent_unchanged(state_dir, state_identity, journal.intent_paths[pending_id],
                            intent_identity, record)
    if err is not None:
        return _result(S_HELD, pending_id, [err], effect_state=E_UNCERTAIN, **hold_extra)
    try:
        install_source(before, after)
    except Exception as exc:
        return _result(S_HELD, pending_id, [_error("install_source_failed", type(exc).__name__)],
                       effect_state=E_UNCERTAIN, installed_source=False, **hold_extra)
    err = _intent_unchanged(state_dir, state_identity, journal.intent_paths[pending_id],
                            intent_identity, record)
    if err is not None:
        return _result(S_HELD, pending_id, [err], effect_state=E_UNCERTAIN,
                       installed_source=True, **hold_extra)
    receipt = _build_receipt(
        pending_id, "committed", intent_identity, None, True,
        record.get("preimage_digest", ""), candidate_digest,
        _sha256_hex(before), _sha256_hex(after),
    )
    receipt_identity, err = _persist_closure(state_dir, receipt)
    if err is not None:
        return _result(S_HELD, pending_id, [err], effect_state=E_APPLIED_VERIFIED,
                       installed_source=True, receipt_written=False, **hold_extra)
    prior = requested_op is not None and requested_op != pending_id
    return _result(
        S_RECONCILED_PRIOR if prior else S_RECONCILED,
        pending_id, [],
        effect_state=E_APPLIED_VERIFIED,
        installed_source=True,
        receipt_written=True,
        receipt_identity=receipt_identity and {"dev": receipt_identity[0], "ino": receipt_identity[1]},
        reconciled_prior=prior,
        **hold_extra,
    )


# --------------------------------------------------------------------------
# publish
# --------------------------------------------------------------------------

def publish(
    *,
    state_dir: Path,
    api: Any,
    expected_preimage: dict,
    candidate: dict,
    source_before: bytes,
    source_after: bytes,
    read_autosave: Callable[[], Any],
    install_source: Callable[[bytes, bytes], Any],
) -> Dict[str, Any]:
    """Run one bounded Caddy publication transaction and return its result.

    See the module docstring for the adapter contract and the state machine.
    This function returns a result dict for every outcome (including refusals
    and holds); it raises nothing by design.
    """
    errors: List[Dict[str, str]] = []

    # ---- argument validation -------------------------------------------------
    if not hasattr(api, "read") or not callable(getattr(api, "read")) \
            or not hasattr(api, "write") or not callable(getattr(api, "write")):
        return _result(S_REFUSED, None, [_error("invalid_api_surface")])
    for name, fn in (("read_autosave", read_autosave), ("install_source", install_source)):
        if not callable(fn):
            return _result(S_REFUSED, None, [_error("invalid_api_surface", name)])

    preimage_digest, err = _validate_doc(expected_preimage)
    if err is not None:
        errors.append(err)
    candidate_digest, err = _validate_doc(candidate)
    if err is not None:
        errors.append(err)
    before, err = _validate_source(source_before, "source_before")
    if err is not None:
        errors.append(err)
    after, err = _validate_source(source_after, "source_after")
    if err is not None:
        errors.append(err)
    if errors:
        return _result(S_REFUSED, None, errors)

    assert preimage_digest is not None and candidate_digest is not None
    assert before is not None and after is not None
    op_id = _op_id(preimage_digest, candidate_digest, _sha256_hex(before), _sha256_hex(after))

    # ---- journal custody -----------------------------------------------------
    if not isinstance(state_dir, (str, Path)):
        return _result(S_REFUSED, op_id, [_error("invalid_state_dir")])
    state_path = Path(state_dir)
    identity, err = _ensure_private_dir(state_path)
    if err is not None:
        return _result(S_REFUSED, op_id, [err])

    journal = _Journal(state_path)
    if journal.custody_errors:
        return _result(S_REFUSED, op_id, list(journal.custody_errors))

    pending = journal.pending_ops()
    if len(pending) > 1:
        # Ambiguous journal custody: more than one unclosed intent.  Fail closed.
        return _result(S_HELD, None, [_error("journal_multiple_pending")], effect_state=E_UNCERTAIN)
    pending_id: Optional[str] = pending[0] if pending else None
    tip, err = _closed_history_tip(journal)
    if err is not None:
        return _result(S_HELD, op_id, [err], effect_state=E_UNCERTAIN)

    # Pending remains the same captured operation regardless of a caller's
    # desired content or closed history. No new generation exists on this path.
    if pending_id is not None:
        if pending_id != tip:
            return _result(S_HELD, op_id, [_error("journal_pending_not_tip")], effect_state=E_UNCERTAIN)
        requested = _op_id(preimage_digest, candidate_digest, _sha256_hex(before),
                           _sha256_hex(after), journal.intents[pending_id]["predecessor"])
        return _reconcile_pending(state_path, journal, pending_id, identity, api,
                                  read_autosave, install_source, requested_op=requested)

    # Only the latest closed transition can be recalled, and historical receipt
    # evidence alone never proves that its candidate is still current.
    tip_intent = journal.intents.get(tip)
    same_transition = tip_intent is not None and all(
        tip_intent.get(key) == value for key, value in (
            ("preimage_digest", preimage_digest), ("candidate_digest", candidate_digest),
            ("source_before_digest", _sha256_hex(before)), ("source_after_digest", _sha256_hex(after))))
    if same_transition:
        receipt = _receipt_for(journal, tip)
        if receipt is None:
            # Receipt missing or lost inode custody for a recorded intent:
            # fail closed rather than re-publishing on a broken boundary.
            return _result(S_HELD, tip, [_error("journal_receipt_unverified")], effect_state=E_UNCERTAIN)
        if receipt.get("closure") == "refused_precondition":
            return _result(S_REFUSED, tip, [_error("write_precondition_refused")],
                           effect_state=E_NONE_PROVEN, write_http_status=412,
                           receipt_written=True, closure="refused_precondition")
        if receipt.get("closure") != "committed":
            return _result(S_HELD, tip, [_error("journal_unknown_closure")],
                           effect_state=E_UNCERTAIN)
        try:
            current, current_etag = _coerce_api_read(api.read())
            if (_validate_etag(current_etag) is None or not _native_equal(current, candidate)
                    or not _native_equal(read_autosave(), candidate)):
                return _result(S_REFUSED, tip, [_error("historical_receipt_not_current")])
            intent_path = journal.intent_paths[tip]
            st = os.lstat(intent_path)
            err = _intent_unchanged(state_path, identity, intent_path,
                                    (st.st_dev, st.st_ino), tip_intent)
            if err is not None:
                return _result(S_HELD, tip, [err], effect_state=E_UNCERTAIN)
            install_source(before, after)  # Idempotent verification of the actual baseline.
            err = _intent_unchanged(state_path, identity, intent_path,
                                    (st.st_dev, st.st_ino), tip_intent)
            if err is not None:
                return _result(S_HELD, tip, [err], effect_state=E_UNCERTAIN,
                               installed_source=True)
        except Exception as exc:
            return _result(S_REFUSED, tip, [_error("current_recall_unverified", type(exc).__name__)])
        return _result(
            S_ALREADY, tip, [],
            effect_state=E_APPLIED_VERIFIED,
            write_http_status=receipt.get("write_http_status"),
            installed_source=True,
            receipt_written=True,
            reconciled_prior=bool(receipt.get("reconciled")),
            closure=receipt.get("closure"),
        )

    # A new normal source transition follows only fully closed history. Thus
    # A→B→A→B is three distinct attempts while a pending B can never get a new ID.
    op_id = _op_id(preimage_digest, candidate_digest, _sha256_hex(before), _sha256_hex(after), tip)

    # ---- qualification: full preimage agreement, then a second full check ----
    try:
        config1, etag1_raw = _coerce_api_read(api.read())
    except Exception as exc:
        return _result(S_REFUSED, op_id, [_error("api_read_failed", type(exc).__name__)])
    if not isinstance(config1, dict):
        return _result(S_REFUSED, op_id, [_error("api_invalid_structure")])
    etag1 = _validate_etag(etag1_raw)
    if etag1 is None:
        return _result(S_REFUSED, op_id, [_error("etag_missing_or_invalid")])
    if not _native_equal(config1, expected_preimage):
        return _result(S_REFUSED, op_id, [_error("preimage_drift")])

    try:
        autosave1 = read_autosave()
    except Exception as exc:
        return _result(S_REFUSED, op_id, [_error("autosave_read_failed", type(exc).__name__)])
    if not isinstance(autosave1, dict):
        return _result(S_REFUSED, op_id, [_error("autosave_invalid_structure")])
    if not _native_equal(autosave1, expected_preimage):
        return _result(S_REFUSED, op_id, [_error("autosave_preimage_mismatch")])

    # Second complete API+ETag check after qualification (concurrent host update).
    try:
        config2, etag2_raw = _coerce_api_read(api.read())
    except Exception as exc:
        return _result(S_REFUSED, op_id, [_error("api_recheck_failed", type(exc).__name__)])
    etag2 = _validate_etag(etag2_raw)
    if not isinstance(config2, dict):
        return _result(S_REFUSED, op_id, [_error("api_invalid_structure")])
    if etag2 is None:
        return _result(S_REFUSED, op_id, [_error("etag_missing_or_invalid")])
    if etag2 != etag1:
        return _result(S_REFUSED, op_id, [_error("etag_stale")])
    if not _native_equal(config2, expected_preimage):
        return _result(S_REFUSED, op_id, [_error("preimage_drift_concurrent")])

    # ---- durable intent BEFORE the sole conditional write --------------------
    intent = _build_intent(
        identity, op_id, etag1, preimage_digest, candidate_digest,
        candidate, before, after, predecessor=tip,
    )
    try:
        payload = _canonical_json_bytes(intent)
    except (TypeError, ValueError):
        return _result(S_REFUSED, op_id, [_error("invalid_structure", "intent not encodable")])
    if len(payload) > MAX_JOURNAL_BYTES:
        return _result(S_REFUSED, op_id, [_error("journal_oversized")])
    intent_path = state_path / ("%s%s.json" % (_INTENT_PREFIX, op_id))
    intent_identity, err = _write_journal_file(intent_path, payload)
    if err is not None:
        return _result(S_REFUSED, op_id, [err])

    # ---- the sole conditional write; never retried ---------------------------
    err = _intent_unchanged(state_path, identity, intent_path, intent_identity, intent)
    if err is not None:
        return _result(S_HELD, op_id, [err], effect_state=E_UNCERTAIN)
    write_attempted = True
    try:
        status = api.write(candidate, etag1)
    except Exception as exc:
        errors.append(_error("write_lost_response", type(exc).__name__))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN, write_attempted=True)
    err = _intent_unchanged(state_path, identity, intent_path, intent_identity, intent)
    if err is not None:
        return _result(S_HELD, op_id, [err], effect_state=E_UNCERTAIN, write_attempted=True)
    if not _is_int(status) or not (100 <= status <= 599):
        errors.append(_error("write_uninterpretable_result"))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN, write_attempted=True)

    if status != 200:
        if status == 412:
            # Server-proven pre-effect refusal: the precondition failed before
            # any configuration effect.  Recorded durably, never cleared.
            receipt = _build_receipt(
                op_id, "refused_precondition", intent_identity or (0, 0),
                412, False, preimage_digest, candidate_digest,
                _sha256_hex(before), _sha256_hex(after),
            )
            _receipt_identity, err = _persist_closure(state_path, receipt)
            errors.append(_error("write_precondition_refused"))
            return _result(
                S_REFUSED, op_id, errors,
                effect_state=E_NONE_PROVEN,
                write_attempted=True, write_http_status=412,
                receipt_written=err is None,
                closure="refused_precondition" if err is None else None,
            )
        errors.append(_error("write_non_200"))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=status)

    # ---- post-200 verification: full API readback AND full autosave ----------
    try:
        config3, _etag3 = _coerce_api_read(api.read())
    except Exception as exc:
        errors.append(_error("readback_failed", type(exc).__name__))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)
    if not isinstance(config3, dict):
        errors.append(_error("api_invalid_structure"))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)
    if not _native_equal(config3, candidate):
        errors.append(_error("readback_mismatch"))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)

    try:
        autosave2 = read_autosave()
    except Exception as exc:
        errors.append(_error("autosave_readback_failed", type(exc).__name__))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)
    if not _native_equal(autosave2, candidate):
        errors.append(_error("autosave_candidate_mismatch"))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)

    # ---- exact source baseline install, then the committed receipt -----------
    err = _intent_unchanged(state_path, identity, intent_path, intent_identity, intent)
    if err is not None:
        return _result(S_HELD, op_id, [err], effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200)
    try:
        install_source(before, after)
    except Exception as exc:
        errors.append(_error("install_source_failed", type(exc).__name__))
        return _result(S_HELD, op_id, errors, effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200, installed_source=False)
    err = _intent_unchanged(state_path, identity, intent_path, intent_identity, intent)
    if err is not None:
        return _result(S_HELD, op_id, [err], effect_state=E_UNCERTAIN,
                       write_attempted=True, write_http_status=200, installed_source=True)

    receipt = _build_receipt(
        op_id, "committed", intent_identity or (0, 0),
        200, False, preimage_digest, candidate_digest,
        _sha256_hex(before), _sha256_hex(after),
    )
    _receipt_identity, err = _persist_closure(state_path, receipt)
    if err is not None:
        errors.append(err)
        return _result(S_HELD, op_id, errors, effect_state=E_APPLIED_VERIFIED,
                       write_attempted=True, write_http_status=200,
                       installed_source=True, receipt_written=False)

    return _result(S_PUBLISHED, op_id, [], effect_state=E_APPLIED_VERIFIED,
                   write_attempted=True, write_http_status=200,
                   installed_source=True, receipt_written=True)


def journal_status(state_dir: Path) -> Dict[str, Any]:
    """Read-only view of the private journal for the owning wrapper.

    Never creates anything: a missing journal simply reports no records.
    """
    state_path = Path(state_dir)
    if os.path.islink(str(state_path)):
        return {"ok": False, "errors": [_error("state_dir_symlink")]}
    if not state_path.exists():
        return {"ok": True, "pending_op_ids": [], "intents": [], "receipts": {}}
    identity, err = _ensure_private_dir(state_path)
    if err is not None:
        return {"ok": False, "errors": [err]}
    journal = _Journal(state_path)
    if journal.custody_errors:
        return {"ok": False, "errors": list(journal.custody_errors)}
    _, err = _closed_history_tip(journal)
    if err is not None:
        return {"ok": False, "errors": [err]}
    pending = journal.pending_ops()
    out: Dict[str, Any] = {
        "ok": True,
        "pending_op_id": pending[0] if len(pending) == 1 else None,
        "pending_op_ids": pending,
        "intents": sorted(journal.intents),
        "receipts": {},
    }
    for op_id in sorted(journal.receipts):
        receipt = _receipt_for(journal, op_id)
        out["receipts"][op_id] = None if receipt is None else receipt.get("closure")
    return out
