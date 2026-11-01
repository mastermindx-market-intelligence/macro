#!/usr/bin/env python3
"""Source-only prepared CLI29 test; default does not execute Docker.

Future explicit root commission only: actual client, synthetic helpers, private
fake Unix API. This never connects to a real daemon or registry. No saved config
is read. A PASS proves only this narrow client behavior, not containment.
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socketserver
import stat
import subprocess
import tempfile
import threading
import time
import urllib.parse

DOCKER = "/usr/bin/docker"
DIGEST = "bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed"
IMAGE = "docker.io/library/python@sha256:" + DIGEST
ANON = b'{"auths":{"https://index.docker.io/v1/":{}}}\n'
WALL = 60
RAW_CAP = 16384


def expected_client_version(raw):
    """Parse only the pinned client version and a bounded package build token."""
    if type(raw) is not bytes or len(raw) > 256:
        raise RuntimeError("actual_client_not_29_1_3")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        raise RuntimeError("actual_client_not_29_1_3") from None
    if not re.fullmatch(r"Docker version 29\.1\.3, build [A-Za-z0-9][A-Za-z0-9_.~-]{0,127}\n?", text):
        raise RuntimeError("actual_client_not_29_1_3")
    return text.removesuffix("\n")


def private_file(path, data, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(data)
            out.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def client_argv(config, endpoint, *tail):
    return [DOCKER, "--host", endpoint, "--config", str(config), *tail]


def client_env(helpers, home, log):
    return {"PATH": str(helpers), "HOME": str(home), "LANG": "C", "LC_ALL": "C",
            "RF_FAKE_HELPER_LOG": str(log)}


def collect(argv, env, deadline, remaining_cap, trace):
    """Incremental own-client collection; no shell or inherited env."""
    limit = min(4096, remaining_cap)
    if limit <= 0 or time.monotonic() >= deadline - 2:
        raise RuntimeError("test_envelope_exhausted")
    proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True, close_fds=True)
    raw = bytearray()
    stop_at = min(deadline - 2, time.monotonic() + 10)
    failed = False
    try:
        with selectors.DefaultSelector() as poll:
            poll.register(proc.stdout, selectors.EVENT_READ)
            while poll.get_map():
                if time.monotonic() >= stop_at:
                    raise RuntimeError("client_timeout")
                for key, _ in poll.select(min(.1, stop_at - time.monotonic())):
                    chunk = os.read(key.fd, min(4096, limit - len(raw)))
                    if not chunk:
                        poll.unregister(key.fileobj)
                    else:
                        raw.extend(chunk)
                        if len(raw) >= limit:
                            raise RuntimeError("client_output_cap")
            proc.wait(timeout=max(.01, stop_at - time.monotonic()))
        return proc.returncode, bytes(raw)
    except BaseException:
        failed = True
        raise
    finally:
        if failed or proc.poll() is None:
            # Only this new-session child's known process group is addressed.
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=.25)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.poll() is None:
                raise RuntimeError("own_client_cleanup_unconfirmed")
        trace.append({"argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
                      "rc": proc.poll(), "raw_bytes": len(raw),
                      "raw_sha256": hashlib.sha256(raw).hexdigest(), "failed": failed})
        proc.stdout.close()


class FakeAPI(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(1)

    def log_message(self, *_):
        pass

    def serve(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = re.sub(r"^/v[0-9]+\.[0-9]+", "", parsed.path)
        row = {"method": self.command, "path": path}
        ok = len(self.server.rows) < 8 and len(self.path) <= 2048
        body = b"OK"
        if path == "/_ping" and self.command in {"HEAD", "GET"}:
            pass
        elif path == "/version" and self.command == "GET":
            body = b'{"Version":"29.1.3","ApiVersion":"1.52","MinAPIVersion":"1.44","Os":"linux","Arch":"amd64"}'
        elif path == "/images/create" and self.command == "POST":
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            repo = query.get("fromImage", [])
            tag = query.get("tag", [])
            ok = ok and repo in [["python"], ["docker.io/library/python"], ["library/python"]]
            ok = ok and tag == ["sha256:" + DIGEST] and set(query) <= {"fromImage", "tag"}
            encoded = self.headers.get("X-Registry-Auth", "")
            try:
                if not encoded or len(encoded) > 2048:
                    raise ValueError()
                auth = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
                empty = isinstance(auth, dict) and set(auth) <= {
                    "username", "password", "auth", "serveraddress", "identitytoken", "registrytoken"}
                empty = empty and all(not auth.get(k) for k in (
                    "username", "password", "auth", "identitytoken", "registrytoken"))
                row["anonymous_auth"] = bool(empty)
                ok = ok and empty
            except (ValueError, TypeError, UnicodeError):
                ok = False
            body = b'{"status":"synthetic-only: no image acquired"}\n'
        else:
            ok = False
        row["accepted"] = bool(ok)
        self.server.rows.append(row)
        self.send_response(200 if ok else 400)
        self.send_header("Api-Version", "1.52")
        self.send_header("Docker-Experimental", "false")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True

    do_HEAD = do_GET = do_POST = serve


def execute(operation_dir, *, absolute_deadline=None, raw_cap=RAW_CAP):
    base = Path(operation_dir)
    meta = base.lstat()
    if (not stat.S_ISDIR(meta.st_mode) or stat.S_ISLNK(meta.st_mode)
            or meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o700):
        raise RuntimeError("operation_dir_not_owned_private")
    started = time.monotonic()
    deadline = min(started + WALL, absolute_deadline) if absolute_deadline is not None else started + WALL
    if (type(raw_cap) is not int or not 0 < raw_cap <= RAW_CAP or deadline <= started):
        raise RuntimeError("invalid_original_envelope")
    fixture = Path(tempfile.mkdtemp(prefix="cli-", dir=base))
    server = thread = None
    result = {"schema": "rf.cli29_anonymous_config.v1", "status": "FAIL",
              "physical_containment": False, "real_daemon_or_registry_used": False}
    calls, raw_total, permission_frozen = [], 0, False
    try:
        sock = fixture / "api.sock"
        if len(os.fsencode(sock)) >= 100:
            raise RuntimeError("fake_socket_path_too_long")
        helpers, home = fixture / "helpers", fixture / "empty-home"
        helpers.mkdir(mode=0o700)
        home.mkdir(mode=0o700)
        log = fixture / "helper.log"
        # Fixed /bin/sh and builtins only. No PATH executable or real store used.
        script = ("#!/bin/sh\n"
                  'printf "%s\\n" "$1" >> "$RF_FAKE_HELPER_LOG"\n'
                  'IFS= read -r registry || :\n'
                  'case "$1" in get) printf \'{"ServerURL":"https://index.docker.io/v1/","Username":"","Secret":""}\\n\';; esac\n')
        for name in ("docker-credential-pass", "docker-credential-secretservice"):
            private_file(helpers / name, script.encode(), 0o700)
        private_file(helpers / "pass", b"#!/bin/sh\nexit 0\n", 0o700)
        env = client_env(helpers, home, log)
        server = socketserver.UnixStreamServer(str(sock), FakeAPI)
        os.chmod(sock, 0o600)
        server.rows = []
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .05})
        thread.start()
        endpoint = "unix://" + str(sock)
        def run(config, *tail):
            nonlocal raw_total
            argv = client_argv(config, endpoint, *tail)
            try:
                rc, raw = collect(argv, env, deadline, raw_cap - raw_total, calls)
            finally:
                raw_total = sum(row["raw_bytes"] for row in calls)
            if rc != 0:
                raise RuntimeError("fake_client_call_failed")
            return raw
        control, anon = fixture / "control", fixture / "anonymous"
        for directory, content in ((control, b"{}\n"), (anon, ANON)):
            directory.mkdir(mode=0o700)
            private_file(directory / "config.json", content)
        version = expected_client_version(run(anon, "--version"))
        run(control, "image", "pull", IMAGE)
        observed = log.read_bytes() if log.exists() else b""
        if observed != b"get\n":
            raise RuntimeError("positive_helper_control_unproven")
        before = len(server.rows)
        run(anon, "image", "pull", IMAGE)
        if log.read_bytes() != observed:
            raise RuntimeError("anonymous_config_called_helper")
        pulls = [r for r in server.rows if r["path"] == "/images/create"]
        new_pulls = [r for r in server.rows[before:] if r["path"] == "/images/create"]
        if len(pulls) != 2 or len(new_pulls) != 1 or not all(r["accepted"] for r in server.rows):
            raise RuntimeError("fake_api_endpoint_auth_proof_failed")
        result.update(status="PASS", client_version=version, docker_binary=DOCKER,
                      owned_fixture_component=fixture.name, fake_socket_component="api.sock",
                      path_directory_component="helpers", environment_keys=sorted(env), config_sha256=hashlib.sha256(ANON).hexdigest(),
                      path_only_owned_helpers=True, discoverable_helpers=["pass", "secretservice"],
                      positive_control_helper_get_count=1, anonymous_helper_get_count=0,
                      fake_api_requests=server.rows, exact_fake_unix_endpoint_sha256=hashlib.sha256(endpoint.encode()).hexdigest(),
                      commands=calls, raw_output_bytes=raw_total)
    except Exception as exc:
        permission_frozen = isinstance(exc, PermissionError)
        result.update(permission_frozen=permission_frozen, problem=type(exc).__name__, category=str(exc) if type(exc) is RuntimeError else "fixture_error",
                      commands=calls, raw_output_bytes=raw_total)
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(2)
            if thread.is_alive():
                result.update(status="FAIL", problem="fake_server_cleanup_unconfirmed")
        if permission_frozen:
            result.update(owned_fixture_removed=False, cleanup_obligation=True)
        else:
            try:
                shutil.rmtree(fixture)
                result["owned_fixture_removed"] = not fixture.exists()
            except Exception as exc:
                result.update(status="FAIL", problem="fixture_cleanup_unconfirmed",
                              owned_fixture_removed=False, cleanup_obligation=True,
                              permission_frozen=isinstance(exc, PermissionError))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    if time.monotonic() > deadline:
        result.update(status="FAIL", problem="whole_test_deadline")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--operation-dir")
    args = p.parse_args()
    if not args.execute:
        print(json.dumps({"status": "SOURCE_PLAN_ONLY", "docker_executed": False,
                          "wall_seconds": WALL, "raw_output_cap": RAW_CAP}))
        return 0
    if not args.operation_dir:
        p.error("--execute requires the separately admitted --operation-dir")
    result = execute(args.operation_dir)
    receipt = Path(args.operation_dir) / "cli29_anonymous_config_receipt.json"
    private_file(receipt, (json.dumps(result, sort_keys=True) + "\n").encode())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
