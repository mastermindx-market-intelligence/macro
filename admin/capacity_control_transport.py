"""One bounded settings RPC slot over the incumbent private SSH observation pipe.

No listener, credentials, worker daemon, admission owner or retry queue is added.
The admin's existing session/CSRF gates authorize a request. Only the installed
router control adapter can apply it. Uncertain effects fence subsequent writes.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

from . import capacity_router
from .capacity_control_owner import MAX_CONTROL_BYTES, TERMINAL, atomic_private, read_private, validate_intent

_ID = re.compile(r"^[a-f0-9]{32}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")


def paths(snapshot_path=None):
    snapshot = Path(snapshot_path or os.environ.get("CAPACITY_OBSERVATORY_PATH", str(capacity_router.DEFAULT_PATH)))
    return (snapshot.with_suffix(".control-request.json"), snapshot.with_suffix(".control-result.json"),
            snapshot.with_suffix(".control-api.lock"))


def _read(path):
    try:
        return read_private(path)
    except FileNotFoundError:
        return None


def clean_receipt(value):
    if not isinstance(value, dict) or not _ID.fullmatch(str(value.get("operation_id", ""))):
        raise ValueError("invalid control receipt")
    if value.get("state") not in TERMINAL | {"EFFECT_UNKNOWN", "PREPARED"}:
        raise ValueError("invalid control state")
    result = {"operation_id": value["operation_id"], "state": value["state"]}
    for key in ("before_revision", "after_revision", "effective_revision"):
        item = value.get(key)
        result[key] = item if isinstance(item, str) and _SHA.fullmatch(item) else None
    for key in ("epoch", "origin_epoch", "request_id"):
        item = value.get(key)
        result[key] = item if isinstance(item, str) and _ID.fullmatch(item) else None
    code = value.get("code", "")
    result["code"] = code if isinstance(code, str) and re.fullmatch(r"[A-Z_]{1,80}", code) else "CONTROL_RESULT"
    at = value.get("at")
    result["at"] = at if isinstance(at, (int, float)) and not isinstance(at, bool) and 0 <= at <= 10**11 else None
    result["retry_allowed"] = False
    return result



def _matching_receipt(pending, cached, projected):
    """Native terminal evidence outranks a stale cached uncertain transport reply."""
    candidates = [r for r in [cached, *projected] if isinstance(r, dict)
                  and r.get("operation_id") == pending["operation_id"]]
    terminal = [r for r in candidates if r.get("state") in TERMINAL]
    return max(terminal or candidates, key=lambda r: r.get("at") or 0, default=None)


def _request_identity(request):
    return request.get("request_id") or request["operation_id"]


def _response_matches(response, request):
    return (isinstance(response, dict) and response.get("operation_id") == request["operation_id"]
            and (response.get("request_id") or response["operation_id"]) == _request_identity(request)
            and response.get("epoch") == request["epoch"])

def settings(*, path=None, now=None):
    live = capacity_router.panel(15, path=path, now=now)
    controls = live.get("controls") or {}
    result = {"ok": live.get("ok", False), "writable": False, "routes": live.get("routes", []),
              "message": "The installed observer has not connected its native configuration owner.", **controls}
    result["epoch"] = live.get("epoch")
    result["source_at"] = live.get("generated_at")
    if live.get("state") != "live":
        result.update(writable=False, message="Telemetry is stale or disconnected. Router writes are disabled until live ownership is established.")
    request_path, result_path, _ = paths(path)
    try:
        pending, receipt = _read(request_path), _read(result_path)
        if pending:
            validate_intent(pending)
            matching = _matching_receipt(pending, receipt, controls.get("receipts", []))
            if matching:
                result["last_operation"] = clean_receipt(matching)
                if matching.get("state") not in TERMINAL:
                    result["writable"] = False
            else:
                result["last_operation"] = {"operation_id": pending["operation_id"], "state": "EFFECT_UNKNOWN", "retry_allowed": False}
                result["writable"] = False
    except (OSError, ValueError, TypeError):
        result.update(writable=False, message="Control transport reconciliation is required; no write has been retried.")
    return result


def submit(body, *, path=None, now=None, timeout=8):
    now = time.time() if now is None else now
    if isinstance(body, dict) and body.get("action") == "reconcile":
        return reconcile_pending(body, path=path, now=now, timeout=timeout)
    if not isinstance(body, dict) or set(body) != {"action", "expected_revision", "patch"}:
        return {"ok": False, "state": "NOT_APPLIED", "error": "Invalid settings request"}, 400
    live = settings(path=path, now=now)
    if not live.get("writable"):
        return {"ok": False, "state": "NOT_APPLIED", "error": live.get("message"), "last_operation": live.get("last_operation")}, 409 if live.get("last_operation") else 503
    intent = {**body, "operation_id": uuid.uuid4().hex, "epoch": live["epoch"], "expires_at": now + 20}
    try:
        validate_intent(intent)
        catalog = {r["id"]: r for r in live.get("routes", [])}
        for row in intent["patch"].get("routes", []):
            if row["id"] not in catalog:
                raise ValueError("route is not in the observed catalog")
            for key in ("model_priority", "model_weight"):
                if set(row.get(key, {})) - set(catalog[row["id"]].get("models", [])):
                    raise ValueError("model is not in the observed route")
        aliases = live.get("aliases") or {}
        for name, members in intent["patch"].get("aliases", {}).items():
            if name not in aliases or set(members) != set(aliases[name]):
                raise ValueError("routing class membership cannot be changed here")
    except (ValueError, TypeError):
        return {"ok": False, "state": "NOT_APPLIED", "error": "Unsupported setting, range or revision"}, 400
    request_path, result_path, lock_path = paths(path)
    fd = None
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("invalid control lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"ok": False, "state": "NOT_APPLIED", "error": "Another explicit settings operation is in progress"}, 409
        old, receipt = _read(request_path), _read(result_path)
        if old:
            validate_intent(old)
            matched = _matching_receipt(old, receipt, live.get("receipts", []))
            if not matched or matched.get("state") not in TERMINAL:
                return {"ok": False, "state": "EFFECT_UNKNOWN", "operation_id": old["operation_id"],
                        "retry_allowed": False, "error": "Reconcile the existing operation before another write"}, 409
        atomic_private(request_path, (json.dumps(intent, separators=(",", ":"), allow_nan=False)+"\n").encode())
        deadline = time.monotonic() + min(10, max(0, timeout))
        while time.monotonic() < deadline:
            response = _read(result_path)
            if _response_matches(response, intent):
                response = clean_receipt(response)
                response["ok"] = response["state"] in {"VALIDATED", "APPLIED"}
                return response, 200 if response["ok"] else 409
            time.sleep(.1)
        return {"ok": False, "state": "EFFECT_UNKNOWN", "operation_id": intent["operation_id"],
                "retry_allowed": False, "error": "The request was delivered to the private control slot; application is not yet confirmed. Refresh settings to reconcile, not retry."}, 202
    except (OSError, ValueError, TypeError):
        return {"ok": False, "state": "EFFECT_UNKNOWN" if request_path.is_file() else "NOT_APPLIED",
                "operation_id": intent["operation_id"], "retry_allowed": False, "error": "Control transport unavailable; inspect the operation receipt before retrying."}, 503
    finally:
        if fd is not None:
            os.close(fd)


def next_request(epoch, *, path=None):
    request_path, result_path, _ = paths(path)
    try:
        request = _read(request_path)
        if not request:
            return None
        validate_intent(request)
        if request["epoch"] != epoch:
            return None
        receipt = _read(result_path)
        if _response_matches(receipt, request):
            return None
        return request
    except (OSError, ValueError, TypeError):
        return None


def accept_result(value, *, path=None):
    request_path, result_path, _ = paths(path)
    receipt = clean_receipt(value)
    request = _read(request_path)
    if not request or not _response_matches(receipt, request):
        return False
    previous = _read(result_path)
    if (previous and previous.get("operation_id") == receipt["operation_id"]
            and previous.get("state") in TERMINAL and receipt["state"] not in TERMINAL):
        return False
    atomic_private(result_path, (json.dumps(receipt, separators=(",", ":"))+"\n").encode())
    return True


def reconcile_pending(body, *, path=None, now=None, timeout=8):
    """Explicit read/adopt reconciliation of the original operation, never apply."""
    now = time.time() if now is None else now
    if set(body) != {"action", "operation_id"} or not _ID.fullmatch(str(body.get("operation_id", ""))):
        return {"ok": False, "error": "Invalid reconciliation request", "state": "NOT_APPLIED"}, 400
    live = capacity_router.panel(15, path=path, now=now)
    if live.get("state") != "live" or not (live.get("controls") or {}).get("ok"):
        return {"ok": False, "error": "Live native ownership is required for reconciliation", "state": "EFFECT_UNKNOWN"}, 503
    request_path, result_path, lock_path = paths(path)
    fd = None
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"ok": False, "error": "The original operation is still being observed", "state": "EFFECT_UNKNOWN"}, 409
        pending = _read(request_path)
        if not pending or pending.get("operation_id") != body["operation_id"]:
            return {"ok": False, "error": "No matching pending operation", "state": "NOT_APPLIED"}, 409
        validate_intent(pending)
        matched = _matching_receipt(pending, _read(result_path), live["controls"].get("receipts", []))
        if matched and matched.get("state") in TERMINAL:
            result = clean_receipt(matched)
            return {**result, "ok": True, "reconciled": True}, 200
        original = pending["original"] if pending["action"] == "reconcile" else pending
        request = {"operation_id": original["operation_id"], "action": "reconcile", "epoch": live["epoch"],
                   "request_id": uuid.uuid4().hex, "original": original}
        validate_intent(request)
        atomic_private(request_path, (json.dumps(request, separators=(",", ":"))+"\n").encode())
        deadline = time.monotonic() + min(10, max(0, timeout))
        while time.monotonic() < deadline:
            response = _read(result_path)
            if _response_matches(response, request):
                result = clean_receipt(response)
                terminal = result["state"] in TERMINAL
                return {**result, "ok": terminal, "reconciled": terminal}, 200 if terminal else 409
            time.sleep(.1)
        return {"ok": False, "state": "EFFECT_UNKNOWN", "operation_id": original["operation_id"],
                "retry_allowed": False, "error": "Reconciliation pending; no configuration patch was replayed."}, 202
    except (OSError, ValueError, TypeError, KeyError):
        return {"ok": False, "state": "EFFECT_UNKNOWN", "operation_id": body["operation_id"],
                "retry_allowed": False, "error": "Original operation remains fenced."}, 503
    finally:
        if fd is not None:
            os.close(fd)
