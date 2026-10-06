"""Controlled real-owner artifacts; no production or natural-use proof.

The LEGACY graph symbol intentionally differs from the Data OS STORE symbol.
A symbol rematch, forged active entity, or issuer/listing collapse must fail here.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.theme_graph import identity_resolution as ir, store, structural_navigation as structural
from engine.theme_graph.ontology import RepositoryStore
from lib import config

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
SEC = "SEC:US-XNAS-AAPL"
NODE = "co:us:LEGACY"
OWNER = {"unmapped_baskets": [{"id": "us_sector_tech", "reason": "Recorded sector context only."}]}
OWNER_SHA = hashlib.sha256(json.dumps(OWNER, sort_keys=True).encode()).hexdigest()


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _node(node_id, kind="company"):
    row = {key: None for key in store.NODE_COLUMNS}
    row.update(node_id=node_id, kind=kind, name_en=node_id, market_scope="us",
               status="canonical", identity_epoch=1, birth_date="2026-06-01",
               computed_at="2026-10-03T10:00:00Z", engine_version=store.ENGINE_VERSION,
               external_ids="{}", source_meta="{}")
    if kind == "basket":
        row["external_ids"] = json.dumps({"suite": "baskets", "basket_id": "us_sector_tech"})
    return row


@pytest.fixture
def owner_root(tmp_path, monkeypatch):
    root = tmp_path / "owner"
    ref = root / "data/reference"
    ref.mkdir(parents=True)
    master = [
        dict(security_id=SEC, listing_key="US-XNAS-AAPL", inception_code="AAPL",
             issuer_id="ISS:US-XNAS-AAPL", issuer_state="RESOLVED",
             security_state=None, superseded_by=None),
        dict(security_id="SEC:US-XNAS-AAPLB", listing_key="US-XNAS-AAPLB", inception_code="AAPLB",
             issuer_id="ISS:US-XNAS-AAPL", issuer_state="RESOLVED",
             security_state=None, superseded_by=None),
    ]
    aliases = [
        dict(vendor="primary", vendor_symbol="LEGACY", security_id=SEC,
             valid_from="2026-01-01", valid_to=None),
        dict(vendor="store", vendor_symbol="CURRENT", security_id=SEC,
             valid_from="2026-01-01", valid_to=None),
        dict(vendor="primary", vendor_symbol="SECOND", security_id="SEC:US-XNAS-AAPLB",
             valid_from="2026-01-01", valid_to=None),
        dict(vendor="store", vendor_symbol="CURRENTB", security_id="SEC:US-XNAS-AAPLB",
             valid_from="2026-01-01", valid_to=None),
    ]
    pd.DataFrame(master).to_parquet(ref / "security_master.parquet", index=False)
    pd.DataFrame(aliases).to_parquet(ref / "vendor_aliases.parquet", index=False)
    _json(ref / "_receipt.json", dict(generated_at="2026-10-04T09:00:00Z",
          symbol_directory_snapshot="2026-10-04", code_version="controlled_owner_fixture"))
    graph = root / "data/theme_graph"
    graph.mkdir(parents=True)
    nodes = [_node(NODE), _node("co:us:SECOND"), _node("basket:baskets:us_sector_tech", "basket"),
             _node("ltheme:finviz:software", "local_theme")]
    pd.DataFrame(nodes, columns=store.NODE_COLUMNS).to_parquet(graph / "nodes.parquet", index=False)
    edge = {key: None for key in store.EDGE_COLUMNS}
    edge.update(edge_id="member:fixture", type="MEMBER_OF", src=NODE,
                dst="basket:baskets:us_sector_tech", valid_from="2026-06-01",
                belief_time="2026-10-03", evidence_time="2026-10-03",
                computed_at="2026-10-03T10:00:00Z")
    pd.DataFrame([edge], columns=store.EDGE_COLUMNS).to_parquet(graph / "edges.parquet", index=False)
    pd.DataFrame(columns=store.NODE_LIFECYCLE_COLUMNS).to_parquet(graph / "node_lifecycle.parquet", index=False)
    (graph / "probation").mkdir()
    (graph / "probation/proposals.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    rows = ir.derive_rows(nodes, resolution_asof="2026-10-04",
                         computed_at="2026-10-04T10:00:00Z",
                         engine_version=store.ENGINE_VERSION, data_dir=root / "data")
    pd.DataFrame(rows, columns=store.IDENTITY_RESOLUTION_COLUMNS).to_parquet(
        graph / "identity_resolution.parquet", index=False)
    _json(root / "data/stage_analysis/screener.json", {
        "schema": "stage_screener.v1", "asof": "2026-10-04",
        "built": "2026-10-04T10:01:00Z", "stage_week_end": "2026-10-02",
        "rows": [dict(ticker=ticker, source="live", industry="Software",
                      stage_current=True, stage_source_asof="2026-10-02",
                      stage_week_end="2026-10-02", retired=False)
                 for ticker in ("CURRENT", "CURRENTB")],
    })
    _json(root / "data/stage_analysis/industry_ranks.json", {
        "schema": "stage_industry_ranks.v1", "asof": "2026-10-04",
        "built": "2026-10-04T10:01:00Z",
        "regions": {"USA": [{"industry_id": "Software", "industry_name": "Software"}]},
    })
    _json(root / "config/theme_crosswalk.yml", OWNER)
    monkeypatch.setattr(structural, "CROSSWALK_PATH", root / "config/theme_crosswalk.yml")

    # Existing owner clocks only. No replacement identity or Stage result is injected.
    from engine.intelligence_workspace import entity, resolver
    class FixedDate(date):
        @classmethod
        def today(cls):
            return NOW.date()
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz else NOW.replace(tzinfo=None)
    monkeypatch.setattr(entity, "date", FixedDate)
    monkeypatch.setattr(resolver, "datetime", FixedDatetime)
    monkeypatch.setattr(ir, "_utc_now_stamp", lambda: NOW.isoformat())
    monkeypatch.setattr(ir, "datetime", FixedDatetime)
    monkeypatch.setattr(structural, "_repo_root", lambda: root, raising=False)
    monkeypatch.setattr(structural, "_utc_now", lambda: NOW, raising=False)
    return root


def _compose(*, node=NODE, day="2026-10-04", cutoff=None):
    compose = getattr(structural, "compose_structure_v2", None)
    assert callable(compose), "versioned actual-owner structural composition is missing"
    return compose(RepositoryStore(), node_id=node, asof=day,
                   knowledge_cutoff=cutoff or day, owner_document=OWNER, owner_sha256=OWNER_SHA)


def _change(root, path, change):
    p = root / path
    doc = json.loads(p.read_text())
    change(doc)
    _json(p, doc)


def _identity_change(root, change):
    p = root / "data/theme_graph/identity_resolution.parquet"
    rows = pd.read_parquet(p).to_dict("records")
    change(next(row for row in rows if row["node_id"] == NODE))
    pd.DataFrame(rows, columns=store.IDENTITY_RESOLUTION_COLUMNS).to_parquet(p, index=False)


def test_actual_owner_chain_retains_graph_security_listing_and_sector_context(owner_root):
    result = _compose()
    assert result["schema"] == "gmi.theme_structural_context/v2"
    fact = result["owner_structure"]
    assert fact["availability"] == {"state": "AVAILABLE", "reason_codes": []}
    assert fact["identity"]["node_id"] == NODE
    assert fact["identity"]["security_id"] == SEC
    assert fact["identity"]["listing_key"] == "US-XNAS-AAPL"
    assert fact["industry_reference"]["target"] == {"type": "industry", "id": "Software", "universe": "us_industry"}
    assert result["context_v1"]["counts"]["sector_references"] == 1
    assert result["context_v1"]["coverage"]["industry"]["state"] == "OWNER_NOT_BOUND"
    assert result["subindustry"]["state"] == "OWNER_NOT_BOUND"
    assert result["use_qualification"]["status"] == "NOT_QUALIFIED"
    assert result["use_qualification"]["rights_state"] == "OWNER_NOT_BOUND"
    assert not any(result["authority_flags"].values())


def test_nullable_issuer_does_not_erase_valid_security(owner_root):
    p = owner_root / "data/reference/security_master.parquet"
    rows = pd.read_parquet(p)
    rows.loc[rows.security_id == SEC, "issuer_state"] = "NO_ISSUER_EVIDENCE"
    rows.to_parquet(p, index=False)
    _identity_change(owner_root, lambda row: row.update(issuer_id=None))
    result = _compose()["owner_structure"]
    assert result["availability"]["state"] == "AVAILABLE"
    assert result["identity"]["security_id"] == SEC
    assert result["identity"]["issuer_id"] is None
    assert result["industry_reference"]["security_id"] == SEC


def test_shared_issuer_preserves_two_security_relationships(owner_root):
    a, b = _compose()["owner_structure"], _compose(node="co:us:SECOND")["owner_structure"]
    assert a["availability"]["state"] == b["availability"]["state"] == "AVAILABLE"
    assert a["identity"]["issuer_id"] == b["identity"]["issuer_id"] == "ISS:US-XNAS-AAPL"
    assert a["identity"]["security_id"] != b["identity"]["security_id"]
    assert a["identity"]["listing_key"] != b["identity"]["listing_key"]


@pytest.mark.parametrize("damage", ["node", "security", "listing", "issuer", "ambiguous", "missing_security"])
def test_identity_contradictions_cannot_qualify(owner_root, damage, monkeypatch):
    changes = {
        "node": {"node_id": "co:us:OTHER"},
        "security": {"security_id": "SEC:US-XNAS-AAPLB", "listing_key": "US-XNAS-AAPLB"},
        "listing": {"listing_key": "US-XNYS-AAPL"},
        "issuer": {"issuer_id": "ISS:US-XNAS-AAPLB"},
        "ambiguous": {"resolution_state": "AMBIGUOUS"},
        "missing_security": {"security_id": None},
    }
    if damage == "node":
        # A missing cache row may legitimately be recomputed by the incumbent bridge.
        # Challenge a contradictory returned owner row, not that supported fallback.
        real_read = ir.resolve_graph_node_identity
        def wrong_subject(*args, **kwargs):
            row = real_read(*args, **kwargs)
            return {**row, **changes[damage]}
        monkeypatch.setattr(ir, "resolve_graph_node_identity", wrong_subject)
    else:
        _identity_change(owner_root, lambda row: row.update(changes[damage]))
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["availability"]["reason_codes"]
    assert fact["industry_reference"] is None


@pytest.mark.parametrize("damage", ["missing", "duplicate", "stale", "unknown", "retired", "target_missing", "target_unknown"])
def test_stage_owner_refusals_do_not_become_absence_or_classification(owner_root, damage):
    def change(doc):
        row = doc["rows"][0]
        if damage == "missing": doc["rows"] = doc["rows"][1:]
        elif damage == "duplicate": doc["rows"].append(copy.deepcopy(row))
        elif damage == "stale": row["stage_current"] = False
        elif damage == "unknown": row.pop("stage_current")
        elif damage == "retired": row["retired"] = True
        elif damage == "target_missing": row["industry"] = None
        elif damage == "target_unknown": row["industry"] = "Unregistered industry"
    _change(owner_root, "data/stage_analysis/screener.json", change)
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["availability"]["reason_codes"]
    assert fact["industry_reference"] is None


@pytest.mark.parametrize("damage", ["superseded", "retired", "missing"])
def test_current_dataos_state_is_rechecked_after_bridge_read(owner_root, damage):
    p = owner_root / "data/reference/security_master.parquet"
    rows = pd.read_parquet(p)
    if damage == "missing": rows = rows[rows.security_id != SEC]
    elif damage == "superseded":
        rows.loc[rows.security_id == SEC, "security_state"] = "SUPERSEDED_DUPLICATE_MINT"
        rows.loc[rows.security_id == SEC, "superseded_by"] = "SEC:US-XNAS-AAPLB"
    else: rows.loc[rows.security_id == SEC, "security_state"] = "UNSUPPORTED_TERMINAL_STATE"
    rows.to_parquet(p, index=False)
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["industry_reference"] is None


@pytest.mark.parametrize("node", ["basket:baskets:us_sector_tech", "ltheme:finviz:software"])
def test_noncompany_keeps_context_without_aggregating_member_industries(owner_root, node):
    result = _compose(node=node)
    assert result["owner_structure"]["availability"]["state"] == "UNSUPPORTED_SUBJECT"
    assert result["owner_structure"]["identity"] is None
    assert result["owner_structure"]["industry_reference"] is None
    assert result["context_v1"]["neighborhood"]["node_id"] == node


@pytest.mark.parametrize("day,cutoff", [("2026-10-03", "2026-10-04"), ("2026-10-04", "2026-10-03"),
                                      ("2026-10-05", "2026-10-05")])
def test_historical_and_future_requests_cannot_use_current_owner_catalog(owner_root, day, cutoff):
    fact = _compose(day=day, cutoff=cutoff)["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert "CURRENT_ONLY_QUERY_REQUIRED" in fact["availability"]["reason_codes"]
    assert fact["industry_reference"] is None


@pytest.mark.parametrize("field,value", [("built", "2026-10-04T12:00:01Z"),
                                         ("built", "2026-10-04"),
                                         ("built", None), ("asof", "2026-10-03"),
                                         ("stage_week_end", "2026-10-09")])
def test_future_stale_unknown_and_date_only_emission_clocks_refuse(owner_root, field, value):
    _change(owner_root, "data/stage_analysis/screener.json", lambda doc: doc.update({field: value}))
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["industry_reference"] is None


def test_date_only_classifier_clock_is_disclosed_not_first_known(owner_root):
    ref = _compose()["owner_structure"]["industry_reference"]
    assert ref["owner_relationship"]["observed_at"] == "2026-10-02"
    assert ref["historical_classification_claim"] is False
    assert ref["classification_first_known_at"] is None


def test_input_bytes_are_separate_observation_and_read_does_not_write(owner_root):
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in owner_root.rglob("*") if p.is_file()}
    result = _compose()
    observed = result["owner_structure"]["input_observation"]
    assert observed["consumed_bytes_proven"] is False
    assert observed["basis"] == "SEPARATELY_OBSERVED_BEFORE_AFTER_OWNER_READ"
    assert observed["artifacts"]["data/stage_analysis/screener.json"]["sha256"] == before[
        str(owner_root / "data/stage_analysis/screener.json")]
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in owner_root.rglob("*") if p.is_file()}


def test_default_cli_remains_v1_and_versioned_opt_in_is_explicit(owner_root, capsys):
    from scripts import query_theme_ontology as cli
    common = ["--node-id", NODE, "--structure", "--asof", "2026-10-04"]
    assert cli.main(common) == 0
    v1 = json.loads(capsys.readouterr().out)
    assert v1["schema"] == "gmi.theme_structural_context/v1"
    assert v1["coverage"]["industry"]["state"] == "OWNER_NOT_BOUND"
    assert cli.main(common + ["--structure-version", "v2"]) == 0
    v2 = json.loads(capsys.readouterr().out)
    assert v2["context_v1"] == v1
    assert v2["owner_structure"]["availability"]["state"] == "AVAILABLE"


def test_versioned_owner_route_requires_structure_and_has_no_source_path_override(owner_root, capsys):
    from scripts import query_theme_ontology as cli
    assert cli.main(["--node-id", NODE, "--asof", "2026-10-04", "--structure-version", "v2"]) == 2
    assert "ONTOLOGY_QUERY_UNAVAILABLE" in capsys.readouterr().err


@pytest.mark.parametrize("field,value", [
    ("computed_at", "2026-10-04T12:00:01Z"),
    ("computed_at", "2026-10-04"),
    ("computed_at", "2026-10-04T08:00:00Z"),
    ("computed_at", "2026-10-03T10:00:00Z"),
    ("refusal_reason", "owner_refused"),
])
def test_identity_clock_and_disposition_cannot_contradict_positive(owner_root, field, value):
    _identity_change(owner_root, lambda row: row.update({field: value}))
    assert _compose()["owner_structure"]["availability"]["state"] == "UNAVAILABLE"


@pytest.mark.parametrize("damage", [
    "from", "schema", "source", "registry", "generated_future",
    "generated_naive", "generated_date", "extra", "audience", "use", "issues", "fingerprint",
])
def test_actual_owner_receipt_contradictions_rehashed_cannot_qualify(owner_root, monkeypatch, damage):
    from engine.intelligence_workspace.resolver import DatapointResolver
    from engine.intelligence_workspace.contracts import canonical_json_sha256
    real_read = DatapointResolver.resolve_current_industry_relationship
    def damaged(self, entity):
        receipt = real_read(self, entity)
        if damage == "from": receipt["from"]["id"] = "SEC:US-XNAS-AAPLB"
        elif damage == "schema": receipt["schema"] = "unaccepted.v1"
        elif damage == "source": receipt["source"]["owner"] = "unbound"
        elif damage == "registry": receipt["registry_digest"] = "0" * 64
        elif damage == "generated_future": receipt["generated_at"] = "2026-10-04T12:00:01Z"
        elif damage == "generated_naive": receipt["generated_at"] = "2026-10-04T10:00:00"
        elif damage == "generated_date": receipt["generated_at"] = "2026-10-04"
        elif damage == "extra": receipt["authorized"] = True
        elif damage == "audience": receipt["audience"] = "public"
        elif damage == "use": receipt["consumer_use"] = "predictive"
        elif damage == "issues": receipt["quality"]["issues"] = ["unresolved_contradiction"]
        if damage == "fingerprint": receipt["relationship_fingerprint"] = "0" * 64
        else:
            receipt["relationship_fingerprint"] = canonical_json_sha256({
                k: v for k, v in receipt.items()
                if k not in {"generated_at", "relationship_fingerprint"}
            })
        return receipt
    monkeypatch.setattr(DatapointResolver, "resolve_current_industry_relationship", damaged)
    result = _compose()
    assert result["owner_structure"]["availability"]["state"] == "UNAVAILABLE"
    assert result["owner_structure"]["industry_reference"] is None
    assert result["use_qualification"]["authorized_uses"] == []


def test_input_changed_during_actual_owner_read_refuses(owner_root, monkeypatch):
    from engine.intelligence_workspace.resolver import DatapointResolver
    real_read = DatapointResolver.resolve_current_industry_relationship
    def changed(self, entity):
        receipt = real_read(self, entity)
        _change(owner_root, "data/stage_analysis/screener.json",
                lambda doc: doc.update({"extra_observation": "changed after owner read"}))
        return receipt
    monkeypatch.setattr(DatapointResolver, "resolve_current_industry_relationship", changed)
    fact = _compose()["owner_structure"]
    assert fact["availability"] == {"state": "UNAVAILABLE", "reason_codes": ["OWNER_INPUT_CHANGED_DURING_READ"]}
    assert fact["industry_reference"] is None


def test_valid_security_identity_survives_missing_stage_fact(owner_root):
    _change(owner_root, "data/stage_analysis/screener.json",
            lambda doc: doc.update({"rows": doc["rows"][1:]}))
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["identity"]["security_id"] == SEC
    assert fact["industry_reference"] is None


def test_missing_sidecar_uses_incumbent_current_owner_fallback(owner_root):
    (owner_root / "data/theme_graph/identity_resolution.parquet").unlink()
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "AVAILABLE"
    assert fact["identity"]["security_id"] == SEC
    assert fact["input_observation"]["artifacts"]["data/theme_graph/identity_resolution.parquet"]["state"] == "MISSING"


@pytest.mark.parametrize("license_class", ["internal_derived", "unknown", "revoked"])
def test_owner_license_label_cannot_grant_a_use(owner_root, monkeypatch, license_class):
    from engine.intelligence_workspace.resolver import DatapointResolver
    from engine.intelligence_workspace.contracts import canonical_json_sha256
    real_read = DatapointResolver.resolve_current_industry_relationship
    def labelled(self, entity):
        receipt = real_read(self, entity)
        receipt["source"]["license_class"] = license_class
        receipt["relationship_fingerprint"] = canonical_json_sha256({
            k: v for k, v in receipt.items()
            if k not in {"generated_at", "relationship_fingerprint"}
        })
        return receipt
    monkeypatch.setattr(DatapointResolver, "resolve_current_industry_relationship", labelled)
    result = _compose()
    assert result["use_qualification"]["status"] == "NOT_QUALIFIED"
    assert result["use_qualification"]["authorized_uses"] == []
    assert not result["use_qualification"]["public_display"]
    assert not result["use_qualification"]["machine_qualified"]
    assert not result["use_qualification"]["predictive_use"]


def test_v2_has_no_injected_identity_relationship_or_qualification_reader(owner_root):
    with pytest.raises(TypeError):
        structural.compose_structure_v2(RepositoryStore(), node_id=NODE, asof="2026-10-04",
                                       owner_relationship={"authorized": True})


@pytest.mark.parametrize("damage", ["source_type", "provenance_type", "freshness_type", "quality_type"])
def test_malformed_nested_owner_result_is_a_typed_refusal(owner_root, monkeypatch, damage):
    from engine.intelligence_workspace.resolver import DatapointResolver
    from engine.intelligence_workspace.contracts import canonical_json_sha256
    real_read = DatapointResolver.resolve_current_industry_relationship
    def malformed(self, entity):
        receipt = real_read(self, entity)
        receipt[damage.removesuffix("_type")] = ["malformed"]
        receipt["relationship_fingerprint"] = canonical_json_sha256({
            k: v for k, v in receipt.items()
            if k not in {"generated_at", "relationship_fingerprint"}
        })
        return receipt
    monkeypatch.setattr(DatapointResolver, "resolve_current_industry_relationship", malformed)
    fact = _compose()["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["availability"]["reason_codes"]
    assert fact["industry_reference"] is None


def _wire_validator():
    import jsonschema
    from referencing import Registry, Resource
    root = Path(__file__).resolve().parents[1] / "contracts/theme_graph"
    registry = Registry()
    for name in ("ontology_neighborhood.v1.schema.json", "structural_context.v1.schema.json",
                 "identity_resolution.v1.schema.json"):
        schema = json.loads((root / name).read_text())
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    schema = json.loads((root / "theme_structural_context.v2.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema, registry=registry,
                                          format_checker=jsonschema.FormatChecker())


@pytest.mark.parametrize("node", [NODE, "basket:baskets:us_sector_tech"])
def test_closed_versioned_wire_validates_actual_output(owner_root, node):
    _wire_validator().validate(_compose(node=node))


@pytest.mark.parametrize("damage", ["grant", "predictive", "extra", "available_without_reference", "consumed_claim"])
def test_closed_versioned_wire_cannot_accept_false_authority_or_input_proof(owner_root, damage):
    import jsonschema
    result = _compose()
    _wire_validator().validate(result)  # Reject the alteration, not an invalid baseline fixture.
    if damage == "grant": result["use_qualification"]["authorized_uses"] = ["research_internal"]
    elif damage == "predictive": result["authority_flags"]["predictive_use"] = True
    elif damage == "extra": result["approved"] = True
    elif damage == "available_without_reference": result["owner_structure"]["industry_reference"] = None
    else: result["owner_structure"]["input_observation"]["consumed_bytes_proven"] = True
    with pytest.raises(jsonschema.ValidationError):
        _wire_validator().validate(result)


def test_non_us_company_is_explicitly_unsupported_without_owner_inference(owner_root):
    p = owner_root / "data/theme_graph/nodes.parquet"
    rows = pd.read_parquet(p)
    row = _node("co:cn:600000")
    row["market_scope"] = "cn"
    pd.concat([rows, pd.DataFrame([row])], ignore_index=True).to_parquet(p, index=False)
    result = _compose(node="co:cn:600000")
    assert result["owner_structure"]["availability"]["state"] == "UNSUPPORTED_SUBJECT"
    assert result["owner_structure"]["identity"] is None
    assert result["owner_structure"]["industry_reference"] is None
    assert result["context_v1"]["neighborhood"]["subject"]["market_scope"] == "cn"


@pytest.mark.parametrize("field,value", [
    ("generated_at", "2026-10-04T12:00:01Z"),
    ("generated_at", "2026-10-04"),
    ("generated_at", None),
    ("symbol_directory_snapshot", "2026-10-05"),
])
def test_dataos_source_clock_damage_is_unavailable(owner_root, field, value):
    _change(owner_root, "data/reference/_receipt.json", lambda doc: doc.update({field: value}))
    result = _compose()
    assert result["owner_structure"]["availability"]["state"] == "UNAVAILABLE"
    assert result["owner_structure"]["industry_reference"] is None
    _wire_validator().validate(result)


def test_unknown_subject_retains_existing_genuine_absence(owner_root):
    result = _compose(node="co:us:NOT_IN_GRAPH")
    assert result["owner_structure"]["availability"] == {
        "state": "UNAVAILABLE", "reason_codes": ["SUBJECT_UNAVAILABLE"],
    }
    assert result["owner_structure"]["identity"] is None
    assert result["context_v1"]["neighborhood"]["subject"] is None
    _wire_validator().validate(result)


def test_versioned_markdown_discloses_source_fact_and_unqualified_use(owner_root, capsys):
    from scripts import query_theme_ontology as cli
    assert cli.main(["--node-id", NODE, "--structure", "--structure-version", "v2",
                     "--asof", "2026-10-04", "--format", "markdown"]) == 0
    text = capsys.readouterr().out
    assert "AVAILABLE" in text and SEC in text and "Software" in text
    assert "NOT_QUALIFIED" in text and "OWNER_NOT_BOUND" in text


def test_reader_clock_regression_cannot_leave_a_positive_reference(owner_root, monkeypatch):
    from datetime import timedelta
    # The first four calls cover start, owner generation and both artifact emissions.
    # Regression only at final readback must not leave an available fact.
    clocks = iter([NOW, NOW, NOW, NOW, NOW - timedelta(seconds=1)])
    monkeypatch.setattr(structural, "_utc_now", lambda: next(clocks))
    result = _compose()
    assert result["owner_structure"]["availability"] == {
        "state": "UNAVAILABLE", "reason_codes": ["READER_CLOCK_REGRESSED"],
    }
    assert result["owner_structure"]["industry_reference"] is None


# P2 successor repairs: fixed-owner artifact shape and portable wire syntax.
@pytest.mark.parametrize("damage", [
    "top_array", "regions_array", "regions_null", "regions_missing",
    "usa_object", "usa_null", "usa_missing",
])
def test_p2_industry_registry_shapes_refuse_before_target_normalizer(owner_root, monkeypatch, damage):
    from engine.intelligence_workspace.entity import DataOSIdentityNormalizer
    path = owner_root / "data/stage_analysis/industry_ranks.json"
    document = json.loads(path.read_text())
    if damage == "top_array": document = []
    elif damage == "regions_array": document["regions"] = [{}]
    elif damage == "regions_null": document["regions"] = None
    elif damage == "regions_missing": document.pop("regions")
    elif damage == "usa_object": document["regions"]["USA"] = {}
    elif damage == "usa_null": document["regions"]["USA"] = None
    else: document["regions"].pop("USA")
    _json(path, document)
    target_requests = []
    original = DataOSIdentityNormalizer.normalize_many
    def tracked(self, entities):
        target_requests.extend(e.id for e in entities if e.type == "industry")
        return original(self, entities)
    monkeypatch.setattr(DataOSIdentityNormalizer, "normalize_many", tracked)
    result = _compose()
    fact = result["owner_structure"]
    assert fact["availability"]["state"] == "UNAVAILABLE"
    assert fact["availability"]["reason_codes"]
    assert fact["industry_reference"] is None
    assert target_requests == [], "malformed registry must refuse before target normalization"
    assert result["use_qualification"]["status"] == "NOT_QUALIFIED"
    assert result["use_qualification"]["rights_state"] == "OWNER_NOT_BOUND"
    assert result["use_qualification"]["authorized_uses"] == []
    assert not any(result["authority_flags"].values())
    assert not any(result["use_qualification"][k] for k in
                   ["public_display", "machine_qualified", "predictive_use"])
    _wire_validator().validate(result)


def test_p2_empty_usa_registry_preserves_existing_unregistered_target_refusal(owner_root):
    _change(owner_root, "data/stage_analysis/industry_ranks.json",
            lambda document: document["regions"].update(USA=[]))
    result = _compose()
    assert result["owner_structure"]["availability"]["state"] == "UNAVAILABLE"
    assert result["owner_structure"]["industry_reference"] is None
    assert not any(result["authority_flags"].values())


_P2_TIMESTAMP_PATHS = [
    ("read_clock", "started_at"),
    ("read_clock", "finished_at"),
    ("owner_structure", "identity", "computed_at"),
    ("owner_structure", "identity", "master_generated_at"),
    ("owner_structure", "industry_reference", "owner_relationship", "generated_at"),
    ("owner_structure", "industry_reference", "owner_relationship", "observed_at"),
    ("owner_structure", "industry_reference", "owner_relationship", "effective_at"),
]


@pytest.mark.parametrize("path", _P2_TIMESTAMP_PATHS)
@pytest.mark.parametrize("value", ["nonsenseTZ", "prefix2026-10-04T10:00:00Z",
                                   "2026-10-04T10:00:00Z\n"])
def test_p2_timestamp_syntax_refuses_without_optional_checker(owner_root, path, value):
    import jsonschema
    validator = _wire_validator().evolve(format_checker=None)
    assert validator.format_checker is None
    result = _compose()
    validator.validate(result)
    target = result
    for part in path[:-1]: target = target[part]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(result)


@pytest.mark.parametrize("path", _P2_TIMESTAMP_PATHS)
@pytest.mark.parametrize("value", ["2026-10-04T10:00:00Z",
                                   "2026-10-04T10:00:00.123456Z",
                                   "2026-10-04T15:30:00+05:30",
                                   "2026-10-04T03:00:00.123456789-07:00"])
def test_p2_timestamp_syntax_preserves_precise_owner_forms_without_checker(owner_root, path, value):
    validator = _wire_validator().evolve(format_checker=None)
    result = _compose()
    target = result
    for part in path[:-1]: target = target[part]
    target[path[-1]] = value
    validator.validate(result)


@pytest.mark.parametrize("field", ["observed_at", "effective_at"])
def test_p2_timestamp_alternative_retains_owner_date_grain_without_checker(owner_root, field):
    result = _compose()
    result["owner_structure"]["industry_reference"]["owner_relationship"][field] = "2026-10-02"
    _wire_validator().evolve(format_checker=None).validate(result)
