"""Failure-case tests for engine.research_vault.generation_evidence.

These tests exercise the durable before-effects evidence boundary. They make
no claim over recovery, ownership transfer, or implementation internals.
"""
import hashlib
import json
import os

import pytest

from engine.research_vault.generation_evidence import (
    EvidenceUnavailable,
    FileGenerationEvidence,
    read_evidence,
)

SCHEMA = "research_vault.generation_evidence.v1"
ALLOWED_KINDS = {
    "header",
    "write_intent",
    "write_result",
    "catalog_observed",
    "publication_plan",
    "terminal",
}


def _identity():
    return {"source_commit": "a" * 40, "run": "test-run-1"}


def _identity_alt():
    return {"source_commit": "b" * 40, "run": "test-run-2"}


def _read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def test_persists_header_and_chain_no_implicit_terminal(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    try:
        w.append("write_intent", {"target": "x.py"})
        w.append("write_result", {"ok": True})
        w.append("catalog_observed", {"entries": 3})
        w.append("publication_plan", {"channels": ["local"]})
    finally:
        w.close()

    raw = _read_bytes(str(p)).decode("utf-8")
    assert raw.endswith("\n"), "file must end with newline"
    envelopes = [json.loads(line) for line in raw.splitlines()]

    # close() never appends a terminal event implicitly
    kinds = [e["event"]["kind"] for e in envelopes]
    assert "terminal" not in kinds

    for env in envelopes:
        assert env["schema"] == SCHEMA
        assert isinstance(env["sequence"], int)
        assert "previous_sha256" in env
        assert "event" in env
        assert "kind" in env["event"]
        assert "payload" in env["event"]
        assert env["event"]["kind"] in ALLOWED_KINDS

    assert envelopes[0]["sequence"] == 0
    assert envelopes[0]["event"]["kind"] == "header"
    assert envelopes[0]["event"]["payload"]["identity"] == _identity()
    assert envelopes[0]["previous_sha256"] is None


def test_sequence_starts_zero_and_increments(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    try:
        s1 = w.append("write_intent", {"a": 1})
        s2 = w.append("write_result", {"b": 2})
        s3 = w.append("catalog_observed", {"c": 3})
    finally:
        w.close()
    assert (s1, s2, s3) == (1, 2, 3)


def test_previous_sha256_chain_hashes_previous_line(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    try:
        w.append("write_intent", {"a": 1})
        w.append("write_result", {"b": 2})
    finally:
        w.close()

    raw = _read_bytes(str(p))
    lines = []
    pos = 0
    while pos < len(raw):
        nl = raw.find(b"\n", pos)
        assert nl != -1, "incomplete newline suffix"
        lines.append(raw[pos:nl + 1])
        pos = nl + 1

    first = json.loads(lines[0])
    assert first["previous_sha256"] is None

    for i in range(1, len(lines)):
        expected = hashlib.sha256(lines[i - 1]).hexdigest()
        env = json.loads(lines[i])
        assert env["previous_sha256"] == expected


def test_create_refuses_overwrite(tmp_path):
    p = tmp_path / "g.md"
    p.write_text("existing\n")
    with pytest.raises(EvidenceUnavailable):
        FileGenerationEvidence.create(str(p), _identity())


def test_create_refuses_symlink(tmp_path):
    target = tmp_path / "real.md"
    target.write_text("")
    link = tmp_path / "link.md"
    os.symlink(str(target), str(link))
    with pytest.raises(EvidenceUnavailable):
        FileGenerationEvidence.create(str(link), _identity())


def test_create_requires_existing_parent_directory(tmp_path):
    p = tmp_path / "missing" / "g.md"
    with pytest.raises(EvidenceUnavailable):
        FileGenerationEvidence.create(str(p), _identity())


def test_file_mode_is_0600(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.close()
    mode = os.stat(str(p)).st_mode & 0o777
    assert mode == 0o600


def test_reader_fails_while_writer_held(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"a": 1})
    try:
        with pytest.raises(EvidenceUnavailable):
            read_evidence(str(p), expected_identity=_identity())
    finally:
        w.close()


def test_read_round_trip_after_close(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"target": "x"})
    w.append("write_result", {"ok": True, "lines": 42})
    w.close()
    events = read_evidence(str(p), expected_identity=_identity())
    assert [e["kind"] for e in events] == [
        "header", "write_intent", "write_result"
    ]
    assert events[0]["payload"]["identity"] == _identity()
    assert events[1]["payload"] == {"target": "x"}
    assert events[2]["payload"] == {"ok": True, "lines": 42}


def test_identity_mismatch_raises(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.close()
    with pytest.raises(EvidenceUnavailable):
        read_evidence(str(p), expected_identity=_identity_alt())


def test_tamper_detection(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"a": 1})
    w.close()
    raw = bytearray(_read_bytes(str(p)))
    nl1 = raw.index(b"\n")
    target = nl1 + 5
    while raw[target] == 0x0A:
        target += 1
    raw[target] = raw[target] ^ 0x20
    with open(str(p), "wb") as f:
        f.write(bytes(raw))
    with pytest.raises(EvidenceUnavailable):
        read_evidence(str(p), expected_identity=_identity())


def test_whole_line_truncation_requires_original_capture_digest(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"a": 1})
    w.append("write_result", {"b": 2})
    w.close()
    raw = _read_bytes(str(p))
    original_digest = hashlib.sha256(raw).hexdigest()
    nl1 = raw.index(b"\n")
    with open(str(p), "wb") as f:
        f.write(raw[:nl1 + 1])
    # A valid prefix is indistinguishable from a shorter journal without an
    # independently retained original capture. Format validity grants nothing.
    assert len(read_evidence(str(p), expected_identity=_identity())) == 1
    with pytest.raises(EvidenceUnavailable):
        read_evidence(str(p), expected_identity=_identity(), expected_sha256=original_digest)


def test_incomplete_newline_suffix_rejected(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"a": 1})
    w.close()
    raw = _read_bytes(str(p))
    with open(str(p), "wb") as f:
        f.write(raw[:-1])
    with pytest.raises(EvidenceUnavailable):
        read_evidence(str(p), expected_identity=_identity())


def test_nonfinite_payload_rejected_before_append(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    try:
        with pytest.raises(EvidenceUnavailable):
            w.append("write_intent", {"x": float("nan")})
        with pytest.raises(EvidenceUnavailable):
            w.append("write_intent", {"x": float("inf")})
        raw = _read_bytes(str(p))
        envelopes = [json.loads(line) for line in raw.splitlines()]
        assert len(envelopes) == 1
        assert envelopes[0]["event"]["kind"] == "header"
    finally:
        w.close()


def test_disallowed_kind_rejected_before_append(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    try:
        with pytest.raises(EvidenceUnavailable):
            w.append("not_a_kind", {"x": 1})
    finally:
        w.close()


def test_max_bytes_narrows_total_budget(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity(), max_bytes=4096)
    try:
        big = "x" * 8192
        with pytest.raises(EvidenceUnavailable):
            w.append("write_intent", {"big": big})
    finally:
        w.close()


def test_append_after_close_refuses(tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())
    w.append("write_intent", {"a": 1})
    w.close()
    with pytest.raises(EvidenceUnavailable):
        w.append("write_result", {"b": 2})


def test_poison_after_io_failure_refuses(monkeypatch, tmp_path):
    p = tmp_path / "g.md"
    w = FileGenerationEvidence.create(str(p), _identity())

    real_write = os.write

    def failing_write(fd, data):
        raise OSError("injected write failure")

    monkeypatch.setattr(os, "write", failing_write)
    with pytest.raises(EvidenceUnavailable):
        w.append("write_intent", {"a": 1})

    monkeypatch.setattr(os, "write", real_write)
    with pytest.raises(EvidenceUnavailable):
        w.append("write_result", {"b": 2})

    w.close()


def test_fsync_failure_poison_survives_restored_io(monkeypatch, tmp_path):
    p = tmp_path / "original.jsonl"
    w = FileGenerationEvidence.create(p, _identity())
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(os, "fsync", lambda _: (_ for _ in ()).throw(OSError("disk")))
            with pytest.raises(EvidenceUnavailable):
                w.append("write_intent", {"key": "synthetic"})
        with pytest.raises(EvidenceUnavailable):
            w.append("write_result", {"outcome": "must not be written"})
    finally:
        w.close()


def test_partial_os_writes_are_fully_drained(monkeypatch, tmp_path):
    p = tmp_path / "original.jsonl"
    w = FileGenerationEvidence.create(p, _identity())
    real_write = os.write
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(os, "write", lambda fd, data: real_write(fd, data[:7]))
            w.append("write_intent", {"key": "synthetic", "message": "utf8 café"})
    finally:
        w.close()
    assert read_evidence(p, expected_identity=_identity())[1]["payload"]["message"] == "utf8 café"


@pytest.mark.parametrize("mode", [0o640, 0o602])
def test_reader_refuses_nonprivate_modes(tmp_path, mode):
    p = tmp_path / "original.jsonl"
    FileGenerationEvidence.create(p, _identity()).close()
    p.chmod(mode)
    with pytest.raises(EvidenceUnavailable):
        read_evidence(p, expected_identity=_identity())


def test_reader_refuses_symlink_and_fifo(tmp_path):
    p = tmp_path / "original.jsonl"
    FileGenerationEvidence.create(p, _identity()).close()
    link = tmp_path / "link"
    link.symlink_to(p)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    for candidate in (link, fifo):
        with pytest.raises(EvidenceUnavailable):
            read_evidence(candidate, expected_identity=_identity())


@pytest.mark.parametrize("replacement", [b'"sequence":0,"sequence":0', b'"sequence":NaN'])
def test_reader_refuses_duplicate_and_nonfinite_json(tmp_path, replacement):
    p = tmp_path / "original.jsonl"
    FileGenerationEvidence.create(p, _identity()).close()
    original = p.read_bytes()
    assert b'"sequence":0' in original
    p.write_bytes(original.replace(b'"sequence":0', replacement))
    with pytest.raises(EvidenceUnavailable):
        read_evidence(p, expected_identity=_identity())


def test_original_capture_digest_binds_valid_last_record(tmp_path):
    p = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(p, _identity()) as w:
        w.append("write_result", {"outcome": "original"})
    original = p.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert len(read_evidence(p, expected_identity=_identity(), expected_sha256=digest)) == 2
    p.write_bytes(original.replace(b'"original"', b'"modified"'))
    with pytest.raises(EvidenceUnavailable, match="capture digest mismatch"):
        read_evidence(p, expected_identity=_identity(), expected_sha256=digest)


def test_reader_total_bound_and_budget_refusal_preserve_bytes(tmp_path):
    p = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(p, _identity(), max_bytes=512) as w:
        before = p.read_bytes()
        with pytest.raises(EvidenceUnavailable):
            w.append("write_intent", {"payload": "x" * 1024})
        assert p.read_bytes() == before
    with pytest.raises(EvidenceUnavailable):
        read_evidence(p, expected_identity=_identity(), max_bytes=1)
