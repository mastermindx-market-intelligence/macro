"""One intentional exact GEX delivery over already-provisioned SSH access.

No scheduler, credential provisioning, directory creation, retention or Save.
The operator supplies the verified source/receiver bindings and original intent.
An exclusive local receipt prevents replay; inspect is read-only reconciliation.
"""
from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import selectors
import time
import stat
import subprocess
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import options_hub_retention as retention
from engine import options_scenario_source_arrival as arrival
from engine.intelligence_workspace import scenario_source_resolution as source

MAX_HEADER = 32768
HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{0,252}\Z")


class DeliveryRefused(ValueError):
    pass


def _json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise DeliveryRefused("duplicate_field")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(DeliveryRefused("nonfinite")))


def descriptor(value):
    if type(value) is not dict or set(value) != {f.name for f in fields(source.ScenarioSourceDescriptor)}:
        raise DeliveryRefused("descriptor_invalid")
    value = dict(value)
    if value["moves"] is not None or value["grant_id"] is not None:
        raise DeliveryRefused("owner_gex_only_required")
    if type(value["gex"]) is not dict or set(value["gex"]) != {f.name for f in fields(retention.SnapshotReference)}:
        raise DeliveryRefused("reference_invalid")
    value["gex"] = retention.SnapshotReference(**value["gex"])
    result = source.ScenarioSourceDescriptor(**value)
    source._validate_descriptor(result)
    return result


def validate_request(request):
    if type(request) is not dict or set(request) != {"operation_id", "descriptor"}:
        raise DeliveryRefused("request_invalid")
    if type(request["operation_id"]) is not str or not source._UUID.fullmatch(request["operation_id"]):
        raise DeliveryRefused("operation_invalid")
    return descriptor(request["descriptor"])


def _path(value):
    if type(value) is not str or not value.startswith("/") or ".." in Path(value).parts or any(ord(c) < 32 for c in value):
        raise DeliveryRefused("path_invalid")
    return Path(value)


def _verify(desc, raw):
    payload = retention.verify_snapshot(desc.gex, raw, today=datetime.now(timezone.utc).date())
    projection = payload.get("exposure_projection")
    clocks = projection.get("clocks") if type(projection) is dict else None
    clock = clocks.get("option_observed_at") if type(clocks) is dict else None
    if clock != desc.source_as_of:
        raise DeliveryRefused("source_clock_mismatch")


def _private_directory(path, expected_uid):
    if type(expected_uid) is not int or expected_uid < 0 or os.geteuid() != expected_uid:
        raise DeliveryRefused("receiving_account_mismatch")
    fd = arrival._existing_gex_directory(path)
    try:
        # Root and leaf directory must both be private to the receiving account.
        root_fd = os.open("..", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            for handle in (root_fd, fd):
                info = os.fstat(handle)
                if info.st_uid != expected_uid or stat.S_IMODE(info.st_mode) & 0o077:
                    raise DeliveryRefused("receiving_directory_not_private")
        finally:
            os.close(root_fd)
        return fd
    except Exception:
        os.close(fd)
        raise


def _read(desc, fd):
    leaf = os.open(f"{desc.root}.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    with os.fdopen(leaf, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != desc.gex.byte_length:
            raise DeliveryRefused("source_changed")
        raw = stream.read(desc.gex.byte_length + 1)
    _verify(desc, raw)
    return raw


def receipt(request, status, **extra):
    return {"operation_id": request["operation_id"],
            "sha256": request["descriptor"]["gex"]["sha256"],
            "status": status, "retry_allowed": False, **extra}


def endpoint(header, body):
    """Run only under the selected authenticated SSH account; never HTTP-mounted."""
    if type(header) is not dict or set(header) != {"action", "request", "directory", "expected_uid"}:
        raise DeliveryRefused("header_invalid")
    request = header["request"]
    desc = validate_request(request)
    path = _path(header["directory"])
    action = header["action"]
    if action == "export":
        if header["expected_uid"] is not None:
            raise DeliveryRefused("source_binding_invalid")
        fd = arrival._existing_gex_directory(path)
        try:
            return _read(desc, fd)
        finally:
            os.close(fd)
    if action not in {"preflight", "arrive", "inspect"}:
        raise DeliveryRefused("action_invalid")
    fd = _private_directory(path, header["expected_uid"])
    try:
        if action == "inspect":
            _read(desc, fd)
            return receipt(request, "present_exact", save_performed=False)
        try:
            os.stat(f"{desc.root}.json", dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise DeliveryRefused("target_exists")
        if action == "preflight":
            return receipt(request, "ready")
        raw = body.read(desc.gex.byte_length + 1)
        _verify(desc, raw)
        # Keep the actual account/privacy-qualified inode through the write.
        arrival.arrive_gex_source(desc, raw, producer_out_dir=path,
                                  today=datetime.now(timezone.utc).date(), directory_fd=fd)
        current = _private_directory(path, header["expected_uid"])
        try:
            before, after = os.fstat(fd), os.fstat(current)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise DeliveryRefused("destination_changed_after_arrival")
        finally:
            os.close(current)
        return receipt(request, "arrived", save_performed=False)
    finally:
        os.close(fd)


def _exchange(args, packet, limit, *, timeout=60):
    """Bound both pipes while preserving any interrupted remote effect as unknown."""
    child = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
    output = bytearray()
    pending = memoryview(packet)
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as poll:
            for pipe in (child.stdin, child.stdout):
                os.set_blocking(pipe.fileno(), False)
            if pending:
                poll.register(child.stdin, selectors.EVENT_WRITE)
            else:
                child.stdin.close()
            poll.register(child.stdout, selectors.EVENT_READ)
            while poll.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DeliveryRefused("remote_result_unconfirmed")
                for key, _ in poll.select(remaining):
                    pipe = key.fileobj
                    if pipe is child.stdin:
                        written = os.write(pipe.fileno(), pending[:16384])
                        pending = pending[written:]
                        if not pending:
                            poll.unregister(pipe); pipe.close()
                    else:
                        chunk = os.read(pipe.fileno(), min(65536, limit + 1 - len(output)))
                        if not chunk:
                            poll.unregister(pipe); pipe.close()
                        else:
                            output.extend(chunk)
                            if len(output) > limit:
                                raise DeliveryRefused("remote_result_unconfirmed")
        if child.wait(timeout=max(0.001, deadline - time.monotonic())) != 0:
            raise DeliveryRefused("remote_result_unconfirmed")
        return bytes(output)
    except Exception:
        # Stop only this invocation's local transport process. A remote write
        # may already have occurred; deliver records UNKNOWN and never retries.
        if child.poll() is None:
            child.kill()
        child.wait()
        raise DeliveryRefused("remote_result_unconfirmed") from None
    finally:
        for pipe in (child.stdin, child.stdout):
            pipe.close()


def ssh_transport(binding):
    if type(binding) is not dict or set(binding) != {"host", "cwd", "python", "directory", "identity", "expected_uid"}:
        raise DeliveryRefused("host_binding_invalid")
    if type(binding["host"]) is not str or not HOST.fullmatch(binding["host"]):
        raise DeliveryRefused("host_invalid")
    for key in ("cwd", "python", "directory"):
        _path(binding[key])
    args = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8",
            "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2"]
    if binding["identity"] is not None:
        args += ["-i", str(_path(binding["identity"]))]
    command = f"cd {shlex.quote(binding['cwd'])} && exec {shlex.quote(binding['python'])} -m scripts.deliver_options_scenario_source endpoint"
    args += [binding["host"], command]
    def invoke(action, request, raw=b""):
        header = {"action": action, "request": request,
                  "directory": binding["directory"], "expected_uid": binding["expected_uid"]}
        encoded = json.dumps(header, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        if len(encoded) > MAX_HEADER:
            raise DeliveryRefused("header_bound")
        limit = request["descriptor"]["gex"]["byte_length"] if action == "export" else MAX_HEADER
        answer = _exchange(args, encoded + raw, limit)
        return answer if action == "export" else _json(answer)
    return invoke


def deliver(request, source_call, target_call, *, record):
    desc = validate_request(request)
    dispatched = False
    try:
        if target_call("preflight", request) != receipt(request, "ready"):
            raise DeliveryRefused("destination_unconfirmed")
        raw = source_call("export", request)
        _verify(desc, raw)
        # Durable original-intent record MUST succeed before the write dispatch.
        record(receipt(request, "effect_unknown"))
        dispatched = True
        answer = target_call("arrive", request, raw)
        if answer != receipt(request, "arrived", save_performed=False):
            raise DeliveryRefused("arrival_unconfirmed")
        result = answer
    except Exception:
        result = receipt(request, "effect_unknown" if dispatched else "not_delivered")
    record(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("endpoint", "deliver", "inspect"))
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.mode == "endpoint":
        try:
            line = sys.stdin.buffer.readline(MAX_HEADER + 1)
            if len(line) > MAX_HEADER or not line.endswith(b"\n"):
                raise DeliveryRefused("header_bound")
            result = endpoint(_json(line), sys.stdin.buffer)
            sys.stdout.buffer.write(result if type(result) is bytes else json.dumps(result).encode())
            return 0
        except Exception:
            # After an endpoint interruption the caller conservatively preserves uncertainty.
            sys.stderr.write("source_endpoint_unconfirmed\n")
            return 2
    if args.intent is None or args.receipt is None:
        parser.error("--intent and --receipt are required")
    with args.intent.open("rb") as stream:
        raw = stream.read(MAX_HEADER + 1)
    if len(raw) > MAX_HEADER:
        raise DeliveryRefused("intent_bound")
    intent = _json(raw)
    if type(intent) is not dict or set(intent) != {"request", "source", "target"}:
        raise DeliveryRefused("intent_invalid")
    validate_request(intent["request"])
    origin, target = ssh_transport(intent["source"]), ssh_transport(intent["target"])
    if args.mode == "inspect":
        handle = os.open(args.receipt, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(handle, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise DeliveryRefused("original_receipt_not_private")
            line = stream.readline(MAX_HEADER + 32)
            if not line.endswith(b"\n"):
                raise DeliveryRefused("original_receipt_invalid")
            original = _json(line)
        if original != {"intent": intent}:
            raise DeliveryRefused("original_intent_mismatch")
        result = target("inspect", intent["request"])
        if result != receipt(intent["request"], "present_exact", save_performed=False):
            raise DeliveryRefused("inspection_unconfirmed")
        print(json.dumps(result))
        return 0
    if not args.execute:
        print(json.dumps(receipt(intent["request"], "not_dispatched")))
        return 0
    # Persist both the original intent and its newly created directory entry
    # before any remote action. Keep this receipt even if durability fails.
    parent = os.open(args.receipt.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(args.receipt.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, "w") as journal:
            def record(value):
                journal.write(json.dumps(value, allow_nan=False) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
            record({"intent": intent})
            os.fsync(parent)
            result = deliver(intent["request"], origin, target, record=record)
    finally:
        os.close(parent)
    print(json.dumps(result))
    return 0 if result["status"] == "arrived" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        sys.stderr.write("source_delivery_unconfirmed; preserve original receipt, do not replay\n")
        raise SystemExit(2)
