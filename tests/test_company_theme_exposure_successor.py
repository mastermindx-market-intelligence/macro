"""In-memory consumer proof; fixtures are qualified-interface shapes, not live rights."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from engine.company_intelligence.views import build_bundle as company_bundle
from engine.company_theme_exposure.contracts import (
    ContractError, canonical_json_bytes, canonical_json_sha256, company_filename,
    validate_exposure, validate_manifest,
)
from engine.company_theme_exposure.views import build_bundle as legacy_bundle
from engine.theme_graph import theme_state as owner

MODULE = Path(__file__).resolve().parents[1] / "engine/company_theme_exposure/successor.py"
QUERY = {"effective_at": "2026-10-03", "known_at": "2026-10-03T12:00:00Z"}
GRAPH = "controlled-graph"
GENERATIONS = {role: "controlled-" + role for role in (*owner.ROLES, "specialist")}
LOCAL = "ltheme:finviz:power_grid"
COMPANY = "co:us:HUBB"


def module():
    assert MODULE.exists(), "missing CTE successor: incumbent closed v1 rejects this owner state"
    spec = importlib.util.spec_from_file_location("cte_successor", MODULE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def receipt(role, payload, subject_id=LOCAL, **changes):
    result = {
        "owner": role, "schema": "controlled." + role + "/v1",
        "generation_id": GENERATIONS.get(role, "controlled-specialist"), "graph_generation_id": GRAPH,
        "subject_id": subject_id, "query": copy.deepcopy(QUERY),
        "effective_at": QUERY["effective_at"], "known_at": "2026-10-03T09:00:00Z",
        "available_at": "2026-10-03T08:00:00Z", "recorded_at": "2026-10-03T09:00:00Z",
        "availability": "AVAILABLE", "payload": payload, "sha256": owner.canonical_sha256(payload),
    }
    result.update(changes)
    return result


def subject(node, *, qualified=False):
    canonical = node.startswith("theme:")
    owners = {
        "ontology": receipt("ontology", {"canonical_mapping": {
            "state": "SUBJECT_IS_CANONICAL" if canonical else "UNMAPPED",
            "theme_node_ids": [],
        }}, node),
        "identity": receipt("identity", {"status": "RESOLVED", "issuer_ids": ["issuer:HUBB"]}, node),
        "membership": receipt("membership", {"status": "AVAILABLE", "members": [{
            "ticker": "HUBB", "issuer_id": "issuer:HUBB", "security_id": "security:HUBB",
        }], "declared_count": 1, "eligible_count": 1, "observed_count": 1,
            "basis": "qualified_owner_query", "era": "OBSERVED"}, node),
        "rights": receipt("rights", {"allowed": True, "purpose": "research_internal",
                                    "revision": "controlled-rights"}, node),
        "eligibility": receipt("eligibility", {
            "status": "QUALIFIED" if qualified else "NOT_QUALIFIED",
            "policy_revision": "controlled-sealed" if qualified else None,
            "reason_codes": [] if qualified else ["D2E_UNSEALED"],
        }, node),
    }
    return {"node_id": node, "kind": "canonical_theme" if canonical else "local_theme",
            "name_en": "Grid", "name_zh": "电网", "source_family": None if canonical else "finviz",
            "native_id": None if canonical else "power_grid", "owners": owners,
            "observations": {}, "canonical_aggregation": None}


def inputs(*, qualified=False):
    contexts, parent = company_bundle(
        [{"document_ticker": "HUBB", "fiscal_year": 2026, "fiscal_quarter": 3,
          "call_date": "2026-10-01", "updated_at": "2026-10-02T00:00:00Z",
          "summary": "owner context", "raw_source_url": "https://issuer.example/hubb"}],
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=QUERY["known_at"], as_of=QUERY["effective_at"],
    )
    # Exact canonical writer bytes in memory; no file or remote-publication claim.
    parent["files"] = {company_filename(ticker): {
        "sha256": hashlib.sha256(canonical_json_bytes(context)).hexdigest(),
        "bytes": len(canonical_json_bytes(context)),
    } for ticker, context in contexts.items()}
    state = owner.compose_state(
        [subject("theme:grid"), subject(LOCAL, qualified=qualified)],
        graph_generation_id=GRAPH, owner_generations=GENERATIONS,
        **QUERY, generated_at=QUERY["known_at"],
    )
    identity = receipt("identity", {"status": "RESOLVED", "ticker": "HUBB",
        "company_node_id": COMPANY, "issuer_id": "issuer:HUBB", "security_id": "security:HUBB"},
        COMPANY)
    local = receipt("membership", {"company_node_id": COMPANY, "declared_count": 1,
        "memberships": [{"node_id": LOCAL, "source_family": "finviz", "native_id": "power_grid",
                         "membership_basis": "CURRENT_MEMBERSHIP_NOT_PIT",
                         "source_refs": ["controlled-membership#/power_grid/HUBB"]}]}, COMPANY)
    return dict(contexts=contexts, company_manifest=parent,
        membership={"baskets": {
            "grid": {"members": [{"ticker": "HUBB", "added": "2026-01-01", "removed": None}]},
            "other": {"members": [{"ticker": "HUBB", "added": "2026-01-01", "removed": None}]},
        }},
        crosswalk={"version": 1, "themes": [{"id": "grid", "foresight_id": "grid",
            "name_en": "Grid", "name_zh": "电网", "basket_ids": ["grid"]}],
            "unmapped_baskets": [{"id": "other", "reason": "not a canonical mapping"}]},
        state_artifact=state, **QUERY, expected_state_generation_id=state["generation_id"],
        company_identity_reads={"HUBB": identity}, local_membership_reads={"HUBB": local})


def bundle(data=None):
    return module().compose_shadow_bundle(**(inputs() if data is None else data))


def test_real_owner_read_unmapped_local_and_canonical_projection():
    data = inputs()
    before = copy.deepcopy(data)
    contexts, manifest = bundle(data)
    item = contexts["HUBB"]
    assert item["schema"] == "company_theme_exposure.v2" and item["mode"] == "shadow"
    assert item["exposures"] == [{"theme_id": "grid", "name_en": "Grid", "name_zh": "电网",
                                 "basket_id": "grid", "mapping_qualifier": "curated"}]
    assert item["coverage"] == {"status": "mixed", "active_basket_count": 2,
                               "mapped_basket_count": 1, "unmapped_basket_count": 1}
    assert item["canonical_membership_qualification"] == "CURRENT_VALID_DATE_NOT_PIT"
    assert item["local_memberships"][0]["node_id"] == LOCAL
    assert item["local_memberships"][0]["membership_basis"] == "CURRENT_MEMBERSHIP_NOT_PIT"
    reads = {r["subject_id"]: r for r in item["theme_state"]["reads"]}
    assert reads[LOCAL] == owner.read_theme_state(data["state_artifact"], LOCAL, **QUERY,
        expected_generation_id=data["expected_state_generation_id"])
    assert reads[LOCAL]["status"] == "DESCRIPTIVE"
    assert reads[LOCAL]["subject"]["mapping"]["state"] == "UNMAPPED"
    assert item["local_coverage"]["status"] == "AVAILABLE"
    assert item["company_intelligence"]["latest_event_id"] == data["contexts"]["HUBB"]["latest_event_id"]
    assert item["company_intelligence"]["context_sha256"] == canonical_json_sha256(data["contexts"]["HUBB"])
    assert manifest["source"]["company_intelligence"]["sha256"] == canonical_json_sha256(data["company_manifest"])
    assert manifest["local_membership_count"] == 1 and manifest["exposure_count"] == 1
    assert not any(v for k, v in item["authority_caps"].items() if k.startswith("may_"))
    assert data == before
    module().validate_exposure_v2(item)
    module().validate_manifest_v2(manifest, allow_unmaterialized_files=True)


def test_qualified_status_is_preserved_without_financial_authority():
    out, _ = bundle(inputs(qualified=True))
    read = next(r for r in out["HUBB"]["theme_state"]["reads"] if r["subject_id"] == LOCAL)
    assert read["status"] == "QUALIFIED"
    assert read["subject"]["eligibility"]["status"] == "QUALIFIED"
    assert out["HUBB"]["authority_caps"]["may_publish"] is False


@pytest.mark.parametrize("case", ["absent", "valid_empty", "unavailable", "malformed_empty"])
def test_local_empty_unavailable_and_missing_are_not_zero_filled(case):
    data = inputs()
    if case == "absent":
        data["local_membership_reads"] = {}
    else:
        read = data["local_membership_reads"]["HUBB"]
        if case == "unavailable":
            read.update(availability="UNAVAILABLE", payload=None, sha256=owner.canonical_sha256(None))
        else:
            read["payload"]["memberships"] = []
            read["payload"]["declared_count"] = 0
            read["sha256"] = owner.canonical_sha256(read["payload"])
            if case == "valid_empty":
                read["availability"] = "VALID_EMPTY"
    if case == "malformed_empty":
        with pytest.raises(ContractError):
            bundle(data)
        return
    out, _ = bundle(data)
    coverage = out["HUBB"]["local_coverage"]
    assert out["HUBB"]["local_memberships"] == []
    assert coverage["status"] == ("VALID_EMPTY" if case == "valid_empty" else "UNAVAILABLE")
    assert coverage["declared_count"] == (0 if case == "valid_empty" else None)
    assert coverage["observed_count"] == (0 if case == "valid_empty" else None)


def test_missing_identity_does_not_invalidate_canonical_membership():
    data = inputs()
    data["company_identity_reads"] = {}
    out, _ = bundle(data)
    assert len(out["HUBB"]["exposures"]) == 1
    assert out["HUBB"]["local_coverage"]["status"] == "UNAVAILABLE"
    assert "COMPANY_IDENTITY_MISSING" in out["HUBB"]["local_coverage"]["reason_codes"]


@pytest.mark.parametrize("field,value", [
    ("graph_generation_id", "foreign-graph"), ("generation_id", "foreign-identity"),
    ("subject_id", "co:us:OTHER"), ("sha256", "0" * 64),
])
def test_identity_receipt_substitution_refuses(field, value):
    data = inputs()
    data["company_identity_reads"]["HUBB"][field] = value
    with pytest.raises(ContractError):
        bundle(data)


@pytest.mark.parametrize("case", ["parent_generation", "context_digest", "latest_event", "foreign_company", "known_query", "state_generation"])
def test_parent_event_and_query_substitution_refuse(case):
    data = inputs()
    if case == "parent_generation":
        data["contexts"]["HUBB"]["generation_id"] = "a" * 24
    elif case == "context_digest":
        data["company_manifest"]["files"]["companies/HUBB.json"]["sha256"] = "0" * 64
    elif case == "latest_event":
        data["contexts"]["HUBB"]["latest_event_id"] = "cie_wrong"
    elif case == "foreign_company":
        data["contexts"]["OTHER"] = data["contexts"].pop("HUBB")
    elif case == "known_query":
        data["known_at"] = "2026-10-03T13:00:00Z"
    else:
        data["expected_state_generation_id"] = "0" * 32
    with pytest.raises(ContractError):
        bundle(data)


def test_later_emission_uses_actual_reader_and_keeps_membership():
    data = inputs()
    state = owner.compose_state(
        [subject("theme:grid"), subject(LOCAL)], graph_generation_id=GRAPH,
        owner_generations=GENERATIONS, **QUERY, generated_at="2026-10-03T13:00:00Z")
    data.update(state_artifact=state, expected_state_generation_id=state["generation_id"])
    out, _ = bundle(data)
    item = out["HUBB"]
    assert len(item["local_memberships"]) == 1 and len(item["exposures"]) == 1
    assert all(r["status"] == "UNAVAILABLE" and "STATE_NOT_YET_EMITTED" in r["reason_codes"]
               for r in item["theme_state"]["reads"])
    assert item["theme_state"]["state_generated_at"] == "2026-10-03T13:00:00Z"
    assert item["local_coverage"]["state_available_count"] == 0


def test_missing_state_is_partial_not_empty_membership():
    data = inputs()
    data["state_artifact"] = None
    out, _ = bundle(data)
    item = out["HUBB"]
    assert item["theme_state"]["status"] == "MISSING"
    assert item["theme_state"]["state_sha256"] is None
    assert len(item["local_memberships"]) == 1
    assert item["status"] == "partial" and "theme_state_missing" in item["warnings"]


def test_digest_scopes_are_distinct_and_raw_bytes_are_unmaterialized():
    data = inputs()
    out, _ = bundle(data)
    binding = out["HUBB"]["theme_state"]
    assert binding["state_sha256"] == data["state_artifact"]["state_sha256"]
    assert binding["canonical_json_sha256"] == canonical_json_sha256(data["state_artifact"])
    raw_digest = hashlib.sha256(json.dumps(data["state_artifact"], indent=2).encode()).hexdigest()
    assert len({binding["state_sha256"], binding["canonical_json_sha256"], raw_digest}) == 3
    assert binding["raw_bytes_sha256"] is None and binding["raw_bytes_status"] == "UNMATERIALIZED"
    for field, wrong in [("state_sha256", binding["canonical_json_sha256"]),
                         ("canonical_json_sha256", binding["state_sha256"]),
                         ("raw_bytes_sha256", raw_digest)]:
        broken = copy.deepcopy(out["HUBB"])
        broken["theme_state"][field] = wrong
        with pytest.raises(ContractError):
            module().validate_exposure_v2(broken, state_artifact=data["state_artifact"])


@pytest.mark.parametrize("case", ["extra", "permission", "eligibility", "receipt_query", "row_identity"])
def test_closed_payload_and_read_contract_tampering_refuse(case):
    out, _ = bundle()
    item = out["HUBB"]
    if case == "extra":
        item["economic_score"] = 0.9
    elif case == "permission":
        item["authority_caps"]["may_publish"] = True
    elif case == "row_identity":
        item["local_memberships"][0]["native_id"] = "other"
    else:
        read = next(r for r in item["theme_state"]["reads"] if r["subject_id"] == LOCAL)
        if case == "eligibility":
            read["status"] = "QUALIFIED"
        else:
            read["known_at"] = "2026-10-03T13:00:00Z"
    with pytest.raises(ContractError):
        module().validate_exposure_v2(item)


def test_manifest_generation_and_aggregate_receipts_are_bound():
    out, manifest = bundle()
    for case in ["generation", "count", "parent", "state_hash"]:
        broken = copy.deepcopy(manifest)
        if case == "generation":
            broken["generation_id"] = "0" * 24
        elif case == "count":
            broken["local_membership_count"] += 1
        elif case == "parent":
            broken["source"]["company_intelligence"]["generation_id"] = "0" * 24
        else:
            broken["source"]["theme_state"]["state_sha256"] = "0" * 64
        with pytest.raises(ContractError):
            module().validate_manifest_v2(broken, allow_unmaterialized_files=True, exposures=out)


def test_incumbent_v1_positive_and_closed_keys_remain_unchanged():
    data = inputs()
    legacy = {"schema": "neuralweb.theme_state.v1", "as_of": QUERY["effective_at"],
              "authority": {"is_context_only": True}, "n_themes": 1,
              "themes": [{"theme_id": "grid"}], "stale_legs": []}
    out, manifest = legacy_bundle(data["contexts"], company_manifest=data["company_manifest"],
        membership=data["membership"], crosswalk=data["crosswalk"], theme_state=legacy)
    validate_exposure(out["HUBB"])
    validate_manifest(manifest, allow_unmaterialized_files=True)
    broken = copy.deepcopy(out["HUBB"])
    broken["local_memberships"] = []
    with pytest.raises(ContractError):
        validate_exposure(broken)
    successor, _ = bundle(data)
    with pytest.raises(ContractError):
        validate_exposure(successor["HUBB"])


def test_no_filesystem_network_or_ambient_clock_in_compiler(monkeypatch):
    data = inputs()
    owner.validate_state(data["state_artifact"])  # prime the owner's existing schema read
    consumer = module()
    import ast
    tree = ast.parse(MODULE.read_text())
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"now", "utcnow", "today"} for node in ast.walk(tree))
    import builtins
    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("unexpected file read/write"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("unexpected file read"))
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("unexpected file read"))
    monkeypatch.setattr(Path, "write_text", lambda *a, **k: pytest.fail("unexpected output"))
    monkeypatch.setattr(Path, "write_bytes", lambda *a, **k: pytest.fail("unexpected output"))
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("network"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network"))
    out, manifest = consumer.compose_shadow_bundle(**data)
    assert manifest["files"] == {}
    assert out["HUBB"]["generated_at"] == data["company_manifest"]["generated_at"]

@pytest.mark.parametrize("clock,expected_reason", [
    ("2026-10-03", "KNOWLEDGE_TIME_UNPROVEN"),
    ("2026-10-03T13:00:00Z", "SOURCE_AFTER_CUTOFF"),
])
def test_owner_membership_clocks_preserve_unavailability_not_zero(clock, expected_reason):
    data = inputs()
    read = data["local_membership_reads"]["HUBB"]
    read.update(available_at=clock, known_at=clock, recorded_at=clock)
    out, _ = bundle(data)
    item = out["HUBB"]
    assert len(item["exposures"]) == 1
    assert item["local_memberships"] == []
    assert item["local_coverage"]["status"] == "UNAVAILABLE"
    assert item["local_coverage"]["observed_count"] is None
    assert expected_reason in item["local_coverage"]["reason_codes"]


def test_valid_empty_identity_cannot_assert_a_resolved_company():
    data = inputs()
    data["company_identity_reads"]["HUBB"]["availability"] = "VALID_EMPTY"
    with pytest.raises(ContractError, match="identity"):
        bundle(data)


def test_owner_state_preserves_specialist_nulls_conflicts_and_source_clocks():
    data = inputs()
    local = subject(LOCAL)
    value = {"acceleration": None, "null_reason": "SHORT_HISTORY", "return": 1.25}
    observation = {
        "owner": "specialist", "schema": "specialist.native/v1",
        "presence": "POSITIVE", "freshness": "FRESH", "value": value,
        "null_reason": None, "units": "percentage_points", "window": "5_closed_sessions",
        "coverage": {"declared": 2, "observed": 1, "basis": "CURRENT_MEMBERSHIP_NOT_PIT"},
        "conflicts": [{"owner": "other_native", "value": -1.0, "reason": "different_window"}],
        "source_receipts": [receipt("specialist", value, effective_at="2026-10-03T08:00:00Z")],
        "freshness_policy": {"max_age_hours": 30, "owner_policy_revision": "controlled-owner-30h"},
    }
    local["observations"]["closed_session_leadership"] = observation
    state = owner.compose_state([subject("theme:grid"), local],
        graph_generation_id=GRAPH, owner_generations=GENERATIONS, **QUERY,
        generated_at=QUERY["known_at"])
    data.update(state_artifact=state, expected_state_generation_id=state["generation_id"])
    out, _ = bundle(data)
    read = next(r for r in out["HUBB"]["theme_state"]["reads"] if r["subject_id"] == LOCAL)
    exact = next(s for s in state["subjects"] if s["node_id"] == LOCAL)["observations"]
    assert read["subject"]["observations"] == exact
    assert exact["closed_session_leadership"]["value"]["acceleration"] is None
    assert exact["closed_session_leadership"]["units"] == "percentage_points"
    assert exact["closed_session_leadership"]["source_receipts"][0]["available_at"] == "2026-10-03T08:00:00Z"


def test_rights_unavailable_does_not_become_permission_or_empty_membership():
    data = inputs()
    local = subject(LOCAL)
    rights = local["owners"]["rights"]
    rights.update(availability="UNAVAILABLE", payload=None, sha256=owner.canonical_sha256(None))
    state = owner.compose_state([subject("theme:grid"), local], graph_generation_id=GRAPH,
        owner_generations=GENERATIONS, **QUERY, generated_at=QUERY["known_at"])
    data.update(state_artifact=state, expected_state_generation_id=state["generation_id"])
    out, _ = bundle(data)
    item = out["HUBB"]
    read = next(r for r in item["theme_state"]["reads"] if r["subject_id"] == LOCAL)
    assert read["status"] == "UNAVAILABLE"
    assert len(item["local_memberships"]) == 1
    assert item["local_coverage"]["state_available_count"] == 0
    assert all(value is False for key, value in item["authority_caps"].items() if key.startswith("may_"))


@pytest.mark.parametrize("extra_seconds,expected", [(0, "DESCRIPTIVE"), (1, "UNAVAILABLE")])
def test_actual_state_reader_30h_boundary_is_preserved(extra_seconds, expected):
    from datetime import datetime, timedelta, timezone
    data = inputs()
    later = (datetime(2026, 10, 3, 12, tzinfo=timezone.utc) +
             timedelta(hours=30, seconds=extra_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    contexts, parent = company_bundle(
        [{"document_ticker": "HUBB", "fiscal_year": 2026, "fiscal_quarter": 3,
          "call_date": "2026-10-01", "updated_at": "2026-10-02T00:00:00Z",
          "summary": "owner context", "raw_source_url": "https://issuer.example/hubb"}],
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=later, as_of=QUERY["effective_at"])
    parent["files"] = {company_filename(ticker): {
        "sha256": canonical_json_sha256(context), "bytes": len(canonical_json_bytes(context)),
    } for ticker, context in contexts.items()}
    data.update(contexts=contexts, company_manifest=parent, known_at=later)
    for name in ("company_identity_reads", "local_membership_reads"):
        data[name]["HUBB"]["query"]["known_at"] = later
    out, _ = bundle(data)
    read = next(r for r in out["HUBB"]["theme_state"]["reads"] if r["subject_id"] == LOCAL)
    assert read["status"] == expected
    assert ("STATE_STALE" in read["reason_codes"]) == bool(extra_seconds)
    assert len(out["HUBB"]["local_memberships"]) == 1

@pytest.mark.parametrize("case", ["ticker_count", "empty_counts", "warning"])
def test_manifest_closed_coverage_and_warning_meanings(case):
    _, manifest = bundle()
    if case == "ticker_count":
        manifest["coverage"]["unmapped_only_ticker_count"] = 2
    elif case == "empty_counts":
        manifest["company_count"] = 0
        manifest["local_coverage"] = dict.fromkeys(manifest["local_coverage"], 0)
        manifest["status"] = "empty"
    else:
        manifest["warnings"].append("economic_signal")
        manifest["warnings"].sort()
    with pytest.raises(ContractError):
        module().validate_manifest_v2(manifest, allow_unmaterialized_files=True)


def test_empty_company_cohort_retains_global_coverage_and_missing_source():
    data = inputs()
    contexts, parent = company_bundle([], tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=QUERY["known_at"], as_of=QUERY["effective_at"])
    data.update(contexts=contexts, company_manifest=parent, state_artifact=None,
                company_identity_reads={}, local_membership_reads={})
    out, manifest = bundle(data)
    assert out == {} and manifest["status"] == "empty"
    assert manifest["company_count"] == manifest["exposure_count"] == manifest["local_membership_count"] == 0
    assert manifest["coverage"]["active_member_tickers_without_company_context"] == 1
    assert manifest["warnings"] == ["active_memberships_unmapped", "theme_state_missing"]


@pytest.mark.parametrize("field,value", [
    ("ticker", "OTHER"), ("issuer_id", "issuer:OTHER"), ("security_id", "security:OTHER"),
])
def test_inverse_local_join_cannot_attach_another_forward_owner_member(field, value):
    data = inputs()
    local = subject(LOCAL)
    forward = local["owners"]["membership"]
    forward["payload"]["members"][0][field] = value
    forward["sha256"] = owner.canonical_sha256(forward["payload"])
    state = owner.compose_state([subject("theme:grid"), local], graph_generation_id=GRAPH,
        owner_generations=GENERATIONS, **QUERY, generated_at=QUERY["known_at"])
    assert owner.read_theme_state(state, LOCAL, **QUERY)["status"] == "DESCRIPTIVE"
    data.update(state_artifact=state, expected_state_generation_id=state["generation_id"])
    with pytest.raises(ContractError, match="forward.*membership"):
        bundle(data)


@pytest.mark.parametrize("target", ["exposure", "manifest"])
def test_authority_caps_require_exact_json_booleans(target):
    data = inputs()
    out, manifest = bundle(data)
    item = out["HUBB"] if target == "exposure" else manifest
    item["authority_caps"] = {key: int(value) for key, value in item["authority_caps"].items()}
    with pytest.raises(ContractError, match="authority"):
        if target == "exposure":
            module().validate_exposure_v2(item, state_artifact=data["state_artifact"])
        else:
            module().validate_manifest_v2(item, allow_unmaterialized_files=True,
                                         state_artifact=data["state_artifact"])


@pytest.mark.parametrize("field", ["declared_count", "observed_count", "state_available_count"])
def test_local_coverage_counts_require_exact_integers(field):
    data = inputs()
    out, _ = bundle(data)
    out["HUBB"]["local_coverage"][field] = True
    with pytest.raises(ContractError, match="count"):
        module().validate_exposure_v2(out["HUBB"], state_artifact=data["state_artifact"])


def test_inverse_forward_source_clocks_cannot_be_refreshed_by_a_matching_label():
    data = inputs()
    inverse = data["local_membership_reads"]["HUBB"]
    inverse.update(available_at="2026-10-03T10:00:00Z", known_at="2026-10-03T11:00:00Z",
                   recorded_at="2026-10-03T11:00:00Z")
    with pytest.raises(ContractError, match="source clocks"):
        bundle(data)
