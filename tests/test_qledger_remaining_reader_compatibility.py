"""Synthetic legacy parity for the US placebo and registry claims seams."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from engine import qledger_store as store
from scripts import backfill_qledger_us as us
from scripts import build_intelligence_registry as registry


def _legacy_us(root):
    """Frozen incumbent reader body; independent of the storage seam."""
    claims_path = root / "data" / "qledger" / "claims.jsonl"
    if not claims_path.exists():
        return set()
    seen = set()
    for line in claims_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not obj.get("is_placebo"):
            continue
        real_src = obj.get("placebo_real_source_id") or (obj.get("extra") or {}).get(
            "placebo_real_source_id"
        )
        if real_src:
            seen.add(str(real_src))
    return seen


def _legacy_registry(text, source):
    """Frozen incumbent record policy; source selection stays caller-owned."""
    if text is None:
        return registry.QLedgerRead(None, None, source, 0, 0)
    rows = Counter()
    horizons = defaultdict(set)
    unparseable = 0
    considered = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        considered += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            unparseable += 1
            continue
        if not isinstance(record, dict):
            unparseable += 1
            continue
        desk = record.get("desk")
        if not desk:
            continue
        rows[desk] += 1
        horizon = record.get("horizon_d")
        if isinstance(horizon, int):
            horizons[desk].add(horizon)
    return registry.QLedgerRead(
        dict(rows), {k: sorted(v) for k, v in horizons.items()},
        source, unparseable, considered,
    )


def _outcome(call):
    try:
        return ("value", call())
    except Exception as exc:
        return ("error", type(exc), str(exc))


@pytest.fixture
def claims(tmp_path):
    path = tmp_path / "data" / "qledger" / "claims.jsonl"
    path.parent.mkdir(parents=True)
    return path


@pytest.mark.parametrize("payload", [
    "",
    "\n \nmalformed\n",
    '{"is_placebo":true,"placebo_real_source_id":"top"}\n'
    '{"is_placebo":true,"extra":{"placebo_real_source_id":"nested"}}\n'
    '{"is_placebo":true,"placebo_real_source_id":"top"}\n',
    '{"is_placebo":false,"placebo_real_source_id":"skip"}\n'
    '{"is_placebo":true,"placebo_real_source_id":7}\n'
    '{"is_placebo":true,"extra":null}\n',
    '{"is_placebo":true,"placebo_real_source_id":"a"}\u2028'
    '{"is_placebo":true,"placebo_real_source_id":"b"}\u0085',
    "null\n", "1\n", "[]\n", '"scalar"\n',
    '{"is_placebo":true,"extra":["bad-shape"]}\n',
])
def test_us_reader_matches_frozen_policy(claims, payload):
    claims.write_text(payload, encoding="utf-8")
    root = claims.parents[2]
    assert _outcome(lambda: us._thesis_ids_with_placebos(root)) == _outcome(
        lambda: _legacy_us(root))


def test_us_missing_does_not_enter_storage_seam(claims, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("missing legacy claims must return before the read")
    monkeypatch.setattr(store, "read_raw_lines", forbidden)
    assert us._thesis_ids_with_placebos(claims.parents[2]) == set()


def test_us_uses_one_strict_read_after_one_precheck(claims, monkeypatch):
    claims.write_text('{"is_placebo":true,"placebo_real_source_id":"x"}\n')
    calls = []
    exists_calls = []
    original_exists = Path.exists
    original_read = store.read_raw_lines
    def exists(path):
        if path == claims:
            exists_calls.append(path)
        return original_exists(path)
    def read(path, **kwargs):
        calls.append((path, kwargs))
        return original_read(path, **kwargs)
    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(store, "read_raw_lines", read)
    assert us._thesis_ids_with_placebos(claims.parents[2]) == {"x"}
    assert calls == [(claims, {"missing_ok": False})]
    assert exists_calls == [claims]


@pytest.mark.parametrize("mode", ["decode", "directory", "permission", "disappeared"])
def test_us_io_failure_is_not_empty_seen_set(claims, monkeypatch, mode):
    if mode == "directory":
        claims.mkdir()
    elif mode == "decode":
        claims.write_bytes(b"{}\n\xff")
    else:
        claims.write_text("{}\n")
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path == claims and mode == "permission":
            raise PermissionError("synthetic claims unreadable")
        if path == claims and mode == "disappeared":
            raise FileNotFoundError("synthetic claims disappeared")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    root = claims.parents[2]
    actual = _outcome(lambda: us._thesis_ids_with_placebos(root))
    assert actual == _outcome(lambda: _legacy_us(root))
    assert actual[0] == "error"


def test_us_unexpected_json_error_stays_line_local(claims, monkeypatch):
    claims.write_text('fault\n{"is_placebo":true,"placebo_real_source_id":"x"}\n')
    original = json.loads
    def loads(line, *args, **kwargs):
        if line == "fault":
            raise RecursionError("synthetic parser error")
        return original(line, *args, **kwargs)
    monkeypatch.setattr(json, "loads", loads)
    assert us._thesis_ids_with_placebos(claims.parents[2]) == _legacy_us(
        claims.parents[2]) == {"x"}


@pytest.mark.parametrize("source", ["worktree", "git", "absent"])
@pytest.mark.parametrize("text", [None, "", "\n# comment\n"])
def test_registry_preserves_source_and_null_vs_empty(tmp_path, monkeypatch, text, source):
    calls = []
    def reader(root, rel):
        calls.append((root, rel))
        return text, source
    monkeypatch.setattr(registry, "read_tracked", reader)
    assert registry._load_qledger(tmp_path) == _legacy_registry(text, source)
    assert calls == [(tmp_path, registry.CLAIMS_REL)]


@pytest.mark.parametrize("text", [
    '{"desk":"retail","horizon_d":5}\n{"desk":"retail","horizon_d":5}\n'
    '{"desk":"retail","horizon_d":20}\n{"desk":"tech","horizon_d":1}\n',
    "# comment\nnot-json\nnull\n[]\n1\ntrue\n{}\n",
    '{"desk":"x","horizon_d":true}\n{"desk":"x","horizon_d":1.5}\n'
    '{"desk":"x","horizon_d":"5"}\n{"desk":"","horizon_d":9}\n',
    '{"desk":"a","horizon_d":1}\u2028{"desk":"b","horizon_d":2}\u0085',
    '{"desk":["unhashable"]}\n',
])
def test_registry_parser_matches_frozen_policy(tmp_path, monkeypatch, text):
    monkeypatch.setattr(registry, "read_tracked", lambda *args: (text, "git"))
    assert _outcome(lambda: registry._load_qledger(tmp_path)) == _outcome(
        lambda: _legacy_registry(text, "git"))


def test_registry_unexpected_parser_error_propagates(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "read_tracked", lambda *args: ("fault\n", "git"))
    def bad(*args, **kwargs):
        raise RecursionError("synthetic registry parser failure")
    monkeypatch.setattr(json, "loads", bad)
    actual = _outcome(lambda: registry._load_qledger(tmp_path))
    assert actual == _outcome(lambda: _legacy_registry("fault\n", "git"))
    assert actual[0] == "error"


def test_tracked_seam_returns_original_tuple_without_extra_io(tmp_path, monkeypatch):
    rel = Path("data/qledger/claims.jsonl")
    expected = ("exact\r\nraw\u2028text", "git")
    calls = []
    def reader(root, relative_path):
        calls.append((root, relative_path))
        return expected
    def forbidden(*args, **kwargs):
        raise AssertionError("the seam must not discover, inspect, or open paths")
    monkeypatch.setattr(Path, "exists", forbidden)
    monkeypatch.setattr(Path, "is_file", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert store.read_tracked_claims_text(
        tmp_path, rel, legacy_reader=reader) is expected
    assert calls == [(tmp_path, rel)]


def test_tracked_seam_preserves_callback_exception_identity(tmp_path):
    failure = UnicodeError("synthetic incumbent decode error")
    def reader(*args):
        raise failure
    with pytest.raises(UnicodeError) as caught:
        store.read_tracked_claims_text(
            tmp_path, Path("data/qledger/claims.jsonl"), legacy_reader=reader)
    assert caught.value is failure


def test_registry_calls_claims_seam_with_incumbent_reader(tmp_path, monkeypatch):
    calls = []
    incumbent = registry.read_tracked
    def seam(root, relative_path, *, legacy_reader):
        calls.append((root, relative_path, legacy_reader))
        return '{"desk":"x","horizon_d":5}\n', "synthetic-explicit-source"
    monkeypatch.setattr(store, "read_tracked_claims_text", seam)
    result = registry._load_qledger(tmp_path)
    assert result.rows == {"x": 1}
    assert result.horizons == {"x": [5]}
    assert result.source == "synthetic-explicit-source"
    assert calls == [(tmp_path, registry.CLAIMS_REL, incumbent)]
