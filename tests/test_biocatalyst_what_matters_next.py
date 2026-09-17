from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from engine.biocatalyst.company_event_adapter import resolve_current_event_identity
from engine.biocatalyst.what_matters_next import compose_company_event_rows
from engine.company_intelligence.events import project_catalyst_event
from engine.company_intelligence.identity import company_id_for_cik
from lib.dataos.identity import IssuerMaster, VendorAliasTable

CIK = "0001365916"
COMPANY = company_id_for_cik(CIK)
CUTOFF = "2026-09-06T12:00:00Z"
ANCHOR = "2026-09-06"
ROW_KEYS = {
    "row_key", "event_fact_ref", "event_family", "event_revision_ref",
    "revision_is_current", "occurrence", "timing", "issuer", "assets",
    "relationships", "economic_exposure_state", "evidence", "revision_summary",
    "research_priority", "probability", "materiality", "historical_response",
    "incorporation", "missingness", "links",
}


def _timing(lower="2026-09-07", upper="2026-09-07"):
    return {
        "state": "consistent", "source_class": "issuer_guided",
        "lower_date": lower, "upper_date": upper, "precision": "day",
        "source_timezone": None, "source_wording": "expects data",
        "evidence_refs": ["ev_public_1"],
    }


def _event(**overrides):
    args = dict(
        company_id=COMPANY, issuer_cik=CIK, source_namespace="issuer_disclosure",
        native_event_key="doc_2026_08_18#claim/readout", event_family="issuer_readout_guidance",
        revision_ref="doc_2026_08_18:r1", revision_is_current=True,
        occurrence="uncorroborated", timing=_timing(),
        source_available_at="2026-08-18T11:30:00-04:00",
        observed_at="2026-08-18T15:31:00Z", document_refs=["doc_2026_08_18:r1"],
        public_evidence=[], asset_mentions=[], relationship_claims=[], generation_cutoff=CUTOFF,
    )
    args.update(overrides)
    return project_catalyst_event(**args)


def _security(sec, issuer, symbol, cik=CIK):
    listing = sec.removeprefix("SEC:")
    return {
        "security_id": sec, "issuer_id": issuer, "issuer_state": "RESOLVED",
        "issuer_cik": cik, "listing_key": listing, "security_state": None,
        "superseded_by": None,
    }, {
        "vendor": "store", "vendor_symbol": symbol, "security_id": sec,
        "valid_from": None, "valid_to": None,
    }


def _identity(event, security_rows=(), alias_rows=()):
    return resolve_current_event_identity(
        event, issuer_master=IssuerMaster.from_records(list(security_rows)),
        alias_table=VendorAliasTable.from_records(list(alias_rows)),
        identity_cut_date=date(2026, 9, 6), identity_observed_at="2026-09-06T10:00:00Z",
        generation_cutoff=CUTOFF,
    )


def _rows(event, identity, source_health="current"):
    return compose_company_event_rows(
        event, identity_projection=identity, source_health=source_health,
        evaluation_cutoff=CUTOFF, anchor_date=ANCHOR,
    )


def test_resolved_disclosure_composes_closed_row_and_stock_research_link() -> None:
    event = _event()
    sr, ar = _security("SEC:US-XNAS-AMLX", "ISS:US-XNAS-AMLX", "AMLX")
    row = _rows(event, _identity(event, [sr], [ar]))[0]
    assert set(row) == ROW_KEYS
    assert row["row_key"] == {"event_fact_ref": event["event_id"], "issuer_id": "ISS:US-XNAS-AMLX"}
    assert row["issuer"] == {
        "state": "resolved", "issuer_id": "ISS:US-XNAS-AMLX", "company_id": COMPANY,
        "relationship_role": "issuer", "identity_scope": "current_only",
        "identity_observed_at": "2026-09-06T10:00:00Z",
        "securities": [{
            "security_id": "SEC:US-XNAS-AMLX", "listing_key": "US-XNAS-AMLX",
            "display_symbol": "AMLX", "symbol_observed_on": "2026-09-06", "state": "active",
        }],
    }
    assert row["links"]["stock_research"] == [{
        "security_id": "SEC:US-XNAS-AMLX", "relationship_role": "issuer",
        "href": "stock.html?ticker=AMLX",
    }]
    assert row["research_priority"]["lane"] == "ACT_NOW"


def test_two_share_classes_survive_without_preferred_security() -> None:
    event = _event()
    s1, a1 = _security("SEC:US-XNAS-SYNA", "ISS:US-XNAS-SYNA", "SYN.A")
    s2, a2 = _security("SEC:US-XNAS-SYNB", "ISS:US-XNAS-SYNA", "SYN B")
    row = _rows(event, _identity(event, [s1, s2], [a1, a2]))[0]
    assert [x["security_id"] for x in row["issuer"]["securities"]] == ["SEC:US-XNAS-SYNA", "SEC:US-XNAS-SYNB"]
    assert [x["href"] for x in row["links"]["stock_research"]] == [
        "stock.html?ticker=SYN.A", "stock.html?ticker=SYN%20B"
    ]
    assert "preferred_security_id" not in row["issuer"]


def test_unresolved_identity_stays_visible_without_stock_link() -> None:
    event = _event()
    row = _rows(event, _identity(event))[0]
    assert row["row_key"]["issuer_id"] is None
    assert row["issuer"] == {
        "state": "unresolved", "issuer_id": None, "company_id": COMPANY,
        "relationship_role": None, "identity_scope": "unavailable",
        "identity_observed_at": "2026-09-06T10:00:00Z", "securities": [],
    }
    assert row["links"]["stock_research"] == []
    assert row["research_priority"]["lane"] == "RECONCILE"
    assert row["research_priority"]["primary_reason"] == "IDENTITY_UNRESOLVED"
    assert row["missingness"]["identity"] == ["CURRENT_ISSUER_UNRESOLVED"]


def test_ambiguous_current_cik_admits_no_issuer_or_stock_link() -> None:
    event = _event()
    a, _ = _security("SEC:US-XNAS-A", "ISS:US-XNAS-A", "A")
    b, _ = _security("SEC:US-XNYS-B", "ISS:US-XNYS-B", "B")
    row = _rows(event, _identity(event, [a, b], []))[0]
    assert row["issuer"]["state"] == "ambiguous"
    assert row["issuer"]["issuer_id"] is None
    assert row["issuer"]["securities"] == []
    assert row["links"]["stock_research"] == []
    assert row["missingness"]["identity"] == ["AMBIGUOUS_CURRENT_CIK"]
    assert "IDENTITY_UNRESOLVED" in row["research_priority"]["gap_reasons"]


def test_first_slice_is_honest_about_missing_assets_economics_and_estimates() -> None:
    event = _event()
    row = _rows(event, _identity(event))[0]
    assert row["assets"] == [] and row["relationships"] == []
    assert row["economic_exposure_state"] == "unresolved"
    assert row["evidence"] == []
    for name in ("probability", "materiality", "historical_response", "incorporation"):
        slot = row[name]
        assert set(slot) == {"state", "value", "reason_code", "method_ref", "as_of", "evidence_refs"}
        assert slot["state"] == "NOT_ESTIMABLE" and slot["value"] is None
        assert slot["reason_code"]
    assert row["missingness"]["asset"] == ["ASSET_PORT_NOT_ADMITTED"]
    assert row["missingness"]["economic"] == ["ECONOMIC_EXPOSURE_UNRESOLVED"]


def test_correction_keeps_row_identity_but_changes_revision_and_priority() -> None:
    before = _event()
    after = _event(
        revision_ref="doc_2026_09_01:r2", timing=_timing("2026-12-05", "2026-12-05"),
        source_available_at="2026-09-01T08:00:00-04:00", observed_at="2026-09-01T12:02:00Z",
    )
    assert before["event_id"] == after["event_id"]
    before_row = _rows(before, _identity(before))[0]
    after_row = _rows(after, _identity(after))[0]
    assert before_row["row_key"] == after_row["row_key"]
    assert before_row["event_revision_ref"] != after_row["event_revision_ref"]
    assert before_row["research_priority"]["lane"] == "RECONCILE"  # identity gap outranks timing
    assert after_row["research_priority"]["lane"] == "RECONCILE"
    # With a resolved issuer, timing correction moves ACT_NOW -> MONITOR.
    sr, ar = _security("SEC:US-XNAS-AMLX", "ISS:US-XNAS-AMLX", "AMLX")
    assert _rows(before, _identity(before, [sr], [ar]))[0]["research_priority"]["lane"] == "ACT_NOW"
    assert _rows(after, _identity(after, [sr], [ar]))[0]["research_priority"]["lane"] == "MONITOR"


def test_stale_source_and_superseded_revision_preserve_policy_semantics() -> None:
    event = _event()
    stale = _rows(event, _identity(event), source_health="stale")[0]
    assert stale["research_priority"]["lane"] == "RECONCILE"
    assert stale["research_priority"]["primary_reason"] == "SOURCE_NOT_CURRENT"
    superseded = _event(revision_is_current=False)
    row = _rows(superseded, _identity(superseded))[0]
    assert row["research_priority"]["disposition"] == "EXCLUDE_SUPERSEDED"
