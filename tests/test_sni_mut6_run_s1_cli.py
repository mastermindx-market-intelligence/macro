"""M6H killing tests for residual/run_s1.py (`_byte_compare`, `_tree_equal`,
`main`) and residual/s1_data.InjectableStore.read_columns.

SNI-local DRAFT contract tests. They consume caller-supplied opaque identity
strings owned by Stock Identity / Data OS; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation, or
trade path. Authority flags stay false. Fixtures are synthetic.

The 2026-10-14 M6H mutation sweep at seed `20261014` (cap 15 run_s1 by the
slow-suite rule, 1 candidate in the s1_data owned range) sampled 16 mutants
across the four owned functions. 3 were KILLED by the existing importer suite
(1 s1_data + 2 run_s1); 13 were non-equivalent SURVIVORS and this file
provides one targeted killing test for each, named
`test_m6h_<module>_<function>_<n>` per the lane spec. Each docstring names
the surviving mutant (file:line, original -> mutated).
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


# --------------------------------------------------------------------------- #
# residual/s1_data.py — InjectableStore.read_columns (no survivors; existing
# MUT5C test in tests/test_sni_mutation_run_s1_b.py killed the only candidate).
# --------------------------------------------------------------------------- #
def test_m6h_s1_data_InjectableStore_read_columns_returns_raw_lists():
    """s1_data.py:162, return column dict -> return None (MUT5C kill witness).

    Existing `test_mut5c_s1_data_InjectableStore_read_columns_1` already
    covers line 162; this regression smoke locks the kill on a fresh
    read of the same site."""
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "vol": [3], "close": [1.5]},
    })
    got = store.read_columns("p", ["vol", "close"])
    assert got == {"vol": [3], "close": [1.5]}


# --------------------------------------------------------------------------- #
# residual/run_s1.py — _byte_compare
# --------------------------------------------------------------------------- #
def test_m6h_run_s1__byte_compare_returns_False_when_REPORT_differs(tmp_path):
    """run_s1.py:1115, return False -> return True in _byte_compare.

    With two trees that differ under REPORT.md, `_byte_compare` must
    return False. A mutated True leaks the byte drift and would print
    `check: differs under REPORT.md` while still claiming OK; the existing
    importer suite does not exercise this False path."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    (b / "REPORT.md").write_text("DRIFT\n", encoding="utf-8")
    assert run_s1._byte_compare(a, b) is False


def test_m6h_run_s1__byte_compare_returns_True_not_None_when_ledger_matches(tmp_path):
    """run_s1.py:1116, return _ledger_equal(...) -> return None in _byte_compare.

    With two trees that agree under REPORT/manifest/results/observations
    AND have byte-equal ledgers (after `ts` is dropped), `_byte_compare`
    must return True. A mutated None is falsy and would be reported as
    a differ; the existing importer suite does not pin this True
    branch for `_byte_compare`."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text(
            '{"k":1,"ts":"wall-a"}\n{"k":2}\n', encoding="utf-8",
        )
    assert run_s1._byte_compare(a, b) is True


def test_m6h_run_s1__byte_compare_does_not_raise_on_ledger_path_arith(tmp_path):
    """run_s1.py:1116, produced / 'trial_ledger.jsonl' -> produced * '...' (×2 sites).

    Path * str raises TypeError; a mutated `_byte_compare` would raise on
    every call. The existing MUT5C test exercises the equal-trees path
    but does not pin "no raise" against a working tree with a non-empty
    ledger."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text(
            '{"k":1,"ts":"wall-a"}\n{"k":2}\n', encoding="utf-8",
        )
    # Must not raise; must return True for the equal case.
    rc = run_s1._byte_compare(a, b)
    assert rc is True


def test_m6h_run_s1__byte_compare_does_not_raise_on_rel_path_arith(tmp_path):
    """run_s1.py:1113, committed / rel -> committed * rel in _byte_compare.

    `Path * str` raises TypeError. The MUT5C byte-compare test never
    exercises the path-arithmetic inside the loop body because the
    equal-trees path short-circuits at `_tree_equal`; this kills the
    mutated by constructing a tree under each side that exercises the
    `_tree_equal(committed / rel, ...)` line."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    # Force `_tree_equal(committed / rel, produced / rel)` to be called
    # with rel == "REPORT.md" and differing bytes.
    (b / "REPORT.md").write_text("DRIFT\n", encoding="utf-8")
    rc = run_s1._byte_compare(a, b)
    # Original: returns False (REPORT.md differs). Mutated: raises TypeError
    # before the `_tree_equal` call can return; pytest would surface the
    # raise as a test error. We assert the False return so the mutated
    # version (which raises) is killed with a hard test failure.
    assert rc is False


# --------------------------------------------------------------------------- #
# residual/run_s1.py — _tree_equal
# --------------------------------------------------------------------------- #
def test_m6h_run_s1__tree_equal_returns_True_not_None_for_subtree_match(tmp_path):
    """run_s1.py:1130, return all(...) -> return None in _tree_equal.

    Two sub-trees that are equal recursively must return True (not
    None). The MUT5C test pins the differing sub-tree case but uses
    `is False`, which also passes if the function returns None for
    the equal case (None is not False either, but the equal-case
    assertion `is True` was the load-bearing one)."""
    a = tmp_path / "ta"
    b = tmp_path / "tb"
    a.mkdir()
    b.mkdir()
    (a / "sub").mkdir()
    (b / "sub").mkdir()
    (a / "sub" / "g.txt").write_text("a", encoding="utf-8")
    (b / "sub" / "g.txt").write_text("a", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is True


def test_m6h_run_s1__tree_equal_does_not_raise_on_b_over_n_arith(tmp_path):
    """run_s1.py:1130, b / n -> b * n in _tree_equal.

    `Path * str` raises TypeError on the recursive descent. The
    equal-trees MUT5C test bypasses the recursion when both sides
    are empty (`all(...)` over an empty generator returns True)."""
    a = tmp_path / "ta"
    b = tmp_path / "tb"
    a.mkdir()
    b.mkdir()
    (a / "f.txt").write_text("same", encoding="utf-8")
    (b / "f.txt").write_text("same", encoding="utf-8")
    # Force the recursive `_tree_equal(a / n, b / n)` to run.
    assert run_s1._tree_equal(a, b) is True


def test_m6h_run_s1__tree_equal_returns_True_for_existing_equal_dirs(tmp_path):
    """run_s1.py:1124, a.exists() != b.exists() -> a.exists() == b.exists().

    With both a and b existing as directories, the third existence
    check must NOT short-circuit to False; the function must
    recurse. The mutated `==` flips the branch and returns False on
    every call where both sides exist, including the canonical
    equal-trees case."""
    a = tmp_path / "ta"
    b = tmp_path / "tb"
    a.mkdir()
    b.mkdir()
    (a / "f.txt").write_text("same", encoding="utf-8")
    (b / "f.txt").write_text("same", encoding="utf-8")
    assert run_s1._tree_equal(a, b) is True


def test_m6h_run_s1__tree_equal_handles_file_vs_dir_correctly(tmp_path):
    """run_s1.py:1120, a.is_file() or b.is_file() -> a.is_file() and b.is_file().

    When a is a regular file and b is a directory (same name), the
    original returns False (the `and b.is_file()` short-circuits the
    read-bytes test). The mutated `and` skips the first branch and
    later raises on `a.iterdir()` because a is a file. This test
    pins the False return and is killed by the raise."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text("payload", encoding="utf-8")  # regular file
    b.mkdir()                                   # directory
    assert run_s1._tree_equal(a, b) is False


def test_m6h_run_s1__tree_equal_returns_True_for_both_missing_paths(tmp_path):
    """run_s1.py:1123, return True -> return False in _tree_equal.

    When both sides resolve to a missing path, the function must
    return True (vacuously equal). The mutated `return False`
    returns False. The earlier `not a.exists() and not b.exists()`
    short-circuit path inside the same If is reachable via the
    exact-missing case; this test pins the True return there."""
    a = tmp_path / "missing-a-xyz"
    b = tmp_path / "missing-b-xyz"
    # Both paths do not exist. Original returns True. Mutated returns False.
    assert run_s1._tree_equal(a, b) is True


# --------------------------------------------------------------------------- #
# residual/run_s1.py — main
# --------------------------------------------------------------------------- #
def test_m6h_run_s1_main_returns_2_not_3_on_pin_verification_failure(tmp_path, monkeypatch):
    """run_s1.py:1184, return 2 -> return 3 in main (verify_all failure path).

    When `store.verify_all()` raises inside the `store is None` branch
    (line 1180-1184), main must return exit 2. The existing
    `test_missing_seal_file_exits_nonzero` exercises an earlier
    `SealMismatch` path with exit 3; it does not pin the verify_all
    failure exit code. We stub `GitBlobStore` so its `verify_all`
    raises a controlled RuntimeError; main should catch it, print
    REFUSED, and return 2 (not 3)."""
    class _BadStore:
        def __init__(self, *a, **k):
            pass
        def verify_all(self):
            raise RuntimeError("PIN MISMATCH test")

    monkeypatch.setattr(run_s1, "GitBlobStore", _BadStore)
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", str(tmp_path / "t.jsonl")],
    )
    assert rc == 2


def test_m6h_run_s1_main_does_not_raise_on_repo_root_data_arith(tmp_path, monkeypatch):
    """run_s1.py:1165, repo_root / 'data' -> repo_root * 'data' in main.

    `Path * str` raises TypeError. The data-root containment check
    `data_root = repo_root / "data"` is the first line of the
    ledger-under-data refusal branch. The mutated function would
    raise before the `if bad:` short-circuit, before any refusal
    message is printed. We pin the refusal message and exit 2."""
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", "data/trial_ledger.jsonl"],
        store=object(),
    )
    assert rc == 2


def test_m6h_run_s1_main_returns_0_not_1_when_check_passes(tmp_path, monkeypatch):
    """run_s1.py:1200, return 0 if ok else 1 -> 1 if ok else 1 (the `0` -> `1`).

    When `--check` runs against a `--runs-dir` whose sealed tree
    byte-equals the produced tree, main must return 0. The mutated
    `0 -> 1` returns 1 even on a clean `--check`. This test stubs
    `_byte_compare` to True and asserts rc == 0."""
    class _StubStore:
        input_ref = "SYNTHETIC"
        def commit_date_iso(self, _ref=None):
            return "1970-01-01T00:00:00+00:00"
    monkeypatch.setattr(run_s1, "_byte_compare", lambda *a, **k: True)
    monkeypatch.setattr(run_s1, "run_pipeline", lambda *a, **k: None)
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", str(tmp_path / "t.jsonl"),
         "--runs-dir", str(tmp_path / "runs"),
         "--check"],
        store=_StubStore(),
    )
    assert rc == 0


def test_m6h_run_s1_main_returns_1_not_0_when_check_differs(tmp_path, monkeypatch):
    """run_s1.py:1200, return 0 if ok else 1 -> return 0 if ok else 0 (the `1` -> `0`).

    When `--check` runs and the produced tree differs from the sealed
    tree, main must return 1. The mutated `1 -> 0` returns 0 even on
    a divergent `--check`, falsely reporting OK. This test stubs
    `_byte_compare` to False and asserts rc == 1."""
    class _StubStore:
        input_ref = "SYNTHETIC"
        def commit_date_iso(self, _ref=None):
            return "1970-01-01T00:00:00+00:00"
    monkeypatch.setattr(run_s1, "_byte_compare", lambda *a, **k: False)
    monkeypatch.setattr(run_s1, "run_pipeline", lambda *a, **k: None)
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", str(tmp_path / "t.jsonl"),
         "--runs-dir", str(tmp_path / "runs"),
         "--check"],
        store=_StubStore(),
    )
    assert rc == 1


# --------------------------------------------------------------------------- #
# regression smoke (unmutated; pins expected behaviour of the owned range)
# --------------------------------------------------------------------------- #
def test_m6h_smoke_run_s1_tree_equal_equal_directories():
    a = REPO / "research" / "single_name_intelligence" / "residual"
    b = REPO / "research" / "single_name_intelligence" / "residual"
    assert run_s1._tree_equal(a, b) is True


def test_m6h_smoke_run_s1_tree_equal_detects_extra_file(tmp_path):
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
    p = tmp_path / "a.jsonl"
    q = tmp_path / "b.jsonl"
    p.write_text('{"k":1,"ts":"wall-a"}\n{"k":2}\n', encoding="utf-8")
    q.write_text('{"k":1,"ts":"wall-b"}\n{"k":2}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, q) is True
    r = tmp_path / "c.jsonl"
    r.write_text('{"k":9}\n', encoding="utf-8")
    assert run_s1._ledger_equal(p, r) is False


def test_m6h_smoke_run_s1_main_refuses_ledger_under_data(tmp_path):
    rc = run_s1.main(
        ["--input-ref", "SYNTHETIC", "--repo-root", str(tmp_path),
         "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", "data/trial_ledger.jsonl"],
        store=object(),
    )
    assert rc == 2


def test_m6h_smoke_s1_data_InjectableStore_read_columns_records_access():
    store = InjectableStore({
        "p": {"Date": [date(2020, 1, 2)], "vol": [3]},
    })
    store.read_columns("p", ["vol"])
    assert store.access_log[-1] == ("read_columns", "p", ("vol",))


def test_m6h_smoke_s1_data_to_date_handles_datetime_and_date():
    assert _to_date(datetime(2020, 1, 2, 15, 30, tzinfo=timezone.utc)) == date(2020, 1, 2)
    assert _to_date(date(2020, 1, 2)) == date(2020, 1, 2)
    try:
        _to_date("2020-01-02")
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError expected for string input to _to_date")


def test_m6h_smoke_s1_data_InjectableStore_commit_date_iso_is_1970():
    store = InjectableStore({})
    assert store.commit_date_iso() == "1970-01-01T00:00:00+00:00"
