from __future__ import annotations

import hashlib

import pytest

from engine.company_intelligence.economic_observations import validate_selected_facts
from engine.company_intelligence.pg_profile import RIGHTS_PROFILE
from engine.company_intelligence.pg_profile import (
    PG_PREPARATION_REFUSALS,
    PG_PRIVATE_RIGHTS_PROFILE,
    PROFILE_SOURCE_FAMILY,
    PgPreparationRefused,
    prepare_pg_workspace,
    source_family_for_profile,
)
from scripts.refresh_event_workspaces import acquire_results_filing
from tests.earnings_economic_fixtures import (
    FISCAL_SCOPE,
    fixture_accession,
    fixture_http_get,
)


def _update_received_bytes(acquisition: dict) -> None:
    body = acquisition["exhibit_body"].encode("utf-8")
    acquisition["received_bytes"] = {
        "sha256": hashlib.sha256(body).hexdigest(), "length": len(body)
    }


def _trace(case: str):
    events = []
    acquisition = acquire_results_filing(
        cik="0000080424", http_get=fixture_http_get(case), trace=events.append
    )
    return acquisition, events[-1]


def test_older_fallback_is_not_current():
    selected, trace = _trace("newer_fetch_failed")
    assert selected["accession"] == fixture_accession("older")
    assert trace["newest_relevant_accession"] == fixture_accession("newer")
    assert trace["selected_accession"] == fixture_accession("older")
    assert trace["currentness"] == "newer_source_pending"
    assert trace["excluded_non_results"] == 1


def test_callback_less_call_returns_the_exact_legacy_dict():
    acquisition = acquire_results_filing(
        cik="0000080424", http_get=fixture_http_get("newer_fetch_failed")
    )
    assert acquisition == {
        "cik": "0000080424",
        "accession": fixture_accession("older"),
        "form": "8-K",
        "filing_date": "2026-07-29",
        "acceptance_datetime": "2026-07-29T17:10:00Z",
        "report_date": "2026-06-30",
        "exhibit_url": "https://www.sec.gov/Archives/edgar/data/80424/000008042426000001/synthetic-exhibit-991.htm",
        "exhibit_body": acquisition["exhibit_body"],
        "items": "2.02",
    }
    assert acquisition["exhibit_body"].startswith("<html><head>")


def test_trace_provenance_is_distinct_and_capped():
    events = []
    with pytest.raises(Exception, match="decode"):
        acquire_results_filing(
            cik="0000080424", http_get=fixture_http_get("malformed_encoding"),
            trace=events.append,
        )
    trace = events[-1]
    assert trace["candidate_limit"] == 24
    assert len(trace["candidates"]) <= 24
    assert trace["candidates"][0]["outcome"] == "decode_failure"
    assert trace["received_bytes"]["length"] == 28
    assert trace["decoded_text"] is None
    assert trace["decode"] == "latin-1-fallback"
    assert trace["declared_encoding"] == "latin-1"
    assert trace["observed_at"] is None
    assert trace["currentness"] == "currentness_unverified"


def test_newest_unparsed_source_stays_selected_and_yields_typed_absences():
    acquisition, _ = _trace("newest_no_facts")
    acquisition["exhibit_body"] = "<document>refused synthetic witness</document>"
    _update_received_bytes(acquisition)
    result = prepare_pg_workspace(
        acquisition, prior=None, observed_at="2026-07-30T18:00:00Z"
    )
    assert result["currentness_context"]["currentness"]["state"] == "up_to_date"
    assert result["workspace"]["sources"][0]["filing_key"]["accession"] == fixture_accession("newer")
    rows = validate_selected_facts(
        result["workspace"], source_texts=result["source_texts"], fiscal_scope=FISCAL_SCOPE
    )
    assert len(rows) == len(FISCAL_SCOPE) * 5
    assert all("typed_absence" in row or "value" in row for row in rows)


def test_newest_refused_body_stays_selected_with_typed_absences():
    acquisition, _ = _trace("newest_no_facts")
    refused = dict(acquisition)
    refused["exhibit_body"] = "<document>unlocated synthetic witness</document>"
    _update_received_bytes(refused)
    result = prepare_pg_workspace(refused, prior=None, observed_at="2026-07-30T18:00:00Z")
    rows = validate_selected_facts(
        result["workspace"], source_texts=result["source_texts"], fiscal_scope=FISCAL_SCOPE
    )
    assert len(rows) == len(FISCAL_SCOPE) * 5
    assert all("typed_absence" in row or "value" in row for row in rows)
    assert result["currentness_context"]["currentness"]["state"] == "up_to_date"


def test_amendment_is_not_a_second_fiscal_quarter():
    selected, trace = _trace("amendment_8ka")
    assert selected["form"] == "8-K/A"
    assert trace["selected_accession"] == fixture_accession("amendment")
    result = prepare_pg_workspace(selected, prior=None, observed_at="2026-07-30T18:01:00Z")
    assert result["workspace"]["fiscal_period"]["quarter"] == 4
    assert result["document_metadata"]["document_kind"] == "release_amendment"


@pytest.mark.parametrize(
    ("acceptance_datetime", "expected_scope", "expected_period"),
    [
        ("2026-07-29T17:00:00Z", ("2026-04-01", "2026-06-30", "2025-04-01", "2025-06-30"), {"year": 2026, "quarter": 4, "calendar_end": "2026-06-30"}),
        ("2026-10-24T17:00:00Z", ("2026-07-01", "2026-09-30", "2025-07-01", "2025-09-30"), {"year": 2027, "quarter": 1, "calendar_end": "2026-09-30"}),
        ("2027-01-23T17:00:00Z", ("2026-10-01", "2026-12-31", "2025-10-01", "2025-12-31"), {"year": 2027, "quarter": 2, "calendar_end": "2026-12-31"}),
        ("2027-04-22T17:00:00Z", ("2027-01-01", "2027-03-31", "2026-01-01", "2026-03-31"), {"year": 2027, "quarter": 3, "calendar_end": "2027-03-31"}),
    ],
)
def test_fiscal_scope_comes_from_the_admitted_calendar_and_source_clock(
    acceptance_datetime, expected_scope, expected_period
):
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["acceptance_datetime"] = acceptance_datetime
    if acceptance_datetime != "2026-07-29T17:00:00Z":
        acquisition["exhibit_body"] = "<html><body><p>Synthetic release with no period signal.</p></body></html>"
        _update_received_bytes(acquisition)
    result = prepare_pg_workspace(acquisition, prior=None, observed_at=acceptance_datetime)
    assert result["currentness_context"]["fiscal_scope"] == expected_scope
    assert result["workspace"]["fiscal_period"] == expected_period
    assert result["document_metadata"]["presented_fiscal_label"] == (
        f"FY{expected_period['year']} Q{expected_period['quarter']}"
    )


def test_document_signals_for_another_quarter_refuse_the_derived_scope():
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["acceptance_datetime"] = "2026-10-24T17:00:00Z"
    acquisition["exhibit_body"] = "<h1>Second Quarter Ended March 31, 2027</h1>"
    _update_received_bytes(acquisition)
    with pytest.raises(PgPreparationRefused, match="document period") as raised:
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-10-24T18:00:00Z")
    assert raised.value.reason == "document_period_not_admitted"


def test_unresolved_cik_refuses_instead_of_defaulting_to_pg():
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["cik"] = "0000000000"
    with pytest.raises(PgPreparationRefused, match="not admitted") as raised:
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-29T17:20:00Z")
    assert raised.value.reason == "unadmitted_issuer"


def test_missing_report_date_is_typed_not_guessed():
    events = []
    acquisition = acquire_results_filing(
        cik="0000080424", http_get=fixture_http_get("no_report_date"),
        trace=events.append,
    )
    assert acquisition["report_date"] == ""
    assert events[-1]["typed_handling"]["report_date"] == "missing"
    result = prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-29T17:20:00Z")
    assert result["currentness_context"]["fiscal_scope"] == (
        "2026-04-01", "2026-06-30", "2025-04-01", "2025-06-30"
    )
    rows = validate_selected_facts(
        result["workspace"], source_texts=result["source_texts"], fiscal_scope=FISCAL_SCOPE
    )
    assert all("typed_absence" in row or "value" in row for row in rows)


def test_missing_acceptance_timestamp_is_typed_not_a_guessed_clock():
    events = []
    with pytest.raises(Exception, match="acceptance_datetime is required"):
        acquire_results_filing(
            cik="0000080424", http_get=fixture_http_get("missing_acceptance_ts"),
            trace=events.append,
        )
    assert events[-1]["typed_handling"]["acceptance_datetime"] == "missing"
    acquisition = {
        "cik": "0000080424",
        "accession": fixture_accession("older"),
        "form": "8-K",
        "filing_date": "2026-07-29",
        "acceptance_datetime": "",
        "report_date": "2026-06-30",
        "exhibit_url": "https://synthetic.invalid/release.htm",
        "exhibit_body": events[-1]["candidates"][-1].get("exhibit_body", ""),
    }
    with pytest.raises(PgPreparationRefused, match="acceptance_datetime must use"):
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-29T17:20:00Z")


def test_two_plausible_exhibits_are_ambiguity_refused():
    events = []
    with pytest.raises(Exception, match="ambiguous"):
        acquire_results_filing(
            cik="0000080424", http_get=fixture_http_get("two_plausible_exhibits"),
            trace=events.append,
        )
    assert events[-1]["selected_accession"] is None


def test_malformed_encoding_is_a_decode_failure_without_evidence():
    events = []
    with pytest.raises(Exception, match="decode"):
        acquire_results_filing(
            cik="0000080424", http_get=fixture_http_get("malformed_encoding"),
            trace=events.append,
        )
    assert events[-1]["candidates"][-1]["outcome"] == "decode_failure"
    assert events[-1]["decode"] == "latin-1-fallback"


_PREPARATION_REASONS = {
    "malformed_acquisition": "acquisition must be a mapping",
    "malformed_prior": "prior must be a mapping",
    "prior_source_identity_missing": "prior issuer release lacks source identity",
    "malformed_source_clock": "acceptance_datetime must use YYYY-MM-DDTHH:MM:SSZ",
    "unadmitted_issuer": "acquisition CIK is not admitted by the issuer registry",
    "document_period_not_admitted": "document period signals do not admit the derived fiscal scope",
    "missing_received_byte_receipt": "acquisition received-byte receipt is required",
    "received_bytes_mismatch": "acquisition received bytes do not match the decoded source text",
    "non_utf8_source": "acquisition source was not cleanly decoded as utf-8",
    "malformed_currentness": "acquisition currentness is malformed",
}


def _prepared():
    acquisition, _ = _trace("same_source_rebuild")
    return prepare_pg_workspace(
        acquisition, prior=None, observed_at=acquisition["acceptance_datetime"]
    )


@pytest.mark.parametrize(
    ("reason", "mutate"),
    [
        ("malformed_acquisition", lambda acquisition, prior: object()),
        ("malformed_prior", lambda acquisition, prior: prior.update({"sources": "not-a-list"})),
        ("prior_source_identity_missing", lambda acquisition, prior: (prior["sources"][0].pop("filing_key"), None)[1]),
        ("malformed_source_clock", lambda acquisition, prior: acquisition.update(acceptance_datetime="2026-07-29 17:00:00Z")),
        ("unadmitted_issuer", lambda acquisition, prior: acquisition.update(cik="0000000000")),
        ("document_period_not_admitted", lambda acquisition, prior: (acquisition.update(exhibit_body="<h1>Second Quarter Ended March 31, 2027</h1>"), _update_received_bytes(acquisition), None)[-1]),
        ("missing_received_byte_receipt", lambda acquisition, prior: (acquisition.pop("received_bytes"), None)[1]),
        ("received_bytes_mismatch", lambda acquisition, prior: acquisition.update(received_bytes={"sha256": "b" * 64, "length": 42, "declared_encoding": "utf-8"})),
        ("non_utf8_source", lambda acquisition, prior: acquisition.update(declared_encoding="latin-1")),
        ("malformed_currentness", lambda acquisition, prior: acquisition.update(currentness={"state": "up_to_date", "checked_at": "2026-07-29T17:10:00Z", "extra": True})),
    ],
)
def test_every_preparation_refusal_is_typed_with_its_exact_reason(reason, mutate):
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    prior = first["workspace"]
    replacement = mutate(acquisition, prior)
    if replacement is not None:
        acquisition = replacement
    with pytest.raises(PgPreparationRefused) as raised:
        prepare_pg_workspace(acquisition, prior=prior, observed_at="2026-07-29T17:20:00Z")
    assert type(raised.value) is PgPreparationRefused
    assert raised.value.reason == reason
    assert str(raised.value) == _PREPARATION_REASONS[reason]


def test_profile_source_family_has_one_immutable_admitted_entry():
    assert PROFILE_SOURCE_FAMILY == {RIGHTS_PROFILE: "sec_edgar"}
    with pytest.raises(TypeError):
        PROFILE_SOURCE_FAMILY[RIGHTS_PROFILE] = "other"
    assert source_family_for_profile(RIGHTS_PROFILE) == "sec_edgar"
    for profile in ("unknown-profile", PG_PRIVATE_RIGHTS_PROFILE):
        with pytest.raises(PgPreparationRefused, match="profile is not mapped") as raised:
            source_family_for_profile(profile)
        assert raised.value.reason == "unsupported_source_profile"


def test_preparation_refusals_are_closed():
    assert PG_PREPARATION_REFUSALS == (
        "malformed_acquisition",
        "malformed_prior",
        "prior_source_identity_missing",
        "malformed_source_clock",
        "unadmitted_issuer",
        "document_period_not_admitted",
        "missing_received_byte_receipt",
        "received_bytes_mismatch",
        "non_utf8_source",
        "malformed_currentness",
        "unsupported_source_profile",
    )


def test_unchanged_source_carries_first_observation_forward_under_each_currentness_state():
    states = (
        ("up_to_date", "2026-07-29T17:10:00Z"),
        ("newer_source_pending", "2026-07-29T17:10:00Z"),
        ("currentness_unverified", None),
    )
    for state, checked_at in states:
        first = _prepared()
        acquisition, _ = _trace("same_source_rebuild")
        acquisition["currentness"] = {"state": state, "checked_at": checked_at}
        second = prepare_pg_workspace(
            acquisition, prior=first["workspace"], observed_at="2026-07-29T17:20:00Z"
        )
        assert second["document_metadata"]["revision"] == 1
        assert second["document_metadata"]["supersedes_document_id"] is None
        assert second["workspace"]["lifecycle"]["observed_at"] == "2026-07-29T17:10:00Z"
        assert second["workspace"]["generated_at"] == first["workspace"]["generated_at"]
        assert second["workspace"]["generation_id"] == first["workspace"]["generation_id"]
        assert second["currentness_context"]["currentness"] == {
            "state": state, "source_clock": checked_at
        }


def test_decoded_source_digest_is_native_with_and_without_prior():
    acquisition, _ = _trace("same_source_rebuild")
    result = prepare_pg_workspace(
        acquisition, prior=None, observed_at=acquisition["acceptance_datetime"]
    )
    source = result["workspace"]["sources"][0]
    document_id = source["document_id"]
    assert source["source_sha256"] == hashlib.sha256(
        result["source_texts"][document_id].encode("utf-8")
    ).hexdigest()
    republished = prepare_pg_workspace(
        acquisition, prior=result["workspace"], observed_at="2026-07-29T17:20:00Z"
    )
    assert republished["workspace"]["sources"][0]["source_sha256"] == source["source_sha256"]


def test_changed_bytes_at_the_same_url_link_a_new_revision_to_its_predecessor():
    first = _prepared()
    acquisition, _ = _trace("changed_bytes")
    new_bytes = acquisition["exhibit_body"].encode("utf-8")
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-07-30T17:20:00Z"
    )
    assert second["workspace"]["sources"][0]["source_sha256"] == hashlib.sha256(new_bytes).hexdigest()
    assert second["workspace"]["sources"][0]["source_sha256"] != first["workspace"]["sources"][0]["source_sha256"]
    assert second["workspace"]["sources"][0]["filing_key"]["accession"] == acquisition["accession"]
    assert second["workspace"]["sources"][0]["form"] == acquisition["form"]
    assert second["workspace"]["sources"][0]["url"] == acquisition["exhibit_url"]
    assert second["document_metadata"]["revision"] == 2
    assert second["document_metadata"]["supersedes_document_id"] == first["document_metadata"]["document_id"]
    assert second["received_byte_receipt"] == {
        "sha256": hashlib.sha256(new_bytes).hexdigest(),
        "length": len(new_bytes),
        "declared_encoding": "utf-8",
    }


def test_changed_accession_with_identical_text_links_a_new_revision():
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["accession"] = fixture_accession("changed")
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-07-29T17:20:00Z"
    )
    assert second["document_metadata"]["revision"] == 2
    assert second["document_metadata"]["supersedes_document_id"] == first["document_metadata"]["document_id"]


def test_amendment_is_not_a_second_fiscal_quarter_and_supersedes_its_original():
    first = _prepared()
    amendment, _ = _trace("amendment_sequence")
    second = prepare_pg_workspace(
        amendment, prior=first, observed_at="2026-07-30T18:01:00Z"
    )
    assert second["workspace"]["event_id"] == first["workspace"]["event_id"]
    assert second["workspace"]["fiscal_period"] == first["workspace"]["fiscal_period"]
    assert second["document_metadata"]["revision"] == 2
    assert second["document_metadata"]["supersedes_document_id"] == first["document_metadata"]["document_id"]


@pytest.mark.parametrize("remove_identity", ["accession", "source_sha256", "release"])
def test_missing_prior_source_identity_is_refused_not_treated_as_no_prior(remove_identity):
    first = _prepared()
    prior = first["workspace"]
    if remove_identity == "accession":
        prior["sources"][0]["filing_key"].pop("accession")
    elif remove_identity == "source_sha256":
        prior["sources"][0].pop("source_sha256")
    else:
        prior["sources"] = [row for row in prior["sources"] if row.get("kind") != "issuer_release"]
    acquisition, _ = _trace("same_source_rebuild")
    with pytest.raises(PgPreparationRefused, match="source identity") as raised:
        prepare_pg_workspace(acquisition, prior=prior, observed_at="2026-07-29T17:20:00Z")
    assert raised.value.reason == "prior_source_identity_missing"


def test_currentness_round_trips_from_trace_to_preparation_for_every_state():
    for state in ("up_to_date", "newer_source_pending", "currentness_unverified"):
        acquisition, trace = _trace("same_source_rebuild")
        checked_at = trace["observed_at"]
        if state == "currentness_unverified":
            checked_at = None
        acquisition["currentness"] = {"state": state, "checked_at": checked_at}
        result = prepare_pg_workspace(
            acquisition, prior=None, observed_at=acquisition["acceptance_datetime"]
        )
        assert result["currentness_context"]["currentness"] == {
            "state": state,
            "source_clock": checked_at,
        }


def test_preparation_uses_checked_at_not_observed_at():
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["currentness"] = {
        "state": "up_to_date", "checked_at": "2026-07-29T17:11:00Z"
    }
    result = prepare_pg_workspace(
        acquisition, prior=None, observed_at="2026-07-29T17:20:00Z"
    )
    assert result["currentness_context"]["currentness"]["source_clock"] == (
        "2026-07-29T17:11:00Z"
    )


def test_absent_acquisition_currentness_prepares_none_currentness():
    acquisition, _ = _trace("same_source_rebuild")
    acquisition.pop("currentness")
    result = prepare_pg_workspace(
        acquisition, prior=None, observed_at=acquisition["acceptance_datetime"]
    )
    assert result["currentness_context"]["currentness"] is None


@pytest.mark.parametrize(
    "currentness",
    [
        {"state": "up_to_date", "checked_at": "2026-07-29T17:10:00Z", "extra": True},
        {"state": "unknown_state", "checked_at": "2026-07-29T17:10:00Z"},
        {"state": "unverified", "checked_at": "2026-07-29T17:10:00Z"},
        {"state": "up_to_date", "checked_at": None},
        {"state": "up_to_date", "checked_at": "2026-07-29T17:10:00+00:00"},
    ],
)
def test_malformed_acquisition_currentness_is_refused(currentness):
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["currentness"] = currentness
    with pytest.raises(PgPreparationRefused, match="currentness is malformed") as raised:
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-29T17:20:00Z")
    assert raised.value.reason == "malformed_currentness"


def test_code_only_change_does_not_alter_sec_acceptance_time():
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-07-29T17:20:00Z"
    )
    assert second["workspace"]["lifecycle"]["source_available_at"] == (
        first["workspace"]["lifecycle"]["source_available_at"]
    )


def test_prior_read_failure_raises():
    class FailingMapping(dict):
        def get(self, key, default=None):
            raise RuntimeError("prior bytes unavailable")

    acquisition, _ = _trace("prior_unavailable")
    with pytest.raises(RuntimeError, match="prior bytes unavailable"):
        prepare_pg_workspace(
            acquisition, prior=FailingMapping(), observed_at="2026-07-29T17:20:00Z"
        )


def test_exact_accession_request_never_falls_back():
    events = []
    with pytest.raises(Exception, match="503"):
        acquire_results_filing(
            cik="0000080424",
            http_get=fixture_http_get("newer_fetch_failed"),
            accession=fixture_accession("newer"),
            trace=events.append,
        )
    assert events[-1]["selected_accession"] is None
    assert events[-1]["candidates"][-1]["outcome"] == "fetch_failure"


def test_legacy_latin1_acquisition_is_refused_as_non_utf8_source():
    acquisition = acquire_results_filing(
        cik="0000080424", http_get=fixture_http_get("malformed_encoding")
    )
    acquisition["received_bytes"] = {"sha256": "a" * 64, "length": len(acquisition["exhibit_body"].encode("utf-8"))}
    with pytest.raises(PgPreparationRefused, match="cleanly decoded as utf-8") as raised:
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-30T17:01:00Z")
    assert raised.value.reason == "non_utf8_source"


def test_exact_accession_success_carries_its_own_receipt_and_currentness():
    events = []
    acquisition = acquire_results_filing(
        cik="0000080424",
        http_get=fixture_http_get("newer_fetch_failed"),
        accession=fixture_accession("older"),
        trace=events.append,
    )
    recorded_bytes = acquisition["exhibit_body"].encode("utf-8")
    assert acquisition["accession"] == fixture_accession("older")
    assert acquisition["received_bytes"] == {
        "sha256": hashlib.sha256(recorded_bytes).hexdigest(),
        "length": len(recorded_bytes),
    }
    assert acquisition["currentness"]["state"] == "newer_source_pending"
    assert acquisition["currentness"]["checked_at"] == events[-1]["observed_at"]
