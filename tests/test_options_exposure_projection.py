"""Qualification failures stay in the denominator; joint cells stay joint."""
from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from engine.options_exposure_projection import build_exposure_projection, exposure_input_digest, expand_projection_cells, RAW_UNITS

ASOF = "2026-10-15"
EXP = "2026-10-23"


def book():
    g = pd.DataFrame([dict(root="SPY", date=ASOF, expiration=EXP, strike=100,
        right=side, underlying_price=100, implied_vol=.20, gamma=.01,
        vanna=-.2, charm=.365) for side in ("C", "P")])
    oi = g[["root", "expiration", "strike", "right"]].copy()
    oi["open_interest"] = [100, 100]
    ctx = dict(source_snapshot_ref="owner:immutable-snapshot-1", security_id="SEC:SPY",
        clocks=dict(source_session=ASOF, oi_report_date=ASOF,
            oi_position_session=None, option_observed_at=ASOF+"T19:00:00Z",
            underlying_observed_at=ASOF+"T19:00:00Z", greeks_available_at=ASOF+"T19:01:00Z",
            oi_available_at=ASOF+"T12:00:00Z", available_at=ASOF+"T20:00:00Z"),
        contract_terms=[dict(root="SPY", expiration=EXP, strike=100, right=side,
            series_id="owner:SPY-100-"+side, security_id="SEC:SPY", terms_ref="owner:terms-"+side,
            deliverable_ref="owner:deliverable-"+side, currency="USD", multiplier=100,
            deliverable="100_underlying_shares", economic_expiry_at=EXP+"T20:00:00Z",
            exercise_style="american", available_at=ASOF+"T12:00:00Z") for side in ("C", "P")],
        greek_provenance={m: dict(source_ref="owner:immutable-snapshot-1", model_ref="owner:provider-model-1",
            unit=RAW_UNITS[m], method="provider_observed", tenor_policy="economic_expiry_no_floor")
            for m in RAW_UNITS})
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    return g, oi, ctx


def project(g=None, oi=None, ctx=None):
    if g is None:
        g, oi, ctx = book()
    if ctx:
        # Synthetic test owner admits each deliberately mutated test book.
        ctx = {**ctx, "input_sha256": exposure_input_digest(g, oi, ASOF, "SPY")}
    p = build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)
    return {**p, "cells": expand_projection_cells(p)}


def test_cancellation_preserves_gross_and_one_time_signed_units():
    p = project()
    cell = p["cells"][0]
    assert cell["gamma"]["net"] == 0
    assert cell["gamma"]["gross"] == 20000
    assert cell["gamma"]["call"] == 10000
    assert cell["gamma"]["put"] == -10000
    assert cell["vanna"]["call"] == pytest.approx(-2000)
    assert cell["vanna"]["put"] == pytest.approx(2000)
    assert cell["charm"]["call"] == pytest.approx(1000)
    assert cell["charm"]["put"] == pytest.approx(-1000)
    assert cell["joint"]["complete"]
    assert p["population"]["expected_contracts"] is None
    assert p["population"]["full_universe_expected"] is None
    assert not p["population"]["full_universe_complete"]
    assert cell["gamma"]["status"] == "complete_observed"
    json.dumps(p, allow_nan=False)


def test_missing_oi_is_not_zero_and_stays_before_exclusions():
    g, oi, ctx = book()
    p = project(g, oi.iloc[:1], ctx)
    gamma = p["cells"][0]["gamma"]
    assert p["population"]["received_contracts"] == 2
    assert gamma["received"] == 2
    assert gamma["qualified"] == 1 and gamma["missing"] == 1
    assert gamma["net"] is None and gamma["gross"] is None and gamma["put"] is None
    assert gamma["known_net"] == 10000
    assert gamma["exclusions"] == {"oi_unknown_or_invalid": 1}


def test_oi_only_contract_is_not_dropped_and_zero_oi_needs_no_greek():
    g, oi, ctx = book()
    oi.loc[1, "open_interest"] = 0
    p = project(g.iloc[:1], oi, ctx)
    gamma = p["cells"][0]["gamma"]
    assert gamma["received"] == 1 and gamma["qualified"] == 2
    assert gamma["put"] == 0 and gamma["gross"] == 10000
    assert p["cells"][0]["joint"]["complete"]
    oi.loc[1, "open_interest"] = 1
    gamma = project(g.iloc[:1], oi, ctx)["cells"][0]["gamma"]
    assert gamma["missing"] == 1 and gamma["net"] is None


def test_absent_side_unknown_unless_explicit_expected_population_proves_empty():
    g, oi, ctx = book()
    gamma = project(g.iloc[:1], oi.iloc[:1], ctx)["cells"][0]["gamma"]
    assert gamma["put"] is None and gamma["gross"] is None
    ctx["expected_contracts"] = g.iloc[:1].to_dict("records")
    gamma = project(g.iloc[:1], oi.iloc[:1], ctx)["cells"][0]["gamma"]
    assert gamma["expected"] == 1 and gamma["put"] == 0
    assert gamma["gross"] == 10000 and gamma["status"] == "complete_expected"


def test_expected_missing_contract_and_unexpected_contract_are_explicit():
    g, oi, ctx = book()
    ctx["expected_contracts"] = g.to_dict("records")
    p = project(g.iloc[:1], oi.iloc[:1], ctx)
    assert p["population"]["expected_contracts"] == 2
    assert p["cells"][0]["gamma"]["expected"] == 2
    assert p["cells"][0]["gamma"]["missing"] == 1
    ctx["expected_contracts"] = g.iloc[:1].to_dict("records")
    p = project(g, oi, ctx)
    assert p["population"]["unexpected_contracts"] == 1
    assert p["population"]["expected_contracts"] is None


def test_disjoint_greeks_cannot_create_joint_coverage_or_combined():
    g, oi, ctx = book()
    g.loc[0, "vanna"] = np.nan
    g.loc[1, "charm"] = np.nan
    cell = project(g, oi, ctx)["cells"][0]
    assert cell["gamma"]["qualified"] == 2
    assert cell["vanna"]["qualified"] == cell["charm"]["qualified"] == 1
    assert cell["vanna"]["qualified_population_id"] != cell["charm"]["qualified_population_id"]
    assert cell["vanna"]["net"] is None
    assert cell["joint"]["qualified"] == 0 and not cell["joint"]["complete"]


def test_mixed_model_cannot_qualify_joint_even_when_all_numbers_finite():
    g, oi, ctx = book()
    ctx["greek_provenance"]["charm"]["model_ref"] = "another-model"
    cell = project(g, oi, ctx)["cells"][0]
    assert cell["charm"]["qualified"] == 2
    assert cell["joint"]["model_ref"] is None and not cell["joint"]["complete"]


@pytest.mark.parametrize("mutation,reason", [
    (lambda g, o, c: c.pop("source_snapshot_ref"), "source_identity_unknown"),
    (lambda g, o, c: c["clocks"].update(source_session=ASOF+"T00:00:00Z"), "source_identity_unknown"),
    (lambda g, o, c: c["clocks"].pop("oi_available_at"), "source_availability_unknown"),
    (lambda g, o, c: c["clocks"].update(oi_available_at="2026-10-16T12:00:00Z"), "source_after_availability_cutoff"),
    (lambda g, o, c: c["clocks"].update(option_observed_at="2026-10-14T19:00:00Z"), "source_session_mismatch"),
    (lambda g, o, c: c["contract_terms"][0].update(multiplier=10), "exact_series_terms_unqualified"),
    (lambda g, o, c: c["contract_terms"][0].pop("deliverable_ref"), "exact_series_terms_unqualified"),
    (lambda g, o, c: c["contract_terms"][0].update(available_at="2026-10-16T12:00:00Z"), "series_terms_availability_unqualified"),
    (lambda g, o, c: c["greek_provenance"]["gamma"].update(tenor_policy="floor_.001_years"), "greek_provenance_unqualified"),
    (lambda g, o, c: c["greek_provenance"]["gamma"].update(unit="millions"), "greek_provenance_unqualified"),
    (lambda g, o, c: c["greek_provenance"]["gamma"].pop("model_ref"), "greek_provenance_unqualified"),
    (lambda g, o, c: g.__setitem__("implied_vol", .0001), "degenerate_iv"),
])
def test_refusals_stay_counted(mutation, reason):
    g, oi, ctx = book()
    mutation(g, oi, ctx)
    gamma = project(g, oi, ctx)["cells"][0]["gamma"]
    assert gamma["net"] is None and gamma["missing"] >= 1
    assert reason in gamma["exclusions"]


def test_duplicate_join_refused_and_foreign_or_malformed_identity_not_hidden():
    g, oi, ctx = book()
    gamma = project(g, pd.concat([oi, oi.iloc[:1]]), ctx)["cells"][0]["gamma"]
    assert gamma["exclusions"] == {"duplicate_contract_key": 1}
    g.loc[1, "root"] = "QQQ"
    p = project(g, oi, ctx)
    assert p["population"]["invalid_rows"]["greeks"] == 1
    assert p["metrics"]["gamma"]["net"] is None
    g.loc[1, "root"] = "SPY"
    g.loc[1, "right"] = "wrong"
    assert project(g, oi, ctx)["population"]["invalid_rows"]["greeks"] == 1


def test_bare_rows_do_not_invent_standard_terms_or_source_qualification():
    g, oi, _ = book()
    p = project(g, oi, None)
    assert p["population"]["received_contracts"] == 2
    assert p["metrics"]["gamma"]["qualified"] == 0
    assert p["metrics"]["gamma"]["known_net"] is None
    assert p["clocks"]["source_session"] is None
    assert p["clocks"]["oi_position_session"] is None


@pytest.mark.parametrize("style,right,dividend,seconds,reason", [
    ("american", "P", False, 3600, "american_put_early_exercise"),
    ("american", "C", None, 3600, "unknown_dividend_schedule"),
    ("american", "C", True, 3600, "american_call_dividend_before_expiry"),
    ("european", "C", False, 30, "inside_min_t_indeterminate"),
    ("european", "C", False, 0, "at_or_after_economic_expiry"),
])
def test_existing_kernel_refusals_are_preserved(style, right, dividend, seconds, reason):
    g, oi, ctx = book()
    expiry = pd.Timestamp(ASOF+"T19:00:00Z") + pd.Timedelta(seconds=seconds)
    for frame in (g, oi):
        frame["expiration"] = ASOF
    for t in ctx["contract_terms"]:
        t.update(expiration=ASOF, economic_expiry_at=expiry.isoformat(),
                 exercise_style=style, discrete_dividend_before_expiry=dividend)
    for p in ctx["greek_provenance"].values():
        p["method"] = "engine.intraday_greeks"
    idx = 0 if right == "C" else 1
    gamma = project(g.iloc[[idx]], oi.iloc[[idx]], ctx)["cells"][0]["gamma"]
    assert gamma["qualified"] == 0 and gamma["exclusions"] == {reason: 1}


def test_true_joint_cells_differ_with_equal_strike_and_expiry_marginals():
    def grid(diagonal):
        g, oi, ctx = book()
        frames, interests, terms = [], [], []
        for strike in (100, 110):
            for exp in (EXP, "2026-10-30"):
                gg, oo = g.copy(), oi.copy()
                gg["strike"] = oo["strike"] = strike
                gg["expiration"] = oo["expiration"] = exp
                oo["open_interest"] = [200 if ((strike == 100) == (exp == EXP)) == diagonal else 100, 0]
                frames.append(gg); interests.append(oo)
                for t in deepcopy(ctx["contract_terms"]):
                    t.update(strike=strike, expiration=exp, economic_expiry_at=exp+"T20:00:00Z",
                             series_id=t["series_id"]+str(strike)+exp)
                    terms.append(t)
        ctx["contract_terms"] = terms
        return project(pd.concat(frames), pd.concat(interests), ctx)
    a, b = grid(True), grid(False)
    assert a["metrics"]["gamma"]["net"] == b["metrics"]["gamma"]["net"]
    assert a["cells"][0]["gamma"]["net"] != b["cells"][0]["gamma"]["net"]


def test_hub_publishes_projection_even_when_legacy_drops_all_oi(monkeypatch):
    from engine import options_hub
    monkeypatch.setattr(options_hub, "_flip_and_profile", lambda *args: (None, None))
    g, oi, ctx = book()
    oi["open_interest"] = 0
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    p = options_hub.compute_gex(g, oi, ASOF, "SPY", exposure_context=ctx)
    assert p["by_strike"] == []
    assert expand_projection_cells(p["exposure_projection"])[0]["gamma"]["net"] == 0
    assert p["exposure_projection"]["population"]["received_contracts"] == 2


def test_membership_is_order_independent_and_correction_changes_identity():
    g, oi, ctx = book()
    a = project(g, oi, ctx)
    ctx["contract_terms"].reverse()
    b = project(g.iloc[::-1], oi.iloc[::-1], ctx)
    assert a == b
    ctx["clocks"]["correction_ref"] = "owner:correction-2"
    c = project(g, oi, ctx)
    assert c["population"]["id"] != a["population"]["id"]
    assert c["cells"][0]["gamma"]["qualified_population_id"] != a["cells"][0]["gamma"]["qualified_population_id"]


def test_elapsed_charm_sign_matches_existing_kernel_finite_difference():
    from engine.intraday_greeks import bs_greeks_vec
    g, oi, ctx = book()
    tau = (pd.Timestamp(EXP+"T20:00:00Z") - pd.Timestamp(ASOF+"T19:00:00Z")).total_seconds() / (365 * 86400)
    h = 1 / (365 * 86400)  # one elapsed second, no tenor floor
    delta, gamma, vanna, charm = bs_greeks_vec(100, [100, 100], [tau, tau], [.2, .2], [True, False])
    later = bs_greeks_vec(100, [100, 100], [tau-h, tau-h], [.2, .2], [True, False])[0]
    earlier = bs_greeks_vec(100, [100, 100], [tau+h, tau+h], [.2, .2], [True, False])[0]
    assert charm == pytest.approx((later-earlier)/(2*h), rel=1e-7)
    g["gamma"], g["vanna"], g["charm"] = gamma, vanna, charm
    p = project(g, oi, ctx)
    assert p["cells"][0]["charm"]["call"] == pytest.approx(charm[0] / 365 * 100 * 100 * 100)


def test_final_hour_uses_owner_feed_without_a_synthetic_t_floor():
    g, oi, ctx = book()
    g["expiration"] = oi["expiration"] = ASOF
    for term in ctx["contract_terms"]:
        term.update(expiration=ASOF, economic_expiry_at=ASOF+"T19:30:00Z")
    p = project(g, oi, ctx)
    assert p["cells"][0]["gamma"]["gross"] == 20000
    assert p["cells"][0]["joint"]["complete"]
    # Viewing this historical source later does not turn it into today's 0DTE.
    assert p["clocks"]["source_session"] == ASOF
    assert p["clocks"]["published_at"] is None


def test_builder_threads_owner_receipt_into_existing_payload(monkeypatch):
    from scripts import build_options_hub_nightly as builder
    g, oi, ctx = book()
    monkeypatch.setattr(builder, "_load_greeks", lambda *a: g)
    monkeypatch.setattr(builder, "_load_oi_for_date", lambda *a: oi)
    _, p, _ = builder.build_root("SPY", ASOF, None, exposure_context=ctx)
    assert p["exposure_projection"]["source_snapshot_ref"] == ctx["source_snapshot_ref"]
    assert expand_projection_cells(p["exposure_projection"])[0]["gamma"]["gross"] == 20000


def test_malformed_expiry_and_ambiguous_series_binding_cannot_qualify():
    g, oi, ctx = book()
    ctx["contract_terms"][1]["series_id"] = ctx["contract_terms"][0]["series_id"]
    gamma = project(g, oi, ctx)["cells"][0]["gamma"]
    assert gamma["qualified"] == 0
    assert gamma["exclusions"] == {"ambiguous_series_binding": 2}
    g.loc[1, "expiration"] = EXP + "garbage"
    assert project(g, oi, ctx)["population"]["invalid_rows"]["greeks"] == 1


def test_unqualified_default_is_compact_without_losing_population_or_reason():
    g, oi, _ = book()
    p = project(g, oi, {})
    assert p["cells"] == [] and p["cells_status"] == "source_unqualified"
    assert p["cell_count"] == 1 and p["population"]["observed_contracts"] == 2
    assert p["metrics"]["gamma"]["exclusions"] == {"source_identity_unknown": 2}
    assert len(json.dumps(p).encode()) < 5000


def test_oversized_grid_is_withheld_in_full_never_top_n(monkeypatch):
    from engine import options_exposure_projection as projection
    monkeypatch.setattr(projection, "MAX_CELL_BYTES", 1)
    p = project()
    assert p["cells"] == [] and p["cells_status"] == "payload_limit"
    assert p["cell_count"] == 1
    assert p["metrics"]["gamma"]["gross"] == 20000


def test_receipt_cannot_be_applied_to_changed_consumed_inputs():
    g, oi, ctx = book()
    assert exposure_input_digest(g.iloc[::-1], oi.iloc[::-1], ASOF, "SPY") == ctx["input_sha256"]
    oi.loc[0, "open_interest"] += 1
    p = build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)
    assert p["metrics"]["gamma"]["net"] is None
    assert p["metrics"]["gamma"]["exclusions"] == {"source_inputs_do_not_match_receipt": 2}


def test_explicit_builder_receipt_input_never_discovers_or_rebinds(tmp_path):
    from scripts.build_options_hub_nightly import load_exposure_contexts
    _, _, ctx = book()
    ctx["root"] = "SPY"
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps({"schema": "options_hub.exposure_contexts/v1", "roots": {"SPY": ctx}}))
    assert load_exposure_contexts(None) == {}
    assert load_exposure_contexts(str(path)) == {"SPY": ctx}
    ctx["root"] = "QQQ"
    path.write_text(json.dumps({"schema": "options_hub.exposure_contexts/v1", "roots": {"SPY": ctx}}))
    with pytest.raises(ValueError, match="root mismatch"):
        load_exposure_contexts(str(path))
    with pytest.raises(FileNotFoundError):
        load_exposure_contexts(str(tmp_path / "absent.json"))


def dense_book(cell_count):
    """Production-sized synthetic grid, varied values and exact per-series terms."""
    g, oi, ctx = book()
    greeks, interests, terms = [], [], []
    dates = pd.bdate_range(EXP, periods=40).date.astype(str).tolist()
    base_g, base_o = g.to_dict("records"), oi.to_dict("records")
    for index in range(cell_count):
        expiry = dates[index % 40]
        strike = 75 + (index // 40) * .1
        economic = pd.Timestamp(expiry + "T16:00:00", tz="America/New_York").tz_convert("UTC").isoformat()
        for side in range(2):
            key = {"expiration": expiry, "strike": strike}
            greeks.append({**base_g[side], **key, "gamma": .002 + index * 1e-7,
                "vanna": -.2 + index * 1e-6, "charm": .365 + index * 1e-5})
            interests.append({**base_o[side], **key, "open_interest": 100 + index + side})
            original = ctx["contract_terms"][side]
            terms.append({**original, **key, "economic_expiry_at": economic,
                "series_id": original["series_id"] + str(index),
                "terms_ref": original["terms_ref"] + str(index)})
    ctx["contract_terms"] = terms
    ctx["expected_contracts"] = [{k: r[k] for k in ("root", "expiration", "strike", "right")} for r in interests]
    g, oi = pd.DataFrame(greeks), pd.DataFrame(interests)
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    return g, oi, ctx


@pytest.mark.parametrize("cell_count", [2795, 10_000, 12_000])
def test_realistic_books_fit_lossless_v2_and_whole_incumbent_envelope(cell_count, monkeypatch):
    from engine import options_hub
    from engine.options_exposure_projection import gex_sse_bytes, MAX_GEX_SSE_BYTES
    from scripts.build_options_hub_nightly import _gex_publish_decision
    g, oi, ctx = dense_book(cell_count)
    monkeypatch.setattr(options_hub, "_flip_and_profile", lambda *args: (None, None))
    payload = options_hub.compute_gex(g, oi, ASOF, "SPY", exposure_context=ctx)
    # Include the existing downstream history attachment before publisher admission.
    payload["history"] = [{"date": ASOF, "net_gex_bn": 1.2, "gamma_flip": 100,
                           "call_wall": 105, "put_wall": 95, "regime": "long"}] * 30
    publish, payload, guarded = _gex_publish_decision(payload, "SPY", ASOF, None)
    p = payload["exposure_projection"]
    assert publish and not guarded
    assert p["schema"] == "options_hub.exposure_projection/v2"
    assert p["cells_status"] == "complete" and len(p["cells"]) == p["cell_count"] == cell_count
    assert p["population"]["expected_contracts"] == 2 * cell_count
    assert p["metrics"]["gamma"]["qualified"] == 2 * cell_count
    decoded = expand_projection_cells(p)
    assert len({(c["expiry"], c["strike"]) for c in decoded}) == cell_count
    assert sum(c["gamma"]["expected"] for c in decoded) == 2 * cell_count
    assert sum(c["gamma"]["qualified"] for c in decoded) == 2 * cell_count
    assert sum(c["gamma"]["gross"] for c in decoded) == pytest.approx(p["metrics"]["gamma"]["gross"])
    assert gex_sse_bytes(payload) < MAX_GEX_SSE_BYTES - 1024


def test_v2_roundtrip_preserves_partial_zero_and_all_source_digests():
    from engine.options_exposure_projection import encode_projection_cells
    g, oi, ctx = book()
    g.loc[0, "vanna"] = np.nan
    oi.loc[1, "open_interest"] = 0
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    p = build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)
    expanded = expand_projection_cells(p)
    assert encode_projection_cells(expanded) == {k: p[k] for k in encode_projection_cells(expanded)}
    c = expanded[0]
    assert c["gamma"]["put"] == 0
    assert c["vanna"]["net"] is None and c["vanna"]["known_net"] == 0
    assert c["vanna"]["qualified"] == 1 and c["vanna"]["missing"] == 1
    assert c["vanna"]["exclusions"] == {"greek_missing": 1}
    assert c["gamma"]["qualified_population_id"] != c["vanna"]["qualified_population_id"]
    # Complete-case repeated qualified populations share one table entry, preserving
    # the original digest rather than replacing it with a lossy short hash.
    assert len(p["population_ids"]) < 5
    assert all(len(d) == 64 for d in p["population_ids"])


def test_publisher_budgets_entire_legacy_envelope_before_publication():
    from engine.options_exposure_projection import gex_sse_bytes, MAX_GEX_SSE_BYTES
    from scripts.build_options_hub_nightly import _gex_publish_decision
    g, oi, ctx = book()
    p = build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)
    payload = {"root": "SPY", "asof": ASOF, "by_strike": [{"strike": 100}],
               "exposure_projection": p}
    # Projection itself fits, but the full legacy/history object consumes the budget.
    payload["large_legacy"] = "x" * (MAX_GEX_SSE_BYTES - 1024 - gex_sse_bytes(payload) + 16)
    publish, bounded, guarded = _gex_publish_decision(payload, "SPY", ASOF, None)
    assert publish and not guarded
    assert bounded["exposure_projection"]["cells_status"] == "payload_limit"
    assert bounded["exposure_projection"]["cell_count"] == 1
    assert bounded["exposure_projection"]["cells"] == []
    assert bounded["exposure_projection"]["population"] == p["population"]
    assert bounded["large_legacy"] == payload["large_legacy"]
    assert gex_sse_bytes(bounded) <= MAX_GEX_SSE_BYTES - 1024
    bounded["large_legacy"] += "x" * MAX_GEX_SSE_BYTES
    publish, _, guarded = _gex_publish_decision(bounded, "SPY", ASOF, None)
    assert not publish and guarded


def test_raw_observation_clock_changes_invalidate_source_receipt():
    g, oi, ctx = book()
    g["timestamp"] = ASOF + "T15:00:00.000"
    g["underlying_timestamp"] = ASOF + "T14:59:59.999"
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    assert build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)["metrics"]["gamma"]["qualified"] == 2
    for field in ("timestamp", "underlying_timestamp"):
        changed = g.copy()
        changed.loc[0, field] = ASOF + "T15:00:00.001"
        p = build_exposure_projection(changed, oi, ASOF, "SPY", context=ctx)
        assert p["metrics"]["gamma"]["qualified"] == 0
        assert p["metrics"]["gamma"]["exclusions"] == {"source_inputs_do_not_match_receipt": 2}


def test_full_event_budget_accounts_for_javascript_decimal_expansion():
    from engine.options_exposure_projection import gex_sse_bytes
    # JSON.stringify uses 0.000001 and 100000000000000000000 for these doubles,
    # while Python's encoder chooses the much shorter scientific notation.
    payload = {"v": [1e-6, -1e-6, 1e20] * 1000}
    node_equivalent = '{"v":[' + ','.join(['0.000001', '-0.000001', '100000000000000000000'] * 1000) + ']}'
    assert gex_sse_bytes(payload) >= len(('data: ' + node_equivalent + '\n\n').encode())


@pytest.mark.parametrize("clock", ["timestamp", "underlying_timestamp"])
def test_raw_clocks_do_not_multiply_legacy_exposure_or_vol_rows(clock, monkeypatch):
    from engine import options_hub
    from engine.vex_engine import compute_vex
    g, oi, ctx = book()
    oi.loc[0, "open_interest"] = 200
    g["delta"] = [.5, -.5]
    g["vega"] = [.1, .1]
    g[clock] = ASOF + "T15:00:00.000"
    repeated = g.iloc[[0]].copy()
    repeated[clock] = ASOF + "T15:00:00.001"
    repeated = pd.concat([g, repeated], ignore_index=True)
    monkeypatch.setattr(options_hub, "_flip_and_profile", lambda *args: (None, None))
    normal = options_hub.compute_gex(g, oi, ASOF, "SPY")
    duplicate = options_hub.compute_gex(repeated, oi, ASOF, "SPY")
    assert normal["by_strike"][0]["gamma_net"] == .01
    # Every legacy field retains its pre-clock population, including coverage.
    assert {k: v for k, v in normal.items() if k != "exposure_projection"} == {
        k: v for k, v in duplicate.items() if k != "exposure_projection"}
    assert compute_vex(g, oi, ASOF, "SPY") == compute_vex(repeated, oi, ASOF, "SPY")
    closes = pd.Series(dtype=float)
    assert options_hub.compute_vol(g, closes, ASOF, "SPY") == options_hub.compute_vol(repeated, closes, ASOF, "SPY")
    # The source projection still sees and refuses ambiguity before legacy dedup.
    assert duplicate["exposure_projection"]["population"]["received_rows"] == 3
    assert duplicate["exposure_projection"]["metrics"]["gamma"]["exclusions"]["duplicate_contract_key"] == 1
    assert len(repeated) == 3 and clock in repeated.columns


def test_raw_oi_clock_binds_receipt_without_multiplying_legacy_exposure(monkeypatch):
    from engine import options_hub
    from engine.vex_engine import compute_vex
    g, oi, ctx = book()
    g["vega"] = [.1, .1]
    oi.loc[0, "open_interest"] = 200
    oi["timestamp"] = ASOF + "T06:30:00.100"
    ctx["input_sha256"] = exposure_input_digest(g, oi, ASOF, "SPY")
    assert build_exposure_projection(g, oi, ASOF, "SPY", context=ctx)["metrics"]["gamma"]["qualified"] == 2
    changed = oi.copy(); changed.loc[0, "timestamp"] = ASOF + "T06:30:00.101"
    rejected = build_exposure_projection(g, changed, ASOF, "SPY", context=ctx)
    assert rejected["metrics"]["gamma"]["exclusions"] == {"source_inputs_do_not_match_receipt": 2}
    repeated = pd.concat([oi, changed.iloc[[0]]], ignore_index=True)
    monkeypatch.setattr(options_hub, "_flip_and_profile", lambda *args: (None, None))
    baseline = options_hub.compute_gex(g, oi, ASOF, "SPY")
    duplicate = options_hub.compute_gex(g, repeated, ASOF, "SPY")
    assert {k: v for k, v in baseline.items() if k != "exposure_projection"} == {
        k: v for k, v in duplicate.items() if k != "exposure_projection"}
    assert compute_vex(g, oi, ASOF, "SPY") == compute_vex(g, repeated, ASOF, "SPY")
    assert duplicate["exposure_projection"]["metrics"]["gamma"]["exclusions"]["duplicate_contract_key"] == 1
    assert len(repeated) == 3 and "timestamp" in repeated.columns
