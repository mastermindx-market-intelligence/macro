"""Hermetic tests for engine/flow_sign_uncertainty.py (Q04 research reference, not wired).

Synthetic inputs only: no network, no repository data, no clock, no tree scan.
"""
from __future__ import annotations

import builtins
import importlib
import inspect
import math
import sys
import threading

import numpy as np

import engine.flow_sign_uncertainty as fsu


def _raises(exc, fn, *a, **k) -> bool:
    try:
        fn(*a, **k)
    except exc:
        return True
    return False


# ── req1: quote-rule agreement is never labeled aggressor accuracy ───────────

def test_req1_quote_rule_agreement_is_not_aggressor_accuracy():
    a = [1, 1, -1, -1, 1, 0, np.nan]
    b = [1, -1, -1, 1, 1, 1, 1]
    for prov in ("quote_rule", "tick_rule", "lee_ready", "production_side",
                 "quote_rule_self_consistency", "execution_location", "delta_adjusted"):
        rep = fsu.agreement_report(a, b, label_provenance=prov)
        assert rep["metric_kind"] == "self_consistency"
        assert rep["is_aggressor_accuracy"] is False
        assert rep["n_both_signed"] == 5
        assert math.isclose(rep["agreement"], 3 / 5)
    rep = fsu.agreement_report(a, b, label_provenance="vendor_side_field")
    assert rep["metric_kind"] == "aggressor_accuracy" and rep["is_aggressor_accuracy"] is True
    assert _raises(ValueError, fsu.agreement_report, a, b, label_provenance="trust_me")

    floor = fsu.disagreement_error_floor(a, b)
    assert math.isclose(floor["disagreement"], 2 / 5)
    assert math.isclose(floor["error_sum_floor"], 2 / 5)
    assert math.isclose(floor["max_error_floor"], 1 / 5)
    assert fsu.disagreement_error_floor([0], [0])["disagreement"] is None


def test_req1_calibrated_buy_probability_refuses_quote_derived_labels():
    seg = ["s1", "s1", "s2", "s2"]
    y = [1, 1, 0, 1]
    assert _raises(fsu.IndependentLabelsRequired, fsu.calibrate_buy_probability,
                   seg, y, label_provenance="quote_rule", shrinkage_k=5.0)
    assert _raises(fsu.IndependentLabelsRequired, fsu.calibrate_buy_probability,
                   seg, None, label_provenance="vendor_side_field", shrinkage_k=5.0)
    assert issubclass(fsu.IndependentLabelsRequired, ValueError)
    assert fsu.VERDICT == "INSUFFICIENT_DATA"
    assert "_dbento_sample.parquet" in fsu.MISSING_INPUT
    side = fsu.annotate_production_sign("~buy", {"unidentified": 0.4, "lower": -0.1, "upper": 0.7})
    assert side["sidecar_is_aggressor_accuracy"] is False


# ── req2: stale/locked/crossed quotes, ties and corrections have explicit outcomes ──

def test_req2_explicit_print_outcomes():
    kw = dict(quote_age_ms=10.0, max_quote_age_ms=1000.0)
    cases = [
        (fsu.classify_print(1.00, 1.00, 1.10, **kw), fsu.AT_BID, -1),
        (fsu.classify_print(1.10, 1.00, 1.10, **kw), fsu.AT_ASK, 1),
        (fsu.classify_print(1.08, 1.00, 1.10, **kw), fsu.INSIDE_ABOVE_MID, None),
        (fsu.classify_print(1.02, 1.00, 1.10, **kw), fsu.INSIDE_BELOW_MID, None),
        (fsu.classify_print(1.05, 1.00, 1.10, **kw), fsu.MIDPOINT_TIE, None),
        (fsu.classify_print(1.20, 1.00, 1.10, **kw), fsu.OUTSIDE_ABOVE, None),
        (fsu.classify_print(0.90, 1.00, 1.10, **kw), fsu.OUTSIDE_BELOW, None),
        (fsu.classify_print(1.00, 1.00, 1.00, **kw), fsu.LOCKED, None),
        (fsu.classify_print(1.00, 1.10, 1.00, **kw), fsu.CROSSED, None),
        (fsu.classify_print(1.05, 1.00, 1.10, quote_age_ms=5000.0, max_quote_age_ms=1000.0),
         fsu.STALE_QUOTE, None),
        (fsu.classify_print(1.05, 1.00, 1.10, quote_age_ms=-1.0, max_quote_age_ms=1000.0),
         fsu.FUTURE_QUOTE, None),
        (fsu.classify_print(1.05, None, 1.10, **kw), fsu.NO_QUOTE, None),
        (fsu.classify_print(1.05, 1.00, 1.10, quote_age_ms=None, max_quote_age_ms=None),
         fsu.NO_QUOTE, None),
        (fsu.classify_print(1.05, 1.00, 1.10, corrected=True, **kw), fsu.CORRECTED, None),
        (fsu.classify_print(float("nan"), 1.00, 1.10, **kw), fsu.INVALID_PRINT, None),
    ]
    for got, outcome, sign in cases:
        assert got.outcome == outcome, (got, outcome)
        assert got.identified_sign == sign
        assert got.outcome in fsu.PRINT_OUTCOMES
        assert got.reason
    # inside-spread quote-rule sign is reported but never treated as identified
    inside = fsu.classify_print(1.08, 1.00, 1.10, **kw)
    assert inside.quote_rule_sign == 1 and inside.identified_sign is None
    # an explicit None staleness limit disables the stale rule (stated, not defaulted)
    assert fsu.classify_print(1.10, 1.00, 1.10, quote_age_ms=9e9, max_quote_age_ms=None).outcome == fsu.AT_ASK


def test_req2_tick_ties_and_bounds_exclusions():
    assert fsu.tick_outcome(1.0, None, None) == (fsu.NO_PRIOR_TRADE, None)
    assert fsu.tick_outcome(1.1, 1.0, None) == (fsu.UPTICK, 1)
    assert fsu.tick_outcome(0.9, 1.0, 1) == (fsu.DOWNTICK, -1)
    assert fsu.tick_outcome(1.0, 1.0, -1) == (fsu.ZERO_TICK_CARRY, -1)
    assert fsu.tick_outcome(1.0, 1.0, None) == (fsu.ZERO_TICK_NO_PRIOR, None)

    kw = dict(quote_age_ms=1.0, max_quote_age_ms=None)
    outs = [
        fsu.classify_print(1.10, 1.00, 1.10, **kw),            # at ask, +1, v=100
        fsu.classify_print(1.05, 1.00, 1.10, **kw),            # tie, unidentified, v=50
        fsu.classify_print(1.00, 1.00, 1.00, **kw),            # locked, unidentified, v=50
        fsu.classify_print(1.10, 1.00, 1.10, corrected=True, **kw),  # excluded, v=999
    ]
    b = fsu.bounds_from_prints(outs, [100.0, 50.0, 50.0, 999.0])
    assert b["gross"] == 200.0 and b["n_excluded"] == 1
    assert math.isclose(b["net_identified"], 0.5)
    assert math.isclose(b["unidentified"], 0.5)
    assert math.isclose(b["lower"], 0.0) and math.isclose(b["upper"], 1.0)
    empty = fsu.bounds_from_prints([outs[3]], [10.0])
    assert empty["lower"] is None and empty["gross"] == 0.0

    eb = fsu.event_bounds(0.8, 0.5, 0.25)
    assert math.isclose(eb["unidentified"], 1 - 0.8 * 0.75)
    assert math.isclose(eb["net_identified"], 0.8 * 0.25)
    # nulls are unidentified, never a measured zero sign
    nb = fsu.event_bounds(None, None, None)
    assert nb["unidentified"] == 1.0 and nb["lower"] == -1.0 and nb["upper"] == 1.0
    arr = fsu.event_bounds_arrays([0.8, np.nan], [0.5, 0.3], [0.25, np.nan])
    assert math.isclose(arr["unidentified"][0], eb["unidentified"])
    assert arr["unidentified"][1] == 1.0
    assert fsu.label_is_identified("~buy", 0.01, 0.9) is True
    assert fsu.label_is_identified("~buy", -0.01, 0.9) is False
    assert fsu.label_is_identified("~sell", -0.9, -0.01) is True
    assert fsu.label_is_identified("~sell", -0.9, 0.01) is False
    assert fsu.label_is_identified("mixed", -1, 1) is None


# ── req3: trade order + receipt cutoff preserved; no universal lag constant ──

def test_req3_trade_order_receipt_cutoff_and_required_lag():
    recs = [
        {"id": "c", "trade_ts": 3.0, "seq": 0, "receipt_ts": 3.5},
        {"id": "a1", "trade_ts": 1.0, "seq": 0, "receipt_ts": 9.0},   # received late
        {"id": "b1", "trade_ts": 2.0, "seq": 0, "receipt_ts": 2.1},
        {"id": "b2", "trade_ts": 2.0, "seq": 0, "receipt_ts": 2.0},   # tie: input order kept
        {"id": "z", "trade_ts": 0.5, "seq": 0, "receipt_ts": 20.0},   # after cutoff
    ]
    kept, late = fsu.order_prints(recs, receipt_cutoff=10.0)
    assert [r["id"] for r in kept] == ["a1", "b1", "b2", "c"]
    assert late == 1

    sig = inspect.signature(fsu.align_quote_asof)
    assert sig.parameters["quote_lag_ms"].default is inspect.Parameter.empty
    assert sig.parameters["quote_lag_ms"].kind is inspect.Parameter.KEYWORD_ONLY
    sig2 = inspect.signature(fsu.classify_print)
    assert sig2.parameters["max_quote_age_ms"].default is inspect.Parameter.empty
    assert sig2.parameters["quote_age_ms"].default is inspect.Parameter.empty
    assert _raises(TypeError, fsu.align_quote_asof, 10_000.0, [0.0, 6000.0, 9000.0])
    q = [0.0, 6000.0, 9000.0]
    assert fsu.align_quote_asof(10_000.0, q, quote_lag_ms=0.0) == 2
    assert fsu.align_quote_asof(10_000.0, q, quote_lag_ms=5000.0) == 0
    assert fsu.align_quote_asof(10.0, q, quote_lag_ms=5000.0) == -1
    assert _raises(ValueError, fsu.align_quote_asof, 1.0, [3.0, 1.0], quote_lag_ms=0.0)
    # behavioural: quote_lag_ms=0 applies no hidden lag (a quote stamped exactly at
    # the trade is causally prior and selected), and the result moves with the lag
    dense = [float(x) for x in range(0, 10_001, 1000)]
    assert fsu.align_quote_asof(10_000.0, dense, quote_lag_ms=0.0) == len(dense) - 1
    picks = [fsu.align_quote_asof(10_000.0, dense, quote_lag_ms=lag)
             for lag in (0.0, 1.0, 1000.0, 2500.0, 5000.0, 10_000.0, 10_001.0)]
    assert picks == [10, 9, 9, 7, 5, 0, -1]
    # no staleness rule applies when max_quote_age_ms=None, even for a very old quote
    old_q = fsu.classify_print(1.10, 1.00, 1.10, quote_age_ms=1e12, max_quote_age_ms=None)
    assert old_q.outcome == "at_ask"
    assert fsu.classify_print(1.10, 1.00, 1.10, quote_age_ms=2.0, max_quote_age_ms=1.0).outcome == "stale_quote"
    # no module-level numeric lag/age constant can silently supply a default
    for name, val in vars(fsu).items():
        if ("LAG" in name.upper() or "AGE_MS" in name.upper()) and isinstance(val, (int, float)):
            raise AssertionError(f"universal time constant present: {name}")


# ── req4: train/test sessions and contracts separated as preregistered ───────

def test_req4_session_and_contract_separation():
    sessions = ["d5", "d1", "d3", "d2", "d7", "d4", "d6", "d1"]
    tr, te = fsu.chronological_split(sessions, 0.6)
    assert tr == ["d1", "d2", "d3", "d4"] and te == ["d5", "d6", "d7"]
    assert not set(tr) & set(te) and max(tr) < min(te)

    train_keys = [("SPY", "C", "e1", 500.0), ("QQQ", "P", "e1", 400.0)]
    test_keys = [("SPY", "C", "e1", 500.0), ("SPY", "C", "e1", 505.0), ("QQQ", "P", "e1", 400.0)]
    m = fsu.contract_disjoint_mask(train_keys, test_keys)
    assert m.tolist() == [False, True, False]

    # training-only fits: test values never move the fitted edges
    train_spread = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    e1 = fsu.liquidity_edges(train_spread)
    e2 = fsu.liquidity_edges(train_spread + [np.nan])
    assert e1 == e2
    assert _raises(ValueError, fsu.liquidity_edges, [0.1, np.nan])

    # LOSO k selection uses training rows only, and ties go to the larger k
    y = np.array([0.5] * 12)
    cells = np.array(["a", "b"] * 6, dtype=object)
    sess = np.array(["d1"] * 4 + ["d2"] * 4 + ["d3"] * 4, dtype=object)
    k, scores = fsu.choose_k_loso(y, cells, sess, [0, 5, 20])
    assert k == 20.0 and set(scores) == {0.0, 5.0, 20.0}
    assert _raises(ValueError, fsu.choose_k_loso, y, cells, np.array(["d1"] * 12, dtype=object), [0])


# ── req5: segments reported; correlated prints do not inflate effective N ────

def test_req5_segments_and_honest_n():
    t = fsu.time_segment([569, 570, 629, 630, 869, 870, 975, 976, np.nan])
    assert t.tolist() == ["other", "open", "open", "mid", "mid", "late", "late", "other", "other"]
    liq = fsu.assign_liquidity([0.01, 0.035, 0.06, np.nan], (0.02, 0.04))
    assert liq.tolist() == ["liq_t1_tight", "liq_t2", "liq_t3_wide", "liq_unknown"]

    rng = np.random.default_rng(7)
    sess = np.repeat(np.array(["s1", "s2", "s3", "s4", "s5"], dtype=object), 4)
    em = rng.uniform(0.0, 1.0, sess.size)
    eb = em + rng.uniform(0.0, 0.2, sess.size)
    r1 = fsu.session_block_bootstrap_skill(sess, em, eb, n_boot=400, seed=11)
    assert r1["n_blocks"] == 5 and r1["n_rows"] == 20
    # duplicating every print 25x (perfectly correlated copies) leaves honest N and CI unchanged
    sess25 = np.repeat(sess, 25)
    r25 = fsu.session_block_bootstrap_skill(sess25, np.repeat(em, 25), np.repeat(eb, 25),
                                            n_boot=400, seed=11)
    assert r25["n_blocks"] == 5 and r25["n_rows"] == 500
    assert math.isclose(r25["skill"], r1["skill"], rel_tol=1e-12)
    assert math.isclose(r25["ci_lo"], r1["ci_lo"], rel_tol=1e-9)
    assert math.isclose(r25["ci_hi"], r1["ci_hi"], rel_tol=1e-9)
    assert fsu.effective_n(sess25) == 5

    m = fsu.session_block_bootstrap_mean(sess, em, n_boot=200, seed=3)
    assert m["n_blocks"] == 5 and m["ci_lo"] <= m["mean"] <= m["ci_hi"]

    # calibration by segment, only with independent labels, shrunk toward pooled
    seg = ["liq_t1|open"] * 4 + ["liq_t3|late"] * 2
    lab = [1, 1, 1, 1, 0, 0]
    cal = fsu.calibrate_buy_probability(seg, lab, label_provenance="exchange_aggressor_flag",
                                        shrinkage_k=2.0)
    pooled = 4 / 6
    assert math.isclose(cal["pooled"], pooled)
    assert math.isclose(cal["segments"]["liq_t3|late"]["p_buy"], (0 + 2 * pooled) / 4)
    assert 0.0 < cal["segments"]["liq_t3|late"]["p_buy"] < pooled

    model = fsu.fit_cell_means([0.2, 0.4, 0.9], ["a", "a", "b"], k=0.0)
    pred = fsu.predict_cells(model, ["a", "b", "unseen"])
    assert np.allclose(pred, [0.3, 0.9, 0.5])


# ── req6: delta-adjustment null and production signing/gate preserved ────────

def test_req6_negative_evidence_and_production_preserved():
    ev = fsu.DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE
    assert ev["tick_minute_agreement"] == 0.556
    assert ev["delta_adjusted_minute_agreement"] == 0.526
    assert ev["improves_direction"] is False
    assert fsu.delta_adjustment_recommended() is False
    try:
        ev["improves_direction"] = True  # type: ignore[index]
    except TypeError:
        pass
    else:
        raise AssertionError("negative evidence must be immutable")
    for sign in ("~buy", "~sell", "mixed", 1, -1, None):
        out = fsu.annotate_production_sign(sign, {"unidentified": 1.0, "lower": -1.0, "upper": 1.0})
        assert out["production_sign"] == sign
    # the reference never binds production signing or the gate
    for name, val in vars(fsu).items():
        mod = getattr(val, "__module__", None) or getattr(val, "__name__", "")
        assert "flow_signing" not in str(mod), name
        assert "calibrate_flow_signing" not in str(mod), name


# ── no silent activation ─────────────────────────────────────────────────────

def test_no_silent_activation(monkeypatch):
    assert fsu.RESEARCH_ONLY is True
    for forbidden in ("register", "schedule", "activate", "promote", "main", "run"):
        assert not hasattr(fsu, forbidden), forbidden

    def _no_open(*a, **k):
        raise AssertionError("module performed file I/O at import")

    before_mods = set(sys.modules)
    before_threads = threading.active_count()
    monkeypatch.setattr(builtins, "open", _no_open)
    mod = importlib.reload(fsu)
    monkeypatch.undo()
    new_mods = set(sys.modules) - before_mods
    assert not any(m.startswith("engine.") for m in new_mods), new_mods
    assert not any(m.split(".")[0] in {"requests", "urllib3", "http", "socket"} for m in new_mods), new_mods
    assert threading.active_count() == before_threads
    assert mod.RESEARCH_ONLY is True
    assert mod.VERDICT == "INSUFFICIENT_DATA"
    assert (mod.__doc__ or "").startswith("RESEARCH REFERENCE — NOT WIRED")


# ── finisher: edge-sign assumption is disclosed, never presented as sharp ────

def test_edge_sign_assumption_is_disclosed_and_bounds_are_conditional():
    text = fsu.EDGE_SIGN_ASSUMPTION
    assert "untested" in text and "lower bound" in text
    assert "EDGE_SIGN_ASSUMPTION" in fsu.__all__
    doc = fsu.__doc__ or ""
    assert "Maintained edge-sign assumption" in doc
    assert "LOWER BOUND" in doc
    for fn in (fsu.bounds_from_prints, fsu.event_bounds, fsu.label_is_identified):
        assert "EDGE_SIGN_ASSUMPTION" in (fn.__doc__ or "")
        assert "sharp" not in (fn.__doc__ or "").lower().replace("not sharp", "")
    # relaxing the assumption can only widen the ambiguous pool: if a fraction m of
    # edge premium is reclassified as ambiguous, U rises and the bounds widen
    base = fsu.event_bounds(0.8, 0.5, 0.25)
    relaxed = fsu.event_bounds(0.8, 0.5 * 0.9, 0.25 * 0.9)
    assert relaxed["unidentified"] > base["unidentified"]
    assert relaxed["lower"] < base["lower"] and relaxed["upper"] > base["upper"]
