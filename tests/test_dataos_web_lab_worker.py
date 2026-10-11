"""Synthetic regression boundaries for the dedicated web Lab worker.

No production dataset or network is used. The irreversible process audit hook
runs only in a short child process; the parent pytest process is not constrained.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lib.dataos import web_lab_worker as worker
from lib.dataos.web_workspace import WorkspaceError

_REF_A = "fixture:stocks/A.parquet"
_REF_B = "fixture:stocks/B.parquet"
_VERSION = "statv1:" + "a" * 64
_CHANGED_VERSION = "statv1:" + "b" * 64


def _execution(refs=None, **overrides):
    request = {
        "request": {
            "signal_id": "golden_cross_7_35",
            "refs": refs or [_REF_A],
            "horizon_bars": 21,
            "cost_bps": 5.0,
            "n_configs_searched": 1,
        },
        "time_column": "stored_time",
        "bar_frequency": "daily",
        "column_map": {"close": "close_tradj", "volume": "stored_volume"},
        "expected_versions": {},
    }
    request.update(overrides)
    return request


def _rows(*times):
    return [
        {"stored_time": value, "close_tradj": str(100 + i), "stored_volume": "10"}
        for i, value in enumerate(times)
    ]


def _page(rows, *, next_offset=None, scanned=None, version=_VERSION):
    return {
        "source": {"file_version": version, "evidence_kind": "research_sample"},
        "result": {
            "rows": rows,
            "scanned_rows": len(rows) if scanned is None else scanned,
            "next_offset": next_offset,
        },
    }


class _Workspace:
    """A deterministic source-page seam that enforces selected versions."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def read(self, **request):
        self.calls.append(request)
        page = copy.deepcopy(self.pages[request["ref"]][request["offset"]])
        selected = request["expected_version"]
        if selected is not None and selected != page["source"]["file_version"]:
            raise WorkspaceError("SOURCE_VERSION_MISMATCH")
        page["source"]["ref"] = request["ref"]
        return page


def _materialize_rows(rows, **execution):
    source = _Workspace({_REF_A: {0: _page(rows)}})
    return worker._materialize(source, _execution(**execution))


def _refused(source, execution, code):
    with pytest.raises(WorkspaceError) as caught:
        worker._materialize(source, execution)
    assert caught.value.code == code
    assert str(caught.value) == code


@pytest.mark.parametrize("value", [
    1700000000, 1700000000.5, True, None,
    "10/11/2026", "20261011", "2026-10-11 12:00:00", "2026-10-11T12:00",
])
def test_materialization_never_guesses_an_epoch_or_ambiguous_date(value):
    source = _Workspace({_REF_A: {0: _page(_rows(value))}})
    _refused(source, _execution(), "LAB_TIME_COLUMN_REQUIRES_ISO_DATES")


@pytest.mark.parametrize("times", [
    ("2026-10-10", "2026-10-11T00:00:00"),
    ("2026-10-10T00:00:00Z", "2026-10-11T00:00:00"),
])
def test_materialization_refuses_mixed_clock_precision_or_awareness(times):
    source = _Workspace({_REF_A: {0: _page(_rows(*times))}})
    _refused(source, _execution(), "LAB_MIXED_TIME_ENCODING")


def test_materialization_rejects_invalid_iso_calendar_dates():
    source = _Workspace({_REF_A: {0: _page(_rows("2026-02-30"))}})
    _refused(source, _execution(), "LAB_INVALID_DATE_INDEX")


@pytest.mark.parametrize("times,first", [
    (("2026-10-10", "2026-10-11"), "2026-10-10T00:00:00"),
    (("2026-10-10T12:00:00", "2026-10-11T12:00:00"), "2026-10-10T12:00:00"),
    (("2026-10-10T12:00:00Z", "2026-10-11T12:00:00Z"), "2026-10-10T12:00:00+00:00"),
    (("2026-10-10T12:00:00+05:30", "2026-10-11T12:00:00+05:30"),
     "2026-10-10T12:00:00+05:30"),
])
def test_explicit_iso_clocks_and_column_mapping_are_preserved(times, first):
    universe, sources = _materialize_rows(_rows(*times))
    frame = universe[_REF_A]
    assert list(frame.columns) == ["close", "volume"]
    assert frame["close"].tolist() == [100, 101]
    assert frame["volume"].tolist() == [10, 10]
    assert frame.index.name == "stored_time"
    assert frame.index[0].isoformat() == first
    assert sources[0]["first_stored_time"] == first
    assert sources[0]["loaded_rows"] == 2
    assert sources[0]["file_version"] == _VERSION
    assert sources[0]["column_map"] == {"close": "close_tradj", "volume": "stored_volume"}


@pytest.mark.parametrize("times", [
    ("2026-10-10", "2026-10-10"),
    ("2026-10-11", "2026-10-10"),
])
def test_duplicate_and_descending_clocks_cannot_enter_the_lab(times):
    source = _Workspace({_REF_A: {0: _page(_rows(*times))}})
    _refused(source, _execution(), "LAB_DATE_INDEX_MUST_BE_UNIQUE_AND_ASCENDING")


@pytest.mark.parametrize("times", [
    ("2026-10-10T09:30:00", "2026-10-10T09:31:00"),
    # These span two UTC dates but belong to one stored calendar date.
    ("2026-10-10T00:30:00+14:00", "2026-10-10T23:30:00+14:00"),
])
def test_multiple_intraday_bars_on_one_stored_date_are_refused(times):
    source = _Workspace({_REF_A: {0: _page(_rows(*times))}})
    _refused(source, _execution(), "LAB_DAILY_BARS_REQUIRED")


@pytest.mark.parametrize("times", [
    ("2026-10-09T16:00:00Z", "2026-10-12T16:00:00Z"),
    # Distinct stored dates remain daily even when their UTC date is the same.
    ("2026-10-10T23:30:00+14:00", "2026-10-11T00:30:00+14:00"),
])
def test_one_timestamp_per_stored_date_is_accepted_as_declared_daily(times):
    universe, sources = _materialize_rows(_rows(*times))
    assert len(universe[_REF_A]) == 2
    assert [value.isoformat() for value in universe[_REF_A].index.date] == [
        value[:10] for value in times
    ]
    assert sources[0]["loaded_rows"] == 2


@pytest.mark.parametrize("initial_version", [None, _VERSION])
def test_selected_version_and_source_row_offset_are_used_on_continuation(initial_version):
    source = _Workspace({_REF_A: {
        0: _page([], next_offset=200, scanned=200),
        200: _page(_rows("2026-10-10"), next_offset=400, scanned=200),
        400: _page(_rows("2026-10-11"), scanned=12),
    }})
    versions = {} if initial_version is None else {_REF_A: initial_version}
    universe, sources = worker._materialize(source, _execution(expected_versions=versions))
    assert [call["offset"] for call in source.calls] == [0, 200, 400]
    assert [call["expected_version"] for call in source.calls] == [
        initial_version, _VERSION, _VERSION,
    ]
    assert all(call["columns"] == ["stored_time", "close_tradj", "stored_volume"]
               and call["limit"] == 200 for call in source.calls)
    assert len(universe[_REF_A]) == 2
    assert sources[0]["scanned_rows"] == 412


def test_changed_file_between_pages_fails_instead_of_combining_versions():
    source = _Workspace({_REF_A: {
        0: _page(_rows("2026-10-10"), next_offset=1),
        1: _page(_rows("2026-10-11"), version=_CHANGED_VERSION),
    }})
    _refused(source, _execution(), "SOURCE_VERSION_MISMATCH")
    assert len(source.calls) == 2
    assert source.calls[1]["expected_version"] == _VERSION


def test_caller_selected_version_is_required_on_the_first_page():
    source = _Workspace({_REF_A: {0: _page(_rows("2026-10-10"))}})
    _refused(source, _execution(expected_versions={_REF_A: _CHANGED_VERSION}),
             "SOURCE_VERSION_MISMATCH")
    assert len(source.calls) == 1


def test_materialization_checks_per_source_row_limit(monkeypatch):
    monkeypatch.setattr(worker, "MAX_ROWS_PER_REF", 1)
    source = _Workspace({_REF_A: {0: _page(_rows("2026-10-10", "2026-10-11"))}})
    _refused(source, _execution(), "LAB_INPUT_TOO_LARGE_NARROW_DATE_RANGE")


def test_materialization_checks_total_rows_across_sources(monkeypatch):
    monkeypatch.setattr(worker, "MAX_TOTAL_ROWS", 3)
    source = _Workspace({
        ref: {0: _page(_rows("2026-10-10", "2026-10-11"))}
        for ref in (_REF_A, _REF_B)
    })
    _refused(source, _execution([_REF_A, _REF_B]), "LAB_INPUT_TOO_LARGE_NARROW_DATE_RANGE")


def test_materialization_checks_scanned_rows_even_when_no_row_matches(monkeypatch):
    monkeypatch.setattr(worker, "MAX_SCANNED_PER_REF", 2)
    source = _Workspace({_REF_A: {0: _page([], scanned=3, next_offset=3)}})
    _refused(source, _execution(), "LAB_SCAN_TOO_LARGE_USE_EXISTING_BATCH_OWNER")
    assert len(source.calls) == 1


def test_materialization_accepts_exact_row_and_scan_limits(monkeypatch):
    monkeypatch.setattr(worker, "MAX_ROWS_PER_REF", 2)
    monkeypatch.setattr(worker, "MAX_TOTAL_ROWS", 2)
    monkeypatch.setattr(worker, "MAX_SCANNED_PER_REF", 2)
    universe, _ = _materialize_rows(_rows("2026-10-10", "2026-10-11"))
    assert len(universe[_REF_A]) == 2


def test_materialization_refuses_nonadvancing_page_cursor():
    source = _Workspace({_REF_A: {0: _page(_rows("2026-10-10"), next_offset=0)}})
    _refused(source, _execution(), "INVALID_READER_CONTINUATION")
    assert len(source.calls) == 1


def test_materialization_distinguishes_no_matching_rows():
    source = _Workspace({_REF_A: {0: _page([])}})
    _refused(source, _execution(), "LAB_SOURCE_HAS_NO_MATCHING_ROWS")


def test_side_effect_guard_is_confined_to_child_process_and_its_run(tmp_path):
    run_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    run_dir.mkdir()
    outside.mkdir()
    (outside / "existing.txt").write_text("keep", encoding="utf-8")
    (outside / ".env").write_text("synthetic-private-canary", encoding="utf-8")
    code = """
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, sys.argv[1])
from lib.dataos.web_lab_worker import _side_effect_guard
run_dir, outside = Path(sys.argv[2]), Path(sys.argv[3])
_side_effect_guard(run_dir)
(run_dir / "allowed.json").write_text("{}", encoding="utf-8")
blocked = []
operations = (
    ("write", lambda: (outside / "escaped.txt").write_text("forbidden")),
    ("remove", lambda: (outside / "existing.txt").unlink()),
    ("private_read", lambda: (outside / ".env").read_text()),
    ("network", lambda: sys.audit("socket.connect", None, ("127.0.0.1", 9))),
    ("spawn", lambda: subprocess.run([sys.executable, "-c", "raise SystemExit(99)"],
                                     check=False)),
)
for name, operation in operations:
    try:
        operation()
    except PermissionError:
        blocked.append(name)
    else:
        raise AssertionError(name + " was not refused")
print(json.dumps(blocked))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(Path(__file__).resolve().parents[1]),
         str(run_dir), str(outside)],
        cwd=run_dir, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True, capture_output=True, timeout=10, check=True,
    )
    assert json.loads(result.stdout) == ["write", "remove", "private_read", "network", "spawn"]
    assert (run_dir / "allowed.json").read_text() == "{}"
    assert not (outside / "escaped.txt").exists()
    assert (outside / "existing.txt").read_text() == "keep"
    # Child audit policy did not contaminate the parent pytest process.
    (outside / "parent-check.txt").write_text("parent unaffected", encoding="utf-8")
