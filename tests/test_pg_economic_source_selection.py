from __future__ import annotations

import pytest

from engine.company_intelligence.economic_observations import validate_selected_facts
from engine.company_intelligence.pg_profile import (
    PG_PREPARATION_REFUSALS,
    PgPreparationRefused,
    prepare_pg_workspace,
)
from scripts.refresh_event_workspaces import acquire_results_filing
from tests.earnings_economic_fixtures import (
    FISCAL_SCOPE,
    fixture_accession,
    fixture_http_get,
)


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


def test_newest_unparsed_source_stays_selected_and_yields_typed_absences():
    acquisition, _ = _trace("newest_no_facts")
    acquisition["exhibit_body"] = "<document>refused synthetic witness</document>"
    result = prepare_pg_workspace(
        acquisition, prior=None, observed_at="2026-08-02T17:00:00Z"
    )
    assert result["currentness"]["state"] == "up_to_date"
    assert result["workspace"]["sources"][0]["filing_key"]["accession"] == fixture_accession("newer")
    rows = validate_selected_facts(
        result["workspace"], source_texts=result["source_texts"], fiscal_scope=FISCAL_SCOPE
    )
    assert len(rows) == len(FISCAL_SCOPE) * 5
    assert all("typed_absence" in row for row in rows)


def test_newest_refused_body_stays_selected_with_typed_absences():
    acquisition, _ = _trace("newest_no_facts")
    refused = dict(acquisition)
    refused["exhibit_body"] = "<document>unlocated synthetic witness</document>"
    result = prepare_pg_workspace(refused, prior=None, observed_at="2026-08-02T17:00:00Z")
    rows = validate_selected_facts(
        result["workspace"], source_texts=result["source_texts"], fiscal_scope=FISCAL_SCOPE
    )
    assert len(rows) == len(FISCAL_SCOPE) * 5
    assert all("typed_absence" in row for row in rows)
    assert result["currentness"]["state"] == "up_to_date"


def test_amendment_is_not_a_second_fiscal_quarter():
    selected, trace = _trace("amendment_8ka")
    assert selected["form"] == "8-K/A"
    assert trace["selected_accession"] == fixture_accession("amendment")
    result = prepare_pg_workspace(selected, prior=None, observed_at="2026-07-30T18:01:00Z")
    assert result["workspace"]["fiscal_period"]["quarter"] == 4
    assert result["document_metadata"]["document_kind"] == "release_amendment"


def test_missing_report_date_is_typed_not_guessed():
    events = []
    acquisition = acquire_results_filing(
        cik="0000080424", http_get=fixture_http_get("no_report_date"),
        trace=events.append,
    )
    assert acquisition["report_date"] == ""
    assert events[-1]["typed_handling"]["report_date"] == "missing"
    result = prepare_pg_workspace(acquisition, prior=None, observed_at="2026-08-02T17:00:00Z")
    assert result["currentness_context"]["fiscal_scope"] is None
    assert all("typed_absence" in row for row in result["workspace"]["facts"] if str(row.get("metric", "")).startswith("pg_"))


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
    with pytest.raises(ValueError, match="acceptance_datetime is required"):
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-08-02T17:00:00Z")


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
        acquisition, prior=None, observed_at="2026-08-02T17:00:00Z"
    )


@pytest.mark.parametrize(
    ("reason", "mutate"),
    [
        ("malformed_acquisition", lambda acquisition, prior: object()),
        ("malformed_prior", lambda acquisition, prior: prior.update({"sources": "not-a-list"})),
        ("prior_source_identity_missing", lambda acquisition, prior: prior["sources"][0].pop("source_sha256")),
        ("malformed_source_clock", lambda acquisition, prior: acquisition.update(acceptance_datetime="2026-07-29 17:00:00Z")),
        ("unadmitted_issuer", lambda acquisition, prior: acquisition.update(cik="0000000000")),
        ("document_period_not_admitted", lambda acquisition, prior: acquisition.update(exhibit_body="<h1>Fourth Quarter Ended March 31, 2027</h1>")),
        ("missing_received_byte_receipt", lambda acquisition, prior: acquisition.pop("received_bytes")),
        ("received_bytes_mismatch", lambda acquisition, prior: acquisition.update(received_bytes={"sha256": "b" * 64, "length": 42, "declared_encoding": "utf-8"})),
        ("non_utf8_source", lambda acquisition, prior: acquisition.update(declared_encoding="latin-1")),
        ("malformed_currentness", lambda acquisition, prior: acquisition.update(currentness={"state": "unverified"})),
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
        prepare_pg_workspace(acquisition, prior=prior, observed_at="2026-09-01T17:00:00Z")
    assert type(raised.value) is PgPreparationRefused
    assert raised.value.reason == reason
    assert str(raised.value) == _PREPARATION_REASONS[reason]


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
    )


def test_unchanged_source_carries_first_observation_and_content_forward():
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-09-01T17:00:00Z"
    )
    assert second["workspace"]["lifecycle"]["observed_at"] == "2026-08-02T17:00:00Z"
    assert second["workspace"]["generated_at"] == first["workspace"]["generated_at"]
    assert second["workspace"]["generation_id"] == first["workspace"]["generation_id"]


def test_changed_bytes_at_the_same_url_link_a_new_revision_to_its_predecessor():
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    acquisition["exhibit_body"] = acquisition["exhibit_body"].replace(
        "<td>$3.07</td>", "<td>$3.17</td>"
    )
    acquisition["cik"] = "80424"
    acquisition["received_bytes"] = {"sha256": "b" * 64, "length": 42}
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-09-01T17:00:00Z"
    )
    assert second["workspace"]["lifecycle"]["state"] == "corrected"
    assert second["workspace"]["lifecycle"]["observed_at"] == "2026-09-01T17:00:00Z"
    assert second["workspace"]["generation_id"] != first["workspace"]["generation_id"]
    assert second["document_metadata"]["revision"] == 2
    assert second["document_metadata"]["supersedes_document_id"] == (
        first["document_metadata"]["document_id"]
    )
    assert second["workspace"]["sources"][0]["filing_key"]["accession"] == acquisition["accession"]
    assert second["document_metadata"]["content_sha256"] == acquisition["received_bytes"]["sha256"]


def test_code_only_change_does_not_alter_sec_acceptance_time():
    first = _prepared()
    acquisition, _ = _trace("same_source_rebuild")
    second = prepare_pg_workspace(
        acquisition, prior=first["workspace"], observed_at="2026-09-01T17:00:00Z"
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
            acquisition, prior=FailingMapping(), observed_at="2026-09-01T17:00:00Z"
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
