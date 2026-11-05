#!/usr/bin/env python3
"""Native API driver used only by the flock-owned Macro updater.

The route planner and publication journal contain the independently testable
logic. This driver binds them to the fixed installed Caddy and source paths.
It never reloads/restarts Caddy or substitutes the source-only adapted config
for the complete active configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import tempfile

APP = Path("/opt/macro")
INSTALLED = Path("/etc/caddy/Caddyfile")
AUTOSAVE = Path("/var/lib/caddy/.config/caddy/autosave.json")
STATE = Path("/var/lib/macro-caddy-publication")
MAX_BYTES = 16 * 1024 * 1024


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def read_regular(path: Path, *, root_owned: bool = True) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size > MAX_BYTES or (root_owned and info.st_uid != 0)
                or info.st_mode & 0o022):
            raise ValueError("unsafe publication input")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
        if len(raw) > MAX_BYTES or (info.st_dev, info.st_ino, info.st_size,
                info.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                      after.st_mtime_ns):
            raise ValueError("publication input changed")
        return raw
    finally:
        os.close(fd)


def decode(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate native JSON field")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError("nonfinite native JSON")))
    if type(value) is not dict:
        raise ValueError("native config must be an object")
    canonical(value)
    return value


class NativeAPI:
    def _request(self, method, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", 2019, timeout=30)
        try:
            connection.request(method, "/config/", body, headers or {})
            response = connection.getresponse()
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("native API response too large")
            pairs = response.getheaders()
            for key in ("etag", "content-length"):
                if sum(name.lower() == key for name, _ in pairs) > 1:
                    raise ValueError("ambiguous native API headers")
            return response.status, dict(pairs), raw
        finally:
            connection.close()

    def read(self):
        status, headers, raw = self._request("GET")
        if status != 200:
            raise ValueError("native API read failed")
        etag = next((v for k, v in headers.items() if k.lower() == "etag"), "")
        if not re.fullmatch(r'"[^"\r\n]{1,256}"', etag):
            raise ValueError("native API ETag unavailable")
        return decode(raw), etag

    def write(self, candidate, etag):
        status, _, _ = self._request("POST", canonical(candidate), {
            "Content-Type": "application/json", "If-Match": etag})
        return status


def run(*args, input=None):
    return subprocess.run(args, input=input, capture_output=True, check=True,
                          timeout=45).stdout


def require_autosave_mode():
    for property_name, verb in (("ExecStart", "run"), ("ExecReload", "reload")):
        effective = run("/usr/bin/systemctl", "show", "caddy", "--value",
                        "-p", property_name).decode()
        # Refuse combined/unknown service inputs rather than guessing ownership.
        if (f"/usr/bin/caddy {verb} " not in effective
                or f"--config {AUTOSAVE}" not in effective
                or "Caddyfile" in effective):
            raise ValueError("effective Caddy service is not the qualified autosave mode")


def adapt(raw: bytes) -> dict:
    # Existing imports reference snippets declared in these captured bytes.
    # File/glob imports or arguments would add uncaptured source dependencies.
    snippets = re.findall(rb"(?m)^\s*\(([A-Za-z0-9_-]+)\)\s*\{", raw)
    imports = re.findall(rb"(?m)^\s*import[ \t]+([^\r\n#]+)", raw)
    if len(set(snippets)) != len(snippets) or any(
            item.strip() not in snippets for item in imports):
        raise ValueError("external Caddyfile imports require separate qualification")
    native = decode(run("/usr/bin/caddy", "adapt", "--adapter", "caddyfile",
                        "--config", "/dev/stdin", input=raw))
    # Caddy 2.11.4 automatically hides its input filename in file_server.
    # Both captured revisions represent this same installed logical filename.
    # Translate that single adapter-added entry, never active configuration or
    # user-authored hide entries. Otherwise stdin becomes a false source delta.
    def logical_filename(value):
        if isinstance(value, dict):
            if value.get("handler") == "file_server":
                hidden = value.get("hide")
                if not isinstance(hidden, list) or not hidden or hidden[0] != "/dev/stdin":
                    raise ValueError("unsupported adapter-generated hide topology")
                hidden[0] = str(INSTALLED)
            for child in value.values():
                logical_filename(child)
        elif isinstance(value, list):
            for child in value:
                logical_filename(child)
    logical_filename(native)
    return native


def validate(candidate: dict):
    with tempfile.TemporaryDirectory(prefix="validate-", dir=STATE) as directory:
        path = Path(directory) / "candidate.json"
        raw = canonical(candidate)
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        run("/usr/bin/caddy", "validate", "--config", str(path))
        if read_regular(path) != raw:
            raise ValueError("validated native bytes changed")


def install_source(before: bytes, after: bytes):
    if read_regular(INSTALLED) == after:
        return  # Same captured pending candidate, not a newer moving source.
    if read_regular(INSTALLED) != before:
        raise ValueError("installed source baseline changed")
    fd, name = tempfile.mkstemp(prefix=".macro-caddy-", dir=INSTALLED.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        if read_regular(INSTALLED) != before:
            raise ValueError("installed source baseline changed before replace")
        os.replace(name, INSTALLED)
        directory = os.open(INSTALLED.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def previous_source(revision: str | None, installed: bytes) -> bytes:
    if revision is None:
        return installed
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("exact protected prior revision required")
    run("/usr/bin/git", "-C", str(APP), "merge-base", "--is-ancestor",
        revision, "origin/main")
    raw = run("/usr/bin/git", "-C", str(APP), "show",
              f"{revision}:app/deploy/Caddyfile")
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("prior protected source unavailable")
    return raw


def read_autosave() -> dict:
    if AUTOSAVE.lstat().st_uid != pwd.getpwnam("caddy").pw_uid:
        raise ValueError("autosave owner differs from the Caddy service")
    return decode(read_regular(AUTOSAVE, root_owned=False))


def main():
    from macro_caddy_publication import publish, journal_status

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-baseline", help="attended prior protected source revision")
    parser.add_argument("--pending-check", action="store_true",
                        help="read-only updater gate: zero for pending/invalid journal, one for clean")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError("root-owned updater required")
    if args.pending_check:
        try:
            status = journal_status(STATE)
        except Exception:
            status = {"ok": False}
        raise SystemExit(0 if not status.get("ok") or status.get("pending_op_ids") else 1)
    # The updater holds its normal FD9 flock. Lock ownership is inherited, not
    # recreated; direct invocation cannot acquire delegation by naming a PID.
    lock = os.fstat(9)
    actual = os.stat("/var/lock/macro-update.lock", follow_symlinks=False)
    if (lock.st_dev, lock.st_ino) != (actual.st_dev, actual.st_ino):
        raise ValueError("incumbent updater lock identity unavailable")
    if "FLOCK  ADVISORY  WRITE" not in Path("/proc/self/fdinfo/9").read_text():
        raise ValueError("incumbent updater flock is not held")
    require_autosave_mode()
    STATE.mkdir(mode=0o700, exist_ok=True)
    info = STATE.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError("unsafe publication journal directory")
    status = journal_status(STATE)
    if not status.get("ok"):
        raise ValueError("publication journal custody is unresolved")
    installed = read_regular(INSTALLED)
    api = NativeAPI()
    active, _ = api.read()
    if status.get("pending_op_ids"):
        # The transaction core ignores these new requested bytes when an
        # original intent is pending. It may only read back and reconcile that
        # intent's captured candidate/source. Never plan or post a moving C.
        receipt = publish(state_dir=STATE, api=api, expected_preimage=active,
                          candidate=active, source_before=installed,
                          source_after=installed, read_autosave=read_autosave,
                          install_source=install_source)
        require_completed(receipt)
        print(json.dumps({"result": "pending_reconciled", "op_id": receipt["op_id"],
                          "source_sha256": hashlib.sha256(read_regular(INSTALLED)).hexdigest()}))
        return receipt
    from macro_caddy_overlay import plan_routes
    source = read_regular(APP / "app/deploy/Caddyfile")
    prior = previous_source(args.source_baseline, installed)
    candidate = plan_routes(adapt(prior), adapt(source), active)
    if canonical(candidate) == canonical(active) and installed == source:
        if canonical(read_autosave()) != canonical(candidate):
            raise ValueError("current source lacks matching autosave")
        result = {"result": "already_current", "source_sha256": hashlib.sha256(source).hexdigest(),
                  "native_sha256": hashlib.sha256(canonical(candidate)).hexdigest()}
        print(json.dumps(result))
        return result
    validate(candidate)
    receipt = publish(state_dir=STATE, api=api, expected_preimage=active,
                      candidate=candidate, source_before=installed,
                      source_after=source,
                      read_autosave=read_autosave,
                      install_source=install_source)
    require_completed(receipt)
    # Configuration itself is private. Only bounded digests leave this driver.
    result = {"result": receipt["status"], "op_id": receipt["op_id"],
              "source_sha256": hashlib.sha256(read_regular(INSTALLED)).hexdigest()}
    if receipt["status"] != "reconciled_prior":
        result["native_sha256"] = hashlib.sha256(canonical(candidate)).hexdigest()
    print(json.dumps(result))
    return receipt


def require_completed(receipt):
    if (receipt.get("status") not in {"published", "reconciled", "reconciled_prior", "already_published"}
            or not receipt.get("published") or not receipt.get("installed_source")
            or not receipt.get("receipt_written") or receipt.get("pending")):
        codes = [error.get("code", "unknown") for error in receipt.get("errors", [])]
        raise RuntimeError("Caddy publication not accepted: " + ",".join(codes))


if __name__ == "__main__":
    main()
