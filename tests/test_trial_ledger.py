"""Trial Ledger + the honest-N contract on deflated_sharpe.

These cover the keystone of the self-improving-AI suite's anti-p-hacking spine:
the multiple-testing N must be COUNTED (at generation, deduplicated, persisted),
not asserted by a caller who can lowball it. See research/SELF_IMPROVING_AI_SUITE.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger
from engine.validation import deflated_sharpe, ret_moments


# --------------------------------------------------------------------------- #
# ledger mechanics
# --------------------------------------------------------------------------- #
def test_dedup_counts_distinct_configs(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    assert led.log_trial({"w": 20}) is True          # new
    assert led.log_trial({"w": 20}) is False         # exact re-run -> idempotent
    assert led.log_trial({"w": 40}) is True          # genuinely new config
    assert led.literal_n() == 2


def test_log_grid_returns_newly_distinct_and_is_idempotent(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    grid = [{"w": w, "cap": c} for w in (20, 60, 120) for c in (1.0, 1.5)]  # 6 configs
    assert led.log_grid(grid) == 6
    assert led.log_grid(grid) == 0                   # re-logging the grid adds nothing
    assert led.literal_n() == 6


def test_persists_and_reloads_from_disk(tmp_path):
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="fam").log_grid([{"w": w} for w in range(10)])
    # a fresh handle (new process, same file) must see the accumulated count
    assert TrialLedger(p, family="fam").literal_n() == 10


def test_family_is_required(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl")          # no default family
    try:
        led.log_trial({"w": 20})
    except ValueError as e:
        assert "family" in str(e)
    else:
        raise AssertionError("expected ValueError when no family is given")


def test_families_are_namespaced(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl")
    led.log_grid([{"w": w} for w in range(5)], family="a")
    led.log_grid([{"w": w} for w in range(3)], family="b")
    assert led.literal_n("a") == 5
    assert led.literal_n("b") == 3
    assert led.families() == ["a", "b"]


# --------------------------------------------------------------------------- #
# effective_n: conservative by default, floored when credit is allowed
# --------------------------------------------------------------------------- #
def test_effective_n_default_equals_literal(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"w": w} for w in range(50)])
    assert led.effective_n() == 50                   # no credit -> count every trial


def test_correlation_credit_is_floored_at_sqrt(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"w": w} for w in range(400)])
    # an adversary asking for 99% correlation credit cannot launder 400 -> ~4
    assert led.effective_n(correlation_credit=0.01) == 20   # ceil(sqrt(400)) floor
    # a mild, legitimate credit still reduces but stays well above the floor
    assert led.effective_n(correlation_credit=0.5) == 200


def test_effective_n_floor_one_when_empty(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    assert led.effective_n() == 1                    # never 0 -> never a div/scale blow-up


# --------------------------------------------------------------------------- #
# declared research budget: a floor that can only RAISE the haircut
# --------------------------------------------------------------------------- #
def test_declared_budget_floors_effective_n_above_itemized(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"v": v} for v in ("a", "b", "c", "d")])   # 4 itemized variants
    led.log_declared_budget(40, reason="manual research upper-bound")
    assert led.literal_n() == 4
    assert led.declared_budget() == 40
    assert led.effective_n() == 40                   # floor wins over the 4 itemized


def test_declared_budget_never_lowers_effective_n(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"v": v} for v in range(100)])     # 100 itemized
    led.log_declared_budget(10)                       # smaller declaration must NOT reduce N
    assert led.effective_n() == 100


def test_declared_budget_is_idempotent_and_takes_the_max(tmp_path):
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, family="fam")
    assert led.log_declared_budget(40, reason="r") is True
    assert led.log_declared_budget(40, reason="r") is False   # same (n, reason) -> no dup row
    led.log_declared_budget(64, reason="bigger")              # a higher declaration raises the floor
    assert led.effective_n() == 64
    # survives a process restart (rebuilt from disk)
    assert TrialLedger(p, family="fam").effective_n() == 64


def test_declared_budget_rejects_below_one(tmp_path):
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    try:
        led.log_declared_budget(0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for a declared budget < 1")


def test_deflated_sharpe_uses_declared_floor(tmp_path):
    sr, sk, ku, n = _strong_series()
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"v": v} for v in ("a", "b", "c", "d")])
    led.log_declared_budget(40)
    by_ledger = deflated_sharpe(sr, sk, ku, n, ledger=led, family="fam")
    by_literal = deflated_sharpe(sr, sk, ku, n, n_trials=40)   # the old hand-declared path
    assert by_ledger["dsr"] == by_literal["dsr"]   # migration is behavior-preserving
    assert by_ledger["n_trials"] == 40


# --------------------------------------------------------------------------- #
# integration: deflated_sharpe honours the ledger and forbids ambiguity
# --------------------------------------------------------------------------- #
def _strong_series():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0010, 0.03, 4000))
    return ret_moments(r)


def test_ledger_path_matches_literal_for_equal_N(tmp_path):
    sr, sk, ku, n = _strong_series()
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"i": i} for i in range(37)])
    by_ledger = deflated_sharpe(sr, sk, ku, n, ledger=led, family="fam")
    by_literal = deflated_sharpe(sr, sk, ku, n, n_trials=37)
    assert by_ledger["dsr"] == by_literal["dsr"]
    assert by_ledger["n_trials"] == 37


def test_honest_N_lowers_dsr_vs_lowballed(tmp_path):
    """The whole point: a lowballed literal yields a rosier DSR than the honest count."""
    sr, sk, ku, n = _strong_series()
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"i": i} for i in range(60)])      # the search really tried 60 configs
    honest = deflated_sharpe(sr, sk, ku, n, ledger=led, family="fam")["dsr"]
    lowballed = deflated_sharpe(sr, sk, ku, n, n_trials=4)["dsr"]
    assert honest <= lowballed                       # honest accounting never flatters


def test_rejects_both_ledger_and_n_trials(tmp_path):
    sr, sk, ku, n = _strong_series()
    led = TrialLedger(tmp_path / "t.jsonl", family="fam")
    led.log_grid([{"i": 1}])
    try:
        deflated_sharpe(sr, sk, ku, n, n_trials=5, ledger=led, family="fam")
    except ValueError as e:
        assert "not both" in str(e)
    else:
        raise AssertionError("expected ValueError when both N sources are passed")


def test_requires_one_N_source(tmp_path):
    sr, sk, ku, n = _strong_series()
    try:
        deflated_sharpe(sr, sk, ku, n)               # neither n_trials nor ledger
    except ValueError as e:
        assert "multiple-testing N" in str(e)
    else:
        raise AssertionError("expected ValueError when no N source is given")


def test_legacy_positional_callers_unaffected():
    """The 45 existing callers pass n_trials positionally — must behave identically."""
    assert deflated_sharpe(None, 0.0, 3.0, 100, 50) is None     # thin input
    assert deflated_sharpe(0.05, 0.0, 3.0, 2, 50) is None       # T < 3
    sr, sk, ku, n = _strong_series()
    assert deflated_sharpe(sr, sk, ku, n, 10)["n_trials"] == 10


# --------------------------------------------------------------------------- #
# register_trials — the W1d budget-declaration decorator / context manager
# --------------------------------------------------------------------------- #
def test_register_trials_context_writes_declared_budget(tmp_path):
    from engine.trial_ledger import register_trials
    led = TrialLedger(tmp_path / "t.jsonl")
    with register_trials("fam_ctx", budget=40, reason="8x5 grid", ledger=led):
        pass
    # a fresh ledger on the same file must see the declared budget as a floor on N
    led2 = TrialLedger(tmp_path / "t.jsonl")
    assert led2.declared_budget("fam_ctx") == 40
    assert led2.effective_n("fam_ctx") == 40


def test_register_trials_decorator_writes_and_runs(tmp_path):
    from engine.trial_ledger import register_trials
    led = TrialLedger(tmp_path / "t.jsonl")

    @register_trials("fam_dec", budget=12, ledger=led)
    def harness():
        return "ran"

    assert harness.__trial_family__ == "fam_dec"
    assert harness.__trial_budget__ == 12
    assert harness() == "ran"                    # the wrapped fn still runs
    led2 = TrialLedger(tmp_path / "t.jsonl")
    assert led2.declared_budget("fam_dec") == 12


def test_register_trials_basis_and_expiry_stamped_in_reason(tmp_path):
    from engine.trial_ledger import register_trials
    led = TrialLedger(tmp_path / "t.jsonl")
    with register_trials("fam_fz", budget=30, reason="spvector quote",
                         basis="frozen-quote", expiry="2026-09-30", ledger=led):
        pass
    # the reason note carries the basis + expiry passport
    import json
    rows = [json.loads(l) for l in (tmp_path / "t.jsonl").read_text().splitlines() if l.strip()]
    decl = [r for r in rows if r.get("kind") == "declared_budget" and r["family"] == "fam_fz"]
    assert decl and "frozen-quote" in decl[0]["reason"] and "2026-09-30" in decl[0]["reason"]


def test_register_trials_is_idempotent(tmp_path):
    from engine.trial_ledger import register_trials
    led = TrialLedger(tmp_path / "t.jsonl")
    for _ in range(3):
        with register_trials("fam_idem", budget=20, reason="same", ledger=led):
            pass
    import json
    rows = [json.loads(l) for l in (tmp_path / "t.jsonl").read_text().splitlines() if l.strip()]
    decl = [r for r in rows if r.get("kind") == "declared_budget" and r["family"] == "fam_idem"]
    assert len(decl) == 1                         # re-running does NOT inflate N


def test_register_trials_rejects_empty_family():
    from engine.trial_ledger import register_trials
    try:
        register_trials("", budget=10)
    except ValueError:
        pass
    else:
        raise AssertionError("empty family must raise")


# --------------------------------------------------------------------------- #
# durability: append-before-memory + counted corruption (C19 WP06 / MAS-269)
# --------------------------------------------------------------------------- #
def test_failed_append_leaves_config_unseen(tmp_path, monkeypatch):
    import pytest

    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, family="f")
    original = TrialLedger._append_rows
    calls = {"n": 0}

    def flaky(self, rows):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated torn write")
        return original(self, rows)

    monkeypatch.setattr(TrialLedger, "_append_rows", flaky)
    cfg = {"w": 20}
    with pytest.raises(OSError):
        led.log_trial(cfg, family="f")
    # memory was NOT poisoned by the failed write: the retry is a genuine new trial
    assert led.log_trial(cfg, family="f") is True
    assert len(p.read_text().splitlines()) == 1
    # a fresh handle sees exactly the one persisted row -> the retry dedups
    assert TrialLedger(p, family="f").log_trial(cfg, family="f") is False


def test_failed_append_leaves_declared_floor_unchanged(tmp_path, monkeypatch):
    import pytest

    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, family="f")
    original = TrialLedger._append_rows
    calls = {"n": 0}

    def flaky(self, rows):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated torn write")
        return original(self, rows)

    monkeypatch.setattr(TrialLedger, "_append_rows", flaky)
    before_budget, before_n = led.declared_budget("f"), led.effective_n("f")
    with pytest.raises(OSError):
        led.log_declared_budget(50, family="f")
    # the floor is raised only after a durable append, so a failed write moves nothing
    assert led.declared_budget("f") == before_budget
    assert led.effective_n("f") == before_n
    assert led.log_declared_budget(50, family="f") is True
    assert led.declared_budget("f") == 50


def test_append_fsyncs_each_write(tmp_path, monkeypatch):
    led = TrialLedger(tmp_path / "t.jsonl", family="f")
    fsyncs: list[int] = []

    def recorder(fd):
        fsyncs.append(fd)
        return None

    monkeypatch.setattr("os.fsync", recorder)
    led.log_trial({"w": 20}, family="f")
    assert len(fsyncs) >= 1
    fsyncs.clear()
    # a whole grid is ONE append call -> exactly one fsync
    assert led.log_grid([{"w": w} for w in (40, 60, 80)], family="f") == 3
    assert len(fsyncs) == 1


def test_load_counts_corrupt_lines(tmp_path):
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, family="f")
    cfg_a, cfg_b = {"w": 20}, {"w": 40}
    led.log_trial(cfg_a, family="f")
    led.log_trial(cfg_b, family="f")
    with p.open("a", encoding="utf-8") as fh:
        fh.write("not json at all\n")
        fh.write('{"family": "f", "config_hash": "ab')  # torn final line, no newline
    fresh = TrialLedger(p, family="f")
    assert fresh.corrupt_lines == 2
    assert fresh.load_error is None
    # corruption did not lose the good rows
    assert fresh.log_trial(cfg_a, family="f") is False
    assert fresh.log_trial(cfg_b, family="f") is False
    assert fresh.literal_n("f") == 2


def test_concurrent_same_config_writes_one_row(tmp_path):
    import threading

    led = TrialLedger(tmp_path / "t.jsonl", family="f")
    cfg = {"w": 20}
    barrier = threading.Barrier(16)
    results: list[bool] = []

    def worker():
        barrier.wait()
        results.append(led.log_trial(cfg, family="f"))

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1                  # the dedup check must not race
    assert len((tmp_path / "t.jsonl").read_text().splitlines()) == 1
    assert led.literal_n("f") == 1


def test_log_grid_batches_into_one_append(tmp_path, monkeypatch):
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, family="f")
    original = TrialLedger._append_rows
    appends = {"n": 0}

    def counting(self, rows):
        appends["n"] += 1
        return original(self, rows)

    monkeypatch.setattr(TrialLedger, "_append_rows", counting)
    grid = [{"w": 20}, {"w": 40}, {"w": 60}, {"w": 20}]  # last is a dup of the first
    assert led.log_grid(grid, family="f") == 3
    assert appends["n"] == 1
    assert len(p.read_text().splitlines()) == 3
    assert led.log_grid(grid, family="f") == 0
    assert appends["n"] == 1                         # idempotent re-run: no append at all


# Concurrent owners must serialize the fresh read, generation and cold readback.
def _trial_process(path, ready, start, results):
    led = TrialLedger(path, family="f")
    ready.set()
    if not start.wait(10):
        raise RuntimeError("test start timed out")
    results.put(led.log_trial({"w": 20}))


def test_stale_instances_do_not_duplicate_rows(tmp_path):
    p = tmp_path / "t.jsonl"
    first, second = TrialLedger(p, "f"), TrialLedger(p, "f")
    assert first.log_trial({"w": 20}) is True
    assert second.log_trial({"w": 20}) is False
    first.log_declared_budget(40, reason="same")
    assert second.log_declared_budget(40, reason="same") is False
    assert len(p.read_text().splitlines()) == 2
    assert second.effective_n() == 40


def test_separate_processes_deduplicate_fresh_reads(tmp_path):
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    start, results = ctx.Event(), ctx.Queue()
    ready = [ctx.Event(), ctx.Event()]
    procs = [ctx.Process(target=_trial_process, args=(str(tmp_path / "t.jsonl"), r, start, results)) for r in ready]
    try:
        for proc in procs:
            proc.start()
        assert all(r.wait(10) for r in ready)
        start.set()
        assert sorted(results.get(timeout=10) for _ in procs) == [False, True]
        for proc in procs:
            proc.join(10)
            assert proc.exitcode == 0
        assert len((tmp_path / "t.jsonl").read_text().splitlines()) == 1
    finally:
        for proc in procs:
            if proc.is_alive():
                proc.terminate()
                proc.join(5)
        results.close()


def test_owner_transaction_serializes_whole_generation_and_readback(tmp_path):
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    p = tmp_path / "t.jsonl"
    p.write_bytes(b"")
    owner = TrialLedger(p, "f")
    ready, start, results = ctx.Event(), ctx.Event(), ctx.Queue()
    proc = ctx.Process(target=_trial_process, args=(str(p), ready, start, results))
    try:
        proc.start()
        assert ready.wait(10)
        with owner.owner_transaction(strict=True) as held:
            assert held is owner
            start.set()
            assert owner.log_grid([{"w": 20}, {"w": 40}]) == 2
            owner.log_declared_budget(40, reason="all generated first")
            import queue
            with __import__("pytest").raises(queue.Empty):
                results.get(timeout=0.15)
            assert len(owner.raw_readback().splitlines()) == 3
        assert results.get(timeout=10) is False
        proc.join(10)
        assert proc.exitcode == 0
    finally:
        if proc.is_alive():
            proc.terminate()
            proc.join(5)
        results.close()


def test_nested_owner_transaction_reuses_only_same_instance(tmp_path):
    import pytest
    p = tmp_path / "t.jsonl"
    p.write_bytes(b"")
    led, other = TrialLedger(p, "f"), TrialLedger(p, "f")
    with pytest.raises(RuntimeError):
        led.raw_readback()
    with led.owner_transaction(strict=True):
        with led.owner_transaction(strict=True):
            assert led.log_trial({"w": 20}) is True
        with pytest.raises(RuntimeError):
            with other.owner_transaction():
                pass
        with pytest.raises(RuntimeError):
            with TrialLedger(tmp_path / "other.jsonl", "f").owner_transaction():
                pass
        assert led.literal_n() == 1


def test_lost_or_replaced_history_is_not_recreated(tmp_path):
    import pytest
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, "f")
    led.log_trial({"w": 20})
    p.unlink()
    with pytest.raises(OSError):
        led.log_trial({"w": 40})
    with pytest.raises(OSError):
        TrialLedger(p, "f").log_trial({"w": 40})
    assert not p.exists()
    p.write_bytes(b"")
    with pytest.raises(OSError):
        led.log_trial({"w": 40})
    assert led.literal_n() == 1


def test_strict_transaction_rejects_incomplete_or_invalid_history(tmp_path):
    import json
    import pytest
    p = tmp_path / "t.jsonl"
    missing = TrialLedger(p, "f")
    with pytest.raises(OSError):
        with missing.owner_transaction(strict=True):
            pass
    assert not p.exists()
    p.write_bytes(b"")
    led = TrialLedger(p, "f")
    led.log_trial({"w": 20})
    good = p.read_bytes()
    row = json.loads(good)
    for corrupt in (good.rstrip(b"\n"), good + b'[]\n',
                    good + b'{"family":"f","family":"g"}\n',
                    json.dumps({**row, "config_hash": "0" * 16}).encode() + b"\n",
                    json.dumps({**row, "ts": True}).encode() + b"\n",
                    json.dumps({**row, "config": {"w": float("nan")}}).encode() + b"\n"):
        p.write_bytes(corrupt)
        fresh = TrialLedger(p, "f")
        with pytest.raises((OSError, ValueError)):
            with fresh.owner_transaction(strict=True):
                pass


def test_failed_fsync_does_not_publish_cache_or_duplicate_charge(tmp_path, monkeypatch):
    import os
    import stat
    import pytest
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, "f")
    led.log_trial({"w": 20})
    real = os.fsync
    def fail_data(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("test data durability unknown")
        return real(fd)
    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_data)
        with pytest.raises(OSError):
            led.log_trial({"w": 40})
    assert led.literal_n() == 1
    # Conservatively count the retained same-path row; never append a replacement.
    assert led.log_trial({"w": 40}) is False
    assert led.literal_n() == 2
    assert len(p.read_text().splitlines()) == 2


def test_unsafe_ledger_aliases_and_fifo_refuse_without_following(tmp_path):
    import os
    import pytest
    target = tmp_path / "target.jsonl"
    target.write_bytes(b"")
    for kind in ("symlink", "hardlink", "fifo"):
        p = tmp_path / (kind + ".jsonl")
        if kind == "symlink":
            p.symlink_to(target)
        elif kind == "hardlink":
            os.link(target, p)
        else:
            os.mkfifo(p)
        with pytest.raises(OSError):
            TrialLedger(p, "f").log_trial({"w": 20})
        p.unlink()
        assert target.read_bytes() == b""


def test_same_bytes_replacement_between_calls_refuses(tmp_path):
    import os
    import pytest
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, "f")
    led.log_trial({"w": 20})
    original, inode = p.read_bytes(), p.stat().st_ino
    replacement = tmp_path / "replacement.jsonl"
    replacement.write_bytes(original)
    os.replace(replacement, p)
    assert p.stat().st_ino != inode
    with pytest.raises(OSError, match="identity changed"):
        led.log_trial({"w": 40})
    assert p.read_bytes() == original
    assert led.literal_n() == 1


def test_same_bytes_replacement_inside_transaction_refuses(tmp_path):
    import os
    import pytest
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, "f")
    led.log_trial({"w": 20})
    original, inode = p.read_bytes(), p.stat().st_ino
    with pytest.raises(OSError, match="identity changed"):
        with led.owner_transaction(strict=True):
            replacement = tmp_path / "replacement.jsonl"
            replacement.write_bytes(original)
            os.replace(replacement, p)
            assert p.stat().st_ino != inode
            led.log_trial({"w": 40})
    assert p.read_bytes() == original
    assert led.literal_n() == 1


def test_first_failed_append_retains_observed_file_identity(tmp_path, monkeypatch):
    import os
    import pytest
    import engine.trial_ledger as module
    p = tmp_path / "t.jsonl"
    led = TrialLedger(p, "f")
    with monkeypatch.context() as patch:
        patch.setattr(module.os, "write", lambda *_: (_ for _ in ()).throw(OSError("partial effect")))
        with pytest.raises(OSError, match="partial effect"):
            led.log_trial({"w": 20})
    assert p.read_bytes() == b""
    replacement = tmp_path / "replacement.jsonl"
    replacement.write_bytes(b"")
    os.replace(replacement, p)
    with pytest.raises(OSError, match="identity changed"):
        led.log_trial({"w": 20})
    assert p.read_bytes() == b""
    assert led.literal_n() == 0


def test_declared_budget_helper_resolves_system_temp_alias(tmp_path, monkeypatch):
    import tempfile
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "system-temp"
    alias.symlink_to(actual, target_is_directory=True)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(alias))
    first = TrialLedger.with_declared_budget(8, "temp-alias-fixture")
    second = TrialLedger.with_declared_budget(8, "temp-alias-fixture")
    assert first.path.parent == actual
    assert first.path == second.path
    assert second.effective_n() == 8
    assert len(first.path.read_text().splitlines()) == 1


def _legacy_lines():
    import json
    rows = (
        # a foreign prereg-registry record: no ledger identity key, only its own trial_id
        {"trial_id": "x", "hypothesis": "h", "fdr_family": "z", "ts": "2026-01-01T00:00:00Z"},
        # annotations: family + a non-budget kind, never a config_hash or config
        {"family": "f", "kind": "amendment", "note": "n", "ts": "2026-01-01T00:00:00Z"},
        {"family": "f", "kind": "filing_budget", "filing_week": "w", "mechanism_id": "m",
         "ts": "2026-01-01T00:00:00Z"},
    )
    return "".join(json.dumps(r) + "\n" for r in rows)


def test_legacy_identityless_records_do_not_block_appends(tmp_path):
    from engine.trial_ledger import register_trials
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="f").log_trial({"w": 20})
    with p.open("a", encoding="utf-8") as fh:
        fh.write(_legacy_lines())
    fresh = TrialLedger(p, family="f")
    assert fresh.corrupt_lines == 0
    assert fresh.legacy_rows == 3
    assert fresh.load_error is None
    assert fresh.literal_n("f") == 1
    before = p.read_bytes()
    assert fresh.log_trial({"w": 40}) is True
    assert fresh.log_declared_budget(3) is True
    with register_trials("g", 2, ledger=fresh):
        pass
    after = p.read_bytes()
    assert after.startswith(before)
    assert len(after.splitlines()) == len(before.splitlines()) + 3
    assert fresh.literal_n("f") == 2
    assert fresh.declared_budget("g") == 2
    reloaded = TrialLedger(p, family="f")
    assert (reloaded.corrupt_lines, reloaded.legacy_rows) == (0, 3)
    assert reloaded.literal_n("f") == 2


def test_unreadable_lines_still_block_appends_beside_legacy_records(tmp_path):
    import pytest
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="f").log_trial({"w": 20})
    with p.open("a", encoding="utf-8") as fh:
        fh.write(_legacy_lines())
        fh.write("not json at all\n")
    fresh = TrialLedger(p, family="f")
    assert (fresh.corrupt_lines, fresh.legacy_rows) == (1, 3)
    before = p.read_bytes()
    with pytest.raises((OSError, ValueError)):
        fresh.log_trial({"w": 40})
    assert p.read_bytes() == before


def test_identity_bearing_or_shapeless_rows_stay_corrupt(tmp_path):
    import json
    import pytest
    for i, bad in enumerate(({"family": 1, "kind": "amendment"},
                {"family": "f", "config": {}},
                {"config_hash": "0" * 16},
                {"family": "f", "kind": "declared_budget", "n": 2},
                {"family": "f", "kind": "amendment", "config": {}},
                {"family": "f", "kind": ""},
                {"kind": "amendment"},
                {"trial_id": "x", "family": "f"},
                {"trial_id": ""},
                {"trial_id": "x", "whatever": 1},
                {"family": "f", "kind": 1},
                {"family": "", "kind": "amendment"},
                {"family": "f", "kind": "Declared_Budget"},
                {"family": "f", "kind": "declared-budget"},
                {"family": "f", "kind": "other"},
                {"family": "f", "kind": ["amendment"]},
                {})):
        p = tmp_path / f"t{i}.jsonl"
        TrialLedger(p, family="f").log_trial({"w": 20})
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(bad) + "\n")
        fresh = TrialLedger(p, family="f")
        assert (fresh.corrupt_lines, fresh.legacy_rows) == (1, 0), bad
        before = p.read_bytes()
        with pytest.raises((OSError, ValueError)):
            fresh.log_trial({"w": 40})
        assert p.read_bytes() == before, bad


def test_live_causal_filing_budget_rows_do_not_block_appends(tmp_path, monkeypatch):
    # scripts/causal_ingest_brainstorm.py used to append a filing_budget row for every card
    # it filed straight into the ledger; those historical rows stay in the file and must
    # never wedge it. The live writer (#9585) now targets its own budget file only.
    import json
    from scripts import causal_ingest_brainstorm as causal
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="f").log_trial({"w": 20})
    with p.open("a", encoding="utf-8") as fh:
        for mech in ("mech-1", "mech-2"):
            fh.write(json.dumps({"ts": "2026-10-13T00:00:00+00:00", "kind": "filing_budget",
                                 "family": "causal_scan", "filing_week": "2026-W42",
                                 "mechanism_id": mech}) + "\n")
    budget = tmp_path / "budget.jsonl"
    monkeypatch.setattr(causal, "_TRIAL_LEDGER", p)
    monkeypatch.setattr(causal, "_FILING_BUDGET", budget)
    before = p.read_bytes()
    causal._log_filing_budget("mech-3", "2026-W42")
    causal._log_filing_budget("mech-4", "2026-W42")
    assert p.read_bytes() == before
    assert len(budget.read_text().splitlines()) == 2
    fresh = TrialLedger(p, family="f")
    assert (fresh.corrupt_lines, fresh.legacy_rows) == (0, 2)
    assert fresh.literal_n("f") == 1
    assert fresh.literal_n("causal_scan") == 0
    assert fresh.log_trial({"w": 40}) is True
    assert TrialLedger(p, family="f").literal_n("f") == 2


def test_annotation_kind_with_config_hash_counts_as_a_trial(tmp_path):
    import json
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="f").log_trial({"w": 20})
    with p.open("a", encoding="utf-8") as fh:
        fh.write(_legacy_lines())
        fh.write(json.dumps({"family": "f", "kind": "amendment",
                             "config_hash": "0123456789abcdef",
                             "ts": "2026-01-01T00:00:00Z"}) + "\n")
    fresh = TrialLedger(p, family="f")
    assert (fresh.corrupt_lines, fresh.legacy_rows) == (0, 3)
    assert fresh.literal_n("f") == 2
    assert fresh.log_trial({"w": 40}) is True
    assert fresh.literal_n("f") == 3


def test_strict_transaction_still_refuses_legacy_records(tmp_path):
    import pytest
    p = tmp_path / "t.jsonl"
    TrialLedger(p, family="f").log_trial({"w": 20})
    clean = p.read_bytes()
    for line in _legacy_lines().splitlines(keepends=True):
        p.write_bytes(clean + line.encode())
        fresh = TrialLedger(p, family="f")
        assert fresh.legacy_rows == 1
        with pytest.raises((OSError, ValueError)):
            with fresh.owner_transaction(strict=True):
                pass
        assert p.read_bytes() == clean + line.encode()
