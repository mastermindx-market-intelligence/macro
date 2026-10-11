"""Public-rights, evidence, clocks, relation and correction fixture discrimination.

PFE case uses the ACTUAL 2026-08-04 SEC accession and canonical EDGAR
producer shape; the rights grants are TEST DOUBLES, never a claim of a real
public source-rights owner receipt. TST is a deliberately imaginary issuer.
"""
from datetime import datetime, timedelta, timezone
from copy import deepcopy

import pytest

from engine.marketing.catalyst_packets import PublicSourceGrant, build_event_packet

UTC = timezone.utc
NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
SEC_URL = ("https://www.sec.gov/Archives/edgar/data/78003/"
           "000007800326000094/0000078003-26-000094-index.htm")
SEC_ID = "sec:0000078003:0000078003-26-000094"


def event():
    return {"source": "edgar_8k_202", "id": "PFE-0000078003-26-000094",
            "filing_key": "0000078003:0000078003-26-000094", "cik": 78003,
            "ticker": "PFE", "when": "2026-08-04T11:03:10",
            "when_semantics": "processing_wall_clock",
            "acceptance_datetime": "2026-08-04T07:02:43-04:00",
       "publication_time_utc": "2026-08-04T11:03:10Z",
            "source_url": SEC_URL, "_eps_basis": "gaap",
            "eps_actual": -0.04, "eps_est": -0.04,
            "rev_actual": 15034000000.0, "private_body": "NEVER PUBLISH THIS"}


def universe():
    return {"PFE": {"issuer_id": "cik:0000078003", "name": "Pfizer", "supported": True,
                    "dossier_path": "/stocks/PFE/"},
            "TST": {"issuer_id": "cik:0000123456", "name": "Fictional Test", "supported": True,
                    "dossier_path": "/stocks/TST/"},
            "OUT": {"issuer_id": "cik:0000999999", "supported": False}}


def grants(*, audience="public_anonymous", expires=None, allowed=True, documents=None):
    # TEST-ONLY source-rights map: this is never derived from a live event.
    permitted_documents = {SEC_ID: SEC_URL, **(documents or {})}
    def resolve(sid, now):
        if not allowed:
            return None
        return PublicSourceGrant(
            source_id=sid, receipt_id="fixture-rights:" + sid, owner_ref="test-owner-only",
            audience=audience, effective_at_utc=NOW - timedelta(days=2),
            expires_at_utc=expires or NOW + timedelta(days=2),
            display_link=True, display_title=True, display_facts=True,
            document_url=permitted_documents.get(sid, ""))
    return resolve


def build(raw=None, **kwargs):
    # In fixtures only, explicitly grant rights for listed test documents.
    # Real callers MUST obtain each document scope from the incumbent owner.
    documents = {
        row["source_id"]: row["url"] for row in kwargs.get("source_refs", ())
        if isinstance(row, dict) and isinstance(row.get("source_id"), str)
        and isinstance(row.get("url"), str)
    }
    resolver = kwargs.pop("rights_resolver", None)
    if resolver is None:
        resolver = grants(documents=documents)
    return build_event_packet(raw or event(), issuers=universe(),
                              rights_resolver=resolver,
                              as_of=kwargs.pop("as_of", NOW), **kwargs)


def test_real_sec_filing_identity_and_separately_attested_publication():
    p = build()
    assert p["public_safe"] is True
    assert p["event_time_utc"] == "2026-08-04T11:02:43Z"
    assert p["first_observed_at_utc"] == "2026-08-04T11:03:10Z"
    assert p["publication_time_utc"] == "2026-08-04T11:03:10Z"
    assert p["source_refs"][0]["source_id"] == SEC_ID
    assert p["source_refs"][0]["first_observed_at_utc"] == p["first_observed_at_utc"]
    assert p["source_refs"][0]["url"] == SEC_URL
    assert p["primary_subject"]["issuer_id"] == "cik:0000078003"
    assert p["affected_tickers"][0]["relationship"] == "DIRECT"
    assert all(x["evidence_ids"] for x in p["what_changed"])
    assert {x["source_id"] for x in p["evidence"]} == {SEC_ID}
    assert any("-0.04" in x["text"] for x in p["what_changed"])
    assert "consensus_not_independently_evidenced" in p["missing_data"]
    assert "publication_time_not_attested" not in p["missing_data"]
    assert "NEVER PUBLISH" not in str(p)


def test_duplicate_news_story_cannot_change_stable_sec_event_id():
    a = event()
    b = {**a, "id": "second vendor story id", "private_teaser": "secret"}
    assert build(a)["event_id"] == build(b)["event_id"]
    assert build(a) == build(b)


def test_qualified_indirect_must_have_independent_source_anchor_and_evidence_id():
    source = {"source_id": "issuer_contract_001", "title": "Test company contract excerpt",
              "url": "https://example.com/official-contract", "evidence_ids": ["rel_001"],
              "first_observed_at_utc": "2026-08-04T14:00:00Z",
              "published_at_utc": "2026-08-04T13:58:00Z"}
    relation = {"ticker": "TST", "issuer_id": "cik:0000123456",
                "primary_issuer_id": "cik:0000078003", "relationship": "EVIDENCED_INDIRECT",
                "relation_type": "supplier", "source_id": "issuer_contract_001",
                "evidence_id": "rel_001", "source_anchor": "document:section-2"}
    p = build(source_refs=[source], relationships=[relation])
    assert p["affected_tickers"][-1]["ticker"] == "TST"
    assert p["affected_tickers"][-1]["relationship"] == "EVIDENCED_INDIRECT"
    assert {x["evidence_id"] for x in p["evidence"]} >= {"rel_001"}
    assert p["source_refs"][-1]["first_observed_at_utc"] == "2026-08-04T14:00:00Z"
    # A nearby story, plausible prose or an unanchored relation is insufficient.
    assert len(build(source_refs=[{**source, "evidence_ids": []}], relationships=[relation])
               ["affected_tickers"]) == 1
    assert len(build(source_refs=[source], relationships=[{**relation, "source_anchor": ""}])
               ["affected_tickers"]) == 1
    assert len(build({**event(), "co_mentioned_tickers": ["TST"]})["affected_tickers"]) == 1


def test_private_relation_is_rights_blocked_and_no_text_exposed():
    source = {"source_id": "paid_story_007", "title": "SECRET VENDOR NEWS",
              "url": "https://paid.example/story", "evidence_ids": ["rel_paid"]}
    relation = {"ticker": "TST", "issuer_id": "cik:0000123456",
                "primary_issuer_id": "cik:0000078003", "relationship": "EVIDENCED_INDIRECT",
                "relation_type": "supplier", "source_id": "paid_story_007",
                "evidence_id": "rel_paid", "source_anchor": "vendor/private"}
    def resolver(sid, now):
        return grants()(sid, now) if sid == SEC_ID else None
    packet = build(rights_resolver=resolver, source_refs=[source], relationships=[relation])
    assert packet["public_safe"] is True
    assert packet["rights_blocked_tickers"] == ["TST"]
    assert "SECRET VENDOR NEWS" not in str(packet)
    assert "paid.example" not in str(packet)


@pytest.mark.parametrize("bad", [
    lambda: grants(allowed=False),
    lambda: grants(audience="site_full"),
    lambda: grants(expires=NOW - timedelta(seconds=1)),
])
def test_missing_wrong_audience_or_expired_public_rights_withholds_all_facts(bad):
    p = build(rights_resolver=bad())
    assert p["public_disposition"] == "BLOCKED_PUBLIC"
    assert p["source_refs"] == p["evidence"] == p["what_changed"] == []
    assert "NEVER PUBLISH" not in str(p)


def test_official_url_and_producer_identity_are_not_self_authorizing():
    for patch in ({"source_url": "https://evil.example.com/private"},
                  {"source_url": "https://www.sec.gov:bad/Archives/data"},
                  {"cik": 78004},
                  {"filing_key": "0000000000:0000078003-26-000094"}):
        p = build({**event(), **patch})
        assert p["public_safe"] is not True
        assert not p["what_changed"]


def test_stale_and_misidentified_clock_fail_closed():
    assert build(as_of=NOW + timedelta(days=20))["public_safe"] is not True
    assert build({**event(), "when": "2026-08-04T03:00:00"})["public_safe"] is not True
    assert build({**event(), "when_semantics": "unknown"})["public_safe"] is not True


def test_corrected_generation_preserves_event_identity_and_records_supersession():
    original = build()
    corrected = build({**event(), "eps_actual": -0.03, "correction_generation": 1,
                       "revision_status": "corrected", "supersedes_generation": 0,
                       "correction_reason": "official_amendment"})
    assert corrected["event_id"] == original["event_id"]
    assert corrected["correction"]["supersedes_generation"] == 0
    assert corrected["evidence"] != original["evidence"]
    retracted = build({**event(), "correction_generation": 2,
                       "revision_status": "retracted", "supersedes_generation": 1,
                       "correction_reason": "source_retraction"})
    assert retracted["public_disposition"] == "RETRACTED"
    assert retracted["what_changed"] == []


def test_llm_hallucinated_number_never_enters_claims_or_scenarios():
    actual = build()
    raw = {**event(), "model_summary": "Revenue surged 99% due to fake deal",
           "model_confidence": 0.999}
    p = build(raw, scenarios=[{"case": "bull", "trigger": "unknown_llm_prediction",
                              "invalidator": "source_withdrawn",
                              "evidence_ids": [actual["evidence"][0]["evidence_id"]],
                              "text": "99% moonshot"}])
    assert "99%" not in str(p)
    assert p["scenarios"] == []
    good = build(scenarios=[{"case": "bear", "trigger": "filing_amended",
                             "invalidator": "filing_corrected",
                             "evidence_ids": [actual["evidence"][0]["evidence_id"]],
                             "text": "9999% collapse expected"}])
    assert len(good["scenarios"]) == 1
    assert "9999" not in str(good)
    assert good["scenarios"][0]["forecast_probability"] is None


def test_private_qbus_story_will_not_get_public_from_paid_read():
    paid_story = {"event_id": "news-1", "event_kind": "ai_capex", "source": "benzinga",
                  "source_id": "benzinga:private-1", "ticker": "PFE", "issuer_id": "cik:0000078003",
                  "event_time_utc": "2026-08-04T11:02:43Z",
                  "first_observed_at_utc": "2026-08-04T11:03:10Z",
                  "source_url": "https://benzinga.com/private", "source_title": "SECRET CONTENT",
                  "body": "PRIVATE BODY"}
    p = build(paid_story, rights_resolver=grants(audience="site_full"))
    assert p["public_disposition"] == "BLOCKED_PUBLIC"
    assert "SECRET CONTENT" not in str(p)
    assert "PRIVATE BODY" not in str(p)


def test_absent_publication_is_not_silently_guessed_from_sec_acceptance():
    raw = event()
    raw.pop("publication_time_utc")
    p = build(raw)
    assert p["public_disposition"] == "BLOCKED_PUBLIC"
    assert not p["sources"] and not p["what_changed"]
    assert "publication_time_not_attested" in p["missing_data"]


@pytest.mark.parametrize("unsafe_url", [
    "https://127.0.0.1/Archives/private",
    "https://192.168.1.10/Archives/private",
    "https://localhost/Archives/private",
    "https://internal.local/Archives/private",
    "https://[::1]/Archives/private",
])
def test_private_link_destination_is_not_published_even_with_fake_grant(unsafe_url):
    packet = build(source_refs=[{"source_id": "private_link", "title": "Private",
                                  "url": unsafe_url,
                                  "published_at_utc": "2026-08-04T11:03:10Z"}])
    assert all(s["source_id"] != "private_link" for s in packet["source_refs"])
    assert unsafe_url not in str(packet)


def test_duplicate_source_identity_with_conflicting_title_is_quarantined():
    one = {"source_id": "source_22", "title": "Documented relationship",
           "url": "https://example.com/official", "evidence_ids": ["relation-1"],
           "published_at_utc": "2026-08-04T13:58:00Z"}
    two = {**one, "title": "Contradictory identity"}
    three = dict(one)
    p = build(source_refs=[one, two, three])
    assert p["public_safe"] is True
    assert all(s["source_id"] != "source_22" for s in p["sources"])
    assert "Contradictory identity" not in str(p)


def test_oversize_source_list_refuses_public_projection_instead_of_truncating():
    rows = [{"source_id": f"issuer_source_{i}", "title": f"Public source {i}",
             "url": f"https://example.com/release-{i}",
             "published_at_utc": "2026-08-04T13:58:00Z"}
            for i in range(12)]
    p = build(source_refs=rows)
    assert p["public_safe"] is False
    assert p["public_disposition"] == "UNAVAILABLE"
    assert "too_many_public_sources" in p["missing_data"]
    assert p["sources"] == []


def test_source_titles_and_identifiers_respect_session_00_public_limits():
    too_long_title = {"source_id": "source_ok", "title": "Q" * 151,
                      "url": "https://example.com/filing",
                      "published_at_utc": "2026-08-04T13:58:00Z"}
    too_long_id = {**too_long_title, "source_id": "a" * 129, "title": "Qualified"}
    p = build(source_refs=[too_long_title, too_long_id])
    assert p["public_safe"] is True
    assert len(p["sources"]) == 1


# Stage-A independent negative findings, original Session 01 carrier only.
SEC_EXHIBIT_URL = ("https://www.sec.gov/Archives/edgar/data/78003/"
                   "000007800326000094/pfe-6282026xex99.htm")


def test_same_filing_grant_does_not_authorize_another_exhibit():
    approved = build()
    assert approved["public_disposition"] == "PUBLIC_READY"
    other_document = build({**event(), "source_url": SEC_EXHIBIT_URL})
    assert other_document["public_disposition"] == "BLOCKED_PUBLIC"
    assert other_document["public_safe"] is False
    assert other_document["sources"] == other_document["what_changed"] == []
    assert SEC_EXHIBIT_URL not in str(other_document)
    # Same filing identifier, separate independently scoped owner approval.
    individually_approved = build(
        {**event(), "source_url": SEC_EXHIBIT_URL},
        rights_resolver=grants(documents={SEC_ID: SEC_EXHIBIT_URL}),
    )
    assert individually_approved["public_disposition"] == "PUBLIC_READY"
    assert individually_approved["sources"][0]["url"] == SEC_EXHIBIT_URL
    assert individually_approved["event_id"] == approved["event_id"]


def test_missing_document_binding_and_wrong_issuer_grant_fail_closed():
    from dataclasses import replace

    def no_document(sid, now):
        return replace(grants()(sid, now), document_url="")
    denied = build(rights_resolver=no_document)
    assert denied["public_disposition"] == "BLOCKED_PUBLIC"
    assert denied["sources"] == denied["what_changed"] == []

    def wrong_document(sid, now):
        return replace(grants()(sid, now), document_url=SEC_EXHIBIT_URL)
    denied = build(rights_resolver=wrong_document)
    assert denied["public_disposition"] == "BLOCKED_PUBLIC"
    assert not denied["sources"]


def test_corrected_document_requires_new_rights_receipt():
    prior = build()
    altered_event = {**event(), "source_url": SEC_EXHIBIT_URL,
                     "correction_generation": 1, "revision_status": "corrected",
                     "supersedes_generation": 0,
                     "correction_reason": "official_amendment"}
    denied = build(altered_event)
    assert denied["generation"] == 1
    assert denied["event_id"] == prior["event_id"]
    assert denied["public_disposition"] == "BLOCKED_PUBLIC"
    assert denied["what_changed"] == []
    admitted = build(altered_event, rights_resolver=grants(documents={
        SEC_ID: SEC_EXHIBIT_URL,
    }))
    assert admitted["public_disposition"] == "PUBLIC_READY"
    assert admitted["correction_state"] == "CORRECTED"


@pytest.mark.parametrize("private_key", [
    "token", "email", "api_key", "session_id", "client_secret", "user_id",
    "authorization", "jwt",
])
@pytest.mark.parametrize("encoded_depth", [0, 1, 2, 4, 8])
def test_private_encoded_source_parameter_never_reaches_public_packet(
    private_key, encoded_depth,
):
    from urllib.parse import quote
    injected = f"&{private_key}=fixture_private_value"
    for _ in range(encoded_depth):
        injected = quote(injected, safe="")
    private_url = SEC_URL + "?ref=ok" + injected
    # Even a resolver returning an exact matching grant must not be able to
    # turn a recipient secret into an otherwise PUBLIC_READY source URL.
    result = build({**event(), "source_url": private_url},
                   rights_resolver=grants(documents={SEC_ID: private_url}))
    assert result["public_safe"] is False
    assert result["public_disposition"] == "BLOCKED_PUBLIC"
    assert result["what_changed"] == []
    assert result["sources"] == []
    assert "fixture_private_value" not in str(result)


@pytest.mark.parametrize("private_url", [
    SEC_URL + "#token=fixture_private_value",
    SEC_URL + "?contact=reader%40example.com",
    SEC_URL + "?ref=ok%26token%3Dfixture_private_value",
    SEC_URL + "?access%255Ftoken=fixture_private_value",
    SEC_URL + "?ref=ok%2526session%255Fid%253Dfixture_private_value",
    SEC_URL + "?ref=%0d%0aAuthorization%3Asecret",
])
def test_url_fragment_email_and_nested_encoded_identity_denied(private_url):
    result = build({**event(), "source_url": private_url},
                   rights_resolver=grants(documents={SEC_ID: private_url}))
    assert result["public_disposition"] == "BLOCKED_PUBLIC"
    assert result["sources"] == result["what_changed"] == []


@pytest.mark.parametrize("public_url", [
    SEC_URL,
    SEC_URL + "?download=1",
    SEC_EXHIBIT_URL,
    SEC_EXHIBIT_URL + "#page=2",
])
def test_normal_sec_urls_remain_eligible_with_individual_grant(public_url):
    result = build({**event(), "source_url": public_url},
                   rights_resolver=grants(documents={SEC_ID: public_url}))
    assert result["public_disposition"] == "PUBLIC_READY"
    assert result["sources"][0]["url"] == public_url


def test_real_edgar_shape_without_separately_attested_publication_fails_closed():
    raw = event()
    raw.pop("publication_time_utc")
    # The actual incumbent edgar_earnings_wire.build_event lacks that clock.
    # Its processing "when" and SEC acceptance MUST NOT become publication.
    raw["when"] = "2026-08-04T11:03:10"
    result = build(raw, rights_resolver=grants())
    assert result["publication_time_utc"] is None
    assert "publication_time_not_attested" in result["missing_data"]
    assert result["public_disposition"] == "BLOCKED_PUBLIC"
    assert not result["sources"] and not result["what_changed"]


DOC_SHA = "a" * 64


def stage_a_receipt(*, first="2026-08-04T11:03:10Z",
                    checked=NOW, digest=DOC_SHA,
                    url=SEC_URL, published=None,
                    pub_ref=""):
    from engine.marketing.catalyst_packets import VerifiedDocumentObservation
    return VerifiedDocumentObservation(
        source_id=SEC_ID,
        document_url=url,
        document_sha256=digest,
        receipt_id="test-only-retained-successful-observation",
        owner_ref="test-ingestion-owner-not-publication",
        first_verified_at_utc=first,
        checked_at_utc=checked,
        source_snapshot_version="test-snapshot-001",
        status="verified",
        official_published_at_utc=published,
        official_publication_ref=pub_ref,
    )


def versioned_rights(sid, now):
    from dataclasses import replace
    return replace(grants()(sid, now), document_sha256=DOC_SHA)


def test_stage_a_verified_availability_without_official_publication_is_safe():
    raw = event()
    raw.pop("publication_time_utc")
    p = build(raw, document_observation=stage_a_receipt(),
              rights_resolver=versioned_rights)
    assert p["public_safe"] is True
    assert p["public_disposition"] == "PUBLIC_READY"
    assert p["publication_time_utc"] is None
    assert p["event_time_utc"] == "2026-08-04T11:02:43Z"
    assert p["first_observed_at_utc"] == "2026-08-04T11:03:10Z"
    assert p["document_sha256"] == DOC_SHA
    assert p["observation_receipt_id"] == "test-only-retained-successful-observation"
    assert p["sources"][0]["first_verified_at_utc"] == p["first_observed_at_utc"]
    assert p["sources"][0]["published_at_utc"] is None
    assert p["sources"][0]["document_sha256"] == DOC_SHA
    assert "publication_time_not_attested" not in p["missing_data"]
    assert p["what_changed"] and p["evidence"]


def test_stage_a_refresh_cannot_make_historical_acceptance_recent():
    raw = event()
    raw.pop("publication_time_utc")
    later = NOW + timedelta(days=8)
    def later_rights(sid, at):
        from dataclasses import replace
        return replace(versioned_rights(sid, at),
                       effective_at_utc=NOW - timedelta(days=2),
                       expires_at_utc=later + timedelta(days=1))
    p = build(raw, as_of=later,
              document_observation=stage_a_receipt(checked=later),
              rights_resolver=later_rights)
    assert p["public_safe"] is False
    assert "event_outside_freshness_window" in p["missing_data"]
    assert p["what_changed"] == []


def test_stage_a_digest_or_document_mismatch_requires_renewed_rights():
    raw = event()
    raw.pop("publication_time_utc")
    for receipt in (
        stage_a_receipt(digest="b" * 64),
        stage_a_receipt(url=SEC_EXHIBIT_URL),
    ):
        p = build(raw, document_observation=receipt,
                  rights_resolver=versioned_rights)
        assert p["public_safe"] is False
        assert p["sources"] == p["what_changed"] == []
    p = build(raw, document_observation=stage_a_receipt(),
              rights_resolver=grants())
    assert p["public_disposition"] == "BLOCKED_PUBLIC"
    assert p["sources"] == []


@pytest.mark.parametrize("first,checked", [
    ("2026-08-04T11:00:00Z", NOW),  # before source acceptance
    ("2026-08-06T10:00:00Z", NOW),  # future first observation
    ("2026-08-04T11:03:10Z", NOW - timedelta(minutes=11)),  # stale recheck
])
def test_stage_a_bad_retained_document_clock_denies(first, checked):
    raw = event()
    raw.pop("publication_time_utc")
    p = build(raw, document_observation=stage_a_receipt(first=first, checked=checked),
              rights_resolver=versioned_rights)
    assert p["public_safe"] is False
    assert p["sources"] == p["what_changed"] == []


def test_stage_a_processing_clock_never_rewrites_retained_first_availability():
    raw = event()
    raw.pop("publication_time_utc")
    raw["when"] = "2026-08-05T11:59:59"  # fresh but not first availability
    p = build(raw, document_observation=stage_a_receipt(),
              rights_resolver=versioned_rights)
    assert p["public_disposition"] == "PUBLIC_READY"
    assert p["first_observed_at_utc"] == "2026-08-04T11:03:10Z"
    assert p["processing_time_utc"] == "2026-08-05T11:59:59Z"


def test_stage_a_official_publication_requires_separate_provenance():
    raw = event()
    raw.pop("publication_time_utc")
    p = build(raw, document_observation=stage_a_receipt(
        published="2026-08-04T11:03:00Z"), rights_resolver=versioned_rights)
    assert p["public_disposition"] == "UNAVAILABLE"
    assert "unqualified_official_publication_provenance" in p["missing_data"]
    with_ref = build(raw, document_observation=stage_a_receipt(
        published="2026-08-04T11:03:00Z",
        pub_ref="test-sec-official-published-at-receipt"),
        rights_resolver=versioned_rights)
    assert with_ref["public_disposition"] == "PUBLIC_READY"
    assert with_ref["publication_time_utc"] == "2026-08-04T11:03:00Z"


def test_stage_a_packet_is_explicitly_v2_and_legacy_fixture_remains_v1():
    raw = event()
    raw.pop("publication_time_utc")
    observed = build(raw, document_observation=stage_a_receipt(),
                     rights_resolver=versioned_rights)
    legacy = build()
    assert (observed["schema"], observed["schema_version"]) == (
        "catalyst.public_event/v2", 2)
    assert (legacy["schema"], legacy["schema_version"]) == (
        "catalyst.public_event/v1", 1)
    assert observed["publication_time_utc"] is None
    assert legacy["publication_time_utc"] is not None


def test_stage_a_document_digest_correction_requires_renewed_version_rights():
    from dataclasses import replace
    raw = {**event(), "correction_generation": 1, "revision_status": "corrected",
           "supersedes_generation": 0, "correction_reason": "official_amendment"}
    raw.pop("publication_time_utc")
    fresh_version = stage_a_receipt(digest="b" * 64)
    denied = build(raw, document_observation=fresh_version,
                   rights_resolver=versioned_rights)
    assert denied["public_disposition"] == "BLOCKED_PUBLIC"
    assert denied["what_changed"] == []
    def renewed(sid, at):
        return replace(versioned_rights(sid, at), document_sha256="b" * 64)
    approved = build(raw, document_observation=fresh_version,
                     rights_resolver=renewed)
    assert approved["public_disposition"] == "PUBLIC_READY"
    assert approved["correction_state"] == "CORRECTED"
    assert approved["sources"][0]["document_sha256"] == "b" * 64


def test_withdrawn_or_naive_verified_document_read_is_not_source_attestation():
    from dataclasses import replace
    raw = event()
    raw.pop("publication_time_utc")
    for receipt in (
        replace(stage_a_receipt(), status="withdrawn"),
        replace(stage_a_receipt(), first_verified_at_utc="2026-08-04T11:03:10"),
        replace(stage_a_receipt(), checked_at_utc="2026-08-05T12:00:00"),
        replace(stage_a_receipt(), document_sha256="not a digest"),
    ):
        pkt = build(raw, document_observation=receipt,
                    rights_resolver=versioned_rights)
        assert pkt["public_safe"] is False
        assert pkt["sources"] == pkt["what_changed"] == []


def test_stage_a_verified_document_requires_typed_source_snapshot_version():
    from dataclasses import replace
    raw = event()
    raw.pop("publication_time_utc")
    for bad in ("", "https://not-a-snapshot", "reader@example.com", 123):
        result = build(raw, document_observation=replace(
            stage_a_receipt(), source_snapshot_version=bad),
            rights_resolver=versioned_rights)
        assert result["public_safe"] is False
        assert "unqualified_verified_document_observation" in result["missing_data"]
    good = build(raw, document_observation=stage_a_receipt(),
                 rights_resolver=versioned_rights)
    assert good["source_snapshot_version"] == "test-snapshot-001"


def _actual_sec_earnings_event(*, adjusted_eps=None):
    """Actual incumbent earnings-wire producer, with synthetic issuer data.

    The chosen accession and figures are from the independently checked 2026
    Pfizer 8-K; no network read, public-rights receipt or real availability
    clock is asserted by constructing this fixture.
    """
    from engine.marketing.edgar_earnings_wire import (
        Expectation, Figures, build_event,
    )
    figures = Figures(
        revenue=15034.0, revenue_label="Total Revenues",
        eps=-0.04, eps_label="GAAP diluted earnings per share",
        table_index=0, adjusted_eps=adjusted_eps,
        adjusted_eps_label="Adjusted diluted EPS" if adjusted_eps is not None else "",
    )
    expectation = Expectation(ticker="PFE", cik=78003, eps_forecast=0.71)
    return build_event(
        expectation, figures,
        when=datetime(2026, 8, 4, 11, 3, 10, tzinfo=timezone.utc),
        accession="0000078003-26-000094",
        source_url=SEC_URL, cik=78003,
        acceptance_datetime="2026-08-04T07:02:43-04:00",
        filing_date="2026-08-04", form="8-K",
    )


def test_actual_incumbent_sec_wire_requires_separate_document_observation():
    source = _actual_sec_earnings_event()
    assert source["source"] == "edgar_8k_202"
    assert source["filing_key"] == "0000078003:0000078003-26-000094"
    assert source["when_semantics"] == "processing_wall_clock"
    assert "publication_time_utc" not in source
    denied = build(source, rights_resolver=versioned_rights)
    assert denied["public_disposition"] == "BLOCKED_PUBLIC"
    assert "publication_time_not_attested" in denied["missing_data"]
    assert denied["what_changed"] == denied["sources"] == []
    qualified = build(source, document_observation=stage_a_receipt(),
                      rights_resolver=versioned_rights)
    assert (qualified["schema"], qualified["schema_version"]) == (
        "catalyst.public_event/v2", 2)
    assert qualified["event_time_utc"] == "2026-08-04T11:02:43Z"
    assert qualified["first_observed_at_utc"] == "2026-08-04T11:03:10Z"
    assert qualified["publication_time_utc"] is None
    assert {x["kind"] for x in qualified["evidence"]} == {
        "eps_actual", "rev_actual"}
    assert any("15,034,000,000" in x["text"] for x in qualified["what_changed"])
    assert any("GAAP EPS of -0.04" in x["text"] for x in qualified["what_changed"])
    assert all(x["evidence_ids"] for x in qualified["what_changed"])


def test_real_earnings_wire_adjusted_and_gaap_bases_never_conflated():
    source = _actual_sec_earnings_event(adjusted_eps=0.77)
    assert source["eps_actual"] == 0.77
    assert source["_eps_gaap"] == -0.04
    assert source["_eps_basis"] == "adjusted"
    public = build(source, document_observation=stage_a_receipt(),
                   rights_resolver=versioned_rights)
    assert public["public_disposition"] == "PUBLIC_READY"
    texts = " ".join(item["text"] for item in public["what_changed"])
    assert "ADJUSTED EPS of 0.77" in texts
    assert "GAAP EPS of 0.77" not in texts
    assert "beat" not in texts.lower() and "expected" not in texts.lower()
    assert "consensus_not_independently_evidenced" in public["missing_data"]
