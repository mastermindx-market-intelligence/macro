"""Q01 — hermetic acceptance tests for engine/options_arbfree_surface.py.

Each test is named after the brief's acceptance requirement it proves (req1..req6).
Synthetic data only, integer clocks only; no network, no repo data, no file reads.
"""
from __future__ import annotations

import copy
import importlib
import json
import logging
import os
import random
import sys
import types
import warnings

import numpy as np

from engine import options_arbfree_surface as m

SESSION, OPEN, AS_OF = 1, 0, 390
BASE_SVI = (0.02, 0.1, -0.5, 0.0, 0.1)
TAUS = (0.1, 0.25, 0.5)
EXPIRIES = (1000, 2000, 3000)
STRIKES = tuple(float(s) for s in range(80, 121, 5))
VOGT = (-0.0410, 0.1331, 0.3586, 0.3060, 0.4153)


def _surface_params():
    return [(BASE_SVI[0] * t, BASE_SVI[1] * t, BASE_SVI[2], BASE_SVI[3], BASE_SVI[4]) for t in TAUS]


def _synthetic(**kw):
    return m.synthetic_svi_records(_surface_params(), EXPIRIES, STRIKES, **kw)


def _screen(records, forwards, as_of=AS_OF, roots=("SPX",)):
    return m.screen_quotes(records, session=SESSION, session_open=OPEN, as_of=as_of,
                           forwards=forwards, roots=roots)


def _call(strike, bid, ask, *, expiry=1000, quote_ts=389, **over):
    rec = {"product": "INDEX_OPTION", "root": "SPX", "style": "EUROPEAN", "right": "C",
           "strike": float(strike), "bid": bid, "ask": ask, "condition": "REGULAR",
           "session": SESSION, "quote_ts": quote_ts, "expiry_ts": expiry}
    rec.update(over)
    return rec


FWD1 = {1000: {"forward": 100.0, "discount": 1.0}}


def _dumps(obj):
    return json.dumps(obj, sort_keys=True, default=repr)


# ------------------------------------------------------------------------------ req1


def test_req1_wrong_product_inconsistent_clock_crossed_and_unknown_style_rejected_before_fitting():
    good = [_call(90, 14.0, 16.0), _call(100, 8.0, 9.0), _call(110, 2.0, 3.0)]
    bad = {
        "wrong_product": _call(95, 10.0, 11.0, product="EQUITY_OPTION"),
        "wrong_root": _call(95, 10.0, 11.0, root="SPY"),
        "american": _call(95, 10.0, 11.0, style="AMERICAN"),
        "unknown_style": _call(95, 10.0, 11.0, style="BERMUDAN"),
        "missing_style": {k: v for k, v in _call(95, 10.0, 11.0).items() if k != "style"},
        "session_mismatch": _call(95, 10.0, 11.0, session=2),
        "before_open": _call(95, 10.0, 11.0, quote_ts=-1),
        "float_clock": _call(95, 10.0, 11.0, quote_ts=389.0),
        "bool_clock": _call(95, 10.0, 11.0, session=True),
        "expired": _call(95, 10.0, 11.0, expiry=AS_OF),
        "crossed": _call(95, 11.5, 11.0),
        "negative_bid": _call(95, -0.1, 11.0),
        "zero_ask": _call(95, 0.0, 0.0),
        "nan_quote": _call(95, float("nan"), 11.0),
        "bad_condition": _call(95, 10.0, 11.0, condition="OPENING_ROTATION"),
        "no_forward": _call(95, 10.0, 11.0, expiry=5000),
        "forward_mismatch": _call(95, 10.0, 11.0, forward=101.0),
        "not_a_mapping": "SPX 95 C",
    }
    expected = {
        "wrong_product": m.WRONG_PRODUCT, "wrong_root": m.WRONG_PRODUCT,
        "american": m.AMERICAN_EXCLUDED, "unknown_style": m.UNKNOWN_STYLE,
        "missing_style": m.UNKNOWN_STYLE, "session_mismatch": m.INCONSISTENT_CLOCK,
        "before_open": m.INCONSISTENT_CLOCK, "float_clock": m.INCONSISTENT_CLOCK,
        "bool_clock": m.INCONSISTENT_CLOCK, "expired": m.INCONSISTENT_CLOCK,
        "crossed": m.CROSSED_QUOTE, "negative_bid": m.NEGATIVE_BID,
        "zero_ask": m.NONPOSITIVE_ASK, "nan_quote": m.NONFINITE_QUOTE,
        "bad_condition": m.BAD_CONDITION, "no_forward": m.MISSING_FORWARD,
        "forward_mismatch": m.FORWARD_MISMATCH, "not_a_mapping": m.MALFORMED,
    }
    for name, rec in bad.items():
        out = _screen([rec], FWD1)
        assert out["admitted"] == [], name
        assert [e["reason"] for e in out["excluded"]] == [expected[name]], name
    mixed = _screen(good + list(bad.values()), FWD1)
    clean = _screen(good, FWD1)
    assert len(mixed["admitted"]) == 3 and len(mixed["excluded"]) == len(bad)
    assert sorted({a["key"][2] for a in mixed["admitted"]}) == [90.0, 100.0, 110.0]
    slices_mixed, slices_clean = m.build_slices(mixed), m.build_slices(clean)
    assert slices_mixed == slices_clean and slices_mixed[0]["strike"] == [90.0, 100.0, 110.0]
    assert _dumps(m.fit_benchmark(slices_mixed)) == _dumps(m.fit_benchmark(slices_clean))


def test_req1_parity_conflict_between_legs_is_excluded_not_averaged():
    put_band_conflict = _call(100, 4.0, 4.5, right="P")  # parity call band [4.0, 4.5] vs [8, 9]
    out = m.build_slices(_screen([_call(90, 14.0, 16.0), _call(100, 8.0, 9.0),
                                  put_band_conflict, _call(110, 2.0, 3.0)], FWD1))
    assert out[0]["strike"] == [90.0, 110.0]
    assert [c["state"] for c in out[0]["parity_conflicts"]] == [m.PARITY_CONFLICT]


# ------------------------------------------------------------------------------ req2


def test_req2_synthetic_monotonicity_and_convexity_violations_detected():
    kappa = np.array([0.9, 1.0, 1.1])
    witness = m.static_violations(kappa, np.array([15.0, 9.0, 2.0]) / 100.0)
    assert witness["convexity"] == [1] and not witness["ok"]  # (15 - 18 + 2) / 10^2 < 0
    control = m.static_violations(kappa, np.array([15.0, 8.0, 2.0]) / 100.0)
    assert control["ok"]
    monotone = m.static_violations(kappa, np.array([10.0, 12.0, 5.0]) / 100.0)
    assert monotone["monotone"] == [1] and not monotone["ok"]
    bound = m.static_violations(kappa, np.array([0.05, 0.04, 0.01]))  # below (1 - 0.9)^+
    assert bound["bounds"] == [0] and not bound["ok"]


def test_req2_infeasible_bands_return_explicit_state_not_fabricated_repair():
    zero_width = [_call(90, 15.0, 15.0), _call(100, 9.0, 9.0), _call(110, 2.0, 2.0)]
    slices = m.build_slices(_screen(zero_width, FWD1))
    fit = m.fit_benchmark(slices)
    assert fit["state"] == m.BANDS_INFEASIBLE and fit["admissible"] is False
    assert fit["max_node_violation_spread_units"] > m.DEFAULT_VIOLATION_TOL
    ev = m.evaluate_at(fit, 0, [0.95, 1.0, 1.05])
    assert ev["value"] == [None, None, None] and set(ev["flag"]) == {m.NOT_ADMITTED}
    svi = m.fit_svi_surface(slices, seed=0, n_starts=3)
    entry = svi["slices"][0]
    assert not (entry["state"] == m.ADMITTED and entry["inside_bands"])
    assert svi["all_inside_bands"] is False

    control = m.fit_benchmark(m.build_slices(_screen(
        [_call(90, 15.0, 15.0), _call(100, 8.0, 8.0), _call(110, 2.0, 2.0)], FWD1)))
    assert control["state"] == m.ADMISSIBLE and control["admissible"] is True

    wide = m.build_slices(_screen([_call(90, 14.0, 16.0), _call(100, 8.5, 9.5),
                                   _call(110, 1.5, 2.5)], FWD1))
    assert not m.static_violations(wide[0]["kappa"], wide[0]["mid"])["ok"]
    repaired = m.fit_benchmark(wide)
    assert repaired["state"] == m.ADMISSIBLE
    vals = np.asarray(repaired["slices"][0]["value"])
    assert np.all(vals >= np.asarray(wide[0]["lo"]) - 1e-9)
    assert np.all(vals <= np.asarray(wide[0]["hi"]) + 1e-9)
    assert m.static_violations(wide[0]["kappa"], vals)["ok"]


def test_req2_empty_input_is_no_data_state():
    fit = m.fit_benchmark(m.build_slices(_screen([], FWD1)))
    assert fit["state"] == m.NO_DATA and fit["admissible"] is False


def test_req2_stage2_solver_failure_is_flagged_and_never_admitted(monkeypatch):
    wide = m.build_slices(_screen([_call(90, 14.0, 16.0), _call(100, 8.5, 9.5),
                                   _call(110, 1.5, 2.5)], FWD1))
    healthy = m.fit_benchmark(wide)
    assert healthy["state"] == m.ADMISSIBLE and healthy["stage2_fallback"] is False
    real = m.optimize.linprog
    calls = []

    def stage2_fails(*args, **kwargs):
        res = real(*args, **kwargs)
        calls.append(int(res.status))
        if len(calls) == 2:
            res.status = 4
            res.message = "forced stage-2 failure"
        return res

    monkeypatch.setattr(m, "optimize", types.SimpleNamespace(linprog=stage2_fails))
    fit = m.fit_benchmark(wide)
    assert len(calls) == 2
    assert fit["stage2_fallback"] is True and fit["stage2_status"] == 4
    assert fit["state"] == m.SOLVER_FAILED and fit["admissible"] is False
    assert fit["stage1_state"] == m.ADMISSIBLE and "forced" in fit["solver_message"]
    ev = m.evaluate_at(fit, 0, [0.95, 1.0, 1.05])
    assert ev["value"] == [None, None, None] and set(ev["flag"]) == {m.NOT_ADMITTED}


# ------------------------------------------------------------------------------ req3


def test_req3_admitted_benchmark_and_svi_pass_dense_strike_and_calendar_checks():
    records, fwds = _synthetic()
    slices = m.build_slices(_screen(records, fwds))
    bench = m.fit_benchmark(slices)
    assert bench["state"] == m.ADMISSIBLE
    finer = m.dense_check_benchmark(bench, n_grid=2001)
    assert finer["pass"] and len(finer["calendar"]) == 3
    assert all(c["pass"] for c in finer["calendar"])
    svi = m.fit_svi_surface(slices, seed=1, n_starts=4)
    assert svi["surface_admitted"]
    params = [s["params"] for s in svi["slices"]]
    supports = [s["support_k"] for s in svi["slices"]]
    check = m.check_svi_surface(params, supports, n_grid=2001)
    assert check["pass"] and len(check["calendar"]) == 3
    for s in check["slices"]:
        assert s["butterfly_ok"] and s["lee_ok"] and s["price_convex_ok"]
        assert s["min_g"] >= -m.DEFAULT_G_TOL


def test_req3_calendar_crossing_between_nodes_is_caught_by_dense_check_only():
    short = {"expiry_ts": 1000, "kappa": [0.9, 1.1], "value": [0.12, 0.02]}
    long = {"expiry_ts": 2000, "kappa": [0.9, 1.0, 1.1], "value": [0.125, 0.06, 0.025]}
    for s in (short, long):
        assert m.static_violations(s["kappa"], s["value"])["ok"]
    shared = [0.9, 1.1]
    assert all(np.interp(p, long["kappa"], long["value"]) >= np.interp(p, short["kappa"], short["value"])
               for p in shared)
    dense = m.dense_check_benchmark({"slices": [short, long]})
    assert dense["pass"] is False and dense["calendar"][0]["worst_gap"] < -0.009

    recs = [_call(90, 12.0, 12.0), _call(110, 2.0, 2.0),
            _call(90, 12.5, 12.5, expiry=2000), _call(100, 6.0, 6.0, expiry=2000),
            _call(110, 2.5, 2.5, expiry=2000)]
    fwds = {1000: {"forward": 100.0, "discount": 1.0}, 2000: {"forward": 100.0, "discount": 1.0}}
    slices = m.build_slices(_screen(recs, fwds))
    with_calendar = m.fit_benchmark(slices)
    assert with_calendar["state"] == m.BANDS_INFEASIBLE
    without_calendar = m.fit_benchmark(slices, calendar=False)
    assert without_calendar["state"] == m.FAILED_CHECK and without_calendar["admissible"] is False
    assert without_calendar["dense_check"]["calendar"][0]["pass"] is False


def test_req3_svi_butterfly_arbitrage_between_nodes_fails_dense_check():
    nodes = np.array([-0.5, 0.0, 0.3, 1.3])
    assert np.all(m.svi_g(VOGT, nodes) > 0)  # sparse node check would pass
    res = m.check_svi_slice(VOGT, [-0.5, 1.3])
    assert res["butterfly_ok"] is False and res["min_g"] < -0.02 and res["pass"] is False


def test_req3_svi_calendar_crossing_between_nodes_fails_dense_check():
    a = (0.04, 0.01, 0.0, 0.0, 0.1)
    b = (0.02, 0.2, 0.0, 0.0, 0.05)
    nodes = np.array([-0.2, 0.2])
    assert np.all(m.svi_total_variance(b, nodes) > m.svi_total_variance(a, nodes))
    res = m.check_svi_calendar(a, [-0.2, 0.2], b, [-0.2, 0.2])
    assert res["pass"] is False and res["worst_gap"] < -0.01


# ------------------------------------------------------------------------------ req4


def test_req4_future_quote_cannot_change_historical_eligibility():
    base = [_call(90, 14.0, 16.0), _call(100, 8.0, 9.0), _call(110, 2.0, 3.0)]
    future = _call(100, 7.0, 7.5, quote_ts=AS_OF + 5)
    plain, with_future = _screen(base, FWD1), _screen(base + [future], FWD1)
    assert plain["admitted"] == with_future["admitted"]
    assert [e["reason"] for e in with_future["excluded"]] == [m.FUTURE_QUOTE]
    assert m.build_slices(plain) == m.build_slices(with_future)
    earlier = _screen(base + [_call(100, 8.2, 8.8, quote_ts=380)], FWD1, as_of=385)
    assert [a["raw"]["bid"] for a in earlier["admitted"]] == [8.2]
    assert sorted(e["reason"] for e in earlier["excluded"]) == [m.FUTURE_QUOTE] * 3


def test_req4_reordered_inputs_give_identical_bytes():
    records, fwds = _synthetic(noise_seed=7)
    first = _screen(records, fwds)
    shuffled = list(records)
    random.Random(11).shuffle(shuffled)
    fwds_reordered = dict(reversed(list(fwds.items())))
    second = _screen(shuffled, fwds_reordered)
    assert _dumps(first) == _dumps(second)
    assert _dumps(m.fit_benchmark(m.build_slices(first))) == _dumps(m.fit_benchmark(m.build_slices(second)))


def test_req4_duplicate_coordinates_resolved_explicitly():
    base = [_call(90, 14.0, 16.0), _call(100, 8.0, 9.0), _call(110, 2.0, 3.0)]
    dup = _screen(base + [_call(100, 8.0, 9.0)], FWD1)
    assert len(dup["admitted"]) == 3 and dup["counts"].get(m.DUPLICATE_IDENTICAL) == 1
    conflict = _screen(base + [_call(100, 8.1, 9.0)], FWD1)
    assert [a["key"][2] for a in conflict["admitted"]] == [90.0, 110.0]
    assert conflict["counts"].get(m.DUPLICATE_CONFLICT) == 2
    superseded = _screen(base + [_call(100, 8.4, 8.6, quote_ts=300)], FWD1)
    assert [a["raw"]["bid"] for a in superseded["admitted"] if a["key"][2] == 100.0] == [8.0]
    assert superseded["counts"].get(m.SUPERSEDED) == 1
    later = _screen(base + [_call(100, 8.4, 8.6, quote_ts=AS_OF)], FWD1)
    assert [a["raw"]["bid"] for a in later["admitted"] if a["key"][2] == 100.0] == [8.4]


# ------------------------------------------------------------------------------ req5


def test_req5_perturbation_within_bid_ask_reports_sensitivity_and_tails_flagged():
    records, fwds = _synthetic()
    slices = m.build_slices(_screen(records, fwds))
    tails = (0.5, 1.0, 1.6)
    bench = m.perturbation_sensitivity(slices, method="benchmark", n_draws=5, seed=3,
                                       tail_kappa=tails)
    assert 0.0 <= bench["state_change_fraction"] <= 1.0
    for s in bench["slices"]:
        assert s["value_range_max"] > 0 and s["density_range_max"] > 0
        assert s["tail"] == [m.UNAVAILABLE, m.SUPPORTED, m.UNAVAILABLE]
    again = m.perturbation_sensitivity(slices, method="benchmark", n_draws=5, seed=3,
                                       tail_kappa=tails)
    assert _dumps(bench) == _dumps(again)
    svi = m.perturbation_sensitivity(slices[:1], method="svi", n_draws=3, seed=3, tail_kappa=tails,
                                     svi_options={"n_starts": 2, "seed": 1})
    assert 0.0 <= svi["state_change_fraction"] <= 1.0
    assert svi["slices"][0]["value_range_max"] > 0
    assert svi["slices"][0]["tail"] == [m.EXTRAPOLATED, m.SUPPORTED, m.EXTRAPOLATED]


def test_req5_unsupported_tails_never_reported_as_supported_values():
    records, fwds = _synthetic()
    slices = m.build_slices(_screen(records, fwds))
    bench = m.fit_benchmark(slices)
    ev = m.evaluate_at(bench, 0, [0.7, 0.8, 1.2, 1.3])
    assert ev["flag"] == [m.UNAVAILABLE, m.SUPPORTED, m.SUPPORTED, m.UNAVAILABLE]
    assert ev["value"][0] is None and ev["value"][3] is None
    svi = m.fit_svi_surface(slices[:1], seed=1, n_starts=3)
    ev2 = m.evaluate_at(svi, 0, [0.7, 1.0, 1.3])
    assert ev2["flag"] == [m.EXTRAPOLATED, m.SUPPORTED, m.EXTRAPOLATED]
    assert all(v is not None for v in ev2["value"])


# ------------------------------------------------------------------------------ req6


def test_req6_observed_exact_leg_outputs_byte_compatible_and_inputs_unmutated():
    records, fwds = _synthetic(include_puts=False, noise_seed=5, forward=100.0, discount=0.99)
    before = copy.deepcopy(records)
    before_fwds = copy.deepcopy(fwds)
    screen = _screen(records, fwds)
    assert records == before and fwds == before_fwds
    in_bytes = sorted(_dumps(r) for r in records)
    out_bytes = sorted(_dumps(a["raw"]) for a in screen["admitted"])
    assert in_bytes == out_bytes
    slices = m.build_slices(screen)
    by_key = {(a["key"][1], a["key"][2]): a["raw"] for a in screen["admitted"]}
    for s in slices:
        for strike, lo, hi in zip(s["strike"], s["lo"], s["hi"]):
            raw = by_key[(s["expiry_ts"], strike)]
            assert lo == raw["bid"] / (0.99 * 100.0) and hi == raw["ask"] / (0.99 * 100.0)
    m.fit_benchmark(slices)
    assert records == before


def test_req6_no_display_rank_alert_score_or_deploy_authority():
    records, fwds = _synthetic()
    screen = _screen(records, fwds)
    slices = m.build_slices(screen)
    outputs = [screen, m.fit_benchmark(slices), m.fit_svi_surface(slices[:1], seed=0, n_starts=2),
               m.perturbation_sensitivity(slices[:1], n_draws=2, seed=0)]
    for out in outputs:
        assert out["authority"] == {"may_display": False, "may_rank": False, "may_alert": False,
                                    "may_score": False, "may_deploy": False}
        assert out["research_only"] is True and out["schema"] == m.SCHEMA
    grant = m.authority()
    grant["may_rank"] = True
    assert m.authority()["may_rank"] is False


# ------------------------------------------------------------------- no silent activation


def test_no_silent_activation_research_only_contract():
    assert m.RESEARCH_ONLY is True
    assert m.VERDICT == "INSUFFICIENT_DATA"
    assert (m.__doc__ or "").startswith("RESEARCH REFERENCE — NOT WIRED")
    for name in ("register", "main", "REGISTRY", "run", "schedule", "wire", "promote"):
        assert not hasattr(m, name), name
    allowed_roots = {"copy", "json", "math", "numpy", "scipy"}
    for value in vars(m).values():
        if isinstance(value, types.ModuleType):
            assert value.__name__.split(".")[0] in allowed_roots, value.__name__
    env_before = dict(os.environ)
    path_before = list(sys.path)
    handlers_before = list(logging.getLogger().handlers)
    filters_before = list(warnings.filters)
    reloaded = importlib.reload(m)
    assert reloaded.RESEARCH_ONLY is True
    assert dict(os.environ) == env_before and list(sys.path) == path_before
    assert list(logging.getLogger().handlers) == handlers_before
    assert list(warnings.filters) == filters_before
