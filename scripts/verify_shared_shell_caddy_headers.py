#!/usr/bin/env python3
"""Exercise actual Caddy header behavior in an isolated loopback server."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def verify(caddyfile: Path, caddy: str) -> list[dict]:
    source = caddyfile.read_text()
    begin = source.index("\t# Shared Shell presentation admission changes framing only.")
    end = source.index("\n}\n\nwww.mastermind-x.com {", begin)
    headers = source[begin:end]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = (
        "{\n admin off\n auto_https off\n}\n"
        + f"http://127.0.0.1:{port} {{\n"
        + headers
        + """
    route {
        @blocked path /blocked.html
        handle @blocked {
            header Cache-Control "no-store"
            respond "existing region gate" 403
        }
        handle {
            header Cache-Control "public, max-age=60, must-revalidate"
            respond "existing product document" 200
        }
    }
}
"""
    )
    cases = [
        ("/macro.html", None, False, 200),
        ("/macro.html?mmx_shell=1", None, False, 200),
        ("/macro.html?mmx_shell=1", "https://example.test/", False, 200),
        ("/macro.html?mmx_shell=1", "https://beta.mastermind-x.com.evil.test/", False, 200),
        ("/macro.html?mmx_shell=0", "https://beta.mastermind-x.com/", False, 200),
        ("/data/member.json?mmx_shell=1", "https://beta.mastermind-x.com/", False, 200),
        ("/macro.html?mmx_shell=1", "https://beta.mastermind-x.com/", True, 200),
        ("/stocks/AAPL.html?filter=a%20b&mmx_shell=1", "https://beta.mastermind-x.com/macro.html", True, 200),
        ("/blocked.html?mmx_shell=1", "https://beta.mastermind-x.com/", True, 403),
        ("/blocked.html", None, False, 403),
    ]
    receipts = []
    with tempfile.TemporaryDirectory(prefix="shared-shell-caddy-proof-") as temp:
        root = Path(temp)
        config_path = root / "Caddyfile"
        config_path.write_text(config)
        with (root / "caddy.log").open("w+") as log:
            process = subprocess.Popen([caddy, "run", "--config", str(config_path), "--adapter", "caddyfile"],
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                base = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 8
                while True:
                    try:
                        urllib.request.urlopen(base + "/ready.html", timeout=1).close()
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if process.poll() is not None or time.monotonic() >= deadline:
                            log.seek(0)
                            raise RuntimeError("Isolated Caddy did not start: " + log.read()[-1500:])
                        time.sleep(0.05)
                for path, referer, embedded, expected_status in cases:
                    request = urllib.request.Request(base + path)
                    if referer:
                        request.add_header("Referer", referer)
                    try:
                        response = urllib.request.urlopen(request, timeout=3)
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        status = response.status
                        actual = response.headers
                        body = response.read()
                    expected_csp = "base-uri 'self'; object-src 'none'; frame-ancestors " + (
                        "https://beta.mastermind-x.com" if embedded else "'none'")
                    assert status == expected_status, (path, status)
                    assert actual.get("Content-Security-Policy") == expected_csp, (path, dict(actual))
                    assert actual.get("X-Frame-Options") == (None if embedded else "DENY"), (path, dict(actual))
                    if embedded:
                        assert actual.get("Cache-Control") == "private, no-store", (path, dict(actual))
                        assert "Cookie" in actual.get("Vary", ""), (path, dict(actual))
                    if expected_status == 403:
                        assert body == b"existing region gate"
                        assert "no-store" in actual.get("Cache-Control", "")
                    receipts.append({"path": path, "referer": referer, "embedded": embedded, "status": status})
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caddyfile", type=Path, default=Path(__file__).resolve().parent.parent / "app/deploy/Caddyfile")
    parser.add_argument("--caddy", default=shutil.which("caddy"))
    args = parser.parse_args()
    if not args.caddy:
        parser.error("An installed Caddy binary is required; this check cannot certify by source inspection.")
    receipts = verify(args.caddyfile, args.caddy)
    print(json.dumps({"schema": "mastermind.shared_shell_caddy_header_proof.v1", "passed": len(receipts), "cases": receipts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
