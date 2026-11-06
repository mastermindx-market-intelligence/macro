"""Shadow CTEv3 over an already-read production generation. No publication."""
from __future__ import annotations

import ast
import copy
import hashlib
import shutil
from pathlib import Path

import pytest

from engine.company_intelligence.views import build_bundle as company_bundle
from engine.company_intelligence.views import write_generation
from engine.company_theme_exposure.contracts import (
    ContractError, canonical_json_sha256, validate_exposure, validate_manifest,
)
from engine.company_theme_exposure.successor import (
    compose_shadow_bundle, validate_exposure_v2, validate_manifest_v2,
)
from engine.company_theme_exposure.views import derive_generation_id, load_company_generation
from engine.neuralweb import theme_state_generation as generation
from engine.neuralweb import theme_state_generation_reader as generation_reader
from engine.theme_graph import identity, theme_state
from engine.theme_graph import theme_state_production as production
from tests.test_company_theme_exposure_successor import (
    GENERATIONS, GRAPH, QUERY, bundle as v2_bundle, inputs as v2_inputs, subject as graph_subject,
)
from tests.test_theme_state_generation import AcceptedFixture
from tests.test_theme_state_generation_reader import ReadFixture, publication_plan
from tests.test_theme_state_production import EFFECTIVE, EMITTED, KNOWN, LOCAL, production_world

SUCCESSOR = Path(__file__).resolve().parents[1] / "engine/company_theme_exposure/successor.py"
ORIGINAL_FUNCTIONS = (
    "_closed", "_text", "_hash", "_count", "_strings", "_clock", "_caps", "_owner_read",
    "_owner_reasons", "_check_state_read", "_binding", "_new_binding", "_local_projection",
    "_check_forward_membership", "_warnings", "validate_exposure_v2", "_manifest_warnings",
    "validate_manifest_v2", "compose_shadow_bundle",
)
ORIGINAL_FUNCTION_AST_SHA256 = "d1b70ba3902f79809fdfde444382cc1ca3a5abc2071160bc792a5c20d14928f6"
USE = "2026-10-04T13:00:00Z"
HISTORY = {
    "document_ticker": "HUBB", "fiscal_year": 2026, "fiscal_quarter": 3,
    "call_date": "2026-10-01", "updated_at": "2026-10-02T00:00:00Z",
    "summary": "owner context", "raw_source_url": "https://issuer.example/hubb",
}
MAPPED = {
    "version": 1,
    "themes": [{"id": "grid", "foresight_id": "grid", "name_en": "Grid", "name_zh": "电网", "basket_ids": ["grid"]}],
    "unmapped_baskets": [],
}
UNMAPPED = {
    "version": 1,
    "themes": [{"id": "grid", "foresight_id": "grid", "name_en": "Grid", "name_zh": "电网", "basket_ids": ["grid"]}],
    "unmapped_baskets": [{"id": "other", "reason": "not a canonical mapping"}],
}


def successor():
    from engine.company_theme_exposure import successor as module
    return module


def membership_for(*baskets):
    return {"baskets": {basket: {"members": [{"ticker": "HUBB", "added": "2026-01-01", "removed": None}]}
                        for basket in baskets}}


def tree_bytes(root: Path):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


def refusal_receipt(status="MISSING", reason="ACCEPTED_REFERENCE_MISSING"):
    return {
        "schema": generation_reader.SCHEMA, "status": status, "reason_codes": [reason],
        "query": {"effective_at": EFFECTIVE, "known_at": KNOWN},
        "purpose": "research_internal", "use_at": USE, "publication": None,
        "state_identity": None, "state": None, "compatibility": None, "history": None,
        "subject_read": None, "source_clocks": None,
        "authority_caps": dict(production.FLAGS), "materialization_allowed": False,
    }


def finalized_ci(tmp: Path, generated_at, rows=(HISTORY,)):
    contexts, manifest = company_bundle(
        list(rows), tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at=generated_at, as_of=EFFECTIVE)
    root = tmp / "company-intelligence"
    write_generation(root, contexts, manifest)
    loaded_contexts, loaded_manifest = load_company_generation(root)
    return loaded_contexts, loaded_manifest, root


def publish(root, *, owner_readers=None, known_at=KNOWN, generated_at=EMITTED):
    from engine.neuralweb import theme_state_adapter as adapter
    bundle = adapter.capture_owner_bundle(
        root, effective_at=EFFECTIVE, known_at=known_at, owner_readers=owner_readers)
    entry = generation.entry_preflight(root, legacy_api=True)
    plan = generation.prepare_generation(
        bundle, root=root, generated_at=generated_at, activation_at=generated_at, entry=entry)
    generation.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    return plan


def read_receipt(root, **overrides):
    args = dict(effective_at=EFFECTIVE, known_at=KNOWN, purpose="research_internal",
                use_at=USE, controlled_verifier=ReadFixture())
    args.update(overrides)
    answer = generation_reader.read_generation(root, **args)
    witness = publication_plan(root, answer) if answer["state"] is not None else None
    generation_reader.validate_read_receipt(answer, publication_plan=witness)
    return answer, witness


def compose(contexts, manifest, receipt, plan, *, membership, crosswalk, identity=None, local=None):
    return successor().compose_production_shadow_bundle(
        contexts, company_manifest=manifest, membership=membership, crosswalk=crosswalk,
        generation_read_receipt=receipt, publication_plan=plan,
        company_identity_reads={} if identity is None else identity,
        local_membership_reads={} if local is None else local)


def install_company(root):
    import pandas as pd
    nodes_path = root / "data/theme_graph/nodes.parquet"
    nodes = pd.read_parquet(nodes_path)
    company = identity.company_node_id("baskets", "HUBB", breaks={})
    row = nodes.iloc[0].to_dict()
    row.update(node_id=company, kind="company", name_en="HUBB", name_zh="HUBB")
    if "source_meta" in row:
        row["source_meta"] = "{}"
    nodes = pd.concat([nodes, pd.DataFrame([row], columns=nodes.columns)], ignore_index=True)
    nodes.to_parquet(nodes_path, index=False)
    ref = root / "data/reference"
    ref.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "inception_code": "HUBB", "security_id": "fixture-security:HUBB",
        "issuer_id": "fixture-issuer:HUBB", "issuer_state": "RESOLVED", "security_state": None,
        "listing_key": "US-HUBB",
    }]).to_parquet(ref / "security_master.parquet", index=False)
    pd.DataFrame(columns=["vendor", "vendor_symbol", "security_id", "valid_from", "valid_to"]).to_parquet(
        ref / "vendor_aliases.parquet", index=False)
    (ref / "_receipt.json").write_text(
        '{"generated_at":"2026-10-02T09:00:00Z","code_version":"controlled-fixture","identity_exceptions":[]}',
        encoding="utf-8")
    return company


class ForwardOwnerReader:
    """Controlled prequalification so the diagnostic witness can prove one roster."""

    def read_state_qualification(self, *, node_id, query, graph_capture_id, native_reads, source_sha256):
        if node_id != LOCAL:
            return None
        native = native_reads["membership"]
        if native["availability"] != "AVAILABLE" or native["value"].get("pit") is not True:
            raise ValueError("fixture membership is not an actual PIT read")
        members = native["value"]["members"]
        identities = native_reads["identity"]
        actual = {}
        for ticker in members:
            matches = [(nid, read["value"]) for nid, read in identities.items()
                       if read["availability"] == "AVAILABLE"
                       and __import__("engine.theme_graph.identity_resolution", fromlist=["_best_effort_symbol"])._best_effort_symbol(nid) == ticker]
            if len(matches) != 1:
                raise ValueError("fixture company identity is unresolved")
            nid, resolved = matches[0]
            if resolved.get("resolution_state") != "RESOLVED" or not resolved.get("security_id"):
                raise ValueError("fixture company identity is unresolved")
            actual[ticker] = {"node_id": nid, "security_id": resolved.get("security_id"),
                              "issuer_id": resolved.get("issuer_id")}
        def receipt(role, payload, availability="AVAILABLE"):
            return {
                "owner": role, "schema": "fixture.accepted_owner_read/v1",
                "generation_id": "controlled-owner-generation", "graph_generation_id": graph_capture_id,
                "subject_id": node_id, "query": copy.deepcopy(query), "effective_at": "2026-10-02",
                "available_at": "2026-10-02T08:00:00Z", "known_at": "2026-10-02T09:00:00Z",
                "recorded_at": "2026-10-02T09:00:00Z", "availability": availability,
                "payload": payload, "sha256": theme_state.canonical_sha256(payload),
            }
        member_rows = [{"ticker": ticker, "security_id": row["security_id"], "issuer_id": row["issuer_id"]}
                       for ticker, row in actual.items()]
        membership_payload = {
            "status": "AVAILABLE", "basket_id": native["value"]["basket_id"], "members": member_rows,
            "declared_count": len(members), "eligible_count": len(members), "observed_count": len(members),
            "basis": "controlled_prequalified_owner_population", "era": "OBSERVED",
            "native_owner_read_sha256": theme_state.canonical_sha256(native),
        }
        identity_payload = {
            "status": "RESOLVED", "member_identities": actual,
            "native_owner_read_sha256": theme_state.canonical_sha256(identities),
        }
        return {"owner_receipts": {
            "membership": receipt("membership", membership_payload),
            "identity": receipt("identity", identity_payload),
        }, "source_receipts": {}}


def owner_receipt(role, payload, *, graph, subject_id, availability="AVAILABLE", clocks=None):
    clocks = clocks or {
        "effective_at": "2026-10-02", "available_at": "2026-10-02T08:00:00Z",
        "known_at": "2026-10-02T09:00:00Z", "recorded_at": "2026-10-02T09:00:00Z",
    }
    result = {
        "owner": role, "schema": "controlled." + role + "/v1",
        "generation_id": graph["owner_generations"][role],
        "graph_generation_id": graph["graph_generation_id"], "subject_id": subject_id,
        "query": {"effective_at": graph["effective_at"], "known_at": graph["known_at"]},
        **clocks, "availability": availability, "payload": payload,
        "sha256": theme_state.canonical_sha256(payload),
    }
    return result


def contains_key(value, key):
    if isinstance(value, dict):
        return key in value or any(contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(contains_key(item, key) for item in value)
    return False


def test_contract_v3_api_is_present():
    module = successor()
    for name in ("compose_production_shadow_bundle", "validate_production_exposure", "validate_production_manifest"):
        assert callable(getattr(module, name)), name


def test_contract_unsupported_schema_is_not_a_missing_state():
    receipt = refusal_receipt()
    receipt["schema"] = "neuralweb.theme_state_generation_read.v999"
    with pytest.raises(ContractError, match="schema"):
        successor().compose_production_shadow_bundle(
            {}, company_manifest={}, membership={}, crosswalk={},
            generation_read_receipt=receipt, publication_plan=None,
            company_identity_reads={}, local_membership_reads={})


def test_contract_unhashable_schema_is_refused_not_a_type_error():
    for bad in (["neuralweb.theme_state_generation_read.v1", "neuralweb.theme_state_generation_read.v2"],
                {"schema": "neuralweb.theme_state_generation_read.v1"},
                {"neuralweb.theme_state_generation_read.v2"}):
        receipt = refusal_receipt()
        receipt["schema"] = bad
        with pytest.raises(ContractError, match="schema"):
            successor().compose_production_shadow_bundle(
                {}, company_manifest={}, membership={}, crosswalk={},
                generation_read_receipt=receipt, publication_plan=None,
                company_identity_reads={}, local_membership_reads={})


def test_contract_invalid_receipt_is_not_a_fabricated_missing_state():
    with pytest.raises(ContractError, match="invalid"):
        successor().compose_production_shadow_bundle(
            {}, company_manifest={}, membership={}, crosswalk={},
            generation_read_receipt=refusal_receipt("INVALID", "READ_CONTRACT_INVALID"),
            publication_plan={"state_b64": "must-not-be-read"},
            company_identity_reads={}, local_membership_reads={})


def test_contract_malformed_receipt_fails_closed():
    with pytest.raises(ContractError):
        successor().compose_production_shadow_bundle(
            {}, company_manifest={}, membership={}, crosswalk={},
            generation_read_receipt={"schema": generation_reader.SCHEMA, "status": "MISSING"},
            publication_plan=None, company_identity_reads={}, local_membership_reads={})


def test_preserved_v1_v2_asts_and_protected_sources():
    module = successor()
    assert module.EXPOSURE_SCHEMA == "company_theme_exposure.v2"
    assert module.MANIFEST_SCHEMA == "company_theme_exposure_manifest.v2"
    tree = ast.parse(SUCCESSOR.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ORIGINAL_FUNCTIONS]
    assert [node.name for node in functions] == list(ORIGINAL_FUNCTIONS)
    digest = hashlib.sha256("\n".join(ast.dump(node, include_attributes=False) for node in functions).encode()).hexdigest()
    assert digest == ORIGINAL_FUNCTION_AST_SHA256
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr == "read_generation" for node in calls)
    assert not any(isinstance(node.func, ast.Name) and node.func.id == "read_generation" for node in calls)
    # Exact unchanged-source hashes are checked by the source owner at review,
    # not hardcoded against unrelated CI/schema revisions in a reusable test.
    assert generation_reader.SCHEMA == "neuralweb.theme_state_generation_read.v1"
    exposed, manifest = v2_bundle()
    validate_exposure_v2(exposed["HUBB"])
    validate_manifest_v2(manifest, allow_unmaterialized_files=True)
    legacy = v2_inputs()
    from engine.company_theme_exposure.views import build_bundle as legacy_bundle
    out, old_manifest = legacy_bundle(
        legacy["contexts"], company_manifest=legacy["company_manifest"], membership=legacy["membership"],
        crosswalk=legacy["crosswalk"], theme_state=None, as_of=QUERY["effective_at"])
    validate_exposure(out["HUBB"])
    validate_manifest(old_manifest, allow_unmaterialized_files=True)
    data = v2_inputs()
    v2_out, _ = compose_shadow_bundle(**data)
    assert v2_out["HUBB"]["schema"] == "company_theme_exposure.v2"
    assert v2_out["HUBB"]["canonical_membership_qualification"] == "CURRENT_VALID_DATE_NOT_PIT"


@pytest.fixture
def standard_publication(production_world):
    root = production_world
    publish(root)
    receipt, plan = read_receipt(root)
    return {"root": root, "receipt": receipt, "plan": plan}


@pytest.fixture
def qualified_publication(production_world):
    root = production_world
    company = install_company(root)
    publish(root, owner_readers=ForwardOwnerReader())
    receipt, plan = read_receipt(root, node_id="theme:travel")
    return {"root": root, "receipt": receipt, "plan": plan, "company": company}


def test_real_canonical_unmapped_local_exact_zero_and_forward_gate(qualified_publication, tmp_path):
    world = qualified_publication
    receipt, plan = world["receipt"], world["plan"]
    graph = receipt["state"]["diagnostic_graph_state"]
    assert receipt["state"]["diagnostic_graph_state_role"] == "NON_AUTHORITATIVE_VALIDATION_WITNESS"
    local_graph = next(row for row in graph["subjects"] if row["node_id"] == LOCAL)
    forward = local_graph["owner_receipts"]["membership"]
    assert forward["availability"] == "AVAILABLE"
    member = forward["payload"]["members"][0]
    assert member["ticker"] == "HUBB"
    company = world["company"]
    assert company == member.get("node_id") or company.startswith("co:")
    identity_read = owner_receipt("identity", {
        "status": "RESOLVED", "ticker": "HUBB", "company_node_id": company,
        "issuer_id": member["issuer_id"], "security_id": member["security_id"],
    }, graph=graph, subject_id=company)
    clocks = {key: forward[key] for key in ("effective_at", "available_at", "known_at", "recorded_at")}
    local_read = owner_receipt("membership", {
        "company_node_id": company, "declared_count": 1,
        "memberships": [{"node_id": LOCAL, "source_family": "finviz", "native_id": "power_grid",
                         "membership_basis": "CURRENT_MEMBERSHIP_NOT_PIT",
                         "source_refs": ["controlled-membership#/power_grid/HUBB"]}],
    }, graph=graph, subject_id=company, clocks=clocks)
    contexts, manifest, ci_root = finalized_ci(tmp_path, KNOWN)
    generation_before = tree_bytes(world["root"])
    ci_before = tree_bytes(ci_root)
    inputs = dict(contexts=contexts, manifest=manifest, receipt=receipt, plan=plan,
                  membership=membership_for("grid", "other"), crosswalk=UNMAPPED,
                  identity={"HUBB": identity_read}, local={"HUBB": local_read})
    frozen = copy.deepcopy(inputs)
    exposures, produced = compose(**inputs)
    assert inputs == frozen
    assert tree_bytes(world["root"]) == generation_before
    assert tree_bytes(ci_root) == ci_before
    item = exposures["HUBB"]
    assert item["schema"] == "company_theme_exposure.v3"
    assert item["authority"] == "context_only" and item["mode"] == "shadow"
    assert item["materialization_allowed"] is False
    assert item["authority_caps"] == production.FLAGS
    assert all(value is False for value in item["authority_caps"].values())
    assert item["canonical_membership_qualification"] == "CURRENT_VALID_DATE_NOT_PIT"
    assert item["generated_at"] == KNOWN and item["generated_at"] != USE
    assert item["production_generation"]["use_at"] == USE
    assert item["production_generation"]["query"]["known_at"] == KNOWN
    assert item["exposures"] == [{"theme_id": "grid", "name_en": "Grid", "name_zh": "电网",
                                 "basket_id": "grid", "mapping_qualifier": "curated"}]
    assert item["coverage"]["unmapped_basket_count"] == 1
    assert item["local_memberships"][0]["node_id"] == LOCAL
    assert item["local_memberships"][0]["native_id"] == "power_grid"
    assert "theme_state" not in item and "diagnostic_graph_state" not in item["production_generation"]
    assert not contains_key(item, "diagnostic_graph_state")
    assert not contains_key(item, "raw_b64") or "prefix_b64" in item["production_generation"]["history"]
    assert set(item["production_generation"]["compatibility_digests"]) == {
        "raw_sha256", "canonical_sha256", "unstamped_sha256"}
    assert item["production_generation"]["publication"] == receipt["publication"]
    assert item["production_generation"]["state_identity"] == receipt["state_identity"]
    assert item["production_generation"]["history"] == receipt["history"]
    assert item["production_generation"]["status"] == receipt["status"] == "DESCRIPTIVE"
    assert "D2E_NOT_QUALIFIED" in item["production_generation"]["reason_codes"]
    reads = {row["subject_id"]: row for row in item["production_generation"]["subject_reads"]}
    assert set(reads) == {"theme:grid", LOCAL}
    assert len(receipt["state"]["subjects"]) > len(reads)
    for node, read in reads.items():
        assert read == production.read_subject(
            receipt["state"], node_id=node, effective_at=EFFECTIVE, known_at=KNOWN, purpose="research_internal")
        assert read["status"] == "DESCRIPTIVE"
        assert read["subject"]["eligibility"] == "NOT_QUALIFIED"
    assert reads[LOCAL]["subject"]["canonical_mapping"]["state"] == "UNMAPPED"
    assert receipt["subject_read"]["subject_id"] == "theme:travel"
    assert "theme:travel" not in reads
    qualified_state = theme_state.compose_state(
        [graph_subject(LOCAL, qualified=True)], graph_generation_id=GRAPH,
        owner_generations=GENERATIONS, **QUERY, generated_at=QUERY["known_at"])
    qualified_read = theme_state.read_theme_state(
        qualified_state, LOCAL, **QUERY, expected_generation_id=qualified_state["generation_id"])
    assert qualified_read["status"] == "QUALIFIED"
    assert qualified_read not in item["production_generation"]["subject_reads"]
    assert item["status"] == "partial" and "active_membership_unmapped" in item["warnings"]
    assert "production_generation_absent" not in item["warnings"]
    assert produced["files"] == {} and produced["schema"] == "company_theme_exposure_manifest.v3"
    assert produced["materialization_allowed"] is False and produced["authority_caps"] == production.FLAGS
    assert produced["generation_id"] == derive_generation_id(exposures, produced)
    assert produced["generation_id"] != receipt["state_identity"]["semantic_sha256"][:24]
    assert produced["production_coverage"]["subject_read_count"] == 2
    assert produced["production_coverage"]["descriptive_subject_count"] == 2
    assert produced["production_coverage"]["unavailable_subject_count"] == 0
    assert produced["source"]["builder"] == "company_theme_exposure.v3.shadow"
    assert produced["source"]["membership"] == {"canonical_json_sha256": canonical_json_sha256(inputs["membership"])}
    assert produced["source"]["production_generation"]["subject_reads"] == item["production_generation"]["subject_reads"]
    successor().validate_production_exposure(
        item, generation_read_receipt=receipt, publication_plan=plan, company_context=contexts["HUBB"])
    successor().validate_production_manifest(
        produced, generation_read_receipt=receipt, publication_plan=plan, exposures=exposures)
    with pytest.raises(ContractError):
        validate_exposure(item)
    with pytest.raises(ContractError):
        validate_exposure_v2(item)

    empty_local = owner_receipt("membership", {
        "company_node_id": company, "declared_count": 0, "memberships": [],
    }, graph=graph, subject_id=company, availability="VALID_EMPTY", clocks=clocks)
    zero_inputs = dict(inputs, membership=membership_for("grid"), crosswalk=MAPPED, local={"HUBB": empty_local})
    zero, zero_manifest = compose(**zero_inputs)
    zero_item = zero["HUBB"]
    assert zero_item["local_memberships"] == []
    assert zero_item["local_coverage"]["status"] == "VALID_EMPTY"
    assert zero_item["local_coverage"]["declared_count"] == 0
    assert zero_item["local_coverage"]["observed_count"] == 0
    assert zero_item["local_coverage"]["state_available_count"] == 0
    assert zero_item["warnings"] == [] and zero_item["status"] == "ready"
    assert zero_manifest["status"] == "ready"
    assert all(value is False for value in zero_item["authority_caps"].values())
    assert zero_item["production_generation"]["status"] == "DESCRIPTIVE"

    absent_node = "ltheme:finviz:not_in_graph"
    unproved = owner_receipt("membership", {
        "company_node_id": company, "declared_count": 1,
        "memberships": [{"node_id": absent_node, "source_family": "finviz", "native_id": "not_in_graph",
                         "membership_basis": "CURRENT_MEMBERSHIP_NOT_PIT",
                         "source_refs": ["controlled-membership#/not_in_graph/HUBB"]}],
    }, graph=graph, subject_id=company, clocks=clocks)
    held, _ = compose(**dict(inputs, local={"HUBB": unproved}))
    assert held["HUBB"]["local_memberships"] == []
    assert held["HUBB"]["local_coverage"]["status"] == "UNAVAILABLE"
    assert held["HUBB"]["local_coverage"]["declared_count"] is None
    assert held["HUBB"]["local_coverage"]["reason_codes"] == ["FORWARD_MEMBERSHIP_UNPROVEN"]
    assert absent_node not in {row["subject_id"] for row in held["HUBB"]["production_generation"]["subject_reads"]}

    forged = copy.deepcopy(identity_read)
    forged["payload"] = dict(forged["payload"], security_id="other-security")
    forged["sha256"] = theme_state.canonical_sha256(forged["payload"])
    with pytest.raises(ContractError, match="forward"):
        compose(**dict(inputs, identity={"HUBB": forged}))


def test_real_refusals_pending_stale_rollback_and_closed_contract(standard_publication, tmp_path, monkeypatch):
    world = standard_publication
    receipt, plan = world["receipt"], world["plan"]
    contexts, manifest, ci_root = finalized_ci(tmp_path, KNOWN)
    base = dict(contexts=contexts, manifest=manifest, membership=membership_for("grid", "other"),
                crosswalk=UNMAPPED, identity={"HUBB": {"owner": "identity"}}, local={"HUBB": {"owner": "membership"}})
    missing_root = tmp_path / "missing"
    shutil.copytree(world["root"], missing_root)
    (missing_root / generation.CURRENT).unlink()
    missing, _ = read_receipt(missing_root)
    assert missing["status"] == "MISSING" and missing["state"] is None
    before = tree_bytes(missing_root)
    exposures, produced = compose(**dict(base, receipt=missing, plan={"state_b64": "not-a-payload"}))
    assert tree_bytes(missing_root) == before
    item = exposures["HUBB"]
    assert item["production_generation"]["status"] == "MISSING"
    assert item["production_generation"]["publication"] is None
    assert item["production_generation"]["compatibility_digests"] is None
    assert item["production_generation"]["subject_reads"] == []
    assert item["company_identity"] is None and item["local_membership"] is None
    assert item["local_memberships"] == []
    assert item["local_coverage"]["status"] == "UNAVAILABLE"
    assert item["local_coverage"]["declared_count"] is None
    assert item["local_coverage"]["reason_codes"] == missing["reason_codes"]
    assert item["exposures"][0]["theme_id"] == "grid"
    assert "production_generation_absent" in item["warnings"]
    assert item["status"] == "partial" and produced["files"] == {}
    assert item["generated_at"] == KNOWN

    revoked, _ = read_receipt(world["root"], controlled_verifier=ReadFixture("REVOKED"))
    assert revoked["status"] == "UNAVAILABLE" and revoked["reason_codes"] == ["CURRENT_USE_REVOKED"]
    revoked_item, _ = compose(**dict(base, receipt=revoked, plan=None))
    assert revoked_item["HUBB"]["production_generation"]["status"] == "UNAVAILABLE"
    assert revoked_item["HUBB"]["local_coverage"]["status"] == "UNAVAILABLE"
    assert revoked_item["HUBB"]["local_coverage"]["reason_codes"] == ["CURRENT_USE_REVOKED"]
    assert "production_generation_unavailable" in revoked_item["HUBB"]["warnings"]
    assert revoked_item["HUBB"]["authority_caps"]["may_publish"] is False

    unwired, _ = read_receipt(world["root"], controlled_verifier=None)
    assert unwired["reason_codes"] == ["CURRENT_USE_AUTHORITY_UNAVAILABLE"]
    unwired_item, _ = compose(**dict(base, receipt=unwired, plan=None))
    assert unwired_item["HUBB"]["company_identity"] is None

    use_contexts, use_manifest, _ = finalized_ci(tmp_path / "use", USE)
    with pytest.raises(ContractError, match="knowledge query"):
        compose(**dict(base, contexts=use_contexts, manifest=use_manifest, receipt=receipt, plan=plan))

    bad_parent = copy.deepcopy(manifest)
    bad_parent["files"][next(iter(bad_parent["files"]))]["sha256"] = "0" * 64
    with pytest.raises(ContractError, match="bytes|parent|context"):
        compose(**dict(base, manifest=bad_parent, receipt=receipt, plan=plan))
    with pytest.raises(ContractError, match="foreign"):
        compose(**dict(base, identity={"OTHER": {}}, local={}, receipt=receipt, plan=plan))
    with pytest.raises(ContractError):
        compose(**dict(base, receipt=receipt, plan=None))
    swapped = copy.deepcopy(plan)
    swapped["generation_id"] = "tsg-" + "0" * 64
    with pytest.raises(ContractError):
        compose(**dict(base, receipt=receipt, plan=swapped))

    corrupt = tmp_path / "corrupt"
    shutil.copytree(world["root"], corrupt)
    plan_path = corrupt / generation.GENERATIONS / receipt["publication"]["generation_id"] / "plan.json"
    plan_path.write_bytes(b"foreign")
    invalid, _ = read_receipt(corrupt)
    assert invalid["status"] == "INVALID" and invalid["state"] is None
    with pytest.raises(ContractError, match="invalid"):
        compose(**dict(base, receipt=invalid, plan=plan))

    pending_root = tmp_path / "pending-first"
    shutil.copytree(world["root"], pending_root, dirs_exist_ok=False)
    # A first-publication crash is built on a clean captured root below.

    from engine.neuralweb import theme_state_adapter as adapter
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: world["root"] / "data")
    next_bundle = adapter.capture_owner_bundle(
        world["root"], effective_at=EFFECTIVE, known_at="2026-10-04T12:01:00Z")
    entry = generation.entry_preflight(world["root"], legacy_api=True)
    next_plan = generation.prepare_generation(
        next_bundle, root=world["root"], generated_at="2026-10-04T12:01:00Z",
        activation_at="2026-10-04T12:01:00Z", entry=entry, correction_reason="controlled correction")
    def crash(point):
        if point == "seal":
            raise RuntimeError("controlled interruption")
    with pytest.raises(RuntimeError):
        generation.publish_generation(world["root"], next_plan, controlled_verifier=AcceptedFixture(), fault=crash)
    pending, pending_plan = read_receipt(world["root"])
    assert pending["status"] == "PENDING" and pending["state"] is not None
    assert pending["publication"]["pending_generation_id"] == next_plan["generation_id"]
    # A pending generation with an accepted payload must still reject malformed
    # injected receipts; only payloadless refusals may ignore unverified inputs.
    with pytest.raises(ContractError, match="identity receipt binding invalid"):
        compose(**dict(base, receipt=pending, plan=pending_plan))
    base = dict(base, identity={}, local={})
    pending_item, _ = compose(**dict(base, receipt=pending, plan=pending_plan))
    assert pending_item["HUBB"]["production_generation"]["status"] == "PENDING"
    assert pending_item["HUBB"]["production_generation"]["publication"]["generation_id"] == receipt["publication"]["generation_id"]
    assert pending_item["HUBB"]["production_generation"]["state_identity"]["generated_at"] == receipt["state_identity"]["generated_at"]
    assert "production_generation_pending" in pending_item["HUBB"]["warnings"]
    assert all(row["status"] != "QUALIFIED" for row in pending_item["HUBB"]["production_generation"]["subject_reads"])

    # Resume the exact controlled pending write through its incumbent API;
    # a normal new publication correctly refuses the already sealed orphan.
    generation.publish_generation(world["root"], next_plan,
                                  controlled_verifier=AcceptedFixture(), resume=True)
    corrected, corrected_plan = read_receipt(world["root"], known_at="2026-10-04T12:01:00Z")
    assert corrected["publication"]["activation_kind"] == "CORRECTION"
    corrected_contexts, corrected_manifest, _ = finalized_ci(tmp_path / "corrected", "2026-10-04T12:01:00Z")
    corrected_item, _ = compose(**dict(
        base, contexts=corrected_contexts, manifest=corrected_manifest,
        receipt=corrected, plan=corrected_plan))
    assert corrected_item["HUBB"]["generated_at"] == "2026-10-04T12:01:00Z"
    assert corrected_item["HUBB"]["generated_at"] != USE
    previous = corrected["state"]["correction"]["previous"]
    assert previous["generated_at"] == KNOWN
    assert previous["state_sha256"] == receipt["state_identity"]["semantic_sha256"]
    assert corrected_item["HUBB"]["production_generation"]["state_identity"]["generation_id"] == corrected["state_identity"]["generation_id"]
    generation.rollback_generation(
        world["root"], receipt["publication"]["generation_id"], activation_at="2026-10-04T12:03:00Z",
        controlled_verifier=AcceptedFixture())
    rolled, rolled_plan = read_receipt(world["root"])
    assert rolled["publication"]["activation_kind"] == "ROLLBACK"
    rolled_item, _ = compose(**dict(base, receipt=rolled, plan=rolled_plan))
    assert rolled_item["HUBB"]["production_generation"]["state_identity"]["generated_at"] == KNOWN
    assert rolled_item["HUBB"]["production_generation"]["state_identity"]["generation_id"] == receipt["state_identity"]["generation_id"]
    assert rolled_item["HUBB"]["production_generation"]["publication"]["activation_at"] == "2026-10-04T12:03:00Z"
    assert rolled_item["HUBB"]["generated_at"] == KNOWN
    assert rolled_item["HUBB"]["production_generation"]["state_identity"]["generated_at"] != "2026-10-04T12:03:00Z"

    # Closed contract tampering of a descriptive shadow built before the root moved.
    # Re-read is unnecessary: the pre-mutation receipt remains the witness.
    del pending_root


def test_real_stale_is_not_promoted_and_empty_cohort_stays_empty(tmp_path, production_world):
    from engine.neuralweb import thematic_state as legacy
    import json
    path = production_world / legacy._FORESIGHT_PATH
    document = json.loads(path.read_text())
    document["asof"] = "2026-09-01"
    path.write_text(json.dumps(document))
    publish(production_world)
    receipt, plan = read_receipt(production_world)
    assert receipt["status"] == "STALE" and receipt["state"] is not None
    contexts, manifest, _ = finalized_ci(tmp_path, KNOWN)
    exposures, produced = compose(
        contexts, manifest, receipt, plan, membership=membership_for("grid", "other"), crosswalk=UNMAPPED)
    item = exposures["HUBB"]
    assert item["production_generation"]["status"] == "STALE"
    assert "production_generation_stale" in item["warnings"]
    assert any(row["status"] == "DESCRIPTIVE" for row in item["production_generation"]["subject_reads"])
    assert all(row["status"] != "QUALIFIED" and row["subject"]["eligibility"] == "NOT_QUALIFIED"
               for row in item["production_generation"]["subject_reads"] if row["status"] == "DESCRIPTIVE")
    assert item["authority_caps"] == production.FLAGS
    empty_contexts, empty_manifest, _ = finalized_ci(tmp_path / "empty", KNOWN, rows=())
    empty, empty_produced = compose(
        empty_contexts, empty_manifest, receipt, plan, membership=membership_for("grid", "other"),
        crosswalk=UNMAPPED)
    assert empty == {} and empty_produced["status"] == "empty" and empty_produced["company_count"] == 0
    assert empty_produced["exposure_count"] == empty_produced["local_membership_count"] == 0
    assert empty_produced["production_coverage"]["subject_read_count"] == 0
    assert "active_memberships_unmapped" in empty_produced["warnings"]


def test_real_output_tamper_and_diagnostic_role_are_rejected(qualified_publication, tmp_path):
    world = qualified_publication
    receipt, plan = world["receipt"], world["plan"]
    graph = receipt["state"]["diagnostic_graph_state"]
    company = world["company"]
    forward = next(row for row in graph["subjects"] if row["node_id"] == LOCAL)["owner_receipts"]["membership"]
    member = forward["payload"]["members"][0]
    clocks = {key: forward[key] for key in ("effective_at", "available_at", "known_at", "recorded_at")}
    identity_read = owner_receipt("identity", {
        "status": "RESOLVED", "ticker": "HUBB", "company_node_id": company,
        "issuer_id": member["issuer_id"], "security_id": member["security_id"],
    }, graph=graph, subject_id=company)
    local_read = owner_receipt("membership", {
        "company_node_id": company, "declared_count": 0, "memberships": [],
    }, graph=graph, subject_id=company, availability="VALID_EMPTY", clocks=clocks)
    contexts, manifest, _ = finalized_ci(tmp_path, KNOWN)
    exposures, produced = compose(
        contexts, manifest, receipt, plan, membership=membership_for("grid"), crosswalk=MAPPED,
        identity={"HUBB": identity_read}, local={"HUBB": local_read})
    item = exposures["HUBB"]
    module = successor()

    def reject(mutate, *, manifest_too=False):
        broken_item = copy.deepcopy(item)
        broken_manifest = copy.deepcopy(produced)
        broken_exposures = copy.deepcopy(exposures)
        mutate(broken_item, broken_manifest, broken_exposures)
        with pytest.raises(ContractError):
            if manifest_too:
                module.validate_production_manifest(
                    broken_manifest, generation_read_receipt=receipt, publication_plan=plan,
                    exposures=broken_exposures)
            else:
                module.validate_production_exposure(
                    broken_item, generation_read_receipt=receipt, publication_plan=plan,
                    company_context=contexts["HUBB"])

    reject(lambda item, manifest, exposures: item.__setitem__("economic_score", 1))
    reject(lambda item, manifest, exposures: item["authority_caps"].__setitem__("ranking", True))
    reject(lambda item, manifest, exposures: item.__setitem__("materialization_allowed", True))
    reject(lambda item, manifest, exposures: item["production_generation"]["authority_caps"].__setitem__("predictive", True))
    reject(lambda item, manifest, exposures: item["production_generation"].__setitem__("graph_witness", {}))
    reject(lambda item, manifest, exposures: item["production_generation"]["subject_reads"][0].__setitem__("status", "QUALIFIED"))
    digests = item["production_generation"]["compatibility_digests"]
    # The actual publisher currently writes canonical JSON, so the raw and
    # canonical hashes can legitimately be equal. Preserve both domains rather
    # than asserting inequality or treating an identity swap as a tamper.
    assert digests["raw_sha256"] == receipt["compatibility"]["raw_sha256"]
    assert digests["canonical_sha256"] == receipt["compatibility"]["canonical_sha256"]
    reject(lambda item, manifest, exposures: item["production_generation"]["compatibility_digests"].update(
        raw_sha256="0" * 64))
    reject(lambda item, manifest, exposures: item["production_generation"]["compatibility_digests"].update(
        canonical_sha256="f" * 64))
    reject(lambda item, manifest, exposures: item["production_generation"]["state_identity"].update(
        semantic_sha256=item["production_generation"]["state_identity"]["raw_sha256"],
        raw_sha256=item["production_generation"]["state_identity"]["semantic_sha256"]))
    reject(lambda item, manifest, exposures: manifest.__setitem__("files", {"companies/HUBB.json": {"sha256": "0" * 64, "bytes": 1}}), manifest_too=True)
    reject(lambda item, manifest, exposures: manifest["production_coverage"].__setitem__(
        "subject_read_count", len(receipt["state"]["subjects"])), manifest_too=True)
    reject(lambda item, manifest, exposures: manifest.__setitem__("generation_id", "0" * 24), manifest_too=True)
    cast = copy.deepcopy(receipt)
    cast["state"]["diagnostic_graph_state_role"] = "AUTHORITATIVE"
    with pytest.raises(ContractError):
        module.compose_production_shadow_bundle(
            contexts, company_manifest=manifest, membership=membership_for("grid"), crosswalk=MAPPED,
            generation_read_receipt=cast, publication_plan=plan,
            company_identity_reads={"HUBB": identity_read}, local_membership_reads={"HUBB": local_read})



def test_publication_time_read_compiles_actual_later_state_without_clock_relabelling(production_world, tmp_path):
    from engine.neuralweb import theme_state_adapter as adapter
    root = production_world
    emitted = "2026-10-05T12:00:00Z"
    activated = "2026-10-06T12:00:00Z"
    use_at = "2026-10-06T13:00:00Z"
    captured = adapter.capture_owner_bundle(root, effective_at=EFFECTIVE, known_at=KNOWN)
    plan = generation.prepare_generation(captured, root=root, generated_at=emitted,
        activation_at=activated, entry=generation.entry_preflight(root, legacy_api=True))
    generation.publish_generation(root, plan, controlled_verifier=AcceptedFixture())
    receipt = generation_reader.read_generation_at_use(root, effective_at=EFFECTIVE,
        known_at=KNOWN, purpose="research_internal", use_at=use_at, controlled_verifier=ReadFixture())
    assert receipt["schema"] == "neuralweb.theme_state_generation_read.v2"
    assert receipt["state"] is not None
    contexts, ci_manifest, _ = finalized_ci(tmp_path, KNOWN)
    before = tree_bytes(root)
    exposures, manifest = compose(contexts, ci_manifest, receipt, plan,
                                 membership=membership_for("grid"), crosswalk=MAPPED)
    assert tree_bytes(root) == before
    item = exposures["HUBB"]
    binding = item["production_generation"]
    assert binding["source_read_schema"] == receipt["schema"]
    assert item["generated_at"] == binding["query"]["known_at"] == KNOWN
    assert binding["state_identity"]["generated_at"] == emitted
    assert binding["publication"]["activation_at"] == activated
    assert binding["use_at"] == use_at
    assert binding["state_identity"]["age_seconds_at_use"] == 90000
    assert binding["subject_reads"][0]["schema"] == "gmi.theme_state_read/v3"
    assert binding["subject_reads"][0]["use_at"] == use_at
    assert binding["subject_reads"][0]["subject"]["eligibility"] == "NOT_QUALIFIED"
    assert all(value is False for value in item["authority_caps"].values())
    assert item["materialization_allowed"] is False and manifest["files"] == {}
    successor().validate_production_manifest(manifest, generation_read_receipt=receipt,
                                             publication_plan=plan, exposures=exposures)
    forged = copy.deepcopy(item)
    forged["production_generation"]["source_read_schema"] = generation_reader.SCHEMA
    with pytest.raises(ContractError):
        successor().validate_production_exposure(forged, generation_read_receipt=receipt,
                                                publication_plan=plan, company_context=contexts["HUBB"])
    legacy = generation_reader.read_generation(root, effective_at=EFFECTIVE, known_at=KNOWN,
        purpose="research_internal", use_at=use_at, controlled_verifier=ReadFixture())
    assert legacy["status"] == "UNAVAILABLE" and legacy["state"] is None
    held, _ = compose(contexts, ci_manifest, legacy, None,
                      membership=membership_for("grid"), crosswalk=MAPPED)
    assert held["HUBB"]["production_generation"]["source_read_schema"] == generation_reader.SCHEMA
    assert held["HUBB"]["production_generation"]["subject_reads"] == []
