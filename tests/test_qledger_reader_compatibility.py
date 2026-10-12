"""Synthetic compatibility proof for the native read-only QLedger seam.

No production ledger, network, registration, or clock writer is used here.
The unchanged legacy reader is a differential oracle; explicit expectations
also pin ordering, values, and failure behavior rather than parity alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import qledger as q
from engine import qledger_store as store


def _load_claims_path(path: Path):
    return q.load_claims(path.parents[2])


READERS = (q._read_jsonl, store.read_legacy_rows, _load_claims_path)


@pytest.fixture
def claims_path(tmp_path):
    path = tmp_path / "data" / "qledger" / "claims.jsonl"
    path.parent.mkdir(parents=True)
    return path


@pytest.mark.parametrize("payload, expected", [
    ("", []),
    (" \n\t\n", []),
    ('{"claim_id":"one"}\nnot-json\n{"claim_id":"two"}', [
        {"claim_id": "one"}, {"claim_id": "two"},
    ]),
    ('null\ntrue\nfalse\n0\n"文字"\n[1, null]\n{}\n', [
        None, True, False, 0, "文字", [1, None], {},
    ]),
    ('\ufeff{"ignored":"bom"}\n{"kept":"café"}\n{"unfinished":', [
        {"kept": "café"},
    ]),
])
def test_public_loader_matches_legacy_values(claims_path, payload, expected):
    claims_path.write_text(payload, encoding="utf-8")
    for reader in READERS:
        assert reader(claims_path) == expected


def test_duplicate_occurrences_keep_order_and_caller_interpretation(claims_path):
    rows = [
        {"claim_id": "same", "timestamp": "first", "extra": {"未知": [None, 2]}},
        {"claim_id": "other", "check_by": "2026-02-02", "horizon_unit": "sessions"},
        {"claim_id": "same", "timestamp": "last", "clock_market": "US"},
    ]
    claims_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    before = claims_path.read_bytes()
    for reader in READERS:
        actual = reader(claims_path)
        assert actual == rows
        assert next(row for row in actual if row["claim_id"] == "same") == rows[0]
        assert {row["claim_id"]: row for row in actual}["same"] == rows[-1]
    assert claims_path.read_bytes() == before


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r", "\u2028", "\x85"])
def test_raw_lines_preserve_whitespace_and_unicode(claims_path, separator):
    lines = ['  {"claim_id":"重复"}  ', "", "\tbad json\t", " null "]
    claims_path.write_bytes(separator.join(lines).encode("utf-8"))
    assert store.read_raw_lines(claims_path) == lines
    assert store.read_legacy_rows(claims_path) == q._read_jsonl(claims_path)
    assert q.load_claims(claims_path.parents[2]) == [{"claim_id": "重复"}, None]


@pytest.mark.parametrize("reader", READERS)
def test_missing_file_does_not_create_directories(tmp_path, reader):
    path = tmp_path / "data" / "qledger" / "claims.jsonl"
    assert reader(path) == []
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("reader", READERS)
def test_invalid_utf8_never_returns_decoded_prefix(claims_path, reader):
    claims_path.write_bytes(b'{"claim_id":"valid-prefix"}\n\xff')
    with pytest.raises(UnicodeDecodeError):
        reader(claims_path)


@pytest.mark.parametrize("reader", READERS)
def test_directory_is_not_empty_history(claims_path, reader):
    claims_path.mkdir()
    with pytest.raises(IsADirectoryError):
        reader(claims_path)


@pytest.mark.parametrize("reader", READERS)
def test_permission_failure_propagates(claims_path, reader, monkeypatch):
    claims_path.write_text('{"claim_id":"unreadable"}\n', encoding="utf-8")
    original = Path.read_text

    def denied(path, *args, **kwargs):
        if path == claims_path:
            raise PermissionError("synthetic denied read")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", denied)
        with pytest.raises(PermissionError, match="synthetic denied read"):
            reader(claims_path)


@pytest.mark.parametrize("reader", READERS)
def test_disappearing_file_propagates(claims_path, reader, monkeypatch):
    claims_path.write_text('{"claim_id":"present-at-check"}\n', encoding="utf-8")
    original = Path.read_text

    def disappeared(path, *args, **kwargs):
        if path == claims_path:
            path.unlink()
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", disappeared)
        with pytest.raises(FileNotFoundError):
            reader(claims_path)


def test_legacy_json_decoder_exceptions_remain_line_local(claims_path, monkeypatch):
    claims_path.write_text('{"claim_id":"before"}\nfault\nnull\n', encoding="utf-8")
    original = json.loads

    def decode(line, *args, **kwargs):
        if line == "fault":
            raise RecursionError("synthetic parser failure")
        return original(line, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(json, "loads", decode)
        for reader in READERS:
            assert reader(claims_path) == [{"claim_id": "before"}, None]


@pytest.mark.parametrize("root_kind", ["path", "string", "none", "empty"])
def test_public_root_resolution_is_unchanged(claims_path, monkeypatch, root_kind):
    root = claims_path.parents[2]
    monkeypatch.setattr(q.config, "ROOT", root)
    claims_path.write_text('{"claim_id":"rooted"}\n', encoding="utf-8")
    root_arg = {"path": root, "string": str(root), "none": None, "empty": ""}[root_kind]
    assert q.load_claims(root_arg) == [{"claim_id": "rooted"}]


@pytest.mark.parametrize("base_exists", [True, False])
def test_only_explicit_legacy_file_is_read_no_format_activation(
    claims_path, monkeypatch, base_exists
):
    if base_exists:
        claims_path.write_text('{"claim_id":"legacy"}\n', encoding="utf-8")
    catalog = claims_path.with_name("claims.parts.jsonl")
    catalog.write_text("synthetic invalid catalog\n", encoding="utf-8")
    parts = claims_path.parent / "claims.parts"
    parts.mkdir()
    (parts / "one.jsonl").write_text('{"claim_id":"unactivated"}\n', encoding="utf-8")
    before = {p.relative_to(claims_path.parent): p.read_bytes()
              for p in claims_path.parent.rglob("*") if p.is_file()}
    reads = []
    original = Path.read_text

    def observed(path, *args, **kwargs):
        reads.append(path)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", observed)
        assert q.load_claims(claims_path.parents[2]) == (
            [{"claim_id": "legacy"}] if base_exists else []
        )
    assert reads == ([claims_path] if base_exists else [])
    after = {p.relative_to(claims_path.parent): p.read_bytes()
             for p in claims_path.parent.rglob("*") if p.is_file()}
    assert after == before
