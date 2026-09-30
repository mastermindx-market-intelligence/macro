from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import engine.company_intelligence.pg_profile as pg_profile_module
import scripts.refresh_event_workspaces as refresh_module
from engine.company_intelligence.documents import DocumentRevisionChain, FilingKey, SourceDocument
from engine.company_intelligence.economic_observations import validate_selected_facts
from engine.company_intelligence.event_workspace import preview_generation_identity
from engine.company_intelligence.pg_profile import RIGHTS_PROFILE
from engine.company_intelligence.pg_profile import (
    PG_PREPARATION_REFUSALS,
    PG_PRIVATE_RIGHTS_PROFILE,
    PROFILE_SOURCE_FAMILY,
    PgPreparationRefused,
    prepare_pg_workspace,
    source_family_for_profile,
)
from scripts.refresh_event_workspaces import RefreshError, acquire_results_filing
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
    "malformed_acquisition": "acquisition is malformed",
    "malformed_prior": "prior is malformed",
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
        ("malformed_prior", lambda acquisition, prior: prior["workspace"].update({"sources": "not-a-list"})),
        ("prior_source_identity_missing", lambda acquisition, prior: (prior["workspace"]["sources"][0].pop("filing_key"), None)[1]),
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
    prior = first
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
        "malformed_observation_clock",
        "source_precedes_prior_event",
        "workspace_build_refused",
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
            acquisition, prior=first, observed_at="2026-07-29T17:20:00Z"
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
        acquisition, prior=result, observed_at="2026-07-29T17:20:00Z"
    )
    assert republished["workspace"]["sources"][0]["source_sha256"] == source["source_sha256"]


def test_changed_text_with_a_prior_valid_receipt_is_refused():
    first = _prepared()
    acquisition, _ = _trace("changed_bytes")
    acquisition["received_bytes"] = {
        "sha256": first["workspace"]["sources"][0]["source_sha256"],
        "length": len(first["decoded_source"].encode("utf-8")),
    }
    with pytest.raises(PgPreparationRefused, match="do not match") as raised:
        prepare_pg_workspace(acquisition, prior=first, observed_at="2026-07-30T17:20:00Z")
    assert raised.value.reason == "received_bytes_mismatch"


def test_missing_decode_label_is_refused_without_a_utf8_default():
    acquisition, _ = _trace("same_source_rebuild")
    acquisition.pop("declared_encoding")
    with pytest.raises(PgPreparationRefused, match="cleanly decoded as utf-8") as raised:
        prepare_pg_workspace(acquisition, prior=None, observed_at="2026-07-29T17:20:00Z")
    assert raised.value.reason == "non_utf8_source"


def test_changed_bytes_at_the_same_url_link_a_new_revision_to_its_predecessor():
    first = _prepared()
    acquisition, _ = _trace("changed_bytes")
    new_bytes = acquisition["exhibit_body"].encode("utf-8")
    second = prepare_pg_workspace(
        acquisition, prior=first, observed_at="2026-07-30T17:20:00Z"
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
        acquisition, prior=first, observed_at="2026-07-29T17:20:00Z"
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
    whole = first
    if remove_identity == "accession":
        prior["sources"][0]["filing_key"].pop("accession")
    elif remove_identity == "source_sha256":
        prior["sources"][0].pop("source_sha256")
    else:
        prior["sources"] = [row for row in prior["sources"] if row.get("kind") != "issuer_release"]
    acquisition, _ = _trace("same_source_rebuild")
    with pytest.raises(PgPreparationRefused, match="source identity") as raised:
        prepare_pg_workspace(acquisition, prior=whole, observed_at="2026-07-29T17:20:00Z")
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
        acquisition, prior=first, observed_at="2026-07-29T17:20:00Z"
    )
    assert second["workspace"]["lifecycle"]["source_available_at"] == (
        first["workspace"]["lifecycle"]["source_available_at"]
    )


def test_prior_read_failure_raises():
    calls = []

    class FailingMapping(dict):
        def get(self, key, default=None):
            calls.append(key)
            raise RuntimeError("prior bytes unavailable")

    acquisition, _ = _trace("prior_unavailable")
    with pytest.raises(PgPreparationRefused, match="prior is malformed") as raised:
        prepare_pg_workspace(
            acquisition, prior=FailingMapping(), observed_at="2026-07-29T17:20:00Z"
        )
    assert type(raised.value) is PgPreparationRefused
    assert raised.value.reason == "malformed_prior"
    assert raised.value.detail == "prior"
    assert calls == []


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


# ---- Round 5 (seat rulings R5.1-R5.14): typed boundary, consistent result, one fiscal period per chain ----

_R5_MESSAGES = {
    **_PREPARATION_REASONS,
    "unsupported_source_profile": "profile is not mapped to a source family",
    "malformed_observation_clock": "observed_at must use YYYY-MM-DDTHH:MM:SSZ and must not precede the source",
    "source_precedes_prior_event": "acquisition is older than the source of the prior workspace",
    "workspace_build_refused": "native workspace build refused the acquisition",
}
_COMPARED = ("workspace", "document_metadata", "decoded_source", "source_texts", "received_byte_receipt")
_CLOCK = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ACQUIRED: dict = {}


def _acquired(case: str) -> dict:
    """A fresh copy of the traced acquisition for *case*; the paced transport runs once per case."""
    if case not in _ACQUIRED:
        _ACQUIRED[case] = _trace(case)[0]
    return copy.deepcopy(_ACQUIRED[case])


def _with_body(acquisition: dict, body: str) -> dict:
    changed = copy.deepcopy(acquisition)
    changed["exhibit_body"] = body
    _update_received_bytes(changed)
    return changed


def _quarter(acceptance: str, number: str) -> dict:
    """A synthetic filing of another fiscal quarter: no period signal, its own accession and clocks."""
    acquisition = _with_body(
        _acquired("same_source_rebuild"),
        "<html><body><p>Synthetic release with no period signal.</p></body></html>",
    )
    acquisition["acceptance_datetime"] = acceptance
    acquisition["accession"] = f"0000080424-26-000{number}"
    acquisition["filing_date"] = acceptance[:10]
    acquisition["report_date"] = acceptance[:10]
    acquisition["exhibit_url"] = (
        f"https://www.sec.gov/Archives/edgar/data/80424/000008042426000{number}/ex991.htm"
    )
    return acquisition


def _raises(name):
    def method(self, *args, **kwargs):
        raise RuntimeError(f"hostile {name} ran")

    return method


class _Hostile:
    """A value every use of which raises: no method of an argument may run before its type is known."""

    __eq__ = _raises("__eq__")
    __ne__ = _raises("__ne__")
    __hash__ = _raises("__hash__")
    __str__ = _raises("__str__")
    __bool__ = _raises("__bool__")
    __len__ = _raises("__len__")
    __iter__ = _raises("__iter__")
    __getitem__ = _raises("__getitem__")
    __contains__ = _raises("__contains__")
    __lt__ = _raises("__lt__")
    __gt__ = _raises("__gt__")
    __int__ = _raises("__int__")
    __index__ = _raises("__index__")

    def __repr__(self):
        return "<hostile>"

    def __getattr__(self, name):
        raise RuntimeError(f"hostile __getattr__({name}) ran")


class _HostileMeta(type):
    __hash__ = _raises("metaclass __hash__")
    __eq__ = _raises("metaclass __eq__")
    __instancecheck__ = _raises("metaclass __instancecheck__")
    __subclasscheck__ = _raises("metaclass __subclasscheck__")


class _HostileTyped(metaclass=_HostileMeta):
    """A value whose type raises when hashed or compared, and whose ``__class__`` raises when read."""

    __class__ = property(_raises("__class__"))

    def __repr__(self):
        return "<hostile type>"


class _StrSub(str):
    __eq__ = _raises("str subclass __eq__")
    __ne__ = _raises("str subclass __ne__")
    __hash__ = _raises("str subclass __hash__")
    __len__ = _raises("str subclass __len__")
    encode = _raises("str subclass encode")
    strip = _raises("str subclass strip")

    def __repr__(self):
        return "<str subclass>"


class _StrKey(str):
    """A ``str`` subclass key: it hashes like the real key and its comparison raises."""

    __hash__ = str.__hash__
    __eq__ = _raises("str subclass key __eq__")
    __ne__ = _raises("str subclass key __ne__")

    def __repr__(self):
        return "<str subclass key>"


class _Twin:
    """A key that is not a string, hashes like a real string key, and raises when compared."""

    def __init__(self, name):
        self._name = name

    def __hash__(self):
        return hash(self._name)

    __eq__ = _raises("twin key __eq__")

    def __repr__(self):
        return "<twin key>"


class _DictSub(dict):
    get = _raises("dict subclass get")
    __getitem__ = _raises("dict subclass __getitem__")
    __iter__ = _raises("dict subclass __iter__")
    __contains__ = _raises("dict subclass __contains__")
    __len__ = _raises("dict subclass __len__")
    __eq__ = _raises("dict subclass __eq__")
    keys = _raises("dict subclass keys")
    items = _raises("dict subclass items")

    def __repr__(self):
        return "<dict subclass>"


class _ListSub(list):
    __iter__ = _raises("list subclass __iter__")
    __getitem__ = _raises("list subclass __getitem__")
    __len__ = _raises("list subclass __len__")
    __eq__ = _raises("list subclass __eq__")

    def __repr__(self):
        return "<list subclass>"


class _IntSub(int):
    __eq__ = _raises("int subclass __eq__")
    __hash__ = _raises("int subclass __hash__")
    __lt__ = _raises("int subclass __lt__")
    __le__ = _raises("int subclass __le__")
    __gt__ = _raises("int subclass __gt__")
    __ge__ = _raises("int subclass __ge__")
    __add__ = _raises("int subclass __add__")
    __index__ = _raises("int subclass __index__")

    def __repr__(self):
        return "<int subclass>"


_JSON_SUBSTITUTES = (None, 5, 1.5, True, "x", "", [], {}, ["x"], {"x": 1})


def _substitutes(original):
    """JSON values, hostile values and near-misses of *original* for one position."""
    values = list(_JSON_SUBSTITUTES) + [
        _Hostile(), _HostileTyped(), _DictSub(), _ListSub(), _IntSub(1), _StrSub("x"),
        b"x", ("x",), {"x"}, float("nan"), float("inf"), 2 ** 70, -1, 0, "\ud800", "\x00", " ", "x" * 3000,
    ]
    if type(original) is str:
        values += [
            _StrSub(original), original + " ", " " + original, original + "\n", original.upper(),
            original[:-1], original + "\ud800",
        ]
    elif type(original) is dict:
        values += [_DictSub(original)]
    elif type(original) is list:
        values += [_ListSub(original), tuple(original)]
    elif type(original) is int:
        values += [_IntSub(original), float(original), str(original), original + 1]
    return values


def _nodes(value, path=()):
    yield path, value
    if type(value) is dict:
        for key, item in value.items():
            yield from _nodes(item, path + (key,))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _nodes(item, path + (index,))


def _at(node, path):
    for step in path:
        node = node[step]
    return node


def _replace_at(node, path, value):
    """A copy of *node* with *value* at *path*.  Only the path is copied: a hostile value is never copied."""
    if not path:
        return value
    copied = dict(node) if type(node) is dict else list(node)
    copied[path[0]] = _replace_at(node[path[0]], path[1:], value)
    return copied


def _without(node, path):
    if len(path) > 1:
        copied = dict(node) if type(node) is dict else list(node)
        copied[path[0]] = _without(node[path[0]], path[1:])
        return copied
    if type(node) is dict:
        return {key: item for key, item in node.items() if key != path[0]}
    return [item for index, item in enumerate(node) if index != path[0]]


def _rekey(node, path, new_key):
    """A copy of *node* whose key at *path* is *new_key*, with the same value in the same place."""
    if len(path) > 1:
        copied = dict(node) if type(node) is dict else list(node)
        copied[path[0]] = _rekey(node[path[0]], path[1:], new_key)
        return copied
    return {(new_key if key == path[0] else key): item for key, item in node.items()}


def _is_clock(value) -> bool:
    if type(value) is not str or _CLOCK.fullmatch(value) is None:
        return False
    try:
        datetime(
            int(value[0:4]), int(value[5:7]), int(value[8:10]),
            int(value[11:13]), int(value[14:16]), int(value[17:19]), tzinfo=timezone.utc,
        )
    except ValueError:
        return False
    return True


def _is_date(value) -> bool:
    if type(value) is not str or _DATE.fullmatch(value) is None:
        return False
    try:
        date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        return False
    return True


def _not_exact_json(value, path=()):
    kind = type(value)
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                yield path + (repr(key),)
            else:
                yield from _not_exact_json(item, path + (key,))
    elif kind is list:
        for index, item in enumerate(value):
            yield from _not_exact_json(item, path + (index,))
    elif kind is float:
        if value != value or value in (float("inf"), float("-inf")):
            yield path
    elif not (kind is str or kind is int or kind is bool or value is None):
        yield path


def _p2_violations(result, acceptance=None) -> list:
    """Everything property P2 demands of a returned result, as a list of what is wrong."""
    bad = []
    if type(result) is not dict or sorted(result) != sorted(_COMPARED + ("currentness_context",)):
        return ["result keys"]
    workspace, document, context = result["workspace"], result["document_metadata"], result["currentness_context"]
    release = workspace["sources"][0]
    raw = result["decoded_source"].encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    lifecycle = workspace["lifecycle"]
    try:
        address = preview_generation_identity({workspace["event_id"]: workspace}, workspace["generated_at"])
    except Exception as error:  # noqa: BLE001 - a workspace that cannot be addressed is itself the finding
        bad.append(f"generation id cannot be recomputed ({type(error).__name__})")
    else:
        if workspace["generation_id"] != address:
            bad.append("generation id is not the content address")
    if release["source_sha256"] != digest:
        bad.append("release digest is not the decoded text digest")
    if result["source_texts"] != {release["document_id"]: result["decoded_source"]}:
        bad.append("source_texts")
    if result["received_byte_receipt"] != {"sha256": digest, "length": len(raw), "declared_encoding": "utf-8"}:
        bad.append("receipt")
    if (document["content_sha256"], document["content_bytes"]) != (digest, len(raw)):
        bad.append("document metadata does not repeat the receipt")
    if (document["document_id"], document["filing_key"], document["event_id"]) != (
        release["document_id"], release["filing_key"], workspace["event_id"]
    ):
        bad.append("document metadata names another document, filing or event")
    if document["fetched_at"] != lifecycle["observed_at"]:
        bad.append("fetched_at is not the first observation")
    source_clocks = {
        document["published_at"], document["available_at"],
        lifecycle["source_available_at"], context["source_available_at"],
    }
    if len(source_clocks) != 1 or (acceptance is not None and source_clocks != {acceptance}):
        bad.append("source clocks")
    clocks = [workspace["generated_at"], lifecycle["observed_at"], *source_clocks]
    if not all(_is_clock(clock) for clock in clocks):
        bad.append("a clock is not canonical")
    elif lifecycle["observed_at"] < lifecycle["source_available_at"]:
        bad.append("first observation precedes the source")
    if type(document["revision"]) is not int or document["revision"] < 1:
        bad.append("revision")
    elif (document["revision"] == 1) != (document["supersedes_document_id"] is None):
        bad.append("revision and supersedes disagree")
    if document["supersedes_document_id"] == document["document_id"]:
        bad.append("a document supersedes itself")
    if lifecycle["state"] not in ("complete", "corrected"):
        bad.append("lifecycle state")
    if sorted(context) != ["currentness", "fiscal_scope", "profile_version", "source_available_at"]:
        bad.append("currentness_context keys")
    scope = context["fiscal_scope"]
    if type(scope) is not tuple or len(scope) != 4 or not all(_is_date(item) for item in scope):
        bad.append("fiscal_scope")
    current = context["currentness"]
    if current is not None:
        if type(current) is not dict or sorted(current) != ["source_clock", "state"]:
            bad.append("currentness shape")
        elif current["state"] == "currentness_unverified":
            if current["source_clock"] is not None:
                bad.append("an unverified currentness carries a clock")
        elif not _is_clock(current["source_clock"]):
            bad.append("a verified currentness has no canonical clock")
    for path in _not_exact_json(result):
        if path != ("currentness_context", "fiscal_scope"):
            bad.append("not an exact JSON type at " + "/".join(map(str, path)))
    return bad


def _outcome(acquisition, prior, observed_at, label=""):
    """``(reason, detail, None)`` for a typed refusal, ``("returned", None, result)`` for a result.

    Anything else that leaves the preparation fails the test, and every returned result is held to P2.
    """
    try:
        result = prepare_pg_workspace(acquisition, prior=prior, observed_at=observed_at)
    except PgPreparationRefused as error:
        assert type(error) is PgPreparationRefused, label
        assert error.reason in PG_PREPARATION_REFUSALS, label
        assert type(error.detail) is str and error.detail, label
        assert str(error) == _R5_MESSAGES[error.reason], label
        return error.reason, error.detail, None
    except Exception as error:  # noqa: BLE001 - the sweep exists to catch exactly this
        pytest.fail(f"{label}: {type(error).__name__} left the preparation: {error}")
    # A returned result proves the acquisition was an exact mapping with string keys: reading it is safe now.
    assert _p2_violations(result, acquisition["acceptance_datetime"]) == [], label
    return "returned", None, result


def _refusal(acquisition, prior, observed_at):
    reason, detail, _ = _outcome(acquisition, prior, observed_at)
    return reason, detail


def _native_document(payload: dict) -> SourceDocument:
    def clock(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    return SourceDocument(
        document_id=payload["document_id"],
        event_id=payload["event_id"],
        document_kind=payload["document_kind"],
        source_class=payload["source_class"],
        content_sha256=payload["content_sha256"],
        revision=payload["revision"],
        content_bytes=payload["content_bytes"],
        filing_key=FilingKey(cik=payload["filing_key"]["cik"], accession=payload["filing_key"]["accession"]),
        fetched_at=clock(payload["fetched_at"]),
        published_at=clock(payload["published_at"]),
        available_at=clock(payload["available_at"]),
        supersedes_document_id=payload["supersedes_document_id"],
        superseded_by_document_id=payload["superseded_by_document_id"],
        rights_profile=payload["rights_profile"],
        rights_state=payload["rights_state"],
        presented_fiscal_label=payload["presented_fiscal_label"],
        holds_bytes=payload["holds_bytes"],
    )


@pytest.fixture(scope="module")
def chain():
    """The chain scenarios.  Each entry is ``(acquisition, prior, observed_at, result)``; never mutate one.

    Along every path the acceptance clock never decreases (R6.1).
    """
    a = _acquired("same_source_rebuild")
    a_in_place = _with_body(a, a["exhibit_body"].replace("</body>", "<p>Synthetic correction in place.</p></body>"))
    b = _acquired("changed_bytes")
    c = _with_body(b, b["exhibit_body"].replace("</body>", "<p>Second synthetic correction.</p></body>"))
    assert c["exhibit_body"] != b["exhibit_body"] and a["exhibit_body"] != b["exhibit_body"]
    assert a_in_place["exhibit_body"] not in (a["exhibit_body"], b["exhibit_body"], c["exhibit_body"])
    refiled = dict(a, accession=fixture_accession("changed"))
    refiled_correction = dict(b, accession=fixture_accession("amended"))
    amendment = _acquired("amendment_sequence")
    moved = dict(a, exhibit_url=a["exhibit_url"] + "?moved=1")
    steps = {}

    def step(name, acquisition, prior, observed_at):
        prior_result = None if prior is None else steps[prior][3]
        steps[name] = (
            acquisition, prior_result, observed_at,
            prepare_pg_workspace(acquisition, prior=prior_result, observed_at=observed_at),
        )

    step("root", a, None, "2026-07-29T17:10:00Z")
    step("changed_in_place", a_in_place, "root", "2026-07-30T09:00:00Z")
    step("back_to_first", a, "changed_in_place", "2026-07-31T11:00:00Z")
    step("changed", b, "root", "2026-07-30T17:20:00Z")
    step("changed_twice", c, "changed", "2026-07-31T10:00:00Z")
    step("refiled", refiled, "root", "2026-07-29T17:20:00Z")
    step("refiled_after_correction", refiled_correction, "changed", "2026-07-31T12:00:00Z")
    step("amendment", amendment, "root", "2026-07-30T18:01:00Z")
    step("moved_url", moved, "root", "2026-07-29T19:00:00Z")
    return steps


_SCENARIOS = (
    "root", "changed_in_place", "back_to_first", "changed", "changed_twice", "refiled", "refiled_after_correction",
    "amendment", "moved_url",
)
_BAD_CLOCKS = (
    None, "", 20260729, "2026-07-29", "2026-07-29T17:20:00", "2026-07-29T17:20:00+00:00", "2026-07-29 17:20:00Z",
    "2026-07-29t17:20:00Z", "2026-07-29T17:20:00z", "2026-07-29T17:20:00.000Z", "2026-7-29T17:20:00Z",
    "2026-13-01T00:00:00Z", "2026-02-30T00:00:00Z", "2026-07-29T24:00:00Z", "2026-07-29T17:60:00Z",
    "2026-07-29T17:20:60Z", "0000-07-29T17:20:00Z", "２０２６-07-29T17:20:00Z",
    " 2026-07-29T17:20:00Z", "2026-07-29T17:20:00Z\n", "2026-07-29T17:20:00ZZ",
)


def _bad_clocks():
    return list(_BAD_CLOCKS) + [
        _StrSub("2026-07-29T17:20:00Z"), datetime(2026, 7, 29, 17, 20, tzinfo=timezone.utc), _Hostile(), _HostileTyped(),
    ]


# -- R5.2 / R5.3: the acquisition rows --------------------------------------------------------

_SHA = "a" * 64
_ACQUISITION_ROWS = [
    # (row, what is wrong, mutation of a fresh acquisition, reason, detail)
    (1, "None", lambda a: None, "malformed_acquisition", "acquisition"),
    (1, "a list", lambda a: [a], "malformed_acquisition", "acquisition"),
    (1, "a string", lambda a: "acquisition", "malformed_acquisition", "acquisition"),
    (1, "a dict subclass", lambda a: type("Mapping", (dict,), {})(a), "malformed_acquisition", "acquisition"),
    (1, "an integer key", lambda a: {**a, 1: "x"}, "malformed_acquisition", "acquisition"),
    (1, "a str subclass key", lambda a: {**a, _StrKey("extra"): "x"}, "malformed_acquisition", "acquisition"),
    (2, "no acceptance", lambda a: _without(a, ("acceptance_datetime",)), "malformed_source_clock", "acquisition.acceptance_datetime"),
    (3, "no body", lambda a: _without(a, ("exhibit_body",)), "malformed_acquisition", "acquisition.exhibit_body"),
    (3, "body None", lambda a: {**a, "exhibit_body": None}, "malformed_acquisition", "acquisition.exhibit_body"),
    (3, "body empty", lambda a: {**a, "exhibit_body": ""}, "malformed_acquisition", "acquisition.exhibit_body"),
    (3, "body blank", lambda a: {**a, "exhibit_body": " \n\t "}, "malformed_acquisition", "acquisition.exhibit_body"),
    (3, "body bytes", lambda a: {**a, "exhibit_body": b"<html></html>"}, "malformed_acquisition", "acquisition.exhibit_body"),
    (3, "body str subclass", lambda a: {**a, "exhibit_body": _StrSub(a["exhibit_body"])}, "malformed_acquisition", "acquisition.exhibit_body"),
    (4, "body lone surrogate", lambda a: {**a, "exhibit_body": a["exhibit_body"] + "\ud800"}, "non_utf8_source", "acquisition.exhibit_body"),
    (5, "no cik", lambda a: _without(a, ("cik",)), "unadmitted_issuer", "acquisition.cik"),
    (5, "cik None", lambda a: {**a, "cik": None}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik empty", lambda a: {**a, "cik": ""}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik unpadded", lambda a: {**a, "cik": "80424"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik nine digits", lambda a: {**a, "cik": "000008042"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik eleven digits", lambda a: {**a, "cik": "00000804240"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik a letter", lambda a: {**a, "cik": "000008042x"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik full-width digits", lambda a: {**a, "cik": "０" * 5 + "８０４２４"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik integer", lambda a: {**a, "cik": 80424}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik padded with a space", lambda a: {**a, "cik": " 0000080424"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik trailing newline", lambda a: {**a, "cik": "0000080424\n"}, "unadmitted_issuer", "acquisition.cik"),
    (5, "cik str subclass", lambda a: {**a, "cik": _StrSub("0000080424")}, "unadmitted_issuer", "acquisition.cik"),
    (6, "no accession", lambda a: _without(a, ("accession",)), "malformed_acquisition", "acquisition.accession"),
    (6, "accession None", lambda a: {**a, "accession": None}, "malformed_acquisition", "acquisition.accession"),
    (6, "accession short", lambda a: {**a, "accession": "0000080424-26-00001"}, "malformed_acquisition", "acquisition.accession"),
    (6, "accession undashed", lambda a: {**a, "accession": "000008042426000001"}, "malformed_acquisition", "acquisition.accession"),
    (6, "accession trailing space", lambda a: {**a, "accession": a["accession"] + " "}, "malformed_acquisition", "acquisition.accession"),
    (6, "accession str subclass", lambda a: {**a, "accession": _StrSub(a["accession"])}, "malformed_acquisition", "acquisition.accession"),
    (7, "no form", lambda a: _without(a, ("form",)), "malformed_acquisition", "acquisition.form"),
    (7, "form None", lambda a: {**a, "form": None}, "malformed_acquisition", "acquisition.form"),
    (7, "form lower case", lambda a: {**a, "form": "8-k"}, "malformed_acquisition", "acquisition.form"),
    (7, "form trailing space", lambda a: {**a, "form": "8-K "}, "malformed_acquisition", "acquisition.form"),
    (7, "form 10-Q", lambda a: {**a, "form": "10-Q"}, "malformed_acquisition", "acquisition.form"),
    (7, "form 8-K/A/A", lambda a: {**a, "form": "8-K/A/A"}, "malformed_acquisition", "acquisition.form"),
    (7, "form a list", lambda a: {**a, "form": ["8-K"]}, "malformed_acquisition", "acquisition.form"),
    (7, "form str subclass", lambda a: {**a, "form": _StrSub("8-K")}, "malformed_acquisition", "acquisition.form"),
    (10, "no url", lambda a: _without(a, ("exhibit_url",)), "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url None", lambda a: {**a, "exhibit_url": None}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url empty", lambda a: {**a, "exhibit_url": ""}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url with a space", lambda a: {**a, "exhibit_url": "https://www.sec.gov/a b"}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url with a newline", lambda a: {**a, "exhibit_url": a["exhibit_url"] + "\n"}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url not ASCII", lambda a: {**a, "exhibit_url": "https://www.sec.gov/é"}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url 2049 characters", lambda a: {**a, "exhibit_url": "https://www.sec.gov/" + "a" * 2029}, "malformed_acquisition", "acquisition.exhibit_url"),
    (10, "url str subclass", lambda a: {**a, "exhibit_url": _StrSub(a["exhibit_url"])}, "malformed_acquisition", "acquisition.exhibit_url"),
    (11, "currentness None", lambda a: {**a, "currentness": None}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness a string", lambda a: {**a, "currentness": "up_to_date"}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness empty", lambda a: {**a, "currentness": {}}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness without checked_at", lambda a: {**a, "currentness": {"state": "up_to_date"}}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness without state", lambda a: {**a, "currentness": {"checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness with a third key", lambda a: {**a, "currentness": {"state": "up_to_date", "checked_at": "2026-07-29T17:20:00Z", "extra": 1}}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness a dict subclass", lambda a: {**a, "currentness": type("Mapping", (dict,), {})(state="up_to_date", checked_at="2026-07-29T17:20:00Z")}, "malformed_currentness", "acquisition.currentness"),
    (11, "currentness with a str subclass key", lambda a: {**a, "currentness": {"state": "up_to_date", _StrKey("checked_at"): "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness"),
    (12, "state None", lambda a: {**a, "currentness": {"state": None, "checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness.state"),
    (12, "state upper case", lambda a: {**a, "currentness": {"state": "UP_TO_DATE", "checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness.state"),
    (12, "state unknown", lambda a: {**a, "currentness": {"state": "unverified", "checked_at": None}}, "malformed_currentness", "acquisition.currentness.state"),
    (12, "state trailing space", lambda a: {**a, "currentness": {"state": "up_to_date ", "checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness.state"),
    (12, "state str subclass", lambda a: {**a, "currentness": {"state": _StrSub("up_to_date"), "checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness.state"),
    (13, "up_to_date without a clock", lambda a: {**a, "currentness": {"state": "up_to_date", "checked_at": None}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (13, "pending without a clock", lambda a: {**a, "currentness": {"state": "newer_source_pending", "checked_at": None}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (13, "unverified with a clock", lambda a: {**a, "currentness": {"state": "currentness_unverified", "checked_at": "2026-07-29T17:20:00Z"}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (13, "unverified with an empty string", lambda a: {**a, "currentness": {"state": "currentness_unverified", "checked_at": ""}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (13, "unverified with zero", lambda a: {**a, "currentness": {"state": "currentness_unverified", "checked_at": 0}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (13, "unverified with False", lambda a: {**a, "currentness": {"state": "currentness_unverified", "checked_at": False}}, "malformed_currentness", "acquisition.currentness.checked_at"),
    (14, "no receipt", lambda a: _without(a, ("received_bytes",)), "missing_received_byte_receipt", "acquisition.received_bytes"),
    (14, "receipt None", lambda a: {**a, "received_bytes": None}, "missing_received_byte_receipt", "acquisition.received_bytes"),
    (14, "receipt a list", lambda a: {**a, "received_bytes": []}, "missing_received_byte_receipt", "acquisition.received_bytes"),
    (14, "receipt a dict subclass", lambda a: {**a, "received_bytes": type("Mapping", (dict,), {})(a["received_bytes"])}, "missing_received_byte_receipt", "acquisition.received_bytes"),
    (14, "receipt with an integer key", lambda a: {**a, "received_bytes": {**a["received_bytes"], 1: 2}}, "missing_received_byte_receipt", "acquisition.received_bytes"),
    (15, "receipt empty", lambda a: {**a, "received_bytes": {}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest None", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": None}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest upper case", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": a["received_bytes"]["sha256"].upper().replace("0", "A")}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest 63 characters", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": _SHA[:63]}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest 65 characters", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": _SHA + "a"}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest not hex", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": "g" * 64}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (15, "digest str subclass", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": _StrSub(a["received_bytes"]["sha256"])}}, "missing_received_byte_receipt", "acquisition.received_bytes.sha256"),
    (16, "no length", lambda a: {**a, "received_bytes": {"sha256": a["received_bytes"]["sha256"]}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (16, "length negative", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": -1}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (16, "length True", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": True}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (16, "length a float", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": float(a["received_bytes"]["length"])}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (16, "length a string", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": str(a["received_bytes"]["length"])}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (16, "length int subclass", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": _IntSub(a["received_bytes"]["length"])}}, "missing_received_byte_receipt", "acquisition.received_bytes.length"),
    (17, "no declared encoding", lambda a: _without(a, ("declared_encoding",)), "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding None", lambda a: {**a, "declared_encoding": None}, "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding upper case", lambda a: {**a, "declared_encoding": "UTF-8"}, "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding utf8", lambda a: {**a, "declared_encoding": "utf8"}, "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding latin-1", lambda a: {**a, "declared_encoding": "latin-1"}, "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding bytes", lambda a: {**a, "declared_encoding": b"utf-8"}, "non_utf8_source", "acquisition.declared_encoding"),
    (17, "encoding str subclass", lambda a: {**a, "declared_encoding": _StrSub("utf-8")}, "non_utf8_source", "acquisition.declared_encoding"),
    (21, "receipt of other bytes", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": hashlib.sha256(b"other").hexdigest()}}, "received_bytes_mismatch", "acquisition.received_bytes"),
    (21, "receipt one byte long", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": a["received_bytes"]["length"] + 1}}, "received_bytes_mismatch", "acquisition.received_bytes"),
    (22, "a ten-digit CIK the registry does not admit", lambda a: {**a, "cik": "0000000001"}, "unadmitted_issuer", "acquisition.cik"),
    (23, "a year the fiscal calendar cannot hold", lambda a: {**a, "acceptance_datetime": "0001-01-01T00:00:00Z"}, "malformed_source_clock", "acquisition.acceptance_datetime"),
    (24, "period signals of another quarter", lambda a: _with_body(a, "<h1>Second Quarter Ended March 31, 2027</h1>"), "document_period_not_admitted", "acquisition.exhibit_body"),
]


@pytest.mark.parametrize(
    ("mutate", "reason", "detail"),
    [row[2:] for row in _ACQUISITION_ROWS],
    ids=[f"row{row[0]}-{row[1]}" for row in _ACQUISITION_ROWS],
)
def test_every_acquisition_row_refuses_with_its_reason_and_position(mutate, reason, detail):
    acquisition = mutate(_acquired("same_source_rebuild"))
    assert _refusal(acquisition, None, "2026-07-29T17:20:00Z") == (reason, detail)


@pytest.mark.parametrize("name", ["filing_date", "report_date"])
def test_a_filing_date_is_a_real_date_or_a_typed_absence(name):
    acquisition = _acquired("same_source_rebuild")
    bad_dates = [
        None, 20260729, "2026-7-29", "2026-02-30", "2026-13-01", "20260729", "2026-07-29T00:00:00Z", " ",
        "0000-01-01", "2026-07-29\n", "２０２６-07-29", _StrSub("2026-07-29"),
    ]
    for bad in bad_dates:
        assert _refusal({**acquisition, name: bad}, None, "2026-07-29T17:20:00Z") == (
            "malformed_acquisition", f"acquisition.{name}"
        ), repr(bad)
    assert _refusal(_without(acquisition, (name,)), None, "2026-07-29T17:20:00Z") == (
        "malformed_acquisition", f"acquisition.{name}"
    )
    for good in ("", "2024-02-29", "0001-01-01", "9999-12-31"):
        reason, _, result = _outcome({**acquisition, name: good}, None, "2026-07-29T17:20:00Z")
        assert reason == "returned", good
        assert _p2_violations(result, acquisition["acceptance_datetime"]) == []


def test_one_canonical_clock_is_read_at_every_clock_position(chain):
    acquisition, _, _, root = chain["root"]
    positions = (
        (lambda bad: ({**acquisition, "acceptance_datetime": bad}, None, "2026-07-29T17:20:00Z"),
         ("malformed_source_clock", "acquisition.acceptance_datetime")),
        (lambda bad: (acquisition, None, bad), ("malformed_observation_clock", "observed_at")),
        (lambda bad: ({**acquisition, "currentness": {"state": "up_to_date", "checked_at": bad}}, None, "2026-07-29T17:20:00Z"),
         ("malformed_currentness", "acquisition.currentness.checked_at")),
        (lambda bad: (acquisition, _replace_at(root, ("workspace", "lifecycle", "observed_at"), bad), "2026-07-29T17:20:00Z"),
         ("malformed_prior", "prior.workspace.lifecycle.observed_at")),
        (lambda bad: (acquisition, _replace_at(root, ("workspace", "lifecycle", "source_available_at"), bad), "2026-07-29T17:20:00Z"),
         ("malformed_prior", "prior.workspace.lifecycle.source_available_at")),
    )
    for build, expected in positions:
        for bad in _bad_clocks():
            assert _refusal(*build(bad)) == expected, (expected, bad)
    # Positive control: the canonical form is admitted at each position, so the refusals above are about form.
    for build, _expected in positions:
        assert _outcome(*build("2026-07-29T17:10:00Z"))[0] == "returned"


def test_the_url_bound_and_the_keys_the_table_does_not_name(chain):
    acquisition, _, _, root = chain["root"]
    longest = {**acquisition, "exhibit_url": "https://www.sec.gov/" + "a" * 2028}
    assert len(longest["exhibit_url"]) == 2048
    assert _outcome(longest, None, "2026-07-29T17:10:00Z")[0] == "returned"
    # `items` and any other key the admission table does not name are never read.
    for extra in ({"items": _Hostile()}, {"items": _HostileTyped()}, {"unnamed": _Hostile()}, {"items": None}):
        reason, _, result = _outcome({**acquisition, **extra}, None, "2026-07-29T17:10:00Z")
        assert reason == "returned"
        assert result == root
    # The acquisition's own key order does not matter.
    reordered = dict(reversed(list(acquisition.items())))
    assert _outcome(reordered, None, "2026-07-29T17:10:00Z")[2] == root


def test_observed_at_is_not_earlier_than_the_acceptance():
    acquisition = _acquired("same_source_rebuild")
    assert acquisition["acceptance_datetime"] == "2026-07-29T17:10:00Z"
    assert _refusal(acquisition, None, "2026-07-29T17:09:59Z") == ("malformed_observation_clock", "observed_at")
    assert _outcome(acquisition, None, "2026-07-29T17:10:00Z")[0] == "returned"
    assert _outcome(acquisition, None, "9999-12-31T23:59:59Z")[0] == "returned"


def test_a_native_refusal_is_typed_with_its_class_name():
    # The native fiscal period admits no fiscal year 10000 and none before its floor; the admission table has no
    # row for either, so the backstop types the native refusal.
    for acceptance in ("9999-12-31T23:59:59Z", "1990-05-01T00:00:00Z"):
        with pytest.raises(PgPreparationRefused) as caught:
            prepare_pg_workspace(_quarter(acceptance, "999"), prior=None, observed_at="9999-12-31T23:59:59Z")
        assert type(caught.value) is PgPreparationRefused
        assert (caught.value.reason, caught.value.detail) == ("workspace_build_refused", "ContractError")
        assert type(caught.value.__cause__).__name__ == "ContractError"
        assert ValueError in type(caught.value.__cause__).__mro__
    # Positive control: the same synthetic filing in an admitted year is prepared.
    assert _outcome(_quarter("2026-04-24T17:00:00Z", "999"), None, "2026-04-24T17:30:00Z")[0] == "returned"


# -- R5.4: the prior rows ----------------------------------------------------------------------

_W, _D = ("workspace",), ("document_metadata",)
_RELEASE = _W + ("sources", 0)
_PRIOR_ROWS = [
    # (row, what is wrong, mutation of the root result used as the prior, reason, detail)
    (1, "a list", lambda p: [p], "malformed_prior", "prior"),
    (1, "a string", lambda p: "prior", "malformed_prior", "prior"),
    (1, "an integer", lambda p: 5, "malformed_prior", "prior"),
    (1, "a dict subclass", lambda p: type("Mapping", (dict,), {})(p), "malformed_prior", "prior"),
    (1, "an integer key", lambda p: {**p, 1: "x"}, "malformed_prior", "prior"),
    (1, "a str subclass key", lambda p: _rekey(p, ("decoded_source",), _StrKey("decoded_source")), "malformed_prior", "prior"),
    (2, "empty", lambda p: {}, "malformed_prior", "prior.workspace"),
    (2, "the bare workspace", lambda p: p["workspace"], "malformed_prior", "prior.workspace"),
    (2, "workspace None", lambda p: _replace_at(p, _W, None), "malformed_prior", "prior.workspace"),
    (2, "workspace a list", lambda p: _replace_at(p, _W, [p["workspace"]]), "malformed_prior", "prior.workspace"),
    (2, "workspace a dict subclass", lambda p: _replace_at(p, _W, type("Mapping", (dict,), {})(p["workspace"])), "malformed_prior", "prior.workspace"),
    (3, "no document metadata", lambda p: _without(p, _D), "malformed_prior", "prior.document_metadata"),
    (3, "document metadata None", lambda p: _replace_at(p, _D, None), "malformed_prior", "prior.document_metadata"),
    (3, "document metadata a dict subclass", lambda p: _replace_at(p, _D, type("Mapping", (dict,), {})(p["document_metadata"])), "malformed_prior", "prior.document_metadata"),
    (4, "no event id", lambda p: _without(p, _W + ("event_id",)), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id None", lambda p: _replace_at(p, _W + ("event_id",), None), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id empty", lambda p: _replace_at(p, _W + ("event_id",), ""), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id with a space", lambda p: _replace_at(p, _W + ("event_id",), "evt a"), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id 129 characters", lambda p: _replace_at(p, _W + ("event_id",), "e" * 129), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id not ASCII", lambda p: _replace_at(p, _W + ("event_id",), "evt_é"), "malformed_prior", "prior.workspace.event_id"),
    (4, "event id str subclass", lambda p: _replace_at(p, _W + ("event_id",), _StrSub(p["workspace"]["event_id"])), "malformed_prior", "prior.workspace.event_id"),
    (5, "no fiscal period", lambda p: _without(p, _W + ("fiscal_period",)), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "fiscal period a list", lambda p: _replace_at(p, _W + ("fiscal_period",), [2026, 4]), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "no year", lambda p: _without(p, _W + ("fiscal_period", "year")), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "no quarter", lambda p: _without(p, _W + ("fiscal_period", "quarter")), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "year a string", lambda p: _replace_at(p, _W + ("fiscal_period", "year"), "2026"), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "year a float", lambda p: _replace_at(p, _W + ("fiscal_period", "year"), 2026.0), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "year True", lambda p: _replace_at(p, _W + ("fiscal_period", "year"), True), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "year int subclass", lambda p: _replace_at(p, _W + ("fiscal_period", "year"), _IntSub(2026)), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "quarter zero", lambda p: _replace_at(p, _W + ("fiscal_period", "quarter"), 0), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "quarter five", lambda p: _replace_at(p, _W + ("fiscal_period", "quarter"), 5), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "quarter True", lambda p: _replace_at(p, _W + ("fiscal_period", "quarter"), True), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "quarter int subclass", lambda p: _replace_at(p, _W + ("fiscal_period", "quarter"), _IntSub(4)), "malformed_prior", "prior.workspace.fiscal_period"),
    (5, "fiscal period a dict subclass", lambda p: _replace_at(p, _W + ("fiscal_period",), type("Mapping", (dict,), {})(p["workspace"]["fiscal_period"])), "malformed_prior", "prior.workspace.fiscal_period"),
    (6, "no lifecycle", lambda p: _without(p, _W + ("lifecycle",)), "malformed_prior", "prior.workspace.lifecycle"),
    (6, "lifecycle a string", lambda p: _replace_at(p, _W + ("lifecycle",), "complete"), "malformed_prior", "prior.workspace.lifecycle"),
    (6, "lifecycle a dict subclass", lambda p: _replace_at(p, _W + ("lifecycle",), type("Mapping", (dict,), {})(p["workspace"]["lifecycle"])), "malformed_prior", "prior.workspace.lifecycle"),
    (7, "no first observation", lambda p: _without(p, _W + ("lifecycle", "observed_at")), "malformed_prior", "prior.workspace.lifecycle.observed_at"),
    ("7a", "no source clock", lambda p: _without(p, _W + ("lifecycle", "source_available_at")), "malformed_prior", "prior.workspace.lifecycle.source_available_at"),
    ("7a", "source clock None", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), None), "malformed_prior", "prior.workspace.lifecycle.source_available_at"),
    ("7a", "source clock with an offset", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), "2026-07-29T17:10:00+00:00"), "malformed_prior", "prior.workspace.lifecycle.source_available_at"),
    ("7a", "source clock a date", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), "2026-07-29"), "malformed_prior", "prior.workspace.lifecycle.source_available_at"),
    ("7a", "source clock str subclass", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), _StrSub("2026-07-29T17:10:00Z")), "malformed_prior", "prior.workspace.lifecycle.source_available_at"),
    (8, "no state", lambda p: _without(p, _W + ("lifecycle", "state")), "malformed_prior", "prior.workspace.lifecycle.state"),
    (8, "state None", lambda p: _replace_at(p, _W + ("lifecycle", "state"), None), "malformed_prior", "prior.workspace.lifecycle.state"),
    (8, "state capitalised", lambda p: _replace_at(p, _W + ("lifecycle", "state"), "Complete"), "malformed_prior", "prior.workspace.lifecycle.state"),
    (8, "state pending", lambda p: _replace_at(p, _W + ("lifecycle", "state"), "pending"), "malformed_prior", "prior.workspace.lifecycle.state"),
    (8, "state trailing space", lambda p: _replace_at(p, _W + ("lifecycle", "state"), "corrected "), "malformed_prior", "prior.workspace.lifecycle.state"),
    (8, "state str subclass", lambda p: _replace_at(p, _W + ("lifecycle", "state"), _StrSub("complete")), "malformed_prior", "prior.workspace.lifecycle.state"),
    (9, "no sources", lambda p: _without(p, _W + ("sources",)), "malformed_prior", "prior.workspace.sources"),
    (9, "sources a mapping", lambda p: _replace_at(p, _W + ("sources",), {}), "malformed_prior", "prior.workspace.sources"),
    (9, "sources a tuple", lambda p: _replace_at(p, _W + ("sources",), tuple(p["workspace"]["sources"])), "malformed_prior", "prior.workspace.sources"),
    (9, "sources a list subclass", lambda p: _replace_at(p, _W + ("sources",), _ListSub(p["workspace"]["sources"])), "malformed_prior", "prior.workspace.sources"),
    (10, "sources empty", lambda p: _replace_at(p, _W + ("sources",), []), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "sources of strings", lambda p: _replace_at(p, _W + ("sources",), ["issuer_release"]), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "no release row", lambda p: _replace_at(p, _RELEASE + ("kind",), "transcript"), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "release kind capitalised", lambda p: _replace_at(p, _RELEASE + ("kind",), "Issuer_Release"), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "release kind str subclass", lambda p: _replace_at(p, _RELEASE + ("kind",), _StrSub("issuer_release")), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "release row a dict subclass", lambda p: _replace_at(p, _RELEASE, type("Mapping", (dict,), {})(p["workspace"]["sources"][0])), "prior_source_identity_missing", "prior.workspace.sources"),
    (10, "release row with a str subclass key", lambda p: _rekey(p, _RELEASE + ("kind",), _StrKey("kind")), "prior_source_identity_missing", "prior.workspace.sources"),
    (11, "no filing key", lambda p: _without(p, _RELEASE + ("filing_key",)), "prior_source_identity_missing", "prior.workspace.sources.filing_key"),
    (11, "filing key a string", lambda p: _replace_at(p, _RELEASE + ("filing_key",), "0000080424"), "prior_source_identity_missing", "prior.workspace.sources.filing_key"),
    (12, "no filing cik", lambda p: _without(p, _RELEASE + ("filing_key", "cik")), "prior_source_identity_missing", "prior.workspace.sources.filing_key.cik"),
    (12, "filing cik unpadded", lambda p: _replace_at(p, _RELEASE + ("filing_key", "cik"), "80424"), "prior_source_identity_missing", "prior.workspace.sources.filing_key.cik"),
    (12, "filing cik str subclass", lambda p: _replace_at(p, _RELEASE + ("filing_key", "cik"), _StrSub("0000080424")), "prior_source_identity_missing", "prior.workspace.sources.filing_key.cik"),
    (13, "no filing accession", lambda p: _without(p, _RELEASE + ("filing_key", "accession")), "prior_source_identity_missing", "prior.workspace.sources.filing_key.accession"),
    (13, "filing accession malformed", lambda p: _replace_at(p, _RELEASE + ("filing_key", "accession"), "000008042426000001"), "prior_source_identity_missing", "prior.workspace.sources.filing_key.accession"),
    (14, "no release digest", lambda p: _without(p, _RELEASE + ("source_sha256",)), "prior_source_identity_missing", "prior.workspace.sources.source_sha256"),
    (14, "release digest upper case", lambda p: _replace_at(p, _RELEASE + ("source_sha256",), "A" * 64), "prior_source_identity_missing", "prior.workspace.sources.source_sha256"),
    (14, "release digest 63 characters", lambda p: _replace_at(p, _RELEASE + ("source_sha256",), _SHA[:63]), "prior_source_identity_missing", "prior.workspace.sources.source_sha256"),
    (15, "no release document id", lambda p: _without(p, _RELEASE + ("document_id",)), "prior_source_identity_missing", "prior.workspace.sources.document_id"),
    (15, "release document id empty", lambda p: _replace_at(p, _RELEASE + ("document_id",), ""), "prior_source_identity_missing", "prior.workspace.sources.document_id"),
    (15, "release document id with a space", lambda p: _replace_at(p, _RELEASE + ("document_id",), "doc a"), "prior_source_identity_missing", "prior.workspace.sources.document_id"),
    (16, "no metadata document id", lambda p: _without(p, _D + ("document_id",)), "malformed_prior", "prior.document_metadata.document_id"),
    (16, "metadata names another document", lambda p: _replace_at(p, _D + ("document_id",), "doc_other"), "malformed_prior", "prior.document_metadata.document_id"),
    (16, "release names another document", lambda p: _replace_at(p, _RELEASE + ("document_id",), "doc_other"), "malformed_prior", "prior.document_metadata.document_id"),
    (16, "metadata document id str subclass", lambda p: _replace_at(p, _D + ("document_id",), _StrSub(p["document_metadata"]["document_id"])), "malformed_prior", "prior.document_metadata.document_id"),
    (17, "no metadata event id", lambda p: _without(p, _D + ("event_id",)), "malformed_prior", "prior.document_metadata.event_id"),
    (17, "metadata names another event", lambda p: _replace_at(p, _D + ("event_id",), "evt_other"), "malformed_prior", "prior.document_metadata.event_id"),
    (17, "workspace names another event", lambda p: _replace_at(p, _W + ("event_id",), "evt_other"), "malformed_prior", "prior.document_metadata.event_id"),
    (18, "no revision", lambda p: _without(p, _D + ("revision",)), "malformed_prior", "prior.document_metadata.revision"),
    (18, "revision zero", lambda p: _replace_at(p, _D + ("revision",), 0), "malformed_prior", "prior.document_metadata.revision"),
    (18, "revision True", lambda p: _replace_at(p, _D + ("revision",), True), "malformed_prior", "prior.document_metadata.revision"),
    (18, "revision a float", lambda p: _replace_at(p, _D + ("revision",), 1.0), "malformed_prior", "prior.document_metadata.revision"),
    (18, "revision a string", lambda p: _replace_at(p, _D + ("revision",), "1"), "malformed_prior", "prior.document_metadata.revision"),
    (18, "revision int subclass", lambda p: _replace_at(p, _D + ("revision",), _IntSub(1)), "malformed_prior", "prior.document_metadata.revision"),
    (19, "a root that supersedes", lambda p: _replace_at(p, _D + ("supersedes_document_id",), "doc_other"), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (19, "a root that supersedes the empty string", lambda p: _replace_at(p, _D + ("supersedes_document_id",), ""), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (19, "a root that supersedes False", lambda p: _replace_at(p, _D + ("supersedes_document_id",), False), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (19, "revision 2 that supersedes nothing", lambda p: _replace_at(p, _D + ("revision",), 2), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (19, "revision 2 that supersedes itself", lambda p: _replace_at(_replace_at(p, _D + ("revision",), 2), _D + ("supersedes_document_id",), p["document_metadata"]["document_id"]), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (19, "revision 2 that supersedes a blank", lambda p: _replace_at(_replace_at(p, _D + ("revision",), 2), _D + ("supersedes_document_id",), "doc a"), "malformed_prior", "prior.document_metadata.supersedes_document_id"),
    (25, "another issuer", lambda p: _replace_at(p, _RELEASE + ("filing_key", "cik"), "0000000001"), "malformed_prior", "prior.workspace.sources.filing_key.cik"),
    (26, "a later fiscal year", lambda p: _replace_at(p, _W + ("fiscal_period", "year"), 2027), "source_precedes_prior_event", "prior.workspace.fiscal_period"),
    (26, "a later fiscal quarter", lambda p: _replace_at(_replace_at(p, _W + ("fiscal_period", "year"), 2027), _W + ("fiscal_period", "quarter"), 1), "source_precedes_prior_event", "prior.workspace.fiscal_period"),
    ("26a", "a source accepted one second after this acquisition", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), "2026-07-29T17:10:01Z"), "source_precedes_prior_event", "prior.workspace.lifecycle.source_available_at"),
    ("26a", "a source accepted a day after this acquisition", lambda p: _replace_at(p, _W + ("lifecycle", "source_available_at"), "2026-07-30T18:00:00Z"), "source_precedes_prior_event", "prior.workspace.lifecycle.source_available_at"),
    (27, "a carried first observation before the acceptance", lambda p: _replace_at(p, _W + ("lifecycle", "observed_at"), "2026-07-29T17:09:59Z"), "malformed_prior", "prior.workspace.lifecycle.observed_at"),
    (30, "an earlier period under this event's id", lambda p: _replace_at(p, _W + ("fiscal_period", "quarter"), 3), "malformed_prior", "prior.workspace.event_id"),
    (30, "this period under another event's id", lambda p: _replace_at(_replace_at(p, _W + ("event_id",), "evt_other"), _D + ("event_id",), "evt_other"), "malformed_prior", "prior.workspace.event_id"),
    (31, "this document id under another accession", lambda p: _replace_at(p, _RELEASE + ("filing_key", "accession"), "0000080424-26-000006"), "malformed_prior", "prior.workspace.sources.document_id"),
    (31, "this document id under another text", lambda p: _replace_at(p, _RELEASE + ("source_sha256",), _SHA), "malformed_prior", "prior.workspace.sources.document_id"),
]


@pytest.mark.parametrize(
    ("mutate", "reason", "detail"),
    [row[2:] for row in _PRIOR_ROWS],
    ids=[f"row{row[0]}-{row[1]}" for row in _PRIOR_ROWS],
)
def test_every_prior_row_refuses_with_its_reason_and_position(chain, mutate, reason, detail):
    acquisition, _, _, root = chain["root"]
    assert _refusal(acquisition, mutate(root), "2026-07-29T17:30:00Z") == (reason, detail)


def test_the_first_release_row_is_the_predecessor_whatever_surrounds_it(chain):
    acquisition, _, _, root = chain["root"]
    release = root["workspace"]["sources"][0]
    for sources in (
        [{"kind": "transcript"}, release],
        [_Hostile(), _HostileTyped(), "x", release],
        [release, _Hostile()],
        [release, {"kind": "issuer_release"}],
    ):
        prior = _replace_at(root, ("workspace", "sources"), sources)
        assert _outcome(acquisition, prior, "2026-07-29T17:30:00Z")[2] == root


_ORDER = [
    # (what is wrong twice, acquisition mutation, prior mutation or None, observed_at, the earlier row's refusal)
    ("rows 2 and 3", lambda a: {**a, "acceptance_datetime": "x", "exhibit_body": ""}, None, "2026-07-29T17:20:00Z",
     ("malformed_source_clock", "acquisition.acceptance_datetime")),
    ("rows 3 and 5", lambda a: {**a, "exhibit_body": "", "cik": "x"}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.exhibit_body")),
    ("rows 4 and 5", lambda a: {**a, "exhibit_body": "\ud800", "cik": "x"}, None, "2026-07-29T17:20:00Z",
     ("non_utf8_source", "acquisition.exhibit_body")),
    ("rows 5 and 6", lambda a: {**a, "cik": "x", "accession": "x"}, None, "2026-07-29T17:20:00Z",
     ("unadmitted_issuer", "acquisition.cik")),
    ("rows 6 and 7", lambda a: {**a, "accession": "x", "form": "x"}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.accession")),
    ("rows 7 and 8", lambda a: {**a, "form": "x", "filing_date": "x"}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.form")),
    ("rows 8 and 9", lambda a: {**a, "filing_date": "x", "report_date": "x"}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.filing_date")),
    ("rows 9 and 10", lambda a: {**a, "report_date": "x", "exhibit_url": ""}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.report_date")),
    ("rows 10 and 11", lambda a: {**a, "exhibit_url": "", "currentness": None}, None, "2026-07-29T17:20:00Z",
     ("malformed_acquisition", "acquisition.exhibit_url")),
    ("rows 12 and 13", lambda a: {**a, "currentness": {"state": "x", "checked_at": "x"}}, None, "2026-07-29T17:20:00Z",
     ("malformed_currentness", "acquisition.currentness.state")),
    ("rows 13 and 14", lambda a: {**a, "currentness": {"state": "up_to_date", "checked_at": "x"}, "received_bytes": None}, None,
     "2026-07-29T17:20:00Z", ("malformed_currentness", "acquisition.currentness.checked_at")),
    ("rows 15 and 16", lambda a: {**a, "received_bytes": {"sha256": "x", "length": -1}}, None, "2026-07-29T17:20:00Z",
     ("missing_received_byte_receipt", "acquisition.received_bytes.sha256")),
    ("rows 16 and 17", lambda a: {**a, "received_bytes": {**a["received_bytes"], "length": -1}, "declared_encoding": "x"}, None,
     "2026-07-29T17:20:00Z", ("missing_received_byte_receipt", "acquisition.received_bytes.length")),
    ("rows 17 and 18", lambda a: {**a, "declared_encoding": "x"}, None, "x",
     ("non_utf8_source", "acquisition.declared_encoding")),
    ("rows 18 and 19", lambda a: a, lambda p: "x", "x", ("malformed_observation_clock", "observed_at")),
    ("rows 19 and 20", lambda a: a, lambda p: "x", "2026-07-29T17:09:59Z", ("malformed_prior", "prior")),
    ("rows 20 and 21", lambda a: {**a, "received_bytes": {**a["received_bytes"], "sha256": _SHA}}, None, "2026-07-29T17:09:59Z",
     ("malformed_observation_clock", "observed_at")),
    ("rows 21 and 22", lambda a: {**a, "cik": "0000000001", "received_bytes": {**a["received_bytes"], "sha256": _SHA}}, None,
     "2026-07-29T17:20:00Z", ("received_bytes_mismatch", "acquisition.received_bytes")),
    ("rows 22 and 24", lambda a: {**_with_body(a, "<h1>Second Quarter Ended March 31, 2027</h1>"), "cik": "0000000001"}, None,
     "2026-07-29T17:20:00Z", ("unadmitted_issuer", "acquisition.cik")),
    ("rows 24 and 25", lambda a: _with_body(a, "<h1>Second Quarter Ended March 31, 2027</h1>"),
     lambda p: _replace_at(p, _RELEASE + ("filing_key", "cik"), "0000000001"), "2026-07-29T17:20:00Z",
     ("document_period_not_admitted", "acquisition.exhibit_body")),
    ("rows 25 and 26", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _RELEASE + ("filing_key", "cik"), "0000000001"), _W + ("fiscal_period", "year"), 2027),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.sources.filing_key.cik")),
    ("rows 26 and 26a", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("fiscal_period", "year"), 2027), _W + ("lifecycle", "source_available_at"), "2026-07-29T17:10:01Z"),
     "2026-07-29T17:20:00Z", ("source_precedes_prior_event", "prior.workspace.fiscal_period")),
    ("rows 26a and 27", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("lifecycle", "source_available_at"), "2026-07-29T17:10:01Z"), _W + ("lifecycle", "observed_at"), "2026-07-29T17:09:59Z"),
     "2026-07-29T17:20:00Z", ("source_precedes_prior_event", "prior.workspace.lifecycle.source_available_at")),
    ("rows 23 and 24", lambda a: {**_with_body(a, "<h1>Second Quarter Ended March 31, 2027</h1>"), "acceptance_datetime": "0001-01-01T00:00:00Z"},
     None, "2026-07-29T17:20:00Z", ("malformed_source_clock", "acquisition.acceptance_datetime")),
    ("rows 27 and 30", lambda a: a,
     lambda p: _replace_at(_replace_at(_replace_at(p, _W + ("event_id",), "evt_other"), _D + ("event_id",), "evt_other"),
                           _W + ("lifecycle", "observed_at"), "2026-07-29T17:09:59Z"),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.lifecycle.observed_at")),
    ("rows 28 and 31", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _RELEASE + ("source_sha256",), _SHA), _W + ("lifecycle", "observed_at"), "2026-07-29T18:00:00Z"),
     "2026-07-29T17:30:00Z", ("malformed_observation_clock", "observed_at")),
    ("rows 30 and 31", lambda a: a,
     lambda p: _replace_at(_replace_at(_replace_at(p, _W + ("event_id",), "evt_other"), _D + ("event_id",), "evt_other"),
                           _RELEASE + ("source_sha256",), _SHA),
     "2026-07-29T17:30:00Z", ("malformed_prior", "prior.workspace.event_id")),
    ("rows 4 of the prior and 16 of the prior", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("event_id",), ""), _D + ("document_id",), "doc_other"),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.event_id")),
    ("rows 7 of the prior and 7a of the prior", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("lifecycle", "observed_at"), "x"), _W + ("lifecycle", "source_available_at"), "x"),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.lifecycle.observed_at")),
    ("rows 7a of the prior and 8 of the prior", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("lifecycle", "source_available_at"), "x"), _W + ("lifecycle", "state"), "x"),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.lifecycle.source_available_at")),
    ("rows 8 of the prior and 10 of the prior", lambda a: a,
     lambda p: _replace_at(_replace_at(p, _W + ("lifecycle", "state"), "x"), _W + ("sources",), []),
     "2026-07-29T17:20:00Z", ("malformed_prior", "prior.workspace.lifecycle.state")),
]


@pytest.mark.parametrize(
    ("change", "change_prior", "observed_at", "expected"),
    [row[1:] for row in _ORDER],
    ids=[row[0] for row in _ORDER],
)
def test_the_first_failing_check_decides(chain, change, change_prior, observed_at, expected):
    acquisition, _, _, root = chain["root"]
    prior = None if change_prior is None else change_prior(root)
    assert _refusal(change(acquisition), prior, observed_at) == expected


# -- R5.1: the sweeps --------------------------------------------------------------------------

_ACQUISITION_FAMILY = (
    "malformed_acquisition", "malformed_source_clock", "unadmitted_issuer", "document_period_not_admitted",
    "missing_received_byte_receipt", "received_bytes_mismatch", "non_utf8_source", "malformed_currentness",
)
_PRIOR_FAMILY = (
    "malformed_prior", "prior_source_identity_missing", "source_precedes_prior_event", "malformed_observation_clock",
)
_READ_FROM_THE_PRIOR = (
    (), _W, _D, _W + ("event_id",), _W + ("fiscal_period",), _W + ("fiscal_period", "year"),
    _W + ("fiscal_period", "quarter"), _W + ("lifecycle",), _W + ("lifecycle", "observed_at"),
    _W + ("lifecycle", "source_available_at"), _W + ("lifecycle", "state"), _W + ("sources",), _RELEASE, _RELEASE + ("kind",), _RELEASE + ("filing_key",),
    _RELEASE + ("filing_key", "cik"), _RELEASE + ("filing_key", "accession"), _RELEASE + ("source_sha256",),
    _RELEASE + ("document_id",), _D + ("document_id",), _D + ("event_id",), _D + ("revision",),
    _D + ("supersedes_document_id",),
)


def test_the_hostile_values_raise_when_anything_is_asked_of_them():
    """Positive control for the sweeps: each probe value does raise, so a sweep that passes proves restraint."""
    probes = (
        lambda: _Hostile() == 1, lambda: hash(_Hostile()), lambda: bool(_Hostile()), lambda: _Hostile().get,
        lambda: isinstance(_HostileTyped(), dict), lambda: isinstance({}, _HostileTyped),
        lambda: type(_HostileTyped()) in (dict, list), lambda: {type(_HostileTyped()): 1},
        lambda: _StrSub("a") == "a", lambda: {_StrSub("a"): 1}, lambda: _StrSub("a").strip(),
        lambda: _DictSub().get("a"), lambda: "a" in _DictSub(), lambda: list(_ListSub()),
        lambda: _IntSub(1) < 2, lambda: _IntSub(1) + 1,
        lambda: {"a": 1, _Twin("a"): 2}, lambda: {_Twin("a"): 1}["a"], lambda: "a" in {_StrKey("a"): 1},
    )
    assert len(probes) == 19
    for probe in probes:
        with pytest.raises(RuntimeError, match="hostile"):
            probe()
    assert hash(_StrKey("a")) == hash("a") and hash(_Twin("a")) == hash("a")
    assert type(_HostileTyped()) is _HostileTyped and type(_StrSub("a")) is not str


def test_no_acquisition_value_escapes_the_typed_boundary(chain):
    acquisition, _, _, root = chain["root"]
    calls = returned = 0
    for path, original in _nodes(acquisition):
        where = "acquisition/" + "/".join(map(str, path))
        edits = [(f"{where} <- {value!r:.40}", _replace_at(acquisition, path, value)) for value in _substitutes(original)]
        if path and type(path[-1]) is str:
            edits.append((f"{where} removed", _without(acquisition, path)))
            for key in (_StrKey(path[-1]), _Twin(path[-1]), 7):
                edits.append((f"{where} rekeyed {key!r}", _rekey(acquisition, path, key)))
        for label, edited in edits:
            for prior in (None, root):
                reason, detail, result = _outcome(edited, prior, "2026-07-29T17:20:00Z", label)
                calls += 1
                if result is None:
                    # With a well-formed prior and run clock, every refusal is about the acquisition.
                    assert reason in _ACQUISITION_FAMILY, (label, reason)
                    assert detail.startswith("acquisition"), (label, detail)
                else:
                    returned += 1
    assert (calls, returned) == (1276, 98), (calls, returned)


def test_no_prior_value_at_a_read_position_escapes_the_typed_boundary(chain):
    acquisition, _, _, root = chain["root"]
    changed, _, _, second = chain["changed"]
    calls = returned = 0
    for name, source, prior in (("carried", acquisition, root), ("not carried", changed, root), ("revision 2", changed, second)):
        for path in _READ_FROM_THE_PRIOR:
            where = f"{name} prior/" + "/".join(map(str, path))
            edits = [(f"{where} <- {value!r:.40}", _replace_at(prior, path, value)) for value in _substitutes(_at(prior, path))]
            if path and type(path[-1]) is str:
                edits.append((f"{where} removed", _without(prior, path)))
                for key in (_StrKey(path[-1]), _Twin(path[-1]), 7):
                    edits.append((f"{where} rekeyed {key!r}", _rekey(prior, path, key)))
            for label, edited in edits:
                reason, detail, result = _outcome(source, edited, "2026-07-31T00:00:00Z", label)
                calls += 1
                if result is None:
                    assert reason in _PRIOR_FAMILY, (label, reason)
                    assert detail.startswith("prior") or (reason, detail) == ("malformed_observation_clock", "observed_at"), label
                else:
                    returned += 1
    assert (calls, returned) == (2485, 25), (calls, returned)


def test_positions_the_preparation_does_not_read_cannot_change_the_result(chain):
    changed, _, _, second = chain["changed"]
    expected = prepare_pg_workspace(changed, prior=second, observed_at="2026-08-01T00:00:00Z")
    read = set(_READ_FROM_THE_PRIOR)
    containers = [path for path in _READ_FROM_THE_PRIOR if type(_at(second, path)) is dict]
    unread = [
        container + (key,) for container in containers for key in _at(second, container) if container + (key,) not in read
    ]
    assert len(unread) == 38, unread
    assert _W + ("generation_id",) in unread and _W + ("facts",) in unread and ("decoded_source",) in unread
    for path in unread:
        for value in (None, 5, {}, _Hostile(), _HostileTyped()):
            label = "/".join(map(str, path)) + f" <- {value!r}"
            assert _outcome(changed, _replace_at(second, path, value), "2026-08-01T00:00:00Z", label)[2] == expected, label
        assert _outcome(changed, _without(second, path), "2026-08-01T00:00:00Z")[2] == expected, path
    # Positive control: a read position does change the outcome.
    assert _outcome(changed, _replace_at(second, _D + ("revision",), 7), "2026-08-01T00:00:00Z")[2] != expected


def test_no_observed_at_value_escapes_the_typed_boundary(chain):
    acquisition, _, _, root = chain["root"]
    values = [value for value in _substitutes("2026-07-29T17:20:00Z") + _bad_clocks() if not _is_clock(value)]
    assert len(values) == 59, len(values)
    for value in values:
        for prior in (None, root):
            assert _refusal(acquisition, prior, value) == ("malformed_observation_clock", "observed_at"), repr(value)
    # Positive control: the canonical clock is admitted with and without a prior.
    for prior in (None, root):
        assert _outcome(acquisition, prior, "2026-07-29T17:20:00Z")[0] == "returned"


def test_a_key_that_is_not_an_exact_string_refuses_its_container_before_it_is_compared(chain):
    acquisition, _, _, root = chain["root"]
    containers = (
        ((), "malformed_acquisition", "acquisition"),
        (("currentness",), "malformed_currentness", "acquisition.currentness"),
        (("received_bytes",), "missing_received_byte_receipt", "acquisition.received_bytes"),
    )
    for container, reason, detail in containers:
        for key in _at(acquisition, container):
            for hostile in (_StrKey(key), _Twin(key), 7, None, ("x",)):
                edited = _rekey(acquisition, container + (key,), hostile)
                assert _refusal(edited, None, "2026-07-29T17:20:00Z") == (reason, detail), (container, key, hostile)
    prior_containers = (
        ((), "malformed_prior", "prior"),
        (_W, "malformed_prior", "prior.workspace"),
        (_D, "malformed_prior", "prior.document_metadata"),
        (_W + ("fiscal_period",), "malformed_prior", "prior.workspace.fiscal_period"),
        (_W + ("lifecycle",), "malformed_prior", "prior.workspace.lifecycle"),
        (_RELEASE, "prior_source_identity_missing", "prior.workspace.sources"),
        (_RELEASE + ("filing_key",), "prior_source_identity_missing", "prior.workspace.sources.filing_key"),
    )
    for container, reason, detail in prior_containers:
        for key in _at(root, container):
            for hostile in (_StrKey(key), _Twin(key), 7):
                edited = _rekey(root, container + (key,), hostile)
                assert _refusal(acquisition, edited, "2026-07-29T17:30:00Z") == (reason, detail), (container, key, hostile)


# -- R5.1 / R5.2: the section's own text ---------------------------------------------------------

def _task2_section() -> ast.Module:
    source = Path(pg_profile_module.__file__).read_text(encoding="utf-8")
    marker = "# ---- Task 2: private native preparation ----"
    assert source.count(marker) == 1
    return ast.parse(source[source.index(marker):])


def test_the_section_tests_types_by_identity_only():
    tree = _task2_section()
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not (names | attributes) & {"isinstance", "issubclass", "__class__", "strptime", "fromisoformat", "strftime"}
    compared = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        if any(isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "type" for item in operands):
            compared += 1
            assert all(isinstance(operator, (ast.Is, ast.IsNot)) for operator in node.ops), ast.unparse(node)
    # The exact count: a type test cannot be removed, or added in another form, without this test changing.
    assert compared == 18, compared


def test_every_refusal_in_the_section_names_a_reason_and_a_position():
    tree = _task2_section()
    refusals = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "PgPreparationRefused"
    ]
    assert len(refusals) == 54, len(refusals)
    reasons = set()
    for node in refusals:
        assert len(node.args) == 2 and not node.keywords, ast.unparse(node)
        reason, detail = node.args
        assert isinstance(reason, ast.Constant) and reason.value in PG_PREPARATION_REFUSALS, ast.unparse(node)
        reasons.add(reason.value)
        if isinstance(detail, ast.Constant):
            assert type(detail.value) is str and detail.value, ast.unparse(node)
        else:
            assert ast.unparse(detail) in ("f'acquisition.{name}'", "type(exc).__name__"), ast.unparse(node)
    assert reasons == set(PG_PREPARATION_REFUSALS)
    for reason in PG_PREPARATION_REFUSALS:
        assert str(PgPreparationRefused(reason, "position")) == _R5_MESSAGES[reason]
    with pytest.raises(ValueError, match="unknown preparation refusal") as raised:
        PgPreparationRefused("not_a_reason", "position")
    assert type(raised.value) is ValueError


# -- P2, P5, R5.11-R5.14: the chain --------------------------------------------------------------

@pytest.mark.parametrize("name", _SCENARIOS)
def test_every_prepared_result_is_consistent(chain, name):
    acquisition, _, _, result = chain[name]
    assert _p2_violations(result, acquisition["acceptance_datetime"]) == []
    workspace = result["workspace"]
    assert workspace["generation_id"] == preview_generation_identity(
        {workspace["event_id"]: workspace}, workspace["generated_at"], previous_generation_id=None
    )
    assert workspace["generated_at"] == workspace["lifecycle"]["observed_at"]
    assert workspace["event_id"] == "evt_cik0000080424_2026q4_results"
    assert workspace["fiscal_period"] == {"year": 2026, "quarter": 4, "calendar_end": "2026-06-30"}
    assert result["currentness_context"]["fiscal_scope"] == ("2026-04-01", "2026-06-30", "2025-04-01", "2025-06-30")
    assert result["currentness_context"]["profile_version"] == "pg_profile.v1"
    json.dumps(dict(result, currentness_context=dict(result["currentness_context"], fiscal_scope=None)), allow_nan=False)


def test_the_consistency_check_can_fail(chain):
    """Positive control for ``_p2_violations``: each tampered result is reported."""
    _, _, _, good = chain["changed"]
    assert _p2_violations(good) == []
    document = good["document_metadata"]
    tampers = (
        (_W + ("generation_id",), "0" * 24), (_W + ("generated_at",), "2026-07-30T17:20:01Z"),
        (_RELEASE + ("source_sha256",), _SHA), (("decoded_source",), good["decoded_source"] + " "),
        (("source_texts",), {}), (("received_byte_receipt", "length"), 1), (("received_byte_receipt", "declared_encoding"), "latin-1"),
        (_D + ("content_sha256",), _SHA), (_D + ("content_bytes",), 1), (_D + ("document_id",), "doc_other"),
        (_D + ("event_id",), "evt_other"), (_D + ("filing_key", "accession"), "0000080424-26-000009"),
        (_D + ("fetched_at",), "2026-07-30T17:20:01Z"), (_D + ("published_at",), "2026-07-29T17:10:01Z"),
        (_D + ("available_at",), "2026-07-29T17:10:00+00:00"), (_W + ("lifecycle", "source_available_at"), "2026-07-29T17:10:01Z"),
        (("currentness_context", "source_available_at"), "2026-07-29T17:10:01Z"),
        (_D + ("revision",), 1), (_D + ("revision",), True), (_D + ("supersedes_document_id",), None),
        (_D + ("supersedes_document_id",), document["document_id"]), (_W + ("lifecycle", "state"), "pending"),
        (("currentness_context", "fiscal_scope"), list(good["currentness_context"]["fiscal_scope"])),
        (("currentness_context", "currentness"), {"state": "currentness_unverified", "source_clock": "2026-07-29T17:10:00Z"}),
        (("currentness_context", "currentness"), {"state": "up_to_date", "source_clock": None}),
        (_W + ("facts",), (1,)), (_W + ("warnings",), {1: 2}), (_D + ("holds_bytes",), float("nan")),
    )
    for path, value in tampers:
        assert _p2_violations(_replace_at(good, path, value)) != [], path
    assert _p2_violations(good, "2026-07-29T17:10:01Z") != []
    assert _p2_violations(dict(good, extra=1)) == ["result keys"]


@pytest.mark.parametrize("name", _SCENARIOS)
def test_re_preparing_a_source_with_its_own_result_reproduces_it(chain, name):
    acquisition, _, _, result = chain[name]
    for state, checked_at, later in (
        ("up_to_date", "2026-08-02T09:00:00Z", "2026-08-02T09:00:00Z"),
        ("newer_source_pending", "2026-08-03T09:00:00Z", "2026-08-03T09:05:00Z"),
        ("currentness_unverified", None, "2031-01-01T00:00:00Z"),
    ):
        again = prepare_pg_workspace(
            dict(acquisition, currentness={"state": state, "checked_at": checked_at}), prior=result, observed_at=later
        )
        for key in _COMPARED:
            assert again[key] == result[key], (state, key)
        assert again["currentness_context"] == dict(
            result["currentness_context"], currentness={"state": state, "source_clock": checked_at}
        )
        # ... and once more from that result: the reuse is stable, not a one-step coincidence.
        third = prepare_pg_workspace(acquisition, prior=again, observed_at="2031-06-01T00:00:00Z")
        assert [third[key] for key in _COMPARED] == [result[key] for key in _COMPARED]


def test_an_absent_currentness_is_prepared_as_none_and_an_unverified_one_carries_no_clock():
    acquisition = _acquired("same_source_rebuild")
    absent = _without(acquisition, ("currentness",))
    assert _outcome(absent, None, "2026-07-29T17:20:00Z")[2]["currentness_context"]["currentness"] is None
    unverified = dict(acquisition, currentness={"state": "currentness_unverified", "checked_at": None})
    assert _outcome(unverified, None, "2026-07-29T17:20:00Z")[2]["currentness_context"]["currentness"] == {
        "state": "currentness_unverified", "source_clock": None
    }
    for state in ("up_to_date", "newer_source_pending"):
        verified = dict(acquisition, currentness={"state": state, "checked_at": "2026-07-29T17:15:00Z"})
        assert _outcome(verified, None, "2026-07-29T17:20:00Z")[2]["currentness_context"]["currentness"] == {
            "state": state, "source_clock": "2026-07-29T17:15:00Z"
        }


def test_the_lifecycle_follows_the_native_law(chain):
    states = {name: chain[name][3]["workspace"]["lifecycle"]["state"] for name in _SCENARIOS}
    assert states == {
        "root": "complete",
        "changed_in_place": "corrected",
        "back_to_first": "corrected",
        "changed": "corrected",
        "changed_twice": "corrected",
        "refiled": "complete",
        "refiled_after_correction": "corrected",
        "amendment": "complete",
        "moved_url": "complete",
    }
    observed = {name: chain[name][3]["workspace"]["lifecycle"]["observed_at"] for name in _SCENARIOS}
    assert observed == {
        "root": "2026-07-29T17:10:00Z",
        "changed_in_place": "2026-07-30T09:00:00Z",
        "back_to_first": "2026-07-31T11:00:00Z",
        "changed": "2026-07-30T17:20:00Z",
        "changed_twice": "2026-07-31T10:00:00Z",
        "refiled": "2026-07-29T17:20:00Z",
        "refiled_after_correction": "2026-07-31T12:00:00Z",
        "amendment": "2026-07-30T18:01:00Z",
        "moved_url": "2026-07-29T17:10:00Z",
    }
    # The same text under the same accession keeps the first observation at any later run clock.
    acquisition, _, _, root = chain["root"]
    for later in ("2026-07-29T17:10:00Z", "2026-07-30T00:00:00Z", "2031-01-01T00:00:00Z"):
        assert _outcome(acquisition, root, later)[2]["workspace"]["lifecycle"] == root["workspace"]["lifecycle"]
    # Task 1's validator admits a corrected workspace.
    corrected = chain["changed"][3]
    assert validate_selected_facts(
        corrected["workspace"], source_texts=corrected["source_texts"], fiscal_scope=FISCAL_SCOPE
    )


def test_the_document_chain_follows_the_native_document_id(chain):
    document = {name: chain[name][3]["document_metadata"] for name in _SCENARIOS}
    ids = {name: document[name]["document_id"] for name in _SCENARIOS}
    assert {name: (document[name]["revision"], document[name]["supersedes_document_id"]) for name in _SCENARIOS} == {
        "root": (1, None),
        "changed_in_place": (2, ids["root"]),
        "back_to_first": (3, ids["changed_in_place"]),
        "changed": (2, ids["root"]),
        "changed_twice": (3, ids["changed"]),
        "refiled": (2, ids["root"]),
        "refiled_after_correction": (3, ids["changed"]),
        "amendment": (2, ids["root"]),
        "moved_url": (2, ids["root"]),
    }
    # A text that returns to an earlier version repeats that version's native id; nothing else repeats.
    assert ids["back_to_first"] == ids["root"]
    assert len(set(ids.values())) == len(_SCENARIOS) - 1
    assert {name: document[name]["document_kind"] for name in _SCENARIOS} == {
        name: ("release_amendment" if name == "amendment" else "release") for name in _SCENARIOS
    }
    for name in _SCENARIOS:
        acquisition, _, _, result = chain[name]
        assert document[name]["fetched_at"] == result["workspace"]["lifecycle"]["observed_at"]
        assert document[name]["published_at"] == document[name]["available_at"] == acquisition["acceptance_datetime"]
        assert document[name]["filing_key"] == {"cik": "0000080424", "accession": acquisition["accession"]}
        assert document[name]["superseded_by_document_id"] is None and document[name]["holds_bytes"] is False
        assert document[name]["presented_fiscal_label"] == "FY2026 Q4"
        # The stored document is private: the rights stamp is the internal profile, never the public one.
        assert (document[name]["rights_profile"], document[name]["rights_state"]) == (PG_PRIVATE_RIGHTS_PROFILE, "internal_only")
        assert PG_PRIVATE_RIGHTS_PROFILE == "rp_internal_private_v1" != RIGHTS_PROFILE
    # The native chain validator admits each path, the repeated id included.
    for path in (
        ("root", "changed", "changed_twice"), ("root", "changed_in_place", "back_to_first"), ("root", "refiled"),
        ("root", "changed", "refiled_after_correction"), ("root", "amendment"), ("root", "moved_url"),
    ):
        DocumentRevisionChain(tuple(_native_document(document[name]) for name in path))
    # Positive control: the validator does refuse a chain that is not one (two roots; a revision 2 alone).
    for path in (("root", "root"), ("changed",)):
        with pytest.raises(ValueError, match="revision numbers are not contiguous"):
            DocumentRevisionChain(tuple(_native_document(document[name]) for name in path))
    # The generation id differs wherever the workspace differs, the repeated document id included.
    generations = {chain[name][3]["workspace"]["generation_id"] for name in _SCENARIOS}
    assert len(generations) == len(_SCENARIOS)


def test_the_predecessor_generation_id_is_never_folded_in(chain):
    changed, _, _, second = chain["changed"]
    root = chain["root"][3]
    for other in ("0" * 24, "f" * 24, None, 5):
        again = prepare_pg_workspace(
            changed, prior=_replace_at(root, _W + ("generation_id",), other), observed_at="2026-07-30T17:20:00Z"
        )
        assert again == second


def test_a_prior_of_another_fiscal_period_never_enters_the_result(chain):
    fourth, _, _, root = chain["root"]
    third = _quarter("2026-04-24T17:00:00Z", "555")
    first_of_next_year = _quarter("2026-10-24T17:00:00Z", "777")
    earlier = _outcome(third, None, "2026-04-24T17:30:00Z")[2]
    assert earlier["workspace"]["event_id"] == "evt_cik0000080424_2026q3_results"
    assert earlier["workspace"]["fiscal_period"] == {"year": 2026, "quarter": 3, "calendar_end": "2026-03-31"}
    # An earlier period is no predecessor: the result is the root, in every part.
    assert _outcome(fourth, earlier, "2026-07-29T17:10:00Z")[2] == root
    # ... whatever its source clock: R6.1 orders the sources of one period, never those of two.
    late = _replace_at(earlier, _W + ("lifecycle", "source_available_at"), "2026-12-01T00:00:00Z")
    assert _outcome(fourth, late, "2026-07-29T17:10:00Z")[2] == root
    later_root = _outcome(first_of_next_year, None, "2026-10-24T17:30:00Z")[2]
    assert later_root["workspace"]["event_id"] == "evt_cik0000080424_2027q1_results"
    assert later_root["document_metadata"]["revision"] == 1
    for prior in (root, chain["changed"][3], chain["changed_twice"][3], earlier):
        assert _outcome(first_of_next_year, prior, "2026-10-24T17:30:00Z")[2] == later_root
    # ... and re-preparing it with its own result still reproduces it.
    assert _outcome(first_of_next_year, later_root, "2026-10-25T09:00:00Z")[2] == later_root
    # A later period is refused: the acquisition would step the chain backwards.
    assert _refusal(fourth, later_root, "2026-10-26T09:00:00Z") == (
        "source_precedes_prior_event", "prior.workspace.fiscal_period"
    )
    assert _refusal(third, root, "2026-08-01T00:00:00Z") == (
        "source_precedes_prior_event", "prior.workspace.fiscal_period"
    )


def test_the_run_clock_is_bound_by_the_predecessor_only_when_it_is_recorded(chain):
    changed, _, _, second = chain["changed"]
    twice = chain["changed_twice"][0]
    assert second["workspace"]["lifecycle"]["observed_at"] == "2026-07-30T17:20:00Z"
    # Not carried: the run clock becomes the first observation, so it cannot precede the predecessor's.
    assert _refusal(twice, second, "2026-07-30T17:19:59Z") == ("malformed_observation_clock", "observed_at")
    assert _outcome(twice, second, "2026-07-30T17:20:00Z")[2]["workspace"]["lifecycle"]["observed_at"] == "2026-07-30T17:20:00Z"
    # Carried: the run clock is recorded nowhere, so an earlier one (not before the acceptance) changes nothing.
    assert changed["acceptance_datetime"] < "2026-07-30T17:20:00Z"
    assert _outcome(changed, second, changed["acceptance_datetime"])[2] == second
    assert _outcome(changed, second, "2031-01-01T00:00:00Z")[2] == second
    # Carried: the first observation kept must not precede the acceptance.
    acquisition, _, _, root = chain["root"]
    exact = _replace_at(root, _W + ("lifecycle", "observed_at"), "2026-07-29T17:10:00Z")
    assert _outcome(acquisition, exact, "2026-07-29T18:00:00Z")[0] == "returned"
    early = _replace_at(root, _W + ("lifecycle", "observed_at"), "2026-07-29T17:09:59Z")
    assert _refusal(acquisition, early, "2026-07-29T18:00:00Z") == ("malformed_prior", "prior.workspace.lifecycle.observed_at")
    # Not carried: that same early observation in the prior is no obstacle (the new run clock is recorded).
    assert _outcome(chain["changed"][0], early, "2026-07-30T17:20:00Z")[0] == "returned"
    # Not carried, under another accession: the bound is the same for an amendment and for a refiling.  Both were
    # accepted before the predecessor was first observed and not before its source, so R6.1 admits them.
    observed_late = _outcome(acquisition, None, "2026-08-05T00:00:00Z")[2]
    for other in (chain["amendment"][0], chain["refiled"][0]):
        assert other["accession"] != acquisition["accession"]
        assert acquisition["acceptance_datetime"] <= other["acceptance_datetime"] < "2026-08-04T23:59:59Z"
        assert _refusal(other, observed_late, "2026-08-04T23:59:59Z") == ("malformed_observation_clock", "observed_at")
        assert _outcome(other, observed_late, "2026-08-05T00:00:00Z")[2]["document_metadata"]["revision"] == 2


@pytest.mark.parametrize("name", _SCENARIOS)
def test_arguments_are_never_mutated_and_nothing_mutable_is_shared(chain, name):
    acquisition, prior, observed_at, result = chain[name]
    before = copy.deepcopy((acquisition, prior))
    again = prepare_pg_workspace(acquisition, prior=prior, observed_at=observed_at)
    assert (acquisition, prior) == before
    assert again == result
    if prior is not None:
        for key in ("workspace", "document_metadata", "source_texts", "received_byte_receipt", "currentness_context"):
            assert again[key] is not prior[key]
        assert again["workspace"]["lifecycle"] is not prior["workspace"]["lifecycle"]
        assert again["workspace"]["sources"] is not prior["workspace"]["sources"]
    assert again["currentness_context"]["currentness"] is not acquisition["currentness"]
    assert again["received_byte_receipt"] is not acquisition["received_bytes"]


# -- R5.6 / R5.7: the backstop and the profile lookup ---------------------------------------------

@pytest.mark.parametrize(
    "raised",
    [
        TypeError("t"), ValueError("v"), ArithmeticError("a"), ZeroDivisionError("z"), OverflowError("o"),
        LookupError("l"), KeyError("k"), IndexError("i"), AttributeError("a"), RecursionError("r"),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    ],
    ids=lambda raised: type(raised).__name__,
)
def test_the_backstop_types_a_native_failure_of_the_six_classes(monkeypatch, raised):
    def build(**_arguments):
        raise raised

    monkeypatch.setattr(pg_profile_module, "build_event_workspace", build)
    with pytest.raises(PgPreparationRefused) as caught:
        prepare_pg_workspace(_acquired("same_source_rebuild"), prior=None, observed_at="2026-07-29T17:20:00Z")
    assert type(caught.value) is PgPreparationRefused
    assert (caught.value.reason, caught.value.detail) == ("workspace_build_refused", type(raised).__name__)
    assert str(caught.value) == "native workspace build refused the acquisition"
    assert caught.value.__cause__ is raised


@pytest.mark.parametrize(
    "raised",
    [RuntimeError("r"), NotImplementedError("n"), MemoryError("m"), AssertionError("a"), OSError("o"), StopIteration("s")],
    ids=lambda raised: type(raised).__name__,
)
def test_the_backstop_lets_every_other_exception_propagate(monkeypatch, raised):
    def build(**_arguments):
        raise raised

    monkeypatch.setattr(pg_profile_module, "build_event_workspace", build)
    with pytest.raises(type(raised)) as caught:
        prepare_pg_workspace(_acquired("same_source_rebuild"), prior=None, observed_at="2026-07-29T17:20:00Z")
    assert caught.value is raised


def test_a_refusal_from_inside_the_build_passes_through_unchanged(monkeypatch):
    raised = PgPreparationRefused("non_utf8_source", "somewhere")

    def build(**_arguments):
        raise raised

    monkeypatch.setattr(pg_profile_module, "build_event_workspace", build)
    with pytest.raises(PgPreparationRefused) as caught:
        prepare_pg_workspace(_acquired("same_source_rebuild"), prior=None, observed_at="2026-07-29T17:20:00Z")
    assert caught.value is raised


def test_a_native_first_observation_that_is_not_canonical_is_refused(monkeypatch):
    real = pg_profile_module.build_event_workspace

    def build(**arguments):
        workspace = real(**arguments)
        workspace["lifecycle"]["observed_at"] = "2026-07-29T17:20:00+00:00"
        return workspace

    monkeypatch.setattr(pg_profile_module, "build_event_workspace", build)
    assert _refusal(_acquired("same_source_rebuild"), None, "2026-07-29T17:20:00Z") == (
        "workspace_build_refused", "workspace.lifecycle.observed_at"
    )


def test_the_native_build_receives_only_admitted_exact_values(monkeypatch, chain):
    seen = []
    real = pg_profile_module.build_event_workspace

    def build(**arguments):
        seen.append(arguments)
        return real(**arguments)

    monkeypatch.setattr(pg_profile_module, "build_event_workspace", build)
    changed, _, _, second = chain["changed"]
    root = chain["root"][3]
    prepare_pg_workspace(changed, prior=root, observed_at="2026-07-30T17:20:00Z")
    prepare_pg_workspace(changed, prior=second, observed_at="2026-08-01T00:00:00Z")
    refiled = chain["refiled"][0]
    prepare_pg_workspace(refiled, prior=root, observed_at="2026-07-29T17:20:00Z")
    prepare_pg_workspace(chain["root"][0], prior=None, observed_at="2026-07-29T17:10:00Z")
    picked = [
        {key: call[key] for key in ("prior_source_sha256", "prior_lifecycle_state", "prior_observed_at", "observed_at", "source_available_at", "ticker", "transcript")}
        for call in seen
    ]
    root_digest = root["workspace"]["sources"][0]["source_sha256"]
    second_digest = second["workspace"]["sources"][0]["source_sha256"]
    assert picked == [
        # a changed text: the predecessor's digest and state, no carried clock
        {"prior_source_sha256": root_digest, "prior_lifecycle_state": "complete", "prior_observed_at": None,
         "observed_at": "2026-07-30T17:20:00Z", "source_available_at": changed["acceptance_datetime"], "ticker": "PG", "transcript": None},
        # the same text in the same filing: digest, state and the first observation
        {"prior_source_sha256": second_digest, "prior_lifecycle_state": "corrected", "prior_observed_at": "2026-07-30T17:20:00Z",
         "observed_at": "2026-08-01T00:00:00Z", "source_available_at": changed["acceptance_datetime"], "ticker": "PG", "transcript": None},
        # the same text under another accession: no digest (not a correction), the state, no carried clock
        {"prior_source_sha256": None, "prior_lifecycle_state": "complete", "prior_observed_at": None,
         "observed_at": "2026-07-29T17:20:00Z", "source_available_at": "2026-07-29T17:10:00Z", "ticker": "PG", "transcript": None},
        # no predecessor
        {"prior_source_sha256": None, "prior_lifecycle_state": None, "prior_observed_at": None,
         "observed_at": "2026-07-29T17:10:00Z", "source_available_at": "2026-07-29T17:10:00Z", "ticker": "PG", "transcript": None},
    ]
    assert [call["asof"] for call in seen] == [date(2026, 7, 30), date(2026, 7, 30), date(2026, 7, 29), date(2026, 7, 29)]
    assert all(type(call["asof"]) is date for call in seen)
    assert seen[0]["filing"] == {
        "cik": "0000080424", "accession": changed["accession"], "form": "8-K", "filing_date": changed["filing_date"],
        "acceptance_datetime": changed["acceptance_datetime"], "report_date": changed["report_date"],
        "exhibit_url": changed["exhibit_url"],
    }


def test_the_profile_lookup_is_typed():
    assert source_family_for_profile(RIGHTS_PROFILE) == "sec_edgar"
    for profile in (
        None, 5, [], {}, [RIGHTS_PROFILE], {RIGHTS_PROFILE: 1}, (RIGHTS_PROFILE,), b"x", "", "unknown-profile",
        RIGHTS_PROFILE + " ", RIGHTS_PROFILE.upper(), _StrSub(RIGHTS_PROFILE), _StrKey(RIGHTS_PROFILE), _Twin(RIGHTS_PROFILE),
        _Hostile(), _HostileTyped(), _DictSub(),
    ):
        with pytest.raises(PgPreparationRefused) as caught:
            source_family_for_profile(profile)
        assert type(caught.value) is PgPreparationRefused
        assert (caught.value.reason, caught.value.detail) == ("unsupported_source_profile", "profile")


# -- R5.8: the traced acquisition ------------------------------------------------------------------

_SUBMISSIONS = "https://data.sec.gov/submissions/CIK0000080424.json"
_ANSWERS = (
    (500, b""), (404, b""), (0, b"{}"), (-1, b"{}"), (301, b"{}"), (2 ** 70, b"{}"),
    (200, b""), (200, b"{"), (200, b"[]"), (200, b"null"), (200, b"5"), (200, b'"x"'), (200, b"\xff\xfe\x00"),
    (200, b"\xef\xbb\xbf{}"), (200, b"<html></html>"), (200, b'{"filings": NaN}'), (200, b'{"filings": "\\ud800"}'),
    (200, b'{"filings": {"recent": ' + b"9" * 5000 + b"}}"),
    (200, b"[" * 100000 + b"]" * 100000), (200, b'{"a":' * 100000 + b"1" + b"}" * 100000),
    (200, b"<html><body>" + b"<div>" * 1000 + b"x" + b"</div>" * 1000 + b"</body></html>"),
)


def _traced(http_get, accession=None):
    """``("returned", acquisition)`` or ``("refused", RefreshError)``; anything else fails the test."""
    events = []
    try:
        acquisition = acquire_results_filing(
            cik="0000080424", http_get=http_get, accession=accession, trace=events.append
        )
    except RefreshError as error:
        assert type(error) is RefreshError
        return "refused", error
    assert len(events) == 1
    return "returned", acquisition


def _answering(case, overrides):
    base = fixture_http_get(case)

    def http_get(url):
        if url in overrides:
            return overrides[url]
        try:
            return base(url)
        except AssertionError:
            return 404, b""  # the fixture asserts on a URL it does not know; a server answers 404

    return http_get


# -- R6.1: within one fiscal period the source clock never steps back ------------------------------

_OLDER_SOURCE = ("source_precedes_prior_event", "prior.workspace.lifecycle.source_available_at")


def test_an_older_filing_never_supersedes_a_newer_one(monkeypatch, chain):
    """Three nights.  The newest exhibit fails once; the fallback to the older filing must not enter the chain."""
    monkeypatch.setattr(refresh_module, "_PACE_S", 0)
    status, amended = _traced(fixture_http_get("amendment_sequence"))
    assert status == "returned"
    assert (amended["accession"], amended["form"], amended["currentness"]["state"]) == (
        fixture_accession("amended"), "8-K/A", "up_to_date"
    )
    first_night = prepare_pg_workspace(amended, prior=None, observed_at="2026-07-31T02:00:00Z")
    # The second night: the amendment's exhibit answers 503, so the acquisition falls back to the original filing.
    status, fallback = _traced(_answering("amendment_sequence", {amended["exhibit_url"]: (503, b"")}))
    assert status == "returned"
    assert (fallback["accession"], fallback["form"], fallback["currentness"]["state"]) == (
        fixture_accession("older"), "8-K", "newer_source_pending"
    )
    assert fallback["acceptance_datetime"] < amended["acceptance_datetime"]
    assert _refusal(fallback, first_night, "2026-08-01T02:00:00Z") == _OLDER_SOURCE
    # The refusal does not depend on the stamp: the older filing is refused however current it claims to be.
    for stamp in (
        {"state": "up_to_date", "checked_at": "2026-08-01T01:59:00Z"},
        {"state": "currentness_unverified", "checked_at": None},
    ):
        assert _refusal(dict(fallback, currentness=stamp), first_night, "2026-08-01T02:00:00Z") == _OLDER_SOURCE
    assert _refusal(_without(fallback, ("currentness",)), first_night, "2026-08-01T02:00:00Z") == _OLDER_SOURCE
    # The third night: the amendment is back.  The caller kept the first night, and the result is the first night.
    status, again = _traced(fixture_http_get("amendment_sequence"))
    assert status == "returned"
    third_night = prepare_pg_workspace(again, prior=first_night, observed_at="2026-08-02T02:00:00Z")
    for key in _COMPARED:
        assert third_night[key] == first_night[key], key
    assert third_night["document_metadata"]["revision"] == 1
    assert third_night["document_metadata"]["fetched_at"] == "2026-07-31T02:00:00Z"
    # With no prior the older filing is a root: the rule orders a chain, it does not judge a first record.
    assert _outcome(fallback, None, "2026-08-01T02:00:00Z")[2]["document_metadata"]["revision"] == 1
    # The same holds on top of a correction: the older, uncorrected text never follows the corrected one.
    older, _, _, _ = chain["root"]
    for name in ("changed", "changed_twice", "refiled_after_correction", "amendment"):
        newer, _, _, held = chain[name]
        assert older["acceptance_datetime"] < newer["acceptance_datetime"]
        assert _refusal(older, held, "2026-08-03T00:00:00Z") == _OLDER_SOURCE
    # Equal acceptance clocks are no step back: a refiling accepted at the predecessor's clock is admitted.
    assert chain["refiled"][0]["acceptance_datetime"] == chain["root"][0]["acceptance_datetime"]
    assert chain["refiled"][3]["document_metadata"]["revision"] == 2


def test_a_generation_id_can_repeat_along_a_chain_and_the_revision_cannot(chain):
    """Equal run clocks: a text that alternates in place rebuilds the same workspace at a later chain position."""
    first, _, _, root = chain["root"]
    second = chain["changed_in_place"][0]
    clock = "2026-07-30T09:00:00Z"
    results = [root]
    for acquisition in (second, first, second):
        results.append(prepare_pg_workspace(acquisition, prior=results[-1], observed_at=clock))
    assert [result["document_metadata"]["revision"] for result in results] == [1, 2, 3, 4]
    assert results[3]["workspace"] == results[1]["workspace"]
    assert results[3]["workspace"]["generation_id"] == results[1]["workspace"]["generation_id"]
    assert results[3]["document_metadata"] != results[1]["document_metadata"]
    for result in results:
        assert _p2_violations(result) == []
    DocumentRevisionChain(tuple(_native_document(result["document_metadata"]) for result in results))


def test_a_token_of_128_characters_is_admitted_and_one_of_129_is_not(chain):
    fourth, _, _, root = chain["root"]
    earlier = _outcome(_quarter("2026-04-24T17:00:00Z", "555"), None, "2026-04-24T17:30:00Z")[2]
    changed, _, _, second = chain["changed"]
    for length, admitted in ((128, True), (129, False)):
        token = "e" * length
        event = _replace_at(_replace_at(earlier, _W + ("event_id",), token), _D + ("event_id",), token)
        document = _replace_at(_replace_at(earlier, _RELEASE + ("document_id",), token), _D + ("document_id",), token)
        supersedes = _replace_at(second, _D + ("supersedes_document_id",), token)
        if admitted:
            # An earlier period is no predecessor, so an admitted token leaves the root unchanged.
            assert _outcome(fourth, event, "2026-07-29T17:10:00Z")[2] == root
            assert _outcome(fourth, document, "2026-07-29T17:10:00Z")[2] == root
            carried = _outcome(changed, supersedes, "2026-08-01T00:00:00Z")[2]
            assert carried["document_metadata"]["supersedes_document_id"] == token
        else:
            assert _refusal(fourth, event, "2026-07-29T17:10:00Z") == ("malformed_prior", "prior.workspace.event_id")
            assert _refusal(fourth, document, "2026-07-29T17:10:00Z") == (
                "prior_source_identity_missing", "prior.workspace.sources.document_id"
            )
            assert _refusal(changed, supersedes, "2026-08-01T00:00:00Z") == (
                "malformed_prior", "prior.document_metadata.supersedes_document_id"
            )


def test_traced_acquisition_returns_or_raises_refresh_error_for_every_answer(monkeypatch, chain):
    monkeypatch.setattr(refresh_module, "_PACE_S", 0)
    root = chain["root"][3]
    outcomes = {"returned": 0, "refused": 0, "prepared": 0, "prepared refusal": 0}

    def run(case, overrides, accession=None, priors=(None,)):
        kind, value = _traced(_answering(case, overrides), accession)
        outcomes[kind] += 1
        if kind == "returned":
            for prior in priors:
                reason, _, _ = _outcome(value, prior, "2026-12-31T00:00:00Z", f"{case} {sorted(overrides)}")
                outcomes["prepared" if reason == "returned" else "prepared refusal"] += 1

    # Every answer at every URL the acquisition asks for, latest and exact-accession, with and without a prior.
    for case, asked in (("same_source_rebuild", 3), ("newer_fetch_failed", 5)):
        seen = []
        base = fixture_http_get(case)
        acquire_results_filing(
            cik="0000080424", http_get=lambda url: (seen.append(url), base(url))[1], trace=[].append
        )
        assert _SUBMISSIONS in seen and len(set(seen)) == asked, seen
        for url in sorted(set(seen)):
            for answer in _ANSWERS:
                run(case, {url: answer}, priors=(None, root))
                run(case, {url: answer}, accession=fixture_accession("older"), priors=(None, root))
    # Every value of the submissions document, down to the first two entries of each column.
    base = fixture_http_get("same_source_rebuild")
    payload = json.loads(base(_SUBMISSIONS)[1].decode("utf-8"))
    swept = 0
    for path, original in _nodes(payload):
        if len(path) > 4 or (len(path) == 4 and type(path[-1]) is int and path[-1] > 1):
            continue
        swept += 1
        for value in (None, 5, "x", [], {}, ["x"], "2026-02-30", "8-K/A", "2026-07-29T17:10:00.000Z"):
            body = json.dumps(_replace_at(payload, path, value)).encode("utf-8")
            run("same_source_rebuild", {_SUBMISSIONS: (200, body)})
        if path:
            run("same_source_rebuild", {_SUBMISSIONS: (200, json.dumps(_without(payload, path)).encode("utf-8"))})
    assert swept == 17, swept
    assert outcomes == {"returned": 197, "refused": 308, "prepared": 318, "prepared refusal": 14}, outcomes


def test_traced_acquisition_converts_exactly_the_six_classes(monkeypatch):
    monkeypatch.setattr(refresh_module, "_PACE_S", 0)
    for raised in (
        TypeError("t"), ValueError("v"), ZeroDivisionError("z"), OverflowError("o"), KeyError("k"), IndexError("i"),
        AttributeError("a"), RecursionError("r"),
    ):
        events = []

        def http_get(url, raised=raised):
            raise raised

        with pytest.raises(RefreshError) as caught:
            acquire_results_filing(cik="0000080424", http_get=http_get, trace=events.append)
        assert type(caught.value) is RefreshError
        assert str(caught.value) == f"results filing acquisition met a malformed response ({type(raised).__name__})"
        assert caught.value.__cause__ is raised
        assert events == []
    for raised in (RuntimeError("r"), NotImplementedError("n"), MemoryError("m"), AssertionError("a"), OSError("o")):
        def http_get(url, raised=raised):
            raise raised

        with pytest.raises(type(raised)) as caught:
            acquire_results_filing(cik="0000080424", http_get=http_get, trace=[].append)
        assert caught.value is raised
    refused = RefreshError("the transport refused")

    def http_get(url):
        raise refused

    with pytest.raises(RefreshError) as caught:
        acquire_results_filing(cik="0000080424", http_get=http_get, trace=[].append)
    assert caught.value is refused
    # A document nested past the decoder's recursion limit is a malformed response, not a crash.
    kind, error = _traced(_answering("same_source_rebuild", {_SUBMISSIONS: (200, b"[" * 100000 + b"]" * 100000)}))
    assert kind == "refused"
    assert str(error) == "results filing acquisition met a malformed response (RecursionError)"


def test_a_trace_callback_exception_is_never_converted(monkeypatch):
    monkeypatch.setattr(refresh_module, "_PACE_S", 0)
    for raised in (ValueError("callback failed"), KeyError("callback failed"), TypeError("callback failed")):
        def trace(event, raised=raised):
            raise raised

        with pytest.raises(type(raised)) as caught:
            acquire_results_filing(cik="0000080424", http_get=fixture_http_get("same_source_rebuild"), trace=trace)
        assert caught.value is raised
        assert caught.value.__cause__ is None


def test_the_callback_less_acquisition_is_not_wrapped(monkeypatch):
    monkeypatch.setattr(refresh_module, "_PACE_S", 0)
    for raised in (KeyError("k"), TypeError("t"), RecursionError("r")):
        def http_get(url, raised=raised):
            raise raised

        with pytest.raises(type(raised)) as caught:
            acquire_results_filing(cik="0000080424", http_get=http_get)
        assert caught.value is raised
