"""Economic integrity cases for versioned outlooks and October table ingestion."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from lib.intl_forecast_vintages import (
    normalize_publication, merge_publications, select_publications, publication_view,
)
from collectors.intl_weo import parse_weo_table_texts, WEO_OCTOBER_2026
from lib.intl_country_outlook import build_country_outlook

NOW = "2026-10-18T12:00:00+00:00"
TODAY = date(2026, 10, 18)
ROOT = Path(__file__).resolve().parents[1]


def raw(**changes):
    value = {"cc": "KR", "provider": "IMF", "family": "WEO", "edition": "2026-10",
             "published": "2026-10-13", "kind": "sourced_forecast",
             "source_url": "https://www.imf.org/en/Publications/WEO",
             "unit": "percent", "period_basis": "calendar_year",
             "values": {"2026": 3.3, "2027": 2.8}}
    value.update(changes)
    return value


def admit(items, previous=None, now=NOW):
    return merge_publications(previous or [], items, observed_at=now)[0]


def chosen(archive, **kwargs):
    return select_publications(archive, "KR", today=TODAY, **kwargs)[0]


def test_october_replaces_july_without_erasing_the_comparison():
    july = raw(edition="2026-07", published="2026-07-08", values={"2026": 2.6, "2027": 2.5})
    archive = admit([raw()], admit([july], now="2026-07-08T12:00:00+00:00"))
    view = publication_view(chosen(archive), archive, today=TODAY)
    assert len(archive) == 2
    assert view["revision"] == 0.7 and view["revision_from"] == "2026-07"
    assert view["revisions"]["2027"]["delta_pp"] == 0.3
    assert view["change"] == -0.5


def test_same_date_provider_preference_is_independent_of_arrival():
    national = raw(provider="DGBAS", family="National accounts",
                   source_url="https://eng.dgbas.gov.tw/release", values={"2026": 4.0, "2027": 3.0})
    for records in ([raw(), national], [national, raw()]):
        archive = admit(records)
        assert len(archive) == 2 and chosen(archive)["provider"] == "IMF"


def test_provider_change_is_an_alternative_not_a_revision():
    national = raw(cc="TW", provider="DGBAS", family="National accounts", edition="2026-08-14",
                   published="2026-08-14", source_url="https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587",
                   values={"2026": 11.05, "2027": 6.04})
    archive = admit([national, raw(cc="TW", values={"2026": 10.7, "2027": 4.3})])
    outlook = build_country_outlook("TW", archive, today=TODAY)
    assert outlook["series"]["real_gdp_growth"]["revision"] is None
    assert outlook["alternatives"][0]["provider"] == "DGBAS"


def test_partial_release_keeps_an_omitted_country():
    archive = admit([raw(cc="JP")], admit([raw()]))
    assert chosen(archive)["cc"] == "KR"


def test_one_relevant_period_survives_january_rollover():
    archive = admit([raw()])
    selection = select_publications(archive, "KR", today=date(2027, 1, 2))
    view = publication_view(selection[0], archive, today=date(2027, 1, 2))
    assert view["year"] == 2027 and view["current"] == 2.8
    assert view["next"] is None and view["change"] is None
    assert view["coverage"] == "one_period"


def test_future_only_period_is_labelled_as_future():
    archive = admit([raw(values={"2027": 2.8})])
    view = publication_view(chosen(archive), archive, today=TODAY)
    assert view["year"] == 2027 and view["is_active_period"] is False


def test_distant_future_only_release_cannot_displace_current_coverage():
    old = raw(published="2026-07-08", edition="2026-07")
    archive = admit([raw(values={"2031": 4.0})], admit([old]))
    assert chosen(archive)["edition"] == "2026-07"


def test_fiscal_year_does_not_roll_on_january_first():
    archive = admit([raw(cc="IN", period_basis="fiscal_year", fiscal_start_month=4,
                         values={"2026": 7.0, "2027": 6.9})])
    selection = select_publications(archive, "IN", today=date(2027, 1, 2))
    view = publication_view(selection[0], archive, today=date(2027, 1, 2))
    assert view["year_label"] == "FY2026/27"
    assert view["current_period"]["end"] == "2027-03-31"
    assert view["next_label"] == "FY2027/28"


def test_reported_revision_remains_on_its_original_target_year():
    archive = admit([raw(revision_current_pp=0.7, revision_from="2026-04")])
    view = publication_view(archive[0], archive, today=date(2027, 1, 1))
    assert view["year"] == 2027 and view["revision"] is None
    assert archive[0]["reported_revisions"]["2026"]["delta_pp"] == 0.7


def test_same_release_conflict_retains_accepted_custody():
    original = admit([raw()])
    archive = admit([raw(values={"2026": 9.0, "2027": 8.0})], original)
    assert chosen(archive)["values"]["2026"] == 3.3
    assert sum(r["admission_status"] == "conflict" for r in archive) == 1


def test_empty_archive_conflict_has_no_arrival_order_winner():
    a, b = raw(), raw(values={"2026": 9.0, "2027": 8.0})
    for batch in ([a, b], [b, a]):
        archive = admit(batch)
        assert len(archive) == 2 and not select_publications(archive, "KR", today=TODAY)
        assert all(r["admission_status"] == "conflict" for r in archive)


def test_held_conflict_can_later_become_a_verified_correction():
    original = admit([raw()], now="2026-10-13T12:00:00+00:00")
    candidate = raw(values={"2026": 3.4, "2027": 2.9})
    conflicted = admit([candidate], original, now="2026-10-15T12:00:00+00:00")
    corrected = {**candidate, "correction_sequence": 1,
                 "supersedes_record_id": original[0]["record_id"],
                 "correction_source_url": "https://www.imf.org/en/correction"}
    archive = admit([corrected], conflicted)
    assert len(archive) == 3 and chosen(archive)["values"]["2026"] == 3.4
    earlier = select_publications(archive, "KR", operational_as_of="2026-10-16T12:00:00+00:00")
    assert earlier[0]["values"]["2026"] == 3.3


def test_two_conflicting_corrections_at_one_sequence_do_not_choose_a_winner():
    original = admit([raw()])
    common = {"correction_sequence": 1, "supersedes_record_id": original[0]["record_id"],
              "correction_source_url": "https://www.imf.org/en/correction"}
    archive = admit([raw(values={"2026": 3.4}, **common), raw(values={"2026": 3.5}, **common)], original)
    assert chosen(archive)["values"]["2026"] == 3.3


def test_withdrawal_is_applied_only_when_the_system_learned_it():
    archive = admit([raw()], now="2026-10-13T12:00:00+00:00")
    incoming = {**archive[0], "withdrawn_at": "2026-10-14T12:00:00+00:00",
                "withdrawal_source_url": "https://www.imf.org/en/withdrawal"}
    updated = admit([incoming], archive)
    assert not select_publications(updated, "KR", today=TODAY)
    assert select_publications(updated, "KR", operational_as_of="2026-10-15T12:00:00+00:00")
    assert updated[0]["withdrawal_admitted_at"] == NOW


def test_replay_derives_its_horizon_from_the_cutoff():
    archive = admit([raw()])
    selected = select_publications(archive, "KR", today=date(2027, 4, 1),
                                   operational_as_of="2026-12-15T12:00:00+00:00")
    view = publication_view(selected[0], archive, today=date(2027, 4, 1),
                            operational_as_of="2026-12-15T12:00:00+00:00")
    assert view["year"] == 2026 and view["next_year"] == 2027


def test_incoming_source_cannot_backdate_operational_knowledge():
    archive = admit([raw(retrieved_at=NOW, first_observed_at="2026-10-13", admitted_at="2026-10-13")])
    assert not select_publications(archive, "KR", operational_as_of="2026-10-14T12:00:00+00:00")
    assert archive[0]["admitted_at"] == NOW


def test_identical_refresh_preserves_first_admission():
    archive = admit([raw()])
    again = admit([raw()], archive, now="2026-10-20T12:00:00+00:00")
    assert again == archive


def test_changed_reported_revision_is_not_the_same_semantic_content():
    a = normalize_publication(raw(revision_current_pp=0.1, revision_from="2026-07"), observed_at=NOW)
    b = normalize_publication(raw(revision_current_pp=0.2, revision_from="2026-07"), observed_at=NOW)
    assert a["record_id"] != b["record_id"]


@pytest.mark.parametrize("changes", [
    {"values": {"2026": 2.0, 2027: 3.0}}, {"values": {"2199": 2.0}},
    {"cc": []}, {"provider": {}}, {"series_id": []},
    {"values": {"2026": True}}, {"values": {"2026": float("inf")}},
    {"values": {"2026": 10**500}}, {"values": {"2026": None}},
    {"revision_current_pp": 0.4, "revision_from": "2027-04"},
    {"withdrawn_at": "bad"}, {"precision": True},
])
def test_malformed_publication_is_isolated(changes):
    assert normalize_publication(raw(**changes), observed_at=NOW) is None
    previous = admit([raw()])
    assert admit([raw(**changes)], previous) == previous


def test_historical_values_need_source_actual_status():
    result = normalize_publication(raw(values={"2025": 1.1, "2026": 3.3}), observed_at=NOW)
    assert result["periods"][0]["status"] == "historical_unclassified"
    result = normalize_publication(raw(values={"2025": 1.1, "2026": 3.3}, actual_through=2025), observed_at=NOW)
    assert result["periods"][0]["status"] == "actual"


def test_negative_growth_is_contraction_and_positive_slowdown_is_not():
    inflation = raw(series_id="inflation_average", values={"2026": 3.0, "2027": 2.0})
    for growth, expected in (({"2026": 2.0, "2027": -0.5}, "Contraction"),
                             ({"2026": 3.0, "2027": 2.0}, "Growth cools")):
        archive = admit([raw(values=growth), inflation])
        assert build_country_outlook("KR", archive, today=TODAY)["title_en"].startswith(expected)


def test_missing_external_inputs_do_not_produce_a_resilience_claim():
    result = build_country_outlook("KR", admit([raw()]), today=TODAY)
    assert not result["balances"] and "current_account" in result["missing_series"]
    assert all(p["id"] != "KR:current_account" for p in result["propositions"])


def test_monthly_and_annual_inflation_can_move_differently():
    inflation = raw(series_id="inflation_average", values={"2026": 3.0, "2027": 2.0})
    metric = {"key": "inflation", "current": True, "change_3m_pp": 0.5, "value": 3.5,
              "period": "2026-09", "source_url": "https://data.bis.org/"}
    result = build_country_outlook("KR", admit([raw(), inflation]), today=TODAY, metrics=[metric])
    assert result["tension_en"]
    claim = next(p for p in result["propositions"] if p["id"] == "KR:inflation_horizons")
    assert claim["evidence"][-1]["period"] == "2026-09"


def fixture():
    return json.loads((ROOT/"tests/fixtures/intl_weo_october_2026_tables.json").read_text())


def test_actual_october_table_columns_and_country_scope():
    data = fixture()
    records = parse_weo_table_texts(data["tables"], release=WEO_OCTOBER_2026,
                                   retrieved_at=NOW, source_sha256=data["source_sha256"])
    by_key = {(r["cc"], r["series_id"]): r for r in records}
    assert len(records) == 28
    assert by_key["KR", "real_gdp_growth"]["values"]["2026"] == 3.3  # Not Q4/Q4 3.0
    assert by_key["KR", "inflation_average"]["values"]["2026"] == 2.7  # Not end-period 2.8
    assert by_key["EZ", "current_account"]["values"]["2026"] == 1.2  # Not unadjusted sum 2.1
    assert by_key["JP", "government_debt"]["values"]["2026"] == 199.4  # Not net debt 127.0
    assert by_key["IN", "inflation_average"]["periods"][0]["label"] == "FY2023/24"
    assert by_key["TW", "real_gdp_growth"]["values"]["2027"] == 4.3


@pytest.mark.parametrize("change", ["unit", "year", "columns"])
def test_pdf_schema_drift_cannot_silently_change_the_measure(change):
    data = fixture()
    if change == "unit":
        data["tables"]["A6"] = data["tables"]["A6"].replace("(Annual percent change)", "(Percent of GDP)")
    elif change == "year":
        data["tables"]["A6"] = data["tables"]["A6"].replace("2025 2026 2027 2031", "2025 2027 2026 2031")
    else:
        data["tables"]["A6"] = data["tables"]["A6"].replace("Korea 2.3 1.5", "Korea 2.3 9.9 1.5")
    with pytest.raises(ValueError, match="weo_"):
        parse_weo_table_texts(data["tables"], release=WEO_OCTOBER_2026,
                             retrieved_at=NOW, source_sha256=data["source_sha256"])
