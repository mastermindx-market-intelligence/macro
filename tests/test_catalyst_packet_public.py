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


def grants(*, audience="public_anonymous", expires=None, allowed=True):
    def resolve(sid, now):
        if not allowed:
            return None
        return PublicSourceGrant(
            source_id=sid, receipt_id="fixture-rights:" + sid, owner_ref="test-owner-only",
            audience=audience, effective_at_utc=NOW - timedelta(days=2),
            expires_at_utc=expires or NOW + timedelta(days=2),
            display_link=True, display_title=True, display_facts=True)
    return resolve


def build(raw=None, **kwargs):
    return build_event_packet(raw or event(), issuers=universe(),
                              rights_resolver=kwargs.pop("rights_resolver", grants()),
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
