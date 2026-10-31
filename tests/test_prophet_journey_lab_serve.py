"""Hermetic tests for the Prophet B23 lab server (BU4).

No test here opens a browser or contacts anything off 127.0.0.1: the server is
the loopback-only static file owner for the latency lab leg, and these tests
exercise exactly its frozen contract — the bind address, the append-only
journal, and the refusals. One named test exists per FROZEN SPEC item 4 clause;
the rest pin the journal line shape the report generator parses.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prophet_journey_lab_serve.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("prophet_journey_lab_serve_under_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lab = _load_module()


@contextlib.contextmanager
def running_server(tmp_path: Path, *, files: dict[str, bytes] | None = None, journal: str = "journal.jsonl"):
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    for name, content in (files or {}).items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    journal_path = tmp_path / journal
    server, port = lab.make_server(root, journal_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, port, journal_path, root
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get(port: int, path: str, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read()
        headers = {k.lower(): v for k, v in response.getheaders()}
        return response.status, headers, body
    finally:
        conn.close()


def journal_rows(journal_path: Path) -> list[dict]:
    if not journal_path.exists():
        return []
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# FROZEN SPEC item 4 — loopback bind, root containment, append-only journal
# ---------------------------------------------------------------------------


def test_spec4_server_binds_127_0_0_1_only(tmp_path):
    """FROZEN SPEC 4a: the server binds 127.0.0.1 only; a test asserts it."""

    root = tmp_path / "root"
    root.mkdir()
    server, port = lab.make_server(root, tmp_path / "journal.jsonl")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # The bound address itself, not just a successful local connection.
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] == port > 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_spec4_journal_is_append_only_never_truncated(tmp_path):
    """FROZEN SPEC 4d: the journal is opened append-only; prior lines survive."""

    journal_path = tmp_path / "journal.jsonl"
    preexisting = [
        {"seq": 1, "method": "GET", "path": "/old.html", "status": 200, "bytes": 2,
         "elapsed_ms": 1.0, "sha256": "0" * 64},
        {"seq": 2, "method": "GET", "path": "/older.html", "status": 200, "bytes": 3,
         "elapsed_ms": 2.0, "sha256": "1" * 64},
    ]
    with journal_path.open("w", encoding="utf-8") as fh:
        for row in preexisting:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    with running_server(tmp_path, files={"index.html": b"hello"}) as (_, port, journal, _):
        status, _, _ = get(port, "/index.html")
        assert status == 200

    rows = journal_rows(journal)
    assert len(rows) == 3, "one request must append exactly one line to the existing journal"
    assert rows[0] == preexisting[0] and rows[1] == preexisting[1]
    assert rows[2]["seq"] == 3, "sequence numbers continue from the existing journal"


def test_spec4_dotdot_traversal_refused_403_and_journaled(tmp_path):
    """FROZEN SPEC 4b: '..' outside the served root is a 403, journaled."""

    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"outside the root")
    with running_server(tmp_path, files={"index.html": b"inside"}) as (_, port, journal, root):
        for target in ("/../secret.txt", "/a/../../secret.txt", "/%2e%2e/secret.txt"):
            status, _, body = get(port, target)
            assert status == 403, target
            assert body  # the refusal itself is served bytes, journaled below
    rows = journal_rows(journal)
    assert len(rows) == 3
    assert {row["status"] for row in rows} == {403}
    assert {row["path"] for row in rows} == {"/../secret.txt", "/a/../../secret.txt", "/%2e%2e/secret.txt"}


def raw_get(port: int, target: str) -> tuple[int, str]:
    """Send a request line verbatim; returns (status, the path the server saw).

    http.client refuses/collapses unusual targets client-side, so the refusal
    contract is proven against what actually reaches the wire.
    """

    import socket

    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(f"GET {target} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode())
        status_line = sock.recv(4096).split(b"\r\n", 1)[0]
    return int(status_line.split()[1]), target


def test_spec4_absolute_path_target_refused_403_and_journaled(tmp_path):
    """FROZEN SPEC 4b: an absolute-path artifact target is refused, journaled.

    Two vectors. The percent-encoded absolute target reaches the resolver in
    its literal spelling and is a 403. The raw ``//`` spelling is collapsed to
    ``/`` by CPython's own ``parse_request`` (gh-87389, an upstream
    open-redirect mitigation that runs before any handler code), so what our
    resolver receives is the collapsed form — which can only ever resolve
    inside the served root. The containment property, not the spelling, is the
    guarantee: neither vector can address a byte outside the root.
    """

    with running_server(tmp_path, files={"index.html": b"inside"}) as (_, port, journal, _):
        status, _ = raw_get(port, "//etc/passwd")
        assert status == 404, "collapsed target resolves inside the root (no such file)"
        status, _, _ = get(port, "/%2Fetc%2Fpasswd")
        assert status == 403
    rows = journal_rows(journal)
    assert [row["status"] for row in rows] == [404, 403]
    assert rows[1]["path"] == "/%2Fetc%2Fpasswd"


def test_spec4_symlink_escape_refused_403_and_journaled(tmp_path):
    """FROZEN SPEC 4c: a symlink resolving outside the root is a 403, journaled."""

    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"escaped bytes")
    root = tmp_path / "root"
    root.mkdir()
    (root / "index.html").write_bytes(b"inside")
    (root / "escape.txt").symlink_to(outside)
    # A symlink that stays inside the root still serves — only escapes refuse.
    (root / "alias.html").symlink_to(root / "index.html")

    journal_path = tmp_path / "journal.jsonl"
    server, port = lab.make_server(root, journal_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert get(port, "/escape.txt")[0] == 403
        assert get(port, "/alias.html")[0] == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    rows = journal_rows(journal_path)
    assert [row["status"] for row in rows] == [403, 200]
    assert rows[0]["path"] == "/escape.txt"


# ---------------------------------------------------------------------------
# journal line shape (what the report generator parses)
# ---------------------------------------------------------------------------


def test_journal_line_shape_frozen_fields(tmp_path):
    payload = b"<html><body>lab bytes</body></html>"
    with running_server(tmp_path, files={"index.html": payload}) as (_, port, journal, _):
        status, _, body = get(port, "/index.html")
        assert status == 200 and body == payload

    rows = journal_rows(journal)
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == set(lab.JOURNAL_KEYS)
    assert row["method"] == "GET"
    assert row["path"] == "/index.html"
    assert row["status"] == 200
    assert row["bytes"] == len(payload)
    assert row["sha256"] == hashlib.sha256(payload).hexdigest()
    assert row["seq"] == 1
    assert isinstance(row["elapsed_ms"], (int, float)) and row["elapsed_ms"] >= 0


def test_sequence_numbers_monotonic_across_requests(tmp_path):
    files = {"a.html": b"a", "b.html": b"bb", "c.html": b"ccc"}
    with running_server(tmp_path, files=files) as (_, port, journal, _):
        for name in ("a.html", "b.html", "c.html", "a.html"):
            status, _, _ = get(port, f"/{name}")
            assert status == 200
    rows = journal_rows(journal)
    assert [row["seq"] for row in rows] == [1, 2, 3, 4]


def test_missing_file_is_404_and_journaled(tmp_path):
    with running_server(tmp_path, files={"index.html": b"x"}) as (_, port, journal, _):
        assert get(port, "/nope.txt")[0] == 404
    rows = journal_rows(journal)
    assert rows[-1]["status"] == 404 and rows[-1]["path"] == "/nope.txt"


def test_unsupported_method_refused_405_and_journaled(tmp_path):
    with running_server(tmp_path, files={"index.html": b"x"}) as (_, port, journal, _):
        assert get(port, "/index.html", method="POST")[0] == 405
        assert get(port, "/index.html", method="DELETE")[0] == 405
        assert get(port, "/index.html", method="HEAD")[0] == 200
    rows = journal_rows(journal)
    assert [row["status"] for row in rows] == [405, 405, 200]
    assert rows[2]["bytes"] == 0, "HEAD sends headers only; body bytes are 0"


def test_every_response_carries_cache_control_no_store(tmp_path):
    outside = tmp_path / "o.txt"
    outside.write_bytes(b"o")
    root = tmp_path / "root"
    root.mkdir()
    (root / "index.html").write_bytes(b"x")
    (root / "escape.txt").symlink_to(outside)
    journal_path = tmp_path / "journal.jsonl"
    server, port = lab.make_server(root, journal_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for target in ("/index.html", "/missing.txt", "/escape.txt"):
            _, headers, _ = get(port, target)
            assert headers.get("cache-control") == "no-store", target
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_root_and_trailing_slash_serve_index_html(tmp_path):
    files = {"index.html": b"root index", "sub/index.html": b"sub index"}
    with running_server(tmp_path, files=files) as (_, port, _, _):
        status, _, body = get(port, "/")
        assert status == 200 and body == b"root index"
        status, _, body = get(port, "/sub/")
        assert status == 200 and body == b"sub index"
        status, _, _ = get(port, "/sub")
        assert status == 404, "a directory without its trailing slash has no file"


def test_make_server_rejects_missing_root(tmp_path):
    with pytest.raises(lab.LabServerError):
        lab.make_server(tmp_path / "not-a-directory", tmp_path / "j.jsonl")
