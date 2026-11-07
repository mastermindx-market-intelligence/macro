"""Literal owner parity for captured Sector macro, heat and broad crowding context."""
from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest

from engine import conditions, crowding, sector_central as central, theme_scoring as theme, market_state
from lib import config, store
from tests.fixtures import base_theme_macro_context_68d836 as old_theme
from tests.fixtures import base_sector_conditions_68d836 as old_conditions
from tests.fixtures import base_sector_crowding_68d836 as old_crowding
from tests.fixtures import base_sector_regime_context_68d836 as old_central


def regime():
    return {"date": "2026-11-03", "quad": "Q1", "quad_name": "Goldilocks",
        "growth_score": 1.2, "inflation_score": -.4, "liquidity_overlay": "expanding",
        "transition_state": "STABLE", "cycle_tag": "mid",
        "fed_path": {"implied": {"now": 4.5, "m6": 4.0}},
        "sector_rs": [{"ticker": "XLK", "pctile_252d": 85}, {"ticker": "XLV", "pctile_252d": 20}],
        "conditions": {"financial_conditions": {"state": "loose", "trend": "loosening", "nfci": -.2, "nfci_pctile": .2},
            "risk_appetite": {"vrp_state": "normal"}, "recession": {"label": "low", "score": 0},
            "drawdown_risk": {"band": "low", "score": 0}, "complacency": {"caution": False}},
        "risk_state": {"label_en": "Read the tape", "label_zh": "观察市场", "score": 25, "state": "calm"},
        "macro_risk": {"score": .9, "label": "persisted"}}


def captured_config(overlay=None, table=None):
    return {"engine": {"macro_overlay": overlay or {},
                      "confluence": {"sector_macro_beta": table or {}}}}


def forbidden(*args, **kwargs):
    raise AssertionError("ambient acquisition reached")


@pytest.mark.parametrize("region", ["us", "cn", "hk", "ca"])
@pytest.mark.parametrize("variant", ["full", "empty", "risk_off", "neutral_rates"])
def test_theme_macro_literal_projection_and_legacy_read_order(region, variant, monkeypatch):
    reg = regime()
    if variant == "empty": reg = {}
    elif variant == "risk_off":
        reg.update(quad="Q4", quad_name="Deflation", growth_score=-2., inflation_score=-1.)
        reg["conditions"] = {"financial_conditions": {"state": "tight", "trend": "tightening"},
            "drawdown_risk": {"band": "high"}, "recession": {"label": "high"},
            "risk_appetite": {"vrp_state": "high"}}
    elif variant == "neutral_rates": reg["fed_path"]["implied"]["m6"] = 4.5
    bonds = {"cycle_phase": "Recovery"}
    forex = {"as_of": "2026-10-30", "regime": "bear", "stance": {"word_en": "Weak dollar", "word_zh": "美元偏弱"}}
    docs = {("regime" if region == "us" else region + "_regime", "latest.json"): reg,
            ("bonds", "latest.json"): bonds, ("forex", "latest.json"): forex}
    calls = []
    def read(*key):
        calls.append(key); return deepcopy(docs[key])
    monkeypatch.setattr(theme, "_read_json", read)
    monkeypatch.setattr(old_theme, "_read_json", read)
    expected = old_theme._macro_context(region); old_calls = list(calls); calls.clear()
    assert theme._macro_context(region) == expected
    assert calls == old_calls
    monkeypatch.setattr(theme, "_read_json", forbidden)
    actual = theme.macro_context_from_inputs(regime=reg, bonds=bonds, forex=forex, region=region)
    assert actual == expected
    assert actual["display"]["as_of"] == reg.get("date")
    if region != "us":
        changed = theme.macro_context_from_inputs(regime=reg, bonds={"cycle_phase": "different"},
            forex={"regime": "bull"}, region=region)
        assert changed["state"] == actual["state"]
        assert changed["display"]["dollar_regime"] != actual["display"]["dollar_regime"]


@pytest.mark.parametrize("transition", [None, "STABLE", "WEAKENING", "TRANSITIONING", "NEW_REGIME"])
@pytest.mark.parametrize("overlay", [{}, {"transition_high": .5},
    {"mrs_weights": {"recession": 0., "drawdown": 0., "nfci": 0., "liquidity": 0., "transition": 0.}},
    {"mrs_weights": {"recession": 2., "nfci": .1}, "transition_high": .25}])
def test_macro_risk_literal_math_and_single_captured_configuration(transition, overlay, monkeypatch):
    latest = regime(); latest["transition_state"] = transition
    cfg = captured_config(deepcopy(overlay))
    calls = []
    def load(): calls.append(1); return deepcopy(cfg)
    monkeypatch.setattr(config, "load", load)
    expected = old_conditions.macro_risk_score(latest); old_count = len(calls); calls.clear()
    assert conditions.macro_risk_score(latest) == expected
    assert len(calls) == old_count == (2 if transition in ("TRANSITIONING", "NEW_REGIME") else 1)
    monkeypatch.setattr(config, "load", forbidden)
    assert conditions.macro_risk_score_from_inputs(latest, macro_overlay=overlay) == expected
    assert conditions.mrs_weights_from_inputs(overlay) == {
        **{"recession": 1., "drawdown": 1., "nfci": .5, "liquidity": .5, "transition": .25},
        **overlay.get("mrs_weights", {})}


def test_transition_setting_is_not_eagerly_converted_and_zero_score_survives(monkeypatch):
    latest = regime()
    monkeypatch.setattr(config, "load", forbidden)
    assert conditions.macro_risk_score_from_inputs(latest, macro_overlay={"transition_high": "unreadable"})["score"] == 0.
    latest["transition_state"] = "NEW_REGIME"
    with pytest.raises(ValueError):
        conditions.macro_risk_score_from_inputs(latest, macro_overlay={"transition_high": "unreadable"})


@pytest.mark.parametrize("key", [None, "", 0, "XLK", " xlk ", "tech", " TECH ", "missing"])
def test_sector_beta_literal_lookup(key, monkeypatch):
    table = {"XLK": .8, " Tech ": -.5}
    calls = []
    def load(): calls.append(1); return captured_config(table=table)
    monkeypatch.setattr(config, "load", load)
    expected = old_conditions.sector_macro_beta(key); count = len(calls); calls.clear()
    assert conditions.sector_macro_beta(key) == expected
    assert len(calls) == count == int(bool(key))
    monkeypatch.setattr(config, "load", forbidden)
    assert conditions.sector_macro_beta_from_inputs(key, table=table) == expected


def crowd_inputs():
    idx = pd.bdate_range(end="2026-11-03", periods=300)
    closes = pd.DataFrame(100 * np.exp(np.outer(np.arange(300), np.linspace(.001, .025, 10))),
                          index=idx, columns=[f"T{i}" for i in range(10)])
    bench = pd.Series(100 + np.arange(300) * .01, index=idx)
    si = pd.DataFrame({"days_to_cover": np.arange(1., 11.)}, index=closes.columns)
    return closes, si, bench


@pytest.mark.parametrize("variant", ["full", "missing_closes", "missing_si", "missing_bench", "bad_si", "outside_si", "subset"])
def test_fragility_literal_math_and_explicit_absence(variant, monkeypatch):
    closes, si, bench = crowd_inputs()
    if variant == "missing_closes": closes = None
    elif variant == "missing_si": si = None
    elif variant == "missing_bench": bench = None
    elif variant == "bad_si": si = pd.DataFrame({"other": [1.]})
    elif variant == "outside_si":
        si = pd.concat([si, pd.DataFrame({"days_to_cover": np.arange(20., 70.)}, index=[f"OTHER{i}" for i in range(50)])])
    elif variant == "subset": closes = closes[["T0"]]
    from engine import equity_factors
    monkeypatch.setattr(equity_factors, "_closes", lambda: closes)
    monkeypatch.setattr(old_crowding, "_short_interest", lambda: si)
    monkeypatch.setattr(old_crowding, "_bench_close", lambda: bench)
    expected = old_crowding.compute_fragility(closes=closes, si=si, bench=bench)
    monkeypatch.setattr(equity_factors, "_closes", forbidden)
    monkeypatch.setattr(crowding, "_short_interest", forbidden)
    monkeypatch.setattr(crowding, "_bench_close", forbidden)
    monkeypatch.setattr(config, "load", forbidden)
    monkeypatch.setattr(store, "read", forbidden)
    before = closes.copy(deep=True) if closes is not None else None
    assert crowding.compute_fragility_from_inputs(closes=closes, si=si, bench=bench) == expected
    if before is not None: pd.testing.assert_frame_equal(before, closes)


@pytest.mark.parametrize("risk", [None, {}, {"score": None, "components": {}}, {"score": 0., "components": {"x": 0.}}, {"score": 1.}])
@pytest.mark.parametrize("snapshot", [None, {"label_en": "Risk-off", "label_zh": "避险", "verdict": "RISK_OFF",
                                          "score": 25, "color": "red", "radar": {"state": "elevated"}}])
def test_central_anchor_literal_projection_and_resolved_market_state(risk, snapshot, monkeypatch):
    latest = regime()
    monkeypatch.setattr(conditions, "macro_risk_score", lambda value: deepcopy(risk))
    monkeypatch.setattr(market_state, "load_persisted", lambda: deepcopy(snapshot))
    monkeypatch.setattr(market_state, "market_state_snapshot", lambda value: None)
    expected = old_central._regime_anchor(latest)
    assert central._regime_anchor(latest) == expected
    monkeypatch.setattr(conditions, "macro_risk_score", forbidden)
    monkeypatch.setattr(market_state, "load_persisted", forbidden)
    monkeypatch.setattr(market_state, "market_state_snapshot", forbidden)
    actual = central.regime_anchor_from_inputs(latest, macro_risk=risk, market_state=snapshot)
    assert actual == expected
    if risk and risk.get("score") == 0. and snapshot:
        assert actual["gate_state_en"] == "Risk-on" and actual["state_en"] == "Risk-off"
    if risk and risk.get("score") is None:
        assert actual["risk_on"] is None  # truthy no-score result does not use persisted .9
    if actual.get("mrs_components") is not None:
        actual["mrs_components"]["changed"] = True
        assert "changed" not in (risk or {}).get("components", {})


def test_invalid_risk_preserves_legacy_order_before_market_state_acquisition(monkeypatch):
    reads = []
    monkeypatch.setattr(conditions, "macro_risk_score", lambda value: {"score": "bad"})
    monkeypatch.setattr(market_state, "load_persisted", lambda: reads.append("market_state"))
    for owner in (old_central, central):
        with pytest.raises(ValueError): owner._regime_anchor(regime())
    assert reads == []


@pytest.mark.parametrize("basis", ["marketcap", "weight_proxy"])
def test_complete_market_context_uses_original_owners_and_source_dates(basis, monkeypatch):
    latest = regime(); closes, si, bench = crowd_inputs()
    overlay = {"transition_high": .5}
    state = {"label_en": "Risk-off", "label_zh": "避险", "verdict": "RISK_OFF", "asof": "2026-10-30"}
    heat = {"size_basis": basis, "tiles": [
        {"sector": "Technology", "size": 10, "perf": {"1M": 0., "1D": 1.}},
        {"sector": "Technology", "size": 30, "perf": {"1M": None, "1D": -1.}}]}
    monkeypatch.setattr(config, "load", lambda: captured_config(overlay))
    monkeypatch.setattr(market_state, "load_persisted", lambda: deepcopy(state))
    monkeypatch.setattr(market_state, "market_state_snapshot", forbidden)
    risk = old_conditions.macro_risk_score(latest)
    expected = old_central._regime_anchor(latest)
    expected["heat"] = central._aggregate_heat(heat)
    expected["_crowd_by_ticker"] = old_crowding.compute_fragility(closes=closes, si=si, bench=bench)
    monkeypatch.setattr(config, "load", forbidden)
    monkeypatch.setattr(config, "data_dir", forbidden)
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(theme, "_read_json", forbidden)
    monkeypatch.setattr(market_state, "load_persisted", forbidden)
    from tests.test_theme_allocation_explicit_inputs import _Trap
    with _Trap() as trap:
        actual = central.market_context_from_inputs(latest=latest, macro_overlay=overlay,
            market_state=state, heatmap=heat, closes=closes, short_interest=si, benchmark=bench)
    assert trap.reads == trap.writes == trap.clocks == trap.providers == []
    assert actual == expected and risk["score"] == 0.
    assert actual["heat"]["Technology"]["breadth_pct"] is None
    assert state["asof"] == "2026-10-30" and latest["date"] == "2026-11-03"


def test_empty_captured_context_never_reads_ambient_defaults(monkeypatch):
    for owner, name in ((config, "load"), (config, "data_dir"), (store, "read"),
        (market_state, "load_persisted"), (market_state, "market_state_snapshot")):
        monkeypatch.setattr(owner, name, forbidden)
    context = central.market_context_from_inputs(latest={}, macro_overlay={}, market_state=None,
        heatmap=None, closes=None, short_interest=None, benchmark=None)
    assert context["risk_on"] is None
    assert context["heat"] == context["_crowd_by_ticker"] == {}


def test_captured_contexts_feed_the_real_five_document_composition():
    from tests.test_sector_document_composition import captured
    from engine.sector_basket_documents import compose_sector_documents
    args = captured(); latest = regime(); state = {"label_en": "Risk-off", "label_zh": "避险", "asof": "2026-10-30"}
    macro = theme.macro_context_from_inputs(regime=latest, bonds={"cycle_phase": "Recovery"},
                                          forex={"regime": "bear"})
    market = central.market_context_from_inputs(latest=latest, macro_overlay={}, market_state=state,
        heatmap=None, closes=args["basket_inputs"].closes, short_interest=None,
        benchmark=args["basket_inputs"].spy["close"])
    args["theme_inputs"] = replace(args["theme_inputs"], macro_context=macro)
    args["context"] = replace(args["context"], market_context=market)
    result = compose_sector_documents(**args)
    assert len(result.member_bytes) == 5
    assert result.evidence["core_source_session"] == "2026-11-05"
    assert macro["display"]["as_of"] == "2026-11-03"
    assert market["state_en"] == "Risk-off" and market["gate_state_en"] == "Risk-on"
    assert all(isinstance(json.loads(raw), dict) for raw in result.member_bytes.values())
