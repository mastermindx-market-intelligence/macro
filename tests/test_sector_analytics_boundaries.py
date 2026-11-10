"""Lane 8 (P04/P05/P06/P18) — boundary cases that pin the written definitions.

Every test here is cited by name from
research/sector_completion_20261021/B04_METRIC_DEFINITIONS.md (§ Lane 8 boundary
register) or B12_HAZARD_PARITY.md (§ Current-MODEL qualification).  Inputs are
synthetic and isolatable; nothing here is a market fact.  `engine/sector_central.py`
is exercised read-only (its owner is a different lane).
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import engine.cycle_ontology as onto
import engine.hazard_score as hs
import engine.leadership_rotation_context as lrc
import engine.sector_cycles as sc
from engine import basket_index
from engine.cycle_rhythm import estimate_kinds, rhythm_window
from engine.sector_central import _aggregate_heat

REPO = Path(__file__).resolve().parent.parent
MODEL_PATH = REPO / "data" / "hazard" / "model_price_c4414dcb.json"
KM_PATH = REPO / "data" / "hazard" / "km_baseline_price_c4414dcb.json"
MEMBERSHIP = REPO / "data" / "baskets" / "membership.json"

needs_hazard = pytest.mark.skipif(
    not (MODEL_PATH.exists() and KM_PATH.exists()),
    reason="admitted hazard artifacts absent (sparse tree: materialize data/hazard)")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constituent participation (Sector Central heat feed) — read-only owner
# ─────────────────────────────────────────────────────────────────────────────

def _tiles(sector, perfs, sizes=None):
    sizes = sizes or [1.0] * len(perfs)
    return [{"sector": sector, "size": s,
             "perf": ({"1M": p, "1D": p, "YTD": p} if p is not None else {})}
            for p, s in zip(perfs, sizes)]


def test_heat_all_flat_breadth_is_null_and_rising_share_is_measured_zero():
    row = _aggregate_heat({"tiles": _tiles("Tech", [0.0, 0.0, 0.0])})["Tech"]
    assert row["breadth_pct"] is None              # adv+dec == 0 → no breadth, not 0
    assert (row["adv"], row["dec"]) == (0, 0)
    assert row["n_priced_1M"] == 3 and row["n_unchanged_1M"] == 3
    # rising / priced is a MEASURED zero: three priced observations, none rising
    assert row["adv"] / row["n_priced_1M"] == 0.0


def test_heat_all_declining_breadth_is_measured_zero_not_null():
    row = _aggregate_heat({"tiles": _tiles("Tech", [-1.0, -2.0])})["Tech"]
    assert row["breadth_pct"] == 0.0 and row["breadth_pct"] is not None


def test_heat_unchanged_population_separates_the_two_denominators():
    # Financials specimen: 75 members, 73 priced, 59 advancing, 14 declining, 2 missing
    perfs = [1.0] * 59 + [-1.0] * 14 + [None] * 2
    row = _aggregate_heat({"tiles": _tiles("Fin", perfs)})["Fin"]
    assert (row["n_tiles"], row["n_priced_1M"], row["adv"], row["dec"]) == (75, 73, 59, 14)
    assert row["n_tiles"] - row["n_priced_1M"] == 2          # missing: neither down nor 0
    assert row["breadth_pct"] == round(100 * 59 / 73)        # agree when unchanged == 0
    # add 7 unchanged names: the denominators now differ
    row2 = _aggregate_heat({"tiles": _tiles("Fin", perfs + [0.0] * 7)})["Fin"]
    assert row2["n_unchanged_1M"] == 7
    assert row2["breadth_pct"] == round(100 * 59 / 73)       # unchanged excluded
    assert row2["adv"] / row2["n_priced_1M"] == pytest.approx(59 / 80)   # priced includes it


def test_heat_missing_member_does_not_shrink_into_a_full_coverage_claim():
    row = _aggregate_heat({"tiles": _tiles("Util", [2.0, None, None, -1.0],
                                           sizes=[4.0, 3.0, 2.0, 1.0])})["Util"]
    assert row["n_tiles"] == 4 and row["n_priced_1M"] == 2
    assert row["weight_coverage_1M"] == pytest.approx(5.0 / 10.0)   # weight ≠ count coverage


def test_heat_partial_weight_mean_is_over_the_priced_subset_only():
    row = _aggregate_heat({"tiles": _tiles("Util", [2.0, None, -1.0],
                                           sizes=[3.0, 6.0, 1.0])})["Util"]
    # cap-weighted mean of the PRICED tiles; the unpriced 6.0 weight is disclosed
    assert row["heat_1M"] == pytest.approx((3 * 2.0 + 1 * -1.0) / 4.0, abs=0.005)
    assert row["weight_coverage_1M"] == pytest.approx(0.4)


def test_heat_weight_proxy_basis_is_equal_weight():
    row = _aggregate_heat({"size_basis": "weight_proxy",
                           "tiles": _tiles("Util", [2.0, -1.0], sizes=[9.0, 1.0])})["Util"]
    assert row["heat_1M"] == pytest.approx(0.5)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Sector-level breadth, weights, overlap and roster change (rotation context)
# ─────────────────────────────────────────────────────────────────────────────

def test_positive_sector_breadth_all_flat_is_measured_zero():
    b = lrc.breadth(0, 11, 11)
    assert b.k_over_n == 0.0 and lrc.is_measured(b.k_over_n)


def test_positive_sector_breadth_no_measured_members_is_unmeasured_not_zero():
    b = lrc.breadth(0, 0, 11)
    assert not lrc.is_measured(b.k_over_n)
    assert b.coverage == 0.0 and b.bounds == (0.0, 1.0)


def test_breadth_missing_members_give_identification_bounds():
    b = lrc.breadth(6, 9, 11)
    assert b.k_over_n == pytest.approx(6 / 9) and b.coverage == pytest.approx(9 / 11)
    assert b.bounds == (pytest.approx(6 / 11), pytest.approx(8 / 11))
    assert b.to_dict()["bounds_kind"] == "identification_bounds_not_confidence_interval"


def test_snapshot_flat_sector_is_measured_and_not_positive():
    payload = {"meta": {"asOf": "2026-11-06", "benchmark": "SPY"},
               "sectors": [{"ticker": t, "now": {"rs_63d": 0.0}}
                           for t in lrc.us_sector_cohort()]}
    snap = lrc.sector_cohort_snapshot(payload)
    assert snap["positive_breadth"]["k_over_n"] == 0.0
    assert len(snap["measured"]) == 11


def test_partial_weight_map_is_refused_not_renormalised():
    assert not isinstance(lrc.normalize_weights({"A": 0.5, "B": 0.5}), lrc.Unmeasured)
    partial = lrc.normalize_weights({"A": 0.5, "B": None})
    assert isinstance(partial, lrc.Unmeasured) and partial.reason == "missing_input"
    assert isinstance(lrc.overlap({"A": 1.0, "B": None}, {"A": 1.0}), lrc.Unmeasured)


def test_weight_coverage_differs_from_count_coverage():
    wc = lrc.weight_coverage({"A": 8.0, "B": 1.0, "C": 1.0}, ["B", "C"])
    assert wc["count_coverage"] == pytest.approx(2 / 3)
    assert wc["measured_weight_share"] == pytest.approx(0.2)
    assert wc["missing_ids"] == ["A"]


def test_overlap_is_issuer_weight_overlap_and_shared_members_are_listed():
    assert lrc.overlap({"A": 1, "B": 1}, {"B": 1, "C": 1}) == pytest.approx(0.5)
    assert lrc.shared_members({"A": 1, "B": 1}, {"B": 1, "C": 1}) == ["B"]


def test_changed_roster_breadth_rise_from_entrants_is_composition_only():
    ch = lrc.breadth_change({"A": False, "B": False}, {"A": False, "B": False, "C": True})
    assert ch["entrants"] == ["C"] and ch["newly_positive_common"] == []
    assert ch["composition_only"] is True


def test_changed_roster_removed_member_leaves_the_reconstructed_index():
    idx = pd.bdate_range("2024-01-01", periods=10)
    members = [{"ticker": "A", "added": "2024-01-01", "removed": None},
               {"ticker": "B", "added": "2024-01-01", "removed": "2024-01-08"}]
    close = pd.DataFrame({"A": 1.0, "B": 1.0}, index=idx)
    mask = basket_index._live_mask(members, idx, ["A", "B"], pit=False, close=close)
    assert mask["B"].loc[:"2024-01-05"].all() and not mask["B"].loc["2024-01-08":].any()


def test_as_known_cohort_excludes_a_back_projected_member_before_curation():
    rows = [{"member_id": "A", "effective_from": "2020-01-01", "known_at": "2020-01-01"},
            {"member_id": "B", "effective_from": "2020-01-01", "known_at": "2025-06-01"}]
    recon = lrc.cohort_at(rows, as_of="2023-01-02")
    known = lrc.cohort_at(rows, as_of="2023-01-02", as_known=True)
    assert recon["members"] == ["A", "B"]
    assert known["members"] == ["A"] and known["excluded_not_yet_known"] == ["B"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Producer ordinals (Sector Cycles rs_rank / rs_21d_rank)
# ─────────────────────────────────────────────────────────────────────────────

def _r(rid, r63, r21):
    return {"id": rid, "now": {"rs_63d": r63, "rs_21d": r21}}


def test_rank_never_assigns_an_ordinal_to_null_nan_or_bool():
    recs = [_r("a", 1.0, 0.5), _r("b", float("nan"), None), _r("c", True, 2.0),
            _r("d", -3.0, float("inf"))]
    sc._stamp_rs_ranks(recs)
    by = {r["id"]: r["now"] for r in recs}
    assert by["a"]["rs_rank"] == 1 and by["d"]["rs_rank"] == 2
    assert by["b"]["rs_rank"] is None and by["c"]["rs_rank"] is None
    assert by["b"]["rs_21d_rank"] is None and by["d"]["rs_21d_rank"] is None
    assert (by["c"]["rs_21d_rank"], by["a"]["rs_21d_rank"]) == (1, 2)


def test_rank_ties_keep_registry_order_and_are_disclosed():
    recs = [_r("x", 2.0, 1.0), _r("y", 5.0, 1.0), _r("z", 2.0, 0.0)]
    sc._stamp_rs_ranks(recs)
    do = sc.display_order(recs, cohort="t", benchmark="SPY")
    h63 = do["horizons"]["rs_rank"]
    assert h63["ordered_ids"] == ["y", "x", "z"]        # x before z: registry order
    assert h63["tie_groups"] == [["x", "z"]]
    assert do["horizons"]["rs_21d_rank"]["tie_groups"] == [["x", "y"]]


def test_display_order_is_the_source_ordinal_not_array_order():
    recs = [_r("b-zeta", 9.0, -1.0), _r("b-alpha", 1.0, 3.0), _r("b-mid", None, 2.0)]
    sc._stamp_rs_ranks(recs)
    recs.sort(key=lambda r: r["id"])                     # presentation sort (chip rail)
    do = sc.display_order(recs, cohort="us_theme_baskets", benchmark="SPY")
    assert do["horizons"]["rs_rank"]["ordered_ids"] == ["b-zeta", "b-alpha"]
    assert do["horizons"]["rs_rank"]["unranked_ids"] == ["b-mid"]
    assert do["horizons"]["rs_21d_rank"]["ordered_ids"] == ["b-alpha", "b-mid", "b-zeta"]
    assert do["horizons"]["rs_rank"]["horizon_sessions"] == 63
    assert do["horizons"]["rs_21d_rank"]["horizon_sessions"] == 21
    assert not any(do["authority"].values())


def test_rotation_context_rank_breaks_ties_by_id_not_registry_order():
    # Documented difference: the descriptive measured-context rank (an observation)
    # orders ties by id; the producer display ordinal keeps registry order.
    assert lrc.rank_measured({"z": 1.0, "a": 1.0})["ranked"] == ["a", "z"]


def test_confluence_board_sorts_missing_rs_after_measured_not_as_zero():
    from engine.subsector_confluence import _board_key
    g = lambda k, rs: {"key": k, "class": "neutral", "entry": {"weight": 0.0},
                       "regime": {"rs_60d": rs}}
    rows = [g("none", None), g("neg", -2.0), g("nan", float("nan")), g("pos", 3.0),
            g("zero", 0.0)]
    rows.sort(key=_board_key)
    assert [r["key"] for r in rows] == ["pos", "zero", "neg", "none", "nan"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Turn knowledge — pivot is not confirmation
# ─────────────────────────────────────────────────────────────────────────────

def _walk(seed, n=1500):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2012-01-02", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.018, n))), index=idx)


@pytest.mark.parametrize("seed", range(12))
def test_legacy_replay_pivots_equal_detect_swings(seed):
    px = _walk(seed)
    live = sc._detect_swings(px, 14.0)
    replay, _ = onto.legacy_zigzag_confirmations(px, 14.0)
    assert [(s["i"], s["k"]) for s in live] == [(i, k) for i, k, _ in replay]


def test_pivot_is_not_confirmation():
    px = _walk(4)
    turns = sc._detect_swings(px, 14.0)
    tk = onto.legacy_turn_knowledge(px, turns, pct=14.0, structure_basis="price")
    assert tk["status"] == "measured" and len(tk["confirmed_at"]) == len(turns)
    for t, conf, lag in zip(turns, tk["confirmed_at"], tk["confirmation_sessions"]):
        if t["provisional"]:
            assert conf is None and lag is None
        else:
            assert conf > t["date"] and lag >= 1          # strictly after the pivot
            # the confirming close really crossed the threshold from the pivot
            p_conf, p_piv = float(px.loc[conf]), float(px.loc[t["date"]])
            if t["k"] == "peak" and t["i"] > 0:
                assert p_conf <= p_piv * 0.86 + 1e-9
            elif t["k"] == "trough" and t["i"] > 0:
                assert p_conf >= p_piv * 1.14 - 1e-9
    anchor = tk["anchor"]
    last_conf = [t for t in turns if not t["provisional"]][-1]
    assert anchor["pivot_date"] == last_conf["date"]     # unconfirmed tail never anchors
    assert anchor["confirmed_at"] != anchor["pivot_date"]


def test_turn_knowledge_window_view_aligns_with_published_turns():
    px = _walk(7)
    turns = [t for t in sc._detect_swings(px, 14.0)][3:]    # windowed suffix
    tk = onto.legacy_turn_knowledge(px, turns, pct=14.0, structure_basis="price")
    assert tk["status"] == "measured" and len(tk["confirmed_at"]) == len(turns)
    assert tk["first_pivot_is_series_seed"] is False


def test_turn_knowledge_replay_mismatch_is_unavailable_not_guessed():
    px = _walk(5)
    turns = copy.deepcopy(sc._detect_swings(px, 14.0))
    turns[-2]["date"] = "1999-01-01"
    tk = onto.legacy_turn_knowledge(px, turns, pct=14.0, structure_basis="price")
    assert tk["status"] == "unavailable" and tk["reason"] == "detector_replay_mismatch"
    assert tk["confirmed_at"] is None and tk["anchor"] is None


def test_turn_knowledge_as_known_stays_unavailable_and_has_no_epoch():
    px = _walk(6)
    tk = onto.legacy_turn_knowledge(px, sc._detect_swings(px, 14.0), pct=14.0,
                                    structure_basis="price",
                                    as_known_blockers=["current_roster_back_projected"])
    assert tk["as_known"]["status"] == "unavailable"
    assert "current_roster_back_projected" in tk["as_known"]["reasons"]
    assert tk["epoch"] is None and tk["detector_version"] == "zigzag_pct.v1"


def test_fixed_turns_keep_window_edges_and_anchor_as_today_advances():
    px = _walk(9, n=2500)
    turns = sc._detect_swings(px, 14.0)
    tk = onto.legacy_turn_knowledge(px, turns, pct=14.0, structure_basis="price")
    first = rhythm_window(turns, turns[-1]["x"])
    if first["status"] == "unavailable":
        pytest.skip("fewer than three confirmed turns on this walk")
    statuses = set()
    for today in np.arange(turns[-1]["x"], turns[-1]["x"] + 6.0, 0.05):
        w = rhythm_window(turns, float(today))
        assert w["window_x"] == first["window_x"] and w["window"] == first["window"]
        assert w["anchor_x"] == first["anchor_x"]
        statuses.add(w["status"])
    assert "past_window" in statuses                     # state changes, edges do not
    anchor_turn = [t for t in turns if not t["provisional"]][-1]
    assert round(anchor_turn["x"], 3) == first["anchor_x"]
    assert tk["anchor"]["pivot_date"] == anchor_turn["date"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. History knowledge — reconstructed vs as-known
# ─────────────────────────────────────────────────────────────────────────────

def test_basket_history_knowledge_counts_back_projection_and_removals():
    members = [
        {"ticker": "A", "added": "2023-05-09", "curated_added": "2023-05-09", "removed": None},
        {"ticker": "B", "added": "2023-05-09", "curated_added": "2025-02-01", "removed": None},
        {"ticker": "C", "added": "2023-05-09", "curated_added": "2023-05-09",
         "removed": "2024-03-01"},
    ]
    hk = sc._history_knowledge_basket(members, created="2023-05-09",
                                      series_start=pd.Timestamp("2010-01-04"))
    m = hk["membership"]
    assert (m["n_members"], m["n_current"], m["n_removed"]) == (3, 2, 1)
    assert m["n_back_projected"] == 3                    # all counted before 2010 curation
    assert m["current_roster_known_from"] == "2025-02-01"
    assert hk["as_known_history"]["status"] == "unavailable"
    assert hk["as_known_history"]["reasons"] == ["price_vintage_not_retained",
                                                 "current_roster_back_projected"]


def test_basket_history_knowledge_missing_curation_is_disclosed():
    hk = sc._history_knowledge_basket([{"ticker": "A", "removed": None}], created=None,
                                      series_start=pd.Timestamp("2020-01-02"))
    assert hk["membership"]["current_roster_known_from"] is None
    assert "member_knowledge_time_missing" in hk["as_known_history"]["reasons"]


def test_sector_history_is_reconstructed_even_for_a_single_instrument():
    hk = sc._history_knowledge_sector()
    assert hk["membership"] == {"kind": "single_instrument"}
    assert hk["as_known_history"]["status"] == "unavailable"


@pytest.mark.skipif(not MEMBERSHIP.exists(), reason="data/baskets not materialized")
def test_membership_curation_evidence_is_complete_and_ordered():
    doc = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    for bid, b in doc["baskets"].items():
        for m in b["members"]:
            assert m.get("curated_added"), (bid, m["ticker"])
            assert str(m["curated_added"]) >= str(b["created"]), (bid, m["ticker"])


# ─────────────────────────────────────────────────────────────────────────────
# 6. Current-MODEL qualification — each single failed qualifier → no MODEL value
# ─────────────────────────────────────────────────────────────────────────────

def _down_model_block(p=(0.11, 0.33, 0.55)):
    return {"epoch": "price_c4414dcb", "revision_optimistic": True,
            "direction": "down", "turn_kind": "trough",
            "1m": {"p": p[0], "source": "MODEL", "cell_verdict": "PASS"},
            "3m": {"p": p[1], "source": "MODEL", "cell_verdict": "PASS"},
            "6m": {"p": p[2], "source": "MODEL", "cell_verdict": "PASS"}}


_HOLDS = {"verdict": "PARITY_HOLDS", "failing": []}
_GOOD = dict(parity=_HOLDS, turn_epoch="price_c4414dcb", family="sector",
             structure_basis="price", turn_direction="down")
_H = ("1m", "3m", "6m")


def _assert_withheld(out, qualifier):
    assert out["unavailable"] is True
    assert out["unavailable_reason"] == "current_model_unqualified"
    assert not any(h in out for h in _H)                  # no from-now cell at all
    assert out["current_model"]["qualified"] is False
    assert qualifier in out["current_model"]["failing"]
    # the KM PRIOR has no population reading (row-weighted at-risk) → withheld, no number
    assert out["prior"]["status"] == "withheld"
    assert out["prior"]["reason"] == "km_by_month_at_risk_counts_panel_rows_not_legs"
    blob = json.dumps(out)
    assert '"MODEL"' not in blob and '"p"' not in blob


@needs_hazard
def test_all_qualifiers_hold_keeps_model():
    out = hs.qualify_current_model(_down_model_block(), **_GOOD)
    assert [out[h]["source"] for h in _H] == ["MODEL"] * 3
    assert out["current_model"]["qualified"] is True
    assert out["current_model"]["failing"] == []
    assert "closing extremum" in out["current_model"]["target"]
    assert "prior" not in out and not out.get("unavailable")


_SINGLE_FAILURES = {
    "parity": dict(parity={"verdict": "PARITY_FAILS"}),
    "epoch": dict(turn_epoch=None),
    "cohort": dict(family="basket"),
    "direction": dict(turn_direction="up"),
    "basis": dict(structure_basis="tr_fallback"),
}


@needs_hazard
@pytest.mark.parametrize("qualifier", sorted(_SINGLE_FAILURES))
def test_single_failed_block_qualifier_downgrades_model_to_prior(qualifier):
    kw = dict(_GOOD)
    kw.update(_SINGLE_FAILURES[qualifier])
    out = hs.qualify_current_model(_down_model_block(), **kw)
    assert out["current_model"]["failing"] == [qualifier]
    assert out["current_model"]["withheld_horizons"] == list(_H)
    _assert_withheld(out, qualifier)


@needs_hazard
def test_single_failed_horizon_downgrades_model_to_prior():
    model = json.loads(MODEL_PATH.read_text())
    model["ledger"]["down"]["6m"]["verdict"] = "PRIOR"
    out = hs.qualify_current_model(_down_model_block(), model=model, **_GOOD)
    assert out["current_model"]["failing"] == ["horizon"]
    _assert_withheld(out, "horizon")


@needs_hazard
def test_a_prior_cell_inside_a_passing_ledger_fails_the_horizon_qualifier():
    hz = _down_model_block()
    hz["6m"] = {"p": 0.9, "source": "PRIOR", "cell_verdict": "PRIOR"}
    out = hs.qualify_current_model(hz, **_GOOD)
    assert out["current_model"]["failing"] == ["horizon"]
    assert out["current_model"]["withheld_horizons"] == ["1m", "3m"]
    _assert_withheld(out, "horizon")


@needs_hazard
def test_up_leg_never_qualifies_because_up_3m_6m_are_prior_cells():
    hz = dict(_down_model_block(), direction="up", turn_kind="peak")
    out = hs.qualify_current_model(hz, **dict(_GOOD, turn_direction="up"))
    assert out["current_model"]["failing"] == ["horizon"]
    _assert_withheld(out, "horizon")


@needs_hazard
def test_partial_curve_downgrades_model_to_prior():
    hz = _down_model_block()
    del hz["6m"]
    out = hs.qualify_current_model(hz, **_GOOD)
    assert out["current_model"]["failing"] == ["horizon", "whole_curve"]
    _assert_withheld(out, "whole_curve")


@needs_hazard
def test_inverted_model_curve_is_withheld_whole_not_sorted():
    out = hs.qualify_current_model(_down_model_block((0.6, 0.3, 0.9)), **_GOOD)
    assert out["current_model"]["failing"] == ["whole_curve"]
    _assert_withheld(out, "whole_curve")
    pre = hs._enforce_hazard_cdf(_down_model_block((0.6, 0.3, 0.9)))
    out2 = hs.qualify_current_model(pre, **_GOOD)
    assert "whole_curve" in out2["current_model"]["failing"]
    _assert_withheld(out2, "whole_curve")


@needs_hazard
def test_withheld_block_is_independent_of_the_model_value():
    kw = dict(_GOOD, parity={"verdict": "PARITY_FAILS"})
    a = hs.qualify_current_model(_down_model_block((0.1, 0.2, 0.3)), **kw)
    b = hs.qualify_current_model(_down_model_block((0.4, 0.5, 0.6)), **kw)
    assert a == b


@needs_hazard
def test_km_prior_is_row_weighted_and_therefore_withheld():
    # the KM at-risk at age 1 equals the number of panel ROWS (not legs) — the
    # reason no PRIOR number is shown (B12 Q9)
    km = json.loads(KM_PATH.read_text())
    up = km["families"]["us_sector"]["up"]
    assert up["km_by_month"][0]["age_m"] == 1
    assert up["km_by_month"][0]["at_risk"] == up["n_rows"]


@needs_hazard
def test_direction_mismatch_reports_the_confirmed_leg_and_keeps_the_scored_one():
    out = hs.qualify_current_model(_down_model_block(),
                                   **dict(_GOOD, turn_direction="up"))
    assert out["direction"] == "up" and out["turn_kind"] == "peak"
    assert out["scored_direction"] == "down"


@needs_hazard
def test_no_confirmed_turn_omits_direction_rather_than_using_the_phase():
    out = hs.qualify_current_model(_down_model_block(),
                                   **dict(_GOOD, turn_direction=None))
    assert "direction" not in out and "turn_kind" not in out
    assert out["scored_direction"] == "down"
    assert out["prior"]["direction"] is None


@needs_hazard
def test_basket_prior_disclosure_does_not_match_the_record():
    out = hs.qualify_current_model(_down_model_block(), **dict(_GOOD, family="basket"))
    assert out["prior"]["population_matches_record"] is False


@needs_hazard
def test_withheld_curve_keeps_the_parity_claim_in_estimate_kinds():
    out = hs.qualify_current_model(_down_model_block(),
                                   **dict(_GOOD, parity={"verdict": "PARITY_FAILS"}))
    ek = estimate_kinds({"hazard": out}, {"status": "unavailable"})
    assert set(ek["hazard"].values()) == {"missing_estimate"}
    assert ek["model_withheld_horizons"] == list(_H)
    assert ek["model_cell_current_claim"] == "parity_failed"
    assert ek["live_feature_parity"]["report_ref"] == "meta.live_hazard_parity"


@needs_hazard
def test_withheld_for_another_qualifier_never_claims_parity_holds(monkeypatch):
    import engine.hazard_parity as hpar
    monkeypatch.setattr(hpar, "LIVE_HAZARD_PARITY", {"verdict": "PARITY_HOLDS", "failing": []})
    out = hs.qualify_current_model(_down_model_block(), **dict(_GOOD, turn_epoch=None))
    ek = estimate_kinds({"hazard": out}, {"status": "unavailable"})
    assert ek["model_cell_current_claim"] == "qualifier_failed"


@needs_hazard
def test_live_sector_build_emits_no_current_model_cell():
    from engine import hazard_parity as hp
    tape = hp.synthetic_tape()
    rec = hp.live_record(tape, tape["index"][-1])
    assert rec["turn_knowledge"]["status"] == "measured"
    for t in rec["turns"]:                                # per-turn knowledge rides the turn
        assert ("confirmed_at" in t) and (t["confirmed_at"] is None) == bool(t["provisional"])
        assert t["confirmed_at"] is None or t["confirmed_at"] > t["date"]
    assert rec["turn_knowledge"]["anchor"]["confirmed_at"] is not None
    assert rec["history_knowledge"]["as_known_history"]["status"] == "unavailable"
    hz = rec["now"].get("hazard")
    assert hz is not None and hz["unavailable"] is True
    assert not any(h in hz for h in _H)
    assert {"parity", "epoch"} <= set(hz["current_model"]["failing"])
    json.dumps(rec)                                       # payload stays JSON-clean
