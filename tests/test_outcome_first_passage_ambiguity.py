from __future__ import annotations

"""Hermetic tests for engine/outcome_first_passage_ambiguity.py (Q19).

Synthetic data only, with integer/relative clocks. No repository files, no
network and no dependence on the current date.
"""

import copy
import importlib
import sys

import numpy as np
import pytest

import engine.outcome_first_passage_ambiguity as fpa


def _path_first(prices, upper, lower):
    """Ground truth on a fully observed tick path."""
    for p in prices:
        if p >= upper:
            return fpa.UPPER_FIRST
        if p <= lower:
            return fpa.LOWER_FIRST
    return fpa.NEITHER


# --- requirement 1 ---------------------------------------------------------

def test_req1_identical_ohlc_with_opposite_first_hit_paths_yields_ambiguity():
    path_a = [100.0, 110.0, 90.0, 100.0]   # upper touched first
    path_b = [100.0, 90.0, 110.0, 100.0]   # lower touched first
    upper, lower = 105.0, 95.0
    assert _path_first(path_a, upper, lower) == fpa.UPPER_FIRST
    assert _path_first(path_b, upper, lower) == fpa.LOWER_FIRST
    ohlc_a = (path_a[0], max(path_a), min(path_a), path_a[-1])
    ohlc_b = (path_b[0], max(path_b), min(path_b), path_b[-1])
    assert ohlc_a == ohlc_b
    for ohlc in (ohlc_a, ohlc_b):
        res = fpa.first_passage([(ohlc[1], ohlc[2])], upper, lower)
        assert res["state"] == fpa.AMBIGUOUS
        assert res["state"] not in (fpa.UPPER_FIRST, fpa.LOWER_FIRST)
    # the identified bounds span both answers, while forced conventions disagree
    b = fpa.first_passage_bounds([{"censoring": fpa.OBSERVED, "state": fpa.AMBIGUOUS}])
    assert b["observed"]["upper_first"] == [0.0, 1.0]
    assert fpa.ordering_convention(fpa.AMBIGUOUS, "optimistic") == fpa.UPPER_FIRST
    assert fpa.ordering_convention(fpa.AMBIGUOUS, "pessimistic") == fpa.LOWER_FIRST
    assert fpa.ordering_convention(fpa.AMBIGUOUS, "identified") == fpa.AMBIGUOUS


def test_req1_finer_windows_identify_when_crossings_fall_in_different_windows():
    res = fpa.first_passage([(110.0, 99.0), (101.0, 90.0)], 105.0, 95.0)
    assert res["state"] == fpa.UPPER_FIRST and res["window_index"] == 0
    nested = fpa.first_passage([(101.0, 99.0), (101.0, 90.0), (110.0, 90.0)], 105.0, 95.0,
                               cumulative=True)
    assert nested["state"] == fpa.LOWER_FIRST and nested["window_index"] == 1
    with pytest.raises(ValueError):
        fpa.first_passage([(110.0, 90.0), (101.0, 95.0)], 105.0, 95.0, cumulative=True)
    with pytest.raises(ValueError):
        fpa.bar_touch(90.0, 110.0, 105.0, 95.0)


# --- requirement 2 ---------------------------------------------------------

def test_req2_open_unmatured_cases_not_counted_as_losses_nor_dropped():
    units = [
        {"censoring": fpa.OBSERVED, "state": fpa.UPPER_FIRST},
        {"censoring": fpa.OBSERVED, "state": fpa.LOWER_FIRST},
        {"censoring": fpa.classify_attrition("pending")["class"], "state": None},
        {"censoring": fpa.classify_attrition("unmatured")["class"], "state": None},
    ]
    b = fpa.first_passage_bounds(units)
    assert b["denominator"]["n_total"] == 4
    assert b["denominator"]["n_administrative_pending"] == 2
    assert b["dropped_units"] == 0 and b["pending_counted_as_loss"] is False
    # loss (lower_first) rate among observed is 1/2, not 3/4
    assert b["observed"]["lower_first"] == [0.5, 0.5]
    # full-denominator bounds keep pending as unknown, never as loss
    assert b["full_denominator"]["lower_first"] == [0.25, 0.75]
    assert b["states"][fpa.LOWER_FIRST] == 1


# --- requirement 3 ---------------------------------------------------------

@pytest.mark.parametrize("status,reason", [
    ("unavailable", "delisted"), ("incomplete", "halted"), ("unavailable", "missing_data"),
    ("unavailable", None), ("weird_status", "weird_reason"),
])
def test_req3_delisted_halted_missing_not_benign_censoring_by_default(status, reason):
    c = fpa.classify_attrition(status, reason)
    assert c["class"] == fpa.INFORMATIVE_UNKNOWN
    assert c["benign"] is False


def test_req3_noninformative_only_by_explicit_caller_admission():
    c = fpa.classify_attrition("unavailable", "halted", admitted_noninformative={"halted"})
    assert c["class"] == fpa.ASSUMED_NONINFORMATIVE
    assert c["benign"] is False and c["assumption"] == "caller_admitted_noninformative"
    units = [{"time": 1.0, "event": None, "censoring": fpa.INFORMATIVE_UNKNOWN},
             {"time": 2.0, "event": "upper", "censoring": fpa.OBSERVED}]
    res = fpa.cumulative_incidence(units, [3.0], censoring_assumption={"noninformative": True, "basis": "x"})
    assert res["status"] == "bounds_only"
    assert "informative_or_invalid_censoring_present" in res["failed_conditions"]


# --- requirement 4 ---------------------------------------------------------

def test_req4_higher_resolution_evidence_joined_only_when_availability_and_rights_permit():
    q = 1_000
    assert fpa.evidence_admissible(q, 900, rights_ok=True, same_entry=True) == (True, "admitted")
    # boundary: evidence available exactly at the question clock is admissible
    assert fpa.evidence_admissible(q, q, rights_ok=True, same_entry=True) == (True, "admitted")
    assert fpa.evidence_admissible(q, 1_001, rights_ok=True, same_entry=True)[1] == "not_available_at_question_clock"
    assert fpa.evidence_admissible(q, 900, rights_ok=False, same_entry=True)[1] == "rights_not_admitted"
    assert fpa.evidence_admissible(q, None, rights_ok=True, same_entry=True)[1] == "availability_unknown"
    assert fpa.evidence_admissible(q, 900, rights_ok=True, same_entry=False)[1] == "entry_mismatch"
    assert fpa.evidence_admissible(q, 900, rights_ok=True, same_entry=True, same_price_basis=False)[1] == "price_basis_mismatch"
    ok, _ = fpa.evidence_admissible(q, 1_001, rights_ok=True, same_entry=True)
    assert fpa.refine_state(fpa.AMBIGUOUS, fpa.LOWER_FIRST, ok)["state"] == fpa.AMBIGUOUS
    ok, _ = fpa.evidence_admissible(q, 900, rights_ok=True, same_entry=True)
    r = fpa.refine_state(fpa.AMBIGUOUS, fpa.LOWER_FIRST, ok)
    assert r["state"] == fpa.LOWER_FIRST and r["refined"] is True
    # identified coarse states are never overwritten by contradicting evidence
    r = fpa.refine_state(fpa.UPPER_FIRST, fpa.LOWER_FIRST, True)
    assert r["state"] == fpa.UPPER_FIRST and r["note"] == "inconsistent_evidence"
    with pytest.raises(ValueError):
        fpa.evidence_admissible(1.5, 1, rights_ok=True, same_entry=True)


# --- requirement 5 ---------------------------------------------------------

def test_req5_canonical_cohort_ids_grades_and_fixed_horizons_unchanged():
    rec = {"episode_id": "ep-1", "outcome_id": "oc-1", "cohort_id": "c-7", "grade": "B",
           "horizon": "10d", "horizon_sessions": 10, "status": "complete",
           "underlying": {"ret": 0.01}}
    before = copy.deepcopy(rec)
    out = fpa.attach_diagnostic(rec, {"state": fpa.AMBIGUOUS, "bounds": [0.0, 1.0]})
    assert rec == before
    for k in fpa.CANONICAL_KEYS:
        if k in rec:
            assert out[k] == rec[k]
    assert out[fpa.DIAGNOSTIC_NAMESPACE]["state"] == fpa.AMBIGUOUS
    with pytest.raises(ValueError):
        fpa.attach_diagnostic(rec, {"grade": "A"})
    with pytest.raises(ValueError):
        fpa.attach_diagnostic(rec, {"horizon": "5d"})


# --- requirement 6 ---------------------------------------------------------

def test_req6_survival_estimate_states_assumptions_and_matches_hand_aalen_johansen():
    units = [
        {"time": 1.0, "event": "upper", "censoring": fpa.OBSERVED},
        {"time": 2.0, "event": None, "censoring": fpa.ADMINISTRATIVE_PENDING},
        {"time": 3.0, "event": "lower", "censoring": fpa.OBSERVED},
        {"time": 4.0, "event": "upper", "censoring": fpa.OBSERVED},
    ]
    res = fpa.cumulative_incidence(units, [1.0, 3.0, 4.0],
                                   censoring_assumption={"noninformative": True, "basis": "calendar-only"})
    assert res["status"] == "estimate"
    assert res["assumptions"]["noninformative_censoring_asserted"] is True
    assert res["assumptions"]["basis"] == "calendar-only"
    # hand AJ: t1 n=4 d_up=1 -> F_up=.25,S=.75; t2 censor; t3 n=2 d_lo=1 -> F_lo=.375,S=.375;
    # t4 n=1 d_up=1 -> F_up=.25+.375=.625
    assert res["cif"]["upper"] == pytest.approx([0.25, 0.25, 0.625])
    assert res["cif"]["lower"] == pytest.approx([0.0, 0.375, 0.375])


def test_req6_fails_to_bounds_or_unavailable_when_assumptions_unsupported():
    units = [{"time": 1.0, "event": "upper", "censoring": fpa.OBSERVED},
             {"time": 2.0, "event": None, "censoring": fpa.ADMINISTRATIVE_PENDING}]
    res = fpa.cumulative_incidence(units, [2.0])
    assert res["status"] == "bounds_only"
    assert "noninformative_censoring_not_asserted" in res["failed_conditions"]
    assert "cif" not in res
    assert res["bounds"]["lower"]["upper"] == [0.5]
    assert res["bounds"]["upper"]["upper"] == [1.0]
    amb = [{"time": 1.0, "event": "ambiguous", "censoring": fpa.OBSERVED}]
    res = fpa.cumulative_incidence(amb, [1.0], censoring_assumption={"noninformative": True, "basis": "x"})
    assert res["status"] == "bounds_only"
    assert "interval_ambiguous_events_present" in res["failed_conditions"]
    assert res["bounds"]["lower"]["upper"] == [0.0] and res["bounds"]["upper"]["upper"] == [1.0]
    assert fpa.cumulative_incidence([], [1.0])["status"] == "unavailable"


def test_block_bootstrap_is_deterministic_and_respects_blocks():
    blocks = [[1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    def mean(bs):
        flat = [x for b in bs for x in b]
        return float(np.mean(flat)) if flat else None

    a = fpa.circular_block_bootstrap(blocks, mean, block_len=2, n_boot=200, seed=7)
    b = fpa.circular_block_bootstrap(blocks, mean, block_len=2, n_boot=200, seed=7)
    assert a == b and a["status"] == "ok" and a["lo"] <= a["point"] <= a["hi"]
    assert fpa.circular_block_bootstrap([], mean, block_len=1, n_boot=10, seed=1)["status"] == "unavailable"


# --- no silent activation --------------------------------------------------

def test_no_silent_activation_research_only_and_side_effect_free():
    assert fpa.RESEARCH_ONLY is True
    assert fpa.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    # Evict every already-loaded engine./scripts./app. module first, so a sibling
    # import made by the subject would be re-executed and observed (a plain reload
    # cannot see an import whose target is already cached), then restore the cache.
    name = fpa.__name__
    prefixes = ("engine.", "scripts.", "app.")
    saved = {k: v for k, v in sys.modules.items() if k.startswith(prefixes)}
    pkg = sys.modules.get("engine")
    try:
        for k in saved:
            del sys.modules[k]
        mod = importlib.import_module(name)
        pulled = {k for k in sys.modules if k.startswith(prefixes)} - {name}
    finally:
        for k in [k for k in sys.modules if k.startswith(prefixes)]:
            del sys.modules[k]
        sys.modules.update(saved)
        if pkg is not None:
            setattr(pkg, name.rsplit(".", 1)[1], fpa)
    assert mod is not fpa  # the subject really was re-executed
    assert pulled == set(), sorted(pulled)
    public = {n for n in dir(mod) if not n.startswith("_")}
    for banned in ("register", "REGISTRY", "schedule", "promote", "activate", "main", "run"):
        assert banned not in public
    # pure functions: repeated calls give equal answers and do not mutate inputs
    w = [(110.0, 90.0)]
    w0 = copy.deepcopy(w)
    assert mod.first_passage(w, 105.0, 95.0) == mod.first_passage(w, 105.0, 95.0)
    assert w == w0
