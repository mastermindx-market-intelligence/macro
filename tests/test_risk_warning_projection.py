"""Warning delivery contracts, not financial-model performance tests.

Run without the application or network:
  python -m pytest tests/test_risk_warning_projection.py -q
"""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module
import json

import pytest

SESSION = "2026-09-25"


def api():
    # Lazy import makes the pre-implementation RED a test failure, not a
    # collection error; after implementation this loads the real module.
    return import_module("scripts.risk_warning_projection")


def radar(state="caution", score=80, market="us", session=SESSION):
    out = {
        "schema": "risk_radar.v2" if market == "us" else "risk_radar_intl.v1",
        "asof": session, "state": state, "top_score": score,
        "dominant_label_en": "Rates / inflation shock",
        "dominant_label_zh": "利率/通胀冲击",
    }
    if market != "us":
        out["market"] = market
    return out


def project(snapshot=None, market="us", expected=SESSION, **kwargs):
    return api().project_radar_warning(
        snapshot, market=market, expected_session=expected, **kwargs
    )


@pytest.mark.parametrize("state,attention", [
    ("calm", "none"), ("watch", "watch"), ("caution", "warning"),
    ("elevated", "high"), ("risk-off", "critical"),
])
def test_existing_states_map_to_attention_without_changing_engine_state(state, attention):
    value = project(radar(state))
    assert value["state"] == state
    assert value["attention"] == attention
    assert value["status"] == "current"
    assert value["artifact_freshness"] == "current"


def test_caution_80_is_visible_but_not_promoted_from_raw_99():
    source = radar(score=99)
    source["state_ungated"] = "risk-off"
    value = project(source)
    assert value["attention"] == "warning"
    assert value["confirmation"] == "pending"
    assert value["score"] == 99
    assert value["score_semantics"] == "intensity_not_probability"


def test_china_99_is_severe_context_not_probability_or_sizing():
    source = radar("risk-off", 99, "cn")
    source.update(drawdown_prob={"h21": .99}, can_force=True, gross=.62)
    value = project(source, market="cn")
    assert value["attention"] == "critical"
    assert value["score"] == 99
    assert "drawdown_prob" not in value and "gross" not in value
    assert value["authority"] == {
        "display_only": True, "may_execute": False, "may_size": False,
        "may_gate": False, "may_rank": False,
    }
    assert value["recovery"] == {"assessed": False, "reentry_authorized": False}


@pytest.mark.parametrize("score", [0, 0.0, 80, 99.5, 100, None])
def test_zero_and_missing_optional_score_do_not_become_fake_risk(score):
    value = project(radar(score=score))
    assert value["status"] == "current"
    assert value["score"] == score


@pytest.mark.parametrize("score", [True, False, float("nan"), float("inf"),
                                  -float("inf"), -1, 101, "80", {}, []])
def test_invalid_score_is_unavailable_and_serializable(score):
    value = project(radar(score=score))
    assert value["status"] == "unavailable"
    assert value["state"] is None and value["score"] is None
    assert "invalid_score" in value["reason_codes"]
    json.dumps(value, allow_nan=False)


@pytest.mark.parametrize("source", [None, [], "risk-off", {}, {"state": "calm"}])
def test_missing_or_wrong_shape_is_not_calm(source):
    value = project(source)
    assert value["status"] == "unavailable"
    assert value["state"] is None
    assert value["attention"] == "unavailable"


@pytest.mark.parametrize("date", [None, "", "2026-9-25", "2026-09-25junk",
                                  "2026-09-25T00:00:00Z", "2026-02-30", 20260925])
def test_strict_source_dates_refuse_truncation(date):
    value = project(radar(session=date))
    assert value["status"] == "unavailable"
    assert "invalid_source_session" in value["reason_codes"]


@pytest.mark.parametrize("session,reason", [
    ("2026-09-24", "stale_source_session"),
    ("2026-09-28", "future_source_session"),
])
def test_calendar_reference_is_independent_of_snapshot(session, reason):
    source = radar(session=session)
    source["generated_at"] = "2026-09-28T03:00:00Z"
    value = project(source)
    assert value["status"] == "unavailable"
    assert reason in value["reason_codes"]


@pytest.mark.parametrize("expected", [None, "", "2026-09-25junk", "2026-02-30"])
def test_missing_expected_calendar_session_never_uses_source_as_reference(expected):
    value = project(radar(), expected=expected)
    assert value["status"] == "unavailable"
    assert "expected_session_unavailable" in value["reason_codes"]


def test_friday_can_be_current_on_weekend_without_fake_weekend_observation():
    value = project(radar())
    assert value["source_session"] == SESSION
    assert "generated_at" not in value and "observed_at" not in value


@pytest.mark.parametrize("state", [None, "Mixed", "RISK_OFF", "", 80, False])
def test_unknown_state_does_not_get_promoted_or_default_to_calm(state):
    value = project(radar(state))
    assert value["status"] == "unavailable"
    assert "invalid_state" in value["reason_codes"]


def test_foreign_and_unscoped_international_sources_are_refused():
    assert project(radar(market="cn"), market="hk")["status"] == "unavailable"
    assert project(radar(), market="cn")["status"] == "unavailable"
    source = radar(market="cn")
    del source["market"]
    assert project(source, market="cn")["status"] == "unavailable"


def test_us_explicit_foreign_market_is_refused():
    source = radar()
    source["market"] = "cn"
    assert project(source)["status"] == "unavailable"


def test_unknown_schema_is_not_guessed():
    source = radar()
    source["schema"] = "some_other_score.v1"
    assert project(source)["status"] == "unavailable"


def test_current_artifact_does_not_launder_stale_underlying_inputs():
    value = project(radar(), input_quality={"any_input_stale": True,
                                          "worst_input_age_days": 86})
    assert value["status"] == "current"
    assert value["attention"] == "warning"
    assert value["artifact_freshness"] == "current"
    assert value["underlying_input_status"] == "degraded"
    assert value["underlying_input_details"]["worst_input_age_days"] == 86
    assert "underlying_inputs_stale" in value["reason_codes"]


def test_absent_quality_receipt_is_unknown_not_all_inputs_fresh():
    assert project(radar())["underlying_input_status"] == "unknown"


def test_malformed_quality_receipt_is_not_an_all_fresh_claim():
    value = project(radar(), input_quality={"any_input_stale": "false"})
    assert value["underlying_input_status"] == "unknown"
    assert "invalid_input_quality" in value["reason_codes"]


def test_identity_is_market_session_state_bound_and_repeatable():
    one = project(radar())
    assert one == project(radar())
    assert one["id"] != project(radar("elevated"))["id"]
    assert one["id"] != project(radar(market="cn"), market="cn")["id"]


def test_projection_does_not_mutate_or_retain_source_objects():
    source = radar()
    source["scares"] = [{"score": 99}]
    original = deepcopy(source)
    value = project(source)
    assert source == original
    value["reason_codes"].append("mutated")
    assert source == original


def test_calm_does_not_call_a_bottom_or_authorize_reentry():
    value = project(radar("calm", 0))
    assert value["recovery"]["assessed"] is False
    assert value["recovery"]["reentry_authorized"] is False


def test_unverifiable_refresh_retains_prior_critical_as_last_known_not_current():
    previous = project(radar("risk-off", 99))
    current = project(None)
    value = api().retain_unresolved_warning(current, previous)
    assert value["status"] == "unverified"
    assert value["attention"] == "critical"
    assert value["state"] is None
    assert value["last_known"]["state"] == "risk-off"
    assert value["last_known"]["source_session"] == SESSION
    assert current["status"] == "unavailable"  # no mutation


def test_repeated_missing_refresh_does_not_nest_history_or_erase_last_known():
    previous = project(radar("risk-off", 99))
    for _ in range(100):
        previous = api().retain_unresolved_warning(project(None), previous)
    assert previous["attention"] == "critical"
    assert "last_known" not in previous["last_known"]
    assert len(json.dumps(previous)) < 5000


def test_previous_other_market_or_fabricated_severity_cannot_contaminate_scope():
    prior = project(radar("risk-off", market="cn"), market="cn")
    assert api().retain_unresolved_warning(project(None), prior)["status"] == "unavailable"
    prior = project(radar("calm"))
    prior["attention"] = "critical"
    assert api().retain_unresolved_warning(project(None), prior)["status"] == "unavailable"


def test_fresh_lower_state_replaces_warning_but_does_not_establish_recovery():
    previous = project(radar("risk-off"))
    value = api().retain_unresolved_warning(project(radar("calm", 0)), previous)
    assert value["status"] == "current" and value["attention"] == "none"
    assert value["recovery"]["reentry_authorized"] is False


def test_older_delivery_cannot_silently_clear_newer_critical():
    previous = project(radar("risk-off", session="2026-09-28"), expected="2026-09-28")
    older = project(radar("calm", 0))
    value = api().retain_unresolved_warning(older, previous)
    assert value["status"] == "unverified"
    assert value["attention"] == "critical"
    assert "out_of_order_delivery" in value["reason_codes"]


def test_set_reports_expected_coverage_without_averaging_or_hiding_missing_markets():
    snapshots = {"us": radar(), "cn": radar("risk-off", 99, "cn")}
    value = api().project_warning_set(snapshots, {"us": SESSION, "cn": SESSION, "hk": SESSION})
    assert [row["market"] for row in value["rows"]] == ["cn", "us", "hk"]
    assert value["coverage"]["expected"] == 3
    assert value["coverage"]["current"] == 2
    assert value["coverage"]["unavailable_markets"] == ["hk"]
    assert "score" not in value and "probability" not in value
    assert "all_clear" not in value
    json.dumps(value, allow_nan=False)


def test_set_counts_retained_warning_separately_from_current_critical():
    prev = {"cn": project(radar("risk-off", 99, "cn"), market="cn")}
    value = api().project_warning_set({}, {"cn": SESSION}, previous=prev)
    assert value["coverage"]["current"] == 0
    assert value["current_attention_counts"]["critical"] == 0
    assert value["last_known_severe_markets"] == ["cn"]
    assert value["rows"][0]["attention"] == "critical"


@pytest.mark.parametrize("expected", [{}, [], {"../bad": SESSION}, {"US": SESSION, "us": SESSION}])
def test_invalid_configuration_does_not_look_like_complete_safe_coverage(expected):
    with pytest.raises(ValueError):
        api().project_warning_set({}, expected)


@pytest.mark.parametrize("field", ["top_score", "input_age"])
def test_extreme_json_integer_cannot_crash_projection(field):
    source = radar()
    quality = None
    if field == "top_score":
        source[field] = 10 ** 1000
    else:
        quality = {"any_input_stale": True, "worst_input_age_days": 10 ** 1000}
    value = project(source, input_quality=quality)
    json.dumps(value, allow_nan=False)
    assert value["score"] is None if field == "top_score" else value["underlying_input_status"] == "degraded"


@pytest.mark.parametrize("bad_id", [None, 99, [], "rw-cn-fake-risk-off"])
def test_malformed_cached_identity_never_crashes_or_manufactures_last_known(bad_id):
    previous = project(radar("risk-off"))
    previous["id"] = bad_id
    value = api().retain_unresolved_warning(project(None), previous)
    assert value["status"] == "unavailable"


def test_missing_cached_identity_is_not_accepted():
    previous = project(radar("risk-off"))
    del previous["id"]
    assert api().retain_unresolved_warning(project(None), previous)["status"] == "unavailable"


def test_case_normalization_applies_to_previous_and_quality_receipts_too():
    previous = {"CN": project(radar("risk-off", 99, "cn"), market="cn")}
    value = api().project_warning_set({}, {"CN": SESSION}, previous=previous)
    assert value["last_known_severe_markets"] == ["cn"]
    value = api().project_warning_set({"US": radar()}, {"US": SESSION},
                                    input_qualities={"US": {"any_input_stale": True}})
    assert value["rows"][0]["underlying_input_status"] == "degraded"
