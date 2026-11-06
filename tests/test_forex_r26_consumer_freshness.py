"""Successor integration regressions for the published #9828 consumer.

These tests validate independent repairs from the permitted retained report;
they do not claim to verify the original parent's inaccessible patch bytes.
"""
from copy import deepcopy
from datetime import date

import pytest

from lib.forex_r26_consumer import project_r26_consumer

REF = date(2026, 10, 21)


def payload():
    return {
        "asof": REF.isoformat(), "risk": "risk-off", "regime": "Risk-off haven bid",
        "favored": ["JPY"], "stance": {"word_en": "Watch", "word_zh": "观望"},
        "pairs": {
            "USDJPY": {"label": "USD/JPY", "quote": 148.2, "chg": -0.4,
                       "reliable": True, "action": "LONG", "score": 12.0,
                       "headline": "JPY source read", "head_zh": "日元来源判断",
                       "sub": "Source evidence", "sub_zh": "来源证据"},
        },
    }


def owner(available=True):
    return {
        "schema": "mastermind.forex.decision-context.v1", "authority": "display_only",
        "snapshot_id": "snapshot-current-1", "assembled_at": "2026-10-21T12:00:00Z",
        "source_revision": None,
        "current_read": {
            "calculated_asof": REF.isoformat(),
            "available": available, "risk": "risk-off" if available else None,
            "regime": "Risk-off haven bid" if available else None,
            "reason": None if available else "missing_or_invalid_risk_or_direction",
            "last_confirmed": {"regime": "US growth premium", "asof": "2026-10-19"},
        },
    }


def view(p):
    return project_r26_consumer(p, reference_date=REF)


def test_old_snapshot_remains_dated_without_current_promotion():
    p = payload()
    p["asof"] = "2026-10-19"
    p["decision_context"] = owner()
    v = view(p)
    assert v["gate"]["status"] == "ok"
    assert v["gate"]["asof_age_days"] == 2
    assert v["gate"]["freshness_status"] == "historical"
    assert v["gate"]["freshness_basis"] == "reference_date_comparison_only_not_source_freshness"
    for destination in ("today", "explore"):
        d = v["destinations"][destination]
        assert d["status"] == "degraded" and d["current_available"] is False
        assert "asof_before_reference_date" in d["gaps"]
    assert v["destinations"]["today"]["pair_tabs"][0]["price"] == 148.2
    assert v["current_read"]["assembled_at"] == "2026-10-21T12:00:00Z"


def test_present_owner_is_authoritative_over_good_legacy_fields():
    p = payload()
    p["decision_context"] = owner(False)
    v = view(p)
    assert v["destinations"]["today"]["current_available"] is False
    assert v["destinations"]["today"]["regime"] is None
    assert v["current_read"]["basis"] == "decision_context"
    assert v["current_read"]["snapshot_id"] == "snapshot-current-1"
    assert v["current_read"]["last_confirmed"]["asof"] == "2026-10-19"
    assert v["destinations"]["today"]["pair_tabs"][0]["price"] == 148.2


@pytest.mark.parametrize("bad", [
    None, [], {}, {"schema": "wrong"},
    dict(owner(), schema="other"),
    dict(owner(), authority="trade"),
    dict(owner(), snapshot_id=" "),
    dict(owner(), current_read={}),
    dict(owner(), current_read={"available": "true"}),
    dict(owner(), current_read={"available": 1}),
    dict(owner(), current_read={"available": None}),
])
def test_malformed_present_owner_never_falls_back(bad):
    p = payload()
    p["decision_context"] = bad
    v = view(p)
    assert v["destinations"]["today"]["status"] == "degraded"
    assert v["destinations"]["today"]["current_available"] is False
    assert v["current_read"]["reason"] == "decision_context_malformed"
    assert v["destinations"]["today"]["regime"] is None
    assert v["destinations"]["today"]["pair_tabs"][0]["price"] == 148.2


def test_current_owner_preserves_distinct_snapshot_and_assembly_fields():
    p = payload()
    p["decision_context"] = owner()
    v = view(p)
    assert v["destinations"]["today"]["status"] == "ok"
    assert v["destinations"]["today"]["current_available"] is True
    assert v["current_read"]["snapshot_id"] != v["current_read"]["assembled_at"]
    assert v["current_read"]["source_revision"] is None


@pytest.mark.parametrize("field", ["risk", "regime"])
@pytest.mark.parametrize("bad,suffix", [(None, "missing"), ("", "blank"), (" ", "blank"),
                                        (True, "invalid"), (0, "invalid"), ({}, "invalid")])
def test_legacy_missing_current_fields_degrade_without_losing_quotes(field, bad, suffix):
    p = payload()
    p[field] = bad
    v = view(p)
    today = v["destinations"]["today"]
    assert today["current_available"] is False
    assert f"{field}_{suffix}" in today["gaps"]
    assert today["pair_tabs"][0]["price"] == 148.2


@pytest.mark.parametrize("field", ["risk", "regime"])
def test_owner_available_flag_cannot_create_missing_current_evidence(field):
    p = payload()
    p["decision_context"] = owner()
    del p["decision_context"]["current_read"][field]
    v = view(p)
    assert v["current_read"]["available"] is False
    assert f"decision_context_{field}_missing" in v["current_read"]["gaps"]


def test_zh_alias_precedence_and_sub_copy_are_preserved():
    p = payload()
    tab = view(p)["destinations"]["today"]["pair_tabs"][0]
    assert tab["source_headline_zh"] == "日元来源判断"
    assert tab["source_sub_zh"] == "来源证据"
    p["pairs"]["USDJPY"]["headline_zh"] = "首选中文"
    assert view(p)["destinations"]["today"]["pair_tabs"][0]["source_headline_zh"] == "首选中文"


@pytest.mark.parametrize("bad", ["USDJPY", b"USDJPY", {"USDJPY": 1}, {"USDJPY"},
                                 [None], [7], [""], ["USDJPY", "USDJPY"]])
def test_universe_rejects_ambiguous_identity_or_order(bad):
    with pytest.raises(ValueError):
        project_r26_consumer(payload(), reference_date=REF, universe=bad)


def test_dxy_cannot_claim_currency_pair_availability():
    p = payload()
    p["pairs"]["DXY"] = {"label": "DXY", "quote": 104.0, "chg": 0.0,
                         "reliable": True, "action": "LONG"}
    tab = view(p)["destinations"]["today"]["pair_tabs"][-1]
    assert tab["status"] == "degraded" and tab["direction"] is None
    assert "not_currency_pair" in tab["gaps"]


def test_cnh_is_the_literal_quote_currency():
    p = payload()
    p["pairs"] = {"USDCNH": dict(p["pairs"]["USDJPY"], label="USD/CNH")}
    tab = view(p)["destinations"]["today"]["pair_tabs"][0]
    assert tab["base_ccy"] == "USD" and tab["quote_ccy"] == "CNH"
    assert tab["direction"]["quote_ccy_state"] == "stronger"


def test_projection_does_not_mutate_or_alias_input_or_destinations():
    p = payload()
    p["decision_context"] = owner()
    original = deepcopy(p)
    v = view(p)
    v["destinations"]["today"]["pair_tabs"][0]["gaps"].append("test-only")
    v["destinations"]["today"]["stance"]["word_en"] = "changed"
    v["current_read"]["last_confirmed"]["regime"] = "changed"
    assert v["destinations"]["explore"]["pairs"][0]["gaps"] == []
    assert p == original


def test_account_watch_state_is_not_inferred_from_empty_projection():
    watches = view(payload())["destinations"]["my_watches"]
    assert watches["account_state"] == "unavailable"
    assert watches["activation_available"] is False
    assert watches["persistence"] == "none"


@pytest.mark.parametrize("current_date,reason", [
    (None, "current_read_asof_unknown_or_malformed"),
    ("2026-99-11", "current_read_asof_unknown_or_malformed"),
    ("2026-10-22", "current_read_asof_future"),
    ("2026-10-20", "current_read_asof_before_reference_date"),
])
def test_newest_pair_date_does_not_refresh_dollar_risk(current_date, reason):
    p = payload()
    p["decision_context"] = owner()
    p["decision_context"]["current_read"]["calculated_asof"] = current_date
    v = view(p)
    assert v["current_read"]["available"] is False
    assert reason in v["current_read"]["gaps"]
    assert v["destinations"]["today"]["pair_tabs"][0]["price"] == 148.2


@pytest.mark.parametrize("pair,inverse", [
    ("USDJPY", True), ("USDCAD", True), ("USDCHF", True), ("USDMXN", True),
    ("USDBRL", True), ("USDCNH", True), ("EURUSD", False), ("GBPUSD", False),
    ("AUDUSD", False),
])
@pytest.mark.parametrize("action", ["LONG", "STRONG LONG", "SHORT", "STRONG SHORT"])
def test_model_lean_is_mapped_through_qualified_literal_pair(pair, inverse, action):
    p = payload()
    row = dict(p["pairs"]["USDJPY"], action=action, chg=0.4, calculated_asof=REF.isoformat())
    p["pairs"] = {pair: row}
    p["decision_context"] = owner()
    p["decision_context"]["pairs"] = [{
        "pair": pair, "display_base": pair[:3], "display_quote": pair[3:],
        "assessed_currency": pair[3:] if inverse else pair[:3],
        "assessed_to_pair_direction": "opposite" if inverse else "same",
        "quote_convention": {"status": "qualified", "inverted_from_assessed": inverse},
    }]
    tab = view(p)["destinations"]["today"]["pair_tabs"][0]
    higher = ("LONG" in action) != inverse
    assert tab["model_direction"]["pair_direction"] == ("higher" if higher else "lower")
    # The observed quote increase stays independent even when the model leans lower.
    assert tab["direction"]["base_ccy_state"] == "stronger"
    assert p["pairs"][pair]["action"] == action


@pytest.mark.parametrize("field,bad", [
    ("display_base", "JPY"), ("display_quote", "USD"),
    ("assessed_currency", "CNY"), ("assessed_to_pair_direction", "same"),
    ("quote_convention", {"status": "qualified", "inverted_from_assessed": False}),
    ("quote_convention", {"status": "unavailable", "inverted_from_assessed": True}),
])
def test_unknown_or_contradictory_convention_withholds_model_direction(field, bad):
    p = payload()
    p["decision_context"] = owner()
    instrument = {
        "pair": "USDJPY", "display_base": "USD", "display_quote": "JPY",
        "assessed_currency": "JPY", "assessed_to_pair_direction": "opposite",
        "quote_convention": {"status": "qualified", "inverted_from_assessed": True},
    }
    instrument[field] = bad
    p["decision_context"]["pairs"] = [instrument]
    tab = view(p)["destinations"]["today"]["pair_tabs"][0]
    assert tab["model_direction"]["available"] is False
    assert tab["model_direction"]["pair_direction"] is None
    assert tab["direction"]["quote_ccy_state"] == "stronger"
