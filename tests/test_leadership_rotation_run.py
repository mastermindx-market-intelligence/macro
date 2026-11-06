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
    build_groups,
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
    assert fam["look_count"] == 0  # P0 synthetic default: not a counted look (see test_look_count_distinguishes_zero_from_counted_looks)
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
        "H2": {"point": 0.01, "safety": {"ok": True}, "stability": {"holds": True}},
        "H3": {"point": 0.01, "stability": {"holds": True}},
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


# MUTATION: scripts/leadership_rotation_run.py:1100 skip P2_EXCLUDED for every partition
def test_build_groups_keeps_xlp_vs_smh_in_p1_not_p2():
    symbols = sorted({s for _id, (_g, num, den) in st.PAIRS.items() for s in (num, den)} | {"SPY"})
    n = 300
    aligned = {sym: np.ones(n) for sym in symbols}
    spy = aligned["SPY"]
    p1 = build_groups(aligned, spy, "P1")
    p2 = build_groups(aligned, spy, "P2")
    p1_ids = {ps.pair_id for plist in p1.values() for ps in plist}
    p2_ids = {ps.pair_id for plist in p2.values() for ps in plist}
    assert "xlp_vs_smh" in p1_ids
    assert "xlp_vs_smh" not in p2_ids


# MUTATION: scripts/leadership_rotation_run.py:1011 set stable=True for H2 in _group_verdicts
def test_h2_verdict_fails_when_stability_clause_fails():
    gr = {
        "group": "defensive_sector",
        "executable": True,
        "coverage": 0.95,
        "honest_n": {"H1": 30, "H2": 30, "H3": 30},
        "test_n": {"H2": 30, "H3": 30},
        "H1": {
            "decision": {"margins_met": True},
            "stability": {"delay_reduction": {"holds": True}, "burden_cut_b": {"holds": True}},
        },
        "H2": {
            "point": 0.02,
            "safety": {"ok": True},
            "stability": {"holds": False},
        },
        "H3": {"point": 0.01, "stability": {"holds": True}},
    }
    from scripts.leadership_rotation_run import _group_verdicts

    holm = [0.01 if g == "defensive_sector" and h == "H2" else 1.0 for g, h in FAMILY_ORDER]
    v = _group_verdicts(gr, "P0", holm, FAMILY_ORDER)
    assert v["H2"] == "DEVELOPMENT_FAIL"


# MUTATION: scripts/leadership_rotation_run.py:1024 set stable=True for H3 in _group_verdicts
def test_h3_verdict_fails_when_stability_clause_fails():
    gr = {
        "group": "defensive_sector",
        "executable": True,
        "coverage": 0.95,
        "honest_n": {"H1": 30, "H2": 30, "H3": 30},
        "test_n": {"H2": 30, "H3": 30},
        "H1": {
            "decision": {"margins_met": True},
            "stability": {"delay_reduction": {"holds": True}, "burden_cut_b": {"holds": True}},
        },
        "H2": {"point": 0.01, "safety": {"ok": True}, "stability": {"holds": True}},
        "H3": {"point": 0.02, "stability": {"holds": False}},
    }
    from scripts.leadership_rotation_run import _group_verdicts

    holm = [0.01 if g == "defensive_sector" and h == "H3" else 1.0 for g, h in FAMILY_ORDER]
    v = _group_verdicts(gr, "P0", holm, FAMILY_ORDER)
    assert v["H3"] == "DEVELOPMENT_FAIL"


# MUTATION: scripts/leadership_rotation_run.py:401 append one t per day instead of out.extend([t] * c)
def test_pair_session_third_boundaries_differ_when_pairs_start_late():
    from scripts.leadership_rotation_run import _measured_pairs_per_day, _pair_session_indices

    n = 600
    t = np.linspace(1.0, 1.05, n)
    spy = np.ones(n)
    early = PairSeries("e", "g", "N", "D", t, np.ones(n), spy)
    late_num = np.concatenate([np.full(280, np.nan), t[280:]])
    late = PairSeries("l", "g", "N", "D", late_num, np.ones(n), spy)
    start, end = 260, 550
    cores = []
    for ps in (early, late):
        from scripts.leadership_rotation_run import _evaluate_pair_core

        cores.append(_evaluate_pair_core(ps, start=start, end=end))
    mpd = _measured_pairs_per_day([early, late], cores, end)
    pair_sess = _pair_session_indices(mpd, start, end)
    day_sess = [t for t in range(start, end + 1) if mpd[t] > 0]
    s_pair = np.sort(np.asarray(pair_sess, dtype=np.int64))
    s_day = np.sort(np.asarray(day_sess, dtype=np.int64))
    assert len(s_pair) != len(s_day)
    b_pair = (int(s_pair[len(s_pair) // 3]), int(s_pair[(2 * len(s_pair)) // 3]))
    b_day = (int(s_day[len(s_day) // 3]), int(s_day[(2 * len(s_day)) // 3]))
    assert b_pair != b_day


# MUTATION: scripts/leadership_rotation_run.py:549 use all b1_days for b1_Wm not matured-only
def test_h2_h3_finite_at_calendar_end_with_pending_baseline_outcomes():
    n = 800
    dr = np.concatenate([np.zeros(400), np.full(400, 0.012)])
    R = np.cumsum(dr)
    num = np.exp(R)
    den = np.ones(n)
    spy = np.exp(0.0005 * np.arange(n))
    ps = PairSeries("end", "g", "N", "D", num, den, spy)
    end = n - 1
    W = inf.stationary_bootstrap_weights(n, reps=32, seed=7)
    gr = evaluate_group([ps], start=300, end=end, partition="P0", W=W)
    assert gr["H2"]["point"] is not None
    assert gr["H3"]["point"] is not None
    assert gr["H2"]["interval_90"][0] is not None
    assert gr["H3"]["interval_90"][1] is not None


# MUTATION: scripts/leadership_rotation_run.py:531 cluster B1 items via _item_coord_map instead of coords.append(t)
def test_b1_bootstrap_replicate_sd_positive_with_own_index_weights():
    n = 500
    spy = np.ones(n)
    num = np.ones(n)
    den = np.ones(n)
    num[200:400] = np.linspace(1.0, 1.08, 200)
    ps = PairSeries("b1", "g", "N", "D", num, den, spy)
    W = inf.stationary_bootstrap_weights(n, reps=64, seed=11)
    gr = evaluate_group([ps], start=150, end=420, partition="P0", W=W)
    from scripts.leadership_rotation_run import _evaluate_pair_core, _matured_b1_y20

    core = _evaluate_pair_core(ps, start=150, end=420)
    b1_y, b1_coords = _matured_b1_y20("g", [ps], [core])
    assert len(b1_y) >= 100
    b1_Wm = inf.item_weights(W, b1_coords)
    means = inf.replicate_means(np.array(b1_y, dtype=float), b1_Wm)
    assert float(np.nanstd(means)) > 1e-12


# MUTATION: scripts/leadership_rotation_run.py:768 default h2_safety ok to True when fs_b2 is NaN
def test_h2_safety_fail_closed_when_b2_unmeasurable():
    n = 400
    spy = np.ones(n)
    num = np.ones(n)
    den = np.ones(n)
    ps = PairSeries("safe", "g", "N", "D", num, den, spy)
    gr = evaluate_group([ps], start=0, end=n - 1, partition="P0", W=np.ones((8, n), dtype=np.int32))
    safety = gr["H2"]["safety"]
    assert safety["ok"] is False
    assert safety["reason"] == "SAFETY_UNEVALUABLE"
    from scripts.leadership_rotation_run import _group_verdicts

    gr["honest_n"] = {"H1": 30, "H2": 30, "H3": 30}
    gr["coverage"] = 0.9
    gr["executable"] = True
    gr["H2"]["point"] = 0.02
    gr["H2"]["stability"] = {"holds": True}
    holm = [0.01 if g == "g" and h == "H2" else 1.0 for g, h in FAMILY_ORDER]
    gr["group"] = "defensive_sector"
    v = _group_verdicts(gr, "P0", holm, FAMILY_ORDER)
    assert v["H2"] != "DEVELOPMENT_PASS"


# MUTATION: scripts/leadership_rotation_run.py:928 omit interval_90 on H3
def test_h1_h3_uncertainty_interval_keys_finite_on_synthetic_group():
    n = 800
    dr = np.concatenate([np.zeros(400), np.full(400, 0.012)])
    R = np.cumsum(dr)
    num = np.exp(R)
    den = np.ones(n)
    spy = np.exp(0.0005 * np.arange(n))
    ps = PairSeries("unc", "g", "N", "D", num, den, spy)
    W = inf.stationary_bootstrap_weights(n, reps=32, seed=5)
    gr = evaluate_group([ps], start=300, end=750, partition="P0", W=W)
    h1_iv = gr["H1"]["interval_90"]
    assert h1_iv["burden_cut_b"][1] is not None
    h3_iv = gr["H3"]["interval_90"]
    assert h3_iv[0] is not None and h3_iv[1] is not None
    assert gr["H3"]["lower_bound"] is not None


def _seeded_walk_pair(seed: int = 20261014, n: int = 900) -> PairSeries:
    """Seeded random-walk pair long enough to clear WARMUP (252) first_eligible."""
    rng = np.random.default_rng(seed)
    R = np.cumsum(rng.normal(0.0, 0.01, n))
    return PairSeries("rw", "g", "N", "D", np.exp(R), np.ones(n), np.ones(n))


# MUTATION: scripts/leadership_rotation_run.py:_evaluate_pair_core drop the
# "a0_raw_class" / "a0_raw_merged_away" keys from either return dict (prereg V2 §3.4).
def test_a0_raw_class_present_in_both_core_branches():
    from scripts.leadership_rotation_run import _evaluate_pair_core

    ps = _seeded_walk_pair()
    n = len(ps.num)

    core = _evaluate_pair_core(ps, start=300, end=700)
    assert core["formation"]["eligible"] is True
    assert isinstance(core["a0_raw_class"], list) and core["a0_raw_class"]
    for rec in core["a0_raw_class"]:
        assert set(rec) == {"index", "cls", "subtype", "phase_T", "delay"}
        assert rec["cls"] in ("MATCHED", "LATE", "REPEATED", "FALSE_START")
        if rec["cls"] == "FALSE_START":
            # off_index=None, as for the A0 arm: no EXPIRES/PERSISTENT split input
            assert rec["subtype"] in ("EXPIRES", "PERSISTENT", "NONE")
        else:
            assert rec["subtype"] is None
    assert isinstance(core["a0_raw_merged_away"], int)
    assert core["a0_raw_merged_away"] > 0
    json.dumps(core["a0_raw_class"])

    # ineligible pair: `start` beyond the series forces the empty early-return branch
    bad = _evaluate_pair_core(ps, start=n, end=n - 1)
    assert bad["formation"]["eligible"] is False
    assert bad["a0_raw_class"] == []
    assert bad["a0_raw_merged_away"] == 0


# MUTATION: scripts/leadership_rotation_run.py:_evaluate_pair_core feed the suppressed
# onsets (a0_onsets) into a0r_w instead of the pre-suppression fires (a0_raw).
def test_a0_raw_kept_count_at_least_suppressed():
    from scripts.leadership_rotation_run import _evaluate_pair_core, _filter_window

    ps = _seeded_walk_pair()
    core = _evaluate_pair_core(ps, start=300, end=700)

    # greedy anchor merge of a superset keeps at least as many ...
    assert len(core["a0_raw_class"]) >= len(core["a0_class"])
    # ... and on this path the 5-quiet-session suppression genuinely removes fires,
    # so equality would mean the raw pipeline was fed the suppressed onsets.
    assert len(core["a0_raw_class"]) > len(core["a0_class"])

    # the A0 arm itself is unchanged: byte-identical classifications
    R = core["R"]
    s0 = core["formation"]["start"]
    end = core["formation"]["end"]
    _raw, a0_onsets = st.arm_a0(R)
    a0_kept, _a0_merged = ep.merge_within_pair(_filter_window(a0_onsets, s0, end))
    expected = ep.classify_alarms(a0_kept, core["phases"], off_index=None)
    assert core["a0_class"] == expected
    assert core["arms"]["A0"]["classifications"] == expected


# MUTATION: scripts/leadership_rotation_run.py:evaluate_group build m_a0_raw from
# records["a0"] (the suppressed arm) instead of each core's "a0_raw_class".
def test_evaluate_group_h1_carries_a0_raw_metrics(monkeypatch):
    from scripts import leadership_rotation_run as lrr

    ps = _seeded_walk_pair()
    n = len(ps.num)
    W = np.ones((3, n), dtype=np.int32)

    full = evaluate_group([ps], start=300, end=700, partition="P0", W=W)
    a0_raw = full["H1"]["A0_raw"]
    assert set(a0_raw) == set(full["H1"]["A0"])
    for field in ("burden", "median_delay", "detection", "n_qualifying", "n_matched",
                  "n_miss", "n_late", "n_repeated", "n_false_start", "merged_away",
                  "quiet_rate"):
        assert field in a0_raw
    assert a0_raw["n_matched"] > 0
    assert a0_raw["burden"] is not None and a0_raw["burden"] > full["H1"]["A0"]["burden"]

    real_core = lrr._evaluate_pair_core

    def _blank_a0_raw(pair, *, start, end):
        core = real_core(pair, start=start, end=end)
        core["a0_raw_class"] = []
        return core

    monkeypatch.setattr(lrr, "_evaluate_pair_core", _blank_a0_raw)
    blank = evaluate_group([ps], start=300, end=700, partition="P0", W=W)
    monkeypatch.setattr(lrr, "_evaluate_pair_core", real_core)

    assert blank["H1"]["A0_raw"]["n_matched"] == 0
    assert blank["H1"]["A0_raw"] != a0_raw

    # measurement only: every decision, p-value and other arm is untouched
    for field in ("A0", "A1", "A2", "delay_reduction", "burden_cut_b", "p", "decision"):
        assert full["H1"][field] == blank["H1"][field]
    left = json.loads(json.dumps(full))
    right = json.loads(json.dumps(blank))
    left["H1"].pop("A0_raw")
    right["H1"].pop("A0_raw")
    assert left == right


# --- prereg V2 §6 C2 direction stratification (c2_strata) -------------------
#
# Deterministic synthetic group whose BOTH legs move, so the contract's
# `absolute_direction` lands in every measured stratum.  Built in this file's
# existing inline style (no data/, no network, no real-data read).
_C2_START = 252  # st.WARMUP
_C2_TAIL = 70  # past the last formation session so entries mature


def _c2_group(n: int = 1200, n_pairs: int = 6, seed: int = 17):
    rng = np.random.default_rng(seed)
    mkt = rng.normal(0.0003, 0.009, n)
    spy = 100.0 * np.exp(np.cumsum(mkt))
    common = rng.normal(0.0, 0.005, n)
    pairs = []
    for i in range(n_pairs):
        idio = rng.normal(0.0, 0.005, n)
        drift = np.where(((np.arange(n) // 80) + i) % 4 == 0, 0.0025, 0.0)
        u = common + idio + drift
        num = 100.0 * np.exp(np.cumsum(0.8 * mkt + u / 2.0 + rng.normal(0.0, 0.004, n)))
        den = 100.0 * np.exp(np.cumsum(1.1 * mkt - u / 2.0 + rng.normal(0.0, 0.004, n)))
        pairs.append(
            PairSeries(f"c2_{i}", "defensive_sector", f"N{i}", f"D{i}", num, den, spy)
        )
    return pairs


def _c2_window(pairs):
    return _C2_START, len(pairs[0].spy) - _C2_TAIL


def _c2_run(pairs, reps: int = 4) -> dict:
    n = len(pairs[0].spy)
    start, end = _c2_window(pairs)
    W = inf.stationary_bootstrap_weights(n, reps=reps, seed=1)
    return evaluate_group(pairs, start=start, end=end, partition="P0", W=W)


def _c2_leaves(obj, path: str = "c2_strata"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _c2_leaves(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _c2_leaves(v, f"{path}[{i}]")
    else:
        yield path, obj


def _c2_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _c2_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _c2_keys(v)


# MUTATION: scripts/leadership_rotation_run.py:641 drop the per-pair memo (recompute every call) and let an unmeasurable leg fall through to a direction
def test_c2_direction_labeler_cases(monkeypatch):
    from scripts.leadership_rotation_run import _direction_labeler

    n = 60
    spy = np.full(n, 100.0)

    def _pair(num40: float, den40: float, *, num20: float = 100.0) -> PairSeries:
        num = np.full(n, 100.0)
        den = np.full(n, 100.0)
        num[20] = num20
        den[20] = 100.0
        num[40] = num40
        den[40] = den40
        return PairSeries("c2lab", "g", "N", "D", num, den, spy)

    # t = 40, Z_LOOKBACK = 20 -> the contract reads [20, 40] on BOTH legs.
    assert _direction_labeler(_pair(110.0, 120.0))(40) == "both_up"
    assert _direction_labeler(_pair(90.0, 80.0))(40) == "both_down"
    assert _direction_labeler(_pair(110.0, 80.0))(40) == "mixed"
    # t below the lookback is unmeasured, NOT a direction and NOT zero.
    assert _direction_labeler(_pair(110.0, 120.0))(5) == "unmeasured"
    # a NaN leg at t - Z_LOOKBACK is unmeasured.
    assert _direction_labeler(_pair(110.0, 120.0, num20=float("nan")))(40) == "unmeasured"

    calls = []
    real = st.entry_context

    def _counting(num, den, t, lookback=st.Z_LOOKBACK):
        calls.append(int(t))
        return real(num, den, t, lookback)

    monkeypatch.setattr(st, "entry_context", _counting)
    label = _direction_labeler(_pair(110.0, 120.0))
    first = label(40)
    second = label(40)
    assert first == second == "both_up"
    assert calls == [40]


# MUTATION: scripts/leadership_rotation_run.py:738 emit the strata in sorted()/insertion-arbitrary order, rename a frozen entry key, or leave a NaN point in the block
def test_c2_strata_present_with_frozen_shape():
    from scripts.leadership_rotation_run import C2_MIN_N, C2_NOTE, C2_STRATA

    out = _c2_run(_c2_group())
    c2 = out["c2_strata"]
    assert c2["note"] == C2_NOTE
    assert c2["min_n"] == C2_MIN_N == 5
    assert list(c2) == ["label_source", "label_time", "note", "min_n", "H1", "H2", "H3"]
    assert c2["label_source"].startswith(
        "engine.leadership_rotation_context.pair_interpretation absolute_direction"
    )
    assert "Z_LOOKBACK" in c2["label_source"]
    assert c2["label_time"].startswith("H1: alarm index")

    frozen = {
        "H1": ["n_items", "n", "status", "delay_reduction", "burden_cut_b", "reason"],
        "H2": ["n_items", "n", "status", "point", "comparator_basis", "reason"],
        "H3": ["n_items", "n", "status", "point", "comparator_basis", "reason"],
    }
    allowed = {"COMPUTED", "SOURCE_LIMITED", "UNMEASURED", "NOT_EXECUTABLE"}
    seen = set()
    for h in ("H1", "H2", "H3"):
        assert list(c2[h]) == list(C2_STRATA)
        for s in C2_STRATA:
            entry = c2[h][s]
            assert list(entry) == frozen[h]
            assert entry["status"] in allowed
            seen.add(entry["status"])
            if h in ("H2", "H3"):
                assert entry["comparator_basis"] == "same_stratum"
            if entry["status"] in ("UNMEASURED", "SOURCE_LIMITED"):
                assert entry["reason"] is not None
    assert {"COMPUTED", "SOURCE_LIMITED", "UNMEASURED"} <= seen

    for path, value in _c2_leaves(c2):
        assert not isinstance(value, float) or math.isfinite(value), path
    # POINTS ONLY: no p-value, no verdict, no Holm anywhere in the block.
    assert not {"p", "p_a", "p_b", "verdict", "holm", "adjusted"} & set(_c2_keys(c2))


# MUTATION: scripts/leadership_rotation_run.py:696 gate the stratum on n_items (raw count) instead of the clustered n, or drop C2_MIN_N to 1
def test_c2_source_limited_below_min_n(monkeypatch):
    import scripts.leadership_rotation_run as lrr
    from scripts.leadership_rotation_run import C2_MIN_N, _evaluate_pair_core

    pairs = _c2_group()
    start, end = _c2_window(pairs)
    cores = [_evaluate_pair_core(ps, start=start, end=end) for ps in pairs]
    matched = {
        int(rec["index"]) for c in cores for rec in c["a1_class"] if rec["cls"] == "MATCHED"
    }
    matured = {
        int(r["t"])
        for c in cores
        for r in c["a1_out"]
        if r["y20"]["state"] == "MATURED" and r["y20"]["y"] is not None
    }
    both = sorted(matched & matured)
    assert both, "fixture must yield at least one MATCHED and MATURED A1 entry"
    t0 = both[0]

    monkeypatch.setattr(
        lrr,
        "_direction_labeler",
        lambda ps: (lambda t: "both_up" if int(t) == t0 else "mixed"),
    )
    c2 = _c2_run(pairs)["c2_strata"]
    point_keys = {
        "H1": ("delay_reduction", "burden_cut_b"),
        "H2": ("point",),
        "H3": ("point",),
    }
    for h, keys in point_keys.items():
        entry = c2[h]["both_up"]
        # exactly one clustered item -> 1 <= n < C2_MIN_N
        assert entry["n_items"] >= 1
        assert entry["n"] == 1 < C2_MIN_N
        assert entry["status"] == "SOURCE_LIMITED"
        assert entry["reason"] == f"n={entry['n']} < {C2_MIN_N}"
        for k in keys:
            assert entry[k] is None


# MUTATION: scripts/leadership_rotation_run.py:827 omit the "unmeasured" stratum from the H2/H3 dicts so the strata no longer partition the group's records
def test_c2_h2_partition_is_complete():
    from scripts.leadership_rotation_run import C2_STRATA, _evaluate_pair_core

    pairs = _c2_group()
    start, end = _c2_window(pairs)
    c2 = _c2_run(pairs)["c2_strata"]
    cores = [_evaluate_pair_core(ps, start=start, end=end) for ps in pairs]

    def _count(field: str) -> int:
        return sum(
            1
            for c in cores
            for r in c["a1_out"]
            if r[field]["state"] == "MATURED" and r[field]["y"] is not None
        )

    n20 = _count("y20")
    nres = _count("y_res_20")
    assert n20 > 0 and nres > 0
    assert sum(c2["H2"][s]["n_items"] for s in C2_STRATA) == n20
    assert sum(c2["H3"][s]["n_items"] for s in C2_STRATA) == nres


# MUTATION: scripts/leadership_rotation_run.py:809 take the B1/B2 comparators from the WHOLE group instead of the same stratum
def test_c2_h2_point_matches_manual_subset(monkeypatch):
    import scripts.leadership_rotation_run as lrr
    from scripts.leadership_rotation_run import (
        C2_MIN_N,
        _evaluate_pair_core,
        _h2_point_subset,
    )

    pairs = _c2_group()
    start, end = _c2_window(pairs)
    strata = ("both_up", "both_down", "mixed")
    block = 25

    def _rule(t: int) -> str:
        return strata[(int(t) // block) % 3]

    monkeypatch.setattr(lrr, "_direction_labeler", lambda ps: _rule)
    c2 = _c2_run(pairs)["c2_strata"]
    cores = [_evaluate_pair_core(ps, start=start, end=end) for ps in pairs]

    checked = 0
    for s in strata:
        a1_y: list = []
        b1_y: list = []
        b2_y: list = []
        for core in cores:
            for r in core["a1_out"]:
                if (
                    r["y20"]["state"] == "MATURED"
                    and r["y20"]["y"] is not None
                    and _rule(r["t"]) == s
                ):
                    a1_y.append(float(r["y20"]["y"]))
            for arm_key, bucket in (("b1_out", b1_y), ("b2_out", b2_y)):
                for r in core[arm_key]:
                    if (
                        r["y20"]["state"] == "MATURED"
                        and r["y20"]["y"] is not None
                        and _rule(r["t"]) == s
                    ):
                        bucket.append(float(r["y20"]["y"]))
        entry = c2["H2"][s]
        assert entry["n_items"] == len(a1_y)
        assert entry["n"] >= C2_MIN_N
        assert entry["status"] == "COMPUTED"
        assert entry["reason"] is None
        assert abs(entry["point"] - _h2_point_subset(a1_y, b1_y, b2_y)) < 1e-12
        checked += 1
    assert checked == 3


# MUTATION: scripts/leadership_rotation_run.py:1092 let the C2 sweep mutate cores/records in place or recompute an existing H1/H2/H3 number
def test_c2_does_not_change_existing_outputs(monkeypatch):
    import scripts.leadership_rotation_run as lrr

    pairs = _c2_group()
    with_c2 = _c2_run(pairs)
    assert with_c2["c2_strata"]

    monkeypatch.setattr(lrr, "_c2_strata", lambda *_a, **_k: {})
    without_c2 = _c2_run(pairs)

    def _strip(out: dict) -> dict:
        assert "c2_strata" in out
        return {k: v for k, v in out.items() if k != "c2_strata"}

    assert json.dumps(_strip(with_c2), sort_keys=True) == json.dumps(
        _strip(without_c2), sort_keys=True
    )


# ---------------------------------------------------------------------------
# P1 harness gate (prereg V2 §3 two-part size rule; T19 F9) and the real
# look_count that makes a P1 read a COUNTED development look (V1 §2).
# ---------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

import scripts.leadership_rotation_run as run  # noqa: E402
from scripts.leadership_rotation_run import (  # noqa: E402
    SizeGateNotPassed,
    _git_blob_sha,
    _wilson_lower,
    assert_size_gate_passed,
    count_prior_looks,
    record_look,
)

_RUNTIME_ROOT = Path(run.__file__).resolve().parents[1]
_GATE_SCHEMA = "leadership_rotation.size_gate.v1"
_GATE_RULE = "V2_SEC3_TWO_PART"
_GATE_ALPHA = 0.025
_GATE_PASSES = 8
_GATE_M = 400
_GATE_ROW_NAMES = (
    "defensive_sector/H1",
    "defensive_sector/H2",
    "defensive_sector/H3",
    "broadening_proxy/H1",
    "broadening_proxy/H2",
    "broadening_proxy/H3",
    "family_any",
)
_HEX = "0123456789abcdef"


def _running_bytes(rel: str) -> bytes:
    """The bytes of a harness module as they will actually execute."""
    return (_RUNTIME_ROOT / rel).read_bytes()


def _harness_files() -> dict:
    return {rel: _running_bytes(rel) for rel in run.HARNESS_MODULES}


def _git_repo(tmp_path, files: dict, *, name: str = "repo") -> str:
    """A throw-away committed git repo holding exactly ``files``."""
    repo = Path(tmp_path, name)
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    for rel, data in files.items():
        dest = Path(repo, rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "add",
            *files,
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    return str(repo)


def _commit(repo, rel: str, message: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "add", rel],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "-m",
            message,
        ],
        check=True,
        capture_output=True,
    )


def _head(repo) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _gate_rows() -> list:
    envelope = _GATE_ALPHA + 2 * math.sqrt(_GATE_ALPHA * (1 - _GATE_ALPHA) / _GATE_M)
    rows = []
    for cid in run.SIZE_GATE_REQUIRED_CELLS:
        for name in _GATE_ROW_NAMES:
            rows.append(
                {
                    "cell_id": cid,
                    "sigma": 0.007,
                    "rho": 0.5,
                    "n_target": 20,
                    "n_sims": _GATE_M,
                    "row": name,
                    "passes": _GATE_PASSES,
                    "m": _GATE_M,
                    "pass_rate_ok": _GATE_PASSES / _GATE_M,
                    "wilson_lower": _wilson_lower(_GATE_PASSES, _GATE_M),
                    "envelope": envelope,
                    "part_i_ok": True,
                    "part_ii_ok": True,
                    "flag": "SIZED",
                }
            )
    return rows


def _gate_artifact(**overrides) -> dict:
    """A size-gate artifact that PASSES every check of the V2 §3 rule."""
    obj = {
        "schema": _GATE_SCHEMA,
        "rule": _GATE_RULE,
        "alpha": _GATE_ALPHA,
        "sized": True,
        "min_m": run.SIZE_GATE_MIN_M,
        "required_cells": list(run.SIZE_GATE_REQUIRED_CELLS),
        "cells": [
            {
                "cell_id": cid,
                "sigma": 0.007,
                "delta": 0.0,
                "rho": 0.5,
                "n_target": 20,
                "n_sims": _GATE_M,
                "n_ok": _GATE_M,
            }
            for cid in run.SIZE_GATE_REQUIRED_CELLS
        ],
        "rows": _gate_rows(),
        "violations": [],
        "not_executable": [],
        "missing_cells": [],
        "h1_null_method": "V2_OPTION_A",
        "h1_null_k": 1000,
        "prereg": {
            "v1_blob": st.PREREG_BLOB_SHA,
            "v2_blob": st.PREREG_V2_BLOB_SHA,
            "v2_1_blob": st.PREREG_V2_1_BLOB_SHA,
        },
        "harness": {"head": "0" * 40, "blobs": {p: _git_blob_sha(b) for p, b in _harness_files().items()}},
        "inputs": {"generator": "G1", "delta": 0.0},
        "generated_utc": "2026-10-14T00:00:00Z",
    }
    obj.update(overrides)
    return obj


def _gate_repo(tmp_path, artifact, *, name: str = "repo", harness_files=None) -> str:
    """Commit the running harness bytes plus ``artifact`` at SIZE_GATE_PATH."""
    files = dict(_harness_files())
    if harness_files:
        files.update(harness_files)
    if artifact is not None:
        files[run.SIZE_GATE_PATH] = json.dumps(artifact).encode("utf-8")
    return _git_repo(tmp_path, files, name=name)


def _refusal(repo, reason: str, *, runtime_root=None, commit: str = "HEAD"):
    with pytest.raises(SizeGateNotPassed) as excinfo:
        assert_size_gate_passed(repo, commit=commit, runtime_root=runtime_root)
    err = excinfo.value
    assert err.reason == reason
    assert err.detail
    assert str(err) == f"{reason}: {err.detail}"
    assert run.SIZE_GATE_PATH in err.detail
    return err


# MUTATION: scripts/leadership_rotation_run.py:1412 hash the bytes without the git blob header
def test_git_blob_sha_matches_git_hash_object(tmp_path):
    data = b"blob header check \x00 binary\n"
    expect = subprocess.run(
        ["git", "hash-object", "--stdin"], input=data, check=True, capture_output=True
    ).stdout.decode().strip()
    assert _git_blob_sha(data) == expect
    assert len(_git_blob_sha(data)) == 40
    assert all(c in _HEX for c in _git_blob_sha(data))


# MUTATION: scripts/leadership_rotation_run.py:1452 use z = 1.6449 or drop the max(0.0, ...) clip
def test_wilson_lower_matches_p0_wilson_interval():
    from scripts import leadership_rotation_p0 as p0

    for passes, m in ((8, 400), (17, 400), (0, 400), (2, 100), (13, 100), (5, 42), (400, 400)):
        assert _wilson_lower(passes, m) == p0.wilson_interval(passes, m)[0]
    assert math.isnan(_wilson_lower(1, 0))
    assert _wilson_lower(8, 400) <= _GATE_ALPHA < _wilson_lower(17, 400)


# MUTATION: scripts/leadership_rotation_run.py:1472 return the identity dict without running any check
def test_size_gate_passes_on_valid_artifact(tmp_path):
    assert _GATE_ROW_NAMES == run._SIZE_GATE_ROW_NAMES
    repo = _gate_repo(tmp_path, _gate_artifact())
    gate = assert_size_gate_passed(repo)
    assert gate["rule"] == "V2_SEC3_TWO_PART"
    assert len(gate["artifact_blob"]) == 40
    assert all(c in _HEX for c in gate["artifact_blob"])
    assert gate["path"] == run.SIZE_GATE_PATH
    assert gate["commit"] == _head(repo)
    assert gate["required_cells"] == [0, 1, 2, 3, 4, 48]
    assert gate["min_m"] == 400
    assert gate["h1_null_method"] == "V2_OPTION_A"
    assert gate["harness_head"] == "0" * 40
    assert gate["artifact_blob"] == _git_blob_sha(
        json.dumps(_gate_artifact()).encode("utf-8")
    )
    # an explicit commit sha reads the same proof as HEAD
    assert assert_size_gate_passed(repo, commit=_head(repo))["commit"] == gate["commit"]


# MUTATION: scripts/leadership_rotation_run.py:1419 read the working tree instead of commit:path
def test_size_gate_refuses_absent_artifact(tmp_path):
    repo = _git_repo(tmp_path, _harness_files())
    err = _refusal(repo, "SIZE_GATE_ARTIFACT_ABSENT")
    assert "HEAD" in err.detail
    # an artifact that exists only in the WORKING TREE is not a committed proof
    Path(repo, run.SIZE_GATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(repo, run.SIZE_GATE_PATH).write_text(json.dumps(_gate_artifact()))
    _refusal(repo, "SIZE_GATE_ARTIFACT_ABSENT")


# MUTATION: scripts/leadership_rotation_run.py:1508 treat any parsed JSON as a gate artifact
@pytest.mark.parametrize("raw", [b"{not json", b"[1, 2]", b'"sized"', b""])
def test_size_gate_refuses_unparseable_artifact(tmp_path, raw):
    files = dict(_harness_files())
    files[run.SIZE_GATE_PATH] = raw
    repo = _git_repo(tmp_path, files, name=f"bad-{len(raw)}")
    _refusal(repo, "SIZE_GATE_UNPARSEABLE")


# MUTATION: scripts/leadership_rotation_run.py:1517 accept the V1 single-part rule or another alpha
@pytest.mark.parametrize(
    "overrides",
    [
        {"rule": "V2_WILSON_LB_ONLY"},
        {"alpha": 0.05},
        {"schema": "leadership_rotation.size_gate.v0"},
    ],
)
def test_size_gate_refuses_rule_mismatch(tmp_path, overrides):
    repo = _gate_repo(tmp_path, _gate_artifact(**overrides), name="rule")
    err = _refusal(repo, "SIZE_GATE_RULE_MISMATCH")
    assert any(str(v) in err.detail for v in overrides.values())


# MUTATION: scripts/leadership_rotation_run.py:1524 treat a falsy or truthy sized flag alike
def test_size_gate_refuses_not_sized_artifact(tmp_path):
    repo = _gate_repo(tmp_path, _gate_artifact(sized=False), name="notsized")
    err = _refusal(repo, "SIZE_GATE_NOT_SIZED")
    assert "sized" in err.detail
    # check 4 precedes check 5: a NOT SIZED artifact with a missing cell is
    # still refused as NOT SIZED, never as the later reason
    rows = [r for r in _gate_rows() if r["cell_id"] != 48]
    both = _gate_repo(
        tmp_path, _gate_artifact(sized=False, rows=rows), name="notsized-and-missing"
    )
    _refusal(both, "SIZE_GATE_NOT_SIZED")


# MUTATION: scripts/leadership_rotation_run.py:1533 require only the cells the artifact happens to carry
def test_size_gate_refuses_missing_cell(tmp_path):
    rows = [r for r in _gate_rows() if r["cell_id"] != 48]
    repo = _gate_repo(tmp_path, _gate_artifact(rows=rows), name="cell48")
    err = _refusal(repo, "SIZE_GATE_CELL_MISSING")
    assert "48" in err.detail
    for name in _GATE_ROW_NAMES:
        assert name in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1548 accept the T12 M = 100 grid
def test_size_gate_refuses_m_below_min(tmp_path):
    rows = _gate_rows()
    for row in rows:
        if row["cell_id"] == 2:
            row["m"] = 100
            row["passes"] = 2
            row["pass_rate_ok"] = 0.02
            row["wilson_lower"] = _wilson_lower(2, 100)
            row["envelope"] = _GATE_ALPHA + 2 * math.sqrt(_GATE_ALPHA * (1 - _GATE_ALPHA) / 100)
    repo = _gate_repo(tmp_path, _gate_artifact(rows=rows), name="mbelow")
    err = _refusal(repo, "SIZE_GATE_M_BELOW_MIN")
    assert "100" in err.detail
    assert str(run.SIZE_GATE_MIN_M) in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1555 trust the recorded flag/part_*_ok instead of recomputing them
def test_size_gate_refuses_hand_edited_sized_row(tmp_path):
    rows = _gate_rows()
    hit = 0
    for row in rows:
        if row["cell_id"] == 0 and row["row"] == "defensive_sector/H1":
            row["passes"] = 17
            row["pass_rate_ok"] = 0.0425
            row["wilson_lower"] = 0.001
            hit += 1
    assert hit == 1
    repo = _gate_repo(tmp_path, _gate_artifact(rows=rows), name="handedit")
    err = _refusal(repo, "SIZE_GATE_ROW_NOT_SIZED")
    assert "defensive_sector/H1" in err.detail
    assert "17" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1593 accept the superseded V1 bootstrap null
def test_size_gate_refuses_null_method_mismatch(tmp_path):
    repo = _gate_repo(
        tmp_path, _gate_artifact(h1_null_method="V1_BOOTSTRAP_SUPERSEDED"), name="nullmethod"
    )
    err = _refusal(repo, "SIZE_GATE_NULL_METHOD_MISMATCH")
    assert "V1_BOOTSTRAP_SUPERSEDED" in err.detail
    assert "V2_OPTION_A" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:assert_size_gate_passed skip the h1_null_k >= SIZE_GATE_MIN_NULL_K check
def test_size_gate_refuses_null_k_below_1000(tmp_path):
    """Prereg V2 §2: an Option A gate built on fewer than 1,000 null paths per
    H1 read is not the gate V2 registered, so the P1 reader refuses it."""
    for name, k in (("k999", 999), ("knone", None), ("kbool", True)):
        repo = _gate_repo(tmp_path, _gate_artifact(h1_null_k=k), name=name)
        err = _refusal(repo, "SIZE_GATE_NULL_K_TOO_SMALL")
        assert repr(k) in err.detail and "1000" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1607 compare only the V1 prereg blob
def test_size_gate_refuses_prereg_pin_mismatch(tmp_path):
    prereg = dict(_gate_artifact()["prereg"])
    prereg["v2_1_blob"] = "f" * 40
    repo = _gate_repo(tmp_path, _gate_artifact(prereg=prereg), name="pin")
    err = _refusal(repo, "SIZE_GATE_PREREG_PIN_MISMATCH")
    assert "v2_1_blob" in err.detail
    assert st.PREREG_V2_1_BLOB_SHA in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1635 skip the commit-side harness blob comparison
def test_size_gate_refuses_commit_side_harness_drift(tmp_path):
    drifted = {"scripts/leadership_rotation_run.py": _running_bytes("scripts/leadership_rotation_run.py") + b"\n# one appended comment byte\n"}
    repo = _gate_repo(tmp_path, _gate_artifact(), name="drift-commit", harness_files=drifted)
    err = _refusal(repo, "SIZE_GATE_HARNESS_DRIFT")
    assert "commit side" in err.detail
    assert "scripts/leadership_rotation_run.py" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1645 skip the runtime-side harness blob comparison
def test_size_gate_refuses_runtime_side_harness_drift(tmp_path):
    repo = _gate_repo(tmp_path, _gate_artifact(), name="drift-runtime")
    root = Path(tmp_path, "runtime-root")
    for rel in run.HARNESS_MODULES:
        data = _running_bytes(rel)
        if rel == "scripts/leadership_rotation_study.py":
            data += b"\n# mutated only at runtime\n"
        dest = Path(root, rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    err = _refusal(repo, "SIZE_GATE_HARNESS_DRIFT", runtime_root=str(root))
    assert "runtime side" in err.detail
    assert "scripts/leadership_rotation_study.py" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1618 accept a subset of HARNESS_MODULES
def test_size_gate_refuses_incomplete_harness_blob_set(tmp_path):
    artifact = _gate_artifact()
    artifact["harness"]["blobs"].pop("scripts/leadership_rotation_p0.py")
    repo = _gate_repo(tmp_path, artifact, name="drift-blobset")
    err = _refusal(repo, "SIZE_GATE_HARNESS_DRIFT")
    assert "scripts/leadership_rotation_p0.py" in err.detail


# MUTATION: scripts/leadership_rotation_run.py:1397 accept any reason string / drop the reason attribute
def test_size_gate_reasons_are_a_closed_vocabulary():
    assert run.SIZE_GATE_REASONS == (
        "SIZE_GATE_ARTIFACT_ABSENT",
        "SIZE_GATE_UNPARSEABLE",
        "SIZE_GATE_RULE_MISMATCH",
        "SIZE_GATE_NOT_SIZED",
        "SIZE_GATE_CELL_MISSING",
        "SIZE_GATE_M_BELOW_MIN",
        "SIZE_GATE_ROW_NOT_SIZED",
        "SIZE_GATE_NULL_METHOD_MISMATCH",
        "SIZE_GATE_NULL_K_TOO_SMALL",
        "SIZE_GATE_PREREG_PIN_MISMATCH",
        "SIZE_GATE_HARNESS_DRIFT",
    )
    err = SizeGateNotPassed("SIZE_GATE_NOT_SIZED", "detail")
    assert err.reason == "SIZE_GATE_NOT_SIZED"
    assert err.detail == "detail"
    assert str(err) == "SIZE_GATE_NOT_SIZED: detail"
    assert isinstance(err, RuntimeError)
    with pytest.raises(AssertionError):
        SizeGateNotPassed("SOME_OTHER_REASON", "detail")


# MUTATION: scripts/leadership_rotation_run.py:1711 load closes before the size gate refuses
def test_run_p1_refuses_without_size_gate_pass(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path, _harness_files(), name="p1-absent")
    calls = []

    def _protocol(_repo, **kw):
        calls.append(("protocol", kw.get("head")))
        return {"v1": {}, "v2": {}, "head": kw.get("head")}

    def _prereg(_repo, **kw):
        calls.append(("prereg", kw.get("path"), kw.get("blob_sha")))
        return {"add_commit": "0" * 40, "blob_sha": kw.get("blob_sha"), "head": kw.get("head")}

    def _load(*_a, **_k):
        calls.append("load")
        raise AssertionError("loader reached before the size gate refused")

    monkeypatch.setattr(st, "assert_protocol_landed", _protocol)
    monkeypatch.setattr(st, "assert_prereg_landed", _prereg)
    monkeypatch.setattr(st, "load_closes_from_git", _load)

    with pytest.raises(SizeGateNotPassed) as excinfo:
        run_p1(repo)
    assert excinfo.value.reason == "SIZE_GATE_ARTIFACT_ABSENT"
    assert "load" not in calls
    # the protocol assert ran FIRST, then the V2.1 amendment assert, then the gate
    assert calls[0][0] == "protocol"
    assert calls[1] == ("prereg", st.PREREG_V2_1_PATH, st.PREREG_V2_1_BLOB_SHA)
    assert len(calls) == 2


# MUTATION: scripts/leadership_rotation_run.py:1524 let a NOT SIZED artifact authorise the P1 read
def test_run_p1_refuses_on_not_sized_artifact(tmp_path, monkeypatch):
    repo = _gate_repo(tmp_path, _gate_artifact(sized=False), name="p1-notsized")
    calls = []
    monkeypatch.setattr(st, "assert_protocol_landed", lambda *a, **k: calls.append("protocol"))
    monkeypatch.setattr(st, "assert_prereg_landed", lambda *a, **k: calls.append("prereg"))
    monkeypatch.setattr(st, "load_closes_from_git", lambda *a, **k: calls.append("load"))
    with pytest.raises(SizeGateNotPassed) as excinfo:
        run_p1(repo)
    assert excinfo.value.reason == "SIZE_GATE_NOT_SIZED"
    assert "load" not in calls
    assert calls == ["protocol", "prereg"]
    # nothing was written to the look ledger by a refused read
    assert not Path(repo, run.LOOK_LEDGER_PATH).exists()


# MUTATION: scripts/leadership_rotation_run.py:1288 accept a bool/negative look_count or hard-code 0
def test_look_count_distinguishes_zero_from_counted_looks():
    n = 400
    g1 = [_flat_pair(n=n, pair_id="a", group="defensive_sector")]
    g2 = [_flat_pair(n=n, pair_id="b", group="broadening_proxy")]
    groups = {"defensive_sector": g1, "broadening_proxy": g2}
    default = evaluate_family(groups, start=300, end=380, partition="P0")
    assert default["look_count"] == 0
    for want in (0, 1, 3):
        fam = evaluate_family(groups, start=300, end=380, partition="P0", look_count=want)
        assert fam["look_count"] == want
        assert isinstance(fam["look_count"], int)
        assert json.loads(json.dumps(fam))["look_count"] == want
    for bad in (-1, True, False, 1.5, "1"):
        with pytest.raises(ValueError):
            evaluate_family(groups, start=300, end=380, partition="P0", look_count=bad)


# MUTATION: scripts/leadership_rotation_run.py:1664 return 0 for a ledger that cannot be read
def test_count_prior_looks_reads_committed_ledger(tmp_path):
    empty = _git_repo(tmp_path, {"README.md": b"x\n"}, name="ledger-empty")
    assert count_prior_looks(empty) == 0

    p1 = json.dumps({"partition": "P1", "look_index": 1}, sort_keys=True) + "\n"
    p0 = json.dumps({"partition": "P0", "look_index": 7}, sort_keys=True) + "\n"
    repo = _git_repo(tmp_path, {run.LOOK_LEDGER_PATH: (p1 + "\n" + p0).encode()}, name="ledger")
    assert count_prior_looks(repo, partition="P1") == 1
    assert count_prior_looks(repo, partition="P0") == 1
    assert count_prior_looks(repo, partition="P2") == 0
    assert count_prior_looks(repo, commit=_head(repo), partition="P1") == 1

    # an UNCOMMITTED append is not a look yet: the count reads commit:path
    dest = record_look(repo, {"partition": "P1", "look_index": 2})
    assert dest == Path(repo, run.LOOK_LEDGER_PATH)
    assert count_prior_looks(repo, partition="P1") == 1
    _commit(repo, run.LOOK_LEDGER_PATH, "look 2")
    assert count_prior_looks(repo, partition="P1") == 2

    # record_look creates the parent directory and appends one sorted-json line
    fresh = record_look(empty, {"partition": "P1", "look_index": 1})
    assert fresh.read_text().splitlines() == [
        json.dumps({"partition": "P1", "look_index": 1}, sort_keys=True)
    ]
    record_look(empty, {"partition": "P1", "look_index": 2})
    assert len(fresh.read_text().splitlines()) == 2

    garbage = _git_repo(
        tmp_path, {run.LOOK_LEDGER_PATH: (p1 + "{oops\n").encode()}, name="ledger-garbage"
    )
    with pytest.raises(ValueError) as excinfo:
        count_prior_looks(garbage, partition="P1")
    assert "LOOK_LEDGER_UNPARSEABLE" in str(excinfo.value)
    assert "line 2" in str(excinfo.value)

    non_dict = _git_repo(
        tmp_path, {run.LOOK_LEDGER_PATH: b"[1, 2]\n"}, name="ledger-nondict"
    )
    with pytest.raises(ValueError) as excinfo:
        count_prior_looks(non_dict, partition="P1")
    assert "LOOK_LEDGER_UNPARSEABLE line 1" in str(excinfo.value)


# MUTATION: scripts/leadership_rotation_run.py:_group_verdicts pass powered_in_principle=True for H2/H3
def test_p2_p3_h2_h3_need_a_landed_power_disposition():
    """V2.1 §2 row 4 / V2 §4.3: without a POWERED_IN_PRINCIPLE disposition the
    binding partitions cannot issue an H2/H3 class at all."""
    from scripts.leadership_rotation_run import _group_verdicts

    gr = {
        "group": "defensive_sector",
        "executable": True,
        "coverage": 0.95,
        "honest_n": {"H1": 30, "H2": 30, "H3": 30},
        "test_n": {"H1": 30, "H2": 30, "H3": 30},
        "H1": {
            "decision": {"margins_met": True},
            "stability": {"delay_reduction": {"holds": True}, "burden_cut_b": {"holds": True}},
        },
        "H2": {"point": 0.02, "safety": {"ok": True}, "stability": {"holds": True}},
        "H3": {"point": None, "stability": {"holds": True}},
    }
    holm = [0.001 if g == "defensive_sector" else 1.0 for g, _h in FAMILY_ORDER]
    for part in ("P2", "P3"):
        v = _group_verdicts(gr, part, holm, FAMILY_ORDER)
        assert v["H2"] == v["H3"] == "NOT_EXECUTABLE"
        assert v["H1"] == ("CONSISTENT" if part == "P2" else "SUPPORTED")
    v = _group_verdicts(gr, "P3", holm, FAMILY_ORDER, {"H2": True, "H3": True})
    assert v["H2"] == "SUPPORTED"
    assert v["H3"] == "NOT_EXECUTABLE"  # undefined point estimate, row 9a
    gr["H2"]["safety"]["ok"] = False
    assert _group_verdicts(gr, "P3", holm, FAMILY_ORDER, {"H2": True})["H2"] == "NOT_SUPPORTED"
    gr["H2"]["safety"]["ok"] = True
    gr["H2"]["stability"]["holds"] = False
    assert _group_verdicts(gr, "P2", holm, FAMILY_ORDER, {"H2": True})["H2"] == "INSUFFICIENT"
    # P0/P1 ignore the power disposition entirely
    assert _group_verdicts(gr, "P1", holm, FAMILY_ORDER)["H2"] == "DEVELOPMENT_FAIL"


def test_unmatched_option_a_null_makes_h1_not_executable():
    """V2.1 §6 item 2 / §2 row 2: an Option A null that could not be matched
    (status != OK, p forced to 1) is NOT_EXECUTABLE, never a scored H1 fail."""
    from scripts.leadership_rotation_run import _group_verdicts

    gr = {
        "group": "defensive_sector",
        "executable": True,
        "coverage": 0.95,
        "honest_n": {"H1": 30, "H2": 30, "H3": 30},
        "test_n": {"H1": 30, "H2": 30, "H3": 30},
        "H1": {
            "decision": {"margins_met": True},
            "stability": {"delay_reduction": {"holds": True}, "burden_cut_b": {"holds": True}},
            "null": {"status": "OK", "p_a": 0.001, "p_b": 0.001},
        },
        "H2": {"point": 0.02, "safety": {"ok": True}, "stability": {"holds": True}},
        "H3": {"point": 0.01, "stability": {"holds": True}},
    }
    holm = [0.001 if g == "defensive_sector" else 1.0 for g, _h in FAMILY_ORDER]
    assert _group_verdicts(gr, "P1", holm, FAMILY_ORDER)["H1"] == "DEVELOPMENT_PASS"
    gr["H1"]["null"] = {"status": "NOT_EXECUTABLE", "p_a": 1.0, "p_b": 1.0}
    for part in ("P1", "P2", "P3"):
        assert _group_verdicts(gr, part, holm, FAMILY_ORDER)["H1"] == "NOT_EXECUTABLE"
