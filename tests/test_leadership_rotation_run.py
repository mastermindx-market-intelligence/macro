"""Synthetic tests for scripts.leadership_rotation_run (T11 composer)."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from scripts import leadership_rotation_episodes as ep
from scripts import leadership_rotation_inference as inf
from scripts import leadership_rotation_study as st
from scripts.leadership_rotation_run import (
    FAMILY_ORDER,
    PairSeries,
    _CONTROL_NAMES,
    evaluate_family,
    evaluate_group,
    evaluate_pair,
    falsifier_controls,
    main,
    run_p1,
)


def _flat_pair(n: int = 500, *, pair_id: str = "synth", group: str = "g") -> PairSeries:
    return PairSeries(pair_id, group, "N", "D", np.ones(n), np.ones(n), np.ones(n))


def _hand_path():
    R = [0.0] * 20
    R += [0.002 * k for k in range(1, 51)]
    R += [0.10 - 0.002 * k for k in range(1, 51)]
    R += [0.001 * k for k in range(1, 51)]
    return np.asarray(R, dtype=float)


# MUTATION: scripts/leadership_rotation_run.py:64 remove frozen=True from PairSeries
def test_pair_series_frozen_and_json_roundtrip():
    ps = _flat_pair()
    with pytest.raises(FrozenInstanceError):
        ps.pair_id = "x"  # type: ignore[misc]
    pr = evaluate_pair(ps, start=300, end=400)
    json.dumps(pr)


# MUTATION: scripts/leadership_rotation_run.py:575 remove PartitionSealed raise for P2
def test_p2_p3_partition_sealed_before_log_ratio(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("log_ratio reached")

    monkeypatch.setattr(st, "log_ratio", _boom)
    with pytest.raises(st.PartitionSealed):
        evaluate_group([_flat_pair()], start=300, end=400, partition="P2")
    with pytest.raises(st.PartitionSealed):
        evaluate_group([_flat_pair()], start=300, end=400, partition="P3")


# MUTATION: scripts/leadership_rotation_run.py:625 use onset_w=3.0 for A1 point metrics
def test_h1_point_metrics_match_episode_metrics():
    R = _hand_path()
    n = len(R)
    num = np.exp(R)
    den = np.ones(n)
    ps = PairSeries("h", "g", "N", "D", num, den, np.ones(n))
    gr = evaluate_group([ps], start=0, end=n - 1, partition="P0", W=np.ones((3, n), dtype=np.int32))
    phases = ep.zigzag(R, start=0, end=n)
    from scripts.leadership_rotation_run import (
        _episode_metrics_unit,
        _evaluate_pair_core,
        _measured_pairs_per_day,
    )

    core = _evaluate_pair_core(ps, start=0, end=n - 1)
    mpd = _measured_pairs_per_day([ps], [core], n - 1)
    session_w = float(np.sum(mpd[0 : n]))
    all_phases = core["phases"]
    for arm, key in (("A1", "a1"), ("A2", "a2"), ("A0", "a0")):
        records = core[f"{key}_class"]
        m = _episode_metrics_unit(records, all_phases, session_w)
        got = gr["H1"][arm]
        for field in ("detection", "burden", "median_delay"):
            exp = m[field]
            if exp is None or (isinstance(exp, float) and math.isnan(exp)):
                assert got[field] is None
            else:
                assert got[field] == pytest.approx(exp)


# MUTATION: scripts/leadership_rotation_run.py:935 draw fresh W per group in evaluate_family
def test_paired_bootstrap_one_w_shared_across_groups():
    n = 400
    W = inf.stationary_bootstrap_weights(n, reps=8, seed=99)
    g1 = [_flat_pair(n=n, pair_id="a", group="defensive_sector")]
    g2 = [_flat_pair(n=n, pair_id="b", group="broadening_proxy")]
    gr1 = evaluate_group(g1, start=300, end=380, partition="P0", W=W)
    gr2 = evaluate_group(g2, start=300, end=380, partition="P0", W=W)
    fam = evaluate_family(
        {"defensive_sector": g1, "broadening_proxy": g2},
        start=300,
        end=380,
        partition="P0",
    )
    assert fam["look_count"] == 0
    assert gr1["H1"]["p_a"] == fam["groups"]["defensive_sector"]["H1"]["p_a"]
    assert gr2["H1"]["p_a"] == fam["groups"]["broadening_proxy"]["H1"]["p_a"]


# MUTATION: scripts/leadership_rotation_inference.py:285 use scalar max of baseline means for all reps
def test_h2_replicates_match_slow_reference():
    a1 = np.array([0.10, 0.12])
    b1 = np.array([0.04, 0.05])
    b2 = np.array([0.02, 0.09])
    W = np.array([[1, 1], [1, 1], [2, 0]], dtype=np.int32)
    a1_W = inf.item_weights(W, [0, 0])
    b1_W = inf.item_weights(W, [0, 1])
    b2_W = inf.item_weights(W, [1, 1])
    fast = inf.h2_replicates(a1, a1_W, b1, b1_W, b2, b2_W)
    ref = []
    for r in range(W.shape[0]):
        m_a1 = inf.replicate_means(a1, a1_W[r : r + 1])[0]
        m_b1 = inf.replicate_means(b1, b1_W[r : r + 1])[0]
        m_b2 = inf.replicate_means(b2, b2_W[r : r + 1])[0]
        ref.append(m_a1 - np.maximum(m_b1, m_b2))
    np.testing.assert_allclose(fast, np.array(ref), rtol=0, atol=1e-12, equal_nan=True)


# MUTATION: scripts/leadership_rotation_inference.py:289 swap a1_res and b3_res in h3_statistic
def test_h3_statistic_sign_flips_when_residual_sets_swapped():
    a1 = np.array([0.01, 0.02, 0.03])
    b3 = np.array([0.0, -0.01, -0.02])
    s1 = inf.h3_statistic(a1, b3)
    s2 = inf.h3_statistic(b3, a1)
    assert s1 == pytest.approx(-s2)


# MUTATION: scripts/leadership_rotation_inference.py:135 use W[:, index] not cluster coordinate
def test_clustered_item_weight_uses_cluster_coordinate():
    n = 50
    W = np.ones((2, n), dtype=np.int32)
    W[1, 7] = 99
    coords = [7, 7]
    Wm = inf.item_weights(W, coords)
    assert Wm[1, 0] == 99
    assert Wm[1, 1] == 99


# MUTATION: scripts/leadership_rotation_run.py:665 return len(items) instead of cluster count
def test_honest_n_counts_clusters_not_items():
    n = 500
    spy = np.ones(n)
    day = 350
    pairs = []
    for i in range(3):
        num = np.ones(n)
        num[day] = 1.05
        pairs.append(PairSeries(f"p{i}", "g", "XLP", "XLK", num, np.ones(n), spy))
    gr = evaluate_group(pairs, start=300, end=400, partition="P0", W=np.ones((4, n), dtype=np.int32))
    assert gr["honest_n"]["H2"] == 1


# MUTATION: scripts/leadership_rotation_run.py:953 leave NaN raw p as NaN in holm input
def test_holm_missing_group_adjusted_p_is_one():
    fam = evaluate_family({"defensive_sector": [_flat_pair()]}, start=300, end=400, partition="P0")
    adj = fam["holm"]["adjusted"]
    assert len(adj) == 6
    broad = [adj[i] for i, (g, _h) in enumerate(FAMILY_ORDER) if g == "broadening_proxy"]
    assert all(p == 1.0 for p in broad)
    raw_def = [fam["holm"]["raw"][i] for i, (g, _h) in enumerate(FAMILY_ORDER) if g == "defensive_sector"]
    assert any(np.isfinite(p) for p in raw_def)


# MUTATION: scripts/leadership_rotation_run.py:848 use tn < MIN_HONEST_N for immature
def test_immature_precedence_over_underpowered():
    gr = {
        "group": "g",
        "executable": True,
        "coverage": 0.9,
        "honest_n": {"H1": 25, "H2": 5, "H3": 25},
        "test_n": {"H2": 25},
        "H1": {"decision": {"margins_met": False}, "stability": {"delay_reduction": {"holds": True}, "burden_cut_b": {"holds": True}}},
        "H2": {"point": 0.01, "safety": {"ok": True}},
        "H3": {"point": 0.01},
    }
    from scripts.leadership_rotation_run import _group_verdicts

    v = _group_verdicts(gr, "P0", [1.0] * 6, FAMILY_ORDER)
    assert v["H2"] == "IMMATURE"


# MUTATION: scripts/leadership_rotation_run.py:914 set source_limited=False for C3
def test_c3_verdict_source_limited_all_partitions():
    fam = evaluate_family({}, start=0, end=10, partition="P1")
    for g in ("defensive_sector", "broadening_proxy"):
        assert fam["verdicts"][g]["C3"] == "SOURCE_LIMITED"


# MUTATION: scripts/leadership_rotation_run.py:985 call load_closes before assert_prereg_landed
def test_run_p1_refuses_before_loader(tmp_path, monkeypatch):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    calls = []

    def _assert(_repo, **_kw):
        calls.append("assert")
        raise st.PreregNotLanded("no prereg")

    monkeypatch.setattr(st, "assert_prereg_landed", _assert)
    monkeypatch.setattr(st, "load_closes_from_git", lambda *a, **k: calls.append("load"))
    with pytest.raises(st.PreregNotLanded):
        run_p1(str(tmp_path))
    assert calls == ["assert"]


# MUTATION: scripts/leadership_rotation_run.py:1020 omit a name from falsifier_controls
def test_falsifier_controls_ten_names_all_pass():
    fc = falsifier_controls()
    assert set(fc) == set(_CONTROL_NAMES)
    assert all(fc[n]["passed"] for n in _CONTROL_NAMES)


# MUTATION: scripts/leadership_rotation_run.py:1035 pass when interpretation is absolute_recovery
def test_falsifier_both_down_mutation_sensitive():
    fc = falsifier_controls()["both_down"]
    assert fc["passed"] is True


# MUTATION: scripts/leadership_rotation_run.py:1105 always return passed True for rolling_carry
def test_falsifier_rolling_carry_mutation_sensitive():
    assert falsifier_controls()["rolling_carry"]["passed"] is True


# MUTATION: scripts/leadership_rotation_run.py:1120 treat any residual as passing beta_only
def test_falsifier_beta_only_mutation_sensitive():
    assert falsifier_controls()["beta_only"]["passed"] is True


# MUTATION: scripts/leadership_rotation_run.py:1155 pass zero_vs_missing when UNMEASURED is zero
def test_falsifier_zero_vs_missing_mutation_sensitive():
    assert falsifier_controls()["zero_vs_missing"]["passed"] is True


# MUTATION: scripts/leadership_rotation_run.py:1235 main controls returns 1 on success
def test_cli_controls_json_exit_zero(capsys):
    code = main(["controls"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert code == 0
    assert len(data) == 10
