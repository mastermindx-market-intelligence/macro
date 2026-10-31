"""One create-only private retained-reference install through provisioned SSH.

No provider request, credential transfer, public upload, GEX adaptation, registry,
retention policy or runtime activation. The principal binds the original artifact
and receiver first. An exclusive original receipt forbids replay after any loss.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import uuid

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

DESTINATION = Path("/var/lib/macro-api/options_plan/reference.json")
MAX_BYTES = 262144
MAX_HEADER = 32768


class InstallRefused(ValueError):
    pass


def _json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise InstallRefused("duplicate_field")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(InstallRefused("nonfinite")))


def validate_request(request):
    fields = {"schema", "operation_id", "original_root", "assigning_parent", "sha256", "byte_length",
              "original_observation_path", "provider_payload_sha256", "captured_at", "reference_as_of"}
    if (type(request) is not dict or set(request) != fields or request["schema"] != "options.plan_reference_install/v1"
            or len(json.dumps(request, allow_nan=False).encode()) > 16384):
        raise InstallRefused("request_invalid")
    for key in ("operation_id", "original_root", "assigning_parent"):
        if type(request[key]) is not str or str(uuid.UUID(request[key])) != request[key]:
            raise InstallRefused("identity_invalid")
    for key in ("sha256", "provider_payload_sha256"):
        if type(request[key]) is not str or re.fullmatch("[a-f0-9]{64}", request[key]) is None:
            raise InstallRefused("digest_invalid")
    if type(request["byte_length"]) is not int or not 0 < request["byte_length"] <= MAX_BYTES:
        raise InstallRefused("byte_bound_invalid")
    if (type(request["original_observation_path"]) is not str or not request["original_observation_path"].startswith("/")
            or len(request["original_observation_path"]) > 4096
            or any(ord(c) < 32 for c in request["original_observation_path"])
            or ".." in Path(request["original_observation_path"]).parts):
        raise InstallRefused("original_path_invalid")
    return request


def verify_observation(raw, request):
    validate_request(request)
    if type(raw) is not bytes or len(raw) != request["byte_length"] or sha256(raw).hexdigest() != request["sha256"]:
        raise InstallRefused("source_bytes_mismatch")
    observed = _json(raw)
    if (type(observed) is not dict or observed.get("schema") != "options_reference_capability_observation/v1"
            or observed.get("state") != "response_observed" or observed.get("origin") != "https://api.polygon.io"
            or (observed.get("path") != "/v3/reference/options/contracts"
                and not str(observed.get("path", "")).startswith("/v3/reference/options/contracts/O:"))
            or observed.get("capability", {}).get("http_status") != 200
            or observed.get("capability", {}).get("verdict") != "entitled"
            or observed.get("payload_sha256") != request["provider_payload_sha256"]
            or observed.get("completed_at") != request["captured_at"]
            or observed.get("params", {}).get("as_of") != request["reference_as_of"]):
        raise InstallRefused("original_source_binding_mismatch")
    from datetime import date
    from lib.options_source_receipts import instant
    if (instant(request["captured_at"]) > datetime.now(timezone.utc)
            or date.fromisoformat(request["reference_as_of"]).isoformat() != request["reference_as_of"]):
        raise InstallRefused("source_clock_invalid")
    return observed


def _walk(path):
    if not path.is_absolute() or ".." in path.parts:
        raise InstallRefused("path_invalid")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd); fd = next_fd
        return fd
    except Exception:
        os.close(fd); raise


def _source_bytes(path, request):
    directory = _walk(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size != request["byte_length"]):
                raise InstallRefused("source_file_unqualified")
            raw = stream.read(MAX_BYTES + 1)
        verify_observation(raw, request)
        return raw
    finally:
        os.close(directory)


def _response(request, status):
    return {"operation_id": request["operation_id"], "sha256": request["sha256"],
            "status": status, "retry_allowed": False, "destination": str(DESTINATION)}


def endpoint(header, body):
    if type(header) is not dict or set(header) != {"action", "request", "expected_uid"}:
        raise InstallRefused("header_invalid")
    request = validate_request(header["request"])
    if type(header["expected_uid"]) is not int or os.geteuid() != header["expected_uid"]:
        raise InstallRefused("receiver_identity_mismatch")
    action = header["action"]
    if action not in {"preflight", "arrive", "inspect"}:
        raise InstallRefused("action_invalid")
    raw = body.read(request["byte_length"] + 1) if action == "arrive" else None
    if raw is not None:
        verify_observation(raw, request)  # before even mkdir
    base = _walk(DESTINATION.parent.parent)
    directory = file_fd = None
    temporary = None
    temporary_inode = None
    try:
        info = os.fstat(base)
        if info.st_uid != header["expected_uid"] or stat.S_IMODE(info.st_mode) & 0o022:
            raise InstallRefused("state_namespace_unqualified")
        try:
            directory = os.open(DESTINATION.parent.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=base)
        except FileNotFoundError:
            if action == "preflight":
                return _response(request, "ready_create_private_leaf")
            if action == "inspect":
                return _response(request, "absent")
            os.mkdir(DESTINATION.parent.name, 0o700, dir_fd=base)
            os.fsync(base)
            directory = os.open(DESTINATION.parent.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=base)
        info = os.fstat(directory)
        if info.st_uid != header["expected_uid"] or stat.S_IMODE(info.st_mode) != 0o700:
            raise InstallRefused("private_leaf_unqualified")
        try:
            os.stat(DESTINATION.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            if action == "inspect": return _response(request, "absent")
        else:
            if action != "inspect": raise InstallRefused("target_exists")
            fd = os.open(DESTINATION.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != header["expected_uid"]
                        or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                    raise InstallRefused("installed_file_unqualified")
                verify_observation(stream.read(MAX_BYTES + 1), request)
            return _response(request, "present_exact")
        if action == "preflight": return _response(request, "ready")
        temporary = f".plan-reference-{request['operation_id']}.tmp"
        file_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        info = os.fstat(file_fd); temporary_inode = (info.st_dev, info.st_ino)
        pending = memoryview(raw)
        while pending:
            count = os.write(file_fd, pending)
            if count <= 0: raise InstallRefused("write_incomplete")
            pending = pending[count:]
        os.fsync(file_fd)
        info = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != temporary_inode or not stat.S_ISREG(info.st_mode) or info.st_size != len(raw):
            raise InstallRefused("staging_changed")
        os.link(temporary, DESTINATION.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        info = os.stat(DESTINATION.name, dir_fd=directory, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != temporary_inode or not stat.S_ISREG(info.st_mode) or info.st_size != len(raw):
            raise InstallRefused("installed_changed")
        os.fsync(directory)
        os.unlink(temporary, dir_fd=directory); temporary = None
        os.fsync(directory)
        current = _walk(DESTINATION.parent)
        try:
            before, after = os.fstat(directory), os.fstat(current)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise InstallRefused("destination_changed")
        finally:
            os.close(current)
        return _response(request, "installed")
    finally:
        if file_fd is not None: os.close(file_fd)
        if temporary is not None and directory is not None and temporary_inode is not None:
            try:
                info = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == temporary_inode:
                    os.unlink(temporary, dir_fd=directory)
            except OSError: pass
        if directory is not None: os.close(directory)
        os.close(base)


def ssh_transport(binding):
    # Reuse the incumbent bounded bidirectional transport, not the GEX contract.
    from scripts.deliver_options_scenario_source import _exchange, HOST, _path
    if type(binding) is not dict or set(binding) != {"host", "cwd", "python", "identity", "expected_uid"}:
        raise InstallRefused("binding_invalid")
    if type(binding["host"]) is not str or not HOST.fullmatch(binding["host"]):
        raise InstallRefused("host_invalid")
    for key in ("cwd", "python", "identity"): _path(binding[key])
    args = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "IdentitiesOnly=yes",
            "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2", "-i", binding["identity"],
            binding["host"], f"cd {shlex.quote(binding['cwd'])} && exec {shlex.quote(binding['python'])} -m scripts.install_options_plan_reference endpoint"]
    def invoke(action, request, raw=b""):
        packet = json.dumps(dict(action=action, request=request, expected_uid=binding["expected_uid"])).encode() + b"\n" + raw
        return _json(_exchange(args, packet, MAX_HEADER))
    return invoke


def _save_receipt(path, record, *, create=False):
    raw = json.dumps(record, sort_keys=True, allow_nan=False).encode()
    parent = _walk(path.parent)
    temporary = path.name if create else f".{path.name}.{uuid.uuid4().hex}.tmp"
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        pending = memoryview(raw)
        while pending:
            count = os.write(fd, pending)
            if count <= 0: raise InstallRefused("receipt_incomplete")
            pending = pending[count:]
        os.fsync(fd)
        if not create: os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def deliver(request, source_path, receipt_path, transport):
    """Exactly one original transport attempt; an existing receipt is inspect-only."""
    validate_request(request)
    raw = _source_bytes(source_path, request)
    record = dict(request=request, status="PREPARED", retry_allowed=False,
                  started_at=datetime.now(timezone.utc).isoformat())
    _save_receipt(receipt_path, record, create=True)
    try:
        preflight = transport("preflight", request)
        if preflight not in (_response(request, "ready"), _response(request, "ready_create_private_leaf")):
            raise InstallRefused("preflight_unconfirmed")
        record["status"] = "TRANSPORT_STARTED"
        _save_receipt(receipt_path, record)
        returned = transport("arrive", request, raw)
        if returned != _response(request, "installed"):
            raise InstallRefused("arrival_unconfirmed")
        record["status"] = "INSTALLED"
        _save_receipt(receipt_path, record)
        return returned
    except Exception:
        record["status"] = "EFFECT_UNKNOWN" if record["status"] in {"TRANSPORT_STARTED", "INSTALLED"} else "PREFLIGHT_FAILED"
        _save_receipt(receipt_path, record)
        raise InstallRefused(record["status"]) from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["endpoint", "deliver", "inspect"])
    parser.add_argument("--request"); parser.add_argument("--source"); parser.add_argument("--receipt"); parser.add_argument("--binding")
    args = parser.parse_args()
    if args.action == "endpoint":
        header = sys.stdin.buffer.readline(MAX_HEADER + 1)
        if len(header) > MAX_HEADER: raise InstallRefused("header_oversize")
        print(json.dumps(endpoint(_json(header), sys.stdin.buffer)))
        return
    request = _json(Path(args.request).read_bytes()); validate_request(request)
    transport = ssh_transport(_json(Path(args.binding).read_bytes()))
    if args.action == "inspect":
        print(json.dumps(transport("inspect", request))); return
    print(json.dumps(deliver(request, Path(args.source), Path(args.receipt), transport)))


if __name__ == "__main__": main()
