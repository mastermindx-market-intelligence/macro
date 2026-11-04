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
            "observation_convention": "end_of_period", "first_observed_at": "2026-10-01T12:00:00+00:00",
            "comparison_observation_date": "2026-09-30"}
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
    assert {r["cc"] for r in base["policy_decisions"]} == {"JP", "KR", "TW", "IN", "AU", "GB", "EZ"}


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


def baseline_policy(cc):
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    return deepcopy(next(row for row in base["policy_decisions"] if row["cc"] == cc))


def test_seven_bank_settings_have_independent_effective_dates():
    expected = {
        "JP": ("uncollateralized_overnight_call_rate_target", 1.0, 1.25, "2026-09-24"),
        "KR": ("bok_base_rate", 2.75, 3.0, "2026-08-27"),
        "AU": ("cash_rate_target", 4.35, 4.6, "2026-09-30"),
        "EZ": ("deposit_facility_rate", 2.25, 2.5, "2026-09-16"),
        "IN": ("policy_repo_rate", 5.25, 5.5, "2026-10-07"),
    }
    for cc, fields in expected.items():
        raw = baseline_policy(cc)
        result = select_policy_decision([raw], cc, today=date(2026, 10, 19))
        assert result["current"]
        assert tuple(result[k] for k in ("instrument", "previous_value", "value", "effective_date")) == fields
        assert result["action"] == "increase" and result["change_pp"] == 0.25
        assert result["last_change_date"] == fields[-1]
        assert result["supporting_sources"]
        assert all(s["retrieved_at"] <= result["first_observed_at"] for s in result["supporting_sources"])


def test_new_evidence_does_not_leak_into_an_earlier_operational_replay():
    for cc in ("JP", "KR", "AU", "EZ", "IN"):
        assert select_policy_decision([baseline_policy(cc)], cc,
                                     operational_as_of="2026-10-18T23:59:59+00:00") is None
    assert baseline_policy("GB")["record_id"] == "GB:bank_rate:1acacb67d1c6b4a2fb4242ee"
    assert baseline_policy("TW")["record_id"] == "TW:discount_rate:6d770222a2dc6ffad23b01a0"


def test_rate_votes_are_not_stance_votes_or_attendance_counts():
    assert baseline_policy("IN")["votes"] == {"hold": 0, "increase": 6, "decrease": 0}
    assert "two separately opposed" in baseline_policy("IN")["rationale_en"]
    assert baseline_policy("KR")["votes"] == {"hold": 1, "increase": 6, "decrease": 0}
    assert baseline_policy("JP")["votes"] is None
    assert "7–2" in baseline_policy("JP")["rationale_en"]
    for cc in ("AU", "EZ"):
        assert baseline_policy(cc)["votes"] is None
        assert "unanimous" in baseline_policy(cc)["rationale_en"].lower()


def test_approximate_target_cannot_become_an_exact_setting():
    jp = baseline_policy("JP")
    assert normalize_policy_decision(jp)["setting_qualifier_en"] == "Around"
    jp.pop("setting_qualifier")
    assert normalize_policy_decision(jp) is None
    gb = baseline_policy("GB")
    gb["setting_qualifier"] = "around"
    assert normalize_policy_decision(gb) is None


def test_realized_overnight_rate_does_not_contradict_an_approximate_target():
    jp = baseline_policy("JP")
    observation = {"value": 1.247, "period": "2026-09", "instrument": jp["instrument"],
                   "observation_convention": "end_of_period",
                   "first_observed_at": "2026-10-01T00:00:00+00:00"}
    assert select_policy_decision([jp], "JP", today=date(2026, 10, 19), monthly=observation)["current"]
    observation.update(setting_qualifier="around", value=0.5,
                       comparison_observation_date="2026-09-30")
    assert select_policy_decision([jp], "JP", today=date(2026, 10, 19), monthly=observation)["state"] == "conflict"


@pytest.mark.parametrize("change", [
    {"source_url": "https://www.rba.gov.au.attacker.example/rates"},
    {"roles": ["votes"]}, {"roles": ["effective_date", []]},
    {"roles": ["effective_date", "effective_date"]},
    {"source_sha256": "not-a-digest"}, {"label": "unregistered"},
    {"retrieved_at": "2099-01-01T00:00:00+00:00"},
])
def test_supporting_source_identity_roles_and_clocks_are_required(change):
    item = baseline_policy("AU")
    item["supporting_sources"][0].update(change)
    assert normalize_policy_decision(item) is None


def test_missing_raw_or_supporting_proof_cannot_qualify_new_instruments():
    for cc in ("JP", "KR", "AU", "EZ", "IN"):
        item = baseline_policy(cc)
        item.pop("supporting_sources")
        assert normalize_policy_decision(item) is None
        item = baseline_policy(cc)
        item.pop("source_sha256")
        assert normalize_policy_decision(item) is None


def test_previous_setting_evidence_can_predate_the_new_decision():
    item = baseline_policy("JP")
    item["supporting_sources"][0]["retrieved_at"] = "2026-09-17T12:00:00+00:00"
    item["supporting_sources"][0]["source_url"] = "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260731a.pdf"
    assert normalize_policy_decision(item) is not None


def test_reviewed_body_detects_corrections_but_ignores_navigation(monkeypatch):
    from hashlib import sha256
    from collectors import intl_policy_sources as parser
    body = "Test decision Rate unchanged; reasoning reviewed End"
    monkeypatch.setitem(parser.REVIEWED_BODIES, "AU", ("Test decision", "End", sha256(body.encode()).hexdigest()))
    assert parser._reviewed_body("New navigation " + body + " New footer", "AU") == body
    with pytest.raises(ValueError, match="body_changed"):
        parser._reviewed_body(body.replace("reviewed", "contradicted"), "AU")
    with pytest.raises(ValueError, match="ambiguous"):
        parser._reviewed_body(body + " " + body, "AU")


def test_pdf_correction_requires_a_new_source_review():
    from collectors import intl_policy_sources as parser
    with pytest.raises(ValueError, match="reviewed_pdf_changed"):
        parser._document_text(b"%PDF-1.7 unreviewed bytes", parser.BOJ_URL)


def test_failed_supporting_download_isolated_to_one_bank(monkeypatch):
    from collectors import intl_policy_sources as parser
    boe = RELEASES[0]
    rba = next(r for r in RELEASES if r["cc"] == "AU")
    monkeypatch.setattr(parser, "RELEASES", (boe, rba))
    html = b"""<p>Published on 17 September 2026</p>
      <p>At its meeting ending on 16 September 2026, the MPC voted by a majority of 6-3 to maintain Bank Rate at 3.75%.</p>
      <p>Three members voted to increase Bank Rate by 0.25 percentage points, to 4%.</p>
      <p>soft labour market conditions; second-round effects</p>"""
    def fetch(url, *, max_bytes):
        assert max_bytes == 4_000_000
        if url == parser.BOE_URL:
            return html
        if url == parser.RBA_URL:
            return b"<p>downloaded, not yet qualified</p>"
        raise TimeoutError("supporting history unavailable")
    result = parser.collect_registered_policy(fetch, retrieved_at="2026-10-19T10:00:00+00:00")
    assert [r["cc"] for r in result["policy_decisions"]] == ["GB"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["failed_url"] == parser.RBA_HISTORY_URL
    assert result["errors"][0]["status"] == "release_not_verified"



def review_event(item, status, observed):
    return {**{k: item[k] for k in ("cc", "instrument", "provider", "source_url", "decision_date", "published", "source_sha256")},
            "schema": "intl_policy_review.v1", "status": status, "observed_at": observed,
            "record_id": item["record_id"] if status == "verified" else None}


def test_detected_source_change_withdraws_current_status_only_after_observation():
    item = baseline_policy("AU")
    changed = review_event(item, "review_required", "2026-10-19T10:00:00+00:00")
    before = select_policy_decision([item], "AU", review_events=[changed],
                                   operational_as_of="2026-10-19T09:59:59+00:00")
    after = select_policy_decision([item], "AU", review_events=[changed],
                                  operational_as_of="2026-10-19T10:00:01+00:00")
    assert before["current"]
    assert after["state"] == "review_required" and not after["current"]
    assert after["record_id"] == item["record_id"]
    assert after["first_observed_at"] == item["first_observed_at"]


def test_source_requalification_restores_the_same_record_without_rewriting_history():
    item = baseline_policy("AU")
    events = [review_event(item, "review_required", "2026-10-19T10:00:00+00:00"),
              review_event(item, "verified", "2026-10-19T10:05:00+00:00")]
    assert select_policy_decision([item], "AU", review_events=events,
                                  operational_as_of="2026-10-19T10:04:00+00:00")["state"] == "review_required"
    assert select_policy_decision([item], "AU", review_events=events,
                                  operational_as_of="2026-10-19T10:06:00+00:00")["current"]
    events[-1]["record_id"] = "AU:cash_rate_target:" + "0" * 24
    assert not select_policy_decision([item], "AU", review_events=events,
                                     operational_as_of="2026-10-19T10:06:00+00:00")["current"]


def test_review_events_cannot_be_backdated_by_an_incoming_collector():
    from lib.intl_policy_evidence import merge_policy_reviews
    item = baseline_policy("AU")
    old_claim = review_event(item, "review_required", "2026-09-30T00:00:00+00:00")
    events = merge_policy_reviews([], [old_claim], observed_at="2026-10-19T12:00:00+00:00")
    assert events[0]["observed_at"] == "2026-10-19T12:00:00+00:00"
    assert select_policy_decision([item], "AU", review_events=events,
                                  operational_as_of="2026-10-19T11:59:59+00:00")["current"]


def test_qualification_history_compacts_repeats_without_losing_transitions():
    from lib.intl_policy_evidence import merge_policy_reviews
    item = baseline_policy("AU")
    events = [review_event(item, "verified", f"2026-10-19T10:00:{second:02d}+00:00") for second in range(50)]
    events += [review_event(item, "review_required", "2026-10-19T10:01:00+00:00"),
               review_event(item, "verified", "2026-10-19T10:02:00+00:00")]
    merged = merge_policy_reviews([], events, preserve_custody=True)
    assert [event["status"] for event in merged] == ["verified", "review_required", "verified"]
    assert merged[0]["observed_at"] == events[0]["observed_at"]


def test_same_instant_failed_qualification_wins_independent_of_arrival():
    from lib.intl_policy_evidence import merge_policy_reviews
    item = baseline_policy("AU")
    events = [review_event(item, status, "2026-10-19T10:00:00+00:00")
              for status in ("verified", "review_required")]
    for incoming in (events, list(reversed(events))):
        merged = merge_policy_reviews([], incoming, preserve_custody=True)
        result = select_policy_decision([item], "AU", review_events=merged,
                                        operational_as_of="2026-10-19T10:01:00+00:00")
        assert result["state"] == "review_required"


def test_cached_qualification_clocks_survive_repeated_page_reads(tmp_path):
    from lib.intl_country_inputs import load_country_inputs
    item = baseline_policy("AU")
    config = tmp_path / "config"
    data = tmp_path / "data" / "intl_macro"
    config.mkdir()
    data.mkdir(parents=True)
    (config / "intl_country_baseline.json").write_text(json.dumps({"schema": SCHEMA}))
    event = review_event(item, "review_required", "2026-10-19T10:00:00+00:00")
    (data / "country_inputs.json").write_text(json.dumps(
        {"schema": SCHEMA, "policy_decisions": [item], "policy_reviews": [event]}))
    for _ in range(2):
        result = load_country_inputs(tmp_path / "data", tmp_path)
        assert result["policy_decisions"][0]["first_observed_at"] == item["first_observed_at"]
        assert result["policy_reviews"][0]["observed_at"] == event["observed_at"]


def test_primary_qualification_failure_is_not_attributed_to_a_support_download(monkeypatch):
    from collectors import intl_policy_sources as parser
    rba = next(r for r in parser.RELEASES if r["cc"] == "AU")
    monkeypatch.setattr(parser, "RELEASES", (rba,))
    source = b"<p>The announcement content requires another review.</p>"
    history = b"<p>Effective Date Change % points Cash rate target % Related Documents 30 Sep 2026 +0.25 4.60 Statement Minutes 12 Aug 2026 0.00 4.35</p>"
    result = parser.collect_registered_policy(
        lambda url, **kwargs: source if url == parser.RBA_URL else history,
        retrieved_at="2026-10-19T10:00:00+00:00")
    assert not result["policy_decisions"]
    assert result["errors"][0]["stage"] == "qualification"
    assert "failed_url" not in result["errors"][0]
    assert result["policy_reviews"][0]["status"] == "review_required"
    old = baseline_policy("AU")
    assert select_policy_decision([old], "AU", review_events=result["policy_reviews"],
                                  operational_as_of="2026-10-19T10:01:00+00:00")["state"] == "review_required"


def future_bank_rate():
    return normalize_policy_decision(raw(
        value=4.0, previous_value=3.75, action="increase", decision_date="2026-10-15",
        published="2026-10-15", effective_date="2026-11-01", last_change_date="2026-11-01",
        first_observed_at="2026-10-18T12:00:00+00:00", source_sha256="a" * 64))


def test_future_announcement_does_not_restore_withdrawn_effective_decision():
    current = normalize_policy_decision(raw(source_sha256="b" * 64))
    future = future_bank_rate()
    events = [review_event(current, "review_required", "2026-10-19T10:00:00+00:00"),
              review_event(future, "verified", "2026-10-19T10:05:00+00:00")]
    result = select_policy_decision([current, future], "GB", review_events=events,
                                    operational_as_of="2026-10-19T10:06:00+00:00")
    assert result["record_id"] == current["record_id"]
    assert result["state"] == "review_required" and not result["current"]
    assert result["announced"]["record_id"] == future["record_id"]
    assert result["announced"]["state"] == "announced"
    effective = select_policy_decision([current, future], "GB", review_events=events,
                                       operational_as_of="2026-11-01T12:00:00+00:00")
    assert effective["record_id"] == future["record_id"] and effective["current"]


def test_announcement_requires_its_own_qualification():
    current = normalize_policy_decision(raw(source_sha256="b" * 64))
    future = future_bank_rate()
    events = [review_event(future, "review_required", "2026-10-19T10:00:00+00:00")]
    result = select_policy_decision([current, future], "GB", review_events=events,
                                    operational_as_of="2026-10-19T10:01:00+00:00")
    assert not result["current"]
    assert result["announced"]["state"] == "review_required"
    assert not result["announced"]["current"]


def test_custody_reconstruction_keeps_the_earliest_complete_record():
    early = baseline_policy("AU")
    later = deepcopy(early)
    later["first_observed_at"] = "2026-10-19T10:30:00+00:00"
    later["source_sha256"] = "d" * 64
    for support in later["supporting_sources"]:
        support["source_sha256"] = "e" * 64
        support["retrieved_at"] = "2026-10-19T10:20:00+00:00"
    for baseline, refreshed in ((later, early), (early, later)):
        merged = merge_policy_decisions([baseline], [refreshed], preserve_custody=True)
        assert len(merged) == 1
        assert merged[0]["first_observed_at"] == early["first_observed_at"]
        assert merged[0]["source_sha256"] == early["source_sha256"]
        assert merged[0]["supporting_sources"] == early["supporting_sources"]
        assert select_policy_decision(merged, "AU",
                   operational_as_of="2026-10-19T09:50:00+00:00")["current"]
    ingested = merge_policy_decisions([later], [early], observed_at="2026-10-19T12:00:00+00:00")
    assert ingested[0]["first_observed_at"] == later["first_observed_at"]


def test_first_qualification_failure_has_review_state_without_an_invented_rate():
    item = baseline_policy("AU")
    event = review_event(item, "review_required", "2026-10-19T10:00:00+00:00")
    assert select_policy_decision([], "AU", review_events=[event],
               operational_as_of="2026-10-19T09:59:59+00:00") is None
    result = select_policy_decision([], "AU", review_events=[event],
                                    operational_as_of="2026-10-19T10:01:00+00:00")
    assert result is not None and result["state"] == "review_required"
    assert result["record_id"] is None and not result["current"]
    assert "value" not in result and "rationale_en" not in result


def test_other_release_url_cannot_restore_a_withdrawn_source():
    one = normalize_policy_decision(raw(source_sha256="b" * 64))
    two = normalize_policy_decision(raw(source_sha256="c" * 64,
                        source_url="https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/september-reviewed-copy"))
    before = select_policy_decision([one, two], "GB", operational_as_of="2026-10-19T10:00:00+00:00")
    selected_record = next(r for r in (one, two) if r["record_id"] == before["record_id"])
    other = next(r for r in (one, two) if r["record_id"] != before["record_id"])
    events = [review_event(selected_record, "review_required", "2026-10-19T10:01:00+00:00"),
              review_event(other, "verified", "2026-10-19T10:02:00+00:00")]
    after = select_policy_decision([one, two], "GB", review_events=events,
                                   operational_as_of="2026-10-19T10:03:00+00:00")
    assert after["state"] == "review_required" and not after["current"]


def bis_policy_observation(*, cc="GB", value=4.0, period="2026-09",
                           daily_date="2026-09-30", definition=None, retrieved_at=NOW, duplicate_definition=None):
    """Actual BIS CSV -> ZIP -> parser boundary, including source compilation."""
    import csv
    import io
    from zipfile import ZipFile
    from collectors.intl_country_sources import parse_bis
    baseline=json.loads((ROOT/"config/intl_country_baseline.json").read_text())
    definition=definition if definition is not None else baseline["official"][cc]["policy"]["definition"]
    area="XM" if cc=="EZ" else cc
    headers=["STRUCTURE_ID","FREQ:Frequency","REF_AREA:Reference area",
        "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value",
        "UNIT_MEASURE:Unit of measure","UNIT_MULT:Unit Multiplier",
        "OBS_CONF:Observation confidentiality","OBS_STATUS:Observation Status","COMPILATION:Compilation"]
    text=io.StringIO()
    writer=csv.writer(text)
    writer.writerow(headers)
    for freq,label in [("M",period)]+([("D",daily_date)] if daily_date is not None else []):
        writer.writerow(["BIS:WS_CBPOL(1.0):"+freq+"."+area,freq,area,label,
                         value,"368","0","F","A",definition])
    if duplicate_definition is not None:
        writer.writerow(["BIS:WS_CBPOL(1.0):M."+area,"M",area,period,
                         value,"368","0","F","A",duplicate_definition])
    data=io.BytesIO()
    with ZipFile(data,"w") as z:
        z.writestr("WS_CBPOL_csv_flat.csv",text.getvalue())
    return parse_bis(data.getvalue(),"policy",retrieved_at=retrieved_at)["observations"][cc]


def test_actual_bis_producer_connects_to_policy_conflict_guard():
    context=bis_policy_observation()
    assert context["instrument"]=="bank_rate"
    assert context["setting_qualifier"] is None
    assert context["observation_convention"]=="end_of_period"
    assert context["comparison_observation_date"]=="2026-09-30"
    assert context["daily_reference"]["value"]==4
    assert selected([raw()],monthly=context)["state"]=="conflict"


@pytest.mark.parametrize("cc,value,instrument,qualifier", [
    ("GB",3.75,"bank_rate",None),("AU",4.6,"cash_rate_target",None),
    ("KR",3.0,"bok_base_rate",None),("IN",5.25,"policy_repo_rate",None),
    ("EZ",2.5,"deposit_facility_rate",None),
    ("JP",1.25,"uncollateralized_overnight_call_rate_target","around"),
])
def test_bis_actual_compilation_defines_the_active_instrument(cc,value,instrument,qualifier):
    context=bis_policy_observation(cc=cc,value=value)
    assert context["comparison_qualification"]=="qualified"
    assert context["instrument"]==instrument and context["setting_qualifier"]==qualifier


@pytest.mark.parametrize("cc,period,definition", [
    ("AU","1990-05","From 2 Aug 1990 onwards: cash rate target; from 23 Jan 1990 to 1 Aug 1990: middle of the cash rate target range;"),
    ("EZ","2024-08","From 18 Sep 2024 onwards: official central bank steering rate is the deposit facility rate, fixed rate; from 15 Oct 2008 to 17 Sep 2024: official central bank liquidity providing, main refinancing operations, fixed rate;"),
    ("JP","2026-09","From 24 Sep 2026: the BOJ encourages the uncollateralized overnight call rate to remain at around 0 to 0.1 percent;"),
    ("GB","2026-09","From 1 Sep 2026 onwards: a new market rate; From 3 Aug 2006 onwards: official bank rate;"),
    ("GB","2026-09","From unknown 2026 onwards: a new market rate; From 3 Aug 2006 onwards: official bank rate;"),
    ("GB","2026-09","From 1 Sep 2026 to 15 Sep 2026: a temporary market rate; From 3 Aug 2006 onwards: official bank rate;"),
])
def test_bis_never_aliases_ranges_historic_or_unknown_newer_instruments(cc,period,definition):
    from calendar import monthrange
    y,m=map(int,period.split("-"))
    context=bis_policy_observation(cc=cc,period=period,
        daily_date=f"{period}-{monthrange(y,m)[1]:02d}",definition=definition)
    assert context["comparison_qualification"]!="qualified"
    assert "instrument" not in context


def test_bis_japan_definition_target_must_match_the_actual_point():
    context=bis_policy_observation(cc="JP",value=9.0)
    assert context["comparison_qualification"]=="definition_value_disagreement"
    assert "instrument" not in context


@pytest.mark.parametrize("changes", [
    {"source_sha256":None},{"series_id":"M.AU"},{"dataset_url":"https://example.com/data"},
    {"source_url":"https://example.com/policy"},{"unit":"percent"},
    {"first_observed_at":"2099-10-18T12:00:00Z"},{"retrieved_at":None},
    {"frequency":"daily"},{"status":"estimated"},
])
def test_bis_comparability_cannot_be_supplied_by_a_wrong_source_shape(changes):
    from lib.intl_policy_evidence import qualify_bis_monthly_policy
    context=bis_policy_observation()
    context.update(changes)
    if "retrieved_at" in changes:
        context.pop("first_observed_at",None)
    assert qualify_bis_monthly_policy(context,"GB",today=TODAY)["comparison_qualification"]!="qualified"


def test_bis_daily_corroboration_must_agree_with_the_monthly_source():
    from lib.intl_policy_evidence import qualify_bis_monthly_policy
    original=bis_policy_observation()
    for changes in ({"value":9.},{"date":"2026-10-01"},{"source_sha256":"0"*64},
                    {"series_id":"D.AU"},{"definition":"From 1 Sep 2026: other rate;"}):
        context=deepcopy(original)
        context["daily_reference"].update(changes)
        assert qualify_bis_monthly_policy(context,"GB",today=TODAY)["comparison_qualification"]!="qualified"


def test_monthly_without_exact_day_cannot_conflict_with_a_within_month_change():
    context=bis_policy_observation(daily_date=None)
    assert context["comparison_qualification"]=="qualified"
    assert context["comparison_observation_date"] is None
    assert selected([raw()],monthly=context)["current"]
    older=raw(decision_date="2026-08-20",published="2026-08-20",
              effective_date="2026-08-20",first_observed_at="2026-08-20T12:00:00Z")
    assert selected([older],monthly=context)["state"]=="conflict"


def test_final_weekend_effective_change_does_not_conflict_with_earlier_business_observation():
    context=bis_policy_observation(value=3.75,period="2026-05",daily_date="2026-05-29",
                                  retrieved_at="2026-06-01T12:00:00Z")
    change=raw(value=4.,previous_value=3.75,action="increase",decision_date="2026-05-28",
        published="2026-05-28",effective_date="2026-05-31",
        first_observed_at="2026-05-28T12:00:00Z")
    result=select_policy_decision([change],"GB",today=date(2026,6,1),monthly=context)
    assert result["current"] and result["value"]==4.


def test_policy_point_custody_survives_cache_replay_and_changes_only_with_new_content(monkeypatch):
    from datetime import datetime,timezone
    from collectors import intl_country_sources as owner
    context=bis_policy_observation()
    class Clock(datetime):
        instant="2026-10-18T13:00:00+00:00"
        @classmethod
        def now(cls,tz):
            return datetime.fromisoformat(cls.instant)
    monkeypatch.setattr(owner,"datetime",Clock)
    first=merge_country_inputs({"schema":SCHEMA},
        {"schema":SCHEMA,"official":{"GB":{"policy":context}}},today=TODAY)
    point=first["official"]["GB"]["policy"]
    assert point["first_observed_at"]==Clock.instant
    Clock.instant="2026-10-18T14:00:00+00:00"
    repeated=deepcopy(context)
    repeated["retrieved_at"]=Clock.instant
    repeated["source_sha256"]="d"*64
    repeated["daily_reference"]["source_sha256"]="d"*64
    same=merge_country_inputs(first,{"schema":SCHEMA,"official":{"GB":{"policy":repeated}}},today=TODAY)
    assert same["official"]["GB"]["policy"]==point
    Clock.instant="2026-10-18T15:00:00+00:00"
    changed=bis_policy_observation(value=4.25)
    changed["first_observed_at"]="2026-01-01T00:00:00Z"
    latest=merge_country_inputs(first,{"schema":SCHEMA,"official":{"GB":{"policy":changed}}},today=TODAY)
    fresh=latest["official"]["GB"]["policy"]
    assert fresh["first_observed_at"]==Clock.instant
    restored=merge_country_inputs({"schema":SCHEMA},latest,today=TODAY,preserve_custody=True)
    assert restored["official"]["GB"]["policy"]==fresh
    assert selected([raw()],monthly=fresh,operational_as_of="2026-10-18T14:30:00Z")["monthly_context"] is None
    reviewed=selected([raw()],monthly=fresh,operational_as_of="2026-10-18T15:30:00Z")
    assert fresh["comparison_qualification"]=="retained_conflict" and fresh["value"] is None
    assert reviewed["state"]=="verified" and reviewed["monthly_check"]=="review_required"
    assert {p["value"] for p in fresh["retained_contexts"]}=={4.,4.25}


def test_bis_duplicate_value_with_conflicting_compilation_is_rejected():
    with pytest.raises(ValueError,match="conflicting_bis_observation"):
        bis_policy_observation(duplicate_definition="From 1 Sep 2026: a different policy instrument;")


def merged_bis_context(a, b):
    def envelope(point):
        return {"schema":SCHEMA,"official":{"GB":{"policy":point}}} if point else {"schema":SCHEMA}
    return merge_country_inputs(envelope(a),envelope(b),today=date(2026,10,20),
                                preserve_custody=True)["official"]["GB"]["policy"]


def test_real_old_cache_cannot_erase_new_baseline_daily_proof():
    base=json.loads((ROOT/"config/intl_country_baseline.json").read_text())["official"]["GB"]["policy"]
    old=deepcopy(base)
    old.pop("daily_reference")
    old.update(retrieved_at="2026-10-18T03:33:39+00:00",first_observed_at="2026-10-18T03:33:39+00:00")
    for a,b in ((base,old),(old,base)):
        selected=merged_bis_context(a,b)
        assert selected == base
        assert selected["comparison_observation_date"]=="2026-09-30"


def test_identical_bis_proof_uses_earliest_complete_actual_custody():
    early=bis_policy_observation(retrieved_at="2026-10-19T08:00:00+00:00")
    early["first_observed_at"]="2026-10-19T08:05:00+00:00"
    late=deepcopy(early)
    late.update(retrieved_at="2026-10-20T09:00:00+00:00",first_observed_at="2026-10-20T09:05:00+00:00")
    for a,b in ((early,late),(late,early)):
        assert merged_bis_context(a,b)==early


def test_later_weaker_bis_copy_does_not_revoke_existing_daily_evidence():
    complete=bis_policy_observation(retrieved_at="2026-10-19T08:00:00+00:00")
    weak=bis_policy_observation(daily_date=None,retrieved_at="2026-10-20T09:00:00+00:00")
    for a,b in ((complete,weak),(weak,complete)):
        assert merged_bis_context(a,b)==complete


def test_bis_proof_enrichment_never_borrows_the_old_knowledge_clock():
    weak=bis_policy_observation(daily_date=None,retrieved_at="2026-10-18T12:00:00+00:00")
    complete=bis_policy_observation(retrieved_at="2026-10-20T09:00:00+00:00")
    complete["first_observed_at"]="2026-10-20T09:05:00+00:00"
    merged=merged_bis_context(weak,complete)
    assert merged == complete
    assert select_policy_decision([raw()],"GB",monthly=merged,
        operational_as_of="2026-10-20T09:04:59+00:00")["state"]=="verified"
    assert select_policy_decision([raw()],"GB",monthly=merged,
        operational_as_of="2026-10-20T09:05:00+00:00")["state"]=="conflict"


@pytest.mark.parametrize("different",["value","definition","daily_disagreement"])
def test_bis_same_period_collision_survives_both_archive_orders(different):
    first=bis_policy_observation(value=3.75,retrieved_at="2026-10-19T08:00:00+00:00")
    if different=="value":
        second=bis_policy_observation(value=4.,retrieved_at="2026-10-20T09:00:00+00:00")
    else:
        second=deepcopy(first)
        second.update(retrieved_at="2026-10-20T09:00:00+00:00",first_observed_at="2026-10-20T09:05:00+00:00")
        if different=="definition":
            second["definition"]="From 1 Sep 2026: a different instrument;"
        else:
            second["daily_reference"]["value"]=4.
    collision=merged_bis_context(first,second)
    assert collision["comparison_qualification"]=="retained_conflict" and collision["value"] is None
    assert len(collision["retained_contexts"])==2
    assert merged_bis_context(second,first)==collision
    assert merged_bis_context(collision,first)==collision
    assert merged_bis_context(first,collision)==collision
    decision=select_policy_decision([raw()],"GB",monthly=collision,
        operational_as_of="2026-10-20T10:00:00+00:00")
    assert decision["state"]=="verified" and decision["current"]
    assert decision["monthly_check"]=="review_required"
    assert decision["monthly_context"] is None


def test_new_policy_reference_month_is_progression_not_collision():
    old=bis_policy_observation(value=4.,period="2026-08",daily_date="2026-08-31")
    new=bis_policy_observation(value=3.75)
    assert merged_bis_context(old,new)==new
    assert merged_bis_context(new,old)==new


def test_bis_custody_cannot_predate_the_evidence_it_contains():
    from lib.intl_policy_evidence import qualify_bis_monthly_policy
    record=bis_policy_observation(retrieved_at="2026-10-20T09:00:00+00:00")
    record["first_observed_at"]="2026-10-19T09:00:00+00:00"
    assert qualify_bis_monthly_policy(record,"GB",today=date(2026,10,20))["comparison_qualification"]=="unqualified_source"


@pytest.mark.parametrize("reserved", ["retained_contexts","schema"])
def test_live_policy_input_cannot_smuggle_retained_custody(reserved):
    old=bis_policy_observation()
    wrapped=deepcopy(old)
    wrapped["retained_contexts"]=[old]
    if reserved=="schema":
        wrapped["schema"]="intl_bis_monthly_context_conflict.v1"
    merged=merge_country_inputs({"schema":SCHEMA},
        {"schema":SCHEMA,"official":{"GB":{"policy":wrapped}}},today=date(2026,10,20))
    assert not merged["official"]["GB"].get("policy")
