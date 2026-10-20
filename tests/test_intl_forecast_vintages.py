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


def fiscal_fixture(indicator="GGXCNL_NGDP"):
    data = json.loads((ROOT / "tests/fixtures/intl_weo_october_2026_fiscal_api.json").read_text())
    return deepcopy(data["responses"][indicator])


def fiscal_parse(payload=None, indicator="GGXCNL_NGDP", **kwargs):
    from collectors.intl_weo import parse_weo_fiscal_datamapper, WEO_FISCAL_RELEASES
    release = deepcopy(next(r for r in WEO_FISCAL_RELEASES if r["indicator_id"] == indicator))
    return parse_weo_fiscal_datamapper(
        json.dumps(payload if payload is not None else fiscal_fixture(indicator)).encode(),
        release=release, retrieved_at=kwargs.get("retrieved_at", NOW))


def test_fiscal_api_projects_only_the_qualified_economies_and_periods():
    balances = {r["cc"]: r for r in fiscal_parse()}
    debt = {r["cc"]: r for r in fiscal_parse(indicator="GGXWDG_NGDP")}
    assert set(balances) == set(debt) == {"KR", "TW", "IN", "AU"}
    assert {cc: r["values"] for cc, r in balances.items()} == {
        "KR": {"2026": -1.3, "2027": 1.4}, "TW": {"2026": 0.3, "2027": 0.3},
        "IN": {"2026": -7.5, "2027": -7.2}, "AU": {"2026": -3.2, "2027": -3.0}}
    assert {cc: r["values"] for cc, r in debt.items()} == {
        "KR": {"2026": 47.3, "2027": 46.2}, "TW": {"2026": 21.1, "2027": 20.0},
        "IN": {"2026": 83.1, "2027": 81.3}, "AU": {"2026": 52.6, "2027": 53.2}}
    india = balances["IN"]["periods"][0]
    assert (india["label"], india["start"], india["end"]) == (
        "FY2026/27", "2026-04-01", "2027-03-31")
    assert balances["AU"]["periods"][0]["start"] == "2026-01-01"
    for r in [*balances.values(), *debt.values()]:
        assert r["family"] == "WEO" and r["information_cutoff"] == "2026-09-30"
        assert r["published"] == "2026-10-13" and r["actual_through"] is None
        assert all(p["status"] == "projection" for p in r["periods"])
        assert r["coverage_note_zh"] and len(r["source_sha256"]) == 64


@pytest.mark.parametrize("key,value", [
    ("source", "Fiscal Monitor (October 2026)"), ("source", "World Economic Outlook (April 2027)"),
    ("unit", "Billions of national currency"), ("dataset", "FM"),
    ("label", "General government net debt"), ("projection-year", 2025)])
def test_fiscal_api_rejects_a_different_edition_or_measure(key, value):
    p = fiscal_fixture()
    p["indicators"]["GGXCNL_NGDP"][key] = value
    with pytest.raises(ValueError, match="edition_or_unit"):
        fiscal_parse(p)


@pytest.mark.parametrize("value", [None, True, "0.3", float("nan"), float("inf"), [], -2001])
def test_fiscal_api_does_not_turn_invalid_cells_into_zero(value):
    p = fiscal_fixture()
    p["values"]["GGXCNL_NGDP"]["TWN"]["2027"] = value
    with pytest.raises(ValueError):
        fiscal_parse(p)


def test_fiscal_api_missing_year_or_economy_fails_qualification():
    for economy, year in [("IND", "2027"), ("KOR", None)]:
        p = fiscal_fixture()
        if year:
            p["values"]["GGXCNL_NGDP"][economy].pop(year)
        else:
            p["values"]["GGXCNL_NGDP"].pop(economy)
        with pytest.raises(ValueError):
            fiscal_parse(p)


def test_fiscal_api_rejects_duplicate_json_keys():
    from collectors.intl_weo import parse_weo_fiscal_datamapper, WEO_FISCAL_RELEASES
    payload = json.dumps(fiscal_fixture()).replace('"2026": -1.3', '"2026": 0, "2026": -1.3')
    with pytest.raises(ValueError, match="invalid_json"):
        parse_weo_fiscal_datamapper(payload.encode(), release=WEO_FISCAL_RELEASES[0], retrieved_at=NOW)


def test_failed_fiscal_source_preserves_accepted_country_data_and_other_source():
    from collectors.intl_weo import collect_registered_weo, WEO_FISCAL_RELEASES
    previous = admit(fiscal_parse() + fiscal_parse(indicator="GGXWDG_NGDP"))
    def fetch(url, **kwargs):
        if "/GGXCNL_NGDP/" in url:
            raise OSError("source unavailable")
        return json.dumps(fiscal_fixture("GGXWDG_NGDP")).encode()
    result = collect_registered_weo(fetch, releases=WEO_FISCAL_RELEASES, retrieved_at=NOW)
    assert len(result["errors"]) == 1 and len(result["forecast_archive"]) == 4
    merged, diagnostics = merge_publications(previous, result["forecast_archive"], observed_at=NOW)
    assert diagnostics == [] and merged == previous


def corrected_cutoff_archive():
    old = raw(information_cutoff="2026-10-01")
    original = admit([old])
    fix = {**old, "information_cutoff": "2026-09-30", "correction_sequence": 1,
           "supersedes_record_id": original[0]["record_id"],
           "correction_source_url": WEO_OCTOBER_2026["documentation_url"]}
    return old, admit([fix], original, now="2026-10-19T12:00:00+00:00")


def test_corrected_cutoff_keeps_old_replay_and_identical_refresh_custody():
    old, archive = corrected_cutoff_archive()
    before = select_publications(archive, "KR", operational_as_of=NOW)[0]
    after = select_publications(archive, "KR", operational_as_of="2026-10-19T13:00:00+00:00")[0]
    assert before["information_cutoff"] == "2026-10-01"
    assert after["information_cutoff"] == "2026-09-30"
    refresh = {**old, "information_cutoff": "2026-09-30"}
    merged, diagnostics = merge_publications(archive, [refresh], observed_at="2026-10-19T14:00:00+00:00")
    assert diagnostics == [] and merged == archive
    assert after["first_observed_at"] == "2026-10-19T12:00:00+00:00"


def test_refresh_withdrawal_keeps_real_corrected_identity_and_cannot_backdate():
    old, archive = corrected_cutoff_archive()
    withdrawal = {**old, "information_cutoff": "2026-09-30",
                  "withdrawn_at": "2026-10-19T12:30:00+00:00",
                  "withdrawal_source_url": WEO_OCTOBER_2026["source_url"]}
    merged, diagnostics = merge_publications(archive, [withdrawal], observed_at="2026-10-19T14:00:00+00:00")
    assert diagnostics == [] and len(merged) == 2
    corrected = next(r for r in merged if r["correction_sequence"] == 1)
    assert corrected["withdrawal_admitted_at"] == "2026-10-19T14:00:00+00:00"
    assert select_publications(merged, "KR", operational_as_of="2026-10-19T13:00:00+00:00")
    assert not select_publications(merged, "KR", operational_as_of="2026-10-19T15:00:00+00:00")


def test_stale_corrected_refresh_cannot_withdraw_newer_different_content():
    old, archive = corrected_cutoff_archive()
    predecessor = next(r for r in archive if r["correction_sequence"] == 1)
    second = {**predecessor, "values": {"2026": 2.0, "2027": 2.1}, "periods": [],
              "correction_sequence": 2, "supersedes_record_id": predecessor["record_id"]}
    archive = admit([second], archive, now="2026-10-19T14:00:00+00:00")
    stale = {**old, "information_cutoff": "2026-09-30",
             "withdrawn_at": "2026-10-19T14:30:00+00:00",
             "withdrawal_source_url": WEO_OCTOBER_2026["source_url"]}
    merged, diagnostics = merge_publications(archive, [stale], observed_at="2026-10-19T15:00:00+00:00")
    assert any(d["kind"] == "publication_conflict" for d in diagnostics)
    active = select_publications(merged, "KR", operational_as_of="2026-10-19T16:00:00+00:00")[0]
    assert active["correction_sequence"] == 2 and not active.get("withdrawn_at")


def test_fiscal_api_accepts_only_the_observed_unnamed_null_placeholder():
    p = fiscal_fixture()
    p["values"][""] = {"TWN": {"2027": 999}}
    with pytest.raises(ValueError, match="measure_changed"):
        fiscal_parse(p)


def test_corrected_refresh_does_not_create_a_synthetic_predecessor():
    old, archive = corrected_cutoff_archive()
    refresh = {**old, "information_cutoff": "2026-09-30"}
    synthetic = normalize_publication(refresh, observed_at=NOW)["record_id"]
    second = {**refresh, "values": {"2026": 2.0, "2027": 2.1},
              "correction_sequence": 2, "supersedes_record_id": synthetic,
              "correction_source_url": WEO_OCTOBER_2026["source_url"]}
    merged, diagnostics = merge_publications(archive, [refresh, second], observed_at="2026-10-19T15:00:00+00:00")
    assert any(d["kind"] == "publication_conflict" for d in diagnostics)
    assert all(r["record_id"] != synthetic for r in merged)
    assert select_publications(merged, "KR", operational_as_of="2026-10-19T16:00:00+00:00")[0]["correction_sequence"] == 1


@pytest.mark.parametrize("cc,phrase", [
    ("KR", "from deficit to surplus"), ("TW", "surplus is broadly unchanged"),
    ("IN", "deficit narrows"), ("AU", "deficit narrows")])
def test_fiscal_country_readings_describe_the_actual_published_path(cc, phrase):
    archive = admit(fiscal_parse() + fiscal_parse(indicator="GGXWDG_NGDP"))
    view = build_country_outlook(cc, archive, today=TODAY)
    b = next(r for r in view["balances"] if r["series_id"] == "fiscal_balance")
    assert phrase in b["reading_en"] and b["reading_zh"]
    debt = next(r for r in view["balances"] if r["series_id"] == "government_debt")
    assert ("rises" if cc == "AU" else "falls") in debt["reading_en"]
    assert all(word not in b["reading_en"].lower() + debt["reading_en"].lower()
               for word in ("nominal borrowing", "fiscal space", "solvent", "tightening"))


@pytest.mark.parametrize("cc", ["GB", "EZ"])
@pytest.mark.parametrize("mismatch", ["family", "edition", "information_cutoff", "period"])
def test_joint_fiscal_thesis_does_not_mix_publication_vintages_or_intervals(cc, mismatch):
    growth = raw(cc=cc, values={"2026": 1.3 if cc == "GB" else 1.1, "2027": 1.2},
                 information_cutoff="2026-09-30")
    inflation = {**growth, "series_id": "inflation_average", "values": {"2026": 3.3, "2027": 2.8}}
    balance = {**growth, "series_id": "fiscal_balance", "unit": "percent_gdp",
               "values": {"2026": -3.8, "2027": -3.0}}
    debt = {**balance, "series_id": "government_debt", "values": {"2026": 102.0, "2027": 102.5}}
    aligned = build_country_outlook(cc, admit([growth, inflation, balance, debt]), today=TODAY)
    aligned_thesis = next(p for p in aligned["propositions"] if p["id"] == cc + ":country_thesis")
    assert ("debt" if cc == "GB" else "fiscal") in aligned_thesis["text_en"]
    for r in (balance, debt):
        if mismatch == "period":
            r.update(period_basis="fiscal_year", fiscal_start_month=4)
        else:
            r[mismatch] = {"family": "Article IV", "edition": "2026-09", "information_cutoff": "2026-09-29"}[mismatch]
    mixed = build_country_outlook(cc, admit([growth, inflation, balance, debt]), today=TODAY)
    thesis = next(p for p in mixed["propositions"] if p["id"] == cc + ":country_thesis")
    assert not ({"fiscal_balance", "government_debt"} & {e["series_id"] for e in thesis["evidence"]})


def test_retained_cache_loader_preserves_actual_fiscal_admission(tmp_path):
    from collectors.intl_country_sources import SCHEMA
    from lib.intl_country_inputs import load_country_inputs
    base = json.loads((ROOT / "config/intl_country_baseline.json").read_text())
    record = next(r for r in base["forecast_archive"]
                  if r["cc"] == "KR" and r["series_id"] == "government_debt"
                  and r["correction_sequence"] == 0)
    source = tmp_path / "source"
    data = tmp_path / "data"
    (source / "config").mkdir(parents=True)
    (data / "intl_macro").mkdir(parents=True)
    (source / "config/intl_country_baseline.json").write_text(json.dumps({"schema":SCHEMA}))
    cache = {"schema":SCHEMA, "forecast_archive":[record]}
    path = data / "intl_macro/country_inputs.json"
    path.write_text(json.dumps(cache))
    original_bytes = path.read_bytes()
    for _ in range(2):
        loaded = load_country_inputs(data, source)
        assert loaded["forecast_archive"] == [record]
        selected = select_publications(loaded["forecast_archive"], "KR",
            series_id="government_debt", today=date(2026,10,19),
            operational_as_of="2026-10-19T23:50:00+00:00")
        assert [r["record_id"] for r in selected] == [record["record_id"]]
    assert path.read_bytes() == original_bytes


def test_retained_archive_restores_correction_and_withdrawal_without_readmission():
    from collectors.intl_country_sources import SCHEMA, merge_country_inputs
    old, corrected = corrected_cutoff_archive()
    withdrawn = admit([{**corrected[-1], "withdrawn_at":"2026-10-19T12:30:00+00:00",
                       "withdrawal_source_url":WEO_OCTOBER_2026["source_url"]}],
                      corrected, now="2026-10-19T14:00:00+00:00")
    original = admit([old])
    # Reconstruct both an empty baseline and an older shipped baseline.
    for previous in ([], original, corrected):
        rebuilt = merge_country_inputs(
            {"schema":SCHEMA,"forecast_archive":previous},
            {"schema":SCHEMA,"forecast_archive":withdrawn}, preserve_custody=True)
        assert rebuilt["forecast_archive"] == withdrawn
        assert rebuilt["forecast_diagnostics"] == []
        for cutoff, expected in ((NOW, "2026-10-01"),
                ("2026-10-19T13:00:00+00:00", "2026-09-30"),
                ("2026-10-19T15:00:00+00:00", None)):
            selected = select_publications(rebuilt["forecast_archive"], "KR",
                                           operational_as_of=cutoff)
            assert (selected[0]["information_cutoff"] if selected else None) == expected


def test_retained_reconstruction_preserves_accepted_and_conflict_identity():
    from collectors.intl_country_sources import SCHEMA, merge_country_inputs
    accepted = admit([raw()])
    archive = admit([raw(values={"2026":4.0,"2027":3.0})], accepted,
                    now="2026-10-19T12:00:00+00:00")
    restored = merge_country_inputs({"schema":SCHEMA},
        {"schema":SCHEMA,"forecast_archive":archive}, preserve_custody=True)
    assert restored["forecast_archive"] == archive
    assert {r["admission_status"] for r in archive} == {"accepted","conflict"}


@pytest.mark.parametrize("field", ["retrieved_at","first_observed_at","admitted_at"])
def test_retained_cache_with_missing_custody_is_not_stamped_by_render(field):
    from collectors.intl_country_sources import SCHEMA, merge_country_inputs
    record = admit([raw()])[0]
    record.pop(field)
    restored = merge_country_inputs({"schema":SCHEMA},
        {"schema":SCHEMA,"forecast_archive":[record]}, preserve_custody=True)
    assert restored["forecast_archive"] == []
    assert restored["forecast_diagnostics"]


def test_live_forecast_payload_cannot_reuse_retained_admission_clocks():
    old = admit([raw()])[0]
    current = "2026-10-20T09:00:00+00:00"
    incoming = {**old, "withdrawn_at":"2026-10-19T12:30:00+00:00",
                "withdrawal_admitted_at":"2026-10-19T13:00:00+00:00",
                "withdrawal_source_url":WEO_OCTOBER_2026["source_url"],
                "superseded_at":"2026-10-19T14:00:00+00:00"}
    records, _ = merge_publications([], [incoming], observed_at=current)
    assert records[0]["first_observed_at"] == current
    assert records[0]["admitted_at"] == current
    assert records[0]["withdrawal_admitted_at"] == current
    assert "superseded_at" not in records[0]


@pytest.mark.parametrize("placement", ["baseline-cache", "cache-baseline", "baseline-only", "cache-only"])
def test_retained_duplicate_custody_is_order_independent(placement):
    early = admit([raw(source_sha256="a"*64)], now="2026-10-19T23:24:00+00:00")[0]
    early["retrieved_at"] = "2026-10-19T23:23:00+00:00"
    late = deepcopy(early)
    late.update(retrieved_at="2026-10-19T23:30:00+00:00",
                first_observed_at="2026-10-19T23:39:00+00:00",
                admitted_at="2026-10-19T23:39:00+00:00", source_sha256="b"*64)
    previous, incoming = {
        "baseline-cache":([late],[early]), "cache-baseline":([early],[late]),
        "baseline-only":([late,early],[]), "cache-only":([],[late,early]),
    }[placement]
    merged, diagnostics = merge_publications(previous,incoming,preserve_custody=True,
                                             observed_at="2026-10-20T09:00:00+00:00")
    assert diagnostics == [] and merged == [early]
    assert select_publications(merged,"KR",operational_as_of="2026-10-19T23:30:00+00:00")


@pytest.mark.parametrize("reverse", [False, True])
def test_retained_withdrawal_uses_one_earliest_complete_event(reverse):
    early = admit([raw()])[0]
    early.update(withdrawn_at="2026-10-19T12:00:00+00:00",
                 withdrawal_admitted_at="2026-10-19T13:00:00+00:00",
                 withdrawal_source_url="https://www.imf.org/early-withdrawal")
    late = deepcopy(early)
    late.update(withdrawal_admitted_at="2026-10-20T08:00:00+00:00",
                withdrawal_source_url="https://www.imf.org/later-withdrawal")
    records = [late,early] if reverse else [early,late]
    merged, diagnostics = merge_publications(records[:1],records[1:],preserve_custody=True,
                                             observed_at="2026-10-20T09:00:00+00:00")
    assert diagnostics == [] and merged == [early]
    assert select_publications(merged,"KR",operational_as_of="2026-10-19T12:30:00+00:00")
    assert not select_publications(merged,"KR",operational_as_of="2026-10-19T14:00:00+00:00")


def test_earlier_retained_correction_reconciles_its_actual_predecessor_event():
    _, original = corrected_cutoff_archive()
    early = next(r for r in original if r["correction_sequence"] == 1)
    late = deepcopy(original)
    for record in late:
        if record["correction_sequence"] == 1:
            record.update(first_observed_at="2026-10-19T14:00:00+00:00",
                          admitted_at="2026-10-19T14:00:00+00:00")
        else:
            record["superseded_at"] = "2026-10-19T14:00:00+00:00"
    for previous,incoming in ((late,[early]),([early],late)):
        merged, diagnostics = merge_publications(previous,incoming,preserve_custody=True,
                                                 observed_at="2026-10-20T09:00:00+00:00")
        assert diagnostics == [] and merged == original
        assert select_publications(merged,"KR",operational_as_of="2026-10-19T11:00:00+00:00")[0]["correction_sequence"] == 0
        assert select_publications(merged,"KR",operational_as_of="2026-10-19T13:00:00+00:00")[0]["correction_sequence"] == 1


def test_incompatible_retained_admission_status_does_not_promote_content():
    accepted = admit([raw()])[0]
    conflict = {**accepted,"admission_status":"conflict"}
    for previous,incoming in (([accepted],[conflict]),([conflict],[accepted])):
        merged, diagnostics = merge_publications(previous,incoming,preserve_custody=True,
                                                 observed_at="2026-10-20T09:00:00+00:00")
        assert diagnostics and merged[0]["admission_status"] == "conflict"
        assert not select_publications(merged,"KR",operational_as_of="2026-10-19T13:00:00+00:00")


def test_live_correction_cannot_resolve_an_unaccepted_predecessor():
    ambiguous, _ = merge_publications([], [raw(),raw(values={"2026":4.,"2027":3.})],observed_at=NOW)
    assert all(r["admission_status"] == "conflict" for r in ambiguous)
    correction = raw(values={"2026":3.5,"2027":2.9},correction_sequence=1,
                     supersedes_record_id=ambiguous[0]["record_id"],
                     correction_source_url=WEO_OCTOBER_2026["documentation_url"])
    archive, diagnostics = merge_publications(ambiguous,[correction],
                                               observed_at="2026-10-19T14:00:00+00:00")
    assert diagnostics and all(r["admission_status"] == "conflict" for r in archive)
    restored, _ = merge_publications([],archive,preserve_custody=True,
                                     observed_at="2026-10-20T09:00:00+00:00")
    assert restored == archive
