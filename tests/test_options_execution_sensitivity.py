from __future__ import annotations

__doc__ = """Hermetic tests for the Q05 research reference (req1-req6, audit parity, no silent activation).

Imports only stdlib, pytest and the module under test. The incumbent OA-3
quote parser (engine/options_nbbo_cohort.parse_quote_response) and Ruling D
session rules are transcribed below as an independent oracle; the live
cross-check against the real incumbent runs in evaluate.py, not here.
"""

import dataclasses
import inspect
import sys
from decimal import Decimal

import pytest

from engine import options_execution_sensitivity as oes

D = Decimal


def q(t, bid, ask, bs=10, asz=10, **kw):
    return oes.Quote(t=t, bid=D(bid), ask=D(ask), bid_size=bs, ask_size=asz, **kw)


def episode(eid="e1", name="AAA", block="s1", entry=None, exit_=None, **kw):
    entry = entry if entry is not None else (q(0, "1.90", "2.00"),)
    exit_ = exit_ if exit_ is not None else (q(3600, "2.50", "2.60"),)
    kw.setdefault("session_close_t", 20000)
    return oes.Episode(
        episode_id=eid, name=name, contract_id=f"{name}-C", block_id=block,
        boundary_t=kw.pop("boundary_t", 0), entry_quotes=tuple(entry),
        exit_quotes=tuple(exit_), **kw,
    )


# ------------------------------------------------ independent OA-3 oracle
# Transcribed from the incumbent; deliberately NOT built from module helpers.
_ORACLE_FIRM = {0, 1, 3, 4, 5, 7, 8, 12, 13, 14, 15, 16, 42, 48, 49, 50, 51, 52, 53, 54, 56}
_ORACLE_KNOWN = {e for e in range(1, 78) if e not in (74, 76)}


class _OracleRaise(Exception):
    pass


def _o_int(v):
    if type(v) is not int or v < 0:
        raise _OracleRaise
    return v


def _oracle_parse(quotes, *, leg, boundary, query_end, rth_open, rth_close):
    """parse_quote_response row order: boundary, RTH, prices, sizes/exchanges,
    negative/crossed, conditions, per-side validity, conflicting duplicates."""
    seen = {}
    for r in sorted(quotes, key=lambda x: x.t):
        if r.t < boundary or r.t > query_end:
            continue
        if not (r.in_session and rth_open <= r.t < rth_close):
            continue
        if not isinstance(r.bid, Decimal) or not isinstance(r.ask, Decimal):
            raise _OracleRaise
        bs, az, bx, ax = _o_int(r.bid_size), _o_int(r.ask_size), _o_int(r.bid_exchange), _o_int(r.ask_exchange)
        if r.bid < 0 or r.ask < 0 or (r.bid > 0 and r.ask > 0 and r.ask < r.bid):
            continue
        bc, ac = _o_int(r.bid_condition), _o_int(r.ask_condition)
        if leg == "entry":
            ok = r.ask > 0 and az > 0 and ac in _ORACLE_FIRM and ax in _ORACLE_KNOWN
        else:
            ok = r.bid > 0 and bs > 0 and bc in _ORACLE_FIRM and bx in _ORACLE_KNOWN
        if not ok:
            continue
        key = (r.bid, r.ask, bs, az, bx, ax, bc, ac)
        if r.t in seen and seen[r.t] != key:
            raise _OracleRaise
        seen.setdefault(r.t, key)
    if not seen:
        return None
    t = min(seen)
    return next(x for x in quotes if x.t == t and x.in_session)


def _oracle_return(ask, bid):
    cost = D(100) * ask + D("0.65")
    val = D(100) * bid - D("0.65")
    return ((val - cost) / cost * D(100)).quantize(D("0.000001"))


def oracle_oa3(ep, rth_open=0):
    """OA-3 Ruling D at latency 0 -> (status, return or None, entry_t, exit_t)."""
    close = ep.session_close_t
    if not (rth_open <= ep.boundary_t < close):
        return ("excluded", None, None, None)
    if ep.boundary_t + 60 >= close:
        return ("excluded", None, None, None)
    try:
        entry = _oracle_parse(ep.entry_quotes, leg="entry", boundary=ep.boundary_t,
                              query_end=ep.boundary_t + 60, rth_open=rth_open, rth_close=close)
    except _OracleRaise:
        return ("unavailable", None, None, None)
    if entry is None:
        return ("unavailable", None, None, None)
    target = entry.t + 3600
    end = target + 60
    if end >= close or not (rth_open <= target < close):
        return ("excluded", None, None, None)
    try:
        ex = _oracle_parse(ep.exit_quotes, leg="exit", boundary=target, query_end=end,
                           rth_open=rth_open, rth_close=close)
    except _OracleRaise:
        return ("unavailable", None, None, None)
    if ex is None:
        return ("unavailable", None, None, None)
    return ("complete", _oracle_return(entry.ask, ex.bid), entry.t, ex.t)


PARITY_PATHS = {
    "plain": episode(),
    "entry_boundary_plus_60_equals_close": episode(session_close_t=60),
    "exit_window_end_equals_close": episode(session_close_t=3660),
    "exit_window_end_one_before_close": episode(session_close_t=3661),
    "boundary_at_close": episode(boundary_t=500, session_close_t=500),
    "crossed_entry_then_valid": episode(entry=(q(0, "2.10", "2.00"), q(5, "1.90", "2.05")),
                                        exit_=(q(3605, "2.50", "2.60"),)),
    "ask_zero_exit_is_valid_bid_side": episode(exit_=(q(3600, "2.50", "0", asz=0),)),
    "bid_zero_entry_is_valid_ask_side": episode(entry=(q(0, "0", "2.00", bs=0),)),
    "bid_zero_exit_is_invalid": episode(exit_=(q(3600, "0", "2.60", bs=0),)),
    "exchange_74_traded_side": episode(entry=(q(0, "1.9", "2.0", ask_exchange=74), q(3, "1.9", "2.1")),
                                       exit_=(q(3603, "2.5", "2.6"),)),
    "exchange_74_other_side": episode(entry=(q(0, "1.9", "2.0", bid_exchange=74),)),
    "condition_2_traded_side": episode(exit_=(q(3600, "2.5", "2.6", bid_condition=2), q(3610, "2.4", "2.6"))),
    "condition_2_other_side": episode(exit_=(q(3600, "2.5", "2.6", ask_condition=2),)),
    "out_of_rth_quote": episode(entry=(q(0, "1.9", "2.0", in_session=False), q(9, "1.9", "2.2")),
                                exit_=(q(3609, "2.5", "2.6"),)),
    "quote_before_boundary": episode(boundary_t=10, entry=(q(5, "0.1", "0.2"), q(10, "1.9", "2.0")),
                                     exit_=(q(3610, "2.5", "2.6"),)),
    "conflicting_duplicate": episode(entry=(q(0, "1.9", "2.0"), q(0, "1.9", "2.1"))),
    "identical_duplicate": episode(entry=(q(0, "1.9", "2.0"), q(0, "1.9", "2.0"))),
    "malformed_size": episode(entry=(q(0, "1.9", "2.0", asz=-1),)),
    "malformed_condition_on_crossed_row_is_skipped": episode(
        entry=(q(0, "2.1", "2.0", ask_condition=-3), q(1, "1.9", "2.0")), exit_=(q(3601, "2.5", "2.6"),)),
    "malformed_condition_on_valid_row": episode(entry=(q(0, "1.9", "2.0", ask_condition=-3),)),
    "no_entry_quote": episode(entry=(q(61, "1.9", "2.0"),)),
    "no_exit_quote": episode(exit_=(q(3661, "2.5", "2.6"),)),
}


@pytest.mark.parametrize("name", sorted(PARITY_PATHS))
def test_audit_parity_baseline_matches_incumbent_oracle(name):
    ep = PARITY_PATHS[name]
    want = oracle_oa3(ep)
    got = oes.scenario_outcome(ep, oes.BASELINE_SCENARIO)
    assert got["status"] == want[0], (name, got["reason"])
    if want[0] == "complete":
        assert got["ruler"]["net_return_pct"] == want[1]
        assert got["scenario_layer"]["net_return_pct"] == want[1]
        assert (got["entry_t"], got["exit_t"]) == (want[2], want[3])


def test_audit_parity_reason_codes_on_boundary_crossed_and_zero_side():
    r = {n: oes.scenario_outcome(PARITY_PATHS[n], oes.BASELINE_SCENARIO) for n in PARITY_PATHS}
    assert r["entry_boundary_plus_60_equals_close"]["reason"] == "horizon_crosses_session_close"
    assert r["exit_window_end_equals_close"]["reason"] == "horizon_crosses_session_close"
    assert r["exit_window_end_one_before_close"]["status"] == "complete"
    assert r["boundary_at_close"]["reason"] == "entry_boundary_outside_rth"
    for n in ("crossed_entry_then_valid", "exchange_74_traded_side", "out_of_rth_quote",
              "malformed_condition_on_crossed_row_is_skipped", "quote_before_boundary"):
        assert r[n]["status"] == "complete", n
    assert r["crossed_entry_then_valid"]["entry_t"] == 5
    assert r["ask_zero_exit_is_valid_bid_side"]["status"] == "complete"
    assert r["ask_zero_exit_is_valid_bid_side"]["ruler"]["net_return_pct"] == D("24.271119")
    assert r["bid_zero_exit_is_invalid"]["reason"] == "exit_no_eligible_quote_in_window"
    assert r["exchange_74_traded_side"]["entry_t"] == 3
    assert r["exchange_74_other_side"]["status"] == "complete"
    assert r["condition_2_traded_side"]["exit_t"] == 3610
    assert r["condition_2_other_side"]["status"] == "complete"
    assert r["conflicting_duplicate"]["reason"] == "entry_quote_response_invalid"
    assert r["identical_duplicate"]["status"] == "complete"
    assert r["malformed_size"]["reason"] == "entry_quote_response_invalid"
    assert r["malformed_condition_on_crossed_row_is_skipped"]["entry_t"] == 1
    assert r["malformed_condition_on_valid_row"]["reason"] == "entry_quote_response_invalid"


# ---------------------------------------------------------------- req1
def test_req1_ruler_reproduces_oa3_return_exactly():
    # OA-3: 100*((100*bid-0.65)-(100*ask+0.65))/(100*ask+0.65), quantized 1e-6.
    assert oes.ruler_net_return_pct("2.00", "2.50") == D("24.271119")
    assert oes.ruler_net_return_pct("1.00", "0.50") == D("-50.968703")
    assert oes.ruler_net_return_pct("0.05", "0.05") == D("-23.008850")
    for a in ("0.05", "0.37", "1.00", "4.15", "12.80"):
        for b in ("0.00", "0.04", "0.36", "1.01", "13.10"):
            assert oes.ruler_net_return_pct(a, b) == _oracle_return(D(a), D(b))


def test_req1_baseline_scenario_equals_ruler_before_any_extension():
    out = oes.scenario_outcome(episode(), oes.BASELINE_SCENARIO)
    assert out["status"] == "complete"
    assert out["ruler"]["net_return_pct"] == oes.ruler_net_return_pct("2.00", "2.50")
    assert out["scenario_layer"]["net_return_pct"] == out["ruler"]["net_return_pct"]
    assert oes.BASELINE_SCENARIO.fee_per_side_usd == D("0.65")
    assert oes.BASELINE_SCENARIO.latency_s == 0
    assert oes.BASELINE_SCENARIO.min_displayed_contracts == 1


def test_req1_ruler_rejects_out_of_bounds_prices():
    with pytest.raises(oes.ExecutionSensitivityError):
        oes.ruler_net_return_pct("0", "1")
    with pytest.raises(oes.ExecutionSensitivityError):
        oes.ruler_net_return_pct("1", "-0.01")


# ---------------------------------------------------------------- req2
def test_req2_delayed_scenario_never_uses_quote_before_arrival():
    entry = (q(0, "0.90", "1.00"), q(4, "0.95", "1.05"), q(6, "1.40", "1.50"))
    ep = episode(entry=entry, exit_=(q(3606, "2.00", "2.10"), q(3611, "2.00", "2.10")))
    out = oes.scenario_outcome(ep, oes.Scenario(5, 1, D("0.65"), D("0")))
    assert out["status"] == "complete"
    assert out["entry_t"] == 6
    assert out["ruler"]["net_return_pct"] == oes.ruler_net_return_pct("1.50", "2.00")
    assert out["ruler"]["basis"] == oes.DELAYED_RULER_BASIS
    # latency shifts BOTH arrivals: exit target = entry event + 3600 + latency
    assert out["exit_t"] == 6 + oes.EXIT_HORIZON_S + 5


def test_req2_selector_skips_earlier_cheaper_quote():
    quotes = (q(9, "0.10", "0.20"), q(10, "1.00", "1.10"))
    chosen, why = oes.select_quote(quotes, side="ask", arrival_t=10, window_end_t=70,
                                   min_displayed_contracts=1)
    assert why is None and chosen.t == 10 and chosen.ask == D("1.10")


def test_req2_quote_after_window_is_unavailable():
    out = oes.scenario_outcome(episode(entry=(q(61, "1.0", "1.1"),)), oes.BASELINE_SCENARIO)
    assert out["status"] == "unavailable"
    assert out["reason"] == "entry_no_eligible_quote_in_window"


# ---------------------------------------------------------------- req3
def test_req3_insufficient_size_is_unavailable_not_filled_later():
    entry = (q(0, "1.90", "2.00", asz=3), q(1, "1.90", "2.00", asz=50))
    out = oes.scenario_outcome(episode(entry=entry), oes.Scenario(0, 5, D("0.65"), D("0")))
    assert out["status"] == "unavailable"
    assert out["reason"] == "entry_insufficient_displayed_size"
    assert out["ruler"] is None and out["scenario_layer"] is None and out["gross"] is None


def test_req3_no_midpoint_or_neighbour_substitute_when_side_missing():
    entry = (q(0, "1.0", "0", asz=0), q(1, "2.0", "1.9"), q(2, "1.0", "1.1", ask_condition=2),
             q(3, "1.0", "1.1", ask_exchange=76), q(4, "1.0", "1.1", in_session=False))
    out = oes.scenario_outcome(episode(entry=entry), oes.BASELINE_SCENARIO)
    assert out["status"] == "unavailable"
    assert out["reason"] == "entry_no_eligible_quote_in_window"
    assert out["actual_fill"]["status"] == "unavailable"


def test_req3_session_close_rules_mirror_oa3_at_latency_zero():
    out = oes.scenario_outcome(episode(session_close_t=3000), oes.BASELINE_SCENARIO)
    assert (out["status"], out["reason"]) == ("excluded", "horizon_crosses_session_close")
    out = oes.scenario_outcome(episode(session_close_t=60), oes.Scenario(0, 5, D("1.30"), D("0.05")))
    assert (out["status"], out["reason"]) == ("excluded", "horizon_crosses_session_close")
    out = oes.scenario_outcome(episode(session_open_t=10), oes.BASELINE_SCENARIO)
    assert (out["status"], out["reason"]) == ("excluded", "entry_boundary_outside_rth")


def test_req3_delayed_window_reaching_close_is_population_loss():
    ep = episode(entry=(q(0, "1.9", "2.0"), q(30, "1.9", "2.0")), session_close_t=3700)
    assert oes.scenario_outcome(ep, oes.BASELINE_SCENARIO)["status"] == "complete"
    out = oes.scenario_outcome(ep, oes.Scenario(30, 1, D("0.65"), D("0")))
    assert (out["status"], out["reason"]) == ("unavailable", "exit_outside_session")
    ep2 = episode(session_close_t=100)
    out = oes.scenario_outcome(ep2, oes.Scenario(40, 1, D("0.65"), D("0")))
    assert (out["status"], out["reason"]) == ("unavailable", "entry_outside_session")
    base = [oes.scenario_outcome(ep, oes.BASELINE_SCENARIO)]
    sc = [oes.scenario_outcome(ep, oes.Scenario(30, 1, D("0.65"), D("0")))]
    assert oes.population_loss(base, sc)["reasons"] == {"exit_outside_session": 1}


def test_req3_exclusions_packages_zero_dte_short():
    for flag, reason in (("is_package", "package_excluded"),
                         ("is_zero_dte", "zero_dte_excluded"),
                         ("is_short", "short_option_excluded")):
        out = oes.scenario_outcome(episode(**{flag: True}), oes.BASELINE_SCENARIO)
        assert out["status"] == "excluded" and out["reason"] == reason


def test_req3_retrieval_and_acquisition_clocks():
    out = oes.scenario_outcome(episode(entry_retrieved_t=59), oes.BASELINE_SCENARIO)
    assert (out["status"], out["reason"]) == ("pending", "entry_window_not_matured_at_retrieval")
    assert oes.scenario_outcome(episode(entry_retrieved_t=60), oes.BASELINE_SCENARIO)["status"] == "complete"
    out = oes.scenario_outcome(episode(exit_retrieved_t=3659), oes.BASELINE_SCENARIO)
    assert (out["status"], out["reason"]) == ("pending", "exit_window_not_matured_at_retrieval")
    out = oes.scenario_outcome(episode(entry=(q(0, "1.9", "2.0", acquired_t=-1),)), oes.BASELINE_SCENARIO)
    assert out["reason"] == "entry_quote_response_invalid"
    out = oes.scenario_outcome(episode(entry=(q(0, "1.9", "2.0", acquired_t=70),), entry_retrieved_t=65),
                               oes.BASELINE_SCENARIO)
    assert out["reason"] == "entry_quote_response_invalid"
    ok = episode(entry=(q(0, "1.9", "2.0", acquired_t=1),), entry_retrieved_t=65, vintage="v1")
    assert oes.scenario_outcome(ok, oes.BASELINE_SCENARIO)["status"] == "complete"
    base = [oes.scenario_outcome(episode(), oes.BASELINE_SCENARIO)]
    pend = [oes.scenario_outcome(episode(exit_retrieved_t=0 + 3600), oes.BASELINE_SCENARIO)]
    assert oes.population_loss(base, pend)["became_untradable"] == 1


def test_req3_bool_and_non_decimal_fields_are_malformed():
    out = oes.scenario_outcome(episode(entry=(q(0, "1.9", "2.0", asz=True),)), oes.BASELINE_SCENARIO)
    assert out["reason"] == "entry_quote_response_invalid"
    bad = oes.Quote(t=0, bid=1.9, ask=2.0, bid_size=10, ask_size=10)
    out = oes.scenario_outcome(episode(entry=(bad,)), oes.BASELINE_SCENARIO)
    assert out["reason"] == "entry_quote_response_invalid"
    # a malformed row before the arrival is never read
    early = q(-5, "1.9", "2.0", asz=-1)
    assert oes.scenario_outcome(episode(entry=(early, q(0, "1.9", "2.0"))),
                                oes.BASELINE_SCENARIO)["status"] == "complete"


# ---------------------------------------------------------------- req4
def test_req4_grid_is_frozen_and_shared():
    with pytest.raises(dataclasses.FrozenInstanceError):
        oes.FROZEN_GRID.latencies_s = (0,)
    with pytest.raises(dataclasses.FrozenInstanceError):
        oes.DECISION_SCENARIO.latency_s = 0
    assert isinstance(oes.FROZEN_GRID.latencies_s, tuple)
    params = inspect.signature(oes.evaluate_episodes).parameters
    assert list(params) == ["episodes", "grid"]
    with pytest.raises(TypeError):
        oes.evaluate_episodes([episode()], grid={"AAA": oes.FROZEN_GRID})


def test_req4_every_name_gets_identical_scenarios():
    res = oes.evaluate_episodes([episode("e1", "AAA"), episode("e2", "BBB")])
    assert len(res) == len(oes.FROZEN_GRID.scenarios()) == 90
    assert list(res)[0] == oes.BASELINE_SCENARIO.key()
    assert oes.DECISION_SCENARIO.key() in res
    for rows in res.values():
        assert [r["name"] for r in rows] == ["AAA", "BBB"]
        assert len({r["scenario"] for r in rows}) == 1


# ---------------------------------------------------------------- req5
def test_req5_layers_remain_separate():
    out = oes.scenario_outcome(episode(), oes.Scenario(0, 1, D("1.30"), D("0.01")))
    assert set(("gross", "ruler", "scenario_layer", "actual_fill")) <= set(out)
    assert out["gross"]["basis"] == "descriptive_mid_to_mid_not_a_fill"
    assert out["ruler"]["basis"] == oes.POLICY_ID
    assert out["actual_fill"] == {"status": "unavailable", "reason": "no_executable_fill_claim",
                                  "net_return_pct": None}
    g, r, s = (out["gross"]["return_pct"], out["ruler"]["net_return_pct"],
               out["scenario_layer"]["net_return_pct"])
    assert g > r > s
    assert s == oes.ruler_net_return_pct("2.00", "2.50", fee_per_side_usd="1.30",
                                         slippage_per_share_usd="0.01")
    out["actual_fill"]["status"] = "x"
    assert oes.ACTUAL_FILL_LAYER["status"] == "unavailable"
    delayed = oes.scenario_outcome(episode(entry=(q(1, "1.9", "2.0"),), exit_=(q(3602, "2.5", "2.6"),)),
                                   oes.Scenario(1, 1, D("0.65"), D("0")))
    assert delayed["ruler"]["basis"] == "oa3_cost_formula_on_delayed_scenario_quotes"


def test_req5_slippage_never_improves_a_fill():
    base = oes.ruler_net_return_pct("2.00", "2.50")
    for slip in ("0.01", "0.05", "3.00"):
        assert oes.ruler_net_return_pct("2.00", "2.50", slippage_per_share_usd=slip) < base
    with pytest.raises(oes.ExecutionSensitivityError):
        oes.ruler_net_return_pct("2.00", "2.50", slippage_per_share_usd="-0.01")


# ---------------------------------------------------------------- req6
def test_req6_population_loss_reports_untradable_contracts():
    eps = [episode("e1", entry=(q(0, "1.9", "2.0", asz=20),)),
           episode("e2", entry=(q(0, "1.9", "2.0", asz=2),)),
           episode("e3", entry=(q(70, "1.9", "2.0"),))]
    base = [oes.scenario_outcome(e, oes.BASELINE_SCENARIO) for e in eps]
    sc = [oes.scenario_outcome(e, oes.Scenario(0, 5, D("0.65"), D("0"))) for e in eps]
    loss = oes.population_loss(base, sc)
    assert loss["baseline_complete"] == 2
    assert loss["scenario_complete"] == 1
    assert loss["became_untradable"] == 1
    assert loss["untradable_episode_ids"] == ["e2"]
    assert loss["reasons"] == {"entry_insufficient_displayed_size": 1}
    assert loss["loss_fraction"] == 0.5


def test_req6_cluster_bootstrap_counts_blocks_not_rows():
    vals = [1.0, 1.2, 0.8, -0.5, -0.4, 2.0, 2.1, 1.9, 0.3]
    blocks = ["a", "a", "a", "b", "b", "c", "c", "c", "d"]
    ci = oes.cluster_bootstrap_mean(vals, blocks, n_boot=500, seed=7)
    assert ci["n_blocks"] == 4 and ci["n_rows"] == 9
    assert ci["lo"] <= ci["mean"] <= ci["hi"]
    assert oes.cluster_bootstrap_mean(vals, blocks, n_boot=500, seed=7) == ci
    empty = oes.cluster_bootstrap_mean([], [], n_boot=10)
    assert empty["n_blocks"] == 0 and empty["mean"] is None


BIG = {"n_blocks": 25, "n_rows": 100, "lo": 0.5, "mean": 1.0}
SMALL_DELTA = {"mean": -0.2, "lo": -0.4, "hi": 0.0}
LOW_LOSS = {"loss_fraction": 0.02}


def _cls(base=BIG, dec=BIG, n=100, delta=SMALL_DELTA, loss=LOW_LOSS):
    return oes.classify(base, dec, n_holdout_episodes=n, paired_delta_ci=delta, decision_loss=loss)


def test_req6_classify_stop_rule_and_fragility():
    assert _cls(base={"n_blocks": 3, "lo": 5.0}, n=500) == "insufficient_data"
    assert _cls(n=10) == "insufficient_data"
    assert _cls(base={"n_blocks": 25, "lo": -0.1}) == "no_benefit_under_ruler"
    assert _cls(base={"n_blocks": 25, "lo": None}) == "no_benefit_under_ruler"
    assert _cls(dec={**BIG, "lo": -0.2}) == "execution_fragile"
    assert _cls(dec={**BIG, "lo": None}) == "execution_fragile"
    assert _cls() == "execution_robust"


def test_req6_classify_applies_prereg_materiality_and_decision_floor():
    assert _cls(delta={"mean": -1.0}) == "execution_fragile"
    assert _cls(delta={"mean": -0.99}) == "execution_robust"
    assert _cls(loss={"loss_fraction": 0.10}) == "execution_fragile"
    assert _cls(loss={"loss_fraction": 0.099}) == "execution_robust"
    assert _cls(dec={**BIG, "n_blocks": 19}) == "execution_fragile"
    assert _cls(dec={**BIG, "n_rows": 59}) == "execution_fragile"
    m = oes.materiality({"mean": -1.5}, {"loss_fraction": 0.2})
    assert m["material"] is True
    assert m["reasons"] == ["paired_mean_drop_ge_1pp", "untradable_fraction_ge_10pct"]
    assert oes.materiality({"mean": None}, {"loss_fraction": None})["material"] is False


def test_req6_paired_delta_and_break_even_distribution():
    eps = [episode("e1", block="s1"), episode("e2", block="s2")]
    base = [oes.scenario_outcome(e, oes.BASELINE_SCENARIO) for e in eps]
    dec = [oes.scenario_outcome(e, oes.Scenario(0, 1, D("0.65"), D("0.01"))) for e in eps]
    deltas, blocks = oes.paired_scenario_delta(base, dec)
    assert blocks == ["s1", "s2"] and all(d < 0 for d in deltas)
    # baseline P&L = (250-0.65) - (200+0.65) = 48.70 -> break-even extra per side 24.35
    be = oes.break_even_extra_cost_usd(base, n_boot=200)
    assert be["mean"] == pytest.approx(24.35)
    assert [p["episode_id"] for p in be["per_episode"]] == ["e1", "e2"]
    assert all(p["usd"] == pytest.approx(24.35) for p in be["per_episode"])
    assert be["ci"]["n_blocks"] == 2
    empty = oes.break_even_extra_cost_usd([])
    assert empty["mean"] is None and empty["per_episode"] == [] and empty["ci"]["n_blocks"] == 0


def test_req6_chronological_whole_session_split():
    keys = [f"s{i:02d}" for i in range(10)]
    train, hold = oes.chronological_session_split(reversed(keys + keys[:3]))
    assert train == tuple(keys[:6]) and hold == tuple(keys[6:])
    assert not set(train) & set(hold)
    for n in range(1, 51):
        tr, ho = oes.chronological_session_split([f"k{i:03d}" for i in range(n)])
        assert len(tr) + len(ho) == n and len(ho) >= 0.4 * n
        assert not tr or max(tr) < min(ho)
    with pytest.raises(oes.ExecutionSensitivityError):
        oes.chronological_session_split(["a", 3])


# ------------------------------------------------- no silent activation
def test_no_silent_activation():
    assert oes.RESEARCH_ONLY is True
    assert oes.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "INSUFFICIENT_DATA" in oes.__doc__
    public = {n for n in dir(oes) if not n.startswith("_")}
    for forbidden in ("register", "REGISTRY", "schedule", "main", "run", "activate", "wire"):
        assert forbidden not in public
    src = inspect.getsource(oes)
    for token in ("open(", "requests", "urllib", "subprocess", "os.environ",
                  "datetime.now", "time.time", "date.today", "logging"):
        assert token not in src
    imported = {v.__name__.split(".")[0] for v in vars(oes).values() if inspect.ismodule(v)}
    assert imported <= {"numpy"}
    assert "engine.options_execution_sensitivity" in sys.modules
