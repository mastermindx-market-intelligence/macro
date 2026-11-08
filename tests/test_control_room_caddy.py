"""CCR-R0 Task 7: fail-closed Caddy boundary for the remote Control Room."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CADDY = ROOT / "app" / "deploy" / "Caddyfile"
CADDY_BIN = os.environ.get("CADDY_BIN", "caddy")


def _site_block(text: str, host: str) -> str:
    """Return one literal host block using the Caddyfile's balanced braces."""
    match = re.search(rf"(?m)^{re.escape(host)}\s*\{{", text)
    assert match is not None, f"missing Caddy host: {host}"
    assert len(re.findall(rf"(?m)^{re.escape(host)}\s*\{{", text)) == 1
    start = match.start()
    opening = text.index("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unbalanced Caddy host block: {host}")


def _control_block() -> str:
    return _site_block(CADDY.read_text(encoding="utf-8"), "control.mastermind-x.com")


def _adapted_control_execution_labels() -> list[str]:
    """Return security-relevant handlers in Caddy's real adapted order."""
    result = subprocess.run(
        [CADDY_BIN, "adapt", "--config", str(CADDY), "--pretty"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    document = json.loads(result.stdout)
    site = None
    for server in document["apps"]["http"]["servers"].values():
        for route in server.get("routes", []):
            if any(
                "control.mastermind-x.com" in matcher.get("host", [])
                for matcher in route.get("match", [])
            ):
                site = route
                break
        if site is not None:
            break
    assert site is not None, "adapted config omitted the Control Room host"

    labels: list[str] = []

    def walk(routes: list[dict]) -> None:
        for route in routes:
            matchers = route.get("match", [])
            for handler in route.get("handle", []):
                kind = handler.get("handler")
                if kind == "subroute":
                    walk(handler.get("routes", []))
                    continue
                if kind == "static_response":
                    if any("/healthz" in matcher.get("path", []) for matcher in matchers):
                        labels.append("health_404")
                    elif any("not" in matcher for matcher in matchers):
                        labels.append("mutation_405")
                    continue
                if kind != "reverse_proxy":
                    continue
                if handler.get("rewrite", {}).get("uri") == "/api/auth-check":
                    labels.append("auth_proxy")
                    continue
                if any(
                    upstream.get("dial") == "unix//run/mastermind-control-room/remote.sock"
                    for upstream in handler.get("upstreams", [])
                ):
                    labels.append("unix_proxy")

    walk([site])
    return labels


def test_control_room_authenticates_once_before_the_only_unix_origin():
    """Removing/reordering the auth subrequest or adding a second origin must fail."""
    block = _control_block()

    assert block.count("reverse_proxy 127.0.0.1:8787 {") == 1
    assert block.count("rewrite /api/auth-check") == 1
    assert block.count("reverse_proxy unix//run/mastermind-control-room/remote.sock {") == 1
    assert block.index("rewrite /api/auth-check") < block.index(
        "reverse_proxy unix//run/mastermind-control-room/remote.sock {"
    )
    auth = block[:block.index("reverse_proxy unix//run/mastermind-control-room/remote.sock {")]
    assert "header_up Host admin.mastermind-x.com" in auth
    assert re.search(r"@operator\s+status\s+2xx", block)
    assert re.search(r"handle_response\s+@operator\s*\{\s*\}", block)
    assert "127.0.0.1:8000" not in block
    assert "/api/control-room/auth-check" not in block
    assert not re.search(r"reverse_proxy\s+(?:127\.0\.0\.1|localhost|\[::1\]):\d+", block.replace("127.0.0.1:8787", ""))


def test_control_room_refuses_health_and_mutation_before_origin():
    """Health and mutation-shaped requests must never reach auth or projection."""
    block = _control_block()

    assert "@health path /healthz" in block
    assert "respond @health 404" in block
    assert "@mutation not method GET HEAD" in block
    assert "respond @mutation 405" in block
    route = block.index("route {")
    auth = block.index("rewrite /api/auth-check")
    assert route < block.index("respond @health 404") < auth
    assert route < block.index("respond @mutation 405") < auth
    assert "rewrite /healthz" not in block


def test_control_room_adapted_order_refuses_health_and_mutation_before_origin():
    """Caddy directive sorting must not move either refusal behind a proxy."""
    assert _adapted_control_execution_labels() == [
        "health_404",
        "mutation_405",
        "auth_proxy",
        "unix_proxy",
    ]


def test_control_room_socket_hop_strips_every_browser_and_forged_identity_header():
    """No browser credential or caller-supplied identity proof may cross the socket."""
    block = _control_block()
    socket = block[block.index("reverse_proxy unix//run/mastermind-control-room/remote.sock {") :]

    for name in (
        "Cookie",
        "Authorization",
        "X-CCR-Token",
        "X-Authenticated-User",
        "X-Original-Uri",
        "X-Original-Method",
        "X-Forwarded-For",
        "X-Forwarded-Host",
        "X-Forwarded-Proto",
    ):
        assert f"header_up -{name}" in socket
    assert "header_up Host control.mastermind-x.com" in socket


def test_control_room_responses_are_private_embeddable_only_by_admin_and_not_cached():
    """A broadened frame/cache/CORS policy or XFO conflict must fail."""
    block = _control_block()

    assert 'Cache-Control "private, no-store"' in block
    assert 'Vary "Cookie"' in block
    assert 'Strict-Transport-Security "max-age=31536000"' in block
    assert 'X-Content-Type-Options "nosniff"' in block
    assert 'X-Robots-Tag "noindex, nofollow, noarchive"' in block
    csp = re.search(r'Content-Security-Policy "([^"]+)"', block)
    assert csp is not None
    assert csp.group(1) == (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'; "
        "frame-ancestors https://admin.mastermind-x.com"
    )
    assert "-X-Frame-Options" in block
    assert not re.search(r"(?m)^\s*X-Frame-Options\b", block)
    assert "Access-Control-Allow" not in block
    assert "stale-if-error" not in block.lower()
    assert "file_server" not in block
    assert "try_files" not in block


# The acquisition checks below run the exact CI shell with a test-owned loopback
# archive, checksum and final Python marker. They never contact the release host
# or invoke/replay the security suites; those remain the unchanged next command.
_PINNED_CADDY_URL = (
    "https://github.com/caddyserver/caddy/releases/download/v2.11.4/"
    "caddy_2.11.4_linux_amd64.tar.gz"
)
_PINNED_CADDY_SHA256 = "527fbf917c39189a1e3b31d34fa955601680b2d5c8055d2a87b8b9588dec7bb9"


def _caddy_acquisition_command() -> str:
    import yaml

    jobs = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())["jobs"]
    steps = jobs["prelaunch-hardening"]["steps"]
    commands = [step["run"] for step in steps if step.get("name") ==
                "Control Room operator, embed, edge and source-publisher boundaries"]
    assert len(commands) == 1
    command = commands[0]
    assert command.count(_PINNED_CADDY_URL) == 1
    assert command.count(_PINNED_CADDY_SHA256) == 1
    return command


def test_caddy_acquisition_has_finite_same_origin_recovery():
    import shlex

    command = _caddy_acquisition_command()
    curl = next(line for line in command.replace("\\\n", " ").splitlines()
                if line.strip().startswith("curl "))
    args = shlex.split(curl)
    for flag, value in {"--retry": "2", "--retry-delay": "1",
                        "--retry-max-time": "45", "--connect-timeout": "10",
                        "--max-time": "15"}.items():
        assert args[args.index(flag) + 1] == value
    assert args.count(_PINNED_CADDY_URL) == 1
    assert not any(flag in args for flag in
                   ("--retry-all-errors", "--insecure", "-k", "--next"))
    assert command.index("sha256sum --check --status") < command.index("tar -xzf")
    assert command.index("tar -xzf") < command.index('CADDY_BIN="$CADDY_DIR/caddy" python')
    assert command.count("python -m pytest") == 1


def _exercise_caddy_acquisition(tmp_path, statuses, *, checksum_mismatch=False):
    import hashlib
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import io
    import shutil
    import sys
    import tarfile
    import threading

    binary = b"test-owned-caddy-fixture\n"
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        member = tarfile.TarInfo("caddy")
        member.size = len(binary)
        member.mode = 0o755
        tar.addfile(member, io.BytesIO(binary))
    payload = archive.getvalue()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            status = statuses[min(len(requests) - 1, len(statuses) - 1)]
            body = payload if status == 200 else b"test-owned acquisition failure"
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    marker = tmp_path / "security-command-reached.json"
    tools = tmp_path / "bin"
    tools.mkdir()
    if sys.platform == "darwin":
        # macOS sha256sum lacks GNU --status. Its standard shasum implements
        # the same SHA256 check/status operation; Ubuntu uses real sha256sum.
        import shlex
        shasum = shutil.which("shasum")
        assert shasum is not None
        checksum = tools / "sha256sum"
        checksum.write_text("#!/bin/sh\nexec " + shlex.quote(shasum) + ' -a 256 "$@"\n')
        checksum.chmod(0o755)
    # Replace only the final Python command, keeping actual curl, hash checking,
    # archive extraction and bash -eo pipefail semantics in this offline proof.
    stub = tools / "python"
    stub.write_text(
        "#!" + sys.executable + "\n"
        "import json,os,pathlib,sys\n"
        "assert pathlib.Path(os.environ['CADDY_BIN']).read_bytes() == " + repr(binary) + "\n"
        "pathlib.Path(os.environ['CADDY_TEST_MARKER']).write_text(json.dumps(sys.argv[1:]))\n"
    )
    stub.chmod(0o755)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        digest = "0" * 64 if checksum_mismatch else hashlib.sha256(payload).hexdigest()
        command = _caddy_acquisition_command().replace(
            _PINNED_CADDY_URL, f"http://127.0.0.1:{server.server_port}/pinned-test-archive"
        ).replace(_PINNED_CADDY_SHA256, digest)
        environment = {"PATH": str(tools) + os.pathsep + os.environ["PATH"],
                       "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
                       "NO_PROXY": "127.0.0.1", "CADDY_TEST_MARKER": str(marker)}
        result = subprocess.run(
            [shutil.which("bash"), "-eo", "pipefail", "-c", command],
            cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=55,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    reached = json.loads(marker.read_text()) if marker.exists() else None
    return result, requests, reached


def test_caddy_acquisition_transient_504_recovers_before_security_execution(tmp_path):
    result, requests, reached = _exercise_caddy_acquisition(tmp_path, [504, 200])
    assert result.returncode == 0, result.stderr
    assert len(requests) == 2
    assert reached == ["-m", "pytest", "tests/test_admin_control_room.py",
                       "tests/test_control_room_auth.py", "tests/test_control_room_caddy.py",
                       "tests/test_publish_control_room_active_builds.py", "-q"]


def test_caddy_acquisition_exhausted_504_stays_blocking(tmp_path):
    result, requests, reached = _exercise_caddy_acquisition(tmp_path, [504])
    assert result.returncode != 0
    assert len(requests) == 3
    assert reached is None


def test_caddy_acquisition_nonretryable_403_stays_blocking(tmp_path):
    result, requests, reached = _exercise_caddy_acquisition(tmp_path, [403])
    assert result.returncode != 0
    assert len(requests) == 1
    assert reached is None


def test_caddy_acquisition_wrong_checksum_never_executes_security_command(tmp_path):
    result, requests, reached = _exercise_caddy_acquisition(
        tmp_path, [200], checksum_mismatch=True,
    )
    assert result.returncode != 0
    assert len(requests) == 1
    assert reached is None
