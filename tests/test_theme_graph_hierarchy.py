"""Fixture-only proofs for crosswalk-owned theme hierarchy emission."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine.theme_graph import materialize
from engine.theme_graph.materialize import ThemeHierarchyError


EPOCH = materialize.HIERARCHY_EPOCH
AFTER = "2026-10-08"
VALID_NOMINATOR = "research:research/theme_notes/semis.md"




@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Copy of the incumbent materialization fixture setup for fixture-only proofs."""
    root = tmp_path / "data"
    root.mkdir()
    (root / "baskets_china_ths").mkdir()
    xwalk = tmp_path / "theme_crosswalk.yml"
    xwalk.write_text(yaml.safe_dump({
        "version": 3, "date": "2026-07-09",
        "themes": [{
            "id": "solar", "name_en": "Solar", "name_zh": "太阳能",
            "theme_node_id": "theme:solar", "basket_ids": [], "cn_basket_ids": [],
            "ths_concept_ids": [],
        }],
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    from engine.theme_graph import identity
    from lib import config
    monkeypatch.setattr(identity, "load_breaks", lambda *a, **k: {})
    monkeypatch.setattr(config, "data_dir", lambda: root)
    return root, xwalk

def hierarchy_doc(categories=None, micro_themes=None, parents=None):
    return {
        "categories": [] if categories is None else categories,
        "micro_themes": [] if micro_themes is None else micro_themes,
        "parents": [] if parents is None else parents,
    }


def category(node_id="theme:hierarchy_cat", asserted_on=EPOCH, **overrides):
    row = {"id": node_id, "name_en": "Hierarchy category",
           "name_zh": "层级大类", "asserted_on": asserted_on}
    row.update(overrides)
    return row


def micro(node_id="theme:hierarchy_micro", asserted_on=EPOCH,
          nominated_from=VALID_NOMINATOR, **overrides):
    row = {"id": node_id, "name_en": "Hierarchy micro",
           "name_zh": "层级微主题", "asserted_on": asserted_on,
           "nominated_from": nominated_from}
    row.update(overrides)
    return row


def parent(parent_id="theme:hierarchy_cat", child_id="theme:solar",
           asserted_on=EPOCH, **overrides):
    row = {"parent": parent_id, "child": child_id, "asserted_on": asserted_on}
    row.update(overrides)
    return row


def document_with_themes(hierarchy, basket_ids=()):
    return {
        **hierarchy,
        "themes": [{"id": "solar", "theme_node_id": "theme:solar",
                    "basket_ids": list(basket_ids), "cn_basket_ids": [],
                    "ths_concept_ids": []}],
    }


def write_document(tree, hierarchy, basket_ids=()):
    doc = yaml.safe_load(tree[1].read_text(encoding="utf-8"))
    doc["hierarchy"] = hierarchy
    if basket_ids:
        doc["themes"][0]["basket_ids"] = list(basket_ids)
    tree[1].write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")


def write_hierarchy(tree, hierarchy):
    _root, source = tree
    doc = yaml.safe_load(source.read_text(encoding="utf-8"))
    doc["hierarchy"] = hierarchy
    source.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")


def tmp_path_of_tree(root: Path, name: str) -> Path:
    return root.parent / name


def nodes_by_id(view):
    return {row["node_id"]: row for row in view.nodes}


def edge_rows(view):
    return pd.DataFrame(view.edges)


def write_views(view, root: Path):
    nodes_path = root / "nodes.parquet"
    edges_path = root / "edges.parquet"
    pd.DataFrame(view.nodes).to_parquet(nodes_path, index=False)
    edge_rows(view).to_parquet(edges_path, index=False)
    return nodes_path.read_bytes(), edges_path.read_bytes()


@pytest.fixture
def populated_view(tree):
    write_document(tree, hierarchy_doc(
        categories=[category()],
        micro_themes=[micro()],
        parents=[parent(), parent("theme:solar", "theme:hierarchy_micro")],
    ))
    return materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=tree[0], crosswalk_path=tree[1],
        raw_snapshot=(AFTER, {}), ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))


def test_hierarchy_absent_is_byte_identical(tree):
    root, source = tree
    before = materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root, crosswalk_path=source, raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    absent = write_views(before, root)
    doc = yaml.safe_load(source.read_text(encoding="utf-8"))
    doc.pop("hierarchy", None)
    source.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")
    after = materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root, crosswalk_path=source, raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    assert write_views(after, root) == absent
    assert pd.DataFrame(before.nodes).equals(pd.DataFrame(after.nodes))
    assert pd.DataFrame(before.edges).equals(pd.DataFrame(after.edges))


def test_hierarchy_empty_is_byte_identical(tree):
    root, source = tree
    before = materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root, crosswalk_path=source, raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    absent = write_views(before, root)
    write_document(tree, hierarchy_doc())
    after = materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root, crosswalk_path=source, raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    assert write_views(after, root) == absent
    assert pd.DataFrame(before.nodes).equals(pd.DataFrame(after.nodes))
    assert pd.DataFrame(before.edges).equals(pd.DataFrame(after.edges))


def test_populated_block_emits_exact_nodes_and_parent_edges(populated_view):
    nodes = nodes_by_id(populated_view)
    category_node = nodes["theme:hierarchy_cat"]
    micro_node = nodes["theme:hierarchy_micro"]
    assert category_node["kind"] == "theme"
    assert category_node["tier"] == "macro_category"
    assert category_node["market_scope"] == "global"
    assert category_node["provenance"] == "crosswalk:config/theme_crosswalk.yml"
    assert category_node["external_ids"] == "{}"
    assert category_node["birth_date"] == EPOCH
    assert category_node["source_meta"] is None
    assert micro_node["tier"] == "micro_theme"
    assert yaml.safe_load(micro_node["source_meta"]) == {"nominated_from": VALID_NOMINATOR}

    parent_edges = [row for row in populated_view.edges if row["type"] == "PARENT_OF"]
    assert {(row["src"], row["dst"]) for row in parent_edges} == {
        ("theme:hierarchy_cat", "theme:solar"),
        ("theme:solar", "theme:hierarchy_micro")}
    edge = next(row for row in parent_edges
                if row["src"] == "theme:hierarchy_cat")
    assert edge["edge_id"] == materialize.edge_id_for(
        "PARENT_OF", "theme:hierarchy_cat", "theme:solar", EPOCH)
    assert edge["valid_from"] == edge["evidence_time"] == EPOCH
    assert edge["valid_to"] is None
    assert edge["source_class"] == "curated"
    assert edge["date_provenance"] == "crosswalk"
    assert edge["era"] == "reconstruction"
    for field in materialize.RESERVED_EDGE_FIELDS:
        assert edge[field] is None
    evidence_by_id = {row["evidence_id"]: row for row in populated_view.evidence}
    assert len(edge["evidence_refs"]) == 1
    evidence = evidence_by_id[edge["evidence_refs"][0]]
    assert evidence["kind"] == "operator_curation"
    assert evidence["source_ref"] == "config/theme_crosswalk.yml"
    assert evidence["published_at"] == EPOCH


def test_new_tier_has_no_membership_or_expression_edges(populated_view):
    edges = [(row["type"], row["src"], row["dst"]) for row in populated_view.edges]
    for node_id in ("theme:hierarchy_cat", "theme:hierarchy_micro"):
        assert all(node_id not in (src, dst)
                   for edge_type, src, dst in edges
                   if edge_type in {"EXPRESSES", "MEMBER_OF"})


def test_populated_block_preserves_expresses_identity(tree):
    root, source = tree
    (root / "baskets").mkdir(exist_ok=True)
    (root / "baskets" / "membership.json").write_text(json.dumps({
        "version": "2026-07-09", "seed_date": "2026-01-01",
        "baskets": {"solar_us": {
            "name": "Solar", "created": "2026-01-01", "etf_proxy": "TAN",
            "members": [{"symbol": "AAA", "added": "2026-01-01", "removed": None,
                         "name": "Alpha"}],
        }},
    }), encoding="utf-8")
    documents = {}
    for name, hierarchy in (
            ("xwalk_empty.yml", None),
            ("xwalk_populated.yml", hierarchy_doc(
                categories=[category()],
                micro_themes=[micro()],
                parents=[parent(), parent("theme:solar", "theme:hierarchy_micro")]))):
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
        if hierarchy is None:
            document.pop("hierarchy", None)
        else:
            document["hierarchy"] = hierarchy
        document["themes"][0]["basket_ids"] = ["solar_us"]
        path = tmp_path_of_tree(root, name)
        path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
        documents[name] = materialize.build(
            era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
            data_dir=root, crosswalk_path=path, raw_snapshot=(AFTER, {}),
            ths_history=pd.DataFrame(
                columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    empty_ids = {row["edge_id"] for row in documents["xwalk_empty.yml"].edges
                 if row["type"] == "EXPRESSES"}
    populated_ids = {row["edge_id"] for row in documents["xwalk_populated.yml"].edges
                     if row["type"] == "EXPRESSES"}
    assert empty_ids == populated_ids
    assert empty_ids
    assert "expresses:basket:baskets:solar_us->theme:solar@2026-07-09" in empty_ids


def test_future_dated_nodes_and_edges_are_pit_filtered(tree):
    write_document(tree, hierarchy_doc(
        categories=[category(asserted_on=AFTER)],
        micro_themes=[micro(asserted_on=AFTER)],
        parents=[parent(asserted_on=AFTER),
                 parent("theme:solar", "theme:hierarchy_micro", asserted_on=AFTER)]))
    view = materialize.build(
        era="reconstruction", belief_time=EPOCH, computed_at=f"{EPOCH}T00:00:00Z",
        data_dir=tree[0], crosswalk_path=tree[1], raw_snapshot=(EPOCH, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    ids = {row["node_id"] for row in view.nodes}
    assert "theme:hierarchy_cat" not in ids
    assert "theme:hierarchy_micro" not in ids
    assert not [row for row in view.edges if row["type"] == "PARENT_OF"]


def test_future_dated_invalid_row_still_refuses(tree):
    write_document(tree, hierarchy_doc(categories=[category("theme:Bad Slug", AFTER)]))
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.build(
            era="reconstruction", belief_time=EPOCH, computed_at=f"{EPOCH}T00:00:00Z",
            data_dir=tree[0], crosswalk_path=tree[1], raw_snapshot=(EPOCH, {}),
            ths_history=pd.DataFrame(
                columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    assert caught.value.reason == "SLUG_GRAMMAR"
    assert str(caught.value).startswith("SLUG_GRAMMAR")


def _refuses(tree, expected_reason, **kwargs):
    write_document(tree, hierarchy_doc(**kwargs))
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.validate_theme_hierarchy(
            yaml.safe_load(tree[1].read_text(encoding="utf-8")))
    assert caught.value.reason == expected_reason
    assert str(caught.value).startswith(expected_reason)


@pytest.mark.parametrize("hierarchy,reason", [
    ({"bad": []}, "BLOCK_SHAPE"),
    ({"categories": None, "micro_themes": [], "parents": []}, "BLOCK_SHAPE"),
    ({"categories": [category(weight=1)], "micro_themes": [], "parents": []},
     "FORBIDDEN_KEY"),
    ({"categories": [category(note="ok", unknown=1)], "micro_themes": [],
      "parents": []}, "BLOCK_SHAPE"),
    ({"categories": [category(node_id="theme:Bad")], "micro_themes": [], "parents": []},
     "SLUG_GRAMMAR"),
    ({"categories": [category(asserted_on="")], "micro_themes": [], "parents": []},
     "ASSERTED_ON_MISSING"),
    ({"categories": [category(asserted_on="2026-10-06")], "micro_themes": [], "parents": []},
     "ASSERTED_ON_PRE_EPOCH"),
    ({"categories": [category(), category()], "micro_themes": [], "parents": []},
     "DUPLICATE_ID"),
])
def test_block_refusal_reasons(tree, hierarchy, reason):
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.validate_theme_hierarchy({"hierarchy": hierarchy, "themes": []})
    assert caught.value.reason == reason
    assert str(caught.value).startswith(reason)


def test_cross_tier_reuse(tree):
    write_document(tree, hierarchy_doc(categories=[category("theme:solar")]))
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.validate_theme_hierarchy(
            yaml.safe_load(tree[1].read_text(encoding="utf-8")))
    assert caught.value.reason == "CROSS_TIER_REUSE"


def test_undeclared_endpoint_and_endpoint_precedence(tree):
    _refuses(tree, "UNDECLARED_ENDPOINT", parents=[parent("theme:missing")])
    _refuses(tree, "UNDECLARED_ENDPOINT",
             categories=[category(asserted_on=AFTER)],
             parents=[parent(asserted_on=EPOCH)])


def test_cycle_refusal(tree):
    source = tree[1]
    doc = yaml.safe_load(source.read_text(encoding="utf-8"))
    doc["hierarchy"] = hierarchy_doc(
        categories=[category()],
        micro_themes=[micro()],
        parents=[parent("theme:hierarchy_cat", "theme:hierarchy_cat")])
    source.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.validate_theme_hierarchy(
            yaml.safe_load(tree[1].read_text(encoding="utf-8")))
    assert caught.value.reason == "CYCLE"


def test_non_adjacent_tier(tree):
    _refuses(tree, "NON_ADJACENT_TIERS",
             categories=[category()],
             micro_themes=[micro()],
             parents=[parent("theme:hierarchy_cat", "theme:hierarchy_micro")])


def test_too_many_parents_requires_distinct_categories(tree):
    categories = [category(f"theme:category_{index}") for index in range(4)]
    _refuses(tree, "TOO_MANY_PARENTS", categories=categories,
             parents=[parent(f"theme:category_{index}") for index in range(4)])


def test_new_tier_referenced_in_mapping_value(tree):
    doc = hierarchy_doc(categories=[category()], parents=[parent()])
    write_document(tree, doc, basket_ids=["theme:hierarchy_cat"])
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize.validate_theme_hierarchy(
            yaml.safe_load(tree[1].read_text(encoding="utf-8")))
    assert caught.value.reason == "NEW_TIER_IN_EXPRESSES_MAP"


def test_nominated_from_grammar_and_vendors(tree):
    _refuses(tree, "NOMINATED_FROM_GRAMMAR", micro_themes=[micro(nominated_from="notes")])
    _refuses(tree, "VENDOR_NOMINATOR",
             micro_themes=[micro(nominated_from="research:finviz_themes")])
    _refuses(tree, "VENDOR_NOMINATOR",
             micro_themes=[micro(nominated_from="research:ths.concepts")])


def test_basket_nominator_rights(tree, monkeypatch):
    _refuses(tree, "VENDOR_NOMINATOR",
             micro_themes=[micro(nominated_from="basket:baskets_china_ths:x")])
    monkeypatch.setattr(
        materialize, "_validate_nominated_from", materialize._validate_nominated_from)
    from engine.theme_graph import rights as rights_module
    monkeypatch.setattr(rights_module, "family_for_node_id", lambda _value: None)
    _refuses(tree, "NOMINATOR_FAMILY_UNRESOLVED",
             micro_themes=[micro(nominated_from="basket:baskets:x")])


def test_research_vendor_path_refused_by_producer(tree):
    _refuses(tree, "VENDOR_NOMINATOR",
             micro_themes=[micro(nominated_from="research:data/themes_heatmap/us.json")])


def test_unregistered_research_source_refused_by_producer(tree):
    _refuses(tree, "NOMINATOR_UNREGISTERED_SOURCE",
             micro_themes=[micro(nominated_from="research:data/unregistered_x/y.json")])


def test_unsafe_research_path_refused_by_producer(tree):
    _refuses(tree, "NOMINATOR_PATH_UNSAFE",
             micro_themes=[micro(
                 nominated_from="research:config/../data/themes_heatmap/us.json")])


def test_producer_delegates_to_probation_rule(monkeypatch):
    from engine.theme_graph import probation

    monkeypatch.setattr(
        probation, "nominated_from_errors", lambda value: ["SENTINEL_NOMINATOR: delegated"])
    with pytest.raises(ThemeHierarchyError) as caught:
        materialize._validate_nominated_from("research:research/x.md")
    assert caught.value.reason == "SENTINEL_NOMINATOR"
    assert str(caught.value) == "SENTINEL_NOMINATOR: delegated"

    monkeypatch.setattr(probation, "nominated_from_errors", lambda value: [])
    assert materialize._validate_nominated_from("research:finviz_themes") is None


def test_producer_passes_raw_nominator_bytes():
    from engine.theme_graph import probation

    expected_reasons = {
        "research:research/x.md ": "NOMINATOR_PATH_UNSAFE",
        " research:research/x.md": "NOMINATOR_PATH_UNSAFE",
        "research:": "NOMINATED_FROM_GRAMMAR",
    }
    for value, expected_reason in expected_reasons.items():
        with pytest.raises(ThemeHierarchyError) as producer_error:
            materialize._validate_nominated_from(value)
        probation_reason = probation.nominated_from_errors(
            value)[0].partition(": ")[0]
        assert producer_error.value.reason == expected_reason
        assert producer_error.value.reason == probation_reason


def test_producer_does_not_reimplement_nominator_rule():
    import inspect

    assert not hasattr(materialize, "_NOMINATED_FROM_RE")
    source = inspect.getsource(materialize._validate_nominated_from)
    assert "nominated_from_errors" in source
    for needle in ("finviz", "ths", "family_for", "fullmatch", "basket:", "research:"):
        assert needle not in source


def test_undated_crosswalk_emits_no_dangling_parent_edge(tree):
    root, source = tree
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document["date"] = "not-a-date"
    document["hierarchy"] = hierarchy_doc(
        categories=[category()], parents=[parent()])
    source.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")
    view = materialize.build(
        era="reconstruction", belief_time=AFTER, computed_at=f"{AFTER}T00:00:00Z",
        data_dir=root, crosswalk_path=source, raw_snapshot=(AFTER, {}),
        ths_history=pd.DataFrame(
            columns=["snapshot_date", "suite", "basket_id", "ticker", "source_shape"]))
    nodes = nodes_by_id(view)
    parent_edges = [row for row in view.edges if row["type"] == "PARENT_OF"]
    assert all(row["src"] in nodes and row["dst"] in nodes for row in parent_edges)
    assert ("PARENT_OF", "theme:hierarchy_cat", "theme:solar") not in {
        (row["type"], row["src"], row["dst"]) for row in view.edges}


def test_parent_edge_endpoints_are_minted_and_tier_typed(populated_view):
    nodes = nodes_by_id(populated_view)
    parent_edges = [row for row in populated_view.edges if row["type"] == "PARENT_OF"]
    assert len(parent_edges) >= 2
    for row in parent_edges:
        source_node = nodes[row["src"]]
        destination_node = nodes[row["dst"]]
        assert source_node["kind"] == "theme"
        assert destination_node["kind"] == "theme"
        assert ((source_node["tier"], destination_node["tier"])
                in {("macro_category", "theme"), ("theme", "micro_theme")})
