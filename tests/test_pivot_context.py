"""tests/test_pivot_context.py — BP1 contract tests for engine/neuralweb/pivot_context.py

Frozen-contract coverage: normal composition, clock gates (future known-time,
future source date, stale vintage, calendar-day age, the US/New_York date
boundary), both evidence modes, conflicts, malformed shapes, value domains,
deterministic JSON, immutability and the negative claim set.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.neuralweb.pivot_context import (  # noqa: E402
    ALLOWED_FIELDS, EVIDENCE_MODES, FIELD_ORDER, SCHEMA, compose_pivot_context,
)

D = "2026-11-05T16:30:00-05:00"   # 21:30Z -> US/New_York date 2026-11-05
AV = "2026-11-05T17:00:00Z"       # a known first-seen time, before the decision
DATE = "2026-11-05"
NUMERIC = ("trigger_age_ticks", "hold_days_basing", "knife_score",
           "hold_ret_since_anchor_pct", "dist_21d_low_pct", "dist_126d_high_pct")


def obs(field, value, *, source="src", as_of=DATE, available_at=AV):
    """One well-formed observation."""
    return {"field": field, "value": value, "source": source, "as_of": as_of,
            "available_at": available_at}


def row(result, field):
    """One evidence row by field name."""
    return {r["field"]: r for r in result["evidence"]}[field]


def full():
    """One usable observation for every allowlisted field."""
    return [obs("trigger_tier", "T2"), obs("trigger_age_ticks", 3), obs("coiled", True),
            obs("star", False), obs("coiled_fire", True), obs("above200", False),
            obs("hold_state", "basing"), obs("hold_days_basing", 12),
            obs("hold_ret_since_anchor_pct", -1.4), obs("knife_score", 0.42),
            obs("dist_21d_low_pct", 3.5), obs("dist_126d_high_pct", 8.1),
            obs("sponsorship_state", "tailwind")]


def compose(observations=None, **kwargs):
    """Compose against the default decision frame."""
    return compose_pivot_context("AAPL", full() if observations is None else observations,
                                 decision_at=D, **kwargs)


def test_observed_normal():
    r = compose()
    assert (r["schema"], r["scope"], r["cadence"]) == (SCHEMA, "single_security", "daily")
    assert (r["symbol"], r["evidence_mode"], r["decision_at"]) == ("AAPL", "current_snapshot", D)
    assert r["is_display_only"] is True and r["quality"] == "available"
    assert [x["field"] for x in r["evidence"]] == list(FIELD_ORDER)
    assert set(x["field"] for x in r["evidence"]) == set(ALLOWED_FIELDS)
    for x in r["evidence"]:
        assert x["state"] == "observed" and x["value"] is not None
        assert set(x) == {"field", "value", "state", "source", "as_of", "available_at"}
    assert {x["field"]: x["value"] for x in r["evidence"]} == {
        "trigger_tier": "T2", "trigger_age_ticks": 3, "coiled": True, "star": False,
        "coiled_fire": True, "above200": False, "hold_state": "basing", "hold_days_basing": 12,
        "hold_ret_since_anchor_pct": -1.4, "knife_score": 0.42, "dist_21d_low_pct": 3.5,
        "dist_126d_high_pct": 8.1, "sponsorship_state": "tailwind"}
    assert r["limitations"][:3] == ["daily_not_intraday", "no_calibrated_probability",
                                    "no_market_bottom_claim"]


def test_explanation_is_bilingual_and_disclaimed():
    en, zh = compose()["explanation"]["en"], compose()["explanation"]["zh"]
    assert "daily single-stock context" in en
    assert "not proof of the market bottom" in en and "not a trade instruction" in en
    assert "市场底部" in zh and "交易指令" in zh
    assert "cohort-washout context is present" in en
    assert "an existing early-turn marker is present" in en and "0.42" in en
    for forbidden in ("buy", "sell", "confirmed bottom", "recommend", "position size"):
        assert forbidden not in (en + zh).lower()


def test_below200_preserves_the_early_marker():
    r = compose([obs("coiled_fire", True), obs("above200", False), obs("knife_score", 0.3)])
    en = r["explanation"]["en"]
    assert row(r, "coiled_fire")["value"] is True
    assert "an existing early-turn marker is present" in en
    assert "does not automatically invalidate an early turn" in en
    assert row(r, "knife_score")["state"] == "observed" and "0.3" in en


def test_no_ma_input_does_not_gate():
    r = compose([obs("coiled_fire", True), obs("coiled", True), obs("knife_score", 0.11)])
    assert row(r, "above200")["state"] == "missing" and row(r, "above200")["value"] is None
    en = r["explanation"]["en"]
    assert "an existing early-turn marker is present" in en
    assert "cohort-washout context is present" in en and "200-day" not in en


def test_missing_coiled_vs_false_coiled():
    missing = compose([])
    assert (row(missing, "coiled")["state"], row(missing, "coiled")["value"]) == ("missing", None)
    assert "cohort-washout context is present" not in missing["explanation"]["en"]
    assert missing["quality"] == "unavailable"
    false = compose([obs("coiled", False)])
    assert (row(false, "coiled")["state"], row(false, "coiled")["value"]) == ("observed", False)
    assert "cohort-washout context is present" not in false["explanation"]["en"]


@pytest.mark.parametrize("mode", ["current_snapshot", "as_issued"])
def test_future_known_time_and_future_source_date_are_rejected(mode):
    late = compose([obs("knife_score", 0.5, available_at="2026-11-06T10:00:00Z")],
                   evidence_mode=mode)
    ahead = compose([obs("knife_score", 0.5, as_of="2026-11-06")])
    for r in (late, ahead):
        assert (row(r, "knife_score")["state"], row(r, "knife_score")["value"]) == ("future", None)


def test_stale_age_and_the_inclusive_age_boundary():
    """Age is calendar days: 7 days is fresh, 8 is stale."""
    assert row(compose([obs("knife_score", 0.5, as_of="2026-10-29")]),
               "knife_score")["state"] == "observed"
    stale = compose([obs("knife_score", 0.5, as_of="2026-10-28")])
    assert (row(stale, "knife_score")["state"], row(stale, "knife_score")["value"]) == \
        ("stale", None)


@pytest.mark.parametrize("bad", ["2026-13-01", "2026-02-30", "20261105", "not-a-date", "",
                                 "2026-11-5", None])
def test_invalid_or_missing_date_is_rejected(bad):
    assert row(compose([obs("knife_score", 0.5, as_of=bad)]), "knife_score")["state"] == "invalid"


def test_blank_source_and_naive_available_at_are_rejected():
    assert row(compose([obs("knife_score", 0.5, source="  ")]),
               "knife_score")["state"] == "invalid"
    assert row(compose([obs("knife_score", 0.5, available_at="2026-11-05T12:00:00")]),
               "knife_score")["state"] == "invalid"


@pytest.mark.parametrize("bad", ["2026-11-05T16:30:00", "2026-11-05", "not-a-timestamp", "",
                                "2026-13-45T99:99:99Z", None, 20261105, []])
def test_invalid_decision_returns_unavailable_and_never_raises(bad):
    r = compose_pivot_context("AAPL", full(), decision_at=bad)
    assert r["quality"] == "unavailable"
    assert r["probability"] is None and r["action_authority"] == "none"
    assert len(r["evidence"]) == len(FIELD_ORDER)
    assert all(x["state"] == "invalid" and x["value"] is None for x in r["evidence"])
    assert "not proof of the market bottom" in r["explanation"]["en"]


@pytest.mark.parametrize("kwargs", [{"max_age_days": bad} for bad in (-1, "7", 7.5, None, True)]
                             + [{"evidence_mode": "as_issued_v2"}])
def test_invalid_requests_fail_closed(kwargs):
    r = compose_pivot_context("AAPL", full(), decision_at=D, **kwargs)
    assert r["quality"] == "unavailable"
    assert all(x["state"] == "invalid" for x in r["evidence"])
    assert compose_pivot_context("", full(), decision_at=D)["quality"] == "unavailable"
    assert compose_pivot_context("AAPL", {"x": 1}, decision_at=D)["quality"] == "unavailable"


def test_as_issued_rejects_a_missing_known_time():
    r = compose([obs("knife_score", 0.42, available_at=None)], evidence_mode="as_issued")
    assert (row(r, "knife_score")["state"], row(r, "knife_score")["value"]) == ("not_known", None)
    assert r["quality"] == "unavailable"
    known = compose([obs("knife_score", 0.42)], evidence_mode="as_issued")
    assert row(known, "knife_score")["state"] == "observed"
    assert "first_seen_unknown" not in known["limitations"]


def test_current_snapshot_marks_first_seen_unknown():
    r = compose([obs("knife_score", 0.42, available_at=None)])
    assert (row(r, "knife_score")["state"], row(r, "knife_score")["value"]) == ("observed", 0.42)
    assert "first_seen_unknown" in r["limitations"]
    assert "first_seen_unknown" not in compose()["limitations"]


def test_duplicate_field_is_a_conflict():
    for pair, field in (([obs("knife_score", 0.42), obs("knife_score", 0.42)], "knife_score"),
                        ([obs("knife_score", 0.42), obs("knife_score", 0.77)], "knife_score"),
                        ([{"field": "coiled", "value": True},
                          {"field": "coiled", "value": True, "source": "s"}], "coiled")):
        entry = row(compose(pair), field)
        assert entry["state"] == "conflict" and entry["value"] is None
        assert entry["source"] is None and entry["as_of"] is None


def test_malformed_observations_do_not_crash():
    observations = [None, "a string", 42, [], {"value": 1.0, "source": "x"},
                    {"field": 123, "value": 1.0}, {"field": "coiled", "value": True},
                    {"field": "not_a_real_field", "value": 1, "source": "s", "as_of": DATE,
                     "available_at": AV}, obs("knife_score", 0.4)]
    r = compose(observations)
    assert r["quality"] == "partial"
    assert row(r, "knife_score")["state"] == "observed"
    assert row(r, "coiled")["state"] == "invalid"
    assert len(r["evidence"]) == len(FIELD_ORDER)
    empty = compose([])
    assert empty["quality"] == "unavailable"
    assert "insufficient current evidence" in empty["explanation"]["en"]
    assert "当前证据不足" in empty["explanation"]["zh"]


@pytest.mark.parametrize("field", NUMERIC)
def test_bool_is_not_accepted_as_a_number(field):
    entry = row(compose([obs(field, True)]), field)
    assert entry["state"] == "missing" and entry["value"] is None


@pytest.mark.parametrize("field", ["coiled", "star", "coiled_fire", "above200"])
@pytest.mark.parametrize("value", [1, 0, "true", "False"])
def test_numbers_are_not_accepted_as_booleans(field, value):
    assert row(compose([obs(field, value)]), field)["state"] == "missing"


@pytest.mark.parametrize("field", ["knife_score", "hold_ret_since_anchor_pct",
                                    "dist_21d_low_pct", "dist_126d_high_pct"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_inf_are_missing(field, value):
    entry = row(compose([obs(field, value)]), field)
    assert entry["state"] == "missing" and entry["value"] is None


def test_value_domains():
    assert row(compose([obs("trigger_tier", "T2")]), "trigger_tier")["state"] == "observed"
    for bad in ("T5", "t2", "", "T2 "):
        assert row(compose([obs("trigger_tier", bad)]), "trigger_tier")["state"] == "invalid"
    for field in ("trigger_age_ticks", "hold_days_basing"):
        assert row(compose([obs(field, -1)]), field)["state"] == "invalid"
    for bad in (-0.1, 1.1, 2):
        assert row(compose([obs("knife_score", bad)]), "knife_score")["state"] == "invalid"
    for field in ("dist_21d_low_pct", "dist_126d_high_pct"):
        assert row(compose([obs(field, -0.5)]), field)["state"] == "invalid"
    assert row(compose([obs("hold_ret_since_anchor_pct", -12.5)]),
               "hold_ret_since_anchor_pct")["value"] == -12.5
    for bad in ("0.42", [0.42], {"v": 1}, object()):
        assert row(compose([obs("knife_score", bad)]), "knife_score")["state"] == "missing"
    for value in ("unavailable", "unknown", "UNAVAILABLE"):
        assert row(compose([obs("sponsorship_state", value)]),
                   "sponsorship_state")["state"] == "missing"
    assert row(compose([obs("hold_state", "x" * 80)]), "hold_state")["state"] == "observed"
    assert row(compose([obs("hold_state", "x" * 81)]), "hold_state")["state"] == "invalid"
    # source is provenance, not a field value: a long path is legitimate
    assert row(compose([obs("coiled", True, source="site/factordata/" + "x" * 120)]),
               "coiled")["state"] == "observed"


def test_json_is_deterministic_and_input_is_not_mutated():
    r = compose()
    assert json.loads(json.dumps(r, allow_nan=False))["schema"] == SCHEMA
    assert json.dumps(compose(), allow_nan=False) == json.dumps(compose(), allow_nan=False)
    observations = full()
    snapshot = copy.deepcopy(observations)
    compose(observations)
    compose_pivot_context("AAPL", observations, decision_at="nonsense")
    assert observations == snapshot


def test_no_fabricated_probability_score_or_recommendation():
    r = compose()
    assert r["probability"] is None
    assert r["action_authority"] == "none" and r["is_display_only"] is True
    assert set(r) == {"schema", "symbol", "scope", "cadence", "evidence_mode", "decision_at",
                      "is_display_only", "probability", "action_authority", "quality",
                      "evidence", "explanation", "limitations"}
    blob = json.dumps(r, allow_nan=False).lower()
    for forbidden in ("recommend", "bullish_score", "risk_score", "rank", "eligible",
                      "position_size", "phase_classifier", "institutional_absorption"):
        assert forbidden not in blob


def test_unrecognized_armed_and_primed_observations_are_ignored():
    r = compose([obs("ARMED", True), obs("PRIMED", True), obs("armed", "yes"),
                 obs("bullish_score", 88), obs("knife_score", 0.2)])
    fields = [x["field"] for x in r["evidence"]]
    assert "ARMED" not in fields and "PRIMED" not in fields
    assert set(fields) == set(FIELD_ORDER)
    blob = json.dumps(r, allow_nan=False).lower()
    assert "armed" not in blob and "primed" not in blob


def test_mixed_valid_and_unavailable_produces_partial():
    r = compose([obs("coiled", True), obs("knife_score", 0.42),
                 obs("coiled_fire", True, as_of="2026-10-01")])
    assert r["quality"] == "partial"
    assert row(r, "coiled")["state"] == "observed"
    assert row(r, "coiled_fire")["state"] == "stale"
    assert row(r, "trigger_tier")["state"] == "missing"
    unusable = compose([obs("coiled", True, as_of="2026-10-01"),
                        obs("star", True, available_at="2026-12-01T00:00:00Z")])
    assert unusable["quality"] == "unavailable"


def test_appending_a_future_observation_does_not_change_the_earlier_frame():
    """A not-yet-knowable row may not change what the frame concluded."""
    base = [obs("coiled", True), obs("knife_score", 0.4)]
    earlier, later = compose(base), compose(base + [
        obs("star", True, available_at="2026-11-06T10:00:00Z"),
        obs("hold_state", "basing", as_of="2026-11-06")])
    observed = lambda r: {x["field"]: x["value"] for x in r["evidence"]
                          if x["state"] == "observed"}
    assert observed(earlier) == observed(later)
    assert earlier["quality"] == later["quality"] == "partial"
    assert earlier["explanation"] == later["explanation"]
    for field in ("star", "hold_state"):
        assert row(later, field)["state"] == "future" and row(later, field)["value"] is None


def test_new_york_date_boundary():
    """2026-11-06T02:30Z is still 2026-11-05 in New York; 05:30Z is 11-06."""
    evening = compose_pivot_context(
        "AAPL", [obs("knife_score", 0.4, as_of="2026-11-05"),
                 obs("coiled", True, as_of="2026-11-06")], decision_at="2026-11-06T02:30:00Z")
    assert row(evening, "knife_score")["state"] == "observed"
    assert row(evening, "coiled")["state"] == "future"
    midnight = compose_pivot_context(
        "AAPL", [obs("knife_score", 0.4, as_of="2026-11-06", available_at="2026-11-06T05:15:00Z"),
                 obs("coiled", True, as_of="2026-11-05")], decision_at="2026-11-06T05:30:00Z")
    assert row(midnight, "knife_score")["state"] == "observed"
    assert row(midnight, "coiled")["state"] == "observed"
    summer = compose_pivot_context(
        "AAPL", [obs("knife_score", 0.4, as_of="2026-07-04", available_at="2026-07-04T20:00:00Z"),
                 obs("coiled", True, as_of="2026-07-05", available_at="2026-07-04T20:00:00Z")],
        decision_at="2026-07-05T03:30:00Z")
    assert row(summer, "knife_score")["state"] == "observed"
    assert row(summer, "coiled")["state"] == "future"


@pytest.mark.parametrize("field", ["trigger_age_ticks", "hold_days_basing",
    "hold_ret_since_anchor_pct", "knife_score", "dist_21d_low_pct", "dist_126d_high_pct"])
def test_zero_numeric_observations_are_not_false_boolean_templates(field):
    result=compose_pivot_context("ABC", [{"field":field,"value":0,"source":"test",
        "as_of":"2026-11-05","available_at":"2026-11-05T20:00:00Z"}],
        decision_at="2026-11-05T22:00:00Z")
    assert result["quality"]=="partial"
    assert next(x for x in result["evidence"] if x["field"]==field)["value"]==0
    json.dumps(result,allow_nan=False)


def test_future_duplicate_cannot_erase_prior_known_observation():
    original={"field":"coiled_fire","value":True,"source":"test","as_of":"2026-11-05",
              "available_at":"2026-11-05T20:00:00Z"}
    future={**original,"value":False,"available_at":"2026-11-06T20:00:00Z"}
    kwargs={"decision_at":"2026-11-05T22:00:00Z","evidence_mode":"as_issued"}
    expected=compose_pivot_context("ABC",[original],**kwargs)
    assert compose_pivot_context("ABC",[original,future],**kwargs)==expected
    assert compose_pivot_context("ABC",[future,original],**kwargs)==expected


def test_timezone_has_no_arbitrary_1987_research_floor():
    result=compose_pivot_context("ABC",[{"field":"above200","value":False,"source":"test",
        "as_of":"1980-06-03","available_at":"1980-06-03T20:00:00Z"}],
        decision_at="1980-06-04T00:30:00Z",evidence_mode="as_issued")
    assert result["quality"]=="partial"


def test_known_time_cannot_precede_the_observation_vintage():
    result=compose_pivot_context('ABC',[{'field':'coiled_fire','value':True,'source':'test',
        'as_of':'2026-11-05','available_at':'2026-11-04T22:00:00Z'}],
        decision_at='2026-11-05T22:00:00Z',evidence_mode='as_issued')
    e=next(e for e in result['evidence'] if e['field']=='coiled_fire')
    assert e['state']=='invalid' and e['value'] is None


def test_extreme_availability_time_fails_closed_without_overflow():
    result=compose_pivot_context('ABC',[{'field':'coiled_fire','value':True,'source':'test',
        'as_of':'2026-11-05','available_at':'0001-01-01T00:00:00+14:00'}],
        decision_at='2026-11-05T22:00:00Z')
    assert result['quality']=='unavailable'
