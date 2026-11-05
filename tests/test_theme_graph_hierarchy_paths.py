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


def _install_w_c3_reader_tier_guard(monkeypatch):
    """Simulate W-C3: _nodes_as_known drops non-theme-tier theme nodes."""
    from engine.theme_graph import ontology

    real = ontology._nodes_as_known

    def guarded(*args, **kwargs):
        out = real(*args, **kwargs)
        return {
            nid: row
            for nid, row in out.items()
            if not (
                str(row.get("kind") or "") == "theme"
                and row.get("tier") is not None
                and str(row.get("tier")) != "theme"
            )
        }

    monkeypatch.setattr(ontology, "_nodes_as_known", guarded)
    return guarded


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
        (
            ([cat, mid, bad_local], [_parent_of(bad_local["node_id"], mid["node_id"])]),
            "endpoint kind must be theme",
        ),
        (
            ([cat, mid, bad_basket], [_parent_of(bad_basket["node_id"], mid["node_id"])]),
            "endpoint kind must be theme",
        ),
        (
            ([cat, bad_theme], [_parent_of(cat["node_id"], bad_theme["node_id"])]),
            "provenance must be crosswalk",
        ),
        (
            ([cat, mid, co], [_parent_of(co["node_id"], mid["node_id"])]),
            "endpoint kind must be theme",
        ),
        (
            ([cat, micro], [_parent_of(cat["node_id"], micro["node_id"])]),
            "invalid tier adjacency",
        ),
    ]
    for (nodes, edges), expected in cases:
        with pytest.raises(ValueError, match="hierarchy_paths: refused PARENT_OF") as info:
            _hp(FakeStore(nodes, edges), mid["node_id"])
        assert expected in str(info.value)
        assert "endpoint not as-known" not in str(info.value)


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


def test_malformed_parent_of_row_fails_closed():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
    ]
    bad = _parent_of("theme:cat", "theme:t")
    bad["src"] = ""
    sv = FakeStore(nodes, [bad])
    with pytest.raises(ValueError, match="missing edge_id/type/src/dst"):
        _hp(sv, "theme:t")


def test_parent_of_liveness_follows_latest_belief():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
    ]
    edge_id = "parent_of:theme:cat->theme:t@2024-01-01"
    belief_a = _parent_of(
        "theme:cat",
        "theme:t",
        belief_time="2024-01-01",
        valid_from="2024-01-01",
        valid_to=None,
    )
    belief_a["edge_id"] = edge_id
    belief_b = _parent_of(
        "theme:cat",
        "theme:t",
        belief_time="2024-08-01",
        valid_from="2024-01-01",
        valid_to="2024-08-01",
    )
    belief_b["edge_id"] = edge_id
    asof = "2024-09-01"

    def assert_belief_order(edges):
        sv = FakeStore(nodes, edges)
        assert len(_hp(sv, "theme:t", asof=asof, knowledge_cutoff="2024-07-01")) == 1
        assert _hp(sv, "theme:t", asof=asof, knowledge_cutoff="2024-09-01") == []

    assert_belief_order([belief_a, belief_b])
    assert_belief_order([belief_b, belief_a])


def test_hierarchy_tier_nodes_survive_reader_tier_guard(monkeypatch):
    _install_w_c3_reader_tier_guard(monkeypatch)
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
    fixture_tiers = {n["node_id"]: n["tier"] for n in nodes}
    for rec in paths:
        for el in rec["path"]:
            assert el["tier"] == fixture_tiers[el["node_id"]]

    cat = _theme("theme:cat", "macro_category")
    micro = _theme("theme:m", "micro_theme")
    with pytest.raises(ValueError, match="invalid tier adjacency"):
        _hp(FakeStore([cat, micro], [_parent_of(cat["node_id"], micro["node_id"])]), micro["node_id"])


def _assert_nodes_unchanged_after_hierarchy_paths(nodes, before, ids_before, blob_before):
    assert nodes == before
    assert json.dumps(nodes, sort_keys=True, default=str) == blob_before
    assert [id(row) for row in nodes] == ids_before
    for row in nodes:
        assert "__hierarchy_paths_tier" not in row


def test_hierarchy_paths_leaves_no_state_behind(monkeypatch):
    from engine.theme_graph.ontology import _parse_date

    guarded = _install_w_c3_reader_tier_guard(monkeypatch)
    asof_date = _parse_date(ASOF, "asof")
    cat = _theme("theme:cat", "macro_category")
    mid = _theme("theme:t", "theme")
    micro = _theme("theme:m", "micro_theme")
    fixture_tiers = {
        cat["node_id"]: cat["tier"],
        mid["node_id"]: mid["tier"],
        micro["node_id"]: micro["tier"],
    }
    nodes_ok = [cat, mid, micro]
    edges_ok = [
        _parent_of(cat["node_id"], mid["node_id"]),
        _parent_of(mid["node_id"], micro["node_id"], valid_from="2024-01-02"),
    ]
    nodes_bad = [cat, micro]
    edges_bad = [_parent_of(cat["node_id"], micro["node_id"])]

    def snapshot(node_list):
        return (
            copy.deepcopy(node_list),
            [id(row) for row in node_list],
            json.dumps(node_list, sort_keys=True, default=str),
        )

    before, ids_before, blob_before = snapshot(nodes_ok)
    _hp(FakeStore(nodes_ok, edges_ok), micro["node_id"])
    _assert_nodes_unchanged_after_hierarchy_paths(nodes_ok, before, ids_before, blob_before)
    for row in nodes_ok:
        assert row["tier"] == fixture_tiers[row["node_id"]]

    known = guarded(nodes_ok, [], asof=asof_date, knowledge_cutoff=asof_date)
    assert cat["node_id"] not in known
    assert micro["node_id"] not in known
    assert mid["node_id"] in known

    before2, ids_before2, blob_before2 = snapshot(nodes_bad)
    with pytest.raises(ValueError, match="invalid tier adjacency"):
        _hp(FakeStore(nodes_bad, edges_bad), micro["node_id"])
    _assert_nodes_unchanged_after_hierarchy_paths(nodes_bad, before2, ids_before2, blob_before2)
    for row in nodes_bad:
        assert row["tier"] == fixture_tiers.get(row["node_id"], row["tier"])

    known2 = guarded(nodes_bad, [], asof=asof_date, knowledge_cutoff=asof_date)
    assert cat["node_id"] not in known2
    assert micro["node_id"] not in known2
    assert mid["node_id"] not in known2


def test_refusal_reasons_not_as_known_and_rights_gate(monkeypatch):
    from engine.theme_graph import rights

    cat = _theme("theme:cat", "macro_category")
    edges_a = [_parent_of(cat["node_id"], "theme:ghost")]
    with pytest.raises(ValueError, match="hierarchy_paths: refused PARENT_OF") as info_a:
        _hp(FakeStore([cat], edges_a), cat["node_id"])
    assert "endpoint not as-known" in str(info_a.value)

    mid = _theme("theme:t", "theme")
    micro = _theme("theme:m", "micro_theme")
    nodes_b = [cat, mid, micro]
    edges_b = [
        _parent_of(cat["node_id"], mid["node_id"]),
        _parent_of(mid["node_id"], micro["node_id"], valid_from="2024-01-02"),
    ]
    monkeypatch.setattr(rights, "emission_allowed", lambda family, **kw: False)
    with pytest.raises(ValueError) as info_b:
        _hp(FakeStore(nodes_b, edges_b), micro["node_id"])
    assert "hierarchy family not emission-allowed" in str(info_b.value)


def _path_ids(paths):
    return [tuple(el["node_id"] for el in rec["path"]) for rec in paths]


def _lifecycle_retired(node_id):
    return {
        "schema": "gmi.node_lifecycle/v1",
        "node_id": node_id,
        "status": "retired",
        "retire_date": "2024-03-01",
        "merged_into": None,
        "reason": "fixture",
        "evidence": "fixture",
        "ratified_by": "fixture",
        "computed_at": STAMP,
        "engine_version": store.ENGINE_VERSION,
    }


def test_sub_theme_micro_returns_four_tier_path():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:sub", "sub_theme"),
        _theme("theme:m", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:sub"),
        _parent_of("theme:sub", "theme:m", valid_from="2024-01-02"),
    ]
    paths = _hp(FakeStore(nodes, edges), "theme:m")
    assert len(paths) == 1
    assert [el["node_id"] for el in paths[0]["path"]] == [
        "theme:cat", "theme:t", "theme:sub", "theme:m",
    ]
    assert [el["tier"] for el in paths[0]["path"]] == [
        "macro_category", "theme", "sub_theme", "micro_theme",
    ]
    assert len(paths[0]["parent_of_edge_ids"]) == 3


def test_micro_directly_under_theme_stays_three_tier_path():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:m", "micro_theme"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02"),
    ]
    paths = _hp(FakeStore(nodes, edges), "theme:m")
    assert len(paths) == 1
    assert [el["node_id"] for el in paths[0]["path"]] == ["theme:cat", "theme:t", "theme:m"]
    assert [el["tier"] for el in paths[0]["path"]] == ["macro_category", "theme", "micro_theme"]


def test_sub_theme_subject_returns_category_theme_sub():
    nodes = [
        _theme("theme:cat", "macro_category"),
        _theme("theme:t", "theme"),
        _theme("theme:sub", "sub_theme"),
    ]
    edges = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:sub"),
    ]
    paths = _hp(FakeStore(nodes, edges), "theme:sub")
    assert len(paths) == 1
    assert [el["node_id"] for el in paths[0]["path"]] == ["theme:cat", "theme:t", "theme:sub"]
    assert [el["tier"] for el in paths[0]["path"]] == ["macro_category", "theme", "sub_theme"]


def test_sub_theme_nonadjacent_pairs_refused():
    refused = (
        ("sub_theme", "sub_theme"),
        ("macro_category", "sub_theme"),
        ("micro_theme", "sub_theme"),
    )
    for src_tier, dst_tier in refused:
        src = _theme("theme:src", src_tier)
        dst = _theme("theme:dst", dst_tier)
        with pytest.raises(ValueError, match="invalid tier adjacency"):
            _hp(
                FakeStore([src, dst], [_parent_of(src["node_id"], dst["node_id"])]),
                dst["node_id"],
            )


def test_withdrawn_or_retired_sub_theme_matches_micro():
    """A sub_theme is dropped or kept by the same incumbent rules as a micro_theme.

    A PARENT_OF whose valid_to equals the as-of is not live, so the subject path is
    empty (same assertion as the withdrawn edge in test_asof_excludes_future_valid_from).
    A lifecycle status of retired overlays the node and does not remove it; the chain
    through that node stays, for a micro_theme and for a sub_theme alike.
    """
    cat = _theme("theme:cat", "macro_category")
    mid = _theme("theme:t", "theme")
    micro = _theme("theme:m", "micro_theme")
    sub = _theme("theme:sub", "sub_theme")
    micro_nodes = [cat, mid, micro]
    micro_live = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02"),
    ]
    live_micro = _hp(FakeStore(micro_nodes, micro_live), "theme:m")
    assert [el["node_id"] for el in live_micro[0]["path"]] == ["theme:cat", "theme:t", "theme:m"]

    micro_withdrawn = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:m", valid_from="2024-01-02", valid_to="2024-06-01"),
    ]
    assert _hp(FakeStore(micro_nodes, micro_withdrawn), "theme:m", asof="2024-06-01") == []
    assert _path_ids(_hp(FakeStore(micro_nodes, micro_withdrawn), "theme:t", asof="2024-06-01")) == [
        ("theme:cat", "theme:t"),
    ]

    sub_nodes = [cat, mid, sub, micro]
    sub_live = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:sub"),
        _parent_of("theme:sub", "theme:m", valid_from="2024-01-02"),
    ]
    live_sub = _hp(FakeStore(sub_nodes, sub_live), "theme:m")
    assert [el["node_id"] for el in live_sub[0]["path"]] == [
        "theme:cat", "theme:t", "theme:sub", "theme:m",
    ]

    sub_withdrawn = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:sub", valid_to="2024-06-01"),
        _parent_of("theme:sub", "theme:m", valid_from="2024-01-02", valid_to="2024-06-01"),
    ]
    assert _hp(FakeStore(sub_nodes, sub_withdrawn), "theme:sub", asof="2024-06-01") == []
    assert _hp(FakeStore(sub_nodes, sub_withdrawn), "theme:m", asof="2024-06-01") == []
    assert _path_ids(_hp(FakeStore(sub_nodes, sub_withdrawn), "theme:t", asof="2024-06-01")) == [
        ("theme:cat", "theme:t"),
    ]

    # Edge into the sub is withdrawn; sub → micro stays live, so the upper chain
    # breaks and the micro path stops at the sub.
    sub_cut = [
        _parent_of("theme:cat", "theme:t"),
        _parent_of("theme:t", "theme:sub", valid_to="2024-06-01"),
        _parent_of("theme:sub", "theme:m", valid_from="2024-01-02"),
    ]
    cut = FakeStore(sub_nodes, sub_cut)
    assert _path_ids(_hp(cut, "theme:t", asof="2024-06-01")) == [("theme:cat", "theme:t")]
    assert _path_ids(_hp(cut, "theme:sub", asof="2024-06-01")) == [("theme:sub", "theme:m")]
    assert _path_ids(_hp(cut, "theme:m", asof="2024-06-01")) == [("theme:sub", "theme:m")]

    retired_micro = _hp(
        FakeStore(micro_nodes, micro_live, lifecycle=[_lifecycle_retired("theme:m")]),
        "theme:m",
    )
    assert [el["node_id"] for el in retired_micro[0]["path"]] == ["theme:cat", "theme:t", "theme:m"]
    retired_sub = _hp(
        FakeStore(sub_nodes, sub_live, lifecycle=[_lifecycle_retired("theme:sub")]),
        "theme:m",
    )
    assert [el["node_id"] for el in retired_sub[0]["path"]] == [
        "theme:cat", "theme:t", "theme:sub", "theme:m",
    ]


# F04 uses the display reader, never the internal neighborhood serialization.
def _selected_security_row(node_id='co:us:AAA', security_id='SEC:US-XNAS-AAA'):
    return dict(schema='gmi.identity_resolution/v1', node_id=node_id,
        graph_kind='company', market_scope='us', graph_identity_epoch=1,
        source_native_symbol='PRIVATE-NOT-A-JOIN', resolution_asof='2026-09-18',
        resolution_state='RESOLVED', issuer_id='ISS:US-XNAS-AAA', security_id=security_id,
        listing_key=security_id.removeprefix('SEC:'), join_method='vendor_alias',
        master_generated_at='2026-09-18T00:00:00Z', master_symbol_directory_snapshot=None,
        master_code_version='fixture', refusal_reason=None, source_receipts='PRIVATE-OWNER-RECEIPTS',
        computed_at='2026-09-18T17:42:27Z', engine_version='theme_graph.v1')


def _selected_house_view(*, second=False):
    nodes = [_company('co:us:AAA'), _basket('basket:baskets:solar'),
             _theme('macro:energy', 'macro_category'), _theme('theme:solar', 'theme'),
             _local_theme('ltheme:finviz:PRIVATE'), _basket('basket:baskets_china_ths:PRIVATE')]
    edges = [_parent_of('macro:energy', 'theme:solar'),
             _edge('member', 'MEMBER_OF', 'co:us:AAA', 'basket:baskets:solar'),
             _edge('express', 'EXPRESSES', 'basket:baskets:solar', 'theme:solar'),
             _edge('private-member', 'MEMBER_OF', 'co:us:AAA', 'ltheme:finviz:PRIVATE'),
             _edge('private-basket', 'MEMBER_OF', 'co:us:AAA', 'basket:baskets_china_ths:PRIVATE'),
             _edge('private-express', 'EXPRESSES', 'basket:baskets_china_ths:PRIVATE', 'theme:solar')]
    if second:
        nodes.append(_company('co:us:AAB'))
        edges.append(_edge('member-b', 'MEMBER_OF', 'co:us:AAB', 'basket:baskets:solar'))
    view = FakeStore(nodes, edges)
    view._evidence = [{**{c: None for c in store.EVIDENCE_COLUMNS},
        'evidence_id': 'ev:fixture', 'source_ref': 'config/theme_crosswalk.yml',
        'licensing_display_ok': True}]
    view.read_evidence = lambda: view._evidence
    return view


def _selected_hierarchy(rows=None, view=None, **kw):
    from engine.theme_graph.security_navigation import compose_security_hierarchy
    return compose_security_hierarchy(view or _selected_house_view(),
        [_selected_security_row()] if rows is None else rows,
        identity_kind=kw.pop('identity_kind', 'security'), identity_id=kw.pop('identity_id', 'SEC:US-XNAS-AAA'),
        asof=ASOF, knowledge_cutoff=kw.pop('knowledge_cutoff', ASOF), **kw)


def test_selected_house_display_retains_current_identity_and_no_private_graph():
    result = _selected_hierarchy()
    assert result['authority_ceiling'] == 'display_only'
    assert result['identity_basis'] == 'LATEST_PUBLISHED_OWNER_REFERENCE'
    assert result['historical_identity_claim'] is False
    assert result['availability']['state'] == 'AVAILABLE'
    binding = result['bindings'][0]
    assert binding['resolution']['computed_at'] == '2026-09-18T17:42:27Z'  # later than graph cutoff, deliberately current
    assert binding['paths'] == _hp(_selected_house_view(), 'co:us:AAA')
    encoded = json.dumps(result)
    assert 'PRIVATE' not in encoded and 'source_receipts' not in encoded
    assert all('neighborhood' not in b and 'relations' not in b for b in result['bindings'])
    assert result['etf_tracking']['status'] == 'unavailable'


def test_selected_house_issuer_preserves_all_share_classes():
    rows = [_selected_security_row(), _selected_security_row('co:us:AAB', 'SEC:US-XNAS-AAB')]
    result = _selected_hierarchy(rows=rows, view=_selected_house_view(second=True),
        identity_kind='issuer', identity_id='ISS:US-XNAS-AAA')
    assert len(result['bindings']) == 2
    assert {b['resolution']['security_id'] for b in result['bindings']} == {'SEC:US-XNAS-AAA', 'SEC:US-XNAS-AAB'}
    assert all(b['paths'] for b in result['bindings'])


@pytest.mark.parametrize('rows,state', [([], 'IDENTITY_OWNER_UNAVAILABLE'),
    ([_selected_security_row(security_id='SEC:US-XNAS-OTHER')], 'NO_GRAPH_BINDING')])
def test_selected_house_absence_is_not_no_themes(rows, state):
    result = _selected_hierarchy(rows=rows)
    assert result['availability']['state'] == state and result['bindings'] == []


@pytest.mark.parametrize('mutation', ['missing', 'retired', 'future', 'vendor_only'])
def test_selected_house_unqualified_subject_has_no_paths(mutation):
    view = _selected_house_view()
    if mutation == 'missing': view._nodes = [n for n in view._nodes if n['node_id'] != 'co:us:AAA']
    elif mutation == 'retired': view._nodes[0]['status'] = 'retired'
    elif mutation == 'future': view._nodes[0]['computed_at'] = '2030-01-01T00:00:00Z'
    else: view._edges = [e for e in view._edges if e['edge_id'] != 'member']
    result = _selected_hierarchy(view=view)
    assert result['availability']['state'] == 'NO_QUALIFIED_HOUSE_PATH'
    assert result['bindings'][0]['paths'] == []


def test_selected_house_keeps_intraday_knowledge_cutoff():
    view = _selected_house_view()
    view._edges[1]['belief_time'] = '2024-06-01T13:00:00Z'
    result = _selected_hierarchy(view=view, knowledge_cutoff='2024-06-01T12:00:00Z')
    assert result['bindings'][0]['paths'] == []
    result = _selected_hierarchy(view=view, knowledge_cutoff='2024-06-01T14:00:00Z')
    assert result['bindings'][0]['paths']
    assert result['knowledge_cutoff'] == '2024-06-01T14:00:00+00:00'


def test_selected_house_duplicate_identity_refuses():
    with pytest.raises(ValueError, match='duplicate'):
        _selected_hierarchy(rows=[_selected_security_row(), _selected_security_row()])


@pytest.mark.parametrize('mutation', ['vendor', 'missing', 'revoked', 'unmapped'])
def test_selected_house_refuses_unqualified_edge_evidence(mutation):
    view = _selected_house_view()
    if mutation == 'vendor': view._evidence[0]['source_ref'] = 'finviz_themes/private'
    elif mutation == 'missing': view._evidence.clear()
    elif mutation == 'revoked': view._evidence[0]['licensing_display_ok'] = False
    else: view._evidence[0]['source_ref'] = 'unknown/private'
    result = _selected_hierarchy(view=view)
    assert result['bindings'][0]['paths'] == []
    assert 'private' not in json.dumps(result)


# ETF009 remains a graph-native TRACKS reference, never a Data OS ETF join.
def _selected_etf_view(*, second=False):
    view = _selected_house_view(second=second)
    for edge in view._edges:
        if edge['type'] == 'MEMBER_OF' and edge['dst'] == 'basket:baskets:solar':
            edge.update(evidence_refs=['ev:membership'], confidence_basis='membership_doc.v1',
                        date_provenance='seed_constant')
    view._evidence.append({**{c: None for c in store.EVIDENCE_COLUMNS},
        'evidence_id': 'ev:membership', 'kind': 'operator_curation',
        'source_ref': 'data/baskets/membership.json', 'published_at': '2024-01-01',
        'computed_at': STAMP, 'licensing_display_ok': True})
    view._nodes.append(_blank_node(node_id='etf:AAAETF', kind='etf',
        provenance='membership_doc:baskets', market_scope='us',
        external_ids=json.dumps({'symbol': 'AAAETF'})))
    view._edges.append(_edge('tracks', 'TRACKS', 'etf:AAAETF', 'basket:baskets:solar',
        evidence_refs=['ev:tracking'], confidence_basis='membership_doc.v1', date_provenance='seed_constant'))
    view._evidence.append({**{c: None for c in store.EVIDENCE_COLUMNS},
        'evidence_id': 'ev:tracking', 'kind': 'operator_curation',
        'source_ref': 'data/baskets/membership.json', 'published_at': '2024-01-01',
        'computed_at': STAMP, 'licensing_display_ok': True})
    return view


def test_selected_etf_keeps_native_reference_clocks_and_no_fund_claim():
    from engine.theme_graph import rights
    view = _selected_etf_view()
    out = _selected_hierarchy(view=view)['etf_tracking']
    assert out['schema'] == 'gmi.theme_etf_tracking_display/v1'
    assert out['status'] == 'available' and out['exhaustive'] is False
    assert len(out['references']) == 1
    ref = out['references'][0]
    assert ref['binding_node_id'] == 'co:us:AAA'
    assert ref['selected_security_id'] == 'SEC:US-XNAS-AAA'
    assert ref['basket_node_id'] == 'basket:baskets:solar'
    assert ref['etf_node_id'] == 'etf:AAAETF' and ref['symbol'] == 'AAAETF'
    assert ref['clocks'] == {k: view._edges[-1][k] for k in
        ('valid_from', 'valid_to', 'evidence_time', 'belief_time', 'computed_at')}
    assert ref['era'] == 'reconstruction' and ref['date_provenance'] == 'seed_constant'
    assert ref['evidence'] == [{'evidence_id': 'ev:tracking', 'published_at': '2024-01-01', 'computed_at': STAMP}]
    assert out['security_identity']['status'] == 'unavailable'
    assert out['holdings'] == {'status': 'unavailable', 'asof': None}
    assert out['weights'] is None and out['performance'] is None
    assert not any(out['authority'].values())
    assert rights.family_for_node_id('etf:AAAETF') is None
    encoded = json.dumps(out)
    assert ref['membership']['basket']['node_id'] == 'basket:baskets:solar'
    assert 'name_en' not in ref and 'source_ref' not in encoded and 'PRIVATE' not in encoded


def test_selected_etf_native_membership_survives_missing_theme_hierarchy():
    view = _selected_etf_view()
    view._edges = [e for e in view._edges if e['type'] not in {'EXPRESSES', 'PARENT_OF'}]
    result = _selected_hierarchy(view=view)
    assert result['availability']['state'] == 'NO_QUALIFIED_HOUSE_PATH'
    assert result['bindings'][0]['paths'] == []
    ref, = result['etf_tracking']['references']
    assert ref['membership']['relationship'] == 'MEMBER_OF'
    assert ref['membership']['edge_id'] == 'member'
    assert ref['membership']['evidence'][0]['evidence_id'] == 'ev:membership'
    assert ref['etf_node_id'] == 'etf:AAAETF'


def test_selected_etf_normalizes_native_parquet_null_clocks():
    view = _selected_etf_view()
    for edge in view._edges:
        if edge['edge_id'] in {'member','tracks'}:
            edge['valid_to'] = float('nan')
    result = _selected_hierarchy(view=view)
    ref, = result['etf_tracking']['references']
    assert ref['clocks']['valid_to'] is None
    assert ref['membership']['clocks']['valid_to'] is None
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('mutation', ['missing','closed','future','undated','vendor','denied',
    'future_receipt','no_receipt','wrong_basis','duplicate_basket','retired_basket','retired_company'])
def test_selected_etf_membership_is_independently_qualified(mutation):
    view = _selected_etf_view()
    view._edges = [e for e in view._edges if e['type'] not in {'EXPRESSES', 'PARENT_OF'}]
    member = next(e for e in view._edges if e['edge_id']=='member')
    receipt = next(e for e in view._evidence if e['evidence_id']=='ev:membership')
    basket = next(n for n in view._nodes if n['node_id']=='basket:baskets:solar')
    if mutation == 'missing': view._edges.remove(member)
    elif mutation == 'closed': member['valid_to'] = ASOF
    elif mutation == 'future': member['belief_time'] = '2025-01-01'
    elif mutation == 'undated': member['computed_at'] = None
    elif mutation == 'vendor': receipt['source_ref'] = 'finviz_themes/private'
    elif mutation == 'denied': receipt['licensing_display_ok'] = False
    elif mutation == 'future_receipt': receipt['published_at'] = '2025-01-01'
    elif mutation == 'no_receipt': receipt['published_at'] = None
    elif mutation == 'wrong_basis': member['confidence_basis'] = 'crosswalk.v1'
    elif mutation == 'duplicate_basket': view._nodes.append(copy.deepcopy(basket))
    elif mutation == 'retired_basket': basket['status'] = 'retired'
    else: next(n for n in view._nodes if n['node_id']=='co:us:AAA')['status'] = 'retired'
    assert _selected_hierarchy(view=view)['etf_tracking']['references'] == []


@pytest.mark.parametrize('mutation', ['vendor', 'unmapped', 'missing', 'snapshot_false',
    'undated', 'future_published', 'future_computed', 'missing_computed', 'mixed_vendor', 'duplicate_ref'])
def test_selected_etf_requires_each_current_house_dated_evidence(mutation):
    view = _selected_etf_view()
    evidence = view._evidence[-1]
    if mutation == 'vendor': evidence['source_ref'] = 'data/baskets_china_ths/private'
    elif mutation == 'unmapped': evidence['source_ref'] = 'unknown/private'
    elif mutation == 'missing': view._evidence.pop()
    elif mutation == 'snapshot_false': evidence['licensing_display_ok'] = False
    elif mutation == 'undated': evidence['published_at'] = None
    elif mutation == 'future_published': evidence['published_at'] = '2025-01-01'
    elif mutation == 'future_computed': evidence['computed_at'] = '2025-01-01T00:00:00Z'
    elif mutation == 'missing_computed': evidence['computed_at'] = None
    elif mutation == 'mixed_vendor':
        view._evidence.append({**evidence, 'evidence_id': 'private', 'source_ref': 'finviz_themes/private'})
        view._edges[-1]['evidence_refs'].append('private')
    else: view._edges[-1]['evidence_refs'].append('ev:tracking')
    out = _selected_hierarchy(view=view)
    assert out['bindings'][0]['paths']  # unrelated qualified company reading survives
    assert out['etf_tracking']['status'] == 'unavailable'
    assert out['etf_tracking']['references'] == []
    assert 'private' not in json.dumps(out['etf_tracking']).lower()


@pytest.mark.parametrize('mutation', ['closed', 'future_belief', 'future_effective', 'missing_symbol',
    'symbol_mismatch', 'retired', 'future_node', 'duplicate_node', 'wrong_kind', 'missing_edge_clock',
    'future_edge_clock', 'unknown_era', 'unknown_date_basis', 'other_basket', 'reverse_tracks', 'not_tracks'])
def test_selected_etf_requires_native_visible_identity_and_selected_basket(mutation):
    view = _selected_etf_view()
    edge, etf = view._edges[-1], view._nodes[-1]
    if mutation == 'closed': edge['valid_to'] = ASOF
    elif mutation == 'future_belief': edge['belief_time'] = '2025-01-01'
    elif mutation == 'future_effective': edge['valid_from'] = '2025-01-01'
    elif mutation == 'missing_symbol': etf['external_ids'] = '{}'
    elif mutation == 'symbol_mismatch': etf['external_ids'] = json.dumps({'symbol': 'OTHER'})
    elif mutation == 'retired': etf['status'] = 'retired'
    elif mutation == 'future_node': etf['computed_at'] = '2025-01-01T00:00:00Z'
    elif mutation == 'duplicate_node': view._nodes.append(copy.deepcopy(etf))
    elif mutation == 'wrong_kind': etf['kind'] = 'company'
    elif mutation == 'missing_edge_clock': edge['computed_at'] = None
    elif mutation == 'future_edge_clock': edge['computed_at'] = '2025-01-01T00:00:00Z'
    elif mutation == 'unknown_era': edge['era'] = None
    elif mutation == 'unknown_date_basis': edge['date_provenance'] = None
    elif mutation == 'other_basket': edge['dst'] = 'basket:baskets:unselected'
    elif mutation == 'reverse_tracks': edge['src'], edge['dst'] = edge['dst'], edge['src']
    else: edge['type'] = 'RELATED'
    assert _selected_hierarchy(view=view)['etf_tracking']['references'] == []


@pytest.mark.parametrize('rights_class,auth', [('internal_only','house'),('unresolved','house'),
    ('direct_display_ok','licensed'),('unknown','house')])
def test_selected_etf_current_policy_revocation_overrides_true_mint_flag(rights_class,auth):
    out = _selected_hierarchy(view=_selected_etf_view(), source_policy={
        'families': {'mastermind_curated': {'rights_class': rights_class, 'auth_class': auth}}})
    assert out['etf_tracking']['reason'] == 'HOUSE_DISPLAY_PERMISSION_UNAVAILABLE'
    assert out['etf_tracking']['references'] == []


def test_selected_etf_policy_is_read_fresh_not_native_memoized(tmp_path, monkeypatch):
    from engine.theme_graph import rights
    registry = tmp_path / 'policy.yml'
    monkeypatch.setattr(rights, 'registry_path', lambda: registry)
    registry.write_text('families: {mastermind_curated: {rights_class: direct_display_ok, auth_class: house}}')
    # Warm the incumbent native cache, then revoke the actual current bytes.
    assert rights.emission_allowed('mastermind_curated')
    registry.write_text('families: {mastermind_curated: {rights_class: internal_only, auth_class: house}}')
    try:
        assert _selected_hierarchy(view=_selected_etf_view())['etf_tracking']['references'] == []
    finally:
        rights._load.cache_clear()


def test_selected_etf_issuer_keeps_share_class_associations():
    out = _selected_hierarchy(view=_selected_etf_view(second=True),
        rows=[_selected_security_row(),_selected_security_row('co:us:AAB','SEC:US-XNAS-AAB')],
        identity_kind='issuer',identity_id='ISS:US-XNAS-AAA')['etf_tracking']
    assert {(r['binding_node_id'],r['selected_security_id']) for r in out['references']} == {
        ('co:us:AAA','SEC:US-XNAS-AAA'),('co:us:AAB','SEC:US-XNAS-AAB')}


def test_selected_etf_latest_known_withdrawal_and_future_withdrawal():
    view = _selected_etf_view()
    closed = {**view._edges[-1], 'belief_time': '2024-05-01', 'valid_to': ASOF,
        'computed_at': '2024-05-01T00:00:00Z'}
    view._edges.append(closed)
    assert _selected_hierarchy(view=view)['etf_tracking']['references'] == []
    closed['belief_time'] = '2025-01-01'
    assert len(_selected_hierarchy(view=view)['etf_tracking']['references']) == 1


def test_selected_etf_date_only_belief_keeps_native_intraday_conservatism():
    view = _selected_etf_view()
    view._edges[-1]['belief_time'] = ASOF
    assert _selected_hierarchy(view=view, knowledge_cutoff=ASOF+'T12:00:00Z')['etf_tracking']['references'] == []
    assert len(_selected_hierarchy(view=view, knowledge_cutoff='2024-06-02T00:00:00Z')['etf_tracking']['references']) == 1


def test_selected_etf_reference_bound_withholds_instead_of_partial_coverage():
    view = _selected_etf_view()
    for i in range(129):
        symbol = 'FUND'+str(i)
        view._nodes.append({**view._nodes[-1], 'node_id':'etf:'+symbol, 'external_ids':json.dumps({'symbol':symbol})})
        view._edges.append({**view._edges[-1], 'edge_id':'tracks:'+str(i), 'src':'etf:'+symbol})
    out = _selected_hierarchy(view=view)['etf_tracking']
    assert out['reason'] == 'ETF_REFERENCE_BOUND_EXCEEDED' and out['references'] == []


@pytest.mark.parametrize('house', [None, True, 'unreviewed'])
def test_selected_etf_unreadable_current_policy_is_typed_unavailable(house):
    result = _selected_hierarchy(view=_selected_etf_view(),
        source_policy={'families': {'mastermind_curated': house}})
    assert result['etf_tracking']['reason'] == 'HOUSE_DISPLAY_PERMISSION_UNAVAILABLE'
    assert result['etf_tracking']['references'] == []


def _etf_adoption_inputs(tmp_path, monkeypatch, *, etf=True):
    import io
    import pandas as pd
    from tests import test_symbol_directory_completion_receipts as listing
    frame = listing._listing_frame()
    frame.loc[0,['symbol','etf']] = ['AAAETF',etf]
    monkeypatch.setattr(listing,'_listing_frame',lambda:frame)
    artifact, sidecar, _ = listing._listing_receipt(tmp_path)
    def parquet(rows):
        out=io.BytesIO();pd.DataFrame(rows).to_parquet(out,index=False);return out.getvalue()
    master=[{'security_id':'SEC:US-XNAS-DIFFERENT','listing_key':'US-XNAS-DIFFERENT',
        'country':'US','mic':'XNAS','inception_code':'DIFFERENT','security_state':None}]
    aliases=[{'vendor':'membership','vendor_symbol':'AAAETF','security_id':master[0]['security_id'],
        'valid_from':None,'valid_to':None,'ingested_at':'2026-08-11T00:00:00Z'}]
    receipt={'producer':'scripts/build_security_master.py','authority':{'identity_authority':'canonical_exact_identity'},
        'dataset_ids':['reference.security_master','reference.vendor_aliases'],
        'symbol_directory_snapshot':'2026-08-10','generated_at':'2026-08-11T00:00:00Z',
        'inputs':{'data/symbol_directory/snapshots':hashlib.sha256(artifact.read_bytes()).hexdigest()},
        'row_counts':{'security_master':1,'vendor_alias_rows_readable':1}}
    sources={'data/reference/_receipt.json':json.dumps(receipt).encode(),
        'data/reference/security_master.parquet':parquet(master),
        'data/reference/vendor_aliases.parquet':parquet(aliases),
        'data/symbol_directory/snapshots/2026-08-10.parquet':artifact.read_bytes(),
        'data/symbol_directory/receipts/snapshots/2026-08-10.json':sidecar.read_bytes()}
    return _selected_etf_view(),sources,master,aliases,receipt,parquet


def _adopt_etf(view, sources):
    from engine.theme_graph.identity_resolution import adopt_etf_references
    return adopt_etf_references(view._nodes,view._lifecycle,['etf:AAAETF'],sources,
        now=datetime(2026,10,19,tzinfo=timezone.utc))['etf:AAAETF']


def test_etf_adoption_uses_canonical_alias_not_graph_spelling_and_keeps_type_observation(tmp_path,monkeypatch):
    view,sources,*_ = _etf_adoption_inputs(tmp_path,monkeypatch)
    before=copy.deepcopy(view._nodes)
    result=_adopt_etf(view,sources)
    assert result['status']=='available'
    assert result['security_id']=='SEC:US-XNAS-DIFFERENT'  # graph is AAAETF
    assert result['listing_key']=='US-XNAS-DIFFERENT'
    assert result['identity_basis']=='LATEST_PUBLISHED_DATAOS_VENDOR_ALIAS'
    assert result['historical_identity_claim'] is False
    assert result['instrument_type']=='ETF'
    assert result['instrument_type_basis']=='NATIVE_LISTING_OBSERVATION_ONLY'
    assert result['listing_observed_on']=='2026-08-10'
    assert result['listing_known_at']=='2026-08-10T00:00:04.000000Z'
    assert 'issuer_id' not in result and 'name' not in result and view._nodes==before


@pytest.mark.parametrize('mutation',['missing_alias','ambiguous_alias','active_wrapper','retired_wrapper',
    'inactive_security','classification_bytes','future_master','foreign_listing_generation','wrong_venue'])
def test_etf_adoption_preserves_native_identity_refusals(tmp_path,monkeypatch,mutation):
    view,sources,master,aliases,receipt,parquet = _etf_adoption_inputs(tmp_path,monkeypatch)
    if mutation=='missing_alias':aliases[0]['vendor_symbol']='OTHER'
    elif mutation=='ambiguous_alias':
        master.append({**master[0],'security_id':'SEC:US-XNAS-OTHER','listing_key':'US-XNAS-OTHER'})
        aliases.append({**aliases[0],'vendor':'yahoo','security_id':'SEC:US-XNAS-OTHER'})
    elif mutation in {'active_wrapper','retired_wrapper'}:
        view._nodes.append(_company('co:us:AAAETF',external_ids=json.dumps({'symbol':'AAAETF'})))
        if mutation=='retired_wrapper':
            view._lifecycle.append(dict(node_id='co:us:AAAETF',status='retired',retire_date='2026-08-22',
                merged_into=None,computed_at='2026-08-22T00:00:00Z'))
    elif mutation=='inactive_security':master[0]['security_state']='SUPERSEDED_DUPLICATE_MINT'
    elif mutation=='classification_bytes':sources['data/symbol_directory/snapshots/2026-08-10.parquet']+=b'changed'
    elif mutation=='future_master':receipt['generated_at']='2027-01-01T00:00:00Z'
    elif mutation=='foreign_listing_generation':receipt['inputs']['data/symbol_directory/snapshots']='0'*64
    else:master[0].update(security_id='SEC:US-XNYS-DIFFERENT',listing_key='US-XNYS-DIFFERENT',mic='XNYS');aliases[0]['security_id']=master[0]['security_id']
    receipt['row_counts']={'security_master':len(master),'vendor_alias_rows_readable':len(aliases)}
    sources['data/reference/_receipt.json']=json.dumps(receipt).encode()
    sources['data/reference/security_master.parquet']=parquet(master)
    sources['data/reference/vendor_aliases.parquet']=parquet(aliases)
    result=_adopt_etf(view,sources)
    assert result['status']==('available' if mutation=='retired_wrapper' else 'unavailable')
    if mutation=='active_wrapper':assert result['reason']=='AMBIGUOUS_ACTIVE_COMPANY_WRAPPER'
    elif mutation=='ambiguous_alias':assert result['reason']=='AMBIGUOUS_CANONICAL_ALIAS'
    if result['status']!='available':assert 'security_id' not in result


def test_etf_adoption_requires_explicit_native_instrument_flag(tmp_path,monkeypatch):
    view,sources,*_=_etf_adoption_inputs(tmp_path,monkeypatch,etf=False)
    assert _adopt_etf(view,sources)=={'status':'unavailable','reason':'ETF_INSTRUMENT_TYPE_UNQUALIFIED'}
