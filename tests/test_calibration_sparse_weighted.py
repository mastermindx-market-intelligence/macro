from __future__ import annotations

"""Hermetic tests for the Q06 research reference (engine/calibration_sparse_weighted.py).

All data is synthetic and indexed by integers. The tests make no repository
reads, no network calls and no wall-clock reads.
"""

import importlib
import math
import sys

import numpy as np
import pytest

import engine.calibration_sparse_weighted as csw


def _brute_native(fill, end, roots):
    """Independent brute-force statement of the frozen §4.4 law, used as an oracle."""
    units = {}
    for i, (f, e, r) in enumerate(zip(fill, end, roots)):
        units.setdefault((f, r), []).append((i, e))
    horizon = max(end) + 1
    conc = [0] * horizon
    for (f, _r), members in units.items():
        e = members[0][1]
        for t in range(f, e + 1):
            conc[t] += 1
    out = [0.0] * len(fill)
    for (f, _r), members in units.items():
        e = members[0][1]
        u = math.fsum(1.0 / conc[t] for t in range(f, e + 1)) / (e - f + 1)
        for i, _e in members:
            out[i] = u / len(members)
    return out


# ── requirement 1: ties, unequal weights, empty cells, monotonicity tolerance ──

def test_req1_ties_unequal_weights_empty_cells_and_tolerance_are_specified():
    p = np.array([0.2, 0.2, 0.2, 0.4, 0.4, 0.6, 0.8, 0.8, 0.5])
    w = np.array([0.5, 0.25, 0.25, 1.0, 0.0, 2.0, 0.1, 0.9, 0.0])
    y = np.array([0, 1, 0, 1, 1, 1, 1, 0, 1], dtype=float)
    groups = csw.tie_groups(p, w, y)
    # Zero-weight rows are dropped and counted. The 0.5 group vanishes.
    assert groups.zero_weight_rows == 2
    assert groups.p.tolist() == [0.2, 0.4, 0.6, 0.8]
    assert groups.weight.tolist() == [1.0, 1.0, 2.0, 1.0]
    # Whole ties are never split: every retained row of a tie maps to one group.
    assert set(groups.row_group[:3].tolist()) == {0}

    # Exact DP with a lexicographic tie-break: [1, 2, 1] into 2 bins has two
    # equal-cost partitions, and the smaller cut vector wins.
    assert csw.whole_tie_partition([1.0, 2.0, 1.0], n_bins=2) == [0, 1]
    # B = min(n_bins, G): with three groups and ten bins requested, three bins form.
    assert csw.whole_tie_partition([1.0, 1.0, 1.0], n_bins=10) == [0, 1, 2]
    # The DP is optimal against brute force on a small instance.
    wts = [3.0, 1.0, 1.0, 4.0, 1.0, 2.0]
    best = csw.whole_tie_partition(wts, n_bins=3)
    target = sum(wts) / 3
    costs = {}
    for a in range(1, 5):
        for b in range(a + 1, 6):
            parts = [sum(wts[:a]), sum(wts[a:b]), sum(wts[b:])]
            costs[(0, a, b)] = sum((x - target) ** 2 for x in parts)
    assert costs[tuple(best)] == pytest.approx(min(costs.values()))
    # Empty population and infeasible floor are refusals (None), never silent bins.
    assert csw.whole_tie_partition([], n_bins=10) is None
    assert csw.whole_tie_partition([5.0, 5.0], n_bins=2, floor=6.0) is None
    with pytest.raises(ValueError):
        csw.whole_tie_partition([1.0, 0.0])
    # A population whose weights are all zero yields no groups.
    assert csw.tie_groups([0.3, 0.3], [0.0, 0.0]).p.size == 0

    # Bins carry exact weight sums, so empty bins cannot exist.
    tab = csw.bin_table(groups, [0, 2])
    assert tab["weight"].tolist() == [2.0, 3.0]
    assert np.all(tab["weight"] > 0)

    # Monotonicity tolerance is explicit and inclusive.
    assert csw.point_monotone([0.1, 0.0995, 0.2], tol=1e-3)
    assert not csw.point_monotone([0.1, 0.098, 0.2], tol=1e-3)
    with pytest.raises(ValueError):
        csw.point_monotone([0.1, 0.2], tol=-1.0)
    # Max-statistic test: an increasing curve with tight replicates is not broken,
    # and a large drop with tight replicates is broken.
    rep_ok = np.tile([0.1, 0.3, 0.5], (100, 1)) + np.linspace(-0.01, 0.01, 100)[:, None]
    assert csw.maxstat_monotonicity(np.array([0.1, 0.3, 0.5]), rep_ok, np.ones(100, bool))["broken"] is False
    rep_bad = np.tile([0.5, 0.2, 0.6], (100, 1)) + np.linspace(-0.01, 0.01, 100)[:, None]
    assert csw.maxstat_monotonicity(np.array([0.5, 0.2, 0.6]), rep_bad, np.ones(100, bool))["broken"] is True
    # No valid replicates means undetermined (None), never "not broken".
    assert csw.maxstat_monotonicity(np.array([0.5, 0.2]), rep_bad[:, :2], np.zeros(100, bool))["broken"] is None
    # Invalid labels or predictions are refused.
    with pytest.raises(ValueError):
        csw.tie_groups([0.2], [1.0], [0.5])
    with pytest.raises(ValueError):
        csw.tie_groups([1.2], [1.0])


# ── requirement 2: weight ESS is not dependence-adjusted uncertainty ──────────

def test_req2_kish_weight_ess_is_separate_from_anchor_block_count():
    # 1,000 equal-weight rows anchored on only 10 sessions with H = 5:
    # Kish N is 1,000 but there are only 2 independent anchor blocks.
    anchors = np.repeat(np.arange(10), 100)
    w = np.full(1000, 0.01)
    summary = csw.support_summary(w, anchors, block_len=5)
    assert summary["kish_n"] == pytest.approx(1000.0)
    assert summary["native_effective_n"] == pytest.approx(10.0)
    assert summary["anchor_blocks"] == 2
    assert summary["state"] == "MEASURED"
    # Unknown, empty and measured-zero support are distinct states.
    assert csw.support_summary(None, None, 5)["state"] == "UNKNOWN"
    assert csw.support_summary([], [], 5)["state"] == "EMPTY"
    assert csw.support_summary([0.0, 0.0], [1, 2], 5)["state"] == "MEASURED_ZERO"
    assert csw.kish_effective_n([1.0, 0.0, 0.0]) == pytest.approx(1.0)
    assert csw.kish_effective_n([]) == 0.0

    # Native sum(w) equals covered sessions / L for equal-length intervals:
    # one unit per session on 0..T-1 with L = 6 covers T + 5 positions.
    t, length = 40, 6
    fill = np.arange(t)
    units = csw.native_units(fill, fill + length - 1, np.zeros(t, dtype=int))
    assert math.fsum(units.event_weight.tolist()) == pytest.approx((t + length - 1) / length)
    assert math.fsum(csw.position_decomposition(units).tolist()) == pytest.approx(
        math.fsum(units.unit_weight.tolist())
    )
    # The bootstrap resamples whole calendar sessions in blocks: each replicate draws T sessions.
    counts = csw.circular_block_counts(30, 5, 50, csw.rng_from_label("req2"))
    assert counts.shape == (50, 30)
    assert np.all(counts.sum(axis=1) == 30)
    # Deterministic for a fixed label.
    again = csw.circular_block_counts(30, 5, 50, csw.rng_from_label("req2"))
    assert np.array_equal(counts, again)


# ── requirement 3: false reassurance and decades-long infeasibility ──────────

def test_req3_simulation_covers_false_reassurance_and_overconservative_infeasibility():
    # Infeasibility: at the steady-panel accrual rate of about 1/6 per session,
    # the draft's 200-total floor needs 1,200 sessions (~4.8 years) while the
    # 30-observation bucket floor needs 180 (bounded below by 20 blocks of H).
    ratio = csw.gate_ratio(1.0 / 6.0, horizon=5)
    assert ratio["t_inc"] == pytest.approx(1200.0)
    assert ratio["t_alt"] == pytest.approx(180.0)
    assert ratio["ratio"] == pytest.approx(1200.0 / 180.0)
    slow = csw.gate_ratio(1.0 / 66.0, horizon=21)
    assert slow["years_inc"] > 50.0  # decades-long infeasibility is representable
    assert csw.projected_sessions(0.0, 200.0, 5, 20) == float("inf")
    assert csw.min_sessions_for_total(30.0, 6, 5) == 175

    # Overconservative: a calibrated steady panel with T = 252 cannot reach
    # R_inc's support floor, but R_alt has support.
    rng = csw.rng_from_label("req3", "T0")
    sim = csw.simulate_panel(rng, 252, 5, "T0", "steady")
    res = csw.evaluate_rules(sim["p"], sim["y"], sim["w"], sim["anchor"], 5, 199,
                             csw.rng_from_label("req3", "boot", "T0"))
    assert res["R_inc"]["decision"] == "NO_VERDICT"
    assert res["R_inc"]["reason"].startswith("CALIBRATION_INSUFFICIENT")
    assert "total_below_200" in res["R_inc"]["reason"]
    assert res["R_alt"]["native_effective_n"] >= csw.BUCKET_FLOOR
    assert res["R_alt"]["decision"] != "FAIL"

    # False reassurance: a strongly miscalibrated truth (logit slope 0.5) must not PASS.
    rng = csw.rng_from_label("req3", "T1")
    sim = csw.simulate_panel(rng, 504, 5, "T1", "steady")
    res = csw.evaluate_rules(sim["p"], sim["y"], sim["w"], sim["anchor"], 5, 199,
                             csw.rng_from_label("req3", "boot", "T1"))
    assert res["R_alt"]["decision"] == "FAIL"
    assert res["proposed"] != "PASS"
    assert csw.true_calibration_gap(sim["p"], sim["w"], "T1") > csw.ECE_THRESHOLD
    # The copula preserves the marginal: calibrated truth has zero gap by construction.
    assert csw.true_calibration_gap(sim["p"], sim["w"], "T0") == 0.0


# ── requirement 4: error and uncertainty are reported without a verdict ──────

def test_req4_error_and_uncertainty_reported_even_without_point_verdict():
    rng = csw.rng_from_label("req4")
    sim = csw.simulate_panel(rng, 120, 21, "T2", "bursty")
    res = csw.evaluate_rules(sim["p"], sim["y"], sim["w"], sim["anchor"], 21, 199,
                             csw.rng_from_label("req4", "boot"))
    # 120 sessions give only 5 anchor blocks at H = 21: no rule may issue a verdict.
    assert res["R_inc"]["decision"] == "NO_VERDICT"
    assert res["R_alt"]["decision"] == "NO_VERDICT"
    assert "blocks_below_20" in res["R_alt"]["reason"]
    report = res["error_report"]
    assert math.isfinite(report["binned_ece"])
    lo, hi = report["binned_ece_interval_90"]
    assert math.isfinite(lo) and math.isfinite(hi) and lo <= hi
    assert report["n_bins"] >= 1
    assert "note" in report
    # Pooling never promotes, and the combined decision is de-escalate-only.
    assert res["R_pool"]["diagnostic"]["can_promote"] is False
    assert csw.proposed_decision({"decision": "PASS"}, {"decision": "FAIL"}) == "NO_VERDICT"
    assert csw.proposed_decision({"decision": "NO_VERDICT"}, {"decision": "PASS"}) == "NO_VERDICT"
    assert csw.proposed_decision({"decision": "FAIL"}, {"decision": "PASS"}) == "FAIL"


# ── requirement 5: the frozen law, membership and windows are preserved ──────

def test_req5_reference_reproduces_frozen_weights_and_never_mutates_inputs():
    # Hand-checked case: unit A on [0, 1] with two events and unit B on [1, 2].
    # Concurrency is [1, 2, 1], so u_A = u_B = 0.75 and A's events get 0.375 each.
    fill = np.array([0, 0, 1])
    end = np.array([1, 1, 2])
    roots = np.array(["SPY", "spy ", "QQQ"], dtype=object)
    units = csw.native_units(fill, end, roots)
    assert units.event_weight.tolist() == [0.375, 0.375, 0.75]
    assert units.concurrency[:3].tolist() == [1, 2, 1]

    # Brute-force agreement on a random panel, exact and fast paths.
    gen = np.random.default_rng(7)
    n = 400
    f = gen.integers(0, 60, size=n)
    r = gen.integers(0, 6, size=n)
    lengths = {(a, b): int(gen.integers(1, 23)) for a, b in zip(f.tolist(), r.tolist())}
    e = np.array([a + lengths[(a, b)] - 1 for a, b in zip(f.tolist(), r.tolist())])
    oracle = _brute_native(f.tolist(), e.tolist(), r.tolist())
    exact = csw.native_units(f, e, r).event_weight
    fast = csw.native_units(f, e, r, exact=False).event_weight
    assert np.max(np.abs(exact - np.array(oracle))) <= 1e-12
    assert np.max(np.abs(fast - np.array(oracle))) <= 1e-12

    # Unit boundary mismatch and non-causal ends are refused, not repaired.
    with pytest.raises(ValueError, match="uniqueness_unit_boundary_mismatch"):
        csw.native_units([0, 0], [1, 2], ["SPY", "SPY"])
    with pytest.raises(ValueError, match="boundary_noncausal_end"):
        csw.native_units([3], [2], ["SPY"])

    # Inputs are never mutated by any public entry point.
    sim = csw.simulate_panel(csw.rng_from_label("req5"), 260, 5, "T0", "steady")
    frozen = {k: v.copy() for k, v in sim.items()}
    csw.native_units(sim["anchor"], sim["end"], sim["root"])
    csw.evaluate_rules(sim["p"], sim["y"], sim["w"], sim["anchor"], 5, 49, csw.rng_from_label("req5", "b"))
    for key, value in frozen.items():
        assert np.array_equal(value, sim[key])
    # The frozen thresholds are reused verbatim and none is relaxed.
    assert (csw.ECE_THRESHOLD, csw.N_BINS, csw.BUCKET_FLOOR, csw.CELL_FLOOR) == (0.05, 10, 30.0, 20.0)
    assert (csw.DRAFT_TOTAL_FLOOR, csw.DRAFT_MIN_BLOCKS, csw.DRAFT_REPLICATES) == (200.0, 20, 9_999)


# ── requirement 6: three separate review states ──────────────────────────────

def test_req6_opus_statistics_and_fable_states_are_separate():
    default = csw.review_record()
    assert default.as_dict() == {"opus_recommendation": "NONE",
                                 "statistical_acceptance": "NOT_REVIEWED",
                                 "fable_ratification": "UNRATIFIED"}
    rec = csw.review_record(opus_recommendation="PROPOSE_AMENDMENT")
    # An Opus recommendation implies neither acceptance nor ratification.
    assert rec.statistical_acceptance == "NOT_REVIEWED"
    assert rec.fable_ratification == "UNRATIFIED"
    # Any combination is representable; nothing is derived from another field.
    mixed = csw.review_record("RECOMMEND_REJECT", "ACCEPTED", "REFUSED")
    assert len(set(mixed.as_dict().values())) == 3
    for kwargs in ({"opus_recommendation": "RATIFIED"},
                   {"statistical_acceptance": "PASS"},
                   {"fable_ratification": "ACCEPTED"}):
        with pytest.raises(ValueError):
            csw.review_record(**kwargs)
    with pytest.raises(Exception):
        rec.fable_ratification = "RATIFIED"  # frozen dataclass


# ── no silent activation ─────────────────────────────────────────────────────

def test_no_silent_activation(capsys):
    assert csw.RESEARCH_ONLY is True
    assert csw.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    before = set(sys.modules)
    reloaded = importlib.reload(csw)
    after = set(sys.modules)
    # Reloading imports nothing new: no engine, lib, scripts or app module is pulled in.
    new = {m for m in after - before if m.split(".")[0] in {"engine", "lib", "scripts", "app", "collectors"}}
    assert new == set()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    public = [name for name in dir(reloaded) if not name.startswith("_")]
    for banned in ("register", "schedule", "promote", "activate", "enable", "write", "save", "main"):
        assert not any(banned in name.lower() for name in public), banned
    assert reloaded.RESEARCH_ONLY is True
