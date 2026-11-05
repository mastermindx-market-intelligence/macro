#!/usr/bin/env python3
"""Loopback-only static server for the Prophet B23 latency lab leg.

Serves one directory over HTTP on ``127.0.0.1`` ONLY — never another interface,
never a port chosen by the caller's environment — and appends one JSON line to a
journal for every request it answers, including the requests it refuses. The
journal is the server-held-time evidence the B23 acceptance report turns into a
per-route distribution (``scripts/prophet_journey_latency_report.py``); the prior
art is ``research/defense_intelligence/e2e_20261011/combined_generation_v13_proof/
diagnostic_server.py`` (per-request ``elapsed_ms``), minus everything that proof
owned which a static lab leg does not: no app import, no entitlement principal,
no in-memory rows — the journal is the record.

Contract
--------
1. **Loopback only.** The bind address is the constant ``BIND_HOST`` and there is
   no flag that can move it. A latency lab has no reason to be reachable from
   any other host, and the render-budget law means it must never run in CI at
   all — local seat hosts only.
2. **Every request is journaled, exactly once, append-only.** One JSON object
   per line: ``method``, ``path`` (the request target without its query),
   ``status``, ``bytes`` (response body length actually sent), ``elapsed_ms``
   (server-held time for the answer), ``sha256`` (of the response body bytes),
   ``seq`` (monotonic across the journal file, continuing from the lines that
   already exist — an append-only ledger does not restart its sequence). The
   journal is opened with ``O_APPEND`` and is never truncated by this tool;
   starting a second server on the same journal appends after the existing
   lines.
3. **A path outside the served root is refused with 403, and the refusal is
   journaled like any other answer.** Dot-dot segments, absolute-artifact
   targets, embedded NULs, and symlink escapes are all refusals — the
   containment check runs on the fully resolved candidate, so a symlink that
   leaves the root is caught however it is spelled. (A literal ``//…`` request
   target never reaches this check: CPython's own ``parse_request`` collapses
   the double slash to one — gh-87389 — and the collapsed form can only
   resolve inside the root; the percent-encoded spelling does reach it and is
   refused.) A well-formed path that simply does not exist inside the root is
   a 404, also journaled.
4. **Every response carries ``Cache-Control: no-store``.** Cold loads must stay
   cold: the statistics the report computes are cold-load numbers, so the lab
   server never lets a browser satisfy a load from cache. (The B23 failure
   taxonomy's "gated asset without no-store" class is about the deployed plane;
   here no-store is unconditional and asserted by test.)
5. **Directories are not listed.** ``/`` and ``…/`` resolve to that directory's
   ``index.html`` when present and 404 when not. Nothing enumerates the tree.
6. **No subprocess, no glob, no directory enumeration, no environment read.**
   Same statically-opaque-edge rule as ``scripts/capture_page_evidence.py`` —
   this module names only the paths it is handed.

Usage::

    python3 scripts/prophet_journey_lab_serve.py --root site --journal run/journal.jsonl
    # prints one readiness line: {"bound": "127.0.0.1", "port": <port>, ...}
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

MODULE_REF = "scripts/prophet_journey_lab_serve.py"
TOOL_VERSION = "1.0.0"

# The whole point of the lab leg: reachable only from the seat host itself.
BIND_HOST = "127.0.0.1"

EXIT_OK = 0
EXIT_USAGE = 2

# Journal line keys — frozen shape; the report generator parses these.
JOURNAL_KEYS: tuple[str, ...] = (
    "bytes",
    "elapsed_ms",
    "method",
    "path",
    "seq",
    "sha256",
    "status",
)

_INDEX_NAME = "index.html"
_REFUSAL_BODY = b"lab server: path outside the served root\n"
_NOT_FOUND_BODY = b"lab server: no such file under the served root\n"
_METHOD_BODY = b"lab server: method not allowed on a static lab server\n"


class LabServerError(RuntimeError):
    """Raised for conditions the operator must fix (unusable root/journal)."""


class RequestJournal:
    """Append-only jsonl request ledger.

    The file descriptor is opened once with ``O_APPEND`` (never ``O_TRUNC``) and
    held for the server's lifetime; ``seq`` continues from the number of lines
    already in the file, so successive runs on one journal keep one monotonic
    sequence instead of restarting it.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        self._lock = threading.Lock()
        self._seq = self._count_existing_lines(path)

    @staticmethod
    def _count_existing_lines(path: Path) -> int:
        # Bounded read of an explicit path the operator named — not enumeration.
        try:
            with path.open("rb") as fh:
                return sum(1 for line in fh if line.strip())
        except FileNotFoundError:
            return 0

    def record(
        self,
        *,
        method: str,
        path: str,
        status: int,
        bytes_sent: int,
        elapsed_ms: float,
        sha256: str,
    ) -> int:
        """Append one request line; returns the sequence number it received."""

        with self._lock:
            self._seq += 1
            row: dict[str, Any] = {
                "seq": self._seq,
                "method": method,
                "path": path,
                "status": status,
                "bytes": bytes_sent,
                "elapsed_ms": round(float(elapsed_ms), 3),
                "sha256": sha256,
            }
            line = json.dumps(row, sort_keys=True) + "\n"
            os.write(self._fd, line.encode("utf-8"))
            return row["seq"]

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1


def resolve_request_path(root: Path, raw_target: str) -> tuple[str, Path | None, str]:
    """Map a raw request target to a file inside ``root``.

    Returns ``(path_for_journal, candidate_or_None, refusal_reason)``. A
    ``None`` candidate with a non-empty reason is a 403 refusal (outside the
    served root however it was spelled); a ``None`` candidate with an empty
    reason is a plain 404 (inside the root, no such file). The journal always
    gets the target path without its query — a static file's identity is its
    path, and per-route grouping in the report keys on exactly that.
    """

    path_only = raw_target.split("?", 1)[0].split("#", 1)[0]
    if not path_only.startswith("/"):
        return path_only, None, "target is not an absolute-path form"
    decoded = urllib.parse.unquote(path_only)
    if "\x00" in decoded:
        return path_only, None, "target contains a NUL byte"

    relative = decoded[1:]
    if relative.startswith("/"):
        # "//…" and "/\x2f…" artifacts: an absolute path glued to the mount,
        # which POSIX treats ambiguously. Not a file under the root.
        return path_only, None, "target embeds an absolute path"

    segments: list[str] = []
    trailing_slash = decoded.endswith("/")
    for segment in relative.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            return path_only, None, "target traverses above the served root"
        segments.append(segment)
    if not segments or trailing_slash:
        segments.append(_INDEX_NAME)

    root_resolved = root.resolve()
    try:
        candidate = root_resolved.joinpath(*segments)
        resolved = candidate.resolve()
    except (OSError, RuntimeError, ValueError):
        return path_only, None, "target does not resolve to a path under the root"
    if resolved != root_resolved and not resolved.is_relative_to(root_resolved):
        # Catches symlink escapes and any spelling the segment walk allowed.
        return path_only, None, "target resolves outside the served root"
    if not resolved.is_file():
        return path_only, None, ""
    return path_only, resolved, ""


class LabServeHandler(http.server.BaseHTTPRequestHandler):
    """One request in, one journal line out."""

    # keep-alive is fine: every answer sets Content-Length through _send().
    protocol_version = "HTTP/1.1"
    server_version = "mastermind-lab-serve/" + TOOL_VERSION
    sys_version = ""

    def log_message(self, *args: Any) -> None:  # noqa: D102 - silence per-request noise
        return

    # -- plumbing -----------------------------------------------------------

    def _send(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        method: str,
        path: str,
        started: float,
        head_only: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if status == 405:
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        sent = 0 if head_only else len(body)
        if not head_only and body:
            self.wfile.write(body)
        digest = hashlib.sha256(body).hexdigest()
        self.server.journal.record(
            method=method,
            path=path,
            status=status,
            bytes_sent=sent,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            sha256=digest,
        )

    def _answer(self, method: str, head_only: bool = False) -> None:
        started = time.perf_counter()
        journal_path, candidate, refusal = resolve_request_path(
            self.server.served_root, self.path
        )
        if candidate is not None:
            try:
                payload = candidate.read_bytes()
            except OSError:
                payload = None
            if payload is not None:
                guessed = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                if guessed.startswith("text/"):
                    guessed += "; charset=utf-8"
                self._send(
                    200,
                    payload,
                    content_type=guessed,
                    method=method,
                    path=journal_path,
                    started=started,
                    head_only=head_only,
                )
                return
        if refusal:
            self._send(
                403,
                _REFUSAL_BODY,
                content_type="text/plain; charset=utf-8",
                method=method,
                path=journal_path,
                started=started,
                head_only=head_only,
            )
            return
        self._send(
            404,
            _NOT_FOUND_BODY,
            content_type="text/plain; charset=utf-8",
            method=method,
            path=journal_path,
            started=started,
            head_only=head_only,
        )

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        self._answer("GET")

    def do_HEAD(self) -> None:  # noqa: N802 - http.server naming
        self._answer("HEAD", head_only=True)

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        self._refuse_method("POST")

    def do_PUT(self) -> None:  # noqa: N802 - http.server naming
        self._refuse_method("PUT")

    def do_DELETE(self) -> None:  # noqa: N802 - http.server naming
        self._refuse_method("DELETE")

    def _refuse_method(self, method: str) -> None:
        # Drain the declared body (bounded by what the client declared) so the
        # connection is not left with unread bytes, then answer and close.
        started = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 0:
            self.rfile.read(min(length, 1 << 20))
        path_only = self.path.split("?", 1)[0].split("#", 1)[0]
        self._send(
            405,
            _METHOD_BODY,
            content_type="text/plain; charset=utf-8",
            method=method,
            path=path_only,
            started=started,
        )


class LabServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer carrying its journal; closing it closes the journal."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, root: Path, journal: RequestJournal, port: int = 0) -> None:
        # BIND_HOST only — see contract §1. There is deliberately no parameter.
        super().__init__((BIND_HOST, port), LabServeHandler)
        self.journal = journal
        self.served_root = root

    def server_close(self) -> None:
        super().server_close()
        self.journal.close()


def make_server(root: Path | str, journal_path: Path | str, port: int = 0) -> tuple[LabServer, int]:
    """Build (and bind, without serving) a lab server; returns (server, port)."""

    root_path = Path(root)
    if not root_path.is_dir():
        raise LabServerError(f"served root is not a directory: {root_path}")
    journal = RequestJournal(Path(journal_path))
    server = LabServer(root_path.resolve(), journal, port=port)
    return server, server.server_address[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", required=True, help="directory to serve (loopback only)")
    parser.add_argument("--journal", required=True, help="append-only jsonl request journal")
    parser.add_argument("--port", type=int, default=0, help="port to bind (0 = ephemeral)")
    args = parser.parse_args(argv)

    try:
        server, port = make_server(args.root, args.journal, port=args.port)
    except LabServerError as exc:
        print(f"lab server: {exc}", file=sys.stderr)
        return EXIT_USAGE

    print(
        json.dumps(
            {
                "bound": BIND_HOST,
                "port": port,
                "root": str(Path(args.root).resolve()),
                "journal": str(Path(args.journal)),
                "tool": MODULE_REF,
                "version": TOOL_VERSION,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
