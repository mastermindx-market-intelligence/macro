"""scripts/metabolism_journal.py — Per-cycle journal for the Metabolism loop (A1).

STATELESS-CATTLE LAW (R-AUT-3): all loop state lives in git artifacts.
This module is the sole canonical writer/reader of
data/metabolism/journal/<cycle_id>.json.

Schema (metabolism.journal.v1):
  {
    "schema":     "metabolism.journal.v1",
    "cycle_id":   str,           # e.g. "cycle-2026-07-09-0001"
    "stage":      str,           # last-written stage name
    "status":     str,           # "pending" | "running" | "done" | "failed" | "noop_paused"
    "auth_ok":    bool | None,   # result of A2 preflight (None = not yet run)
    "artifacts":  list[str],     # paths of artifacts produced so far
    "next_stage": str | None,    # stage to run next (null when done/failed)
    "ts":         str,           # ISO-8601 UTC of last update
    "stages":     dict,          # per-stage completion records
  }

RESUME SEMANTICS:
  - start_stage()  → sets stage="<name>", status="running", ts=now; idempotent if
    already "done" for that stage (returns existing record without overwriting).
  - finish_stage() → records status for a stage in journal["stages"][name]; if the
    stage was the last → sets top-level status to "done".
  - is_stage_done() → True when journal["stages"][name]["status"] == "done".
  - The caller loop: if is_stage_done("sense"): skip sense.  Only run pending stages.

NEVER-RAISE CONTRACT (mirrors governance.py):
  All public functions catch ALL exceptions, log a warning, and return a safe
  fallback.  A journal failure must never abort the stage that invoked it.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import copy
import fcntl
import re
import secrets
import stat
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SCHEMA = "metabolism.journal.v1"
_JOURNAL_SUBDIR = Path("data") / "metabolism" / "journal"

_VALID_STATUSES = frozenset({"pending", "running", "done", "failed", "noop_paused"})

# These are serialization and I/O helpers for the incumbent journal, audit,
# market-state and lessons owners. They do not create another operation store.
_FABRIC_KEY = "_fabric_operations_v1"
_STATE_LIMIT = 8 * 1024 * 1024
_TEXT_LIMIT = 256 * 1024
_PURPOSES = {
    "propose": "lobe_maintenance", "adjudicate": "fable_orchestration",
    "agenda": "fable_orchestration", "attention": "fable_orchestration",
    "audit": "development_agent", "standout": "lobe_analysis",
    "pick_autopsies": "lobe_analysis", "dream": "lobe_analysis",
    "trade_memory": "portfolio_analysis",
}
_OWNERS = {
    "propose": "journal", "adjudicate": "journal", "agenda": "journal",
    "attention": "journal", "dream": "journal", "audit": "audit",
    "standout": "market", "pick_autopsies": "market", "trade_memory": "private_row",
}
# The strict top-level fields an audit owner may publish. They are the only
# verdict fields an audit original may commit, and the only ones a consumer
# may read back as an audited result.
_AUDIT_RECORD_FIELDS = ("schema", "pr_number", "proposal_id", "head_sha", "verdict",
                        "deterministic_ok", "llm_verdict", "confidence", "findings",
                        "rationale", "ts")
# The audit owner document also carries the publication custody of the verdict
# it holds: the exact governance event that was appended for it, and the
# acknowledgement that event received. It is never a verdict field and it is
# never readable as one.
_AUDIT_PUBLICATION_KEY = "publication"
# The closed field set of one publication custody record. A pending
# publication carries exactly the intent fields; an acknowledged publication
# additionally carries the durable receipt of its governance event. Anything
# else in the owner document is a foreign shape and is never readable as
# publication custody.
_AUDIT_PUBLICATION_FIELDS = frozenset({
    "event_type", "target", "event_id", "ts", "head_sha", "proposal_id",
    "verdict", "deterministic_ok", "llm_verdict", "confidence",
    "decision_digest", "state", "receipt",
})
_AUDIT_PUBLICATION_BASE_FIELDS = _AUDIT_PUBLICATION_FIELDS - {"receipt"}
# The incumbent audit reply grammar. These are the audit text/type/count
# bounds, not identifier bounds: a finding is a paragraph and the rationale is
# a paragraph, so the identifier label limit would make valid historical
# verdicts unreadable. The owner of the audit record owns its grammar.
_AUDIT_REPLY_BYTE_LIMIT = 64 * 1024
_AUDIT_FINDING_LIMIT = 64
_AUDIT_FINDING_CHAR_LIMIT = 2 * 1024
_AUDIT_RATIONALE_CHAR_LIMIT = 8 * 1024


class FabricHeld(ValueError):
    """A stable, non-private reason; never a request to invoke again."""


def fabric_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def fabric_digest(value):
    return hashlib.sha256(fabric_json(value).encode("utf-8")).hexdigest()


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FabricHeld("metabolism_duplicate_json_key")
        result[key] = value
    return result


def strict_json(raw):
    def nonfinite(_):
        raise FabricHeld("metabolism_nonfinite_json")
    if not isinstance(raw, (str, bytes)) or len(raw) > _STATE_LIMIT:
        raise FabricHeld("metabolism_state_bound")
    return json.loads(raw, object_pairs_hook=_strict_pairs, parse_constant=nonfinite)


def _digest(value):
    return type(value) is str and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _label(value):
    return type(value) is str and bool(value.strip()) and len(value) <= 256


def _count(value):
    return type(value) is int and 0 <= value <= 10 ** 12


def _physical_path(path):
    """Accept macOS's root-owned /tmp alias; no application symlink is followed."""
    path = Path(path).absolute()
    if sys.platform == "darwin" and path.parts[1:2] == ("tmp",):
        alias = os.lstat("/tmp")
        if (stat.S_ISLNK(alias.st_mode) and alias.st_uid == 0
                and os.readlink("/tmp") in ("private/tmp", "/private/tmp")):
            return Path("/private/tmp").joinpath(*path.parts[2:])
    return path


def _owner_path(root, owner, unit):
    root = _physical_path(root)
    if not root.is_dir() or root.is_symlink():
        raise FabricHeld("metabolism_root_required")
    if (type(unit) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", unit)
            or ".." in unit):
        raise FabricHeld("metabolism_unit_invalid")
    if owner == "journal":
        path = root / "data/metabolism/journal" / (unit + ".json")
    elif owner == "audit" and re.fullmatch(r"[1-9][0-9]{0,12}", unit):
        path = root / "data/metabolism/audit" / (unit + ".json")
    elif owner == "market" and unit in ("us", "cn"):
        path = root / "data/standout_audit" / (unit + "_audit_state.json")
    elif owner == "lessons" and unit == "lessons":
        path = root / "data/metabolism/lessons.jsonl"
    elif owner == "bus" and unit == "bus":
        path = root / "data/metabolism/insight_bus.jsonl"
    else:
        raise FabricHeld("metabolism_owner_invalid")
    return root, path


@contextmanager
def _parent_fd(path, root, *, create=False, durable=False):
    """Hold physical ancestors through the transaction; reject replaced links."""
    path, root = _physical_path(path), _physical_path(root)
    if path == root or not path.is_relative_to(root):
        raise FabricHeld("metabolism_root_boundary")
    fds, links = [], []
    try:
        parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(parent)
        current = Path(path.anchor)
        for component in path.parent.parts[1:]:
            current = current / component
            try:
                before = os.stat(component, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                if not create or not current.is_relative_to(root) or current == root:
                    raise
                os.mkdir(component, mode=0o700, dir_fd=parent)
                os.fsync(parent)
                before = os.stat(component, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise FabricHeld("metabolism_unsafe_parent")
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=parent)
            fds.append(child)
            actual = os.fstat(child)
            identity = (actual.st_dev, actual.st_ino)
            if identity != (before.st_dev, before.st_ino):
                raise FabricHeld("metabolism_parent_changed")
            links.append((parent, component, child, identity))
            if durable and (current == root or current.is_relative_to(root)):
                os.fsync(child)
                os.fsync(parent)
            parent = child

        def check():
            for parent_fd, component, child_fd, identity in links:
                named = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
                actual = os.fstat(child_fd)
                if (not stat.S_ISDIR(named.st_mode) or
                        (named.st_dev, named.st_ino) != identity or
                        (actual.st_dev, actual.st_ino) != identity):
                    raise FabricHeld("metabolism_parent_changed")
        check()
        yield parent, check
        check()
    finally:
        for fd in reversed(fds):
            os.close(fd)


class _OwnedBytes:
    def __init__(self, parent, name, check, *, byte_limit=_STATE_LIMIT):
        self.parent, self.name, self.check = parent, name, check
        self.byte_limit = byte_limit

    def _over_limit(self, size):
        return self.byte_limit is not None and size > self.byte_limit

    def read(self):
        self.check()
        try:
            fd = os.open(self.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=self.parent)
        except FileNotFoundError:
            return {"raw": None, "identity": None, "mode": 0o600}
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or before.st_uid != os.geteuid() or self._over_limit(before.st_size)):
                raise FabricHeld("metabolism_unsafe_state")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(self.byte_limit + 1 if self.byte_limit is not None else -1)
            after = os.fstat(fd)
            named = os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)
            identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns,
                                  x.st_ctime_ns, x.st_uid, x.st_nlink)
            if (self._over_limit(len(raw)) or identity(before) != identity(after)
                    or identity(after) != identity(named)):
                raise FabricHeld("metabolism_state_changed")
            self.check()
            return {"raw": raw, "identity": identity(after),
                    "mode": stat.S_IMODE(after.st_mode)}
        finally:
            os.close(fd)

    def replace(self, expected, raw):
        if type(raw) is not bytes or self._over_limit(len(raw)):
            raise FabricHeld("metabolism_state_bound")
        if self.read() != expected:
            raise FabricHeld("metabolism_state_cas_failed")
        name = "." + self.name + "." + secrets.token_hex(12) + ".tmp"
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     expected["mode"], dir_fd=self.parent)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
            staged = os.fstat(fd)
            if self.read() != expected:
                raise FabricHeld("metabolism_state_cas_failed")
            self.check()
            os.replace(name, self.name, src_dir_fd=self.parent, dst_dir_fd=self.parent)
            os.fsync(self.parent)
            actual = self.read()
            if (actual["raw"] != raw or actual["identity"][:2] !=
                    (staged.st_dev, staged.st_ino)):
                raise FabricHeld("metabolism_state_readback_unknown")
            return actual
        finally:
            os.close(fd)
            try:
                os.unlink(name, dir_fd=self.parent)
            except FileNotFoundError:
                pass

    def publish_absent(self, raw):
        """Publish one complete keep-first file without replacing any named file."""
        if type(raw) is not bytes or self._over_limit(len(raw)) or self.read()["raw"] is not None:
            raise FabricHeld("metabolism_existing_artifact_conflict")
        name = "."+self.name+"."+secrets.token_hex(12)+".tmp"
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.parent)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
            staged = os.fstat(fd)
            self.check()
            os.link(name, self.name, src_dir_fd=self.parent, dst_dir_fd=self.parent, follow_symlinks=False)
            os.unlink(name, dir_fd=self.parent)
            os.fsync(self.parent)
            result = self.read()
            if result["raw"] != raw or result["identity"][:2] != (staged.st_dev, staged.st_ino):
                raise FabricHeld("metabolism_state_readback_unknown")
            return result
        finally:
            os.close(fd)
            try:
                os.unlink(name, dir_fd=self.parent)
            except FileNotFoundError:
                pass


@contextmanager
def owned_bytes(root, owner, unit):
    """The same physical lock is used by model receipts and incumbent writers."""
    root, path = _owner_path(root, owner, unit)
    with _parent_fd(path, root, create=True, durable=True) as (parent, check):
        name = ".journal-owner.lock" if owner == "journal" else path.name + ".lock"
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or before.st_uid != os.geteuid()):
                raise FabricHeld("metabolism_unsafe_lock")
            fcntl.flock(fd, fcntl.LOCK_EX)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
                raise FabricHeld("metabolism_lock_changed")
            check()
            os.fsync(fd)
            os.fsync(parent)
            # Append/compaction business logs are not operation-state documents.
            # Preserve their existing total-size contract; selected lesson input
            # and individual strict JSON rows retain their own explicit bounds.
            yield _OwnedBytes(parent, path.name, check,
                              byte_limit=None if owner in ("bus", "lessons") else _STATE_LIMIT)
            check()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)



def _state_document(snapshot, owner, unit):
    raw = snapshot["raw"]
    value = (_default_journal(unit) if owner == "journal" else {}) if raw is None else strict_json(raw)
    if type(value) is not dict:
        raise FabricHeld("metabolism_state_not_object")
    if owner == "journal" and (value.get("schema") != _SCHEMA or value.get("cycle_id") != unit):
        raise FabricHeld("metabolism_foreign_journal")
    for record in _records(value).values():
        if record["owner"] != owner or record["unit"] != unit:
            raise FabricHeld("metabolism_foreign_operation")
    if owner == "audit" and _AUDIT_PUBLICATION_KEY in value:
        try:
            pr_number = int(unit)
        except (TypeError, ValueError) as exc:
            raise FabricHeld("metabolism_state_publication_invalid") from exc
        validate_audit_publication(value[_AUDIT_PUBLICATION_KEY], pr_number,
                                   require_ack=False)
    return value


def read_owner_state(root, owner, unit):
    root, path = _owner_path(root, owner, unit)
    try:
        with _parent_fd(path, root) as (parent, check):
            return _state_document(_OwnedBytes(parent, path.name, check).read(), owner, unit)
    except FileNotFoundError:
        return _default_journal(unit) if owner == "journal" else {}


def update_owner_state(root, owner, unit, updates):
    """Merge a legacy/business update; the operation map is never caller-writable."""
    with owned_bytes(root, owner, unit) as file:
        return _merge_owner_state(file, owner, unit, updates)


def _validated_audit_reply(value):
    """The native/legacy response is data; malformed fields cannot grant approval."""
    import math

    if (type(value) is not dict
            or set(value) != {"verdict", "confidence", "findings", "rationale"}
            or type(value["verdict"]) is not str
            or value["verdict"] not in {"approve", "reject"}):
        return None
    confidence = value["confidence"]
    if (type(confidence) not in (int, float) or not 0 <= confidence <= 1
            or not math.isfinite(confidence)):
        return None
    findings, rationale = value["findings"], value["rationale"]
    if (type(findings) is not list or len(findings) > _AUDIT_FINDING_LIMIT
            or type(rationale) is not str or not rationale.strip()
            or len(rationale) > _AUDIT_RATIONALE_CHAR_LIMIT):
        return None
    if any(type(f) is not str or not f.strip() or len(f) > _AUDIT_FINDING_CHAR_LIMIT
           for f in findings):
        return None
    for text in [*findings, rationale]:
        if any(ord(c) < 32 and c not in "\n\t" or ord(c) == 127 for c in text):
            return None
        try:
            text.encode("utf-8")
        except UnicodeError:
            return None
    return {
        "verdict": value["verdict"], "confidence": confidence,
        "findings": list(findings), "rationale": rationale,
    }


def _slice_braced(s):
    i, j = s.find("{"), s.rfind("}")
    if 0 <= i < j:
        return s[i:j + 1]
    return ""


def _parse_llm_reply(text, *, strict=False):
    """Decode a bounded typed verdict; native originals use strict whole-JSON mode."""
    if type(text) is not str or not text:
        return None
    try:
        if len(text.encode("utf-8")) > _AUDIT_REPLY_BYTE_LIMIT:
            return None
    except UnicodeError:
        return None
    s = text.strip()
    # Legacy formatting remains readable. A selected native original must
    # validate the actual entire result and cannot repair a partial response.
    if not strict and s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate audit member")
            result[key] = value
        return result

    def nonfinite(_value):
        raise ValueError("nonfinite audit value")

    for candidate in ((s,) if strict else (s, _slice_braced(s))):
        if not candidate:
            continue
        try:
            data = json.loads(candidate, object_pairs_hook=unique, parse_constant=nonfinite)
        except (ValueError, TypeError, RecursionError):
            continue
        validated = _validated_audit_reply(data)
        if validated is not None:
            return validated
    return None


def validate_audit_record(record, pr_number=None):
    """Validate one owned audit verdict. A malformed record is never a verdict.

    The bounds are the incumbent audit grammar: up to 64 findings of up to 2048
    characters each and a rationale of up to 8192 characters. The identifier
    label limit is not the audit grammar and would make valid historical
    verdicts unreadable.
    """
    if (type(record) is not dict or not set(record) <= set(_AUDIT_RECORD_FIELDS)
            or not {"schema", "pr_number", "head_sha", "verdict", "deterministic_ok",
                    "llm_verdict", "confidence", "findings", "rationale", "ts"} <= set(record)
            or record["schema"] != "metabolism.audit.v1"
            or type(record["pr_number"]) is not int or record["pr_number"] < 1
            or pr_number is not None and record["pr_number"] != pr_number
            or not _label(record["head_sha"])
            or record["verdict"] not in ("approve", "reject")
            or type(record["deterministic_ok"]) is not bool
            or record["llm_verdict"] is not None and not _label(record["llm_verdict"])
            or record["confidence"] is not None and (type(record["confidence"]) not in (int, float)
                or not 0 <= record["confidence"] <= 1)
            or type(record["findings"]) is not list
            or len(record["findings"]) > _AUDIT_FINDING_LIMIT
            or any(type(f) is not str or not f.strip() or len(f) > _AUDIT_FINDING_CHAR_LIMIT
                   for f in record["findings"])
            or type(record["rationale"]) is not str or not record["rationale"].strip()
            or len(record["rationale"]) > _AUDIT_RATIONALE_CHAR_LIMIT
            or not _label(record["ts"])
            or "proposal_id" in record and not (record["proposal_id"] == "" or _label(record["proposal_id"]))):
        raise FabricHeld("metabolism_audit_record_invalid")
    return record


def _audit_original_verdict(original):
    """The typed verdict an original actually holds, parsed from its own text.

    The strict whole-response parse is the only accepted reading of a retained
    original. A reply that does not decode as one bounded typed verdict is not
    a verdict at all.
    """
    text = original.get("text")
    if type(text) is not str or not text:
        return None
    return _parse_llm_reply(text, strict=True)


def _audit_outcome_matches(outcome, parsed):
    """True when a publication outcome is exactly the parsed original verdict."""
    if type(outcome) is not dict or parsed is None:
        return False
    return (type(outcome.get("confidence")) in (int, float)
            and outcome.get("verdict") == parsed["verdict"]
            and outcome.get("llm_verdict") == parsed["verdict"]
            and outcome.get("confidence") == parsed["confidence"]
            and outcome.get("rationale") == parsed["rationale"]
            and outcome.get("findings") == list(parsed["findings"]))



def _audit_document_result(document, pr_number):
    """Validate one already-read owner document, including under its write lock."""
    unit = str(pr_number)
    empty = {"status": "absent", "record": None, "original": None,
             "reason": "metabolism_audit_record_absent"}
    originals = [item for item in _records(document).values() if item["kind"] == "audit"]
    owned = {key: document[key] for key in _AUDIT_RECORD_FIELDS if key in document}
    original = None
    try:
        if not owned:
            if originals or _AUDIT_PUBLICATION_KEY in document:
                raise FabricHeld("metabolism_audit_verdict_missing")
            return empty
        record = validate_audit_record(owned, pr_number)
        publication_present = _AUDIT_PUBLICATION_KEY in document
        publication = document.get(_AUDIT_PUBLICATION_KEY)
        if publication_present:
            validate_audit_publication(publication, pr_number, record=record)
        matches = [
            candidate for candidate in originals
            if candidate["state"] == "complete" and candidate["business"] is not None
            and fabric_json(candidate["business"]["intent"]) == fabric_json(audit_publication_expected(record))]
        if len(matches) > 1:
            raise FabricHeld("metabolism_audit_operation_mismatch")
        original = matches[0] if matches else None
        if original is None:
            legacy = not originals and not publication_present
            zero_model = (
                publication_present and record["verdict"] == "reject"
                and record["deterministic_ok"] is False
                and record["llm_verdict"] is None and record["confidence"] is None
                and not any(candidate["state"] != "complete"
                            and "pr:" + unit in candidate["scope"] for candidate in originals))
            if not (legacy or zero_model):
                raise FabricHeld("metabolism_audit_operation_mismatch")
            return {"status": "audited", "record": record, "original": None,
                    "reason": "metabolism_audit_record_present"}
        if not publication_present:
            raise FabricHeld("metabolism_audit_publication_unacknowledged")
        original_record = audit_original_result(original, pr_number, publication=publication)
        if record != original_record:
            raise FabricHeld("metabolism_audit_projection_mismatch")
        return {"status": "audited", "record": record, "original": original,
                "reason": "metabolism_audit_record_present"}
    except FabricHeld as exc:
        return {"status": "held", "record": owned, "original": original or (originals[0] if originals else None),
                "reason": str(exc)}


def audit_owner_result(root, pr_number):
    """Return the same qualified audit result to public and merge consumers."""
    unit = str(pr_number)
    empty = {"status": "absent", "record": None, "original": None,
             "reason": "metabolism_audit_record_absent"}
    try:
        root, path = _owner_path(root, "audit", unit)
    except FabricHeld as exc:
        return {**empty, "reason": str(exc)}
    try:
        with _parent_fd(path, root) as (parent, check):
            document = _state_document(_OwnedBytes(parent, path.name, check).read(), "audit", unit)
    except FileNotFoundError:
        return empty
    except FabricHeld as exc:
        return {"status": "held", "record": None, "original": None, "reason": str(exc)}
    return _audit_document_result(document, pr_number)


def audit_publication_decision_digest(record):
    """The identity of one published audit decision.

    The publication time is not part of the decision identity: a retried
    publication of the same decision must reuse the same governance event
    instead of appending a second one.
    """
    return fabric_digest({key: record.get(key) for key in
                          ("pr_number", "proposal_id", "head_sha", "verdict",
                           "deterministic_ok", "llm_verdict", "confidence",
                           "findings", "rationale")})


def audit_publication_expected(record):
    """Derive the exact intent from the existing audit owner's typed verdict."""
    from engine.neuralweb.governance import event_identity
    validate_audit_record(record)
    target = "metabolism_pr:" + str(record["pr_number"])
    ts = record["ts"]
    return {"event_type": "metabolism_audit", "target": target,
            "event_id": event_identity("metabolism_audit", target, ts), "ts": ts,
            **{key: record.get(key) for key in ("head_sha", "proposal_id", "verdict",
                "deterministic_ok", "llm_verdict", "confidence")},
            "decision_digest": audit_publication_decision_digest(record)}


def validate_audit_publication(publication, pr_number, *, record=None, require_ack=True):
    """Qualify a closed intent and its full correlated governance ACK.

    A present null or pending publication is never historical absence. The
    current projection is compared only when requested, because a pending
    successor can coexist with the preceding projection during its owner CAS.
    """
    from engine.neuralweb.governance import event_identity
    if type(publication) is not dict:
        raise FabricHeld("metabolism_state_publication_invalid")
    acknowledged = publication.get("state") == "acknowledged"
    fields = _AUDIT_PUBLICATION_BASE_FIELDS | ({"receipt"} if acknowledged else set())
    if (set(publication) != fields
            or publication.get("state") not in ("pending", "acknowledged")
            or type(pr_number) is not int or pr_number < 1
            or publication["event_type"] != "metabolism_audit"
            or publication["target"] != "metabolism_pr:" + str(pr_number)
            or not _label(publication["ts"])
            or not _digest(publication["decision_digest"])):
        raise FabricHeld("metabolism_state_publication_invalid")
    validate_audit_record({
        "schema": "metabolism.audit.v1", "pr_number": pr_number,
        **{key: publication[key] for key in ("head_sha", "proposal_id", "verdict",
            "deterministic_ok", "llm_verdict", "confidence", "ts")},
        "findings": [], "rationale": "publication grammar",
    }, pr_number)
    if publication["event_id"] != event_identity(
            publication["event_type"], publication["target"], publication["ts"]):
        raise FabricHeld("metabolism_audit_publication_identity_mismatch")
    if record is not None:
        validate_audit_record(record, pr_number)
        expected = audit_publication_expected(record)
        if any(publication[key] != value for key, value in expected.items()):
            raise FabricHeld("metabolism_audit_publication_mismatch")
    if require_ack and not acknowledged:
        raise FabricHeld("metabolism_audit_publication_unacknowledged")
    if acknowledged:
        expected_receipt = {key: publication[key] for key in
                            ("event_id", "event_type", "target", "ts")}
        expected_receipt["evidence"] = {key: publication[key] for key in
            ("head_sha", "proposal_id", "verdict", "deterministic_ok", "llm_verdict", "confidence")}
        if (type(publication["receipt"]) is not dict
                or publication["receipt"] != expected_receipt
                or fabric_json(publication["receipt"]) != fabric_json(expected_receipt)):
            raise FabricHeld("metabolism_audit_publication_receipt_mismatch")
    return publication


def audit_original_result(original, pr_number, *, publication=None):
    """Read this completed original's frozen verdict and publication evidence.

    New originals retain their own ACK in their incumbent business outcome.
    A legacy completion may use the current publication only when it matches
    this exact result. A superseded completion without its ACK stays held.
    """
    validate_operation(original)
    if (original["kind"] != "audit" or original["owner"] != "audit"
            or original["unit"] != str(pr_number) or original["scope"] != ["pr:" + str(pr_number)]
            or original["state"] != "complete" or original["business"] is None):
        raise FabricHeld("metabolism_audit_operation_incomplete")
    logical = original["logical"]
    facts = logical.get("facts")
    if (type(facts) is not dict or facts.get("pr_number") != pr_number
            or not _label(facts.get("head_sha"))
            or not _digest(facts.get("proposal_digest"))
            or not _digest(facts.get("diff_digest"))
            or facts.get("response_contract") != "complete-text-v1"
            or original["request"]["response_contract"] != facts["response_contract"]):
        raise FabricHeld("metabolism_audit_operation_mismatch")
    outcome = original["business"]["outcome"]
    fields = {"governance", "target", "event_id", "verdict", "llm_verdict", "confidence",
              "findings", "rationale", "ts", "head_sha", "proposal_id", "provider", "served_model"}
    if (type(outcome) is not dict or not fields <= set(outcome)
            or not set(outcome) <= fields | {"governance_receipt"}):
        raise FabricHeld("metabolism_audit_outcome_mismatch")
    parsed = _audit_original_verdict(original)
    if not _audit_outcome_matches(outcome, parsed):
        raise FabricHeld("metabolism_audit_outcome_mismatch")
    response = original["receipt"].get("response")
    if (type(response) is not dict or response.get("stop_reason") != "end_turn"
            or not response.get("content_shape")
            or any(kind != "text" for kind in response["content_shape"])
            or not _label(original["receipt"]["provider"])):
        raise FabricHeld("metabolism_audit_response_incomplete")
    if (outcome["head_sha"] != facts["head_sha"]
            or ("proposal_id" in facts and outcome["proposal_id"] != facts["proposal_id"])
            or outcome["provider"] != original["receipt"]["provider"]
            or outcome["served_model"] != original["receipt"]["served_model"]):
        raise FabricHeld("metabolism_audit_operation_mismatch")
    record = {
        "schema": "metabolism.audit.v1", "pr_number": pr_number,
        "proposal_id": outcome["proposal_id"], "head_sha": facts["head_sha"],
        "verdict": parsed["verdict"], "deterministic_ok": True,
        "llm_verdict": parsed["verdict"], "confidence": parsed["confidence"],
        "findings": list(parsed["findings"]), "rationale": parsed["rationale"], "ts": outcome["ts"],
    }
    validate_audit_record(record, pr_number)
    intent = audit_publication_expected(record)
    if (fabric_json(original["business"]["intent"]) != fabric_json(intent)
            or outcome["governance"] != intent["event_type"]
            or outcome["target"] != intent["target"]
            or outcome["event_id"] != intent["event_id"]):
        raise FabricHeld("metabolism_audit_original_publication_mismatch")
    if "governance_receipt" in outcome:
        retained_publication = {**intent, "state": "acknowledged",
                                "receipt": outcome["governance_receipt"]}
    elif publication is not None:
        retained_publication = publication
    else:
        raise FabricHeld("metabolism_audit_original_ack_missing")
    validate_audit_publication(retained_publication, pr_number, record=record)
    return record


def _audit_zero_model_admission(document, unit):
    """Serialize zero-model publication against model claims in this owner."""
    if any(item["kind"] == "audit" and item["state"] != "complete"
           and "pr:" + str(unit) in item["scope"] for item in _records(document).values()):
        raise FabricHeld("metabolism_original_held")


def _audit_model_claim_admission(document, owner):
    """A pending zero-model publication retains the same audit owner's turn."""
    if (owner == "audit" and _AUDIT_PUBLICATION_KEY in document
            and document[_AUDIT_PUBLICATION_KEY]["state"] == "pending"):
        raise FabricHeld("metabolism_audit_publication_held")


def audit_publication_intent(root, pr_number, intent, *, replace_acknowledged=False):
    """Own the exact publication intent of one audit verdict.

    The intent is persisted before any external append. A pending publication
    of the same decision is reused — its event identity and its publication
    time are the original ones, so a retry reconciles instead of appending a
    second event. A pending publication of a different decision is never
    overwritten: the owner holds it until its own reconciliation. An
    acknowledged publication of the same decision is reused as the completed
    publication it already is — same event identity, same completion, no
    second event — and an acknowledged publication of a different decision is
    a conflict that only an explicit transition may clear.
    """
    unit = str(pr_number)
    validate_audit_publication({**copy.deepcopy(intent), "state": "pending"},
                               pr_number, require_ack=False)
    with owned_bytes(root, "audit", unit) as file:
        before = file.read()
        document = _state_document(before, "audit", unit)
        _audit_zero_model_admission(document, unit)
        existing = document.get(_AUDIT_PUBLICATION_KEY)
        if type(existing) is dict and existing.get("state") == "pending":
            if existing.get("decision_digest") != intent.get("decision_digest"):
                raise FabricHeld("metabolism_audit_publication_held")
            return copy.deepcopy(existing)
        if type(existing) is dict and existing.get("state") == "acknowledged":
            if existing.get("decision_digest") == intent.get("decision_digest"):
                return copy.deepcopy(existing)
            # A new deterministic rejection may supersede an acknowledged
            # verdict through this same owner CAS. Never replace a pending
            # publication, an unqualified prior result, or an incomplete model.
            qualified = _audit_document_result(document, pr_number)
            if (not replace_acknowledged or qualified["status"] != "audited"
                    or intent["verdict"] != "reject" or intent["deterministic_ok"] is not False
                    or intent["llm_verdict"] is not None or intent["confidence"] is not None
                    or any(item["kind"] == "audit" and item["state"] != "complete"
                           and "pr:" + unit in item["scope"]
                           for item in _records(document).values())):
                raise FabricHeld("metabolism_audit_publication_conflict")
        document[_AUDIT_PUBLICATION_KEY] = {**copy.deepcopy(intent), "state": "pending"}
        file.replace(before, (fabric_json(document) + "\n").encode())
        return copy.deepcopy(document[_AUDIT_PUBLICATION_KEY])


def audit_publication_commit(root, pr_number, record, *, event_id, receipt):
    """Publish one audit verdict and its acknowledged governance event together.

    The verdict and the acknowledgement become visible in one owner commit. A
    publication that is not owned by this event, or that was already
    acknowledged with a different content, is never overwritten.
    """
    unit = str(pr_number)
    validate_audit_record(record, pr_number)
    updates = {key: record[key] for key in _AUDIT_RECORD_FIELDS if key in record}
    with owned_bytes(root, "audit", unit) as file:
        before = file.read()
        document = _state_document(before, "audit", unit)
        _audit_zero_model_admission(document, unit)
        publication = document.get(_AUDIT_PUBLICATION_KEY)
        if type(publication) is not dict or publication.get("event_id") != event_id:
            raise FabricHeld("metabolism_audit_publication_missing")
        validate_audit_publication(
            {**publication, "state": "acknowledged", "receipt": receipt},
            pr_number, record=record)
        if publication.get("state") == "acknowledged":
            if (publication.get("receipt") == receipt
                    and all(document.get(key) == value for key, value in updates.items())):
                return True
            raise FabricHeld("metabolism_audit_publication_conflict")
        document.update(copy.deepcopy(updates))
        document[_AUDIT_PUBLICATION_KEY] = {**publication, "state": "acknowledged",
                                             "receipt": copy.deepcopy(receipt)}
        file.replace(before, (fabric_json(document) + "\n").encode())
    return True


def host_profile():
    """The incumbent host workload profile.

    The journal owns the selection of a retained original, so it also owns the
    one host-profile read the shared owners need. Consumers never read the
    environment for it themselves.
    """
    return os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")


def _merge_owner_state(file, owner, unit, updates):
    """Merge through an already held transaction of this incumbent owner."""
    if type(updates) is not dict:
        raise FabricHeld("metabolism_state_update_invalid")
    before = file.read()
    current = _state_document(before, owner, unit)
    protected = copy.deepcopy(current.get(_FABRIC_KEY))
    updated = {**current, **copy.deepcopy(updates)}
    if owner == "journal":
        updated["stages"] = {**current.get("stages", {}), **updated.get("stages", {})}
        for stage, value in current.get("stages", {}).items():
            if isinstance(value, dict) and value.get("status") == "done":
                updated["stages"][stage] = copy.deepcopy(value)
        updated["artifacts"] = list(dict.fromkeys(
            current.get("artifacts", []) + updated.get("artifacts", [])))
    updated.pop(_FABRIC_KEY, None)
    if protected is not None:
        updated[_FABRIC_KEY] = protected
    _state_document({"raw": fabric_json(updated)}, owner, unit)
    file.replace(before, (fabric_json(updated) + "\n").encode())
    return updated


def _inspection(value, purpose):
    if (type(value) is not dict or set(value) != {"provider", "model", "cap_id",
            "capability_id", "cost_basis", "workload_policy", "transport_identity"}
            or any(not _label(value[k]) for k in ("provider", "model", "cap_id", "capability_id", "cost_basis"))
            or not _digest(value["transport_identity"])):
        raise FabricHeld("metabolism_inspection_invalid")
    policy = value["workload_policy"]
    if (type(policy) is not dict or set(policy) != {"schema", "policy_revision", "policy_hash",
            "profiles", "execution_surface", "allowed_order", "denied_order"}
            or policy["schema"] != "mastermind.provider_workload_decision.v1"
            or type(policy["policy_revision"]) is not int or policy["policy_revision"] < 1
            or not _digest(policy["policy_hash"]) or type(policy["profiles"]) is not list
            or any(not _label(p) for p in policy["profiles"])
            or len(set(policy["profiles"])) != len(policy["profiles"])
            or purpose not in policy["profiles"]):
        raise FabricHeld("metabolism_workload_receipt_invalid")
    # Two genuine workload classifications are admitted, and neither is
    # relabeled as the other. An inference consumer keeps its exact form; a
    # native-purpose consumer keeps its own empty-order decision. The transport
    # kind (native_cli, fabric, oauth) is not a workload classification, and
    # every other surface or order is refused.
    surface = policy["execution_surface"]
    if surface == "inference":
        if policy["allowed_order"] != ["fabric"] or policy["denied_order"] != []:
            raise FabricHeld("metabolism_workload_receipt_invalid")
    elif surface == "native_agent":
        if policy["allowed_order"] != [] or policy["denied_order"] != []:
            raise FabricHeld("metabolism_workload_receipt_invalid")
    else:
        raise FabricHeld("metabolism_workload_receipt_invalid")


def _operation_identity(record):
    return {k: record[k] for k in ("root", "owner", "unit", "kind", "logical", "scope",
                                  "request", "inspection", "selection")}


def _served_model_matches(served, inspection):
    """True when the model that actually served is the one that was requested.

    A fabric claim is served by exactly the model its recipe pinned. A legacy
    inference waterfall reports a dated variant of the requested model family;
    the family must still be the requested one.
    """
    requested = inspection["model"]
    if served == requested:
        return True
    return (inspection["cost_basis"] == "incumbent_inference" and type(served) is str
            and bool(requested) and served.startswith(requested + "-"))


def _original_identity(record):
    """The immutable consumer facts that identify one logical original.

    The current policy (inspection/selection) is deliberately absent: a
    selector removal, a workload-policy revision or a changed route must not
    make a saved original unreachable. The literal request text is absent too
    because a consumer may freeze a per-attempt marker inside it; the frozen
    request-determining facts belong in ``logical``.
    """
    return {k: record[k] for k in ("root", "owner", "unit", "kind", "logical", "scope")}


def saved_original(records, kind, identity):
    """Find the retained original for one immutable consumer identity.

    Returns the saved record when it may still be used, or None when this
    identity has no saved original yet. A retained original that is claimed,
    observed, held or ambiguously publishing is never handed back for a new
    call: it stays held until it is reconciled by its own owner.
    """
    matches = [record for record in records.values()
               if record["kind"] == kind and _original_identity(record) == identity]
    if not matches:
        return None
    complete = [record for record in matches if record["state"] == "complete"]
    if complete:
        if len({record["text_digest"] for record in complete}) != 1:
            raise FabricHeld("metabolism_original_ambiguous")
        return sorted(complete, key=lambda record: record["operation_id"])[0]
    resumable = [record for record in matches if record["state"] == "known"]
    if len(resumable) == 1:
        return resumable[0]
    if len(resumable) > 1:
        raise FabricHeld("metabolism_original_ambiguous")
    # Claimed, observed, publishing and held originals are never recoverable
    # by sending again; an ambiguous publication stays held.
    raise FabricHeld("metabolism_original_held")


def original_identity(root, kind, unit, logical, scope):
    """The immutable consumer identity of one logical original."""
    return {"root": str(_physical_path(root)), "owner": _OWNERS[kind], "unit": str(unit),
            "kind": kind, "logical": copy.deepcopy(logical), "scope": list(scope)}


def saved_original_for(root, kind, unit, logical, scope):
    """Read the retained original of one identity through its own owner.

    Returns None when this identity has no saved original. A held, claimed,
    observed or ambiguous original raises instead: it is never handed back for
    a new call.
    """
    identity = original_identity(root, kind, unit, logical, scope)
    document = read_owner_state(root, _OWNERS[kind], str(unit))
    return saved_original(_records(document), kind, identity)


def _operation_key(record, identity):
    if record["kind"] == "trade_memory":
        return "metabolism:episode:" + fabric_digest({
            "operator": record["logical"].get("operator"), "episode": record["unit"],
        })[:40]
    return "metabolism:" + identity[:48]


def validate_operation(record):
    keys = {"schema", "operation_id", "attempt_nonce", "root", "owner", "unit", "kind",
            "logical", "scope", "request", "inspection", "selection", "identity_digest",
            "state", "text", "text_digest", "receipt", "business", "error"}
    if (type(record) is not dict or set(record) != keys
            or record["schema"] != "mastermind.metabolism_fabric_operation.v1"
            or record["kind"] not in _PURPOSES or record["owner"] != _OWNERS[record["kind"]]
            or not _label(record["unit"]) or type(record["root"]) is not str
            or not Path(record["root"]).is_absolute()
            or type(record["logical"]) is not dict or type(record["scope"]) is not list
            or not record["scope"] or any(not _label(x) for x in record["scope"])
            or len(set(record["scope"])) != len(record["scope"])
            or type(record["attempt_nonce"]) is not str
            or not re.fullmatch(r"[0-9a-f]{32}", record["attempt_nonce"])):
        raise FabricHeld("metabolism_operation_invalid")
    _inspection(record["inspection"], _PURPOSES[record["kind"]])
    request = record["request"]
    if (type(request) is not dict or set(request) != {"system", "user", "max_tokens", "response_contract"}
            or request["response_contract"] != "complete-text-v1"
            or any(type(request[k]) is not str or not request[k].strip()
                   or len(request[k].encode()) > _TEXT_LIMIT for k in ("system", "user"))
            or type(request["max_tokens"]) is not int or not 1 <= request["max_tokens"] <= 16000
            or type(record["selection"]) is not dict
            or set(record["selection"]) != {"mode", "host_profile"}
            or not _label(record["selection"]["mode"])
            or record["selection"]["host_profile"] is not None and not _label(record["selection"]["host_profile"])):
        raise FabricHeld("metabolism_request_invalid")
    identity = fabric_digest(_operation_identity(record))
    if (record["identity_digest"] != identity
            or record["operation_id"] != _operation_key(record, identity)
            or record["state"] not in ("claimed", "observed", "known", "held", "publishing", "complete")
            or record["text"] is not None and (type(record["text"]) is not str
                or len(record["text"].encode()) > _TEXT_LIMIT)
            or record["text_digest"] != (fabric_digest(record["text"]) if record["text"] is not None else None)
            or record["error"] is not None and not _label(record["error"])):
        raise FabricHeld("metabolism_operation_commitment_invalid")
    if record["state"] == "claimed":
        if any(record[k] is not None for k in ("text", "text_digest", "receipt", "business", "error")):
            raise FabricHeld("metabolism_claim_invalid")
        return
    receipt = record["receipt"]
    receipt_keys = {"operation_id", "provider", "requested_model", "served_model",
                    "observation", "usage", "close", "effect_unknown"}
    if (type(receipt) is not dict or not receipt_keys <= set(receipt)
            or not set(receipt) <= receipt_keys | {"response"}
            or receipt["operation_id"] != record["operation_id"]
            or (receipt["provider"] != record["inspection"]["provider"]
                and record["inspection"]["cost_basis"] != "incumbent_inference")
            or receipt["requested_model"] != record["inspection"]["model"]
            or receipt["served_model"] is not None and not _label(receipt["served_model"])
            or type(receipt["effect_unknown"]) is not bool):
        raise FabricHeld("metabolism_response_receipt_invalid")
    response = receipt.get("response")
    if response is not None and (type(response) is not dict
            or set(response) != {"stop_reason", "content_shape"}
            or response["stop_reason"] is not None and not _label(response["stop_reason"])
            or type(response["content_shape"]) is not list
            or any(not _label(kind) for kind in response["content_shape"])):
        raise FabricHeld("metabolism_response_receipt_invalid")
    observation, usage, close = receipt["observation"], receipt["usage"], receipt["close"]
    if usage is None and (observation is not None or receipt["served_model"] is not None or record["text"] is not None):
        raise FabricHeld("metabolism_usage_missing_from_observation")
    if observation is not None and (type(observation) is not dict or set(observation) != {
            "request_id", "serving_model", "input_tokens", "output_tokens"}
            or observation["request_id"] != record["operation_id"] + ":brain:0"
            or observation["serving_model"] is not None and not _label(observation["serving_model"])
            or any(observation[k] is not None and not _count(observation[k]) for k in ("input_tokens", "output_tokens"))):
        raise FabricHeld("metabolism_observation_invalid")
    if usage is not None and (type(usage) is not dict or set(usage) != {"input_tokens", "output_tokens",
            "completed_input_tokens", "completed_output_tokens", "usage_state"}
            or usage["usage_state"] not in ("known", "unknown")
            or any(not _count(usage[k]) for k in ("completed_input_tokens", "completed_output_tokens"))
            or any(usage[k] is not None and not _count(usage[k]) for k in ("input_tokens", "output_tokens"))
            or usage["usage_state"] == "known" and any(usage[k] != usage["completed_"+k] for k in ("input_tokens", "output_tokens"))
            or usage["usage_state"] == "unknown" and any(usage[k] is not None for k in ("input_tokens", "output_tokens"))):
        raise FabricHeld("metabolism_usage_invalid")
    if observation is not None and usage is not None:
        pair = all(observation[k] is not None for k in ("input_tokens", "output_tokens"))
        if any(usage["completed_" + k] != (observation[k] if pair else 0) for k in ("input_tokens", "output_tokens")):
            raise FabricHeld("metabolism_usage_observation_mismatch")
    if close is None:
        if not receipt["effect_unknown"]:
            raise FabricHeld("metabolism_close_missing")
    elif (type(close) is not dict or set(close) != {"disposition", "closed", "effect_unknown", "attempted"}
            or close["disposition"] not in ("closed", "local_only", "not_bound", "refused", "pending", "effect_unknown")
            or any(type(close[k]) is not bool for k in ("closed", "effect_unknown", "attempted"))
            or close["closed"] != (close["disposition"] == "closed")
            or close["closed"] and (not close["attempted"] or close["effect_unknown"])
            or close["disposition"] in ("local_only", "not_bound") and any(close[k] for k in ("closed", "effect_unknown", "attempted"))
            or close["effect_unknown"] and not receipt["effect_unknown"]):
        raise FabricHeld("metabolism_close_invalid")
    if record["state"] in ("known", "publishing", "complete"):
        if (record["error"] is not None or not record["text"] or not record["text"].strip()
                or receipt["effect_unknown"] or close is None
                or close["disposition"] not in ("closed", "local_only") or close["effect_unknown"]
                or not _served_model_matches(receipt["served_model"], record["inspection"])
                or observation is None or observation["serving_model"] != receipt["served_model"]
                or usage is None):
            raise FabricHeld("metabolism_known_result_invalid")
    if record["state"] == "held" and not _label(record["error"]):
        raise FabricHeld("metabolism_hold_reason_missing")
    business = record["business"]
    if business is not None and (type(business) is not dict or set(business) != {"intent", "outcome"}
            or type(business["intent"]) is not dict
            or business["outcome"] is not None and type(business["outcome"]) is not dict):
        raise FabricHeld("metabolism_business_receipt_invalid")
    if record["state"] in ("claimed", "observed", "known") and business is not None:
        raise FabricHeld("metabolism_business_out_of_order")
    if record["state"] == "publishing" and (business is None or business["outcome"] is not None):
        raise FabricHeld("metabolism_publication_intent_invalid")
    if record["state"] == "complete" and (business is None or business["outcome"] is None):
        raise FabricHeld("metabolism_completion_invalid")


def _records(document):
    if _FABRIC_KEY not in document:
        return {}
    envelope = document[_FABRIC_KEY]
    if (type(envelope) is not dict or set(envelope) != {"schema", "records"}
            or envelope["schema"] != "mastermind.metabolism_fabric_operations.v1"
            or type(envelope["records"]) is not dict or len(envelope["records"]) > 128):
        raise FabricHeld("metabolism_operations_invalid")
    for key, record in envelope["records"].items():
        validate_operation(record)
        if key != record["operation_id"]:
            raise FabricHeld("metabolism_operation_key_invalid")
    return envelope["records"]


def _owner_operations(root, owner, unit):
    """Inspect existing cycle journals without adding an index or a second ledger."""
    units = [unit]
    if owner == "journal":
        root, path = _owner_path(root, owner, unit)
        try:
            with _parent_fd(path, root) as (parent, check):
                units = sorted(name[:-5] for name in os.listdir(parent) if name.endswith(".json"))
                if len(units) > 4096:
                    raise FabricHeld("metabolism_journal_census_bound")
                check()
        except FileNotFoundError:
            units = []
    result, total = [], 0
    for actual_unit in units:
        document = read_owner_state(root, owner, actual_unit)
        total += len(fabric_json(document).encode())
        if total > 32 * 1024 * 1024:
            raise FabricHeld("metabolism_journal_census_bound")
        for record in _records(document).values():
            if (record["root"] != str(_physical_path(root)) or record["owner"] != owner
                    or record["unit"] != actual_unit):
                raise FabricHeld("metabolism_foreign_operation")
            result.append(record)
    return result


def guard_saved(root, owner, unit, kind, scope, *, owned=None):
    """Read original holds before config, model discovery, force or mutable caps.

    ``owned`` is the caller's own in-flight claim. It is exempt from the hold
    only when the owner still stores exactly that claim: its identity, its
    attempt nonce, its frozen scope and its current stored content must all
    match. Every other incomplete original that overlaps the scope still
    holds, so a foreign or concurrent claim is never borrowed.
    """
    records = _owner_operations(root, owner, unit)
    owned_id = None
    if owned is not None:
        if (type(owned) is not dict or owned.get("owner") != owner
                or owned.get("unit") != str(unit) or owned.get("kind") != kind
                or owned.get("state") != "claimed"
                or owned.get("root") != str(_physical_path(root))
                or type(owned.get("scope")) is not list
                or not set(owned["scope"]).intersection(scope)
                or not _label(owned.get("operation_id"))):
            raise FabricHeld("metabolism_owned_claim_invalid")
        owned_id = owned["operation_id"]
        current = [record for record in records if record["operation_id"] == owned_id]
        if not current or current[0] != owned:
            raise FabricHeld("metabolism_owned_claim_changed")
    for record in records:
        if (record["kind"] == kind and record["state"] != "complete"
                and set(record["scope"]).intersection(scope)
                and record["operation_id"] != owned_id):
            raise FabricHeld("metabolism_original_held")


@contextmanager
def native_publication_guard(root, owner, unit, kind, scope):
    """Serialize a legacy write with the same owner's selected claim boundary."""
    with owned_bytes(root, owner, unit) as file:
        guard_legacy_route(root, kind, unit, scope)
        yield file


def guard_legacy_route(root, kind, unit, scope, *, cfg=None, providers=None, reason=None,
                       owned=None):
    """An entered legacy path cannot change routes or adopt a selected recipe."""
    guard_saved(root, _OWNERS[kind], str(unit), kind, scope, owned=owned)
    from engine import llm_auth
    try:
        if (llm_auth.application_mode_id(cfg) is not None
                or providers is not None and llm_auth.is_fabric_selection(providers)
                or isinstance(reason, str) and reason.startswith("fabric_")):
            raise FabricHeld("metabolism_selection_changed")
    except FabricHeld:
        raise
    except Exception as exc:
        raise FabricHeld("metabolism_selection_changed") from exc


def legacy_provider_call(root, kind, unit, scope, providers, invoke, *, context, cfg=None):
    from engine import llm_auth
    guard_legacy_route(root, kind, unit, scope, cfg=cfg, providers=providers)
    try:
        result = llm_auth.make_call(providers, invoke, context=context)
    except llm_auth.FabricProviderError as exc:
        raise FabricHeld("metabolism_selection_changed") from exc
    guard_legacy_route(root, kind, unit, scope, cfg=cfg, providers=providers, reason=result[1])
    return result


def selected_factory(root, kind, cfg=None):
    from engine import llm_auth
    from engine.provider_production_modes import make_application_fabric_factory
    if kind not in _PURPOSES:
        raise FabricHeld("metabolism_kind_invalid")
    cfg = copy.deepcopy(cfg or {})
    mode = llm_auth.application_mode_id(cfg)
    if mode is None:
        return None, cfg
    lane = "metabolism-" + kind.replace("_", "-")
    selected = {**cfg, "provider_order": ["fabric"], "usage_lane": lane, "oauth_pool_lane": lane}
    selected.setdefault("workload_profile", _PURPOSES[kind])
    factory = make_application_fabric_factory(mode_id=mode, lane=lane, root=_physical_path(root),
        workload_cfg={"workload_profile": _PURPOSES[kind], "provider_order": ["fabric"]})
    return factory, selected


def guard_native_route(root, kind, unit, scope, *, cfg=None, model_requested=True,
                       providers=None, reason=None, owned=None):
    """Consult the real purpose policy before any incumbent native model path.

    Structural, zero-model work stays available. A selected native-agent purpose
    must never fall through to an injected provider, credential preflight, or an
    inference workload relabel. The original owner is inspected even after the
    selector disappears. This boundary does not claim a native job was admitted.

    ``owned`` is the caller's own in-flight claim; it never exempts another
    original from the hold.
    """
    if kind not in {"propose", "adjudicate", "agenda", "attention", "audit"}:
        raise FabricHeld("metabolism_native_kind_invalid")
    guard_saved(root, _OWNERS[kind], str(unit), kind, scope, owned=owned)
    if not model_requested:
        return
    try:
        from engine import llm_auth
        factory, selected = selected_factory(root, kind, cfg)
        if factory is None:
            if ((providers is not None and llm_auth.is_fabric_selection(providers))
                    or isinstance(reason, str) and reason.startswith("fabric_")):
                raise FabricHeld("metabolism_selected_recipe_requires_original")
            return
        factory.inspect(selected)
    except FabricHeld:
        raise
    except Exception as exc:
        raise FabricHeld("metabolism_selected_native_policy_refused") from exc
    # An inference allowance alone cannot create the native task, workspace and
    # accounting original required by these organizational consumers.
    raise FabricHeld("metabolism_native_operation_binding_required")


def native_provider_call(root, kind, unit, scope, providers, invoke, *, context, cfg=None,
                         owned=None):
    """Guard the incumbent call before/after its actual shared-auth boundary."""
    from engine import llm_auth
    guard_native_route(root, kind, unit, scope, cfg=cfg, providers=providers, owned=owned)
    try:
        result = llm_auth.make_call(providers, invoke, context=context)
    except llm_auth.FabricProviderError as exc:
        raise FabricHeld("metabolism_selected_recipe_requires_original") from exc
    guard_native_route(root, kind, unit, scope, cfg=cfg, providers=providers, reason=result[1],
                       owned=owned)
    return result


def operation_record(root, kind, unit, logical, scope, system, user, max_tokens, factory, cfg,
                     *, inspection=None, selection=None):
    from engine import llm_auth
    if inspection is None:
        inspection = factory.inspect(cfg)
    if selection is None:
        selection = {"mode": llm_auth.application_mode_id(cfg),
                     "host_profile": os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")}
    record = {"schema": "mastermind.metabolism_fabric_operation.v1", "operation_id": "",
        "attempt_nonce": secrets.token_hex(16), "root": str(_physical_path(root)),
        "owner": _OWNERS[kind], "unit": str(unit), "kind": kind, "logical": copy.deepcopy(logical),
        "scope": list(scope), "request": {"system": system, "user": user, "max_tokens": max_tokens,
            "response_contract": "complete-text-v1"}, "inspection": inspection,
        "selection": copy.deepcopy(selection),
        "identity_digest": "", "state": "claimed", "text": None, "text_digest": None,
        "receipt": None, "business": None, "error": None}
    record["identity_digest"] = fabric_digest(_operation_identity(record))
    record["operation_id"] = _operation_key(record, record["identity_digest"])
    validate_operation(record)
    return record


def validate_transition(old, new):
    validate_operation(old)
    validate_operation(new)
    if (old["operation_id"] != new["operation_id"] or old["attempt_nonce"] != new["attempt_nonce"]
            or _operation_identity(old) != _operation_identity(new)):
        raise FabricHeld("metabolism_original_changed")
    allowed = {"claimed": {"observed"}, "observed": {"known", "held"},
               "known": {"publishing", "held"}, "publishing": {"complete", "held"},
               "complete": set(), "held": set()}
    if new != old and new["state"] not in allowed[old["state"]]:
        raise FabricHeld("metabolism_transition_invalid")
    if old["state"] == "observed" and any(new[k] != old[k] for k in ("text", "text_digest")):
        raise FabricHeld("metabolism_known_result_changed")
    if old["state"] == "observed" and any(new["receipt"][k] != old["receipt"][k]
            for k in ("operation_id", "provider", "requested_model", "served_model", "observation", "usage")):
        raise FabricHeld("metabolism_known_observation_changed")
    if old["state"] in ("known", "publishing", "complete", "held") and any(
            new[k] != old[k] for k in ("text", "text_digest", "receipt")):
        raise FabricHeld("metabolism_known_result_changed")


class FabricInvocation:
    """One original operation inside one existing file owner; no resume sends."""
    def __init__(self, root, kind, unit, logical, scope, system, user, max_tokens, *,
                 cfg=None, inspection=None, selection=None):
        self.root, self.kind, self.unit = _physical_path(root), kind, str(unit)
        if kind not in _PURPOSES:
            raise FabricHeld("metabolism_kind_invalid")
        self.owner = _OWNERS[kind]
        self.factory = None
        self.cfg = copy.deepcopy(cfg) if cfg is not None else {}
        self.reused = False
        self._send_started = False
        identity = original_identity(self.root, kind, unit, logical, scope)
        # A saved original is looked up BEFORE any selection, inspection,
        # secret, nonce or admission happens. A completed original therefore
        # reopens with zero provider, credential and governance effect.
        with owned_bytes(self.root, self.owner, self.unit) as file:
            document = _state_document(file.read(), self.owner, self.unit)
            records = _records(document)
            saved = saved_original(records, kind, identity)
            if saved is not None:
                self.record = copy.deepcopy(saved)
                self.reused = True
                return
            # A different original or pending zero-model publication owns
            # this same audit turn before any provider discovery.
            _audit_model_claim_admission(document, self.owner)
            guard_saved(self.root, self.owner, self.unit, kind, scope)
        if inspection is None:
            self.factory, self.cfg = selected_factory(self.root, kind, cfg)
            if self.factory is None:
                raise FabricHeld("metabolism_selection_required")
            record = operation_record(self.root, kind, self.unit, logical, scope,
                                      system, user, max_tokens, self.factory, self.cfg)
        else:
            # A consumer that already owns its transport presents its own
            # inspected receipt; no factory and no credential are involved.
            record = operation_record(self.root, kind, self.unit, logical, scope,
                                      system, user, max_tokens, None, self.cfg,
                                      inspection=inspection, selection=selection)
        with owned_bytes(self.root, self.owner, self.unit) as file:
            before = file.read()
            document = _state_document(before, self.owner, self.unit)
            records = _records(document)
            # Journal writers share one directory lock, so the cross-cycle
            # original-hold check and the new claim are one owner transaction.
            guard_saved(self.root, self.owner, self.unit, kind, scope)
            for previous in records.values():
                if (previous["root"] != str(self.root) or previous["owner"] != self.owner
                        or previous["unit"] != self.unit):
                    raise FabricHeld("metabolism_foreign_operation")
                if previous["kind"] == kind and previous["state"] != "complete" and set(previous["scope"]).intersection(scope):
                    raise FabricHeld("metabolism_original_held")
            # Recheck zero-model custody under the final claim CAS lock.
            _audit_model_claim_admission(document, self.owner)
            # A concurrent caller that finished first owns this original.
            saved = saved_original(records, kind, identity)
            if saved is not None:
                self.record, self.reused = copy.deepcopy(saved), True
                return
            previous = records.get(record["operation_id"])
            if previous is not None:
                if previous["state"] != "complete" or _operation_identity(previous) != _operation_identity(record):
                    raise FabricHeld("metabolism_original_held")
                self.record, self.reused = copy.deepcopy(previous), True
                return
            if len(records) >= 128:
                raise FabricHeld("metabolism_operation_bound")
            document[_FABRIC_KEY] = {"schema": "mastermind.metabolism_fabric_operations.v1",
                                     "records": {**records, record["operation_id"]: record}}
            file.replace(before, (fabric_json(document) + "\n").encode())
            self.record = copy.deepcopy(record)

    @classmethod
    def reopen(cls, root, kind, unit, logical, scope):
        """Bind the retained original of one identity without a request.

        A saved original is reopened before any selection, inspection, secret,
        nonce or admission happens. Nothing here can send: the retained
        original already owns its own outcome.
        """
        self = cls.__new__(cls)
        self.root, self.kind, self.unit = _physical_path(root), kind, str(unit)
        if kind not in _PURPOSES:
            raise FabricHeld("metabolism_kind_invalid")
        self.owner = _OWNERS[kind]
        self.factory = None
        self.cfg = {}
        self.reused = True
        self._send_started = False
        identity = original_identity(self.root, kind, unit, logical, scope)
        with owned_bytes(self.root, self.owner, self.unit) as file:
            document = _state_document(file.read(), self.owner, self.unit)
            saved = saved_original(_records(document), kind, identity)
            if saved is None:
                raise FabricHeld("metabolism_original_absent")
            self.record = copy.deepcopy(saved)
        return self

    def save(self, updated, *, owner_updates=None, expected_owner_values=None):
        validate_transition(self.record, updated)
        with owned_bytes(self.root, self.owner, self.unit) as file:
            before = file.read()
            document = _state_document(before, self.owner, self.unit)
            records = _records(document)
            if records.get(self.record["operation_id"]) != self.record:
                raise FabricHeld("metabolism_operation_cas_failed")
            if owner_updates is not None:
                if self.owner == "market":
                    allowed = {"last_audit_graded_as_of", "last_postmortem_cycle_id",
                               "last_run_utc"}
                    permitted = updated["state"] == "complete"
                elif self.owner == "audit":
                    allowed = set(_AUDIT_RECORD_FIELDS) | {_AUDIT_PUBLICATION_KEY}
                    # The audit owner may own its publication intent while the
                    # verdict is still unpublished, and its verdict together
                    # with the acknowledged event when it completes.
                    permitted = (updated["state"] == "complete"
                                 or (updated["state"] == "publishing"
                                     and set(owner_updates) <= {_AUDIT_PUBLICATION_KEY}))
                else:
                    allowed, permitted = set(), False
                if (not permitted
                        or type(owner_updates) is not dict or not set(owner_updates) <= allowed
                        or type(expected_owner_values) is not dict
                        or not set(expected_owner_values) <= allowed
                        or any(document.get(key) != value for key, value in expected_owner_values.items())):
                    raise FabricHeld("metabolism_cursor_cas_failed")
                document.update(copy.deepcopy(owner_updates))
            records[self.record["operation_id"]] = copy.deepcopy(updated)
            file.replace(before, (fabric_json(document) + "\n").encode())
            self.record = copy.deepcopy(updated)

    def call(self):
        if self.reused or self._send_started or self.record["state"] != "claimed":
            raise FabricHeld("metabolism_send_not_owned")
        if self.factory is None:
            raise FabricHeld("metabolism_send_not_owned")
        self._send_started = True
        return execute_claimed_model(self.record, self.factory, self.cfg, self.save, self.confirm_claim)

    def confirm_claim(self):
        with owned_bytes(self.root, self.owner, self.unit) as file:
            document = _state_document(file.read(), self.owner, self.unit)
            if _records(document).get(self.record["operation_id"]) != self.record:
                raise FabricHeld("metabolism_claim_changed_before_bind")

    def publication_intent(self, intent, *, owner_updates=None):
        updated = copy.deepcopy(self.record)
        updated.update(state="publishing", business={"intent": copy.deepcopy(intent), "outcome": None})
        self.save(updated, owner_updates=owner_updates, expected_owner_values={})

    def complete(self, outcome, *, owner_updates=None, expected_owner_values=None):
        updated = copy.deepcopy(self.record)
        updated["state"] = "complete"
        updated["business"]["outcome"] = copy.deepcopy(outcome)
        self.save(updated, owner_updates=owner_updates,
                  expected_owner_values=expected_owner_values or {})

    def hold(self, reason):
        if self.record["state"] in ("known", "publishing"):
            updated = copy.deepcopy(self.record)
            updated.update(state="held", error=reason)
            self.save(updated)


def execute_claimed_model(record, factory, cfg, persist, confirm_claim):
    """Shared call mechanics; persist belongs to the incumbent file or private row."""
    from engine import llm_auth
    validate_operation(record)
    if record["state"] != "claimed":
        raise FabricHeld("metabolism_send_not_owned")
    provider = operation = None
    text = observed_model = error = fatal = None
    saved = None

    def receipt(closing):
        observation = provider.get("_fabric_last_observation") if provider is not None else None
        model = observed_model or (observation.get("serving_model") if isinstance(observation, dict) else None)
        close = (provider.get("_fabric_close") if provider is not None else
                 {"disposition": "not_bound", "closed": False, "effect_unknown": False, "attempted": False}) if closing else None
        unknown = (not closing or type(close) is not dict or close.get("effect_unknown") is not False
            or close.get("disposition") not in ("closed", "local_only", "not_bound")
            or bool(provider and (provider.get("_fabric_pending")
                or getattr(provider.get("_fabric_failure"), "effect_unknown", False))))
        return {"operation_id": record["operation_id"], "provider": record["inspection"]["provider"],
                "requested_model": record["inspection"]["model"], "served_model": model,
                "observation": copy.deepcopy(observation),
                "usage": llm_auth.fabric_usage(provider) if provider is not None else None,
                "close": copy.deepcopy(close), "effect_unknown": unknown}

    try:
        if ({"mode": llm_auth.application_mode_id(cfg), "host_profile": os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")} != record["selection"]
                or factory.inspect(cfg) != record["inspection"]):
            raise FabricHeld("metabolism_selection_changed")
        confirm_claim()
        bound = llm_auth.build_providers(cfg, fabric_selected=True,
            fabric_provider_factory=factory.with_inspection(record["inspection"]),
            request_id=record["operation_id"])
        if len(bound) != 1:
            raise FabricHeld("metabolism_binding_invalid")
        provider = bound[0]
        operation = llm_auth.begin_operation(bound, operation_id=record["operation_id"], context="metabolism_"+record["kind"])

        def invoke(client, model):
            nonlocal text, observed_model
            request = record["request"]
            response = client.messages.create(model=model, max_tokens=request["max_tokens"],
                system=request["system"], messages=[{"role": "user", "content": request["user"]}])
            observed_model = getattr(response, "model", None)
            blocks = getattr(response, "content", None)
            if (isinstance(blocks, (list, tuple)) and blocks and all(
                    getattr(b, "type", None) == "text" and type(getattr(b, "text", None)) is str for b in blocks)):
                candidate = "".join(b.text for b in blocks)
                if len(candidate.encode()) <= _TEXT_LIMIT:
                    text = candidate
            if getattr(response, "stop_reason", None) != "end_turn" or text is None or not text.strip():
                raise llm_auth.FabricProviderError("metabolism_response_not_complete")
            return text, None, response

        answer, reason, _ = llm_auth.make_call(operation.providers, invoke, context="metabolism_"+record["kind"])
        if answer is None or reason is not None:
            raise FabricHeld("metabolism_response_unavailable")
    except BaseException as exc:
        error = getattr(exc, "code", "metabolism_model_held")
        if not isinstance(exc, Exception):
            fatal = exc
    finally:
        try:
            saved = copy.deepcopy(record)
            saved.update(state="observed", text=text, text_digest=fabric_digest(text) if text is not None else None,
                         receipt=receipt(False), error=error)
            validate_transition(record, saved)
            persist(saved)  # retain the known observation before a possibly uncertain close
        except BaseException as exc:
            saved = None
            error = "metabolism_result_publication_unknown"
            if not isinstance(exc, Exception):
                fatal = exc
        try:
            if operation is not None:
                operation.close()
            elif provider is not None:
                llm_auth.close_fabric_provider(provider)
        except BaseException as exc:
            error = "metabolism_close_unknown"
            if not isinstance(exc, Exception):
                fatal = exc
    if saved is None:
        if fatal is not None:
            raise fatal
        raise FabricHeld("metabolism_original_held")
    final = copy.deepcopy(saved)
    final["receipt"] = receipt(True)
    held = error is not None or final["receipt"]["effect_unknown"] or not text
    final.update(state="held" if held else "known", error=error or ("metabolism_original_held" if held else None))
    validate_transition(saved, final)
    persist(final)
    if fatal is not None:
        raise fatal
    if held:
        raise FabricHeld("metabolism_original_held")
    return text


# ── Path helpers ─────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    """Auto-detect repo root from this file's location (scripts/metabolism_journal.py)."""
    return Path(__file__).resolve().parent.parent


def journal_path(cycle_id: str, root: Path | None = None) -> Path:
    """Return the path for a given cycle_id's journal file."""
    base = root if root is not None else _repo_root()
    return base / _JOURNAL_SUBDIR / f"{cycle_id}.json"


# ── Internal read/write ──────────────────────────────────────────────────────

def _read_journal(cycle_id: str, root: Path | None = None) -> dict[str, Any]:
    """Read the journal for cycle_id; returns an empty-ish default if absent or corrupt."""
    p = journal_path(cycle_id, root)
    if not p.exists():
        return _default_journal(cycle_id)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal: corrupt journal %s: %s — returning default", p, exc)
        return _default_journal(cycle_id)


def _write_journal(cycle_id: str, data: dict[str, Any], root: Path | None = None) -> bool:
    """Merge under the incumbent physical lock, preserving all original claims."""
    try:
        update_owner_state(root if root is not None else _repo_root(), "journal", cycle_id, data)
        return True
    except Exception as exc:
        log.warning("metabolism_journal: write held for %s (%s)", cycle_id, type(exc).__name__)
        return False


def _default_journal(cycle_id: str) -> dict[str, Any]:
    """Return the default (empty) journal for a new cycle."""
    return {
        "schema": _SCHEMA,
        "cycle_id": cycle_id,
        "stage": "",
        "status": "pending",
        "auth_ok": None,
        "artifacts": [],
        "next_stage": None,
        "ts": _now_iso(),
        "stages": {},
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Public API ───────────────────────────────────────────────────────────────

def load_journal(cycle_id: str, root: Path | None = None) -> dict[str, Any]:
    """Return the current journal for cycle_id (reads from disk).

    Returns
    -------
    dict — journal data (never raises).
    """
    try:
        return _read_journal(cycle_id, root)
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal.load_journal: %s", exc)
        return _default_journal(cycle_id)


def start_stage(
    cycle_id: str,
    stage: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Record that a stage has started running.

    If the stage is already "done" in the journal, returns the existing journal
    unchanged (idempotency: re-running a done stage is a no-op).

    Parameters
    ----------
    cycle_id : str
    stage    : str — stage name (e.g. "sense", "preflight", "propose")
    root     : Path | None — repo root for test isolation

    Returns
    -------
    dict — updated journal (never raises).
    """
    try:
        j = _read_journal(cycle_id, root)

        # Idempotency: if this stage is already done, skip
        existing = j.get("stages", {}).get(stage, {})
        if existing.get("status") == "done":
            log.debug("metabolism_journal.start_stage: %s/%s already done — skipping", cycle_id, stage)
            return j

        ts = _now_iso()
        j["stage"] = stage
        j["status"] = "running"
        j["ts"] = ts

        # Record per-stage entry
        if "stages" not in j:
            j["stages"] = {}
        j["stages"][stage] = {
            "status": "running",
            "started_at": ts,
        }
        _write_journal(cycle_id, j, root)
        return j
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal.start_stage(%s, %s): %s", cycle_id, stage, exc)
        return _default_journal(cycle_id)


def finish_stage(
    cycle_id: str,
    stage: str,
    status: str,
    *,
    artifacts: list[str] | None = None,
    next_stage: str | None = None,
    auth_ok: bool | None = None,
    note: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Record that a stage has finished with the given status.

    Parameters
    ----------
    cycle_id  : str
    stage     : str — stage name
    status    : str — one of "done" | "failed" | "noop_paused"
    artifacts : list[str] | None — paths produced by this stage (appended)
    next_stage: str | None — stage to run next
    auth_ok   : bool | None — if provided, sets journal["auth_ok"]
    note      : str | None — human-readable annotation
    root      : Path | None

    Returns
    -------
    dict — updated journal (never raises).
    """
    try:
        if status not in _VALID_STATUSES:
            log.warning("metabolism_journal.finish_stage: unknown status %r", status)

        j = _read_journal(cycle_id, root)
        ts = _now_iso()

        # Update per-stage record
        if "stages" not in j:
            j["stages"] = {}
        stage_rec = j["stages"].get(stage, {})
        stage_rec["status"] = status
        stage_rec["finished_at"] = ts
        if note:
            stage_rec["note"] = note
        j["stages"][stage] = stage_rec

        # Update top-level fields
        j["stage"] = stage
        j["status"] = status
        j["ts"] = ts

        if artifacts:
            existing = j.get("artifacts") or []
            j["artifacts"] = list(dict.fromkeys(existing + artifacts))  # dedup, order-stable

        if next_stage is not None:
            j["next_stage"] = next_stage

        if auth_ok is not None:
            j["auth_ok"] = auth_ok

        _write_journal(cycle_id, j, root)
        return j
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal.finish_stage(%s, %s): %s", cycle_id, stage, exc)
        return _default_journal(cycle_id)


def is_stage_done(cycle_id: str, stage: str, root: Path | None = None) -> bool:
    """Return True if stage is recorded as "done" in the journal.

    Used by loop orchestrators to skip already-completed stages (resume semantics).

    Returns
    -------
    bool — True iff the stage status == "done"; never raises.
    """
    try:
        j = _read_journal(cycle_id, root)
        return j.get("stages", {}).get(stage, {}).get("status") == "done"
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal.is_stage_done(%s, %s): %s", cycle_id, stage, exc)
        return False


def new_cycle_id(prefix: str = "cycle") -> str:
    """Generate a fresh, collision-resistant cycle ID.

    Format: ``<prefix>-<date>-<sha4>``
    e.g.  ``cycle-2026-07-09-a3f2``

    The SHA-4 suffix uses the UTC timestamp at microsecond resolution to
    distinguish rapid successive calls.  Not cryptographically random — just
    collision-resistant for nightly scheduling.
    """
    ts_str = datetime.now(timezone.utc).isoformat()
    sha4 = hashlib.sha256(ts_str.encode()).hexdigest()[:4]
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}-{date_str}-{sha4}"


def list_cycles(root: Path | None = None) -> list[str]:
    """Return sorted list of known cycle_ids (from journal directory).

    Returns
    -------
    list[str] — sorted cycle IDs; empty on error (never raises).
    """
    try:
        base = root if root is not None else _repo_root()
        d = base / _JOURNAL_SUBDIR
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.json"))
    except Exception as exc:  # noqa: BLE001
        log.warning("metabolism_journal.list_cycles: %s", exc)
        return []
