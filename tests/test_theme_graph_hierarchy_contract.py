"""W-C1 hierarchy contract fixtures — positive path and one test per refusal."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from engine.theme_graph import store
from scripts import check_theme_graph_contracts as guard

STAMP = "2024-01-02T00:00:00Z"
EV_CROSSWALK = "ev:00000000000000bb"
CROSSWALK_PROV = guard.CROSSWALK_NODE_PROVENANCE


def _evidence(**over) -> dict:
    row = {
        "evidence_id": EV_CROSSWALK, "kind": "operator_curation",
        "published_at": "2024-01-01", "effective_at": None,
        "source_ref": "config/theme_crosswalk.yml#hierarchy:test",
        "licensing_internal_ok": True, "licensing_display_ok": True,
        "licensing_redistribution_ok": True, "retention": None,
        "computed_at": STAMP, "provider": None, "claim_type": None,
    }
    row.update(over)
    return row


def _theme_node(node_id: str, tier: str, **over) -> dict:
    row = {
        "node_id": node_id, "kind": "theme", "name_en": "T", "name_zh": None,
        "market_scope": "global", "tier": tier, "status": "canonical",
        "merged_into": None, "birth_date": None, "retire_date": None,
        "identity_epoch": 1, "external_ids": "{}", "provenance": CROSSWALK_PROV,
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
        "source_meta": None,
    }
    row.update(over)
    return row


def _parent_of(src: str, dst: str, valid_from: str = "2024-01-01", **over) -> dict:
    row = {
        "edge_id": f"parent_of:{src}->{dst}@{valid_from}",
        "type": "PARENT_OF", "src": src, "dst": dst,
        "valid_from": valid_from, "valid_to": None,
        "evidence_time": valid_from, "belief_time": "2024-01-02",
        "era": "reconstruction", "source_class": "curated",
        "date_provenance": "crosswalk", "evidence_refs": [EV_CROSSWALK],
        "confidence_basis": "crosswalk.v1",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
    }
    for f in store.RESERVED_EDGE_FIELDS:
        row[f] = None
    row.update(over)
    return row


def _write_store(root: Path, *, nodes, edges, evidence) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rows, cols, name in (
            (nodes, store.NODE_COLUMNS, "nodes"),
            (edges, store.EDGE_COLUMNS, "edges"),
            (evidence, store.EVIDENCE_COLUMNS, "evidence"),
    ):
        pd.DataFrame(rows).reindex(columns=list(cols)).to_parquet(
            root / f"{name}.parquet", index=False)
    return root


def _hierarchy_chain_nodes_edges():
    nodes = [
        _theme_node("theme:cat_h", "macro_category"),
        _theme_node("theme:mid_h", "theme"),
        _theme_node("theme:micro_h", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat_h", "theme:mid_h"),
        _parent_of("theme:mid_h", "theme:micro_h", valid_from="2024-01-02"),
    ]
    evidence = [_evidence()]
    return nodes, edges, evidence


@pytest.fixture
def breaks(tmp_path) -> Path:
    p = tmp_path / "breaks.yml"
    p.write_text("breaks: []\n", encoding="utf-8")
    return p


def _hierarchy_breaches(root: Path, breaks_file: Path) -> list[str]:
    return [b for b in guard.audit(root, breaks_file)[0] if b.startswith("hierarchy:")]


def test_hierarchy_valid_chain_has_no_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    root = _write_store(tmp_path / "ok", nodes=nodes, edges=edges, evidence=ev)
    assert _hierarchy_breaches(root, breaks) == []


def test_theme_node_null_tier_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes[1]["tier"] = None
    root = _write_store(tmp_path / "null_tier", nodes=nodes, edges=edges, evidence=ev)
    assert any("kind=theme requires tier" in x for x in _hierarchy_breaches(root, breaks))


def test_company_node_with_tier_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes.append({
        "node_id": "co:us:ZZZ", "kind": "company", "name_en": None, "name_zh": None,
        "market_scope": "us", "tier": "theme", "status": "canonical",
        "merged_into": None, "birth_date": None, "retire_date": None,
        "identity_epoch": 1, "external_ids": "{}", "provenance": "fixture",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
    })
    root = _write_store(tmp_path / "co_tier", nodes=nodes, edges=edges, evidence=ev)
    assert any("must have tier null" in x for x in _hierarchy_breaches(root, breaks))


def test_bogus_tier_string_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes[0]["tier"] = "sector"
    root = _write_store(tmp_path / "bogus", nodes=nodes, edges=edges, evidence=ev)
    assert any("kind=theme requires tier" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_missing_endpoint_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges[0]["src"] = "theme:missing_cat"
    edges[0]["edge_id"] = "parent_of:theme:missing_cat->theme:mid_h@2024-01-01"
    root = _write_store(tmp_path / "missing", nodes=nodes, edges=edges, evidence=ev)
    bs = guard.audit(root, breaks)[0]
    assert any("hierarchy:" in x and "kind=theme" in x for x in bs)


def test_parent_of_basket_endpoint_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes.append({
        "node_id": "basket:baskets:demo", "kind": "basket", "name_en": None,
        "name_zh": None, "market_scope": "us", "tier": None, "status": "canonical",
        "merged_into": None, "birth_date": None, "retire_date": None,
        "identity_epoch": 1, "external_ids": "{}", "provenance": "fixture",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
    })
    edges[0]["dst"] = "basket:baskets:demo"
    edges[0]["edge_id"] = "parent_of:theme:cat_h->basket:baskets:demo@2024-01-01"
    root = _write_store(tmp_path / "basket_dst", nodes=nodes, edges=edges, evidence=ev)
    assert any("kind=theme" in x for x in _hierarchy_breaches(root, breaks))


def test_macro_category_to_micro_theme_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges.append(_parent_of("theme:cat_h", "theme:micro_h"))
    root = _write_store(tmp_path / "cat_micro", nodes=nodes, edges=edges, evidence=ev)
    assert any("adjacency" in x for x in _hierarchy_breaches(root, breaks))


def test_theme_to_theme_parent_of_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes.append(_theme_node("theme:peer", "theme"))
    edges.append(_parent_of("theme:mid_h", "theme:peer", valid_from="2024-01-03"))
    root = _write_store(tmp_path / "theme_theme", nodes=nodes, edges=edges, evidence=ev)
    assert any("adjacency" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_two_cycle_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes.append(_theme_node("theme:cycle_x", "theme"))
    nodes.append(_theme_node("theme:cycle_y", "theme"))
    edges.append(_parent_of("theme:cycle_x", "theme:cycle_y", valid_from="2024-01-03"))
    edges.append(_parent_of("theme:cycle_y", "theme:cycle_x", valid_from="2024-01-03"))
    root = _write_store(tmp_path / "cycle", nodes=nodes, edges=edges, evidence=ev)
    bs = _hierarchy_breaches(root, breaks)
    assert any("cycle" in x for x in bs)
    assert any("adjacency" in x for x in bs)


def test_parent_of_empty_evidence_refs_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges[0]["evidence_refs"] = []
    root = _write_store(tmp_path / "empty_ev_refs", nodes=nodes, edges=edges, evidence=ev)
    assert any(
        "carries no evidence_refs" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_dangling_evidence_ref_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    good_ref = edges[0]["evidence_refs"][0]
    edges[0]["evidence_refs"] = [good_ref, "ev:doesnotexist999"]
    root = _write_store(tmp_path / "dangling_ev", nodes=nodes, edges=edges, evidence=ev)
    bs = _hierarchy_breaches(root, breaks)
    assert any("does not resolve" in x for x in bs)
    assert not any(good_ref in x for x in bs)


def test_nodes_without_tier_column_breach(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    root = tmp_path / "no_tier_col"
    root.mkdir(parents=True, exist_ok=True)
    node_cols = [c for c in store.NODE_COLUMNS if c != "tier"]
    pd.DataFrame(nodes).reindex(columns=node_cols).to_parquet(
        root / "nodes.parquet", index=False)
    pd.DataFrame(edges).reindex(columns=list(store.EDGE_COLUMNS)).to_parquet(
        root / "edges.parquet", index=False)
    pd.DataFrame(ev).reindex(columns=list(store.EVIDENCE_COLUMNS)).to_parquet(
        root / "evidence.parquet", index=False)
    theme_ids = {n["node_id"] for n in nodes if n.get("kind") == "theme"}
    bs = _hierarchy_breaches(root, breaks)
    tier_breaches = [x for x in bs if "requires tier" in x]
    assert len(tier_breaches) == len(theme_ids)
    for nid in theme_ids:
        assert any(nid in x for x in tier_breaches)


def test_mastermind_curated_emission_disallowed_breaches(tmp_path, breaks, monkeypatch):
    monkeypatch.setattr(
        guard.rights, "emission_allowed", lambda fam: fam != "mastermind_curated")
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    root = _write_store(tmp_path / "emission_off", nodes=nodes, edges=edges, evidence=ev)
    assert any(
        "emission_allowed('mastermind_curated') is false" in x
        for x in _hierarchy_breaches(root, breaks))


def test_four_parents_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    for i in range(3):
        cid = f"theme:cat_{i}"
        nodes.append(_theme_node(cid, "macro_category"))
        edges.append(_parent_of(cid, "theme:mid_h", valid_from=f"2024-01-{10+i:02d}"))
    root = _write_store(tmp_path / "four_parents", nodes=nodes, edges=edges, evidence=ev)
    assert any("has 4 open parents" in x for x in _hierarchy_breaches(root, breaks))


def test_three_parents_no_cap_breach(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    for i in range(2):
        cid = f"theme:cat_{i}"
        nodes.append(_theme_node(cid, "macro_category"))
        edges.append(_parent_of(cid, "theme:mid_h", valid_from=f"2024-01-{10+i:02d}"))
    root = _write_store(tmp_path / "three_parents", nodes=nodes, edges=edges, evidence=ev)
    assert not any("open parents" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_scrape_source_class_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges[0]["source_class"] = "scrape"
    root = _write_store(tmp_path / "scrape", nodes=nodes, edges=edges, evidence=ev)
    assert any("source_class=curated" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_raw_snapshot_provenance_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges[0]["date_provenance"] = "raw_snapshot"
    root = _write_store(tmp_path / "raw_snap", nodes=nodes, edges=edges, evidence=ev)
    assert any("date_provenance=crosswalk" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_economic_share_non_null_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    edges[0]["economic_share"] = 0.5
    root = _write_store(tmp_path / "econ", nodes=nodes, edges=edges, evidence=ev)
    assert any("economic_share=null" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_foreign_endpoint_provenance_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes[0]["provenance"] = "fixture:elsewhere"
    root = _write_store(tmp_path / "foreign_prov", nodes=nodes, edges=edges, evidence=ev)
    assert any("provenance must" in x for x in _hierarchy_breaches(root, breaks))


def test_parent_of_vendor_evidence_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    ev_vendor = _evidence(
        evidence_id="ev:00000000000000cc",
        source_ref="finviz_themes/snapshot.json",
    )
    edges[0]["evidence_refs"] = ["ev:00000000000000cc"]
    root = _write_store(
        tmp_path / "vendor_ev", nodes=nodes, edges=edges, evidence=[ev_vendor])
    assert any("mastermind_curated" in x for x in _hierarchy_breaches(root, breaks))


def test_company_to_theme_edge_breaches(tmp_path, breaks):
    nodes, edges, ev = _hierarchy_chain_nodes_edges()
    nodes.append({
        "node_id": "co:us:AAA", "kind": "company", "name_en": None, "name_zh": None,
        "market_scope": "us", "tier": None, "status": "canonical",
        "merged_into": None, "birth_date": None, "retire_date": None,
        "identity_epoch": 1, "external_ids": "{}", "provenance": "fixture",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
    })
    edges.append({
        "edge_id": "expresses:co:us:AAA->theme:mid_h@2024-01-01",
        "type": "EXPRESSES", "src": "co:us:AAA", "dst": "theme:mid_h",
        "valid_from": "2024-01-01", "valid_to": None,
        "evidence_time": "2024-01-01", "belief_time": "2024-01-02",
        "era": "reconstruction", "source_class": "curated",
        "date_provenance": "crosswalk", "evidence_refs": [EV_CROSSWALK],
        "confidence_basis": "crosswalk.v1",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
        **{f: None for f in store.RESERVED_EDGE_FIELDS},
    })
    root = _write_store(tmp_path / "co_theme", nodes=nodes, edges=edges, evidence=ev)
    assert any("company→theme" in x for x in _hierarchy_breaches(root, breaks))


@pytest.fixture
def nodes_schema():
    path = Path(__file__).resolve().parent.parent / "contracts/theme_graph/nodes.v1.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def edges_schema():
    path = Path(__file__).resolve().parent.parent / "contracts/theme_graph/edges.v1.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(schema, row):
    jsonschema.Draft202012Validator(schema).validate(row)


def _validate_fails(schema, row):
    with pytest.raises(jsonschema.ValidationError):
        _validate(schema, row)


def test_jsonschema_theme_without_tier_rejected(nodes_schema):
    row = _theme_node("theme:x", "theme")
    row["tier"] = None
    _validate_fails(nodes_schema, row)


def test_jsonschema_company_with_tier_rejected(nodes_schema):
    row = {
        "node_id": "co:us:AAA", "kind": "company", "name_en": None, "name_zh": None,
        "market_scope": "us", "tier": "theme", "status": "canonical",
        "merged_into": None, "birth_date": None, "retire_date": None,
        "identity_epoch": 1, "external_ids": "{}", "provenance": "fixture",
        "computed_at": STAMP, "engine_version": store.ENGINE_VERSION,
    }
    _validate_fails(nodes_schema, row)


def test_jsonschema_parent_of_scrape_rejected(edges_schema):
    row = _parent_of("theme:cat_h", "theme:mid_h")
    row["source_class"] = "scrape"
    _validate_fails(edges_schema, row)


def test_jsonschema_parent_of_economic_share_rejected(edges_schema):
    row = _parent_of("theme:cat_h", "theme:mid_h")
    row["economic_share"] = 0.1
    _validate_fails(edges_schema, row)


def test_jsonschema_valid_parent_of_accepted(edges_schema):
    _validate(edges_schema, _parent_of("theme:cat_h", "theme:mid_h"))
