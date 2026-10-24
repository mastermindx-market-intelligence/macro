"""Falsifying controls for the R26 availability and condition contract.

Synthetic inputs only. Tests never fetch data, rebuild event ledgers, activate
watches, invoke the nightly pipeline or write production artifacts.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine import forex_signals as signals
from engine import forex_alerts as alerts
from engine import commodity_signals
from lib import config
from scripts import build_forex as builder
from scripts import build_macro_context as macro

NOW = "2026-10-16T16:05:00Z"


def frame(risk=np.nan, direction=0.1, regime=None):
    idx = pd.date_range("2026-06-01", periods=100, freq="B")
    return pd.DataFrame({"broad": 100.0, "dxy": 101.0, "broad_afe": 99.0,
                         "broad_eme": 102.0, "risk_off": risk, "dollar_roc": direction,
                         "smile_regime": regime, "dollar_day_z": 0.0}, index=idx)


def receipt(value=0.0, **changes):
    r = {"dependency_id": "price", "state": "fresh", "critical": True,
         "value_kind": "number", "value": value, "unit": "JPY per USD",
         "source_observed_at": "2026-10-16T16:00:00Z",
         "source_available_at": "2026-10-16T16:00:02Z",
         "expires_at": "2026-10-16T20:00:00Z"}
    return {**r, **changes}


def rule(**changes):
    r = {"condition_id": "usd-jpy-break", "revision": 1, "kind": "price_close",
         "pair": "USDJPY", "feed": "qualified-test-feed", "interval": "4H",
         "calendar": "fx-utc-4h/v1", "operator": "lt", "threshold": 145.60,
         "consecutive": 2, "expires_at": "2026-10-23T16:00:00Z"}
    return {**r, **changes}


def bars():
    return [{"observation_id": "bar-1", "revision": 1, "pair": "USDJPY",
             "feed": "qualified-test-feed", "interval": "4H", "calendar": "fx-utc-4h/v1",
             "quote_basis": "literal", "status": "final", "bar_sequence": 400,
             "bar_end": "2026-10-16T12:00:00Z", "available_at": "2026-10-16T12:00:02Z",
             "expires_at": "2026-10-16T16:00:00Z", "close": 145.56},
            {"observation_id": "bar-2", "revision": 1, "pair": "USDJPY",
             "feed": "qualified-test-feed", "interval": "4H", "calendar": "fx-utc-4h/v1",
             "quote_basis": "literal", "status": "final", "bar_sequence": 401,
             "bar_end": "2026-10-16T16:00:00Z", "available_at": "2026-10-16T16:00:02Z",
             "expires_at": "2026-10-16T20:00:00Z", "close": 145.52}]


@pytest.mark.parametrize("direction", [-0.1, 0.0, 0.1])
def test_missing_risk_not_reflation_or_growth(direction):
    vm = builder.dollar_vm(frame(direction=direction, regime="US growth premium"))
    assert vm["regime"] is None and vm["risk_word"] is None
    assert vm["favored"] == [] and vm["risk_off"] is None
    assert vm["broad"] == 100.0 and vm["dxy"] == 101.0
    assert vm["current_available"] is False


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf"), True, False, "0"])
def test_invalid_risk_is_not_a_numeric_observation(value):
    assert signals._finite_fx(value) is False
    assert builder._r4_number(value) is None


def test_zero_risk_and_direction_are_valid():
    assert signals._finite_fx(0)
    vm = builder.dollar_vm(frame(risk=0.0, direction=0.0, regime="Global reflation"))
    assert vm["risk_word"] == "risk-on" and vm["roc"] == 0
    assert vm["current_available"] is True


def test_actual_producer_masks_absent_risk(monkeypatch):
    idx = pd.date_range("2025-01-01", periods=400, freq="B")
    for slope in [-0.001, 0.001]:
        driver = pd.Series(np.exp(np.arange(400) * slope) * 100, index=idx)
        result = signals.dollar_master({"broad_dollar": driver}, config.load()["forex"])
        assert result["risk_off"].isna().all()
        assert result["smile_regime"].isna().all()
        assert result["broad"].notna().all()


def test_confirmation_gap_resets_candidate_without_erasing_history():
    state = pd.Series(["A"] + ["B"] * 4 + [None, "B"])
    out = signals._confirm_fx_regime(state)
    # Pandas string dtypes may represent the unavailable cell as NaN rather than
    # Python None. The contract is missingness, never a manufactured regime.
    assert pd.isna(out.iloc[-1]["smile_regime"])
    assert out.iloc[-1]["smile_last_confirmed"] == "A"
    assert out.iloc[-1]["smile_candidate"] == "B"
    assert out.iloc[-1]["smile_candidate_count"] == 1
    resumed = signals._confirm_fx_regime(pd.concat([state, pd.Series(["B"] * 4)], ignore_index=True))
    assert resumed.iloc[-1]["smile_regime"] == "B"


def test_populated_confirmation_control_matches_legacy():
    s = pd.Series(["A"] * 5 + ["B"] * 4 + ["A"] * 2 + ["B"] * 7 + ["A"] * 8)
    expected = commodity_signals._confirm(s, 5)
    actual = signals._confirm_fx_regime(s)["smile_regime"]
    assert actual.tolist() == expected.tolist()


def test_risk_factor_does_not_fill_missing_composite():
    s = pd.Series([0.8, np.nan, 0.6])
    out = signals.riskoff_factor(s, {"archetype": "haven-funder"}, s.index)
    assert out["riskoff"].iloc[0] > 0 and pd.isna(out["riskoff"].iloc[1])


def test_gap_recovery_is_not_an_economic_flip():
    d = frame().tail(4).copy()
    d["smile_regime"] = ["US growth premium", None, "Global reflation", "Global reflation"]
    assert alerts.dollar_events(d) == []
    assert alerts.desk_smile_regime_events(d) == []
    d.iloc[1, d.columns.get_loc("smile_regime")] = "US growth premium"
    one = alerts.dollar_events(d)
    assert len(one) == 1 and one[0]["id"] == alerts.dollar_events(d)[0]["id"]


def test_old_false_event_is_withheld_without_history_mutation():
    d = frame().tail(3).copy()
    d["smile_regime"] = ["US growth premium", "Global reflation", "Global reflation"]
    old = alerts.dollar_events(d)[0]
    independent = {"id": "price-event", "type": "momentum", "ts": old["ts"]}
    events = [old, independent]
    before = copy.deepcopy(events)
    d["smile_regime"] = None
    out = alerts.qualified_current_events(events, d)
    assert out["events"] == [independent]
    assert out["withheld"][0]["id"] == old["id"]
    assert out["history_modified"] is False and events == before


def test_empty_dependencies_and_empty_action_fail_closed():
    out = builder._r4_readiness({}, checked_at=NOW, action_requirements={"watch": []})
    assert out["verdict"] == "unavailable"
    assert out["actions"]["watch"]["allowed"] is False


@pytest.mark.parametrize("value", [True, False, np.nan, np.inf, "unknown", None])
def test_readiness_rejects_invalid_values(value):
    out = builder._r4_readiness({"price": receipt(value)}, checked_at=NOW, action_requirements={"watch": ["price"]})
    assert not out["actions"]["watch"]["allowed"]


@pytest.mark.parametrize("changes", [
    {"source_observed_at": None}, {"source_available_at": None}, {"expires_at": None},
    {"source_available_at": "2026-10-16T17:00:00Z"},
    {"expires_at": "2026-10-16T16:04:00Z"},
    {"source_observed_at": "2026-10-16T16:01:00Z"}, {"unit": None},
])
def test_clock_or_unit_gaps_cannot_be_replaced_by_build_time(changes):
    out = builder._r4_readiness({"price": receipt(**changes)}, checked_at=NOW, action_requirements={"watch": ["price"]})
    assert not out["actions"]["watch"]["allowed"]


def test_readiness_zero_and_dependency_isolation():
    out = builder._r4_readiness({"price": receipt(0), "positioning": receipt(None, dependency_id="positioning", critical=False, state="missing")},
        checked_at=NOW, action_requirements={"price_only": ["price"], "positioning": ["positioning"]})
    assert out["actions"]["price_only"]["allowed"]
    assert not out["actions"]["positioning"]["allowed"]
    duplicate = builder._r4_readiness({"one": receipt(), "two": receipt()}, checked_at=NOW, action_requirements={"watch": ["one"]})
    assert not duplicate["actions"]["watch"]["allowed"]


def test_exact_close_condition_and_determinism():
    a = alerts.evaluate_price_condition(rule(), bars(), now=NOW)
    b = alerts.evaluate_price_condition(rule(), bars(), now="2026-10-16T16:06:00Z")
    assert a["outcome"] == "met" and a["evaluation_id"] == b["evaluation_id"]
    assert a["forecast_probability"] is None and a["activation"] == "not_performed"
    assert len(a["observations"]) == 2


def test_strict_operator_is_distinct_from_inclusive():
    b = bars(); b[-1]["close"] = 145.60
    assert alerts.evaluate_price_condition(rule(), b, now=NOW)["outcome"] == "not_met"
    assert alerts.evaluate_price_condition(rule(operator="lte"), b, now=NOW)["outcome"] == "met"


@pytest.mark.parametrize("change", [
    {"status": "forming"}, {"status": "corrected"}, {"quote_basis": "synthesized_ohlc"},
    {"close": np.nan}, {"close": True}, {"feed": "another-feed"}, {"interval": "1D"},
    {"bar_sequence": 403}, {"available_at": None}, {"available_at": "2026-10-16T17:00:00Z"},
    {"expires_at": "2026-10-16T16:04:00Z"}, {"observation_id": "bar-1"}, {"revision": None},
])
def test_unqualified_bars_withhold_condition(change):
    b = bars();b[-1].update(change)
    out = alerts.evaluate_price_condition(rule(), b, now=NOW)
    assert out["outcome"] == "withheld" and out["withheld_reasons"]


def test_correction_changes_evaluation_without_emitting_event():
    original = alerts.evaluate_price_condition(rule(), bars(), now=NOW)
    b = bars(); b[-1].update(revision=2, close=145.65)
    corrected = alerts.evaluate_price_condition(rule(), b, now=NOW)
    assert corrected["outcome"] == "not_met"
    assert corrected["evaluation_id"] != original["evaluation_id"]
    assert "event_id" not in corrected and corrected["activation"] == "not_performed"


def test_unsupported_composite_and_expired_rules():
    assert alerts.evaluate_price_condition(rule(kind="event_reaction"), bars(), now=NOW)["outcome"] == "withheld"
    assert alerts.evaluate_price_condition(rule(expires_at=NOW), bars(), now=NOW)["outcome"] == "withheld"
    assert alerts.evaluate_price_condition(rule(), bars()[:1], now=NOW)["outcome"] == "withheld"


def project_sample():
    d = frame()
    pair = {"key": "USDJPY", "base": "JPY", "quote": 145.82, "ts_trend": "up", "structure_state": "constructive"}
    return builder._decision_context({"USDJPY": d}, [pair], builder.dollar_vm(d), {}, {},
        [{"id": "canonical-change-1", "ts": "2026-10-16T16:00:00Z", "type": "momentum", "context": {"from": "steady", "to": "accelerating"}}],
        checked_at=NOW)


def test_projection_preserves_orientation_identity_and_unknown_clocks():
    c = project_sample();p = c["pairs"][0]
    assert p["display_base"] == "USD" and p["display_quote"] == "JPY"
    assert p["assessed_currency"] == "JPY" and p["assessed_to_pair_direction"] == "opposite"
    assert p["literal_quote"] == 145.82
    assert c["changes"][0]["id"] == "canonical-change-1"
    assert c["dependencies"]["USDJPY:literal_quote"]["source_available_at"] is None
    assert not c["capabilities"]["USDJPY:price_close_4h"]["allowed"]
    assert c["probability_policy"] == "withheld"
    assert project_sample()["snapshot_id"] == c["snapshot_id"]


def test_full_template_and_json_preserve_same_decision_record():
    c = project_sample(); d = builder.dollar_vm(frame())
    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)
    env.globals.update(tr=lambda x:x, td=lambda x:x)
    rendered = env.get_template("forex.html.j2").render(C=builder.C, as_of="Oct 16, 2026", built=NOW,
        cal_span="synthetic", dollar=d, desk={}, transmission={}, strength={}, scorecards={},
        regime={}, kinematics={}, kinematics_view={}, decision_context=c, pairs=[], sections=[],
        carry_table=[], cot_ok=False, timeline=[], timeline_days=7, n_alerts=0,
        stance=builder._stance("up", [], False, False, None), real_rate_chart="")
    payload = re.search(r'<script id="forex-decision-context" type="application/json">(.*?)</script>', rendered, re.S).group(1)
    snapshot = json.loads(json.dumps({"decision_context": c}, allow_nan=False))
    assert json.loads(payload) == snapshot["decision_context"]
    assert 'class="smile-dot"' not in rendered
    assert "Current regime unavailable" in rendered and "Risk context unavailable" in rendered
    assert "The dollar is quiet today." not in rendered
    assert "t||'light'" in rendered


def test_independent_warning_survives_missing_risk():
    assert builder._stance("up", ["dollar_wrecking_ball"], False, False, None)["tone"] == "alert"
    assert builder._stance("up", [], True, False, None)["tone"] == "watch"
    assert builder._stance("up", [], False, False, None)["tone"] == "unavailable"


def test_macro_current_null_cannot_resurrect_old_risk():
    snap = {"sources": {"data/forex/latest.json": "2026-10-16"}}
    old = {"asof": "2026-10-15", "regime": "Global reflation", "risk": "risk-on"}
    assert macro._decision_fx_current({"fx_risk": None}, old, snap, "fx_risk", "risk", "2026-10-16") is None
    assert macro._decision_fx_current({}, old, snap, "fx_risk", "risk", "2026-10-16") is None
    fresh = {**old, "asof": "2026-10-16"}
    assert macro._decision_fx_current({}, fresh, snap, "fx_risk", "risk", "2026-10-16") == "risk-on"
    assert macro._decision_fx_current({"fx_risk": "risk-off"}, old, snap, "fx_risk", "risk", "2026-10-16") == "risk-off"


@pytest.mark.parametrize('family', ['smile_regime', 'smile_regime_flip'])
def test_out_of_coverage_smile_event_cannot_appear_current(family):
    d=frame().tail(3)
    e={'id':'old-future-event','type':family,'ts':'2026-12-31T16:00:00Z'}
    original=copy.deepcopy(e);out=alerts.qualified_current_events([e],d)
    assert out['events']==[] and out['withheld'][0]['reason']=='outside_qualified_dollar_coverage'
    assert e==original and not out['history_modified']


@pytest.mark.parametrize('value', [np.nan,np.inf,True,{},[]])
def test_readiness_missing_value_kind_is_not_qualified(value):
    r=receipt(value);r.pop('value_kind')
    out=builder._r4_readiness({'price':r},checked_at=NOW,action_requirements={'watch':['price']})
    assert not out['actions']['watch']['allowed'];json.dumps(out,allow_nan=False)


def test_correction_cannot_be_hidden_before_selected_tail():
    b=bars();newer={**b[0],'revision':2,'close':146.0}
    out=alerts.evaluate_price_condition(rule(),[newer,*b],now=NOW)
    assert out['outcome']=='withheld'
    assert 'missing_or_duplicate_observation_identity' in out['withheld_reasons']
    assert len(out['supplied_observations'])==3
    assert alerts.evaluate_price_condition(rule(),[newer,b[1]],now=NOW)['outcome']=='not_met'


@pytest.mark.parametrize('interval,calendar', [('UNKNOWN','unregistered/calendar'),('1D','fx-utc-4h/v1'),('4H','unregistered/calendar')])
def test_matching_unknown_calendar_assertions_do_not_qualify(interval,calendar):
    b=bars()
    for v in b:v.update(interval=interval,calendar=calendar)
    out=alerts.evaluate_price_condition(rule(interval=interval,calendar=calendar),b,now=NOW)
    assert out['outcome']=='withheld' and 'unsupported_interval_or_calendar' in out['withheld_reasons']


@pytest.mark.parametrize('end', ['2026-10-16T12:01:00Z','2026-10-16T16:00:00.000001Z','2026-10-16T08:00:00Z','2026-10-16T20:00:00Z'])
def test_4h_assertion_requires_real_slot_geometry(end):
    b=bars();b[1]['bar_end']=end
    assert alerts.evaluate_price_condition(rule(),b,now=NOW)['outcome']=='withheld'


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_invalid_numeric_evidence_is_strict_json(value):
    b=bars();b[-1]['close']=value
    for out in [alerts.evaluate_price_condition(rule(),b,now=NOW),alerts.evaluate_price_condition(rule(threshold=value),bars(),now=NOW)]:
        assert out['outcome']=='withheld'
        assert json.loads(json.dumps(out,allow_nan=False))['outcome']=='withheld'
        assert out['evaluation_id']


def test_duplicate_slot_under_different_identity_withholds():
    b=bars();newer={**b[0],'observation_id':'different-id','revision':2,'close':146.0}
    out=alerts.evaluate_price_condition(rule(),[newer,*b],now=NOW)
    assert out['outcome']=='withheld' and 'ambiguous_bar_revision_or_identity' in out['withheld_reasons']


@pytest.mark.parametrize('r,b',[(None,[]),(rule(operator=[]),bars()),(rule(),[None]),(rule(condition_id=[]),bars()),(rule(),[{**bars()[0],'observation_id':[]},bars()[1]])])
def test_malformed_contract_withholds_without_crashing(r,b):
    out=alerts.evaluate_price_condition(r,b,now=NOW)
    assert out['outcome']=='withheld';json.dumps(out,allow_nan=False)


def test_technical_provenance_does_not_invent_horizon_ladder():
    d=frame();d['residual_method']='raw_fallback';d['residual_dollar_carried']=False
    p={'key':'USDJPY','base':'JPY','quote':145.82,'ts_trend':'up','structure_state':'constructive','mtf_rows':[{'key':'D','trend':'up'}]}
    c=builder._decision_context({'USDJPY':d},[p],builder.dollar_vm(d),{},config.load()['forex'],[],checked_at=NOW)
    tech=c['pairs'][0]['technical_state']
    assert 'horizons' not in tech and tech['sampling']=='daily_observations'
    assert tech['trend_lookback_observations']==252 and tech['structure_swing_observations']==20
    assert tech['structure_breakout_observations']==60 and tech['residual_method']=='raw_fallback'
    assert c['pairs'][0]['multi_timeframe']['rows']==p['mtf_rows']
