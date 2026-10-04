from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from engine.biocatalyst.company_event_adapter import resolve_current_event_identity
from engine.biocatalyst.what_matters_next import compose_company_event_rows
from engine.company_intelligence.events import project_catalyst_event
from engine.company_intelligence.contracts import ContractError, canonical_json_sha256
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

from engine.biocatalyst.what_matters_next import select_what_matters_next_rows


def _resolved_identity(event, symbol="AMLX"):
    sr, ar = _security(f"SEC:US-XNAS-{symbol.replace('.', '')}", f"ISS:US-XNAS-{symbol.replace('.', '')}", symbol)
    return _identity(event, [sr], [ar])


def test_upcoming_view_uses_requested_horizon_and_excludes_reconcile_and_history() -> None:
    near = _event(native_event_key="doc#near", timing=_timing("2026-09-07", "2026-09-07"))
    later = _event(native_event_key="doc#later", timing=_timing("2026-12-05", "2026-12-05"))
    unresolved = _event(native_event_key="doc#unresolved", timing=_timing("2026-09-08", "2026-09-08"))
    history = _event(native_event_key="doc#history", occurrence="corroborated", timing=_timing("2026-09-07", "2026-09-07"))
    rows = [
        _rows(near, _resolved_identity(near))[0],
        _rows(later, _resolved_identity(later))[0],
        _rows(unresolved, _identity(unresolved))[0],
        _rows(history, _resolved_identity(history))[0],
    ]
    seven = select_what_matters_next_rows(rows, view="upcoming", horizon_days=7, q=None, event_family=None, lane=None, anchor_date=ANCHOR)
    assert [r["event_fact_ref"] for r in seven] == [near["event_id"]]
    year = select_what_matters_next_rows(rows, view="upcoming", horizon_days=365, q=None, event_family=None, lane=None, anchor_date=ANCHOR)
    assert {r["event_fact_ref"] for r in year} == {near["event_id"], later["event_id"]}


def test_reconcile_view_retains_unresolved_and_conflicted_without_horizon() -> None:
    unresolved = _event(native_event_key="doc#unresolved")
    conflicted = _event(
        native_event_key="doc#conflicted",
        timing={**_timing(), "state": "conflicted", "lower_date": None, "upper_date": None},
    )
    rows = [
        _rows(unresolved, _identity(unresolved))[0],
        _rows(conflicted, _resolved_identity(conflicted))[0],
    ]
    selected = select_what_matters_next_rows(rows, view="reconcile", horizon_days=None, q=None, event_family=None, lane=None, anchor_date=ANCHOR)
    assert {r["event_fact_ref"] for r in selected} == {unresolved["event_id"], conflicted["event_id"]}
    assert all(r["research_priority"]["lane"] == "RECONCILE" for r in selected)


def test_history_view_is_explicit_and_superseded_rows_never_surface() -> None:
    history = _event(native_event_key="doc#history", occurrence="withdrawn")
    superseded = _event(native_event_key="doc#old", revision_is_current=False)
    rows = [
        _rows(history, _resolved_identity(history))[0],
        _rows(superseded, _resolved_identity(superseded))[0],
    ]
    selected = select_what_matters_next_rows(rows, view="history", horizon_days=None, q=None, event_family=None, lane=None, anchor_date=ANCHOR)
    assert [r["event_fact_ref"] for r in selected] == [history["event_id"]]


def test_wmn_filters_are_exact_and_search_is_casefolded_over_public_fields() -> None:
    event = _event(native_event_key="doc#search")
    row = _rows(event, _resolved_identity(event, "AMLX"))[0]
    assert select_what_matters_next_rows([row], view="upcoming", horizon_days=90, q="amlx", event_family="issuer_readout_guidance", lane="ACT_NOW", anchor_date=ANCHOR) == [row]
    assert select_what_matters_next_rows([row], view="upcoming", horizon_days=90, q="nope", event_family=None, lane=None, anchor_date=ANCHOR) == []
    with pytest.raises(ValueError):
        select_what_matters_next_rows([row], view="bogus", horizon_days=90, q=None, event_family=None, lane=None, anchor_date=ANCHOR)
    with pytest.raises(ValueError):
        select_what_matters_next_rows([row], view="reconcile", horizon_days=90, q=None, event_family=None, lane=None, anchor_date=ANCHOR)

from engine.biocatalyst.what_matters_next import compose_rows_from_wmn_inputs, validate_wmn_inputs


def _wmn_inputs(event, identity, *, cutoff=CUTOFF):
    return {
        "contract_id": "biocatalyst_wmn_inputs.v1",
        "schema_version": "1.0.0",
        "input_cut": {
            "cutoff": cutoff,
            "members": [
                {
                    "contract_id": "company_catalyst_event.v1",
                    "ref": event["event_id"],
                    "sha256": canonical_json_sha256(event),
                    "observed_at": event["observed_at"],
                    "accepted_at": event["observed_at"],
                    "availability": "available",
                },
                {
                    "contract_id": "dataos_issuer_master.current",
                    "ref": "issuer-master-cut-2026-09-06",
                    "sha256": "2" * 64,
                    "observed_at": "2026-09-06T10:00:00Z",
                    "accepted_at": "2026-09-06T10:00:00Z",
                    "availability": "available",
                },
            ],
        },
        "events": [event],
        "relationships": [],
        "identity_projection": {event["event_id"]: identity},
        "coverage": {
            "declared_universe_ref": "bio:first-company-event-slice",
            "source_health": "current",
            "family_states": {
                "issuer_readout_guidance": {
                    "declared_scope": "issuer_disclosure:first_slice",
                    "observed_count": 1,
                    "state": "partial",
                },
                "registry_primary_completion": {
                    "declared_scope": "not_in_first_company_event_slice",
                    "observed_count": None,
                    "state": "not_built",
                },
            },
            "missing_owner_ports": [
                "asset_relationships", "economic_exposure", "probability",
                "materiality", "historical_response", "incorporation",
            ],
        },
        "authority": event["authority"],
    }


def test_wmn_inputs_are_closed_cut_bound_and_compose_rows_without_live_owner_reads() -> None:
    event = _event()
    inputs = _wmn_inputs(event, _resolved_identity(event))
    normalized = validate_wmn_inputs(inputs)
    assert normalized["contract_id"] == "biocatalyst_wmn_inputs.v1"
    rows = compose_rows_from_wmn_inputs(normalized, evaluation_cutoff=CUTOFF, anchor_date=ANCHOR)
    assert len(rows) == 1
    assert rows[0]["event_fact_ref"] == event["event_id"]
    assert rows[0]["issuer"]["state"] == "resolved"


def test_wmn_inputs_refuse_future_cut_members_and_future_generation_self_reference() -> None:
    event = _event()
    inputs = _wmn_inputs(event, _identity(event))
    inputs["input_cut"]["members"][0]["observed_at"] = "2026-09-06T12:00:01Z"
    with pytest.raises(ContractError, match="input_cut"):
        validate_wmn_inputs(inputs)

    inputs = _wmn_inputs(event, _identity(event))
    inputs["input_cut"]["members"][0]["ref"] = "ctgov_run_future_output_123"
    with pytest.raises(ContractError, match="future generation"):
        validate_wmn_inputs(inputs, forbidden_generation_id="ctgov_run_future_output_123")


def test_wmn_inputs_require_exact_event_identity_bindings_and_no_unowned_relationship_blob() -> None:
    event = _event()
    inputs = _wmn_inputs(event, _identity(event))
    inputs["identity_projection"] = {}
    with pytest.raises(ContractError, match="identity_projection"):
        validate_wmn_inputs(inputs)

    inputs = _wmn_inputs(event, _identity(event))
    inputs["relationships"] = [{"kind": "owner", "guessed": True}]
    with pytest.raises(ContractError, match="relationships"):
        validate_wmn_inputs(inputs)


def test_wmn_inputs_family_states_and_authority_are_closed() -> None:
    event = _event()
    inputs = _wmn_inputs(event, _identity(event))
    inputs["coverage"]["family_states"]["issuer_readout_guidance"]["state"] = "magical"
    with pytest.raises(ContractError, match="family_states"):
        validate_wmn_inputs(inputs)

    inputs = _wmn_inputs(event, _identity(event))
    inputs["authority"]["decision_authority"] = True
    with pytest.raises(ContractError, match="authority"):
        validate_wmn_inputs(inputs)


def test_wmn_inputs_bind_embedded_company_event_to_cut_hash() -> None:
    event = _event()
    inputs = _wmn_inputs(event, _identity(event))
    inputs["input_cut"]["members"][0]["sha256"] = "f" * 64
    with pytest.raises(ContractError, match="event hash mismatch"):
        validate_wmn_inputs(inputs)

from engine.biocatalyst.what_matters_next import (
    build_what_matters_next,
    normalize_wmn_query,
    wmn_row_cursor_key,
)


def test_wmn_read_model_counts_global_universe_before_view_and_partial_outranks_stale() -> None:
    near = _event(native_event_key="doc#near-model")
    unresolved = _event(native_event_key="doc#unresolved-model", timing=_timing("2026-10-01", "2026-10-01"))
    inputs = _wmn_inputs(near, _resolved_identity(near))
    inputs["events"].append(unresolved)
    inputs["identity_projection"][unresolved["event_id"]] = _identity(unresolved)
    inputs["input_cut"]["members"].append({
        "contract_id": "company_catalyst_event.v1",
        "ref": unresolved["event_id"],
        "sha256": canonical_json_sha256(unresolved),
        "observed_at": unresolved["observed_at"],
        "accepted_at": unresolved["observed_at"],
        "availability": "available",
    })
    inputs["coverage"]["family_states"]["issuer_readout_guidance"]["observed_count"] = 2
    inputs["coverage"]["source_health"] = "stale"
    query = normalize_wmn_query(view="upcoming", horizon_days=90, q=None, event_family=None, lane=None, limit=50)
    model = build_what_matters_next(
        inputs,
        generation_id="ctgov_run_abcdef1234567890",
        query=query,
        evaluation_cutoff=CUTOFF,
        anchor_date=ANCHOR,
    )
    assert model["state"] == "partial"
    assert model["reason_codes"] == []
    assert model["coverage"]["source_event_count"] == 2
    assert model["coverage"]["issuer_event_count"] == 1
    assert model["coverage"]["security_count"] == 1
    assert model["coverage"]["unresolved_event_count"] == 1
    assert model["coverage"]["selected_row_count"] == 0  # stale source routes rows to reconcile
    assert model["coverage"]["lane_counts"]["RECONCILE"] == 2


def test_wmn_read_model_empty_only_for_complete_selected_view() -> None:
    event = _event(native_event_key="doc#empty-model")
    inputs = _wmn_inputs(event, _resolved_identity(event))
    inputs["coverage"]["missing_owner_ports"] = []
    inputs["coverage"]["family_states"] = {
        "issuer_readout_guidance": {
            "declared_scope": "issuer_disclosure:first_slice",
            "observed_count": 1,
            "state": "supported",
        }
    }
    query = normalize_wmn_query(view="upcoming", horizon_days=7, q="no-such-security", event_family=None, lane=None, limit=50)
    model = build_what_matters_next(
        inputs,
        generation_id="ctgov_run_abcdef1234567890",
        query=query,
        evaluation_cutoff=CUTOFF,
        anchor_date=ANCHOR,
    )
    assert model["state"] == "empty"
    assert model["rows"] == []
    assert model["coverage"]["source_event_count"] == 1
    assert model["coverage"]["selected_row_count"] == 0


def test_wmn_query_normalizer_is_closed_and_cursor_key_is_complete_row_identity() -> None:
    assert normalize_wmn_query(view="upcoming", horizon_days=None, q="  AMLX  ", event_family=None, lane=None, limit=50) == {
        "view": "upcoming", "horizon_days": 90, "q": "amlx", "event_family": None, "lane": None, "limit": 50,
    }
    assert normalize_wmn_query(view="history", horizon_days=None, q=None, event_family=None, lane="MONITOR", limit=25)["horizon_days"] is None
    with pytest.raises(ValueError):
        normalize_wmn_query(view="history", horizon_days=90, q=None, event_family=None, lane=None, limit=50)
    with pytest.raises(ValueError):
        normalize_wmn_query(view="upcoming", horizon_days=14, q=None, event_family=None, lane=None, limit=50)
    with pytest.raises(ValueError):
        normalize_wmn_query(view="upcoming", horizon_days=90, q="x" * 101, event_family=None, lane=None, limit=50)

    event = _event(native_event_key="doc#cursor-key")
    row = _rows(event, _resolved_identity(event))[0]
    key = wmn_row_cursor_key(row)
    assert key == {
        "lane": "ACT_NOW",
        "upper_date": "2026-09-07",
        "lower_date": "2026-09-07",
        "last_material_revision_known_at": None,
        "event_fact_ref": event["event_id"],
        "row_key": row["row_key"],
    }

from engine.biocatalyst.what_matters_next import build_what_matters_next_detail


def test_wmn_detail_is_generation_local_and_related_rows_share_admitted_issuer() -> None:
    first = _event(native_event_key="doc#detail-a")
    second = _event(native_event_key="doc#detail-b", timing=_timing("2026-10-01", "2026-10-01"))
    identity = _resolved_identity(first)
    inputs = _wmn_inputs(first, identity)
    inputs["events"].append(second)
    inputs["identity_projection"][second["event_id"]] = deepcopy(identity)
    inputs["input_cut"]["members"].append({
        "contract_id": "company_catalyst_event.v1", "ref": second["event_id"],
        "sha256": canonical_json_sha256(second), "observed_at": second["observed_at"],
        "accepted_at": second["observed_at"], "availability": "available",
    })
    inputs["coverage"]["family_states"]["issuer_readout_guidance"]["observed_count"] = 2
    detail = build_what_matters_next_detail(
        inputs, generation_id="ctgov_run_detail", event_fact_ref=first["event_id"], issuer_id=None,
        evaluation_cutoff=CUTOFF, anchor_date=ANCHOR,
    )
    assert set(detail) == {"contract_id", "schema_version", "generation_id", "event", "trial", "related_events", "reason_codes", "authority"}
    assert detail["contract_id"] == "biocatalyst_wmn_detail.v1"
    assert detail["generation_id"] == "ctgov_run_detail"
    assert detail["event"]["event_fact_ref"] == first["event_id"]
    assert detail["trial"] is None
    assert detail["reason_codes"] == ["non_registry_event"]
    assert [row["event_fact_ref"] for row in detail["related_events"]] == [second["event_id"]]


def test_wmn_detail_requires_issuer_disambiguation_only_when_event_has_multiple_rows() -> None:
    event = _event(native_event_key="doc#detail-issuer")
    inputs = _wmn_inputs(event, _resolved_identity(event))
    resolved = build_what_matters_next_detail(
        inputs, generation_id="G", event_fact_ref=event["event_id"], issuer_id="ISS:US-XNAS-AMLX",
        evaluation_cutoff=CUTOFF, anchor_date=ANCHOR,
    )
    assert resolved["event"]["issuer"]["issuer_id"] == "ISS:US-XNAS-AMLX"
    with pytest.raises(LookupError):
        build_what_matters_next_detail(
            inputs, generation_id="G", event_fact_ref="evt_source_" + "f" * 64, issuer_id=None,
            evaluation_cutoff=CUTOFF, anchor_date=ANCHOR,
        )
    with pytest.raises(LookupError):
        build_what_matters_next_detail(
            inputs, generation_id="G", event_fact_ref=event["event_id"], issuer_id="ISS:US-XNAS-WRONG",
            evaluation_cutoff=CUTOFF, anchor_date=ANCHOR,
        )


def test_registry_milestone_composition_preserves_owner_identity_and_refuses_sponsor_promotion() -> None:
    from engine.biocatalyst.catalyst_events import project_trial_milestones
    from engine.biocatalyst.what_matters_next import compose_registry_milestone_rows

    projected = project_trial_milestones(
        trials=[{
            "nct_id": "NCT00000001",
            "title": "Synthetic trial",
            "brief_title": "Synthetic trial",
            "status": "RECRUITING",
            "study_type": "INTERVENTIONAL",
            "phases": ["PHASE2"],
            "sponsor": {"name": "Synthetic Sponsor"},
            "conditions": ["Synthetic condition"],
            "enrollment": {"count": 100, "type": "ESTIMATED"},
            "dates": {
                "start": None,
                "primary_completion": {"date": "2026-09-20", "type": "ESTIMATED"},
                "completion": None,
            },
            "updated_at": "2026-09-01",
            "retrieved_at": "2026-09-06T10:00:00Z",
        }],
        anchor_date=date(2026, 9, 6),
        horizon_days=None,
        evidence_by_nct={
            "NCT00000001": {
                "url": "https://clinicaltrials.gov/study/NCT00000001",
                "coverage": "current_only",
            }
        },
    )
    event = projected.events[0].as_dict()
    event["event_revision_ref"] = "trial_snapshot_NCT00000001_revision1"
    row = compose_registry_milestone_rows(
        [event],
        source_health="current",
        evaluation_cutoff=CUTOFF,
        anchor_date=ANCHOR,
    )[0]
    assert row["event_fact_ref"] == "nct:NCT00000001:primary_completion"
    assert row["event_family"] == "registry_primary_completion"
    assert row["event_revision_ref"] == "trial_snapshot_NCT00000001_revision1"
    assert row["occurrence"] == "uncorroborated"
    assert row["timing"]["source_class"] == "registry_schedule"
    assert row["issuer"]["state"] == "unresolved"
    assert row["issuer"]["issuer_id"] is None
    assert row["links"]["stock_research"] == []
    assert row["research_priority"]["lane"] == "RECONCILE"
    assert row["research_priority"]["primary_reason"] == "IDENTITY_UNRESOLVED"


def test_registry_family_coverage_is_derived_from_same_generation_rows() -> None:
    from engine.biocatalyst.catalyst_events import project_trial_milestones

    event = _event()
    inputs = _wmn_inputs(event, _resolved_identity(event))
    projected = project_trial_milestones(
        trials=[{
            "nct_id": "NCT00000001",
            "title": "Synthetic trial",
            "brief_title": "Synthetic trial",
            "status": "RECRUITING",
            "study_type": "INTERVENTIONAL",
            "phases": ["PHASE2"],
            "sponsor": None,
            "conditions": [],
            "enrollment": None,
            "dates": {
                "start": None,
                "primary_completion": {"date": "2026-10", "type": "ESTIMATED"},
                "completion": None,
            },
            "updated_at": "2026-09-01",
            "retrieved_at": "2026-09-06T10:00:00Z",
        }],
        anchor_date=date(2026, 9, 6),
        horizon_days=None,
    )
    registry = []
    for item in projected.events:
        raw = item.as_dict()
        raw["event_revision_ref"] = "trial_snapshot_NCT00000001_revision1"
        registry.append(raw)
    model = build_what_matters_next(
        inputs,
        generation_id="gen-registry",
        query={"view": "reconcile", "limit": 50},
        evaluation_cutoff=CUTOFF,
        anchor_date=ANCHOR,
        registry_events=registry,
    )
    assert model["coverage"]["source_event_count"] == 2
    assert model["coverage"]["family_states"]["registry_primary_completion"] == {
        "declared_scope": "committed_trial_projection:current_generation",
        "observed_count": 1,
        "state": "supported",
    }
    assert model["coverage"]["family_states"]["registry_study_completion"]["observed_count"] == 0
    assert any(row["event_family"] == "registry_primary_completion" for row in model["rows"])
