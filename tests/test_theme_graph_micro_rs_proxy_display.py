"""Micro-theme RS proxy display reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L13).

Display-tier only. These tests pin the frozen envelope shape, the proxy
ancestor walk over PARENT_OF, the EXPRESSES instrument projection, the Gate #2
vendor-id filters and the typed refusal semantics. Frames are always injected
in-memory; the store is never read except through the counted-loader test.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from engine.classification_axes.cell import FORBIDDEN_VALUE_KEY_WORDS
from engine.theme_graph import micro_rs_proxy_display as mod
from engine.theme_graph import store

# ---------------------------------------------------------------------------
# Fixture builders (small in-memory frames; data/** is never read)
# ---------------------------------------------------------------------------

NODE_COLUMNS = [
    "node_id", "kind", "name_en", "name_zh", "market_scope", "tier", "status",
    "merged_into", "source_meta",
]

EDGE_COLUMNS = [
    "edge_id", "type", "src", "dst", "valid_from", "valid_to",
    "economic_share", "trading_beta", "attention_share",
]


def _node(node_id, tier, *, kind="theme", status="active", merged_into=None):
    return {
        "node_id": node_id,
        "kind": kind,
        "name_en": node_id.split(":", 1)[-1],
        "name_zh": None,
        "market_scope": "global",
        "tier": tier,
        "status": status,
        "merged_into": merged_into,
        "source_meta": None,
    }


def _edge(edge_id, etype, src, dst, *, valid_to=None, economics=False):
    row = {
        "edge_id": edge_id,
        "type": etype,
        "src": src,
        "dst": dst,
        "valid_from": "2026-01-01",
        "valid_to": valid_to,
        "economic_share": 0.42 if economics else None,
        "trading_beta": 1.7 if economics else None,
        "attention_share": 0.11 if economics else None,
    }
    return row


def _frames(nodes, edges):
    """Frames with an active basket/etf row added for every house EXPRESSES
    source — in the real store every instrument is a node row, and the reader
    drops an instrument whose source is not a present, active node."""
    have = {row["node_id"] for row in nodes}
    derived: list[dict] = []
    for row in edges:
        src = row["src"]
        if row["type"] != "EXPRESSES" or src in have or src.startswith("ltheme:"):
            continue
        have.add(src)
        kind = "etf" if src.startswith("etf:") else "basket"
        derived.append(_node(src, None, kind=kind))
    return (
        pd.DataFrame(nodes + derived, columns=NODE_COLUMNS),
        pd.DataFrame(edges, columns=EDGE_COLUMNS),
    )


def _hierarchy_frames():
    """theme:space → (sub) theme:space_orbital → (micro) theme:space_launch,
    plus a direct theme parent hop used by several cases."""
    nodes = [
        _node("theme:space", "theme"),
        _node("theme:space_orbital", "sub_theme"),
        _node("theme:space_launch", "micro_theme"),
        _node("theme:space_human", "micro_theme"),
    ]
    edges = [
        _edge("p1", "PARENT_OF", "theme:space", "theme:space_orbital"),
        _edge("p2", "PARENT_OF", "theme:space_orbital", "theme:space_launch"),
        _edge("p3", "PARENT_OF", "theme:space", "theme:space_human"),
    ]
    return _frames(nodes, edges)


def _forbidden_keys(value, path="value"):
    problems = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            for word in FORBIDDEN_VALUE_KEY_WORDS:
                if word in lowered:
                    problems.append(f"{path}.{key} contains {word!r}")
                    break
            problems.extend(_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for position, child in enumerate(value):
            problems.extend(_forbidden_keys(child, f"{path}[{position}]"))
    return problems


def _with_edges(nodes, edges, new_edges):
    """Extend a fixture with edges, deriving node rows for any NEW house
    EXPRESSES source (the reader keeps only instruments that are live nodes)."""
    derived, added = _frames([], new_edges)
    derived = derived[~derived["node_id"].isin(set(nodes["node_id"]))]
    return (
        pd.concat([nodes, derived], ignore_index=True),
        pd.concat([edges, added], ignore_index=True),
    )


@pytest.fixture
def hierarchy():
    return _hierarchy_frames()


# ---------------------------------------------------------------------------
# Envelope shape
# ---------------------------------------------------------------------------

def test_available_envelope_shape(hierarchy):
    nodes, edges = hierarchy
    env = mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges)
    assert set(env) == {
        "schema_version", "subject_id", "status", "reason_code",
        "value", "labels", "quality", "source",
    }
    assert env["schema_version"] == "gmi.micro_rs_proxy_display.v1"
    assert env["subject_id"] == "theme:space_launch"
    assert env["status"] == "available"
    assert env["reason_code"] is None
    assert env["labels"] == ["proxy_not_micro_membership"]
    assert env["quality"] == "display_only"
    assert env["source"] == {
        "owner": "engine/theme_graph/store.py",
        "artifact": "data/theme_graph/nodes.parquet+edges.parquet",
        "field": "PARENT_OF+EXPRESSES",
    }
    assert set(env["value"]) == {
        "tier", "proxy_themes", "proxy_instruments",
        "proxy_instrument_count", "path_kind",
    }


def test_non_available_envelope_carries_null_value_and_reason(hierarchy):
    nodes, edges = hierarchy
    for env in (
        mod.read_micro_rs_proxy("theme:space", nodes=nodes, edges=edges),  # theme tier
        mod.read_micro_rs_proxy("theme:missing", nodes=nodes, edges=edges),  # absent
        mod.read_micro_rs_proxy("theme:orphan_none", nodes=nodes, edges=edges),
    ):
        assert env["reason_code"] is not None
        assert env["value"] is None
        assert env["status"] in ("unknown", "not_applicable")


# ---------------------------------------------------------------------------
# Proxy ancestor walk + instrument projection
# ---------------------------------------------------------------------------

def test_micro_via_sub_theme(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes, edges, [_edge("e1", "EXPRESSES", "basket:baskets:space_etf", "theme:space")]
    )
    env = mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["tier"] == "micro_theme"
    assert env["value"]["proxy_themes"] == ["theme:space"]
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:space_etf"}
    ]
    assert env["value"]["proxy_instrument_count"] == 1
    assert env["value"]["path_kind"] == "via_sub_theme"


def test_micro_direct_under_theme(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes, edges, [_edge("e1", "EXPRESSES", "basket:baskets:robo", "theme:space")]
    )
    env = mod.read_micro_rs_proxy("theme:space_human", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_themes"] == ["theme:space"]
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:robo"}
    ]
    assert env["value"]["path_kind"] == "direct_theme"


def test_both_paths_dedupe():
    # A micro under BOTH its sub_theme and the theme directly: both routes meet
    # on one deduped ancestor, and the instruments are not duplicated either.
    nodes, edges = _frames(
        [
            _node("theme:space", "theme"),
            _node("theme:space_orbital", "sub_theme"),
            _node("theme:twin", "micro_theme"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:space", "theme:space_orbital"),
            _edge("p2", "PARENT_OF", "theme:space_orbital", "theme:twin"),
            _edge("p3", "PARENT_OF", "theme:space", "theme:twin"),
            _edge("e1", "EXPRESSES", "basket:baskets:a", "theme:space"),
            _edge("e2", "EXPRESSES", "basket:baskets:robo", "theme:space"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:twin", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_themes"] == ["theme:space"]  # deduped
    assert env["value"]["path_kind"] == "both"
    assert env["value"]["proxy_instrument_count"] == 2
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:a"},
        {"theme_id": "theme:space", "src_id": "basket:baskets:robo"},
    ]


def test_sub_theme_subject(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes, edges, [_edge("e1", "EXPRESSES", "basket:baskets:orb", "theme:space")]
    )
    env = mod.read_micro_rs_proxy("theme:space_orbital", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["tier"] == "sub_theme"
    assert env["value"]["proxy_themes"] == ["theme:space"]
    assert env["value"]["path_kind"] == "direct_theme"
    assert env["value"]["proxy_instrument_count"] == 1


def test_sub_theme_subject_uses_direct_theme_parents_only():
    # A sub_theme parent hop is a micro-only route (SPEC §1 adjacency): a
    # sub_theme subject reads only its own theme parents, never upward
    # through another sub_theme.
    nodes, edges = _frames(
        [
            _node("theme:grid", "theme"),
            _node("theme:grid_storage", "sub_theme"),
            _node("theme:grid_nested", "sub_theme"),
            _node("theme:grid_cells", "sub_theme"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:grid_storage", "theme:grid_nested"),
            _edge("p2", "PARENT_OF", "theme:grid_nested", "theme:grid_cells"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:grid_cells", nodes=nodes, edges=edges)
    assert env["status"] == "unknown"
    assert env["reason_code"] == "value_missing"


def test_orphan_micro_is_unknown_value_missing():
    nodes, edges = _frames([_node("theme:lonely", "micro_theme")], [])
    env = mod.read_micro_rs_proxy("theme:lonely", nodes=nodes, edges=edges)
    assert env["status"] == "unknown"
    assert env["reason_code"] == "value_missing"
    assert env["value"] is None
    assert env["labels"] == ["proxy_not_micro_membership"]


def test_retired_ancestor_theme_excluded(hierarchy):
    nodes, edges = _frames(
        [
            _node("theme:space", "theme"),
            _node("theme:space_old", "theme", status="retired"),
            _node("theme:space_orbital", "sub_theme"),
            _node("theme:space_energy", "sub_theme"),
            _node("theme:space_launch", "micro_theme"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:space", "theme:space_orbital"),
            _edge("p2", "PARENT_OF", "theme:space_orbital", "theme:space_launch"),
            _edge("p3", "PARENT_OF", "theme:space_old", "theme:space_energy"),
            _edge("p4", "PARENT_OF", "theme:space_energy", "theme:space_launch"),
            _edge("e1", "EXPRESSES", "basket:baskets:new", "theme:space"),
            _edge("e2", "EXPRESSES", "basket:baskets:old", "theme:space_old"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_themes"] == ["theme:space"]
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:new"}
    ]


def test_closed_expresses_edge_ignored(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes,
        edges,
        [
            _edge("e_open", "EXPRESSES", "basket:baskets:robo", "theme:space"),
            _edge("e_closed", "EXPRESSES", "etf:OLD", "theme:space", valid_to="2026-09-30"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:space_human", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:robo"}
    ]
    assert env["value"]["proxy_instrument_count"] == 1


# ---------------------------------------------------------------------------
# Gate #2 filters
# ---------------------------------------------------------------------------

def test_ltheme_src_filtered_but_ltheme_only_theme_stays_available(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes,
        edges,
        [
            _edge("e1", "EXPRESSES", "ltheme:finviz:robotics", "theme:space"),
            _edge("e2", "EXPRESSES", "basket:baskets:robo", "theme:space"),
            _edge("e3", "EXPRESSES", "ltheme:ths:space", "theme:space"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:space_human", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:space", "src_id": "basket:baskets:robo"}
    ]

    # A theme whose ONLY instrument sources are vendor-local: empty instruments,
    # still available — the proxy path exists, it just carries no instruments.
    nodes2, edges2 = _frames(
        [
            _node("theme:solar", "theme"),
            _node("theme:solar_panels", "micro_theme"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:solar", "theme:solar_panels"),
            _edge("e1", "EXPRESSES", "ltheme:finviz:solar", "theme:solar"),
        ],
    )
    env2 = mod.read_micro_rs_proxy("theme:solar_panels", nodes=nodes2, edges=edges2)
    assert env2["status"] == "available"
    assert env2["value"]["proxy_themes"] == ["theme:solar"]
    assert env2["value"]["proxy_instruments"] == []
    assert env2["value"]["proxy_instrument_count"] == 0


def test_internal_only_subject_and_instruments_never_emitted():
    nodes, edges = _frames(
        [_node("theme:grid", "theme"), _node("theme:grid_micro", "micro_theme")],
        [
            _edge("p1", "PARENT_OF", "theme:grid", "theme:grid_micro"),
            _edge("e1", "EXPRESSES", "basket:finviz_themes:one", "theme:grid"),
            _edge("e2", "EXPRESSES", "basket:baskets:ok", "theme:grid"),
        ],
    )
    env = mod.read_micro_rs_proxy("ltheme:finviz:grid", nodes=nodes, edges=edges)
    assert env["status"] == "not_applicable"
    assert env["reason_code"] == "not_applicable"
    assert env["value"] is None
    # A theme id carrying an internal suite token is filtered from the output.
    nodes2, edges2 = _frames(
        [_node("theme:grid_ths_concepts", "theme"), _node("theme:gm", "micro_theme")],
        [_edge("p1", "PARENT_OF", "theme:grid_ths_concepts", "theme:gm")],
    )
    env2 = mod.read_micro_rs_proxy("theme:gm", nodes=nodes2, edges=edges2)
    assert env2["status"] == "unknown"
    assert env2["reason_code"] == "value_missing"


def test_vendor_derived_instrument_refused_by_rights_registry():
    """``basket:baskets_china_ths:*`` does not spell its vendor in the id, so
    only the rights registry knows it is ``ths_concepts`` (internal_only)."""
    nodes, edges = _frames(
        [
            _node("theme:grid", "theme"),
            _node("theme:grid_micro", "micro_theme"),
            _node("basket:baskets_china_ths:ths_grid", None, kind="basket"),
            _node("basket:baskets:ok", None, kind="basket"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:grid", "theme:grid_micro"),
            _edge("e1", "EXPRESSES", "basket:baskets_china_ths:ths_grid", "theme:grid"),
            _edge("e2", "EXPRESSES", "basket:baskets:ok", "theme:grid"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:grid_micro", nodes=nodes, edges=edges)
    assert env["value"]["proxy_instruments"] == [
        {"theme_id": "theme:grid", "src_id": "basket:baskets:ok"}
    ]
    assert "ths" not in repr(env)


def test_unmapped_instrument_family_fails_closed():
    nodes, edges = _frames(
        [
            _node("theme:grid", "theme"),
            _node("theme:grid_micro", "micro_theme"),
            _node("etf:GRID", None, kind="basket"),
        ],
        [
            _edge("p1", "PARENT_OF", "theme:grid", "theme:grid_micro"),
            _edge("e1", "EXPRESSES", "etf:GRID", "theme:grid"),
        ],
    )
    env = mod.read_micro_rs_proxy("theme:grid_micro", nodes=nodes, edges=edges)
    assert env["status"] == "available"
    assert env["value"]["proxy_instruments"] == []
    assert env["value"]["proxy_instrument_count"] == 0


# ---------------------------------------------------------------------------
# Subject eligibility
# ---------------------------------------------------------------------------

def test_theme_tier_and_non_theme_subjects_not_applicable(hierarchy):
    nodes, edges = hierarchy
    company = pd.DataFrame(
        [_node("co:us:ACME", None, kind="company")], columns=NODE_COLUMNS
    )
    both = pd.concat([nodes, company], ignore_index=True)
    assert mod.read_micro_rs_proxy("theme:space", nodes=both, edges=edges)[
        "reason_code"
    ] == "not_applicable"
    macro = pd.DataFrame(
        [_node("theme:tech", "macro_category")], columns=NODE_COLUMNS
    )
    assert mod.read_micro_rs_proxy("theme:tech", nodes=macro, edges=edges)[
        "reason_code"
    ] == "not_applicable"
    assert mod.read_micro_rs_proxy("co:us:ACME", nodes=both, edges=edges) == {
        "schema_version": mod.SCHEMA_VERSION,
        "subject_id": "co:us:ACME",
        "status": "not_applicable",
        "reason_code": "not_applicable",
        "value": None,
        "labels": ["proxy_not_micro_membership"],
        "quality": "display_only",
        "source": mod.SOURCE,
    }


def test_subject_absent_from_nodes_is_unknown():
    nodes, edges = _frames([_node("theme:space", "theme")], [])
    env = mod.read_micro_rs_proxy("theme:nowhere", nodes=nodes, edges=edges)
    assert env["status"] == "unknown"
    assert env["reason_code"] == "value_missing"


def test_retired_and_merged_subject_refusals(hierarchy):
    nodes, edges = hierarchy
    nodes = pd.DataFrame(
        [
            _node("theme:space", "theme"),
            _node("theme:space_orbital", "sub_theme"),
            _node("theme:space_launch", "micro_theme", status="retired"),
            _node("theme:space_human", "micro_theme", status="merged", merged_into="theme:space_launch"),
        ],
        columns=NODE_COLUMNS,
    )
    retired = mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges)
    assert retired["status"] == "not_applicable"
    assert retired["reason_code"] == "retired_entity"
    assert retired["value"] is None
    merged = mod.read_micro_rs_proxy("theme:space_human", nodes=nodes, edges=edges)
    assert merged["status"] == "not_applicable"
    assert merged["reason_code"] == "superseded_entity"


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

def test_table_covers_active_micro_and_sub_sorted(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes, edges, [_edge("e1", "EXPRESSES", "basket:baskets:robo", "theme:space")]
    )
    table = mod.micro_rs_proxy_table(nodes=nodes, edges=edges)
    subjects = [env["subject_id"] for env in table]
    assert subjects == sorted(subjects)
    assert subjects == ["theme:space_human", "theme:space_launch", "theme:space_orbital"]
    by_id = {env["subject_id"]: env for env in table}
    assert by_id["theme:space_launch"]["value"]["path_kind"] == "via_sub_theme"
    assert by_id["theme:space_human"]["value"]["path_kind"] == "direct_theme"
    assert by_id["theme:space_orbital"]["value"]["tier"] == "sub_theme"


def test_table_excludes_retired_subjects(hierarchy):
    nodes, edges = hierarchy
    nodes = pd.concat(
        [
            nodes,
            pd.DataFrame(
                [_node("theme:space_dead", "micro_theme", status="retired")],
                columns=NODE_COLUMNS,
            ),
        ],
        ignore_index=True,
    )
    table = mod.micro_rs_proxy_table(nodes=nodes, edges=edges)
    assert "theme:space_dead" not in [env["subject_id"] for env in table]


def test_store_inputs_loaded_at_most_once(hierarchy, monkeypatch):
    nodes, edges = hierarchy
    calls = {"nodes": 0, "edges": 0}

    def counting_nodes(**kwargs):
        calls["nodes"] += 1
        assert kwargs.get("current") is True
        return nodes

    def counting_edges(**kwargs):
        calls["edges"] += 1
        assert kwargs == {}
        return edges

    monkeypatch.setattr(mod.store, "read_nodes", counting_nodes)
    monkeypatch.setattr(mod.store, "read_edges", counting_edges)
    table = mod.micro_rs_proxy_table()
    assert calls == {"nodes": 1, "edges": 1}
    assert len(table) == 3
    single = mod.read_micro_rs_proxy("theme:space_launch")
    assert calls == {"nodes": 2, "edges": 2}
    assert single["subject_id"] == "theme:space_launch"


# ---------------------------------------------------------------------------
# Display-tier invariants
# ---------------------------------------------------------------------------

def test_labels_present_on_every_envelope():
    frames = [_hierarchy_frames(), _frames([_node("theme:lonely", "micro_theme")], [])]
    envelopes: list[dict] = []
    for nodes, edges in frames:
        envelopes.append(mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges))
        envelopes.extend(mod.micro_rs_proxy_table(nodes=nodes, edges=edges))
    for env in envelopes:
        assert env["labels"] == ["proxy_not_micro_membership"]
        assert env["quality"] == "display_only"


def test_no_forbidden_keys_or_economics_leak_into_output(hierarchy):
    nodes, edges = hierarchy
    nodes, edges = _with_edges(
        nodes,
        edges,
        [
            _edge("e1", "EXPRESSES", "basket:baskets:robo", "theme:space", economics=True),
            _edge("p9", "PARENT_OF", "theme:space", "theme:space_orbital"),
        ],
    )
    outputs = [
        mod.read_micro_rs_proxy("theme:space_launch", nodes=nodes, edges=edges),
        mod.read_micro_rs_proxy("theme:space_orbital", nodes=nodes, edges=edges),
        mod.read_micro_rs_proxy("theme:space", nodes=nodes, edges=edges),
        mod.micro_rs_proxy_table(nodes=nodes, edges=edges),
    ]
    for output in outputs:
        assert _forbidden_keys(output) == []
        text = json.dumps(output)
        for word in FORBIDDEN_VALUE_KEY_WORDS:
            assert word not in text
        for column in ("economic_share", "trading_beta", "attention_share"):
            assert column not in text
    # The instrument projection carries exactly the two identity keys.
    instruments = outputs[0]["value"]["proxy_instruments"]
    for instrument in instruments:
        assert set(instrument) == {"theme_id", "src_id"}


def test_deterministic_under_shuffled_frames():
    nodes_rows = [
        _node("theme:space", "theme"),
        _node("theme:space_orbital", "sub_theme"),
        _node("theme:space_launch", "micro_theme"),
        _node("theme:space_human", "micro_theme"),
        _node("theme:grid", "theme"),
        _node("theme:grid_micro", "micro_theme"),
        _node("basket:baskets:robo", None, kind="etf"),
        _node("basket:baskets:space_etf", None, kind="basket"),
    ]
    edges_rows = [
        _edge("p1", "PARENT_OF", "theme:space", "theme:space_orbital"),
        _edge("p2", "PARENT_OF", "theme:space_orbital", "theme:space_launch"),
        _edge("p3", "PARENT_OF", "theme:space", "theme:space_human"),
        _edge("p4", "PARENT_OF", "theme:grid", "theme:grid_micro"),
        _edge("e1", "EXPRESSES", "basket:baskets:robo", "theme:space"),
        _edge("e2", "EXPRESSES", "basket:baskets:space_etf", "theme:space"),
    ]
    nodes_a, edges_a = _frames(nodes_rows, edges_rows)
    nodes_b, edges_b = _frames(nodes_rows, edges_rows)
    nodes_b = nodes_b.sample(frac=1.0, random_state=7).reset_index(drop=True)
    edges_b = edges_b.sample(frac=1.0, random_state=11).reset_index(drop=True)
    assert json.dumps(mod.micro_rs_proxy_table(nodes=nodes_a, edges=edges_a)) == json.dumps(
        mod.micro_rs_proxy_table(nodes=nodes_b, edges=edges_b)
    )
    for subject in ("theme:space_launch", "theme:grid_micro", "theme:space"):
        assert json.dumps(mod.read_micro_rs_proxy(subject, nodes=nodes_a, edges=edges_a)) == json.dumps(
            mod.read_micro_rs_proxy(subject, nodes=nodes_b, edges=edges_b)
        )


def test_malformed_and_blank_subjects_refuse_cleanly(hierarchy):
    nodes, edges = hierarchy
    for bad in ("", "   ", None, 7):
        env = mod.read_micro_rs_proxy(bad, nodes=nodes, edges=edges)
        assert env["status"] == "not_applicable"
        assert env["reason_code"] == "not_applicable"
        assert env["subject_id"] == bad


def test_retired_like_statuses_come_from_the_owner():
    # SPEC §5: retirement vocabulary is the incumbent store's, never redefined.
    assert store.RETIRED_LIKE_STATUSES == frozenset({"retired", "merged"})
