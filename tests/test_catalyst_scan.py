"""Anonymous scan composition negative, dedup, correction, entitlement tests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.marketing.catalyst_packets import PublicSourceGrant, build_event_packet
from engine.marketing.catalyst_scan import compose_scan, normalize_tickers

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
    monkeypatch.setattr(module, "read_qualified_event_context", lambda now: ([packet()], UNIVERSE))
    answer = module.scan_tickers(["PFE", "OUT"], now_utc=NOW)
    assert answer["results"][0]["status"] == "SUPPORTED"
    assert answer["results"][1]["status"] == "NOT_COVERED"
    assert answer["publication_state"] == "PARTIAL"


def test_scan_input_enforces_session_00_public_symbol_syntax():
    for candidate in ("12345", "A" * 11, "BRK..B", "TOO_LONG_TICKER"):
        with pytest.raises(ValueError):
            normalize_tickers([candidate])
    assert normalize_tickers(["brk.b", "AAPL"]) == ["BRK.B", "AAPL"]
