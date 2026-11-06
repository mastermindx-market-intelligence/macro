"""Synthetic parity for the eight claims-only legacy reader adapters.

These tests use temporary files only. Distinct incumbent parser policies are
intentional: eager splitlines, strict physical streaming, and line-local JSON
recovery are not interchangeable. No writer or market/provider input is used.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from engine import operator_grading as operator
from engine import qledger_falsifier as falsifier
from engine import qledger_store as store
from engine.metabolism import til_fitness as fitness
from engine.neuralweb import evidence_clock as clock
from engine.neuralweb import query
from scripts import audit_claim_accountability as accountability
from scripts import audit_grading_closure as closure
from scripts import check_qledger_metric_validity as metric


@pytest.fixture
def claims_path(tmp_path):
    path = tmp_path / "data" / "qledger" / "claims.jsonl"
    path.parent.mkdir(parents=True)
    return path


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")


def _error(call):
    try:
        call()
    except Exception as exc:
        return type(exc), str(exc)
    raise AssertionError("expected a failure")


def _legacy_forgiving(path):
    """Frozen incumbent falsifier parser, independent of the new seam."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _legacy_whole(path, *, encoding="utf-8"):
    """Frozen all-or-nothing eager policy shared by the audit readers."""
    try:
        lines = path.read_text(encoding=encoding).splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except Exception:
        return []


def _legacy_physical(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _call_stream_reader(reader, path):
    root = path.parents[2]
    if reader == "query":
        return query.adapt_qledger(root)
    if reader == "clock":
        return clock._adapt_qledger(root, {}, date(2026, 1, 12))
    return metric._read_jsonl(path, qledger_claims=True)


def _assert_stream_failure(reader, result, message):
    rows, gaps = result
    assert len(rows) == 0
    if reader == "query":
        assert gaps == [f"qledger: claims.jsonl read failed ({message}) — zero rows"]
    else:
        assert gaps == [f"qledger: could not load data/qledger/claims.jsonl: {message}"]


def test_strict_raw_read_does_not_check_existence_again(claims_path, monkeypatch):
    claims_path.write_text("  one\n\ntwo  ", encoding="utf-8")
    original = Path.exists

    def forbidden(path):
        if path == claims_path:
            raise AssertionError("strict read must not recheck")
        return original(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", forbidden)
        assert store.read_raw_lines(claims_path, missing_ok=False) == ["  one", "", "two  "]
        claims_path.unlink()
        assert _error(lambda: store.read_raw_lines(claims_path, missing_ok=False)) == _error(
            lambda: claims_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
def test_stream_is_real_physical_iterator_and_closes(claims_path, separator):
    text = '{"text":"left\u2028middle\u0085right"}' + separator + "null" + separator
    claims_path.write_bytes(text.encode("utf-8"))
    with claims_path.open(encoding="utf-8") as legacy:
        expected = list(legacy)
    with store.open_raw_lines(claims_path) as actual:
        assert iter(actual) is actual
        assert actual.closed is False
        assert list(actual) == expected
    assert actual.closed is True
    assert expected == ['{"text":"left\u2028middle\u0085right"}\n', "null\n"]


@pytest.mark.parametrize("mode", ["missing", "directory", "decode", "permission"])
def test_strict_stream_failure_matches_direct_open(claims_path, monkeypatch, mode):
    if mode == "directory":
        claims_path.mkdir()
    elif mode == "decode":
        claims_path.write_bytes(b'{}\n\xff')
    elif mode == "permission":
        claims_path.write_text("{}\n", encoding="utf-8")
    original = Path.open

    def opened(path, *args, **kwargs):
        if mode == "permission" and path == claims_path:
            raise PermissionError("synthetic read denied")
        return original(path, *args, **kwargs)

    def via_seam():
        with store.open_raw_lines(claims_path) as handle:
            return list(handle)

    def direct():
        with claims_path.open(encoding="utf-8") as handle:
            return list(handle)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opened)
        assert _error(via_seam) == _error(direct)


@pytest.mark.parametrize("payload, expected", [
    ("", []),
    ('null\ntrue\n0\n[1]\n{}\n', [None, True, 0, [1], {}]),
    ('{"claim_id":"same","v":1}\nbad\n{"claim_id":"same","v":2}\n',
     [{"claim_id": "same", "v": 1}, {"claim_id": "same", "v": 2}]),
    ('\ufeff{"bad":"BOM"}\n{"ok":"café"}\n{"truncated":', [{"ok": "café"}]),
    ('{"id":1}\u2028{"id":2}\u0085null', [{"id": 1}, {"id": 2}, None]),
])
def test_falsifier_preserves_forgiving_values(claims_path, payload, expected):
    claims_path.write_text(payload, encoding="utf-8")
    assert falsifier._read_jsonl(claims_path) == _legacy_forgiving(claims_path) == expected


def test_falsifier_unexpected_parser_error_stays_line_local(claims_path, monkeypatch):
    claims_path.write_text('{}\nfault\nnull\n', encoding="utf-8")
    original = json.loads

    def loads(line, *args, **kwargs):
        if line == "fault":
            raise RecursionError("synthetic parser failure")
        return original(line, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(json, "loads", loads)
        assert falsifier._read_jsonl(claims_path) == _legacy_forgiving(claims_path) == [{}, None]


@pytest.mark.parametrize("mode", ["decode", "directory", "permission"])
def test_falsifier_read_failure_never_becomes_empty_history(claims_path, monkeypatch, mode):
    if mode == "decode":
        claims_path.write_bytes(b'{}\n\xff')
    elif mode == "directory":
        claims_path.mkdir()
    else:
        claims_path.write_text("{}\n", encoding="utf-8")
    original = Path.read_text

    def read(path, *args, **kwargs):
        if mode == "permission" and path == claims_path:
            raise PermissionError("synthetic read denied")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", read)
        assert _error(lambda: falsifier._read_jsonl(claims_path)) == _error(
            lambda: _legacy_forgiving(claims_path))


@pytest.mark.parametrize("exists", [False, True])
def test_falsifier_empty_claims_never_reach_evaluation_or_writer(claims_path, monkeypatch, exists):
    if exists:
        claims_path.write_text("", encoding="utf-8")
    calls = []
    real = store.read_legacy_rows

    def observed(path):
        calls.append(path)
        return real(path)

    def forbidden(*args, **kwargs):
        raise AssertionError("empty claims must not reach evaluation or writers")

    monkeypatch.setattr(store, "read_legacy_rows", observed)
    for name in ("_load_evaluated_ids", "evaluate_check", "_ledger_advance_enabled"):
        monkeypatch.setattr(falsifier, name, forbidden)
    result = falsifier.evaluate_falsifiers(claims_path.parents[2], today="2026-01-12")
    assert calls == [claims_path]
    assert result["note"] == "Honest null — claims.jsonl absent or empty."
    assert not claims_path.with_name("falsifier_evaluations.jsonl").exists()


EAGER_CALLERS = ("operator", "accountability", "closure")


def _eager(reader, path):
    if reader == "operator":
        return operator._load_jsonl(path, qledger_claims=True)
    module = accountability if reader == "accountability" else closure
    return module._read_jsonl(path, qledger_claims=True)


@pytest.mark.parametrize("reader", EAGER_CALLERS)
@pytest.mark.parametrize("payload, expected", [
    ('{"id":1}\nbad\n{"id":2}\n', []),
    ('null\nfalse\n[2]\n{"id":1}\n{"id":1}\n', [None, False, [2], {"id": 1}, {"id": 1}]),
    ('{"id":1}\u2028{"id":2}', [{"id": 1}, {"id": 2}]),
    ('{"text":"left\u2028right"}\n', []),
])
def test_eager_caller_keeps_whole_input_policy(claims_path, reader, payload, expected):
    claims_path.write_text(payload, encoding="utf-8")
    assert _eager(reader, claims_path) == _legacy_whole(claims_path) == expected


@pytest.mark.parametrize("reader", EAGER_CALLERS)
@pytest.mark.parametrize("mode", ["missing", "empty", "directory", "decode", "permission", "parser"])
def test_eager_error_policy_and_operator_warning(claims_path, monkeypatch, caplog, reader, mode):
    if mode == "directory":
        claims_path.mkdir()
    elif mode == "decode":
        claims_path.write_bytes(b'{}\n\xff')
    elif mode not in ("missing",):
        claims_path.write_text("" if mode == "empty" else "{}\n", encoding="utf-8")
    read = Path.read_text
    loads = json.loads

    def maybe_read(path, *args, **kwargs):
        if mode == "permission" and path == claims_path:
            raise PermissionError("synthetic permission failure")
        return read(path, *args, **kwargs)

    def maybe_loads(line, *args, **kwargs):
        if mode == "parser":
            raise RuntimeError("synthetic parser failure")
        return loads(line, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", maybe_read)
        patch.setattr(json, "loads", maybe_loads)
        assert _eager(reader, claims_path) == []
    warnings = [r.getMessage() for r in caplog.records if r.name == "engine.operator_grading"]
    if reader == "operator" and mode not in ("missing", "empty"):
        assert len(warnings) == 1
        assert warnings[0].startswith(f"operator_grading: jsonl load failed {claims_path}: ")
    else:
        assert warnings == []


def test_operator_disappearing_file_warns_after_one_check(claims_path, monkeypatch, caplog):
    _write_rows(claims_path, [{"claim_id": "a"}])
    original = Path.exists
    checks = []

    def disappears(path):
        if path == claims_path:
            checks.append(path)
            path.unlink()
            return True
        return original(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", disappears)
        assert operator._load_claims(claims_path.parents[2]) == {}
    message = _error(lambda: claims_path.read_text(encoding="utf-8"))[1]
    assert checks == [claims_path]
    assert [r.getMessage() for r in caplog.records if r.name == "engine.operator_grading"] == [
        f"operator_grading: jsonl load failed {claims_path}: {message}"]


def test_operator_last_wins_and_non_claim_readers_stay_direct(claims_path, monkeypatch):
    rows = [{"claim_id": "a", "v": 1}, {"claim_id": "a", "v": 2}]
    _write_rows(claims_path, rows)
    grades = claims_path.with_name("grades.jsonl")
    actions = claims_path.with_name("synthetic_actions.jsonl")
    _write_rows(grades, [{"claim_id": "a", "horizon_d": 5}, {"claim_id": "a", "horizon_d": 21}])
    _write_rows(actions, [{"action_id": "one"}])
    real = store.read_raw_lines
    calls = []

    def observed(path, **kwargs):
        calls.append((path, kwargs))
        assert path == claims_path
        return real(path, **kwargs)

    monkeypatch.setattr(store, "read_raw_lines", observed)
    assert operator._load_claims(claims_path.parents[2]) == {"a": rows[-1]}
    assert len(operator._load_grades(claims_path.parents[2])["a"]) == 2
    assert operator._load_jsonl(actions) == [{"action_id": "one"}]
    assert calls == [(claims_path, {"missing_ok": False})]
    claims_path.write_text("null\n", encoding="utf-8")
    with pytest.raises(AttributeError):
        operator._load_claims(claims_path.parents[2])


def test_accountability_run_counts_occurrences_and_keeps_other_inputs_direct(claims_path, monkeypatch):
    rows = [{"claim_id": "a", "desk": "test", "claim_family": "test", "falsifier": "watch"}] * 2
    _write_rows(claims_path, rows)
    _write_rows(claims_path.with_name("grades.jsonl"), [{"claim_id": "a", "horizon_d": 5}])
    track = claims_path.parents[2] / "site" / "qledger" / "track_record.json"
    track.parent.mkdir(parents=True)
    track.write_text('{"generated_at":"2026-01-10","by_desk":{"test":{}}}', encoding="utf-8")
    real = store.read_raw_lines
    calls = []

    def observed(path, **kwargs):
        calls.append(path)
        assert path == claims_path
        return real(path, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("read-only audit must not write")

    monkeypatch.setattr(store, "read_raw_lines", observed)
    monkeypatch.setattr(accountability, "_write_json", forbidden)
    monkeypatch.setattr(accountability, "_write_md", forbidden)
    result = accountability.run(claims_path.parents[2], write=False)
    assert result["global"]["n_claims"] == 2
    assert result["global"]["n_grades"] == 1
    assert result["track_record_ref"]["generated_at"] == "2026-01-10"
    assert calls == [claims_path]
    claims_path.write_text('null\n', encoding="utf-8")
    with pytest.raises(AttributeError):
        accountability.run(claims_path.parents[2], write=False)


def test_fitness_counts_duplicate_claims_but_dedupes_evaluations(claims_path, monkeypatch):
    claim = {"claim_id": "a", "falsifier": "watch", "check_by": "2026-01-10"}
    _write_rows(claims_path, [claim, claim, {**claim, "claim_id": "b"}, None, {}])
    with claims_path.open("a", encoding="utf-8") as handle:
        handle.write("bad\n")
    evaluations = claims_path.with_name("falsifier_evaluations.jsonl")
    _write_rows(evaluations, [{"claim_id": "a", "outcome": "CONFIRMED"}] * 2)
    real = store.read_raw_lines
    calls = []

    def observed(path, **kwargs):
        calls.append((path, kwargs))
        assert path == claims_path
        return real(path, **kwargs)

    monkeypatch.setattr(store, "read_raw_lines", observed)
    result = fitness._read_live_leg_quality(claims_path.parents[2])
    assert result["n"] == 3
    assert result["n_quality_legs"] == 2
    assert calls == [(claims_path, {"missing_ok": False})]


@pytest.mark.parametrize("mode", ["disappears", "decode"])
def test_fitness_read_errors_are_not_ordinary_zero_coverage(claims_path, monkeypatch, mode):
    _write_rows(claims_path, [{"claim_id": "a"}])
    evaluations = claims_path.with_name("falsifier_evaluations.jsonl")
    evaluations.write_text("", encoding="utf-8")
    if mode == "decode":
        claims_path.write_bytes(b'{}\n\xff')
    real = Path.read_text

    def read(path, *args, **kwargs):
        value = real(path, *args, **kwargs)
        if mode == "disappears" and path == evaluations:
            claims_path.unlink()
        return value

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", read)
        result = fitness._read_live_leg_quality(claims_path.parents[2])
    assert result["value"] is None
    assert result["n"] == 0
    assert "n_quality_legs" not in result
    assert result["note"].startswith("read error: ")
    assert result["source"] == str(claims_path)


@pytest.mark.parametrize("separator", ["\u2028", "\u0085"])
@pytest.mark.parametrize("reader", ["query", "clock", "metric"])
def test_physical_readers_preserve_unicode_inside_strings(claims_path, reader, separator):
    row = {"claim_id": "a", "desk": "left" + separator + "right", "status": "open"}
    _write_rows(claims_path, [row])
    if reader == "metric":
        assert _call_stream_reader(reader, claims_path) == [row]
    elif reader == "query":
        frame, gaps = _call_stream_reader(reader, claims_path)
        assert len(frame) == 1
        assert frame.iloc[0]["engine"] == row["desk"]
        assert gaps == ["qledger: data/qledger/grades.jsonl absent — outcomes will be null"]
    else:
        rows, gaps = _call_stream_reader(reader, claims_path)
        assert gaps == []
        assert next(r for r in rows if r["clock_id"].startswith("qledger:left"))["subject_id"] == row["desk"]


@pytest.mark.parametrize("separator", ["\u2028", "\u0085"])
@pytest.mark.parametrize("reader", ["query", "clock", "metric"])
def test_physical_readers_do_not_split_unicode_between_records(claims_path, reader, separator):
    claims_path.write_text('{"claim_id":"a"}' + separator + '{"claim_id":"b"}\n', encoding="utf-8")
    expected = _error(lambda: _legacy_physical(claims_path))[1]
    result = _call_stream_reader(reader, claims_path)
    if reader == "metric":
        assert result == []  # one malformed physical line, not two accepted rows
    else:
        _assert_stream_failure(reader, result, expected)


@pytest.mark.parametrize("reader", ["query", "clock"])
@pytest.mark.parametrize("payload", [b'{"unfinished":\n', b'{}\n\xff'])
def test_neuralweb_gap_text_preserves_direct_failure(claims_path, reader, payload):
    claims_path.write_bytes(payload)
    expected = _error(lambda: _legacy_physical(claims_path))[1]
    _assert_stream_failure(reader, _call_stream_reader(reader, claims_path), expected)


def test_neuralweb_missing_and_empty_are_distinct(claims_path):
    frame, gaps = query.adapt_qledger(claims_path.parents[2])
    assert frame.empty
    assert gaps == ["qledger: data/qledger/claims.jsonl absent — zero rows"]
    missing_error = _error(lambda: _legacy_physical(claims_path))[1]
    _assert_stream_failure("clock", _call_stream_reader("clock", claims_path), missing_error)
    claims_path.write_text("", encoding="utf-8")
    rows, gaps = _call_stream_reader("clock", claims_path)
    assert gaps == []
    assert len(rows) == 1
    assert rows[0]["clock_id"] == "qledger:falsifier_coverage"
    assert rows[0]["readiness"]["n_claims"] == 0


def test_query_disappearance_after_precheck_retains_read_failed_gap(claims_path, monkeypatch):
    claims_path.write_text("{}\n", encoding="utf-8")
    real = Path.exists
    checks = []

    def disappears(path):
        if path == claims_path:
            checks.append(path)
            path.unlink()
            return True
        return real(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", disappears)
        result = query.adapt_qledger(claims_path.parents[2])
    assert checks == [claims_path]
    _assert_stream_failure("query", result, _error(lambda: _legacy_physical(claims_path))[1])


class _ControlledStream:
    """No prefetch: later read failures must not supersede earlier parse errors."""
    def __init__(self, first):
        self.first = first
        self.reads = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def __iter__(self):
        return self

    def __next__(self):
        self.reads += 1
        if self.reads == 1:
            return self.first
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "synthetic late decode")

    def read(self, *args):
        raise AssertionError("must not replace physical iteration with eager read")


@pytest.mark.parametrize("reader", ["query", "clock"])
def test_first_json_error_wins_and_stream_closes(claims_path, monkeypatch, reader):
    claims_path.write_text("", encoding="utf-8")
    stream = _ControlledStream('{"unfinished":\n')
    real = Path.open

    def opened(path, *args, **kwargs):
        return stream if path == claims_path else real(path, *args, **kwargs)

    expected = _error(lambda: json.loads(stream.first))[1]
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opened)
        result = _call_stream_reader(reader, claims_path)
    _assert_stream_failure(reader, result, expected)
    assert stream.reads == 1
    assert stream.closed is True


@pytest.mark.parametrize("reader", ["query", "clock", "metric"])
def test_unexpected_parser_error_closes_without_reading_suffix(claims_path, monkeypatch, reader):
    claims_path.write_text("", encoding="utf-8")
    stream = _ControlledStream("fault\n")
    real_open = Path.open
    real_loads = json.loads

    def opened(path, *args, **kwargs):
        return stream if path == claims_path else real_open(path, *args, **kwargs)

    def loads(line, *args, **kwargs):
        if line.strip() == "fault":
            raise RuntimeError("synthetic unexpected parser error")
        return real_loads(line, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opened)
        patch.setattr(json, "loads", loads)
        if reader == "metric":
            with pytest.raises(RuntimeError, match="synthetic unexpected parser error"):
                _call_stream_reader(reader, claims_path)
        else:
            _assert_stream_failure(reader, _call_stream_reader(reader, claims_path),
                                   "synthetic unexpected parser error")
    assert stream.reads == 1
    assert stream.closed is True


def test_query_grade_join_and_clock_rollup_keep_occurrences(claims_path, monkeypatch):
    claim = {"claim_id": "a", "desk": "test", "status": "open", "falsifier": "watch",
             "check_by": "2026-01-10", "asof": "2026-01-01"}
    _write_rows(claims_path, [claim, claim])
    _write_rows(claims_path.with_name("grades.jsonl"), [
        {"claim_id": "a", "horizon_d": 5, "hit": True, "excess": 0.1},
        {"claim_id": "a", "horizon_d": 21, "hit": False, "excess": -0.1},
    ])
    real = store.open_raw_lines
    calls = []

    def observed(path, **kwargs):
        calls.append(path)
        assert path == claims_path
        return real(path, **kwargs)

    monkeypatch.setattr(store, "open_raw_lines", observed)
    frame, gaps = query.adapt_qledger(claims_path.parents[2])
    assert gaps == []
    assert len(frame) == 4
    assert list(frame["signal_id"]) == ["qledger:a:5", "qledger:a:21"] * 2
    rows, gaps = _call_stream_reader("clock", claims_path)
    assert gaps == []
    desk = next(row for row in rows if row["clock_id"] == "qledger:test")
    assert desk["readiness"] == {"n_open": 2, "n_past_check_by": 2}
    assert calls == [claims_path, claims_path]
    claims_path.write_text("null\n", encoding="utf-8")
    for reader in ("query", "clock"):
        with pytest.raises(AttributeError):
            _call_stream_reader(reader, claims_path)


def test_metric_comments_narrow_catch_and_scalar_rows(claims_path):
    claims_path.write_text(' # schema\n\n{"id":1}\nbad\nnull\n# trailing\n', encoding="utf-8")
    assert metric._read_jsonl(claims_path, qledger_claims=True) == [{"id": 1}, None]


def test_metric_json_recovery_still_exposes_later_decode_failure(claims_path, monkeypatch):
    stream = _ControlledStream("bad\n")
    real = Path.open

    def opened(path, *args, **kwargs):
        return stream if path == claims_path else real(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opened)
        with pytest.raises(UnicodeDecodeError, match="synthetic late decode"):
            metric._read_jsonl(claims_path, qledger_claims=True)
    assert stream.reads == 2
    assert stream.closed is True


def test_metric_missing_cli_disclosure_and_claims_only_wiring(claims_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_qledger_metric_validity", "--root", str(claims_path.parents[2]), "--json"])
    assert metric.main() == 0
    missing = json.loads(capsys.readouterr().out)
    assert missing["store_absent"] is True
    assert missing["findings"] is None
    _write_rows(claims_path, [{"claim_id": "a"}])
    _write_rows(claims_path.with_name("grades.jsonl"), [{"claim_id": "a", "horizon_d": 5}])
    real = store.open_raw_lines
    calls = []
    audited = []

    def observed(path, **kwargs):
        calls.append(path)
        assert path == claims_path
        return real(path, **kwargs)

    def audit(claims, grades):
        audited.append((claims, grades))
        return []

    monkeypatch.setattr(store, "open_raw_lines", observed)
    monkeypatch.setattr(metric, "audit", audit)
    assert metric.main() == 0
    assert json.loads(capsys.readouterr().out)["store_absent"] is False
    assert calls == [claims_path]
    assert audited == [([{"claim_id": "a"}], [{"claim_id": "a", "horizon_d": 5}])]


def test_metric_disappearing_after_precheck_propagates(claims_path, monkeypatch, capsys):
    _write_rows(claims_path, [{"claim_id": "a"}])
    claims_path.with_name("grades.jsonl").write_text("", encoding="utf-8")
    real = Path.exists
    checks = []

    def disappeared(path):
        if path == claims_path:
            checks.append(path)
            path.unlink()
            return True
        return real(path)

    monkeypatch.setattr(sys, "argv", ["check_qledger_metric_validity", "--root", str(claims_path.parents[2]), "--json"])
    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", disappeared)
        with pytest.raises(FileNotFoundError):
            metric.main()
    assert checks == [claims_path]
    assert capsys.readouterr().out == ""


def test_closure_retains_default_encoding_without_changing_host_locale(claims_path, monkeypatch):
    claims_path.write_bytes(b'{"claim_id":"caf\xe9"}\n')
    original = Path.read_text
    encodings = []

    def platform_read(path, *args, **kwargs):
        if path == claims_path:
            encoding = kwargs.get("encoding")
            encodings.append(encoding)
            # Simulate the incumbent platform default; no process locale change.
            return path.read_bytes().decode("cp1252" if encoding is None else encoding)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", platform_read)
        expected = closure._read_jsonl(claims_path)
        assert closure._read_jsonl(claims_path, qledger_claims=True) == expected == [{"claim_id": "café"}]
    assert encodings == [None, None]


def test_closure_canonical_claims_only_inventory_and_separate_grade_count(claims_path, monkeypatch):
    _write_rows(claims_path, [{"claim_id": "a"}] * 2)
    _write_rows(claims_path.with_name("grades.jsonl"), [
        {"claim_id": "a", "graded_at": "2026-01-09"},
        {"claim_id": "a", "graded_at": "2026-01-10"},
    ])
    spec = next(s for s in closure.INVENTORY if s["key"] == "qledger_claims")
    real = store.read_raw_lines
    calls = []

    def observed(path, **kwargs):
        calls.append((path, kwargs))
        assert path == claims_path
        return real(path, **kwargs)

    monkeypatch.setattr(store, "read_raw_lines", observed)
    result = closure.audit_entry(spec, claims_path.parents[2])
    assert result["storage"] == "present"
    assert (result["n_logged"], result["n_graded"], result["last_graded_at"]) == (2, 2, "2026-01-10")
    other = claims_path.with_name("other.jsonl")
    _write_rows(other, [{"graded": True}])
    other_spec = {"key": "other", "path": str(other.relative_to(claims_path.parents[2])), "format": "jsonl", "graders": [], "grade_field": "graded"}
    assert closure.audit_entry(other_spec, claims_path.parents[2])["n_logged"] == 1
    directory = claims_path.parent / "other_parts"
    directory.mkdir()
    _write_rows(directory / "one.jsonl", [{"graded": True}])
    directory_spec = {**other_spec, "format": "parquet_dir", "path": str(directory.relative_to(claims_path.parents[2]))}
    assert closure.audit_entry(directory_spec, claims_path.parents[2])["n_logged"] == 1
    assert calls == [(claims_path, {"missing_ok": False, "encoding": None})]


def test_closure_physical_absence_and_disappearance_keep_storage_semantics(claims_path, monkeypatch):
    spec = next(s for s in closure.INVENTORY if s["key"] == "qledger_claims")
    absent = closure.audit_entry(spec, claims_path.parents[2])
    assert absent["storage"] == "absent-locally"
    assert absent["n_logged"] == 0
    _write_rows(claims_path, [{"claim_id": "a"}])
    _write_rows(claims_path.with_name("grades.jsonl"), [{"claim_id": "a", "graded_at": "2026-01-10"}])
    real = Path.is_file

    def disappeared(path):
        if path == claims_path:
            path.unlink()
            return True
        return real(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "is_file", disappeared)
        result = closure.audit_entry(spec, claims_path.parents[2])
    assert result["storage"] == "present"
    assert result["n_logged"] == 0
    assert result["n_graded"] == 1
    assert result["last_graded_at"] == "2026-01-10"


@pytest.mark.parametrize("invocation", [
    ["-m", "scripts.audit_claim_accountability", "--check"],
    ["-m", "scripts.audit_grading_closure", "--check"],
    ["scripts/check_qledger_metric_validity.py"],
])
def test_documented_cli_import_paths_use_only_synthetic_root(claims_path, invocation):
    _write_rows(claims_path, [{"claim_id": "synthetic-cli", "desk": "test"}])
    _write_rows(claims_path.with_name("grades.jsonl"), [])
    root = claims_path.parents[2]
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    completed = subprocess.run(
        [sys.executable, *invocation, "--root", str(root), "--json"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    if "accountability" in " ".join(invocation):
        assert payload["global"]["n_claims"] == 1
    elif "closure" in " ".join(invocation):
        row = next(r for r in payload["ledgers"] if r["key"] == "qledger_claims")
        assert row["n_logged"] == 1
    else:
        assert payload["store_absent"] is False
        assert payload["claims"] == 1
    after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
