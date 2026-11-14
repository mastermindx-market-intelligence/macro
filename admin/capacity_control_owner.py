"""Narrow admin adapter to the incumbent router's ConfigRefresh owner.

The existing routes document remains the only configuration authority. This
module does not own admission, retries, providers, credentials or quota limits.
A prepared receipt is written before an atomic configuration update. Replayed
operation IDs reconcile that receipt; they never replay an uncertain mutation.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time

from .capacity_config_transaction import acquire_writer, WriterBusy, PendingConfiguration, TERMINAL

MAX_CONTROL_BYTES = 64 * 1024
_SHA = re.compile(r"^[a-f0-9]{64}$")
_ID = re.compile(r"^[a-f0-9]{32}$")


def _bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def read_private(path, maximum=MAX_CONTROL_BYTES):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("nonregular control path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
            raise ValueError("invalid control file")
        raw = os.read(fd, maximum + 1)
    finally:
        os.close(fd)
    if len(raw) > maximum:
        raise ValueError("control file exceeds bound")
    return json.loads(raw)


def atomic_private(path, raw):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("nonregular control path")
    fd, temporary = tempfile.mkstemp(prefix=".capacity-control-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if temporary:
            os.unlink(temporary)


def validate_intent(value):
    if isinstance(value, dict) and value.get("action") == "reconcile":
        if set(value) != {"operation_id", "action", "epoch", "request_id", "original"}:
            raise ValueError("invalid reconciliation envelope")
        if not _ID.fullmatch(str(value["epoch"])) or not _ID.fullmatch(str(value["request_id"])):
            raise ValueError("invalid reconciliation identity")
        original = value["original"]
        if not isinstance(original, dict) or original.get("action") not in {"apply", "validate"}:
            raise ValueError("invalid original intent")
        validate_intent(original)
        if original["operation_id"] != value["operation_id"]:
            raise ValueError("reconciliation operation mismatch")
        return value
    if not isinstance(value, dict) or set(value) != {"operation_id", "action", "epoch", "expires_at", "expected_revision", "patch"}:
        raise ValueError("invalid control envelope")
    if not _ID.fullmatch(str(value["operation_id"])) or not _ID.fullmatch(str(value["epoch"])):
        raise ValueError("invalid control identity")
    if value["action"] not in {"validate", "apply"} or not _SHA.fullmatch(str(value["expected_revision"])):
        raise ValueError("invalid control action or revision")
    expiry = value["expires_at"]
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
        raise ValueError("invalid control expiry")
    patch = value["patch"]
    if not isinstance(patch, dict) or not patch or set(patch) - {"interval_s", "routes", "aliases"}:
        raise ValueError("unsupported setting")
    if "interval_s" in patch:
        interval = patch["interval_s"]
        if isinstance(interval, bool) or not isinstance(interval, (float, int)) or interval not in {.25, .5, 1, 2, 5}:
            raise ValueError("unsupported telemetry interval")
    rows = patch.get("routes", [])
    if not isinstance(rows, list) or len(rows) > 128:
        raise ValueError("invalid route updates")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or "id" not in row or set(row)-{"id", "priority", "weight", "model_priority", "model_weight"}:
            raise ValueError("unsupported route setting")
        if not isinstance(row["id"], str) or len(row["id"]) > 128 or row["id"] in seen:
            raise ValueError("invalid route identity")
        seen.add(row["id"])
        for name in ("priority", "weight"):
            values = [row[name]] if name in row else []
            mapping = row.get("model_" + name, {})
            if not isinstance(mapping, dict) or len(mapping) > 64:
                raise ValueError("invalid model override")
            values += list(mapping.values())
            for number in values:
                if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                    raise ValueError("invalid routing value")
                if not 0 <= number <= (100000 if name == "priority" else 1000) or (name == "priority" and int(number) != number):
                    raise ValueError("routing value outside bounds")
    aliases = patch.get("aliases", {})
    if not isinstance(aliases, dict) or len(aliases) > 32:
        raise ValueError("invalid routing classes")
    for name, members in aliases.items():
        if not isinstance(name, str) or not isinstance(members, list) or not 1 <= len(members) <= 32 or not all(isinstance(m, str) for m in members) or len(set(members)) != len(members):
            raise ValueError("invalid routing class order")
    if len(_bytes(value)) > MAX_CONTROL_BYTES:
        raise ValueError("control envelope exceeds bound")
    return value


def _owner(app, gateway):
    owner = getattr(app.state, "config_refresh", None)
    if owner is None or owner.path is None or not callable(getattr(gateway, "read_document", None)) or not callable(getattr(gateway, "_routes_from_document", None)):
        raise ValueError("native configuration owner unavailable")
    return owner, Path(owner.path)


def _journal(path):
    try:
        rows = read_private(path, 256 * 1024)
    except FileNotFoundError:
        return []
    if not isinstance(rows, list) or len(rows) > 100 or not all(isinstance(r, dict) and _ID.fullmatch(str(r.get("operation_id", ""))) for r in rows):
        raise ValueError("control receipt store invalid")
    return rows


def _candidate(document, patch, gateway):
    candidate = copy.deepcopy(document)
    if "interval_s" in patch:
        observed = candidate.setdefault("observability", {})
        if not isinstance(observed, dict):
            raise ValueError("observability owner is incompatible")
        observed["interval_s"] = patch["interval_s"]
    rows = candidate.get("routes")
    if not isinstance(rows, list):
        raise ValueError("native route document incompatible")
    # The incumbent document uses route_id; do not manufacture bindings.
    by_id = {r.get("id", r.get("route_id")): r for r in rows if isinstance(r, dict)}
    for change in patch.get("routes", []):
        row = by_id.get(change["id"])
        if row is None:
            raise ValueError("route is not in the live catalog")
        for name in ("priority", "weight", "model_priority", "model_weight"):
            if name not in change:
                continue
            if name.startswith("model_"):
                if set(change[name]) - set(row.get("models", [])):
                    raise ValueError("override model is not on this route")
                existing = row.setdefault(name, {})
                if not isinstance(existing, dict):
                    raise ValueError("native override is incompatible")
                existing.update(change[name])
            else:
                row[name] = int(change[name]) if name == "priority" else change[name]
    aliases = candidate.get("aliases", {})
    for name, members in patch.get("aliases", {}).items():
        if name not in aliases or set(members) != set(aliases[name]):
            raise ValueError("routing classes can be reordered, not expanded here")
        aliases[name] = list(members)
    before = gateway._routes_from_document(document)
    after = gateway._routes_from_document(candidate)
    previously_usable = {m for r in before for m in r.models if r.effective_weight(m) > 0}
    still_usable = {m for r in after for m in r.models if r.effective_weight(m) > 0}
    if previously_usable - still_usable:
        raise ValueError("update would disable the last configured path for a model")
    return candidate


def projection(app, gateway, *, enabled=False):
    """Content-free configured/effective state, not a grant derived from a UI."""
    try:
        owner, path = _owner(app, gateway)
        document, revision = gateway.read_document(path)
        rows = _journal(path.with_name(path.name + ".admin-receipts.json"))
        cfg = app.state.settings
        return {"ok": True, "writable": bool(enabled and revision == owner.digest and not owner.error
                                               and all(r.get("state") in TERMINAL for r in rows)),
            "revision": revision, "effective_revision": owner.digest,
            "interval_s": (document.get("observability") or {}).get("interval_s", 2),
            "scope": "future_admissions_only", "aliases": {a: list(m) for a, m in cfg.aliases},
            "routes": [{"id": r.route_id, "provider": getattr(r, "pool", "") or r.route_id.split("-", 1)[0],
                        "models": list(r.models), "priority": r.priority, "weight": r.weight,
                        "model_priority": dict(getattr(r, "model_priority", {})),
                        "model_weight": dict(getattr(r, "model_weight", {}))} for r in cfg.routes],
            "receipts": [{k: r.get(k) for k in ("operation_id", "state", "code", "before_revision", "after_revision", "effective_revision", "at")} for r in rows[-8:]],
            "message": "Connected to the incumbent hot-reload owner. Credentials, enrollment, quota ceilings and paid-routing permissions are excluded." if enabled else "Control transport is not enabled by the installed observer configuration."}
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return {"ok": False, "writable": False, "message": "The incumbent configuration or receipt owner is unavailable."}


def handle(request, app, gateway, *, epoch, enabled=False, now=None, refresh_owner=None):
    """One explicit authenticated intent; duplicate IDs reconcile, never retry."""
    now = time.time() if now is None else now
    operation = request.get("operation_id") if isinstance(request, dict) else None
    result = {"operation_id": operation, "epoch": epoch, "state": "NOT_APPLIED", "code": "INVALID_CONTROL", "at": now}
    lock_fd = None
    try:
        validate_intent(request)
        if request["action"] == "reconcile":
            return reconcile(request, app, gateway, epoch=epoch, now=now, refresh_owner=refresh_owner)
        if not enabled or request["epoch"] != epoch:
            return dict(result, code="CONTROL_NOT_ENABLED_OR_EPOCH_CHANGED")
        owner, path = _owner(app, gateway)
        refresh = refresh_owner or (lambda: owner.refresh(app, gateway._routes_from_document, force=True))
        try:
            lock_fd = acquire_writer(path, operation_id=operation)
        except (WriterBusy, PendingConfiguration):
            return dict(result, state="NOT_APPLIED", code="CONTROL_OWNER_BUSY")
        journal_path = path.with_name(path.name + ".admin-receipts.json")
        receipts = _journal(journal_path)
        intent_hash = _digest(_bytes(request))
        prior = next((r for r in receipts if r["operation_id"] == operation), None)
        document, revision = gateway.read_document(path)
        if prior:
            if prior.get("intent_hash") != intent_hash:
                return dict(result, code="OPERATION_ID_CONFLICT", state="CONFLICT")
            if prior["state"] in TERMINAL:
                return {**prior, "epoch": epoch}
            os.close(lock_fd)
            lock_fd = None
            return reconcile({"operation_id": operation, "action": "reconcile", "epoch": epoch,
                              "request_id": operation, "original": request},
                             app, gateway, epoch=epoch, now=now, refresh_owner=refresh_owner)
        if request["expires_at"] < now or request["expires_at"] > now + 60:
            return dict(result, code="CONTROL_EXPIRED")
        if revision != request["expected_revision"]:
            return dict(result, state="CONFLICT", code="CONFIGURATION_REVISION_CHANGED", before_revision=revision)
        if not refresh() or owner.digest != revision:
            return dict(result, code="NATIVE_OWNER_NOT_EFFECTIVE")
        candidate = _candidate(document, request["patch"], gateway)
        body = _bytes(candidate)
        after = _digest(body)
        receipt = {**result, "intent_hash": intent_hash, "before_revision": revision,
                   "after_revision": after, "effective_revision": owner.digest, "code": "VALIDATED", "state": "VALIDATED"}
        if request["action"] == "validate":
            return receipt
        if candidate == document:
            # A no-op is readback, not fabricated write proof.
            return dict(receipt, state="NOT_APPLIED", code="NO_CHANGES", after_revision=revision)
        meta = path.stat()
        receipt.update(state="PREPARED", code="PREPARED",
                       before_file_identity=[meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns, meta.st_ctime_ns])
        receipts = (receipts + [receipt])[-100:]
        atomic_private(journal_path, _bytes(receipts))
        # Recheck under the same writer lock immediately before atomic replacement.
        if gateway.read_document(path)[1] != revision:
            receipt.update(state="CONFLICT", code="CONFIGURATION_REVISION_CHANGED")
            atomic_private(journal_path, _bytes(receipts))
            return receipt
        atomic_private(path, body)
        effective = refresh()
        current = gateway.read_document(path)[1]
        if effective and owner.digest == after and current == after:
            receipt.update(state="APPLIED", code="EFFECTIVE_REVISION_VERIFIED", effective_revision=owner.digest)
        else:
            receipt.update(state="EFFECT_UNKNOWN", code="EFFECTIVE_REVISION_NOT_CONFIRMED", effective_revision=owner.digest)
        atomic_private(journal_path, _bytes(receipts))
        return receipt
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        # If the prepared record exists, effects require reconciliation, not replay.
        try:
            if any(r.get("operation_id") == operation for r in _journal(journal_path)):
                return dict(result, state="EFFECT_UNKNOWN", code="CONTROL_RECONCILIATION_REQUIRED")
        except (OSError, ValueError, UnboundLocalError):
            pass
        return dict(result, code="CONTROL_VALIDATION_OR_OWNER_FAILURE")
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def reconcile(request, app, gateway, *, epoch, now=None, refresh_owner=None):
    """Observe/fence one original operation; never write its configuration patch."""
    now = time.time() if now is None else now
    original = request["original"]
    result = {"operation_id": request["operation_id"], "request_id": request["request_id"],
              "epoch": epoch, "origin_epoch": original["epoch"], "at": now,
              "state": "EFFECT_UNKNOWN", "code": "CONTROL_RECONCILIATION_REQUIRED"}
    if request["epoch"] != epoch:
        return dict(result, code="OBSERVED_EPOCH_CHANGED")
    fd = None
    try:
        owner, path = _owner(app, gateway)
        fd = acquire_writer(path, operation_id=original["operation_id"])
        journal_path = path.with_name(path.name + ".admin-receipts.json")
        rows = _journal(journal_path)
        prior = next((r for r in rows if r["operation_id"] == original["operation_id"]), None)
        intent_hash = _digest(_bytes(original))
        if prior is None:
            if not journal_path.is_file():
                return dict(result, code="RECEIPT_STORE_CONTINUITY_UNKNOWN")
            # No prepared write exists. Fence a late original delivery with a durable
            # terminal receipt under the same lock before releasing this operation.
            # A changed configuration cannot establish that history was intact.
            document, revision = gateway.read_document(path)
            if revision != original["expected_revision"]:
                return dict(result, code="MISSING_RECEIPT_CONFIGURATION_CHANGED")
            prior = {**result, "epoch": original["epoch"], "intent_hash": intent_hash,
                     "state": "NOT_APPLIED", "code": "NO_PREPARED_WRITE_FENCED",
                     "before_revision": revision, "after_revision": revision,
                     "effective_revision": owner.digest}
            rows = (rows + [prior])[-100:]
        elif prior.get("intent_hash") != intent_hash:
            return dict(result, code="OPERATION_ID_CONFLICT")
        elif prior["state"] in TERMINAL:
            return {**prior, **{k: result[k] for k in ("request_id", "epoch", "origin_epoch")}}
        else:
            document, revision = gateway.read_document(path)
            refresh = refresh_owner or (lambda: owner.refresh(app, gateway._routes_from_document, force=True))
            if revision == prior["after_revision"]:
                effective = refresh()
                if effective and owner.digest == revision and gateway.read_document(path)[1] == revision:
                    prior.update(state="APPLIED", code="RECONCILED_EFFECTIVE_REVISION", effective_revision=owner.digest, at=now)
                else:
                    prior.update(state="EFFECT_UNKNOWN", code="NATIVE_ADOPTION_NOT_CONFIRMED", at=now)
            elif revision == prior["before_revision"]:
                meta = path.stat()
                identity = [meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns, meta.st_ctime_ns]
                if identity == prior.get("before_file_identity"):
                    prior.update(state="NOT_APPLIED", code="INTERRUPTED_BEFORE_WRITE", at=now)
                else:
                    prior.update(state="EFFECT_UNKNOWN", code="PREIMAGE_WRITER_CONTINUITY_UNKNOWN", at=now)
            else:
                prior.update(state="EFFECT_UNKNOWN", code="CONFIGURATION_CHANGED_DURING_INTERRUPTION", at=now)
        atomic_private(journal_path, _bytes(rows))
        return {**prior, **{k: result[k] for k in ("request_id", "epoch", "origin_epoch")}}
    except (WriterBusy, PendingConfiguration, OSError, ValueError, TypeError, KeyError, AttributeError):
        return result
    finally:
        if fd is not None:
            os.close(fd)
