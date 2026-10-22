"""Point-in-time knowledge cutoff and invalid-shadow handling for qualified_reads."""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.theme_graph import theme_state
from engine.theme_graph.ontology import (
    RepositoryStore,
    _collapse_relevant_edges,
    _nodes_as_known,
    _parse_date,
    _records,
    compose_neighborhood,
)
from engine.theme_graph.selection_cohort import FLAGS
from engine.theme_graph import selection_cohort_reads as scr
from engine.theme_graph.selection_cohort_reads import (
    COMPOSE_KEYS,
    MEMBERSHIP_OWNER_SCHEMA,
    _REASON_NO_OVERLAP,
    _REASON_OWNER,
    publication_reads,
    qualified_reads,
)


def _knowledge_cutoff_for_tests(known_at: str):
    if hasattr(scr, "_knowledge_cutoff"):
        return scr._knowledge_cutoff(known_at)
    return scr._knowledge_cutoff_date(known_at)

COMPOSE_NEIGHBORHOOD_LEGACY_SHA256 = (
    "8578cde8392c96c1a1823da6c0821a9118a3b112bcb3ec7f1346404f91f24999"
)

KNOWN_INSTANT = "2026-10-06T01:00:00Z"
EFFECTIVE_INSTANT = "2026-10-06T08:00:00Z"
COMPANY = "co:us:HUBB"
THEME = "ltheme:ths:battery"
OLD = "2026-10-02T08:00:00Z"


def _selection():
    from engine.theme_graph.selection_cohort import content_sha256

    rows = [
        {
            "selection_id": "owner-row-0",
            "original_identity": {"ticker": "HUBB", "node_id": COMPANY},
            "original_reasons": {"en": "Reason", "zh": "理由"},
            "source_row": {"ticker": "HUBB", "display_rank": 1},
        }
    ]
    return dict(
        owner="fixture-selection-owner",
        source_schema="fixture.owner/v1",
        source_ref="fixture://immutable-generation",
        source_sha256="a" * 64,
        generation_id="owner-generation-1",
        cohort_scope="us_today",
        effective_at=EFFECTIVE_INSTANT,
        selected_at=KNOWN_INSTANT,
        known_at=KNOWN_INSTANT,
        n_selected=1,
        rows=rows,
        rows_sha256=content_sha256(rows),
        ordered_identity_sha256=content_sha256([r["original_identity"] for r in rows]),
        ordered_reasons_sha256=content_sha256([r["original_reasons"] for r in rows]),
    )


def _resolved_identity():
    return {
        "node_id": COMPANY,
        "resolution_state": "RESOLVED",
        "security_id": "SEC:US-XNYS-HUBB",
        "computed_at": OLD,
        "engine_version": "theme_graph.v1",
    }


@pytest.fixture
def graph_root(tmp_path, monkeypatch):
    from lib import config

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "theme_graph").mkdir(parents=True)
    registry = Path(__file__).resolve().parents[1] / "config" / "theme_sources.yml"
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "theme_sources.yml").write_bytes(registry.read_bytes())
    return tmp_path


@pytest.fixture
def data_root(graph_root, monkeypatch):
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.rights.emission_allowed",
        lambda family, path=None: True,
    )
    return graph_root


def _write_graph(
    tmp_path,
    *,
    lifecycle_computed_at: str,
    belief_time: str = "2015-01-01",
    node_computed_at: str = OLD,
):
    tg = tmp_path / "theme_graph"
    nodes = pd.DataFrame(
        [
            {
                "node_id": COMPANY,
                "kind": "company",
                "name_en": "Hubbell",
                "name_zh": None,
                "market_scope": "us",
                "tier": None,
                "status": "active",
                "merged_into": None,
                "birth_date": "2015-01-01",
                "retire_date": None,
                "identity_epoch": 1,
                "external_ids": "{}",
                "provenance": "test",
                "computed_at": node_computed_at,
                "engine_version": "theme_graph.v1",
                "source_meta": None,
            },
            {
                "node_id": THEME,
                "kind": "local_theme",
                "name_en": "Battery",
                "name_zh": "电池",
                "market_scope": "cn",
                "tier": None,
                "status": "active",
                "merged_into": None,
                "birth_date": "2015-01-01",
                "retire_date": None,
                "identity_epoch": 1,
                "external_ids": "{}",
                "provenance": "test",
                "computed_at": OLD,
                "engine_version": "theme_graph.v1",
                "source_meta": json.dumps({"source_family": "ths", "native_id": "battery"}),
            },
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "edge_id": "edge-member-1",
                "type": "MEMBER_OF",
                "src": COMPANY,
                "dst": THEME,
                "valid_from": "2015-01-01",
                "valid_to": None,
                "evidence_time": "2015-01-01",
                "belief_time": belief_time,
                "era": "OBSERVED",
                "source_class": "scrape",
                "date_provenance": "membership_pit",
                "evidence_refs": json.dumps(["data/baskets/test/membership.json"]),
                "confidence_basis": "membership_pit.ths.v1",
                "economic_share": None,
                "trading_beta": None,
                "attention_share": None,
                "economic_share_formula_id": None,
                "trading_beta_formula_id": None,
                "attention_share_formula_id": None,
                "economic_share_display": None,
                "trading_beta_display": None,
                "attention_share_display": None,
                "computed_at": OLD,
                "engine_version": "theme_graph.v1",
            }
        ]
    )
    lifecycle = pd.DataFrame(
        [
            {
                "schema": "gmi.node_lifecycle/v1",
                "node_id": THEME,
                "status": "retired",
                "retire_date": "2026-10-06",
                "merged_into": None,
                "reason": "test",
                "evidence": "{}",
                "ratified_by": "test",
                "computed_at": lifecycle_computed_at,
                "engine_version": "theme_graph.v1",
            }
        ]
    )
    nodes.to_parquet(tg / "nodes.parquet", index=False)
    edges.to_parquet(tg / "edges.parquet", index=False)
    lifecycle.to_parquet(tg / "node_lifecycle.parquet", index=False)
    (tg / "probation").mkdir(exist_ok=True)
    (tg / "probation" / "proposals.jsonl").write_text("", encoding="utf-8")
    (tg / "_meta.json").write_text(json.dumps({"engine_version": "theme_graph.v1"}), encoding="utf-8")


def _node_map_for_reads(data_root, selection):
    store_view = RepositoryStore()
    effective_at = selection["effective_at"]
    known_at = selection["known_at"]
    if "T" in effective_at:
        asof = dt.datetime.fromisoformat(effective_at.replace("Z", "+00:00")).date()
    else:
        asof = dt.date.fromisoformat(effective_at[:10])
    cutoff = _knowledge_cutoff_for_tests(known_at)
    nodes = _records(store_view.read_nodes())
    lifecycle = _records(store_view.read_node_lifecycle())
    return _nodes_as_known(nodes, lifecycle, asof=asof, knowledge_cutoff=cutoff)


def _qualified_reads_setup(data_root, monkeypatch, lifecycle_computed_at: str):
    _write_graph(data_root, lifecycle_computed_at=lifecycle_computed_at)
    source = _selection()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    return source


def test_t1_late_lifecycle_not_visible_to_qualified_reads(data_root, monkeypatch):
    source = _qualified_reads_setup(data_root, monkeypatch, "2026-10-06T18:00:00Z")
    reads = qualified_reads(source, data_dir=data_root)
    assert reads["membership_reads"]
    node_map = _node_map_for_reads(data_root, source)
    assert node_map[THEME]["status"] == "active"


def test_t2_early_lifecycle_visible_to_qualified_reads(data_root, monkeypatch):
    source = _qualified_reads_setup(data_root, monkeypatch, "2026-10-06T00:30:00Z")
    reads = qualified_reads(source, data_dir=data_root)
    assert reads["membership_reads"]
    node_map = _node_map_for_reads(data_root, source)
    assert node_map[THEME]["status"] == "retired"


def test_t3_date_only_belief_instant_known_at(graph_root):
    _write_graph(graph_root, lifecycle_computed_at=OLD, belief_time="2026-10-06")
    store_view = RepositoryStore()
    edges = _records(store_view.read_edges())
    asof = dt.date(2026, 10, 6)
    cutoff = _knowledge_cutoff_for_tests(KNOWN_INSTANT)
    live_same_day, _ = _collapse_relevant_edges(
        edges, node_id=COMPANY, asof=asof, knowledge_cutoff=cutoff
    )
    assert not live_same_day
    _write_graph(graph_root, lifecycle_computed_at=OLD, belief_time="2026-10-05")
    store_view = RepositoryStore()
    edges = _records(store_view.read_edges())
    live_prior, _ = _collapse_relevant_edges(
        edges, node_id=COMPANY, asof=asof, knowledge_cutoff=cutoff
    )
    assert live_prior


def test_t4_legacy_date_cutoff_unchanged_and_compose_neighborhood_digest(graph_root):
    _write_graph(
        graph_root,
        lifecycle_computed_at="2026-10-06T18:00:00Z",
        belief_time="2026-10-06",
        node_computed_at="2026-10-06T18:00:00Z",
    )
    store_view = RepositoryStore()
    nodes = _records(store_view.read_nodes())
    lifecycle = _records(store_view.read_node_lifecycle())
    asof = dt.date(2026, 10, 6)
    cutoff = dt.date(2026, 10, 6)
    node_map = _nodes_as_known(nodes, lifecycle, asof=asof, knowledge_cutoff=cutoff)
    assert node_map[THEME]["status"] == "retired"
    edges = _records(store_view.read_edges())
    live, _ = _collapse_relevant_edges(
        edges, node_id=COMPANY, asof=asof, knowledge_cutoff=cutoff
    )
    assert live
    result = compose_neighborhood(
        store_view,
        node_id=THEME,
        asof="2026-10-06",
        knowledge_cutoff="2026-10-06",
    )
    digest = hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
    assert digest == COMPOSE_NEIGHBORHOOD_LEGACY_SHA256


def _valid_state_artifact(data_root, theme=THEME):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("fx_state", root / "tests/test_theme_graph_state.py")
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    fx.QUERY = {"effective_at": EFFECTIVE_INSTANT, "known_at": KNOWN_INSTANT}
    src = fx.subject(theme, qualified=True)
    src.update(source_family="ths", native_id="battery")
    return fx.compose([src], generated_at=KNOWN_INSTANT)


def _run_qualified_with_shadow(data_root, monkeypatch, artifact):
    _write_graph(data_root, lifecycle_computed_at=OLD)
    if artifact is not None:
        path = data_root / "theme_graph" / "shadow_theme_state.v1.json"
        if isinstance(artifact, str):
            path.write_text(artifact, encoding="utf-8")
        else:
            path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
    source = _selection()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    return qualified_reads(source, data_dir=data_root)


def test_t5_invalid_shadow_empty_object(data_root, monkeypatch):
    reads = _run_qualified_with_shadow(data_root, monkeypatch, {})
    state_rows = [u for u in reads["unqualified"] if u.get("kind") == "state"]
    assert state_rows
    row = state_rows[0]
    assert row["reason_code"] == _REASON_OWNER
    assert row["owner"] == theme_state.READ_SCHEMA
    assert row["detail"] == "invalid"


def test_t6_invalid_shadow_wrong_schema(data_root, monkeypatch):
    artifact = _valid_state_artifact(data_root)
    artifact["schema"] = "wrong.schema/v9"
    reads = _run_qualified_with_shadow(data_root, monkeypatch, artifact)
    state_rows = [u for u in reads["unqualified"] if u.get("kind") == "state"]
    assert state_rows and state_rows[0]["detail"] == "invalid"


def test_t7_invalid_shadow_generation_mismatch(data_root, monkeypatch):
    artifact = _valid_state_artifact(data_root)
    artifact["generation_id"] = "mismatched-generation-id"
    reads = _run_qualified_with_shadow(data_root, monkeypatch, artifact)
    state_rows = [u for u in reads["unqualified"] if u.get("kind") == "state"]
    assert state_rows and state_rows[0]["detail"] == "invalid"


def test_t8_missing_and_bad_json_keep_concept_detail(data_root, monkeypatch):
    _write_graph(data_root, lifecycle_computed_at=OLD)
    source = _selection()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    reads_missing = qualified_reads(source, data_dir=data_root)
    row_missing = next(u for u in reads_missing["unqualified"] if u.get("kind") == "state")
    assert row_missing["detail"] == THEME
    bad_path = data_root / "theme_graph" / "shadow_theme_state.v1.json"
    bad_path.write_text("{not-json", encoding="utf-8")
    reads_bad = qualified_reads(source, data_dir=data_root)
    row_bad = next(u for u in reads_bad["unqualified"] if u.get("kind") == "state")
    assert row_bad["detail"] == THEME


def test_t9_authority_stamp_and_publication_keys(data_root, monkeypatch):
    _write_graph(data_root, lifecycle_computed_at=OLD)
    source = _selection()
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    reads = qualified_reads(source, data_dir=data_root)
    assert reads["authority_ceiling"] == "research_internal_only"
    for flag in FLAGS:
        assert flag in reads
        assert reads[flag] is False
    pub = publication_reads(source, data_dir=data_root)
    assert set(pub) == set(COMPOSE_KEYS)


def _membership_concept_node_ids(reads: dict) -> list[str]:
    ids: list[str] = []
    for receipt in reads["membership_reads"].values():
        for row in receipt["memberships"]:
            ids.append(str(row["node_id"]))
    return ids


def _install_cutoff_spies(monkeypatch):
    recorded_nodes: list[object] = []
    recorded_edges: list[object] = []
    orig_nodes = scr._nodes_as_known
    orig_collapse = scr._collapse_relevant_edges

    def spy_nodes(*args, **kwargs):
        recorded_nodes.append(kwargs.get("knowledge_cutoff"))
        return orig_nodes(*args, **kwargs)

    def spy_collapse(*args, **kwargs):
        recorded_edges.append(kwargs.get("knowledge_cutoff"))
        return orig_collapse(*args, **kwargs)

    monkeypatch.setattr(scr, "_nodes_as_known", spy_nodes)
    monkeypatch.setattr(scr, "_collapse_relevant_edges", spy_collapse)
    return recorded_nodes, recorded_edges


def test_t10_qualified_reads_wires_knowledge_cutoff_into_ontology(data_root, monkeypatch):
    recorded_nodes, recorded_edges = _install_cutoff_spies(monkeypatch)
    source = _qualified_reads_setup(data_root, monkeypatch, "2026-10-06T18:00:00Z")
    qualified_reads(source, data_dir=data_root)

    expected_instant = dt.datetime(2026, 10, 6, 1, 0, tzinfo=dt.timezone.utc)
    assert len(recorded_nodes) >= 1
    assert len(recorded_edges) >= 2
    for cutoff in recorded_nodes + recorded_edges:
        assert isinstance(cutoff, dt.datetime)
        assert cutoff.tzinfo is not None
        assert cutoff == expected_instant

    recorded_nodes.clear()
    recorded_edges.clear()
    _write_graph(data_root, lifecycle_computed_at="2026-10-06T18:00:00Z")
    source_date = _selection()
    source_date = {**source_date, "known_at": "2026-10-06"}
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    qualified_reads(source_date, data_dir=data_root)

    expected_day = dt.date(2026, 10, 6)
    for cutoff in recorded_nodes + recorded_edges:
        assert type(cutoff) is dt.date
        assert cutoff == expected_day


def test_t11_belief_time_same_day_excludes_theme_from_membership_reads(data_root, monkeypatch):
    monkeypatch.setattr(
        "engine.theme_graph.selection_cohort_reads.ir.resolve_graph_node_identity",
        lambda node_id, asof=None: _resolved_identity(),
    )
    source = _selection()

    _write_graph(data_root, lifecycle_computed_at=OLD, belief_time="2026-10-06")
    reads_same_day = qualified_reads(source, data_dir=data_root)
    assert THEME not in _membership_concept_node_ids(reads_same_day)
    membership_unqualified = [
        u
        for u in reads_same_day["unqualified"]
        if u.get("kind") == "membership" and u.get("detail") == COMPANY
    ]
    if membership_unqualified:
        row = membership_unqualified[0]
        assert row["reason_code"] == _REASON_NO_OVERLAP
        assert row["owner"] == MEMBERSHIP_OWNER_SCHEMA

    _write_graph(data_root, lifecycle_computed_at=OLD, belief_time="2026-10-05")
    reads_prior_day = qualified_reads(source, data_dir=data_root)
    assert THEME in _membership_concept_node_ids(reads_prior_day)
