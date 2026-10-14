"""M6H smoke tests for the owned site range in residual/run_s1.py and
residual/s1_data.py.

SNI-local DRAFT contract tests. They consume caller-supplied opaque identity
strings owned by Stock Identity / Data OS; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation, or
trade path. Authority flags stay false. Fixtures are synthetic.

This file carries the M6H lane's regression smoke for the owned site range
(`run_s1._tree_equal`, `run_s1._byte_compare`, `run_s1.main`,
`s1_data.InjectableStore.read_columns`).

The 2026-10-14 M6H mutation sweep at seed `20261014` (cap 15 run_s1 by the
slow-suite rule, 1 candidate in the s1_data owned range) sampled 16 mutants
across the four owned functions; every one was KILLED by the existing
importer suite. No non-equivalent SURVIVED mutant was found at this seed
and cap, so the lane's "honest statement that fewer survivors existed"
path applies and this file holds the regression smoke only — no
`test_m6h_*_<n>` killing tests are added.

A regression smoke that runs against UNMUTATED code and pins the
expected behaviour of the owned functions is included so the lane's
required `python3 -m pytest tests/test_sni_mut6_run_s1_cli.py -q` exits 0
even when the file carries no new killing tests.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO))

import run_s1  # noqa: E402
from s1_data import InjectableStore, _to_date  # noqa: E402


def test_m6h_smoke_run_s1_tree_equal_equal_directories():
    """Regression smoke: equal directories compare equal under `_tree_equal`."""
    a = REPO / "research" / "single_name_intelligence" / "residual"
    b = REPO / "research" / "single_name_intelligence" / "residual"
    assert run_s1._tree_equal(a, b) is True


def test_m6h_smoke_run_s1_tree_equal_detects_extra_file(tmp_path):
    """Regression smoke: an extra file under one side makes `_tree_equal` False."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "f.txt").write_text("same", encoding="utf-8")
    (b / "f.txt").write_text("same", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is True
    (b / "extra.txt").write_text("extra", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is False


def test_m6h_smoke_run_s1_byte_compare_runs_over_laid_out_trees(tmp_path):
    """Regression smoke: `_byte_compare` returns True when REPORT.md, manifest,
    results/, observations/, and the ledger (after dropping `ts`) are all
    byte-equal between the two trees."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    assert run_s1._byte_compare(a, b) is True


def test_m6h_smoke_run_s1_byte_compare_detects_report_drift(tmp_path):
    """Regression smoke: differing REPORT.md makes `_byte_compare` False."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    (b / "REPORT.md").write_text("drift\n", encoding="utf-8")
    assert run_s1._byte_compare(a, b) is False


def test_m6h_smoke_run_s1_ledger_equal_ignores_ts_wallclock(tmp_path):
    """Regression smoke: `_ledger_equal` ignores the wall-clock `ts` field."""
    p = tmp_path / "a.jsonl"
    q = tmp_path / "b.jsonl"
    p.write_text('{"k":1,"ts":"wall-a"}\n{"k":2}\n', encoding="utf-8")
    q.write_text('{"k":1,"ts":"wall-b"}\n{"k":2}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, q) is True
    r = tmp_path / "c.jsonl"
    r.write_text('{"k":9}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, r) is False


def test_m6h_smoke_run_s1_main_refuses_ledger_under_data(tmp_path):
    """Regression smoke: a `--trial-ledger-path` under `<repo>/data/` is REFUSED."""
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", "data/trial_ledger.jsonl"],
        store=object(),
    )
    assert rc == 2


def test_m6h_smoke_s1_data_InjectableStore_read_columns_returns_raw_lists():
    """Regression smoke: `InjectableStore.read_columns` returns the stored
    lists (NOT the float-coerced lists `frame()` produces)."""
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "vol": [3], "close": [1.5]},
    })
    got = store.read_columns("p", ["vol", "close"])
    assert got == {"vol": [3], "close": [1.5]}


def test_m6h_smoke_s1_data_InjectableStore_read_columns_records_access():
    """Regression smoke: the access_log captures the call (path, columns)."""
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "vol": [3]},
    })
    store.read_columns("p", ["vol"])
    assert store.access_log[-1] == ("read_columns", "p", ("vol",))


def test_m6h_smoke_s1_data_to_date_handles_datetime_and_date():
    """Regression smoke: `_to_date` accepts `datetime` and `date`, refuses
    unrelated types."""
    assert _to_date(datetime(2020, 1, 2, 15, 30, tzinfo=timezone.utc)) == date(2020, 1, 2)
    assert _to_date(date(2020, 1, 2)) == date(2020, 1, 2)
    try:
        _to_date("2020-01-02")
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError expected for string input to _to_date")


def test_m6h_smoke_s1_data_InjectableStore_commit_date_iso_is_1970():
    """Regression smoke: the synthetic BASE commit date is the deterministic 1970 stamp."""
    store = InjectableStore({})
    assert store.commit_date_iso() == "1970-01-01T00:00:00+00:00"
