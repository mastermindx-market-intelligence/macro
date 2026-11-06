"""Prereg V2 §2 Option A — the δ = 0 parametric surrogate null for H1.

The null module re-derives H1's two statistics and its honest-N on null paths
with an incremental (traced) zig-zag instead of re-running evaluate_group at
every candidate window end. These tests pin that re-derivation to the harness
it mirrors, and pin the properties the prereg relies on: seed-stream separation
from the size paths, prefix invariance (the rung ladder changes compute, never
results), shard/request-order independence of the shared bank, and the
(1 + #{null ≥ obs}) / (1 + K) p-value.
"""

from __future__ import annotations

import json
import math
import zlib
from pathlib import Path

import numpy as np
import pytest

from scripts import leadership_rotation_episodes as ep
from scripts import leadership_rotation_null as nl
from scripts import leadership_rotation_p0 as p0
from scripts import leadership_rotation_run as run
from scripts import leadership_rotation_study as st


def _f(x):
    return float("nan") if x is None else float(x)


def _same(a, b) -> bool:
    a, b = _f(a), _f(b)
    return (math.isnan(a) and math.isnan(b)) or abs(a - b) <= 1e-12


@pytest.fixture(scope="module")
def sim_groups():
    groups, _truth = p0.simulate_family(0.007, 0.0, 0.5, 252 * 6, np.random.SeedSequence([7, 1]))
    return groups


# MUTATION: scripts/leadership_rotation_null.py:zigzag_trace record mode/trough only on finite steps (NaN steps lose the carried state)
def test_traced_zigzag_equals_zigzag_at_every_end_including_nan_runs():
    rng = np.random.default_rng(11)
    R = np.cumsum(rng.normal(0, 0.012, 1400))
    R[300:305] = np.nan
    R[777] = np.nan
    R[1100:1160] = np.nan
    s0 = 40
    completed, count, mode, trough, rmax = nl.zigzag_trace(R, s0, len(R))
    tr = nl.PairTrace(
        R=R, s0=s0, eligible=True, completed=completed, count=count, mode=mode,
        trough=trough, rmax=rmax, finite_cum=np.cumsum(np.isfinite(R)),
        a1=[], a2=[], a0=[], scan_end=len(R) - 1,
    )
    assert len(completed) >= 5
    for e in list(range(s0, len(R), 7)) + [s0, 303, 777, 1159, len(R) - 1]:
        assert tr.phases_at(e) == ep.zigzag(R, start=s0, end=e + 1), e
    assert tr.phases_at(s0 - 1) == []
    with pytest.raises(ValueError):
        tr.phases_at(len(R))


# MUTATION: scripts/leadership_rotation_null.py:h1_stats_at pass off_index=0 to classify_alarms and count session weight from index 0
def test_h1_statistics_equal_evaluate_group_on_delta_zero_paths(sim_groups):
    for g, pairs in sim_groups.items():
        n = len(pairs[0].spy)
        traces = [nl.trace_pair(ps, start=st.WARMUP, scan_end=n - 1) for ps in pairs]
        for e in (st.WARMUP + 200, st.WARMUP + 650, st.WARMUP + 1100, n - 1):
            ref = run.evaluate_group(pairs, start=st.WARMUP, end=e, partition="P0")["H1"]
            t_a, t_b = nl.h1_stats_at(traces, e)
            assert _same(t_a, ref["delay_reduction"]), (g, e)
            assert _same(t_b, ref["burden_cut_b"]), (g, e)


# MUTATION: scripts/leadership_rotation_null.py:first_reach treat a gap == CLUSTER_RADIUS as a cluster boundary
def test_first_reach_is_the_first_end_with_honest_n_at_least_N(sim_groups):
    checked = 0
    for g, pairs in sim_groups.items():
        n = len(pairs[0].spy)
        traces = [nl.trace_pair(ps, start=st.WARMUP, scan_end=n - 1) for ps in pairs]
        reach = nl.first_reach(traces, range(1, 40))
        assert reach, g
        for N, (e_star, n_real) in sorted(reach.items())[::5]:
            at = run.evaluate_group(pairs, start=st.WARMUP, end=e_star, partition="P0")
            assert at["honest_n"]["H1"] == n_real >= N, (g, N)
            before = run.evaluate_group(pairs, start=st.WARMUP, end=e_star - 1, partition="P0")
            assert before["honest_n"]["H1"] < N, (g, N)
            checked += 1
    assert checked >= 4


# MUTATION: scripts/leadership_rotation_null.py:_null_normals draw one (n, width) block instead of fixed 252-row chunks
def test_null_paths_are_prefix_invariant():
    short = nl.null_family(4, 0.007, 0.5, 600, 12345, 3)
    long = nl.null_family(4, 0.007, 0.5, 1500, 12345, 3)
    for a, b in zip(short, long):
        for attr in ("num", "den", "spy"):
            np.testing.assert_array_equal(getattr(a, attr), getattr(b, attr)[:600])
    other = nl.null_family(4, 0.007, 0.5, 600, 12345, 4)
    assert not np.array_equal(short[0].num, other[0].num)


# MUTATION: scripts/leadership_rotation_null.py:path_results evaluate at the end of the simulated path instead of at e*_N
def test_rung_ladder_changes_compute_never_results():
    Ns = range(8, 16)
    lo_rung, lo = nl.path_results(3, 0.007, 0.5, 777, 0, Ns, rung_hint=0)
    hi_rung, hi = nl.path_results(3, 0.007, 0.5, 777, 0, Ns, rung_hint=lo_rung + 2)
    assert hi_rung > lo_rung
    assert lo == hi
    assert all(lo[str(N)] is not None for N in Ns)


# MUTATION: scripts/leadership_rotation_null.py:null_seed_sequence build SeedSequence([seed, j]) without a spawn key
def test_null_seed_streams_never_coincide_with_size_paths():
    """A size path is SeedSequence([20261014, cell_id, k]); no null path of any
    registered (partition, group) may reproduce one of its generator states."""
    size_states = set()
    for cid in sorted(p0._catalog_map()):
        for k in range(400):
            ss = np.random.SeedSequence([p0.PATH_SEED_ROOT, cid, k])
            size_states.add(tuple(ss.generate_state(4)))
    null_states = set()
    for part in ("P0", "P1"):
        for group in sorted(p0.GROUP_SIZES):
            seed, crc = nl.seed_entropy(part, group)
            assert seed == 20261014 + zlib.crc32(f"{part}|{group}".encode())
            assert crc == zlib.crc32(f"{part}|{group}".encode())
            for j in range(1000):
                null_states.add(tuple(nl.null_seed_sequence(seed, j).generate_state(4)))
    assert len(null_states) == 2 * len(p0.GROUP_SIZES) * 1000
    assert not (size_states & null_states)


# MUTATION: scripts/leadership_rotation_null.py:_tail count a NaN null statistic as below the observed value
def test_p_value_formula_and_conservative_counting():
    paths = [
        {"res": {"10": [3.0, 0.5, 10, 100]}},
        {"res": {"10": [1.0, None, 11, 120]}},
        {"res": {"10": None}},
        {"res": {"10": [5.0, 0.9, 10, 90]}},
    ]
    a = nl._tail(paths, 10, 3.0, 0)
    # ≥ 3.0: 3.0, 5.0, and the unreached path → 3; K = 4
    assert a["n_ge"] == 3 and a["p"] == pytest.approx(4 / 5)
    assert a["n_unreached"] == 1 and a["n_finite"] == 3
    b = nl._tail(paths, 10, 0.95, 1)
    # nothing finite ≥ 0.95; NaN and unreached both count → 2
    assert b["n_ge"] == 2 and b["n_nan"] == 1 and b["p"] == pytest.approx(3 / 5)
    assert nl._tail(paths, 10, float("nan"), 0)["p"] == 1.0
    assert a["q975"] == pytest.approx(np.quantile([3.0, 1.0, 5.0], 0.975))


# MUTATION: scripts/leadership_rotation_null.py:match_params invert rho with sigma_hat instead of the rounded sigma_b
def test_matching_rounds_sigma_and_inverts_rho_for_the_market_term():
    m = nl.match_params(0.00712, 0.5)
    assert m["status"] == "OK" and m["sigma_b"] == pytest.approx(0.007)
    s2 = 0.007 ** 2
    assert m["rho_gen"] == pytest.approx((0.5 * s2 - nl.MARKET_VAR) / (s2 - nl.MARKET_VAR))
    assert m["rho_b"] == pytest.approx(round(m["rho_gen"] / 0.05) * 0.05)
    assert nl.match_params(0.007, 0.999)["rho_b"] == pytest.approx(nl.RHO_MAX)
    assert nl.match_params(0.007, 0.0)["rho_b"] == 0.0
    floor = nl.match_params(0.0028, 0.5)
    assert floor["status"] == "NOT_EXECUTABLE" and "market floor" in floor["reason"]
    assert nl.match_params(float("nan"), 0.5)["status"] == "NOT_EXECUTABLE"


# MUTATION: scripts/leadership_rotation_null.py:read_moments use ΔR from index 0 instead of the formation window (s0, end]
def test_generator_sigma_and_rho_are_recovered_by_the_read_moments():
    pairs = nl.null_family(4, 0.008, 0.6, st.WARMUP + 252 * 16, 4242, 0)
    end = len(pairs[0].spy) - 1
    cores = [run._evaluate_pair_core(ps, start=st.WARMUP, end=end) for ps in pairs]
    mom = nl.read_moments(cores, end)
    assert mom["n_pairs_measured"] == 4 and mom["n_correlations"] == 6
    m = nl.match_params(mom["sigma_hat"], mom["rho_hat"])
    assert m["sigma_b"] == pytest.approx(0.008)
    assert m["rho_b"] == pytest.approx(0.6)


# MUTATION: scripts/leadership_rotation_null.py:bank_paths key shards by request order instead of the shard index
def test_bank_is_shard_and_request_order_independent(tmp_path, monkeypatch):
    payload = nl.bank_payload("P0", "broadening_proxy", 3, 0.007, 0.45, 7, 1)
    nl._BANK_CACHE.clear()
    monkeypatch.setattr(nl, "SHARD_PATHS", 3)
    a = nl.bank_paths(payload, tmp_path / "a")
    assert len(a) == 7 and [p["j"] for p in a] == list(range(7))
    assert len(list((tmp_path / "a").glob("*.json"))) == 3
    nl._BANK_CACHE.clear()
    monkeypatch.setattr(nl, "SHARD_PATHS", 2)
    b = nl.bank_paths(payload, tmp_path / "b")
    assert [p["res"] for p in a] == [p["res"] for p in b]
    # a fresh process reads the stored shards back without recomputing
    nl._BANK_CACHE.clear()
    c = nl.bank_paths(payload, tmp_path / "b", on_miss="raise")
    assert [p["res"] for p in c] == [p["res"] for p in b]
    nl._BANK_CACHE.clear()
    with pytest.raises(LookupError):
        nl.bank_paths(payload, tmp_path / "empty", on_miss="raise")
    # every path's result is a pure function of (payload, j)
    _, direct = nl.path_results(3, 0.007, 0.45, payload["seed"], 5, range(8, 16))
    assert json.loads(json.dumps(direct)) == a[5]["res"]
    nl._BANK_CACHE.clear()


# MUTATION: scripts/leadership_rotation_run.py:evaluate_group decide H1 on the bootstrap p-values even when h1_null is given
def test_evaluate_family_uses_the_option_a_p_values(sim_groups, tmp_path):
    prov = nl.make_h1_null_provider(K=12, bank_dir=tmp_path)
    fam = run.evaluate_family(
        sim_groups, start=st.WARMUP, end=st.WARMUP + 1000, partition="P0", h1_null=prov
    )
    for g, gr in fam["groups"].items():
        h1 = gr["H1"]
        nul = h1["null"]
        assert h1["p_method"] == "V2_OPTION_A" and nul["method"] == "V2_OPTION_A"
        assert nul["K"] == 12 and nul["status"] == "OK"
        assert nul["matched"]["N"] == gr["honest_n"]["H1"]
        for key in ("p_a", "p_b"):
            assert h1[key] == nul[key]
            assert round(h1[key] * 13) == pytest.approx(h1[key] * 13)
        assert h1["p"] == max(h1["p_a"], h1["p_b"])
        assert h1["decision"]["p_h1"] == h1["p"]
        assert set(h1["p_bootstrap_superseded"]) == {"p_a", "p_b"}
        assert nul["seed"]["entropy"] == nl.seed_entropy("P0", g)[0]
    plain = run.evaluate_family(sim_groups, start=st.WARMUP, end=st.WARMUP + 1000, partition="P0")
    for gr in plain["groups"].values():
        assert gr["H1"]["p_method"] == "V1_BOOTSTRAP" and "null" not in gr["H1"]
    nl._BANK_CACHE.clear()


# MUTATION: scripts/leadership_rotation_run.py:evaluate_family let a P1 read fall back to the V1 bootstrap null
def test_a_p1_read_refuses_the_superseded_bootstrap_null(sim_groups):
    with pytest.raises(ValueError, match="Option A"):
        run.evaluate_family(sim_groups, start=st.WARMUP, end=st.WARMUP + 500, partition="P1")
    # an empty family is not a read and stays callable
    run.evaluate_family({}, start=0, end=10, partition="P1")


def test_null_module_is_a_pinned_harness_module():
    assert "scripts/leadership_rotation_null.py" in run.HARNESS_MODULES
    assert nl.NULL_K_MIN == run.SIZE_GATE_MIN_NULL_K == 1000
    assert nl.METHOD == run.SIZE_GATE_H1_NULL_METHOD == "V2_OPTION_A"
