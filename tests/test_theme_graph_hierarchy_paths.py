"""W-C6 read-time hierarchy_paths composition (synthetic in-memory fixtures only)."""
from __future__ import annotations

import copy
import hashlib
import json
import random
from datetime import datetime, timezone

import pytest

from engine.theme_graph import store, structural_navigation as structural
from scripts import check_theme_graph_contracts as guard

STAMP = "2024-01-02T00:00:00Z"
ASOF = "2024-06-01"
CROSSWALK_PROV = guard.CROSSWALK_NODE_PROVENANCE
FIXED_NOW = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
OWNER = {"unmapped_baskets": [{"id": "us_sector_tech", "reason": "Recorded sector context only."}]}
OWNER_SHA = hashlib.sha256(json.dumps(OWNER, sort_keys=True).encode()).hexdigest()


class FakeStore:
    def __init__(self, nodes, edges, lifecycle=None):
        self._nodes = nodes
        self._edges = edges
        self._lifecycle = lifecycle if lifecycle is not None else []

    def read_nodes(self):
        return self._nodes

    def read_edges(self):
        return self._edges

    def read_node_lifecycle(self):
        return self._lifecycle

    def read_proposals(self):
        return []


def _blank_node(**over):
    row = {key: None for key in store.NODE_COLUMNS}
    row.update(
        status="canonical",
        merged_into=None,
        birth_date="2024-01-01",
        retire_date=None,
        identity_epoch=1,
        external_ids="{}",
        computed_at=STAMP,
        engine_version=store.ENGINE_VERSION,
        source_meta=None,
    )
    row.update(over)
    return row


def _theme(node_id, tier, **over):
    return _blank_node(
        node_id=node_id,
        kind="theme",
        tier=tier,
        name_en=node_id,
        name_zh=None,
        market_scope="global",
        provenance=CROSSWALK_PROV,
        **over,
    )


def _basket(node_id, **over):
    bid = node_id.split(":", 2)[-1] if node_id.startswith("basket:") else "x"
    suite = "baskets_china_ths" if "baskets_china_ths" in node_id else "baskets"
    return _blank_node(
        node_id=node_id,
        kind="basket",
        name_en=bid,
        name_zh=None,
        market_scope="us",
        external_ids=json.dumps({"suite": suite, "basket_id": bid.split(":")[-1]}),
        provenance="fixture",
        **over,
    )


def _company(node_id, **over):
    return _blank_node(
        node_id=node_id,
        kind="company",
        name_en=node_id,
        name_zh=None,
        market_scope="us",
        provenance="fixture",
        **over,
    )


def _local_theme(node_id, **over):
    return _blank_node(
        node_id=node_id,
        kind="local_theme",
        name_en=node_id,
        name_zh=None,
        market_scope="us",
        provenance="fixture",
        **over,
    )


def _edge(edge_id, type_, src, dst, **over):
    row = {key: None for key in store.EDGE_COLUMNS}
    row.update(
        edge_id=edge_id,
        type=type_,
        src=src,
        dst=dst,
        valid_from="2024-01-01",
        valid_to=None,
        evidence_time="2024-01-01",
        belief_time="2024-01-02",
        era="reconstruction",
        source_class="curated",
        date_provenance="crosswalk",
        evidence_refs=["ev:fixture"],
        confidence_basis="crosswalk.v1",
        computed_at=STAMP,
        engine_version=store.ENGINE_VERSION,
    )
    row.update(over)
    return row


def _parent_of(src, dst, valid_from="2024-01-01", **over):
    return _edge(
        f"parent_of:{src}->{dst}@{valid_from}",
        "PARENT_OF",
        src,
        dst,
        valid_from=valid_from,
        **over,
    )


def _hp(store_view, node_id, asof=ASOF, **kw):
    return structural.hierarchy_paths(store_view, node_id, asof, **kw)


def _full_hierarchy_plane():
    """Hierarchy nodes not wired to T1/T2 subjects."""
    nodes = [
        _theme("theme:cat_iso", "macro_category"),
        _theme("theme:mid_iso", "theme"),
        _theme("theme:micro_iso", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat_iso", "theme:mid_iso"),
        _parent_of("theme:mid_iso", "theme:micro_iso", valid_from="2024-01-02"),
    ]
    return nodes, edges


def test_empty_hierarchy_returns_empty_list():
    theme = _theme("theme:semis", "theme")
    basket = _basket("basket:baskets:semis")
    company = _company("co:us:AAA")
    edges = [
        _edge("exp:1", "EXPRESSES", basket["node_id"], theme["node_id"]),
        _edge("mem:1", "MEMBER_OF", company["node_id"], basket["node_id"]),
    ]
    sv = FakeStore([theme, basket, company], edges)
    assert _hp(sv, theme["node_id"]) == []
    assert _hp(sv, basket["node_id"]) == []
    assert _hp(sv, company["node_id"]) == []
    assert _hp(sv, "co:us:MISSING") == []


def test_compose_structure_outputs_unchanged_by_hierarchy_plane(monkeypatch):
    monkeypatch.setattr(structural, "_utc_now", lambda: FIXED_NOW)
    subject = _company("co:us:PLAIN")
    store_a = FakeStore([subject], [])
    iso_nodes, iso_edges = _full_hierarchy_plane()
    store_b = FakeStore([subject] + iso_nodes, iso_edges)
    kwargs = dict(
        node_id=subject["node_id"],
        asof=ASOF,
        knowledge_cutoff=ASOF,
        owner_document=OWNER,
        owner_sha256=OWNER_SHA,
    )
    a1 = json.dumps(structural.compose_structure(store_a, **kwargs), sort_keys=True, default=str)
    a2 = json.dumps(structural.compose_structure(store_b, **kwargs), sort_keys=True, default=str)
    b1 = json.dumps(structural.compose_structure_v2(store_a, **kwargs), sort_keys=True, default=str)
    b2 = json.dumps(structural.compose_structure_v2(store_b, **kwargs), sort_keys=True, default=str)
    assert a1 == a2
    assert b1 == b2


def test_multi_parent_micro_yields_both_paths():
    nodes = [
        _theme("theme:cat_a", "macro_category"),
        _theme("theme:cat_b", "macro_category"),
        _theme("theme:a", "theme"),
        _theme("theme:b", "theme"),
        _theme("theme:micro", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat_a", "theme:a"),
        _parent_of("theme:cat_b", "theme:b"),
        _parent_of("theme:a", "theme:micro"),
        _parent_of("theme:b", "theme:micro", valid_from="2024-01-02"),
    ]
    sv = FakeStore(nodes, edges)
    paths = _hp(sv, "theme:micro")
    ids = [tuple(el["node_id"] for el in p["path"]) for p in paths]
    assert sorted(ids) == [
        ("theme:cat_a", "theme:a", "theme:micro"),
        ("theme:cat_b", "theme:b", "theme:micro"),
    ]


def test_asof_excludes_future_valid_from():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
    ]
    future_edge = _parent_of("theme:cat", "theme:t", valid_from="2024-07-01")
    edges = [future_edge]
    sv = FakeStore(nodes, edges)
    assert _hp(sv, "theme:t", asof="2024-06-01") == []
    assert len(_hp(sv, "theme:t", asof="2024-07-01")) == 1

    withdrawn = _parent_of("theme:cat", "theme:t", valid_from="2024-01-01", valid_to="2024-06-01")
    sv2 = FakeStore(nodes, [withdrawn])
    assert _hp(sv2, "theme:t", asof="2024-06-01") == []

    late_belief = _parent_of(
        "theme:cat",
        "theme:t",
        belief_time="2024-07-01",
    )
    sv3 = FakeStore(nodes, [late_belief])
    assert _hp(sv3, "theme:t", asof=ASOF, knowledge_cutoff="2024-06-15") == []
    assert len(_hp(sv3, "theme:t", asof=ASOF, knowledge_cutoff="2024-07-02")) == 1


def test_vendor_parent_refused():
    cat = _theme("theme:cat", "macro_category")
    mid = _theme("theme:t", "theme")
    micro = _theme("theme:m", "micro_theme")
    bad_local = _local_theme("ltheme:finviz:chip")
    bad_basket = _basket("basket:baskets_china_ths:concept")
    bad_theme = _blank_node(
        node_id="theme:bad_prov",
        kind="theme",
        tier="theme",
        name_en="bad",
        market_scope="global",
        provenance="vendor:other",
    )
    co = _company("co:us:Z")

    cases = [
        ([cat, mid, bad_local], [_parent_of(bad_local["node_id"], mid["node_id"])]),
        ([cat, mid, bad_basket], [_parent_of(bad_basket["node_id"], mid["node_id"])]),
        ([cat, bad_theme], [_parent_of(cat["node_id"], bad_theme["node_id"])]),
        ([cat, mid, co], [_parent_of(co["node_id"], mid["node_id"])]),
        ([cat, micro], [_parent_of(cat["node_id"], micro["node_id"])]),
    ]
    for nodes, edges in cases:
        with pytest.raises(ValueError, match="hierarchy_paths: refused PARENT_OF"):
            _hp(FakeStore(nodes, edges), mid["node_id"])


def test_rights_receipts_on_every_element():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:m", "micro_theme"),
        _basket("basket:baskets:cur"),
        _company("co:us:C"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02"),
        _edge("e1", "EXPRESSES", "basket:baskets:cur", "theme:t"),
        _edge("m1", "MEMBER_OF", "co:us:C", "basket:baskets:cur"),
    ]
    sv = FakeStore(nodes, edges)
    for node_id in ("theme:t", "basket:baskets:cur", "co:us:C"):
        for rec in _hp(sv, node_id):
            for el in rec["path"]:
                _assert_rights(el)
            for hop in rec["via"]:
                _assert_rights(hop["node"])


def _assert_rights(el):
    rights = el["rights"]
    assert set(rights) == {"family", "rights_class", "public_display_allowed"}
    if el["kind"] == "theme":
        assert rights["family"] == "mastermind_curated"
        assert rights["rights_class"] == "direct_display_ok"
        assert rights["public_display_allowed"] is True


def test_company_path_via_curated_basket_membership():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:m", "micro_theme"),
        _basket("basket:baskets:x"),
        _company("co:us:C"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02"),
        _edge("exp", "EXPRESSES", "basket:baskets:x", "theme:t"),
        _edge("mem", "MEMBER_OF", "co:us:C", "basket:baskets:x"),
    ]
    paths = _hp(FakeStore(nodes, edges), "co:us:C")
    assert len(paths) == 1
    rec = paths[0]
    assert [el["node_id"] for el in rec["path"]] == ["theme:cat", "theme:t"]
    assert len(rec["via"]) == 2
    assert rec["via"][0]["type"] == "MEMBER_OF"
    assert rec["via"][1]["type"] == "EXPRESSES"
    assert "theme:m" not in [el["node_id"] for el in rec["path"]]


def test_vendor_entry_never_followed():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _basket("basket:baskets_china_ths:y"),
        _company("co:us:C"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _edge("exp", "EXPRESSES", "basket:baskets_china_ths:y", "theme:t"),
        _edge("mem", "MEMBER_OF", "co:us:C", "basket:baskets_china_ths:y"),
    ]
    assert _hp(FakeStore(nodes, edges), "co:us:C") == []

    curated_basket = _basket("basket:baskets:deny")
    nodes2 = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        curated_basket,
        _company("co:us:D"),
    ]
    edges2 = [
        _parent_of("theme:cat", "theme:t"),
        _edge("exp2", "EXPRESSES", curated_basket["node_id"], "theme:t"),
        _edge("mem2", "MEMBER_OF", "co:us:D", curated_basket["node_id"]),
    ]

    def deny_resolver(node_id):
        if node_id == curated_basket["node_id"]:
            return {
                "family": "mastermind_curated",
                "rights_class": "direct_display_ok",
                "public_display_allowed": False,
            }
        return structural._default_rights_resolver(node_id)

    assert _hp(FakeStore(nodes2, edges2), "co:us:D", rights_resolver=deny_resolver) == []


def test_theme_and_category_subjects_include_descendants():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:m1", "micro_theme"),
        _theme("theme:m2", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m1"),
        _parent_of("theme:t", "theme:m2", valid_from="2024-01-02"),
    ]
    sv = FakeStore(nodes, edges)
    theme_paths = _hp(sv, "theme:t")
    theme_leaf_ids = sorted(tuple(el["node_id"] for el in p["path"]) for p in theme_paths)
    assert ("theme:cat", "theme:t", "theme:m1") in theme_leaf_ids
    assert ("theme:cat", "theme:t", "theme:m2") in theme_leaf_ids

    cat_paths = _hp(sv, "theme:cat")
    assert any(el["node_id"] == "theme:m1" for p in cat_paths for el in p["path"])

    micro_paths = _hp(sv, "theme:m1")
    assert len(micro_paths) == 1
    assert [el["node_id"] for el in micro_paths[0]["path"]] == ["theme:cat", "theme:t", "theme:m1"]


def test_record_shape_has_no_weights_and_is_deterministic():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:m", "micro_theme"),
        _basket("basket:baskets:b"),
        _company("co:us:E"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02"),
        _edge("exp", "EXPRESSES", "basket:baskets:b", "theme:t"),
        _edge("mem", "MEMBER_OF", "co:us:E", "basket:baskets:b"),
    ]
    sv = FakeStore(nodes, edges)
    first = _hp(sv, "co:us:E")
    second = _hp(sv, "co:us:E")
    assert first == second

    shuffled_nodes = copy.deepcopy(nodes)
    shuffled_edges = copy.deepcopy(edges)
    random.Random(0).shuffle(shuffled_nodes)
    random.Random(1).shuffle(shuffled_edges)
    third = _hp(FakeStore(shuffled_nodes, shuffled_edges), "co:us:E")
    assert first == third

    banned = ("weight", "share", "score", "rank", "count", "confidence")
    for rec in first:
        assert set(rec) == {"path", "parent_of_edge_ids", "anchor_node_id", "via"}
        assert len(rec["parent_of_edge_ids"]) == len(rec["path"]) - 1 >= 1
        for el in rec["path"]:
            assert set(el) == {"node_id", "kind", "tier", "name_en", "name_zh", "rights"}
            for key in el:
                assert not any(b in key.lower() for b in banned)
        for hop in rec["via"]:
            assert set(hop) == {"type", "edge_id", "node"}
