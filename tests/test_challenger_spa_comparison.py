"""Hermetic tests for engine.challenger_spa_comparison (Q20 research reference, not wired).

Synthetic data only, integer/relative indexes, no network, no repo data, no wall clock.
"""
from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from engine import challenger_spa_comparison as q


def _ledger(family="fam", configs=({"v": "a"}, {"v": "b"}, {"v": "c"}), declared=(5, 9)):
    rows = [{"ts": i, "family": family, "kind": "declared_budget", "n": n,
             "config_hash": f"decl{i}"} for i, n in enumerate(declared)]
    for i, c in enumerate(configs):
        rows.append({"ts": 100 + i, "family": family, "config": dict(c), "source": "grid",
                     "config_hash": q.trial_config_hash(family, c)})
    rows.append({"ts": 200, "family": "other", "config": {"v": "a"}, "source": "grid",
                 "config_hash": q.trial_config_hash("other", {"v": "a"})})
    return rows


def _ar1(n, phi, rng, k=1):
    e = rng.standard_normal((n + 50, k))
    x = np.zeros_like(e)
    for t in range(1, e.shape[0]):
        x[t] = phi * x[t - 1] + e[t]
    return x[50:]


# ------------------------------------------------------------------ req1

def test_req1_candidates_map_to_generation_time_trials_and_no_losing_trial_vanishes():
    # hash rule replicates the ledger rule (known ledger identity for vector/optimal)
    assert q.trial_config_hash("vector", {"variant": "optimal"}) == "911496757c3b4247"
    rows = _ledger()
    cands = {"A": {"v": "a"}, "B": {"v": "b"}, "C": {"v": "c"}}
    mapped = q.map_candidates_to_trials(cands, rows, "fam", source="grid")
    assert [m["candidate"] for m in mapped] == ["A", "B", "C"]
    assert all(m["ledger_ts"] is not None for m in mapped)
    with pytest.raises(q.UnmappedCandidateError):
        q.map_candidates_to_trials({**cands, "X": {"v": "zzz"}}, rows, "fam")
    # dropping the losing trial C is refused ...
    with pytest.raises(q.MissingTrialError):
        q.map_candidates_to_trials({"A": {"v": "a"}, "B": {"v": "b"}}, rows, "fam")
    # ... unless explicitly excluded with a reason
    hc = q.trial_config_hash("fam", {"v": "c"})
    ok = q.map_candidates_to_trials({"A": {"v": "a"}, "B": {"v": "b"}}, rows, "fam",
                                    excluded={hc: "panel not retained"})
    assert len(ok) == 2
    with pytest.raises(ValueError):
        q.map_candidates_to_trials({"A": {"v": "a"}, "B": {"v": "b"}}, rows, "fam", excluded={hc: " "})
    # another family's identical config is not a match
    with pytest.raises(q.UnmappedCandidateError):
        q.map_candidates_to_trials({"A": {"v": "a"}}, _ledger(family="fam2", configs=()), "fam2")


def test_req1_cross_source_budget_trials_are_attrition_not_silently_dropped():
    # a same-family trial from ANOTHER source has no panel in a source-scoped comparison:
    # the source-scoped mapping does not flag it, but the budget still counts it, so the
    # caller's attrition (budget - mapped) is exactly that trial, never zero
    rows = _ledger(declared=())
    rows.append({"ts": 300, "family": "fam", "config": {"v": "other_src"}, "source": "manual",
                 "config_hash": q.trial_config_hash("fam", {"v": "other_src"})})
    cands = {"A": {"v": "a"}, "B": {"v": "b"}, "C": {"v": "c"}}
    mapped = q.map_candidates_to_trials(cands, rows, "fam", source="grid")
    assert len(mapped) == 3 and all(m["source"] == "grid" for m in mapped)
    budget = q.original_trial_budget(rows, "fam")
    assert budget["literal_n"] == 4 and budget["budget"] == 4
    assert budget["budget"] - len(mapped) == 1
    # without source scoping the same omission is refused as a vanished trial
    with pytest.raises(q.MissingTrialError):
        q.map_candidates_to_trials(cands, rows, "fam")


# ------------------------------------------------------------------ req2

def test_req2_resampling_preserves_dependence_and_reports_block_sensitivity():
    rng = np.random.default_rng(3)
    n = 600
    idx = q.stationary_bootstrap_indices(n, 200, 20.0, rng)
    assert idx.shape == (200, n) and idx.min() >= 0 and idx.max() < n
    steps = np.diff(idx, axis=1)
    cont = (steps == 1) | (steps == -(n - 1))
    assert 0.9 < cont.mean() < 0.99  # mean block ~20 -> ~95% continuation
    # common indices: identical candidates get identical bootstrap means/scales
    x = _ar1(n, 0.5, rng)[:, 0]
    r = q.spa_test(np.column_stack([x, x]), B=300, mean_block=20.0, seed=1)
    assert r["common_indices"] is True
    assert r["omega"][0] == pytest.approx(r["omega"][1])
    # serial dependence: block bootstrap scale exceeds iid scale for a persistent series
    s_iid = q.spa_test(x, B=400, mean_block=1.0, seed=2)["omega"][0]
    s_blk = q.spa_test(x, B=400, mean_block=30.0, seed=2)["omega"][0]
    assert s_blk > 1.3 * s_iid
    sens = q.block_length_sensitivity(np.column_stack([x, -x]), blocks=(5, 10, 20), B=200, seed=4)
    assert set(sens["rows"]) == {"5", "10", "20"}
    assert sens["min_p_c"] <= sens["max_p_c"]
    assert q.honest_n_blocks(2106, 21) == 100
    assert q.effective_sample_size(x) < n


def test_req2_spa_pvalue_ordering_and_discrimination():
    rng = np.random.default_rng(11)
    n, k = 800, 6
    base = rng.standard_normal((n, k))
    null = q.spa_test(base - base.mean(axis=0) - np.linspace(0, 0.3, k), B=500, mean_block=10, seed=5)
    assert null["p_l"] <= null["p_c"] <= null["p_u"]
    sig = base.copy()
    sig[:, 2] += 0.4
    strong = q.spa_test(sig, B=500, mean_block=10, seed=5)
    assert strong["p_c"] < 0.01 and strong["best_index"] == 2
    allneg = q.spa_test(base - base.mean(axis=0) - 1.0, B=200, mean_block=10, seed=5)
    assert allneg["stat"] == 0.0 and allneg["p_c"] == 1.0
    with pytest.raises(ValueError):
        q.spa_test(np.full((100, 2), np.nan), B=100)
    with pytest.raises(ValueError):
        q.spa_test(np.ones((100, 2)), B=100)  # degenerate zero variance


# ------------------------------------------------------------------ req3

def test_req3_chronological_holdout_not_replaced_by_shuffled_cv_or_pbo():
    t = np.arange(400)
    train, test = q.chronological_split(t, 300)
    assert train[:300].all() and test[300:].all()
    shuffled = np.random.default_rng(0).permutation(t)
    with pytest.raises(ValueError):
        q.chronological_split(shuffled, 300)
    rng = np.random.default_rng(1)
    d = rng.standard_normal((400, 3))
    with pytest.raises(ValueError):
        q.spa_test(d, B=100, mean_block=5, time_index=shuffled)
    pbo = q.cscv_pbo(rng.standard_normal((320, 4)), S=8)
    assert pbo["role"] == "supplementary" and pbo["can_set_verdict"] is False
    assert pbo["replaces_chronological_holdout"] is False and 0.0 <= pbo["pbo"] <= 1.0
    assert "pbo" not in inspect.signature(q.claim_decision).parameters
    spa = {"p_c": 0.2, "mean_block": 21.0}
    sens = {"rows": {"7": {"p_c": 0.3}, "21": {"p_c": 0.2}}}
    win = {"fresh_confirmation_allowed": True}
    a = q.assemble_report(spa, sens, 0.05, win, pbo={"pbo": 0.0})
    b = q.assemble_report(spa, sens, 0.05, win, pbo={"pbo": 1.0})
    assert a["decision"] == b["decision"] and a["decision"]["claim"] == "VANISHES"


# ------------------------------------------------------------------ req4

def test_req4_adding_null_correlated_candidates_never_lowers_the_budget():
    rows = _ledger()
    base = q.original_trial_budget(rows, "fam")
    assert base == {"declared_max": 9, "literal_n": 3, "budget": 9}
    for rho in (0.0, 0.5, 0.9, 0.99, 1.0):
        seq = [q.trial_budget_after_adding(base["budget"], base["literal_n"], m, rho) for m in range(60)]
        assert min(seq) >= base["budget"]
        assert all(b >= a for a, b in zip(seq, seq[1:]))
    assert q.trial_budget_after_adding(9, 3, 100, 0.0) == 103  # uncorrelated additions count fully
    assert q.budget_bonferroni(0.01, 71) == pytest.approx(0.71)
    with pytest.raises(ValueError):
        q.trial_budget_after_adding(9, 3, -1, 0.5)


# ------------------------------------------------------------------ req5

def test_req5_reused_windows_disclosed_never_marketed_as_fresh():
    reused = q.window_reuse_disclosure(100, 300, generated_at=200, prior_use_windows=[(100, 200)],
                                       n_blocks=50)
    assert reused["label"] == "REUSED" and reused["fresh_confirmation_allowed"] is False
    overlap = q.window_reuse_disclosure(250, 300, generated_at=200, prior_use_windows=[(100, 260)],
                                        n_blocks=50)
    assert overlap["label"] == "REUSED"
    thin = q.window_reuse_disclosure(250, 300, generated_at=200, n_blocks=4)
    assert thin["label"] == "FRESH_UNDERPOWERED" and thin["fresh_confirmation_allowed"] is False
    fresh = q.window_reuse_disclosure(250, 600, generated_at=200, n_blocks=q.MIN_INDEPENDENT_BLOCKS)
    assert fresh["label"] == "FRESH" and fresh["fresh_confirmation_allowed"] is True
    spa = {"p_c": 0.001, "mean_block": 21.0}
    sens = {"rows": {"7": {"p_c": 0.01}, "21": {"p_c": 0.001}}}
    rep = q.assemble_report(spa, sens, 0.10, reused)
    assert rep["decision"]["claim"] == "SURVIVES"
    assert rep["fresh_confirmation"] is False and rep["window"]["label"] == "REUSED"


# ------------------------------------------------------------------ req6

def test_req6_no_core_read_no_gate_bypass_no_ledger_no_promotion(tmp_path):
    repo = str(Path(q.__file__).resolve().parents[1])
    code = ("import sys, engine.challenger_spa_comparison as m; "
            "print(','.join(sorted(k for k in sys.modules if k == 'engine' or k.startswith('engine.'))))")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    env["PYTHONPATH"] = repo
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-P", "-c", code], capture_output=True, text=True, env=env,
                         cwd=str(tmp_path), timeout=60, check=True).stdout.strip()
    assert out.split(",") == ["engine", "engine.challenger_spa_comparison"]
    assert q.PROMOTION_AUTHORITY is False
    spa = {"p_c": 0.001, "mean_block": 21.0}
    rep = q.assemble_report(spa, {"rows": {"21": {"p_c": 0.001}}}, 0.5,
                            {"fresh_confirmation_allowed": True})
    assert rep["promotion_authority"] is False and rep["research_only"] is True
    assert q.study_verdict({"g": True}, data_eligible=False, missing_input="x")["verdict"] == "INSUFFICIENT_DATA"
    assert q.study_verdict({"g": True, "h": False}, data_eligible=True)["verdict"] == "REJECT"
    assert q.study_verdict({"g": True}, data_eligible=True)["verdict"] == "KEEP"
    decision = q.claim_decision(0.2, {"7": 0.3}, 0.0)
    assert decision["claim"] == "VANISHES" and "keep the incumbent" in decision["on_vanish"]


def test_no_silent_activation(tmp_path):
    assert q.RESEARCH_ONLY is True
    public = [n for n in dir(q) if not n.startswith("_")]
    banned = ("register", "promote", "publish", "schedule", "activate", "write", "save", "emit")
    assert not [n for n in public if any(b in n.lower() for b in banned)]
    repo = str(Path(q.__file__).resolve().parents[1])
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    env["PYTHONPATH"] = repo
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    work = tmp_path / "cwd"
    work.mkdir()
    res = subprocess.run([sys.executable, "-P", "-c", "import engine.challenger_spa_comparison"],
                         capture_output=True, text=True, env=env, cwd=str(work), timeout=60)
    assert res.returncode == 0 and res.stdout == "" and res.stderr == ""
    try:
        work.rmdir()  # import performs no I/O: fails with ENOTEMPTY if anything was written
    except OSError as exc:
        pytest.fail(f"import wrote into its working directory: {exc}")


# ------------------------------------------------------------------ supporting units

def test_strategy_net_returns_lag_and_cost():
    r = np.array([0.0, 0.10, -0.05, 0.02, 0.01])
    a = np.array([1.0, 0.0, 1.0, 1.0, 0.5])
    net = q.strategy_net_returns(r, a, 0.001, lag=1)
    assert np.isnan(net[:2]).all()
    # t=2: pos=a1=0, prev=a0=1 -> 0*r - 0.001*1
    assert net[2] == pytest.approx(-0.001)
    # t=3: pos=a2=1, prev=0 -> 0.02 - 0.001
    assert net[3] == pytest.approx(0.019)
    assert net[4] == pytest.approx(0.01)
    beta = q.risk_match_beta(0.5 * (np.arange(40.0) % 7), np.arange(40.0) % 7)
    assert beta == pytest.approx(0.5)


def test_newey_west_and_naive_selection_discriminator():
    rng = np.random.default_rng(5)
    x = _ar1(2000, 0.6, rng)[:, 0]
    assert q.newey_west_lrvar(x) > 2.0 * np.var(x)
    assert q.newey_west_lag(2100) == 7
    nb = q.naive_best_pvalue(rng.standard_normal((300, 5)))
    assert nb["selection_ignored"] is True and 0.0 <= nb["p_naive"] <= 1.0


def test_simulation_harness_small_and_bounded():
    rng = np.random.default_rng(9)
    panel = q.simulate_correlated_panel(500, 4, 0.9, 0.3, 0.0, rng)
    c = np.corrcoef(panel.T)
    assert panel.shape == (500, 4) and c[0, 1] > 0.7
    assert abs(float(panel.std()) - 1.0) < 0.2
    res = q.simulate_rejection_rates(300, 4, 0.5, 0.3, [0.5, 0, 0, 0], reps=8, B=99,
                                     mean_block=10, seed=1)
    assert res["rates"]["p_c"] >= 0.75
    with pytest.raises(ValueError):
        q.simulate_rejection_rates(300, 4, 0.5, 0.3, 0.0, reps=0, B=99, mean_block=10, seed=1)
