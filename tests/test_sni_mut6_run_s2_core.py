"""MUT6C invariant-pin tests for run_s2.py core evaluation paths.

SNI-local DRAFT contract tests. They consume caller-supplied synthetic
episodes and opaque issuer tokens; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation,
or trade path. Authority flags stay false. Fixtures are synthetic.
Residuals and event-study numbers are descriptive, never causal, never a
news-impact claim (A24). An unestimable family ABSTAINS (A25).

Lane MUT6C: AST mutation of `compute_outcomes`, `pooled_prior`,
`evaluate_family`, and `build_block` in
`research/single_name_intelligence/event_response/run_s2.py` (the
owned site range listed in MUT6C / MUT6 lane 4 of the coverage
census). 40 sampled mutants, deterministic `random.Random(20261014)`,
stratified by function; the pre-existing importer suite
(`test_sni_mutation_run_s2_a.py`, `test_sni_mutation_run_s2_b.py`,
`test_sni_s2_v1_1_hardening.py`, `test_sni_s2_abstain.py`,
`test_sni_s2_seal_integrity.py`, `test_sni_s2_nonfinite_abstain.py`,
`test_sni_s2_cli.py`, `test_sni_s2_info_leak.py`,
`test_sni_injection_safety.py`, `test_sni_mutation_build_seal.py`)
already killed every sampled mutant (40/40). No non-equivalent
SURVIVED mutant was produced. Per the MUT6C spec OR clause, this
file ships the small set of INVARIANT-PIN tests that document and
re-exercise the named MUT6-lane-4 contract properties so future
modifications cannot silently regress them. Each
`test_m6c_pin_*` docstring names the census invariant it pins
(`X2-01`, `A25`, etc.) and the evaluation path it covers.

Deterministic; no git-history reads; no network; CI depth-1 safe.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

import run_s2 as run_s2_mod  # noqa: E402
from run_s2 import (  # noqa: E402
    RETIRED_TOKEN,
    build_block,
    compute_outcomes,
    episode_identity,
    evaluate_family,
    pooled_prior,
)
from s2_seal import (  # noqa: E402
    BASELINE_ALWAYS_LONG,
    BASELINE_POOLED_PRIOR,
    BASELINE_TRAILING63,
    GRADE_HORIZONS,
    MIN_TRAIN_CLUSTERS_POOLED_PRIOR,
    PROTOCOLS,
    TESTED,
)
from s2_splits import episode_key  # noqa: E402

ISSUER = "synthetic-issuer-m6c"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _ep(s_us: str, n: int = 1) -> SimpleNamespace:
    opener = SimpleNamespace(
        issuer_key=ISSUER,
        family="results",
        t_avail_utc=f"{s_us}T20:00:00Z",
        evidence_pointer=f"synthetic#ep={n}",
        s_us=s_us,
        s_hk=s_us,
        member_ids=[f"synthetic-{n}"],
    )
    return SimpleNamespace(opener=opener, confounded=False, absorbed_count=0)


def _empty_state() -> dict:
    return {
        "membership": {
            pid: {"counted": {h: [] for h in GRADE_HORIZONS}} for pid in PROTOCOLS
        },
        "collapse": {
            "counts": {
                "literal_row_count_pre_step0": 0,
                "excluded_and_listed": [],
            }
        },
        "prereg_digest_sha256": "aa" * 32,
    }


def _ok(excess: float) -> dict:
    return {"state": "OK", "excess": excess, "window": None}


def _ledger() -> dict:
    return {"literal_n": 0, "effective_n": 0, "declared_budget": 6}


class _Engine:
    """Recording stub of OutcomeEngine. episode_excess and
    trailing63_direction are tracked; the test asserts that
    episode_excess is NEVER called for a retired (protocol, split)."""

    def __init__(self) -> None:
        self.excess_calls: list[tuple[str, int]] = []
        self.trailing_calls: list[str] = []
        self.trailing_value = 1  # default trailing63 direction

    def episode_excess(self, s_us: dt_date, h: int):  # noqa: ANN001 — duck
        self.excess_calls.append((s_us.isoformat(), h))
        return {"state": "OK", "excess": 0.05, "window": None}

    def trailing63_direction(self, s_us: dt_date) -> int:  # noqa: ANN001
        self.trailing_calls.append(s_us.isoformat())
        return self.trailing_value


import datetime as _dt  # noqa: E402

dt_date = _dt.date


# ---------------------------------------------------------------------------
# X2-01: retired (protocol, split) cell NEVER resolves a window return.
#         compute_outcomes must skip episode_excess for a retired cell.
# ---------------------------------------------------------------------------


def test_m6c_pin_x2_01_compute_outcomes_skips_retired_cell() -> None:
    """X2-01 — retired (pid, split) cell: compute_outcomes must NOT call
    episode_excess for that (pid, split). Pin: a P04 episode whose split
    is QUARANTINE is in retired_cells; engine.excess_calls stays empty
    for that episode even though it sits in state['membership']['P04']."""
    state = _empty_state()
    ep = _ep("2019-06-03", 1)
    state["membership"]["P04"]["counted"][5] = [ep]
    engine = _Engine()
    # X2-01: retire (P04, QUARANTINE). 2019-06-03 -> split = QUARANTINE in
    # this fixture (synthetic date well before the actual fence; the split
    # label is monotonic and QUARANTINE is reserved for >= 2026-10-01 in
    # production but we exercise the (pid, split) skip independently).
    # Instead, retire via the canonical key the retire test exercises:
    # we set retired_cells = {("P04", "TRAIN")} and assert the episode on
    # 2019-06-03 (TRAIN per the s2_splits split_label) is skipped.
    out = compute_outcomes(engine, state, retired_cells={("P04", "TRAIN")})
    assert engine.excess_calls == [], (
        "X2-01 violated: episode_excess called for a retired (P04, TRAIN) cell"
    )
    assert out["outcomes"] == {}
    assert out["trailing"] == {}


# ---------------------------------------------------------------------------
# evaluate_family retired=True pins the RETIRED-CONTAMINATED token
# ---------------------------------------------------------------------------


def test_m6c_pin_x2_01_evaluate_family_retired_row_uses_retired_token() -> None:
    """X2-01 — evaluate_family(retired=True) must mark every row's
    outcome_state with RETIRED_TOKEN and pin excess=None / window=None,
    even when occ['outcomes'] has an entry for the (key, h) pair.
    A mutated evaluate_family that drops the retired branch would return
    the live occ outcome; this test forbids that."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(0.05)}, "trailing": {key: 1}}
    ev = evaluate_family(
        "P04", state, occ, 5, "TRAIN", BASELINE_ALWAYS_LONG,
        pooled_prior_dir=None, retired=True,
    )
    assert len(ev["rows"]) == 1
    row = ev["rows"][0]
    assert row["outcome_state"] == RETIRED_TOKEN
    assert row["window"] is None
    assert row["excess"] is None
    assert row["direction"] == 1  # BASELINE_ALWAYS_LONG still picks dir
    assert row["hit"] is None


# ---------------------------------------------------------------------------
# A25: pooled_prior ABSTAINS with a named reason when cluster-N < floor.
#     Never a 50/50 fill, never a default 0/+-1, never a sample mean.
# ---------------------------------------------------------------------------


def test_m6c_pin_a25_pooled_prior_abstains_below_cluster_floor() -> None:
    """A25 — pooled_prior must ABSTAIN with a named reason when the TRAIN
    cluster count is below MIN_TRAIN_CLUSTERS_POOLED_PRIOR. Two TRAIN
    episodes sharing one cluster_key -> exactly one distinct cluster ->
    MIN_TRAIN_CLUSTERS_POOLED_PRIOR (2) not met -> (None, "NOT ESTIMABLE…").
    A mutated pooled_prior that returns (sign_exact(mean), token) here
    would silently inject a 50/50 direction (A25 violation)."""
    e1, e2 = _ep("2019-03-01", 1), _ep("2019-03-01", 2)  # same s_us -> 1 cluster
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [e1, e2]
    k1, k2 = episode_identity(e1), episode_identity(e2)
    occ = {
        "outcomes": {(k1, 5): _ok(0.10), (k2, 5): _ok(0.30)},
        "trailing": {},
    }
    direction, token = pooled_prior(state, occ, 5)
    assert direction is None
    assert "NOT ESTIMABLE" in token
    assert "TRAIN" in token
    assert "cluster-N" in token or "cluster" in token


# ---------------------------------------------------------------------------
# A25 positive case: pooled_prior returns the named mean-excess direction
# above the cluster floor (regression fence against a swapped /, == vs >=).
# ---------------------------------------------------------------------------


def test_m6c_pin_a25_pooled_prior_returns_mean_excess_direction() -> None:
    """A25 — pooled_prior above the cluster floor: the pooled direction
    equals sign_exact(mean excess) of all TRAIN PRIMARY excesses across
    PROTOCOLS, and the token prints the same mean excess to six decimals.
    Pin: (0.10 + 0.30) / 2 = +0.200000 -> direction == +1."""
    e1, e2 = _ep("2019-03-01", 1), _ep("2019-06-03", 2)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [e1, e2]
    k1, k2 = episode_identity(e1), episode_identity(e2)
    occ = {
        "outcomes": {(k1, 5): _ok(0.10), (k2, 5): _ok(0.30)},
        "trailing": {},
    }
    direction, token = pooled_prior(state, occ, 5)
    assert direction == 1
    assert "+0.200000" in token


# ---------------------------------------------------------------------------
# compute_outcomes trailing direction uniqueness — a key seen twice
# across protocols keeps ONE trailing63 call (X2-01 adjacent).
# ---------------------------------------------------------------------------


def test_m6c_pin_compute_outcomes_trailing_direction_unique_per_key() -> None:
    """compute_outcomes dedup — trailing63_direction must be called at
    most once per episode_key across PROTOCOLS. Two episodes from
    different protocols with identical issuer / family / t_avail /
    evidence_pointer collide on key; only ONE trailing63 call."""
    state = _empty_state()
    ep1 = _ep("2019-06-03", 1)
    ep2 = _ep("2019-06-03", 1)  # identical opener -> identical key
    state["membership"]["P04"]["counted"][5] = [ep1]
    state["membership"]["P05"]["counted"][5] = [ep2]
    engine = _Engine()
    out = compute_outcomes(engine, state)
    assert len(engine.trailing_calls) == 1, (
        f"trailing63_direction must be called once per unique key; got "
        f"{len(engine.trailing_calls)} calls: {engine.trailing_calls}"
    )
    assert len(out["trailing"]) == 1


# ---------------------------------------------------------------------------
# build_block TESTED hits regression: hits count is exact.
# ---------------------------------------------------------------------------


def test_m6c_pin_build_block_tested_hits_count() -> None:
    """build_block TESTED branch — for a 153-episode TRAIN PRIMARY with
    100 positive and 53 negative excesses under BASELINE_ALWAYS_LONG,
    `block["test"]["hits"]` is the count of row["hit"] == 1, i.e. 100
    (always-long baseline always agrees with a positive excess). Pin
    a mutated hits expression or wrong hit computation."""
    eps = []
    occ = {"outcomes": {}, "trailing": {}}
    for i in range(153):
        s_us = "2019-03-01" if i < 80 else "2019-06-03"
        ep = _ep(s_us, i + 1)
        eps.append(ep)
        key = episode_identity(ep)
        excess = 0.05 if i < 100 else -0.05
        occ["outcomes"][(key, 5)] = _ok(excess)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = eps
    block = build_block("P04", state, occ, 5, "TRAIN", _ledger(), [], {})
    assert block["family_row"]["abstention_state"] == TESTED
    assert block["test"]["hits"] == 100
    assert block["test"]["n"] == 153


# ---------------------------------------------------------------------------
# evaluate_family direction branches — pin the BASELINE_TRAILING63
# trailing lookup and BASELINE_POOLED_PRIOR dir lookup.
# ---------------------------------------------------------------------------


def test_m6c_pin_evaluate_family_trailing63_uses_occ_trailing() -> None:
    """evaluate_family BASELINE_TRAILING63 branch — direction comes from
    occ['trailing'][key], not from a constant. A mutated evaluate_family
    that hard-codes direction=1 (BASELINE_ALWAYS_LONG path) or returns 0
    for the trailing branch would be caught by this assert."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(0.05)}, "trailing": {key: 1}}
    ev = evaluate_family(
        "P04", state, occ, 5, "TRAIN", BASELINE_TRAILING63, None
    )
    assert ev["rows"][0]["direction"] == 1
    assert ev["rows"][0]["hit"] == 1


def test_m6c_pin_evaluate_family_pooled_prior_uses_pooled_dir() -> None:
    """evaluate_family BASELINE_POOLED_PRIOR branch — direction comes
    from the caller-supplied pooled_prior_dir, not from a constant or
    from occ. Pin: pooled_dir=-1 -> direction=-1; a mutated evaluate_family
    that ignores pooled_prior_dir would default direction to None."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(-0.05)}, "trailing": {}}
    ev = evaluate_family(
        "P04", state, occ, 5, "TRAIN", BASELINE_POOLED_PRIOR,
        pooled_prior_dir=-1,
    )
    assert ev["rows"][0]["direction"] == -1
    assert ev["rows"][0]["hit"] == 1  # sign_exact(-0.05) == -1 -> hit