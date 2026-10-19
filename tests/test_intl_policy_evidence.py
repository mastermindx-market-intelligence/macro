"""Policy decisions must preserve instrument, effectiveness and knowledge clocks."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from lib.intl_policy_evidence import normalize_policy_decision, merge_policy_decisions, select_policy_decision
from collectors.intl_policy_sources import RELEASES, parse_registered_policy_release
from collectors.intl_country_sources import merge_country_inputs, SCHEMA

TODAY = date(2026, 10, 18)
NOW = "2026-10-18T12:00:00+00:00"
ROOT = Path(__file__).resolve().parents[1]


def raw(**changes):
    item = {**deepcopy(RELEASES[0]), "schema": "intl_policy_decision.v1", "unit": "percent",
            "action": "hold", "first_observed_at": "2026-09-17T12:00:00+00:00"}
    item.update(changes)
    return item


def selected(records, **kwargs):
    return select_policy_decision(records, "GB", today=TODAY, **kwargs)


def test_hold_uses_decision_date_without_inventing_last_change():
    result = selected([raw(last_change_date="2026-02-05")])
    assert result["current"] and result["value"] == 3.75 and result["action"] == "hold"
    assert result["decision_date"] == "2026-09-16" and result["last_change_date"] == "2026-02-05"
    assert result["instrument_en"] == "Bank Rate"


def test_future_effective_change_remains_announced():
    future = raw(value=4.0, previous_value=3.75, action="increase", decision_date="2026-10-15",
                 published="2026-10-15", effective_date="2026-11-01", first_observed_at=NOW)
    result = selected([raw(), future])
    assert result["value"] == 3.75 and result["current"]
    assert result["announced"]["value"] == 4.0
    only = selected([future])
    assert only["state"] == "announced" and not only["current"]


def test_conflicting_actions_cannot_win_by_arrival():
    hold = raw()
    cut = raw(previous_value=4.0, action="decrease")
    for rows in ([hold, cut], [cut, hold]):
        assert selected(rows)["state"] == "conflict"


def test_future_effective_version_does_not_hide_same_decision_conflict():
    common = dict(value=4.0, previous_value=3.75, action="increase", decision_date="2026-10-15",
                  published="2026-10-15", first_observed_at="2026-10-15T12:00:00+00:00")
    first = raw(**common, effective_date="2026-10-16")
    second = raw(**common, effective_date="2026-11-01")
    assert selected([first, second])["state"] == "conflict"
    assert select_policy_decision([first, second], "GB", operational_as_of="2026-10-18T12:00:00+00:00")["state"] == "conflict"


def test_vote_disagreement_is_not_reported_as_verified():
    other = raw(votes={"hold": 5, "increase": 4, "decrease": 0})
    assert selected([raw(), other])["state"] == "conflict"


def test_latest_decision_replaces_older_conflict():
    later = raw(value=4.0, previous_value=3.75, action="increase", decision_date="2026-10-15",
                published="2026-10-15", effective_date="2026-10-15", first_observed_at=NOW)
    assert selected([raw(), raw(previous_value=4.0, action="decrease"), later])["value"] == 4.0
    assert selected([raw(), raw(previous_value=4.0, action="decrease"), later])["current"]


def monthly(**changes):
    item = {"value": 4.0, "period": "2026-09", "instrument": "bank_rate",
            "observation_convention": "end_of_period", "first_observed_at": "2026-10-01T12:00:00+00:00"}
    item.update(changes)
    return item


def test_newer_matching_monthly_setting_demands_reconciliation():
    assert selected([raw()], monthly=monthly())["state"] == "conflict"
    assert selected([raw()], monthly=monthly(instrument="three_month_money_market_rate"))["current"]
    assert selected([raw()], monthly=monthly(observation_convention="monthly_average"))["current"]


@pytest.mark.parametrize("changes", [
    {"period": "2099-99"}, {"period": "2026-13"}, {"period": "2026-10"},
    {"value": float("nan")}, {"value": float("inf")}, {"value": 10 ** 1000},
])
def test_malformed_or_future_monthly_input_cannot_suppress_sound_decision(changes):
    result = selected([raw()], monthly=monthly(**changes))
    assert result["current"] and result["monthly_context"] is None


def test_replay_omits_monthly_evidence_not_yet_observed():
    result = selected([raw()], monthly=monthly(),
                      operational_as_of="2026-09-20T12:00:00+00:00")
    assert result["current"] and result["monthly_context"] is None
    unknown = monthly(period="2026-08", first_observed_at=None)
    assert selected([raw()], monthly=unknown, operational_as_of="2026-09-20T12:00:00+00:00")["monthly_context"] is None


@pytest.mark.parametrize("cutoff", ["", False, "not-a-date"])
def test_invalid_replay_never_defaults_to_current(cutoff):
    with pytest.raises(ValueError, match="replay_cutoff"):
        selected([raw()], operational_as_of=cutoff)


def test_future_custody_is_not_current_evidence():
    assert selected([raw(first_observed_at="2030-01-01T00:00:00+00:00")]) is None


def test_incoming_source_cannot_backdate_system_custody():
    records = merge_policy_decisions([], [raw()], observed_at=NOW)
    assert records[0]["first_observed_at"] == NOW
    repeated = merge_policy_decisions(records, [raw()], observed_at="2026-10-19T12:00:00+00:00")
    assert repeated[0]["first_observed_at"] == NOW
    assert selected(records, operational_as_of="2026-10-17T12:00:00+00:00") is None


@pytest.mark.parametrize("changes", [
    {"value": 10 ** 1000}, {"cc": []}, {"instrument": {}}, {"source_url": []},
    {"published": "2026-09-15"}, {"unit": "percent_gdp"}, {"action": "decrease"},
    {"votes": {"hold": 6}}, {"rationale_en": []},
    {"value": 4.0, "action": "increase", "last_change_date": "2026-08-01"},
])
def test_malformed_decision_is_isolated(changes):
    assert normalize_policy_decision(raw(**changes)) is None


def test_partial_replay_retains_source_receipts():
    old = {"schema": SCHEMA, "retrieved_at": "2026-10-18T08:00:00+00:00",
           "sources": [{"url": "https://example.org/bis", "sha256": "a", "status": "read"}]}
    new = {"schema": SCHEMA, "retrieved_at": NOW,
           "sources": [{"dataset_url": "https://www.imf.org/tablea.pdf", "sha256": "b",
                        "status": "verified", "retrieved_at": NOW}]}
    merged = merge_country_inputs(new, old)
    assert len(merged["sources"]) == 2 and merged["retrieved_at"] == NOW
    assert next(r for r in merged["sources"] if r.get("dataset_url"))["retrieved_at"] == NOW


def test_latest_baseline_contains_world_and_distinct_national_forecasts():
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    world = [x for x in base["forecast_archive"] if x["cc"] == "WORLD"]
    assert world[0]["values"]["2026"] == 3.1 and world[0]["values"]["2027"] == 3.4
    cbc = [x for x in base["forecast_archive"] if x["provider"] == "CBC"]
    assert {x["series_id"] for x in cbc} == {"real_gdp_growth", "inflation_average"}
    assert len(base["policy_decisions"]) == 2


def test_reviewed_boe_parser_checks_meeting_rate_and_vote():
    # A minimal parser contract fixture, not a recorded HTML retrieval.
    html = b"""<p>Published on 17 September 2026</p>
      <p>At its meeting ending on 16 September 2026, the MPC voted by a majority of 6-3 to maintain Bank Rate at 3.75%.</p>
      <p>Three members voted to increase Bank Rate by 0.25 percentage points, to 4%.</p>
      <p>soft labour market conditions; second-round effects</p>"""
    result = parse_registered_policy_release(html, RELEASES[0], retrieved_at=NOW)
    assert result["policy_decisions"][0]["votes"]["increase"] == 3
    with pytest.raises(ValueError, match="decision_changed"):
        parse_registered_policy_release(html.replace(b"3.75%", b"4.25%"), RELEASES[0], retrieved_at=NOW)
