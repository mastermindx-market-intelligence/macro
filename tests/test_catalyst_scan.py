"""Anonymous scan composition negative, dedup, correction, entitlement tests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.marketing.catalyst_packets import PublicSourceGrant, build_event_packet
from engine.marketing.catalyst_scan import (
    SourceCoverageReceipt, compose_scan, normalize_tickers,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
K = "0000078003:0000078003-26-000094"
PRIMARY = "sec:" + K
UNIVERSE = {
    "PFE": {"supported": True, "issuer_id": "cik:0000078003", "dossier_path": "/stocks/PFE/"},
    "TST": {"supported": True, "issuer_id": "cik:0000123456", "dossier_path": "/stocks/TST/"},
    "OTH": {"supported": True, "issuer_id": "cik:0000789012", "dossier_path": "/stocks/OTH/"},
    "OUT": {"supported": False, "issuer_id": "cik:0000000055", "dossier_path": "/stocks/OUT/"},
}
RAW = {"source": "edgar_8k_202", "filing_key": K, "cik": 78003,
       "ticker": "PFE", "when": "2026-08-04T11:03:10", "when_semantics": "processing_wall_clock",
       "acceptance_datetime": "2026-08-04T07:02:43-04:00",
       "publication_time_utc": "2026-08-04T11:03:10Z",
       "source_url": "https://www.sec.gov/Archives/edgar/data/78003/000007800326000094/0000078003-26-000094-index.htm",
       "eps_actual": -0.04, "_eps_basis": "gaap", "rev_actual": 15034000000.0,
       "private_raw_vendor_story": "PRIVATE BODY 21"}


# Explicit TEST-ONLY per-document approvals; no event can grant itself rights.
GRANTED_DOCUMENTS = {
    PRIMARY: RAW["source_url"],
    "rel_src_1": "https://example.com/fictional",
}


def resolver(sid, now):
    return PublicSourceGrant(sid, "fixture-receipt:" + sid, "fixture-rights-owner",
                             "public_anonymous", NOW - timedelta(days=2),
                             NOW + timedelta(days=2), True, True, True,
                             document_url=GRANTED_DOCUMENTS.get(sid, ""))


def packet(**changes):
    return build_event_packet({**RAW, **changes}, issuers=UNIVERSE,
                              rights_resolver=resolver, as_of=NOW)


def scan(tickers, *packets, event_id=None, as_of=NOW):
    return compose_scan(tickers, issuers=UNIVERSE, packets=list(packets),
                        event_id=event_id, as_of=as_of)


def verified_packet(**changes):
    from dataclasses import replace
    from engine.marketing.catalyst_packets import VerifiedDocumentObservation
    source_event = {**RAW, **changes}
    source_event.pop("publication_time_utc", None)
    read = VerifiedDocumentObservation(
        source_id=PRIMARY, document_url=RAW["source_url"],
        document_sha256="a" * 64,
        receipt_id="test-only-retained-document-observation",
        owner_ref="test-incumbent-source-reader",
        first_verified_at_utc="2026-08-04T11:03:10Z",
        checked_at_utc=NOW,
        source_snapshot_version="test-snapshot-001",
        official_published_at_utc=None,
    )
    def version_rights(sid, now):
        return replace(resolver(sid, now), document_sha256="a" * 64)
    return build_event_packet(source_event, issuers=UNIVERSE,
                              rights_resolver=version_rights,
                              as_of=NOW, document_observation=read,
                              max_age=timedelta(days=7))


def coverage_receipt(**changes):
    # Source-owner receipt fixture only; no real SEC fetch or installed GMI
    # registry is inferred from this test.
    fields = dict(
        source="edgar_8k_202",
        receipt_id="test-only-complete-edgar-window",
        owner_ref="test-source-owner",
        snapshot_version="test-snapshot-001",
        issuer_tickers=frozenset({"PFE", "TST", "OTH"}),
        window_start_utc=NOW - timedelta(days=7),
        window_end_utc=NOW,
        checked_at_utc=NOW,
        outcome="COMPLETE",
        pagination_exhausted=True,
        truncated=False,
        returned_events=1,
        event_limit=20,
    )
    fields.update(changes)
    return SourceCoverageReceipt(**fields)


def test_one_to_ten_tickers_and_hostile_input_rejected_not_silently_cleaned():
    assert normalize_tickers(["pfe", " tst "]) == ["PFE", "TST"]
    for bad in ([], ["PFE"] * 11, ["PFE", "pfe"], ["../SECRET"],
                ["PFE/../../"], "PFE", [123], ["BAD URL"]):
        with pytest.raises(ValueError):
            normalize_tickers(bad)


def test_supported_direct_unsupported_and_unknown_relationship_are_distinct():
    p = packet()
    result = scan(["PFE", "OUT", "OTH"], p)
    statuses = [x["status"] for x in result["results"]]
    assert statuses == ["SUPPORTED", "NOT_COVERED", "NOT_COVERED"]
    assert result["schema"] == "catalyst.scan/v1" and result["schema_version"] == 1
    direct = result["results"][0]
    assert direct["relationship"] == "DIRECT"
    assert direct["dossier_path"] == "/stocks/PFE/"
    assert len(direct["sources"]) == 1
    assert direct["sources"][0]["url"].startswith("https://www.sec.gov/")
    assert direct["as_of_utc"] == "2026-08-05T12:00:00Z"
    assert result["results"][1]["what_changed"] == []
    assert result["results"][2]["relationship"] == "UNKNOWN"
    assert "PRIVATE BODY" not in str(result)


def test_qualified_indirect_exposure_survives_but_not_unproved_co_mention():
    src = {"source_id": "rel_src_1", "title": "Fictional test company supplier disclosure",
           "url": "https://example.com/fictional",
           "published_at_utc": "2026-08-04T13:50:00Z", "evidence_ids": ["supplier_doc_1"]}
    rel = {"ticker": "TST", "issuer_id": "cik:0000123456",
           "primary_issuer_id": "cik:0000078003", "relationship": "EVIDENCED_INDIRECT",
           "relation_type": "supplier", "source_id": "rel_src_1", "evidence_id": "supplier_doc_1",
           "source_anchor": "file:v1#para2"}
    p = build_event_packet(RAW, issuers=UNIVERSE, rights_resolver=resolver,
                           as_of=NOW, source_refs=[src], relationships=[rel])
    found = scan(["TST"], p)["results"][0]
    assert found["status"] == "SUPPORTED"
    assert found["relationship"] == "EVIDENCED_INDIRECT"
    assert "Documented supplier" in found["what_changed"][0]["text"]
    assert {x["source_id"] for x in found["sources"]} == {PRIMARY, "rel_src_1"}
    with_bad_id = build_event_packet(RAW, issuers=UNIVERSE, rights_resolver=resolver,
                 as_of=NOW, source_refs=[src], relationships=[{**rel, "evidence_id": "made_up"}])
    assert scan(["TST"], with_bad_id)["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"


def test_private_secondary_does_not_leak_through_unsupported_relationship():
    src = {"source_id": "paid_src_2", "title": "PRIVATE PREMIUM TITLE",
           "url": "https://private.example.com/secret", "evidence_ids": ["hidden_rel"]}
    rel = {"ticker": "TST", "issuer_id": "cik:0000123456",
           "primary_issuer_id": "cik:0000078003", "relationship": "EVIDENCED_INDIRECT",
           "relation_type": "supplier", "source_id": "paid_src_2", "evidence_id": "hidden_rel",
           "source_anchor": "private"}
    def only_sec(sid, now):
        return resolver(sid, now) if sid == PRIMARY else None
    p = build_event_packet(RAW, issuers=UNIVERSE, rights_resolver=only_sec,
                           as_of=NOW, source_refs=[src], relationships=[rel])
    result = scan(["PFE", "TST"], p)
    assert [x["status"] for x in result["results"]] == ["SUPPORTED", "RIGHTS_BLOCKED"]
    assert "PRIVATE PREMIUM TITLE" not in str(result)
    assert "private.example.com" not in str(result)


def test_denied_primary_rights_never_fall_back_to_private_news():
    def no_grant(sid, now):
        return None
    p = build_event_packet(RAW, issuers=UNIVERSE, rights_resolver=no_grant, as_of=NOW)
    r = scan(["PFE"], p)["results"][0]
    assert r["status"] == "RIGHTS_BLOCKED"
    assert r["sources"] == r["what_changed"] == []


def test_latest_correction_wins_and_retraction_overrides_older_public_packet():
    old = packet()
    corrected = packet(eps_actual=-0.03, correction_generation=1,
                       revision_status="corrected", supersedes_generation=0,
                       correction_reason="official_amendment")
    assert scan(["PFE"], old, corrected)["generation"] == 1
    assert scan(["PFE"], old, corrected)["results"][0]["correction_state"] == "CORRECTED"
    withdrawn = packet(correction_generation=2, revision_status="retracted",
                       supersedes_generation=1, correction_reason="source_retraction")
    r = scan(["PFE"], old, corrected, withdrawn)["results"][0]
    assert r["status"] == "TEMPORARILY_UNAVAILABLE"
    assert r["sources"] == []
    assert r["what_changed"] == []


def test_duplicate_story_is_deduped_and_same_generation_conflict_quarantined():
    p = packet()
    assert scan(["PFE"], p, deepcopy(p))["results"][0]["status"] == "SUPPORTED"
    conflicted = deepcopy(p)
    conflicted["what_changed"][0]["text"] = "MALICIOUS FALSE PUBLIC COPY 777"
    result = scan(["PFE"], p, conflicted)["results"][0]
    assert result["status"] == "TEMPORARILY_UNAVAILABLE"
    assert result["what_changed"] == []
    assert "777" not in str(result)


def test_expired_packet_and_unknown_event_reference_do_not_reuse_stale_data():
    p = packet()
    assert scan(["PFE"], p, as_of=NOW + timedelta(hours=1))["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    assert scan(["PFE"], p, event_id="not-this-event")["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"


def test_invalid_dossier_path_is_never_constructed_from_user_input():
    u = deepcopy(UNIVERSE)
    u["PFE"]["dossier_path"] = "https://evil.example?token=x"
    p = packet()
    result = compose_scan(["PFE"], packets=[p], issuers=u, as_of=NOW)
    assert result["results"][0]["dossier_path"] is None


def test_default_entrypoint_is_read_only_and_fails_closed(monkeypatch):
    from engine.marketing import catalyst_scan as module
    result = module.scan_tickers(["PFE"], now_utc=NOW)
    assert result["publication_state"] == "UNAVAILABLE"
    assert result["results"][0]["status"] == "NOT_COVERED"
    # A legacy two-part read cannot certify source completeness or corrections.
    monkeypatch.setattr(module, "read_qualified_event_context", lambda now: ([packet()], UNIVERSE))
    legacy = module.scan_tickers(["PFE", "OUT"], now_utc=NOW)
    assert legacy["publication_state"] == "UNAVAILABLE"
    assert all(not r["sources"] and not r["what_changed"] for r in legacy["results"])
    monkeypatch.setattr(module, "read_qualified_event_context",
                        lambda now: ([packet()], UNIVERSE, coverage_receipt()))
    # Even a complete window cannot upgrade a legacy event whose only source
    # clock is the producer's processing wall-clock.
    unverified = module.scan_tickers(["PFE", "OUT"], now_utc=NOW)
    assert unverified["publication_state"] == "UNAVAILABLE"
    monkeypatch.setattr(module, "read_qualified_event_context",
                        lambda now: ([verified_packet()], UNIVERSE, coverage_receipt()))
    answer = module.scan_tickers(["PFE", "OUT"], now_utc=NOW)
    assert answer["results"][0]["status"] == "SUPPORTED"
    assert answer["results"][1]["status"] == "NOT_COVERED"
    assert answer["publication_state"] == "PARTIAL"


def test_scan_input_enforces_session_00_public_symbol_syntax():
    for candidate in ("12345", "A" * 11, "BRK..B", "TOO_LONG_TICKER"):
        with pytest.raises(ValueError):
            normalize_tickers([candidate])
    assert normalize_tickers(["brk.b", "AAPL"]) == ["BRK.B", "AAPL"]


def test_stage_a_observed_first_availability_and_nullable_publication_survive_scan():
    from dataclasses import replace
    from engine.marketing.catalyst_packets import VerifiedDocumentObservation
    doc_read = VerifiedDocumentObservation(
        source_id=PRIMARY, document_url=RAW["source_url"],
        document_sha256="a" * 64,
        receipt_id="test-only-successful-retained-document-read",
        owner_ref="test-incumbent-edgar-owner",
        first_verified_at_utc="2026-08-04T11:03:10Z",
        checked_at_utc=NOW,
        source_snapshot_version="test-snapshot-001",
        official_published_at_utc=None,
    )
    def version_rights(sid, now):
        return replace(resolver(sid, now), document_sha256="a" * 64)
    raw = dict(RAW)
    raw.pop("publication_time_utc")
    p = build_event_packet(raw, issuers=UNIVERSE, rights_resolver=version_rights,
                           as_of=NOW, document_observation=doc_read,
                           max_age=timedelta(days=7))
    result = compose_scan(["PFE", "OUT"], packets=[p], issuers=UNIVERSE,
                          as_of=NOW, coverage=coverage_receipt())
    assert [r["status"] for r in result["results"]] == ["SUPPORTED", "NOT_COVERED"]
    assert result["publication_state"] == "PARTIAL"
    source = result["results"][0]["sources"][0]
    assert source["published_at_utc"] is None
    assert source["first_verified_at_utc"] == "2026-08-04T11:03:10Z"
    assert source["rights_receipt_id"].startswith("fixture-receipt:")
    assert result["results"][0]["what_changed"]
    assert result["checked_window"]["kind"] == "earnings_8k"


def test_trusted_complete_empty_is_distinct_from_bare_empty_or_unknown_event_id():
    complete = coverage_receipt(returned_events=0)
    result = compose_scan(["PFE", "OUT"], packets=[], issuers=UNIVERSE,
                          as_of=NOW, coverage=complete)
    assert result["publication_state"] == "COMPLETE_EMPTY"
    assert [r["status"] for r in result["results"]] == [
        "NO_QUALIFIED_EVENT", "NOT_COVERED"]
    assert all(not r["sources"] and not r["what_changed"]
               for r in result["results"])
    assert result["event_id"] is None and result["generation"] is None
    assert result["checked_window"]["end_utc"] == "2026-08-05T12:00:00Z"

    missing = compose_scan(["PFE", "OUT"], packets=[], issuers=UNIVERSE,
                           as_of=NOW)
    assert missing["publication_state"] == "UNAVAILABLE"
    assert missing["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    specified = compose_scan(["PFE"], packets=[], issuers=UNIVERSE, as_of=NOW,
                             coverage=complete, event_id="unknown-id")
    assert specified["publication_state"] == "UNAVAILABLE"
    assert specified["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"


@pytest.mark.parametrize("mutation", [
    {"outcome": "FAILED"},
    {"outcome": "PARTIAL"},
    {"truncated": True},
    {"pagination_exhausted": False},
    {"checked_at_utc": NOW - timedelta(minutes=11)},
    {"window_end_utc": NOW - timedelta(minutes=11)},
    {"window_start_utc": NOW - timedelta(days=6)},
    {"issuer_tickers": frozenset({"TST"})},
    {"issuer_tickers": frozenset({"PFE", "TST", "OTH", "FAKE"})},
    {"returned_events": 20},
    {"event_limit": 0},
    {"source": "private_benzinga"},
    {"snapshot_version": ""},
    {"receipt_id": ""},
])
def test_failed_partial_truncated_stale_or_unbound_coverage_cannot_claim_empty(mutation):
    receipt = coverage_receipt(returned_events=0, **mutation) if (
        "returned_events" not in mutation) else coverage_receipt(**mutation)
    answer = compose_scan(["PFE", "OUT"], packets=[], issuers=UNIVERSE,
                          coverage=receipt, as_of=NOW)
    assert answer["publication_state"] == "UNAVAILABLE"
    assert answer["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    assert answer["results"][1]["status"] == "NOT_COVERED"
    assert all(not r["sources"] and not r["what_changed"]
               for r in answer["results"])


def test_source_read_requires_three_part_owner_result_and_current_receipt(monkeypatch):
    from engine.marketing import catalyst_scan as module
    monkeypatch.setattr(module, "read_qualified_event_context",
                        lambda now: ([], UNIVERSE))
    legacy = module.scan_tickers(["PFE"], now_utc=NOW)
    assert legacy["publication_state"] == "UNAVAILABLE"
    monkeypatch.setattr(module, "read_qualified_event_context",
                        lambda now: ([], UNIVERSE, coverage_receipt(
                            returned_events=0, truncated=True)))
    truncated = module.scan_tickers(["PFE"], now_utc=NOW)
    assert truncated["publication_state"] == "UNAVAILABLE"
    monkeypatch.setattr(module, "read_qualified_event_context",
                        lambda now: ([], UNIVERSE, coverage_receipt(
                            returned_events=0)))
    empty = module.scan_tickers(["PFE"], now_utc=NOW)
    assert empty["publication_state"] == "COMPLETE_EMPTY"
    assert empty["results"][0]["status"] == "NO_QUALIFIED_EVENT"


def test_stage_a_scan_v2_is_explicit_and_not_a_silent_v1_extension():
    observed = verified_packet()
    v2 = compose_scan(["PFE", "OUT"], packets=[observed],
                      issuers=UNIVERSE, as_of=NOW,
                      coverage=coverage_receipt())
    assert (observed["schema"], observed["schema_version"]) == (
        "catalyst.public_event/v2", 2)
    assert (v2["schema"], v2["schema_version"]) == ("catalyst.scan/v2", 2)
    old = compose_scan(["PFE", "OUT"], packets=[packet()],
                       issuers=UNIVERSE, as_of=NOW)
    assert (old["schema"], old["schema_version"]) == ("catalyst.scan/v1", 1)
    complete = compose_scan(["PFE"], packets=[], issuers=UNIVERSE,
                            as_of=NOW, coverage=coverage_receipt(returned_events=0))
    assert complete["schema"] == "catalyst.scan/v2"
    assert complete["publication_state"] == "COMPLETE_EMPTY"


def test_stage_a_complete_receipt_cannot_admit_indirect_link_or_legacy_packet():
    direct = verified_packet()
    indirect = deepcopy(direct)
    indirect["affected_tickers"].append({
        "ticker": "TST", "relationship": "EVIDENCED_INDIRECT",
        "relation_evidence_ids": ["test_doc_relation"]})
    for candidate in (indirect, packet()):
        result = compose_scan(["PFE"], packets=[candidate],
                              issuers=UNIVERSE, as_of=NOW,
                              coverage=coverage_receipt())
        assert result["publication_state"] == "UNAVAILABLE"
        assert result["results"][0]["sources"] == []


def test_twenty_event_truncation_cannot_claim_complete_current_issuer_coverage():
    rows = [verified_packet()] * 20
    incomplete = coverage_receipt(returned_events=20, truncated=True)
    result = compose_scan(["PFE"], packets=rows, issuers=UNIVERSE,
                          as_of=NOW, coverage=incomplete)
    assert result["publication_state"] == "UNAVAILABLE"
    assert result["results"][0]["what_changed"] == []


def test_stage_a_current_window_cannot_certify_old_snapshot_or_uncovered_issuer():
    from dataclasses import replace
    row = verified_packet()
    wrong_snapshot = replace(coverage_receipt(), snapshot_version="new-source-generation")
    rejected = compose_scan(["PFE"], packets=[row], issuers=UNIVERSE,
                            as_of=NOW, coverage=wrong_snapshot)
    assert rejected["publication_state"] == "UNAVAILABLE"
    assert rejected["results"][0]["what_changed"] == []
    wrong_scope = replace(coverage_receipt(), issuer_tickers=frozenset({"TST", "OTH"}))
    rejected = compose_scan(["TST"], packets=[row], issuers=UNIVERSE,
                            as_of=NOW, coverage=wrong_scope)
    assert rejected["publication_state"] == "UNAVAILABLE"
    assert rejected["results"][0]["sources"] == []


def test_v2_packet_never_publishes_without_complete_current_source_coverage():
    new = verified_packet()
    unsafe = compose_scan(["PFE"], packets=[new],
                          issuers=UNIVERSE, as_of=NOW)
    assert unsafe["publication_state"] == "UNAVAILABLE"
    assert unsafe["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    assert unsafe["results"][0]["sources"] == unsafe["results"][0]["what_changed"] == []
    # A legacy packet cannot hide a new event lacking completeness.
    mixed = compose_scan(["PFE"], packets=[packet(), new],
                         issuers=UNIVERSE, as_of=NOW)
    assert mixed["publication_state"] == "UNAVAILABLE"
    assert mixed["results"][0]["sources"] == []
    good = compose_scan(["PFE"], packets=[new],
                        issuers=UNIVERSE, as_of=NOW,
                        coverage=coverage_receipt())
    assert good["results"][0]["status"] == "SUPPORTED"
    assert good["schema"] == "catalyst.scan/v2"


def test_stage_a_event_freshness_expires_at_seven_day_acceptance_boundary():
    from dataclasses import replace
    from engine.marketing.catalyst_packets import VerifiedDocumentObservation
    accepted = datetime(2026, 8, 4, 11, 2, 43, tzinfo=UTC)
    built_at = accepted + timedelta(days=7) - timedelta(minutes=2)
    overdue = accepted + timedelta(days=7) + timedelta(seconds=1)
    retained = VerifiedDocumentObservation(
        source_id=PRIMARY, document_url=RAW["source_url"],
        document_sha256="a" * 64,
        receipt_id="test-successful-filing-observation",
        owner_ref="test-incumbent-source",
        first_verified_at_utc="2026-08-04T11:03:10Z",
        checked_at_utc=built_at,
        source_snapshot_version="test-snapshot-001",
        official_published_at_utc=None,
    )
    raw = dict(RAW)
    raw.pop("publication_time_utc")
    def extended_rights(sid, when):
        return replace(resolver(sid,when),document_sha256="a" * 64,
                       expires_at_utc=overdue + timedelta(days=1))
    p = build_event_packet(raw, issuers=UNIVERSE, rights_resolver=extended_rights,
                           as_of=built_at, document_observation=retained)
    assert p["public_disposition"] == "PUBLIC_READY"
    eligible = replace(coverage_receipt(),
                       window_start_utc=built_at - timedelta(days=7),
                       window_end_utc=built_at, checked_at_utc=built_at)
    after = compose_scan(["PFE"],packets=[p],issuers=UNIVERSE,
                         as_of=overdue,coverage=eligible)
    assert after["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    assert not after["results"][0]["what_changed"]


@pytest.mark.parametrize("window_end_offset,checked_offset", [
    (timedelta(minutes=1), timedelta(0)),
    (timedelta(seconds=1), timedelta(0)),
    (timedelta(0), timedelta(seconds=1)),
])
def test_future_or_unchecked_source_window_cannot_certify_no_event(
    window_end_offset, checked_offset,
):
    from dataclasses import replace
    receipt = replace(
        coverage_receipt(returned_events=0),
        window_end_utc=NOW + window_end_offset,
        checked_at_utc=NOW + checked_offset,
    )
    result = compose_scan(["PFE"], packets=[], issuers=UNIVERSE,
                          as_of=NOW, coverage=receipt)
    assert result["publication_state"] == "UNAVAILABLE"
    assert result["results"][0]["status"] == "TEMPORARILY_UNAVAILABLE"
    assert not result["results"][0]["what_changed"]


def test_event_accepted_after_checked_window_cannot_be_certified():
    from dataclasses import replace
    versioned = deepcopy(verified_packet())
    new_accept = NOW - timedelta(seconds=30)
    first_verified = NOW - timedelta(seconds=20)
    versioned["event_time_utc"] = new_accept.isoformat().replace("+00:00", "Z")
    versioned["first_observed_at_utc"] = first_verified.isoformat().replace("+00:00", "Z")
    window = replace(coverage_receipt(), window_end_utc=NOW-timedelta(seconds=60))
    result = compose_scan(["PFE"], packets=[versioned], issuers=UNIVERSE,
                          as_of=NOW, coverage=window)
    assert result["publication_state"] == "UNAVAILABLE"
    assert result["results"][0]["sources"] == []
